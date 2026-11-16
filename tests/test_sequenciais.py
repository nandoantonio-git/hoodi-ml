import numpy as np
import pandas as pd
from ml import config as C, features, sequenciais
from tests.test_split_temporal import _base
from tests.test_sem_dado import usadas


def _exemplos(u, origem):
    X, y, _ = features.exemplos(u, origem, [0.1, 0.3, 0.6])
    return X, y


def test_serie_so_usa_meses_de_features_da_origem():
    u = _base()
    X, _ = _exemplos(u, "T2")
    s = sequenciais.serie(u, X)
    assert s.shape[1] == len(C.ORIGENS["T2"]["features"])
    futuro = usadas(*[dict(mes=m, rubrica="Homicídio (art. 121)", celula=X.index[0][0], faixa=X.index[0][1])
                      for m in (4, 5, 8, 9)] * 3)
    s2 = sequenciais.serie(pd.concat([u, futuro], ignore_index=True), X)
    np.testing.assert_array_equal(s, s2)


def test_lstm_reprodutivel_com_mesma_semente():
    u = _base()
    X = pd.concat([_exemplos(u, o)[0] for o in ("T1", "T2")])
    y = pd.concat([_exemplos(u, o)[1] for o in ("T1", "T2")])
    a = sequenciais.LSTMNivel(u, 8, 1e-2, 0.0).fit(X, y.values).predict(X)
    b = sequenciais.LSTMNivel(u, 8, 1e-2, 0.0).fit(X, y.values).predict(X)
    assert (a == b).all() and set(a) <= {0, 1, 2, 3}


def test_kmeans_mapa_vem_so_do_treino():
    u = _base()
    X, y = _exemplos(u, "T3")
    m = sequenciais.KMeansPCANivel(2, 3, False).fit(X, y.values)
    assert set(m.mapa) == {0, 1, 2} and set(m.predict(X)) <= set(m.mapa.values())
