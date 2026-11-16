# Research (Fase 0): Nível de risco registrado por célula H3 e faixa horária

**Data**: 2026-11-11 · **Spec**: [spec.md](spec.md)

Os números abaixo foram medidos de verdade sobre `ml/dados/interim/*.parquet` com um script de pesquisa (fora do repositório, só leitura). Eles se repetem no pipeline final e **não** valem como resultado do relatório, que só usa números do pipeline executado.

## Números medidos (perímetro 5×5 km, coordenada e hora válidas)

| Item | Valor |
|---|---|
| Registros válidos no perímetro | 20.657 |
| Fato anterior a 2026 ("fora da janela") | 307 |
| Fato em outubro/2026 ou depois | 0 |
| Registros na janela jan–set 2026 | 20.350 |
| Células H3 res. 9 com registro | 258 |
| Chaves (célula × faixa) com registro | 952 |
| Registros treino (jan–jul) / teste (ago–set) | 15.919 / 4.431 |
| Chaves com registro no treino / no teste | 933 / 739 |
| Registros por chave, treino: mediana, p25–p75 | 9, de 3 a 23 |
| Registros por chave, teste: mediana, p25–p75 | 3, de 2 a 8 |
| Chaves de teste com 1 só registro | 178 |
| Registros por mês, jan a set | 1.837; 2.216; 2.161; 2.233; 2.566; 2.598; 2.308; 2.330; 2.101 |

Distribuição **exploratória** (pesos da spec, cortes de quartil no treino reaplicados ao teste, mas com a **soma de pesos** de jan–jul para o treino e de ago–set para o teste, não a taxa mensal por origem de D-03/D-04). Os números do pipeline (T017) serão diferentes e são os que valem:

| Nível | Chaves de treino | Chaves de teste |
|---|---|---|
| 0 | 212 | 347 |
| 1 | 252 | 231 |
| 2 | 227 | 137 |
| 3 | 242 | 23 |

Cortes exploratórios da soma de pesos: 5, 14 e 35 (os cortes finais serão em pontuação mensal). Mesmo com quartis, o teste fica desbalanceado (47% das chaves no nível 0, só 23 no nível 3), porque ago–set tem menos meses que jan–jul. A spec já prevê isso como caso de borda. A seção "D-04" abaixo trata disso.

Rubricas sem regra de peso na janela, antes da decisão sobre feminicídio: **59 registros** (0,3%), por exemplo associação para o tráfico (20), posse de arma de uso restrito (13), porte de arma (9 e 4), morte suspeita (4), feminicídio (3), comunicação de óbito (2). Com feminicídio pontuando, restam **56**.

## Decisões

### D-01. Interpretador e bibliotecas
- **Decisão**: usar o `.venv311` (Python 3.11.15), que já tem h3 4.5.0, numpy 2.4.6, pandas 3.1.1, scikit-learn 1.9.1, xgboost 3.2.0, pytest 9.2.0, duckdb 2.0.0, pyarrow, nbconvert, nbformat e ipykernel. O `.venv` (3.9.6, só duckdb) sai de uso.
- **Achado**: `import xgboost` falhava nesta máquina por falta do OpenMP (`libomp.dylib`).
- **Decisão (Nando, 2026-11-11)**: instalar o `libomp` com Homebrew. Instalado e testado: o XGBoost 3.2.0 importa e treina no `.venv311`. O XGBoost fica como candidato; o `HistGradientBoostingClassifier` não é necessário.
- **Alternativas**: manter o 3.9.6 (rejeitado: pacotes antigos e Python do Xcode).
- **Observação**: a versão do duckdb difere entre os ambientes (1.4.5 no `.venv`, 2.0.0 no `.venv311`). Os scripts 00 e 01 devem rodar no `.venv311` e reproduzir as contagens de `qualidade_etapa1.txt` antes de seguir (T004).

### D-02. Dado e janela
- **Decisão**: `DATA_OCORRENCIA_BO` (número serial do Excel, 46023 = 2026-01-01) define o mês. Registros com fato fora de jan–set 2026 são "fora da janela" (307 no perímetro).
- **Faixa horária**: `HORA_OCORRENCIA_BO` é fração do dia em [0,1). Faixa por bordas explícitas [0,6), [6,12), [12,18), [18,21), [21,24), com 0 a 4 (noite quebrada em 2 a pedido do Abner, 2026-11-11; medido: 18–21h ~4,4 mil registros, 21–24h ~2,6 mil).
- **Célula**: `h3.latlng_to_cell(lat, lon, 9)`.
- **Contagem**: cada linha é um crime registrado. O parquet fica em `interim/` (fora do git, 36 MB).

### D-03. Construção do alvo e dos exemplos de treino (decisão que a clarificação deixou em aberto)
- **Decisão**: origens temporais móveis, com janela de rótulo de 2 meses, igual à do teste.

| Origem | Features (só registros até aqui) | Rótulo |
|---|---|---|
| T1 | jan–fev | mar–abr |
| T2 | jan–mar | abr–mai |
| T3 | jan–abr | mai–jun |
| T4 | jan–mai | jun–jul |
| Teste | jan–jul | ago–set |

- As features são taxas mensais (contagem dividida pelo número de meses da janela), para que janelas de tamanhos diferentes sejam comparáveis.
- A validação cruzada é por origem, com **expurgo**: o treino de cada dobra usa só origens cujo rótulo termina antes do início do rótulo validado, porque os rótulos de T1 a T4 se sobrepõem em abr, mai e jun. Dobras: T1→T3, T1–T2→T4. T2 não é validada (nenhum rótulo anterior sem sobreposição). Os cortes de quartil de cada dobra saem só dos rótulos do treino da dobra. Nunca embaralhada, só dentro do treino. O ajuste final usa T1 a T4.
- **Rationale**: o treino tem 7 meses; um único bloco daria ~1 mês de rótulo. As origens móveis aumentam os exemplos sem tocar em ago–set e mantêm o formato idêntico ao do teste.
- **Alternativas**: um bloco único jan–mai → jun–jul (poucos exemplos); janela mensal de 1 mês (rótulo quase aleatório, com 3 registros por chave).
- **Ressalva**: as taxas por janela de 2 meses ficam esparsas. O relatório declara a incerteza.

### D-04. Rótulo e desbalanceamento
- **Decisão**: pontuação = soma de pesos por chave ÷ n meses da janela ÷ horas da faixa (6, 6, 6, 3, 3), em pontos por mês por hora. Os três cortes de quartil vêm do conjunto de rótulos de treino (T1 a T4 juntos) e são fixos para o teste.
- **Métricas** (por desbalanceamento): macro-F1, balanced accuracy e erro absoluto médio de nível (o nível é ordinal). Acurácia simples só como informação.
- **Linhas de base**: (1) classe mais frequente; (2) persistência, que usa o nível da própria chave na janela de features como previsão.
- **"Sem dado" (decisão original, substituída em 2026-11-16):** a decisão de 2026-11-11 aceitava 1 registro como dado. Após o red-team de privacidade, o Nando aprovou a opção A: o contrato v2 publica como `sem_dado` toda chave com 0–2 registros (supressão k ≥ 3). Esta mudança não altera os universos internos de treino/teste do classificador.
  - Três situações distintas, não intercambiáveis: (1) chave com menos de três registros pontuáveis em jan–set → `sem_dado` no snapshot v2; (2) chave sem registro na janela de features de uma origem → fora do treino e do teste do classificador daquela origem; (3) chave com features e sem registro no rótulo → excluída da avaliação e contada em `resultados/` (viés de seleção).
- **Viés de seleção**: chave com features e sem registro no rótulo sai das métricas de nível; só 719 das 933 chaves de treino têm registro no teste. O relatório declara a contagem e o viés.
- **Nível do snapshot**: `pontuacao_mensal` = soma de pesos de jan–set ÷ 9 meses ÷ horas da faixa (comparável entre faixas de 3h e 6h; os rótulos de treino usam a mesma normalização); `nivel` aplica os 3 cortes do treino (D-04) a essa taxa. É o nível observado; `nivel_previsto` é a previsão de ago–set.

- **Registro (red-team, 2026-11-11):** a distribuição do teste (ago–set) foi vista na aprovação do T017. Cortes, pesos e critério (quartis só do treino) estavam fixados antes e não mudaram. Ago–set é avaliação exploratória, não confirmatória; a escolha do modelo usa só a CV do treino.

### D-05. Rubricas sem peso
- **Decisão**: feminicídio (3 registros) entra com **peso 5**, como homicídio (decisão do Nando, 2026-11-11). O que a spec não lista (56 registros na janela) fica **fora da pontuação**, sem peso inventado, e é contado no relatório como "rubrica sem peso", junto com o ilícito extrapenal.

### D-06. Modelos
- **Decisão**: executar baseline, Random Forest, XGBoost e MLP. Busca de ≥10 combinações de 3 hiperparâmetros por candidato, com a validação por origem de D-03.
- **LSTM e KMeans+PCA**: não executados. Justificativa a registrar no relatório: o LSTM pede séries longas, e aqui há só 4 origens por chave; KMeans+PCA é não supervisionado e não produz o nível. O relatório os declara como "não executados" e não inventa número.
- **Alternativa rejeitada**: forçar o LSTM só para constar. Com 4 passos de tempo e ~950 chaves, o resultado seria ruído.
- **Decisão (Nando, 2026-11-15)**: executar também LSTM (PyTorch) e KMeans+PCA (nível por cluster, mapa do treino), com o mesmo protocolo de CV. Como ago–set já tinha sido visto, constam como exploração adicional (`resultados/cv_exploracao_adicional.json`), sem substituir a seleção pré-registrada.
- **Atenção**: FR-010 e o briefing citam esses cinco modelos. Se a rubrica exige executar todos, essa decisão precisa de revisão do Nando.

### D-07. Formato do contrato com o Abner
- **Decisão**: CSV UTF-8 com cabeçalho, `manifest.json` e `.sha256`, mais uma fixture JSON pequena. Detalhes em [contracts/snapshot-risco.md](contracts/snapshot-risco.md).
- **Rationale**: a API do Abner é .NET; CSV e JSON abrem sem dependência extra. O Parquet fica interno.
- **O snapshot lista todas as células que cobrem o perímetro × 5 faixas**, com `sem_dado` explícito, para o app não precisar inferir ausência.
- **Alternativa rejeitada**: só linhas com dado (obriga o app a tratar ausência como 0, o que a constituição proíbe).

### D-08. Reprodutibilidade
- **Decisão**: sementes fixas, `requirements.txt` congelado com versões exatas, snapshot ordenado por (célula, faixa) e sem timestamp no conteúdo do CSV, para o checksum ser idêntico em duas execuções (SC-001). A data de geração vai só no `manifest.json`, fora do hash do CSV.

## Pendências que dependem do Nando
1. Se a rubrica exige executar LSTM e KMeans+PCA (D-06).
2. Distribuição dos níveis antes de aplicar o rótulo (T011).

Resolvidas em 2026-11-11: `libomp` instalado (D-01) e peso 5 para feminicídio (D-05).

Nenhum `NEEDS CLARIFICATION` no plano; decisões pendentes do responsável estão listadas em tasks.md (T027, T020a/b).
