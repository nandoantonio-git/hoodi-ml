# Plano de execução do ML — hoodi (2026-11-15 → congelamento 16/11)

Tudo neste computador, no `.venv311`. Nada é publicado ou enviado sem o Nando confirmar.

## Regra que vale para os modelos novos
A seleção pré-registrada (`resultados/selecao_modelo.json`, Random Forest) foi gravada antes de ver ago–set,
mas ago–set já foi visto em 15/11. Pela spec (T026), LSTM e KMeans+PCA entram com o MESMO protocolo
(mesmas dobras com expurgo, ≥10 combinações de 3 hiperparâmetros, mesmas métricas), mas constam como
**exploração adicional**: se um deles ganhar, o relatório diz isso, sem trocar a escolha retroativamente.

## Fase 1 — Ambiente (10 min) ✔ 15/11
- Instalar `torch` e `matplotlib` no `.venv311` (uv); atualizar `requirements.txt`; atualizar research D-01 e D-06 e FR-010.

## Fase 2 — LSTM (T025b) ✔ 15/11
- `ml/sequenciais.py` (série + LSTM + KMeans+PCA): por chave, série mensal dos meses de features (pontuação da chave, registros, 5 grupos, vizinhas, 5 faixas da célula) — T1 tem 2 passos, Teste 7; cada origem é um lote próprio (sem preenchimento).
- LSTM (PyTorch) + camada final de 4 classes, perda com peso balanceado, semente fixa.
- Busca: hidden_size {16, 32, 64} × learning_rate {1e-3, 1e-2} × dropout {0, 0,3} = 12 combinações, épocas fixas (60). Nota técnica: `OMP_NUM_THREADS=1` e torch importado antes do xgboost (duas libomp no macOS derrubavam o processo), mesmas dobras T1→T3 e T1–T2→T4.
- Testes: série nunca contém mês ≥ início do rótulo; mesma semente → mesma previsão.

## Fase 3 — KMeans + PCA (T025c) ✔ 15/11
- Padronização → PCA → KMeans. O nível sai do cluster: cada cluster recebe o nível mais frequente dos exemplos de treino que caem nele (mapa ajustado só no treino da dobra).
- Busca: n_components {2, 4, 8} × n_clusters {4, 8, 16} × whiten {False, True} = 18 combinações.
- Saída extra: perfil dos clusters (o que caracteriza cada grupo de células) para a conclusão ao cidadão.

## Fase 4 — Resultados e backtest (T026–T028, ~45 min)
- `metricas_treino_teste.csv` com os 5 modelos + 2 linhas de base lado a lado, gap de overfitting, matrizes de confusão.
- Escolha: Random Forest (regra pré-registrada) salvo decisão contrária do Nando; LSTM/KMeans como exploração.
- `backtest_ago_set.csv` fora do arquivo do app; reexecutar testes de snapshot e idempotência.

## Fase 5 — Notebook executado (T029, ~1h30)
- `notebooks/hoodi_ml.ipynb`: ingestão → rótulo → features → 5 modelos → resultados → snapshot, com gráficos
  (distribuição dos níveis, macro-F1 por modelo treino×teste, matrizes de confusão, curvas do LSTM, PCA/clusters, mapa das células).
- Executar com `jupyter nbconvert --execute --inplace` e manter as saídas.

## Fase 6 — Documentação (T030–T034, ~2h)
- `ml/dados/README.md` (fonte, sha256, campos, quarentena, privacidade; regenerar `usadas.parquet` sem lat/lon + teste de esquema).
- `RELATORIO_ML.md` (2–4 páginas, só números do notebook, limites e linguagem obrigatória).
- `README.md` com Ficha CitizenTech e ODS — **conteúdo da Ficha vem do Nando** (o documento mestre v3 tem ODS e indicador; usar dele, sem inventar).
- `prompts.md` em dia; varredura de "tempo real", "rota segura", "local seguro".

## Fase 7 — Red-team real e fechamento (T035–T038, ~1h + espera)
- Codex CLI real em modo leitura sobre o repositório pronto; disposição de cada achado; reexecutar pytest e notebook.
- Checklist A1–A6 contra os arquivos reais.

## Depois do ML (fora deste plano, na sequência)
- Wokwi: receber o nível de risco por Serial a partir da `fixture_v1.json`, rodar no Wokwi e gerar o `.txt`.
- Repositório no GitHub: só com confirmação do Nando.
