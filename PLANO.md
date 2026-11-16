> **Substituído** em 2026-11-11 por `specs/001-risco-h3-faixa-horaria/` (spec, plan, tasks). Mantido só como histórico.

# Plano ML hoodi (rascunho, aguarda OK do Nando em rótulo e perímetro)
1 Qualidade do dado (feito) → 2 Rótulo/alvo → 3 Features por célula H3 res.9 × faixa → 4 Baseline → 5 Candidatos (RF, XGBoost, MLP) → 6 Busca ≥10 combinações × 3 hiperparâmetros, CV só no treino, split temporal → 7 Treino×teste + overfitting → 8 Snapshot + checksum → 9 RELATORIO_ML.md, ml/dados/README.md, requirements.txt, README com Ficha e ODS → 10 prompts.md → 11 Red-team real via Codex CLI (obrigatório) → entrega.
