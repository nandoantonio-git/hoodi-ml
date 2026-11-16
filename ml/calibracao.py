"""Calibração das probabilidades do RF regularizado e métricas por estrato (revisão de código, 2026-11-16).

Exploração adicional, test_seen=true: os hiperparâmetros do RF regularizado foram escolhidos depois de
ago–set ter sido visto. Nada aqui altera `selecao_modelo.json` nem o snapshot.

1. Calibração no Teste: Brier multiclasse, log-loss, ECE do nível mais provável (10 faixas iguais) e curva
   de confiabilidade de P(nível 3), que é a probabilidade que importa para o alerta.
2. Correção isotônica um-contra-todos, renormalizada. O calibrador aprende SÓ com probabilidades fora da
   dobra nas dobras temporais de CV (T1→T3, T1+T2→T4); o Teste não entra no ajuste. Cada dobra usa os
   próprios cortes, como na CV de seleção.
4. Backtest agregado em `resultados/backtest_ago_set.csv` (T028): métricas das previsões do RF original
   (vencedor pré-registrado), do RF regularizado e da persistência. Não publica H3, faixa, rótulo ou contagem
   por chave, para impedir inferências por composição com o snapshot do app.
3. Macro-F1 por faixa horária e por quantidade de registros da chave na janela de features, RF regularizado
   × persistência, para ver se o modelo só acerta onde há muito dado.
"""
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
import torch  # noqa: F401 — antes do xgboost (ver modelos.py)

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import f1_score, log_loss

from ml import config as C
from ml import features
from ml import modelos as M
from ml import rotulo
from ml.diagnostico_rf import BASE, _rf, dobras
from ml.incerteza_custo import REGULARIZADO

N_FAIXAS_CONF = 10
EPS = 1e-6


def brier(y, proba) -> float:
    alvo = np.eye(proba.shape[1])[np.asarray(y)]
    return float(((proba - alvo) ** 2).sum(axis=1).mean())


def ece(y, proba, n=N_FAIXAS_CONF) -> float:
    conf, pred = proba.max(axis=1), proba.argmax(axis=1)
    acerto = (pred == np.asarray(y)).astype(float)
    faixa = np.minimum((conf * n).astype(int), n - 1)
    return float(sum(abs(acerto[faixa == b].mean() - conf[faixa == b].mean()) * (faixa == b).mean()
                     for b in range(n) if (faixa == b).any()))


def confiabilidade(evento, p, n=N_FAIXAS_CONF) -> list:
    faixa = np.minimum((p * n).astype(int), n - 1)
    return [dict(faixa=f"[{b / n:.1f},{(b + 1) / n:.1f})", n=int((faixa == b).sum()),
                 p_media=float(p[faixa == b].mean()), frequencia_observada=float(evento[faixa == b].mean()))
            for b in range(n) if (faixa == b).any()]


def _renorm(q):
    return q / q.sum(axis=1, keepdims=True)


def resumo(y, proba) -> dict:
    y = np.asarray(y)
    p3 = proba[:, 3]
    return dict(brier_multiclasse=brier(y, proba),
                log_loss=float(log_loss(y, _renorm(np.clip(proba, EPS, 1)), labels=M.NIVEIS)),
                ece_nivel_mais_provavel=ece(y, proba),
                brier_nivel3=float(((p3 - (y == 3)) ** 2).mean()),
                macro_f1_argmax=float(f1_score(y, proba.argmax(axis=1), average="macro",
                                               labels=M.NIVEIS, zero_division=0)))


class Isotonica:
    """Isotônica um-contra-todos por nível, seguida de renormalização."""

    def fit(self, proba, y):
        y = np.asarray(y)
        self.f = [IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(proba[:, k], y == k)
                  for k in range(proba.shape[1])]
        return self

    def transform(self, proba):
        q = np.column_stack([f.predict(proba[:, k]) for k, f in enumerate(self.f)]) + EPS
        return q / q.sum(axis=1, keepdims=True)


def fora_da_dobra(u):
    ps, ys = [], []
    for Xtr, ytr, Xv, yv in dobras(u):
        ps.append(_rf(REGULARIZADO).fit(Xtr, ytr).predict_proba(Xv))
        ys.append(yv)
    return np.vstack(ps), np.concatenate(ys)


def _f1(y, p):
    return float(f1_score(y, p, average="macro", labels=M.NIVEIS, zero_division=0)) if len(y) else None


def por_estrato(Xte, y, pred_rf, pred_pers) -> dict:
    n_meses = len(C.ORIGENS["Teste"]["features"])
    n_reg = np.rint(Xte.taxa_registros.values * n_meses).astype(int)
    grupo = np.where(n_reg == 1, "1", np.where(n_reg <= 4, "2-4", "5+"))
    faixa = Xte.index.get_level_values("faixa").astype(int).values
    out = {"por_faixa": [], "por_registros_na_janela_de_features": []}
    for f in sorted(set(faixa)):
        m = faixa == f
        out["por_faixa"].append(dict(faixa=int(f), faixa_nome=C.FAIXA_NOME[int(f)], n=int(m.sum()),
                                     f1_rf_regularizado=_f1(y[m], pred_rf[m]),
                                     f1_persistencia=_f1(y[m], pred_pers[m])))
    for g in ("1", "2-4", "5+"):
        m = grupo == g
        out["por_registros_na_janela_de_features"].append(
            dict(registros=g, n=int(m.sum()), f1_rf_regularizado=_f1(y[m], pred_rf[m]),
                 f1_persistencia=_f1(y[m], pred_pers[m]),
                 acerto_exato_rf=float((y[m] == pred_rf[m]).mean())))
    return out


def backtest_agregado(y, previsoes: dict) -> pd.DataFrame:
    """Uma linha por modelo, sem identificador espacial/temporal nem observação individual."""
    y = np.asarray(y)
    linhas = []
    for modelo, pred in previsoes.items():
        pred = np.asarray(pred)
        linhas.append(dict(modelo=modelo, n=len(y), macro_f1=_f1(y, pred),
                           acerto_exato=float((y == pred).mean()),
                           erro_le_1_nivel=float((np.abs(y - pred) <= 1).mean())))
    return pd.DataFrame(linhas)


def main():
    u = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    cortes = rotulo.cortes_treino(u)
    Xtr, ytr, _ = M.conjunto(u, C.ORIGENS_TREINO, cortes)
    Xte, yte, _ = M.conjunto(u, ["Teste"], cortes)
    y = yte.values

    rf = _rf(REGULARIZADO).fit(M._matriz(Xtr), ytr.values)
    proba = rf.predict_proba(M._matriz(Xte))
    p_oof, y_oof = fora_da_dobra(u)
    iso = Isotonica().fit(p_oof, y_oof)
    proba_cal = iso.transform(proba)

    pred_rf = proba.argmax(axis=1)
    pred_pers = features.persistencia(Xte, cortes)
    res = dict(
        nota=("Exploração adicional, test_seen=true. Calibrador ajustado só com probabilidades fora da dobra "
              "nas dobras temporais de CV; o Teste não entra no ajuste."),
        modelo="rf_regularizado", params=REGULARIZADO, n_teste=int(len(y)), n_calibracao=int(len(y_oof)),
        frequencia_nivel3_teste=float((y == 3).mean()),
        sem_calibracao=resumo(y, proba), isotonica_cv=resumo(y, proba_cal),
        confiabilidade_p_nivel3=dict(sem_calibracao=confiabilidade(y == 3, proba[:, 3]),
                                     isotonica_cv=confiabilidade(y == 3, proba_cal[:, 3])),
        estratos=por_estrato(Xte, y, pred_rf, pred_pers),
    )
    C.RESULTADOS.mkdir(parents=True, exist_ok=True)
    rf_or = _rf(BASE).fit(M._matriz(Xtr), ytr.values)
    bt = backtest_agregado(y, {
        "persistencia": pred_pers,
        "rf_original": rf_or.predict(M._matriz(Xte)),
        "rf_regularizado": pred_rf,
    })
    bt.to_csv(C.RESULTADOS / "backtest_ago_set.csv", index=False)
    (C.RESULTADOS / "calibracao.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ("sem_calibracao", "isotonica_cv", "estratos")}, ensure_ascii=False, indent=1))
