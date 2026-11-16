"""Contagens de local e conduta (2026) para a proposta v3. Só leitura do interim 2026; grava um JSON em resultados/.

Dois universos, com denominador explícito:
- `perimetro_coord_valida`: linhas do interim 2026 com coordenada válida dentro do perímetro (sem filtrar hora,
  data, duplicata ou conflito);
- `usadas_jan_set`: linhas com destino `usada` na ingestão v1 (`ingestao.classificar`), as mesmas da modelagem.
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml import config as C, ingestao  # noqa: E402

VEICULO = ["Veículo", "Interior de Veículo", "Aplicativo de Mobilidade Urbana", "Carga"]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def resumo(d):
    cond = d.DESCR_CONDUTA.fillna("NULL").replace({"": "NULL"})
    sub = d.DESCR_SUBTIPOLOCAL.fillna("NULL").replace({"": "NULL"})
    return dict(
        n=int(len(d)),
        via_publica=int((sub == "Via Pública").sum()),
        conduta_nula=int((cond == "NULL").sum()),
        conduta_veiculo=int(cond.isin(VEICULO).sum()),
        conduta_veiculo_por_valor={v: int((cond == v).sum()) for v in VEICULO},
        conduta_top=cond.value_counts().head(12).astype(int).to_dict(),
        subtipo_top=sub.value_counts().head(8).astype(int).to_dict(),
    )


def main():
    fontes = [C.INTERIM / "jan_jun.parquet", C.INTERIM / "jul_dez.parquet"]
    raw = pd.concat([pd.read_parquet(f) for f in fontes], ignore_index=True)
    d = ingestao.classificar(raw)
    coord_perim = d.lat.between(C.BBOX["lat_min"], C.BBOX["lat_max"]) & d.lon.between(C.BBOX["lon_min"], C.BBOX["lon_max"])
    out = dict(
        fontes={f.name: _sha(f) for f in fontes},
        nota="DESCR_CONDUTA e DESCR_SUBTIPOLOCAL existem só no interim 2026; o interim 2023–2025 foi gravado sem elas.",
        perimetro_coord_valida=resumo(d[coord_perim]),
        usadas_jan_set=resumo(d[d.destino == "usada"]),
    )
    alvo = C.RESULTADOS / "conduta_local_2026.json"
    alvo.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: (v["n"], v["via_publica"], v["conduta_nula"], v["conduta_veiculo"])
                      for k, v in out.items() if isinstance(v, dict) and "n" in v}, ensure_ascii=False))


if __name__ == "__main__":
    main()
