# Red-team real (Codex CLI) — rodada 2 da spec/plano (2026-11-11)

Relatório bruto, sem edição. Triagem do JARVIS no chat. Veredito do Codex: permanecem objeções bloqueantes (1, 5, 17).

A revisão abaixo usa os conteúdos dos arquivos transcritos na mensagem. Não há ferramenta de leitura local disponível nesta sessão; portanto, não verifiquei código, hashes, logs ou artefatos gerados. Um `[X]` documenta uma declaração de conclusão, não comprova a execução. A numeração corresponde à rodada 1; os caminhos abreviados pertencem a `specs/001-risco-h3-faixa-horaria/`.

1. **[BLOQUEANTE — aberta] A fórmula ainda não é única.**  
   **Arquivo + trecho:** `docs/SPEC-ML.md`, §5, inclui “÷ n meses […] ÷ horas”; `research.md`, D-04, ainda define “soma de pesos […] em taxa mensal”; `tasks.md`, T016, termina com “snapshot = soma de pesos de jan–set ÷ 9”; contrato, `manifest.janela_nivel`, repete “soma ÷ 9”. FR-006 também não exige explicitamente as duas divisões.  
   **Correção:** usar a mesma fórmula e unidade em todos esses pontos, incluindo persistência e cortes. Demonstrar numericamente a implementação e vincular distribuição, aprovação e snapshot à fórmula efetivamente executada.

2. **[BLOQUEANTE na rodada 1 — encerrada no desenho documental] O snapshot passou a ser identificado como histórico observado.**  
   **Arquivo + trecho:** contrato, `natureza`: “mapa histórico observado […] não é previsão”; `data-model.md`: “Sem `nivel_previsto`”; T028 separa o backtest do arquivo do app, e T033 exige essa distinção no relatório.  
   **Correção restante:** comprovar que o manifest gerado e a apresentação final contêm essa delimitação. A separação dos dois entregáveis está agora expressa; não mantenho o bloqueante conceitual original.

3. **[IMPORTANTE — parcialmente corrigida] A limitação de disponibilidade histórica foi declarada, mas permanecem promessas incompatíveis.**  
   **Arquivo + trecho:** FR-009 reconhece o backtest retrospectivo e a impossibilidade de provar disponibilidade na origem. Entretanto, ainda afirma que o split “controla o vazamento temporal”; US3 continua “Modelo avaliado sem vazamento”; `plan.md` aprova o princípio V como “OK”.  
   **Correção:** uniformizar a linguagem como separação por data do fato, com disponibilidade histórica não reconstruída. Distinguir essa limitação dos controles implementáveis contra uso de dados futuros e ajuste indevido de transformações. A objeção original foi mitigada, mas não eliminada de todos os documentos.

4. **[IMPORTANTE — parcialmente corrigida] Ago–set foi reclassificado, mas o fluxo de seleção continua ambíguo.**  
   **Arquivo + trecho:** `research.md`, D-04: “avaliação exploratória, não confirmatória” e escolha “só a CV”; T026 avalia os melhores candidatos no teste antes de T027 apresentar a escolha.  
   **Correção:** registrar a escolha e sua regra antes de T026, com resultados de CV e configuração congelada. Manter ago–set como exploratório e registrar qualquer alteração posterior. A alegação de avaliação final independente foi retirada; falta alinhar as tarefas.

5. **[BLOQUEANTE — encerramento não comprovado] T005 agora relata reprodução, mas falta evidência auditável e há contradição documental.**  
   **Arquivo + trecho:** T005 declara novo download, igualdade de hash, reconversão e parquets idênticos; `docs/SPEC-ML.md`, §2, ainda diz “não baixei de novo”; `research.md` mantém o script de pesquisa “fora do repositório”.  
   **Correção:** anexar registro com hashes completos do download e dos parquets, comandos, versões, contagens e comparação; atualizar §2 e incorporar os scripts necessários à auditoria. O texto de T005 atende à ação solicitada, mas, sozinho, não permite verificar seu cumprimento. Não afirmo que a execução não ocorreu; afirmo que seu fechamento não está demonstrado no material revisado.

6. **[IMPORTANTE na rodada 1 — encerrada documentalmente] FR-003 agora contém cinco intervalos.**  
   **Arquivo + trecho:** FR-003: “0–6, 6–12, 12–18, 18–21, 21–24”; contrato e modelo de dados usam os mesmos limites.  
   **Correção restante:** comprovar testes das fronteiras e da correspondência entre IDs e nomes. A inconsistência textual original foi removida.

7. **[IMPORTANTE — aberta] “Sem dado” continua com critérios incompatíveis.**  
   **Arquivo + trecho:** contrato e `data-model.md`, Snapshot: nenhum registro **pontuável**; `spec.md`, Edge Cases: nenhum registro **utilizável**; D-04 e T016: nenhum **registro**. D-04 ainda transporta ausência na janela de features para o snapshot, cuja janela é diferente.  
   **Correção:** definir separadamente elegibilidade de features, disponibilidade de rótulo e status do snapshot. Especificar o tratamento de rubricas sem peso, chaves novas e chaves sem alvo; incluir testes desses três casos.

8. **[IMPORTANTE — aberta] O estimando continua condicionado à ocorrência futura de registros.**  
   **Arquivo + trecho:** `spec.md`, Edge Cases: chave sem registro no rótulo “fica fora das métricas”; D-04 informa “719 das 933”.  
   **Correção:** declarar que as métricas avaliam somente chaves com histórico elegível **e rótulo pontuável observado**. Publicar cobertura e motivos de exclusão por origem, suporte por classe entre rotuláveis e tratamento das chaves novas. A declaração genérica de viés não estabelece desempenho sobre todas as chaves atendidas.

9. **[IMPORTANTE — aberta] A promessa de 25% por nível permanece.**  
   **Arquivo + trecho:** `spec.md`, Clarifications: “25% das chaves em cada nível”. Não há método de quantil, convenção de bordas ou política para cortes coincidentes.  
   **Correção:** remover a garantia de proporções exatas; fixar algoritmo, desigualdades e comportamento diante de empates e classes ausentes. Pontuações iguais devem receber tratamento consistente.

10. **[IMPORTANTE — aberta] A população dos quantis e sua ponderação continuam insuficientemente definidas.**  
    **Arquivo + trecho:** D-04: “T1 a T4 juntos”; `docs/SPEC-ML.md`, §5: “quartis entre as chaves […] do treino”.  
    **Correção:** declarar que a população é de pares chave×origem elegíveis, definir se cada par recebe peso igual e justificar a repetição de meses e chaves. Considerar essa dependência na análise de incerteza; não apresentar os pares como observações independentes.

11. **[IMPORTANTE — aberta] O teste temporal ainda permite igualdade com o início do alvo.**  
    **Arquivo + trecho:** T021: “nenhuma data de feature é posterior ao início da janela do rótulo”; SC-003 verifica apenas ordenação global.  
    **Correção:** exigir `data_feature < inicio_rotulo`. Testar também ajuste de imputação, escala, seleção, cortes e agregações dentro de cada dobra. Incluir teste de invariância: alterar registros futuros não pode modificar features passadas. Isso não resolve a disponibilidade histórica reconhecida em FR-009.

12. **[IMPORTANTE — aberta] Falta regra operacional de seleção e tratamento da incerteza.**  
    **Arquivo + trecho:** `plan.md` e D-04 listam macro-F1, balanced accuracy e MAE; T025 define busca, mas não métrica principal, desempate ou agregação das dobras.  
    **Correção:** fixar esses critérios antes da busca; definir classes consideradas e tratamento de classes ausentes. Reportar suporte, matriz de confusão, subestimações graves e comparação pareada com baselines. Quantificar incerteza respeitando dependências ou declarar explicitamente sua limitação. MAE de nível não é erro de probabilidade de vitimização.

13. **[IMPORTANTE — aberta] A persistência continua subespecificada.**  
    **Arquivo + trecho:** D-04 e T024: “nível da […] chave na janela de features”.  
    **Correção:** definir fórmula por mês e hora, cortes exclusivos do treino da dobra e comportamento sem histórico pontuável. Identificar essa baseline como média histórica acumulada e acrescentar persistência dos dois meses anteriores, comparando nas mesmas chaves elegíveis.

14. **[IMPORTANTE — aberta] Hipóteses e números exploratórios continuam apresentados como resultados estabelecidos.**  
    **Arquivo + trecho:** `spec.md`, Assumptions: setembro “é incompleto”; `plan.md`: distribuição “Medido, sob a regra clarificada”; `research.md` esclarece que a distribuição usa soma sem normalização; T033 exige “178 chaves”.  
    **Correção:** tratar menor volume como observação, sem inferir incompletude sem evidência de cobertura. Substituir os números por saídas rastreáveis da regra final e fazer T033 exigir a contagem calculada, não um valor previamente fixado.

15. **[IMPORTANTE — aberta] “Linha = crime” e deduplicação continuam sem validação suficiente.**  
    **Arquivo + trecho:** constituição IV: “Uma linha […] é um crime registrado”; `docs/SPEC-ML.md`, §4: “linha idêntica (mesmo BO e rubrica)”; T007 repete essa regra.  
    **Correção:** demonstrar a granularidade da fonte e definir exatamente quais campos originais determinam igualdade. Preservar referência de aba/linha e exemplos anonimizados auditáveis. Mesmo BO e rubrica não bastam para demonstrar duplicidade de ocorrência.

16. **[IMPORTANTE — aberta] Datas inválidas e precedência de destinos continuam ausentes.**  
    **Arquivo + trecho:** `data-model.md` enumera apenas motivos de coordenada/hora; `usada` é “o resto”; T010 apenas manda converter a data serial.  
    **Correção:** definir validação de data, calendário do workbook e destino para datas inválidas. Estabelecer precedência determinística dos destinos, preservar motivos auxiliares e explicitar o universo em que conflitos por BO são calculados antes dos filtros.

17. **[BLOQUEANTE — aberta] A privacidade continua presumida; `bo_id` preserva uma chave de vinculação.**  
    **Arquivo + trecho:** `data-model.md`: `bo_id = NUM_BO + ANO_BO + NOME_DELEGACIA`; conversão “sem limpar”; T010 permite “`bo_id` interno”; T014 examina apenas CSV, manifest e fixture; `plan.md` mantém princípio VII “OK”.  
    **Correção:** inventariar campos **e conteúdo** de raw, interim, processed, quarentena, logs, notebook e relatórios; definir campos permitidos, acesso, retenção e verificações. Concatenar identificadores e chamar o resultado de “interno” não anonimiza nem impede vinculação. Justificar sua necessidade e restringir sua persistência; eventual pseudonimização também não comprova anonimato. Se o raw contiver dados incompatíveis com “nenhum dado pessoal”, resolver explicitamente a incompatibilidade constitucional. Não há evidência suficiente para afirmar que o sistema contém dados pessoais, mas tampouco para aprovar sua ausência.

18. **[IMPORTANTE — parcialmente corrigida] Nome e cardinalidade foram corrigidos; valores inventados continuam no contrato.**  
    **Arquivo + trecho:** contrato usa `noite_cedo` e “15 linhas”; porém mantém exemplo “não são dado real” com `nivel: 1` e `n_registros: 12`. Constituição I só excepciona entradas manuais em testes unitários.  
    **Correção:** substituir o exemplo por esquema de tipos ou amostra real rastreável. A constituição v1.1.0 não estende a exceção a exemplos documentais; o `plan.md` não pode encerrar essa incompatibilidade apenas chamando o exemplo de ilustrativo.

19. **[IMPORTANTE — aberta] A cobertura nas bordas continua indefinida.**  
    **Arquivo + trecho:** D-07 e contrato: “todas as células que cobrem o perímetro”; manifest mantém centro provisório; `spec.md` afirma impacto não relevante de aproximadamente 50 m.  
    **Correção:** fixar centro, geometria, inclusão das bordas e seleção de células por centro ou interseção. Informar ao consumidor que células de borda têm observação parcial e fornecer geometria exata para consulta de cobertura. Medir diferenças em registros, células e níveis antes de afirmar irrelevância.

20. **[IMPORTANTE — aberta] A interpretação de “risco” e comparabilidade continua excessiva.**  
    **Arquivo + trecho:** contrato: “Comparável entre células e entre faixas”; pergunta principal mantém “nível de risco registrado”.  
    **Correção:** definir o resultado como intensidade registrada ponderada por mês e hora, limitada pela cobertura, exposição desconhecida, subnotificação e recorte espacial. Normalização temporal não estabelece comparabilidade de risco individual. Prever análise de sensibilidade aos pesos sem ajustá-los pelos resultados de ago–set.

21. **[IMPORTANTE — aberta] As decisões críticas continuam tardias e a rota permanece sem definição.**  
    **Arquivo + trecho:** T027 consulta exigências de modelos depois de T026; T032 pede Ficha/ODS na fase final; T020b exige “rota”; não há tarefa que defina ou produza essa rota.  
    **Correção:** antecipar verificação da rubrica e coleta de conteúdo; definir responsável, escopo e aceite da rota. Estabelecer entregas diárias, esforço estimado e margem para revisão/reexecução até 16/11. O material não demonstra viabilidade do cronograma.

22. **[IMPORTANTE — parcialmente corrigida] A versão constitucional foi atualizada; os gates continuam prematuramente aprovados.**  
    **Arquivo + trecho:** `spec.md` e `tasks.md` agora referenciam v1.1.0. Entretanto, `plan.md` ainda declara “sem violações”, inclusive privacidade “OK”; `research.md` afirma não haver clarificações abertas enquanto lista decisões pendentes; T017 não identifica artefatos aprovados.  
    **Correção:** reabrir verificações sem evidência, distinguir planejado, implementado, executado, verificado e aprovado, e vincular decisões a versões/hashes de fórmula, cortes e artefatos. A troca de versão não encerra a objeção de governança.

23. **[IMPORTANTE — aberta] A revisão ainda não tem critério de encerramento dos achados.**  
    **Arquivo + trecho:** T036 exige corrigir e reexecutar testes/notebook; US4 exige revisão “antes de qualquer envio”, mas T020a/b antecedem T035.  
    **Correção:** exigir disposição individual dos 23 achados, evidência da correção e nova verificação dos bloqueantes sobre os artefatos finais. Definir se a revisão é exigida antes de envios intermediários ou apenas da entrega acadêmica, alinhando US4 e dependências; preservar confirmação humana em todos os envios. Testes passando não encerram objeções metodológicas ou constitucionais.

**Permanecem objeções bloqueantes.**