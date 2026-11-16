# Red-team real (Codex CLI) — entrega, rodada 2

Executado em 2026-11-16 sobre o commit `389aa61`, em modo `read-only` e `--ephemeral`, para verificar as correções da rodada 1. A disposição e as correções subsequentes estão em `REVISAO-CODIGO-2026-11-16.md`.

## Parecer

**Não aprovar `389aa61` como entrega final. Restam 1 BLOQUEANTE e 2 ALTAS**, contando separadamente o risco residual do snapshot. Também foram identificadas 2 MÉDIAS e 1 BAIXA.

## Achados

1. **BLOQUEANTE — Ficha CitizenTech e ODS ausentes.** `README.md` ainda contém `[PREENCHER]`; A4 depende dos dados oficiais e de revisão humana.
2. **ALTA — Remover a coluna não encerrou a recuperação de contagens temporais.** O backtest só incluía chaves presentes nas janelas de features e de rótulo. Havia 33 chaves do backtest com total 2 no snapshot; logo, necessariamente uma ocorrência em cada janela. O histórico Git local também preserva em `df5b431` a coluna retirada, permitindo reproduzir 225 chaves com 1 e 144 com 2 ocorrências em ago–set. Correção mínima: distribuir somente métricas agregadas sem associação com H3 × faixa e decidir humanamente sobre o histórico.
3. **ALTA — Snapshot mantém risco residual k < 3.** Foram confirmadas 130 chaves com 1 registro e 88 com 2. Nenhuma está no nível 3, mas isso não elimina a exposição. Correção exige decisão explícita: aceitar distribuição restrita ou versionar contrato com agregação/supressão.
4. **MÉDIA — Inventário não cobria logs.** Faltavam conteúdo permitido, localização, acesso, retenção e descarte para saídas persistidas.
5. **MÉDIA — Resumo contraditório.** `REVISAO-CODIGO-2026-11-16.md` dizia “Bloqueantes: nenhum”, mas a tabela registrava A4 como bloqueante.
6. **BAIXA — Interpretação incorreta dos estratos.** O texto chamava 18–21h de pior F1 (0,404), mas 21–24h tem F1 menor (0,390). 18–21h tem, na verdade, a maior desvantagem observada frente à persistência.

## Correções confirmadas pela rodada 2

- Conversores criam `interim/` e executam `INSTALL excel` antes de `LOAD excel`.
- Notebook tem 27 células de código executadas em sequência, sem erro, e quatro saídas novas para calibração, tolerância e estratos.
- Acerto exato/tolerância conferem: RF 52,3%/88,7%; persistência 50,2%/87,5%.
- As afirmações centrais de causalidade, teto e empate foram corrigidas.
- Fixture cobre exatamente níveis 0–3 e `sem_dado`, com correspondência real ao snapshot.
- CSV, `.sha256` e `manifest.csv_sha256` conferem: `e721974f1966fb901144ee33036eb07a4640544203f72db83e0666719191152e`.

## A1–A6

| Critério | Parecer da rodada 2 |
|---|---|
| A1 | Atendido quanto ao repositório e notebook com saídas. |
| A2 | Arquivos e checksum conferem; correções dos conversores confirmadas conceitualmente. |
| A3 | Métricas rastreáveis; havia uma interpretação incorreta de estrato. |
| A4 | **Não atendido — bloqueante humano.** |
| A5 | Registro datado presente. |
| A6 | Rodada 1 anexada; rodada 2 ainda precisava ser incorporada. |

**Conclusão da rodada 2:** 1 BLOQUEANTE, 2 ALTAS, 2 MÉDIAS e 1 BAIXA.
