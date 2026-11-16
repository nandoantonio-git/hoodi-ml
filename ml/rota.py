"""Bloco B do plano v3 (PLANO-EXECUCAO-V3-r2 §4): pontuação de rota, implementação Python de REFERÊNCIA.

Quem calcula rotas em produção é a API .NET (contexto Rotas); o ML entrega a definição exata, esta referência e os
vetores-ouro (docs/contratos-v3/vetores_rota_v2.json) para conferir a implementação em C#. Demonstração retrospectiva
não validada (test_seen=true). A saída é um ÍNDICE em pontos/(mês·hora) × km, não contagem esperada nem probabilidade.

Uso: ~/.venvs/hoodi-ml311/bin/python -m ml.rota   # grava os vetores-ouro e imprime o sha256
"""
import hashlib
import json
import math
from pathlib import Path

import h3
import pandas as pd

from ml import config as C

R_TERRA = 6_371_008.8      # metros (raio médio IUGG)
PASSO_M = 5.0              # subsegmento máximo
RES = 9
TOL_REL = 1e-9             # empate: |a − b| <= TOL_REL · max(|a|, |b|, 1)
LIMITE_INSUFICIENTE = 30.0  # % do trajeto sem dado ou fora da cobertura; regra de produto hipotética
ROTULO = "pontuação acumulada observada, jan–set/2026 (retrospectiva), demonstração não validada"
UNIDADE = "pontos/(mês·hora) × km"
SNAPSHOT_CSV = C.SNAPSHOT / "risco_h3_faixa_v2.csv"
DESTINO = C.RAIZ / "docs" / "contratos-v3"


class RotaInvalida(ValueError):
    codigo = "rota_invalida"


def haversine(p0, p1) -> float:
    """Distância em metros entre (lat, lon) em graus. Fórmula fixada no contrato."""
    f1, f2 = math.radians(p0[0]), math.radians(p1[0])
    df = f2 - f1
    dl = math.radians(p1[1] - p0[1])
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * R_TERRA * math.asin(math.sqrt(a))


def _validar(pontos):
    limpos = []
    for p in pontos:
        try:
            if len(p) != 2:
                raise RotaInvalida(f"ponto deve ter exatamente (lat, lon): {p!r}")
            lat, lon = float(p[0]), float(p[1])
        except RotaInvalida:
            raise
        except (TypeError, ValueError) as e:
            raise RotaInvalida(f"ponto malformado: {p!r}") from e
        if not (math.isfinite(lat) and math.isfinite(lon)) or not (-90 <= lat <= 90) or not (-180 <= lon < 180):
            raise RotaInvalida(f"coordenada fora dos limites: {p}")
        if not limpos or limpos[-1] != (lat, lon):  # remove pontos consecutivos idênticos
            limpos.append((lat, lon))
    if len(limpos) < 2:
        raise RotaInvalida("menos de 2 pontos distintos")
    return limpos


def discretizar(pontos) -> list:
    """Polilinha [(lat, lon)] → [(h3_cell, metros)] na ordem da primeira ocorrência, metros em precisão dupla.
    Cada segmento vira n = max(1, ceil(d/5)) subsegmentos por interpolação linear em graus; cada subsegmento tem
    comprimento haversine entre as extremidades e vai para latlng_to_cell(ponto médio, 9)."""
    pts = _validar(pontos)
    metros = {}
    for p0, p1 in zip(pts, pts[1:]):
        d = haversine(p0, p1)
        n = max(1, math.ceil(d / PASSO_M))
        ant = p0
        for i in range(1, n + 1):
            t = i / n
            cur = (p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])) if i < n else p1
            meio = ((ant[0] + cur[0]) / 2, (ant[1] + cur[1]) / 2)
            c = h3.latlng_to_cell(meio[0], meio[1], RES)
            metros[c] = metros.get(c, 0.0) + haversine(ant, cur)
            ant = cur
    return list(metros.items())


def indice_snapshot(snap: pd.DataFrame) -> dict:
    return {(r.h3_cell, int(r.faixa)): (r.status, None if pd.isna(r.pontuacao_mensal) else float(r.pontuacao_mensal))
            for r in snap.itertuples()}


def pontuar(trechos, faixa: int, idx: dict) -> dict:
    """Função pura do núcleo (r3): [(h3_cell, metros)] + faixa + snapshot → resultado sem arredondar."""
    if faixa not in C.FAIXA_HORAS:
        raise RotaInvalida(f"faixa inexistente: {faixa}")
    m_total = m_com = m_sem = m_fora = 0.0
    soma = 0.0
    for c, m in trechos:
        m_total += m
        st = idx.get((c, faixa))
        if st is None:
            m_fora += m
        elif st[0] == "sem_dado":
            m_sem += m
        else:
            m_com += m
            soma += st[1] * (m / 1000.0)
    if m_total <= 0:
        raise RotaInvalida("comprimento zero")
    pct_sem, pct_fora = 100 * m_sem / m_total, 100 * m_fora / m_total
    return dict(pontuacao_acumulada_observada=soma, unidade=UNIDADE,
                indice_por_km=(soma / (m_com / 1000.0)) if m_com > 0 else None,
                km_total=m_total / 1000.0, km_com_dado=m_com / 1000.0,
                pct_sem_dado=pct_sem, pct_fora_da_cobertura=pct_fora,
                dado_insuficiente=(pct_sem + pct_fora) > LIMITE_INSUFICIENTE, faixa=faixa, rotulo=ROTULO)


def empate(a: float, b: float) -> bool:
    return abs(a - b) <= TOL_REL * max(abs(a), abs(b), 1.0)


def _classes(itens: list, chave) -> list:
    """Classes de empate transitivas: itens em ordem crescente EXATA de `chave` (desempate interno pelo índice);
    uma classe nova começa quando o valor não empata com o PRIMEIRO (menor) da classe atual (âncora)."""
    itens = sorted(itens, key=lambda i: (chave(i), i))
    classes = []
    for i in itens:
        if classes and empate(chave(classes[-1][0]), chave(i)):
            classes[-1].append(i)
        else:
            classes.append([i])
    return classes


def ordenar(resultados: list) -> list:
    """Ranking entre rotas do MESMO par origem-destino. Retorna a posição (1..n) de cada rota na ordem de entrada,
    ou None para 'dado insuficiente no trajeto'. Menor pontuação primeiro. Empates em classes transitivas ancoradas
    no menor valor (`_classes`): dentro de cada classe de pontuação, classes de km_total pela mesma regra; dentro
    destas, menor índice de entrada. Comparação sem arredondar."""
    validas = [i for i, r in enumerate(resultados) if not r["dado_insuficiente"]]
    ordem = []
    for cp in _classes(validas, lambda i: resultados[i]["pontuacao_acumulada_observada"]):
        for ck in _classes(cp, lambda i: resultados[i]["km_total"]):
            ordem.extend(sorted(ck))
    pos = [None] * len(resultados)
    for p, i in enumerate(ordem, 1):
        pos[i] = p
    return pos


def exibir(r: dict) -> dict:
    """Arredondamento só na exibição: half-even (round do Python) a 1e-6 no índice e 0,01 m nos comprimentos."""
    out = dict(r)
    for k in ("pontuacao_acumulada_observada", "indice_por_km", "pct_sem_dado", "pct_fora_da_cobertura"):
        if out[k] is not None:
            out[k] = round(out[k], 6)
    for k in ("km_total", "km_com_dado"):
        out[f"metros_{k[3:]}"] = round(out.pop(k) * 1000, 2)  # 0,01 m; km só na saída sem arredondar
    return out


# Três polilinhas FIXAS entre o mesmo par origem-destino (não vêm de malha viária; o motor de rotas é do Abner).
ORIGEM_EXEMPLO = (-23.5646, -46.6522)   # centro provisório do perímetro (manifest v2)
DESTINO_EXEMPLO = (-23.5560, -46.6400)
ROTAS_EXEMPLO = {
    "reta": [ORIGEM_EXEMPLO, DESTINO_EXEMPLO],
    "norte_depois_leste": [ORIGEM_EXEMPLO, (DESTINO_EXEMPLO[0], ORIGEM_EXEMPLO[1]), DESTINO_EXEMPLO],
    "leste_depois_norte": [ORIGEM_EXEMPLO, (ORIGEM_EXEMPLO[0], DESTINO_EXEMPLO[1]), DESTINO_EXEMPLO],
}


def exemplo(snap: pd.DataFrame, faixa: int = 4) -> pd.DataFrame:
    """Pontua as 3 polilinhas fixas na faixa dada e devolve a tabela com a posição no ranking."""
    idx = indice_snapshot(snap)
    res = [pontuar(discretizar(p), faixa, idx) for p in ROTAS_EXEMPLO.values()]
    pos = ordenar(res)
    t = pd.DataFrame([exibir(r) for r in res], index=list(ROTAS_EXEMPLO))
    t["posicao"] = pos
    return t


# ------------------------------------------------------------------------------------------- vetores-ouro
def _centro(c):
    return h3.cell_to_latlng(c)


def _caminho(cels):
    return [list(_centro(c)) for c in cels]


def _escolher(snap):
    """Células reais do snapshot para montar os casos (determinístico: ordenação por id)."""
    idx = indice_snapshot(snap)
    cels = sorted(snap.h3_cell.unique())
    f = 2  # tarde
    com = [c for c in cels if idx[(c, f)][0] == "com_dado"]
    sem = [c for c in cels if idx[(c, f)][0] == "sem_dado"]
    # trilha de 3 células com_dado vizinhas em sequência
    trilha = None
    for a in com:
        for b in sorted(h3.grid_disk(a, 1)):
            if b == a or b not in com:
                continue
            for c in sorted(h3.grid_disk(b, 1)):
                if c not in (a, b) and c in com and h3.grid_distance(a, c) == 2:
                    trilha = [a, b, c]
                    break
            if trilha:
                break
        if trilha:
            break
    par_sem = next((a, s) for a in com for s in sorted(h3.grid_disk(a, 1)) if s in sem)
    return idx, trilha, par_sem


def _caso(nome, descricao, rotas, faixa, idx, erro_esperado=None):
    saida = []
    for pts in rotas:
        try:
            tr = discretizar(pts)
            r = pontuar(tr, faixa, idx)
            saida.append(dict(entrada=dict(pontos=pts, faixa=faixa),
                              celulas=[dict(h3_cell=c, metros=m, metros_exibicao=round(m, 2)) for c, m in tr],
                              resultado=r, resultado_exibicao=exibir(r)))
        except RotaInvalida as e:
            saida.append(dict(entrada=dict(pontos=pts, faixa=faixa), erro=RotaInvalida.codigo, detalhe=str(e)))
    validos = [s["resultado"] for s in saida if "resultado" in s]
    caso = dict(nome=nome, descricao=descricao, rotas=saida)
    if len(validos) == len(saida) and len(saida) > 1:
        caso["ordenacao_posicoes"] = ordenar(validos)
    if erro_esperado:
        assert all(s.get("erro") == erro_esperado for s in saida), nome
    return caso


def _fronteira(cels, n=20):
    """Pontos a 5e-8 grau de arestas de células do perímetro, com a célula do core C."""
    out = []
    for c in cels:
        b = h3.cell_to_boundary(c)
        for t, (v0, v1) in ((0.37, (b[0], b[1])), (0.61, (b[2], b[3]))):
            lat, lon = v0[0] + t * (v1[0] - v0[0]), v0[1] + t * (v1[1] - v0[1])
            for dlat in (5e-8, -5e-8):
                out.append(dict(lat=lat + dlat, lon=lon, h3_cell=h3.latlng_to_cell(lat + dlat, lon, RES)))
        if len(out) >= n:
            break
    return out[:n]


def vetores(snap: pd.DataFrame, snapshot_sha256: str) -> dict:
    idx, trilha, (a_sem, s_sem) = _escolher(snap)
    a, b, c = trilha
    pa, pb, pc = _centro(a), _centro(b), _centro(c)
    fora = [pa[0] + 0.03, pa[1]]  # ~3,3 km ao norte: sai do perímetro
    if pa[0] + 0.03 <= C.BBOX["lat_max"]:
        fora = [C.BBOX["lat_max"] + 0.02, pa[1]]
    meio_ab = [(pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2]
    casos = [
        _caso("1_toda_com_dado", "duas células com_dado vizinhas, centro a centro", [_caminho([a, b])], 2, idx),
        _caso("2_trecho_sem_dado", "de uma célula com_dado a uma vizinha sem_dado", [_caminho([a_sem, s_sem])], 2, idx),
        _caso("3_sai_do_perimetro", "do centro de uma célula até ponto fora do snapshot", [[list(pa), fora]], 2, idx),
        _caso("4_cruza_bordas", "três células em sequência (cruza duas bordas)", [_caminho([a, b, c])], 2, idx),
        _caso("5_empate_e_ranking", "mesma rota nos dois sentidos (empate → km → índice) e uma rota com dado "
              "insuficiente", [_caminho([a, b, c]), _caminho([c, b, a]), [list(pa), fora]], 2, idx),
        _caso("6_um_ponto", "um ponto só → rota_invalida", [[list(pa)]], 2, idx, erro_esperado="rota_invalida"),
        _caso("7_pontos_repetidos", "pontos consecutivos repetidos são removidos",
              [[list(pa), list(pa), meio_ab, meio_ab, list(pb)]], 2, idx),
        _caso("8_segmento_menor_5m", "segmento de ~2 m (n=1)", [[list(pa), [pa[0] + 1.8e-5, pa[1]]]], 2, idx),
        _caso("9_volta_mesma_celula", "vai e volta: a célula de partida reaparece e soma metros",
              [_caminho([a, b, a])], 2, idx),
        _caso("10_faixa_3h", "mesma rota do caso 4 na faixa noite_cedo (3 h)", [_caminho([a, b, c])], 3, idx),
    ]
    cels_perim = sorted(snap.h3_cell.unique())
    fr = _fronteira(cels_perim)
    rotas_fronteira = []
    for p in fr[:2]:
        rotas_fronteira.append(_caso(f"fronteira_{len(rotas_fronteira) + 1}",
                                     "subsegmento único (~2 m) cujo ponto médio é um ponto de fronteira",
                                     [[[p["lat"], p["lon"] - 1e-5], [p["lat"], p["lon"] + 1e-5]]], 2, idx))
    interiores = []
    for cel in cels_perim[::max(1, len(cels_perim) // 20)][:20]:
        lat, lon = _centro(cel)
        lat, lon = lat + 1.3e-4, lon - 0.9e-4
        interiores.append(dict(lat=lat, lon=lon, h3_cell=h3.latlng_to_cell(lat, lon, RES)))
    base = 2.5
    return dict(
        contrato="docs/contratos-v3/rota_pontuacao_v1.md", versao_vetores=2, test_seen=True,
        natureza="referência para validação da implementação C#; demonstração retrospectiva não validada",
        snapshot_csv_sha256=snapshot_sha256, h3_core_c=h3.versions()["c"], resolucao=RES,
        constantes=dict(R_terra_m=R_TERRA, passo_m=PASSO_M, tol_rel_empate=TOL_REL,
                        limite_dado_insuficiente_pct=LIMITE_INSUFICIENTE),
        aceite=dict(celulas="igualdade exata", metros="|Δ| <= 0,01 m", indice="|Δ| <= 1e-6 relativo"),
        casos=casos, rotas_fronteira=rotas_fronteira,
        pontos_interiores=interiores, pontos_fronteira=fr,
        empate_vetores=[dict(a=base, b=base * (1 + 0.5e-9), empate=empate(base, base * (1 + 0.5e-9))),
                        dict(a=base, b=base * (1 + 2e-9), empate=empate(base, base * (1 + 2e-9)))],
    )


def gravar(destino=DESTINO) -> dict:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    snap = pd.read_csv(SNAPSHOT_CSV, dtype={"h3_cell": str})
    h_snap = hashlib.sha256(SNAPSHOT_CSV.read_bytes()).hexdigest()
    v = vetores(snap, h_snap)
    arq = destino / "vetores_rota_v2.json"
    arq.write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n")
    h = hashlib.sha256(arq.read_bytes()).hexdigest()
    (destino / "vetores_rota_v2.json.sha256").write_text(f"{h}  {arq.name}\n")
    return dict(arquivo=str(arq), sha256=h, vetores=v)


if __name__ == "__main__":
    r = gravar()
    print(r["arquivo"], r["sha256"])
    for cs in r["vetores"]["casos"]:
        for s in cs["rotas"]:
            e = s.get("resultado_exibicao") or s
            print(cs["nome"], {k: e.get(k) for k in ("pontuacao_acumulada_observada", "km_total", "pct_sem_dado",
                                                    "pct_fora_da_cobertura", "dado_insuficiente", "erro")})
        if "ordenacao_posicoes" in cs:
            print("  ordenação:", cs["ordenacao_posicoes"])
