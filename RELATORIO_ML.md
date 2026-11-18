# Relatório de ML — hoodi (GS CitizenTech, FIAP)

Todos os números saem de arquivos em `ml/dados/resultados/` e do notebook `notebooks/hoodi_ml_documentado.ipynb`, gerados por execução real sobre o dado oficial da SSP-SP. Nenhum número foi digitado à mão.

## 1. Problema e decisão de produto
O app avisa quem anda a pé quando a pessoa entra numa área com histórico alto de ocorrências naquela faixa horária. A unidade é a **chave célula H3 (resolução 9, ~0,1 km²) × faixa horária** (5 faixas). O nível vai de 0 a 3: a pontuação é a soma dos pesos das ocorrências por mês por hora da faixa, e os cortes 0,25 / 0,5 / 1,25 são quartis do treino.

**Arquitetura.** O ML roda em lote e gera um snapshot versionado com sha256 (contrato v2, supressão k ≥ 3). A API .NET serve o snapshot e calcula as rotas; o app Expo aplica a política de proximidade no aparelho, offline. O app recebe o **mapa observado** (contrato vigente v3: abr–set/2026; o v2, jan–set/2026, fica para rollback), não a previsão do classificador, que é um experimento retrospectivo.

**Onde o ML entra na rota.** Nenhum modelo decide a rota: a recomendação usa a média histórica por célula, determinística e explicável (seção 8). RF, XGBoost, MLP, LSTM e KMeans+PCA foram testados como pontuação de rota e não superaram essa regra.

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
- **Tamanho:** treino com 3.132 exemplos e teste com 847 (227 / 167 / 254 / 199 nos níveis 0–3); 290 chaves do teste ficaram fora por não terem registro no alvo.


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

**Acerto por tolerância (`backtest_ago_set.csv`):** RF regularizado 52,3 % no nível exato e 88,7 % com erro ≤ 1 nível; persistência 50,2 % e 87,5 %.

**Sobreajuste.** O RF pré-registrado tem gap de 0,36 (F1 de 0,83 no treino contra 0,47 no teste). A regularização escolhida só pela CV, com limite de gap 0,10, leva o gap para perto de zero.

## 5. Calibração e onde o modelo erra
- **Calibração** (RF regularizado): ECE 0,047, Brier 0,591. A correção isotônica piora (ECE 0,105) e **não é aplicada**. A curva de P(nível 3) superestima o risco entre 0,3 e 0,7. Detalhe no anexo (A1).
- **Por faixa:** madrugada, manhã e tarde têm F1 de 0,51 a 0,54; as duas faixas da noite (18–24 h), 0,39–0,40. Com 1 a 4 registros na chave o RF fica acima da persistência (0,27 e 0,36 contra 0,21 e 0,20); com 5 ou mais, empata. As explicações são hipóteses, sem ablação.
- **Repetibilidade do rótulo:** repetir um semestre para prever o seguinte, sem modelo, dá F1 de 0,54 a 0,57. Com o histórico 2023–2025 e alvo semestral, o RF regularizado chega a 0,603 [0,572; 0,632], exploratório, e muda o alvo do produto.

## 6. Alerta de proximidade (T-A, descritivo)
**Política:** nível ≥ 3 na célula atual ou nas vizinhas (anel 1), com intervalo de 30 min entre alertas e a faixa em America/Sao_Paulo (`docs/contratos-v3/politica_proximidade_v2.json`, amarrada ao snapshot v2 por sha256). Marcando 10 % das áreas, a fração da pontuação futura capturada tem mediana 0,365 na persistência, 0,383 na média histórica e 0,390 no RF regularizado (acaso 0,10). Descritivo, sem intervalo, `test_seen=true`.

## 7. Classificação da zona e abstenção (exploratório; anexo A2)
O produto classifica a zona como mais ou menos arriscada; não prevê o futuro. Numa tarefa de recuperação dentro de janelas de 12 meses (metades alternadas A/B; n ≈ 2.200 chaves por janela; não comparável à seção 4), o **RF soma +0,015 de macro-F1 sobre a média histórica** [+0,001; +0,030] (0,647 contra 0,631) e RF e XGBoost somam +0,012 de Spearman. Os modelos **igualam a média histórica nas chaves com menos de 16 registros**; por faixa horária nada se distingue de zero, e a **noite (21–24 h) tem o pior acerto binário** (0,78, contra 0,86–0,89). Empírico-Bayes e suavização espacial não ajudam; a tipologia KMeans+PCA é pouco estável (ARI 0,09 a 0,23).

**Abstenção.** Marcar como "indeterminada" a zona próxima ao corte eleva o acerto binário da média histórica de 0,85 para 0,92 (75 % mais claras) e 0,975 (50 %). O ganho vem da regra, vale para qualquer método e não do ML. O limite está no rótulo (contagem ruidosa de BO): o ML soma cerca de 1 ponto. Informação nova (exposição e fluxo de pessoas; zonas k < 3) **não foi testada**. Janelas trimestral e semestral estabilizam o rótulo, mas RF e XGBoost não superam a média histórica no trimestral.

> **Escopo e limites deste resultado (revisão final, 18/11).** O ganho de 10,6 % vale **só** para o experimento de rotas geométricas sobre o mapa bimestral/v2; **não foi revalidado para o v3 nem para o candidato de carro** e não deve ser citado para eles. Nesse exploratório as chaves sem dado (k < 3) entram com índice 0 na pontuação e no alvo futuro, o que pode favorecer rotas com menos cobertura; a cobertura foi registrada por rota, mas as métricas não foram recalculadas excluindo rotas pouco observadas. Tratar como evidência exploratória, não como garantia.


## 8. Recomendação de rota (T-B, exploratório; anexo A3)
Em 600 pares origem–destino com 4 a 5 alternativas (trajetos **geométricos, não a malha viária**), 10 origens walk-forward × 5 faixas (29.838 casos), a **média histórica ordena as rotas com concordância 0,751** (acaso 0,50; rota mais curta 0,649) e reduz a exposição em **10,6 % [9,5; 11,8]** sobre a mais curta, ao custo de 8,6 % a mais de distância. **Nenhum modelo supera a média histórica** (RF 0,735; persistência 0,709).

**Regra proposta:** desviar só se o ganho previsto for ≥ 10 %. No teste, desvia em 44 % dos casos, mantém 10,2 % de redução e baixa o km extra de 8,4 % para 6,9 %. Mesmo assim, a rota escolhida fica pior que a mais curta em 18 % a 23 % dos desvios: o ganho previsto ordena, não garante.

**Limites.** Trajetos sintéticos; origens sobrepostas (o IC subestima a incerteza); média histórica sem a supressão k < 3; ago–set/2026 já visto. Os resultados medem **exposição histórica observada**, não segurança.

## 9. Limites e uso responsável
- **Não indica tempo real nem local seguro.** O mapa é histórico, e uma área sem registro não é área sem risco.
- **Viés de registro:** só entra ocorrência registrada em BO com hora e coordenada. Ficaram fora 202.401 registros sem hora e 182.090 sem coordenada na base inteira.
- **Privacidade:** não há coordenada nem número de BO em nenhum arquivo versionado. O backtest publica somente métricas agregadas por modelo. O snapshot v2 aplica k ≥ 3: as 218 chaves com 1–2 registros são publicadas como `sem_dado`, sem contagem, pontuação ou nível; apenas os totais agregados da supressão ficam no manifesto. A branch só pode ser enviada após o saneamento do histórico local.
- **Avaliação já vista:** ago–set/2026 foi consultado em decisões posteriores. Uma afirmação de melhoria exige o teste cego com out–nov/2026, quando a SSP publicar esses meses.
- **Reprodutibilidade:** semente 42, dependências fixadas em `requirements.txt`. O snapshot v2 gerado de novo em 2026-11-16 deu o mesmo sha256 (`2dddef701bde…`).
- **Testes:** a suíte automatizada inclui o contrato v2, a supressão k ≥ 3 e os arquivos que a API e o app consomem (`tests/test_schemas_derivados.py`).


## 10. Próximos passos
1. Repetir a seção 8 com rotas reais do HeiGIT e com o snapshot k ≥ 3 de cada período.
2. Fazer o teste cego em out–nov/2026.
3. Decidir entre o mapa bimestral e o semestral (rótulo mais estável em janelas maiores, sem ganho na decisão).
4. Testar exposição e fluxo de pessoas (OSM/IBGE) como variável nova.
5. Usar a fixture v2 (níveis 0–3 e `sem_dado`) nos testes da API e do app; escolher o limiar do alerta pela taxa de alertas aceitável.

## Limitações conhecidas do candidato de carro (revisão de 18/11)

Os cortes de nível do `snapshot_carro_candidato` são quartis de janelas de 24 meses que chegam até jun/2026, e o candidato cobre out/2024–set/2026: há sobreposição. Os níveis são, portanto, **descritivos** e não servem para conclusões preditivas. Por isso o candidato não substitui v2/v3.
