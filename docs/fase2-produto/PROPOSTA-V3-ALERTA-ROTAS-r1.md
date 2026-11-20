# Proposta v3 — alerta de entrada e escolha de rota (rodada 1)

Status: **proposta, rodada 1** (15/11/2026, JARVIS). Revisa a `PROPOSTA-V3-ALERTA-ROTAS-r0.md`, que fica preservada, com os 17 achados do red-team real (`REDTEAM-V3-rodada1.md`). Nada aqui foi implementado. Nada aqui altera a v1 pré-registrada (`selecao_modelo.json`), a v2, `SPEC-ML.md` nem `specs/001`. Mudança de especificação só com o aceite do Nando, numa spec nova (`specs/002`).

## 0. Veredito (delimitado — achados 1 e 2)

Intenção do app (Nando, 15/11): (1) alertar a pessoa **antes** de entrar numa região com muitas ocorrências registradas; (2) entre 3–4 rotas de carro, escolher a de melhor índice de ocorrências.

**A solução atual não implementa nem valida nenhuma dessas duas decisões.** Ela tem insumos que uma decisão futura poderia usar, mas a decisão em si não existe:

| Necessidade | O que existe | O que falta |
|---|---|---|
| Alerta de entrada | O snapshot do app é o **mapa histórico observado** de jan–set/2026 (contrato v1, `natureza`: "não é previsão"). Ele já permite ao app mostrar "esta área teve muitas ocorrências registradas". | Regra de alerta (limiar, orçamento de alertas, antecedência) e avaliação dessa regra. O classificador ML (nível 0–3 no bimestre seguinte) não entra no contrato do app. |
| Escolha entre rotas de carro | Nada. "Rota segura" está fora de escopo (`SPEC-ML.md` §11, FR-012). | Pontuação de rota, contrato com o app, avaliação de ordenação de rotas e um evento definido como relevante para quem está **dentro de um carro**. |

Desempenho, separado por grau de exposição do Teste:
- **v1 pré-registrada (cega):** RF macro-F1 0,467 em ago–set/2026, abaixo da persistência (0,491), em 847 chaves com rótulo; 290 chaves com features ficaram sem rótulo (`incerteza_custo.json`, `teste`).
- **v2 exploratória (Teste já visto):** no desenho A, RF regularizado 0,517 contra persistência 0,485, com IC da diferença acima de zero (`v2_historico.json`, `A_mesmo_alvo`, `comparacao_primaria`). Não é confirmação cega e não mede utilidade para alertar ninguém.

## 1. Números da proposta, reproduzíveis (achados 15–17)

Script: `scripts/medir_conduta_2026.py` → `ml/dados/resultados/conduta_local_2026.json`, com sha256 dos dois interim 2026. Os universos têm denominador explícito:

| Universo | n | Via Pública | Conduta nula | Conduta de veículo¹ |
|---|---|---|---|---|
| Interim 2026, coordenada válida no perímetro (sem filtro de hora, data ou duplicata) | 34.771 | 30.991 (89%) | 15.334 (44%) | 1.745 (5,0%) |
| **Usadas na modelagem** (destino `usada`, jan–set/2026) | **20.343** | **18.091 (89%)** | **9.376 (46%)** | **1.391 (6,8%)** |

¹ "Veículo", "Interior de Veículo", "Aplicativo de Mobilidade Urbana", "Carga".

- O `SPEC-ML.md` §3 registra 34.769 "com coordenada" (medido em 11/11 por outro filtro). A diferença de 2 linhas **não foi reconciliada** e não afeta nenhum número de modelagem: estes saem do universo "usadas".
- `DESCR_CONDUTA` e `DESCR_SUBTIPOLOCAL` existem só em 2026; o interim 2023–2025 foi gravado sem elas.
- Por chave célula×faixa em ago–set/2026: 883 chaves, mediana de 3 registros, p90 = 12. Por célula, todas as faixas somadas, jan–set/2026: 258 células, mediana de 48,5 (`usadas_v2.parquet`; conferido pelo red-team). Isso **mostra** a baixa contagem. Que agregar reduza o erro de previsão é **hipótese**.

## 2. Reestruturação: duas tarefas, cada uma com alvo, universo, métrica primária e abstenção

### 2.1 Universo avaliável (achado 4, BLOQUEANTE na r0)

Painel completo de **células H3 res. 9 do perímetro × 5 faixas × janela**, com três status distintos:
- `zero_observado`: célula **coberta**, sem registro pontuável na janela. Entra na avaliação como 0 registrado, que é diferente de 0 ocorrido.
- `sem_dado`: célula do perímetro **não coberta**. Critério proposto: nenhum registro com coordenada em nenhuma janela anterior ao alvo (sem histórico de registro, não dá para distinguir "não houve" de "não se registra ali"). Fica fora das métricas e é contado.
- `fora_da_cobertura`: fora do perímetro.

As métricas são sempre reportadas com a cobertura (% de chaves avaliáveis e % da extensão de rota avaliável). O critério de "coberta" é fixado antes de qualquer avaliação. Para continuar compatível, o snapshot v1 mantém o seu `sem_dado` = nenhum registro na chave.

### 2.2 T-A: ordenação espacial para alerta (achados 5, 6 e 11)

- **Alvo:** contagem ponderada de ocorrências registradas por chave (célula×faixa) na janela futura, com a fórmula v1, no painel 2.1.
- **Métrica primária (uma só):** *hit rate* com área fixa de 10% das chaves avaliáveis, ou seja, a % da pontuação futura capturada pelas chaves do topo previsto. Pareada contra as linhas de base.
- **Linhas de base, todas calculadas só com o passado do alvo:**
  1. persistência (janela anterior);
  2. taxa média histórica até o início do alvo;
  3. média suavizada com as vizinhas, com peso escolhido só em validação temporal.
- **Candidato de modelo:** **um** só, o RF regularizado já existente, usado como ordenador. Sem modelos novos (Poisson/Tweedie, encolhimento empírico-bayesiano, LSTM) até haver avaliação confiável das linhas de base. Esses ficam para a fase 2.
- **IC:** bootstrap pareado em blocos espaciais (res. 7) × origens temporais. Secundárias (precisão e *recall* no topo 10%, PAI, área alertada, cobertura) com correção de Holm explícita.
- **Política de alerta ≠ ordenação.** Orçamento de alertas por km e antecedência exigem trajetos reais de caminhada, que **não temos**. Sem eles, a conclusão se limita a "concentração futura capturada por área fixa" e **não** se afirma desempenho de alerta para uma pessoa.

### 2.3 T-B: comparação de rotas (achados 7, 8, 9, 10 e 12)

- **Evento:** "ocorrências registradas em via pública ao longo do trajeto". **Não** é risco para motorista nem para ocupante, e assim deve ser nomeado. Um índice específico para motorista exige definir o evento (por exemplo, conduta de veículo) com cobertura histórica, que hoje é 6,8% dos registros, com 46% de conduta nula e só em 2026. Fica para a fase 2.
- **Métrica primária da decisão:** **total esperado no trajeto** = Σ (índice da célula na faixa × comprimento percorrido na célula), comparando só rotas do **mesmo** par origem-destino. Ocorrências/km é análise de sensibilidade.
- **Avaliação de ordenação:** *regret* pareado (total realizado da rota escolhida − total realizado da melhor rota do par), contra a rota mais curta, a persistência e a média histórica.
- **Abstenção (achado 10):** bootstrap **conjunto** das rotas do mesmo par, nos mesmos blocos espaço-temporais, porque as rotas compartilham células. O app só ordena se P(rota escolhida é a de menor total) ≥ 0,8, limiar fixado antes. Caso contrário, mostra "sem diferença clara nas ocorrências registradas". Sobreposição de intervalos não é usada como critério.
- **Rotas (achado 12):** uma avaliação real exige rede viária congelada (OSM, com hash), algoritmo e parâmetros congelados, e comprimento percorrido por célula a partir da geometria da via. **Isso fica para a fase 2.** Na fase 1 só existe uma **demonstração** sobre rotas fixas de exemplo, rotulada "não validada", sem alegação de navegação.

### 2.4 Linguagem e interface (achados 9 e 14)

- Sempre "ocorrências registradas", com janela, cobertura e "retrospectivo" junto do número. Nunca "seguro", "perigoso", "risco pessoal" nem "tempo real".
- Não rotular bairros. A informação aparece agregada por célula ou trajeto.
- Quando a cobertura ou a diferença são insuficientes, o app se abstém.
- Viés de exposição declarado: o registro reflete movimento de pessoas e veículos e subnotificação; não é taxa por pessoa, veículo ou tempo de exposição.

## 3. Status do Teste (achado 3, BLOQUEANTE na r0)

- **Todo resultado novo em jan–set/2026 é exploratório**, com `test_seen=true` no MLflow. Não existe teste cego em 2026 e o termo "semi-cego" foi retirado.
- **Pré-registro para o teste futuro:** antes de out–nov/2026 ser publicado, congelar em `specs/002` e num `pre_registro_v3.json` com hash:
  - alvo, universo e critério de cobertura;
  - janelas;
  - o modelo único;
  - métrica primária, linhas de base, regra de abstenção e método de IC;
  - hash do dado e do código.

  out–nov/2026 fica intocado até lá. O teste acontece depois da entrega e é declarado como trabalho futuro.

## 4. Escopo por fase (achado 13)

**Fase 1 — até 19/11 (cabe no prazo; nada de dado novo):**
1. A v1 congelada é o entregável da rubrica, sem mudança no pipeline, snapshot, contrato v1 ou resultados.
2. **Notebook, seção 9 "Da previsão retrospectiva à decisão no app":** as lacunas deste §0, os números reproduzíveis do §1, o desenho da fase 2 e o que **não** se pode afirmar. Sai de `scripts/gerar_notebook.py` e lê só arquivos salvos.
3. **Opcional, se o tempo permitir (exploratório, `test_seen=true`):**
   - T-A com as 3 linhas de base + o RF regularizado na métrica primária, sobre o painel do §2.1, só com os dados já processados;
   - T-B como demonstração estática em 3 pares de rotas de exemplo, rotulada "não validada".

   Ambos ficam num experimento MLflow `hoodi-v3-exploratorio`, com as tags de proveniência existentes mais `test_seen`, `alvo`, `janela`, `universo` e `cobertura`.
4. Red-team real até não sobrar bloqueante nem ALTA.

**Cortado da fase 1** (vai para a fase 2): reextração do histórico com conduta, ampliação do perímetro, malha OSM, modelos novos, endpoint e contrato v2 com o Abner, índice específico para motorista.

**Fase 2 — depois da entrega:** `specs/002` aceita pelo Nando, pré-registro, reextração, rede viária, modelos novos e o teste em out–nov/2026.

## 5. Notebook e MLflow (requisito do Nando)

- O notebook continua gerado por `scripts/gerar_notebook.py` a partir de resultados salvos, no padrão escolha → evidência → leitura, com rastreabilidade. As seções 1–8 ficam intactas.
- MLflow:
  - os experimentos v1 e v2 são preservados;
  - toda execução nova é registrada como exploratória, com hash do dado e do código e só com métricas efetivamente calculadas;
  - nenhum run para etapa não executada;
  - nada registrado como modelo de produção.

## 6. Decisões do Nando

1. Aceitar a fase 1 como acima (v1 congelada + seção 9; a parte opcional, sim ou não).
2. Aceitar que T-B nomeia o evento "ocorrências em via pública no trajeto", e não risco ao motorista, até a fase 2.
3. Abrir a `specs/002` (fase 2) depois da entrega.
