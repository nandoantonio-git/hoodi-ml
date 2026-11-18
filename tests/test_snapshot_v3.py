"""Snapshot v3 candidato: janela de 24 meses, k >= 3 e o v2 intacto."""
import hashlib

import pandas as pd
import pytest

from ml import config as C
from ml import snapshot, snapshot_v3


def _usadas(meses, n_por_mes=1, rubrica="Furto (art. 155)", celula="89a8100c003ffff"):
    linhas = []
    for m in meses:
        data = pd.Timestamp("2023-01-15") + pd.DateOffset(months=m - 1)
        serial = (data - pd.Timestamp("1899-12-30")).days
        linhas += [dict(rubrica=rubrica, data_fato=float(serial), mes=m, hora=10.0, faixa=1, celula=celula)] * n_por_mes
    return pd.DataFrame(linhas)


def test_janela_exige_24_meses():
    j = snapshot_v3.carregar_janela(_usadas(range(1, 46)))
    assert j.mes.nunique() == snapshot_v3.N_MESES


def test_janela_com_menos_meses_falha():
    with pytest.raises(ValueError):
        snapshot_v3.montar(_usadas(range(30, 40)))


def test_snapshot_valido_e_k_anonimato():
    # chave com 2 registros vira sem_dado; chave com 3 vira com_dado
    j = pd.concat([_usadas(range(22, 46), celula="89a8100c003ffff").iloc[:3],
                   _usadas([22, 23], celula="89a8100c00bffff"),
                   _usadas(range(22, 46), n_por_mes=1, rubrica="Outra coisa", celula="89a8100c00fffff")])
    snap = snapshot_v3.montar(j)
    snapshot.validar(snap)
    dois = snap[(snap.h3_cell == "89a8100c00bffff") & (snap.faixa == 1)].iloc[0]
    assert dois.status == "sem_dado" and dois.n_registros == 0 and pd.isna(dois.nivel)


def test_v2_nao_foi_alterado():
    csv = C.SNAPSHOT / "risco_h3_faixa_v2.csv"
    assert hashlib.sha256(csv.read_bytes()).hexdigest().startswith("2dddef70")


def test_cortes_de_treino_ignoram_ultimo_trimestre():
    base = _usadas(range(1, 43), n_por_mes=3)
    ruido = _usadas([43, 44, 45], n_por_mes=500)  # pico só em jul–set/26
    a = snapshot_v3.cortes_treino(base)
    b = snapshot_v3.cortes_treino(pd.concat([base, ruido]))
    assert a == b and len(a) == 3 and a == sorted(a)
