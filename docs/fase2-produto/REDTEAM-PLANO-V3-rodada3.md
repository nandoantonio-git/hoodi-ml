<!-- Saída integral do Codex CLI (codex exec --sandbox read-only --ephemeral), 15/11/2026, sobre docs/PLANO-EXECUCAO-V3-r2.md -->
## Achados 10–13

1. **Achado 10 — Resolvido.** O plano mantém as opções da proposta para C e B, e separa A como aditivo com decisão própria do Nando. Evidência: `docs/PLANO-EXECUCAO-V3-r2.md:19-24, 249-254`.

2. **Achado 11 — Parcial.** A especificação agora fixa versão do H3, coordenadas, aritmética, comparação, arredondamento e vetores de fronteira. Mas a concordância entre Python e C# ainda depende de implementação e aceite externos; o plano não demonstra que os vetores passaram nos dois lados. Evidência: `docs/PLANO-EXECUCAO-V3-r2.md:125-144, 176-181`; integração C# listada como externa em `:60-67`.

3. **Achado 12 — Resolvido.** O alerta é chamado de proximidade, e o plano declara que não garante distância nem antecedência mínima. Evidência: `docs/PLANO-EXECUCAO-V3-r2.md:71-74`.

4. **Achado 13 — Resolvido.** O denominador é explicitamente o total de chaves `com_dado` (1.172). A meta de ≤10% foi retirada; `L=3` fica como padrão exploratório, com fração de 17,1% das chaves e 56,5% da pontuação mensal. Evidência: `docs/PLANO-EXECUCAO-V3-r2.md:83-96`. Recalculei os valores no CSV; a tabela confere: `L=1`: 682 chaves, 58,2%, 93,3%; `L=2`: 475, 40,5%, 84,0%; `L=3`: 200, 17,1%, 56,5%.

## Novos achados BLOQUEANTES ou ALTOS

Não encontrei novos problemas dessa severidade no escopo revisado.

## Veredito

A r2 resolve 10, 12 e 13; o achado 11 fica **parcial** até haver evidência de concordância entre as implementações Python e C#. O plano é coerente como roteiro de demonstrações retrospectivas e não validadas, mas não comprova integração nem validação de produto — limitações que ele próprio registra (`docs/PLANO-EXECUCAO-V3-r2.md:3, 57-67`).