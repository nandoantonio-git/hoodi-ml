# Tasks: Nível de risco registrado por célula H3 e faixa horária

**Input**: `specs/001-risco-h3-faixa-horaria/` (plan.md, spec.md, research.md, data-model.md, contracts/snapshot-risco.md, quickstart.md)

**Prerequisites**: plan.md e spec.md (com a sessão de clarificação de 2026-11-11), constituição v1.2.0.

**Tests**: pedidos pela constituição (Princípios V e VI) e pelos critérios SC-001 a SC-005. Cada história começa pelos testes, que devem falhar antes da implementação. Dado sintético só aparece nesses testes unitários, em entradas mínimas escritas na hora; o pipeline só lê o dado real (Princípio I).

**Organization**: por história de usuário. US2 vem antes de US1 na ordem de execução porque o snapshot depende da ingestão; as duas são P1.

## Format: `- [ ] [ID] [P?] [Story] Descrição com caminho`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente).
- **[Story]**: US1 contrato de risco, US2 qualidade e quarentena, US3 modelo com controle de vazamento temporal, US4 entrega auditável.
- **[Nando]**: precisa de decisão ou confirmação dele antes de seguir. Nunca executar sozinho.
- Interpretador de todos os comandos: `.venv311/bin/python` (Python 3.11.15).

## Phase 1: Setup

- [X] T001 Congelar as versões exatas do `.venv311` em `requirements.txt` com `uv pip freeze --python .venv311/bin/python` (h3 4.5.0, numpy 2.4.6, pandas 3.1.1, scikit-learn 1.9.1, xgboost 3.2.0, pytest 9.2.0, duckdb 2.0.0, pyarrow 26.0.1, nbconvert 7.17.2, nbformat 5.11.1, ipykernel 7.4.0); registrar em `requirements.txt` um comentário de que o XGBoost exige `libomp` (`brew install libomp`)
- [X] T002 [P] Criar a estrutura do plano: `ml/__init__.py`, `tests/__init__.py`, `notebooks/` e as pastas `ml/dados/processed/`, `ml/dados/quarantine/`, `ml/dados/features/`, `ml/dados/snapshot/`, `ml/dados/resultados/`; acrescentar ao `.gitignore` o que for gerado e grande (`ml/dados/processed/`, `ml/dados/features/`) e manter `raw/CHECKSUM.txt` e `snapshot/` versionados
- [ ] T003 [P] [Nando] Confirmar com ele e rodar `git init` na raiz de `<repo>` (rubrica A1: repositório Python separado); sem remoto e sem push
- [X] T004 [P] Criar `tests/conftest.py` com fixtures de entradas mínimas escritas na hora (poucas linhas no formato do parquet: `NUM_BO`, `ANO_BO`, `NOME_DELEGACIA`, `RUBRICA`, `LATITUDE`, `LONGITUDE`, `HORA_OCORRENCIA_BO`, `DATA_OCORRENCIA_BO`, tudo como texto)

## Phase 2: Foundational (bloqueia todas as histórias)

- [X] T005 Antes de rodar qualquer script, conferir `shasum -a 256 ~/Downloads/SPDadosCriminais_2026.xlsx` contra `ml/dados/raw/CHECKSUM.txt` (f627d84e…acbaf); o `scripts/00_xlsx_para_parquet.py` agora nunca sobrescreve o `CHECKSUM.txt` e aborta se o hash divergir. Em seguida rodar os scripts 00 e 01 no `.venv311` e conferir que reproduzem `ml/dados/qualidade_etapa1.txt` (814.900 linhas; 20.657 com coordenada e hora no perímetro); se divergir, parar e reportar antes de seguir **Fechado em 2026-11-11:** hash do XLSX local = hash do arquivo baixado de novo da SSP-SP (f627d84e…acbaf, 139.931.418 bytes); script 00 reexecutado (555.404 + 259.496 linhas), parquets com conteúdo tabular idêntico aos anteriores (EXCEPT ALL = 0 nos dois sentidos; arquivos binariamente diferentes; comandos, versões e saídas em `ml/dados/raw/PROVENIENCIA.md`; a ordem das linhas não é provada, então `linha` só vale com a origem estável do parquet gravado), snapshot regenerado com o mesmo hash. A SSP não publica hash oficial: a verificação prova que o arquivo local é o que o servidor serve hoje, não a data original.
- [X] T006 [P] Criar `ml/config.py` com as constantes do plano: bbox (lat -23,58706 a -23,54214; lon -46,67671 a -46,62769), H3 resolução 9, 5 faixas por bordas explícitas [0,6), [6,12), [12,18), [18,21), [21,24), janela de fato 2026-01-01 a 2026-09-30 (serial Excel 46023 = 2026-01-01), origens T1 a T4 e Teste (research D-03), tabela de pesos (furto 1; tráfico, drogas para consumo e lesão corporal culposa no trânsito 1; roubo e lesão corporal 3; homicídio, feminicídio e estupro 5; ilícito extrapenal e rubrica não listada sem peso), sementes fixas e caminhos

**Checkpoint**: ambiente e dado conferem; constantes num só lugar.

## Phase 3: US2 — Qualidade e quarentena dos dados (P1)

**Goal**: cada linha da base recebe exatamente um destino, e a reconciliação fecha.

**Independent Test**: `entrada = usada + quarentena + duplicata_removida + fora_da_janela`, sem diferença (SC-002).

### Testes primeiro
- [X] T007 [P] [US2] `tests/test_dedup.py`: só a linha idêntica de mesmo BO e rubrica vira `duplicata_removida`; BO com vários crimes mantém uma linha por crime (FR-005)
- [X] T008 [P] [US2] `tests/test_quarentena.py`: motivos `sem_coordenada`, `sem_hora`, `bo_conflito_coordenada`, `bo_conflito_hora` vão para `quarentena` sinalizados e não são descartados; hora válida só em [0,1); coordenada válida só numérica, ≠ 0 e dentro do retângulo de SP; reconciliação exata (FR-004)
- [X] T009 [P] [US2] `tests/test_janela.py`: fato fora de jan–set 2026 vira `fora_da_janela` com motivo; coordenada válida fora do perímetro vira `fora_da_janela` com motivo `fora_do_perimetro`; o split usa a data do fato (FR-009)

### Implementação
- [X] T010 [US2] `ml/ingestao.py`: ler os parquets com duckdb, converter data (serial Excel) e hora, calcular `faixa` (bordas explícitas) e `celula` (`h3.latlng_to_cell(lat, lon, 9)`), atribuir `destino` exclusivo (`usada`, `quarentena`, `duplicata_removida`, `fora_da_janela`) e `motivo` conforme [data-model.md](data-model.md); manter em `processed/` só as colunas necessárias (sem `bo_id`, `NUM_BO` nem outro identificador de BO; o `bo_id` existe só em memória durante a deduplicação e nunca é gravado; quarentena sem coordenada) e gravar `ml/dados/processed/` e `ml/dados/quarantine/` (FR-013)
- [X] T011 [US2] Executar a ingestão no dado real, gravar `ml/dados/reconciliacao.txt` com a contagem por destino e o "% de dado utilizável", e conferir a reconciliação exata; comparar com [research.md](research.md) (20.350 registros na janela) e explicar qualquer diferença pela quarentena de BOs conflitantes

**Checkpoint**: US2 completa e testável sozinha.

## Phase 4: US1 — Contrato de risco para o app (P1)

**Goal**: snapshot versionado com checksum e fixture para o Abner, com nível 0–3 ou "sem dado".

**Independent Test**: gerar o snapshot duas vezes e conferir hash idêntico, invariantes do contrato e nenhum `sem_dado` com nível (SC-001, SC-004).

### Testes primeiro
- [X] T012 [P] [US1] `tests/test_sem_dado.py`: `nivel` só assume 0, 1, 2 ou 3; chave `sem_dado` tem `nivel` vazio e nunca 0; chave sem registro na janela é `sem_dado`
- [X] T013 [P] [US1] `tests/test_cortes_treino.py`: os 3 cortes de quartil saem só dos rótulos de treino (T1 a T4, em taxa mensal) e são reaplicados ao teste sem recalcular (FR-006)
- [X] T014 [P] [US1] `tests/test_snapshot.py`: invariantes de [contracts/snapshot-risco.md](contracts/snapshot-risco.md): cada par (`h3_cell`, `faixa`) único; todas as células que cobrem o perímetro × 5 faixas presentes; ordenação por `h3_cell` e `faixa`; cabeçalho e colunas exatos; `.sha256` igual ao hash do CSV; nenhuma coluna do CSV, do manifest ou da fixture carrega identificador de BO ou dado pessoal (FR-013)
- [X] T015 [P] [US1] `tests/test_idempotencia.py`: duas execuções sobre o mesmo raw geram CSV com hash idêntico (SC-001)

### Implementação
- [X] T016 [US1] `ml/rotulo.py`: pontuação mensal por chave (soma de pesos de `ml/config.py` dividida pelo número de meses da janela e pelas horas da faixa: 6, 6, 6, 3, 3); rubricas sem peso fora da pontuação e contadas em `ml/dados/resultados/rubricas_sem_peso.csv`; 3 cortes de quartil dos rótulos de treino; níveis 0–3; contar em `resultados/` as chaves com features e sem registro no rótulo (viés de seleção); nos universos internos, preservar o protocolo original; no snapshot público v2, publicar chaves com 0–2 registros como `sem_dado`, contagem 0 e sem nível/pontuação; nível publicado = soma de pesos de jan–set ÷ 9 meses ÷ horas da faixa (6, 6, 6, 3, 3), aplicada aos cortes do treino; teste numérico: 54 pontos em 9 meses = 1,0/mês/hora numa faixa de 6 h e 2,0 numa de 3 h
- [X] T017 [US1] [Nando] Mostrar a distribuição real dos níveis (treino, teste e snapshot) e os 3 cortes, e esperar a aprovação dele antes de gerar o snapshot (FR-008); registrar no resultado o hash do manifest e a configuração (pesos, cortes, janela) aprovados
- [X] T018 [US1] `ml/snapshot.py`: gerar `ml/dados/snapshot/risco_h3_faixa_v2.csv`, `.sha256`, `manifest.json` (campos do contrato, incluindo supressão k ≥ 3, fuso, faixas, resolução, centro e tamanho do perímetro, total de linhas e fórmula; CSV sem `nivel_previsto`, com o aviso "melhor dado disponível no período") e `fixture_v2.json`, tudo a partir do dado real e sem timestamp dentro do CSV
- [X] T019 [US1] Rodar o snapshot duas vezes, conferir hash idêntico, os 4 invariantes do contrato e que `SHA256(CSV)` = conteúdo do `.sha256` = `manifest.csv_sha256`; o hash dos bytes do `manifest.json` aprovado no T017 é registrado à parte, porque `gerado_em` muda a cada geração
- [ ] T020a [US1] [Nando] Até 11/11 12h: enviar ao Abner só o contrato (chave de risco, janela, colunas, 5 faixas, `sem_dado` explícito, formato CSV + JSON, o rascunho de [contracts/snapshot-risco.md](contracts/snapshot-risco.md)) e perguntar o que cada prazo exige; só depois da aprovação dele. Pode rodar antes de T017
- [ ] T020b [US1] [Nando] Enviar o caminho de entrega (CSV v2, `.sha256`, `manifest.json`, `fixture_v2.json` versionados e a instrução de como o app os lê; "rota" aqui não é rota de navegação) e a fixture real (de T018) depois de T019; aceite = o Abner confirma que lê a fixture; não enviar sem a confirmação dele

**Checkpoint**: US1 e US2 completas. **MVP = Phase 1 a 4** (até T020b), que cobre o contrato de hoje.

## Phase 5: US3 — Modelo avaliado com controle de vazamento temporal (P2)

**Goal**: modelo escolhido com justificativa, contra linhas de base, com treino e teste lado a lado.

**Independent Test**: nenhum registro de ago–set entra nas features de teste, as datas das features são estritamente anteriores ao início do rótulo e as transformações são ajustadas só no treino da dobra (SC-003, T021) e todo número do relatório vem de execução.

### Testes primeiro
- [x] T021 [P] [US3] `tests/test_split_temporal.py`: para T1 a T4 e Teste, `data_feature < inicio_rotulo` (estritamente anterior); transformações ajustadas só no treino da dobra; features passadas invariantes a alterações dos registros futuros; na CV com expurgo, nenhuma origem de treino tem rótulo que toque o mês do rótulo validado; o rótulo de teste vem só de ago–set; nenhuma data de teste anterior à última de treino (SC-003, FR-009)
- [x] T022 [P] [US3] `tests/test_features_taxas.py`: taxas mensais iguais para janelas de tamanhos diferentes com a mesma intensidade; chave sem registro na janela de features fica fora do classificador

### Implementação
- [x] T023 [US3] `ml/features.py`: construir X por origem T1 a T4 e Teste (research D-03) com: taxa mensal de registros e de pontuação da chave; taxa mensal por grupo de rubrica (furto, roubo, lesão corporal, crimes graves, drogas); taxas das 5 faixas da mesma célula; taxa média das células vizinhas (`h3.grid_disk(celula, 1)`) na mesma faixa; gravar em `ml/dados/features/`
- [x] T024 [US3] `ml/modelos.py`: linhas de base (classe mais frequente; persistência, que usa o nível da chave na janela de features) e as métricas macro-F1, balanced accuracy e erro absoluto médio de nível
- [x] T025 [US3] Em `ml/modelos.py`: candidatos Random Forest, XGBoost e MLP, cada um com busca de ao menos 10 combinações de 3 hiperparâmetros e validação cruzada por origem com expurgo (dobras T1→T3 e T1–T2→T4; cortes de quartil recalculados só com o treino da dobra), nunca embaralhada, só no treino; sementes de `ml/config.py`
- [x] T026 [US3] Antes de consultar ago–set, gravar em `ml/dados/resultados/selecao_modelo.json` a regra de seleção, o vencedor, a configuração e as métricas de CV por origem (somente CV); depois treinar o melhor de cada candidato em T1–T4, avaliar no Teste e gravar em `ml/dados/resultados/` as métricas de treino e de teste lado a lado, a análise de overfitting (diferença treino × teste) e o desbalanceamento declarado; qualquer mudança de modelo depois de ver ago–set consta como exploração adicional, nunca como a escolha
- [ ] T027 [US3] [Nando] Apresentar a escolha do modelo com a justificativa e a declaração de que LSTM e KMeans+PCA não foram executados (research D-06); ele decide se a rubrica do briefing aceita isso ou se algum deles deve ser rodado
- [ ] T028 [US3] Com o modelo aprovado, gravar o backtest de ago–set em `ml/dados/resultados/backtest_ago_set.csv`, fora do arquivo do app; reexecutar `tests/test_snapshot.py` e `tests/test_idempotencia.py`

**Checkpoint**: US3 completa.

## Phase 6: US4 — Entrega auditável (P2)

**Goal**: repositório, notebook executado, relatório e prompts, com red-team real antes da entrega final; cada envio intermediário (T020a/T020b: contrato e fixture ao Abner) é coberto apenas pela rodada vigente do próprio artefato e versão enviados (o contrato pela rodada da spec; a fixture só após revisão própria, ou, não havendo, pela confirmação humana), e todo envio, sempre com a confirmação do Nando.

**Independent Test**: lista A1 a A6 de `docs/SPEC-ML.md` §7 conferida e relatório real do Codex CLI anexado.

- [ ] T029 [US4] `notebooks/hoodi_ml.ipynb` cobrindo ingestão, rótulo, features, modelos e snapshot; executar com `.venv311/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/hoodi_ml.ipynb` e manter as saídas gravadas (A1)
- [ ] T030 [P] [US4] `ml/dados/README.md`: fonte oficial SSP-SP, nome do arquivo, sha256, descrição dos campos, destinos e quarentena, janela de dados, perímetro e a reconciliação de T011 (A2); inventário de privacidade por camada (conteúdo, acesso, retenção e descarte, incluindo logs, notebook e prompts) e teste `tests/test_schemas_derivados.py` que lê os parquets derivados reais e falha se houver `bo_id`, `NUM_BO`, endereço, bairro, delegacia, `lat`, `lon`, `latitude` ou `longitude` em `processed/` (inventariar e regenerar `usadas.parquet`, que hoje contém `lat` e `lon`); sensibilidade do centro do perímetro (deslocar ±100 m e contar as células cujo nível muda)
- [ ] T031 [P] [US4] Atualizar `prompts.md` com uma entrada datada por sessão de trabalho (A5), resumindo o prompt e o uso do resultado
- [ ] T032 [P] [US4] [Nando] `README.md` com a Ficha da CitizenTech e os ODS (A4): pedir a ele o conteúdo da Ficha e dos ODS já em 2026-11-12, sem esperar o final, que não estão em nenhum arquivo do projeto, e não inventar
- [ ] T033 [US4] `RELATORIO_ML.md` de 2 a 4 páginas, só com números das saídas do notebook, incluindo o limite do dado ("% de dado utilizável", possível incompletude de setembro (hipótese; afirmar só com evidência de cobertura), pesos como ponto de partida, rubricas sem peso, desbalanceamento, chaves de teste com 1 só registro (contagem lida de `resultados/`, sem número fixo), chaves excluídas por falta de rótulo e o viés de seleção) (A3). Redação obrigatória: o snapshot é "mapa histórico observado + experimento retrospectivo", nunca previsão; o backtest é retrospectivo e não afirma "ausência de vazamento"; ago–set é avaliação exploratória (visto no T017); sensibilidade aos pesos (todos iguais a 1; 1/2/3) reportada sem escolher pesos por ago–set; "risco" descrito como intensidade registrada; proveniência do raw declarada com o que foi e o que não foi verificado
- [ ] T034 [US4] Varrer `README.md`, `RELATORIO_ML.md`, `ml/dados/README.md` e o `manifest.json` por "tempo real", "rota segura" e "local seguro" fora de negação; corrigir o que achar (Princípio II)
- [ ] T035 [US4] [Nando] Avisá-lo e só então rodar a revisão red-team real com o Codex CLI sobre o repositório já pronto (T029 a T034 concluídas); anexar o relatório do Codex e registrar achados e correções (A6)
- [ ] T036 [US4] Para cada achado do red-team do diff, registrar disposição individual (corrigido, recusado com motivo ou adiado por decisão do Nando) e a evidência; aplicar as correções, reexecutar `pytest` e o notebook e revalidar os artefatos finais (hashes, snapshot, relatório)

**Checkpoint**: US4 completa.

## Phase 7: Polish e entrega

- [ ] T037 Rodar `.venv311/bin/python -m pytest -q` completo e os 9 cenários de [quickstart.md](quickstart.md); registrar o resultado
- [ ] T038 [P] Atualizar `checklists/requirements.md` e conferir A1 a A6 de `docs/SPEC-ML.md` §7 contra os arquivos reais; refazer o `shasum -a 256` do XLSX contra `raw/CHECKSUM.txt` (raw imutável, FR-002); confirmar que snapshot e fixture não têm identificador de BO; reportar o que falta
- [ ] T039 [Nando] Congelamento em 2026-11-16 e entrega em 2026-11-19 às 23h55; nada é enviado ou publicado sem a confirmação dele (Princípio VII)

## Dependências

- **Fases**: Setup → Foundational → US2 → US1 → US3 → US4 → Polish. US1 depende de US2 (usa `processed/`).
- **Dentro de cada história**: testes primeiro (devem falhar), depois implementação.
- **Pontos de parada humana**: T003, T017, T020a, T020b, T027, T032, T035, T039. T017 precede T018. T020a pode vir antes de T017; T020b só depois de T019. T028 só depois de T027. T035 só depois de T029 a T034.
- **Prazos**: T020a venceu em 2026-11-11 às 12h (contrato) e T020b às 20h (caminho e fixture); não há confirmação de envio, então ficam abertos até o Nando confirmar.
- **Replanejamento (2026-11-12)**: T021–T027 até 14/11; T028–T034 até 15/11; 16/11 congelamento e red-team do diff (T035); 17–18/11 correções (T036), reexecução e checklist; 19/11 gate humano e entrega até 23h55. Se T026 passar de 14/11, corta-se primeiro o que for opcional do notebook, nunca a reexecução.

## Execução em paralelo

- Setup: T002, T003 e T004 juntas.
- US2: T007, T008 e T009 juntas.
- US1: T012, T013, T014 e T015 juntas.
- US3: T021 e T022 juntas.
- US4: T030, T031 e T032 juntas.

## Estratégia de implementação

1. **MVP primeiro**: Phase 1 a 4 (T001 a T020b) entrega o contrato com o Abner, que é o prazo de hoje.
2. **Incremental**: Phase 5 (modelo) e Phase 6 (entrega) depois, sem alterar o formato já combinado com o Abner, (o backtest de T028 fica fora do arquivo do app).
3. **Parar nos pontos [Nando]**: nenhuma tarefa marcada executa sem a decisão dele.
