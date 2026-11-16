"""Constantes do pipeline (plan.md, research D-02 a D-06). Um só lugar."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "ml" / "dados"
INTERIM = DADOS / "interim"
PROCESSED = DADOS / "processed"
QUARANTINE = DADOS / "quarantine"
FEATURES = DADOS / "features"
SNAPSHOT = DADOS / "snapshot"
RESULTADOS = DADOS / "resultados"
CHECKSUM = DADOS / "raw" / "CHECKSUM.txt"

SEMENTE = 42

# Perímetro 5x5 km em torno da FIAP Paulista
BBOX = dict(lat_min=-23.58706, lat_max=-23.54214, lon_min=-46.67671, lon_max=-46.62769)
# Retângulo do estado de SP (coordenada fora dele é inválida)
BBOX_SP = dict(lat_min=-25.4, lat_max=-19.7, lon_min=-53.2, lon_max=-44.1)
H3_RES = 9

# Faixas: bordas em minutos do dia, [inicio, fim)
FAIXAS = [
    (0, "madrugada", 0, 360),
    (1, "manha", 360, 720),
    (2, "tarde", 720, 1080),
    (3, "noite_cedo", 1080, 1260),
    (4, "noite", 1260, 1440),
]
FAIXA_HORAS = {0: 6, 1: 6, 2: 6, 3: 3, 4: 3}
FAIXA_NOME = {f: n for f, n, _, _ in FAIXAS}

# Janela de fato: 2026-01-01 a 2026-09-30 (serial Excel; 46023 = 2026-01-01)
SERIAL_2026_01_01 = 46023
SERIAL_2026_09_30 = 46023 + 272  # 2026-09-30
MES_PRIMEIRO, MES_ULTIMO = 1, 9

# Origens: meses de features e meses do rótulo (research D-03)
ORIGENS = {
    "T1": dict(features=[1, 2], rotulo=[3, 4]),
    "T2": dict(features=[1, 2, 3], rotulo=[4, 5]),
    "T3": dict(features=[1, 2, 3, 4], rotulo=[5, 6]),
    "T4": dict(features=[1, 2, 3, 4, 5], rotulo=[6, 7]),
    "Teste": dict(features=[1, 2, 3, 4, 5, 6, 7], rotulo=[8, 9]),
}
ORIGENS_TREINO = ["T1", "T2", "T3", "T4"]

# Pesos por rubrica: (prefixo em minúsculas, peso); a primeira regra que casar vale.
# Rubrica sem regra = sem peso (fora da pontuação, contada no relatório).
PESOS = [
    ("furto (art. 155)", 1),
    ("tráfico drogas", 1),
    ("drogas para consumo", 1),
    ("lesão corporal culposa", 1),
    ("roubo (art. 157)", 3),
    ("lesão corporal (art. 129)", 3),
    ("homicídio (art. 121)", 5),
    ("feminicídio", 5),
    ("estupro", 5),
]


def peso_rubrica(rubrica):
    """Peso da rubrica ou None (sem peso)."""
    r = str(rubrica).strip().lower()
    for prefixo, peso in PESOS:
        if r.startswith(prefixo):
            return peso
    return None
