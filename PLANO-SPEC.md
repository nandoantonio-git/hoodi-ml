# Plano de uso do Spec Kit no hoodi-ml

Escrito em 2026-11-11. Base: análise de `.specify/`, `specs/001-risco-h3-faixa-horaria/`, `docs/SPEC-ML.md`, `PLANO.md`, `prompts.md`, `scripts/` e `ml/dados/`.

## 1. Onde o projeto está

| Item | Estado |
|---|---|
| Spec Kit | v1.4.0, integração Claude, comandos com hífen (`/speckit-plan`) |
| Constituição | v1.0.0 própria, 7 princípios, completa. Mudança exige decisão do Nando |
| Feature | `specs/001-risco-h3-faixa-horaria/` com `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`. `.specify/feature.json` aponta para ela |
| Código | só `scripts/00` (XLSX→parquet) e `scripts/01` (qualidade). `ml/`, `tests/`, `notebooks/` do plano ainda não existem |
| Ambiente | `.venv` Python 3.9.6 só com duckdb. `.venv311` Python 3.11.15 vazio. Nenhum h3, pandas, scikit-learn, xgboost ou pytest instalado |
| Git | o repositório não é git. A rubrica A1 pede "repositório Python separado" |
| Codex CLI | instalado (`codex` no PATH), pronto para o red-team (T025) |
| Hooks | sem `.specify/extensions.yml`, então nenhum hook roda |

O ciclo do Spec Kit já foi percorrido até `tasks.md` (feito à mão, sem rodar os comandos). Falta validar e implementar.

## 2. Lacunas encontradas nos artefatos

Estas lacunas devem ser fechadas **antes** do `/speckit-implement`, porque mudam o código.

1. **"Tercis" não dá níveis 0–3.** Tercis dividem em 3 faixas, e a escala tem 4 valores (0, 1, 2, 3). Falta dizer o que é o nível 0 e onde ficam os cortes. (`spec.md` FR-006, `SPEC-ML.md` §5)
2. **Rubricas sem peso.** Os pesos cobrem furto, roubo, lesão corporal, homicídio e estupro. No perímetro há também tráfico (339), drogas para consumo (53), lesão culposa no trânsito (528) e ilícito extrapenal (49). São cerca de 970 registros sem peso definido.
3. **O alvo de previsão não está definido.** O rótulo é calculado dos próprios registros. Se o modelo aprende a prever o nível de ago–set a partir de jan–jul, isso é previsão. Se as features usam os mesmos registros que formam o rótulo do mesmo período, há vazamento. A spec precisa dizer: features do período A, rótulo do período B.
4. **Qual data separa treino e teste.** A base tem 22.222 linhas com fato anterior a 2026. A spec não diz se o split usa a data do fato (`DATA_OCORRENCIA_BO`) nem o que fazer com essas linhas.
5. **Candidatos incoerentes entre documentos.** `PLANO.md` lista RF, XGBoost e MLP. `SPEC-ML.md` e `spec.md` listam também LSTM e KMeans+PCA. KMeans+PCA não é classificador supervisionado e LSTM exige sequência longa. O próprio `plan.md` reconhece que o baseline e a RF podem vencer.
6. **`PLANO.md` está desatualizado.** Diz "aguarda OK do Nando em rótulo e perímetro", mas `SPEC-ML.md` diz que as decisões estão fechadas.
7. **Coordenada exata da FIAP pendente.** Impacto de cerca de 50 m, não bloqueia.
8. **Checklist com 1 item aberto**, justificado (H3 e os modelos são exigência do briefing). Pode ficar como está.
9. **Escala dos dados (estimativa minha).** 5×5 km com células H3 res. 9 dá cerca de 237 células, ou cerca de 950 chaves (célula × faixa), para 20.657 registros válidos. São em média 22 registros por chave, mas desigual. Medir antes de escolher o modelo.

## 3. Sequência de uso

Ordem dos comandos, com o que cada um entrega. O diretório é sempre `hoodi-ml/`.

| # | Comando | Objetivo | Entrega |
|---|---|---|---|
| 1 | `/speckit-clarify` | Fechar as lacunas 1 a 5 da seção 2 (o comando faz até 5 perguntas) | `spec.md` com seção de esclarecimentos |
| 2 | Editar `PLANO.md` e `SPEC-ML.md` à mão | Alinhar candidatos e o status de "aguardando OK" (lacunas 5 e 6) | Documentos coerentes |
| 3 | `/speckit-plan` | Completar a Fase 0 e 1 que faltam: `research.md`, `data-model.md`, `contracts/` (formato do snapshot e da fixture do Abner), `quickstart.md` | Artefatos de design em `specs/001-.../` |
| 4 | `/speckit-tasks` | Regenerar `tasks.md` com base nos novos artefatos. O atual vira rascunho de comparação | `tasks.md` revisado |
| 5 | `/speckit-analyze` | Conferir spec, plan e tasks entre si e com a constituição | Relatório de inconsistências |
| 6 | `/speckit-checklist` (opcional) | Checklist de qualidade dos requisitos de dado e de avaliação | `checklists/dados.md` |
| 7 | `/speckit-implement` | Executar as tarefas, parando nas marcadas `[Nando]` | Código, testes, snapshot |
| 8 | `/speckit-converge` | Comparar o código com a spec e acrescentar o que faltar | Tarefas novas em `tasks.md` |

Observação: o `plan.md` e o `tasks.md` atuais foram escritos manualmente. Os passos 3 e 4 reaproveitam o conteúdo deles, não precisam começar do zero.

## 4. Ordem de execução do `/speckit-implement`

O prazo de hoje (2026-11-11) manda na ordem. O contrato com o Abner vence às 12h e a rota/fixture às 20h.

**Caminho crítico:** T001 → T002/T003 → T004 → T005–T008 (testes) → T009 → T010 → **T011 (Nando)** → T012 → **T013 (Nando)**.

| Fase | Tarefas | Parar para o Nando em |
|---|---|---|
| Setup | T001–T004 | T001: escolher o interpretador. Recomendo o `.venv311` (Python 3.11), porque h3, scikit-learn e xgboost têm rodas prontas nele. O `.venv` 3.9.6 é o Python do Xcode |
| Contrato e qualidade (US1 e US2) | T005–T013 | T011 (aprovar a distribuição dos níveis) e T013 (enviar ao Abner) |
| Modelo (US3) | T014–T019 | nenhuma |
| Entrega (US4) | T020–T026 | T025 (avisar antes do Codex CLI) e T026 (congelamento e entrega) |

Regras de uso do `/speckit-implement` neste projeto:
- Testes primeiro. A constituição exige idempotência, quarentena e ausência de vazamento, e cada um tem teste em T005–T008 e T014.
- Rodar por fase, não tudo de uma vez, para o Nando validar a distribuição de níveis (T011) antes do snapshot.
- Nada de envio ou publicação sem confirmação (Princípio VII).
- `git init` na raiz antes do primeiro commit. O `.gitignore` já exclui `.venv*`, `ml/dados/interim/` e `__pycache__`.

## 5. Datas

| Data | Marco |
|---|---|
| 2026-11-11 12h | Chave de risco, janela do snapshot e fixture para o Abner |
| 2026-11-11 20h | Rota e fixture |
| 2026-11-16 | Congelamento |
| 2026-11-19 23h55 | Entrega |

## 6. Decisões que dependem do Nando

1. Interpretador Python (T001).
2. Resposta às lacunas 1 a 5 da seção 2, via `/speckit-clarify`.
3. Pesos das rubricas sem peso (lacuna 2).
4. Aprovação da distribuição dos níveis (T011).
5. Uso do Codex CLI no red-team (T025).
