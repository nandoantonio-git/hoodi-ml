from ml.ingestao import classificar


def test_linha_identica_vira_duplicata(mk):
    r = classificar(mk({}, {}))
    assert sorted(r.destino) == ["duplicata_removida", "usada"]


def test_bo_com_varios_crimes_mantem_uma_linha_por_crime(mk):
    r = classificar(mk({}, {"RUBRICA": "Roubo (art. 157)"}))
    assert list(r.destino) == ["usada", "usada"]


def test_mesmo_crime_em_bos_diferentes_nao_e_duplicata(mk):
    r = classificar(mk({}, {"NUM_BO": "A2"}))
    assert list(r.destino) == ["usada", "usada"]
