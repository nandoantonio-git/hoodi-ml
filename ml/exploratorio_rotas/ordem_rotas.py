"""EXPLORATÓRIO (fora do repositório hoodi-ml-v2; nada gravado lá). Concordância de ordem entre rotas alternativas:
a ordem pelo passado (média histórica até a origem) se mantém na janela seguinte (bimestre-alvo)?
Trajetos = proxies geométricos (reta, L, desvios), NÃO malha viária. Dado real nas células."""
import json, math, sys
import numpy as np, pandas as pd, h3
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from ml import config as C, rota
from ml.ta_descritiva import Base, USADAS_V2, REPORTADAS, JA_VISTA, LARGURA, nome_janela

rng = np.random.default_rng(42)
u = pd.read_parquet(USADAS_V2)
b = Base(u)
snap = pd.read_csv(C.SNAPSHOT / "risco_h3_faixa_v2.csv", dtype={"h3_cell": str})
cels = sorted(snap.h3_cell.unique())
pos = b.pos  # (celula, faixa) -> linha
B = C.BBOX

def dentro(p): return B["lat_min"] <= p[0] <= B["lat_max"] and B["lon_min"] <= p[1] <= B["lon_max"]

def rotas_par(o, d):
    mid = ((o[0]+d[0])/2, (o[1]+d[1])/2)
    dx, dy = d[1]-o[1], d[0]-o[0]
    n = math.hypot(dx, dy) or 1.0
    off = 0.0028  # ~300 m
    perp = (-dy/n*off, dx/n*off)
    v1 = (mid[0]+perp[0], mid[1]+perp[1]); v2 = (mid[0]-perp[0], mid[1]-perp[1])
    cand = {"reta": [o, d], "L_norte": [o, (d[0], o[1]), d], "L_leste": [o, (o[0], d[1]), d],
            "desvio_a": [o, v1, d], "desvio_b": [o, v2, d]}
    return {k: v for k, v in cand.items() if all(dentro(p) for p in v)}

pares = []
while len(pares) < 600:
    a, c = rng.choice(cels, 2, replace=False)
    o, d = h3.cell_to_latlng(a), h3.cell_to_latlng(c)
    dist = rota.haversine(o, d)
    if 900 <= dist <= 2500:
        r = rotas_par(o, d)
        if len(r) >= 4:
            pares.append({k: rota.discretizar(v) for k, v in r.items()})
print("pares:", len(pares))

def score_rota(tr, f, vec):
    s = 0.0; km = 0.0
    for c, m in tr:
        k = pos.get((c, f))
        km += m/1000
        if k is not None: s += vec[k] * m/1000
    return s, km

def kendall_pairs(past, real):
    conc = disc = 0
    for i in range(len(past)):
        for j in range(i+1, len(past)):
            a, bb = past[i]-past[j], real[i]-real[j]
            if a == 0 or bb == 0: continue
            if a*bb > 0: conc += 1
            else: disc += 1
    return conc, disc

linhas = []
origens = REPORTADAS + [JA_VISTA]
for ini in origens:
    hist = b.pont(range(1, ini)); pers = b.pont(range(ini-LARGURA, ini)); alvo = b.pont(range(ini, ini+LARGURA))
    for f in range(5):
        for pi, rt in enumerate(pares):
            nomes = list(rt)
            ph = np.array([score_rota(rt[n], f, hist)[0] for n in nomes])
            pp = np.array([score_rota(rt[n], f, pers)[0] for n in nomes])
            ra = np.array([score_rota(rt[n], f, alvo)[0] for n in nomes])
            km = np.array([score_rota(rt[n], f, hist)[1] for n in nomes])
            if ra.max() - ra.min() <= 1e-9 or ph.max()-ph.min() <= 1e-9: continue
            conc, disc = kendall_pairs(ph, ra)
            conc_p, disc_p = kendall_pairs(pp, ra)
            conc_k, disc_k = kendall_pairs(km, ra)
            ih = int(np.argmin(ph)); ik = int(np.argmin(km)); ip = int(np.argmin(pp))
            rank_real = lambda i: float((ra < ra[i]).sum() + 1)  # 1 = melhor
            linhas.append(dict(ini=ini, faixa=f, par=pi, n=len(nomes), conc=conc, disc=disc, conc_pers=conc_p, disc_pers=disc_p,
                               conc_km=conc_k, disc_km=disc_k,
                               rank_hist=rank_real(ih), rank_km=rank_real(ik), rank_pers=rank_real(ip),
                               exp_hist=ra[ih], exp_km=ra[ik], km_hist=km[ih], km_km=km[ik], rank_medio=(len(nomes)+1)/2,
                               exp_media=ra.mean()))
df = pd.DataFrame(linhas)
df.to_csv("ordem_rotas_linhas.csv", index=False)

def resumo(d):
    c, x = d.conc.sum(), d.disc.sum()
    cp, xp = d.conc_pers.sum(), d.disc_pers.sum(); ck, xk = d.conc_km.sum(), d.disc_km.sum()
    # bootstrap por par (cluster) para IC da diferença de exposição relativa vs rota mais curta
    pares_ids = d.par.unique(); g = {p: x for p, x in d.groupby("par")}
    red = []
    for _ in range(500):
        s = pd.concat([g[p] for p in rng.choice(pares_ids, len(pares_ids))])
        red.append(1 - s.exp_hist.sum()/s.exp_km.sum())
    return dict(n_casos=len(d), concordancia_historica=c/(c+x), concordancia_persistencia=cp/(cp+xp),
                concordancia_km_mais_curta=ck/(ck+xk),
                rank_medio_escolhida_hist=d.rank_hist.mean(), rank_medio_mais_curta=d.rank_km.mean(),
                rank_medio_persistencia=d.rank_pers.mean(), rank_medio_acaso=d.rank_medio.mean(),
                top1_hist=float((d.rank_hist == 1).mean()), top1_km=float((d.rank_km == 1).mean()),
                reducao_exposicao_vs_mais_curta=1-d.exp_hist.sum()/d.exp_km.sum(),
                ic95_reducao=[float(np.percentile(red, 2.5)), float(np.percentile(red, 97.5))],
                km_extra_pct=d.km_hist.sum()/d.km_km.sum()-1)

geral = resumo(df[df.ini != JA_VISTA])
print("REPORTADAS (10 origens) ", json.dumps(geral, indent=1, ensure_ascii=False))
print("ago–set/2026", json.dumps(resumo(df[df.ini == JA_VISTA]), indent=1, ensure_ascii=False))
print("por faixa:")
for f in range(5): 
    r = resumo(df[(df.ini != JA_VISTA) & (df.faixa == f)]); print(f, round(r["concordancia_historica"],3), round(r["reducao_exposicao_vs_mais_curta"],3), round(r["km_extra_pct"],3), r["n_casos"])
print("por origem:")
for i in REPORTADAS:
    r = resumo(df[df.ini == i]); print(nome_janela(i), round(r["concordancia_historica"],3), round(r["reducao_exposicao_vs_mais_curta"],3))
