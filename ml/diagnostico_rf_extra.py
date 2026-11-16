import os, json
os.environ.setdefault("OMP_NUM_THREADS","1")
import numpy as np, pandas as pd
from ml import config as C, modelos as M, features as F
from ml.diagnostico_rf import _rf, _f1, BASE, avaliar_cv, dobras
u = pd.read_parquet(C.PROCESSED/"usadas.parquet")
ds = dobras(u)
REG = json.loads((C.RESULTADOS/"rf_reavaliacao.json").read_text())["escolhida_por_cv"]["params"]
out = {}
out["min_samples_split"] = {v: avaliar_cv(ds, {**BASE, "min_samples_split": v}) for v in [2,10,20,50,100,200]}
out["n_estimators"] = {f"{n}|{nome}": avaliar_cv(ds, {**p, "n_estimators": n}) for nome,p in (("orig",BASE),("reg",REG)) for n in [50,100,300,600]}
# curva de aprendizado: dobra 2 (T1–T2 -> T4), fração das células de treino
treino, val = M.DOBRAS[1]; c = M.cortes_de(u, treino)
Xtr, ytr, _ = M.conjunto(u, treino, c); Xv, yv, _ = M.conjunto(u, [val], c)
cels = Xtr.index.get_level_values("celula").unique().values; rng = np.random.default_rng(42)
lc = {}
for frac in [0.2,0.4,0.6,0.8,1.0]:
    r = {"orig":[], "reg":[]}
    for s in range(5):
        esc = set(rng.choice(cels, int(len(cels)*frac), replace=False))
        msk = Xtr.index.get_level_values("celula").isin(esc)
        for nome,p in (("orig",BASE),("reg",REG)):
            m = _rf(p).fit(M._matriz(Xtr[msk]), ytr.values[msk])
            r[nome].append((_f1(ytr.values[msk], m.predict(M._matriz(Xtr[msk]))), _f1(yv.values, m.predict(M._matriz(Xv)))))
    lc[frac] = {k: dict(treino=float(np.mean([a for a,_ in v])), validacao=float(np.mean([b for _,b in v]))) for k,v in r.items()}
out["curva_aprendizado_dobra2"] = lc
# mesma célula: validação separada por células vistas x não vistas no treino da dobra
vistas = set(Xtr.index.get_level_values("celula"))
mv = Xv.index.get_level_values("celula").isin(vistas)
grp = {}
for nome,p in (("orig",BASE),("reg",REG)):
    m = _rf(p).fit(M._matriz(Xtr), ytr.values); pv = m.predict(M._matriz(Xv))
    grp[nome] = dict(vistas=_f1(yv.values[mv], pv[mv]), nao_vistas=_f1(yv.values[~mv], pv[~mv]))
grp["persistencia"] = (lambda pv: dict(vistas=_f1(yv.values[mv], pv[mv]), nao_vistas=_f1(yv.values[~mv], pv[~mv])))(F.persistencia(Xv, c))
grp["n_vistas"], grp["n_nao_vistas"] = int(mv.sum()), int((~mv).sum())
out["celulas_vistas_dobra2"] = grp
# validação agrupada por célula (GroupKFold no treino completo T1–T4): mede generalização a células novas
from sklearn.model_selection import GroupKFold
from ml import rotulo
ct = rotulo.cortes_treino(u); Xa, ya, _ = M.conjunto(u, C.ORIGENS_TREINO, ct)
g = Xa.index.get_level_values("celula")
gk = {}
for nome,p in (("orig",BASE),("reg",REG)):
    sc=[]
    for tr,va in GroupKFold(5).split(Xa, ya, g):
        m=_rf(p).fit(M._matriz(Xa.iloc[tr]), ya.values[tr]); sc.append(_f1(ya.values[va], m.predict(M._matriz(Xa.iloc[va]))))
    gk[nome]=float(np.mean(sc))
out["groupkfold_celula_sem_ordem_temporal"]=gk
# vazamento: identificadores fora de X?
out["colunas_X"] = F.COLUNAS_X
(C.RESULTADOS/"rf_checagens_extra.json").write_text(json.dumps(out, indent=2, default=str)+"\n")
print(json.dumps(out, indent=1, default=lambda x: round(x,4) if isinstance(x,float) else str(x)))
