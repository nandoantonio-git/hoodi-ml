"""EXPLORATÓRIO (fora do repo ML): o foco é CLASSIFICAR o nível observado da zona (mais/menos segura), não prever o futuro.
Tarefa de recuperação: dentro de uma janela R de 12 meses, os meses alternados formam duas metades A e B. O estimador vê A
(+ todo o contexto até o fim de R, exceto B); o alvo é o nível de B. Roda nas duas direções (A→B e B→A).
R1 = meses 10–21 (ajuste de λ/a e treino), R2 = 22–33, R3 = 34–45 (reportadas). Rótulo = chave com registro pontuável em B.
Estimadores: contexto, só A, empírico-Bayes com prior hierárquico (res-8 → res-7), suavização espacial, XGBoost/RF.
Níveis por quantis dos escores sobre as chaves rotuladas (sem usar rótulo); o alvo usa quartis de B."""
from pathlib import Path
AQUI = Path(__file__).resolve().parent
SAIDA = AQUI.parent / "dados" / "resultados" / "classificacao_exploratorio"
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import torch  # noqa: F401
import json, numpy as np, pandas as pd, h3
from scipy.stats import spearmanr, rankdata
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBRegressor, XGBClassifier
from ml.ta_descritiva import Base, media_vizinhas, USADAS_V2

rng = np.random.default_rng(7)
u = pd.read_parquet(USADAS_V2); b = Base(u); K = len(b.chaves); H = b.horas
cod8 = pd.factorize(np.array([f"{h3.cell_to_parent(c, 8)}|{f}" for c, f in zip(b.cel, b.faixa)]))[0]
cod7 = pd.factorize(np.array([f"{h3.cell_to_parent(c, 7)}|{f}" for c, f in zip(b.cel, b.faixa)]))[0]
codc = pd.factorize(b.cel)[0]

def loo_mean(x, cod):
    s = np.bincount(cod, weights=x); n = np.bincount(cod).astype(float)
    return s[cod], n[cod]
def prior_hier(x, w=3.0):
    s7, n7 = loo_mean(x, cod7); p7 = (s7 - x) / np.maximum(n7 - 1, 1)
    s8, n8 = loo_mean(x, cod8); p8 = np.where(n8 > 1, (s8 - x) / np.maximum(n8 - 1, 1), p7)
    k = np.maximum(n8 - 1, 0)
    return (k * p8 + w * p7) / (k + w), p8, p7

def conjunto(ini, fim, d):
    mons = list(range(ini, fim + 1)); A = mons[d::2]; Bm = mons[1 - d::2]
    ctx = [m for m in range(1, fim + 1) if m not in Bm]
    ctx_mean = b.S[:, ctx].sum(1) / len(ctx) / H
    rawA = b.S[:, A].sum(1) / len(A) / H
    ult12 = [m for m in range(max(1, fim - 11), fim + 1) if m not in Bm]
    ult = b.S[:, ult12].sum(1) / len(ult12) / H
    alvo = b.S[:, Bm].sum(1) / len(Bm) / H
    lab = b.N[:, Bm].sum(1) > 0
    prior, p8, p7 = prior_hier(ctx_mean)
    nrec = b.N[:, ctx].sum(1); nmes = (b.N[:, ctx] > 0).sum(1)
    viz = media_vizinhas(b.viz, b.n_viz, ctx_mean, np.ones(K, bool))
    celtot = np.bincount(codc, weights=ctx_mean)[codc]
    return dict(ctx=ctx, nctx=len(ctx), ctx_mean=ctx_mean, rawA=rawA, ult=ult, alvo=alvo, lab=lab, prior=prior, p8=p8, p7=p7,
                nrec=nrec, nmes=nmes, viz=viz, celtot=celtot)

def eb(s, a, lam):
    e = (s["ctx_mean"] * s["nctx"] + a * s["prior"]) / (s["nctx"] + a)
    if lam:
        v = media_vizinhas(b.viz, b.n_viz, e, np.ones(K, bool)); e = (1 - lam) * e + lam * v
    return e
def X_de(s):
    return np.column_stack([s["ctx_mean"], s["rawA"], s["ult"], s["viz"], s["p8"], s["p7"], s["nrec"], s["nmes"], b.faixa, s["celtot"], eb(s, A_EB, L_EB)])
def niveis(est, lab):
    c = np.quantile(est[lab], [.25, .5, .75]); return np.searchsorted(c, est, side="right")
def alvo_nivel(s):
    c = np.quantile(s["alvo"][s["lab"]], [.25, .5, .75]); return np.searchsorted(c, s["alvo"], side="right"), c
def macro(y, p): return f1_score(y, p, average="macro")

# ---- ajuste de a e λ em R1 (Spearman médio, ambas as direções)
S1 = [conjunto(10, 21, d) for d in (0, 1)]
grade = {}
for a in (0, 2, 4, 8, 16, 32, 64):
    for lam in (0, .25, .5):
        r = []
        for s in S1:
            m = s["lab"]; r.append(spearmanr(eb(s, a, lam)[m], s["alvo"][m])[0])
        grade[(a, lam)] = float(np.mean(r))
A_EB, L_EB = max(grade, key=grade.get)
print("AJUSTE R1 (a, λ) -> Spearman:", {f"{k}": round(v, 3) for k, v in sorted(grade.items(), key=lambda kv: -kv[1])[:6]}, "| escolhido", A_EB, L_EB, flush=True)

def treino_modelos(reps):
    Xs, ys, cs = [], [], []
    for (ini, fim) in reps:
        for d in (0, 1):
            s = conjunto(ini, fim, d); m = s["lab"]
            Xs.append(X_de(s)[m]); ys.append(s["alvo"][m])
    X = np.vstack(Xs); y = np.concatenate(ys)
    cuts = np.quantile(y, [.25, .5, .75]); yl = np.searchsorted(cuts, y, side="right")
    reg = XGBRegressor(n_estimators=300, max_depth=3, learning_rate=.05, subsample=.8, colsample_bytree=.8, random_state=7, n_jobs=4, verbosity=0).fit(X, np.sqrt(y))
    clf = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=.05, subsample=.8, colsample_bytree=.8, objective="multi:softprob", num_class=4, random_state=7, n_jobs=4, verbosity=0).fit(X, yl, sample_weight=compute_sample_weight("balanced", yl))
    rf = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=40, max_features=.5, class_weight="balanced", random_state=7, n_jobs=4).fit(X, yl)
    return reg, clf, rf

def avaliar(rep, treino):
    reg, clf, rf = treino_modelos(treino)
    linhas = {}; pool = {}
    for d in (0, 1):
        s = conjunto(*rep, d); lab = s["lab"]; X = X_de(s)
        yl, _ = alvo_nivel(s)
        pc = clf.predict_proba(X); pr = rf.predict_proba(X)
        est = {"so_A (bruto)": s["rawA"], "contexto (média histórica)": s["ctx_mean"], "suavizada λ=.25": 0.75 * s["ctx_mean"] + 0.25 * media_vizinhas(b.viz, b.n_viz, s["ctx_mean"], np.ones(K, bool)),
               f"empírico-Bayes a={A_EB}": eb(s, A_EB, 0), f"EB+espacial a={A_EB} λ={L_EB}": eb(s, A_EB, L_EB),
               "XGBoost regressor": reg.predict(X), "XGBoost classificador (E[nível])": pc @ np.arange(4), "RF classificador (E[nível])": pr @ np.arange(4)}
        conf = {"XGBoost classificador (E[nível])": pc.max(1), "RF classificador (E[nível])": pr.max(1)}
        for nome, e in est.items():
            lv = niveis(e, lab)
            p = pool.setdefault(nome, dict(y=[], p=[], e=[], a=[], cel=[], nrec=[], conf=[], mb=[]))
            m = lab
            rk = rankdata(e[m]) / m.sum()
            pb = (pc if nome.startswith("XGBoost c") else pr)[m][:, 2:].sum(1) if nome in conf else None
            p["mb"].append(np.abs(pb - .5) if pb is not None else np.abs(rk - .5))
            p["y"].append(yl[m]); p["p"].append(lv[m]); p["e"].append(e[m]); p["a"].append(s["alvo"][m]); p["cel"].append(codc[m]); p["nrec"].append(s["nrec"][m]); p["conf"].append(conf.get(nome, s["nrec"])[m].astype(float))
    out = {}
    for nome, p in pool.items():
        y = np.concatenate(p["y"]); pr_ = np.concatenate(p["p"]); e = np.concatenate(p["e"]); a = np.concatenate(p["a"])
        out[nome] = dict(macroF1=macro(y, pr_), exato=float((y == pr_).mean()), ate1=float((abs(y - pr_) <= 1).mean()),
                         spearman=float(spearmanr(e, a)[0]), auc_metade_alta=float(roc_auc_score(y >= 2, e)),
                         acc_binaria=float(((y >= 2) == (pr_ >= 2)).mean()))
    # IC pareado por célula contra o contexto
    base = pool["contexto (média histórica)"]; cel = np.concatenate(base["cel"]); ucel = np.unique(cel)
    idx = {c: np.where(cel == c)[0] for c in ucel}
    ys = {n: np.concatenate(p["y"]) for n, p in pool.items()}; ps = {n: np.concatenate(p["p"]) for n, p in pool.items()}
    es = {n: np.concatenate(p["e"]) for n, p in pool.items()}; as_ = np.concatenate(base["a"])
    dif = {n: [] for n in pool}; difs = {n: [] for n in pool}
    for _ in range(300):
        ii = np.concatenate([idx[c] for c in rng.choice(ucel, len(ucel))])
        bf = macro(ys["contexto (média histórica)"][ii], ps["contexto (média histórica)"][ii]); bs = spearmanr(es["contexto (média histórica)"][ii], as_[ii])[0]
        for n in pool:
            dif[n].append(macro(ys[n][ii], ps[n][ii]) - bf); difs[n].append(spearmanr(es[n][ii], as_[ii])[0] - bs)
    for n in pool:
        out[n]["dMacroF1_vs_contexto"] = [round(float(np.mean(dif[n])), 3), *[round(float(x), 3) for x in np.percentile(dif[n], [2.5, 97.5])]]
        out[n]["dSpearman_vs_contexto"] = [round(float(np.mean(difs[n])), 3), *[round(float(x), 3) for x in np.percentile(difs[n], [2.5, 97.5])]]
    # classificação seletiva (abstenção): mantém os x% com mais evidência (nº de registros no contexto) ou maior confiança do modelo
    sel = {}
    for n in ("contexto (média histórica)", f"EB+espacial a={A_EB} λ={L_EB}", "XGBoost classificador (E[nível])", "RF classificador (E[nível])"):
        p = pool[n]; y = ys[n]; pr_ = ps[n]; c = np.concatenate(p["conf"]); r = {}
        for cov in (1.0, .75, .5, .25):
            keep = c >= np.quantile(c, 1 - cov) if cov < 1 else np.ones(len(c), bool)
            r[f"cob{int(cov*100)}"] = dict(n=int(keep.sum()), macroF1=round(macro(y[keep], pr_[keep]), 3), ate1=round(float((abs(y[keep] - pr_[keep]) <= 1).mean()), 3),
                                          acc_binaria=round(float(((y[keep] >= 2) == (pr_[keep] >= 2)).mean()), 3))
        mb = np.concatenate(p["mb"]); rb = {}
        for cov in (1.0, .75, .5, .25):
            keep = mb >= np.quantile(mb, 1 - cov) if cov < 1 else np.ones(len(mb), bool)
            rb[f"cob{int(cov*100)}"] = dict(n=int(keep.sum()), acc_binaria=round(float(((y[keep] >= 2) == (pr_[keep] >= 2)).mean()), 3))
        r["binaria_por_margem"] = rb
        sel[n] = r
    return out, sel, int(len(y)), int(len(ucel))

resultado = {}
for nome, rep, tr in (("R2 (22–33)", (22, 33), [(10, 21)]), ("R3 (34–45)", (34, 45), [(10, 21), (22, 33)])):
    out, sel, n, nc = avaliar(rep, tr)
    resultado[nome] = dict(n=n, n_celulas=nc, metricas=out, seletiva=sel)
    print(f"\n=== {nome} n={n} células={nc} ===", flush=True)
    for k, v in out.items():
        print(f"{k:38s} F1 {v['macroF1']:.3f} exato {v['exato']:.3f} ≤1 {v['ate1']:.3f} rho {v['spearman']:.3f} AUC(alta) {v['auc_metade_alta']:.3f} bin {v['acc_binaria']:.3f} | ΔF1 {v['dMacroF1_vs_contexto']} Δrho {v['dSpearman_vs_contexto']}", flush=True)
    print("-- classificação seletiva (macroF1 / ≤1 / acerto binário) --")
    for k, v in sel.items():
        print(f"{k:38s}", {c: (x['macroF1'], x['ate1'], x['acc_binaria']) for c, x in v.items() if c != 'binaria_por_margem'}, "| bin por margem", {c: x['acc_binaria'] for c, x in v['binaria_por_margem'].items()}, flush=True)
json.dump(resultado, open(SAIDA / "classificacao_zonas.json", "w"), ensure_ascii=False, default=float, indent=1)

# ---- E4: tipologia de zonas (KMeans+PCA no perfil de crime × faixa) é estável entre as metades A e B?
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from ml import features, rotulo
x = rotulo.com_peso(u[u.mes.between(34, 45)]); x = x[x.peso.notna()].copy(); x["g"] = x.rubrica.map(features._grupo).fillna("outro")
def perfil(meses):
    t = x[x.mes.isin(meses)]
    g = t.groupby(["celula", "g"]).size().unstack(fill_value=0).reindex(columns=["furto", "roubo", "lesao", "graves", "drogas", "outro"], fill_value=0)
    f = t.groupby(["celula", "faixa"]).size().unstack(fill_value=0).reindex(columns=range(5), fill_value=0)
    return g, f
mons = list(range(34, 46)); gA, fA = perfil(mons[0::2]); gB, fB = perfil(mons[1::2])
cels = [c for c in gA.index.intersection(gB.index) if gA.loc[c].sum() >= 15 and gB.loc[c].sum() >= 15]
def vetor(g, f):
    P = np.hstack([g.loc[cels].div(g.loc[cels].sum(1), axis=0).values, f.loc[cels].div(f.loc[cels].sum(1), axis=0).values]); return P
PA, PB = vetor(gA, fA), vetor(gB, fB)
ref = np.vstack([PA, PB]); pca = PCA(n_components=4, random_state=7).fit(ref)
res4 = {}
for k in (3, 4, 5):
    km = KMeans(n_clusters=k, n_init=20, random_state=7).fit(pca.transform(ref))
    la, lb = km.predict(pca.transform(PA)), km.predict(pca.transform(PB))
    perm = np.mean([adjusted_rand_score(la, rng.permutation(lb)) for _ in range(200)])
    res4[k] = dict(n_celulas=len(cels), ARI_A_vs_B=round(float(adjusted_rand_score(la, lb)), 3), mesmo_cluster=round(float((la == lb).mean()), 3), ARI_embaralhado=round(float(perm), 3))
print("\nE4 tipologia (cluster do perfil, metades A×B, células com ≥15 registros em cada):", json.dumps(res4), flush=True)
