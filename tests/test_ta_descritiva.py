"""Bloco C (r3 §2.2): métrica e regras da T-A descritiva."""
import json

import numpy as np

from ml import ta_descritiva as T


def test_hit_rate_top_10_e_desempate():
    alvo = np.array([5.0, 0, 0, 0, 0, 0, 0, 0, 0, 5.0, 0])  # N=11 → k=ceil(1,1)=2
    esc = np.array([1.0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    hist = np.zeros(11)
    cel = np.array([f"c{i:02d}" for i in range(11)])
    fx = np.zeros(11, int)
    assert T.hit_rate(alvo, esc, hist, cel, fx) == 0.5
    # empate total no escore: desempata pela média histórica e depois id crescente
    esc0 = np.zeros(11)
    hist2 = np.zeros(11)
    hist2[9] = 1.0
    assert T.hit_rate(alvo, esc0, hist2, cel, fx) == 1.0  # c09 (hist) e c00 (menor id)


def test_denominador_zero_excluido():
    z = np.zeros(4)
    assert T.hit_rate(z, z, z, np.array(list("abcd")), np.zeros(4, int)) is None


def test_janelas_do_plano():
    assert T.nome_janela(T.SELECAO[0]) == "mar–abr/2024" and T.nome_janela(T.SELECAO[-1]) == "nov–dez/2024"
    assert T.nome_janela(T.REPORTADAS[0]) == "jan–fev/2025" and T.nome_janela(T.REPORTADAS[-1]) == "jul–ago/2026"
    assert T.nome_janela(T.JA_VISTA) == "ago–set/2026"
    assert all(i - 12 >= 1 for i in T.SELECAO)  # ≥ 12 meses de passado


def test_lambda_congelado_e_resultado_coerente():
    lam = json.loads(T.LAMBDA_JSON.read_text())
    res = json.loads(T.SAIDA.read_text())
    assert lam["lambda_escolhido"] in T.LAMBDAS and res["lambda_escolhido"] == lam["lambda_escolhido"]
    assert len(res["origens_reportadas"]) == 10
    for o in res["origens_reportadas"]:
        assert o["meses_alvo"][0] >= 25  # nenhuma origem de seleção entre as reportadas
        u1, u2 = o["universos"]["U1"], o["universos"]["U2"]
        assert u1["n_chaves"] <= u2["n_chaves"]
        for m in T.METODOS:
            assert 0 <= u1["hit_rate_10"][m] <= 1


def test_rf_treina_so_com_passado():
    res = json.loads(T.SAIDA.read_text())
    for o in res["origens_reportadas"]:
        # janelas de treino começam no mês 13 com passo 1 e terminam antes do alvo
        assert o["rf"]["n_janelas_treino"] == o["meses_alvo"][0] - T.LARGURA - 13 + 1


import h3
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def dados():
    u = pd.read_parquet(T.USADAS_V2)
    return u, T.Base(u)


def test_divisor_da_suavizada_conta_so_vizinhas_existentes(dados):
    _, b = dados
    assert not [c for c in b.cel if h3.is_pentagon(c)]  # o perímetro de SP não tem pentágono; a regra vale mesmo assim
    assert (b.n_viz == 6).all()
    # implementação real (media_vizinhas): pentágono simulado com 5 vizinhas existentes, todas hist=1 em U1 → 1, não 5/6
    hist, u1 = np.ones(3), np.ones(3, bool)
    viz = np.array([[0, 1, 2, 0, 1, -2],      # pentágono: 5 vizinhas
                    [0, 1, 2, 0, 1, -1],      # hexágono com 1 vizinha fora do universo (conta 0, entra no divisor)
                    [0, 1, 2, 0, 1, 2]])
    n = (viz != -2).sum(axis=1)
    m = T.media_vizinhas(viz, n, hist, u1)
    assert m[0] == 1.0 and m[1] == pytest.approx(5 / 6) and m[2] == 1.0
    u1[2] = False  # vizinha fora de U1 conta 0 e continua no divisor
    assert T.media_vizinhas(viz, n, hist, u1)[0] == pytest.approx(4 / 5)


def test_lambda_reproduz_o_congelado(dados):
    u, b = dados
    assert T.escolher_lambda(u, b) == json.loads(T.LAMBDA_JSON.read_text())
    # todas as origens de seleção terminam antes da primeira reportada
    assert max(T.SELECAO) + T.LARGURA - 1 < min(T.REPORTADAS)


@pytest.mark.parametrize("ini", [T.REPORTADAS[0], T.JA_VISTA])
def test_escores_nao_usam_o_futuro(dados, ini):
    """Escores calculados com os dados cortados em mes < ini são idênticos aos calculados com tudo."""
    u, b = dados
    uc = u[u.mes < ini]
    bc = T.Base(uc)
    us = T.universos(b, ini)
    e, _ = T.escores_base(b, ini, us["U1"], 0.5)
    # Base cortada tem matriz até ini-1; universos U1 só olham o passado
    u1c = bc.tem(range(ini - 12, ini))
    ec, _ = T.escores_base(bc, ini, u1c, 0.5)
    comum = b.chaves.intersection(bc.chaves)
    assert len(comum) == len(bc.chaves)
    i, ic = b.pos.loc[comum].values, bc.pos.loc[comum].values
    for m in ("persistencia", "media_historica", "suavizada"):
        np.testing.assert_allclose(e[m][i], ec[m][ic], rtol=0, atol=1e-12)
    # chaves que só existem por causa do futuro têm escore 0
    so_futuro = np.setdiff1d(np.arange(len(b.chaves)), i)
    for m in ("persistencia", "media_historica"):
        assert (e[m][so_futuro] == 0).all()


def test_rf_nao_usa_o_futuro(dados):
    u, b = dados
    ini = T.REPORTADAS[0]
    e, meta = T.rf_escore(u, b, ini, None)
    ec, metac = T.rf_escore(u[u.mes < ini], b, ini, None)
    assert meta == metac
    np.testing.assert_allclose(e, ec, rtol=0, atol=1e-12)
