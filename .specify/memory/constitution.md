# Constituição do ML do hoodi

Versão 1.2.0 · ratificada em 2026-11-11 pelo Nando (Fernando Antonio) · emendada em 2026-11-11 (princípio I) e em 2026-11-12 (princípio VII), ambas por decisão do Nando · repositório separado da API .NET.

## Princípios

### I. Só dado real e oficial
Fonte, arquivo e checksum sha256 declarados. Nenhum dado simulado. O raw é imutável. Entradas mínimas escritas à mão, só em testes unitários e sem alimentar nenhum resultado, snapshot, fixture ou relatório, não contam como dado simulado.

### II. Linguagem honesta
Nunca "tempo real" nem "rota/local seguro". Usar "melhor dado disponível no período".

### III. "Sem dado" não é nível 0
Célula sem dado utilizável é "sem dado", fora da escala 0–3.

### IV. Risco vem do crime registrado
Nunca da presença de pessoas. Uma linha da base é um crime registrado, não um BO.

### V. Avaliação sem vazamento
Divisão temporal (treino jan–jul, teste ago–set). Validação cruzada só no treino. Nenhum número do relatório sem execução real.

### VI. Quarentena e idempotência
Registro malformado ou conflitante vai para a quarentena, sinalizado e não descartado. Ingestão idempotente: reexecutar não duplica nem muda o resultado.

### VII. Privacidade e confirmação humana
Nenhum campo que identifique pessoa nos derivados e nas entregas (processed, features, rótulos, snapshot, fixture, notebook, relatório, prompts); sem `bo_id`, número de BO, endereço, bairro, logradouro ou coordenada exata fora do raw/interim/quarentena. O raw público da SSP-SP e o interim ficam como cópia fiel fora do git, sem entrega, com retenção até a entrega; o inventário por camada fica em `ml/dados/README.md`. Nenhum envio ou publicação sem confirmação do Nando. Revisão red-team real (Codex CLI) antes da entrega; simulação própria não vale.

## Governança
Mudança nesta constituição exige decisão explícita do Nando e novo número de versão.
