<!-- Saída integral do Codex CLI (codex exec --sandbox read-only --ephemeral), 15/11/2026, sobre docs/PLANO-EXECUCAO-V3-r1.md -->
## Resolução dos achados da rodada 1

1. **Resolvido — Escopo opcional.** O plano reserva o obrigatório à seção 9 e condiciona os blocos opcionais à decisão do Nando; também os rotula como demonstrações retrospectivas, não validadas. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:15-22`.

2. **Resolvido — Alerta “antes da entrada”.** A regra agora se chama alerta por proximidade e declara que não é direcional. Isso resolve a ambiguidade da demonstração, embora não implemente a intenção original de alertar antes da entrada. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:63-73`.

3. **Parcial — Reprodutibilidade e unidade da pontuação de rota.** O plano especifica amostragem, células, agregação e arredondamento, e chama a saída de índice observado, não de contagem esperada. Mas a igualdade entre Python e C# ainda depende de convenções não fixadas; veja o achado 11. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:96-121`.

4. **Resolvido — Limiar como orçamento de alertas.** O critério é chamado de exploratório e o texto nega que seja orçamento de área ou de alertas; medir alertas em trajetos fica para a fase 2. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:75-83`.

5. **Resolvido — Faixa horária.** O alerta usa a hora local no instante de avaliação, com fuso e bordas do contrato. A rota usa a faixa de partida para toda a viagem, declaradamente como limitação da demonstração. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:68-70, 112`.

6. **Parcial — Ownership e integração.** O plano separa quem define e quem executa, identifica o vínculo por hash e lista contrato HTTP, implementação C# e entrega/consumo como dependências externas. Porém, a forma de servir a política continua pendente do Abner, sem mecanismo definido. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:48-61`.

7. **Resolvido — Uso de dados já vistos.** Os blocos opcionais são identificados como retrospectivos, `test_seen=true` e sem validação ou promessa de produto. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:19-22, 82-83`.

8. **Resolvido — Caminho e versionamento do contrato novo.** Os artefatos novos ficam em `docs/contratos-v3/`, fora de `specs/001` e do contrato v1. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:40-44, 51-52`.

9. **Resolvido — Cronograma e prioridade do congelamento.** O obrigatório tem prazo e reserva de red-team; A e B só entram depois do commit obrigatório e podem ir para a fase 2. A implementação C# segue explicitamente fora do cronograma do ML. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:178-196`.

## Achados novos

10. **ALTA — As opções dos blocos não correspondem às opções aprováveis da r3.** O plano apresenta A = política de proximidade, B = pontuação de rota e C = T-A; suas opções incluem “A” e “A+B”. A r3 §4 descreve como opcionais T-A e um protótipo de rota, e §6 oferece “nenhuma”, “só T-A” ou “T-A + protótipo de rota”. A política A e esse menu não aparecem ali. Isso pode fazer a decisão 2 aprovar um escopo diferente do previsto na proposta. **Correção:** alinhar os blocos e as opções à r3, ou registrar a política como aditivo independente e obter decisão explícita sobre ela. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:19-22, 63-65, 94-96, 215-219`; `docs/PROPOSTA-V3-ALERTA-ROTAS-r3.md:137-144, 153-157`.

11. **ALTA — “Totalmente especificada” e reproduzível entre linguagens ainda não são garantidos.** O plano fixa raio e interpolação linear em lat/lon, mas não fixa a versão do core H3, a normalização de longitude, o tratamento numérico perto de bordas, nem as convenções completas de arredondamento e empate do ranking. Vinte pares lat/lon→célula não garantem concordância em pontos próximos a fronteiras; diferenças de implementação podem trocar a célula e alterar metros e pontuação. **Correção:** fixar versões H3 e especificações numéricas, definir normalização e regras de arredondamento/desempate, e incluir vetores de fronteira e casos de empate em Python e C#. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:98-110, 123-145`.

12. **ALTA — A aproximação de ponto médio não garante a antecedência descrita.** O texto associa a aresta média de ~201 m à “antecedência limitada a cerca de uma célula”, mas o gatilho é qualquer célula de `grid_disk(c, 1)` e não depende da distância do usuário à célula elegível nem da direção do deslocamento. O valor da aresta média, sozinho, não determina a distância entre quaisquer pontos dessas células. A regra de proximidade está definida; essa alegação de antecedência, porém, não decorre dela. **Correção:** manter o nome “proximidade” e retirar a afirmação de antecedência/distância, ou definir e avaliar uma medida de distância ao alvo. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:65, 71`.

13. **MÉDIA — A regra de L não define o denominador nem o caso sem limiar elegível.** “Fração de chaves `com_dado` elegíveis no snapshot” não esclarece se a fração divide por todas as chaves do snapshot ou apenas pelas chaves `com_dado`. Também não diz o que fazer se nenhum nível 0–3 resultar em fração ≤10%. Isso pode levar duas implementações a escolherem limiares diferentes ou não ter limiar. **Correção:** especificar numerador, denominador e comportamento se nenhum nível atender ao corte. Evidência: `docs/PLANO-EXECUCAO-V3-r1.md:75-80`.

## Veredito

**Não recomendo congelar o plano r1 como especificação de execução dos blocos A e B ainda.** A revisão resolveu a maior parte dos nove achados anteriores, mas há divergência entre as opções da r3 e as do plano, e a discretização ainda não fixa o suficiente para exigir resultados idênticos em Python e C#. O obrigatório documental da seção 9 está separado desses blocos opcionais; os pontos acima precisam ser ajustados antes de aprovar ou implementar A/B.