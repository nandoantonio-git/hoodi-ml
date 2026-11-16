# Red-team da spec — rodada 4 (Codex CLI real)

Gerado em 2026-11-12. Comando: codex exec --ignore-user-config --ignore-rules --ephemeral -s read-only --skip-git-repo-check -c features.shell_tool=false -c features.apply_patch_freeform=false. O Codex vê só o texto do prompt, não os arquivos. Prompt: /tmp/rt-hoodi-spec4/prompt.txt

Revisão documental das transcrições fornecidas. Não inspecionei código, parquets, manifest ou registros de aprovação, nem executei testes. Os marcadores `[X]` não constituem verificação independente. Considero a emenda constitucional v1.2.0 autorizada conforme informado.

**Bloqueantes**

Nenhum bloqueante documental remanescente identificado. B1 e B17 podem ser retirados neste escopo; isso não certifica os artefatos nem encerra as pendências de entrega.

**Correções verificadas**

1. **[B1 — CORRIGIDO DOCUMENTALMENTE] Fórmula e vínculo da aprovação.**  
   **Arquivo + trecho:** `tasks.md`, T016: “÷ 9 meses ÷ horas da faixa”; teste “54 pontos em 9 meses = 1,0 […] 6 h e 2,0 […] 3 h”. `spec.md`, FR-006: divisão por meses e horas, igual para treino, teste e snapshot. T017: “hash do manifest e a configuração […] aprovados”.  
   **Verificação:** os resultados numéricos estão corretos: `54/9/6 = 1` e `54/9/3 = 2`. A contradição apontada na rodada 3 foi removida.  
   **Pendência:** comprovar a implementação, a execução do teste e o registro efetivo da aprovação vinculada ao artefato final. Não há evidência desses resultados nas transcrições.

2. **[B17 — CORRIGIDO DOCUMENTALMENTE; VERIFICAÇÃO PENDENTE] Privacidade e uso transitório de identificadores.**  
   **Arquivo + trecho:** constituição VII delimita derivados e entregas, exclui raw/interim do Git e da entrega e estabelece retenção; T010 determina `bo_id` “só em memória”, “nunca […] gravado” e “quarentena sem coordenada”; `data-model.md` também restringe `bo_id` à memória.  
   **Verificação:** a decisão explícita de governança resolve a incompatibilidade anterior quanto à cópia fiel de raw/interim; a persistência autorizada de `bo_id` foi retirada. A exceção constitucional para quarentena não obriga conservar coordenadas: T010 pode ser mais restritivo.  
   **Pendência:** inventário em `ml/dados/README.md` e teste dos schemas derivados, conforme informado. A ausência desses trabalhos futuros não é tratada como falha nesta rodada, nem como prova de anonimato.

**Importantes — pendências para implementação e fechamento**

Nos caminhos seguintes, os arquivos da feature pertencem a `specs/001-risco-h3-faixa-horaria/`.

3. **[IMPORTANTE — PENDENTE] Propagar a política de privacidade vigente.**  
   **Arquivo + trecho:** `spec.md` e `tasks.md` ainda citam “v1.1.0”; FR-013 mantém “o sistema MUST NOT conter dado pessoal”; `plan.md` repete a proibição geral. T030 ainda não explicita o inventário por camada.  
   **Correção:** alinhar essas referências à v1.2.0, incorporando campos permitidos, conteúdo, acesso, retenção e descarte por camada, incluindo logs, notebooks e prompts. No `data-model.md`, distinguir campos transitórios de colunas persistidas: a tabela ainda contém `lat`, `lon`, data e hora sem essa separação completa. É harmonização da decisão já autorizada, sem necessidade de reabrir sua aprovação.

4. **[IMPORTANTE — PENDENTE; achado 5] Reprodução da proveniência.**  
   **Arquivo + trecho:** T005: “parquets idênticos”; `PROVENIENCIA.md`: hashes diferentes e `EXCEPT ALL = 0` nos dois sentidos.  
   **Correção:** escrever “conteúdo tabular idêntico, arquivos binariamente diferentes”; guardar comando de download, SQL e saídas da comparação e hash/versão do conversor. Igualdade de multiconjunto não comprova ordem: qualquer referência por `linha` precisa de origem estável. O bloqueante documental de proveniência permanece encerrado.

5. **[IMPORTANTE — PENDENTE; achado 3] Garantia excessiva sobre vazamento.**  
   **Arquivo + trecho:** FR-009: “controla o vazamento temporal”; US3: “Modelo avaliado sem vazamento”; `plan.md`, princípio V: “OK”.  
   **Correção:** delimitar o controle à separação por data do fato, construção das features e ajuste dentro das dobras. Manter explícita a disponibilidade histórica não reconstruída. A ressalva retrospectiva de FR-009 não elimina as garantias dos demais trechos.

6. **[IMPORTANTE — PENDENTE; achado 4] Congelar a escolha antes das métricas exploratórias.**  
   **Arquivo + trecho:** D-04: escolha “só a CV”; T026 consulta ago–set antes de T027 apresentar a escolha.  
   **Correção:** registrar regra, vencedor, configuração e resultados de CV antes de T026. Mudança posterior deve constar como exploração adicional.

7. **[IMPORTANTE — PENDENTE; achado 7] Separar três significados de ausência de dado.**  
   **Arquivo + trecho:** contrato: nenhum registro “pontuável”; T016: “sem nenhum registro”; D-04: ausência nas features implica `sem_dado` no snapshot.  
   **Correção:** distinguir elegibilidade das features, alvo pontuável observado e histórico pontuável de jan–set. Testar chave apenas com rubrica sem peso, chave nova em ago–set e chave com histórico sem alvo. Ausência nas features não determina ausência no snapshot histórico.

8. **[IMPORTANTE — PENDENTE; achado 8] Delimitar a população avaliada.**  
   **Arquivo + trecho:** `spec.md`, Edge Cases, exclui chaves sem registro no rótulo; D-04 cita “719 das 933”.  
   **Correção:** declarar que a métrica cobre chaves com histórico elegível e alvo pontuável observado; publicar cobertura por origem, exclusões, suporte por classe e tratamento das chaves novas. Não extrapolar para todo o universo do app.

9. **[IMPORTANTE — PENDENTE; achado 9] Quartis e empates.**  
   **Arquivo + trecho:** `spec.md`, Clarifications: “25% das chaves em cada nível”.  
   **Correção:** retirar a garantia e definir método de quantil, desigualdades nas bordas, cortes coincidentes e classes ausentes. Pontuações iguais devem receber classificação consistente.

10. **[IMPORTANTE — PENDENTE; achado 10] População dos cortes.**  
    **Arquivo + trecho:** D-04: “T1 a T4 juntos”; SPEC §5: “chaves com dado do treino”.  
    **Correção:** definir pares chave×origem elegíveis, ponderação e exclusões. Documentar repetição de chaves e sobreposição de meses, inclusive na análise de incerteza.

11. **[IMPORTANTE — PENDENTE; achado 11] Fronteira temporal do teste.**  
    **Arquivo + trecho:** T021: nenhuma feature “posterior ao início” do rótulo.  
    **Correção:** exigir estritamente `data_feature < inicio_rotulo`. Verificar ajuste das transformações só no treino da dobra e invariância das features passadas a alterações nos registros futuros.

12. **[IMPORTANTE — PENDENTE; achado 12] Seleção e incerteza.**  
    **Arquivo + trecho:** T025 define a busca; D-04 lista métricas sem principal, desempate ou agregação.  
    **Correção:** fixar essas regras antes da busca, incluindo classes ausentes. Reportar suporte, matriz de confusão, subestimações graves e comparação pareada com baselines; tratar dependências na incerteza ou declarar a limitação. MAE de nível não mede erro de probabilidade de vitimização.

13. **[IMPORTANTE — PENDENTE; achado 13] Baseline histórica.**  
    **Arquivo + trecho:** D-04/T024: “nível da própria chave na janela de features”.  
    **Correção:** explicitar divisão por meses e horas, cortes do treino da dobra e ausência de histórico pontuável. Nomear como média histórica acumulada e comparar também com os dois meses anteriores nas mesmas chaves elegíveis.

14. **[IMPORTANTE — PENDENTE; achado 14] Números exploratórios e cobertura de setembro.**  
    **Arquivo + trecho:** `plan.md`: “Medido, sob a regra clarificada”; `research.md`: distribuição calculada sem normalização; T033 fixa “178 chaves”; Assumptions afirma setembro “incompleto”.  
    **Correção:** substituir números fixos pelas saídas rastreáveis da execução final. Tratar incompletude como hipótese até haver evidência de cobertura; menor volume não basta.

15. **[IMPORTANTE — PENDENTE; achado 15] Granularidade e deduplicação.**  
    **Arquivo + trecho:** constituição IV: “uma linha […] é um crime”; SPEC §4: “linha idêntica (mesmo BO e rubrica); 1 caso”; proveniência: “2.390” duplicatas.  
    **Correção:** definir campos exatos de igualdade e demonstrar a unidade da fonte. Reconciliar 1 versus 2.390 por universo e regra, sem presumir erro pela diferença. Preservar rastreabilidade minimizada e estável; mesmo BO e rubrica não bastam para demonstrar duplicidade.

16. **[IMPORTANTE — PENDENTE; achado 16] Datas inválidas e precedência.**  
    **Arquivo + trecho:** `data-model.md` enumera motivos de coordenada/hora e define `usada` como “o resto”.  
    **Correção:** validar datas e calendário do workbook; definir motivo/destino para data inválida, precedência determinística, motivos auxiliares e universo de detecção dos conflitos por BO. Esclarecer também seu uso transitório para conflitos, pois T010/modelo mencionam apenas deduplicação.

17. **[IMPORTANTE — PENDENTE; achado 18] Exemplo artificial no contrato.**  
    **Arquivo + trecho:** contrato, Fixture: “não são dado real”, com `nivel: 1` e `n_registros: 12`; constituição I excepciona somente entradas unitárias.  
    **Correção:** substituir por esquema de tipos ou amostra real rastreável. A emenda ao princípio VII não alterou essa restrição.

18. **[IMPORTANTE — PENDENTE DE DECISÃO DO RESPONSÁVEL; achado 19] Cobertura espacial.**  
    **Arquivo + trecho:** D-07/contrato: células que “cobrem o perímetro”; centro provisório; Assumptions declara deslocamento irrelevante.  
    **Correção:** fechar centro, geometria, seleção H3 por centro/interseção e bordas; fornecer geometria ao consumidor e indicar observação parcial nas células de borda. Medir o efeito antes de afirmar irrelevância.

19. **[IMPORTANTE — PENDENTE DE DECISÃO DO RESPONSÁVEL; achado 20] Interpretação da intensidade.**  
    **Arquivo + trecho:** contrato: “pontos de gravidade”, “Comparável entre células e entre faixas”; SPEC §1: “risco registrado”.  
    **Correção:** descrever intensidade registrada ponderada por mês e hora, com pesos convencionais, exposição desconhecida, cobertura e subnotificação. A normalização temporal não demonstra comparabilidade de risco individual. Planejar sensibilidade aos pesos sem selecioná-los por ago–set.

20. **[IMPORTANTE — PENDENTE DE DECISÃO DO RESPONSÁVEL; achado 21] Dependências e cronograma.**  
    **Arquivo + trecho:** T027 confirma rubrica depois de T026; T032 deixa Ficha/ODS para o final; T020b pede rota sem tarefa produtora; prazos de 11/11.  
    **Correção:** antecipar decisões de escopo e conteúdo, definir responsável e aceite da rota e replanejar com margem de reexecução antes de 16/11. Viabilidade ainda não demonstrada.

21. **[IMPORTANTE — PENDENTE; achado 22] Gates e estados de evidência.**  
    **Arquivo + trecho:** `plan.md`: todos “OK”, “sem violações”; T021/modelagem pendentes; pesquisa: nenhum `NEEDS CLARIFICATION` apesar das decisões abertas.  
    **Correção:** separar planejado, implementado, executado, verificado e aprovado. Atualizar os gates conforme evidência. T017 ganhou o requisito de vínculo, mas seu registro efetivo não foi fornecido.

22. **[IMPORTANTE — PENDENTE; achado 23] Critério de encerramento.**  
    **Arquivo + trecho:** T036 exige correções e reexecução, sem disposição individual; US4 exige revisão “antes de qualquer envio”, enquanto constituição VII agora exige antes da entrega.  
    **Correção:** manter disposição e evidência por achado; harmonizar envios intermediários e entrega acadêmica, preservando confirmação humana. Revalidar os artefatos finais; quantidade de testes não encerra questões metodológicas.

23. **[IMPORTANTE — PENDENTE; inconsistência adicional] Hash do manifest versus hash do CSV.**  
    **Arquivo + trecho:** T019 manda conferir “hash do `manifest.json` […] com o do `.sha256`”; o contrato define esse `.sha256` como hash do CSV.  
    **Correção:** exigir `SHA256(CSV) = conteúdo do .sha256 = manifest.csv_sha256`. Registrar separadamente o hash dos bytes do manifest aprovado em T017. Como ele contém `gerado_em`, uma regeneração pode mudar seu hash mesmo com CSV idêntico; definir qual versão fica vinculada à aprovação.

Os achados 2 e 6 permanecem encerrados documentalmente, sem nova evidência de execução nesta rodada. As pendências acima continuam necessárias para o fechamento; não foram promovidas a bloqueantes apenas por ainda não terem sido executadas.

SEM OBJEÇÃO BLOQUEANTE RESTANTE