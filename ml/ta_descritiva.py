"""Bloco C do plano v3 (PROPOSTA-V3-ALERTA-ROTAS-r3 §2.2): T-A descritiva — ordenação espacial para alerta.

Descritiva, sem inferência (sem IC, sem teste, sem afirmação de superioridade). Exploratória, test_seen=true.
Mês absoluto: 1 = jan/2023 … 45 = set/2026 (usadas_v2.parquet).

Alvo: pontuação da chave na janela-alvo = Σ pesos ÷ meses da janela ÷ horas da faixa (zero registrado = 0).
Escores, só com o passado: persistência, média histórica, suavizada (λ escolhido uma vez nas origens de seleção e
congelado em ta_lambda.json antes das origens reportadas) e RF regularizado walk-forward (retreinado por origem só com
rótulos que terminam antes do alvo; hiperparâmetros fixos REGULARIZADO; escore E[nível]).
Métrica: hit rate a 10% = Σ alvo das ⌈0,10·N⌉ chaves de maior escore ÷ Σ alvo das N chaves do universo.
Universos: U1 (≥1 registro pontuável na mesma faixa nos 12 meses anteriores; primário), U0 (registro na janela-alvo),
U2 (todas as células do perímetro × 5 faixas).

Uso: ~/.venvs/hoodi-ml311/bin/python -m ml.ta_descritiva
"""
import hashlib
import json
import math
import subprocess

import h3
import numpy as np
import pandas as pd

from ml import config as C
from ml import rotulo, snapshot

USADAS_V2 = C.PROCESSED / "usadas_v2.parquet"
LAMBDA_JSON = C.RESULTADOS / "ta_lambda.json"
SAIDA = C.RESULTADOS / "ta_descritiva.json"
LAMBDAS = [0.0, 0.25, 0.5, 0.75]
LARGURA = 2
SELECAO = list(range(15, 24, 2))      # alvos mar–abr/2024 … nov–dez/2024 (início do bimestre)
REPORTADAS = list(range(25, 44, 2))   # alvos jan–fev/2025 … jul–ago/2026
JA_VISTA = 44                         # ago–set/2026 (Teste da v1), reportada à parte
CURVA = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
METODOS = ["persistencia", "media_historica", "suavizada", "rf_regularizado"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def nome_janela(ini):
    a, b = ini, ini + LARGURA - 1
    return f"{MESES[(a - 1) % 12]}–{MESES[(b - 1) % 12]}/{2023 + (b - 1) // 12}"


class Base:
    """Somas de pesos e contagens pontuáveis por chave × mês (matrizes densas no universo U2)."""

    def __init__(self, u: pd.DataFrame):
        x = rotulo.com_peso(u)
        x = x[x.peso.notna()]
        uni = snapshot.universo(extras=x.celula.dropna().unique())
        self.chaves = pd.MultiIndex.from_frame(uni.rename(columns={"h3_cell": "celula"}))
        self.pos = pd.Series(np.arange(len(self.chaves)), index=self.chaves)
        nm = int(u.mes.max())
        self.S = np.zeros((len(self.chaves), nm + 1))
        self.N = np.zeros((len(self.chaves), nm + 1))
        g = x.groupby(["celula", "faixa", "mes"]).peso.agg(["sum", "size"])
        i = self.pos.loc[list(zip(g.index.get_level_values(0), g.index.get_level_values(1)))].values
        m = g.index.get_level_values(2).values
        self.S[i, m] = g["sum"].values
        self.N[i, m] = g["size"].values
        self.horas = np.array([C.FAIXA_HORAS[f] for f in self.chaves.get_level_values("faixa")], dtype=float)
        cel = self.chaves.get_level_values("celula")
        self.cel = np.asarray(cel)
        self.faixa = np.asarray(self.chaves.get_level_values("faixa"))
        # vizinhas k=1 (mesma faixa); vizinha existente fora do universo → -1 (conta 0 e entra no divisor);
        # posição inexistente (célula pentagonal tem 5 vizinhas) → -2 (fora do divisor)
        self.viz = np.full((len(self.chaves), 6), -2, dtype=int)
        for k, (c, f) in enumerate(self.chaves):
            vs = sorted(v for v in h3.grid_disk(c, 1) if v != c)
            for j, v in enumerate(vs):
                self.viz[k, j] = self.pos.get((v, f), -1)
        self.n_viz = (self.viz != -2).sum(axis=1)

    def pont(self, meses):
        meses = list(meses)
        return self.S[:, meses].sum(axis=1) / len(meses) / self.horas

    def tem(self, meses):
        return self.N[:, list(meses)].sum(axis=1) > 0


def universos(b: Base, ini):
    alvo = range(ini, ini + LARGURA)
    return {"U1": b.tem(range(ini - 12, ini)), "U0": b.tem(alvo), "U2": np.ones(len(b.chaves), bool)}


def media_vizinhas(viz, n_viz, hist, u1):
    """Média k=1 da mesma faixa: vizinha fora do universo (-1) ou fora de U1 conta 0 e entra no divisor;
    posição inexistente (-2, pentágono) fica fora do divisor."""
    idx = np.clip(viz, 0, None)
    return np.where(viz >= 0, hist[idx] * u1[idx], 0.0).sum(axis=1) / n_viz


def escores_base(b: Base, ini, u1, lam):
    hist = b.pont(range(1, ini))
    viz = media_vizinhas(b.viz, b.n_viz, hist, u1)
    return dict(persistencia=b.pont(range(ini - LARGURA, ini)), media_historica=hist,
                suavizada=(1 - lam) * hist + lam * viz), hist


def hit_rate(alvo, escore, hist, cel, faixa, frac=0.10):
    """Desempate: média histórica (maior primeiro) e depois id H3 crescente, faixa crescente."""
    n = len(alvo)
    tot = alvo.sum()
    if n == 0 or tot <= 0:
        return None
    k = math.ceil(frac * n)
    ordem = np.lexsort((faixa, cel, -hist, -escore))
    return float(alvo[ordem[:k]].sum() / tot)


def rf_escore(u, b: Base, ini, cache):
    """RF regularizado retreinado na origem: rótulos bimestrais (passo 1, primeiro rótulo no mês 13) que terminam
    antes de `ini`; cortes = quartis desses rótulos; variáveis do desenho A da v2 (construir_v2), todas calculadas só
    com meses < início de cada rótulo. Escore = Σ k·P(nível=k). Chave sem variável (nenhum registro na história) → 0."""
    from ml.diagnostico_rf import _rf
    from ml.incerteza_custo import REGULARIZADO
    from ml.v2_historico import construir_v2, cortes_quartis, exemplos_v2
    janelas = [list(range(m, m + LARGURA)) for m in range(13, ini - LARGURA + 1)]
    cortes = cortes_quartis(u, janelas)
    Xs, ys = [], []
    for j in janelas:
        X, y, _ = exemplos_v2(u, j, cortes, 7)
        Xs.append(X)
        ys.append(y)
    Xtr, ytr = pd.concat(Xs), pd.concat(ys)
    m = _rf(REGULARIZADO).fit(Xtr.values, ytr.values)
    ate = ini - 1
    Xo = construir_v2(u, ate, list(range(ate - 6, ate + 1)), [ini - 12, ini - 11])
    Xo = Xo.reindex(b.chaves).fillna(0.0)[Xtr.columns]
    proba = m.predict_proba(Xo.values)
    esc = proba @ m.classes_.astype(float)
    return esc, dict(cortes=cortes, n_treino=int(len(Xtr)), n_janelas_treino=len(janelas),
                     classes=[int(c) for c in m.classes_])


def avaliar_origem(u, b, ini, lam, com_rf=True):
    us = universos(b, ini)
    alvo = b.pont(range(ini, ini + LARGURA))
    esc, hist = escores_base(b, ini, us["U1"], lam)
    meta = {}
    if com_rf:
        esc["rf_regularizado"], meta = rf_escore(u, b, ini, None)
    out = dict(janela_alvo=nome_janela(ini), meses_alvo=[ini, ini + LARGURA - 1], rf=meta, universos={})
    for nome, mask in us.items():
        r = dict(n_chaves=int(mask.sum()), soma_alvo=float(alvo[mask].sum()), hit_rate_10={}, curva={})
        for met, e in esc.items():
            args = (alvo[mask], e[mask], hist[mask], b.cel[mask], b.faixa[mask])
            r["hit_rate_10"][met] = hit_rate(*args)
            r["curva"][met] = {f"{int(f * 100)}%": hit_rate(*args, frac=f) for f in CURVA}
        out["universos"][nome] = r
    return out


def escolher_lambda(u, b):
    medias = {}
    for lam in LAMBDAS:
        hs = [avaliar_origem(u, b, ini, lam, com_rf=False)["universos"]["U1"]["hit_rate_10"]["suavizada"]
              for ini in SELECAO]
        hs = [h for h in hs if h is not None]
        medias[str(lam)] = float(np.mean(hs))
    melhor = max(medias.values())
    lam = min(l for l in LAMBDAS if math.isclose(medias[str(l)], melhor, rel_tol=0, abs_tol=1e-12))
    return dict(lambda_escolhido=lam, media_hit_rate_10_U1_por_lambda=medias,
                origens_selecao=[nome_janela(i) for i in SELECAO],
                regra="maior hit rate a 10% médio em U1 nas origens de seleção; empate → menor λ",
                nota="congelado antes de calcular qualquer origem reportada (r3 §2.2)")


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _commit():
    g = lambda *a: subprocess.run(["git", *a], cwd=C.RAIZ, capture_output=True, text=True).stdout.strip()
    return dict(head=g("rev-parse", "HEAD"),
                codigo_alterado_sem_commit=bool(g("status", "--porcelain", "--", "ml", "scripts", ":(exclude)ml/dados")))


def resumo(origens):
    out = {}
    for un in ("U1", "U0", "U2"):
        base = [o["universos"][un]["hit_rate_10"]["persistencia"] for o in origens]
        out[un] = {}
        for m in METODOS:
            vs = [o["universos"][un]["hit_rate_10"].get(m) for o in origens]
            ok = [v for v in vs if v is not None]
            out[un][m] = dict(mediana=float(np.median(ok)), minimo=float(min(ok)), maximo=float(max(ok)),
                              origens_acima_da_persistencia=int(sum(1 for v, p in zip(vs, base)
                                                                    if v is not None and p is not None and v > p)),
                              n_origens=len(ok))
    return out


def main():
    u = pd.read_parquet(USADAS_V2)
    b = Base(u)
    sel = escolher_lambda(u, b)
    if LAMBDA_JSON.exists():
        assert json.loads(LAMBDA_JSON.read_text()) == json.loads(json.dumps(sel)), "ta_lambda.json diverge"
    else:
        LAMBDA_JSON.write_text(json.dumps(sel, ensure_ascii=False, indent=2) + "\n")
    lam = sel["lambda_escolhido"]
    reportadas = [avaliar_origem(u, b, ini, lam) for ini in REPORTADAS]
    vista = avaliar_origem(u, b, JA_VISTA, lam)
    saida = dict(
        natureza="T-A descritiva, exploratória (test_seen=true); sem IC, sem teste de hipótese, sem afirmação de "
                 "superioridade. Universos são filtros de registro anterior, não medidas de cobertura da coleta.",
        commit=_commit(), usadas_v2_sha256=_sha(USADAS_V2), ta_lambda_sha256=_sha(LAMBDA_JSON),
        lambda_escolhido=lam,
        ressalva_rf=("hiperparâmetros REGULARIZADO escolhidos em 15/11 depois de ver ago–set/2026: RF é exploratório e "
                     "não sustenta superioridade sobre as linhas de base"),
        desempate="média histórica (maior primeiro), depois id H3 crescente e faixa crescente",
        origens_reportadas=reportadas, resumo_reportadas=resumo(reportadas),
        ja_vista_ago_set_2026=vista,
    )
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n")
    return saida


if __name__ == "__main__":
    s = main()
    print("λ =", s["lambda_escolhido"])
    for un, r in s["resumo_reportadas"].items():
        print(un, {m: (round(v["mediana"], 3), f'{v["origens_acima_da_persistencia"]}/{v["n_origens"]}')
                   for m, v in r.items()})
    print("ago–set/2026 U1:", {m: round(v, 3) for m, v in s["ja_vista_ago_set_2026"]["universos"]["U1"]["hit_rate_10"].items()})
