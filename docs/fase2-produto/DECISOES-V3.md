# Decisões do Nando sobre o plano v3 (registro)

Registro das respostas do Nando às decisões abertas em `docs/PLANO-EXECUCAO-V3-r2.md` §10 e no relatório do JARVIS que
a acompanhou. O plano r2 fica preservado sem edição; este arquivo é o registro posterior.

## 15/11/2026, ~21h

Pergunta do JARVIS (resumo do relatório que apresentou o plano r2):
1. partes opcionais: nenhuma, só T-A (bloco C) ou T-A + protótipo de rota (blocos C + B);
2. aditivo A, política de proximidade com `L = 3`: sim ou não.

Resposta do Nando, literal: **"1ok 2ok entra, implemente agora"**.

Interpretação do JARVIS, informada ao Nando na mesma conversa ("Interpretei o '1 ok' como as duas partes opcionais"):
- **Decisão 2 da r3 / item 2 do plano:** T-A + protótipo de rota, ou seja, **blocos C e B**.
- **Decisão 3 do plano (aditivo A):** **sim**, com `L = 3`, anel `k = 1` e cooldown de 30 min, como no plano r2 §3.
- **Implementar agora**, em 15/11 à noite, fora da ordem do cronograma (que previa o obrigatório antes), mantendo as
  regras do plano: demonstração retrospectiva exploratória, `test_seen=true`, red-team real antes do commit.

Não decidido aqui, e portanto ainda aberto:
- item 1 do plano (encaixe na arquitetura): tratado como aceito por o Nando ter mandado implementar sobre ele;
- item 4 (envio ao Abner em 18/11): **só com confirmação explícita do Nando**.

## Nome do experimento MLflow

O plano r2 §6 chama o experimento de `hoodi-v3-exploratorio`. Na implementação, o nome exibido segue a numeração
dos experimentos 1–4 já existentes: **`5 · v3 · exploratório (alerta e rotas)`**. O nome lógico do plano fica na tag
`experimento_logico=hoodi-v3-exploratorio` de cada run. É a mesma coisa com outro rótulo, escolha intencional.

## Correções pós-rodada 2 do red-team (2026-11-15)

Os dois achados BAIXA da rodada 2 (`docs/REDTEAM-IMPL-V3-rodada2.md`) foram corrigidos antes do commit:

1. `ml/rota.py::_validar` exige exatamente `(lat, lon)` por ponto e converte erro de forma ou de conversão em `RotaInvalida` (`rota_invalida`). Teste: `test_ponto_malformado_vira_rota_invalida`.
2. A média das vizinhas foi extraída para `ml/ta_descritiva.py::media_vizinhas`, usada por `escores_base`; o teste do pentágono passa a exercitar essa função (5 vizinhas, vizinha fora do universo, vizinha fora de U1).

A refatoração é equivalente: o notebook reexecutado tem as mesmas saídas (só mudam endereços de memória de objetos `Styler`). Suíte: 84 testes passando. Não houve rodada 3 de red-team só para estas duas correções.
