"""Registra no MLflow (local, SQLite) os resultados JÁ GRAVADOS em ml/dados/resultados/, sem retreinar nada.
Serve para comparar execuções na interface do MLflow; a fonte da verdade continua sendo os JSON/CSV versionados.
Uso (venv isolado com mlflow==3.9.0, só biblioteca padrão + mlflow):
  ~/.venvs/hoodi-mlflow/bin/python scripts/registrar_mlflow.py   # recria mlflow/mlflow.db
  ~/.venvs/hoodi-mlflow/bin/mlflow ui --backend-store-uri sqlite:///mlflow/mlflow.db --port 5055"""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import mlflow

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "ml" / "dados" / "resultados"
DB = RAIZ / "mlflow" / "mlflow.db"
# Proveniência separada: o commit do registrador NÃO é o commit que gerou os números.
# Cada run leva o arquivo de origem, o sha256 dele e o último commit que alterou esse arquivo.
git = lambda *a: subprocess.run(["git", *a], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
COMMIT_REGISTRADOR = git("rev-parse", "--short", "HEAD")


def proveniencia(nome):
    arq = RES / nome
    return {"arquivo_fonte": f"ml/dados/resultados/{nome}", "sha256_fonte": hashlib.sha256(arq.read_bytes()).hexdigest(),
            "commit_ultima_alteracao_fonte": git("log", "-1", "--format=%h", "--", str(arq)) or "não versionado"}


def ler(nome):
    return json.loads((RES / nome).read_text())


def run(exp, nome, fonte, params=None, metricas=None, tags=None):
    mlflow.set_experiment(exp)
    with mlflow.start_run(run_name=nome):
        mlflow.set_tags({"commit_registrador": COMMIT_REGISTRADOR, "fonte": "resultados versionados (sem retreino)",
                         **proveniencia(fonte), **(tags or {})})
        if params:
            mlflow.log_params({k: str(v) for k, v in params.items()})
        if metricas:
            mlflow.log_metrics({k: float(v) for k, v in metricas.items() if v is not None})


def v1_cv():
    sel, extra = ler("selecao_modelo.json"), ler("cv_exploracao_adicional.json")
    grades = dict(sel["todas_combinacoes"], lstm=extra["lstm"], kmeans_pca=extra["kmeans_pca"])
    for modelo, combos in grades.items():
        for c in combos:
            run("1 · v1 · seleção (CV temporal)", modelo,
                "selecao_modelo.json" if modelo in sel["todas_combinacoes"] else "cv_exploracao_adicional.json", {"modelo": modelo, **c["params"]},
                {f"cv_{k}": v for k, v in c["media"].items()},
                {"modelo": modelo, "pre_registrado": str(modelo in sel["todas_combinacoes"]),
                 "vencedor": str(modelo == sel["vencedor"] and c["params"] == sel["melhores_por_candidato"][modelo]["params"])})
    for b, r in sel["baselines_cv"].items():
        run("1 · v1 · seleção (CV temporal)", b, "selecao_modelo.json", {"modelo": b}, {f"cv_{k}": v for k, v in r["media"].items()},
            {"modelo": b, "linha_de_base": "True"})


def v1_teste():
    with open(RES / "metricas_treino_teste.csv") as f:
        for r in csv.DictReader(f):
            m = {k: r[k] for k in r if k.endswith(("_treino", "_teste")) or k == "gap_macro_f1"}
            run("2 · v1 · Teste ago–set 2026", r["modelo"], "metricas_treino_teste.csv", {"modelo": r["modelo"], **json.loads(r["params"] or "{}")},
                {k: (float(v) if v not in ("", None) else None) for k, v in m.items()},
                {"exploracao_adicional": r["exploracao_adicional"]})
    ic = ler("incerteza_custo.json")
    for nome, mets in ic.get("teste", {}).items():
        run("2 · v1 · Teste ago–set 2026 (IC bootstrap)", nome, "incerteza_custo.json", {"modelo": nome},
            {**{f"{k}": v["valor"] for k, v in mets.items()}, **{f"{k}_ic_inf": v["ic95"][0] for k, v in mets.items()},
             **{f"{k}_ic_sup": v["ic95"][1] for k, v in mets.items()}})


def v2():
    v, sel = ler("v2_historico.json"), ler("selecao_v2_r2.json")
    for d in ("A_mesmo_alvo", "B_semestral"):
        for nome, mets in v[d]["teste"].items():
            run("3 · v2 · histórico 2023–2026 (Teste)", f"{d} · {nome}", "v2_historico.json", {"desenho": d, "modelo": nome},
                {**{k: x["valor"] for k, x in mets.items()}, "macro_f1_ic_inf": mets["macro_f1"]["ic95"][0],
                 "macro_f1_ic_sup": mets["macro_f1"]["ic95"][1],
                 "validacao_macro_f1": sel[d]["validacao"].get(nome, {}).get("macro_f1")},
                {"desenho": d, "modelo": nome, "vencedor_selecao": str(nome == sel[d]["vencedor"]),
                 "commit_resultados": v["commit"]["head"][:7]})
    ab = v["ablacao_historia_A"]
    for nome, mets in ab["teste"].items():
        hist, modelo = nome.split("_", 1)
        run("4 · v2 · ablação da história (desenho A)", nome, "v2_historico.json", {"historia": hist, "modelo": modelo},
            {k: x["valor"] for k, x in mets.items()}, {"historia": hist, "modelo": modelo,
                                                       "commit_resultados": v["commit"]["head"][:7]})


CONTRATOS = RAIZ / "docs" / "contratos-v3"
EXP_V3 = "5 · v3 · exploratório (alerta e rotas)"
TAGS_V3 = {"test_seen": "true", "natureza": "demonstracao", "experimento_logico": "hoodi-v3-exploratorio",
           "plano": "docs/PLANO-EXECUCAO-V3-r2.md"}


def _prov_v3(arq):
    rel = str(arq.relative_to(RAIZ))
    return {"arquivo_fonte": rel, "sha256_fonte": hashlib.sha256(arq.read_bytes()).hexdigest(),
            "commit_ultima_alteracao_fonte": git("log", "-1", "--format=%h", "--", str(arq)) or "não versionado"}


def _run_v3(nome, arq, params, metricas, artefatos, tags=None):
    if mlflow.get_experiment_by_name(EXP_V3) is None:  # artefatos dentro de mlflow/ (não versionado)
        mlflow.create_experiment(EXP_V3, artifact_location=(DB.parent / "artefatos").as_uri())
    mlflow.set_experiment(EXP_V3)
    with mlflow.start_run(run_name=nome):
        mlflow.set_tags({"commit_registrador": COMMIT_REGISTRADOR, "fonte": "artefatos versionados (sem retreino)",
                         **_prov_v3(arq), **TAGS_V3, **(tags or {})})
        mlflow.log_params({k: str(v) for k, v in params.items()})
        mlflow.log_metrics({k: float(v) for k, v in metricas.items() if v is not None})
        for a in artefatos:
            mlflow.log_artifact(str(a))


def v3():
    """Blocos A, B e C do plano v3 r2. Um run por bloco executado; nada registrado como modelo."""
    pol_arq = CONTRATOS / "politica_proximidade_v2.json"
    if pol_arq.exists():
        pol = json.loads(pol_arq.read_text())
        met = {f"L{l['L']}_fracao_chaves": l["fracao_chaves_com_dado"] for l in pol["tabela_por_L"]}
        met.update({f"L{l['L']}_fracao_pontuacao": l["fracao_pontuacao"] for l in pol["tabela_por_L"]})
        met.update({f"anel_fracao_celulas_{c['faixa_nome']}": c["fracao"] for c in pol["cobertura_anel_por_faixa"]})
        met.update({"p90_fracao_chaves": pol["sensibilidade_p90"]["fracao_chaves_com_dado"],
                    "p90_fracao_pontuacao": pol["sensibilidade_p90"]["fracao_pontuacao"]})
        _run_v3("politica_proximidade_v2", pol_arq,
                {"L": pol["L"], "k_anel": pol["k_anel"], "cooldown_min": pol["cooldown_min"], "fuso": pol["fuso"],
                 "snapshot_csv_sha256": pol["snapshot_csv_sha256"]}, met,
                [pol_arq, CONTRATOS / "politica_proximidade_v2.json.sha256"], {"bloco": "A"})
    vet_arq = CONTRATOS / "vetores_rota_v2.json"
    if vet_arq.exists():
        v = json.loads(vet_arq.read_text())
        _run_v3("rota_pontuacao_v1", vet_arq, {**v["constantes"], "h3_core_c": v["h3_core_c"], "resolucao": v["resolucao"]},
                {"n_casos": len(v["casos"]), "n_rotas_fronteira": len(v["rotas_fronteira"]),
                 "n_pontos_interiores": len(v["pontos_interiores"]), "n_pontos_fronteira": len(v["pontos_fronteira"])},
                [vet_arq, CONTRATOS / "vetores_rota_v2.json.sha256", CONTRATOS / "rota_pontuacao_v1.md"],
                {"bloco": "B", "integracao": "referência para validação; C# não testado"})
    ta_arq = RES / "ta_descritiva.json"
    if ta_arq.exists():
        t = ler("ta_descritiva.json")
        met = {}
        for un, r in t["resumo_reportadas"].items():
            for m, x in r.items():
                met[f"{un}_{m}_hit10_mediana"] = x["mediana"]
                met[f"{un}_{m}_origens_acima_persistencia"] = x["origens_acima_da_persistencia"]
        for m, x in t["ja_vista_ago_set_2026"]["universos"]["U1"]["hit_rate_10"].items():
            met[f"ja_vista_ago_set_U1_{m}_hit10"] = x
        _run_v3("ta_descritiva", ta_arq, {"lambda": t["lambda_escolhido"], "metrica": "hit rate a 10%",
                                          "universo_primario": "U1", "n_origens_reportadas": len(t["origens_reportadas"])},
                met, [ta_arq, RES / "ta_lambda.json"], {"bloco": "C", "inferencia": "nenhuma (descritiva)",
                                                        "commit_resultados": t["commit"]["head"][:7]})


if __name__ == "__main__":
    DB.parent.mkdir(exist_ok=True)
    DB.unlink(missing_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{DB}")
    v1_cv()
    v1_teste()
    v2()
    v3()
    print("ok", DB)
