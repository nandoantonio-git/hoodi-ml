# Red-team Codex CLI (real), 2026-11-18

Duas passadas (privacidade/itens rastreados; código do snapshot v3). Achados corrigidos em 7e6acce. RT-01 (histórico Git antigo) não se aplica ao repositório público, que tem histórico novo.

## Passada 1
## Achados

| ID | Severidade | Arquivo:linha | Evidência | Impacto | Correção | Fato ou hipótese |
|---|---|---|---|---|---|---|
| RT-01 | P1 | `docs/DECISAO-PRIVACIDADE-SNAPSHOT-V2.md:66` | O documento registra que um snapshot removido, com chaves H3 × faixa horária de baixa contagem, permanece na ancestralidade do Git. Confirmei que o commit citado contém o arquivo e é ancestral de `HEAD`. | Publicar o histórico pode expor associações de local e horário capazes de facilitar a identificação de ocorrências. | Reescrever o histórico antes da publicação ou publicar um histórico novo contendo apenas artefatos saneados; revisar também as branches que serão publicadas. | Fato documentado e presença do arquivo histórico confirmada; o risco de identificação é inferência. |
| RT-02 | P2 | `ml/dados/resultados/classificacao_zonas.txt:32` | Saída versionada contém um caminho absoluto local, com diretórios pessoais e nome de usuário. | Expõe detalhes da máquina e do ambiente de trabalho. | Regenerar ou editar a saída para remover o caminho local e manter apenas informação reproduzível, como caminho relativo ou aviso sem caminho. | Fato. |
| RT-03 | P2 | `ml/dados/resultados/rubricas_sem_peso.csv:9` | O CSV agrega registros por rubrica, mas cinco linhas têm contagens abaixo de três. Não encontrei nelas chaves espaciais ou temporais. | Pode revelar a raridade de categorias de ocorrência; a evidência disponível não associa essas linhas a um local ou horário específico. | Suprimir contagens abaixo de três ou combinar categorias raras antes de publicar. | Fato quanto às contagens; possível impacto de inferência é hipótese. |

## Verificações sem achado impeditivo

Não encontrei, nos arquivos rastreados atuais, valores de boletins com nomes, documentos, contatos, endereço completo, número de BO, narrativa ou coordenadas individuais, nem segredos ou arquivos `.env`. Também não encontrei dumps, Parquet, arquivos de quarentena ou diretórios de execuções MLflow rastreados. Nos cinco CSVs de snapshots, as linhas `com_dado` passam o limiar de três; as linhas `sem_dado` têm contagem zero e sem pontuação ou nível.

A ocorrência de “tranquilo” no notebook está negada: diz que `sem_dado` nunca é tratado dessa forma. Não encontrei uso de “Tamagotchi”, promessa de tempo real ou previsão futura para o produto, nem menção a vídeo na documentação. A Ficha do README foi ignorada conforme instruído.

## Veredito

**NÃO PUBLICAR.** Primeiro, saneie a ancestralidade do Git para remover o snapshot de baixa contagem. Também recomendo limpar o caminho local e suprimir as contagens raras no CSV de rubricas.
## Passada 2
**Veredito: PUBLICAR APÓS CORRIGIR.** Não encontrei vazamento confirmado de dado pessoal. O hash e as contagens do CSV publicado conferem, e as linhas `sem_dado` não expõem contagem, nível ou pontuação.

| ID | P0/P1/P2 | arquivo:linha | evidência | impacto | correção | fato ou hipótese |
|---|---|---|---|---|---|---|
| R1 | P1 | [ml/snapshot_semestral.py](ml/snapshot_semestral.py:20); [ml/snapshot_v3_contrato.py](ml/snapshot_v3_contrato.py:47) | `FIMS_TREINO = range(6, 40, 3)` inclui fim no índice 39, março/2026. O contrato diz que os cortes usam janelas até dezembro/2025 e “sem 2026”; `snapshot_v3_contrato.main()` chama essa rotina ao gerar o contrato. | Os níveis publicados podem refletir dados de jan–mar/2026 apesar de o contrato declarar que 2026 foi excluído. | Se a regra pretendida termina em dez/2025, limitar a faixa de treino e regenerar snapshot, manifest e derivados; caso contrário, corrigir a documentação e o contrato. | **Fato**: o índice 39 corresponde a mar/2026 e está incluído. |
| R2 | P2 | [ml/snapshot_semestral.py](ml/snapshot_semestral.py:34) | `montar(..., cortes=None)` encaminha `cortes` diretamente a `rotulo.nivel()` (linha 46), que tenta convertê-lo em lista. Não há cálculo de cortes quando o argumento é omitido. | Chamar `montar(u)` falha em vez de produzir snapshot; o caminho principal evita isso porque passa cortes explicitamente. | Calcular cortes quando `cortes is None` ou tornar o argumento obrigatório. | **Fato** pelo fluxo do código. |

**Verificações:** o SHA-256 calculado do CSV é `e33bd004ffcf0c47378ef0c9518bdf19a9ea84ca007222d798a2003a7c71c0da`, igual ao manifest. O CSV tem 824 `com_dado` e 571 `sem_dado`; todas as chaves publicadas com dados têm `n_registros >= 3`, e as `sem_dado` têm contagem zero, nível vazio e pontuação vazia. A regra de proximidade seleciona apenas chaves `com_dado` e declara que `sem_dado` nunca dispara nem é exibido como seguro. Não encontrei afirmações positivas de segurança, previsão ou tempo real nos arquivos revisados.

`rota.py` não grava entradas de usuário em logs. Porém, erros de validação incluem o ponto recebido na mensagem da exceção ([ml/rota.py](ml/rota.py:54)); se um chamador registrar essa exceção, coordenadas ou texto malformado podem parar em logs. Isso é um risco hipotético. Os vetores de rota persistem coordenadas sintéticas de teste, não entradas fornecidas por usuários.

O CI instala dependências especificadas e testa artefatos versionados sem exigir a base bruta da SSP-SP. **Não rodei `python3 -m pytest -q`**: o ambiente somente leitura não disponibilizou diretório temporário gravável, necessário para o capture do pytest.