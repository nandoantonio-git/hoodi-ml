"""EXPLORATÓRIO: o ML acrescenta algo à ordem de rotas além da média histórica? Mesmos 600 pares e 10 origens."""
import sys, json, numpy as np
src = open(__import__('pathlib').Path(__file__).with_name('ordem_rotas.py')).read().split("linhas = []")[0]
exec(src)
from ml.ta_descritiva import rf_escore, media_vizinhas, universos
import pandas as pd

# pré-computa matriz célula-por-rota para velocidade: vetor de metros por chave
def matriz(f):
    idx = []; 
    for rt in pares:
        for n, tr in rt.items():
            pass
    return None

nomes_met = ["historica", "persistencia", "suavizada50", "rf", "mistura_hist_rf", "mais_curta"]
acc = {m: dict(conc=0, disc=0, rank=[], exp=0.0) for m in nomes_met}
acc_ll = {m: dict(c=0, n=0) for m in nomes_met}
for ini in REPORTADAS:
    hist = b.pont(range(1, ini)); pers = b.pont(range(ini-LARGURA, ini)); alvo = b.pont(range(ini, ini+LARGURA))
    u1 = universos(b, ini)["U1"]
    viz = media_vizinhas(b.viz, b.n_viz, hist, u1)
    rf, _ = rf_escore(u, b, ini, None)
    rfn = rf / (rf[rf > 0].mean() or 1); hn = hist / (hist[hist > 0].mean() or 1)
    vec = dict(historica=hist, persistencia=pers, suavizada50=0.5*hist+0.5*viz, rf=rf, mistura_hist_rf=0.5*hn+0.5*rfn)
    print(nome_janela(ini), flush=True)
    for f in range(5):
        for rt in pares:
            ns = list(rt)
            ra = np.array([score_rota(rt[n], f, alvo)[0] for n in ns])
            km = np.array([score_rota(rt[n], f, hist)[1] for n in ns])
            sc = {m: np.array([score_rota(rt[n], f, v)[0] for n in ns]) for m, v in vec.items()}
            sc["mais_curta"] = km
            if ra.max()-ra.min() <= 1e-9 or sc["historica"].max()-sc["historica"].min() <= 1e-9: continue
            for m in nomes_met:
                c, d = kendall_pairs(sc[m], ra); acc[m]["conc"] += c; acc[m]["disc"] += d
                i = int(np.argmin(sc[m])); acc[m]["rank"].append(float((ra < ra[i]).sum()+1)); acc[m]["exp"] += ra[i]
            if "L_norte" in rt and "L_leste" in rt:
                j, k = ns.index("L_norte"), ns.index("L_leste")
                for m in nomes_met[:-1]:
                    s = sc[m][j]-sc[m][k]; r = ra[j]-ra[k]
                    if s != 0 and r != 0: acc_ll[m]["n"] += 1; acc_ll[m]["c"] += (s*r > 0)
out = {}
for m in nomes_met:
    a = acc[m]
    out[m] = dict(concordancia=a["conc"]/(a["conc"]+a["disc"]), rank_medio=float(np.mean(a["rank"])),
                  top1=float(np.mean(np.array(a["rank"]) == 1)), exposicao_total=a["exp"],
                  concordancia_L_x_L=(acc_ll[m]["c"]/acc_ll[m]["n"]) if acc_ll[m]["n"] else None)
base = out["mais_curta"]["exposicao_total"]
for m in out: out[m]["reducao_vs_mais_curta"] = 1 - out[m]["exposicao_total"]/base
print(json.dumps(out, indent=1, ensure_ascii=False))
