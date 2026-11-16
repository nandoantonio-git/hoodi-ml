"""Reavaliação do Random Forest (overfitting), feita depois de ago–set ter sido visto: exploração adicional.

Nada aqui altera `selecao_modelo.json`. As curvas e a escolha regularizada usam SÓ as dobras de CV com
expurgo (T1→T3, T1–T2→T4); o Teste é consultado uma única vez, no fim, para a configuração já fixada.
Referências: documentação do RandomForestClassifier (scikit-learn) e Probst, Wright & Boulesteix (2019).
"""
import itertools
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score

from ml import config as C
from ml import modelos as M
from ml import rotulo

BASE = dict(n_estimators=300, max_depth=None, min_samples_leaf=5)  # vencedor pré-registrado
CURVAS = {
    "max_depth": [2, 3, 4, 5, 6, 8, 10, 15, None],
    "min_samples_leaf": [1, 5, 10, 20, 40, 80, 160],
    "max_features": [1, 2, 4, "sqrt", 8, 0.75, 1.0],
    "max_samples": [0.1, 0.2, 0.35, 0.5, 0.75, None],
    "ccp_alpha": [0.0, 1e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2],
}
GRADE_REG = dict(max_depth=[4, 6, 8, None], min_samples_leaf=[5, 20, 40, 80],
                 max_features=["sqrt", 0.5], max_samples=[0.5, None])
LIMITE_GAP = 0.10  # critério da exploração adicional (não está na SPEC-ML): diferença treino × validação de no máximo 0,10


def _rf(p):
    return RandomForestClassifier(**{**dict(n_estimators=300), **p}, class_weight="balanced",
                                  random_state=C.SEMENTE, n_jobs=-1)


def _f1(y, p):
    return float(f1_score(y, p, average="macro", labels=M.NIVEIS, zero_division=0))


def dobras(u):
    out = []
    for treino, val in M.DOBRAS:
        c = M.cortes_de(u, treino)
        Xtr, ytr, _ = M.conjunto(u, treino, c)
        Xv, yv, _ = M.conjunto(u, [val], c)
        out.append((M._matriz(Xtr), ytr.values, M._matriz(Xv), yv.values))
    return out


def avaliar_cv(ds, p):
    tr, va = [], []
    for Xtr, ytr, Xv, yv in ds:
        m = _rf(p).fit(Xtr, ytr)
        tr.append(_f1(ytr, m.predict(Xtr)))
        va.append(_f1(yv, m.predict(Xv)))
    return dict(f1_treino=float(np.mean(tr)), f1_validacao=float(np.mean(va)),
                gap=float(np.mean(tr) - np.mean(va)))


def main():
    u = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    ds = dobras(u)
    curvas = []
    for par, valores in CURVAS.items():
        for v in valores:
            p = {**BASE, par: v}
            curvas.append(dict(parametro=par, valor=str(v), **avaliar_cv(ds, p)))
    curvas = pd.DataFrame(curvas)

    grade = []
    for vals in itertools.product(*GRADE_REG.values()):
        p = {"n_estimators": 300, **dict(zip(GRADE_REG, vals))}
        grade.append(dict(params=p, **avaliar_cv(ds, p)))
    ok = [g for g in grade if g["gap"] <= LIMITE_GAP]
    escolhida = max(ok or grade, key=lambda g: (g["f1_validacao"], -g["gap"]))

    # OOB no treino completo: otimista, porque a mesma chave aparece em várias origens com janelas sobrepostas
    cortes = rotulo.cortes_treino(u)
    Xtr, ytr, _ = M.conjunto(u, C.ORIGENS_TREINO, cortes)
    Xte, yte, _ = M.conjunto(u, ["Teste"], cortes)
    final = {}
    for nome, p in (("pre_registrado", BASE), ("regularizado_cv", escolhida["params"])):
        m = _rf({**p}).set_params(oob_score=True).fit(M._matriz(Xtr), ytr.values)
        oob = _f1(ytr.values, m.oob_decision_function_.argmax(1))
        final[nome] = dict(params=p, f1_treino=_f1(ytr.values, m.predict(M._matriz(Xtr))), f1_oob=oob,
                           f1_teste=_f1(yte.values, m.predict(M._matriz(Xte))))
        final[nome]["gap_treino_teste"] = final[nome]["f1_treino"] - final[nome]["f1_teste"]
        final[nome]["importancia"] = dict(sorted(zip(M.features.COLUNAS_X, m.feature_importances_.round(4).tolist()),
                                                 key=lambda kv: -kv[1])[:6])

    C.RESULTADOS.mkdir(parents=True, exist_ok=True)
    curvas.to_csv(C.RESULTADOS / "rf_curvas_validacao.csv", index=False, float_format="%.4f")
    (C.RESULTADOS / "rf_reavaliacao.json").write_text(json.dumps(dict(
        nota="exploração adicional (ago–set já visto); a escolha pré-registrada não muda",
        limite_gap=LIMITE_GAP, n_grade=len(grade), n_dentro_do_limite=len(ok),
        escolhida_por_cv=escolhida, final=final,
        grade=grade), ensure_ascii=False, indent=2, default=str) + "\n")
    return curvas, escolhida, final, len(grade), len(ok)


if __name__ == "__main__":
    curvas, esc, final, n, n_ok = main()
    print(curvas.to_string(index=False))
    print("grade:", n, "dentro do gap:", n_ok)
    print("escolhida por CV:", esc)
    print(json.dumps(final, indent=1, default=str))
