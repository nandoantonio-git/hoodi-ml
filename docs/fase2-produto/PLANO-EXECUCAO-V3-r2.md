# Plano de execução v3: alerta e rotas na arquitetura decidida (rodada 2)

**Status:** plano, rodada 2 (15/11/2026, JARVIS). Nada aqui foi implementado.

**De onde vem esta rodada:**
- Revisa a `PLANO-EXECUCAO-V3-r1.md` com os achados 10–13 do red-team real em `REDTEAM-PLANO-V3-rodada2.md`. A r0, a r1 e a rodada 1 ficam preservadas.
- O método vem da `PROPOSTA-V3-ALERTA-ROTAS-r3.md`: universos, linguagem, status do Teste e fase 2.

**O que este plano acrescenta à r3:**
- onde cada decisão do app roda na arquitetura decidida;
- a ordem de execução.

**O que este plano não toca:** `selecao_modelo.json`, a v1, a v2, `SPEC-ML.md`, `specs/001` e o contrato v1.

## 0. Escopo: o mesmo da r3 (achados 1 e 9)

**Obrigatório até o congelamento de 16/11:** o mesmo da r3 §4, ou seja, a v1 congelada, a seção 9 do notebook e o red-team.

**Opcional, alinhado às opções da r3 §6 (achado 10).** A decisão 2 da r3 continua com as mesmas três opções:
- nenhuma;
- só T-A, que é o **bloco C**;
- T-A + protótipo de rota, que são os **blocos C + B**.

O **bloco A** (política de proximidade) **não está na r3**. Ele é um **aditivo independente** e exige uma decisão própria do Nando, sim ou não (§10, decisão 3).

Regras para todos os blocos:
- Cada bloco é uma **demonstração retrospectiva exploratória**: `test_seen=true`, não validada e sem promessa de comportamento de produto.
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

O nome é **alerta por proximidade**, não "alerta antecipado de entrada". Ele avisa quando a pessoa está numa célula elegível ou numa célula vizinha a ela.
- A regra **não garante distância nem antecedência mínima** até a célula elegível (achado 12).
- Medir a distância ao alvo e fazer um alerta direcional fica para a fase 2.

**Regra, verificável:**
1. **Quando avaliar:** a cada atualização de posição do aparelho e também na troca de faixa horária.
2. **Faixa:** a faixa vigente é a da hora local do aparelho naquele instante, convertida para `America/Sao_Paulo`, com as bordas do contrato v1.
3. **Célula elegível:** chave (`h3_cell`, faixa vigente) com `status = com_dado` e `nivel ≥ L`.
4. **Quando dispara:** se a célula atual `c` for elegível, ou se alguma célula de `grid_disk(c, 1)` for elegível. `grid_disk` é o anel completo: a célula `c` e as 6 vizinhas, sem filtro de direção.
5. **Cooldown:** cada célula elegível dispara no máximo uma vez a cada `cooldown_min` minutos (proposta: 30).
6. **Chave `sem_dado`:** nunca dispara e nunca é exibida como segura. Se a pessoa consultar, o app mostra "sem dado registrado".

**Como escolher `L` (achado 13).** Medido no snapshot v1 em 15/11:
- numerador: chaves `com_dado` com `nivel ≥ L`;
- denominador: todas as chaves `com_dado` (1.172 de 1.395).

| `L` | Chaves elegíveis | Fração das chaves `com_dado` | Fração da `pontuacao_mensal` somada |
|---|---|---|---|
| 1 | 682 | 58,2% | 93,3% |
| 2 | 475 | 40,5% | 84,0% |
| **3** | **200** | **17,1%** | **56,5%** |

- **`L = 3` é o padrão,** por ser o nível mais restrito que o contrato v1 oferece. Como os níveis são quartis do treino, nenhum `L` fica abaixo de 10%. A meta de "≤ 10%" da r1 foi **retirada**. Se o contrato um dia mudar e nenhum nível existir, a política não alerta e registra o erro.
- Essas frações são de **chaves históricas**, rotuladas `retrospectiva, test_seen=true`. Elas **não** são orçamento de área nem de alertas. O arquivo da política informa também a fração de células do perímetro cobertas pelo anel k=1.
- **Sensibilidade, só registrada:** elegível quando `pontuacao_mensal` ≥ P90 das chaves `com_dado`. Ela serve para comparar com um corte de 10% sem mudar o contrato. A regra não usa essa sensibilidade.
- Um orçamento de alertas medido em trajetos fica para a fase 2.

**Texto do alerta:** "Área próxima com muitas ocorrências registradas (jan–set/2026)". Nunca "perigoso", "risco" ou "tempo real" (r3 §2.4).

**Código e testes:** `ml/politica_proximidade.py`. Os testes cobrem:
- nenhuma chave `sem_dado` dispara;
- `L = 3` e a tabela acima reproduzida a partir do snapshot;
- as frações batem com o snapshot;
- o hash do snapshot está correto;
- gerar duas vezes dá o mesmo sha256.

## 4. Bloco B: pontuação de rota, referência (opcional; achados 3 e 5)

**Núcleo (r3):** a função pura `pontuar(trechos: [(h3_cell, metros)], faixa, snapshot) → resultado`.

**Discretização da polilinha:** é uma função separada, especificada para Python e C# chegarem às mesmas células. A reprodutibilidade depende das convenções fixadas logo abaixo (achado 11).
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

A atribuição pelo ponto médio do subsegmento de ≤ 5 m é uma aproximação da interseção exata com o hexágono.

**Convenções numéricas e de versão (achado 11):**
- **H3:** core C **4.5.0**, o mesmo usado pelo ML (`h3.versions()`: c 4.5.0, python 4.5.0).
  - O .NET deve usar um binding do core C oficial nessa mesma versão.
  - Um porte reimplementado só é aceito se passar nos vetores de fronteira.
- **Coordenadas:**
  - longitude em [-180, 180) e latitude em [-90, 90];
  - ponto fora desses limites dá `rota_invalida`;
  - o perímetro fica longe do antimeridiano e dos polos.
- **Aritmética:**
  - IEEE 754 em precisão dupla;
  - haversine = `2R·asin(sqrt(sin²(Δφ/2) + cos φ1·cos φ2·sin²(Δλ/2)))`;
  - interpolação `p_i = p0 + (i/n)·(p1 − p0)` em graus; os radianos só entram dentro do haversine.
- **Comparação:**
  - é feita sem arredondar;
  - empate quando `|a − b| ≤ 1e-9·max(|a|, |b|, 1)`.
- **Arredondamento:** *half-even* e só na exibição (0,01 m; 1e-6 no índice).
- **Vetores de fronteira:**
  - 20 pontos a ≤ 1e-7 grau de arestas de células do perímetro, com a célula esperada pelo core C 4.5.0;
  - 2 rotas cujos pontos médios caem nessa faixa;
  - 1 caso de empate dentro da tolerância e 1 logo fora dela.

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
- Empate, pela tolerância acima: vence a rota de menor `km_total`, com a mesma tolerância, e depois a de menor índice na lista de entrada.
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

Cada caso traz a entrada, as células com metros, a saída e a ordenação. O arquivo inclui também 20 pares lat/lon → célula em pontos interiores, mais os vetores de fronteira.

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
| seg 16/11, só se o obrigatório já estiver commitado e houver decisão | C e B (decisão 2) e A (decisão 3), cada um com código, testes, run MLflow, seção 10/11 e red-team | C 3–4 h, B 3,5 h, A 2 h, red-team 1,5 h |
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
| H3 diferente entre .NET e Python | Core C 4.5.0 fixado e vetores de fronteira; o aceite exige igualdade exata nas células. |
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
2. Decisão 2 da r3, ainda aberta e com as mesmas opções: nenhuma; só T-A (C); ou T-A + protótipo de rota (C+B).
3. Aditivo A, a política de proximidade com `L = 3`: sim ou não.
4. Envio ao Abner em 18/11: só com a sua confirmação.
