# Red-team real (Codex CLI) — rodada 3 da spec/plano (2026-11-12)

Relatório bruto, sem edição. Veredito: permanecem objeções bloqueantes (1 e 17).

**Permanecem dois bloqueantes: fórmula ainda contraditória e privacidade sem verificação suficiente.** A proveniência recebeu documentação suficiente para retirar o bloqueante documental, com ressalvas de reprodução.

Esta revisão considera as transcrições fornecidas. Não encontrei ferramenta de leitura local disponível; portanto, não inspecionei código, artefatos nem executei os 33 testes. A remoção de `bo_id` e o resultado dos testes são declarações do autor, não verificações independentes desta rodada. Os caminhos abreviados abaixo pertencem a `specs/001-risco-h3-faixa-horaria/`.

**Objeções bloqueantes**

1. **[BLOQUEANTE — parcialmente corrigida] A fórmula continua contraditória em uma tarefa concluída.**  
   **Arquivo + trecho:** `docs/SPEC-ML.md` §5, `research.md` D-04 e contrato agora concordam com `soma dos pesos ÷ meses ÷ horas`. Entretanto, `tasks.md` T016 ainda termina com “snapshot = soma de pesos de jan–set ÷ 9 aplicada aos cortes do treino”. FR-006 continua sem exigir explicitamente as duas divisões.  
   **Correção:** atualizar T016 e FR-006; comprovar a fórmula no código, no manifest e nos cortes efetivamente usados. Incluir verificação numérica: uma soma de 54 pontos em nove meses deve produzir 1 ponto/mês/hora numa faixa de 6h e 2 numa de 3h. Vincular a aprovação T017 ao hash/configuração dessa execução. A normalização inicial de T016 não elimina a contradição específica sobre o snapshot.

17. **[BLOQUEANTE — parcialmente corrigida] Remover identificadores dos derivados reduz a exposição, mas não encerra a privacidade.**  
   **Arquivo + trecho:** inventário informado: raw/interim preservam “30 colunas”; `usadas` conserva data, hora, coordenadas e rubrica; quarentena conserva `fonte,linha`. `data-model.md` ainda apresenta `bo_id`, e T010 permite “`bo_id` interno”. Constituição VII e FR-013 exigem “nenhum dado pessoal” no sistema, não apenas no snapshot.  
   **Constatação:** o inventário declarado dos derivados não contém identificadores explícitos de BO. Entretanto, faltam nomes e análise de conteúdo das 30 colunas, cobertura de logs/notebooks/relatórios e regras de acesso e retenção. Coordenadas, horário e rubrica podem permitir vinculação; `fonte,linha` também permite reencontrar o registro quando a fonte e a ordem são recuperáveis. Isso não demonstra, isoladamente, identificação pessoal, mas impede concluir anonimato apenas pela ausência de quatro nomes de coluna. Fonte pública e exclusão do Git não resolvem essa questão.  
   **Correção:** concluir agora o inventário e a inspeção de conteúdo, documentar campos permitidos por camada, acesso, retenção e verificações sobre os arquivos existentes; atualizar T010 e o modelo de dados. Se forem encontrados dados pessoais no raw/interim, resolver a incompatibilidade constitucional por minimização ou decisão explícita de governança. T030/T033 futuros não comprovam o cumprimento atual.

**Achados importantes e fechamento documental**

5. **[IMPORTANTE — bloqueante documental retirado; execução não verificada] A proveniência agora oferece uma trilha auditável, mas incompleta para reprodução independente.**  
   **Arquivo + trecho:** `ml/dados/raw/PROVENIENCIA.md` apresenta URL, data, tamanho, hash completo do XLSX, versões, comando de conversão, abas, contagens, hashes anteriores/novos, comparação bidirecional e hash do snapshot. `docs/SPEC-ML.md` §2 removeu “não baixei de novo”.  
   **Constatação:** a reconciliação apresentada soma 814.900 linhas. O registro distingue corretamente igualdade de conteúdo de igualdade binária dos parquets. Entretanto, T005 ainda diz “parquets idênticos”, enquanto os hashes diferem.  
   **Correção:** registrar o comando exato de download, os comandos/SQL e saídas da comparação, além da versão ou hash do conversor; esclarecer em T005 “conteúdo tabular idêntico, arquivos binariamente diferentes”. `EXCEPT ALL` confirma igualdade de multiconjunto, não ordem — relevante para a rastreabilidade por `linha`. Incorporar o script exploratório se seus números forem usados como evidência final. Não é necessário exigir um hash oficial inexistente para encerrar este achado.

3. **[IMPORTANTE — aberta] A linguagem sobre vazamento continua excessiva.**  
   **Arquivo + trecho:** FR-009: o split “controla o vazamento temporal”; US3: “Modelo avaliado sem vazamento”; `plan.md`: princípio V “OK”.  
   **Correção:** distinguir separação por data do fato, prevenção de uso de registros futuros e ajuste dentro das dobras da disponibilidade histórica não reconstruída. Retirar a garantia geral de ausência de vazamento.

4. **[IMPORTANTE — aberta] A escolha anterior à avaliação exploratória não está operacionalizada.**  
   **Arquivo + trecho:** D-04 diz que a escolha usa “só a CV”; T026 avalia candidatos em ago–set antes de T027 apresentar a escolha.  
   **Correção:** registrar regra, vencedor, configuração e resultados de CV antes de consultar métricas de ago–set. Qualquer alteração posterior deve ficar registrada como exploração adicional.

7. **[IMPORTANTE — aberta] “Sem dado” mistura três populações diferentes.**  
   **Arquivo + trecho:** contrato: nenhum registro “pontuável”; Edge Cases: nenhum “utilizável”; D-04: ausência na janela de features implica `sem_dado` no snapshot.  
   **Correção:** definir separadamente elegibilidade de features, existência de alvo pontuável e status histórico de jan–set. Testar chave apenas com rubrica sem peso, chave nova no teste e chave com histórico sem alvo. Uma chave nova pode ter dado no snapshot mesmo sem elegibilidade para o classificador.

8. **[IMPORTANTE — aberta] A métrica permanece condicionada à observação futura do alvo.**  
   **Arquivo + trecho:** Edge Cases exclui chaves sem registro no rótulo; D-04 cita “719 das 933”.  
   **Correção:** declarar o estimando como desempenho entre chaves com histórico elegível e alvo pontuável observado. Publicar cobertura por origem, exclusões por motivo, suporte por classe e tratamento das chaves novas. Não extrapolar esse desempenho para todo o universo do app.

9. **[IMPORTANTE — aberta] Quartis não garantem 25% por nível.**  
   **Arquivo + trecho:** `spec.md`, Clarifications: “25% das chaves em cada nível”.  
   **Correção:** remover a garantia; fixar método de quantil, desigualdades nas bordas e comportamento com empates, cortes coincidentes e classes ausentes. Pontuações iguais precisam receber classificação consistente.

10. **[IMPORTANTE — aberta] Falta definir a população dos cortes.**  
    **Arquivo + trecho:** D-04: “T1 a T4 juntos”; SPEC §5: “quartis entre as chaves […] do treino”.  
    **Correção:** especificar pares chave×origem elegíveis, ponderação e exclusões. Explicar a repetição de chaves e meses entre origens; não tratar esses pares como observações independentes na incerteza.

11. **[IMPORTANTE — aberta] O teste temporal ainda permite o instante inicial do alvo.**  
    **Arquivo + trecho:** T021: nenhuma data de feature “posterior ao início” do rótulo.  
    **Correção:** exigir `data_feature < inicio_rotulo`; verificar transformações ajustadas apenas no treino da dobra e invariância das features passadas ao alterar registros futuros. A ordenação global de SC-003 é insuficiente.

12. **[IMPORTANTE — aberta] Seleção e incerteza continuam sem regras executáveis.**  
    **Arquivo + trecho:** T025 define a busca; D-04 lista métricas sem principal, desempate ou agregação das dobras.  
    **Correção:** fixar essas regras antes da busca, incluindo classes ausentes. Reportar suporte, matriz de confusão, subestimações graves e comparação pareada com baselines. Estimar incerteza respeitando dependências ou declarar a limitação; MAE de nível não mede erro de probabilidade de vitimização.

13. **[IMPORTANTE — parcialmente corrigida] A fórmula geral avançou; a baseline continua ambígua.**  
    **Arquivo + trecho:** D-04/T024: persistência usa “nível da própria chave na janela de features”.  
    **Correção:** explicitar normalização por meses e horas, cortes exclusivos do treino da dobra e tratamento sem histórico pontuável. Nomear essa baseline como média histórica acumulada; comparar também com os dois meses anteriores, nas mesmas chaves elegíveis.

14. **[IMPORTANTE — aberta] Números exploratórios ainda aparecem como resultados finais.**  
    **Arquivo + trecho:** `plan.md` chama a distribuição de “Medido, sob a regra clarificada”; `research.md` informa que ela usa soma sem normalização; T033 exige “178 chaves”; Assumptions afirma setembro “incompleto”.  
    **Correção:** substituir números fixos por resultados rastreáveis da execução final. Menor volume não comprova incompletude; usar essa hipótese apenas com evidência de cobertura ou identificá-la como hipótese.

15. **[IMPORTANTE — aberta, com nova discrepância] Granularidade e deduplicação seguem sem demonstração.**  
    **Arquivo + trecho:** constituição IV: “Uma linha […] é um crime”; SPEC §4: “linha idêntica (mesmo BO e rubrica); 1 caso medido”; proveniência: **2.390 duplicatas removidas**.  
    **Correção:** definir exatamente os campos de igualdade e demonstrar a granularidade da fonte. Explicar a diferença entre 1 e 2.390 por universo e regra aplicada, sem presumir erro apenas pela diferença. Preservar referência estável de aba/linha e exemplos auditáveis minimizados; mesmo BO e rubrica não demonstram duplicidade.

16. **[IMPORTANTE — aberta] Datas inválidas e precedência de destinos permanecem indefinidas.**  
    **Arquivo + trecho:** `data-model.md` enumera motivos de coordenada/hora e define `usada` como “o resto”; T010 manda converter o serial.  
    **Correção:** validar datas e calendário do workbook, criar destino/motivo para data inválida, fixar precedência determinística e preservar motivos auxiliares. Definir em qual universo se detectam conflitos por BO, antes ou depois de cada filtro.

18. **[IMPORTANTE — aberta] O exemplo continua incompatível com a exceção constitucional vigente.**  
    **Arquivo + trecho:** contrato: valores “não são dado real”, incluindo `nivel: 1` e `n_registros: 12`; constituição I excepciona somente entradas de testes unitários.  
    **Correção:** substituir por esquema de tipos ou amostra real rastreável. A etiqueta “ilustrativo” não amplia a exceção.

19. **[IMPORTANTE — aberta] A cobertura espacial ainda não é reproduzível pelo contrato.**  
    **Arquivo + trecho:** D-07/contrato: células que “cobrem o perímetro”; manifest: centro provisório; Assumptions: deslocamento sem impacto relevante.  
    **Correção:** fixar centro, geometria, regras de borda e seleção H3 por centro ou interseção. Fornecer geometria exata ao consumidor e indicar observação parcial nas células de borda. Medir efeitos antes de declarar irrelevância.

20. **[IMPORTANTE — aberta] A unidade foi corrigida, mas a interpretação continua excessiva.**  
    **Arquivo + trecho:** contrato: “pontos de gravidade” e “Comparável entre células e entre faixas”; SPEC §1: “nível de risco registrado”.  
    **Correção:** apresentar intensidade registrada ponderada por mês e hora, com pesos convencionais. Explicitar cobertura, exposição desconhecida, subnotificação e recorte espacial; normalização temporal não demonstra comparabilidade de risco individual. Planejar sensibilidade aos pesos sem escolhê-los pelo desempenho em ago–set.

21. **[IMPORTANTE — aberta] Dependências críticas e rota seguem sem definição.**  
    **Arquivo + trecho:** T027 verifica aceitação dos modelos após T026; T032 deixa Ficha/ODS para o final; T020b pede rota sem tarefa produtora.  
    **Correção:** antecipar confirmação da rubrica e coleta de conteúdo; definir responsável, escopo e aceite da rota. Replanejar os prazos de 11/11, já passados na data desta revisão, com entregas e margem para reexecução antes de 16/11. Não há evidência suficiente para afirmar viabilidade do cronograma.

22. **[IMPORTANTE — aberta] Os gates continuam aprovados além da evidência disponível.**  
    **Arquivo + trecho:** `plan.md`: todos os princípios “OK” e “sem violações”; T021 e tarefas de modelagem ainda pendentes; pesquisa declara ausência de clarificações enquanto lista decisões pendentes.  
    **Correção:** separar planejado, implementado, executado, verificado e aprovado. Reabrir gates sem comprovação e vincular T017 à fórmula, cortes, configuração e hashes aprovados.

23. **[IMPORTANTE — aberta] Ainda falta critério verificável para encerrar a revisão.**  
    **Arquivo + trecho:** T036 exige correção e reexecução, mas não disposição individual dos achados; US4 exige revisão “antes de qualquer envio”, enquanto T020a/b podem anteceder T035.  
    **Correção:** registrar os 23 achados com disposição, justificativa e evidência; exigir nova verificação dos bloqueantes nos artefatos finais. Harmonizar revisão antes de envios intermediários versus entrega acadêmica, preservando confirmação humana. Os 33 testes declarados não encerram questões metodológicas ou constitucionais.

Os achados **2 e 6 permanecem encerrados documentalmente**, sem nova evidência de execução nesta rodada.

**Permanecem objeções bloqueantes.**