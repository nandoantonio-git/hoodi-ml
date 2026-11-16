# Red-team real (Codex CLI) — implementação v3, rodada 2

Data: 15/11/2026. Comando: `codex exec --sandbox read-only --ephemeral`. Parecer abaixo sem edição.

## Achados

1. **BAIXA — coordenadas malformadas nem sempre viram `rota_invalida`.**  
   **Arquivo:** [ml/rota.py](ml/rota.py:45).  
   **Evidência:** `_validar` acessa `p[0]` e `p[1]` antes de validar a forma do ponto; pontos curtos podem gerar `IndexError`, e pontos com campos extras são aceitos. Isso diverge do contrato de pontos `(lat, lon)` e do erro `rota_invalida`.  
   **Correção:** exigir exatamente dois valores por ponto e converter erros de forma ou conversão em `RotaInvalida`.

2. **BAIXA — o teste de pentágono não exercita a implementação da suavização.**  
   **Arquivo:** [tests/test_ta_descritiva.py](tests/test_ta_descritiva.py:67).  
   **Evidência:** o perímetro não contém pentágonos; o teste simula manualmente o divisor, sem passar por `Base` ou `escores_base`. O código atual usa `n_viz` e trata posições inexistentes fora do divisor, mas o teste não detectaria uma regressão nessa lógica.  
   **Correção:** testar a suavização da implementação com uma vizinhança simulada que tenha cinco vizinhas, ou extrair a operação para uma função testável.

## Achados da rodada 1

1. **Ordenação não transitiva — resolvido.** Classes ancoradas no menor valor, documentadas no contrato e cobertas por teste de permutação.
2. **Divisor para pentágonos — resolvido no código.** A implementação divide por vizinhas existentes. O teste ainda tem a limitação descrita no achado 2 acima.
3. **Limite de dado insuficiente no notebook — resolvido.** Texto e tabela mostram que `sem_dado` e fora da cobertura são somados.
4. **Decisões abertas versus aprovadas — resolvido.** `docs/DECISOES-V3.md` registra a resposta literal e a interpretação; o plano r2 permanece preservado.
5. **Nome do experimento MLflow — resolvido.** A escolha do nome numerado está registrada, e `experimento_logico=hoodi-v3-exploratorio` preserva o vínculo com o nome lógico.
6. **Garantias temporais da T-A — resolvido.** Os testes recalculam λ, comparam escores usando dados cortados em jan–fev/2025 e ago–set/2026, e comparam o RF com dados completos e cortados.

## Verificações e veredito

Os hashes dos contratos JSON conferem com os arquivos `.sha256`. O diff e o status indicam que o notebook e os scripts foram alterados e que contratos, código, resultados e testes novos estão **untracked**; `git diff` não os inclui, então foram lidos diretamente. Não encontrei outra inconsistência material no código, contratos ou seções 9–11 do notebook.

A revisão foi somente leitura; não executei a suíte de testes. As conclusões sobre os testes são baseadas na inspeção do código.

**Contagem:** 0 BLOQUEANTES, 0 ALTAS, 0 MÉDIAS, 2 BAIXAS.  
**Veredito: pronto para commit**, com as duas melhorias baixas registradas acima.