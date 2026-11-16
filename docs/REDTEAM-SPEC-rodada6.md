# Red-team da spec — rodada 6 (Codex CLI real)

Gerado em 2026-11-13. Mesmo comando da rodada 4. Prompt: /tmp/rt-hoodi-spec6/prompt.txt

Revisão documental do estado transcrito, sem inspeção de código ou artefatos nem execução de testes. O fechamento abaixo vale **para a especificação**, não comprova conformidade da implementação. `[X]` não constitui evidência de execução.

**BLOQUEANTE**

1. **[R5-1 — RESOLVIDO NA SPEC; implementação pendente] Coordenadas em `processed/`.**  
   **Arquivo + trecho:** `data-model.md`, “Persistido × transitório”: schema fechado sem coordenadas e “`lat` e `lon` […] MUST NOT ser gravadas em `processed/`”. `tasks.md`, T030: teste dos parquets reais incluindo coordenadas proibidas e obrigação de “regenerar `usadas.parquet`, que hoje contém `lat` e `lon`”.  
   A autorização documental incompatível com a constituição VII foi removida. A existência declarada do parquet antigo continua sendo uma **não conformidade material pendente**, sem reabrir o bloqueante da spec.  
   **Correção restante:** implementar a remoção, regenerar o artefato e registrar o resultado do teste sobre os derivados reais.

**IMPORTANTE**

2. **[R5-3 — PARCIALMENTE RESOLVIDO] Controle temporal ainda não propagado a todos os critérios.**  
   **Arquivo + trecho:** `spec.md`, FR-009 e SC-003 agora abrangem features e ajuste das transformações por dobra. Entretanto, US3, *Independent Test*, continua verificando somente “nenhuma data de teste […] anterior à última de treino” e números executados. `docs/SPEC-ML.md`, §8, mantém a mesma verificação restrita.  
   **Correção:** alinhar esses dois critérios a SC-003 e T021, incluindo anterioridade estrita das features e ajuste das transformações somente no treino da dobra. A ressalva sobre disponibilidade histórica foi preservada.

3. **[R5-4 — RESOLVIDO QUANTO AO SNAPSHOT; definição do alvo ainda pendente em R5-5] Separação das ausências.**  
   **Arquivo + trecho:** `research.md`, D-04, substituiu a regra antiga: ausência de features “não as torna `sem_dado` no snapshot”; o snapshot depende de histórico **pontuável** em jan–set. T016 repete essa regra e exige os três casos de teste solicitados.  
   Entretanto, D-04 ainda descreve a situação 3 como “sem registro no rótulo”, sem exigir registro pontuável; `data-model.md`, “Janela de dados e exemplo”, conserva a mesma formulação.  
   **Correção:** fechar a elegibilidade do alvo no tratamento da pendência R5-5 e explicitar os resultados esperados dos três testes. Não contabilizo essa lacuna compartilhada como falha nova.

4. **[R5-8 — RESOLVIDO DOCUMENTALMENTE] Fronteira temporal estrita.**  
   **Arquivo + trecho:** `tasks.md`, T021: “`data_feature < inicio_rotulo`”, transformações ajustadas só no treino da dobra e invariância das features passadas a alterações futuras.  
   **Correção restante:** nenhuma documental para este item; implementar e executar os testes planejados.

5. **[R5-11 — PARCIALMENTE RESOLVIDO] Incompletude de setembro ainda exigida como fato no relatório.**  
   **Arquivo + trecho:** `spec.md`, Assumptions, e `plan.md`, riscos, passaram a tratar incompletude como hipótese. Porém `tasks.md`, T033, ainda manda incluir “setembro incompleto” entre os limites do dado.  
   O “178” saiu das referências operacionais de spec/plano; sua permanência na tabela histórica de `research.md` não é, isoladamente, falha. A distribuição antiga no plano foi identificada como exploração sob outra fórmula.  
   **Correção:** substituir em T033 por “possível incompletude de setembro, hipótese sem evidência de cobertura”, exigindo afirmação conclusiva apenas se houver evidência. A propagação incompleta mantém uma divergência entre os documentos.

6. **[R5-17 — PARCIALMENTE RESOLVIDO] Estados de execução e conformidade continuam incompatíveis.**  
   **Arquivo + trecho:** `plan.md` agora chama os candidatos de “planejados”, mas `spec.md`, FR-010, mantém “Executados: RF, XGBoost e MLP”; `docs/SPEC-ML.md`, §6, mantém “Candidatos executados”, com T025 aberto. O plano também afirma “sem violações no planejamento” e, em *Complexity Tracking*, “Sem violações da constituição”, mantendo o princípio I como “OK” pela justificativa do exemplo ilustrativo.  
   **Correção:** trocar as declarações de execução por planejamento até existir evidência; limitar a conclusão de conformidade às verificações efetivamente sustentadas e reconhecer a pendência R5-14. A explicação sobre `NEEDS CLARIFICATION` passou a distinguir pendências do responsável, mas não resolve essas afirmações residuais.

7. **[R5-18 — PARCIALMENTE RESOLVIDO] Cobertura da fixture pela revisão intermediária permanece ambígua.**  
   **Arquivo + trecho:** `spec.md`, US4, exige rodada vigente “do artefato enviado”; `tasks.md`, meta da Fase 6, diz que contrato **e fixture** são cobertos pela rodada vigente “do contrato”.  
   A exigência antiga de executar T035 antes de qualquer envio foi retirada, e T036 preserva disposição individual e revalidação. Contudo, revisar o contrato não demonstra revisão da fixture produzida.  
   **Correção:** uniformizar a cobertura por artefato e versão, identificando qual revisão cobre T020a e T020b; ou limitar a exigência intermediária à confirmação humana constitucional. Não atribuir automaticamente à revisão documental cobertura dos arquivos gerados.

8. **[PENDÊNCIAS HERDADAS — não são falhas novas] R5-2, 5, 6, 7, 9, 10, 12, 13, 14, 15 e 16.**  
   Permanecem, conforme o escopo declarado:
   
   - **R5-2:** `PROVENIENCIA.md`/T005 — completar comandos, comparação e vínculo da indexação ao parquet.
   - **R5-5–7:** Edge Cases, Clarifications e D-04 — definir população avaliada, regras de quantis e população dos cortes.
   - **R5-9–10:** T024–T026/D-04 — fixar seleção antes da busca e especificar baseline histórica.
   - **R5-12–13:** `docs/SPEC-ML.md` §4 e `data-model.md` — demonstrar unidade/deduplicação e definir datas inválidas e precedência de destinos.
   - **R5-14:** contrato, Fixture — substituir exemplo artificial por esquema ou amostra real rastreável.
   - **R5-15:** Assumptions, D-07 e T030 — definir cobertura espacial e protocolo de sensibilidade.
   - **R5-16:** T027/T032 e dependências — antecipar decisão sobre modelos exigidos e explicitar a exceção de sequência.

Não identifiquei novo bloqueante documental introduzido pelo diff. Restam correções parciais e divergências de propagação descritas acima; isso não autoriza considerar os artefatos atuais conformes.

SEM OBJEÇÃO BLOQUEANTE RESTANTE