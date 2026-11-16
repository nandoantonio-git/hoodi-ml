"""T024–T026: linhas de base, candidatos com busca de hiperparâmetros por CV com expurgo e avaliação final.

Ordem obrigatória (research D-03/D-04): a seleção usa só a CV no treino e é gravada em
`resultados/selecao_modelo.json` ANTES de qualquer consulta a ago–set.
"""
import itertools
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")  # torch + xgboost no macOS: com várias threads o processo cai
import torch  # noqa: F401 — antes do xgboost: duas libomp no macOS derrubam o processo na ordem inversa

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from ml import config as C
from ml import features, rotulo, sequenciais

# Treino da dobra → origem validada. T2 não é validada (nenhum rótulo anterior sem sobreposição).
DOBRAS = [(["T1"], "T3"), (["T1", "T2"], "T4")]
NIVEIS = [0, 1, 2, 3]

GRADES = {
    "random_forest": dict(n_estimators=[100, 300], max_depth=[None, 5, 10], min_samples_leaf=[1, 5]),
    "xgboost": dict(n_estimators=[100, 300], max_depth=[3, 6], learning_rate=[0.05, 0.1, 0.3]),
    "mlp": dict(hidden_layer_sizes=[(32,), (64,), (64, 32)], alpha=[1e-4, 1e-2], learning_rate_init=[1e-3, 1e-2]),
}
# Exploração adicional (entraram depois de ago–set ter sido visto; nunca a escolha pré-registrada)
GRADES_EXTRA = {
    "lstm": dict(hidden_size=[16, 32, 64], learning_rate=[1e-3, 1e-2], dropout=[0.0, 0.3]),
    "kmeans_pca": dict(n_components=[2, 4, 8], n_clusters=[4, 8, 16], whiten=[False, True]),
}
PRE_REGISTRADOS = list(GRADES)


def combinacoes(nome):
    g = {**GRADES, **GRADES_EXTRA}[nome]
    return [dict(zip(g, v)) for v in itertools.product(*g.values())]


def novo_modelo(nome, params, u=None):
    if nome == "lstm":
        return sequenciais.LSTMNivel(u, **params)
    if nome == "kmeans_pca":
        return sequenciais.KMeansPCANivel(**params)
    if nome == "random_forest":
        return RandomForestClassifier(**params, class_weight="balanced", random_state=C.SEMENTE, n_jobs=-1)
    if nome == "xgboost":
        return XGBClassifier(**params, objective="multi:softprob", num_class=4, random_state=C.SEMENTE,
                             n_jobs=4, tree_method="hist", verbosity=0)
    if nome == "mlp":
        return make_pipeline(StandardScaler(), MLPClassifier(**params, max_iter=2000, early_stopping=True,
                                                             random_state=C.SEMENTE))
    raise ValueError(nome)


def ajustar(nome, params, X, y, u=None):
    """X é o DataFrame de features.exemplos; os modelos tabulares recebem só a matriz."""
    m = novo_modelo(nome, params, u)
    if nome in GRADES_EXTRA:
        m.fit(X, y)
    elif nome == "xgboost":
        m.fit(_matriz(X), y, sample_weight=compute_sample_weight("balanced", y))
    else:  # RF usa class_weight; MLP não aceita peso (desbalanceamento declarado no relatório)
        m.fit(_matriz(X), y)
    return m


def prever(nome, m, X):
    return m.predict(X) if nome in GRADES_EXTRA else m.predict(_matriz(X))


def metricas(y, p) -> dict:
    y, p = np.asarray(y), np.asarray(p)
    return dict(macro_f1=float(f1_score(y, p, average="macro", labels=NIVEIS, zero_division=0)),
                balanced_accuracy=float(balanced_accuracy_score(y, p)),
                erro_abs_medio_nivel=float(np.abs(y - p).mean()),
                acuracia=float(accuracy_score(y, p)))


def cortes_de(u, origens) -> list:
    todos = pd.concat([rotulo.rotulos(u, o) for o in origens])
    return [float(v) for v in np.quantile(todos.values, [0.25, 0.5, 0.75])]


def conjunto(u, origens, cortes):
    partes = [features.exemplos(u, o, cortes) for o in origens]
    X = pd.concat([p[0] for p in partes])
    y = pd.concat([p[1] for p in partes])
    return X, y, {o: p[2] for o, p in zip(origens, partes)}


def _matriz(X):
    return X[features.COLUNAS_X].values


def _baselines(Xtr, ytr, Xav, cortes):
    classe = int(pd.Series(ytr).mode().iloc[0])
    return {"base_classe_mais_frequente": np.full(len(Xav), classe),
            "base_persistencia": features.persistencia(Xav, cortes)}


def validacao_cruzada(u, nomes=None) -> dict:
    """Métricas por dobra e média, para baselines e cada combinação de cada candidato. Nunca toca ago–set."""
    dobras = []
    for treino, val in DOBRAS:
        c = cortes_de(u, treino)
        Xtr, ytr, _ = conjunto(u, treino, c)
        Xv, yv, _ = conjunto(u, [val], c)
        dobras.append((treino, val, c, Xtr, ytr, Xv, yv))
    res = {}
    for nome in nomes or GRADES:
        res[nome] = []
        for params in combinacoes(nome):
            por = []
            for treino, val, c, Xtr, ytr, Xv, yv in dobras:
                m = ajustar(nome, params, Xtr, ytr.values, u)
                por.append(dict(treino=treino, validada=val, **metricas(yv, prever(nome, m, Xv))))
            res[nome].append(dict(params=params, dobras=por, media=_media(por)))
    for treino, val, c, Xtr, ytr, Xv, yv in dobras:
        for b, p in _baselines(Xtr, ytr, Xv, c).items():
            res.setdefault(b, [dict(params={}, dobras=[], media={})])
            res[b][0]["dobras"].append(dict(treino=treino, validada=val, **metricas(yv, p)))
    for b in ("base_classe_mais_frequente", "base_persistencia"):
        res[b][0]["media"] = _media(res[b][0]["dobras"])
    return res


def _media(por):
    return {k: float(np.mean([d[k] for d in por])) for k in ("macro_f1", "balanced_accuracy",
                                                             "erro_abs_medio_nivel", "acuracia")}


def selecionar(cv) -> dict:
    """Regra: maior macro-F1 médio na CV; empate → menor erro absoluto médio de nível."""
    melhores = {}
    for nome in GRADES:
        melhores[nome] = max(cv[nome], key=lambda r: (r["media"]["macro_f1"], -r["media"]["erro_abs_medio_nivel"]))
    vencedor = max(melhores, key=lambda n: (melhores[n]["media"]["macro_f1"],
                                            -melhores[n]["media"]["erro_abs_medio_nivel"]))
    return dict(regra="maior macro-F1 médio na CV por origem com expurgo; empate: menor erro absoluto médio de nível",
                dobras=[dict(treino=t, validada=v) for t, v in DOBRAS],
                vencedor=vencedor, melhores_por_candidato=melhores,
                baselines_cv={b: cv[b][0] for b in ("base_classe_mais_frequente", "base_persistencia")},
                todas_combinacoes={n: cv[n] for n in GRADES})


def melhor(cv_nome):
    return max(cv_nome, key=lambda r: (r["media"]["macro_f1"], -r["media"]["erro_abs_medio_nivel"]))


def avaliar_final(u, selecao, extra_cv=None) -> tuple:
    """Treina o melhor de cada candidato em T1–T4 (cortes do treino) e avalia treino × Teste lado a lado."""
    cortes = rotulo.cortes_treino(u)
    Xtr, ytr, sem_tr = conjunto(u, C.ORIGENS_TREINO, cortes)
    Xte, yte, sem_te = conjunto(u, ["Teste"], cortes)
    linhas, previsoes, matrizes, modelos = [], {}, {}, {}
    escolhidos = {n: selecao["melhores_por_candidato"][n]["params"] for n in GRADES}
    escolhidos.update({n: melhor(r)["params"] for n, r in (extra_cv or {}).items() if n in GRADES_EXTRA})
    for nome, params in escolhidos.items():
        m = ajustar(nome, params, Xtr, ytr.values, u)
        modelos[nome] = m
        ptr, pte = prever(nome, m, Xtr), prever(nome, m, Xte)
        previsoes[nome] = pte
        matrizes[nome] = confusion_matrix(yte, pte, labels=NIVEIS).tolist()
        linhas.append(_linha(nome, params, ytr, ptr, yte, pte, nome not in GRADES))
    for b, pte in _baselines(Xtr, ytr, Xte, cortes).items():
        ptr = _baselines(Xtr, ytr, Xtr, cortes)[b]
        previsoes[b] = pte
        matrizes[b] = confusion_matrix(yte, pte, labels=NIVEIS).tolist()
        linhas.append(_linha(b, {}, ytr, ptr, yte, pte, False))
    tabela = pd.DataFrame(linhas)
    extra = dict(cortes=cortes, n_treino=int(len(Xtr)), n_teste=int(len(Xte)),
                 sem_rotulo_treino=sem_tr, sem_rotulo_teste=sem_te["Teste"],
                 distribuicao_treino={int(k): int(v) for k, v in ytr.value_counts().sort_index().items()},
                 distribuicao_teste={int(k): int(v) for k, v in yte.value_counts().sort_index().items()},
                 chaves_teste_1_registro=int((Xte.taxa_registros * len(C.ORIGENS["Teste"]["features"]) == 1).sum()),
                 matrizes_confusao_teste=matrizes)
    return tabela, extra, (Xtr, ytr, Xte, yte), previsoes, modelos


def _linha(nome, params, ytr, ptr, yte, pte, exploracao):
    a, b = metricas(ytr, ptr), metricas(yte, pte)
    d = dict(modelo=nome, exploracao_adicional=exploracao, params=json.dumps(params, default=str))
    for k in a:
        d[f"{k}_treino"], d[f"{k}_teste"] = a[k], b[k]
    d["gap_macro_f1"] = a["macro_f1"] - b["macro_f1"]
    return d


def main():
    u = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    C.RESULTADOS.mkdir(parents=True, exist_ok=True)
    resumo = features.gravar(u, rotulo.cortes_treino(u))
    selecao = selecionar(validacao_cruzada(u))
    selecao["exemplos_por_origem"] = resumo
    alvo = C.RESULTADOS / "selecao_modelo.json"
    if alvo.exists():  # pré-registro de 15/11: nunca reescrever depois de ago–set ter sido visto
        registrada = json.loads(alvo.read_text())
        assert registrada["vencedor"] == selecao["vencedor"], "CV mudou: investigar antes de seguir"
    else:
        alvo.write_text(json.dumps(selecao, ensure_ascii=False, indent=2, default=str) + "\n")
    extra_cv = validacao_cruzada(u, list(GRADES_EXTRA))
    (C.RESULTADOS / "cv_exploracao_adicional.json").write_text(
        json.dumps(extra_cv, ensure_ascii=False, indent=2, default=str) + "\n")
    tabela, extra, _, _, _ = avaliar_final(u, selecao, extra_cv)
    tabela.to_csv(C.RESULTADOS / "metricas_treino_teste.csv", index=False, float_format="%.4f")
    (C.RESULTADOS / "avaliacao_final.json").write_text(json.dumps(extra, ensure_ascii=False, indent=2) + "\n")
    return selecao, tabela, extra


if __name__ == "__main__":
    s, t, e = main()
    print("vencedor (CV):", s["vencedor"])
    print(t[["modelo", "macro_f1_treino", "macro_f1_teste", "balanced_accuracy_teste",
             "erro_abs_medio_nivel_teste", "gap_macro_f1"]].to_string(index=False))
    print({k: v for k, v in e.items() if k != "matrizes_confusao_teste"})
