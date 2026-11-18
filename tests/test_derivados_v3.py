"""Política de proximidade e vetores de rota gerados sobre o snapshot v3 (semestral, contrato v3)."""
import datetime as dt
import hashlib
import json
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from ml import config as C
from ml import politica_proximidade as P
from ml import rota as R

V3 = C.DADOS / "snapshot_v3"
CSV = V3 / "risco_h3_faixa_v3.csv"
CONTRATOS = C.RAIZ / "docs" / "contratos-v3"
SP = ZoneInfo("America/Sao_Paulo")


def _sha(caminho) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def snap():
    return pd.read_csv(CSV, dtype={"h3_cell": str})


@pytest.fixture(scope="module")
def pol():
    return json.loads((CONTRATOS / "politica_proximidade_v3.json").read_text())


def test_politica_v3_amarrada_ao_csv_v3(pol):
    assert pol["snapshot_csv_sha256"] == _sha(CSV)
    assert pol["contrato_snapshot_versao"] == 3
    assert pol["snapshot_csv"].endswith("snapshot_v3/risco_h3_faixa_v3.csv")
    assert "abr–set/2026" in pol["texto_alerta"] and "jan–set" not in json.dumps(pol, ensure_ascii=False)


def test_politica_v3_gravada_e_reproduzivel(pol, snap):
    assert P.montar(snap, _sha(CSV), contrato=3) == pol
    gravado = (CONTRATOS / "politica_proximidade_v3.json.sha256").read_text().split()[0]
    assert gravado == _sha(CONTRATOS / "politica_proximidade_v3.json")


def test_politica_v3_nao_alerta_com_snapshot_v2(pol):
    v2 = pd.read_csv(C.SNAPSHOT / "risco_h3_faixa_v2.csv", dtype={"h3_cell": str})
    av = P.Avaliador(pol, v2, _sha(C.SNAPSHOT / "risco_h3_faixa_v2.csv"))
    r = av.avaliar(v2.h3_cell.iloc[0], dt.datetime(2026, 11, 18, 15, 0, tzinfo=SP))
    assert not av.ativa and not r["alerta"] and r["erro"]


def test_politica_v3_alerta_so_com_dado_nunca_sem_dado(pol, snap):
    eleg = P.elegiveis(snap, pol["L"])
    sem = set(zip(snap[snap.status == "sem_dado"].h3_cell, snap[snap.status == "sem_dado"].faixa.astype(int)))
    assert eleg and not (eleg & sem)
    assert len(eleg) == 207


def test_vetores_v3_amarrados_e_reproduziveis(snap):
    v = json.loads((CONTRATOS / "vetores_rota_v3.json").read_text())
    assert v["snapshot_csv_sha256"] == _sha(CSV) and v["contrato_snapshot_versao"] == 3
    assert "jan–set" not in json.dumps(v, ensure_ascii=False)
    assert (CONTRATOS / "vetores_rota_v3.json.sha256").read_text().split()[0] == _sha(CONTRATOS / "vetores_rota_v3.json")
    idx = R.indice_snapshot(snap)
    for caso in v["casos"]:
        for s in caso["rotas"]:
            if "resultado" not in s:
                continue
            esperado = R.pontuar(R.discretizar(s["entrada"]["pontos"]), s["entrada"]["faixa"], idx)
            assert esperado["pontuacao_acumulada_observada"] == pytest.approx(
                s["resultado"]["pontuacao_acumulada_observada"], abs=1e-9)


def test_vetores_v3_regerados_sao_identicos_byte_a_byte(tmp_path):
    """Cobre resultado completo, erros, dado insuficiente e ordenação: o arquivo publicado é exatamente o gerado."""
    R.gravar(tmp_path, contrato=3)
    assert (tmp_path / "vetores_rota_v3.json").read_bytes() == (CONTRATOS / "vetores_rota_v3.json").read_bytes()
