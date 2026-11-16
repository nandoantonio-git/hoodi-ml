import pandas as pd
from ml import rotulo
from tests.test_sem_dado import usadas


def _treino():
    linhas = []
    for mes, (n_cel) in zip([3, 4, 5, 6, 7], [1, 2, 3, 4, 5]):
        for c in range(n_cel):
            linhas.append(dict(mes=mes, celula=f"89a8100000{c}ffff", faixa=c % 5, rubrica="Roubo (art. 157)"))
    return usadas(*linhas)


def test_cortes_sao_tres_e_crescentes():
    c = rotulo.cortes_treino(_treino())
    assert len(c) == 3 and c[0] <= c[1] <= c[2]


def test_cortes_ignoram_ago_set():
    base = _treino()
    ruido = usadas(*[dict(mes=m, celula=f"89a8100001{i}ffff", faixa=0, rubrica="Homicídio (art. 121)")
                     for i in range(30) for m in (8, 9)])
    assert rotulo.cortes_treino(base) == rotulo.cortes_treino(pd.concat([base, ruido], ignore_index=True))


def test_cortes_do_treino_sao_reaplicados_ao_teste_sem_recalcular():
    base = _treino()
    c = rotulo.cortes_treino(base)
    teste = usadas(*[dict(mes=8, rubrica="Homicídio (art. 121)")] * 6)
    y = rotulo.rotulos(teste, "Teste")
    assert rotulo.nivel(y, c).iloc[0] == 3
    assert rotulo.cortes_treino(pd.concat([base, teste], ignore_index=True)) == c
