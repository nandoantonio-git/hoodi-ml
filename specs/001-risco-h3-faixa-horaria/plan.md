# Implementation Plan: Nível de risco registrado por célula H3 e faixa horária

**Branch**: `001-risco-h3-faixa-horaria` (repositório sem git; só o identificador da feature) | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-risco-h3-faixa-horaria/spec.md` (com as 5 decisões da sessão de clarificação de 2026-11-11). Números medidos: [research.md](research.md).

## Summary

Pipeline em Python que lê o XLSX oficial da SSP-SP, classifica cada linha em `usada`, `quarentena`, `duplicata_removida` ou `fora_da_janela`, atribui os registros usados a uma célula H3 res. 9 e a uma de 5 faixas horárias, calcula o nível de risco 0–3 por quartis com cortes só do treino, treina e avalia modelos com origens temporais móveis (features só do passado) e gera um snapshot versionado com checksum, mais fixture, para o app do Abner. A entrega inclui notebook executado, relatório de 2 a 4 páginas e revisão red-team real.

## Technical Context

**Language/Version**: Python 3.11.15 (`.venv311`). O `.venv` 3.9.6 sai de uso. (research D-01)

**Primary Dependencies**: já instaladas no `.venv311`: h3 4.5.0, numpy 2.4.6, pandas 3.1.1, scikit-learn 1.9.1, xgboost 3.2.0, pytest 9.2.0, duckdb 2.0.0, pyarrow 26, nbconvert, nbformat, ipykernel. Falta congelar `requirements.txt`.

**OpenMP**: o `libomp` foi instalado com Homebrew em 2026-11-11 (autorizado pelo Nando); o XGBoost 3.2.0 importa e treina no `.venv311`.

**Storage**: arquivos: `ml/dados/raw/` (imutável), `interim/` (parquet, fora do git), `processed/`, `quarantine/`, `features/`, `snapshot/` (CSV, `.sha256`, `manifest.json`, fixture).

**Testing**: pytest, com os testes antes do código: reconciliação, deduplicação, idempotência, "sem dado", split temporal, cortes só do treino, snapshot.

**Target Platform**: macOS arm64, local.

**Project Type**: pipeline de ML em lote com notebook e relatório.

**Performance Goals**: reexecução completa em minutos. O XLSX (140 MB) é lido uma vez e convertido em parquet.

**Constraints**: só dado oficial; nada de "tempo real" nem "rota segura"; nenhum campo que identifique pessoa nos derivados e entregas (constituição VII, v1.2.0); Codex CLI real antes da entrega; congelamento 16/11; entrega 19/11 23h55.

**Scale/Scope** (medido, research): 814.900 linhas na base; 20.657 válidas no perímetro; 20.350 na janela jan–set; 258 células e 952 chaves com registro; treino 15.919 e teste 4.431 registros. Mediana de 9 registros por chave no treino e de 3 no teste.

## Constitution Check

*GATE: passa antes da Fase 0 e foi reavaliado após a Fase 1.*

| Princípio | Atendimento no plano | Status |
|---|---|---|
| I. Só dado real e oficial | o pipeline lê só o dado real; entradas mínimas escritas à mão existem apenas em testes unitários, sem alimentar nenhum resultado (exceção explícita na constituição v1.1.0 e mantida na v1.2.0); fonte, arquivo e sha256 em `CHECKSUM.txt`; a fixture é gerada do dado real, nunca à mão; o exemplo do contrato está marcado como ilustrativo | OK |
| II. Linguagem honesta | `manifest.json` leva o aviso "melhor dado disponível no período"; relatório e README revisados contra a lista de termos proibidos | OK |
| III. "Sem dado" não é 0 | `status = sem_dado` com `nivel` vazio no contrato; `tests/test_sem_dado.py` | OK |
| IV. Risco vem do crime | pontuação só de registros de crime; linha = crime; rubricas sem peso fora e contadas | OK |
| V. Controle de vazamento temporal | origens móveis T1–T4 e teste; features só do passado; cortes só do treino; CV por origem; `test_split_temporal.py` e `test_cortes_treino.py`; escopo: separação por data do fato, features e ajuste dentro das dobras; disponibilidade histórica não reconstruída | PLANEJADO (evidência após T021–T026) |
| VI. Quarentena e idempotência | destino exclusivo por linha com reconciliação exata; CSV sem timestamp; hash idêntico em duas execuções | OK |
| VII. Privacidade e confirmação | derivados e entregas sem campo identificador; `bo_id` só em memória; inventário por camada (T030) e teste dos schemas dos parquets derivados; tarefas `[Nando]` param para confirmação; red-team real via Codex CLI | PLANEJADO (testes de ausência de `bo_id` existem; inventário e teste de schemas pendentes) |

Resultado: sem violações no planejamento. Estados distintos: PLANEJADO (V, VII), não implementado nem verificado; nenhum gate está executado ou aprovado. A seção de complexidade fica vazia.

## Design de modelagem (resumo; detalhes em research D-03 a D-06)

- **Exemplos de treino**: origens móveis com janela de rótulo de 2 meses (T1 a T4), igual à janela do teste (ago–set). Features em taxa mensal (por hora da faixa, quando for pontuação), para janelas de tamanhos diferentes.
- **Rótulo**: nível 0–3 por quartis; os três cortes saem do conjunto de rótulos de treino e valem para o teste.
- **Validação cruzada**: por origem com expurgo (dobras T1→T3 e T1–T2→T4; rótulos que se sobrepõem não entram juntos), nunca embaralhada, só no treino.
- **Linhas de base**: classe mais frequente e persistência.
- **Candidatos planejados (T025 ainda aberto)**: Random Forest, XGBoost e MLP, com ≥10 combinações de 3 hiperparâmetros cada. LSTM e KMeans+PCA: justificados e declarados como não executados.
- **Métricas**: macro-F1, balanced accuracy e erro absoluto médio de nível; treino e teste lado a lado.

## Project Structure

### Documentation (this feature)

```text
specs/001-risco-h3-faixa-horaria/
├── spec.md
├── plan.md              # este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   └── snapshot-risco.md   # Fase 1: contrato com o Abner
├── tasks.md             # /speckit-tasks
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
scripts/            # 00 conversão XLSX→parquet, 01 qualidade (já existem)
ml/
├── ingestao.py     # destino por linha: usada, quarentena, duplicata, fora da janela
├── rotulo.py       # pesos, pontuação mensal, cortes de quartil do treino, níveis 0–3, "sem dado"
├── features.py     # origens T1–T4 e teste; taxas mensais só do passado
├── modelos.py      # linhas de base e candidatos; busca ≥10 combinações; CV por origem
├── snapshot.py     # snapshot, manifest, checksum, fixture
├── config.py       # constantes: bbox, pesos, origens, sementes
└── dados/          # README, raw, interim, processed, quarantine, features, snapshot, resultados/, reconciliacao.txt
tests/              # pytest
notebooks/          # notebook executado
RELATORIO_ML.md, README.md, requirements.txt, prompts.md
```

**Structure Decision**: projeto único, separado da API .NET do Abner. O contrato com o app é só o que está em `contracts/snapshot-risco.md`.

## Riscos e decisões pendentes

- **Dado ralo no teste**: mediana e chaves com 1 só registro lidas de `resultados/` (valores da exploração inicial, sob outra fórmula, não são referência operacional); o relatório declara a incerteza e usa métricas adequadas. Cortes do treino deixam o teste desbalanceado (nível 0 com 347 de 738 chaves; nível 3 com 23). Exploração sob a fórmula anterior (soma sem normalização); será substituída pela saída final rastreável.
- **Rubricas sem peso**: 56 registros na janela (0,3%) ficam fora da pontuação e são contados no relatório. Feminicídio (3) entra com peso 5, por decisão do Nando.
- **LSTM e KMeans+PCA**: decisão de não executar; confirmar que a rubrica do briefing aceita a justificativa.
- **Setembro possivelmente incompleto** (~73 mil contra ~85 mil por mês na base; menor volume não demonstra incompletude, hipótese a confirmar com evidência de cobertura): declarado; pode enviesar o teste.
- **Coordenada exata da FIAP**: pendente, impacto de ~50 m.
- **Formato do contrato com o Abner**: CSV + JSON proposto; precisa da confirmação dele (prazo 11/11 12h).

## Complexity Tracking

Sem violações da constituição; nada a justificar.
