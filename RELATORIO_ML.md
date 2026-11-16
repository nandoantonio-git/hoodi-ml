# Relatório de ML — hoodi (GS CitizenTech, FIAP)

Todos os números saem de arquivos em `ml/dados/resultados/` e do notebook `notebooks/hoodi_ml_documentado.ipynb`, gerados por execução real sobre o dado oficial da SSP-SP. Nenhum número foi digitado à mão.

## 1. Problema e decisão de produto
O app avisa quem anda a pé quando a pessoa entra numa área com histórico alto de ocorrências naquela faixa horária. A unidade é a **chave célula H3 (resolução 9, ~0,1 km²) × faixa horária** (5 faixas). O nível vai de 0 a 3. A pontuação é a soma dos pesos das ocorrências por mês por hora da faixa, e os cortes 0,25 / 0,5 / 1,25 são quartis do treino.

**Arquitetura.** O ML roda em lote e gera um snapshot versionado com sha256 (contrato v2, supressão k ≥ 3). A API .NET serve esse snapshot e calcula as rotas. O app Expo aplica a política de proximidade no aparelho, offline.

**O que o app recebe.** O app recebe o **mapa observado de jan–set/2026**, não a previsão do classificador. O classificador é um experimento retrospectivo que mede o quanto o passado prevê o bimestre seguinte.

## 2. Dados
- Fonte: SSP-SP, `SPDadosCriminais_2026.xlsx`, sha256 `f627d84e…`. Proveniência em `ml/dados/README.md`.
- Base: 814.900 linhas. Usadas: **20.343 (2,50 % da base; 58,5 % do que cai no perímetro de 5 × 5 km)**.
  - Dentro do perímetro, a maior perda é ocorrência sem hora (14.113 registros).
- Snapshot v2: 279 células × 5 faixas = 1.395 chaves; 954 têm pelo menos três registros e 441 são publicadas como `sem_dado` (223 sem registro e 218 suprimidas por k < 3).
  - "Sem dado" nunca é tratado como risco 0.

## 3. Protocolo de avaliação
- **Origens temporais T1–T4 para treino** e **teste em ago–set/2026**:
  - as features usam só os meses anteriores ao alvo;
  - a CV de seleção tem expurgo (T1→T3, T1+T2→T4);
  - os cortes de nível são calculados só no treino.
  - Os testes `tests/test_split_temporal.py`, `test_cortes_treino.py` e `test_sequenciais.py` verificam essas três regras.
- **Seleção pré-registrada:** o vencedor da CV (Random Forest) foi gravado em `selecao_modelo.json` antes de abrir o teste.
  - O que veio depois é **exploração adicional com `test_seen=true`**: o RF regularizado, o LSTM, o KMeans+PCA, a regra de custo, o histórico 2023–2025 e a calibração.
- **Incerteza:** bootstrap por célula H3, com 2.000 reamostras e as faixas da mesma célula juntas. As diferenças entre modelos são pareadas, medidas nas mesmas reamostras.
- **Tamanho:** treino com 3.132 exemplos e teste com 847.
  - O teste tem 227 / 167 / 254 / 199 exemplos nos níveis 0–3.
  - 290 chaves do teste ficaram fora por não terem registro no período do alvo.

## 4. Resultados no teste (ago–set/2026, n = 847)

| Modelo | Situação | Macro-F1 [IC95 %] | Gap treino−teste | Custo médio¹ | Recall risco alto² | Precisão risco alto² |
|---|---|---|---|---|---|---|
| Classe mais frequente | base | 0,115 | 0,01 | — | — | — |
| Persistência (nível da janela anterior) | base | 0,491 [0,457; 0,524] | −0,02 | 0,950 | 0,773 | 0,776 |
| Random Forest (vencedor pré-registrado) | pré-registrado | 0,467 [0,432; 0,500] | **0,36** | 0,927 | 0,832 | 0,752 |
| XGBoost | pré-registrado | 0,476 [0,441; 0,509] | 0,17 | 0,921 | 0,830 | 0,775 |
| MLP | pré-registrado | 0,477 [0,443; 0,510] | 0,05 | 0,822 | 0,936 | 0,707 |
| LSTM | exploração | 0,492 [0,459; 0,525] | 0,09 | 0,980 | 0,726 | 0,835 |
| KMeans + PCA | exploração | 0,503 [0,467; 0,535] | −0,01 | 0,819 | 0,909 | 0,729 |
| **RF regularizado** (max_depth 6, min_samples_leaf 80) | exploração | **0,513 [0,479; 0,546]** | ≈ 0 | 0,844 | 0,839 | 0,776 |

¹ Custo do erro = distância entre níveis, ×2 quando o modelo subestima. O peso 2 é escolha de produto, não ajustada.
² Risco alto = níveis 2–3.

**Diferenças pareadas (RF regularizado − persistência):**
- **Macro-F1:** +0,022 [−0,010; 0,052]. **Sem diferença estabelecida.**
- **Recall de risco alto:** +0,066 [0,038; 0,095].
- **Custo médio:** −0,106 [−0,166; −0,043].
- **Taxa de subestimação:** −0,066 [−0,088; −0,045].

O RF regularizado **não demonstrou superar a persistência em acerto de nível**. Neste teste, ele subestimou menos o nível registrado; como foi escolhido depois de ver ago–set, isso é resultado exploratório, não prova de superioridade.

**Acerto por tolerância (backtest agregado, `backtest_ago_set.csv`):**

| Modelo | Nível exato | Erro ≤ 1 nível |
|---|---|---|
| RF regularizado | 52,3 % | 88,7 % |
| Persistência | 50,2 % | 87,5 % |

**Sobreajuste.** O RF pré-registrado tem gap de 0,36 (F1 de 0,83 no treino contra 0,47 no teste). A regularização escolhida só pela CV, com limite de gap 0,10, leva o gap para perto de zero.

## 5. Calibração (`ml/calibracao.py`, `calibracao.json`)

| RF regularizado | Brier multiclasse | Log-loss | ECE (nível mais provável) | Brier P(nível 3) |
|---|---|---|---|---|
| Sem calibração | 0,591 | 1,044 | **0,047** | 0,109 |
| Isotônica ajustada na CV | 0,602 | 1,131 | 0,105 | 0,112 |

- **As probabilidades saem razoavelmente calibradas.** A curva de P(nível 3) acompanha a frequência observada:
  - de 0 a 0,3 a previsão fica 1 a 4 pontos acima da frequência (superestima levemente o risco);
  - de 0,3 a 0,7 superestima mais; na faixa de 0,6 a 0,7 a previsão é 0,65 e a frequência é 0,41, com 37 chaves;
  - acima de 0,9 a previsão é 0,93 e a frequência é 0,96.
- **A correção isotônica piora o resultado.** Ela foi ajustada só com as 1.616 previsões fora da dobra da CV, e por isso **não é aplicada**.
- Recalibrar só faz sentido se `predict_proba` passar a alimentar uma decisão do produto. Hoje ele alimenta só o experimento da regra de custo.

## 6. Onde o modelo erra
- **Por faixa horária:**
  - Madrugada, manhã e tarde ficam com F1 de 0,51 a 0,54.
  - Noite cedo (18–21h) fica com F1 0,40, abaixo da persistência (0,50).
  - Noite (21–24h) fica com F1 0,39, contra 0,35 da persistência.
  - As faixas de 3 horas têm menos registros por chave; que isso explique a instabilidade do rótulo é uma hipótese, não uma relação causal demonstrada.
- **Por quantidade de registros na janela de features:**

  | Registros | Chaves | F1 do RF | F1 da persistência |
  |---|---|---|---|
  | 1 | 47 | 0,27 | 0,21 |
  | 2–4 | 151 | 0,36 | 0,20 |
  | 5 ou mais | 649 | 0,44 | 0,45 |

  Onde há pouco dado, o RF ficou acima da persistência. O uso de células vizinhas é uma hipótese compatível com esse padrão, mas não houve ablação específica para demonstrar causalidade. Onde há muito dado, a diferença observada é pequena.
- **Referência de repetibilidade do rótulo.** Repetir um semestre para prever o seguinte, sem modelo nenhum, dá F1 de 0,54 a 0,57 (`v2_historico.json`); isso é uma referência descritiva, não um teto de desempenho.
  - Com o histórico 2023–2025 e alvo semestral, o RF regularizado chega a **0,603 [0,572; 0,632]**.
  - É o maior macro-F1 observado nestes experimentos, mas muda o alvo e o produto para um mapa semestral; não isola o efeito de acrescentar histórico.

## 7. Alerta de proximidade (T-A, descritivo)
**Política:** nível ≥ 3 na célula atual ou nas vizinhas (anel 1), com intervalo de 30 min entre alertas e a faixa calculada em America/Sao_Paulo. Ela está em `docs/contratos-v3/politica_proximidade_v2.json`, amarrada ao snapshot v2 por sha256.

**Teste retrospectivo (10 origens):** marcando 10 % das áreas (U1), a fração da pontuação futura capturada tem estas medianas:

| Método | Mediana | Origens acima da persistência |
|---|---|---|
| Persistência | 0,365 | — |
| Média histórica | 0,383 | 9 de 10 |
| RF regularizado | 0,390 | 9 de 10 |

A suavização pelas vizinhas não ajudou (λ = 0). O teste é descritivo, sem intervalo e com `test_seen=true`.

## 8. Limites e uso responsável
- **Não indica tempo real nem local seguro.** O mapa é histórico, e uma área sem registro não é área sem risco.
- **Viés de registro:** só entra ocorrência registrada em BO com hora e coordenada. Ficaram fora 202.401 registros sem hora e 182.090 sem coordenada na base inteira.
- **Privacidade:** não há coordenada nem número de BO em nenhum arquivo versionado. O backtest publica somente métricas agregadas por modelo. O snapshot v2 aplica k ≥ 3: as 218 chaves com 1–2 registros são publicadas como `sem_dado`, sem contagem, pontuação ou nível; apenas os totais agregados da supressão ficam no manifesto. A branch só pode ser enviada após o saneamento do histórico local.
- **Avaliação já vista:** ago–set/2026 foi consultado em decisões posteriores. Uma afirmação de melhoria exige o teste cego com out–nov/2026, quando a SSP publicar esses meses.
- **Reprodutibilidade:** semente 42, dependências fixadas em `requirements.txt`. O snapshot v2 gerado de novo em 2026-11-16 deu o mesmo sha256 (`2dddef701bde…`).
- **Testes:** a suíte automatizada inclui o contrato v2, a supressão k ≥ 3 e os arquivos que a API e o app consomem (`tests/test_schemas_derivados.py`).

## 9. Próximos passos
1. Fazer o teste cego em out–nov/2026.
2. Decidir entre o mapa bimestral e o semestral.
3. Usar a fixture v2, que cobre os níveis 0–3 e `sem_dado`, nos testes da API e do app.
4. Escolher o limiar do alerta pela taxa de alertas aceitável.
