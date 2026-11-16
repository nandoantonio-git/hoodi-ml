from ml.ingestao import classificar


def test_fato_fora_de_jan_set_2026(mk):
    r = classificar(mk({"DATA_OCORRENCIA_BO": "46022"}, {"NUM_BO": "B", "DATA_OCORRENCIA_BO": "46296"},
                       {"NUM_BO": "C", "DATA_OCORRENCIA_BO": "46023"}, {"NUM_BO": "D", "DATA_OCORRENCIA_BO": "46295"}))
    assert list(r.destino) == ["fora_da_janela", "fora_da_janela", "usada", "usada"]
    assert r.motivo.iloc[0] == "fora_da_janela_data"


def test_coordenada_valida_fora_do_perimetro(mk):
    r = classificar(mk({"LATITUDE": "-23.60"}))
    assert r.destino.iloc[0] == "fora_da_janela"
    assert r.motivo.iloc[0] == "fora_do_perimetro"


def test_data_ausente_vai_para_quarentena(mk):
    r = classificar(mk({"DATA_OCORRENCIA_BO": "NULL"}))
    assert (r.destino.iloc[0], r.motivo.iloc[0]) == ("quarentena", "sem_data")


def test_faixa_por_bordas_explicitas(mk):
    horas = ["0", "0.249", "0.25", "0.499", "0.5", "0.749", "0.75", "0.874", "0.875", "0.99"]
    df = mk(*[{"NUM_BO": f"B{i}", "HORA_OCORRENCIA_BO": h} for i, h in enumerate(horas)])
    assert list(classificar(df).faixa) == [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]


def test_celula_h3_res9_so_para_usadas(mk):
    r = classificar(mk({}, {"NUM_BO": "B", "LATITUDE": "-23.60"}))
    assert len(r.celula.iloc[0]) == 15 and r.celula.iloc[0].startswith("89")
    assert r.celula.iloc[1] is None or r.celula.iloc[1] != r.celula.iloc[1]
