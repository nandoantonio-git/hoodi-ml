"""Etapa 0: converte o XLSX da SSP-SP em Parquet (tudo como texto, sem limpar nada).
Não altera o arquivo original. Registra sha256 do original em ml/dados/raw/CHECKSUM.txt."""
import hashlib
import os
import sys
import time

import duckdb

# Pasta do XLSX baixado da SSP-SP: HOODI_XLSX_DIR ou ~/Downloads (o sha256 em CHECKSUM.txt é a referência)
SRC = os.path.join(os.environ.get("HOODI_XLSX_DIR", os.path.expanduser("~/Downloads")), "SPDadosCriminais_2026.xlsx")
OUT = "ml/dados/interim"
os.makedirs(OUT, exist_ok=True)
h = hashlib.sha256()
with open(SRC, "rb") as f:
    for b in iter(lambda: f.read(1 << 20), b""):
        h.update(b)
CK = "ml/dados/raw/CHECKSUM.txt"
linha = f"{h.hexdigest()}  SPDadosCriminais_2026.xlsx\n"
if os.path.exists(CK):
    # nunca sobrescreve: o CHECKSUM.txt é a referência; divergência aborta
    with open(CK) as f:
        checksum_registrado = f.read().split()[0]
    if checksum_registrado != h.hexdigest():
        sys.exit(f"ERRO: sha256 do XLSX ({h.hexdigest()}) difere de {CK}. Abortado, nada convertido.")
else:
    with open(CK, "w") as f:
        f.write(linha)
c = duckdb.connect()
c.execute("INSTALL excel")
c.execute("LOAD excel")
for aba, nome in [("JAN-JUN_2026", "jan_jun"), ("JUL-DEZ_2026", "jul_dez")]:
    t = time.time()
    c.execute(f"COPY (SELECT * FROM read_xlsx('{SRC}', sheet='{aba}', all_varchar=true)) TO '{OUT}/{nome}.parquet' (FORMAT parquet)")
    n = c.execute(f"select count(*) from '{OUT}/{nome}.parquet'").fetchone()[0]
    print(aba, n, "linhas", round(time.time() - t), "s", flush=True)
