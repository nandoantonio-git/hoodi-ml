# Red-team real (Codex CLI 0.156.1) — spec/plano/tarefas — rodada 1

Data: 2026-11-11. Execução: `codex exec --ephemeral -s read-only`, shell e apply_patch desligados; entrada = constituição v1.1.0, SPEC-ML, spec, plan, research, data-model, contrato e tasks. Relatório abaixo é o texto bruto devolvido pelo Codex, sem edição. Status: **5 bloqueantes e 18 importantes abertos; nenhuma objeção foi fechada.** O Codex não declarou "sem objeção bloqueante restante".

Triagem do JARVIS (verificada nos arquivos em 2026-11-11, não é fechamento de objeção):
- Confirmados nos arquivos: objeção 6 (FR-003 lista 4 intervalos), objeção 18 (exemplo do contrato usa `faixa: 3` com `faixa_nome: "noite"`; o nome correto é `noite_cedo`; fixture "cerca de 12 linhas" para 3 células × 5 faixas = 15), objeção 22 (spec.md linha 11 cita constituição v1.0.0).
- Objeção 1, parcial: o código (`ml/rotulo.py`, `ml/snapshot.py`) e o contrato usam soma ÷ 9 meses ÷ horas da faixa; SPEC-ML §5 diz só "soma" e T016 diz "soma ÷ 9". É inconsistência de documentos, e o código segue o contrato. Falta decidir se a unidade é por hora.
- Dependem de decisão do Nando: 2 (snapshot é histórico observado, não previsão do classificador), 3, 4 (teste já usado na aprovação de T017), 17 (privacidade), 21 (rubrica LSTM/KMeans+PCA).

---

1. **[BLOQUEANTE] A fórmula do alvo muda entre documentos e tarefas já marcadas como concluídas.**  
   **Trechos:** `docs/SPEC-ML.md`, §5: “Pontuação da célula×faixa = soma dos pesos”; `research.md`, D-04: “em taxa mensal”; contrato, `pontuacao_mensal`: “÷ 9 meses ÷ horas da faixa”; `tasks.md`, T016 `[X]`: “soma de pesos de jan–set ÷ 9 aplicada aos cortes do treino”.  
   **Problema:** soma, pontos/mês e pontos/mês/hora são grandezas distintas. A divisão por horas muda especialmente a comparação das faixas de 3h com as de 6h. Não há evidência fornecida de que o código concluído implemente o contrato.  
   **Correção:** fixar uma fórmula única, com unidade explícita, para rótulos, cortes, persistência e snapshot. Atualizar todos os documentos e verificar numericamente a implementação; regenerar distribuições, aprovação e artefatos se necessário.

2. **[BLOQUEANTE] O produto entregue ao app não é a previsão formulada como objetivo.**  
   **Trechos:** `spec.md`, Clarifications: “nível de cada chave em ago–set, usando só informação de jan–jul”; contrato, `nivel`: “observado em jan–set”; `data-model.md`: “Sem `nivel_previsto`”.  
   **Problema:** o app recebe uma classificação histórica calculada diretamente, sem depender do classificador. O ML produz apenas um backtest separado. Isso precisa ser explicitado como delimitação do projeto, sob risco de apresentar agregação histórica como previsão operacional.  
   **Correção:** separar formalmente os dois entregáveis: mapa histórico observado e experimento retrospectivo de previsão. Ajustar pergunta, critérios de aceite e apresentação acadêmica. Se houver exigência de previsão no app, falta definir horizonte futuro, origem, artefato e avaliação correspondente.

3. **[BLOQUEANTE] Dividir pela data do fato não garante disponibilidade histórica dos dados.**  
   **Trechos:** `docs/SPEC-ML.md`, §2: arquivo “atualizado no servidor em 28/10/2026”; §6: “Split temporal pela data do fato”; `research.md`, D-03: “Features (só registros até aqui)”.  
   **Problema:** um fato de janeiro registrado ou corrigido em setembro pode entrar nas features de uma previsão supostamente feita em fevereiro. Um único arquivo obtido posteriormente não demonstra o que estava disponível em cada origem.  
   **Correção:** usar data de registro/disponibilização e versões históricas, se disponíveis, impondo disponibilidade até a origem. Se isso não puder ser reconstruído, declarar o backtest como retrospectivo sobre a versão de outubro, sem afirmar ausência de vazamento de disponibilidade.

4. **[BLOQUEANTE] O teste já participa de decisões antes da seleção final do modelo.**  
   **Trechos:** `tasks.md`, T017 `[X]`: mostrar distribuição “treino, teste e snapshot” para aprovação; T026: avaliar os melhores candidatos “no Teste”; T027: depois disso, apresentar “a escolha do modelo”.  
   **Problema:** o fluxo permite ajustar o alvo após observar o teste e escolher o modelo pelas métricas de ago–set. Nesse caso, ago–set deixa de ser uma avaliação final independente.  
   **Correção:** fixar alvo, features, métrica de seleção e modelo usando somente treino/CV antes da avaliação final. Registrar quais decisões já usaram ago–set. Se houve adaptação, apresentar esse período como avaliação exploratória e reservar outro período intocado quando disponível.

5. **[BLOQUEANTE] A cadeia de proveniência e reprodução do raw está incompleta, apesar do checkpoint aprovado.**  
   **Trechos:** `docs/SPEC-ML.md`, §2: “não baixei de novo para comparar o hash”; `tasks.md`, T005 `[X]`: “o script 00 não foi reexecutado”; `research.md`: script de pesquisa “fora do repositório”.  
   **Problema:** tamanho igual ao servidor não comprova identidade do arquivo. Reproduzir um relatório a partir dos mesmos parquets não comprova que esses parquets correspondam ao XLSX declarado. T005 não cumpriu sua própria condição de conclusão.  
   **Correção:** documentar a obtenção oficial e verificar os bytes obtidos; executar raw→parquet em ambiente reproduzível, registrando hashes, versões e contagens. Reabrir T005 até concluir. Incorporar os scripts necessários à auditoria.

6. **[IMPORTANTE] Há literalmente quatro intervalos em um requisito de cinco faixas.**  
   **Trecho:** `spec.md`, FR-003: “uma de 5 faixas (0–6, 6–12, 12–18, 18–24)”.  
   **Problema:** uma implementação fiel a FR-003 diverge do contrato e de `config.py`.  
   **Correção:** substituir 18–24 por 18–21 e 21–24; testar as fronteiras 0h, 6h, 12h, 18h e 21h e a correspondência entre identificador e nome.

7. **[IMPORTANTE] “Sem dado” possui definições incompatíveis.**  
   **Trechos:** `spec.md`, Edge Cases: “só a chave sem nenhum registro utilizável”; `research.md`, D-04: “sem registros na janela de features”; contrato: “nenhum registro pontuável”; T016: “só para chave sem nenhum registro”.  
   **Problema:** uma chave com apenas rubricas sem peso pode virar nível 0 em uma implementação e `sem_dado` em outra. Também se confundem ausência de histórico, ausência de alvo e ausência de pontuação.  
   **Correção:** definir elegibilidade por artefato e janela, distinguindo esses motivos. Testar explicitamente chave com apenas rubricas sem peso, chave nova no teste e chave com histórico, mas sem registro no alvo.

8. **[IMPORTANTE] A avaliação responde a uma pergunta condicionada ao futuro.**  
   **Trechos:** `spec.md`, Edge Cases: chave sem registro no rótulo “fica fora das métricas”; `research.md`, D-04: “só 719 das 933 chaves de treino têm registro no teste”.  
   **Problema:** as métricas medem desempenho apenas onde se descobriu posteriormente haver registro. Não avaliam todas as chaves às quais uma previsão seria oferecida, nem as chaves novas. Declarar viés não transforma essa métrica em desempenho operacional.  
   **Correção:** formular explicitamente o estimando condicionado à existência de registro pontuável; publicar cobertura e exclusões por origem e classe. Separar elegibilidade da previsão da disponibilidade de rótulo, sem converter ausência em nível 0.

9. **[IMPORTANTE] Quartis não garantem 25% das chaves em cada nível.**  
   **Trechos:** `spec.md`, Clarifications: “25% das chaves em cada nível”; `research.md`: distribuição de treino “212; 252; 227; 242”.  
   **Problema:** pontuações discretas e empates podem impedir quatro grupos iguais ou até gerar cortes repetidos. Não estão definidos método de quantil, inclusão das bordas ou tratamento de classes ausentes.  
   **Correção:** especificar algoritmo, desigualdades e política para cortes coincidentes; preservar pontuações iguais no mesmo nível. Remover a promessa de 25% exatos e testar esses casos.

10. **[IMPORTANTE] A definição dos cortes dá peso implícito a meses e chaves repetidos.**  
    **Trecho:** `research.md`, D-04: cortes dos rótulos “T1 a T4 juntos”; D-03: janelas mar–abr, abr–mai, mai–jun, jun–jul.  
    **Problema:** abril, maio e junho aparecem em dois alvos; março e julho, em um. Chaves recorrentes também aparecem mais vezes. Isso não equivale a quartis entre chaves únicas de jan–jul, como outros trechos sugerem. A sobreposição no ajuste final não é, por si só, vazamento para o teste, mas altera o alvo e a dependência amostral.  
    **Correção:** declarar a população usada nos quantis — pares chave×origem — e justificar a ponderação. Não tratar essas linhas como observações independentes na análise de incerteza.

11. **[IMPORTANTE] Os testes temporais previstos são insuficientes e têm uma fronteira permissiva.**  
    **Trechos:** `spec.md`, SC-003: “Nenhuma data de teste é anterior à última data de treino”; T021: “nenhuma data de feature é posterior ao início da janela do rótulo”.  
    **Problema:** T021 permite igualdade com o início do alvo, contrariando “anteriores”. A ordenação global tampouco detecta scaler, imputação, seleção de features, agregações de vizinhos ou cortes ajustados fora do treino da dobra.  
    **Correção:** exigir `data_feature < inicio_rotulo`; testar o ajuste de todas as transformações dentro de cada dobra, os cortes locais e a disponibilidade histórica. Incluir um teste em que alterar dados futuros não modifique features passadas.

12. **[IMPORTANTE] A avaliação não tem regra de seleção nem incerteza especificadas.**  
    **Trechos:** `plan.md`: “macro-F1, balanced accuracy e erro absoluto médio”; `tasks.md`, T025: “ao menos 10 combinações” por candidato, com duas dobras.  
    **Problema:** as métricas são pertinentes, mas falta definir qual escolhe o modelo, desempates, classes ausentes e comparação pareada com as baselines. Duas dobras temporalmente próximas e dependência espacial limitam a robustez da busca. MAE de nível também pressupõe distâncias iguais entre níveis derivados de quantis.  
    **Correção:** pré-fixar métrica principal e desempate; reportar suporte por classe, matriz de confusão, erros graves de subestimação e resultados por dobra. Quantificar incerteza respeitando dependência espacial/temporal ou declarar explicitamente a limitação; não interpretar MAE ordinal como erro em probabilidade de crime.

13. **[IMPORTANTE] A baseline de persistência não está suficientemente definida.**  
    **Trecho:** `research.md`, D-04: “usa o nível da própria chave na janela de features como previsão”.  
    **Problema:** isso usa médias históricas de 2 a 7 meses para prever dois meses, enquanto “persistência” poderia significar os dois meses imediatamente anteriores. Faltam fórmula normalizada, cortes por dobra e comportamento quando não há histórico pontuável.  
    **Correção:** definir a baseline exatamente e acrescentar persistência da última janela de dois meses, quando disponível. Comparar todas as alternativas nas mesmas chaves elegíveis.

14. **[IMPORTANTE] Há afirmações apresentadas como fatos sem evidência suficiente no material.**  
    **Trechos:** `spec.md`: “setembro é incompleto (~73 mil contra ~85 mil por mês)”; `plan.md`: distribuição “Medido, sob a regra clarificada”; `research.md`: essa distribuição usa soma sem normalização e “os números do pipeline [...] serão diferentes”.  
    **Problema:** menor volume não comprova incompletude. O plano reutiliza uma distribuição calculada sob outra regra como caracterização do modelo atual. T033 ainda exige “178 chaves” antes de confirmar esse total após limpeza e elegibilidade finais.  
    **Correção:** distinguir observação, hipótese e comprovação; substituir números exploratórios por saídas rastreáveis do pipeline final. Exigir evidência de cobertura/publicação para afirmar incompletude.

15. **[IMPORTANTE] A unidade “linha = crime” precisa de validação, e a deduplicação está ambígua.**  
    **Trechos:** constituição, IV: “Uma linha [...] é um crime registrado”; `docs/SPEC-ML.md`, §4: “linha idêntica (mesmo BO e rubrica)”; `data-model.md`: BO definido por três campos.  
    **Problema:** a constituição estabelece uma interpretação, mas não comprova a granularidade da fonte. Mesmo BO e rubrica não garantem identidade de linha nem identidade de crime. Deduplicar após remover colunas pode eliminar registros distintos.  
    **Correção:** validar granularidade e chave com documentação da fonte e inspeção auditável; definir igualdade sobre os campos originais pertinentes, preservar identificador de linha/aba e registrar exemplos reais anonimizados de decisões.

16. **[IMPORTANTE] A classificação de qualidade não cobre datas inválidas nem precedência de motivos.**  
    **Trechos:** `data-model.md`, destinos: quarentena lista apenas problemas de coordenada/hora; “`usada`: o resto”; T010: converter data serial.  
    **Problema:** data vazia, inválida ou incompatível com o calendário do workbook pode cair fora da janela ou ser usada indevidamente. Uma linha também pode ser duplicada, conflitante e externa ao perímetro simultaneamente, sem precedência formal.  
    **Correção:** acrescentar validação de data e motivo próprio; definir prioridade determinística dos destinos e preservar todos os motivos auxiliares. Calcular conflitos por BO no escopo explicitado antes de filtros que possam escondê-los.

17. **[BLOQUEANTE] O atendimento à privacidade foi declarado sem um controle que cubra o pipeline inteiro.**  
    **Trechos:** constituição, VII: “Nenhum dado pessoal”; `data-model.md`: conversão “sem limpar”; T010: “`bo_id` interno”; T014: verificação apenas de CSV, manifest e fixture; `plan.md`: princípio VII “OK”.  
    **Problema:** o material não demonstra quais campos existem no raw, interim e quarentena, nem se `bo_id` mantém o identificador original recuperável. Verificar nomes de colunas na saída não prova ausência de dados pessoais no sistema.  
    **Correção:** inventariar campos e conteúdo, estabelecer lista permitida e verificar também raw, intermediários, quarentena, logs e notebook. Se a fonte contiver dados pessoais incompatíveis com a constituição, resolver a incompatibilidade explicitamente com Nando; não marcar o princípio como atendido por presunção.

18. **[IMPORTANTE] O contrato contém valores inventados fora da exceção constitucional e erros internos.**  
    **Trechos:** constituição, I: entradas à mão “só em testes unitários”; contrato: exemplo “não são dado real”, com `nivel: 1`, `n_registros: 12`; exemplo com `faixa: 3`, `faixa_nome: "noite"`; fixture “cerca de 12 linhas, 3 células vizinhas × 5 faixas”.  
    **Problema:** o exemplo ilustrativo não está abrangido pela exceção literal; faixa 3 deveria ser `noite_cedo`; três células completas produzem 15 linhas.  
    **Correção:** substituir valores por um esquema de tipos ou por amostra realmente extraída e rastreável; corrigir nome e cardinalidade. Não tratar “ilustrativo” como autorização constitucional implícita.

19. **[IMPORTANTE] A geometria da cobertura pode produzir interpretações incorretas nas bordas.**  
    **Trechos:** `research.md`, D-07: “todas as células que cobrem o perímetro”; contrato: fora do perímetro é tratado pelo app; `spec.md`: mudança do centro “não altera [...] de forma relevante (~50 m)”.  
    **Problema:** não está definido se cobertura significa centro dentro do bbox ou interseção. Células de borda recebem apenas registros da parte interna, mas seu identificador representa o hexágono inteiro. A irrelevância de deslocar o centro não foi demonstrada.  
    **Correção:** fixar centro, geometria e regra de interseção; fornecer a cobertura exata ao consumidor e testar pontos de borda. Medir alterações em células, registros e níveis antes de afirmar impacto irrelevante.

20. **[IMPORTANTE] “Risco” e comparabilidade excedem o que a pontuação mede.**  
    **Trechos:** contrato: pontuação “Comparável entre células e entre faixas”; constituição, IV: “Risco vem do crime registrado”; `spec.md`: pesos “ponto de partida”.  
    **Problema:** pontos de gravidade por mês/hora medem intensidade registrada ponderada. Não estimam probabilidade individual de vitimização, exposição, subnotificação ou segurança de trajeto. A normalização temporal não resolve esses fatores, nem o recorte desigual das células de borda.  
    **Correção:** definir operacionalmente “nível de intensidade de crimes registrados”; limitar a interpretação de comparabilidade e testar sensibilidade aos pesos sem escolher pesos pelo teste. Não derivar garantia de rota segura dessa escala.

21. **[IMPORTANTE] As tarefas adiam decisões que podem invalidar o trabalho e não demonstram viabilidade até o congelamento.**  
    **Trechos:** T027 decide sobre LSTM/KMeans+PCA depois de T026; T032 solicita conteúdo obrigatório apenas na fase final; T020b exige “rota” sem tarefa de produção; congelamento em 16/11.  
    **Problema:** faltam estimativas, responsáveis e folga para revisão e reexecução. A rota não tem definição nem aceite, e app/API estão fora do escopo. Confirmar exigências acadêmicas depois de treinar pode provocar retrabalho no caminho crítico.  
    **Correção:** verificar imediatamente a rubrica original e decidir os modelos obrigatórios; obter Ficha/ODS antecipadamente; definir responsável e significado de “rota”. Planejar entregas diárias até 16/11, incluindo conversão reproduzível, notebook completo, revisão e correções. O material não sustenta garantia de prazo.

22. **[IMPORTANTE] A governança está inconsistente e o gate constitucional foi aprovado prematuramente.**  
    **Trechos:** `spec.md` e `tasks.md`: constituição “v1.0.0”; constituição fornecida: “1.1.0”; `research.md`: “Nenhum `NEEDS CLARIFICATION` fica aberto”; `plan.md`: “sem violações”; permanecem pendentes rubrica, centro e contrato.  
    **Problema:** decisões abertas e verificações incompletas aparecem como resolvidas. T017 está concluída, mas não há no material registro da aprovação vinculado à fórmula, cortes e artefato exatos.  
    **Correção:** atualizar referências, reabrir gates não comprovados e registrar decisões com versão/hash. Distinguir “implementado”, “executado”, “verificado” e “aprovado”.

23. **[IMPORTANTE] A revisão final não tem critério explícito de encerramento dos bloqueantes.**  
    **Trechos:** T035: revisão real; T036: “Aplicar as correções [...] e reexecutar `pytest` e o notebook”; T039: entrega.  
    **Problema:** testes passando não demonstram que objeções metodológicas, documentais ou constitucionais foram resolvidas. Também há tensão entre US4, “antes de qualquer envio”, e os envios T020a/b anteriores à revisão.  
    **Correção:** exigir registro de disposição de cada achado e nova verificação dos bloqueantes sobre os artefatos finais. Especificar se a revisão antecede apenas a entrega acadêmica ou também os envios intermediários, mantendo confirmação humana em todos os envios.

**Permanecem objeções bloqueantes.**