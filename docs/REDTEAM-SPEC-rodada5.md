# Red-team da spec — rodada 5 (Codex CLI real)

Gerado em 2026-11-13. Mesmo comando da rodada 4. Prompt: /tmp/rt-hoodi-spec5/prompt.txt

Revisão documental das transcrições fornecidas. Não inspecionei código, artefatos ou aprovações, nem executei testes. `[X]` não comprova execução. As pendências declaradas e a implementação futura de T021+ não são, por si, falhas. A numeração R4 abaixo corresponde à lista da rodada 4.

**BLOQUEANTE**

1. **[BLOQUEANTE — R4-3; contradição explícita no diff] Coordenadas exatas persistidas em `processed/`.**  
   **Arquivo + trecho:** `data-model.md`, “Persistido × transitório”: “`processed/` grava […] `lat`, `lon` […] (gitignored, nunca entregue)”. Constituição VII: “sem […] coordenada exata fora do raw/interim/quarentena”.  
   **Constatação:** a nova separação entre persistido e transitório autoriza expressamente o que a constituição proíbe. Estar fora do Git ou da entrega não excepciona `processed/`. T030 tampouco inclui coordenadas no teste de schema. A correção documental de B17 da rodada anterior deixa de se sustentar.  
   **Correção:** manter coordenadas apenas transitoriamente na transformação para H3; retirá-las do schema persistido de `processed/` e incluir essa proibição no teste dos derivados reais. Inventariar e corrigir artefatos existentes, se contiverem essas colunas. As referências à v1.2.0 e FR-013 foram propagadas, mas não resolvem essa incompatibilidade.

**IMPORTANTE**

2. **[IMPORTANTE — R4-4; parcialmente resolvido] Proveniência ainda não reproduzível pelo registro fornecido.**  
   **Arquivo + trecho:** T005 afirma “comandos, versões e saídas em […] `PROVENIENCIA.md`”; esse arquivo registra o comando de conversão e o resultado “0 linhas diferentes”, mas não o comando completo de download, SQL da comparação ou hash/versão do script conversor.  
   **Correção:** anexar esses elementos e vincular `fonte` + `linha` ao hash do parquet efetivamente indexado. A distinção entre conteúdo tabular idêntico e bytes diferentes foi corrigida.

3. **[IMPORTANTE — R4-5; parcialmente resolvido] Delimitação do vazamento não chegou a todos os critérios.**  
   **Arquivo + trecho:** `plan.md`, V, delimita data do fato, features e ajuste dentro das dobras; FR-009 ainda diz que “o split pela data do fato controla o vazamento temporal”; US3 e SC-003 verificam apenas que nenhuma data de teste antecede a última de treino.  
   **Correção:** alinhar FR-009 e os critérios ao escopo do plano, incluindo construção das features e ajuste das transformações nas dobras. Preservar a ressalva de disponibilidade histórica não reconstruída. O título de US3 e o status PLANEJADO foram corrigidos.

4. **[IMPORTANTE — R4-7; contradição residual] As três definições de ausência coexistem com a regra antiga.**  
   **Arquivo + trecho:** `research.md`, D-04, ainda afirma que chaves sem registros nas features “permanecem no snapshot como `sem_dado`”; o novo subitem define o snapshot pelo histórico pontuável de jan–set. T016 mantém “sem nenhum registro”, sem exigir que seja pontuável.  
   **Correção:** substituir a regra antiga e distinguir explicitamente elegibilidade das features, alvo pontuável e histórico pontuável do snapshot. Especificar testes para chave só com rubrica sem peso, chave nova em ago–set e chave com histórico sem alvo. A adição das definições, isoladamente, não resolveu a contradição.

5. **[IMPORTANTE — R4-8; não resolvido] População avaliada permanece incompletamente definida.**  
   **Arquivo + trecho:** `spec.md`, Edge Cases, exclui ausência de registro no rótulo; D-04 conserva “719 das 933”.  
   **Correção:** definir a população como chaves com features elegíveis e alvo pontuável observado; publicar cobertura e exclusões por origem, suporte por classe e tratamento das chaves novas. Não apresentar a métrica como representativa de todas as chaves do app.

6. **[IMPORTANTE — R4-9; não resolvido] Quartis ainda prometem classes de tamanho igual.**  
   **Arquivo + trecho:** `spec.md`, Clarifications: “25% das chaves em cada nível”.  
   **Correção:** retirar a garantia e fixar método de quantil, desigualdades nas bordas, tratamento de cortes coincidentes e classes ausentes. Pontuações iguais devem receber o mesmo nível.

7. **[IMPORTANTE — R4-10; não resolvido] População dos cortes segue ambígua.**  
   **Arquivo + trecho:** D-04: “T1 a T4 juntos”; `docs/SPEC-ML.md`, §5: “chaves com dado do treino”.  
   **Correção:** definir quais pares chave×origem entram, elegibilidade pontuável, ponderação e exclusões, tanto no ajuste final quanto nas dobras. Documentar a repetição de chaves e meses sobrepostos.

8. **[IMPORTANTE — R4-11; não resolvido] Teste temporal admite igualdade na fronteira.**  
   **Arquivo + trecho:** T021: “nenhuma data de feature é posterior ao início da janela do rótulo”.  
   **Correção:** exigir `data_feature < inicio_rotulo`. Acrescentar verificação de ajuste das transformações apenas no treino da dobra e invariância das features passadas a alterações dos registros futuros.

9. **[IMPORTANTE — R4-12; parcialmente resolvido] Regra de seleção pode ser fixada depois da busca.**  
   **Arquivo + trecho:** T025 executa a busca; T026 só então registra “a regra de seleção”; D-04 lista métricas sem principal, agregação ou desempate.  
   **Correção:** fixar essas regras antes de T025, incluindo tratamento de classes ausentes. Planejar suporte, matriz de confusão, subestimações graves e comparação pareada com baselines; tratar dependências na incerteza ou declarar a limitação. O congelamento antes das métricas de ago–set não substitui essa definição prévia.

10. **[IMPORTANTE — R4-13; não resolvido] Baseline histórica continua subespecificada.**  
    **Arquivo + trecho:** D-04/T024: “nível da própria chave na janela de features”, chamado de “persistência”.  
    **Correção:** explicitar normalização por meses e horas, cortes do treino da dobra e tratamento da ausência de histórico pontuável. Nomear a média histórica acumulada e incluir comparação com os dois meses anteriores nas mesmas chaves elegíveis.

11. **[IMPORTANTE — R4-14; parcialmente resolvido] Números antigos e incompletude de setembro continuam apresentados como fatos atuais.**  
    **Arquivo + trecho:** T033 retirou “178” fixo; `spec.md` e `plan.md` mantêm esse número. O plano chama a distribuição antiga de “Medido, sob a regra clarificada”, embora `research.md` explique que ela usou soma sem normalização. Assumptions, plano e T033 afirmam “setembro incompleto”.  
    **Correção:** marcar números antigos como exploração sob outra fórmula e substituir referências operacionais por saídas finais rastreáveis. Tratar incompletude como hipótese até apresentar evidência de cobertura; menor volume não a demonstra.

12. **[IMPORTANTE — R4-15; não resolvido] Unidade de contagem e deduplicação não foram demonstradas.**  
    **Arquivo + trecho:** `docs/SPEC-ML.md`, §4: “linha idêntica (mesmo BO e rubrica); 1 caso”; `PROVENIENCIA.md`: “2.390 duplicata_removida”.  
    **Correção:** enumerar os campos de igualdade, demonstrar a unidade da fonte e reconciliar as duas contagens por universo e regra. Mesmo BO e rubrica não bastam para provar duplicidade.

13. **[IMPORTANTE — R4-16; não resolvido] Datas inválidas e precedência de destinos permanecem sem regra.**  
    **Arquivo + trecho:** `data-model.md` enumera motivos de coordenada/hora e define `usada` como “o resto”; `bo_id` é descrito como usado “só para deduplicar”, apesar da detecção de conflitos por BO.  
    **Correção:** definir validação da data e calendário do workbook, destino para data inválida, precedência determinística, motivos auxiliares e universo de detecção dos conflitos. Documentar também o uso transitório do identificador para essa detecção.

14. **[IMPORTANTE — R4-17; não resolvido] Exemplo artificial permanece no contrato.**  
    **Arquivo + trecho:** contrato, Fixture: “não são dado real”, com `nivel: 1` e `n_registros: 12`; `plan.md`, princípio I, usa o caráter ilustrativo para justificar “OK”.  
    **Correção:** substituir por esquema de tipos ou amostra real rastreável. A exceção constitucional cobre somente entradas unitárias; marcar o exemplo como ilustrativo não cria outra exceção.

15. **[IMPORTANTE — R4-18; parcialmente resolvido] Sensibilidade espacial foi planejada, mas a regra de cobertura continua aberta.**  
    **Arquivo + trecho:** T030 determina deslocamento de ±100 m; contrato e D-07 dizem “células que cobrem o perímetro”; Assumptions ainda afirma impacto irrelevante.  
    **Correção:** retirar a irrelevância presumida; definir seleção por centro ou interseção, tratamento das bordas e observação parcial. Na sensibilidade, especificar direções, comparação por chave célula×faixa e contagem separada de mudanças de nível, `sem_dado` e cobertura. A coordenada provisória aprovada não é uma falha.

16. **[IMPORTANTE — R4-20; parcialmente resolvido] Replanejamento não antecipou a decisão sobre os modelos exigidos.**  
    **Arquivo + trecho:** T027 ainda decide sobre LSTM/KMeans+PCA depois da avaliação em T026; dependências mantêm US4 após US3, embora T032 determine pedido antecipado.  
    **Correção:** decidir a exigência da rubrica antes da busca e explicitar T032 como exceção às dependências sequenciais. Rota, produtor da fixture, aceite por leitura e cronograma foram esclarecidos; viabilidade de execução continua por demonstrar, sem constituir bloqueante documental.

17. **[IMPORTANTE — R4-21; parcialmente resolvido] Estados de evidência seguem inconsistentes.**  
    **Arquivo + trecho:** V e VII agora estão PLANEJADO, mas o plano conclui “sem violações”; princípio I está “OK” apesar do exemplo artificial. `research.md` diz “Nenhum `NEEDS CLARIFICATION`”, embora liste decisões pendentes; plano/spec chamam candidatos de “executados” com T025 aberto.  
    **Correção:** distinguir planejado, implementado, executado, verificado e aprovado, vinculando cada estado à evidência. Retirar conclusões globais incompatíveis com pendências e com o bloqueante desta revisão.

18. **[IMPORTANTE — R4-22; parcialmente resolvido] Encerramento por achado foi acrescentado, mas envios intermediários não foram harmonizados.**  
    **Arquivo + trecho:** T036 exige disposição individual e revalidação; US4 e a meta da Fase 6 ainda exigem red-team antes de “qualquer envio intermediário”, enquanto T020a/T020b precedem T035.  
    **Correção:** explicitar qual revisão cobre cada envio intermediário ou harmonizar a exigência com a constituição, que exige red-team antes da entrega e confirmação humana em qualquer envio. Preservar a disposição individual e a verificação dos artefatos finais.

**Importantes da rodada 4 resolvidos documentalmente**

19. **[R4-6 — RESOLVIDO; execução pendente] Congelamento da escolha antes da avaliação exploratória.**  
    **Arquivo + trecho:** T026 exige `selecao_modelo.json` com vencedor, configuração e métricas de CV antes de consultar ago–set, classificando mudanças posteriores como exploração.  
    **Correção adicional:** esclarecer “antes de consultar as métricas dos modelos em ago–set”, pois a distribuição já foi vista em T017. A definição prévia da regra de seleção continua no item 9.

20. **[R4-19 — RESOLVIDO NO ESCOPO APROVADO; execução pendente] Interpretação da intensidade.**  
    **Arquivo + trecho:** contrato descreve intensidade registrada, pesos convencionais, exposição desconhecida e subnotificação; T033 exige sensibilidade com pesos iguais e 1/2/3 sem seleção por ago–set.  
    **Correção adicional:** nenhuma necessária para essa decisão documental. A sensibilidade ainda precisa ser executada e reportada.

21. **[R4-23 — RESOLVIDO DOCUMENTALMENTE; evidência pendente] Hash do CSV separado do hash do manifest.**  
    **Arquivo + trecho:** T019 exige `SHA256(CSV) = .sha256 = manifest.csv_sha256` e registra separadamente o hash dos bytes do manifest aprovado.  
    **Correção adicional:** nenhuma na igualdade especificada. No fechamento, preservar a versão exata aprovada e demonstrar seu vínculo com os artefatos entregues; os marcadores `[X]` não comprovam esse vínculo.

Permanecem objeções bloqueantes.