# Triagem e decisões propostas após o red-team da rodada 3 (2026-11-12)

Proposta do JARVIS, **não aplicada**: nenhum arquivo de spec, plano ou tarefa foi editado. Relatórios das rodadas 1 a 3 preservados em `docs/REDTEAM-SPEC-rodada{1,2,3}.md`.

## Bloqueantes (2)
**B1 — Fórmula (T016 e FR-006).** O T016 ainda termina com "soma de jan–set ÷ 9"; o FR-006 não exige as duas divisões.
Edição proposta: T016 e FR-006 passam a dizer "soma dos pesos ÷ n meses da janela ÷ horas da faixa". Adicionar teste numérico: 54 pontos em 9 meses dão 1,0 em faixa de 6 h e 2,0 em faixa de 3 h. O T017 passa a registrar o hash do manifest e da configuração usados na aprovação.

**B2 — Privacidade (obj. 17).** Inspeção só dos nomes das 30 colunas do interim (valores não lidos): não há coluna de nome de pessoa, vítima ou autor. Há quase-identificadores: `NUM_BO`+`ANO_BO`+`NOME_DELEGACIA`, `LOGRADOURO`+`NUMERO_LOGRADOURO`+`BAIRRO`, `LATITUDE`/`LONGITUDE`, data e hora.
Decisões propostas:
- Raw e interim: cópia fiel da fonte pública, fora do git, sem entrega, sem cópia fora desta máquina; retenção até a entrega.
- Derivados: `usadas` conserva lat/lon, data, hora e rubrica (necessário para H3). Nenhuma coluna de endereço, bairro ou BO passa para derivados.
- Quarentena: `fonte,linha,rubrica,motivo`, sem coordenada.
- Atualizar `data-model.md` (tirar `bo_id` da tabela persistida, marcar como transitório em memória) e o T010 (sem "bo_id interno" persistido).
- Escrever o inventário em `ml/dados/README.md` já agora, não só no T030, e acrescentar um teste que lê os schemas reais dos parquets derivados.
- Constituição VII: interpretar "nenhum dado pessoal" como "nenhum campo que identifique pessoa nos derivados e entregas". Isso exige decisão explícita do Nando (a constituição pede nova versão se o texto mudar).

## Importantes: o que priorizo (mecânico, sem decisão sua)
Ordem: 18, 3, 11, 13, 4, 9/10/12, 7/8, 14, 15/16, 22, 23.
- 18: trocar o exemplo do contrato por esquema de tipos ou por amostra real rastreável.
- 3: trocar "sem vazamento" por "separação por data do fato; disponibilidade histórica não reconstruída".
- 11: T021 com `data_feature < inicio_rotulo` e teste de invariância a registros futuros.
- 13: baseline "média histórica acumulada" mais "últimos 2 meses", nas mesmas chaves.
- 4: congelar regra de seleção, vencedor e configuração antes de consultar ago–set (nova tarefa antes do T026).
- 9/10/12: método de quantil e empates, população chave×origem, métrica principal (macro-F1), desempate e agregação das dobras.
- 7/8: três definições separadas (elegível para feature, alvo pontuável, status do snapshot) e estimando condicionado.
- 14: T033 passa a exigir a contagem calculada, em vez de "178"; "setembro incompleto" vira hipótese.
- 15/16: demonstrar a granularidade (explicar 1 contra 2.390 duplicatas) e criar destino para data inválida, com precedência.
- 22/23: tabela de gates por estado (planejado/executado/verificado/aprovado) e disposição individual dos 23 achados no T036.

## Fica para você
- Objetos 19 (centro e geometria do perímetro), 20 (texto de "risco" e sensibilidade dos pesos) e 21 (rota do T020b, Ficha/ODS, T027 e replanejamento): dependem de decisão ou de escopo seu.
- `git init` (T003).
