<!-- Saída integral do Codex CLI (codex exec --sandbox read-only --ephemeral), 15/11/2026, sobre PROPOSTA-V3-ALERTA-ROTAS-r1.md. -->

## 1. Situação dos 17 achados da rodada 1

1. **RESOLVIDO** — §0 delimita que a solução atual não implementa nem valida alerta ou escolha de rota, sem negar que o mapa histórico possa servir de insumo.
2. **RESOLVIDO** — Separa a v1 pré-registrada da v2 exploratória e identifica que o período de teste já foi visto.
3. **RESOLVIDO** — Classifica resultados novos em jan–set/2026 como exploratórios e reserva out–nov para um teste futuro pré-registrado.
4. **PARCIAL** — O painel distingue zero observado, sem dado e fora de cobertura, mas considera coberta uma célula com qualquer registro em qualquer janela anterior; isso não comprova cobertura da faixa horária ou da janela avaliadas.
5. **RESOLVIDO** — Separa ranking espacial de política de alerta e limita a conclusão sem trajetos de caminhada.
6. **PARCIAL** — Define uma métrica primária, linhas de base e bootstrap em blocos, mas ainda não especifica completamente o cálculo do hit rate ponderado nem como serão tratados empates e dependência entre origens.
7. **RESOLVIDO** — Fixa total esperado no trajeto como métrica primária, limita a comparação ao mesmo par origem–destino e deixa ocorrências/km como sensibilidade.
8. **RESOLVIDO** — Nomeia o evento como ocorrências registradas em via pública e adia a validação de um índice específico para motoristas.
9. **RESOLVIDO** — Declara viés de exposição e subnotificação e veda linguagem de risco pessoal ou “rota segura”.
10. **PARCIAL** — Substitui sobreposição de intervalos por bootstrap conjunto e limiar de abstenção, mas não define a distribuição preditiva necessária para interpretar P(rota escolhida é a de menor total).
11. **PARCIAL** — Adia modelos novos e limita a suavização a baseline com peso escolhido em validação temporal, mas a atribuição de zeros continua dependente do critério de cobertura questionável do §2.1.
12. **RESOLVIDO** — Adia uma avaliação real de rotas para a fase 2; especifica rede congelada e geometria de via como requisitos e rotula a demonstração da fase 1 como não validada.
13. **RESOLVIDO** — Corta reextração, OSM e modelos novos da fase 1, mantendo a v1 congelada e uma seção documental no notebook.
14. **RESOLVIDO** — Define linguagem retrospectiva com janela e cobertura, evita rótulos de bairros e prevê abstenção.
15. **RESOLVIDO** — Os números de distribuição por chave e por célula de §1 conferem com `usadas_v2.parquet`.
16. **PARCIAL** — A r1 explica que 34.771 e 34.769 usam filtros diferentes e que a diferença não altera a modelagem, mas não reconcilia as duas linhas.
17. **RESOLVIDO** — O JSON e o script fornecem uma trilha reproduzível para as contagens de local e conduta, com hashes das fontes.

## 2. Novos achados na r1

1. **[BLOQUEANTE] A definição de “coberta” pode tratar falta de observação como zero avaliável.**  
   **Evidência:** [PROPOSTA-V3-ALERTA-ROTAS-r1.md](docs/PROPOSTA-V3-ALERTA-ROTAS-r1.md:39), linhas 40–44: basta haver registro em qualquer janela anterior para a célula contar como coberta; depois, uma chave sem registro pontuável no alvo vira `zero_observado`. Um registro numa faixa horária não demonstra cobertura de todas as cinco faixas, nem que a coleta detectaria ocorrências nas chaves sem registros.  
   **Correção:** definir cobertura na granularidade célula × faixa × janela, com evidência de que a fonte coletava nessa unidade; separar indisponibilidade de zero observado e testar a sensibilidade das métricas aos zeros assumidos.

2. **[ALTA] A métrica primária de T-A não está especificada o bastante para reprodução.**  
   **Evidência:** r1, linhas 48–55. “% da pontuação futura capturada” não fixa a transformação exata da contagem ponderada, o mapeamento da saída do RF — que é um classificador de níveis — para pontuação, regra de desempate no corte de 10% ou denominador quando há pontuação zero. “Correção de Holm explícita” também não identifica a família de testes.  
   **Correção:** registrar fórmula e pesos exatos, converter previsões em escore de ranking, fixar desempate e denominador, e listar quais métricas e comparações entram na correção de multiplicidade.

3. **[ALTA] O bootstrap de T-A pode não ter origens independentes suficientes.**  
   **Evidência:** r1, linha 55, especifica blocos espaciais res. 7 × origens temporais, mas não define quantas origens serão avaliadas, o tratamento das bordas dos blocos, nem a unidade pareada para cada diferença. O artefato v2 informa somente nove blocos res. 7 em uma análise; essa quantidade pequena pede justificativa para inferência.  
   **Correção:** pré-fixar o desenho temporal, os blocos, o número mínimo de unidades independentes e o cálculo do intervalo pareado; se não houver origens suficientes, reportar resultado descritivo e evitar conclusão inferencial.

4. **[ALTA] P ≥ 0,8 em T-B não tem interpretação operacional definida.**  
   **Evidência:** r1, linha 63. A proposta diz que haverá bootstrap conjunto das rotas, mas não esclarece se ele reamostra incerteza preditiva disponível antes da viagem ou resultados observados em retrospecto. Bootstrap de totais realizados não fornece, por si só, a probabilidade de uma rota ser a menor antes da decisão.  
   **Correção:** especificar a distribuição preditiva conjunta das rotas no momento da escolha, como será validada sua calibração e como dependência e cobertura das células entram na probabilidade. Até então, manter o limiar como requisito futuro, não como regra validada.

5. **[ALTA] A fase 1 não entrega uma decisão funcional de alerta ou rota.**  
   **Evidência:** r1, linhas 87–99. O núcleo da fase 1 é preservar a v1 e documentar a lacuna na seção 9; T-A e T-B são opcionais, e T-B é uma demonstração não validada. Assim, a proposta trata da documentação e do plano futuro, mas não atende à intenção de alertar antes da entrada nem de escolher entre rotas.  
   **Correção:** declarar explicitamente que a entrega de novembro é documental e acadêmica, e que as duas decisões de produto ficam fora dela; não apresentar a fase 1 como implementação ou validação do produto.

6. **[MÉDIA] “Cabe no prazo” não está apoiado por decomposição de trabalho.**  
   **Evidência:** r1, linha 87, afirma que cabe até 19/11; linhas 89–95 ainda incluem seção nova no notebook gerado, possível experimento T-A/T-B em MLflow e uma rodada real de red-team até não haver achados altos. O prazo de congelamento é 16/11.  
   **Correção:** separar entregáveis obrigatórios dos opcionais e estimar a seção do notebook, geração/revisão e red-team; manter T-A/T-B fora do compromisso de prazo salvo se já estiverem executados.

## 3. Conferência dos números de §0 e §1

- **§0:** os valores da v1 conferem: RF macro-F1 = 0,46687 (arredondado para 0,467) e persistência = 0,49136 (0,491), com 847 chaves. A v2 também confere: RF regularizado = 0,51729 e persistência = 0,48518; o IC95% da diferença de macro-F1 é [0,00670; 0,05619], acima de zero. Esses números estão em `incerteza_custo.json` e `v2_historico.json`.
- **§1, conduta/local:** os totais e as contagens citados conferem com `conduta_local_2026.json`; as proporções arredondadas também: 89%, 44%, 5,0%, 89%, 46% e 6,8%. O código em `scripts/medir_conduta_2026.py` usa as colunas de conduta/subtipo, filtra os universos descritos e registra hashes dos dois arquivos interim. Não executei o script.
- **§1, contagens espaciais:** `usadas_v2.parquet` confirma 883 chaves em ago–set, mediana 3, p90 12; e 258 células em jan–set, mediana 48,5.
- **Ressalva numérica:** a diferença de duas linhas entre 34.771 e os 34.769 registrados em `SPEC-ML.md` permanece sem reconciliação.

**Veredito:** Ainda não apresentaria a r1 ao dono como plano fechado de reestruturação; ela serve como proposta documental, mas cobertura, métrica de T-A e probabilidade de T-B precisam ser especificadas antes de se comprometer com a avaliação, e a fase 1 não implementa as decisões de produto.