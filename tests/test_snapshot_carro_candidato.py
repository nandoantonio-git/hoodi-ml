"""Candidato de carro: o CSV bate com o SHA do manifesto e respeita as invariantes (k >= 3, sem_dado sem nível)."""
import csv
import hashlib
import json
from pathlib import Path

PASTA = Path(__file__).resolve().parents[1] / "ml" / "dados" / "snapshot_carro_candidato"


def test_sha_do_csv_confere_com_o_manifesto():
    m = json.loads((PASTA / "manifest.json").read_text())
    h = hashlib.sha256((PASTA / "risco_h3_faixa_carro_candidato.csv").read_bytes()).hexdigest()
    assert h == m["csv_sha256"]


def test_invariantes_k_e_sem_dado():
    m = json.loads((PASTA / "manifest.json").read_text())
    linhas = list(csv.DictReader((PASTA / "risco_h3_faixa_carro_candidato.csv").open()))
    assert len(linhas) == m["n_chaves"]
    assert sum(1 for r in linhas if r["status"] == "com_dado") == m["n_com_dado"]
    for r in linhas:
        if r["status"] == "com_dado":
            assert int(r["n_registros"]) >= m["k_minimo"] and r["nivel"] in {"0", "1", "2", "3"}
        else:
            assert r["status"] == "sem_dado" and r["nivel"] == ""
