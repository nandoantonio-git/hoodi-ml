# Modelo de dados (Fase 1): Nível de risco registrado por célula H3 e faixa horária

**Spec**: [spec.md](spec.md) · **Pesquisa**: [research.md](research.md)

Fluxo: `raw (XLSX, imutável)` → `interim (parquet)` → `processed` + `quarantine` + `fora_da_janela` → `features/rotulos` → `snapshot`.

## Entidades

### Registro de ocorrência (uma linha da base, um crime registrado)
| Campo | Origem | Regra |
|---|---|---|
| `bo_id` (só em memória) | `NUM_BO` + `ANO_BO` + `NOME_DELEGACIA` | usado só para deduplicar; nunca gravado em processed, quarentena, features, rótulos nem snapshot (constituição VII) |
| `rubrica` | `RUBRICA` | tipo de crime; define o peso |
| `data_fato` | `DATA_OCORRENCIA_BO` (serial Excel) | define o mês e o split |
| `hora` | `HORA_OCORRENCIA_BO` | fração do dia em [0,1); válida só nesse intervalo |
| `lat`, `lon` | `LATITUDE`, `LONGITUDE` | numéricas, ≠ 0, dentro do retângulo do estado de SP |
| `celula` | derivada | H3 res. 9 de (`lat`, `lon`) |
| `faixa` | derivada | bordas explícitas da hora: 0 madrugada [0,6), 1 manhã [6,12), 2 tarde [12,18), 3 noite_cedo [18,21), 4 noite [21,24) |
| `destino` | derivada | `usada`, `quarentena`, `duplicata_removida` ou `fora_da_janela` |
| `motivo` | derivada | motivo da quarentena ou da exclusão, ou vazio |

**Persistido × transitório** (inventário por camada em `ml/dados/README.md`): `processed/` grava só `rubrica`, `data_fato`, `mes`, `hora`, `faixa`, `celula` (gitignored, nunca entregue); `lat` e `lon` existem só em memória, até a conversão para H3, e MUST NOT ser gravadas em `processed/` (constituição VII); `quarantine/` grava só `fonte`, `linha`, `rubrica`, `motivo`; `bo_id` existe só em memória, para deduplicar. Snapshot, manifest e fixture levam `h3_cell`, `faixa`, `faixa_nome`, `status`, `nivel`, `pontuacao_mensal`, `n_registros`.

**Destino (exclusivo, cada linha tem exatamente um)**
- `duplicata_removida`: linha idêntica de mesmo BO e rubrica; só a repetida é removida.
- `quarentena`: sem coordenada utilizável, sem hora utilizável, ou BO com coordenada ou hora conflitante entre linhas. Motivos: `sem_coordenada`, `sem_hora`, `bo_conflito_coordenada`, `bo_conflito_hora`.
- `fora_da_janela`: dado utilizável, mas fora do perímetro ou com fato fora de jan–set 2026.
- `usada`: o resto.

**Reconciliação (SC-002)**: `entrada = usada + quarentena + duplicata_removida + fora_da_janela`, sempre exata. O perímetro é filtro de `usada`; linhas válidas fora dele contam como `fora_da_janela` com motivo `fora_do_perimetro`.

### Chave de risco
`(celula, faixa)`. Universo do snapshot: todas as células H3 res. 9 que cobrem o perímetro × 5 faixas. Há registros em 258 células e 952 chaves na janela (medido, ver pesquisa).

### Peso por rubrica (ponto de partida)
| Rubrica | Peso |
|---|---|
| Furto | 1 |
| Tráfico, drogas para consumo, lesão corporal culposa no trânsito | 1 |
| Roubo, lesão corporal | 3 |
| Homicídio, feminicídio, estupro | 5 |
| Ilícito extrapenal e qualquer rubrica não listada | sem peso: fora da pontuação, contada no relatório |

### Janela de dados e exemplo
| Campo | Regra |
|---|---|
| `origem` | T1 a T4 e Teste, conforme a pesquisa D-03 |
| `janela_features` | meses de features; só registros daquele intervalo |
| `janela_rotulo` | 2 meses seguintes à janela de features |
| `X` | taxas mensais de registros e de pontuação por chave, por rubrica agrupada e por faixa vizinha, da janela de features |
| `y` | nível 0 a 3 da chave na janela de rótulo |

Chave sem registro na janela de features: fica fora do classificador. Chave com features e sem registro no rótulo: o rótulo é "sem dado" e ela sai do cálculo de métricas de nível (viés de seleção declarado, com a contagem), e vai para um relatório à parte. Sem mínimo de registros por chave.

### Nível de risco
Inteiro de 0 a 3, ou "sem dado" (fora da escala, nunca 0). Cortes: três valores de pontuação mensal derivados dos rótulos de treino, fixos para o teste.

### Snapshot
Ver [contracts/snapshot-risco.md](contracts/snapshot-risco.md). Campos: `h3_cell`, `faixa`, `faixa_nome`, `status`, `nivel`, `pontuacao_mensal`, `n_registros`. Sem `nivel_previsto` (o backtest de ago–set fica fora do arquivo do app). `n_registros` conta só registros pontuáveis; no contrato v2, chaves com 0–2 registros são publicadas como `sem_dado`, contagem 0 e campos de pontuação/nível vazios.

### Quarentena
Registros com `destino = quarentena` e `motivo`. Arquivo próprio, nunca descartado.

## Validações (ligam a spec aos testes)
| Regra | Spec | Teste |
|---|---|---|
| Reconciliação exata | SC-002, FR-004 | `tests/test_quarentena.py` |
| Duplicata só da linha idêntica | FR-005 | `tests/test_dedup.py` |
| Mesmo raw, mesmo checksum | SC-001 | `tests/test_idempotencia.py` |
| "Sem dado" nunca vira 0 | SC-004, FR-007 | `tests/test_sem_dado.py` |
| Features só do passado; rótulo de teste só de ago–set | SC-003, FR-009 | `tests/test_split_temporal.py` |
| Cortes só do treino | FR-006 | `tests/test_cortes_treino.py` |
| CV com expurgo: nenhuma origem de treino tem rótulo que toque o rótulo validado | FR-009 | `tests/test_split_temporal.py` |
| Snapshot e fixture sem identificador de BO nem dado pessoal | FR-013 | `tests/test_snapshot.py` |
| Snapshot cobre todas as chaves do universo | FR-011 | `tests/test_snapshot.py` |

## Transições
`raw` → `interim` (conversão sem limpar) → classificação de destino (uma passagem, determinística) → features e rótulos por origem → modelos → snapshot. Cada etapa grava seu artefato e pode ser reexecutada sozinha.
