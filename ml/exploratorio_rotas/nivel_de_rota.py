"""EXPLORATÓRIO. Testa a proposta: classificar a ROTA com os cortes das células, usando o índice por km
(média da pontuação ao longo do trajeto ponderada pelo comprimento). Trajetos = proxies geométricos, não malha viária.
Perguntas: (1) a média esconde pico? (2) o nível de rota prevê a janela seguinte? (3) usa os 4 níveis ou colapsa no meio?
(4) a cobertura (trecho sem dado) distorce? Uso: python nivel_de_rota.py <perfil> <dmin_m> <dmax_m> <perimetro: carro|pedestre>"""
import math, sys, json
import numpy as np, pandas as pd, h3
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from ml import config as C, rota, rotulo, snapshot_carro as S

perfil, dmin, dmax, per = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
rng = np.random.default_rng(42)
d = pd.read_pickle("/tmp/carro_usadas.pkl")
B = S.BBOX if per == "carro" else C.BBOX
cels = sorted(d.celula.unique()) if per == "carro" else sorted(c for c in d.celula.unique()
        if B["lat_min"] <= h3.cell_to_latlng(c)[0] <= B["lat_max"] and B["lon_min"] <= h3.cell_to_latlng(c)[1] <= B["lon_max"])
if per == "pedestre":   # pedestre: dados e cortes só do recorte de 5x5 km
    d = d[d.celula.isin(cels)].reset_index(drop=True)
w = S.aplicar_pesos(d, perfil)
cortes = S.cortes_treino(d, w)
dentro = lambda p: B["lat_min"] <= p[0] <= B["lat_max"] and B["lon_min"] <= p[1] <= B["lon_max"]
OFF = 0.0028 * (3 if per == "carro" else 1)

def rotas_par(o, t):
    mid = ((o[0]+t[0])/2, (o[1]+t[1])/2); dx, dy = t[1]-o[1], t[0]-o[0]; n = math.hypot(dx, dy) or 1.0
    perp = (-dy/n*OFF, dx/n*OFF)
    c = {"reta": [o, t], "L_norte": [o, (t[0], o[1]), t], "L_leste": [o, (o[0], t[1]), t],
         "desvio_a": [o, (mid[0]+perp[0], mid[1]+perp[1]), t], "desvio_b": [o, (mid[0]-perp[0], mid[1]-perp[1]), t]}
    return {k: v for k, v in c.items() if all(dentro(p) for p in v)}

pares = []
while len(pares) < 600:
    a, b = rng.choice(cels, 2, replace=False); o, t = h3.cell_to_latlng(a), h3.cell_to_latlng(b)
    if dmin <= rota.haversine(o, t) <= dmax:
        r = rotas_par(o, t)
        if len(r) >= 4: pares.append({k: rota.discretizar(v) for k, v in r.items()})

def vetor(meses, n):
    agr = S.agregar(d, w, meses); p = S.pontuacao(agr, n)
    return {(c, f): v for (c, f), v in p[agr.n >= 3].items()}   # só chaves com k>=3; o resto = sem dado

linhas = []
for fim in range(24, 43, 3):
    hist = vetor(range(fim-23, fim+1), 24); alvo = vetor(range(fim+1, fim+4), 3)
    for f in range(5):
        for pi, rt in enumerate(pares):
            for nome, tr in rt.items():
                km = sum(m for _, m in tr) / 1000
                ph = np.array([hist.get((c, f), np.nan) for c, _ in tr]); m = np.array([x for _, x in tr]) / 1000
                pa = np.array([alvo.get((c, f), 0.0) for c, _ in tr])
                com = ~np.isnan(ph)
                idx = float(np.nansum(ph * m) / km)                      # índice por km, sem dado = 0
                cob = float(m[com].sum() / km)
                niv_c = np.searchsorted(cortes, np.nan_to_num(ph), side="right")
                m3 = float(m[com & (niv_c == 3)].sum() * 1000)
                linhas.append(dict(fim=fim, faixa=f, par=pi, rota=nome, km=km, idx=idx, cobertura=cob,
                                   nivel=int(np.searchsorted(cortes, idx, side="right")), metros_n3=m3,
                                   max_cel_nivel=int(niv_c[com].max()) if com.any() else -1,
                                   futuro=float((pa*m).sum()/km)))
r = pd.DataFrame(linhas)
out = dict(perfil=perfil, perimetro=per, cortes=[round(c, 3) for c in cortes], n_rotas=len(r))
out["distribuicao_nivel_rota"] = {int(k): round(v, 3) for k, v in r.nivel.value_counts(normalize=True).sort_index().items()}
# (1) pico escondido: rota com nível médio <=1 que passa por célula nível 3 / com >=200 m em nível 3
low = r[r.nivel <= 1]
out["pico"] = dict(rotas_nivel_le1=len(low), com_celula_n3=round(float((low.max_cel_nivel == 3).mean()), 3),
                   com_200m_n3=round(float((low.metros_n3 >= 200).mean()), 3))
# (2) validade preditiva: futuro médio por nível de rota (deve crescer) e Spearman idx x futuro
out["futuro_medio_por_nivel"] = {int(k): round(float(v), 3) for k, v in r.groupby("nivel").futuro.mean().items()}
out["spearman_idx_futuro"] = round(float(r.idx.corr(r.futuro, method="spearman")), 3)
out["spearman_idx_futuro_por_origem"] = [round(float(g.idx.corr(g.futuro, method="spearman")), 3) for _, g in r.groupby("fim")]
# metros_n3 como sinal adicional
out["spearman_metros_n3_futuro"] = round(float(r.metros_n3.corr(r.futuro, method="spearman")), 3)
# (3) dentro do mesmo par, o nível separa rotas? fração de pares onde as rotas têm níveis diferentes
g = r.groupby(["fim", "faixa", "par"]).nivel.nunique()
out["pares_com_niveis_distintos"] = round(float((g > 1).mean()), 3)
# (4) cobertura
out["cobertura_media"] = round(float(r.cobertura.mean()), 3)
out["spearman_cobertura_idx"] = round(float(r.cobertura.corr(r.idx, method="spearman")), 3)
out["spearman_cobertura_futuro"] = round(float(r.cobertura.corr(r.futuro, method="spearman")), 3)
out["rotas_cobertura_lt70"] = round(float((r.cobertura < 0.7).mean()), 3)
print(json.dumps(out, ensure_ascii=False, indent=1))
