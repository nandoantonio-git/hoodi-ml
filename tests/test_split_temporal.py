import numpy as np
import pandas as pd
from ml import config as C, features, modelos
import h3
from tests.test_sem_dado import usadas, CEL

CELS = sorted(h3.grid_disk(CEL, 2))[:12]


def _base():
    rng = np.random.default_rng(0)
    linhas = []
    for m in range(1, 10):
        for c in range(12):
            for _ in range(rng.integers(0, 4)):
                linhas.append(dict(mes=m, celula=CELS[c], faixa=int(rng.integers(0, 5)),
                                   rubrica=rng.choice(["Roubo (art. 157)", "Furto (art. 155)"])))
    return usadas(*linhas)


def test_features_sempre_antes_do_rotulo_e_teste_so_ago_set():
    for o, d in C.ORIGENS.items():
        assert max(d["features"]) < min(d["rotulo"])
    assert C.ORIGENS["Teste"]["rotulo"] == [8, 9]
    assert all(max(C.ORIGENS[o]["rotulo"]) <= 7 for o in C.ORIGENS_TREINO)


def test_features_invariantes_a_registros_futuros():
    u = _base()
    futuro = usadas(*[dict(mes=m, rubrica="Homicídio (art. 121)") for m in (3, 4, 8, 9)] * 5)
    for o in C.ORIGENS:
        a = features.construir(u, C.ORIGENS[o]["features"])
        b = features.construir(pd.concat([u, futuro], ignore_index=True), C.ORIGENS[o]["features"])
        if o == "Teste":
            continue  # ago-set está fora; mar-abr entram nas features do Teste por construção
        if max(C.ORIGENS[o]["features"]) < 3:
            pd.testing.assert_frame_equal(a, b)


def test_dobras_com_expurgo_sem_sobreposicao_de_rotulo():
    for treino, val in modelos.DOBRAS:
        ini_val = min(C.ORIGENS[val]["rotulo"])
        for t in treino:
            assert max(C.ORIGENS[t]["rotulo"]) < ini_val
    assert "Teste" not in [v for _, v in modelos.DOBRAS]
    assert all("Teste" not in t for t, _ in modelos.DOBRAS)


def test_cortes_da_dobra_saem_so_do_treino_da_dobra():
    u = _base()
    c1 = modelos.cortes_de(u, ["T1"])
    ruido = usadas(*[dict(mes=m, rubrica="Homicídio (art. 121)", celula=CELS[3]) for m in (5, 6)] * 10)
    assert c1 == modelos.cortes_de(pd.concat([u, ruido], ignore_index=True), ["T1"])
