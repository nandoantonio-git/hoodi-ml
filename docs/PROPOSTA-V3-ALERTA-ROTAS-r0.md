# Proposta v3 — do "nível por célula" para as duas decisões do app (alerta e escolha de rota)

Status: **proposta, rodada 0** (15/11/2026, JARVIS). Nada aqui foi implementado. A v1 pré-registrada (`selecao_modelo.json`) e a v2 continuam como estão.

## 0. Pergunta do Nando e veredito

Intenção do app (Nando, 15/11):
1. **Alerta:** classificar e alertar a pessoa *antes* de ela entrar numa região com muitas ocorrências.
2. **Rotas de carro:** entre 3 ou 4 rotas, escolher a que tem o melhor índice de ocorrências.

**A solução atual não atende nenhuma das duas como decisão.**

| Necessidade do app | O que existe hoje | Lacuna |
|---|---|---|
| Alerta antes de entrar | O snapshot entregue ao app é o **mapa histórico observado** de jan–set (contrato v1, `natureza`: "não é previsão"). O classificador ML prevê o nível 0–3 do bimestre seguinte por célula×faixa, e esse nível **não vai para o app**. | Não há regra de alerta: nem limiar, nem taxa de alarmes, nem métrica de acerto do alerta. O macro-F1 de 4 níveis mede acerto no nível 0 tanto quanto no nível 3, mas o alerta só depende de acertar as áreas mais altas. O modelo pré-registrado (0,467) não supera a persistência (0,491). |
| Comparar 3–4 rotas de carro | Nada. `SPEC-ML.md` §11 e FR-012 põem "rota segura" **fora de escopo**. | Não há função de pontuação de rota, contrato de rota com o app nem avaliação de ordenação de rotas. O perímetro de 5×5 km comporta poucas rotas de carro com alternativas reais. Os pesos foram pensados para crime em geral, não para quem está dentro de um carro. |
| Honestidade de linguagem | FR-012 proíbe "rota/local seguro" e "tempo real". | **Mantém-se.** O app diria "rota com menos ocorrências registradas", nunca "rota segura". |

Medições que orientam a proposta (dados reais, `usadas_v2.parquet` e interim 2026, perímetro atual):
- Por chave célula×faixa em ago–set/2026: 883 chaves, **mediana de 3 registros**, p90 = 12. O rótulo por chave é ruidoso.
- Por célula, somando todas as faixas, em jan–set/2026: 258 células, **mediana de 48,5 registros**. Agregar no espaço e no tempo reduz muito o ruído.
- 2026 no perímetro: 34.771 registros. `DESCR_SUBTIPOLOCAL` = "Via Pública" em 30.991 (89%). Em `DESCR_CONDUTA`, cerca de 1,7 mil têm conduta ligada a veículo ("Veículo" 953, "Interior de Veículo" 635, "Aplicativo de Mobilidade" 132, "Carga" 25), e 44% vêm sem conduta (NULL).
- O histórico 2023–2025 em `interim/` foi gravado só com 8 colunas, **sem** `DESCR_CONDUTA` nem `DESCR_SUBTIPOLOCAL`. Para usá-las é preciso reextrair dos XLSX originais (sha256 em `CHECKSUM_HISTORICO.txt`).

Hipótese central da v3: **uma rota atravessa dezenas de células.** O índice de uma rota soma muitos registros, então ordenar rotas pode ser bem mais previsível que acertar o nível de uma chave isolada. Isso é hipótese a testar, não resultado.

## 1. Reenquadramento: duas decisões, dois alvos, métricas de decisão

### D1 — Alerta de entrada (célula × faixa)

- **Alvo:** o índice de ocorrências registradas na via pública no próximo período (contagem ponderada por hora da faixa, mesma fórmula da v1). É uma **regressão/ordenação**, não uma classificação de 4 níveis.
- **Decisão:** alertar quando a chave está entre os *q*% de maior índice previsto. *q* é fixado antes do teste a partir de uma meta de alarmes (por exemplo, no máximo 1 alerta a cada X km de caminhada típica, medido no treino).
- **Métricas (padrão de previsão espacial de crime):**
  - *hit rate* com área de alerta fixa: % das ocorrências do período futuro que caem nas chaves alertadas;
  - **PAI**, *Predictive Accuracy Index* = hit rate ÷ % da área alertada;
  - precisão e *recall* das chaves no topo *q*% realizadas;
  - IC por bootstrap em blocos espaciais (como na v2).
- **Linhas de base obrigatórias:** persistência (último período); média histórica longa (2023 em diante); suavização espacial (média com as vizinhas H3 / *kernel*). O modelo só "vale" se superar a **melhor** linha de base com IC acima de zero.
- **Modelos candidatos:** XGBoost/LightGBM com objetivo Poisson/Tweedie; RF regressor; GLM Poisson com encolhimento empírico-bayesiano rumo à vizinhança. O encolhimento ataca diretamente o problema dos 3 registros. LSTM entra se o tempo permitir, com o mesmo protocolo.

### D2 — Ordenação de rotas de carro

- **O ML não calcula rotas.** O app (Abner) obtém de 3 a 4 rotas de um roteador e as envia como lista de `(h3_cell, metros_na_celula)` mais a hora de partida. O ML devolve, por rota: índice previsto, % do trajeto "sem dado", intervalo de incerteza e a decisão.
- **Índice da rota** = Σ células (índice previsto da célula na faixa de passagem × metros na célula) ÷ comprimento total. Isso dá ocorrências por km, para rotas de tamanhos diferentes serem comparáveis. A variante "total da rota", sem dividir pelo comprimento, é avaliada como análise de sensibilidade.
- **Decisão com incerteza:** se as rotas estiverem dentro do intervalo de incerteza umas das outras, o app diz "rotas equivalentes em ocorrências registradas" em vez de forçar uma escolha. Isso evita fingir precisão.
- **Avaliação offline (sem app):**
  - gerar pares origem-destino dentro da área e, para cada um, 3–4 rotas alternativas de carro;
  - opção preferida: k caminhos mais curtos com no máximo +X% de comprimento, sobre a malha viária do OpenStreetMap (osmnx, dado público, baixado uma vez com hash);
  - opção de contingência: caminhos sobre a grade H3, declarados como aproximação;
  - **métricas:**
    - concordância par a par entre a ordem prevista e a ordem realizada no período futuro (só pares cuja diferença realizada supera o ruído);
    - Kendall τ;
    - **arrependimento** (*regret*) = índice realizado da rota escolhida − índice realizado da melhor rota.
  - **Linhas de base:** rota mais curta (ignora ocorrências); persistência; média histórica.
- **Crimes considerados:** todos os da via pública (decisão padrão). Análise de sensibilidade com o subconjunto ligado a veículo (só 2026 tem a conduta, e com 44% NULL; isso é declarado).

## 2. Dados

1. **Perímetro:** 5×5 km é pequeno para rotas de carro com alternativas. Proposta: ampliar para cerca de 10×10 km em torno do mesmo centro, se o reprocessamento couber no prazo; senão, manter 5×5 e restringir os pares origem-destino ao interior, declarando o limite.
2. **Reextração do histórico** 2023–2025 com `DESCR_CONDUTA`, `DESCR_SUBTIPOLOCAL` e `DESCR_TIPOLOCAL`. O raw continua imutável e o hash é conferido.
3. **Viés de exposição declarado:** contagem registrada reflete também movimento de pessoas e de veículos, além de subnotificação. Índice alto ≠ probabilidade individual alta. Isso já está no contrato v1 e se mantém.
4. A quarentena, a reconciliação e o "sem dado" ≠ 0 continuam iguais. Na rota, "sem dado" entra como fração declarada, nunca como 0.

## 3. Avaliação honesta: o problema do Teste já visto

Jan–set/2026 já foi visto na v1 e na v2. Não existe Teste cego em 2026.
- **Proposta:** pré-registrar a v3 **antes** de rodar, num `selecao_v3.json` novo, com seleção feita só em validação temporal até jul/2026 e avaliação em ago–set/2026. A avaliação é declarada **semi-cega**: o período já foi visto, mas as tarefas D1 e D2 e suas métricas nunca foram avaliadas nele.
- **Compromisso de teste cego:** congelar o modelo e o código e avaliá-los em out–nov/2026 quando a SSP publicar. Isso fica depois da entrega e é declarado como trabalho futuro.
- A v1 continua sendo o único resultado pré-registrado cego da tarefa original e não é reescrita.

## 4. O que se preserva (pedido do Nando)

- **Notebook:** `notebooks/hoodi_ml_documentado.ipynb` ganha as seções 9 (reenquadramento e lacunas), 10 (D1 alerta) e 11 (D2 rotas), no mesmo estilo de escolha → evidência → leitura. As seções 1–8 ficam como história da decisão. O notebook continua gerado por `scripts/gerar_notebook.py` e só lê resultados salvos.
- **MLflow:** novos experimentos `hoodi-v3-alerta` e `hoodi-v3-rotas`, registrados por `scripts/registrar_mlflow.py` com as mesmas tags de proveniência (commit, arquivo fonte, sha256). Os prints mostram as comparações com as linhas de base.
- **Red-team real (Codex CLI)** em cada rodada, até não sobrar bloqueante nem achado de gravidade ALTA.

## 5. Mudanças de especificação necessárias (precisam do aceite do Nando)

- `SPEC-ML.md` §1: a pergunta passa a ser dupla (D1 e D2).
- §11 e FR-012: "rota" sai do fora de escopo; continua proibido dizer "segura", "tempo real" ou "risco pessoal". O texto do app passa a ser "rota com menos ocorrências registradas".
- Contrato com o Abner, v2: um endpoint ou arquivo de pontuação de rotas `(h3_cell, metros)[] + hora → índice, %sem_dado, IC, decisão`. O snapshot v1 continua.
- Critério de aceite novo: D1 e D2 comparados às linhas de base com IC, no notebook e no MLflow.

## 6. Prazo e escopo realista

| Data | Marco |
|---|---|
| 16/11 | Congelamento. Proposta: congelar a v1 como está (entregável da rubrica original) e pré-registrar a v3. |
| 16–18/11 | Reextração; D1 com linhas de base e modelos; D2 com rotas (OSM ou contingência H3); notebook; MLflow; red-team. |
| 19/11 23h55 | Entrega |

Se o prazo apertar, o mínimo viável é D1 com linhas de base + modelo Poisson, e D2 com a pontuação aplicada às rotas da grade H3, ambos semi-cegos e declarados.

## 7. Decisões abertas para o Nando

1. Aceitar o reenquadramento (D1 + D2) e a mudança no escopo da especificação.
2. Perímetro: ampliar para cerca de 10×10 km ou manter 5×5.
3. Rotas para avaliação: baixar a malha do OpenStreetMap (dado público, uma vez) ou usar a grade H3.
4. Índice da rota por km (padrão proposto) ou total da rota.
5. Meta de alarmes do D1 (quantos alertas por km de caminhada são aceitáveis).
