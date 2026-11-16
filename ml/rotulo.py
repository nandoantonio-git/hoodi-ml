"""Pontuação, cortes de quartil do treino e níveis 0–3 (research D-03 a D-05)."""
import numpy as np
import pandas as pd

from ml import config as C


def com_peso(u: pd.DataFrame) -> pd.DataFrame:
    x = u.copy()
    x["peso"] = x.rubrica.map(C.peso_rubrica)
    return x


def agregar(u: pd.DataFrame, meses) -> pd.DataFrame:
    """Por (celula, faixa): n de registros pontuáveis e soma dos pesos nos meses dados."""
    x = com_peso(u[u.mes.isin(list(meses))])
    x = x[x.peso.notna()]
    return x.groupby(["celula", "faixa"]).agg(n=("peso", "size"), soma=("peso", "sum"))


def pontuacao_mensal(agr: pd.DataFrame, n_meses: int) -> pd.Series:
    """soma de pesos ÷ n_meses ÷ horas da faixa (pontos por mês por hora)."""
    horas = agr.index.get_level_values("faixa").map(C.FAIXA_HORAS).astype(float)
    return agr.soma / n_meses / horas.values


def rotulos(u: pd.DataFrame, origem: str) -> pd.Series:
    """Pontuação mensal das chaves com registro pontuável na janela de rótulo da origem."""
    meses = C.ORIGENS[origem]["rotulo"]
    return pontuacao_mensal(agregar(u, meses), len(meses))


def cortes_treino(u: pd.DataFrame) -> list:
    """3 cortes de quartil dos rótulos de treino (T1 a T4 juntos). Nunca usa ago–set."""
    todos = pd.concat([rotulos(u, o) for o in C.ORIGENS_TREINO])
    return [float(v) for v in np.quantile(todos.values, [0.25, 0.5, 0.75])]


def nivel(pontuacao: pd.Series, cortes) -> pd.Series:
    """0 abaixo do corte 1; 1 em [c1,c2); 2 em [c2,c3); 3 de c3 em diante. NaN fica NaN (sem dado)."""
    v = pontuacao.astype(float)
    n = pd.Series(np.searchsorted(list(cortes), v.fillna(0).values, side="right"), index=v.index).astype("Int64")
    return n.where(v.notna(), pd.NA)


def rubricas_sem_peso(u: pd.DataFrame) -> pd.DataFrame:
    x = com_peso(u)
    return (x[x.peso.isna()].groupby("rubrica").size().rename("n_registros")
            .sort_values(ascending=False).reset_index())
