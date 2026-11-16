## BLOQUEANTE

Nenhum.

## ALTA

- [ml/v2_historico.py:9](ml/v2_historico.py:9): o docstring ainda diz que, na comparação A, “a única mudança é a história disponível nas variáveis”. Isso contradiz a própria seção 5.2 do notebook, que reconhece mudanças nas variáveis, origens e tamanho do treino; o JSON também registra 25.972 exemplos de treino em A. A rodada 2 já apontava essa frase como forte demais. **Correção:** alinhar o docstring ao notebook: a comparação é pareada nas mesmas chaves e rótulos do Teste, mas não isola o efeito do histórico; reservar essa interpretação à ablação.

## MÉDIA

- [scripts/gerar_notebook.py:268](scripts/gerar_notebook.py:268) e [scripts/gerar_notebook.py:346](scripts/gerar_notebook.py:346): há leituras explicativas mais fortes que a evidência mostrada. “Esses cinco achados explicam por que” e “modelos … superestimam o risco” atribuem uma explicação geral; a seção 4.3 mostra proporções dos rótulos — nível 3 cai de 28,1% no treino para 23,5% no Teste —, mas não apresenta ali a comparação entre previsões e rótulos de cada modelo que sustentaria a afirmação plural. **Correção:** descrever esses resultados como hipóteses compatíveis com os diagnósticos, sem atribuir causa ou generalizar para todos os modelos.

- [scripts/registrar_mlflow.py:16](scripts/registrar_mlflow.py:16) e [scripts/registrar_mlflow.py:26](scripts/registrar_mlflow.py:26): a tag `commit` registra o HEAD no momento de registrar no MLflow, não o commit de geração dos resultados. No estado revisado, o HEAD é `0c82410`, enquanto `v2_historico.json` identifica `0dad95eb…` como commit dos resultados. A tag atual pode, portanto, ser lida como proveniência dos números quando só identifica a execução do registrador. **Correção:** registrar separadamente o commit do registrador e o commit de origem dos resultados, e associar os runs aos arquivos versionados, por exemplo com seus hashes.

## BAIXA

- [scripts/gerar_notebook.py:241](scripts/gerar_notebook.py:241) e [scripts/gerar_notebook.py:540](scripts/gerar_notebook.py:540): as capturas 02 e 04 exibem o filtro `metrics.rmse < 1 and params.model = "tree"`, alheio aos experimentos descritos. Os runs e valores visíveis correspondem às métricas do projeto, mas o filtro pode confundir a leitura da captura. **Correção:** recapturar sem filtro residual ou identificá-lo como filtro inativo/irrelevante.

## Veredito:

A separação entre v1 pré-registrada e exploração, os números centrais, os ICs plotados e os limites de inferência estão em geral bem declarados; permanece uma contradição no docstring da comparação A e há leituras causais e uma tag de commit que precisam de ajuste para evitar interpretações indevidas. Não executei scripts nem testes.