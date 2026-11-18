"""EXPLORATÓRIO (fora do repo ML): janela do alvo bimestral × trimestral × semestral com RF regularizado e XGBoost.
Reaproveita ml.v2_historico (mesmas variáveis, origens a cada 3 meses no trimestral, expurgo, cortes só do treino).
XGBoost: grade de ml.modelos.GRADES escolhida pelo macro-F1 na origem de validação (última do treino), sem tocar no Teste.
Teste: últimos W meses até set/2026 (já visto na v1: test_seen). Comparação: modelo − persistência da história (média histórica)."""
import json, numpy as np, pandas as pd
from ml import config as C, rotulo
from ml import modelos as M
from ml import v2_historico as V
from ml.diagnostico_rf import _rf
from ml.incerteza_custo import REGULARIZADO, bootstrap, diferencas, metricas, resumo_ic
from xgboost import XGBClassifier
from sklearn.utils.class_weight import compute_sample_weight

class XGB:
    def __init__(self, **p): self.p = p
    def fit(self, X, y):
        y = np.asarray(y); self.m = M.novo_modelo("xgboost", self.p)
        self.m.fit(X, y, sample_weight=compute_sample_weight("balanced", y)); return self
    def predict(self, X): return self.m.predict(X)

u = pd.read_parquet(V.USADAS_V2)
DES = {"bimestral": dict(largura=2, passo=1, primeiro=13, n_recente=7, teste=[44, 45]),
       "trimestral": dict(largura=3, passo=3, primeiro=13, n_recente=3, teste=[43, 44, 45]),
       "semestral": dict(largura=6, passo=3, primeiro=13, n_recente=6, teste=list(range(40, 46)))}
res = {}
for nome, cfg in DES.items():
    L, teste = cfg["largura"], cfg["teste"]
    treino = V.origens(cfg["primeiro"], teste[0] - L, L, cfg["passo"])
    val = treino[-1]; treino_sel = [j for j in treino if j[-1] < val[0]]
    cortes_sel = V.cortes_quartis(u, treino_sel); cortes = V.cortes_quartis(u, treino)
    rf = lambda: _rf(REGULARIZADO)
    # seleção do XGBoost só na validação
    Xs, ys = V.montar(u, treino_sel, cortes_sel, cfg["n_recente"]); Xv, yv, _ = V.exemplos_v2(u, val, cortes_sel, cfg["n_recente"])
    sel = {}
    for p in M.combinacoes("xgboost"):
        pr = XGB(**p).fit(Xs.values, ys.values).predict(Xv.values)
        sel[json.dumps(p)] = metricas(yv.values, pr)["macro_f1"]
    melhor = json.loads(max(sel, key=sel.get))
    cands = {"rf_regularizado": rf, "xgboost": lambda: XGB(**melhor)}
    Xtr, ytr = V.montar(u, treino, cortes, cfg["n_recente"])
    Xte, yte, _ = V.exemplos_v2(u, teste, cortes, cfg["n_recente"])
    prev, _ = V.ajustar_prever(cands, Xtr, ytr, [Xte])
    p = {k: v[0] for k, v in prev.items()}; p.update(V.persistencias(Xte, cortes))
    y = yte.values; cel = np.asarray(Xte.index.get_level_values("celula"))
    pont = {k: metricas(y, v) for k, v in p.items()}
    boot = bootstrap(y, p, cel)
    pares = [("rf_regularizado", "base_persistencia_historia"), ("xgboost", "base_persistencia_historia"),
             ("rf_regularizado", "base_persistencia_recente"), ("xgboost", "base_persistencia_recente"), ("xgboost", "rf_regularizado")]
    res[nome] = dict(n_treino=int(len(Xtr)), n_teste=int(len(y)), n_origens_treino=len(treino), xgb_escolhido=melhor,
                     xgb_val_macroF1=round(max(sel.values()), 3), cortes=[round(c, 3) for c in cortes],
                     teste=resumo_ic(boot, pont), diferencas=diferencas(boot, pares, n_familia=len(pares)))
    print(nome, json.dumps(res[nome], ensure_ascii=False, default=float), flush=True)
