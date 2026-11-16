<!-- Saída integral do Codex CLI (codex exec --sandbox read-only --ephemeral), 15/11/2026, sobre PROPOSTA-V3-ALERTA-ROTAS-r3.md. Os dois ajustes (MÉDIA e BAIXA) foram aplicados à r3 depois desta rodada. -->

## 1. Status dos achados da rodada 3

- **U1 — RESOLVIDO:** a r3 o chama explicitamente de filtro de registro anterior, limita as conclusões ao universo e não afirma que mede cobertura.
- **RF — PARCIAL:** o plano define retreino walk-forward e cálculo das transformações só com o passado. Porém, os hiperparâmetros foram escolhidos depois de ver ago–set/2026; o rótulo “exploratório” é necessário, e o resultado não serve como confirmação independente.
- **λ — RESOLVIDO:** critério, origens de seleção, desempate e congelamento antes das origens reportadas estão definidos.
- **Protótipo de rota — RESOLVIDO:** a r3 o rotula como pontuação observada retrospectiva e retira “total esperado” e “previsão” da saída do protótipo.

## 2. Novos achados na r3

- **[MÉDIA] RF continua sujeito a seleção retrospectiva de hiperparâmetros.** `REGULARIZADO` existe em [incerteza_custo.py](ml/incerteza_custo.py:30), com os quatro valores citados. A ressalva da r3 reconhece que foi escolhido após ver ago–set/2026. **Correção:** manter o RF explicitamente exploratório e não usar seu desempenho para alegar superioridade; para confirmação, congelar hiperparâmetros antes de um período futuro não visto.
- **[BAIXA] “sem_dado” pode confundir dois estados.** Na proposta, `sem_registro_anterior` significa chave fora de U1; no código do snapshot v1, `sem_dado` significa ausência de registros no próprio snapshot jan–set/2026. O §4 usa `% sem_dado` para o protótipo, mas não explicita essa distinção. **Correção:** escrever “% sem dado no snapshot v1 (jan–set/2026)” e distingui-lo de `sem_registro_anterior`.
- **Janelas e passado — conferido:** `usadas_v2.parquet` contém meses absolutos de **1 a 45**, sem lacunas. A primeira origem de seleção, mar–abr/2024 (15–16), tem os meses 3–14 como passado; a primeira reportada, jan–fev/2025 (25–26), tem 13–24. A última reportada, jul–ago/2026 (43–44), tem 31–42. Todas têm 12 meses disponíveis.
- **Consistência dos §§0/4/6 — sem contradição material:** o §0 descreve a situação atual; o §4 propõe, como opcional, um protótipo retrospectivo; o §6 oferece essa opção. A distinção entre o futuro “total esperado” da comparação de rotas (§2.3) e a pontuação observada do protótipo (§4) é compatível, mas convém preservar os rótulos para não misturar os conceitos.

## 3. Veredito

**Não sobra BLOQUEANTE nem ALTA para apresentar a r3 como plano de reestruturação; sim, pode ser apresentada, mantendo explícito que o RF e os resultados novos são exploratórios.**