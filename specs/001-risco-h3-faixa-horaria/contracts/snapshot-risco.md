# Contrato: snapshot de risco para o app (Abner)

**Spec**: [../spec.md](../spec.md) · **Modelo de dados**: [../data-model.md](../data-model.md) · **Versão do contrato**: 2 (supressão k ≥ 3 aprovada em 2026-11-16; mantém 5 faixas e não inclui `nivel_previsto`)

A API e o app ficam fora deste repositório. O contrato entre os dois lados é este: a chave de risco, os arquivos do snapshot e a fixture.

## Arquivos entregues

| Arquivo | Conteúdo |
|---|---|
| `ml/dados/snapshot/risco_h3_faixa_v2.csv` | uma linha por chave de risco (célula × faixa) |
| `ml/dados/snapshot/risco_h3_faixa_v2.csv.sha256` | sha256 do CSV, no formato `<hash>  <arquivo>` |
| `ml/dados/snapshot/manifest.json` | janela de dados, fonte, versão, contagens e hash |
| `ml/dados/snapshot/fixture_v2.json` | amostra pequena para testes do app |

## Chave de risco

`h3_cell` (H3 resolução 9, 15 caracteres hexadecimais minúsculos) + `faixa` (inteiro de 0 a 4). Fuso `America/Sao_Paulo`.

| `faixa` | `faixa_nome` | Horas |
|---|---|---|
| 0 | `madrugada` | 0h até antes das 6h |
| 1 | `manha` | 6h até antes das 12h |
| 2 | `tarde` | 12h até antes das 18h |
| 3 | `noite_cedo` | 18h até antes das 21h |
| 4 | `noite` | 21h até antes das 24h |

Intervalos fechados à esquerda e abertos à direita: `[0,6)`, `[6,12)`, `[12,18)`, `[18,21)`, `[21,24)`.

## Colunas do CSV (UTF-8, separador vírgula, **ponto como separador decimal**, cabeçalho, quebra de linha LF)

| Coluna | Tipo | Regra |
|---|---|---|
| `h3_cell` | texto | obrigatória |
| `faixa` | inteiro 0–4 | obrigatória |
| `faixa_nome` | texto | obrigatória |
| `status` | `com_dado` ou `sem_dado` | obrigatória. `com_dado` exige pelo menos 3 registros pontuáveis. `sem_dado` cobre 0–2 registros depois da supressão k ≥ 3; quem está fora do perímetro é "fora da cobertura", tratado pelo app e fora do arquivo |
| `nivel` | inteiro 0–3 | observado em jan–set: os 3 cortes do treino aplicados a `pontuacao_mensal`; preenchida **só** quando `status = com_dado`; vazia quando `sem_dado`. **Nunca** 0 para "sem dado" |
| `pontuacao_mensal` | decimal, ponto como separador | pontos de gravidade por mês por hora da faixa: (soma dos pesos dos registros de jan–set) ÷ 9 meses ÷ horas da faixa (6, 6, 6, 3, 3). Intensidade registrada por hora, com pesos convencionais; comparável entre células e faixas nesse sentido, sem representar probabilidade individual nem exposição (a população exposta é desconhecida e há subnotificação); vazia quando `sem_dado` |
| `n_registros` | inteiro | registros **pontuáveis** usados na chave em jan–set; 0 quando `sem_dado`, ou ≥ 3 quando `com_dado`. Valores 1 e 2 nunca são publicados |

Linhas ordenadas por `h3_cell` e depois `faixa`. Sem timestamp dentro do CSV, para o hash ser idêntico em duas execuções.

O snapshot lista **todas** as células H3 res. 9 que cobrem o perímetro × 5 faixas. Assim, "sem dado" é explícito e o app não precisa inferir ausência.

## Invariantes (o app pode contar com elas)

1. Nenhuma linha tem `status = sem_dado` com `nivel` ou `pontuacao_mensal` preenchidos; sua contagem publicada é 0.
2. `nivel` só assume 0, 1, 2 ou 3.
3. Cada par (`h3_cell`, `faixa`) aparece uma única vez.
4. Toda linha `com_dado` tem `n_registros ≥ 3`; não há valores 1 ou 2 no CSV.
5. O `sha256` do CSV bate com o do `.sha256` e com o do `manifest.json`.

## `manifest.json`

| Campo | Conteúdo |
|---|---|
| `contrato_versao` | 2 |
| `fonte` | SSP-SP, SPDadosCriminais_2026.xlsx, com o sha256 do raw |
| `janela_dados` | `2026-01-01` a `2026-09-30` (data do fato) |
| `fuso` | `America/Sao_Paulo` |
| `faixas` | lista com `faixa`, `faixa_nome` e intervalo, por exemplo `[18,21)` |
| `h3_resolucao` | 9 |
| `perimetro_centro`, `perimetro_tamanho_km` | centro do retângulo (lat -23,56460; lon -46,65220, provisório até a coordenada exata da FIAP) e 5 × 5 km |
| `total_linhas_base`, `total_registros_usados` | linhas da base e registros usados (reconciliação) |
| `formula_pontuacao` | texto: soma dos pesos ÷ 9 ÷ horas da faixa, com a tabela de pesos |
| `perimetro` | bbox lat -23,58706 a -23,54214; lon -46,67671 a -46,62769 |
| `cortes_nivel` | os três cortes de pontuação mensal, do treino (rótulos T1 a T4, janelas de 2 meses) |
| `janela_nivel` | `2026-01-01` a `2026-09-30`; `pontuacao_mensal` = soma dos pesos ÷ 9 meses ÷ horas da faixa (6, 6, 6, 3, 3) |
| `n_chaves`, `n_com_dado`, `n_sem_dado` | contagens |
| `privacidade` | regra k ≥ 3 e apenas os totais agregados de chaves/registros suprimidos; nunca a associação das chaves suprimidas |
| `csv_sha256` | hash do CSV |
| `gerado_em` | data e hora da geração (fora do hash do CSV) |
| `natureza` | "mapa histórico observado (jan–set 2026); não é previsão. O backtest do classificador é um experimento retrospectivo à parte" |
| `aviso` | "Melhor dado disponível no período. Não indica tempo real nem local seguro." |

## Fixture

Pequena amostra tirada do snapshot real, com um exemplo de cada nível 0–3 e ao menos uma chave `sem_dado`. É gerada por `ml/snapshot.py` a partir dos dados reais, nunca escrita à mão.

Formato, **ilustrativo** (os valores abaixo mostram só a estrutura e não são dado real):

```json
{
  "contrato_versao": 2,
  "chaves": [
    { "h3_cell": "89a8100c53bffff", "faixa": 0, "faixa_nome": "madrugada",
      "status": "com_dado", "nivel": 1, "n_registros": 12 },
    { "h3_cell": "89a8100c507ffff", "faixa": 3, "faixa_nome": "noite_cedo",
      "status": "sem_dado", "nivel": null, "n_registros": 0 }
  ]
}
```

O exemplo usa células reais do perímetro (a célula do centro e uma vizinha) só como identificadores.

## Pendências com o Abner (prazo 11/11 12h; rota e fixture 11/11 20h)

- Confirmar CSV + JSON como formato (D-07 da [pesquisa](../research.md)).
- Confirmar as 5 faixas e os nomes de coluna. `nivel_previsto` não existe no arquivo do app: o backtest de ago–set fica num arquivo à parte da entrega de ML.
- Confirmar que `sem_dado` explícito é o que o app espera.
