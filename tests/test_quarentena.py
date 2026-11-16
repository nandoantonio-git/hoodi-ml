import pytest
from ml.ingestao import classificar, reconciliar


@pytest.mark.parametrize("campos,motivo", [
    ({"LATITUDE": "0", "LONGITUDE": "0"}, "sem_coordenada"),
    ({"LATITUDE": "NULL"}, "sem_coordenada"),
    ({"LATITUDE": "abc"}, "sem_coordenada"),
    ({"LATITUDE": "10.0", "LONGITUDE": "-46.6"}, "sem_coordenada"),  # fora do retângulo de SP
    ({"HORA_OCORRENCIA_BO": "NULL"}, "sem_hora"),
    ({"HORA_OCORRENCIA_BO": "1.0"}, "sem_hora"),  # válida só em [0,1)
    ({"HORA_OCORRENCIA_BO": "-0.1"}, "sem_hora"),
])
def test_motivos_de_quarentena(mk, campos, motivo):
    r = classificar(mk(campos))
    assert r.destino.iloc[0] == "quarentena"
    assert r.motivo.iloc[0] == motivo


def test_hora_zero_e_valida(mk):
    assert classificar(mk({"HORA_OCORRENCIA_BO": "0"})).destino.iloc[0] == "usada"


def test_bo_com_coordenada_conflitante_vai_inteiro_para_quarentena(mk):
    r = classificar(mk({}, {"RUBRICA": "Roubo (art. 157)", "LATITUDE": "-23.5700"}))
    assert set(r.destino) == {"quarentena"}
    assert set(r.motivo) == {"bo_conflito_coordenada"}


def test_bo_com_hora_conflitante(mk):
    r = classificar(mk({}, {"RUBRICA": "Roubo (art. 157)", "HORA_OCORRENCIA_BO": "0.9"}))
    assert set(r.motivo) == {"bo_conflito_hora"}


def test_reconciliacao_exata(mk):
    df = mk({}, {}, {"LATITUDE": "0", "LONGITUDE": "0"}, {"NUM_BO": "B", "LATITUDE": "-23.0"},
            {"NUM_BO": "C", "DATA_OCORRENCIA_BO": "40000"})
    r = classificar(df)
    rec = reconciliar(r)
    assert rec["entrada"] == len(df) == 5
    assert rec["entrada"] == rec["usada"] + rec["quarentena"] + rec["duplicata_removida"] + rec["fora_da_janela"]
    assert r.destino.notna().all()


def test_persistencia_sem_identificador_de_bo(mk):
    from ml.ingestao import saida_quarentena, saida_usadas
    df = mk({"NUM_BO": "SECRETO"}, {"NUM_BO": "SECRETO2", "HORA_OCORRENCIA_BO": "NULL"})
    df["fonte"], df["linha"] = "jan_jun", [1, 2]
    r = classificar(df)
    u, q = saida_usadas(r), saida_quarentena(r)
    for t in (u, q):
        txt = t.to_csv()
        assert "SECRETO" not in txt and "DP X" not in txt
        assert not {"bo_id", "NUM_BO", "NOME_DELEGACIA", "ANO_BO"} & set(t.columns)
    assert list(q.columns) == ["fonte", "linha", "rubrica", "motivo"]
    assert q.motivo.iloc[0] == "sem_hora" and q.linha.iloc[0] == 2
