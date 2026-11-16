# Feature Specification: Nível de risco registrado por célula H3 e faixa horária

**Feature Branch**: `001-risco-h3-faixa-horaria` (repositório sem git; o nome é só o identificador da feature)

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Dada uma célula H3 resolução 9 e uma faixa horária, qual é o nível de risco registrado? Usar a base oficial SSP-SP 2026, perímetro 5×5 km em torno da FIAP Paulista, nível 0–3, com divisão temporal treino/teste. Decisões fechadas na grill-me de 2026-11-10/11 e detalhadas em docs/SPEC-ML.md."

Constituição aplicável: `.specify/memory/constitution.md` v1.2.0. Detalhes e números medidos: `docs/SPEC-ML.md`.

## Clarifications

### Session 2026-11-11

- Q: Como os níveis 0, 1, 2 e 3 são formados a partir da pontuação, se o texto dizia "tercis"? → A: Quartis entre as chaves com dado (25% das chaves em cada nível, de 0 = menor pontuação a 3 = maior).
- Q: O que o modelo prevê, exatamente? → A: O nível de cada chave em ago–set, usando só informação de jan–jul; o rótulo de teste vem só de registros de ago–set; as features de qualquer exemplo usam apenas registros anteriores ao período do seu rótulo.
- Q: O que fazer com as rubricas sem peso definido? → A: Tráfico, drogas para consumo e lesão corporal culposa no trânsito entram com peso 1; ilícito extrapenal fica fora da pontuação e é contado no relatório como "rubrica sem peso".
- Decisão do Nando (fora do loop de perguntas): feminicídio entra com peso 5, como homicídio.
- Q: Os cortes dos quartis no teste vêm do treino ou de ago–set? → A: Cortes calculados só com o treino (jan–jul) e reaplicados ao teste.
- Q: Qual data define o mês no split e o que fazer com fatos anteriores a 2026? → A: Data do fato. Registros com fato fora de jan–set 2026 ficam fora da modelagem e entram na reconciliação como "fora da janela".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Contrato de risco para o app (Priority: P1)

O app do Abner precisa, para cada célula H3 e faixa horária do perímetro, de um nível de risco de 0 a 3 ou de "sem dado", num snapshot versionado com checksum.

**Why this priority**: o contrato com o Abner (chave de risco, janela do snapshot, fixture) vence em 11/11 às 12h e a rota/fixture às 20h.

**Independent Test**: gerar o snapshot e uma fixture pequena, e conferir que cada chave (célula + faixa) tem nível 0–3 ou "sem dado", sem nenhum outro valor.

**Acceptance Scenarios**:

1. **Given** a base oficial com checksum declarado, **When** o pipeline é executado, **Then** o snapshot é gerado com checksum e a janela de dados declarada.
2. **Given** uma célula sem registros utilizáveis, **When** o snapshot é consultado, **Then** ela aparece como "sem dado" e nunca como nível 0.
3. **Given** o pipeline executado duas vezes sobre o mesmo raw, **When** os snapshots são comparados, **Then** os checksums são idênticos.

---

### User Story 2 - Qualidade e quarentena dos dados (Priority: P1)

O Nando precisa saber quanto do dado é utilizável e o que foi isolado, para declarar o limite do modelo no relatório.

**Why this priority**: a rubrica do briefing exige honestidade sobre o dado, e o indicador "% de dado utilizável" depende disso.

**Independent Test**: reconciliar as contagens: linhas de entrada = linhas usadas + quarentena + duplicata removida + fora da janela.

**Acceptance Scenarios**:

1. **Given** registros sem coordenada ou sem hora válida, **When** a ingestão roda, **Then** eles vão para a quarentena sinalizados, e não são descartados.
2. **Given** um BO com coordenada ou hora conflitante entre linhas, **When** a ingestão roda, **Then** ele vai para a quarentena.
3. **Given** uma linha idêntica de mesmo BO e rubrica, **When** a ingestão roda, **Then** só ela é removida; BOs com vários crimes mantêm uma linha por crime.

---

### User Story 3 - Modelo avaliado com controle de vazamento temporal (Priority: P2)

O Nando precisa de um modelo escolhido com justificativa, comparado a uma linha de base, com métricas de treino e teste lado a lado.

**Why this priority**: é o núcleo da rubrica de ML (≥10 combinações, CV só no treino, discussão de overfitting).

**Independent Test**: conferir que nenhuma data de teste é anterior à última de treino e que o relatório só cita números produzidos por execução.

**Acceptance Scenarios**:

1. **Given** treino de jan a jul e teste de ago a set, **When** o modelo é avaliado, **Then** as métricas de treino e de teste aparecem lado a lado.
2. **Given** a busca de hiperparâmetros, **When** ela roda, **Then** ao menos 10 combinações de 3 hiperparâmetros são avaliadas por validação cruzada somente no treino.
3. **Given** as features de um exemplo de teste, **When** elas são calculadas, **Then** nenhum registro de ago–set entra nelas.

---

### User Story 4 - Entrega auditável (Priority: P2)

O Nando precisa entregar repositório, notebook executado, relatório e prompts, com revisão red-team real antes da entrega final; cada envio intermediário é coberto pela rodada vigente do artefato enviado, e todo envio, sempre com a confirmação do Nando.

**Why this priority**: sem a entrega auditável, os resultados não contam para a rubrica.

**Independent Test**: checar a lista de entregáveis e anexar o relatório real do Codex CLI.

**Acceptance Scenarios**:

1. **Given** o repositório pronto, **When** a revisão red-team real é executada, **Then** os achados e correções ficam registrados antes da entrega.

---

### Edge Cases

- Célula com poucos registros: os universos internos de treino e teste continuam avaliando as chaves elegíveis do protocolo original. No **snapshot público v2**, porém, aplica-se k ≥ 3: chave com 0–2 registros é publicada como `sem_dado`, contagem 0 e sem nível/pontuação. A associação das chaves suprimidas não é entregue.
- Chave com features e sem registro na janela do rótulo fica fora das métricas de nível (viés de seleção: só se avalia onde houve crime); o relatório declara a contagem de chaves excluídas e esse viés.
- Registro com hora fora de [0,1) ou coordenada fora do retângulo de SP: quarentena.
- Faixa horária sem registros numa célula que tem dado em outras faixas: "sem dado" naquela chave.
- Classes desbalanceadas entre treino e teste, mesmo com quartis: declarar no relatório e usar métricas adequadas.
- Pesos de crime são ponto de partida e não verdade; o relatório precisa dizer isso.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST usar somente a base oficial SSP-SP 2026, com fonte, arquivo e sha256 declarados, sem dado simulado.
- **FR-002**: O sistema MUST manter o raw imutável e produzir ingestão idempotente.
- **FR-003**: O sistema MUST recortar o perímetro de 5×5 km em torno da FIAP Paulista e atribuir cada registro a uma célula H3 res. 9 e a uma de 5 faixas (0–6, 6–12, 12–18, 18–21, 21–24).
- **FR-004**: O sistema MUST enviar à quarentena sinalizada registros sem coordenada ou hora utilizável e BOs com coordenada ou hora conflitante, e reportar a perda como "% de dado utilizável".
- **FR-005**: O sistema MUST tratar cada linha como um crime registrado, removendo apenas a linha idêntica de mesmo BO e rubrica.
- **FR-006**: O sistema MUST calcular a pontuação da chave (célula + faixa) pela soma de pesos iniciais por crime, dividida pelo número de meses da janela e pelas horas da faixa (6, 6, 6, 3 e 3), na mesma fórmula para treino, teste e snapshot, (furto 1; roubo e lesão corporal 3; homicídio, feminicídio e estupro 5; tráfico, drogas para consumo e lesão corporal culposa no trânsito 1; ilícito extrapenal sem peso, fora da pontuação e contado no relatório) e converter em níveis 0–3 por quartis entre as chaves com dado do treino (nível 0 = quartil de menor pontuação; nível 3 = quartil de maior pontuação). Os cortes MUST ser calculados só com o treino (jan–jul) e reaplicados ao teste (ago–set).
- **FR-007**: O sistema MUST representar "sem dado" fora da escala 0–3.
- **FR-008**: O sistema MUST mostrar a distribuição real dos níveis ao Nando antes de aplicar o rótulo.
- **FR-009**: O sistema MUST dividir treino (jan–jul) e teste (ago–set) por tempo, usando a data do fato (registros com fato fora de jan–set 2026 ficam fora da modelagem e são contados como "fora da janela") e usar validação cruzada só no treino. O backtest é **retrospectivo**: o split pela data do fato, a construção das features e o ajuste das transformações apenas no treino de cada dobra controlam o vazamento temporal (plan.md, princípio V), mas não prova que o dado já existia na origem na época (só há o arquivo atualizado em 28/10/2026). O relatório não afirma "ausência de vazamento". Ago–set é **avaliação exploratória**: a distribuição do teste foi vista na aprovação do T017, e cortes, pesos e critério já estavam fixados só com o treino e não mudaram depois. O alvo é o nível da chave em ago–set; as features de qualquer exemplo MUST usar apenas registros anteriores ao período do seu rótulo, e o rótulo de teste MUST vir só de registros de ago–set. Na validação cruzada, o treino de cada dobra MUST usar só origens cujo rótulo termina antes do início do rótulo validado (validação com expurgo, sem sobreposição de rótulo).
- **FR-010**: O sistema MUST comparar com uma linha de base simples, avaliar ao menos 10 combinações de 3 hiperparâmetros e justificar o modelo escolhido entre XGBoost, RF, MLP, LSTM e KMeans+PCA. Planejados (T025 aberto): RF, XGBoost e MLP; LSTM e KMeans+PCA são declarados "não executados" com justificativa, sujeito à confirmação do Nando (research D-06).
- **FR-011**: O sistema MUST gerar snapshot versionado com checksum e uma fixture para o contrato com o Abner.
- **FR-012**: O relatório MUST conter apenas números rastreáveis a execuções reais e MUST evitar "tempo real" e "rota/local seguro".
- **FR-013**: O sistema MUST NOT conter, nos derivados e nas entregas, campo que identifique pessoa (constituição VII, v1.2.0; inventário por camada em `ml/dados/README.md`); raw e interim ficam fora do git e sem entrega; nada é enviado ou publicado sem confirmação do Nando.

### Key Entities

- **Registro de ocorrência**: uma linha da base, um crime registrado, com BO, rubrica, data, hora e coordenada.
- **Chave de risco**: célula H3 res. 9 + faixa horária.
- **Nível de risco**: 0–3, ou "sem dado".
- **Snapshot**: tabela versionada de chaves e níveis, com janela de dados e checksum.
- **Quarentena**: registros isolados com o motivo.
- **Destino**: um por linha: `usada`, `quarentena`, `duplicata_removida` ou `fora_da_janela`.
- **Origem e janela**: par (janela de features, janela de rótulo de 2 meses) que forma um exemplo; T1 a T4 no treino e Teste em ago–set.
- **Peso por rubrica**: valor de pontuação do crime; rubrica sem peso fica fora da pontuação e é contada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Duas ingestões do mesmo raw geram snapshots com checksum idêntico.
- **SC-002**: 100% das linhas de entrada são reconciliadas: usadas + quarentena + duplicata removida + fora da janela.
- **SC-003**: Nenhuma data de teste é anterior à última data de treino, nenhuma data de feature é igual ou posterior ao início do rótulo, e as transformações são ajustadas só no treino de cada dobra (controle temporal por data do fato; backtest retrospectivo).
- **SC-004**: Nenhuma chave "sem dado" aparece com nível 0 no snapshot.
- **SC-005**: Toda métrica do relatório é reproduzida pela execução do notebook.
- **SC-006**: Os seis critérios de aceite A1–A6 de `docs/SPEC-ML.md` §7 são atendidos até 16/11 (congelamento) e 19/11 às 23h55 (entrega).

## Assumptions

- O centro do perímetro é aproximado (-23,5646; -46,6522); a coordenada exata da FIAP Paulista está pendente e não altera o perímetro de 5×5 km de forma relevante (~50 m).
- Os pesos iniciais (furto 1; roubo e lesão corporal 3; homicídio, feminicídio e estupro 5; tráfico, drogas para consumo e lesão corporal culposa no trânsito 1) são ponto de partida, sujeitos à sua revisão. Ilícito extrapenal (49 registros no perímetro) fica fora da pontuação.
- A base cobre ocorrências até 30/09/2026; o mês de setembro pode estar incompleto (~73 mil contra ~85 mil por mês; hipótese, sem evidência de cobertura) e isso é declarado.
- O app e a API do Abner ficam fora deste repositório; o contrato é a chave de risco, o snapshot e a fixture.
- Fora de escopo: campo que identifique pessoa nos derivados e entregas, "tempo real", "rota segura", qualquer envio sem confirmação.
