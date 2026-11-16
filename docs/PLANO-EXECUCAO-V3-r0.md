# Plano de execução v3 — alerta e rotas, encaixado na arquitetura (r0)

Status: **plano, rodada 0** (15/11/2026 21h, JARVIS). Parte da `PROPOSTA-V3-ALERTA-ROTAS-r3.md`, que fica preservada e continua valendo para método, universos, linguagem e status do Teste. Este documento acrescenta o que faltava: **onde cada decisão roda na arquitetura decidida** e **a ordem de execução até 19/11**. Nada aqui foi implementado. Nada altera `selecao_modelo.json`, a v1, a v2, `SPEC-ML.md`, `specs/001` nem o contrato v1.

## 1. Arquitetura decidida (fontes: documento mestre hoodi, `specs/001/plan.md`, `contracts/snapshot-risco.md`)

```
SSP-SP XLSX ──► pipeline ML (Python, lote, offline) ──► snapshot versionado + manifest + sha256
                                                              │
                                                              ▼
                                          API .NET (Abner) — ingere o snapshot, serve ao app,
                                          contexto Rotas (RouteRequest/RouteSuggestion, RF-07)
                                                              │  download periódico (RF-04)
                                                              ▼
                                          App Expo — geofencing local, alerta offline (RNF-03),
                                          notificação do celular → smartwatch / hoodi Pet
```

Princípios que este plano assume (todos já decididos; nenhum é novo):
- **O ML não vira serviço.** Não há modelo respondendo requisição. O ML entrega artefatos versionados com checksum.
- **O alerta roda no aparelho**, sem rede, a partir do último snapshot.
- **A rota é responsabilidade da API**, no contexto Rotas. O **motor de rotas ainda não foi escolhido** (documento mestre, gap aberto da rodada 4).
- O contrato v1 não muda. Tudo que for novo é **aditivo** e versionado à parte.

## 2. Divisão de responsabilidades por decisão

| Decisão do app | Quem calcula | Insumo | O que o ML entrega | Dependência externa |
|---|---|---|---|---|
| Alerta antes de entrar | **App**, no aparelho | snapshot v1 + política de alerta | `politica_alerta_v1.json`: regra, parâmetros, texto e a evidência descritiva que justificou o limiar | nenhuma para a demo; Abner/Mari para servir e consumir o arquivo |
| Escolha entre 3–4 rotas | **API .NET** | rotas candidatas + snapshot v1 | **especificação de referência** da pontuação de rota + implementação Python de referência + **vetores-ouro** (entrada → saída esperada) para o Abner validar o C# | **motor de rotas** (escolha do Abner); sem ele, não há rota candidata |

O ML é dono da **definição** e da **prova de equivalência**; a API e o app são donos da **execução em produção**.

## 3. Entregáveis do ML (novos, aditivos)

### 3.1 Política de alerta v1 (`ml/dados/snapshot/politica_alerta_v1.json`)

- **Regra:** alertar quando a posição prevista do usuário (célula atual e anel H3 k=1 na direção do deslocamento; na demo, simplesmente o anel k=1) contém chave `com_dado` da **faixa atual** com `nivel ≥ L`.
- **Parâmetros:** `L`, `k`, `cooldown_min` (mesma célula não alerta de novo dentro do cooldown), `faixa_por_hora_local` (fuso `America/Sao_Paulo`).
- **Chave `sem_dado`:** não alerta e não é tratada como segura; o app mostra "sem dado registrado" se o usuário tocar.
- **Como `L` é escolhido:** pelo **orçamento de área** e não por desempenho. `L` é o menor nível cuja fração de chaves `com_dado` alertáveis não passa de ~10% da área, coerente com a métrica da T-A (hit rate a 10%). O arquivo traz a fração de área e de pontuação coberta por cada `L` em jan–set/2026, marcada `retrospectiva, test_seen=true`.
- **Natureza declarada:** "regra de produto sobre mapa histórico observado; não validada como alerta para pessoas".
- Gerado por código (`ml/politica_alerta.py`), com sha256 no manifest próprio. Testes: invariantes (nenhum `sem_dado` dispara; `L` ∈ 0–3; fração reportada bate com o snapshot).

### 3.2 Pontuação de rota v1 (`specs/001/contracts/rota-pontuacao-v1.md` + `ml/rota.py` + `ml/dados/snapshot/vetores_rota_v1.json`)

- **Entrada da API:** polilinha da rota (lista de lat/lon em WGS84), hora de partida local.
- **Discretização determinística:** a polilinha é amostrada a cada **10 m** ao longo da geometria; cada amostra recebe a célula H3 res. 9; o comprimento é atribuído à célula da amostra. Passo, resolução e método de amostragem ficam fixos no contrato.
- **Faixa:** a faixa da hora de partida (v1 não divide a viagem entre faixas; limitação declarada).
- **Saída por rota:**
  - `pontuacao_acumulada_observada` = Σ (pontuacao_mensal da chave × km na célula), só em chaves `com_dado`;
  - `pct_sem_dado`, `pct_fora_da_cobertura` (por comprimento);
  - `km_total`;
  - rótulo fixo: "pontuação acumulada observada, jan–set/2026 (retrospectiva)".
- **Ordenação:** menor `pontuacao_acumulada_observada` entre rotas do **mesmo** par origem-destino. Ocorrências/km vai junto como sensibilidade. Rota com `pct_sem_dado + pct_fora_da_cobertura` acima de um limite fixo (proposta: 30%) é mostrada **sem posição no ranking** ("dado insuficiente no trajeto"). Esse limite é regra de produto, não validada, e é declarado assim.
- **Sem** "rota segura", "risco" nem abstenção probabilística (r3 §2.3).
- **Vetores-ouro:** ~10 casos gerados pela referência Python, cobrindo: rota toda `com_dado`; rota com trecho `sem_dado`; rota saindo do perímetro; polilinha que cruza borda de célula; empate; rota de 1 ponto (erro esperado); polilinha com ponto repetido. Cada caso traz entrada, células esperadas com metros e saída. Inclui também pares lat/lon → célula H3 para o Abner conferir a biblioteca H3 do .NET contra a do Python.
- **Critério de aceite com o Abner:** a implementação C# reproduz os vetores-ouro com tolerância de 1e-6 na pontuação e igualdade exata nas células.

### 3.3 O que **não** muda

- Snapshot v1 (CSV, manifest, fixture) e o hash dele.
- `selecao_modelo.json`, v1 e v2.
- O classificador não entra no app. O RF continua como artefato de avaliação.

## 4. Notebook e MLflow (requisito do Nando)

- **Notebook** (gerado por `scripts/gerar_notebook.py`, seções 1–8 intactas):
  - **Seção 9 "Da previsão retrospectiva à decisão no app":** diagnóstico da r3 §0–§1, o diagrama da §1 deste plano, a tabela de responsabilidades da §2 e o que não se afirma.
  - **Seção 10 "Política de alerta e pontuação de rota (demonstração)":** curva área × pontuação coberta por `L`, o `L` escolhido e o porquê; 3 rotas de exemplo pontuadas com mapa; vetores-ouro resumidos. Rótulo: "demonstração, não validado, test_seen=true".
  - Opcional, se houver tempo: **Seção 11 "T-A descritiva"** (r3 §2.2).
- **MLflow:** experimento novo `hoodi-v3-exploratorio`, sem tocar v1/v2.
  - run `politica_alerta_v1`: params `L`, `k`, `cooldown_min`; métricas de fração de área e de pontuação; artefato JSON; tags de proveniência + `test_seen=true`, `natureza=regra_de_produto`.
  - run `rota_pontuacao_v1`: params passo, resolução, limite de dado insuficiente; artefatos contrato, vetores-ouro e sha256; métrica `n_vetores`.
  - run `ta_descritiva` só se a seção 11 for feita.
  - Nada registrado como modelo de produção. Prints do MLflow entram no notebook como nas seções 6.

## 5. Cronograma (hoje é dom 15/11, 21h)

| Quando | Item | Estimativa | Saída verificável |
|---|---|---|---|
| seg 16/11 manhã | `ml/politica_alerta.py` + testes | 1 h | JSON + testes verdes |
| seg 16/11 manhã | `ml/rota.py` + contrato `rota-pontuacao-v1.md` + vetores-ouro + testes | 2 h | vetores gerados duas vezes com hash igual |
| seg 16/11 tarde | runs MLflow + prints | 1 h | 2 runs no experimento novo |
| seg 16/11 tarde | seções 9 e 10 do notebook, gerar e executar | 1,5 h | notebook executado sem erro |
| seg 16/11 noite | red-team real (Codex) até 0 BLOQUEANTE / 0 ALTA | 1–1,5 h | `REDTEAM-PLANO-V3-rodadaN.md` |
| seg 16/11 noite | commit + **congelamento** | 10 min | commit no `v2-historico` |
| ter 17/11 | **sem ML**: dia reservado ao CV do iFood (prazo 17/11) | — | — |
| qua 18/11 | enviar contrato de rota + vetores-ouro + política ao Abner (com aprovação do Nando); RELATORIO_ML.md, README com Ficha/ODS | 2–3 h | relatório e README no repo |
| qui 19/11 até 23h55 | revisão final e entrega | 1 h | entrega |

Corte de escopo se atrasar, nesta ordem: (1) seção 11 T-A; (2) mapa das rotas de exemplo no notebook (fica só a tabela); (3) runs MLflow viram um só run. **Não cortar:** seção 9, vetores-ouro e red-team.

## 6. Riscos e mitigação

| Risco | Efeito | Mitigação |
|---|---|---|
| Motor de rotas não escolhido | a escolha de rota não funciona ponta a ponta na demo | demo da API com 3 polilinhas fixas; contrato independe do motor (só recebe polilinha); recomendação ao Abner: OSRM com `alternatives=3` ou a API de rotas que ele já usar |
| Biblioteca H3 do .NET diferente da do Python | células divergentes, ranking diferente | vetores-ouro com lat/lon → célula; aceite só com igualdade exata |
| Perímetro 5×5 km | rotas de carro saem da cobertura | `pct_fora_da_cobertura` explícito e regra de "dado insuficiente" |
| Alerta excessivo | usuário desliga o app | `L` por orçamento de área + cooldown; declarado como não validado |
| Leitura de "seguro" | promessa indevida | regras de linguagem da r3 §2.4 aplicadas aos textos da política e da rota |
| Prazo | entrega incompleta | ordem de corte da §5 |

## 7. Fase 2 (depois de 19/11; sem mudança em relação à r3)

`specs/002` com pré-registro antes de out–nov/2026; reextração com conduta; perímetro maior; malha OSM; T-A inferencial; distribuição preditiva para abstenção; índice para motorista; contrato v2 com o Abner.

## 8. Decisões do Nando

1. Aprovar este encaixe: ML entrega política de alerta e especificação de rota com vetores-ouro; app e API executam.
2. Aprovar o cronograma, com 17/11 reservado ao iFood.
3. Seção 11 (T-A descritiva): entra se sobrar tempo, ou fica para a fase 2.
4. Envio do material ao Abner em 18/11: só com a sua confirmação.
