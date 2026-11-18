"""Snapshot v3 CANDIDATO: mesma regra do v2 (pesos, k >= 3, 5 faixas), janela móvel de 24 meses.

Não substitui o v2: grava em ml/dados/snapshot_v3_candidato/ e não altera nenhum arquivo do v2.
Cortes de nível: protocolo do v2 (fixos, definidos só com o passado). São os quartis da pontuação mensal
de janelas de 24 meses que terminam antes do último trimestre (jul–set/2026), agrupadas, com k >= 3.
Aplicados à janela final, que não entra no cálculo dos cortes.
"""
import datetime as dt
import hashlib
import json

import numpy as np
import pandas as pd

from ml import config as C
from ml import rotulo, snapshot

NOME = "risco_h3_faixa_v3_candidato"
JANELA_INICIO, JANELA_FIM = "2024-10-01", "2026-09-30"
N_MESES = 24
DESTINO = C.DADOS / "snapshot_v3_candidato"


def carregar_janela(usadas: pd.DataFrame) -> pd.DataFrame:
    """Registros dentro da janela. `data_fato` vem como serial do Excel."""
    d = usadas.copy()
    d["rubrica"] = d.rubrica.astype(object)  # evita que .map devolva dtype string no pandas novo
    d["data"] = pd.to_datetime("1899-12-30") + pd.to_timedelta(d.data_fato.floordiv(1), unit="D")
    return d[(d.data >= JANELA_INICIO) & (d.data <= JANELA_FIM)]


FIMS_TREINO = range(24, 43, 3)  # janelas de 24 meses terminando em dez/24 ... jun/26 (índice corrido; jul–set/26 = 43–45 fora)


def cortes_treino(usadas: pd.DataFrame) -> list:
    """Quartis da pontuação mensal das chaves com n >= k em janelas de 24 meses que não tocam o último trimestre."""
    u = usadas.copy()
    u["rubrica"] = u.rubrica.astype(object)
    pontos = []
    for fim in FIMS_TREINO:
        meses = list(range(fim - N_MESES + 1, fim + 1))
        agr = rotulo.agregar(u, meses)
        pont = rotulo.pontuacao_mensal(agr, N_MESES)
        pontos.append(pont[agr.n >= snapshot.K_MINIMO].dropna().astype(float))
    return [float(v) for v in np.quantile(pd.concat(pontos).values, [0.25, 0.5, 0.75])]


def montar(janela: pd.DataFrame, cortes=None) -> pd.DataFrame:
    meses = sorted(janela.mes.unique())  # `mes` do v2 é índice corrido (jan/2023 = 1), não mês do calendário
    if len(meses) != N_MESES:
        raise ValueError(f"janela deve ter {N_MESES} meses, tem {len(meses)}")
    agr = rotulo.agregar(janela, meses)
    pont = rotulo.pontuacao_mensal(agr, N_MESES)
    uni = snapshot.universo(extras=janela.celula.dropna().unique())
    d = uni.set_index(["h3_cell", "faixa"])
    d["n_registros"] = agr.n.rename_axis(["h3_cell", "faixa"]).reindex(d.index).fillna(0).astype(int)
    d["pontuacao_mensal"] = pont.rename_axis(["h3_cell", "faixa"]).reindex(d.index)
    d = d.reset_index()
    sup = d.n_registros.between(1, snapshot.K_MINIMO - 1)
    n_chaves, n_regs = int(sup.sum()), int(d.loc[sup, "n_registros"].sum())
    d.loc[sup, ["n_registros", "pontuacao_mensal"]] = [0, pd.NA]
    d["status"] = d.n_registros.gt(0).map({True: "com_dado", False: "sem_dado"})
    if cortes is None:
        cortes = [float(v) for v in np.quantile(d.pontuacao_mensal.dropna().astype(float), [0.25, 0.5, 0.75])]
    d["nivel"] = rotulo.nivel(d.pontuacao_mensal, cortes)
    d["faixa_nome"] = d.faixa.map(C.FAIXA_NOME)
    out = d.sort_values(["h3_cell", "faixa"]).reset_index(drop=True)[snapshot.COLUNAS].copy()
    out.attrs.update(cortes=cortes, n_chaves_suprimidas=n_chaves, n_registros_suprimidos=n_regs)
    return out


def comparar_com_v2(v3: pd.DataFrame, v2: pd.DataFrame) -> dict:
    j = v3.merge(v2, on=["h3_cell", "faixa"], how="outer", suffixes=("_v3", "_v2"), indicator=True)
    ambos = j[j._merge == "both"]
    com2, com3 = ambos.status_v2 == "com_dado", ambos.status_v3 == "com_dado"
    nos_dois = ambos[com2 & com3]
    return dict(
        chaves_v3=int(len(v3)), chaves_v2=int(len(v2)), so_em_um=int((j._merge != "both").sum()),
        com_dado_v2=int(com2.sum()), com_dado_v3=int(com3.sum()),
        ganhou_dado=int((~com2 & com3).sum()), perdeu_dado=int((com2 & ~com3).sum()),
        nivel_igual=round(float((nos_dois.nivel_v2 == nos_dois.nivel_v3).mean()), 3),
        nivel_difere_ate_1=round(float(((nos_dois.nivel_v2 - nos_dois.nivel_v3).abs() <= 1).mean()), 3),
        spearman_pontuacao=round(float(nos_dois.pontuacao_mensal_v2.astype(float)
                                       .corr(nos_dois.pontuacao_mensal_v3.astype(float), method="spearman")), 3),
        distribuicao_nivel_v2={int(k): int(n) for k, n in nos_dois.nivel_v2.value_counts().sort_index().items()},
        distribuicao_nivel_v3={int(k): int(n) for k, n in nos_dois.nivel_v3.value_counts().sort_index().items()},
    )


def gravar(snap: pd.DataFrame, usadas_total: int, destino=DESTINO) -> dict:
    snapshot.validar(snap)
    destino.mkdir(parents=True, exist_ok=True)
    csv = destino / f"{NOME}.csv"
    snap.to_csv(csv, index=False, lineterminator="\n", na_rep="", float_format="%.6f")
    h = hashlib.sha256(csv.read_bytes()).hexdigest()
    (destino / f"{NOME}.csv.sha256").write_text(f"{h}  {csv.name}\n")
    manifest = dict(
        status="candidato; não substitui o v2 (SHA 2dddef70…)", contrato_base=snapshot.CONTRATO_VERSAO,
        janela_dados=[JANELA_INICIO, JANELA_FIM], n_meses=N_MESES,
        formula_pontuacao="pontuacao_mensal = soma dos pesos da chave na janela ÷ 24 meses ÷ horas da faixa",
        cortes_nivel=[round(c, 6) for c in snap.attrs["cortes"]],
        cortes_regra="quartis fixos de treino: janelas de 24 meses terminando entre dez/24 e jun/26 (passo de 3 meses), sem jul–set/26; mesma lógica do v2",
        privacidade=dict(k_minimo=snapshot.K_MINIMO, n_chaves_suprimidas=snap.attrs["n_chaves_suprimidas"],
                         n_registros_suprimidos=snap.attrs["n_registros_suprimidos"]),
        n_chaves=int(len(snap)), n_com_dado=int((snap.status == "com_dado").sum()),
        n_sem_dado=int((snap.status == "sem_dado").sum()), total_registros_usados_historico=usadas_total,
        csv_sha256=h, gerado_em=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        natureza="Mapa histórico observado (out/2024–set/2026); não é previsão.", aviso=snapshot.AVISO)
    (destino / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main():
    usadas = pd.read_parquet(C.PROCESSED / "usadas_v2.parquet")
    snap = montar(carregar_janela(usadas), cortes_treino(usadas))
    manifest = gravar(snap, int(len(usadas)))
    v2 = pd.read_csv(C.SNAPSHOT / f"{snapshot.NOME}.csv", dtype={"h3_cell": str})
    comp = comparar_com_v2(snap, v2)
    (DESTINO / "comparacao_v2.json").write_text(json.dumps(comp, ensure_ascii=False, indent=2) + "\n")
    print(manifest["csv_sha256"]); print(json.dumps(comp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
