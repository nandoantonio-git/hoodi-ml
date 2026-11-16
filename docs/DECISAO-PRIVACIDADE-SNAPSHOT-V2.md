# Decisão de privacidade — snapshot v2

Data: 2026-11-16  
Decisor: Nando  
Escolha: opção A — suprimir/agregar chaves com menos de três ocorrências e sanear o histórico antes de publicar.

## Mudança aplicada

- O contrato do snapshot passa de v1 para v2.
- Uma chave H3 resolução 9 × faixa só é publicada como `com_dado` quando tem pelo menos três registros pontuáveis.
- Chaves com 0–2 registros são publicadas como `sem_dado`, com `n_registros=0` e `nivel`/`pontuacao_mensal` vazios.
- O arquivo entregue não identifica quais chaves foram suprimidas.
- O manifesto guarda somente os totais agregados: 218 chaves e 306 registros suprimidos.

## Efeito no contrato

| Artefato | Versão atual |
|---|---|
| Snapshot | `risco_h3_faixa_v2.csv` |
| Fixture | `fixture_v2.json` |
| Política de proximidade | `politica_proximidade_v2.json` |
| Vetores de rota | `vetores_rota_v2.json` |

Novo SHA-256 do snapshot:

`2dddef701bdecb65142874980f1ae5aba7b2ac6ab2abad5c47b07f07ecc5080a`

Contagens publicadas:

- 1.395 chaves no universo;
- 954 `com_dado`, todas com `n_registros >= 3`;
- 441 `sem_dado`, incluindo as 218 suprimidas.

## Compatibilidade

O v2 substitui o v1 antes da integração. API e app precisam aceitar os novos nomes, `contrato_versao=2` e o novo hash. Um consumidor que apresentar o hash antigo deve falhar fechado e não disparar alertas.

## Verificação

- geração determinística do snapshot e dos contratos derivados;
- igualdade entre hash real, `.sha256`, manifesto, política e vetores;
- ausência de contagens 1 ou 2 nas linhas publicadas;
- fixture como subconjunto exato do snapshot;
- suíte completa: 100 testes passando.

O histórico publicável é reescrito para conter apenas o estado agregado do backtest e os artefatos v2. Nenhum push ou envio foi realizado durante esta mudança.

## Saneamento do histórico local (executado em 2026-11-16)

Backup prévio feito fora do repositório, em arquivo local não publicado (contém a cadeia antiga com o backtest detalhado).

Os cinco commits da revisão foram reescritos para que o backtest detalhado (848 linhas com H3 × faixa) nunca tenha existido na ancestralidade publicável; nos dois commits que o continham, o blob foi substituído pelo backtest agregado (4 linhas). Autor, data, mensagem e a árvore final foram preservados. Referências antigas, reflogs e objetos órfãos foram removidos do repositório compartilhado (`git gc --prune=now`).

| Commit antigo | Commit novo | Conteúdo |
|---|---|---|
| `df5b431` | `4a5098b` | Revisão de código 2026-11-16 (backtest agora agregado) |
| `389aa61` | `3331a05` | Correções da rodada 1 (backtest agora agregado) |
| `475cd5b` | `95d0721` | Agregação do backtest e rodada 2 |
| `81b8d18` | `b4657d8` | Fechamento da rodada 3 |
| `b78777a` | `c2b187e` | Contrato v2 (decisão A) |

Os documentos `REDTEAM-ENTREGA-rodada1..3` e `REVISAO-CODIGO-2026-11-16` citam os hashes antigos; foram preservados como estavam e esta tabela faz a tradução.

## Limite do saneamento — exige decisão humana

O snapshot v1 (`risco_h3_faixa_v1.csv`, com as 218 chaves de 1–2 registros) entrou no repositório em `07934d8` (2026-11-12) e faz parte da ancestralidade **compartilhada** com `main` e `feat/industrialize-hoodi-ml` (base comum `4f3aef5`). Ele foi removido da árvore atual, mas continua nos commits antigos das três branches. Reescrever `main` e `feat/industrialize` está fora do escopo autorizado (a branch `feat/industrialize` foi explicitamente deixada de fora). Antes de qualquer publicação, escolher: (1) reescrever também `main`/`feat` removendo o CSV v1 do histórico; ou (2) publicar a partir de um histórico novo (branch órfã ou clone filtrado) contendo só o estado v2; ou (3) aceitar formalmente que o histórico publicado contém o snapshot v1.
