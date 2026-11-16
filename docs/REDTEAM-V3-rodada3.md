<!-- Saída integral do Codex CLI (codex exec --sandbox read-only --ephemeral), 15/11/2026, sobre PROPOSTA-V3-ALERTA-ROTAS-r2.md. -->

## 1. Status dos achados

| Achado da rodada 2 | Status na r2 |
|---|---|
| 4 — cobertura | **PARCIAL** — U1 exige registro anterior na mesma faixa, mas isso não prova que a coleta cobria toda a unidade. |
| 6 — métrica de T-A | **RESOLVIDO** — fórmula, corte, desempate e tratamento de denominador zero estão definidos. |
| 10 — abstenção em T-B | **RESOLVIDO para a fase 1** — a regra foi retirada; calibração e distribuição preditiva ficam para a fase 2. |
| 11 — suavização e zeros | **PARCIAL** — U1 limita a inclusão, mas a escolha de λ e a interpretação de ausência de registro ainda precisam de validação explícita. |
| 16 — 34.771 × 34.769 | **PARCIAL** — a r2 explica por que a diferença não foi reconciliada, mas não a reconcilia. |
| r2-1 — universo U1 | **PARCIAL** — é calculável no parquet, mas não demonstra cobertura da coleta. |
| r2-2 — métrica de T-A | **RESOLVIDO** — a métrica descritiva está suficientemente especificada. |
| r2-3 — bootstrap e poucos blocos | **RESOLVIDO para a fase 1** — não haverá inferência; o plano inferencial continua pendente do pré-registro da fase 2. |
| r2-4 — probabilidade de abstenção | **RESOLVIDO para a fase 1** — não se apresenta uma regra probabilística como validada. |
| r2-5 — decisões de produto na fase 1 | **RESOLVIDO** — a entrega é declarada acadêmica e documental, sem validar alerta ou escolha de rota. |
| r2-6 — prazo | **RESOLVIDO como plano** — separa o obrigatório do opcional e apresenta estimativas; o cronograma é apertado e sem folga explícita. |

## 2. Novos achados na r2

- **[BLOQUEANTE] U1 é um filtro de ocorrência passada, não uma medida de cobertura.** A regra “ao menos um registro nos 12 meses anteriores” seleciona locais e faixas que já tiveram registro; não prova que a SSP observava sistematicamente os demais, nem que um zero futuro significa ausência de ocorrência. Isso limita as conclusões ao subconjunto selecionado e pode enviesar o ranking. **Correção:** nomear U1 como “universo com registro anterior”, manter `zero registrado` separado de zero real e qualificar os resultados como condicionais a esse universo. Para afirmar cobertura, obter evidência de coleta por unidade e período.

- **[ALTA] O RF regularizado existente não pode ser aplicado às origens históricas como está sem risco de vazamento temporal.** O código da v2 ajusta o RF para um teste posterior; a r2 não define um ajuste walk-forward por origem. Usar o modelo existente em origens de 2024–2026 deixaria informação futura entrar nos escores. Também é preciso tratar a seleção dos hiperparâmetros, feita em dados posteriores às origens iniciais. `E[nível] = Σ k·P(nível=k)` define um escore ordinal, mas não resolve esse problema. **Correção:** para cada origem, ajustar o modelo e as transformações só com dados anteriores a ela; pré-fixar os hiperparâmetros sem consultar origens avaliadas ou fazer seleção temporal aninhada. Gerar o escore com `predict_proba` e registrar os cortes usados.

- **[MÉDIA] A escolha de λ ainda não é reproduzível.** A r2 lista quatro valores e exige escolhê-lo antes da primeira origem avaliada, mas não fixa o critério de seleção, os dados de validação nem o desempate. **Correção:** definir a métrica de validação e as origens anteriores usadas para escolher λ, e congelar essa escolha antes de calcular os resultados reportados.

- **[MÉDIA] O protótipo de rota pode chamar dado observado de valor esperado.** A pontuação viria do snapshot v1 observado em jan–set/2026; “total esperado no trajeto” pode sugerir previsão para uma viagem futura. Um exemplo de rota também pode parecer retrospectivamente validado se não trouxer a janela junto. **Correção:** no protótipo, apresentar “pontuação acumulada observada, jan–set/2026”, com indicação de retrospectivo e cobertura, e não como expectativa ou previsão.

## 3. Conferência dos números

- **`n_blocos_res7 = 9`: confere** em `v2_historico.json`.
- **34.771 inclusivo = estrito: confere** no interim 2026: leitura somente de coordenadas, com os mesmos critérios de validade e perímetro, dá 34.771 pelos limites inclusivos e 34.771 pelos estritos; não há registros na borda. Isso não explica a diferença em relação aos 34.769 da medição antiga, cujo script não está no repositório.

A r2 mantém o notebook gerado por `scripts/gerar_notebook.py` e preserva v1/v2 no MLflow; registro de análises novas fica opcional. Isso atende ao requisito de manter ambos.

**Veredito:** a r2 pode ser apresentada ao dono como plano de reestruturação, ressalvando que U1 não comprova cobertura, T-A exige avaliação walk-forward sem vazamento e o protótipo de rota deve ser rotulado como retrospectivo; nenhuma das duas decisões do produto estará validada na entrega de novembro.