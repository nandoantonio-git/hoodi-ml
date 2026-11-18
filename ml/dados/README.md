# Dados do hoodi ML

## Fonte
- **Órgão:** Secretaria da Segurança Pública do Estado de São Paulo (SSP-SP), portal de Transparência.
- **Arquivo principal:** `SPDadosCriminais_2026.xlsx` (139.931.418 bytes), baixado de `https://www.ssp.sp.gov.br/assets/estatistica/transparencia/spDados/SPDadosCriminais_2026.xlsx`; o servidor informava atualização em 28/10/2026.
- **sha256:** `f627d84ea8d95ae9301180d92e267610176b00d58a3eed5f7b1a8cd4e65acbaf` (`raw/CHECKSUM.txt`). A SSP não publica hash oficial; a prova é de identidade com o arquivo servido em 2026-11-11 (`raw/PROVENIENCIA.md`).
- **Histórico (v2, exploração adicional):** `SPDadosCriminais_2023/2024/2025.xlsx`, sha256 em `raw/CHECKSUM_HISTORICO.txt`.
- Os XLSX **não** são versionados (`*.xlsx` no `.gitignore`). Para reproduzir, baixe-os e aponte `HOODI_XLSX_DIR` para a pasta (padrão `~/Downloads`); os scripts abortam se o sha256 divergir.

## Pipeline e destinos
| Etapa | Script / módulo | Saída | Versionado? |
|---|---|---|---|
| 0. XLSX → Parquet, tudo texto | `scripts/00_xlsx_para_parquet.py` | `interim/*.parquet` | não |
| 1. Ingestão, janela, perímetro, deduplicação | `ml/ingestao.py` | `processed/usadas.parquet`, `quarantine/` | não |
| 2. Snapshot do app | `ml/gerar_snapshot.py` | `snapshot/` (CSV v2, `.sha256`, `manifest.json`, `fixture_v2.json`) | **sim** |
| 3. Modelos e avaliações | `ml/modelos.py`, `ml/incerteza_custo.py`, `ml/calibracao.py`… | `resultados/` | **sim** (métricas agregadas; backtest sem H3, faixa, rótulo ou contagem por chave) |
| 4. Exploratórios (anexo) | `ml/exploratorio_classificacao/*.py`, `ml/exploratorio_rotas/` | `resultados/classificacao_exploratorio/`, `resultados/rotas_exploratorio/` | **sim** (agregados). Reproduzidos em 17/11/2026: os 3 scripts de classificação por faixa dão saída idêntica à guardada |

Reconciliação da base 2026 (`reconciliacao.txt`): 814.900 linhas = 20.343 usadas + 384.867 quarentena + 2.390 duplicatas removidas + 407.300 fora da janela ou do perímetro. **Dado utilizável: 2,50 % da base; 58,5 % do que cai no perímetro.** A maior perda dentro do perímetro é `sem_hora` (14.113 registros), que não pode ser atribuído a uma faixa horária.

## Campos usados
| Campo | Origem | Uso |
|---|---|---|
| `rubrica` | `RUBRICA` | peso do registro (furto, tráfico, drogas, lesão culposa no trânsito = 1; roubo, lesão corporal = 3; homicídio, feminicídio, estupro = 5; demais sem peso) |
| `data_fato`, `mes` | `DATA_OCORRENCIA_BO` (serial Excel) | janela jan–set/2026 e origens temporais |
| `hora`, `faixa` | `HORA_OCORRENCIA_BO` | faixa horária: 0 madrugada [0,6), 1 manhã [6,12), 2 tarde [12,18), 3 noite cedo [18,21), 4 noite [21,24), America/Sao_Paulo |
| `celula` | `LATITUDE`, `LONGITUDE` | célula H3 resolução 9 (~0,1 km²); a coordenada é descartada depois disso |

Perímetro: retângulo de 5 × 5 km em torno da FIAP Paulista (lat −23,58706 a −23,54214; lon −46,67671 a −46,62769).

## Privacidade
- `processed/usadas.parquet` guarda só `rubrica, data_fato, mes, hora, faixa, celula`: **sem latitude, longitude, número de BO ou delegacia** (testado em `tests/test_schema_processed.py`).
- Snapshot, fixture e resultados têm só agregados por célula H3 × faixa; os testes conferem que não há identificador de BO (`tests/test_snapshot.py`, `tests/test_quarentena.py`).
- O backtest publica somente métricas agregadas por modelo, sem H3, faixa, rótulo ou contagem por chave.
- **Supressão aplicada no contrato v2:** chaves com 1–2 registros são publicadas como `sem_dado`, com `n_registros=0` e pontuação/nível vazios. As 218 chaves suprimidas não são identificadas; o manifesto contém apenas os totais agregados (218 chaves, 306 registros). As 954 chaves `com_dado` têm pelo menos três registros.
- O histórico publicável será reescrito antes de qualquer push; até essa etapa terminar, a branch não deve ser enviada.
- `interim/`, `processed/`, `quarantine/`, `features/` e `/mlflow/` estão no `.gitignore`.

### Inventário por camada

| Camada | Conteúdo | Acesso atual | Retenção e descarte |
|---|---|---|---|
| `raw/` local | XLSX público original, com todos os campos da SSP-SP | somente no computador do responsável pelo ML; fora do Git | manter até a entrega e a conferência dos hashes; descarte local após o encerramento acadêmico, mediante confirmação humana |
| `interim/` local | cópia fiel em Parquet, ainda com identificadores e coordenadas do raw | mesmo acesso do raw; fora do Git | mesma retenção do raw; descarte junto com o raw |
| `quarantine/` local | fonte, linha, rubrica e motivo; sem BO, delegacia ou coordenada | responsável pelo ML; fora do Git | manter até fechar a reconciliação da entrega; depois descartar mediante confirmação humana |
| `processed/` e `features/` locais | rubrica, data, hora, H3 e atributos derivados por registro/chave | responsável pelo ML; fora do Git | manter até reproduzir a entrega; depois descartar mediante confirmação humana |
| `snapshot/` versionado | agregados H3 × faixa com supressão k ≥ 3, manifesto, hash e fixture | equipe e avaliadores do repositório | conservar com a entrega; o contrato v2 não publica chaves com contagem 1–2 |
| `resultados/`, notebook e MLflow | métricas agregadas; backtest sem contagem por chave; notebook sem identificadores; banco MLflow local fora do Git | resultados/notebook: equipe e avaliadores; MLflow: responsável pelo ML | resultados/notebook acompanham a entrega; MLflow local pode ser descartado depois da conferência, mediante confirmação humana |
| `prompts.md` e revisões | resumo de decisões e saídas de revisão, sem conteúdo do raw | equipe e avaliadores do repositório | conservar como evidência da rubrica |
| logs e saídas de terminal | o projeto não cria arquivo de log próprio; saídas ficam no terminal, salvo redirecionamento manual. Diagnósticos persistentes permitidos são apenas os arquivos inventariados acima | responsável pela execução; não versionar logs ad hoc | não conservar logs ad hoc; se houver redirecionamento manual, revisar e descartar após registrar apenas o resultado necessário, mediante confirmação humana |

Nenhum descarte é executado automaticamente por este projeto. As ações de descarte dependem de confirmação humana e devem ser registradas.

## Natureza do dado
Mapa histórico **observado** de jan–set/2026, não previsão. Melhor dado disponível no período: não indica tempo real nem local seguro.
