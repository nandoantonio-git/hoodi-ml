# Red-team real (Codex CLI) — entrega, rodada 1

Executado em 2026-11-16 sobre o commit `df5b431`, com foco no diff `cf1e345..df5b431`, em modo `read-only` e `--ephemeral`. A saída abaixo preserva o parecer do Codex CLI; a disposição dos achados está em `REVISAO-CODIGO-2026-11-16.md`.

## Parecer

**Não aprovar o HEAD `df5b431` como entrega final. Restam 1 BLOQUEANTE de aceite e 2 achados de severidade ALTA.** A calibração e o snapshot são numericamente reproduzíveis, mas o novo backtest amplia a exposição de dados, a reprodução em checkout limpo está incompleta e a rubrica A4 não foi cumprida.

## Achados

### 1. BLOQUEANTE — Ficha CitizenTech e ODS ausentes; A4 não cumprida

Local: `README.md:7`.

- Evidência: equipe/RMs, desafio, público-alvo, ODS e justificativa permanecem como `[PREENCHER]`.
- Impacto: impede considerar a entrega completa segundo a rubrica.
- Correção mínima: preencher os campos com informações oficiais e registrar a conferência humana de A4.

### 2. ALTA — O novo backtest permite recuperar contagens em uma janela menor

Locais: `ml/calibracao.py:147`, `ml/dados/resultados/backtest_ago_set.csv:1`, `ml/dados/README.md:33`.

- Evidência: o CSV publicava H3, faixa e contagem exata de jan–jul; o snapshot publica a contagem de jan–set. A subtração recupera `n_ago_set`. Nas 847 chaves, havia 225 com exatamente uma ocorrência em ago–set e 144 com duas.
- Impacto: estreita a janela temporal para possível vinculação com registros públicos. Não estar no nível 3 não elimina o risco.
- Correção mínima: retirar a contagem exata de features do backtest distribuído e revisar conjuntamente as publicações por chave. Para células pequenas do snapshot, aplicar agregação/supressão coerente e testar ataques por diferença.

### 3. ALTA — A receita de reprodução falha em checkout limpo

Locais: `README.md:38`, `scripts/00_xlsx_para_parquet.py:20`, `scripts/00b_historico_xlsx_para_parquet.py:36`.

- Evidência: `ml/dados/interim/` não é versionado e os conversores não criavam a pasta. Também executavam `LOAD excel` sem preparar a extensão numa instalação nova.
- Impacto: a sequência publicada dependia de estado local anterior.
- Correção mínima: criar a saída, preparar explicitamente a extensão Excel e validar a sequência em pasta e ambiente novos.

### 4. MÉDIA — Notebook não contém as novas evidências de calibração e backtest

- Evidência: o notebook versionado não lia `calibracao.json` nem `backtest_ago_set.csv`.
- Correção mínima: incluir calibração, estratos e acerto por tolerância no gerador; regenerar e executar o notebook.

### 5. MÉDIA — O relatório transforma diagnósticos em conclusões não demonstradas

- Evidência: “ganha porque usa as células vizinhas” atribui causalidade sem ablação; “o teto vem do dado” contradiz o notebook; “empate” não é demonstrado por um intervalo de diferença que contém zero.
- Correção mínima: usar “hipótese a investigar”, “referência de repetibilidade” e “diferença não estabelecida”.

### 6. MÉDIA — A fixture não exercita os níveis 0–2

- Evidência: continha somente nível 3 e `sem_dado`; o teste aceitava até uma fixture só com `sem_dado`.
- Correção mínima: acrescentar exemplos reais de 0–3 e `sem_dado` e exigir a cobertura no teste.

### 7. MÉDIA — Inventário de privacidade não define acesso, retenção e descarte

- Evidência: a documentação enumerava campos e exclusões do Git, mas não acesso, retenção e descarte por camada.
- Correção mínima: completar o inventário e distinguir agregados publicados de registros locais.

## Verificações reproduzidas pelo revisor

- Snapshot reconstruído em memória: SHA-256 `e721974f1966fb901144ee33036eb07a4640544203f72db83e0666719191152e`.
- RF regularizado: macro-F1 `0.5129095761`, Brier `0.5909493224`, log-loss `1.0440637242`, ECE `0.0466497469`.
- Isotônica com 1.616 exemplos: ECE `0.1047718659`.
- Rótulos, previsões e probabilidades do backtest conferem com a recomputação; diferenças só no arredondamento de seis casas.
- Não foi encontrado vazamento direto do alvo de teste no ajuste da calibração.
- Contratos novos passaram nas verificações de CSV, manifest, hashes, política e fixture, mas isso não certifica as implementações .NET/Expo.
- Gitleaks no diff não encontrou vazamentos.
- O ambiente read-only permitiu 90 testes; seis foram deselecionados por gravarem arquivos e um falhou ao tentar criar cache temporário do PyTorch. O revisor classificou a falha como ambiental.

## Rubrica no parecer da rodada 1

| Critério | Parecer |
|---|---|
| A1 | Repositório e notebook presentes; notebook documental não reexecuta todo o pipeline. |
| A2 | Arquivos e checksum presentes; reprodução inicial incompleta pelo achado 3. |
| A3 | Parcial: métricas conferem, mas faltavam no notebook. |
| A4 | **Não cumprido; bloqueante.** |
| A5 | Registro de prompts presente. |
| A6 | Esta revisão precisava ser integrada e fechada. |

**Conclusão da rodada 1:** 1 BLOQUEANTE, 2 ALTAS e 4 MÉDIAS.
