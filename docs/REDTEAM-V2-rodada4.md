## BLOQUEANTE

Nenhum.

## ALTA

Nenhum.

## MÉDIA

Nenhum.

## BAIXA

Nenhum.

## Verificação das rodadas anteriores

- **Rodada 3:** o texto de A no docstring agora diz que a comparação não isola o efeito do histórico ([ml/v2_historico.py:9](ml/v2_historico.py:9)). As leituras sobre os diagnósticos estão qualificadas como hipóteses, não causas demonstradas ([scripts/gerar_notebook.py:268](scripts/gerar_notebook.py:268), [scripts/gerar_notebook.py:348](scripts/gerar_notebook.py:348)). A proveniência separa o commit do registrador do arquivo-fonte, inclui SHA-256 e registra o commit dos resultados v2 ([scripts/registrar_mlflow.py:17](scripts/registrar_mlflow.py:17), [scripts/registrar_mlflow.py:36](scripts/registrar_mlflow.py:36)). As legendas esclarecem que o texto cinza das capturas 02 e 04 é o exemplo padrão do campo de busca ([scripts/gerar_notebook.py:241](scripts/gerar_notebook.py:241), [scripts/gerar_notebook.py:543](scripts/gerar_notebook.py:543)); nas imagens, ele aparece como texto inativo.
- **Rodadas 1 e 2:** coordenadas e identificadores são excluídos de `processed/` e há teste de schema ([ml/ingestao.py:98](ml/ingestao.py:98), [tests/test_schema_processed.py:8](tests/test_schema_processed.py:8)). A seleção r2 calcula cortes sem a origem de validação; a falta de cegamento ao Teste anterior está declarada. O resultado de B é descrito como inconclusivo: a diferença primária é +0,024, com IC por célula [−0,001; 0,048] e por bloco [−0,005; 0,054], usando 9 blocos. A diferença entre cortes de seleção e finais em A, a cobertura das métricas e os limites da análise retrospectiva também estão explícitos no notebook. A comparação v2 × v1 é identificada como não sendo uma ablação; a ablação de 7 meses é apresentada separadamente.

Conferi os números do notebook com os JSON/CSV, a reconciliação e `destinos.csv`; também conferi as métricas e legendas dos quatro PNG do MLflow. Não executei scripts nem testes e não escrevi em disco.

**Veredito:** não encontrei achados ativos nesta rodada; as pendências anteriores estão corrigidas ou explicitamente limitadas no código e na documentação.