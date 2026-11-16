# Plano de execução v3: alerta e rotas na arquitetura decidida (rodada 1)

**Status:** plano, rodada 1 (15/11/2026, JARVIS). Nada aqui foi implementado.

**De onde vem esta rodada:**
- Revisa a `PLANO-EXECUCAO-V3-r0.md`, que fica preservada, com os 9 achados do red-team real em `REDTEAM-PLANO-V3-rodada1.md`.
- O método vem da `PROPOSTA-V3-ALERTA-ROTAS-r3.md`: universos, linguagem, status do Teste e fase 2.

**O que este plano acrescenta à r3:**
- onde cada decisão do app roda na arquitetura decidida;
- a ordem de execução.

**O que este plano não toca:** `selecao_modelo.json`, a v1, a v2, `SPEC-ML.md`, `specs/001` e o contrato v1.

## 0. Escopo: o mesmo da r3 (achados 1 e 9)

**Obrigatório até o congelamento de 16/11:** o mesmo da r3 §4, ou seja, a v1 congelada, a seção 9 do notebook e o red-team.

**Opcional, os blocos A, B e C da §4:**
- Cada bloco é uma **demonstração retrospectiva exploratória**: `test_seen=true`, não validada e sem promessa de comportamento de produto.
- Cada bloco só entra com a **decisão 2 do Nando** (r3 §6), que continua aberta.
- O que não estiver commitado até 16/11 23h vai para a fase 2. Isso não quebra o congelamento.

## 1. Arquitetura decidida

Fontes: documento mestre hoodi, `specs/001-risco-h3-faixa-horaria/plan.md` e `contracts/snapshot-risco.md`.

```
SSP-SP XLSX ──► pipeline ML (Python, lote, offline) ──► snapshot v1 + manifest + sha256
                                                              │
                                                              ▼
                                          API .NET (Abner): ingere e serve o snapshot;
                                          contexto Rotas (RouteRequest/RouteSuggestion, RF-07)
                                                              │  download periódico (RF-04)
                                                              ▼
                                          App Expo: geofencing local, alerta offline (RNF-03),
                                          notificação do celular → smartwatch / hoodi Pet
```

Este plano parte de decisões já tomadas e não introduz nenhuma nova:
- O ML **não** vira serviço. Ele entrega artefatos versionados com checksum.
- O alerta é avaliado **no aparelho**, a partir do último snapshot.
- A rota é calculada pela **API**. O motor de rotas **não foi escolhido**.
- Tudo o que for novo é **aditivo** e fica em `docs/contratos-v3/`, independente do contrato v1 e de `specs/001` (achado 8).

## 2. Artefatos, donos e integração (achado 6)

| Artefato | Dono da definição | Dono da execução em produção | Versionamento e vínculo | Entrega |
|---|---|---|---|---|
| Snapshot v1 (existente) | ML | API serve, app consome | `csv_sha256` no manifest | sem mudança |
| Política de proximidade (bloco A) | ML | App | `politica_proximidade_v1.json` carrega `snapshot_csv_sha256`. O app só aplica a política se esse hash bater com o do snapshot carregado; se não bater, não alerta e registra o erro. | arquivo ao lado do snapshot. A forma como a API serve o arquivo depende do Abner |
| Pontuação de rota (bloco B) | ML: especificação, referência Python e vetores-ouro | API, em C# | `rota_pontuacao_v1.md` + `vetores_rota_v1.json`, com sha256 | **referência para validação**. Não é integração |

**Dependências externas, fora do cronograma deste plano e da responsabilidade do ML:**
1. motor de rotas;
2. contrato HTTP de rotas (endpoint, payload);
3. implementação em C# e o teste dela contra os vetores-ouro;
4. como a API serve a política;
5. consumo dos arquivos no app.

Nada disso é apresentado como concluído. O envio do material ao Abner só acontece com a confirmação do Nando.

## 3. Bloco A: política de proximidade (opcional; achados 2, 4, 5 e 7)

O nome é **alerta por proximidade**, não "alerta antecipado de entrada". Ele avisa quando a pessoa está numa célula vizinha a uma célula elegível. A antecedência fica limitada a cerca de uma célula: a aresta média de H3 res. 9 é de ~201 m, medida com `h3.average_hexagon_edge_length(9)`. Um alerta direcional, que use a direção e a velocidade do deslocamento, fica para a fase 2.

**Regra, verificável:**
1. **Quando avaliar:** a cada atualização de posição do aparelho e também na troca de faixa horária.
2. **Faixa:** a faixa vigente é a da hora local do aparelho naquele instante, convertida para `America/Sao_Paulo`, com as bordas do contrato v1.
3. **Célula elegível:** chave (`h3_cell`, faixa vigente) com `status = com_dado` e `nivel ≥ L`.
4. **Quando dispara:** se a célula atual `c` for elegível, ou se alguma célula de `grid_disk(c, 1)` for elegível. `grid_disk` é o anel completo: a célula `c` e as 6 vizinhas, sem filtro de direção.
5. **Cooldown:** cada célula elegível dispara no máximo uma vez a cada `cooldown_min` minutos (proposta: 30).
6. **Chave `sem_dado`:** nunca dispara e nunca é exibida como segura. Se a pessoa consultar, o app mostra "sem dado registrado".

**Como escolher `L`:** é um **limiar exploratório pela fração de chaves históricas**. `L` é o menor nível cuja fração de chaves `com_dado` elegíveis no snapshot fica ≤ 10%.
- Isso **não** é um orçamento de área nem de alertas. A fração de chaves não equivale à área geográfica alertada, porque o anel k=1 amplia essa área. Também não equivale à frequência de alertas por deslocamento ou por pessoa.
- O arquivo traz, para cada `L` de 0 a 3:
  - a fração de chaves elegíveis;
  - a fração de células cobertas pelo anel;
  - a fração da pontuação de jan–set/2026.

  Tudo é rotulado `retrospectiva, test_seen=true`.
- Um orçamento de alertas exige uma métrica definida sobre trajetos e uma avaliação em período não usado para escolher `L`. Isso fica para a fase 2.

**Texto do alerta:** "Área próxima com muitas ocorrências registradas (jan–set/2026)". Nunca "perigoso", "risco" ou "tempo real" (r3 §2.4).

**Código e testes:** `ml/politica_proximidade.py`. Os testes cobrem:
- nenhuma chave `sem_dado` dispara;
- `L` ∈ 0–3;
- as frações batem com o snapshot;
- o hash do snapshot está correto;
- gerar duas vezes dá o mesmo sha256.

## 4. Bloco B: pontuação de rota, referência (opcional; achados 3 e 5)

**Núcleo (r3):** a função pura `pontuar(trechos: [(h3_cell, metros)], faixa, snapshot) → resultado`.

**Discretização da polilinha:** é uma função separada e totalmente especificada, para Python e C# chegarem às mesmas células.
1. A entrada é uma lista de pontos (lat, lon) em WGS84, em graus decimais.
2. Pontos consecutivos idênticos são removidos. Se restarem menos de 2 pontos, o resultado é o erro `rota_invalida`.
3. Cada segmento entre pontos consecutivos é dividido em `n = max(1, ceil(d / 5))` subsegmentos iguais:
   - `d` é a distância haversine, com R = 6 371 008,8 m;
   - a subdivisão é feita por interpolação linear em lat/lon.
4. Cada subsegmento:
   - tem comprimento haversine entre as suas extremidades;
   - é atribuído à célula `latlng_to_cell(ponto_médio, 9)`.
5. Os metros são somados por célula em precisão dupla. O arredondamento para 0,01 m acontece **só na saída**.
6. A ordem de saída das células é a da primeira ocorrência ao longo da rota.

A atribuição pelo ponto médio do subsegmento de ≤ 5 m é uma aproximação da interseção exata com o hexágono. Ela é a mesma nas duas linguagens, e por isso o resultado é reproduzível.

**Faixa:** a faixa da hora de partida vale para a viagem inteira. É uma **limitação explícita da demonstração**. Dividir o trajeto pelo horário estimado de passagem fica para a fase 2.

**Saída, por rota:**

| Campo | Definição |
|---|---|
| `pontuacao_acumulada_observada` | Σ (`pontuacao_mensal` da chave × km na célula), só nas chaves `com_dado`. É um **índice**, em pontos/(mês·hora) × km. **Não** é contagem esperada de ocorrências nem probabilidade (contrato v1, `pontuacao_mensal`). |
| `indice_por_km` | o índice acima ÷ km com dado. Sensibilidade. |
| `km_total`, `pct_sem_dado`, `pct_fora_da_cobertura` | por comprimento |
| `rotulo` | "pontuação acumulada observada, jan–set/2026 (retrospectiva), demonstração não validada" |

**Ordenação:**
- Só entre rotas do mesmo par origem-destino, da menor `pontuacao_acumulada_observada` para a maior.
- Empate exato após o arredondamento: vence a rota de menor `km_total` e, depois, a de menor índice na lista de entrada.
- Uma rota com `pct_sem_dado + pct_fora_da_cobertura > 30%` aparece **sem posição** no ranking, com a marca "dado insuficiente no trajeto". Esse limite é **regra de produto hipotética**, não validada.

**Vetores-ouro** (`docs/contratos-v3/vetores_rota_v1.json`), gerados pela referência Python. São 10 casos:
1. rota toda `com_dado`;
2. trecho `sem_dado`;
3. saída do perímetro;
4. segmento que cruza a borda de uma célula;
5. empate;
6. 1 ponto, que dá `rota_invalida`;
7. pontos repetidos;
8. segmento < 5 m;
9. rota que volta para a mesma célula;
10. faixa de 3 h.

Cada caso traz a entrada, as células com metros, a saída e a ordenação. O arquivo inclui também 20 pares lat/lon → célula, para conferir a biblioteca H3 do .NET.

**Aceite (do lado do Abner, externo):**
- igualdade exata nas células;
- diferença ≤ 0,01 m nos metros;
- diferença ≤ 1e-6 relativo no índice.

**Código e testes:** `ml/rota.py`. Os testes cobrem os 10 casos e a geração dos vetores duas vezes com o mesmo sha256.

## 5. Bloco C: T-A descritiva (opcional)

Como na r3 §2.2, sem mudança.

## 6. Notebook e MLflow (requisito do Nando)

**Notebook** (gerado por `scripts/gerar_notebook.py`; as seções 1–8 ficam intactas):
- **Seção 9 (obrigatória), "Da previsão retrospectiva à decisão no app":**
  - r3 §0–§1;
  - o diagrama da §1;
  - a tabela de donos da §2;
  - o que não se afirma.
- **Seção 10 (se A ou B entrarem), "Demonstração: proximidade e pontuação de rota":**
  - tabela por `L`;
  - 3 rotas de exemplo pontuadas;
  - resumo dos vetores;
  - rótulo "demonstração retrospectiva, não validada, test_seen=true".
- **Seção 11 (se C entrar):** T-A.

**MLflow:** experimento `hoodi-v3-exploratorio`. Os experimentos v1 e v2 ficam intactos.
- Um run por bloco executado: `politica_proximidade_v1`, `rota_pontuacao_v1` e `ta_descritiva`.
- Cada run leva:
  - os parâmetros da regra;
  - as métricas descritivas;
  - os artefatos com sha256;
  - as tags de proveniência, mais `test_seen=true` e `natureza=demonstracao`.
- Não há run para bloco não executado. Nada é registrado como modelo de produção.
- Os prints entram no notebook.

## 7. Cronograma (hoje é domingo, 15/11, 21h)

| Quando | Item | Estimativa |
|---|---|---|
| seg 16/11 | **Obrigatório:** seção 9, gerar e executar o notebook | 2 h |
| seg 16/11 | red-team real da seção 9, com folga para retrabalho | 2 h |
| seg 16/11 | commit do obrigatório (**ponto de congelamento garantido**) | 10 min |
| seg 16/11, só se o obrigatório já estiver commitado e com a decisão 2 | blocos A e/ou B, com testes, run MLflow, seção 10 e red-team | A 2 h, B 3 h, red-team 1,5 h |
| seg 16/11, 23h | o que não estiver commitado vai para a fase 2 | — |
| ter 17/11 | **sem ML:** CV do iFood (prazo 17/11) | — |
| qua 18/11 | `RELATORIO_ML.md` e README com Ficha/ODS, só documentação. Se o Nando confirmar, envio do material ao Abner | 2–3 h |
| qui 19/11, até 23h55 | revisão final e entrega | 1 h |

**Ordem de corte se atrasar:**
1. C;
2. B;
3. A.

**Nunca cortar:** a seção 9 e o red-team.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Motor de rotas não escolhido | O bloco B independe do motor, porque só recebe a polilinha. A demonstração usa 3 polilinhas fixas. A escolha do motor é do Abner. |
| H3 diferente entre .NET e Python | Pares lat/lon → célula nos vetores; o aceite exige igualdade exata. |
| Perímetro de 5×5 km | `pct_fora_da_cobertura` explícito e a marca "dado insuficiente". |
| Leitura de "seguro" ou de previsão | Regras da r3 §2.4 e rótulos fixos nos artefatos. |
| Política tomada como validada | Nome "proximidade", `test_seen=true` e "limiar exploratório" em todos os artefatos. |

## 9. Fase 2

Mesma lista da r3, acrescida de:
- alerta direcional;
- orçamento de alertas medido em trajetos;
- faixa por horário de passagem na rota.

## 10. Decisões do Nando

1. Aprovar o encaixe na arquitetura: o ML entrega a definição e os vetores; o app e a API executam.
2. Decisão 2 da r3, ainda aberta: quais blocos opcionais entram (nenhum; A; A+B; A+B+C).
3. Envio ao Abner em 18/11: só com a sua confirmação.
