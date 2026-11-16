"""Etapa 1: qualidade do dado na base INTEIRA, no município de São Paulo e no perímetro candidato.
Válido = lat/long numéricas, != 0, dentro do retângulo do estado de SP; hora = número em [0,1)."""
import duckdb
c = duckdb.connect()
c.execute("""create view b as select *, 'jan_jun' as aba from 'ml/dados/interim/jan_jun.parquet'
 union all by name select *, 'jul_dez' as aba from 'ml/dados/interim/jul_dez.parquet'""")
# FIAP Paulista (Av. Paulista, 1106) ~ -23.5646, -46.6522 (APROXIMADO; a confirmar). 5x5 km => ±2,5 km
LAT0, LON0 = -23.5646, -46.6522
DLAT, DLON = 2.5 / 111.32, 2.5 / (111.32 * 0.9164)
c.execute(f"""create view v as select *,
  try_cast(LATITUDE as double) la, try_cast(LONGITUDE as double) lo,
  try_cast(HORA_OCORRENCIA_BO as double) h from b""")
c.execute(f"""create view w as select *,
  (la is not null and lo is not null and la<>0 and lo<>0 and la between -25.4 and -19.7 and lo between -53.2 and -44.1) coord_ok,
  (h is not null and h>=0 and h<1) hora_ok,
  (la between {LAT0-DLAT} and {LAT0+DLAT} and lo between {LON0-DLON} and {LON0+DLON}) no_perimetro from v""")
def rel(nome, where):
    n, cp, hr, amb, per = c.execute(f"""select count(*), sum(coord_ok::int), sum(hora_ok::int), sum((coord_ok and hora_ok)::int), sum((coord_ok and hora_ok and no_perimetro)::int)
      from w where {where}""").fetchone()
    print(f"{nome:34s} n={n:>8,}  coord={cp/n:6.1%}  hora={hr/n:6.1%}  ambas={amb/n:6.1%} ({amb:,})  ambas&perímetro={per:,}")
rel("Base inteira", "true")
rel("  aba JAN-JUN", "aba='jan_jun'")
rel("  aba JUL-DEZ", "aba='jul_dez'")
rel("Município S.PAULO", "NOME_MUNICIPIO='S.PAULO'")
rel("  S.PAULO, só ocorrência 2026", "NOME_MUNICIPIO='S.PAULO' and DATA_OCORRENCIA_BO>='46023'")
print("coord fora do retângulo do estado (não-zero, numérica):", c.execute("select count(*) from v where la is not null and la<>0 and not (la between -25.4 and -19.7 and lo between -53.2 and -44.1)").fetchone())
print("BOs distintos (num+ano+delegacia):", c.execute("select count(distinct NUM_BO||'|'||ANO_BO||'|'||NOME_DELEGACIA) from b").fetchone())
print("Ocorrência anterior a 2026 (data real do fato):", c.execute("select count(*) from b where try_cast(DATA_OCORRENCIA_BO as int) < 46023").fetchone())
print("Cobertura temporal do fato em 2026 (mês):")
for r in c.execute("select strftime(date '1899-12-30' + cast(DATA_OCORRENCIA_BO as int), '%Y-%m') m, count(*) from b where try_cast(DATA_OCORRENCIA_BO as int)>=46023 group by 1 order by 1").fetchall(): print("  ", r)
print("Perímetro: bbox lat", round(LAT0-DLAT,5), round(LAT0+DLAT,5), "lon", round(LON0-DLON,5), round(LON0+DLON,5))
print("Perímetro, registros brutos com coord ok (sem exigir hora):", c.execute("select count(*) from w where coord_ok and no_perimetro").fetchone())
print("Perímetro, RUBRICA (coord+hora ok):")
for r in c.execute("select RUBRICA, count(*) from w where coord_ok and hora_ok and no_perimetro group by 1 order by 2 desc limit 8").fetchall(): print("  ", r)
