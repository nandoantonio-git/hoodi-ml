"""Contrato dos arquivos derivados que a API e o app consomem (revisão de código, 2026-11-16).

Lê os arquivos versionados reais: snapshot CSV, manifest, fixture e política de proximidade. A
reprodução dos vetores-ouro de rota já está em test_rota.py; aqui só a amarração por sha256.
"""
import csv
import hashlib
import json
import math

import h3
import pytest

from ml import config as C

CONTRATOS = C.RAIZ / "docs" / "contratos-v3"
CSV = C.SNAPSHOT / "risco_h3_faixa_v2.csv"
COLUNAS = ["h3_cell", "faixa", "faixa_nome", "status", "nivel", "pontuacao_mensal", "n_registros"]


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def linhas():
    with CSV.open(newline="") as f:
        r = csv.DictReader(f)
        assert r.fieldnames == COLUNAS
        return list(r)


@pytest.fixture(scope="module")
def manifest():
    return json.loads((C.SNAPSHOT / "manifest.json").read_text())


@pytest.fixture(scope="module")
def politica():
    return json.loads((CONTRATOS / "politica_proximidade_v2.json").read_text())


def _nivel_esperado(p, cortes):
    return sum(p >= c for c in cortes)


def test_csv_linha_a_linha(linhas, manifest):
    cortes = manifest["cortes_nivel"]
    nomes = {f["faixa"]: f["faixa_nome"] for f in manifest["faixas"]}
    for x in linhas:
        cel = x["h3_cell"]
        assert h3.is_valid_cell(cel) and h3.get_resolution(cel) == manifest["h3_resolucao"] == 9
        f = int(x["faixa"])
        assert f in nomes and x["faixa_nome"] == nomes[f]
        n = int(x["n_registros"])
        assert n >= 0
        if x["status"] == "sem_dado":
            assert n == 0 and x["nivel"] == "" and x["pontuacao_mensal"] == ""
        else:
            assert x["status"] == "com_dado" and n >= manifest["privacidade"]["k_minimo"] == 3
            p = float(x["pontuacao_mensal"])
            assert math.isfinite(p) and p >= 0
            assert int(x["nivel"]) == _nivel_esperado(p, cortes)


def test_chaves_unicas_universo_completo_e_contagens(linhas, manifest):
    chaves = [(x["h3_cell"], int(x["faixa"])) for x in linhas]
    assert len(chaves) == len(set(chaves)) == manifest["n_chaves"]
    celulas = {c for c, _ in chaves}
    assert len(chaves) == len(celulas) * len(manifest["faixas"])
    com = sum(x["status"] == "com_dado" for x in linhas)
    assert com == manifest["n_com_dado"] and len(linhas) - com == manifest["n_sem_dado"]
    assert manifest["n_com_dado"] + manifest["n_sem_dado"] == manifest["n_chaves"]


def test_celulas_dentro_do_perimetro(linhas, manifest):
    b = manifest["perimetro"]
    # A célula entra quando algum registro dentro do perímetro cai nela, então o centro pode ficar fora do
    # retângulo por até uma aresta H3 r9 (~0,2 km). Folga de 0,3 km convertida em graus na latitude local.
    lat0 = (b["lat_min"] + b["lat_max"]) / 2
    f_lat = 0.3 / 111.32
    f_lon = 0.3 / (111.32 * math.cos(math.radians(lat0)))
    for cel in {x["h3_cell"] for x in linhas}:
        lat, lon = h3.cell_to_latlng(cel)
        assert b["lat_min"] - f_lat <= lat <= b["lat_max"] + f_lat
        assert b["lon_min"] - f_lon <= lon <= b["lon_max"] + f_lon


def test_manifest_campos(manifest):
    assert manifest["contrato_versao"] == 2
    assert manifest["fuso"] == "America/Sao_Paulo"
    assert len(manifest["fonte"]["sha256"]) == 64
    assert manifest["cortes_nivel"] == sorted(manifest["cortes_nivel"]) and len(manifest["cortes_nivel"]) == 3
    assert [f["faixa"] for f in manifest["faixas"]] == [f for f, *_ in C.FAIXAS]
    for texto in ("natureza", "aviso"):
        assert manifest[texto]
    assert "não indica tempo real nem local seguro" in manifest["aviso"].lower()
    assert manifest["gerado_em"].endswith("+00:00")
    assert manifest["privacidade"]["k_minimo"] == 3
    assert manifest["privacidade"]["n_chaves_suprimidas"] == 218
    assert manifest["privacidade"]["n_registros_suprimidos"] == 306


def test_sha256_amarrado_em_todos_os_consumidores(manifest, politica):
    real = _sha(CSV)
    gravado = (C.SNAPSHOT / "risco_h3_faixa_v2.csv.sha256").read_text().split()[0]
    vetores = json.loads((CONTRATOS / "vetores_rota_v2.json").read_text())
    assert real == gravado == manifest["csv_sha256"] == politica["snapshot_csv_sha256"] \
        == vetores["snapshot_csv_sha256"]
    for nome in ("politica_proximidade_v2.json", "vetores_rota_v2.json"):
        assert (CONTRATOS / f"{nome}.sha256").read_text().split()[0] == _sha(CONTRATOS / nome)


def test_fixture_e_subconjunto_exato_com_e_sem_dado(linhas):
    fx = json.loads((C.SNAPSHOT / "fixture_v2.json").read_text())
    assert fx["contrato_versao"] == 2
    por_chave = {(x["h3_cell"], int(x["faixa"])): x for x in linhas}
    vistos = set()
    for k in fx["chaves"]:
        x = por_chave[(k["h3_cell"], k["faixa"])]
        assert k["faixa_nome"] == x["faixa_nome"] and k["status"] == x["status"]
        assert k["n_registros"] == int(x["n_registros"])
        if k["status"] == "sem_dado":
            assert k["nivel"] is None and k["pontuacao_mensal"] is None
            vistos.add("sem_dado")
        else:
            assert k["nivel"] == int(x["nivel"])
            assert k["pontuacao_mensal"] == pytest.approx(float(x["pontuacao_mensal"]), abs=1e-6)
            vistos.add(k["nivel"])
    assert vistos == {0, 1, 2, 3, "sem_dado"}


def test_politica_coerente_com_o_snapshot(politica, manifest):
    assert politica["contrato_snapshot_versao"] == manifest["contrato_versao"]
    assert politica["test_seen"] is True
    assert politica["fuso"] == manifest["fuso"]
    assert [(f["faixa"], f["faixa_nome"], f["inicio_min"], f["fim_min"]) for f in politica["faixas"]] == C.FAIXAS
    assert 0 <= politica["L"] <= 3 and politica["k_anel"] >= 0 and politica["cooldown_min"] > 0


def test_textos_sem_promessa_indevida(manifest, politica):
    for texto in (manifest["natureza"], manifest["aviso"], politica["natureza"],
                  json.dumps(politica.get("texto_alerta", ""), ensure_ascii=False)):
        t = texto.lower()
        for proibido in ("rota segura", "local seguro", "tempo real"):
            assert proibido not in t or f"não indica {proibido}" in t or "nem " + proibido in t \
                or f"não {proibido}" in t
