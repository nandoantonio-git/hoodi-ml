"""Snapshot CANDIDATO do modo carro: quadrado de 20 km (raio de 10 km) em torno da FIAP Paulista, janela de 24 meses
(out/2024–set/2026), k >= 3, 5 faixas, pesos do perfil escolhido (ml/pesos_perfis.json).
Não substitui o v2 nem o v3; grava em ml/dados/snapshot_carro_candidato/. O pedestre segue no recorte de 5x5 km."""
import json

import h3
import numpy as np
import pandas as pd

from ml import config as C
from ml import ingestao, rotulo, snapshot

R_KM = 10.0
LAT, LON = snapshot.CENTRO["lat"], snapshot.CENTRO["lon"]
BBOX = dict(lat_min=LAT - R_KM / 111.0, lat_max=LAT + R_KM / 111.0,
            lon_min=LON - R_KM / (111.0 * 0.9178), lon_max=LON + R_KM / (111.0 * 0.9178))
PASTA = C.DADOS / "interim_carro"
SERIAL_2023_01_01 = 44927  # primeiro dia da base extraída (índice de mês 1 = jan/2023)
SERIAL_2026_09_30 = C.SERIAL_2026_09_30
DESTINO = C.DADOS / "snapshot_carro_candidato"
N_MESES = 24
PERFIS = json.loads((C.RAIZ / "ml" / "pesos_perfis.json").read_text())["perfis"]


def carregar() -> pd.DataFrame:
    """Registros usados no quadrado de 20 km, com mês corrido (jan/2023 = 1), faixa e célula H3."""
    antes = C.BBOX
    C.BBOX = BBOX  # o filtro de perímetro da ingestão passa a ser o quadrado maior, só neste processo
    try:
        df = pd.concat([pd.read_parquet(p) for p in sorted(PASTA.glob("*.parquet"))], ignore_index=True)
        d = ingestao.classificar(df, janela=(SERIAL_2023_01_01, SERIAL_2026_09_30))
    finally:
        C.BBOX = antes
    d = d[d.destino == "usada"].copy()
    ts = pd.to_datetime("1899-12-30") + pd.to_timedelta(d.data_fato, unit="D")
    d["mes"] = (ts.dt.year - 2023) * 12 + ts.dt.month
    d["natureza"] = d.NATUREZA_APURADA.fillna("")
    d["conduta"] = d.DESCR_CONDUTA.fillna("")
    return d.reset_index(drop=True)


def aplicar_pesos(d: pd.DataFrame, perfil: str) -> pd.Series:
    """Peso por linha: primeira regra do perfil que casa; sem regra = NaN (fora da pontuação)."""
    campos = {"rubrica": d.rubrica.fillna("").str.lower(), "natureza": d.natureza.str.lower(), "conduta": d.conduta.str.lower()}
    peso = pd.Series(np.nan, index=d.index)
    for campo, prefixo, p in PERFIS[perfil]:
        casa = campos[campo].str.startswith(prefixo) if campo != "conduta" else campos[campo].str.contains(prefixo, regex=False)
        peso[peso.isna() & casa] = p
    return peso


def agregar(d, peso, meses):
    x = d[d.mes.isin(list(meses)) & peso.notna()].assign(peso=peso)
    return x.groupby(["celula", "faixa"]).agg(n=("peso", "size"), soma=("peso", "sum"))


def pontuacao(agr, n_meses):
    return rotulo.pontuacao_mensal(agr, n_meses)


def universo(d) -> pd.DataFrame:
    b = BBOX
    poly = h3.LatLngPoly([(b["lat_min"], b["lon_min"]), (b["lat_min"], b["lon_max"]), (b["lat_max"], b["lon_max"]), (b["lat_max"], b["lon_min"])])
    cells = set(h3.h3shape_to_cells_experimental(poly, C.H3_RES, contain="overlap")) | set(d.celula.dropna().unique())
    return pd.DataFrame([(c, f) for c in sorted(cells) for f, *_ in C.FAIXAS], columns=["h3_cell", "faixa"])


def cortes_treino(d, peso) -> list:
    pts = []
    for fim in range(24, 43, 3):
        agr = agregar(d, peso, range(fim - N_MESES + 1, fim + 1))
        p = pontuacao(agr, N_MESES)
        pts.append(p[agr.n >= snapshot.K_MINIMO].dropna().astype(float))
    return [float(v) for v in np.quantile(pd.concat(pts).values, [0.25, 0.5, 0.75])]


def montar(d, peso, cortes) -> pd.DataFrame:
    meses = range(22, 46)  # out/2024–set/2026
    agr = agregar(d, peso, meses)
    pont = pontuacao(agr, N_MESES)
    uni = universo(d).set_index(["h3_cell", "faixa"])
    uni["n_registros"] = agr.n.rename_axis(["h3_cell", "faixa"]).reindex(uni.index).fillna(0).astype(int)
    uni["pontuacao_mensal"] = pont.rename_axis(["h3_cell", "faixa"]).reindex(uni.index)
    uni = uni.reset_index()
    sup = uni.n_registros.between(1, snapshot.K_MINIMO - 1)
    uni.loc[sup, ["n_registros", "pontuacao_mensal"]] = [0, pd.NA]
    uni["status"] = uni.n_registros.gt(0).map({True: "com_dado", False: "sem_dado"})
    uni["nivel"] = rotulo.nivel(uni.pontuacao_mensal, cortes)
    uni["faixa_nome"] = uni.faixa.map(C.FAIXA_NOME)
    return uni.sort_values(["h3_cell", "faixa"]).reset_index(drop=True)[snapshot.COLUNAS]


def main(perfil="carro"):
    import hashlib
    d = carregar(); peso = aplicar_pesos(d, perfil); cortes = cortes_treino(d, peso); snap = montar(d, peso, cortes)
    snapshot.validar(snap)
    DESTINO.mkdir(parents=True, exist_ok=True)
    csv = DESTINO / f"risco_h3_faixa_{perfil}_candidato.csv"
    snap.to_csv(csv, index=False, lineterminator="\n", na_rep="", float_format="%.6f")
    h = hashlib.sha256(csv.read_bytes()).hexdigest()
    (DESTINO / "manifest.json").write_text(json.dumps(dict(
        status="candidato exploratório; não substitui v2/v3", perfil=perfil, raio_km=R_KM, bbox=BBOX, janela=["2024-10-01", "2026-09-30"],
        cortes_nivel=[round(c, 6) for c in cortes], perfis_pesos="ml/pesos_perfis.json", k_minimo=snapshot.K_MINIMO,
        n_chaves=int(len(snap)), n_com_dado=int((snap.status == "com_dado").sum()), csv_sha256=h), ensure_ascii=False, indent=2) + "\n")
    print(h, len(snap), int((snap.status == "com_dado").sum()))


if __name__ == "__main__":
    main()
