# hoodi — módulo de Machine Learning (Global Solution CitizenTech, FIAP)

> **Natureza do resultado:** mapa **histórico observado** de ocorrências registradas pela SSP-SP (contrato v3 vigente: abr–set/2026; v2, jan–set/2026, fica para rollback), por área (célula H3, resolução 9) e faixa horária. É o melhor dado disponível no período. **Não** indica risco em tempo real, **não** prevê o futuro e **não** aponta lugar seguro.

O hoodi é um aplicativo de apoio à decisão para quem anda a pé por São Paulo: mostra no mapa o nível de ocorrências registradas por área e horário e avisa quando a pessoa entra em uma área de nível alto. A comparação de rotas de carro é a fase 2, depois da entrega. Este repositório contém **somente o módulo de ML**: ingestão do dado público, construção do mapa de níveis, avaliação honesta de modelos e os contratos que a API e o app consomem.

## Ficha CitizenTech
- **Equipe e RMs:** Abner Barbosa (RM558468), Beatriz Vieira de Novais (RM554746), Fernando Antonio (RM555201) e Mariana Neugebauer (RM550494).
- **Desafio / problema:** quem se desloca pela cidade decide trajetos e horários sem informação organizada sobre onde e quando houve ocorrências. O hoodi oferece apoio à decisão, com base em dado oficial (SSP-SP), para evitar vias e rotas de maior exposição histórica.
- **Público-alvo:** pessoas ativas que andam a pé por São Paulo, em geral com trabalho presencial ou híbrido. O app avisa, de forma ambiente, quando a pessoa entra em área com ocorrências registradas. Rotas de carro ficam para a fase 2 e exigem avaliação própria do ML (o dado atual não distingue crime contra veículo; ver Limites).
- **ODS relacionados:** ODS 11, Cidades e Comunidades Sustentáveis (principal, meta 11.2); ODS 16, Paz, Justiça e Instituições Eficazes (secundário).
- **Justificativa dos ODS:** ODS 11: o hoodi apoia a decisão de deslocamento na cidade, com alerta ambiente a pé por exposição histórica a ocorrências, em linha com a meta de transporte mais seguro. ODS 11 é o principal. ODS 16 (secundário): usa só dado público oficial (SSP-SP), com método, limites e código abertos. É um indicador histórico observado, não garantia de segurança nem previsão.

## Sumário
1. [Arquitetura e papel do ML](#arquitetura-e-papel-do-ml)
2. [O que este módulo entrega](#o-que-este-módulo-entrega)
3. [Dados](#dados)
4. [Contrato do snapshot (v2)](#contrato-do-snapshot-v2)
5. [Resultados](#resultados)
6. [Privacidade e uso responsável](#privacidade-e-uso-responsável)
7. [Como reproduzir](#como-reproduzir)
8. [Testes](#testes)
9. [Estrutura do repositório](#estrutura-do-repositório)
10. [Processo: especificação, revisões e decisões](#processo-especificação-revisões-e-decisões)
11. [Limites conhecidos e próximos passos](#limites-conhecidos-e-próximos-passos)

## Arquitetura e papel do ML

```
SSP-SP (XLSX público) ──► ml/ (lote, Python) ──► snapshot CSV + sha256 + manifest
                                                        │
                                                        ▼
                                            API .NET (serve o snapshot,
                                            pontua rotas pelos vetores-ouro)
                                                        │
                                                        ▼
                                            App Expo (mapa, alerta de
                                            proximidade no aparelho, offline)
```

- O ML roda **em lote**, fora do caminho do usuário. Nada é calculado em tempo real.
- A API só aceita um snapshot cujo SHA-256 seja o do contrato vigente. Hash diferente = falha fechada, sem alerta.
- O app aplica a política de proximidade localmente, com o snapshot embarcado.

## O que este módulo entrega

| Entregável | Onde |
|---|---|
| **Snapshot v3 (vigente)**: semestral abr–set/2026, 5×5 km, k ≥ 3, SHA-256 `e33bd004…c71c0da` | `ml/dados/snapshot_v3/` |
| Snapshot v2 (referência e rollback, jan–set/2026), SHA-256 `2dddef70…` | `ml/dados/snapshot/` |
| Derivados v3: política de proximidade e vetores de rota | `docs/contratos-v3/politica_proximidade_v3.json`, `vetores_rota_v3.json` |
| Fixture de 5 linhas para testes dos consumidores | `ml/dados/snapshot/fixture_v2.json` |
| Política de alerta de proximidade (parâmetros e casos) | `docs/contratos-v3/politica_proximidade_v2.json` |
| Vetores-ouro para validar a pontuação de rota na API | `docs/contratos-v3/vetores_rota_v2.json` + `rota_pontuacao_v1.md` |
| Notebook documentado de ponta a ponta, executado | `notebooks/hoodi_ml_documentado.ipynb` |
| Relatório com métricas, intervalos, calibração e limites | `RELATORIO_ML.md` |
| Proveniência, inventário e privacidade dos dados | `ml/dados/README.md` |
| Revisão de código e quatro rodadas de red-team independente | `docs/REVISAO-CODIGO-2026-11-16.md`, `docs/REDTEAM-ENTREGA-rodada*.md` |
| Registro dos prompts de IA usados no trabalho | `prompts.md` |

## Dados

- **Fonte:** SSP-SP, portal da Transparência, arquivo `SPDadosCriminais_2026.xlsx`. URL, tamanho e SHA-256 em `ml/dados/README.md`; o conversor aborta se o hash divergir.
- **Janela:** 1º de janeiro a 30 de setembro de 2026, fuso America/Sao_Paulo.
- **Volume:** 814.900 linhas no arquivo; 20.657 com coordenada e hora dentro do perímetro (todo o ano); **20.343 usadas na modelagem** (jan–set/2026, após remover 307 fora da janela e as duplicatas/conflitos de BO), 2,50 % da base e 58,5 % do que cai no perímetro.
- **Reconciliação:** entrada = usadas + quarentena + duplicatas removidas + fora da janela, sem resto. Linhas sem hora, sem coordenada ou com BO conflitante vão para a quarentena com o motivo registrado (`ml/dados/reconciliacao*.txt`).
- **Unidade de análise:** célula H3 resolução 9 (≈ 0,1 km²) × 5 faixas horárias: madrugada [0,6), manhã [6,12), tarde [12,18), noite cedo [18,21), noite [21,24).
- **Rótulo:** `pontuacao_mensal` = soma dos pesos ÷ 9 meses ÷ horas da faixa; `nivel` 0–3 pelos três cortes de quartil calculados **só no treino**.
- **O dado bruto não está no Git.** Apenas agregados por célula e faixa são versionados.

> **Contrato vigente: v3** (`ml/dados/snapshot_v3/`). O texto abaixo descreve o formato, idêntico em v2 e v3; os números (1.395 chaves, 954/441) são do v2. No v3: 1.395 chaves, 824 `com_dado` e 571 `sem_dado`.

## Contrato do snapshot (formato v2/v3)

Arquivo: `ml/dados/snapshot/risco_h3_faixa_v2.csv` · SHA-256: `2dddef701bdecb65142874980f1ae5aba7b2ac6ab2abad5c47b07f07ecc5080a` · `contrato_versao = 2`.

| Coluna | Tipo | Significado |
|---|---|---|
| `h3_cell` | texto | índice H3 resolução 9 |
| `faixa` | 0–4 | faixa horária |
| `faixa_nome` | texto | nome da faixa |
| `status` | `com_dado` \| `sem_dado` | se há nível publicado |
| `nivel` | 0–3 ou vazio | nível observado; **vazio** quando `sem_dado` (nunca 0 por ausência) |
| `pontuacao_mensal` | decimal ou vazio | base do nível |
| `n_registros` | inteiro | ocorrências na chave; 0 quando `sem_dado` |

Invariantes verificadas por teste: 1.395 chaves no universo; 954 `com_dado`, todas com `n_registros ≥ 3`; 441 `sem_dado`. Chaves com 1 ou 2 registros são publicadas como `sem_dado` e são **indistinguíveis de ausência**; o manifesto guarda só os totais agregados da supressão (218 chaves, 306 registros). A especificação completa está em `specs/001-risco-h3-faixa-horaria/contracts/snapshot-risco.md`.

## Resultados

Protocolo: divisão **temporal** (origens T1–T4 no treino, 3.132 exemplos; teste ago–set/2026, 847 exemplos), features só com meses anteriores ao alvo, seleção por validação cruzada com expurgo só no treino, vencedor pré-registrado antes de abrir o teste, intervalos por bootstrap pareado (2.000 reamostras por célula). Detalhes e tabela completa em `RELATORIO_ML.md`.

| Modelo | Macro-F1 [IC 95 %] | Nível exato | Erro ≤ 1 nível |
|---|---|---|---|
| Persistência (nível da janela anterior) | 0,491 [0,457; 0,524] | 50,2 % | 87,5 % |
| Random Forest pré-registrado | 0,467 [0,432; 0,500] | — | — |
| **Random Forest regularizado** (exploratório) | **0,513 [0,479; 0,546]** | 52,3 % | 88,7 % |

- A diferença pareada RF regularizado − persistência em macro-F1 é +0,022 [−0,010; 0,052]: **não ficou estabelecida**.
- O RF regularizado subestimou menos o nível registrado e teve menor custo médio de erro, mas foi escolhido depois de ver o teste (`test_seen = true`). É evidência exploratória, não prova de superioridade.
- Calibração: ECE 0,047 sem pós-processamento; a calibração isotônica piorou para 0,105 e foi rejeitada.
- O RF pré-registrado sobreajusta (gap treino−teste 0,36); a regularização escolhida por CV leva o gap a ≈ 0.

**Decisão de produto:** o que vai para o app é o **mapa observado**, não a saída de um modelo preditivo.

## Privacidade e uso responsável

- Nenhuma coordenada de ocorrência, número de BO ou campo individual é versionado; só agregados por célula e faixa. As únicas coordenadas no repositório são o polígono do perímetro de estudo (manifesto) e pontos sintéticos dos casos de teste de rota (vetores-ouro).
- Supressão k ≥ 3 por chave; o backtest publicado tem apenas métricas agregadas por modelo, sem associação com célula ou faixa.
- Hash obrigatório em todos os derivados; consumidor com hash diferente deve falhar fechado.
- O texto do app nunca diz "seguro": `sem_dado` é mostrado como "dados insuficientes para exibição".
- Inventário por camada (conteúdo, acesso, retenção, descarte) em `ml/dados/README.md`.

## Como reproduzir

Requisitos: Python 3.11; no macOS, `brew install libomp` para o XGBoost.

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Baixe SPDadosCriminais_2026.xlsx da SSP-SP (URL e sha256 em ml/dados/README.md)
export HOODI_XLSX_DIR=~/Downloads
python scripts/00_xlsx_para_parquet.py      # aborta se o sha256 divergir
python -m ml.ingestao                        # ml/dados/processed/usadas.parquet
python -m ml.gerar_snapshot                  # snapshot + manifest + fixture
python -m ml.modelos                         # seleção por CV e avaliação no teste
python -m ml.incerteza_custo                 # IC por bootstrap, RF regularizado e custo
python -m ml.calibracao                      # calibração, estratos e backtest agregado
python -m ml.politica_proximidade            # política de proximidade v2
python -m ml.rota                            # vetores-ouro de rota v2

pytest -q                                    # suíte completa (100 testes)
```

O snapshot regenerado tem o mesmo SHA-256 do versionado; só o campo `gerado_em` do manifesto muda. O conversor cria `ml/dados/interim/` e instala/carrega a extensão `excel` do DuckDB (a primeira execução precisa de rede para baixá-la).

O notebook `notebooks/hoodi_ml_documentado.ipynb` é a fonte única e é editado diretamente. Para reexecutá-lo, rode `jupyter nbconvert --execute --to notebook --inplace notebooks/hoodi_ml_documentado.ipynb` dentro de `notebooks/` (caminhos relativos). `scripts/gerar_notebook.py` está aposentado e não deve ser executado: ele sobrescreveria o notebook com uma versão antiga.

## Testes

`pytest -q` roda 100 testes em 17 arquivos. O que eles garantem:

| Grupo | Arquivos | Garantia |
|---|---|---|
| Reconciliação do dado | `test_quarentena`, `test_dedup`, `test_janela`, `test_schema_processed` | nada se perde nem se duplica na ingestão |
| Sem vazamento temporal | `test_split_temporal`, `test_cortes_treino`, `test_features_taxas` | teste nunca entra no treino; cortes só do treino |
| Contrato do snapshot | `test_snapshot`, `test_sem_dado`, `test_idempotencia`, `test_schemas_derivados` | k ≥ 3, `sem_dado` sem nível, hash reproduzível, derivados amarrados |
| Produto | `test_politica_proximidade`, `test_rota` | política determinística; vetores-ouro batem com a implementação de referência |
| Modelagem | `test_calibracao`, `test_sequenciais`, `test_ta_descritiva`, `test_v2_historico` | métricas, backtest agregado sem célula/faixa, histórico v2 |

Os cinco arquivos de modelagem importam `torch` e são os mais lentos para iniciar.

## Estrutura do repositório

```
ml/                 ingestão, rótulo, features, modelos, snapshot, política de proximidade, rota
ml/dados/snapshot/  snapshot v2, sha256, manifest e fixture (entregáveis)
ml/dados/resultados/ métricas, seleção, calibração e backtest agregado (JSON/CSV)
docs/contratos-v3/  política de proximidade v2, vetores de rota v2 e o contrato de pontuação de rota
docs/               especificação, decisões, revisões e todas as rodadas de red-team
specs/              spec-kit: spec, plano, modelo de dados, contrato, quickstart e tarefas
scripts/            conversão do XLSX, qualidade do dado, geração do notebook, registro no MLflow
notebooks/          notebook documentado e executado
tests/              suíte pytest
RELATORIO_ML.md     relatório técnico
prompts.md          registro dos prompts de IA usados
```

## Processo: especificação, revisões e decisões

O trabalho seguiu especificação antes do código (`specs/`), pré-registro dos candidatos e revisão independente a cada entrega:

- `docs/SPEC-ML.md`, `docs/DECISOES-V3.md` e `docs/PLANO-EXECUCAO-V3-r*.md`: o que foi decidido e por quê.
- `docs/REDTEAM-*.md`: rodadas de red-team feitas por um revisor automatizado independente, em modo somente leitura, com os achados e o que foi corrigido em cada uma.
- `docs/REVISAO-CODIGO-2026-11-16.md`: revisão de segurança, contratos, cobertura (76 % total; 82–100 % nos módulos de contrato) e disposição de cada achado.
- `docs/DECISAO-PRIVACIDADE-SNAPSHOT-V2.md`: a decisão humana que criou o contrato v2 e o saneamento do histórico.

## Limites conhecidos e próximos passos

- O mapa descreve **registros**, não ocorrências reais: subnotificação e variação de registro entre regiões afetam o resultado.
- Nove meses de dado; sem validação com pessoas em uso real. A política de proximidade é demonstração retrospectiva.
- Nenhum modelo superou a persistência de forma estabelecida; o app usa o mapa observado.
- Próximos passos em `RELATORIO_ML.md`, seção 9.
