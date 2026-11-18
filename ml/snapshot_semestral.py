"""Snapshot CANDIDATO semestral: mesma regra do v2 (pesos, k >= 3, 5 faixas, perímetro 5x5 km), janela de 6 meses (abr–set/2026).

Não substitui o v2 nem o v3 de 24 meses; grava em ml/dados/snapshot_semestral_candidato/ e não altera nenhum outro arquivo.
Cortes de nível: quartis da pontuação mensal (chaves com n >= k) de janelas de 6 meses que terminam em jun/2023 ... dez/2025
(passo de 3 meses), sem tocar jul–set/2026, aplicados à janela final (mesma lógica dos cortes fixos do v3).
"""
import datetime as dt
import hashlib
import json

import numpy as np
import pandas as pd

from ml import config as C
from ml import rotulo, snapshot, v2_historico as V

NOME = "risco_h3_faixa_semestral_candidato"
N_MESES = 6
MESES_JANELA = list(range(40, 46))  # abr–set/2026 (mês corrido: jan/2023 = 1)
FIMS_TREINO = range(6, 37, 3)       # janelas de 6 meses terminando em jun/23 ... dez/25
DESTINO = C.DADOS / "snapshot_semestral_candidato"


def cortes_treino(u: pd.DataFrame) -> list:
    pontos = []
    for fim in FIMS_TREINO:
        meses = list(range(fim - N_MESES + 1, fim + 1))
        agr = rotulo.agregar(u, meses)
        pont = rotulo.pontuacao_mensal(agr, N_MESES)
        pontos.append(pont[agr.n >= snapshot.K_MINIMO].dropna().astype(float))
    return [float(v) for v in np.quantile(pd.concat(pontos).values, [0.25, 0.5, 0.75])]


def montar(u: pd.DataFrame, meses=MESES_JANELA, cortes=None) -> pd.DataFrame:
    if cortes is None:
        cortes = cortes_treino(u)
    janela = u[u.mes.isin(meses)]
    agr = rotulo.agregar(janela, meses)
    pont = rotulo.pontuacao_mensal(agr, len(meses))
    d = snapshot.universo(extras=janela.celula.dropna().unique()).set_index(["h3_cell", "faixa"])
    d["n_registros"] = agr.n.rename_axis(["h3_cell", "faixa"]).reindex(d.index).fillna(0).astype(int)
    d["pontuacao_mensal"] = pont.rename_axis(["h3_cell", "faixa"]).reindex(d.index)
    d = d.reset_index()
    sup = d.n_registros.between(1, snapshot.K_MINIMO - 1)
    n_chaves, n_regs = int(sup.sum()), int(d.loc[sup, "n_registros"].sum())
    d.loc[sup, ["n_registros", "pontuacao_mensal"]] = [0, pd.NA]
    d["status"] = d.n_registros.gt(0).map({True: "com_dado", False: "sem_dado"})
    d["nivel"] = rotulo.nivel(d.pontuacao_mensal, cortes)
    d["faixa_nome"] = d.faixa.map(C.FAIXA_NOME)
    out = d.sort_values(["h3_cell", "faixa"]).reset_index(drop=True)[snapshot.COLUNAS].copy()
    out.attrs.update(cortes=cortes, n_chaves_suprimidas=n_chaves, n_registros_suprimidos=n_regs)
    return out


def gravar(snap: pd.DataFrame, destino=DESTINO) -> dict:
    snapshot.validar(snap)
    destino.mkdir(parents=True, exist_ok=True)
    csv = destino / f"{NOME}.csv"
    snap.to_csv(csv, index=False, lineterminator="\n", na_rep="", float_format="%.6f")
    h = hashlib.sha256(csv.read_bytes()).hexdigest()
    (destino / f"{NOME}.csv.sha256").write_text(f"{h}  {csv.name}\n")
    manifest = dict(
        status="candidato; não substitui o v2 (SHA 2dddef70…) nem o v3 de 24 meses; sem aprovação para virar contrato",
        contrato_base=snapshot.CONTRATO_VERSAO, janela_dados=["2026-04-01", "2026-09-30"], n_meses=N_MESES,
        formula_pontuacao="pontuacao_mensal = soma dos pesos da chave na janela ÷ 6 meses ÷ horas da faixa",
        cortes_nivel=[round(c, 6) for c in snap.attrs["cortes"]],
        cortes_regra="quartis fixos de treino: janelas de 6 meses terminando entre jun/23 e dez/25 (passo de 3 meses), sem 2026",
        privacidade=dict(k_minimo=snapshot.K_MINIMO, n_chaves_suprimidas=snap.attrs["n_chaves_suprimidas"],
                         n_registros_suprimidos=snap.attrs["n_registros_suprimidos"]),
        n_chaves=int(len(snap)), n_com_dado=int((snap.status == "com_dado").sum()),
        n_sem_dado=int((snap.status == "sem_dado").sum()), csv_sha256=h,
        gerado_em=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        natureza="Mapa histórico observado (abr–set/2026); não é previsão.", aviso=snapshot.AVISO)
    (destino / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main():
    u = pd.read_parquet(V.USADAS_V2)
    snap = montar(u, cortes=cortes_treino(u))
    manifest = gravar(snap)
    v2 = pd.read_csv(C.SNAPSHOT / f"{snapshot.NOME}.csv", dtype={"h3_cell": str})
    from ml import snapshot_v3
    comp = snapshot_v3.comparar_com_v2(snap, v2)
    (DESTINO / "comparacao_v2.json").write_text(json.dumps(comp, ensure_ascii=False, indent=2) + "\n")
    print(manifest["csv_sha256"]); print(json.dumps(comp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
