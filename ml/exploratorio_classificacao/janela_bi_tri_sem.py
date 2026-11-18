"""EXPLORATÓRIO (fora do repo ML): o mapa/alvo com janela trimestral ou semestral ganha algo sobre o bimestral?
Mede, sem modelo (persistência e média histórica), por largura W de janela do alvo (2, 3, 6 meses), walk-forward alinhado
ao fim (último alvo termina em set/2026 = mês 45): (1) cobertura de rótulo, (2) repetibilidade do nível (macro-F1, exato,
erro<=1), (3) hit rate a 10% (U1), (4) ordem de rotas (concordância, redução de exposição). Cortes de nível = quartis
das pontuações positivas das janelas anteriores de mesma largura."""
from pathlib import Path
import json, sys, numpy as np
src = open(Path(__file__).resolve().parent.parent.joinpath("exploratorio_rotas","ordem_rotas.py")).read().split("linhas = []")[0]
exec(src)
from ml.ta_descritiva import hit_rate, universos
from sklearn.metrics import f1_score
NM = 45
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
def sc(vec, f): return [np.array([vec[d[n][f][0]] @ d[n][f][1] for n in d]) for d in R]
KM = [[np.array([d[n][f][2] for n in d]) for d in R] for f in range(5)]

def nivel(x, cortes): return np.digitize(x, cortes)  # 0..3
out = {}
for W in (2, 3, 6):
    inis = sorted([NM - W + 1 - W*k for k in range(20) if NM - W + 1 - W*k >= 25])
    acc = dict(cob=[], f1p=[], exp_p=[], l1_p=[], f1h=[], exp_h=[], l1_h=[], hr_p=[], hr_h=[], hr_n=[], conc=0, disc=0, e_h=0.0, e_k=0.0, km_h=0.0, km_k=0.0, conc_p=0, disc_p=0)
    for ini in inis:
        alvo = b.pont(range(ini, ini+W)); hist = b.pont(range(1, ini)); pers = b.pont(range(ini-W, ini))
        # cortes: quartis das pontuações positivas das janelas anteriores de largura W (não sobrepostas ao alvo)
        prev = np.concatenate([b.pont(range(s, s+W))[b.tem(range(s, s+W))] for s in range(ini-W, 0, -W) if s >= 1])
        cortes = np.quantile(prev[prev > 0], [.25, .5, .75])
        lab = b.tem(range(ini, ini+W)) & (alvo > 0)
        labp = b.tem(range(ini-W, ini))
        acc["cob"].append(lab.mean())
        m = lab & labp
        ya = nivel(alvo[m], cortes)
        for nome, v, kf in (("p", pers, "f1p"), ("h", hist, "f1h")):
            yp = nivel(v[m], cortes)
            acc[kf].append(f1_score(ya, yp, average="macro")); acc["exp_"+nome].append((ya == yp).mean()); acc["l1_"+nome].append((abs(ya-yp) <= 1).mean())
        u1 = universos(b, ini)["U1"]
        # universo U1 restrito às chaves; hit rate com alvo de W meses
        for nome, v in (("p", pers), ("h", hist)):
            x = hit_rate(alvo[u1], v[u1], hist[u1], b.cel[u1], b.faixa[u1])
            if x is not None: acc["hr_"+nome].append(x)
        acc["hr_n"].append(int(u1.sum()))
        for f in range(5):
            S, A, P = sc(hist, f), sc(alvo, f), sc(pers, f)
            for s, a, p, k in zip(S, A, P, KM[f]):
                if a.max()-a.min() <= 1e-9 or s.max()-s.min() <= 1e-9: continue
                c, d_ = kendall_pairs(s, a); acc["conc"] += c; acc["disc"] += d_
                c, d_ = kendall_pairs(p, a); acc["conc_p"] += c; acc["disc_p"] += d_
                i = int(np.argmin(s)); j = int(np.argmin(k))
                acc["e_h"] += a[i]; acc["e_k"] += a[j]; acc["km_h"] += k[i]; acc["km_k"] += k[j]
    mean = lambda x: round(float(np.mean(x)), 3)
    out[f"W={W}m"] = dict(n_origens=len(inis), alvos=[nome_janela(i) if W == 2 else f"{i}-{i+W-1}" for i in inis],
        chaves_com_rotulo=mean(acc["cob"]), U1_chaves=int(np.mean(acc["hr_n"])),
        macroF1_persistencia=mean(acc["f1p"]), macroF1_media_hist=mean(acc["f1h"]),
        exato_pers=mean(acc["exp_p"]), exato_hist=mean(acc["exp_h"]), ate1_pers=mean(acc["l1_p"]), ate1_hist=mean(acc["l1_h"]),
        hit10_pers=mean(acc["hr_p"]), hit10_hist=mean(acc["hr_h"]),
        rota_conc_hist=round(acc["conc"]/(acc["conc"]+acc["disc"]), 3), rota_conc_pers=round(acc["conc_p"]/(acc["conc_p"]+acc["disc_p"]), 3),
        rota_reducao=round(1-acc["e_h"]/acc["e_k"], 3), rota_km_extra=round(acc["km_h"]/acc["km_k"]-1, 3))
    print(W, json.dumps(out[f"W={W}m"], ensure_ascii=False), flush=True)
