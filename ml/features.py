"""T023: matriz X e rótulo y por origem (research D-03/D-04). Só registros dos meses de features entram em X."""
import h3
import numpy as np
import pandas as pd

from ml import config as C
from ml import rotulo

GRUPOS = {
    "furto": ("furto",),
    "roubo": ("roubo",),
    "lesao": ("lesão corporal",),
    "graves": ("homicídio", "feminicídio", "estupro"),
    "drogas": ("tráfico drogas", "drogas para consumo"),
}
FAIXA_IDS = [f for f, *_ in C.FAIXAS]
COLUNAS_X = (["faixa", "taxa_registros", "taxa_pontuacao"]
             + [f"taxa_{g}" for g in GRUPOS]
             + [f"pont_faixa_{f}" for f in FAIXA_IDS]
             + ["pont_vizinhas"])


def _grupo(rubrica: str):
    r = str(rubrica).strip().lower()
    for g, prefixos in GRUPOS.items():
        if r.startswith(prefixos):
            return g
    return None


def construir(u: pd.DataFrame, meses) -> pd.DataFrame:
    """X por chave (celula, faixa) com registro pontuável nos `meses`. Taxas = contagem ÷ n meses."""
    meses = list(meses)
    n_meses = len(meses)
    x = rotulo.com_peso(u[u.mes.isin(meses)])
    x = x[x.peso.notna()].copy()
    if x.empty:
        return pd.DataFrame(columns=COLUNAS_X, index=pd.MultiIndex.from_tuples([], names=["celula", "faixa"]))
    agr = x.groupby(["celula", "faixa"]).agg(n=("peso", "size"), soma=("peso", "sum"))
    X = pd.DataFrame(index=agr.index)
    X["taxa_registros"] = agr.n / n_meses
    X["taxa_pontuacao"] = rotulo.pontuacao_mensal(agr, n_meses)
    x["grupo"] = x.rubrica.map(_grupo)
    por_grupo = x.groupby(["celula", "faixa", "grupo"]).size().unstack("grupo")
    for g in GRUPOS:
        col = por_grupo[g] if g in por_grupo.columns else 0
        X[f"taxa_{g}"] = (pd.Series(col, index=por_grupo.index).reindex(X.index).fillna(0) / n_meses)
    pont = X.taxa_pontuacao.unstack("faixa").reindex(columns=FAIXA_IDS).fillna(0.0)
    celulas = X.index.get_level_values("celula")
    for f in FAIXA_IDS:
        X[f"pont_faixa_{f}"] = pont.loc[celulas, f].values
    viz = {}
    for c in pont.index:
        vs = [v for v in h3.grid_disk(c, 1) if v != c]
        viz[c] = pont.reindex(vs).fillna(0.0).mean(axis=0)  # vizinha sem registro conta como 0
    viz = pd.DataFrame(viz).T
    X["pont_vizinhas"] = [float(viz.at[c, f]) for c, f in X.index]
    X["faixa"] = X.index.get_level_values("faixa").astype(int)
    return X[COLUNAS_X].astype(float)


def exemplos(u: pd.DataFrame, origem: str, cortes) -> tuple:
    """(X, y, n_sem_rotulo) da origem: chaves com features E rótulo; y = nível 0–3 com os `cortes` dados."""
    o = C.ORIGENS[origem]
    X = construir(u, o["features"])
    y_pont = rotulo.rotulos(u, origem)
    comum = X.index.intersection(y_pont.index)
    sem_rotulo = len(X.index.difference(y_pont.index))
    X = X.loc[comum].sort_index()
    y = rotulo.nivel(y_pont.loc[X.index], cortes).astype(int)
    X.insert(0, "origem", origem)
    return X, y, sem_rotulo


def persistencia(X: pd.DataFrame, cortes) -> np.ndarray:
    """Linha de base: o nível da própria chave na janela de features (mesma normalização do rótulo)."""
    return rotulo.nivel(X.taxa_pontuacao, cortes).astype(int).values


def gravar(u: pd.DataFrame, cortes, destino=None) -> dict:
    destino = destino or C.FEATURES
    destino.mkdir(parents=True, exist_ok=True)
    resumo = {}
    for o in C.ORIGENS:
        X, y, sem = exemplos(u, o, cortes)
        d = X.copy()
        d["nivel"] = y.values
        d.reset_index(level="celula").to_parquet(destino / f"{o}.parquet", index=False)
        resumo[o] = dict(n_exemplos=int(len(X)), n_sem_rotulo=sem)
    return resumo
