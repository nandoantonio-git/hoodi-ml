"""Invariantes da política de proximidade sobre o snapshot v2 real, com supressão k >= 3."""
import datetime as dt
import hashlib
import json
from zoneinfo import ZoneInfo

import h3
import pytest

from ml import politica_proximidade as P

SP = ZoneInfo("America/Sao_Paulo")


@pytest.fixture(scope="module")
def snap():
    return P.ler_snapshot()


@pytest.fixture(scope="module")
def h_snap():
    return P.sha256_arquivo(P.SNAPSHOT_CSV)


@pytest.fixture(scope="module")
def pol(snap, h_snap):
    return P.montar(snap, h_snap)


def test_sem_dado_nunca_elegivel(snap):
    eleg = P.elegiveis(snap, 0)
    sem = set(zip(snap[snap.status == "sem_dado"].h3_cell, snap[snap.status == "sem_dado"].faixa))
    assert sem and not (eleg & sem)


def test_L3_e_tabela_do_plano(pol):
    assert pol["L"] == 3 and pol["k_anel"] == 1 and pol["cooldown_min"] == 30
    t = {l["L"]: l for l in pol["tabela_por_L"]}
    assert [t[L]["chaves_elegiveis"] for L in (1, 2, 3)] == [682, 475, 200]
    assert all(t[L]["chaves_com_dado"] == 954 for L in (1, 2, 3))
    assert [round(100 * t[L]["fracao_chaves_com_dado"], 1) for L in (1, 2, 3)] == [71.5, 49.8, 21.0]
    assert [round(100 * t[L]["fracao_pontuacao"], 1) for L in (1, 2, 3)] == [94.8, 85.3, 57.4]


def test_fracoes_batem_com_snapshot(snap, pol):
    cd = snap[snap.status == "com_dado"]
    e = cd[cd.nivel >= 3]
    t3 = pol["tabela_por_L"][2]
    assert abs(t3["fracao_pontuacao"] - e.pontuacao_mensal.sum() / cd.pontuacao_mensal.sum()) < 1e-6


def test_hash_do_snapshot_e_do_manifest(pol, h_snap):
    manifest = json.loads((P.C.SNAPSHOT / "manifest.json").read_text())
    assert pol["snapshot_csv_sha256"] == h_snap == manifest["csv_sha256"]


def test_geracao_deterministica(tmp_path):
    a = P.gravar(tmp_path / "a")["sha256"]
    b = P.gravar(tmp_path / "b")["sha256"]
    assert a == b


def test_artefato_versionado_confere(tmp_path):
    novo = P.gravar(tmp_path)["sha256"]
    gravado = (P.DESTINO / f"{P.NOME}.sha256").read_text().split()[0]
    assert novo == gravado == hashlib.sha256((P.DESTINO / P.NOME).read_bytes()).hexdigest()


def test_hash_errado_desativa(pol, snap):
    av = P.Avaliador(pol, snap, "0" * 64)
    cel = next(iter(P.elegiveis(snap, 3)))[0]
    r = av.avaliar(cel, dt.datetime(2026, 11, 16, 15, tzinfo=SP))
    assert r["alerta"] is False and r["erro"]


def test_faixa_por_fuso_e_bordas():
    assert P.faixa_do_instante(dt.datetime(2026, 11, 16, 5, 59, tzinfo=SP)) == 0
    assert P.faixa_do_instante(dt.datetime(2026, 11, 16, 6, 0, tzinfo=SP)) == 1
    assert P.faixa_do_instante(dt.datetime(2026, 11, 16, 18, 0, tzinfo=SP)) == 3
    assert P.faixa_do_instante(dt.datetime(2026, 11, 16, 21, 0, tzinfo=SP)) == 4
    # 00:30 UTC = 21:30 em São Paulo (UTC−3)
    assert P.faixa_do_instante(dt.datetime(2026, 11, 17, 0, 30, tzinfo=dt.timezone.utc)) == 4
    with pytest.raises(ValueError):
        P.faixa_do_instante(dt.datetime(2026, 11, 16, 12))


def test_vizinha_dispara_e_cooldown(pol, snap, h_snap):
    eleg = P.elegiveis(snap, 3)
    alvo, faixa = sorted(eleg)[0]
    viz = sorted(c for c in h3.grid_disk(alvo, 1) if c != alvo)[0]
    hora = {0: 3, 1: 9, 2: 15, 3: 19, 4: 22}[faixa]
    t0 = dt.datetime(2026, 11, 16, hora, 0, tzinfo=SP)
    av = P.Avaliador(pol, snap, h_snap)
    r1 = av.avaliar(viz, t0)
    assert r1["alerta"] and alvo in r1["celulas"] and r1["texto"] == P.TEXTO
    assert not av.avaliar(viz, t0 + dt.timedelta(minutes=29))["alerta"] or \
        alvo not in av.avaliar(viz, t0 + dt.timedelta(minutes=29))["celulas"]
    r3 = av.avaliar(viz, t0 + dt.timedelta(minutes=30))
    assert alvo in r3["celulas"]


def test_texto_sem_linguagem_proibida(pol):
    texto = (pol["texto_alerta"] + " " + pol["texto_sem_dado"]).lower()
    for proibida in ("perigos", "seguro", "risco", "tempo real"):
        assert proibida not in texto
