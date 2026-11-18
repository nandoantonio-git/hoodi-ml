# Anexo exploratório — hoodi ML

Detalhe das análises exploratórias resumidas em `RELATORIO_ML.md` (seções 5, 8 e 9). Texto e números idênticos ao relatório anterior; nada foi alterado, só movido.

## A1. Calibração (`ml/calibracao.py`, `calibracao.json`)

| RF regularizado | Brier multiclasse | Log-loss | ECE (nível mais provável) | Brier P(nível 3) |
|---|---|---|---|---|
| Sem calibração | 0,591 | 1,044 | **0,047** | 0,109 |
| Isotônica ajustada na CV | 0,602 | 1,131 | 0,105 | 0,112 |

- **As probabilidades saem razoavelmente calibradas** (ECE 0,047). A curva de P(nível 3) superestima o risco na faixa de 0,3 a 0,7 (em 0,6 a 0,7: previsão 0,65, frequência 0,41, 37 chaves) e acompanha a frequência acima de 0,9.
- **A correção isotônica piora o resultado** (ajustada com 1.616 previsões fora da dobra) e **não é aplicada**. Recalibrar só faz sentido se `predict_proba` alimentar uma decisão do produto; hoje alimenta só o experimento da regra de custo.

## A2. Classificação da zona e abstenção (exploratório)
**Pergunta.** O produto classifica a zona como mais ou menos arriscada; ele não prevê o futuro. Nessa tarefa, o ML recupera o nível observado melhor que a média histórica?

**Método (`ml/exploratorio_classificacao/`).** Em cada janela de 12 meses, os meses alternados formam as metades A e B. O estimador vê A e o contexto (todos os meses até o fim da janela, exceto B) e classifica o nível de B (quartis de B), nas duas direções, nas janelas 22–33 e 34–45 (n = 2.186 e 2.216 chaves; 260 células). RF e XGBoost treinam em janelas anteriores. É interpolação dentro da janela: **não é previsão e não é comparável** aos números da seção 4 do relatório.

| Estimador (janela 34–45) | Macro-F1 | Spearman | Acerto acima/abaixo da mediana |
|---|---|---|---|
| Só metade A | 0,606 | 0,845 | 0,843 |
| Média histórica (contexto) | 0,631 | 0,869 | 0,853 |
| Suavização espacial | 0,630 | 0,867 | 0,859 |
| Empírico-Bayes (prior res-8/res-7) | 0,631 | 0,869 | 0,853 |
| XGBoost | 0,633 | 0,882 | 0,856 |
| RF regularizado | 0,647 | 0,882 | 0,861 |

Sobre a média histórica, o RF soma +0,015 de macro-F1 [+0,001; +0,030], e RF e XGBoost somam +0,012 de Spearman [+0,008; +0,016] (IC por bootstrap de células). Na janela 22–33, com um só período de treino, nenhum modelo se separa. Encolhimento e suavização não ajudam. **Por evidência**, os modelos igualam a média histórica nas chaves com poucos registros (diferença 0,000 no acerto binário abaixo de 16 registros na janela 34–45) e ganham até +0,010 [−0,001; +0,020] nas de 16 ou mais. **Por faixa horária**, nenhuma diferença se distingue de zero na janela 34–45, e a **noite** (21–24 h) tem o pior acerto binário (0,78, contra 0,86–0,89 nas demais).

**Abstenção.** Marcar como "indeterminada" a zona próxima ao corte mais/menos arriscada melhora o acerto binário da média histórica de 0,85 (todas) para 0,92 (75 % mais claras), 0,975 (50 %) e 0,99 (25 %). RF e XGBoost chegam a 0,93–0,94, 0,975–0,98 e ~1,0: o ganho vem da regra de abstenção e vale para qualquer método.

**Tipologia e janela.** KMeans+PCA no perfil de crime × faixa horária é pouco estável entre as metades (ARI 0,23 com 3 grupos, 0,15 com 4, 0,09 com 5; embaralhado 0,00): descreve, não gradua risco. Janelas trimestral e semestral estabilizam o rótulo (macro-F1 da média histórica 0,48 → 0,52 → 0,58), mas a redução de exposição na rota fica em ~10 % e, no trimestral, RF e XGBoost não superam a média histórica (−0,008 e −0,002).

**Leitura e limites.** O limite está no rótulo (contagem ruidosa de BO), não no algoritmo: o ML soma cerca de 1 ponto. A alavanca que falta é informação nova (exposição e fluxo de pessoas; zonas k < 3), **não testada**. Exploratório; ago–set/2026 já visto; só chaves com registro em B; mede o observado na SSP-SP, não o perigo real.

## A3. Recomendação de rota (T-B, exploratório)
**Pergunta.** A ordem das rotas pelo histórico se mantém no bimestre seguinte? Se sim, a recomendação não depende de acertar o nível de cada célula, porque os erros de rótulo se cancelam ao somar dezenas de células ao longo do trajeto.

**Método (`ml/exploratorio_rotas/`, saídas em `ml/dados/resultados/rotas_exploratorio/`).** 600 pares origem–destino no perímetro, a 0,9–2,5 km, com 4 a 5 alternativas cada (reta, dois L e dois desvios de ~300 m). A pontuação da rota é a soma, sobre as células do trajeto, da pontuação mensal da célula × km no trecho. Os trajetos são **proxies geométricos, não a malha viária**; o dado de risco por célula é real. São 10 origens walk-forward (jan–fev/2025 a jul–ago/2026) × 5 faixas, 29.838 casos.

> **Escopo e limites deste resultado (revisão final, 18/11).** O ganho de 10,6 % vale **só** para o experimento de rotas geométricas sobre o mapa bimestral/v2; **não foi revalidado para o v3 nem para o candidato de carro** e não deve ser citado para eles. Nesse exploratório as chaves sem dado (k < 3) entram com índice 0 na pontuação e no alvo futuro, o que pode favorecer rotas com menos cobertura; a cobertura foi registrada por rota, mas as métricas não foram recalculadas excluindo rotas pouco observadas. Tratar como evidência exploratória, não como garantia.


| Pontuação da rota | Concordância de ordem | Posição da escolhida (1–5) | Escolhida é a melhor | Redução de exposição vs. mais curta |
|---|---|---|---|---|
| Média histórica | 0,751 | 1,98 | 46,5 % | 10,6 % [9,5; 11,8] |
| Mistura histórica + RF | 0,751 | 1,97 | 45,0 % | 10,7 % |
| Suavizada com vizinhas | 0,741 | 2,03 | 43,3 % | 9,8 % |
| RF regularizado | 0,735 | 2,03 | 41,3 % | 9,3 % |
| Persistência (2 meses) | 0,709 | 2,19 | 41,1 % | 7,8 % |
| Rota mais curta | 0,649 | 2,48 | 22,3 % | 0 % |

Acaso: concordância 0,50, posição 3,0, escolhida melhor em 20 %. O custo da escolha é 8,6 % a mais de distância. Restringindo a comparação aos dois L (mesmo comprimento), a concordância é 0,762 (histórico) contra 0,716 (persistência): o resultado não vem só de rotas longas acumularem mais risco. Em ago–set/2026 a concordância é 0,744.

**Modelos como pontuação de rota.** O RF, a mistura e a suavização por vizinhas **não superaram a média histórica**. KMeans+PCA (6 a 16 clusters, 3 a 4 componentes) e decaimento exponencial (meia-vida de 6 a 24 meses) variam entre 0,749 e 0,758 de concordância contra 0,752 da média histórica no conjunto de teste, diferença dentro do ruído. Os hiperparâmetros foram escolhidos nas cinco primeiras origens e medidos nas cinco últimas.

**Quando vale desviar.** O ganho previsto sobre a rota mais curta ordena bem o ganho real:

| Ganho previsto | Escolhida é melhor que a mais curta | Redução real | Km extra |
|---|---|---|---|
| até 5 % | 58 % | 1,1 % | 3,7 % |
| 5–15 % | 62 % | 6,7 % | 8,2 % |
| 15–30 % | 74 % | 17,2 % | 12,8 % |
| mais de 30 % | 81 % | 34,5 % | 24,3 % |

Regra proposta: desviar da rota mais curta só se o ganho previsto for ≥ 10 %. No teste (cinco últimas origens) a política desvia em 44 % dos casos, mantém 10,2 % de redução (contra 11,0 % sempre desviando) e reduz o km extra de 8,4 % para 6,9 %. O comportamento é o mesmo nas cinco primeiras origens. Mesmo com limiar alto, a rota escolhida fica pior que a mais curta em 18 % a 23 % dos desvios: o ganho previsto ordena, não garante.

**Limites.** Trajetos sintéticos; origens sobrepostas (o IC por par subestima a incerteza); média histórica sem a supressão k < 3 do snapshot publicado; ago–set/2026 já foi visto. A validação com rotas reais do HeiGIT e com o snapshot publicado em cada período está pendente. Os resultados medem **exposição histórica observada**, não segurança.
