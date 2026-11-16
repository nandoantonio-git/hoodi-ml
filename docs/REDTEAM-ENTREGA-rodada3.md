# Red-team da entrega — rodada 3

Data: 2026-11-16  
Revisor: Codex CLI real, execução independente e somente leitura  
HEAD revisado: `475cd5b`  
Escopo principal: diff `389aa61..475cd5b`

## Parecer

Nenhum bloqueante técnico e nenhuma alta técnica corrigível foram identificados no estado atual. A entrega ainda não está liberada para publicação ou aceite final porque permanecem três gates humanos:

1. **ALTA — histórico local:** o commit `df5b431` conserva o backtest detalhado. Por composição com o snapshot, o revisor recuperou 225 chaves com uma ocorrência e 144 com duas ocorrências em ago–set. É preciso decidir por saneamento do histórico ou distribuição sem esses objetos antes de publicar/enviar.
2. **ALTA — snapshot k < 3:** o snapshot atual contém 130 chaves com um registro e 88 com dois. Nenhuma está no nível 3, mas isso não elimina a possibilidade de inferência. É preciso aceitar formalmente uma distribuição restrita ou aprovar agregação/supressão com nova versão do contrato e novo hash.
3. **BLOQUEANTE A4:** a Ficha CitizenTech continua sem equipe/RMs, desafio, público, ODS e justificativa oficiais. Esses dados não foram inferidos.

## Correções confirmadas

- O backtest do HEAD contém apenas três linhas agregadas e cinco campos: `modelo`, `n`, `macro_f1`, `acerto_exato` e `erro_le_1_nivel`.
- O revisor recalculou essas métricas a partir dos resultados históricos e obteve diferença numérica zero.
- O notebook contém 27 células de código executadas, sem saída de erro, e não expõe H3 nem os antigos campos individuais do backtest.
- A interpretação dos estratos está correta: 21–24h tem o menor F1 do RF; 18–21h tem a maior desvantagem diante da persistência.
- O inventário de privacidade cobre logs e saídas de terminal.
- CSV, arquivo `.sha256` e manifesto concordam no hash `e721974f1966fb901144ee33036eb07a4640544203f72db83e0666719191152e`.

## Achado técnico baixo e disposição

O revisor observou que o teste do backtest não exigia exatamente três linhas nem unicidade de modelo. O teste foi fortalecido para verificar cardinalidade, unicidade e o esquema completo. Depois da correção, a suíte completa passou: **99 testes em 16,47 s**.

## Limite da execução independente

O sandbox somente leitura do revisor passou 92 testes, excluiu seis que escrevem artefatos e não conseguiu executar o teste LSTM porque o PyTorch precisava de diretório temporário gravável. Fora desse sandbox, a suíte completa do mesmo estado passou com 99 testes; portanto, a falha observada pelo revisor foi ambiental.

## Contagem final

- 0 bloqueantes técnicos;
- 0 altas técnicas corrigíveis;
- 0 achados técnicos pendentes;
- 3 gates humanos: duas altas de privacidade e um bloqueante documental A4.
