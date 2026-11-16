# Revisão de código — hoodi ML, 2026-11-16

**Alvo:** branch `v2-historico`, a partir de `cf1e345`. Fica fora o branch `feat/industrialize-hoodi-ml`, que não faz parte da entrega.
**Plano seguido:** segurança, qualidade, vazamento temporal, contrato dos derivados, reprodutibilidade, métricas e calibração, documentação.
**Execução:** todas as verificações abaixo rodaram de fato. Os comandos estão listados no fim do documento.

## Resumo
- **Bloqueantes de aceite:** 1, a Ficha CitizenTech/ODS ainda sem conteúdo oficial.
- **Severidade ALTA:** 0 no working tree após a decisão A de 2026-11-16; o saneamento da ancestralidade permanece como gate antes do push.
- **Severidade MÉDIA:** 0 após as correções da rodada 2.
- **Severidade BAIXA:** 5 achados históricos; o erro de interpretação do estrato da rodada 2 foi corrigido.
- **Testes:** 84 → 100, todos passando após o contrato v2 e as correções do red-team de entrega.

## Achados

| # | Sev. | Área | Achado | Disposição |
|---|---|---|---|---|
| 1 | ALTA | Privacidade | 218 das 1.172 chaves originalmente com dado tinham 1–2 registros. Com a faixa e a rubrica pública, uma chave assim apontava para poucas ocorrências reais. | **Corrigido por decisão humana A:** contrato v2 publica essas chaves como `sem_dado`, contagem 0 e pontuação/nível vazios; os testes exigem k ≥ 3 em toda linha `com_dado`. |
| 2 | MÉDIA | Contrato | `fixture_v1.json` cobria só os valores {nível 3, sem_dado}. Os níveis 0–2 não apareciam. | **Corrigido:** `fixture_v2.json` traz um exemplo real de cada nível 0–3 e `sem_dado`; o teste exige o conjunto completo. |
| 3 | MÉDIA | Modelo | Na faixa noite cedo (18–21h), o RF regularizado tem F1 0,40, abaixo da persistência (0,50). | **Documentado** em `RELATORIO_ML.md` §6. Corrigir isso com o mesmo teste exigiria ajustar sobre um dado já visto. |
| 4 | MÉDIA | Avaliação | O RF regularizado, a calibração e os estratos foram feitos com `test_seen=true`. | **Declarado** no relatório e marcado nos JSON. O teste cego será com out–nov/2026. |
| 5 | BAIXA | Portabilidade | Os scripts `00_*.py` tinham o caminho `~/Downloads` fixo no código. | **Corrigido:** agora usam `HOODI_XLSX_DIR`, com padrão `~/Downloads`. |
| 6 | BAIXA | Qualidade | ruff F401 apontou imports não usados em 6 arquivos. | **Corrigido** com `ruff --fix`. |
| 7 | BAIXA | Qualidade | ruff F841: a variável `pc` em `ml/rota.py:249` não é usada. | **Mantido.** Está num trecho coberto pelos vetores-ouro, e não vale mexer às vésperas da entrega. |
| 8 | BAIXA | Tipagem | mypy acusa 5 erros: anotações `var-annotated` em `rota.py` e `politica_proximidade.py`, e `list.__setitem__` em `rota.py:143`. | **Mantido.** São só anotações, sem efeito em tempo de execução. |
| 9 | BAIXA | Estilo | Com a configuração completa, o ruff acha 186 problemas, quase todos de ordem de import (I001). | **Não aplicado.** Reformatar mexeria em 38 arquivos e não muda o comportamento. |

### Sem achado (verificado)
- **Segredos:**
  - gitleaks: 0 vazamentos na árvore de trabalho e em todo o histórico de todos os branches.
  - detect-secrets: só falsos positivos. São hashes sha256 e PNG em base64; a "AWS key" no notebook cai dentro de uma imagem.
  - Busca manual: os 2 acertos são a regra anti-segredo do `ci.yml`, no branch fora da entrega.
  - As saídas do notebook não têm caminho, BO, latitude/longitude nem segredo.
- **Dependências:** pip-audit não acha vulnerabilidade conhecida.
- **SAST:** bandit acha só itens Low, que são `assert` em teste e `subprocess` git com argumentos fixos. Os dois B608 são falso positivo, porque o SQL é montado só com constantes.
- **Vazamento temporal:**
  - `test_split_temporal`: as features vêm antes do rótulo, há invariância ao futuro, há expurgo e os cortes por dobra estão certos.
  - `test_cortes_treino`: os cortes são calculados só no treino.
  - `test_sequenciais`: o KMeans é ajustado só no treino.
  - O MLP usa `StandardScaler` dentro do pipeline.
- **Reprodutibilidade:** o snapshot v2 gerado de novo tem o mesmo sha256 do CSV (`2dddef701bde…`).
- **Ruff B023** em `achados_revisao.py`: não é bug, porque o lambda é chamado na mesma iteração.

## Métricas e testes novos
- **`tests/test_schemas_derivados.py`** (8 testes) cobre o contrato do snapshot:
  - linha a linha: H3 r9 válido, faixa, coerência de `sem_dado` e nível conforme os cortes;
  - unicidade das chaves e contagens contra o manifest;
  - perímetro;
  - amarração do sha256 entre CSV, manifest, política e vetores;
  - fixture como subconjunto exato;
  - política coerente com o manifest;
  - ausência de "tempo real", "rota segura" e "local seguro", salvo em negação.
- **`ml/calibracao.py`** e `tests/test_calibracao.py` (6 testes):
  - Brier, log-loss, ECE e curva de confiabilidade;
  - isotônica ajustada só com previsões fora da dobra da CV;
  - estratos por faixa e por quantidade de registros;
  - backtest agregado por modelo (`backtest_ago_set.csv`, T028), sem identificadores de chave.
  - Resultado: ECE de 0,047 sem calibração. **A isotônica piora para 0,105 e foi rejeitada.**
- **Cobertura:** 76 % no total após a rodada 1. Nos módulos de contrato fica entre 82 % e 100 %:

  | Módulo | Cobertura |
  |---|---|
  | rota | 92 % |
  | politica | 92 % |
  | rotulo | 93 % |
| snapshot | 100 % |
  | features | 82 % |
  | ingestao | 83 % |
  | sequenciais | 100 % |

  Os scripts exploratórios ficam entre 0 % e 32 %.

## Correção de um número dito antes
Na revisão anterior, eu disse que 251 chaves do teste tinham um único registro. O número correto, conforme `calibracao.json`, é **47 chaves com 1 registro** na janela de features. Outras 151 chaves têm de 2 a 4 registros.

## Comandos executados
```
gitleaks detect --source . --log-opts="--all"; gitleaks detect --no-git --source .
uvx detect-secrets scan; uvx pip-audit -r requirements.txt; uvx bandit -r ml scripts
ruff check --select F401,F841 --fix; ruff check --select ALL --statistics; uvx mypy ml
coverage run -m pytest && coverage report
python -m ml.gerar_snapshot  (sha256 comparado; manifest revertido)
python -m ml.calibracao
pytest -q
```

## Red-team da entrega — rodada 1 e disposição

Relatório: `docs/REDTEAM-ENTREGA-rodada1.md`.

| # | Sev. | Disposição após a rodada 1 | Evidência |
|---|---|---|---|
| 1 | BLOQUEANTE | **Pendente de dado oficial do Nando.** Não foram encontrados equipe/RMs nem ODS confirmados nos arquivos do projeto. | `README.md` mantém os campos marcados; não foram inventados. |
| 2 | ALTA | **Corrigido no HEAD após a rodada 2.** O backtest agora contém apenas métricas agregadas por modelo, sem associação com H3 × faixa. **Pendente no histórico local:** `df5b431` preserva a versão detalhada e não pode ser publicado antes de decisão humana sobre saneamento. | `backtest_ago_set.csv`; dois testes de regressão em `test_calibracao.py`. |
| 3 | ALTA | **Corrigido e reproduzido.** Os scripts criam `interim/`, executam `INSTALL excel` e `LOAD excel`. A conversão rodou numa pasta temporária vazia: 555.404 + 259.496 linhas. | `scripts/00*.py`; execução limpa em 2026-11-16. |
| 4 | MÉDIA | **Corrigido.** Calibração, acerto por tolerância e estratos entraram no gerador; o notebook foi regenerado e executado. | seção 8 do notebook, célula executada com quatro saídas. |
| 5 | MÉDIA | **Corrigido.** Removidas causalidade, “teto” e equivalência não testada. | `README.md`, `RELATORIO_ML.md`. |
| 6 | MÉDIA | **Corrigido.** Fixture cobre 0–3 e `sem_dado`. | `fixture_v1.json`, `test_schemas_derivados.py`. |
| 7 | MÉDIA | **Corrigido.** Inventário por camada documenta conteúdo, acesso, retenção e descarte, sempre dependente de confirmação humana. | `ml/dados/README.md`. |

Após as correções da rodada 1: notebook executado, snapshot com o mesmo SHA-256, fixture revisada e 98 testes passando.

## Red-team da entrega — rodada 2

A rodada 2 reproduziu uma inferência ainda possível em 33 chaves do HEAD anterior e confirmou separadamente o risco k < 3 do snapshot. A correção técnica foi elevar o backtest a métricas agregadas sem H3/faixa/rótulo/contagem. Também foram corrigidos o inventário de logs, o resumo contraditório e a interpretação dos estratos. O relatório integral fica em `docs/REDTEAM-ENTREGA-rodada2.md`. Após essas correções, são **99 testes passando**.

## Red-team da entrega — rodada 3

A rodada final confirmou **0 bloqueantes técnicos e 0 altas técnicas corrigíveis** no HEAD. O único achado técnico, de gravidade baixa, era a ausência de asserções de cardinalidade e unicidade no teste do backtest agregado; ele foi corrigido e a suíte completa passou novamente com **99 testes**.

Permanecem três gates que exigem decisão ou informação humana e impedem publicação/aceite final:

1. o commit local `df5b431` ainda contém a versão detalhada do backtest e não deve entrar em histórico publicado sem saneamento;
2. o snapshot contém 218 chaves com `k < 3`, exigindo aceitação formal de distribuição restrita ou alteração versionada do contrato;
3. a Ficha CitizenTech/ODS da rubrica A4 continua sem os dados oficiais.

Relatório integral: `docs/REDTEAM-ENTREGA-rodada3.md`.

## Decisão A — supressão e saneamento

Em 2026-11-16, o Nando escolheu explicitamente a opção A. O snapshot foi versionado como contrato v2 e aplica k ≥ 3 por chave H3 × faixa: as 218 chaves com 1–2 registros são indistinguíveis de ausência no arquivo entregue. O manifesto conserva somente os totais agregados da supressão (218 chaves, 306 registros).

O snapshot, a fixture, a política de proximidade e os vetores de rota foram regenerados e amarrados ao novo hash `2dddef701bdecb65142874980f1ae5aba7b2ac6ab2abad5c47b07f07ecc5080a`. A suíte completa passou com 100 testes. O histórico local da revisão será reescrito antes de qualquer push para que o backtest detalhado não pertença à ancestralidade publicável.

Com isso, os dois gates de privacidade da rodada 3 ficam resolvidos. Permanece apenas o bloqueante documental A4: Ficha CitizenTech/ODS oficiais.

## Red-team da entrega — rodada 4 e saneamento

A rodada 4 (Codex CLI, somente leitura) confirmou os três achados corrigidos, nenhum vazamento dos 218 pares suprimidos nos artefatos v2 e hashes consistentes; **nenhum achado alto ou bloqueante**. Relatório: `docs/REDTEAM-ENTREGA-rodada4.md`. Os 73 testes sem `torch` passaram no mesmo HEAD; os 27 restantes não puderam rodar por falta de memória na máquina nesta sessão (última execução completa: 100/100, mais cedo no mesmo dia).

O histórico local foi saneado: os commits `df5b431`…`b78777a` foram reescritos como `4a5098b`…`c2b187e`, sem o backtest detalhado (tabela em `docs/DECISAO-PRIVACIDADE-SNAPSHOT-V2.md`). O gate 1 (histórico da revisão) e o gate 2 (k < 3 na árvore entregue) ficam resolvidos. Permanecem abertos: o bloqueante documental A4 (Ficha CitizenTech/ODS) e a decisão sobre o snapshot v1 presente na ancestralidade compartilhada com `main` e `feat/industrialize`.
