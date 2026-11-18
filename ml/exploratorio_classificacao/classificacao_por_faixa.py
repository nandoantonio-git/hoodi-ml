"""EXPLORATÓRIO: mesma tarefa de classificacao_zonas.py, estratificada (a) por faixa de EVIDÊNCIA (nº de registros pontuáveis
no contexto da chave) e (b) por faixa HORÁRIA. Modelos treinados como antes (R3 treina em R1+R2; R2 em R1). Níveis calculados
sobre todas as chaves rotuladas e só depois fatiados."""
from pathlib import Path
src = open(Path(__file__).with_name("classificacao_zonas.py")).read().split("resultado = {}")[0]
exec(src)
import json
ESTS = ["contexto (média histórica)", "RF classificador (E[nível])", "XGBoost classificador (E[nível])", "XGBoost regressor"]
def coleta(rep, treino):
    reg, clf, rf = treino_modelos(treino); rows = []
    for d in (0, 1):
        s = conjunto(*rep, d); lab = s["lab"]; X = X_de(s); yl, _ = alvo_nivel(s)
        est = {"contexto (média histórica)": s["ctx_mean"], "RF classificador (E[nível])": rf.predict_proba(X) @ np.arange(4),
               "XGBoost classificador (E[nível])": clf.predict_proba(X) @ np.arange(4), "XGBoost regressor": reg.predict(X)}
        for n, e in est.items():
            lv = niveis(e, lab); m = lab
            rows.append(pd.DataFrame(dict(est=n, y=yl[m], p=lv[m], e=e[m], alvo=s["alvo"][m], nrec=s["nrec"][m], faixa=b.faixa[m], cel=codc[m], d=d)))
    return pd.concat(rows)
def resumo(df, col, bins, rotulos):
    out = {}
    df = df.assign(g=pd.cut(df[col], bins=bins, labels=rotulos, right=False))
    for g in rotulos:
        r = {}
        for n in ESTS:
            t = df[(df.est == n) & (df.g == g)]
            if len(t) < 30: continue
            r[n] = dict(n=int(len(t)), acc_bin=round(float(((t.y >= 2) == (t.p >= 2)).mean()), 3), ate1=round(float((abs(t.y - t.p) <= 1).mean()), 3),
                        exato=round(float((t.y == t.p).mean()), 3), rho=round(float(spearmanr(t.e, t.alvo)[0]), 3))
        out[g] = r
    return out
def dif_ic(df, col, bins, rotulos, modelo):
    """Δ acerto binário (modelo − contexto), IC por bootstrap de células, por estrato."""
    df = df.assign(g=pd.cut(df[col], bins=bins, labels=rotulos, right=False)); res = {}
    for g in rotulos:
        a = df[(df.est == "contexto (média histórica)") & (df.g == g)].reset_index(drop=True); m = df[(df.est == modelo) & (df.g == g)].reset_index(drop=True)
        if len(a) < 30: continue
        ca = ((a.y >= 2) == (a.p >= 2)).values.astype(float); cm = ((m.y >= 2) == (m.p >= 2)).values.astype(float); cel = a.cel.values; u_ = np.unique(cel)
        ix = {c: np.where(cel == c)[0] for c in u_}; ds = []
        for _ in range(300):
            ii = np.concatenate([ix[c] for c in rng.choice(u_, len(u_))]); ds.append(cm[ii].mean() - ca[ii].mean())
        res[g] = [round(float(cm.mean() - ca.mean()), 3), round(float(np.percentile(ds, 2.5)), 3), round(float(np.percentile(ds, 97.5)), 3)]
    return res
saida = {}
for nome, rep, tr in (("R2 (22–33)", (22, 33), [(10, 21)]), ("R3 (34–45)", (34, 45), [(10, 21), (22, 33)])):
    df = coleta(rep, tr)
    ev = resumo(df, "nrec", [0, 3, 6, 16, 10**6], ["1–2", "3–5", "6–15", "16+"])
    fx = resumo(df, "faixa", [0, 1, 2, 3, 4, 5], ["0", "1", "2", "3", "4"])
    ice = dif_ic(df, "nrec", [0, 3, 6, 16, 10**6], ["1–2", "3–5", "6–15", "16+"], "RF classificador (E[nível])")
    icx = dif_ic(df, "nrec", [0, 3, 6, 16, 10**6], ["1–2", "3–5", "6–15", "16+"], "XGBoost classificador (E[nível])")
    icf = dif_ic(df, "faixa", [0, 1, 2, 3, 4, 5], ["0", "1", "2", "3", "4"], "RF classificador (E[nível])")
    saida[nome] = dict(evidencia=ev, faixa_horaria=fx, d_acc_bin_RF_evid=ice, d_acc_bin_XGB_evid=icx, d_acc_bin_RF_faixa=icf)
    print(f"\n=== {nome} ===")
    for titulo, blocos, ic in (("EVIDÊNCIA (registros no contexto)", ev, ice), ("FAIXA HORÁRIA", fx, icf)):
        print("--", titulo)
        for g, r in blocos.items():
            ctx = r.get("contexto (média histórica)"); rf_ = r.get("RF classificador (E[nível])"); xg = r.get("XGBoost classificador (E[nível])")
            if ctx: print(f"  {g:5s} n={ctx['n']:4d} | bin ctx {ctx['acc_bin']} RF {rf_['acc_bin']} XGB {xg['acc_bin']} | ≤1 ctx {ctx['ate1']} RF {rf_['ate1']} | exato ctx {ctx['exato']} RF {rf_['exato']} | Δbin RF {ic.get(g)}")
json.dump(saida, open(SAIDA / "classificacao_por_faixa.json", "w"), ensure_ascii=False, indent=1)
