# Proposta v3 — alerta de entrada e escolha de rota (rodada 2)

Status: **proposta, rodada 2** (15/11/2026, JARVIS). Revisa a r1 com a rodada 2 do red-team real (`REDTEAM-V3-rodada2.md`). As versões r0 e r1 ficam preservadas. Nada aqui foi implementado. Nada aqui altera a v1 pré-registrada (`selecao_modelo.json`), a v2, `SPEC-ML.md` nem `specs/001`. Mudança de especificação só com o aceite do Nando, numa spec nova (`specs/002`).

## 0. Veredito

Intenção do app (Nando, 15/11): (1) alertar a pessoa **antes** de entrar numa região com muitas ocorrências registradas; (2) entre 3–4 rotas de carro, escolher a de melhor índice de ocorrências.

**A solução atual não implementa nem valida nenhuma dessas duas decisões.** Ela tem insumos que uma decisão futura poderia usar, mas a decisão em si não existe.

| Necessidade | O que existe | O que falta |
|---|---|---|
| Alerta de entrada | O snapshot do app é o **mapa histórico observado** de jan–set/2026 (contrato v1, `natureza`: "não é previsão"). | Regra de alerta (limiar, orçamento de alertas, antecedência) e avaliação dessa regra. O classificador ML não entra no contrato do app. |
| Escolha entre rotas de carro | Nada. "Rota segura" está fora de escopo (`SPEC-ML.md` §11, FR-012). | Pontuação de rota, contrato com o app, avaliação de ordenação e um evento definido como relevante para quem está dentro de um carro. |

Desempenho, separado por grau de exposição do Teste:
- **v1 pré-registrada (cega):** RF macro-F1 0,467 em ago–set/2026, abaixo da persistência (0,491), em 847 chaves com rótulo. 290 chaves com features ficaram sem rótulo (`incerteza_custo.json`, `avaliacao_final.json`).
- **v2 exploratória (Teste já visto):** desenho A, RF regularizado 0,517 contra persistência 0,485, IC95% da diferença [0,007; 0,056] (`v2_historico.json`). Não é confirmação cega e não mede utilidade para alertar ninguém.

**O que a entrega de novembro pode e não pode ser (achado r2-5):**
- A entrega de 19/11 é **acadêmica e documental**: a v1 congelada, o diagnóstico da lacuna e, opcionalmente, análises exploratórias e um protótipo funcional **não validado**.
- **As duas decisões de produto não serão validadas até 19/11.** Validá-las exige dados que ainda não existem: um período futuro não visto, trajetos reais e a malha viária.
- A proposta não apresenta a fase 1 como implementação validada do produto.

## 1. Números reproduzíveis

Script: `scripts/medir_conduta_2026.py` → `ml/dados/resultados/conduta_local_2026.json`, com sha256 dos dois interim 2026.

| Universo | n | Via Pública | Conduta nula | Conduta de veículo¹ |
|---|---|---|---|---|
| Interim 2026, coordenada válida no perímetro (sem filtro de hora, data ou duplicata) | 34.771 | 30.991 (89%) | 15.334 (44%) | 1.745 (5,0%) |
| **Usadas na modelagem** (destino `usada`, jan–set/2026) | **20.343** | **18.091 (89%)** | **9.376 (46%)** | **1.391 (6,8%)** |

¹ "Veículo", "Interior de Veículo", "Aplicativo de Mobilidade Urbana", "Carga".

- **34.771 × 34.769 (achado 16).** O 34.769 vem de `ml/dados/qualidade_etapa1.txt`, uma medição exploratória de 11/11 feita direto no XLSX. O script dela não está no repositório. Com o interim e a ingestão atuais, os limites inclusivos e estritos do perímetro dão os mesmos 34.771, então a diferença não vem da borda. Ela **não pode ser reconciliada** sem o script original. Nenhum número de modelagem depende dela.
- `DESCR_CONDUTA` e `DESCR_SUBTIPOLOCAL` existem só em 2026.
- Por chave célula×faixa em ago–set/2026: 883 chaves, mediana de 3 registros, p90 = 12. Por célula, jan–set/2026: 258 células, mediana de 48,5. Que agregar reduza o erro de previsão é **hipótese**.

## 2. Reestruturação

### 2.1 Universo avaliável e cobertura (achado r2-1, BLOQUEANTE)

Não temos evidência externa de que a SSP "coletaria" uma ocorrência em cada chave. O que existe é só o histórico de registros. Por isso, "zero" nunca é tratado como "não houve": é sempre **zero registrado**, e a cobertura é definida na granularidade **célula × faixa**.

- **Universo primário U1 (cobertura por faixa):** chave célula×faixa com **≥ 1 registro pontuável na mesma faixa** nos 12 meses anteriores ao início da janela-alvo.
  - Na janela-alvo, cada chave de U1 recebe a sua contagem, inclusive **zero registrado**.
  - O critério usa só o passado, então não depende do alvo.
- **Sensibilidade, obrigatória e sempre lado a lado com U1:**
  - **U0:** só chaves com registro na janela-alvo. É o recorte da v1, que exclui os zeros e é viesado para onde houve crime.
  - **U2:** todas as células do perímetro × 5 faixas, com zero onde não houver registro.

  Se a conclusão mudar entre U0, U1 e U2, ela é declarada **frágil**.
- `sem_dado` = chave fora de U1. Fica fora das métricas e é contada. `fora_da_cobertura` = fora do perímetro.
- O snapshot v1 do app não muda.

### 2.2 T-A: ordenação espacial para alerta (achados 6, 11, r2-2 e r2-3)

**Na fase 1, T-A é descritiva, sem inferência.** O desenho inferencial vai para o pré-registro da fase 2.

**Fórmula do alvo:** pontuação da chave na janela-alvo = Σ pesos v1 ÷ meses da janela ÷ horas da faixa, a mesma de `rotulo.pontuacao_mensal`. Zero registrado = 0.

**Escore de ordenação, calculado só com o passado:**
- persistência: a pontuação da janela imediatamente anterior;
- média histórica: a pontuação média de todas as janelas desde jan/2023 até o início do alvo;
- suavizada: (1−λ)·própria + λ·média das vizinhas H3 (k=1), com λ ∈ {0; 0,25; 0,5; 0,75} escolhido em origens anteriores à primeira origem avaliada;
- RF regularizado (classificador de níveis): **E[nível] = Σₖ k·P(nível=k)**, a esperança da classe prevista.

**Desempate:** pela média histórica e depois pelo id H3 em ordem crescente.

**Métrica primária:** hit rate a 10% = Σ pontuação-alvo das ⌈0,10·N⌉ chaves de maior escore ÷ Σ pontuação-alvo de todas as N chaves avaliáveis. Uma origem com denominador 0 é excluída e contada.

**Origens:** janelas-alvo bimestrais e consecutivas de mar–abr/2024 a jul–ago/2026, todas com ≥ 12 meses de passado. Ago–set/2026 é reportada à parte e marcada como já vista.

**Saída:**
- por origem: o hit rate de cada método e o número de origens em que cada um supera a persistência;
- curva de hit rate × % da área (5–30%);
- o mesmo em U0 e U2.

**Sem IC, sem teste de hipótese e sem afirmação de superioridade.** A dependência entre origens que se sobrepõem no passado e o pequeno número de blocos espaciais independentes (9 blocos res. 7 na v2) não sustentam inferência.

### 2.3 T-B: comparação de rotas (achados 7–10 e 12, r2-4)

- **Evento:** "ocorrências registradas em via pública ao longo do trajeto". **Não** é risco para motorista. Um índice para motorista exige definir o evento com cobertura histórica (hoje 6,8% de conduta de veículo, 46% nula, só em 2026) e fica para a fase 2.
- **Métrica primária da decisão:** **total esperado no trajeto** = Σ (pontuação da célula na faixa × comprimento percorrido na célula), só entre rotas do **mesmo** par origem-destino. Ocorrências/km é sensibilidade.
- **Avaliação de ordenação (fase 2):** *regret* pareado contra a rota mais curta, a persistência e a média histórica, em rotas de rede viária congelada (OSM com hash; algoritmo e parâmetros congelados; comprimento percorrido por célula a partir da geometria da via).
- **Abstenção (achado r2-4):**
  - **retirada da fase 1.** Uma probabilidade "esta rota é a de menor total" exige uma distribuição **preditiva** conjunta das rotas no momento da escolha, e bootstrap de totais realizados não fornece isso;
  - na fase 2, o pré-registro define essa distribuição (por exemplo, uma contagem com sobredispersão por célula, somada no trajeto com as células compartilhadas contadas uma vez) e valida a calibração dela em origens passadas, pela cobertura dos intervalos preditivos, antes de qualquer limiar;
  - até lá, **nenhuma regra de abstenção é apresentada como validada**.
- **Fase 1:** só a demonstração descrita no §4.

### 2.4 Linguagem e interface

- Sempre "ocorrências registradas", com janela, cobertura e "retrospectivo" junto do número.
- Nunca "seguro", "perigoso", "risco pessoal" nem "tempo real".
- Sem rótulos de bairro.
- Viés de exposição e subnotificação declarados.

## 3. Status do Teste

- Todo resultado novo em jan–set/2026 é **exploratório** (`test_seen=true`). Não existe teste cego em 2026.
- **Pré-registro da fase 2,** antes de out–nov/2026 ser publicado, em `specs/002` e num `pre_registro_v3.json` com hash:
  - universo (U1) e sensibilidades;
  - fórmulas, escores e desempate;
  - janelas;
  - modelo único;
  - métrica primária e linhas de base;
  - desenho inferencial: número mínimo de unidades independentes; se não for atingido, o resultado é só descritivo;
  - distribuição preditiva de T-B com o teste de calibração;
  - hash do dado e do código.

## 4. Escopo e prazo (achados 13, r2-5 e r2-6)

**Obrigatório até 16/11 (congelamento), cerca de 3–4 h:**

| Item | Estimativa |
|---|---|
| v1 congelada sem mudança | 0 |
| Notebook, seção 9 "Da previsão retrospectiva à decisão no app": §0, §1, U0/U1/U2 em texto, desenho da fase 2 e o que não se afirma, gerado por `scripts/gerar_notebook.py` | 1,5 h |
| Gerar, executar e conferir o notebook | 0,5 h |
| Red-team real até 0 BLOQUEANTE / 0 ALTA (1–2 rodadas de cerca de 10 min + correções) | 1–1,5 h |
| Commit | 5 min |

**Opcional, só se o obrigatório fechar antes, sem compromisso de prazo (exploratório, `test_seen=true`):**

| Item | Estimativa |
|---|---|
| T-A descritiva (§2.2) sobre `usadas_v2.parquet`, sem dado novo, com `scripts/` e um JSON de resultados | 3–4 h |
| Registro MLflow no experimento `hoodi-v3-exploratorio` (tags de proveniência + `test_seen`, `alvo`, `janela`, `universo`, `cobertura`), prints e seção 10 | 1,5 h |
| **Protótipo funcional não validado** da pontuação de rota: uma função pura `(h3_cell, metros)[] + faixa → total no trajeto, % sem_dado`, sobre o snapshot v1 (mapa observado, não previsão), com testes e 3 rotas de exemplo; rotulado "demonstração, não validado" | 1,5 h |
| Red-team da parte opcional | 1 h |

**Cortado até 19/11 (fase 2):** reextração do histórico com conduta, ampliação do perímetro, malha OSM, modelos novos, abstenção probabilística, contrato v2 com o Abner e índice para motorista.

## 5. Notebook e MLflow (requisito do Nando)

- O notebook continua gerado a partir de resultados salvos, no padrão escolha → evidência → leitura, com rastreabilidade. As seções 1–8 ficam intactas.
- No MLflow, v1 e v2 são preservados; execuções novas entram como exploratórias, com hash do dado e do código. Não há run para etapa não executada nem modelo de produção.

## 6. Decisões do Nando

1. Aceitar a entrega de novembro como acadêmica e documental, com a v1 congelada e a seção 9, deixando a validação do produto para a fase 2.
2. Partes opcionais: nenhuma; só T-A descritiva; ou T-A + protótipo de rota não validado.
3. Abrir a `specs/002` (fase 2) depois da entrega.
