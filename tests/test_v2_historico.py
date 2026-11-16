"""v2 (exploração adicional): variáveis só com meses anteriores ao rótulo; origens de treino antes do Teste."""
import numpy as np
import h3
from ml import v2_historico as V
from tests.test_sem_dado import usadas, CEL

CELS = sorted(h3.grid_disk(CEL, 2))[:8]


def _base(meses):
    rng = np.random.default_rng(1)
    return [dict(mes=m, celula=CELS[c], faixa=int(rng.integers(0, 5)),
                 rubrica=str(rng.choice(["Roubo (art. 157)", "Furto (art. 155)"])))
            for m in meses for c in range(8) for _ in range(int(rng.integers(1, 3)))]


def test_origens_de_treino_terminam_antes_do_teste():
    for cfg in V.DESENHOS.values():
        L, teste = cfg["largura"], cfg["teste"]
        treino = V.origens(cfg["primeiro"], teste[0] - L, L, cfg["passo"])
        assert treino and max(j[-1] for j in treino) < teste[0]
        assert all(len(j) == L for j in treino)


def test_variaveis_v2_invariantes_a_registros_do_rotulo_e_futuros():
    rotulo_meses = [20, 21]
    linhas = _base(range(1, 20))
    X1 = V.construir_v2(usadas(*linhas), 19, list(range(13, 20)), [8, 9])
    futuro = [dict(mes=m, celula=CELS[0], faixa=0, rubrica="Homicídio (art. 121)")
              for m in rotulo_meses + [30] for _ in range(5)]
    X2 = V.construir_v2(usadas(*(linhas + futuro)), 19, list(range(13, 20)), [8, 9])
    assert X1.equals(X2)


def test_ablacao_historia_curta_ignora_meses_anteriores_a_janela():
    linhas = _base(range(1, 20))
    antigos = [dict(mes=m, celula=CELS[1], faixa=1, rubrica="Roubo (art. 157)") for m in (1, 2, 8) for _ in range(4)]
    a = V.construir_v2(usadas(*linhas), 19, list(range(13, 20)), [8, 9], historia=7)
    b = V.construir_v2(usadas(*(linhas + antigos)), 19, list(range(13, 20)), [8, 9], historia=7)
    assert a.equals(b)
