"""Etapa 0b (exploração adicional, v2): converte os XLSX históricos da SSP-SP (2023–2025) em Parquet,
tudo como texto, sem limpar nada, só as colunas que a ingestão usa. Não altera os originais.
Registra sha256 de cada original em ml/dados/raw/CHECKSUM_HISTORICO.txt; nunca sobrescreve: divergência aborta.
Uso: .venv311/bin/python scripts/00b_historico_xlsx_para_parquet.py [ano ...]"""
import hashlib
import os
import sys
import time

import duckdb

ANOS = [int(a) for a in sys.argv[1:]] or [2023, 2024, 2025]
# Pasta dos XLSX: HOODI_XLSX_DIR ou ~/Downloads (o sha256 em CHECKSUM_HISTORICO.txt é a referência)
SRC = os.path.join(os.environ.get("HOODI_XLSX_DIR", os.path.expanduser("~/Downloads")), "SPDadosCriminais_{ano}.xlsx")
OUT = "ml/dados/interim"
os.makedirs(OUT, exist_ok=True)
CK = "ml/dados/raw/CHECKSUM_HISTORICO.txt"
COLS = ["NUM_BO", "ANO_BO", "NOME_DELEGACIA", "RUBRICA", "LATITUDE", "LONGITUDE",
        "HORA_OCORRENCIA_BO", "DATA_OCORRENCIA_BO"]


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


registrados = {}
if os.path.exists(CK):
    with open(CK) as f:
        for ln in f:
            if ln.strip():
                hx, nome = ln.split()
                registrados[nome] = hx

c = duckdb.connect()
c.execute("INSTALL excel")
c.execute("LOAD excel")
for ano in ANOS:
    src = SRC.format(ano=ano)
    nome = os.path.basename(src)
    hx = sha256(src)
    if nome in registrados and registrados[nome] != hx:
        sys.exit(f"ERRO: sha256 de {nome} ({hx}) difere de {CK}. Abortado.")
    if nome not in registrados:
        with open(CK, "a") as f:
            f.write(f"{hx}  {nome}\n")
    for aba, sufixo in [(f"JAN-JUN_{ano}", "jan_jun"), (f"JUL-DEZ_{ano}", "jul_dez")]:
        t = time.time()
        destino = f"{OUT}/{ano}_{sufixo}.parquet"
        cols = ", ".join(f'"{k}"' for k in COLS)
        c.execute(f"COPY (SELECT {cols} FROM read_xlsx('{src}', sheet='{aba}', all_varchar=true)) "
                  f"TO '{destino}' (FORMAT parquet)")
        n = c.execute(f"select count(*) from '{destino}'").fetchone()[0]
        print(aba, n, "linhas", round(time.time() - t), "s", flush=True)
