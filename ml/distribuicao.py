"""T017: distribuição real dos níveis, para aprovação do Nando antes do snapshot (FR-008)."""
import pandas as pd

from ml import config as C
from ml import rotulo, snapshot


def main():
    u = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    C.RESULTADOS.mkdir(parents=True, exist_ok=True)
    rubricas = rotulo.rubricas_sem_peso(u)
    rubricas.to_csv(C.RESULTADOS / "rubricas_sem_peso.csv", index=False)
    cortes = rotulo.cortes_treino(u)
    L = [f"Cortes de pontuação mensal (pontos/mês/hora), do treino T1–T4: {[round(c, 4) for c in cortes]}",
         "Regra: nível 0 < c1 ≤ nível 1 < c2 ≤ nível 2 < c3 ≤ nível 3", ""]

    def dist(s):
        n = rotulo.nivel(s, cortes)
        return n.value_counts().reindex([0, 1, 2, 3], fill_value=0)

    tab = {}
    for o in C.ORIGENS:
        tab[o] = dist(rotulos := rotulo.rotulos(u, o))
        L.append(f"{o}: rótulo em meses {C.ORIGENS[o]['rotulo']}, chaves com dado {len(rotulos)}")
    tr = pd.concat([rotulo.rotulos(u, o) for o in C.ORIGENS_TREINO])
    tab["Treino (T1–T4 juntos)"] = dist(tr)
    snap = snapshot.montar(u, cortes)
    cd = snap[snap.status == "com_dado"]
    tab["Snapshot jan–set"] = cd.nivel.value_counts().reindex([0, 1, 2, 3], fill_value=0)
    t = pd.DataFrame(tab)
    t.loc["total"] = t.sum()
    L += ["", "Chaves por nível:", t.to_string(), ""]
    L.append(f"Snapshot: {len(snap)} chaves; com dado {len(cd)}; sem dado {len(snap) - len(cd)}; "
             f"células {snap.h3_cell.nunique()}")
    # viés de seleção: chaves com features em jan–jul sem registro no rótulo de ago–set
    feat = rotulo.agregar(u, C.ORIGENS["Teste"]["features"]).index
    rot = rotulo.rotulos(u, "Teste").index
    L.append(f"Teste: chaves com features (jan–jul) {len(feat)}; com rótulo ago–set {len(feat.intersection(rot))}; "
             f"excluídas por falta de rótulo {len(feat.difference(rot))}; rótulo sem features {len(rot.difference(feat))}")
    L.append(f"Chaves de teste com 1 só registro pontuável: "
             f"{int((rotulo.agregar(u, C.ORIGENS['Teste']['rotulo']).n == 1).sum())}")
    L.append(f"Rubricas sem peso (registros usados): {int(rubricas.n_registros.sum())} "
             f"({rubricas.n_registros.sum() / len(u):.2%}); ver resultados/rubricas_sem_peso.csv")
    out = "\n".join(L) + "\n"
    (C.RESULTADOS / "distribuicao_niveis.txt").write_text(out)
    print(out)
    print(rubricas.head(12).to_string())


if __name__ == "__main__":
    main()
