"""Constituição VII / FR-013: nada em processed/ carrega coordenada ou identificador de BO."""
import pyarrow.parquet as pq
import pytest
from ml import config as C, ingestao


def test_saida_usadas_sem_coordenada_nem_bo(mk):
    d = ingestao.classificar(mk({}))
    u = ingestao.saida_usadas(d)
    assert list(u.columns) == ingestao.COLS_USADAS
    assert not ingestao.PROIBIDAS_PROCESSED & set(u.columns)


@pytest.mark.parametrize("arq", sorted(C.PROCESSED.glob("*.parquet")) or [None])
def test_parquets_reais_em_processed_sem_coordenada_nem_bo(arq):
    if arq is None:
        pytest.skip("processed/ vazio neste checkout")
    cols = set(pq.read_schema(arq).names)
    assert not ingestao.PROIBIDAS_PROCESSED & cols, f"{arq.name}: {ingestao.PROIBIDAS_PROCESSED & cols}"
