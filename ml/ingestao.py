"""Ingestão: dá a cada linha da base exatamente um destino (data-model.md).

destino: usada | quarentena | duplicata_removida | fora_da_janela
Precedência (determinística, uma passagem):
 1. duplicata_removida: linha idêntica de mesmo BO e rubrica (só a repetida)
 2. quarentena: sem_coordenada > sem_hora > sem_data > bo_conflito_coordenada > bo_conflito_hora
 3. fora_da_janela: fora_do_perimetro, depois fora_da_janela_data
 4. usada
"""
import numpy as np
import pandas as pd

from ml import config as C

CHAVE_DUP = ["NUM_BO", "ANO_BO", "NOME_DELEGACIA", "RUBRICA", "LATITUDE", "LONGITUDE",
             "HORA_OCORRENCIA_BO", "DATA_OCORRENCIA_BO"]


def _faixa(minutos):
    f = np.full(len(minutos), -1)
    for cod, _, ini, fim in C.FAIXAS:
        f[(minutos >= ini) & (minutos < fim)] = cod
    return f


def classificar(df: pd.DataFrame, janela=(C.SERIAL_2026_01_01, C.SERIAL_2026_09_30)) -> pd.DataFrame:
    """Recebe as colunas do parquet (texto) e devolve cópia com bo_id, lat, lon, hora, data_fato,
    mes, faixa, celula, destino e motivo. `janela` = (primeiro, último) dia em serial Excel; o padrão é a v1."""
    d = df.copy().reset_index(drop=True)
    d["bo_id"] = d.NUM_BO.astype(str) + "|" + d.ANO_BO.astype(str) + "|" + d.NOME_DELEGACIA.astype(str)
    d["lat"] = pd.to_numeric(d.LATITUDE, errors="coerce")
    d["lon"] = pd.to_numeric(d.LONGITUDE, errors="coerce")
    d["hora"] = pd.to_numeric(d.HORA_OCORRENCIA_BO, errors="coerce")
    d["data_fato"] = pd.to_numeric(d.DATA_OCORRENCIA_BO, errors="coerce").floordiv(1)
    d["rubrica"] = d.RUBRICA

    coord_ok = (d.lat.notna() & d.lon.notna() & (d.lat != 0) & (d.lon != 0)
                & d.lat.between(C.BBOX_SP["lat_min"], C.BBOX_SP["lat_max"])
                & d.lon.between(C.BBOX_SP["lon_min"], C.BBOX_SP["lon_max"]))
    hora_ok = d.hora.notna() & (d.hora >= 0) & (d.hora < 1)
    data_ok = d.data_fato.notna()
    no_perim = (coord_ok & d.lat.between(C.BBOX["lat_min"], C.BBOX["lat_max"])
                & d.lon.between(C.BBOX["lon_min"], C.BBOX["lon_max"]))
    na_janela = data_ok & d.data_fato.between(*janela)

    dup = d.duplicated(subset=CHAVE_DUP, keep="first")

    # conflito entre linhas do mesmo BO (só linhas não duplicadas, só valores válidos)
    base = ~dup
    par = d.lat.astype(str) + "|" + d.lon.astype(str)
    n_coord = par[base & coord_ok].groupby(d.bo_id[base & coord_ok]).nunique()
    n_hora = d.hora[base & hora_ok].groupby(d.bo_id[base & hora_ok]).nunique()
    conf_coord = d.bo_id.isin(n_coord[n_coord > 1].index)
    conf_hora = d.bo_id.isin(n_hora[n_hora > 1].index)

    destino = np.full(len(d), "usada", dtype=object)
    motivo = np.full(len(d), "", dtype=object)
    # aplica do menos para o mais prioritário (o último vence)
    regras = [
        (~na_janela & data_ok, "fora_da_janela", "fora_da_janela_data"),
        (~no_perim, "fora_da_janela", "fora_do_perimetro"),
        (conf_hora, "quarentena", "bo_conflito_hora"),
        (conf_coord, "quarentena", "bo_conflito_coordenada"),
        (~data_ok, "quarentena", "sem_data"),
        (~hora_ok, "quarentena", "sem_hora"),
        (~coord_ok, "quarentena", "sem_coordenada"),
        (dup, "duplicata_removida", ""),
    ]
    for mask, dest, mot in regras:
        destino[mask.values] = dest
        motivo[mask.values] = mot
    d["destino"], d["motivo"] = destino, motivo

    minutos = np.minimum(np.round(d.hora.fillna(0) * 1440), 1439).astype(int).values
    d["faixa"] = np.where(hora_ok.values, _faixa(minutos), -1)
    d["mes"] = np.where(na_janela.values, ((pd.Timestamp("1899-12-30") + pd.to_timedelta(
        d.data_fato.fillna(0), unit="D")).dt.month), 0)

    d["celula"] = None
    usada = d.destino == "usada"
    if usada.any():
        import h3
        pares = d.loc[usada, ["lat", "lon"]].drop_duplicates()
        mapa = {(a, b): h3.latlng_to_cell(a, b, C.H3_RES) for a, b in zip(pares.lat, pares.lon)}
        d.loc[usada, "celula"] = [mapa[(a, b)] for a, b in zip(d.loc[usada, "lat"], d.loc[usada, "lon"])]
    return d


def reconciliar(d: pd.DataFrame) -> dict:
    """Contagem por destino; entrada = soma dos quatro (SC-002)."""
    c = d.destino.value_counts().to_dict()
    r = {k: int(c.get(k, 0)) for k in ["usada", "quarentena", "duplicata_removida", "fora_da_janela"]}
    r["entrada"] = len(d)
    assert r["entrada"] == sum(r[k] for k in ["usada", "quarentena", "duplicata_removida", "fora_da_janela"])
    return r


COLS_USADAS = ["rubrica", "data_fato", "mes", "hora", "faixa", "celula"]
PROIBIDAS_PROCESSED = {"lat", "lon", "LATITUDE", "LONGITUDE", "bo_id", "NUM_BO", "ANO_BO", "NOME_DELEGACIA"}
COLS_QUARENTENA = ["fonte", "linha", "rubrica", "motivo"]


def saida_usadas(d: pd.DataFrame) -> pd.DataFrame:
    """Persistência das usadas: sem bo_id, identificador de BO nem coordenada (FR-013; constituição VII).
    A célula H3 res 9 é a menor unidade espacial persistida."""
    u = d[d.destino == "usada"][COLS_USADAS]
    assert not PROIBIDAS_PROCESSED & set(u.columns)
    return u.sort_values(["celula", "faixa", "data_fato", "hora", "rubrica"], kind="stable").reset_index(drop=True)


def saida_quarentena(d: pd.DataFrame) -> pd.DataFrame:
    """Quarentena rastreável por fonte (aba) e linha, sem número de BO, delegacia nem coordenada."""
    return d[d.destino == "quarentena"][COLS_QUARENTENA].reset_index(drop=True)


def main():
    import duckdb
    cols = ", ".join(CHAVE_DUP)
    partes = [f"select '{n}' as fonte, row_number() over () as linha, {cols} from '{C.INTERIM / n}.parquet'"
              for n in ("jan_jun", "jul_dez")]
    df = duckdb.sql(" union all ".join(partes)).df()
    d = classificar(df)
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    C.QUARANTINE.mkdir(parents=True, exist_ok=True)
    usadas = saida_usadas(d)
    usadas.to_parquet(C.PROCESSED / "usadas.parquet", index=False)
    saida_quarentena(d).to_parquet(C.QUARANTINE / "quarentena.parquet", index=False)
    d.groupby(["destino", "motivo"]).size().rename("n").reset_index().to_csv(
        C.PROCESSED / "destinos.csv", index=False)
    return d, usadas


if __name__ == "__main__":
    main()
