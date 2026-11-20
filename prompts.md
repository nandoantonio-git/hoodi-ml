# prompts.md — prompts usados (IA como copiloto)

## 2026-11-10 — Etapa 0/1 (JARVIS, Claude)
Prompt (resumo fiel): refazer do zero, com o Nando acompanhando, o pipeline de risco e ML do hoodi; extrair do briefing todos os critérios de ML e entrega com página; contar a base SSP-SP inteira e o recorte município de São Paulo; propor plano e pedir OK ao Nando para rótulo de risco e perímetro.
Uso do resultado: critérios do briefing e contagens de `ml/dados/qualidade_etapa1.txt` (geradas por `scripts/01_qualidade_dado.py`, executado de verdade).

## 2026-11-15 — Features, divisão temporal e modelos (JARVIS, Claude)
Prompt (resumo fiel): o Nando cobrou que a parte de ML não estava montada; implementar T021–T026 da spec 001 com os dados oficiais da SSP-SP já ingeridos (features por origem, testes de split temporal, linhas de base, RF/XGBoost/MLP com 12 combinações de 3 hiperparâmetros cada, CV por origem com expurgo, seleção gravada antes de consultar ago–set).
Uso do resultado: `ml/features.py`, `ml/modelos.py`, testes `tests/test_features_taxas.py` e `tests/test_split_temporal.py`; números em `ml/dados/resultados/` gerados por `python -m ml.modelos`, executado de verdade.

## 2026-11-15 — LSTM e KMeans+PCA (JARVIS, Claude)
Prompt (resumo fiel): o Nando pediu LSTM e KMeans+PCA e um plano para executar tudo neste computador. Implementar os dois com o mesmo protocolo de CV com expurgo, ≥10 combinações de 3 hiperparâmetros, registrados como exploração adicional porque ago–set já tinha sido visto.
Uso do resultado: `ml/sequenciais.py`, `tests/test_sequenciais.py`, `PLANO-EXECUCAO-2026-11-15.md`; números em `ml/dados/resultados/` (execução real de `python -m ml.modelos`).

## 2026-11-15 — Reavaliação do RF, incerteza e custo (JARVIS, Claude)
Prompt (resumo fiel): o Nando pediu para investigar o sobreajuste do Random Forest (treino 0,83 × teste 0,47) e medir a incerteza das métricas. Curvas de validação por CV com expurgo, grade regularizada com limite de gap 0,10, bootstrap por célula H3 e custo assimétrico (subestimar = 2), tudo marcado como exploração adicional porque ago–set já tinha sido visto.
Uso do resultado: `ml/diagnostico_rf.py`, `ml/diagnostico_rf_extra.py`, `ml/incerteza_custo.py`; números em `ml/dados/resultados/rf_reavaliacao.json` e `incerteza_custo.json` (execução real).

## 2026-11-15 — v2: histórico SSP 2023–2025 (JARVIS, Claude; red-team Codex CLI)
Prompt (resumo fiel): usar o histórico oficial da SSP-SP de 2023 a 2025 para testar se mais história ajuda (desenho A, mesmo alvo bimestral) e se uma janela semestral é mais estável (desenho B). Quatro rodadas de red-team real com o Codex CLI.
Uso do resultado: `ml/v2_historico.py`, `scripts/00b_historico_xlsx_para_parquet.py`, `tests/test_v2_historico.py`; `ml/dados/resultados/v2_historico.json`; relatórios `docs/REDTEAM-V2-rodada1..4.md`.

## 2026-11-15 — Notebook documentado e MLflow (JARVIS, Claude; red-team Codex CLI)
Prompt (resumo fiel): montar um notebook que explique cada escolha com evidência e comparação, com prints do MLflow, e passar por red-team real.
Uso do resultado: `scripts/gerar_notebook.py`, `notebooks/hoodi_ml_documentado.ipynb` (executado com `jupyter nbconvert --execute`), `scripts/registrar_mlflow.py`, `docs/mlflow/*.png`.

## 2026-11-15 — v3: da previsão à decisão no app (JARVIS, Claude; red-team Codex CLI)
Prompt (resumo fiel): o Nando perguntou se o trabalho respeitava a arquitetura decidida (ML em lote → API .NET do Abner → app Expo) e pediu um plano de AI Engineer sênior; aprovou as duas partes ("1ok 2ok entra, implemente agora"): política de alerta de proximidade aplicada no aparelho e referência de pontuação de rota com vetores-ouro para a API .NET, mais o teste descritivo de alerta (T-A).
Uso do resultado: `ml/politica_proximidade.py`, `ml/rota.py`, `ml/ta_descritiva.py`, `docs/contratos-v3/`, seções 9–11 do notebook; red-team real em `docs/fase2-produto/REDTEAM-V3-*.md` e `docs/fase2-produto/REDTEAM-IMPL-V3-*.md`; decisões em `docs/fase2-produto/DECISOES-V3.md`.

## 2026-11-16 — Revisão de código, métricas e segredos (JARVIS, Claude)
Prompt (resumo fiel): "como AI Engineer e Software Engineer sênior, monte um plano completo de code review com métricas e testes, campos a serem verificados, vazamento de segredos" e, em seguida, "fazer esse plano agora".
Uso do resultado: varredura com gitleaks, detect-secrets, bandit e pip-audit; `tests/test_schemas_derivados.py` (contrato dos arquivos que a API e o app consomem); `ml/calibracao.py` e `tests/test_calibracao.py` (Brier, log-loss, ECE, curva de confiabilidade, métricas por estrato e backtest por chave); caminhos locais removidos dos scripts; registro em `docs/REVISAO-CODIGO-2026-11-16.md`.

## 2026-11-16 — Red-team da entrega e correções (Codex CLI real)
Prompt (resumo fiel): revisar como AI Engineer e Software Engineer sênior o commit `df5b431`, com foco no diff desde `cf1e345`; verificar ML, vazamento temporal, métricas, calibração, privacidade, segredos, contratos, reprodução, notebook e rubrica A1–A6; listar achados acionáveis com severidade e confirmar bloqueantes/altas.
Uso do resultado: `docs/REDTEAM-ENTREGA-rodada1.md`; remoção da contagem exata do backtest; reprodução limpa dos conversores; calibração no notebook; fixture 0–3 + `sem_dado`; linguagem estatística e inventário de privacidade corrigidos.

## 2026-11-16 — Red-team da entrega, rodada 2 (Codex CLI real)
Prompt (resumo fiel): verificar as sete correções da rodada 1, procurar regressões, avaliar separadamente backtest, risco k < 3 e A1–A6, e confirmar quantos bloqueantes e altas restam.
Uso do resultado: `docs/REDTEAM-ENTREGA-rodada2.md`; backtest convertido em três linhas de métricas agregadas, sem H3/faixa/rótulo/contagem; inventário de logs; resumo corrente da revisão; interpretação correta dos estratos.

## 2026-11-16 — Red-team da entrega, rodada 3 (Codex CLI real)
Prompt (resumo fiel): revisar o HEAD `475cd5b` como rodada final, distinguindo falhas técnicas atuais, exposição preservada no histórico, risco k < 3 do snapshot e os dados oficiais ausentes da rubrica A4; confirmar o backtest agregado, o notebook executado, os estratos, o inventário de logs e a integridade do snapshot.
Uso do resultado: `docs/REDTEAM-ENTREGA-rodada3.md`; teste do backtest fortalecido para exigir esquema, cardinalidade e modelos únicos; confirmação de 0 bloqueantes técnicos e 0 altas técnicas corrigíveis, com três gates humanos ainda abertos.

## 2026-11-16 — Decisão de privacidade A (Nando)
Prompt (resumo fiel): o Nando escolheu a opção A: suprimir/agregar as 218 chaves com menos de três ocorrências e sanear o histórico antes de publicar, aceitando a geração de novo contrato/hash e a necessidade de coordenar os consumidores.
Uso do resultado: snapshot/fixture/política/vetores v2 com supressão k ≥ 3; testes de não exposição; histórico local da revisão reescrito para conter apenas o estado saneado.
