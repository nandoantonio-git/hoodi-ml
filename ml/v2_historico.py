"""v2 — histórico SSP-SP 2023 a set/2026 (exploração adicional; a v1 pré-registrada não muda).

Motivo (revisão de 15/11): a repetibilidade do rótulo v1 entre bimestres, sem modelo, é ~0,49 de macro-F1 (referência,
não limite superior) porque cada chave tem mediana de 3 registros no bimestre do rótulo. Mais anos dão mais registros.

Mês absoluto: 1 = jan/2023 … 45 = set/2026. O resto reaproveita rotulo/features da v1 (que recebem listas de meses).

Dois desenhos, ambos com seleção em validação temporal (selecao_v2_r2.json):
  A. mesmo alvo da v1: rótulo ago–set/2026 com os cortes da v1 → mesmas chaves e mesmos rótulos que a v1,
     comparação pareada nas mesmas chaves e rótulos do Teste. NÃO isola o efeito do histórico: mudam também
     variáveis extras, origens e tamanho do treino. O efeito do histórico é isolado só na ablação
     (`ablacao_historia_A`: mesmas origens e cortes, história visível de 7 meses).
  B. alvo semestral: rótulo abr–set/2026 (6 meses), cortes do treino; menos ruído no rótulo.
Ressalva: ago–set/2026 já foi visto na v1; tudo aqui é exploração adicional.

Revisão r2 (red-team Codex de 15/11): na r1 (selecao_v2.json, preservado) os cortes usados na seleção incluíam a
própria origem de validação. Na r2 os cortes da seleção vêm só das origens de treino da seleção. A r2 foi feita
depois de o Teste da r1 ter sido visto: o critério é o mesmo e só usa a validação, mas não é cego ao Teste.
Comparação primária, fixada na r2: vencedor da seleção − persistência da história (macro-F1). As demais são
secundárias, com IC de Bonferroni para a família.
"""
import hashlib
import json
import os
import subprocess

os.environ.setdefault("OMP_NUM_THREADS", "1")
import torch  # noqa: F401 — antes do xgboost (ver modelos.py)

import numpy as np
import pandas as pd

from ml import config as C
from ml import features, ingestao, rotulo
from ml import modelos as M
from ml.diagnostico_rf import BASE, _rf
from ml.incerteza_custo import REGULARIZADO, bootstrap, diferencas, metricas, resumo_ic
from ml.sequenciais import KMeansPCANivel

SERIAL_2023_01_01 = 44927
JANELA = (SERIAL_2023_01_01, C.SERIAL_2026_09_30)
ANOS = [2023, 2024, 2025]
USADAS_V2 = C.PROCESSED / "usadas_v2.parquet"
MES_TESTE_A = [44, 45]                 # ago–set/2026
MES_TESTE_B = list(range(40, 46))      # abr–set/2026


# ---------------------------------------------------------------- ingestão
def ingerir():
    import duckdb
    cols = ", ".join(ingestao.CHAVE_DUP)
    fontes = [f"{a}_{s}" for a in ANOS for s in ("jan_jun", "jul_dez")] + ["jan_jun", "jul_dez"]
    partes = [f"select '{n}' as fonte, row_number() over () as linha, {cols} from '{C.INTERIM / n}.parquet'"
              for n in fontes]
    df = duckdb.sql(" union all ".join(partes)).df()
    d = ingestao.classificar(df, janela=JANELA)
    rec = ingestao.reconciliar(d)
    u = ingestao.saida_usadas(d)
    data = pd.Timestamp("1899-12-30") + pd.to_timedelta(u.data_fato, unit="D")
    u["mes"] = (data.dt.year - 2023) * 12 + data.dt.month
    u.to_parquet(USADAS_V2, index=False)
    por_ano = u.assign(ano=data.dt.year).groupby("ano").size()
    pontuaveis = u.rubrica.map(C.peso_rubrica).notna().groupby(data.dt.year).mean()
    motivos = d.groupby(["destino", "motivo"]).size()
    linhas = ["Reconciliação v2 (2023-01-01 a 2026-09-30, mesmo perímetro e mesmas regras da v1)", ""]
    linhas += [f"{k}: {v}" for k, v in rec.items()]
    linhas += ["", "destino/motivo:"] + [f"  {a}/{b or '-'}: {n}" for (a, b), n in motivos.items()]
    linhas += ["", "usadas por ano do fato / fração com peso (pontuáveis):"]
    linhas += [f"  {a}: {por_ano[a]} / {pontuaveis[a]:.3f}" for a in por_ano.index]
    (C.DADOS / "reconciliacao_v2.txt").write_text("\n".join(linhas) + "\n")
    return u, rec


# ---------------------------------------------------------------- variáveis
def _janela(u, meses, prefixo):
    X = features.construir(u, meses)[["taxa_registros", "taxa_pontuacao", "pont_vizinhas"]]
    return X.add_prefix(prefixo)


def construir_v2(u, ate, recente, sazonal, historia=None):
    """Base = COLUNAS_X da v1 sobre toda a história (meses 1..ate); extras: janela recente, últimos 12 meses
    e mesmo período do ano anterior. Chaves = as com registro pontuável na história."""
    ini = 1 if historia is None else max(1, ate - historia + 1)  # historia = nº de meses visíveis (ablação)
    hist = list(range(ini, ate + 1))
    X = features.construir(u, hist)
    for meses, p in ((recente, "rec_"), (list(range(max(1, ate - 11), ate + 1)), "u12_"), (sazonal, "saz_")):
        X = X.join(_janela(u, [m for m in meses if ini <= m <= ate], p), how="left")
    return X.fillna(0.0)


def exemplos_v2(u, rotulo_meses, cortes, n_recente, historia=None):
    ini = rotulo_meses[0]
    ate = ini - 1
    X = construir_v2(u, ate, list(range(ate - n_recente + 1, ate + 1)), [m - 12 for m in rotulo_meses], historia)
    y_pont = rotulo.pontuacao_mensal(rotulo.agregar(u, rotulo_meses), len(rotulo_meses))
    comum = X.index.intersection(y_pont.index)
    sem_rotulo = X.index.difference(y_pont.index)
    y = rotulo.nivel(y_pont.loc[comum], cortes).astype(int)
    return X.loc[comum].sort_index(), y.sort_index(), X.loc[sem_rotulo].sort_index()


def origens(primeiro_rotulo, ultimo_ini, largura, passo):
    return [list(range(m, m + largura)) for m in range(primeiro_rotulo, ultimo_ini + 1, passo)]


def cortes_quartis(u, janelas):
    p = pd.concat([rotulo.pontuacao_mensal(rotulo.agregar(u, j), len(j)) for j in janelas])
    return [float(v) for v in np.quantile(p.values, [0.25, 0.5, 0.75])]


def montar(u, janelas, cortes, n_recente, historia=None):
    partes = [exemplos_v2(u, j, cortes, n_recente, historia) for j in janelas]
    return pd.concat([p[0] for p in partes]), pd.concat([p[1] for p in partes])


# ---------------------------------------------------------------- modelos
def candidatos(kmeans_params):
    return {
        "rf_regularizado": lambda: _rf(REGULARIZADO),
        "rf_original": lambda: _rf(BASE),
        "kmeans_pca": lambda: KMeansPCANivel(**kmeans_params),
    }


def _mat(nome, X):
    return X if nome == "kmeans_pca" else X.values


def persistencias(X, cortes):
    return {"base_persistencia_historia": rotulo.nivel(X.taxa_pontuacao, cortes).astype(int).values,
            "base_persistencia_recente": rotulo.nivel(X.rec_taxa_pontuacao, cortes).astype(int).values}


def ajustar_prever(cands, Xtr, ytr, Xs):
    out, modelos = {}, {}
    for nome, f in cands.items():
        m = f().fit(_mat(nome, Xtr), ytr.values)
        modelos[nome] = m
        out[nome] = [np.asarray(m.predict(_mat(nome, X))) for X in Xs]
    return out, modelos


DESENHOS = {
    # rótulo bimestral; origens de treino com rótulo de jan/2024 em diante (12 meses de história mínima)
    "A_mesmo_alvo": dict(largura=2, passo=1, primeiro=13, n_recente=7, teste=MES_TESTE_A),
    # rótulo semestral; origens a cada 3 meses
    "B_semestral": dict(largura=6, passo=3, primeiro=13, n_recente=6, teste=MES_TESTE_B),
}


def desenho(u, u_v1, nome, cfg, kmeans_params):
    L, teste = cfg["largura"], cfg["teste"]
    ini_teste = teste[0]
    # treino final: rótulo termina antes do rótulo do Teste
    treino = origens(cfg["primeiro"], ini_teste - L, L, cfg["passo"])
    # validação de seleção: a última origem do treino; o treino da seleção expurga rótulos que a tocam
    val = treino[-1]
    treino_sel = [j for j in treino if j[-1] < val[0]]
    # cortes da seleção: só origens de treino da seleção (nunca a validação). Cortes finais: A herda os da v1
    # (ajustados em jan–jul/2026, antes do Teste ago–set) para a comparação pareada; B usa todas as origens de treino.
    cortes_sel = cortes_quartis(u, treino_sel)
    cortes = rotulo.cortes_treino(u_v1) if nome == "A_mesmo_alvo" else cortes_quartis(u, treino)
    cands = candidatos(kmeans_params)

    # 1) seleção (só treino da seleção + validação)
    Xs, ys = montar(u, treino_sel, cortes_sel, cfg["n_recente"])
    Xv, yv, _ = exemplos_v2(u, val, cortes_sel, cfg["n_recente"])
    pv, _ = ajustar_prever(cands, Xs, ys, [Xv])
    sel = {k: metricas(yv.values, v[0]) for k, v in pv.items()}
    sel.update({k: metricas(yv.values, p) for k, p in persistencias(Xv, cortes_sel).items()})
    vencedor = max(cands, key=lambda k: sel[k]["macro_f1"])
    registro = dict(desenho=nome, cortes_selecao=cortes_sel, cortes_finais=cortes,
                    origens_treino_selecao=[[j[0], j[-1]] for j in treino_sel],
                    origem_validacao=[val[0], val[-1]], n_validacao=int(len(yv)), validacao=sel, vencedor=vencedor,
                    parametros=dict(semente=C.SEMENTE, rf_regularizado=REGULARIZADO, rf_original=BASE,
                                    kmeans_pca=kmeans_params, **{k: cfg[k] for k in ("largura", "passo", "primeiro",
                                                                                      "n_recente", "teste")}),
                    regra="maior macro-F1 na origem de validação",
                    comparacao_primaria=f"{vencedor} − base_persistencia_historia (macro-F1, Teste)")
    return registro, (treino, cortes, cands)


def _blocos(celulas, res=7):
    import h3
    return np.array([h3.cell_to_parent(c, res) for c in celulas])


def avaliar_teste(u, nome, cfg, treino, cortes, cands, vencedor):
    Xtr, ytr = montar(u, treino, cortes, cfg["n_recente"])
    Xte, yte, Xsem = exemplos_v2(u, cfg["teste"], cortes, cfg["n_recente"])
    prev, modelos = ajustar_prever(cands, Xtr, ytr, [Xte, Xsem])
    p_te = {k: v[0] for k, v in prev.items()}
    p_sem = {k: v[1] for k, v in prev.items()}
    for k, p in persistencias(Xte, cortes).items():
        p_te[k] = p
    for k, p in persistencias(Xsem, cortes).items():
        p_sem[k] = p
    y = yte.values
    celulas = np.asarray(Xte.index.get_level_values("celula"))
    pontual = {k: metricas(y, p) for k, p in p_te.items()}
    boot = bootstrap(y, p_te, celulas)
    primaria = [(vencedor, "base_persistencia_historia")]
    secundarias = [(c, b) for c in cands for b in ("base_persistencia_historia", "base_persistencia_recente")
                   if (c, b) not in primaria]
    secundarias += [(a, b) for i, a in enumerate(cands) for b in list(cands)[i + 1:]]
    secundarias += [("base_persistencia_historia", "base_persistencia_recente")]
    blocos = _blocos(celulas)
    boot_b = bootstrap(y, {k: p_te[k] for k in {a for par in primaria for a in par}}, blocos)
    out = dict(n_treino=int(len(Xtr)), n_teste=int(len(y)), n_celulas_teste=int(len(np.unique(celulas))),
               n_chaves_sem_rotulo=int(len(Xsem)),
               mediana_registros_rotulo=float(rotulo.agregar(u, cfg["teste"]).n.loc[Xte.index].median()),
               distribuicao_treino={int(k): int(v) for k, v in ytr.value_counts().sort_index().items()},
               distribuicao_teste={int(k): int(v) for k, v in yte.value_counts().sort_index().items()},
               escopo="métricas só sobre chaves com registro pontuável no período do alvo; chaves sem rótulo "
                      "(n_chaves_sem_rotulo) ficam fora e aparecem em alerta_em_chave_sem_rotulo",
               teste=resumo_ic(boot, pontual),
               comparacao_primaria=dict(celula_res9=diferencas(boot, primaria),
                                        bloco_res7=diferencas(boot_b, primaria),
                                        n_blocos_res7=int(len(np.unique(blocos)))),
               diferencas_secundarias=diferencas(boot, secundarias, n_familia=len(secundarias)),
               alerta_em_chave_sem_rotulo={k: float((np.asarray(p) >= 2).mean()) for k, p in p_sem.items()})
    return out, (Xte, yte, p_te), modelos


def comparacao_v1(Xte_a, yte_a, p_te_a):
    """Desenho A × v1 nas MESMAS chaves (as 847 da v1): mesmo rótulo, pareado."""
    from ml.incerteza_custo import M as _M  # noqa: F401
    u1 = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    selecao = json.loads((C.RESULTADOS / "selecao_modelo.json").read_text())
    extra_cv = json.loads((C.RESULTADOS / "cv_exploracao_adicional.json").read_text())
    _, _, (Xtr1, ytr1, Xte1, yte1), prev1, _ = M.avaliar_final(u1, selecao, extra_cv)
    rf1 = _rf(REGULARIZADO).fit(M._matriz(Xtr1), ytr1.values)
    v1 = {"v1_rf_regularizado": rf1.predict(M._matriz(Xte1)), "v1_rf_original": np.asarray(prev1["random_forest"]),
          "v1_persistencia": np.asarray(prev1["base_persistencia"]),
          "v1_kmeans_pca": np.asarray(prev1["kmeans_pca"])}
    idx1 = Xte1.index
    pos = pd.Series(np.arange(len(Xte_a)), index=Xte_a.index)
    comum = idx1.intersection(Xte_a.index)
    i1 = pd.Series(np.arange(len(idx1)), index=idx1).loc[comum].values
    ia = pos.loc[comum].values
    assert (yte1.values[i1] == yte_a.values[ia]).all(), "rótulo do desenho A deveria ser idêntico ao da v1"
    prev = {k: v[i1] for k, v in v1.items()}
    prev.update({f"v2_{k}": np.asarray(v)[ia] for k, v in p_te_a.items()})
    y = yte1.values[i1]
    cel = np.asarray(comum.get_level_values("celula"))
    boot = bootstrap(y, prev, cel)
    pontual = {k: metricas(y, p) for k, p in prev.items()}
    pares = [("v2_rf_regularizado", "v1_rf_regularizado"), ("v2_rf_original", "v1_rf_original"),
             ("v2_kmeans_pca", "v1_kmeans_pca"), ("v2_base_persistencia_historia", "v1_persistencia")]
    return dict(n_chaves_comuns=int(len(comum)), n_chaves_v1=int(len(idx1)),
                leitura="mesmas chaves e mesmos rótulos no Teste; muda o pipeline inteiro (história nas variáveis, variáveis "
                        "extras, origens e tamanho do treino). Não é ablação do histórico (ver ablacao_historia_A). "
                        "IC que cruza zero = inconclusivo (não demonstra ausência de efeito)",
                teste=resumo_ic(boot, pontual), diferencas_pareadas=diferencas(boot, pares, n_familia=len(pares)))


HISTORIA_CURTA = 7  # meses visíveis, como a v1 no Teste (jan–jul/2026)


def ablacao_historia(u, cfg, treino, cortes, cands, Xte_longa, p_longa):
    """Ablação do desenho A: MESMAS origens de treino, cortes e candidatos; só a história visível nas variáveis cai
    para HISTORIA_CURTA meses antes de cada rótulo (janelas u12_/saz_ truncadas a ela). Isola o comprimento da
    história, ao contrário da comparação A × v1 (que também muda origens e tamanho do treino). Pareada nas chaves
    comuns do Teste."""
    Xtr, ytr = montar(u, treino, cortes, cfg["n_recente"], HISTORIA_CURTA)
    Xte, yte, _ = exemplos_v2(u, cfg["teste"], cortes, cfg["n_recente"], HISTORIA_CURTA)
    prev, _ = ajustar_prever(cands, Xtr, ytr, [Xte])
    comum = Xte.index.intersection(Xte_longa.index)
    ic = pd.Series(np.arange(len(Xte)), index=Xte.index).loc[comum].values
    il = pd.Series(np.arange(len(Xte_longa)), index=Xte_longa.index).loc[comum].values
    y = yte.values[ic]
    pv = {f"curta_{k}": np.asarray(v[0])[ic] for k, v in prev.items()}
    pv.update({f"longa_{k}": np.asarray(p_longa[k])[il] for k in cands})
    cel = np.asarray(comum.get_level_values("celula"))
    boot = bootstrap(y, pv, cel)
    pares = [(f"longa_{k}", f"curta_{k}") for k in cands]
    return dict(historia_curta_meses=HISTORIA_CURTA, n_treino_curta=int(len(Xtr)), n_teste_curta=int(len(yte)),
                n_chaves_comuns=int(len(comum)),
                leitura="longa − curta > 0 favorece mais história; IC que cruza zero = inconclusivo",
                teste=resumo_ic(boot, {k: metricas(y, p) for k, p in pv.items()}),
                diferencas_pareadas=diferencas(boot, pares, n_familia=len(pares)))


def repetibilidade_semestral(u):
    """Repetibilidade do rótulo semestral sem modelo: semestre anterior → seguinte, cortes do anterior, só chaves
    com rótulo nos dois. NÃO é teto nem é comparável ao Teste B (cortes e elegibilidade diferentes); a linha de base
    comparável é base_persistencia_* no próprio Teste B."""
    from sklearn.metrics import f1_score
    out = {}
    for a, b in [(list(range(28, 34)), list(range(34, 40))), (list(range(34, 40)), list(range(40, 46))),
                 (list(range(31, 37)), list(range(37, 43)))]:
        sa = rotulo.pontuacao_mensal(rotulo.agregar(u, a), 6)
        sb = rotulo.pontuacao_mensal(rotulo.agregar(u, b), 6)
        cortes = list(np.quantile(sa, [.25, .5, .75]))
        k = sa.index.intersection(sb.index)
        ya, yb = np.digitize(sa[k], cortes), np.digitize(sb[k], cortes)
        out[f"meses {a[0]}-{a[-1]} → {b[0]}-{b[-1]}"] = dict(
            macro_f1=float(f1_score(yb, ya, average="macro")), exata=float((ya == yb).mean()), n=int(len(k)))
    return out


def _sha(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def manifesto():
    """sha256 dos Parquets intermediários e processados que alimentam esta execução."""
    arqs = sorted(C.INTERIM.glob("*.parquet")) + sorted(C.PROCESSED.glob("*.parquet"))
    return {str(a.relative_to(C.DADOS)): _sha(a) for a in arqs}


def _commit():
    def git(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, cwd=C.RAIZ).stdout.strip()
    return dict(head=git("rev-parse", "HEAD"),
                codigo_alterado_sem_commit=bool(git("status", "--porcelain", "--", "ml", "scripts", "tests",
                                                    ":(exclude)ml/dados")))


def main():
    u = pd.read_parquet(USADAS_V2) if USADAS_V2.exists() else ingerir()[0]
    u_v1 = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    extra_cv = json.loads((C.RESULTADOS / "cv_exploracao_adicional.json").read_text())
    kp = M.melhor(extra_cv["kmeans_pca"])["params"]

    # seleção de todos os desenhos gravada antes de qualquer Teste
    registros, preparos = {}, {}
    for nome, cfg in DESENHOS.items():
        registros[nome], preparos[nome] = desenho(u, u_v1, nome, cfg, kp)
    alvo = C.RESULTADOS / "selecao_v2_r2.json"
    if alvo.exists():
        antigo = json.loads(alvo.read_text())
        assert antigo == json.loads(json.dumps(registros)), "selecao_v2_r2.json diverge da seleção recalculada"
    else:
        alvo.write_text(json.dumps(registros, ensure_ascii=False, indent=2) + "\n")

    saida = dict(nota="exploração adicional v2 (histórico 2023–2026); a seleção pré-registrada da v1 não muda",
                 revisao="r2: seleção com cortes sem a validação (selecao_v2_r2.json); r1 preservada em "
                         "selecao_v2.json como histórico (cortes da seleção incluíam a validação)",
                 commit=_commit(), manifesto_dados=manifesto(),
                 repetibilidade_semestral_sem_modelo=repetibilidade_semestral(u))
    for nome, cfg in DESENHOS.items():
        treino, cortes, cands = preparos[nome]
        res, (Xte, yte, p_te), _ = avaliar_teste(u, nome, cfg, treino, cortes, cands, registros[nome]["vencedor"])
        res["vencedor_selecao"] = registros[nome]["vencedor"]
        res["cortes"] = cortes
        saida[nome] = res
        if nome == "A_mesmo_alvo":
            saida["A_vs_v1_mesmas_chaves"] = comparacao_v1(Xte, yte, p_te)
            saida["ablacao_historia_A"] = ablacao_historia(u, cfg, treino, cortes, cands, Xte, p_te)
    (C.RESULTADOS / "v2_historico.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n")
    return saida


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["ingerir"]:
        print(ingerir()[1])
    else:
        s = main()
        for nome in ("A_mesmo_alvo", "B_semestral"):
            print("==", nome, "vencedor:", s[nome]["vencedor_selecao"], "n_teste", s[nome]["n_teste"])
            for k, v in s[nome]["teste"].items():
                print(f"  {k:30s} F1 {v['macro_f1']['valor']:.3f} {[round(x, 3) for x in v['macro_f1']['ic95']]}"
                      f"  sub {v['taxa_subestimacao']['valor']:.3f}  rec_alto {v['recall_risco_alto']['valor']:.3f}")
            print(json.dumps(s[nome]["comparacao_primaria"], ensure_ascii=False)[:1500])
        for b in ("A_vs_v1_mesmas_chaves", "ablacao_historia_A"):
            print(b, json.dumps({k: v["macro_f1"] for k, v in s[b]["diferencas_pareadas"].items()}, ensure_ascii=False))
