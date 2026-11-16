from ml import features
from tests.test_sem_dado import usadas, CEL


def test_taxa_igual_para_janelas_de_tamanhos_diferentes_com_mesma_intensidade():
    curta = usadas(*[dict(mes=m, rubrica="Roubo (art. 157)") for m in (1, 2)])
    longa = usadas(*[dict(mes=m, rubrica="Roubo (art. 157)") for m in (1, 2, 3, 4)])
    a = features.construir(curta, [1, 2]).iloc[0]
    b = features.construir(longa, [1, 2, 3, 4]).iloc[0]
    for col in ("taxa_registros", "taxa_pontuacao", "taxa_roubo"):
        assert a[col] == b[col]


def test_chave_sem_registro_na_janela_de_features_fica_fora():
    u = usadas(dict(mes=1, faixa=2), dict(mes=3, faixa=4))
    X = features.construir(u, [1, 2])
    assert list(X.index) == [(CEL, 2)]


def test_vizinha_sem_registro_conta_zero_e_vizinha_com_registro_entra():
    import h3
    viz = sorted(v for v in h3.grid_disk(CEL, 1) if v != CEL)[0]
    u = usadas(dict(mes=1, faixa=2), dict(mes=1, faixa=2, celula=viz, rubrica="Roubo (art. 157)"))
    X = features.construir(u, [1])
    esperado = 3 / 1 / 6 / 6  # 1 vizinha com pontuação 3/6, média sobre 6 vizinhas
    assert abs(X.loc[(CEL, 2), "pont_vizinhas"] - esperado) < 1e-12
