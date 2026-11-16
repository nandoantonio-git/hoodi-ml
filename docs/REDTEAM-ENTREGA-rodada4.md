# Red-team da entrega — rodada 4

Data: 2026-11-16  
Revisor: Codex CLI real (`codex exec --sandbox read-only`), execução independente e somente leitura  
HEAD revisado: `b78777a` (reescrito depois para `c2b187e`, mesma árvore; ver `DECISAO-PRIVACIDADE-SNAPSHOT-V2.md`)  
Escopo: contrato v2 do snapshot (decisão A), correção dos três achados da revisão intermediária, vazamento dos 218 pares suprimidos, consistência de hashes.

## Parecer do revisor (transcrito)

## Parecer

No HEAD `b78777a32bac72e112b627e95d6b90c8759d1e9b`, os três achados estão corrigidos nos arquivos examinados e não encontrei vazamento dos 218 pares suprimidos nos derivados verificados. Hashes e fixture são consistentes; não encontrei consumidor ativo apontando para o CSV v1. A suíte solicitada **não chegou a executar os testes**: o pytest falhou ao criar um arquivo temporário no ambiente somente leitura.

## Verificações

| item | resultado | evidência resumida |
|---|---|---|
| (a) Spec ainda permitia 1–2 registros | Corrigido | `contracts/snapshot-risco.md` especifica `com_dado` com pelo menos 3 registros, `sem_dado` para 0–2, e que valores 1 e 2 nunca são publicados. `spec.md`, `data-model.md` e `ml/snapshot.py` também descrevem/aplicam k≥3. |
| (b) Mensagem “sem dado registrado” | Corrigido nos pontos encontrados | Busca em specs, código, scripts, notebook, contratos e documentos pedidos não encontrou essa mensagem. A política e o notebook usam “dados insuficientes para exibição”. |
| (c) Notebook com percentuais/contagens v1 | Corrigido no material de snapshot | O notebook versionado descreve o snapshot v2 e k≥3. Seus vetores referenciam o hash do CSV v2. |
| Pares com 1–2 registros no v1 | Conferidos | `git show 81b8d18:...v1.csv` contém 218 pares: 130 com contagem 1 e 88 com contagem 2, totalizando 306 registros. |
| CSV v2 e fixture | Sem vazamento observado | Os 218 pares estão no CSV v2 como `sem_dado`, `n_registros=0`, nível e pontuação vazios; zero divergências. A fixture tem 5 linhas e é subconjunto exato do CSV; não inclui nenhum dos pares suprimidos. |
| Política, vetores e notebook | Sem associação dos pares suprimidos observada | A verificação por chave/faixa não achou pares suprimidos na fixture, política ou notebook. Os vetores contêm algumas células H3 coincidentes, mas **nenhuma chave suprimida na respectiva faixa**. |
| Hashes | Consistentes | SHA-256 calculado do CSV v2: `2dddef701bdecb65142874980f1ae5aba7b2ac6ab2abad5c47b07f07ecc5080a`; encontrado no `.sha256`, manifesto, política e vetores. |
| Versões dos derivados | Consistente, com representação distinta nos vetores | Manifesto e fixture declaram `contrato_versao: 2`; política declara `contrato_snapshot_versao: 2`; vetores identificam `versao_vetores: 2` e fixam o hash do snapshot. |
| Referências a v1 | Sem consumidor ativo encontrado | `git grep` encontrou referências a `fixture_v1.json`/CSV v1 apenas em plano/diffs históricos. Código e documentos atuais examinados apontam para v2. |
| Testes solicitados | Não executados | O pytest abortou antes da coleta: `FileNotFoundError: No usable temporary directory found` ao inicializar captura, tentando usar diretórios temporários indisponíveis no ambiente somente leitura. |

## Achados

Nenhum achado ALTO ou BLOQUEANTE de privacidade/publicação foi identificado nesta auditoria. Os testes permanecem sem resultado por falha ambiental, não por falha reportada em teste.

## Comandos executados

- `git status --short --branch && git rev-parse HEAD && git branch --show-current && rg --files specs ml scripts notebooks docs/contratos-v3 | sort`  
  Saída: worktree `## v2-historico`, HEAD `b78777a32bac72e112b627e95d6b90c8759d1e9b`.
- `rg -n -i "sem dado registrado|sem_dado|n_registros|contrato_versao|v1|risco_h3_faixa" ...`  
  Busca ampla; saída foi truncada pelo volume de ocorrências do CSV.
- Verificação Python via `git show`, biblioteca padrão (`csv`, `hashlib`, `json`): contou os pares v1, validou os campos desses pares no CSV v2, hashes e fixture.
- `sed` e `rg` nos contratos, `ml/snapshot.py`, mensagens de UX, manifesto, fixture e derivados.
- `git grep -n -E 'risco_h3_faixa_v1\.csv|fixture_v1\.json' HEAD ...`  
  Referências encontradas em artefatos históricos.
- Comando pytest conforme solicitado:  
  `.venv311/bin/python -m pytest -q -p no:cacheprovider tests/test_cortes_treino.py tests/test_dedup.py tests/test_features_taxas.py tests/test_idempotencia.py tests/test_janela.py tests/test_politica_proximidade.py tests/test_quarentena.py tests/test_rota.py tests/test_schema_processed.py tests/test_schemas_derivados.py tests/test_sem_dado.py tests/test_snapshot.py`

## Limites desta execução

A execução dos testes foi bloqueada pela falta de diretório temporário gravável, antes da coleta de testes. A verificação de vazamento avaliou o HEAD indicado e os artefatos rastreados solicitados; não avaliou histórico remoto nem publicação externa.
## Complemento do operador (JARVIS)

- Os testes que o revisor não conseguiu executar (sandbox sem diretório temporário gravável) foram executados fora do sandbox, no mesmo HEAD e com o mesmo comando: **73 testes passando** nos 12 arquivos sem dependência de `torch`.
- Os 5 arquivos restantes (`test_calibracao`, `test_sequenciais`, `test_split_temporal`, `test_ta_descritiva`, `test_v2_historico`; 27 testes) importam `torch` e não puderam ser executados nesta sessão: a máquina estava com a memória de troca quase cheia e só o `import torch` passou de 15 minutos. A última execução completa com **100/100** foi feita antes, no mesmo dia e no mesmo estado dos arquivos v2 (ver `REVISAO-CODIGO-2026-11-16.md`). Repetir a suíte completa quando a máquina estiver livre.
- Nenhuma correção de código foi necessária após esta rodada.
