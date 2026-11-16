# Proveniência do raw (T005) — registro auditável

Gerado em 2026-11-11 a partir dos arquivos locais e da reexecução do script 00.

## Fonte
- URL: https://www.ssp.sp.gov.br/assets/estatistica/transparencia/spDados/SPDadosCriminais_2026.xlsx (SSP-SP, Transparência; servidor informa atualização em 28/10/2026)
- Arquivo local: ~/Downloads/SPDadosCriminais_2026.xlsx, 139.931.418 bytes
- sha256 do local: f627d84ea8d95ae9301180d92e267610176b00d58a3eed5f7b1a8cd4e65acbaf
- Baixado de novo em 2026-11-11 (curl, HTTP 200, 139.931.418 bytes): sha256 idêntico ao do local
- A SSP não publica hash oficial: a prova é de identidade com o que o servidor serve em 2026-11-11, não da data original

## Conversão (scripts/00_xlsx_para_parquet.py, tudo como texto, sem limpar)
- Comando: `.venv311/bin/python scripts/00_xlsx_para_parquet.py` (reexecutado em 2026-11-11; não sobrescreve `CHECKSUM.txt` e aborta se o hash divergir)
- Parquets antigos (de antes da reexecução) comparados com os novos por EXCEPT ALL nos dois sentidos: 0 linhas diferentes

## Versões
- Python 3.11.15, duckdb 2.0.0, pandas 3.1.1, pyarrow 26.0.1; extensão duckdb `excel` instalada em 2026-11-11 (autorizada pelo Nando)

## Parquets em ml/dados/interim/
| Arquivo | Aba do XLSX | Linhas | sha256 |
|---|---|---|---|
| jan_jun.parquet | JAN-JUN_2026 | 555404 | 3ad519f5eed0a05aa8817d45e29c3640ee5de203510293c23b9a7d11167fa063 |
| jul_dez.parquet | JUL-DEZ_2026 | 259496 | 594ce6e835baf7dd216863e7e0f2bebb2a87bd30444b80d00dd827bbc18f925e |

Observação (medido): os parquets de antes da reexecução tinham sha256 diferente (jan_jun f2930379aff0612433b4040081a41c30f63be6633e4679fde6ce699cae50e7fe; jul_dez 332aa485d50903f0886424eee5649f029f1a3345a1137e29ed148e9a45897f83), embora o conteúdo seja idêntico (EXCEPT ALL = 0 nos dois sentidos). O que prova a identidade é o conteúdo, não o hash do arquivo parquet.

## Resultado a jusante
- Ingestão: 814.900 linhas = 20.343 usadas + 384.867 quarentena + 2.390 duplicata_removida + 407.300 fora_da_janela (ml/dados/reconciliacao.txt)
- Snapshot v2 com supressão k ≥ 3: sha256 2dddef701bdecb65142874980f1ae5aba7b2ac6ab2abad5c47b07f07ecc5080a, idêntico em duas gerações
