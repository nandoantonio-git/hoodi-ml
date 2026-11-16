import hashlib
from ml import snapshot
from tests.test_sem_dado import usadas


def test_duas_execucoes_geram_o_mesmo_hash(tmp_path):
    hs = []
    for i in range(2):
        d = tmp_path / str(i)
        snap = snapshot.montar(usadas({}, {"rubrica": "Roubo (art. 157)", "faixa": 4}), [0.01, 0.05, 0.1])
        snapshot.gravar(snap, d, cortes=[0.01, 0.05, 0.1], meta={})
        hs.append(hashlib.sha256((d / "risco_h3_faixa_v2.csv").read_bytes()).hexdigest())
    assert hs[0] == hs[1]
