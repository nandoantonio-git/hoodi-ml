"""Extrai da SSP-SP (XLSX) os registros do quadrado de 20 km (raio de 10 km) em torno da FIAP Paulista,
com NATUREZA_APURADA e DESCR_CONDUTA, para o candidato do modo carro. Não altera os XLSX."""
import os, time
import duckdb

PASTA = os.environ.get("HOODI_XLSX_DIR", os.path.expanduser("~/Downloads"))
OUT = "ml/dados/interim_carro"
LAT, LON, R_KM = -23.56460, -46.65220, 10.0
DLAT = R_KM / 111.0
DLON = R_KM / (111.0 * 0.9178)  # cos(23,56 graus)
os.makedirs(OUT, exist_ok=True)
c = duckdb.connect(); c.execute("LOAD excel")
for ano in [int(a) for a in os.environ.get("HOODI_ANOS", "2023,2024,2025,2026").split(",")]:
    for aba, nome in [(f"JAN-JUN_{ano}", "jan_jun"), (f"JUL-DEZ_{ano}", "jul_dez")]:
        t = time.time()
        src = f"{PASTA}/SPDadosCriminais_{ano}.xlsx"
        try:
            c.execute(f"""COPY (SELECT NUM_BO, ANO_BO, NOME_DELEGACIA, RUBRICA, NATUREZA_APURADA, DESCR_CONDUTA,
                LATITUDE, LONGITUDE, HORA_OCORRENCIA_BO, DATA_OCORRENCIA_BO
                FROM read_xlsx('{src}', sheet='{aba}', all_varchar=true)
                WHERE try_cast(LATITUDE AS DOUBLE) BETWEEN {LAT-DLAT} AND {LAT+DLAT}
                  AND try_cast(LONGITUDE AS DOUBLE) BETWEEN {LON-DLON} AND {LON+DLON})
                TO '{OUT}/{ano}_{nome}.parquet' (FORMAT parquet)""")
            n = c.execute(f"select count(*) from '{OUT}/{ano}_{nome}.parquet'").fetchone()[0]
            print(aba, n, "linhas", round(time.time() - t), "s", flush=True)
        except Exception as e:
            print(aba, "ERRO", str(e)[:150], flush=True)
