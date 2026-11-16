"""Achados da revisão de 15/11 sobre a v1 (exploração adicional; nada aqui altera selecao_modelo.json).

2. Viés de seleção: chaves com variáveis mas sem nenhum registro pontuável em ago–set ficam fora da avaliação.
   Medimos quantas delas cada modelo marcaria como risco 2–3 (o falso alarme que a avaliação não vê).
3. Repetibilidade do rótulo (referência, não limite superior): o próprio rótulo comparado entre janelas, sem
   modelo, e com agregação maior (célula H3 res 8 e 2 faixas dia/noite). Cortes e chaves diferem do Teste.
6. Deslocamento de distribuição: níveis no treino × Teste e quantis do Teste frente aos cortes do treino.
7. Bootstrap em blocos espaciais: reamostra células-mãe H3 res 7 (~5 km²) em vez de células res 9. Com só ~9 blocos
   o IC por blocos é instável: serve de sensibilidade, não de IC principal.
8. Importância por permutação (macro-F1 no Teste) × importância por impureza do RF contido. Diagnóstico exploratório
   no próprio Teste: variáveis correlacionadas repartem importância; dp = variação entre permutações, não amostral.
"""
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
import torch  # noqa: F401 — antes do xgboost (ver modelos.py)

import h3
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import f1_score, make_scorer

from ml import config as C
from ml import features, rotulo
from ml import modelos as M
from ml.diagnostico_rf import _rf
from ml.incerteza_custo import REGULARIZADO, bootstrap, diferencas, metricas, resumo_ic


def vies_selecao(u, modelos, rf_reg, cortes):
    X = features.construir(u, C.ORIGENS["Teste"]["features"])
    y_pont = rotulo.rotulos(u, "Teste")
    Xsem = X.loc[X.index.difference(y_pont.index)].copy()
    Xsem.insert(0, "origem", "Teste")
    prev = {n: np.asarray(M.prever(n, m, Xsem)) for n, m in modelos.items()}
    prev["rf_regularizado"] = rf_reg.predict(M._matriz(Xsem))
    prev["base_persistencia"] = features.persistencia(Xsem, cortes)
    return dict(n_chaves_sem_rotulo=int(len(Xsem)),
                fracao_marcada_risco_2_3={k: float((p >= 2).mean()) for k, p in prev.items()},
                distribuicao_prevista={k: {int(a): int(b) for a, b in zip(*np.unique(p, return_counts=True))}
                                       for k, p in prev.items()})


def _f1(a, b):
    return float(f1_score(a, b, average="macro"))


def teto(u):
    """Repetibilidade do rótulo entre janelas (nome histórico `teto`; não é limite superior)."""
    u8 = u.copy()
    u8["celula"] = [h3.cell_to_parent(c, 8) for c in u.celula]
    horas2 = {0: 12, 1: 12}
    linhas = []
    for res, base in (("res9 (~0,1 km²)", u), ("res8 (~0,7 km²)", u8)):
        for duas in (False, True):
            x = base.copy()
            if duas:
                x["faixa"] = x.faixa.map({0: 1, 1: 0, 2: 0, 3: 1, 4: 1})  # 0 = dia 6–18h, 1 = noite
            horas = horas2 if duas else C.FAIXA_HORAS

            def pont(meses):
                a = rotulo.agregar(x, meses)
                h = a.index.get_level_values("faixa").map(horas).astype(float)
                return a.soma / len(meses) / h.values, a.n

            for ant, post in (([8], [9]), ([4, 5], [6, 7]), ([6, 7], [8, 9]), (list(range(1, 8)), [8, 9])):
                sa, _ = pont(ant)
                sb, nb = pont(post)
                cortes = list(np.quantile(sa, [.25, .5, .75]))
                k = sa.index.intersection(sb.index)
                ya, yb = np.digitize(sa[k], cortes), np.digitize(sb[k], cortes)
                linhas.append(dict(resolucao=res, faixas="2 (dia/noite)" if duas else "5",
                                   janelas=f"{ant[0]}-{ant[-1]} → {post[0]}-{post[-1]}", n_chaves=int(len(k)),
                                   mediana_registros_rotulo=float(nb[k].median()), macro_f1=_f1(yb, ya),
                                   concordancia_exata=float((ya == yb).mean()),
                                   ate_1_nivel=float((np.abs(ya - yb) <= 1).mean())))
    return linhas


def deslocamento(ytr, yte, u, cortes):
    p = rotulo.rotulos(u, "Teste")
    return dict(cortes_treino=cortes,
                quantis_teste_25_50_75=[float(v) for v in np.quantile(p.values, [.25, .5, .75])],
                proporcao_treino={int(k): float(v) for k, v in ytr.value_counts(normalize=True).sort_index().items()},
                proporcao_teste={int(k): float(v) for k, v in yte.value_counts(normalize=True).sort_index().items()})


def bootstrap_blocos(y, prev, celulas):
    blocos = np.array([h3.cell_to_parent(c, 7) for c in celulas])
    pares = [("rf_regularizado", "base_persistencia"), ("rf_regularizado", "random_forest"),
             ("kmeans_pca", "base_persistencia")]
    prev = {k: prev[k] for k in ("rf_regularizado", "random_forest", "kmeans_pca", "base_persistencia")}
    pontual = {k: metricas(y, p) for k, p in prev.items()}
    out = {}
    for nome, g in (("celula_res9", celulas), ("bloco_res7", blocos)):
        boot = bootstrap(y, prev, g)
        out[nome] = dict(n_grupos=int(len(np.unique(g))),
                         macro_f1={k: v["macro_f1"]["ic95"] for k, v in resumo_ic(boot, pontual).items()},
                         diferencas={k: v["macro_f1"] for k, v in diferencas(boot, pares).items()})
    return out


def importancias(rf, Xte, yte):
    cols = features.COLUNAS_X
    r = permutation_importance(rf, M._matriz(Xte), yte.values, n_repeats=20, random_state=C.SEMENTE, n_jobs=1,
                               scoring=make_scorer(f1_score, average="macro"))
    return sorted([dict(variavel=c, permutacao_media=float(m), permutacao_dp=float(s), impureza=float(i))
                   for c, m, s, i in zip(cols, r.importances_mean, r.importances_std, rf.feature_importances_)],
                  key=lambda d: -d["permutacao_media"])


def main():
    u = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    selecao = json.loads((C.RESULTADOS / "selecao_modelo.json").read_text())
    extra_cv = json.loads((C.RESULTADOS / "cv_exploracao_adicional.json").read_text())
    _, extra, (Xtr, ytr, Xte, yte), prev, modelos = M.avaliar_final(u, selecao, extra_cv)
    cortes = extra["cortes"]
    rf = _rf(REGULARIZADO).fit(M._matriz(Xtr), ytr.values)
    prev = {k: np.asarray(v) for k, v in prev.items() if k != "base_classe_mais_frequente"}
    prev["rf_regularizado"] = rf.predict(M._matriz(Xte))
    celulas = np.asarray(Xte.index.get_level_values("celula"))
    saida = dict(
        nota="exploração adicional (ago–set já visto); seleção pré-registrada inalterada",
        item2_vies_selecao=vies_selecao(u, modelos, rf, cortes),
        item3_repetibilidade_rotulo=teto(u),
        item6_deslocamento=deslocamento(ytr, yte, u, cortes),
        item7_bootstrap_blocos=bootstrap_blocos(yte.values, prev, celulas),
        item8_importancias_rf_regularizado=importancias(rf, Xte, yte),
    )
    (C.RESULTADOS / "achados_revisao.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n")
    return saida


if __name__ == "__main__":
    s = main()
    print(json.dumps(s["item2_vies_selecao"]["fracao_marcada_risco_2_3"], indent=1),
          s["item2_vies_selecao"]["n_chaves_sem_rotulo"])
    print(pd.DataFrame(s["item3_repetibilidade_rotulo"]).to_string(index=False))
    print(json.dumps(s["item6_deslocamento"]))
    print(json.dumps(s["item7_bootstrap_blocos"], ensure_ascii=False, indent=1))
    print(pd.DataFrame(s["item8_importancias_rf_regularizado"]).to_string(index=False))
