"""Gera o snapshot v2 a partir do dado real, com supressão k >= 3."""
import pandas as pd

from ml import config as C
from ml import rotulo, snapshot


def main(destino=None):
    u = pd.read_parquet(C.PROCESSED / "usadas.parquet")
    cortes = rotulo.cortes_treino(u)
    snap = snapshot.montar(u, cortes)
    destino = destino or C.SNAPSHOT
    meta = dict(raw_sha256=C.CHECKSUM.read_text().split()[0], total_linhas_base=814900,
                total_registros_usados=int(len(u)))
    return snapshot.gravar(snap, destino, cortes, meta)


if __name__ == "__main__":
    print(main()["csv_sha256"])
