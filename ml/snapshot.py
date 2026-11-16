"""Snapshot v2 para o app: CSV, sha256, manifest.json e fixture (contracts/snapshot-risco.md)."""
import datetime as dt
import hashlib
import json
from pathlib import Path

import h3
import pandas as pd

from ml import config as C
from ml import rotulo

CONTRATO_VERSAO = 2
K_MINIMO = 3
NOME = "risco_h3_faixa_v2"
FIXTURE_NOME = "fixture_v2.json"
COLUNAS = ["h3_cell", "faixa", "faixa_nome", "status", "nivel", "pontuacao_mensal", "n_registros"]
AVISO = "Melhor dado disponível no período. Não indica tempo real nem local seguro."
NATUREZA = ("Mapa histórico observado (jan–set 2026); não é previsão. "
            "O backtest do classificador é um experimento retrospectivo à parte.")
CENTRO = dict(lat=-23.56460, lon=-46.65220)  # centro do retângulo; provisório até a coordenada exata da FIAP


def universo(extras=()) -> pd.DataFrame:
    """Todas as células H3 res. 9 que cobrem o perímetro (mais as de `extras`) × 5 faixas."""
    b = C.BBOX
    poly = h3.LatLngPoly([(b["lat_min"], b["lon_min"]), (b["lat_min"], b["lon_max"]),
                          (b["lat_max"], b["lon_max"]), (b["lat_max"], b["lon_min"])])
    cells = set(h3.h3shape_to_cells_experimental(poly, C.H3_RES, contain="overlap")) | set(extras)
    return pd.DataFrame([(c, f) for c in sorted(cells) for f, *_ in C.FAIXAS], columns=["h3_cell", "faixa"])


def montar(usadas: pd.DataFrame, cortes) -> pd.DataFrame:
    """Uma linha por chave. Chaves com menos de K_MINIMO registros são publicadas como sem_dado."""
    agr = rotulo.agregar(usadas, range(C.MES_PRIMEIRO, C.MES_ULTIMO + 1))
    meses = C.MES_ULTIMO - C.MES_PRIMEIRO + 1
    pont = rotulo.pontuacao_mensal(agr, meses)
    uni = universo(extras=usadas.celula.dropna().unique())
    d = uni.set_index(["h3_cell", "faixa"])
    d["n_registros"] = agr.n.rename_axis(["h3_cell", "faixa"]).reindex(d.index).fillna(0).astype(int)
    d["pontuacao_mensal"] = pont.rename_axis(["h3_cell", "faixa"]).reindex(d.index)
    d = d.reset_index()
    suprimidas = d.n_registros.between(1, K_MINIMO - 1)
    n_chaves_suprimidas = int(suprimidas.sum())
    n_registros_suprimidos = int(d.loc[suprimidas, "n_registros"].sum())
    d.loc[suprimidas, "n_registros"] = 0
    d.loc[suprimidas, "pontuacao_mensal"] = pd.NA
    d["status"] = d.n_registros.gt(0).map({True: "com_dado", False: "sem_dado"})
    d["nivel"] = rotulo.nivel(d.pontuacao_mensal, cortes)
    d["faixa_nome"] = d.faixa.map(C.FAIXA_NOME)
    d = d.sort_values(["h3_cell", "faixa"]).reset_index(drop=True)
    out = d[COLUNAS].copy()
    out.attrs.update(k_minimo=K_MINIMO, n_chaves_suprimidas=n_chaves_suprimidas,
                     n_registros_suprimidos=n_registros_suprimidos)
    return out


def _fixture(snap: pd.DataFrame) -> dict:
    # Um exemplo real e determinístico de cada nível, mais sem_dado. A fixture é para integração/legenda;
    # não precisa formar um recorte espacial contíguo e não altera o CSV de produção.
    partes = []
    for nivel in range(4):
        candidatas = snap[(snap.status == "com_dado") & (snap.nivel == nivel)]
        if len(candidatas):
            partes.append(candidatas.sort_values(["n_registros", "h3_cell", "faixa"],
                                                  ascending=[False, True, True]).head(1))
    sem_dado = snap[snap.status == "sem_dado"].sort_values(["h3_cell", "faixa"]).head(1)
    if len(sem_dado):
        partes.append(sem_dado)
    amostra = pd.concat(partes).sort_values(["h3_cell", "faixa"]).reset_index(drop=True)
    chaves = []
    for r in amostra.itertuples():
        chaves.append(dict(
            h3_cell=r.h3_cell, faixa=int(r.faixa), faixa_nome=r.faixa_nome, status=r.status,
            nivel=None if pd.isna(r.nivel) else int(r.nivel),
            pontuacao_mensal=None if pd.isna(r.pontuacao_mensal) else round(float(r.pontuacao_mensal), 6),
            n_registros=int(r.n_registros)))
    return dict(contrato_versao=CONTRATO_VERSAO,
                descricao="Amostra real com níveis 0–3 e sem_dado para testes do app; não é o snapshot completo.",
                chaves=chaves)


def gravar(snap: pd.DataFrame, destino, cortes, meta: dict) -> dict:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    csv = destino / f"{NOME}.csv"
    snap.to_csv(csv, index=False, lineterminator="\n", na_rep="", float_format="%.6f")
    h = hashlib.sha256(csv.read_bytes()).hexdigest()
    (destino / f"{NOME}.csv.sha256").write_text(f"{h}  {csv.name}\n")
    b = C.BBOX
    manifest = dict(
        contrato_versao=CONTRATO_VERSAO,
        fonte=dict(orgao="SSP-SP", arquivo="SPDadosCriminais_2026.xlsx", sha256=meta.get("raw_sha256")),
        janela_dados=["2026-01-01", "2026-09-30"],
        janela_nivel="2026-01-01 a 2026-09-30; pontuacao_mensal = soma ÷ 9 meses ÷ horas da faixa",
        fuso="America/Sao_Paulo",
        h3_resolucao=C.H3_RES,
        faixas=[dict(faixa=f, faixa_nome=n, intervalo_horas=f"[{i // 60},{fim // 60})") for f, n, i, fim in C.FAIXAS],
        perimetro=dict(lat_min=b["lat_min"], lat_max=b["lat_max"], lon_min=b["lon_min"], lon_max=b["lon_max"]),
        perimetro_centro=dict(**CENTRO, provisorio=True),
        perimetro_tamanho_km=[5, 5],
        cortes_nivel=[round(float(c), 6) for c in cortes],
        formula_pontuacao=("pontuacao_mensal = (soma dos pesos dos registros da chave em jan–set) ÷ 9 meses ÷ "
                           "horas da faixa (6,6,6,3,3). Pesos: furto, tráfico, drogas para consumo, lesão culposa "
                           "no trânsito 1; roubo, lesão corporal 3; homicídio, feminicídio, estupro 5; "
                           "demais rubricas sem peso."),
        nivel_regra="0 abaixo do corte 1; 1 em [c1,c2); 2 em [c2,c3); 3 a partir de c3 (quartis do treino)",
        privacidade=dict(
            regra=f"k-anonimato por chave H3 × faixa: publicar como sem_dado quando n_registros < {K_MINIMO}",
            k_minimo=K_MINIMO,
            n_chaves_suprimidas=int(snap.attrs.get("n_chaves_suprimidas", 0)),
            n_registros_suprimidos=int(snap.attrs.get("n_registros_suprimidos", 0)),
        ),
        n_chaves=int(len(snap)), n_com_dado=int((snap.status == "com_dado").sum()),
        n_sem_dado=int((snap.status == "sem_dado").sum()),
        total_linhas_base=meta.get("total_linhas_base"),
        total_registros_usados=meta.get("total_registros_usados"),
        csv_sha256=h,
        gerado_em=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),  # fora do hash do CSV
        natureza=NATUREZA,
        aviso=AVISO,
    )
    (destino / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    (destino / FIXTURE_NOME).write_text(json.dumps(_fixture(snap), ensure_ascii=False, indent=2) + "\n")
    return manifest
