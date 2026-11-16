import numpy as np
import pandas as pd
from ml import rotulo, snapshot

CEL = "89a81000003ffff"


def usadas(*linhas):
    base = dict(bo_id="b", rubrica="Furto (art. 155)", data_fato=46040, mes=1, hora=0.5, faixa=2,
                lat=-23.56, lon=-46.65, celula=CEL)
    return pd.DataFrame([{**base, **l, "bo_id": f"b{i}"} for i, l in enumerate(linhas)])


def test_nivel_so_assume_0_a_3():
    n = rotulo.nivel(pd.Series([0.0, 0.5, 1.0, 5.0, 99.0]), [1.0, 2.0, 3.0])
    assert set(n.dropna()) <= {0, 1, 2, 3}
    assert list(n) == [0, 0, 1, 3, 3]


def test_sem_dado_fica_fora_da_escala_e_nunca_vira_zero():
    n = rotulo.nivel(pd.Series([np.nan, 2.0]), [1.0, 2.0, 3.0])
    assert pd.isna(n.iloc[0]) and n.iloc[1] == 2


def test_chave_sem_registro_e_sem_dado():
    snap = snapshot.montar(usadas({}, {}), [0.001, 0.002, 0.003])
    sd = snap[snap.status == "sem_dado"]
    assert len(sd) > 0
    assert sd.nivel.isna().all() and sd.pontuacao_mensal.isna().all() and (sd.n_registros == 0).all()
    cd = snap[snap.status == "com_dado"]
    assert cd.nivel.notna().all() and cd.nivel.isin([0, 1, 2, 3]).all()


def test_chave_so_com_rubrica_sem_peso_e_sem_dado():
    snap = snapshot.montar(usadas({"rubrica": "Porte de arma (art. 19)"}), [1, 2, 3])
    linha = snap[(snap.h3_cell == CEL) & (snap.faixa == 2)].iloc[0]
    assert linha.status == "sem_dado" and pd.isna(linha.nivel)
