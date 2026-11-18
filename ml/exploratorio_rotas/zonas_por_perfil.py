"""EXPLORATÓRIO. Agrupa células H3 do quadrado de 20 km pelo perfil de crime (KMeans), sem rótulo.
Perguntas: há perfis distintos (carro x pedestre)? São estáveis entre as duas metades da janela de 24 meses?"""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score

d = pd.read_pickle("/tmp/carro_usadas.pkl")
d = d[d.mes.between(22, 45)].copy()
r, n, c = d.rubrica.fillna("").str.lower(), d.natureza.str.lower(), d.conduta.str.lower()
cat = pd.Series("outros", index=d.index)
for nome, m in [("patrimonio_a_pe", r.str.startswith(("roubo (art. 157)", "furto (art. 155)"))),
                ("drogas", r.str.startswith(("tráfico", "drogas para consumo"))),
                ("pessoa", r.str.startswith(("lesão corporal (art. 129)", "homicídio (art. 121)", "feminicídio", "estupro", "extorsão"))),
                ("transito", r.str.contains("direção de veículo", regex=False)),
                ("veiculo", n.str.contains("veículo") | c.str.contains("interior de veículo", regex=False)),
                ("carga", n.str.contains("carga"))]:
    cat[m] = nome   # a última regra que casa vence (carga > veículo > trânsito > ...)
d["cat"] = cat
print(d.cat.value_counts().to_dict())
d = d[d.cat != "outros"]
CATS = ["patrimonio_a_pe", "veiculo", "carga", "pessoa", "drogas", "transito"]

def perfil(x):
    t = x.groupby(["celula", "cat"]).size().unstack(fill_value=0).reindex(columns=CATS, fill_value=0)
    t = t[t.sum(axis=1) >= 30]                     # k alto: perfil só onde há volume
    sh = t.div(t.sum(axis=1), axis=0)
    noite = x[x.faixa.isin([3, 4, 0])].groupby("celula").size().reindex(t.index).fillna(0) / t.sum(axis=1)
    sh["noite"] = noite
    return np.sqrt(sh), t.sum(axis=1)

F, vol = perfil(d)
print("células com perfil (n>=30):", len(F))
res = {}
for k in range(2, 8):
    km = KMeans(k, n_init=10, random_state=42).fit(F); res[k] = round(float(silhouette_score(F, km.labels_)), 3)
print("silhouette por k:", res)
K = 4
km = KMeans(K, n_init=10, random_state=42).fit(F)
F["cluster"] = km.labels_
tab = d[d.celula.isin(F.index)].merge(F[["cluster"]], left_on="celula", right_index=True)
comp = tab.groupby(["cluster", "cat"]).size().unstack(fill_value=0).reindex(columns=CATS, fill_value=0)
print("composição por cluster (% dos registros):"); print(comp.div(comp.sum(axis=1), axis=0).mul(100).round(1).to_string())
print("células por cluster:", F.cluster.value_counts().sort_index().to_dict())
print("noite média por cluster:", F.groupby("cluster").noite.mean().round(2).to_dict())
# estabilidade: perfis de cada metade (22-33 x 34-45), células comuns
A, _ = perfil(d[d.mes <= 33]); Bm, _ = perfil(d[d.mes >= 34]); com = A.index.intersection(Bm.index)
ka = KMeans(K, n_init=10, random_state=42).fit(A.loc[com]); kb = KMeans(K, n_init=10, random_state=42).fit(Bm.loc[com])
print("estabilidade ARI entre metades (células comuns=%d):" % len(com), round(adjusted_rand_score(ka.labels_, kb.labels_), 3))
# bootstrap de células
ar = []
for s in range(20):
    rng = np.random.default_rng(s); idx = rng.choice(len(F), len(F))
    k2 = KMeans(K, n_init=5, random_state=s).fit(F.iloc[idx].drop(columns="cluster"))
    ar.append(adjusted_rand_score(km.labels_, k2.predict(F.drop(columns="cluster"))))
print("ARI bootstrap médio:", round(float(np.mean(ar)), 3), "min", round(float(np.min(ar)), 3))
F["cluster"].reset_index().rename(columns={"celula": "h3_cell"}).to_csv("/tmp/zonas_perfil.csv", index=False)
