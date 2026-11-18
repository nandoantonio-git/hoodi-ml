"""EXPLORATÓRIO: janela do alvo (bimestral, trimestral, semestral) × raio do perímetro (meia-largura 2,5 / 5 / 7,5 / 10 km).

Usa os registros extraídos do quadrado de 20 km (ml/dados/interim_carro, regras de ingestão do v2) e recorta o raio.
Mesmo protocolo de ml/exploratorio_classificacao/trimestral_rf_xgb.py: origens de treino a cada passo, cortes de nível
só do treino, teste = últimos W meses até set/2026 (JÁ VISTO; nada aqui é confirmatório), bootstrap por célula H3.
Modelos: média histórica (persistência da história), persistência recente e RF regularizado (sem XGBoost: o ganho dele
já foi medido e não superou a média).

Duas leituras por raio:
  - "nucleo": avalia só as chaves do perímetro atual (5x5 km), com os cortes do núcleo. Os rótulos são idênticos entre
    raios, então a comparação entre raios é limpa (o que o raio maior ajuda a prever no mesmo lugar).
  - "raio": avalia todas as chaves do raio, com os cortes do próprio raio (o que o produto veria com o mapa maior).
Uso: python -I -m ml.exploratorio_classificacao.janela_raio   (a partir da raiz do repositório)
"""
import json
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
import pandas as pd

from ml import config as C
from ml import snapshot_carro as SC
from ml import v2_historico as V
from ml.diagnostico_rf import _rf
from ml.incerteza_custo import REGULARIZADO, bootstrap, diferencas, metricas, resumo_ic

import h3

LAT, LON = SC.LAT, SC.LON
DESENHOS = {"bimestral": dict(largura=2, passo=1, primeiro=13, n_recente=7, teste=[44, 45]),
            "trimestral": dict(largura=3, passo=3, primeiro=13, n_recente=3, teste=[43, 44, 45]),
            "semestral": dict(largura=6, passo=3, primeiro=13, n_recente=6, teste=list(range(40, 46)))}
RAIOS_KM = [2.5, 5.0, 7.5, 10.0]
SAIDA = C.RESULTADOS / "janela_raio" / "janela_raio.json"


def recorte(d: pd.DataFrame, r_km: float) -> pd.DataFrame:
    dlat, dlon = r_km / 111.0, r_km / (111.0 * 0.9178)
    m = d.lat.between(LAT - dlat, LAT + dlat) & d.lon.between(LON - dlon, LON + dlon)
    return d[m][["rubrica", "data_fato", "mes", "hora", "faixa", "celula"]].reset_index(drop=True)


def eh_nucleo(celulas) -> np.ndarray:
    b = C.BBOX
    out = []
    for c in celulas:
        la, lo = h3.cell_to_latlng(c)
        out.append(b["lat_min"] <= la <= b["lat_max"] and b["lon_min"] <= lo <= b["lon_max"])
    return np.array(out)


def avaliar(u, cfg, cortes, mascara_nucleo):
    """Treina RF com os cortes dados e devolve métricas no Teste (todo o raio ou só o núcleo)."""
    L, teste = cfg["largura"], cfg["teste"]
    treino = V.origens(cfg["primeiro"], teste[0] - L, L, cfg["passo"])
    Xtr, ytr = V.montar(u, treino, cortes, cfg["n_recente"])
    Xte, yte, _ = V.exemplos_v2(u, teste, cortes, cfg["n_recente"])
    rf = _rf(REGULARIZADO).fit(Xtr.values, ytr.values)
    p = {"rf_regularizado": np.asarray(rf.predict(Xte.values))}
    p.update(V.persistencias(Xte, cortes))
    y = yte.values
    cel = np.asarray(Xte.index.get_level_values("celula"))
    if mascara_nucleo:
        m = eh_nucleo(cel)
        y, cel, p = y[m], cel[m], {k: v[m] for k, v in p.items()}
    pont = {k: metricas(y, v) for k, v in p.items()}
    boot = bootstrap(y, p, cel)
    pares = [("rf_regularizado", "base_persistencia_historia"), ("rf_regularizado", "base_persistencia_recente"),
             ("base_persistencia_historia", "base_persistencia_recente")]
    return dict(n_treino=int(len(Xtr)), n_teste=int(len(y)), n_celulas_teste=int(len(np.unique(cel))),
                distribuicao_teste={int(k): int(n) for k, n in pd.Series(y).value_counts().sort_index().items()},
                cortes=[round(c, 4) for c in cortes],
                teste=resumo_ic(boot, pont), diferencas=diferencas(boot, pares, n_familia=len(pares)))


def main(raios=RAIOS_KM, janelas=tuple(DESENHOS)):
    d = pd.read_parquet(os.environ.get("HOODI_CARRO_USADAS", "/tmp/carro_usadas.parquet"))
    res = json.loads(SAIDA.read_text()) if SAIDA.exists() else {}  # acumula janelas rodadas em chamadas separadas
    res.update({"nota": "exploratório; teste ago–set/2026 e últimos W meses já vistos (test_seen); sem seleção pré-registrada",
                "semente": C.SEMENTE, "n_registros_20km": int(len(d))})
    for jn in janelas:
        cfg = DESENHOS[jn]
        L, teste = cfg["largura"], cfg["teste"]
        treino = V.origens(cfg["primeiro"], teste[0] - L, L, cfg["passo"])
        u_nucleo = recorte(d, 2.5)
        cortes_nucleo = V.cortes_quartis(u_nucleo, treino)
        for r in raios:
            u = recorte(d, r)
            cortes_raio = V.cortes_quartis(u, treino)
            ch = f"{jn}|raio_{r}"
            res[ch] = dict(
                n_registros=int(len(u)), n_celulas=int(u.celula.nunique()),
                nucleo=avaliar(u, cfg, cortes_nucleo, True),
                raio=avaliar(u, cfg, cortes_raio, False))
            for leitura in ("nucleo", "raio"):
                t = res[ch][leitura]["teste"]
                print(f"{jn:10s} raio {r:>4} {leitura:6s} n={res[ch][leitura]['n_teste']:5d} " + "  ".join(
                    f"{k.replace('base_persistencia_', 'pers_')}: {v['macro_f1']['valor']:.3f} "
                    f"[{v['macro_f1']['ic95'][0]:.3f};{v['macro_f1']['ic95'][1]:.3f}]" for k, v in t.items()), flush=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=float) + "\n")
    return res


if __name__ == "__main__":
    args = sys.argv[1:]
    main(janelas=tuple(args) if args else tuple(DESENHOS))
