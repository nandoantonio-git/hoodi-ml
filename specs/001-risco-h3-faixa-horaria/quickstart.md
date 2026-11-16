# Quickstart (validação): Nível de risco registrado por célula H3 e faixa horária

**Spec**: [spec.md](spec.md) · **Contrato**: [contracts/snapshot-risco.md](contracts/snapshot-risco.md) · **Modelo de dados**: [data-model.md](data-model.md)

Guia para provar que a feature funciona de ponta a ponta. Não contém código de implementação. Todos os comandos rodam na raiz do repositório.

## Pré-requisitos

- Python 3.11 no `.venv311` com as bibliotecas de `requirements.txt` (h3, numpy, pandas, scikit-learn, pytest, duckdb, pyarrow, nbconvert; XGBoost depende de `libomp`, ver [research.md](research.md) D-01).
- XLSX original em `~/Downloads/SPDadosCriminais_2026.xlsx`, com o sha256 igual ao de `ml/dados/raw/CHECKSUM.txt`.

## Cenários

### 1. Ambiente e dado conferem (US2, FR-001)
```bash
.venv311/bin/python -m pytest -q
shasum -a 256 ~/Downloads/SPDadosCriminais_2026.xlsx
```
**Esperado**: o hash é `f627d84e…acbaf` (o de `CHECKSUM.txt`) e os testes de ambiente passam.

### 2. Qualidade reproduz as contagens (T004)
Confira o hash do cenário 1 antes: o script 00 não sobrescreve o `CHECKSUM.txt` e aborta se o hash divergir. Saídas extras: `ml/dados/reconciliacao.txt` e `ml/dados/resultados/`.
```bash
.venv311/bin/python scripts/00_xlsx_para_parquet.py
.venv311/bin/python scripts/01_qualidade_dado.py
```
**Esperado**: 814.900 linhas na base, 20.657 com coordenada e hora no perímetro, iguais a `ml/dados/qualidade_etapa1.txt`.

### 3. Reconciliação e quarentena (US2, SC-002)
```bash
.venv311/bin/python -m pytest -q tests/test_quarentena.py tests/test_dedup.py
```
**Esperado**: entrada = usadas + quarentena + duplicata removida + fora da janela, sem diferença. Linhas sem hora, sem coordenada ou com BO conflitante estão na quarentena com o motivo.

### 4. Idempotência (US1, SC-001)
```bash
.venv311/bin/python -m ml.gerar_snapshot
shasum -a 256 ml/dados/snapshot/risco_h3_faixa_v2.csv
.venv311/bin/python -m ml.gerar_snapshot
shasum -a 256 ml/dados/snapshot/risco_h3_faixa_v2.csv
```
**Esperado**: os dois hashes são idênticos e batem com `manifest.json`.

### 5. "Sem dado" nunca vira 0 (SC-004)
```bash
.venv311/bin/python -m pytest -q tests/test_sem_dado.py
```
**Esperado**: nenhuma linha `sem_dado` com `nivel` preenchido; todo `nivel` é 0, 1, 2 ou 3.

### 6. Sem vazamento (US3, SC-003)
```bash
.venv311/bin/python -m pytest -q tests/test_split_temporal.py tests/test_cortes_treino.py
```
**Esperado**: nenhum registro de ago–set entra em features de teste; cortes dos quartis calculados só com o treino.

### 7. Distribuição dos níveis antes do rótulo (FR-008, T011)
Executar a etapa de rótulo e conferir a tabela de níveis por conjunto. **Esperado**: tabela com níveis 0 a 3 no treino e no teste, mostrada ao Nando antes de gerar o snapshot.

### 8. Modelo e relatório (US3, SC-005)
Executar `notebooks/hoodi_ml_documentado.ipynb` com `nbconvert --execute`. **Esperado**: baseline e candidatos, ≥10 combinações de 3 hiperparâmetros por candidato, métricas de treino e teste lado a lado, calibração, estratos e discussão de overfitting; todo número do `RELATORIO_ML.md` aparece nas saídas do notebook.

### 9. Entrega (US4, SC-006)
Conferir a lista A1 a A6 de `docs/SPEC-ML.md` §7. **Esperado**: repositório, `ml/dados/README.md`, `requirements.txt`, snapshot com checksum, `RELATORIO_ML.md` de 2 a 4 páginas, README com Ficha e ODS, `prompts.md` contínuo e o relatório real do Codex CLI anexado.
