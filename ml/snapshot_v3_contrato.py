"""Snapshot v3 (contrato): mapa histórico semestral abr–set/2026, mesmo perímetro 5x5 km, mesma regra de pesos e k >= 3.

Promove o candidato de ml/snapshot_semestral.py ao formato completo do contrato (CSV, .sha256, manifest.json, fixture_v3.json)
em ml/dados/snapshot_v3/. Não altera nem apaga o v2 (ml/dados/snapshot/), que segue como referência e para rollback.
"""
import datetime as dt
import hashlib
import json

import pandas as pd

from ml import config as C
from ml import snapshot, snapshot_semestral as S, v2_historico as V

CONTRATO_VERSAO = 3
NOME = "risco_h3_faixa_v3"
FIXTURE_NOME = "fixture_v3.json"
DESTINO = C.DADOS / "snapshot_v3"
NATUREZA = ("Mapa histórico observado (abr–set 2026); não é previsão. "
            "O backtest do classificador é um experimento retrospectivo à parte.")


def gravar(snap: pd.DataFrame, meta_v2: dict, total_usados: int, destino=DESTINO) -> dict:
    snapshot.validar(snap)
    destino.mkdir(parents=True, exist_ok=True)
    csv = destino / f"{NOME}.csv"
    snap.to_csv(csv, index=False, lineterminator="\n", na_rep="", float_format="%.6f")
    h = hashlib.sha256(csv.read_bytes()).hexdigest()
    (destino / f"{NOME}.csv.sha256").write_text(f"{h}  {csv.name}\n")
    manifest = dict(
        contrato_versao=CONTRATO_VERSAO,
        fonte=meta_v2["fonte"],
        janela_dados=["2026-04-01", "2026-09-30"],
        janela_nivel="2026-04-01 a 2026-09-30; pontuacao_mensal = soma ÷ 6 meses ÷ horas da faixa",
        fuso="America/Sao_Paulo",
        h3_resolucao=C.H3_RES,
        faixas=meta_v2["faixas"],
        perimetro=meta_v2["perimetro"],
        perimetro_centro=meta_v2["perimetro_centro"],
        perimetro_tamanho_km=[5, 5],
        cortes_nivel=[round(float(c), 6) for c in snap.attrs["cortes"]],
        formula_pontuacao=("pontuacao_mensal = (soma dos pesos dos registros da chave em abr–set) ÷ 6 meses ÷ "
                           "horas da faixa (6,6,6,3,3). Pesos: furto, tráfico, drogas para consumo, lesão culposa "
                           "no trânsito 1; roubo, lesão corporal 3; homicídio, feminicídio, estupro 5; "
                           "demais rubricas sem peso."),
        nivel_regra="0 abaixo do corte 1; 1 em [c1,c2); 2 em [c2,c3); 3 a partir de c3 (quartis do treino)",
        cortes_regra=("quartis fixos de treino: janelas de 6 meses terminando entre jun/23 e dez/25 "
                      "(passo de 3 meses), sem 2026"),
        privacidade=dict(
            regra=f"k-anonimato por chave H3 × faixa: publicar como sem_dado quando n_registros < {snapshot.K_MINIMO}",
            k_minimo=snapshot.K_MINIMO,
            n_chaves_suprimidas=int(snap.attrs["n_chaves_suprimidas"]),
            n_registros_suprimidos=int(snap.attrs["n_registros_suprimidos"])),
        n_chaves=int(len(snap)), n_com_dado=int((snap.status == "com_dado").sum()),
        n_sem_dado=int((snap.status == "sem_dado").sum()),
        total_linhas_base=meta_v2["total_linhas_base"],
        total_registros_usados=total_usados,
        csv_sha256=h,
        gerado_em=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        natureza=NATUREZA,
        aviso=snapshot.AVISO)
    (destino / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    fx = snapshot._fixture(snap)
    fx["contrato_versao"] = CONTRATO_VERSAO
    (destino / FIXTURE_NOME).write_text(json.dumps(fx, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main():
    u = pd.read_parquet(V.USADAS_V2)
    snap = S.montar(u, cortes=S.cortes_treino(u))
    meta_v2 = json.loads((C.SNAPSHOT / "manifest.json").read_text())
    total = int(u.mes.isin(S.MESES_JANELA).sum())
    m = gravar(snap, meta_v2, total)
    # confere o que foi gravado: o candidato aprovado tem de ter o mesmo CSV
    cand = json.loads((S.DESTINO / "manifest.json").read_text())["csv_sha256"]
    assert cand == m["csv_sha256"], f"CSV difere do candidato aprovado: {cand} != {m['csv_sha256']}"
    print(json.dumps({k: m[k] for k in ("csv_sha256", "n_chaves", "n_com_dado", "n_sem_dado", "cortes_nivel", "privacidade",
                                         "total_registros_usados")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
