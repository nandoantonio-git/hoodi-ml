"""Bloco B (plano v3 r2 §4): referência da pontuação de rota e vetores-ouro."""
import hashlib
import json
import math

import h3
import pandas as pd
import pytest

from ml import rota as R


@pytest.fixture(scope="module")
def snap():
    return pd.read_csv(R.SNAPSHOT_CSV, dtype={"h3_cell": str})


@pytest.fixture(scope="module")
def idx(snap):
    return R.indice_snapshot(snap)


@pytest.fixture(scope="module")
def vet():
    return json.loads((R.DESTINO / "vetores_rota_v2.json").read_text())


def test_h3_core_fixado():
    assert h3.versions()["c"] == "4.5.0"


def test_haversine_conhecido():
    # 1 grau de latitude no meridiano = R·π/180
    assert abs(R.haversine((0, 0), (1, 0)) - R.R_TERRA * math.pi / 180) < 1e-6


def test_rota_invalida():
    for pts in ([], [(-23.56, -46.65)], [(-23.56, -46.65)] * 3, [(-23.56, -46.65), (91, 0)],
                [(-23.56, -46.65), (0, 180)], [(-23.56, -46.65), (float("nan"), 0)]):
        with pytest.raises(R.RotaInvalida):
            R.discretizar(pts)


def test_soma_dos_metros_igual_ao_comprimento():
    pts = [(-23.5646, -46.6522), (-23.5600, -46.6450), (-23.5560, -46.6400)]
    total = sum(m for _, m in R.discretizar(pts))
    comp = R.haversine(pts[0], pts[1]) + R.haversine(pts[1], pts[2])
    assert abs(total - comp) < 0.05  # subsegmentos de corda: diferença desprezível


def test_sem_dado_e_fora_nao_somam(idx, snap):
    sem = snap[snap.status == "sem_dado"].iloc[0]
    r = R.pontuar([(sem.h3_cell, 100.0), ("8928308280fffff", 50.0)], int(sem.faixa), idx)
    assert r["pontuacao_acumulada_observada"] == 0 and r["indice_por_km"] is None
    assert abs(r["pct_sem_dado"] - 200 / 3) < 1e-9 and abs(r["pct_fora_da_cobertura"] - 100 / 3) < 1e-9
    assert r["dado_insuficiente"]


def test_ordenacao_empate_e_insuficiente():
    base = dict(dado_insuficiente=False)
    rs = [dict(base, pontuacao_acumulada_observada=2.0, km_total=1.0),
          dict(base, pontuacao_acumulada_observada=2.0 * (1 + 5e-10), km_total=0.9),
          dict(base, pontuacao_acumulada_observada=1.0, km_total=5.0),
          dict(dado_insuficiente=True, pontuacao_acumulada_observada=0.0, km_total=1.0)]
    assert R.ordenar(rs) == [3, 2, 1, None]


def test_vetores_reproduzem(vet, idx):
    assert len(vet["casos"]) == 10
    for caso in vet["casos"] + vet["rotas_fronteira"]:
        for s in caso["rotas"]:
            e = s["entrada"]
            if "erro" in s:
                with pytest.raises(R.RotaInvalida):
                    R.discretizar(e["pontos"])
                continue
            tr = R.discretizar(e["pontos"])
            assert [c for c, _ in tr] == [x["h3_cell"] for x in s["celulas"]]
            assert all(abs(m - x["metros"]) <= 0.01 for (_, m), x in zip(tr, s["celulas"]))
            r = R.pontuar(tr, e["faixa"], idx)
            a, b = r["pontuacao_acumulada_observada"], s["resultado"]["pontuacao_acumulada_observada"]
            assert abs(a - b) <= 1e-6 * max(abs(b), 1e-12)


def test_casos_cobrem_o_plano(vet):
    nomes = [c["nome"] for c in vet["casos"]]
    assert nomes[5] == "6_um_ponto" and vet["casos"][5]["rotas"][0]["erro"] == "rota_invalida"
    r2 = vet["casos"][1]["rotas"][0]["resultado"]
    assert r2["pct_sem_dado"] > 0
    r3 = vet["casos"][2]["rotas"][0]["resultado"]
    assert r3["pct_fora_da_cobertura"] > 0
    assert vet["casos"][4]["ordenacao_posicoes"] == [1, 2, None]
    c9 = vet["casos"][8]["rotas"][0]["celulas"]
    assert len(c9) == 2  # a→b→a: a célula de partida reaparece e soma metros na mesma entrada
    assert vet["casos"][9]["rotas"][0]["entrada"]["faixa"] == 3
    assert len(vet["pontos_interiores"]) == 20 and len(vet["pontos_fronteira"]) == 20
    assert [v["empate"] for v in vet["empate_vetores"]] == [True, False]


def test_pontos_de_fronteira_conferem(vet):
    for p in vet["pontos_fronteira"] + vet["pontos_interiores"]:
        assert h3.latlng_to_cell(p["lat"], p["lon"], 9) == p["h3_cell"]
    # pares ±5e-8 grau em torno da aresta caem em células diferentes
    fr = vet["pontos_fronteira"]
    assert sum(fr[i]["h3_cell"] != fr[i + 1]["h3_cell"] for i in range(0, 20, 2)) >= 8


def test_geracao_deterministica_e_artefato(tmp_path):
    a = R.gravar(tmp_path / "a")["sha256"]
    b = R.gravar(tmp_path / "b")["sha256"]
    gravado = (R.DESTINO / "vetores_rota_v2.json.sha256").read_text().split()[0]
    assert a == b == gravado == hashlib.sha256((R.DESTINO / "vetores_rota_v2.json").read_bytes()).hexdigest()


def test_empate_nao_transitivo_vira_classes_ancoradas():
    # A~B e B~C, mas A≁C: classes ancoradas no menor → {A, B}, {C}; dentro de {A, B} vence o menor km (B)
    base = dict(dado_insuficiente=False)
    a = dict(base, nome="A", pontuacao_acumulada_observada=1.0, km_total=3.0)
    b = dict(base, nome="B", pontuacao_acumulada_observada=1.0 + 0.9e-9, km_total=2.0)
    c = dict(base, nome="C", pontuacao_acumulada_observada=1.0 + 1.8e-9, km_total=1.0)
    assert R.ordenar([a, b, c]) == [2, 1, 3]
    # a ordem resultante não depende da ordem de entrada (não há empate total aqui)
    import itertools
    for perm in itertools.permutations([a, b, c]):
        pos = R.ordenar(list(perm))
        assert [r["nome"] for _, r in sorted(zip(pos, perm), key=lambda t: t[0])] == ["B", "A", "C"]


@pytest.mark.parametrize("ruim", [[(1.0,), (2.0, 3.0)], [(-23.5, -46.6, 0.0), (-23.5, -46.61)],
                                  [("x", -46.6), (-23.5, -46.61)], [None, (-23.5, -46.61)]])
def test_ponto_malformado_vira_rota_invalida(ruim):
    with pytest.raises(R.RotaInvalida):
        R.discretizar(ruim)
