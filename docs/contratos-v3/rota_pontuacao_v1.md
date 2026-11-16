# Contrato de referência: pontuação de rota v1

**Status:** referência para validação, não integração. É uma demonstração retrospectiva não validada (`test_seen=true`). O algoritmo de rota permanece v1, mas seus vetores v2 são vinculados ao snapshot público v2. Fonte histórica: `PLANO-EXECUCAO-V3-r2.md` §4.

**Quem faz o quê:**
- **ML:** esta definição, a referência Python `ml/rota.py` e os vetores-ouro `vetores_rota_v2.json` (sha256 em `vetores_rota_v2.json.sha256`).
- **API .NET (Abner):**
  - o motor de rotas;
  - o endpoint;
  - a implementação em C# e o teste dela contra os vetores-ouro.

  Nada disso está feito e nada disso é responsabilidade do ML.

**Insumo:** snapshot v2 com supressão k ≥ 3, `ml/dados/snapshot/risco_h3_faixa_v2.csv`. O sha256 fica em `vetores_rota_v2.json → snapshot_csv_sha256`.

## 1. Entrada

- `pontos`: polilinha de pontos (lat, lon) em WGS84, em graus decimais.
- `faixa`: a faixa da **hora de partida**, de 0 a 4, com as bordas do contrato de snapshot v2, em `America/Sao_Paulo`. Ela vale para a viagem inteira; essa é uma limitação declarada.

## 2. Discretização

1. **Validar os pontos.** A latitude fica em [-90, 90] e a longitude em [-180, 180). Valor não finito ou fora desses limites dá `rota_invalida`.
2. **Limpar a polilinha.** Pontos consecutivos idênticos são removidos. Se restarem menos de 2 pontos, o resultado é `rota_invalida`.
3. **Dividir cada segmento** p0→p1 em `n = max(1, ceil(d/5))` subsegmentos:
   - `d` é a distância haversine;
   - `p_i = p0 + (i/n)·(p1 − p0)`, com a interpolação feita em graus;
   - o último ponto é exatamente `p1`.
4. **Medir e atribuir cada subsegmento.** O comprimento é a distância haversine entre as extremidades. O subsegmento vai para a célula `latlng_to_cell(ponto_médio, 9)`, com `ponto_médio = ((a.lat+b.lat)/2, (a.lon+b.lon)/2)`.
5. **Somar por célula.** Os metros são somados em precisão dupla. A ordem das células é a da primeira ocorrência na rota.

**Haversine:**
- `d = 2R·asin(sqrt(sin²(Δφ/2) + cos φ1·cos φ2·sin²(Δλ/2)))`;
- R = 6 371 008,8 m;
- os ângulos são convertidos para radianos só dentro dessa fórmula.

**H3:** core C **4.5.0**. No .NET, deve ser um binding do core C oficial nessa versão. Um porte reimplementado só é aceito se passar nos vetores de fronteira.

**Aproximação:** atribuir o subsegmento de ≤ 5 m pelo ponto médio aproxima a interseção exata com o hexágono.

## 3. Pontuação: a função pura `pontuar(trechos, faixa, snapshot)`

Para cada `(h3_cell, metros)`, a chave consultada é `(h3_cell, faixa)`:

| Situação da chave | Como entra no resultado |
|---|---|
| ausente do snapshot | conta como **fora da cobertura** |
| `status = sem_dado` | conta como **sem dado**. Não soma pontuação e **não** é tratada como segura. |
| `status = com_dado` | soma `pontuacao_mensal × metros/1000` |

**Saída, sem arredondar:**

| Campo | Definição |
|---|---|
| `pontuacao_acumulada_observada` | Σ `pontuacao_mensal × km`. É um **índice**, em pontos/(mês·hora) × km. Não é contagem esperada nem probabilidade. |
| `indice_por_km` | o índice acima ÷ km com dado; `null` se não houver km com dado |
| `km_total`, `km_com_dado` | — |
| `pct_sem_dado`, `pct_fora_da_cobertura` | percentual do comprimento (0–100) |
| `dado_insuficiente` | `pct_sem_dado + pct_fora_da_cobertura > 30`. É uma regra de produto **hipotética**. |
| `rotulo` | "pontuação acumulada observada, jan–set/2026 (retrospectiva), demonstração não validada" |

## 4. Ordenação, só entre rotas do mesmo par origem-destino

1. Rotas com `dado_insuficiente` ficam **sem posição**, com a marca "dado insuficiente no trajeto".
2. As demais são ordenadas da menor para a maior `pontuacao_acumulada_observada`.
3. **Empate:** `empate(a, b) = |a − b| ≤ 1e-9·max(|a|, |b|, 1)`, comparado sem arredondar. Como essa relação não é
   transitiva, o empate é aplicado por **classes ancoradas** (regra fechada, revisada após o red-team da implementação,
   rodada 1):
   - ordene as rotas pela pontuação exata, crescente (valores iguais: menor índice de entrada primeiro);
   - percorra a lista: a rota entra na classe atual se empata com a **primeira** rota da classe (a âncora, de menor
     pontuação); senão abre uma classe nova;
   - dentro de cada classe de pontuação, aplique a mesma regra a `km_total`;
   - dentro de cada classe de km, a ordem é o menor índice na lista de entrada.

## 5. Exibição

O arredondamento é *half-even* e só acontece na exibição:
- 1e-6 nos índices e percentuais;
- 0,01 m nos comprimentos (`metros_total`, `metros_com_dado`).

## 6. Vetores-ouro e aceite

`vetores_rota_v2.json` traz:
- **10 casos:**
  1. rota toda com dado;
  2. trecho sem dado;
  3. saída do perímetro;
  4. rota que cruza bordas;
  5. empate e ranking;
  6. 1 ponto (`rota_invalida`);
  7. pontos repetidos;
  8. segmento < 5 m;
  9. rota que volta para a mesma célula;
  10. faixa de 3 h.
- 2 rotas cujo ponto médio é um ponto de fronteira;
- 20 pontos interiores e 20 pontos a 5e-8 grau de arestas, cada um com a célula esperada;
- 2 vetores de empate, um dentro e outro logo fora da tolerância.

**Critério de aceite, do lado do Abner:**
- igualdade exata nas células;
- |Δ| ≤ 0,01 m nos metros;
- |Δ| ≤ 1e-6 relativo no índice.

A equivalência entre Python e C# só é demonstrada quando a implementação em C# passar nesses vetores. Até lá, ela **não** está provada.

## 7. O que este contrato não afirma

- Não afirma que uma rota seja segura nem que tenha risco, perigo ou funcione em tempo real.
- Não afirma previsão para o momento da viagem: a pontuação é retrospectiva de jan–set/2026.
- Não mede risco para quem está dentro do carro. O evento é "ocorrências registradas em via pública"; na base, a conduta de veículo cobre 6,8% e a conduta nula, 46%.
- Não cobre a escolha de rota fora do perímetro de 5×5 km.
