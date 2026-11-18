"""EXPLORATÓRIO (fora do repo ML): onde o ML pode agregar à rota? (A) memória/regime, (B) incerteza/abstenção, (C) KMeans+PCA.
Hiperparâmetros escolhidos nas 5 primeiras origens, avaliados nas 5 últimas."""
import json, numpy as np
src = open(__import__('pathlib').Path(__file__).with_name('ordem_rotas.py')).read().split("linhas = []")[0]
exec(src)
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# rotas como (idx, km) por faixa
R = []
for rt in pares:
    d = {}
    for n, tr in rt.items():
        per = []
        for f in range(5):
            ii = [(pos.get((c, f)), m/1000) for c, m in tr]
            per.append((np.array([i for i, _ in ii if i is not None], int), np.array([k for i, k in ii if i is not None]), sum(k for _, k in ii)))
        d[n] = per
    R.append(d)

def sc(vec, f):
    out = []
    for d in R:
        out.append(np.array([vec[d[n][f][0]] @ d[n][f][1] for n in d]))
    return out
def kms(f): return [np.array([d[n][f][2] for n in d]) for d in R]
KM = [kms(f) for f in range(5)]

def avalia(vecs_by_ini, orig):
    c = x = 0; exp = base = 0.0; kmx = kmb = 0.0
    for ini in orig:
        vec, alvo = vecs_by_ini[ini]
        for f in range(5):
            S, A = sc(vec, f), sc(alvo, f)
            for s, a, k in zip(S, A, KM[f]):
                if a.max()-a.min() <= 1e-9 or s.max()-s.min() <= 1e-9: continue
                cc, dd = kendall_pairs(s, a); c += cc; x += dd
                i = int(np.argmin(s)); j = int(np.argmin(k))
                exp += a[i]; base += a[j]; kmx += k[i]; kmb += k[j]
    return dict(conc=round(c/(c+x), 4), reducao=round(1-exp/base, 4), km_extra=round(kmx/kmb-1, 4))

orig = REPORTADAS; tr_o, te_o = orig[:5], orig[5:]
alvos = {i: b.pont(range(i, i+LARGURA)) for i in orig}
def pw(ini, h):
    m = np.arange(1, ini); w = np.ones(len(m)) if h is None else 0.5 ** ((ini-1-m)/h)
    return (b.S[:, m] * w).sum(axis=1) / w.sum() / b.horas
def montar(fn): return {i: (fn(i), alvos[i]) for i in orig}

res = {}
# ---------- A) memória: média histórica vs decaimento exponencial vs mistura com recente
cands = {"hist": lambda i: b.pont(range(1, i))}
for h in (6, 12, 24): cands[f"ewma_h{h}"] = (lambda h: lambda i: pw(i, h))(h)
for lam in (0.25, 0.5):
    cands[f"mix_hist_pers{lam}"] = (lambda lam: lambda i: (1-lam)*b.pont(range(1, i)) + lam*b.pont(range(i-LARGURA, i)))(lam)
cands["recente12"] = lambda i: b.pont(range(i-12, i))
A = {}
for nm, fn in cands.items():
    v = montar(fn); A[nm] = dict(treino=avalia(v, tr_o), teste=avalia(v, te_o))
res["A_memoria"] = A

# ---------- C) KMeans+PCA: perfil da célula -> centro do cluster por faixa; encolhimento da pontuação
def kmpca(ini, k, ncomp, w, seed=0):
    hist = b.pont(range(1, ini)); rec = b.pont(range(ini-6, ini))
    cels = sorted(set(b.cel)); ci = {c: n for n, c in enumerate(cels)}
    X = np.zeros((len(cels), 10))
    for kx, (c, f) in enumerate(b.chaves):
        X[ci[c], f] = np.log1p(hist[kx]*100); X[ci[c], 5+f] = np.log1p(rec[kx]*100)
    Z = PCA(ncomp, random_state=seed).fit_transform((X - X.mean(0)) / (X.std(0) + 1e-9))
    lab = KMeans(k, n_init=10, random_state=seed).fit_predict(Z)
    cent = np.zeros((k, 5))
    for g in range(k):
        for f in range(5):
            mk = [kx for kx, (c, ff) in enumerate(b.chaves) if ff == f and lab[ci[c]] == g]
            cent[g, f] = hist[mk].mean() if mk else 0
    cl = np.array([cent[lab[ci[c]], f] for c, f in b.chaves])
    return (1-w)*hist + w*cl
C = {}
for k, nc, w in [(6,3,0.25),(6,3,0.5),(10,3,0.25),(10,3,0.5),(16,4,0.25),(16,4,0.5)]:
    v = montar(lambda i: kmpca(i, k, nc, w)); C[f"k{k}_pc{nc}_w{w}"] = dict(treino=avalia(v, tr_o), teste=avalia(v, te_o))
res["C_kmeans_pca"] = C
print(json.dumps(res, indent=1)); 

# ---------- B) incerteza: abstenção quando ganho relativo sobre a mais curta < tau
rows = []
for ini in orig:
    hist = b.pont(range(1, ini)); alvo = alvos[ini]
    for f in range(5):
        S, A_, K = sc(hist, f), sc(alvo, f), KM[f]
        for s, a, k in zip(S, A_, K):
            if a.max()-a.min() <= 1e-9 or s.max()-s.min() <= 1e-9: continue
            i = int(np.argmin(s)); j = int(np.argmin(k))
            ganho = (s[j]-s[i])/s[j] if s[j] > 0 else 0
            ss = np.sort(s); gap12 = (ss[1]-ss[0])/ss[1] if ss[1] > 0 else 0
            rows.append(dict(ini=ini, ganho_prev=ganho, gap12=gap12, ei=a[i], ej=a[j], ki=k[i], kj=k[j], hit=a[i] < a[j], igual=(i == j), perde=a[i] > a[j]))
D = pd.DataFrame(rows)
print("\nB) por faixa de ganho previsto sobre a mais curta (hist):")
D["bin"] = pd.cut(D.ganho_prev, [-.001, 0.0001, .05, .15, .30, 1.0])
print(D.groupby("bin", observed=True).apply(lambda g: pd.Series(dict(n=len(g), melhor_que_curta=g[~g.igual].hit.mean() if (~g.igual).any() else np.nan,
      reducao_real=1-g.ei.sum()/g.ej.sum(), km_extra=g.ki.sum()/g.kj.sum()-1))).round(3).to_string())
print("\nB) política: só desvia da mais curta se ganho previsto ≥ tau (treino = 5 primeiras, teste = 5 últimas)")
for nm, dd in (("treino", D[D.ini.isin(tr_o)]), ("teste", D[D.ini.isin(te_o)])):
    for tau in (0, .05, .10, .15, .20, .30):
        esc = dd.ganho_prev >= tau
        e = np.where(esc, dd.ei, dd.ej).sum(); kk = np.where(esc, dd.ki, dd.kj).sum()
        print(nm, f"tau={tau:.2f} desvia={esc.mean():.2%} reducao={1-e/dd.ej.sum():.3%} km_extra={kk/dd.kj.sum()-1:.3%} red/km={(1-e/dd.ej.sum())/max(kk/dd.kj.sum()-1,1e-9):.2f} pior_que_curta={(esc & dd.perde).sum()/max(esc.sum(),1):.2%}")
