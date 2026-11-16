"""Métricas de calibração (ml/calibracao.py) com entradas escritas na hora."""
import csv

import numpy as np
import pytest

from ml import calibracao as K


def test_brier_perfeito_e_pior_caso():
    y = np.array([0, 3])
    assert K.brier(y, np.eye(4)[y]) == 0
    assert K.brier(y, np.eye(4)[[3, 0]]) == pytest.approx(2.0)


def test_ece_zero_quando_confianca_igual_ao_acerto():
    # confiança 0,5 e metade dos acertos na mesma faixa
    proba = np.tile([0.5, 0.5, 0.0, 0.0], (4, 1))
    assert K.ece(np.array([0, 1, 0, 1]), proba) == pytest.approx(0.0)


def test_ece_mede_excesso_de_confianca():
    proba = np.tile([0.9, 0.1, 0.0, 0.0], (10, 1))
    y = np.array([0] * 5 + [1] * 5)  # acerta 50 % com confiança 0,9
    assert K.ece(y, proba) == pytest.approx(0.4)


def test_isotonica_devolve_probabilidades_validas():
    rng = np.random.default_rng(0)
    p = rng.dirichlet(np.ones(4), 200)
    y = p.argmax(axis=1)
    q = K.Isotonica().fit(p, y).transform(p)
    assert np.allclose(q.sum(axis=1), 1) and (q >= 0).all()


def test_confiabilidade_conta_todos_os_exemplos():
    p = np.linspace(0, 0.999, 50)
    linhas = K.confiabilidade(p > 0.5, p)
    assert sum(r["n"] for r in linhas) == 50


def test_backtest_nao_publica_contagem_por_chave():
    with (K.C.RESULTADOS / "backtest_ago_set.csv").open(newline="") as f:
        linhas = list(csv.DictReader(f))
    assert len(linhas) == 3
    assert set(linhas[0]) == {"modelo", "n", "macro_f1", "acerto_exato", "erro_le_1_nivel"}
    modelos = [r["modelo"] for r in linhas]
    assert len(modelos) == len(set(modelos))
    assert set(modelos) == {"persistencia", "rf_original", "rf_regularizado"}
    assert {int(r["n"]) for r in linhas} == {847}


def test_backtest_agregado_sem_identificador_e_com_metricas():
    y = np.array([0, 1, 2, 3])
    bt = K.backtest_agregado(y, {"perfeito": y, "um_nivel": np.array([1, 0, 3, 2])})
    assert list(bt.columns) == ["modelo", "n", "macro_f1", "acerto_exato", "erro_le_1_nivel"]
    assert len(bt) == 2 and bt["modelo"].is_unique
    assert not {"h3_cell", "faixa", "nivel_real", "n_registros"} & set(bt.columns)
    assert bt.set_index("modelo").loc["perfeito", "acerto_exato"] == 1
    assert bt.set_index("modelo").loc["um_nivel", "erro_le_1_nivel"] == 1
