"""Entradas mínimas escritas na hora, só para testes unitários (constituição v1.1.0, princípio I).
Nada daqui alimenta resultado, snapshot, fixture ou relatório."""
import pandas as pd
import pytest

COLS = ["NUM_BO", "ANO_BO", "NOME_DELEGACIA", "RUBRICA", "LATITUDE", "LONGITUDE",
        "HORA_OCORRENCIA_BO", "DATA_OCORRENCIA_BO"]
BASE = dict(NUM_BO="A1", ANO_BO="2026", NOME_DELEGACIA="DP X", RUBRICA="Furto (art. 155)",
            LATITUDE="-23.5646", LONGITUDE="-46.6522", HORA_OCORRENCIA_BO="0.5",
            DATA_OCORRENCIA_BO="46039")


@pytest.fixture
def mk():
    def _mk(*linhas):
        return pd.DataFrame([{**BASE, **l} for l in linhas], columns=COLS).astype(str)
    return _mk
