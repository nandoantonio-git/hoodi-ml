# Red-team real (Codex CLI) — implementação v3, rodada 1

Data: 15/11/2026. Comando: `codex exec --sandbox read-only --ephemeral`. Parecer abaixo sem edição.

## Achados

1. **ALTA — a ordenação por empate tolerante pode não ser determinística.**  
   **Arquivo:** `ml/rota.py:117–125`. O comparador trata pares dentro da tolerância como empate e usa distância como próximo critério. Essa equivalência não é transitiva: A pode empatar com B, B com C, mas A não com C. Nesse caso, `sorted()` não recebe uma ordem consistente, e o ranking pode contrariar o contrato, que exige desempate pela distância e depois pela entrada.  
   **Correção sugerida:** definir uma regra de ordenação transitiva, por exemplo agrupar pontuações em classes de empate antes de ordenar, ou usar comparação exata na ordenação e reservar a tolerância para uma etapa explícita de desempate.

2. **MÉDIA — a suavização da T-A dilui células pentagonais.**  
   **Arquivo:** `ml/ta_descritiva.py:67–72`. O código sempre calcula a média sobre seis posições. Células pentagonais têm cinco vizinhas; a posição ausente fica como zero e entra no divisor. A proposta define a média das vizinhas H3 e zero para vizinhas fora de U1, não para uma vizinha inexistente.  
   **Correção sugerida:** dividir pelo número de vizinhas existentes, mantendo zero para vizinhas existentes que estejam fora de U1. Acrescentar um teste com célula pentagonal.

3. **MÉDIA — a seção 10 descreve incorretamente o limite de dado insuficiente.**  
   **Arquivo:** `scripts/gerar_notebook.py:754–755`. O notebook diz que a rota fica sem posição “acima de 30% de km sem dado”. O contrato e o código aplicam o limite à soma de `pct_sem_dado` e `pct_fora_da_cobertura`; portanto, uma rota pode ficar insuficiente só por estar fora da cobertura, ou pela soma das duas parcelas. A tabela de exemplo também não mostra `pct_fora_da_cobertura`.  
   **Correção sugerida:** dizer explicitamente “mais de 30% sem dado **ou fora da cobertura, somados**” e exibir ambas as parcelas ou a soma usada na regra.

4. **MÉDIA — o notebook registra como decisão tomada algo que o plano ainda marca como aberto.**  
   **Arquivos:** `scripts/gerar_notebook.py:699–704`; `docs/PLANO-EXECUCAO-V3-r2.md:249–253`. A seção 10 chama `L=3`, anel `k=1` e cooldown de “decisão do Nando, 15/11”, mas o plano ainda lista a aprovação do bloco A como decisão pendente e exige decisão separada para esse aditivo. Também estão presentes B e C, embora o plano os condicione a uma decisão opcional.  
   **Correção sugerida:** reconciliar o registro da decisão com o plano; se a decisão não estiver documentada, identificar esses valores como configuração da demonstração, não como escolha aprovada.

5. **MÉDIA — o nome real do experimento MLflow diverge do definido no plano.**  
   **Arquivo:** `scripts/registrar_mlflow.py:91–95`. O plano pede o experimento `hoodi-v3-exploratorio`, mas `EXP_V3` cria/seleciona `5 · v3 · exploratório (alerta e rotas)`. O primeiro nome aparece apenas como tag lógica.  
   **Correção sugerida:** usar `hoodi-v3-exploratorio` como nome real do experimento, ou registrar no plano que o nome com prefixo é intencional.

6. **MÉDIA — os testes da T-A não demonstram as garantias temporais que dizem cobrir.**  
   **Arquivo:** `tests/test_ta_descritiva.py:36–53`. O teste de λ apenas confere o artefato existente; não recalcula a seleção nem verifica que o JSON foi congelado antes das origens reportadas. O teste do RF confere apenas a quantidade de janelas, não que rótulos, cortes e features de cada origem excluam dados futuros. Isso deixa sem teste direto dois requisitos centrais da proposta.  
   **Correção sugerida:** adicionar testes que inspecionem as janelas e os limites temporais dos dados usados por origem, além de uma checagem reproduzível da seleção de λ contra o artefato congelado.

## Verificações que passaram

- A política implementa `L=3`, `k=1`, cooldown de 30 min, conversão para `America/Sao_Paulo`, bordas `[início, fim)`, filtro `com_dado` e desativação por hash divergente. O JSON confere com o SHA-256 calculado e declara a cobertura do anel por faixa, inclusive o máximo de **61,6% das células**.
- A referência de rota segue a discretização e a soma de metros especificadas; o contrato documenta as limitações e os vetores de fronteira. Os arquivos `.sha256` conferem com os JSON.
- A T-A usa λ=0, selecionado em 2024 e gravado antes das origens reportadas; escores e RF são calculados com passado anterior ao alvo. Os artefatos declaram `test_seen=true`, ausência de inferência e a escolha dos hiperparâmetros do RF após ver ago–set. `codigo_alterado_sem_commit` está marcado como `true`.
- Nas seções 9–11, não encontrei afirmação de validação ou superioridade. A seção 11 também relata corretamente as medianas e contagens de origens dos artefatos. A referência a mais avisos aparece como possibilidade, condicionada à medição em trajetos reais.
- Pelo `git status`, `selecao_modelo.json`, snapshot v1, `SPEC-ML.md` e `specs/001` permanecem intocados. A revisão foi somente leitura.

**Contagem:** 1 ALTA, 5 MÉDIAS, 0 BAIXAS.

**Veredito: não pronto para commit.** Corrigir a ordenação não transitiva e reconciliar a linguagem da seção 10 e o status das decisões; os demais achados devem ser resolvidos ou explicitamente aceitos, especialmente os testes de vazamento temporal.