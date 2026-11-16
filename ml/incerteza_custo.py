"""Intervalos de confiança no Teste e avaliação com custo assimétrico (exploração adicional).

Feito depois de ago–set ter sido visto; nada aqui altera `selecao_modelo.json`.

1. Bootstrap por célula: sorteia células H3 com reposição, levando todas as faixas da célula juntas,
   porque chaves da mesma célula não são independentes. Dá IC 95 % de cada métrica e das diferenças
   pareadas entre modelos (mesmas reamostras para todos).
2. Custo assimétrico: para quem anda na rua, avisar risco que não vem (superestimar o nível) é menos grave
   que calar sobre um risco real (subestimar). Custo de um erro = distância de níveis, multiplicada por
   PESO_SUB quando a previsão fica abaixo do rótulo. PESO_SUB = 2 é uma escolha de produto, não ajustada
   nos dados; 1,5 e 3 aparecem como sensibilidade.
3. Regra de decisão por custo: em vez do nível mais provável, o RF escolhe o nível de menor custo esperado
   dadas as probabilidades. O peso usado no Teste é o fixado acima; a CV mostra o efeito antes do Teste.
"""
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
import torch  # noqa: F401 — antes do xgboost (ver modelos.py)

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, recall_score

from ml import config as C
from ml import modelos as M
from ml.diagnostico_rf import BASE, _rf, dobras

REGULARIZADO = dict(n_estimators=300, max_depth=6, min_samples_leaf=80, max_features=0.5)
PESO_SUB = 2.0
PESOS_SENSIBILIDADE = [1.0, 1.5, 2.0, 3.0]
N_BOOT = 2000


def matriz_custo(peso_sub):
    n = len(M.NIVEIS)
    return np.array([[(y - p) * peso_sub if p < y else (p - y) for p in range(n)] for y in range(n)], float)


def decidir_por_custo(proba, peso_sub):
    """Nível de menor custo esperado; proba tem colunas na ordem M.NIVEIS."""
    return (proba @ matriz_custo(peso_sub)).argmin(1)


def metricas(y, p, peso_sub=PESO_SUB):
    y, p = np.asarray(y), np.asarray(p)
    return dict(
        macro_f1=float(f1_score(y, p, average="macro", labels=M.NIVEIS, zero_division=0)),
        custo_medio=float(matriz_custo(peso_sub)[y, p].mean()),
        taxa_subestimacao=float((p < y).mean()),
        taxa_superestimacao=float((p > y).mean()),
        recall_nivel_3=float(recall_score(y == 3, p == 3, zero_division=0)),
        recall_risco_alto=float(recall_score(y >= 2, p >= 2, zero_division=0)),  # níveis 2–3 sinalizados como 2–3
        precisao_risco_alto=float(((p >= 2) & (y >= 2)).sum() / max((p >= 2).sum(), 1)),
    )


def bootstrap(y, previsoes, celulas, n=N_BOOT, semente=C.SEMENTE):
    rng = np.random.default_rng(semente)
    unicas = np.unique(celulas)
    pos = {c: np.flatnonzero(celulas == c) for c in unicas}
    amostras = {k: [] for k in previsoes}
    for _ in range(n):
        idx = np.concatenate([pos[c] for c in rng.choice(unicas, len(unicas), replace=True)])
        for k, p in previsoes.items():
            amostras[k].append(metricas(y[idx], p[idx]))
    return {k: pd.DataFrame(v) for k, v in amostras.items()}


def _ic(s):
    return [float(s.quantile(0.025)), float(s.quantile(0.975))]


def resumo_ic(boot, pontual):
    return {k: {m: dict(valor=pontual[k][m], ic95=_ic(df[m])) for m in df} for k, df in boot.items()}


def diferencas(boot, pares, n_familia=1):
    """Diferença pareada a − b por reamostra. ic95 é nominal; ic_bonferroni ajusta para `n_familia` comparações.
    frac_reamostras_a_melhor = fração das reamostras bootstrap em que a supera b: descritiva, não é p-valor
    nem probabilidade posterior."""
    alfa = 0.05 / max(n_familia, 1)
    out = {}
    for a, b in pares:
        d = boot[a] - boot[b]
        out[f"{a} − {b}"] = {m: dict(media=float(d[m].mean()), ic95=_ic(d[m]),
                                     ic_bonferroni=[float(d[m].quantile(alfa / 2)), float(d[m].quantile(1 - alfa / 2))],
                                     frac_reamostras_a_melhor=float((d[m] < 0).mean()
                                                                    if m in ("custo_medio", "taxa_subestimacao")
                                                                    else (d[m] > 0).mean()))
                             for m in ("macro_f1", "custo_medio", "taxa_subestimacao", "recall_risco_alto")}
    return out


def cv_regra_custo(u):
    """Efeito da regra de custo nas dobras de CV, por peso (antes do Teste)."""
    linhas = []
    for i, (Xtr, ytr, Xv, yv) in enumerate(dobras(u)):
        for nome, p in (("rf_original", BASE), ("rf_regularizado", REGULARIZADO)):
            m = _rf(p).fit(Xtr, ytr)
            linhas.append(dict(dobra=i, modelo=nome, regra="mais_provavel", peso=None, **metricas(yv, m.predict(Xv))))
            for w in PESOS_SENSIBILIDADE:
                linhas.append(dict(dobra=i, modelo=nome, regra="menor_custo", peso=w,
                                   **metricas(yv, decidir_por_custo(m.predict_proba(Xv), w))))
    df = pd.DataFrame(linhas)
    return df.groupby(["modelo", "regra", "peso"], dropna=False).mean(numeric_only=True).drop(columns="dobra").reset_index()


def main():
    u = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    cv = cv_regra_custo(u)

    selecao = json.loads((C.RESULTADOS / "selecao_modelo.json").read_text())
    extra_cv = json.loads((C.RESULTADOS / "cv_exploracao_adicional.json").read_text())
    _, _, (Xtr, ytr, Xte, yte), prev, _ = M.avaliar_final(u, selecao, extra_cv)
    prev = {("rf_original" if k == "random_forest" else k): np.asarray(v) for k, v in prev.items()
            if k != "base_classe_mais_frequente"}
    rf_reg = _rf(REGULARIZADO).fit(M._matriz(Xtr), ytr.values)
    proba = rf_reg.predict_proba(M._matriz(Xte))
    prev["rf_regularizado"] = rf_reg.predict(M._matriz(Xte))
    prev["rf_regularizado_custo"] = decidir_por_custo(proba, PESO_SUB)
    rf_or = _rf(BASE).fit(M._matriz(Xtr), ytr.values)
    prev["rf_original_custo"] = decidir_por_custo(rf_or.predict_proba(M._matriz(Xte)), PESO_SUB)

    y = yte.values
    celulas = np.asarray(Xte.index.get_level_values("celula"))
    pontual = {k: metricas(y, p) for k, p in prev.items()}
    boot = bootstrap(y, prev, celulas)
    pares = [("rf_regularizado", "rf_original"), ("rf_regularizado", "base_persistencia"),
             ("rf_regularizado", "kmeans_pca"), ("kmeans_pca", "base_persistencia"),
             ("rf_regularizado_custo", "rf_regularizado"), ("rf_regularizado_custo", "base_persistencia"),
             ("rf_regularizado_custo", "kmeans_pca")]
    sens = {str(w): {"rf_regularizado_custo": metricas(y, decidir_por_custo(proba, w), w),
                     "rf_regularizado": metricas(y, prev["rf_regularizado"], w),
                     "base_persistencia": metricas(y, prev["base_persistencia"], w)}
            for w in PESOS_SENSIBILIDADE}

    saida = dict(
        nota="exploração adicional (ago–set já visto); a escolha pré-registrada não muda",
        bootstrap=dict(unidade="célula H3 (todas as faixas juntas)", reamostras=N_BOOT,
                       n_chaves=int(len(y)), n_celulas=int(len(np.unique(celulas)))),
        peso_subestimacao=PESO_SUB, matriz_custo=matriz_custo(PESO_SUB).tolist(),
        teste=resumo_ic(boot, pontual), diferencas_pareadas=diferencas(boot, pares),
        sensibilidade_peso_teste=sens,
        matrizes_confusao_teste={k: pd.crosstab(pd.Series(y, name="real"), pd.Series(p, name="previsto"))
                                 .reindex(index=M.NIVEIS, columns=M.NIVEIS, fill_value=0).values.tolist()
                                 for k, p in prev.items() if k.startswith("rf_regularizado")},
    )
    C.RESULTADOS.mkdir(parents=True, exist_ok=True)
    cv.to_csv(C.RESULTADOS / "cv_regra_custo.csv", index=False, float_format="%.4f")
    (C.RESULTADOS / "incerteza_custo.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n")
    return cv, saida


if __name__ == "__main__":
    cv, s = main()
    pd.set_option("display.width", 200)
    print(cv.to_string(index=False))
    for k, v in s["teste"].items():
        print(k, {m: (round(d["valor"], 3), [round(x, 3) for x in d["ic95"]]) for m, d in v.items()})
    print(json.dumps(s["diferencas_pareadas"], ensure_ascii=False, indent=1))
    print(json.dumps(s["matrizes_confusao_teste"]))
