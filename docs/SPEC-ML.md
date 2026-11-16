# Especificação do ML do hoodi (v1, 2026-11-11)

Decisões fechadas com o Nando na grill-me (rodadas 1 e 2). Constituição: `.specify/memory/constitution.md`.

Atualizado em 2026-11-11 com as cinco decisões do /speckit-clarify (ver `specs/001-risco-h3-faixa-horaria/spec.md`, seção Clarifications).

## 1. Pergunta de ML
Dada uma célula H3 res. 9 e uma faixa horária, qual é o nível de risco registrado (0–3)?

## 2. Dado
- SSP-SP 2026, XLSX original com sha256 em `ml/dados/raw/CHECKSUM.txt`. 814.900 linhas (555.404 + 259.496).
- Fonte oficial: https://www.ssp.sp.gov.br/assets/estatistica/transparencia/spDados/SPDadosCriminais_2026.xlsx (SSP-SP, Transparência; atualizado no servidor em 28/10/2026). Verificado em 11/11/2026 por requisição de cabeçalho: 139.931.418 bytes, igual ao arquivo local em ~/Downloads. O sha256 do arquivo local está em CHECKSUM.txt; em 11/11/2026 baixei o arquivo de novo e o sha256 coincide com o local (ver `ml/dados/raw/PROVENIENCIA.md`).
- Página do portal: https://www.ssp.sp.gov.br/transparencia/dados-abertos (só traz o Plano de Dados Abertos e PDFs de chamadas ao 190; os XLSX ficam no caminho acima).

## 3. Perímetro
5×5 km centrados na FIAP Paulista. Centro aproximado (-23,5646; -46,6522); coordenada exata PENDENTE (OSM dá -23,5643240; -46,6527132 para Av. Paulista 1106, mas o número do endereço da FIAP não está confirmado).
bbox: lat -23,58706..-23,54214; lon -46,67671..-46,62769.
Medido: 34.769 registros com coordenada, 20.657 com coordenada e hora.

## 4. Qualidade, quarentena e unidade de contagem
- Válido: lat/long numéricas, ≠0, dentro do retângulo de SP; hora em [0,1).
- Sem hora utilizável: quarentena sinalizada. Perda reportada como "% de dado utilizável".
- Unidade: cada linha é um crime registrado. Remove-se só a linha idêntica (mesmo BO e rubrica); 1 caso medido.
- BO com coordenada ou hora conflitante: quarentena (385 e 13 BOs medidos).
- Medido: 9.526 BOs em mais de uma linha; 7.166 com rubricas diferentes.

## 5. Rótulo
- Faixas: madrugada 0–6, manhã 6–12, tarde 12–18, noite_cedo 18–21, noite 21–24 (5 faixas; noite quebrada a pedido do Abner). Pontuação normalizada por hora da faixa.
- Pesos iniciais (ponto de partida, declarados como tal): furto 1; roubo e lesão corporal 3; homicídio, feminicídio e estupro 5; tráfico, drogas para consumo e lesão corporal culposa no trânsito 1. Ilícito extrapenal fica fora da pontuação e é contado no relatório como "rubrica sem peso".
- Pontuação da célula×faixa = soma dos pesos ÷ n meses da janela ÷ horas da faixa (6, 6, 6, 3, 3), em pontos por mês por hora. Níveis 0–3 por quartis entre as chaves com dado do treino (0 = quartil de menor pontuação, 3 = maior). Os cortes saem só do treino (jan–jul) e são reaplicados ao teste. Distribuição real mostrada ao Nando antes de aplicar.
- "Sem dado" fora da escala.

## 6. Modelagem
- Split temporal pela data do fato: treino jan–jul, teste ago–set. Registros com fato fora de jan–set 2026 ficam fora da modelagem ("fora da janela"). Desbalanceamento declarado.
- Alvo: o nível de cada chave em ago–set, com features só de jan–jul. Features de qualquer exemplo usam apenas registros anteriores ao período do seu rótulo; o rótulo de teste vem só de registros de ago–set.
- Candidatos planejados (T025 aberto): RF, XGBoost e MLP (mais linhas de base). LSTM e KMeans+PCA: declarados "não executados" com justificativa, pendente de confirmação do Nando. Escolha justificada no relatório.
- Busca de ≥10 combinações de 3 hiperparâmetros, CV só no treino, por origem e com expurgo (sem sobreposição de rótulo).
- Métricas de treino e teste lado a lado; discussão de overfitting; baseline simples.

## 7. Critérios de aceite (rubrica do briefing p. 33)
| # | Critério | Verificação |
|---|----------|-------------|
| A1 | Repositório Python separado, com `ml/` e notebook executado | notebook com saídas |
| A2 | `ml/dados/README.md`, `requirements.txt`, snapshot com checksum | arquivos e sha256 conferem |
| A3 | `RELATORIO_ML.md` de 2 a 4 páginas, só com números executados | números rastreáveis a saídas |
| A4 | README com Ficha da CitizenTech e ODS | revisão humana |
| A5 | `prompts.md` contínuo | entradas por data |
| A6 | Red-team real via Codex CLI | relatório do Codex anexado |

## 8. Testes esperados
- Idempotência: duas ingestões produzem o mesmo snapshot (mesmo checksum).
- Checksum: o XLSX e o snapshot batem com o declarado.
- Quarentena: linhas sem hora ou conflitantes não entram no treino; contagem reconciliada (entrada = usadas + quarentena + duplicata removida + fora da janela).
- Controle de vazamento temporal: nenhuma data de teste anterior à última de treino, features estritamente anteriores ao início do rótulo e transformações ajustadas só no treino da dobra (backtest retrospectivo; não afirma "ausência de vazamento").
- "Sem dado" nunca vira 0.

## 9. Contrato com o Abner (prazo 11/11 12h)
Chave de risco (célula H3 + faixa), janela do snapshot, fixture. Rota e fixture: 11/11 20h.

## 10. Prazos
Congelamento 16/11. Entrega 19/11 às 23h55.

## 11. Fora de escopo
Dado pessoal; "tempo real"; "rota segura"; qualquer envio sem confirmação.
