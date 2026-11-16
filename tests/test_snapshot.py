import hashlib, json

import pandas as pd

from ml import snapshot
from tests.test_sem_dado import usadas, CEL

CORTES = [0.01, 0.05, 0.1]
COLS = ["h3_cell", "faixa", "faixa_nome", "status", "nivel", "pontuacao_mensal", "n_registros"]


def test_colunas_exatas_sem_nivel_previsto():
    snap = snapshot.montar(usadas({}), CORTES)
    assert list(snap.columns) == COLS


def test_chave_unica_e_ordenada_e_universo_completo():
    snap = snapshot.montar(usadas({}), CORTES)
    assert not snap.duplicated(["h3_cell", "faixa"]).any()
    assert list(snap.index) == list(range(len(snap)))
    assert snap.equals(snap.sort_values(["h3_cell", "faixa"]).reset_index(drop=True))
    uni = snapshot.universo(extras=[CEL])
    assert len(snap) == len(uni) and set(snap.faixa) == {0, 1, 2, 3, 4}
    assert (snap.groupby("h3_cell").faixa.nunique() == 5).all()


def test_pontuacao_normalizada_por_hora_da_faixa():
    linhas = ([{"rubrica": "Roubo (art. 157)", "faixa": 3}] * 3
              + [{"rubrica": "Roubo (art. 157)", "faixa": 2}] * 3)
    snap = snapshot.montar(usadas(*linhas), CORTES)
    p3 = snap[(snap.faixa == 3) & (snap.status == "com_dado")].pontuacao_mensal.iloc[0]
    p2 = snap[(snap.faixa == 2) & (snap.status == "com_dado")].pontuacao_mensal.iloc[0]
    assert abs(p3 - 9 / 9 / 3) < 1e-9 and abs(p2 - 9 / 9 / 6) < 1e-9


def test_k_menor_que_3_e_suprimido_sem_revelar_a_chave():
    snap = snapshot.montar(usadas({}, {}), CORTES)
    linha = snap[(snap.h3_cell == CEL) & (snap.faixa == 2)].iloc[0]
    assert linha.status == "sem_dado" and linha.n_registros == 0
    assert pd.isna(linha.nivel) and pd.isna(linha.pontuacao_mensal)
    assert snap.attrs["k_minimo"] == 3
    assert snap.attrs["n_chaves_suprimidas"] == 1
    assert snap.attrs["n_registros_suprimidos"] == 2


def test_gravacao_sha256_e_manifest(tmp_path):
    snap = snapshot.montar(usadas({}), CORTES)
    snapshot.gravar(snap, tmp_path, cortes=CORTES, meta=dict(total_linhas_base=10, total_registros_usados=1,
                                                              raw_sha256="x"))
    csv = tmp_path / "risco_h3_faixa_v2.csv"
    h = hashlib.sha256(csv.read_bytes()).hexdigest()
    assert (tmp_path / "risco_h3_faixa_v2.csv.sha256").read_text() == f"{h}  risco_h3_faixa_v2.csv\n"
    m = json.loads((tmp_path / "manifest.json").read_text())
    assert m["contrato_versao"] == 2 and m["csv_sha256"] == h
    assert m["fuso"] == "America/Sao_Paulo" and m["h3_resolucao"] == 9
    assert m["privacidade"]["k_minimo"] == 3
    assert "Não indica tempo real nem local seguro" in m["aviso"]
    assert csv.read_text().splitlines()[0] == ",".join(COLS)
    assert "\r" not in csv.read_text()


def test_fixture_sem_identificador_de_bo_e_com_sem_dado(tmp_path):
    snap = snapshot.montar(usadas({"bo_id": "BO-SECRETO"}), CORTES)
    snapshot.gravar(snap, tmp_path, cortes=CORTES, meta={})
    txt = (tmp_path / "fixture_v2.json").read_text() + (tmp_path / "manifest.json").read_text() \
        + (tmp_path / "risco_h3_faixa_v2.csv").read_text()
    assert "BO-SECRETO" not in txt and "NUM_BO" not in txt
    fx = json.loads((tmp_path / "fixture_v2.json").read_text())
    assert any(c["status"] == "sem_dado" and c["nivel"] is None for c in fx["chaves"])
