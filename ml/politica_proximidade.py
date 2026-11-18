"""Bloco A do plano v3: política de alerta POR PROXIMIDADE sobre o snapshot v2 (k ≥ 3).

Demonstração retrospectiva exploratória (test_seen=true), não validada como alerta para pessoas. O ML define a regra e
a referência; quem executa em produção é o app, no aparelho, sem rede. A regra NÃO garante distância nem antecedência
mínima até a célula elegível: avisa quando a pessoa está numa célula elegível ou numa vizinha (grid_disk k=1).

Uso: ~/.venvs/hoodi-ml311/bin/python -m ml.politica_proximidade [2|3]
     # grava docs/contratos-v3/politica_proximidade_v2.json (padrão) ou politica_proximidade_v3.json (snapshot v3 semestral)
"""
import sys
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import h3
import numpy as np
import pandas as pd

from ml import config as C

SNAPSHOT_CSV = C.SNAPSHOT / "risco_h3_faixa_v2.csv"
DESTINO = C.RAIZ / "docs" / "contratos-v3"
NOME = "politica_proximidade_v2.json"
# Por versão do contrato do snapshot: onde ele está, como a política se chama e qual janela o texto cita.
VERSOES = {
    2: dict(pasta=C.SNAPSHOT, csv="risco_h3_faixa_v2.csv", nome=NOME, janela="jan–set/2026"),
    3: dict(pasta=C.DADOS / "snapshot_v3", csv="risco_h3_faixa_v3.csv", nome="politica_proximidade_v3.json",
            janela="abr–set/2026"),
}
FUSO = "America/Sao_Paulo"

L_PADRAO = 3
K_ANEL = 1
COOLDOWN_MIN = 30
TEXTO = "Área próxima com muitas ocorrências registradas ({janela})"
TEXTO_SEM_DADO = "dados insuficientes para exibição"
NATUREZA = ("Regra de produto exploratória sobre o mapa histórico observado ({janela}). Demonstração retrospectiva, "
            "não validada como alerta para pessoas; test_seen=true. Alerta por proximidade: não garante distância nem "
            "antecedência mínima até a célula elegível.")


def ler_snapshot(caminho=SNAPSHOT_CSV) -> pd.DataFrame:
    return pd.read_csv(caminho, dtype={"h3_cell": str})


def sha256_arquivo(caminho) -> str:
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def faixa_do_instante(instante: dt.datetime) -> int:
    """Faixa vigente: hora local do aparelho convertida para America/Sao_Paulo, bordas [início, fim) do contrato v2.
    Instante sem fuso é recusado: o app sempre conhece o fuso do aparelho."""
    if instante.tzinfo is None:
        raise ValueError("instante sem fuso")
    local = instante.astimezone(ZoneInfo(FUSO))
    minuto = local.hour * 60 + local.minute
    for f, _, ini, fim in C.FAIXAS:
        if ini <= minuto < fim:
            return f
    raise AssertionError("faixas do contrato não cobrem o dia")


def elegiveis(snap: pd.DataFrame, L: int) -> set:
    """Chaves (h3_cell, faixa) com status com_dado e nivel >= L. sem_dado nunca é elegível."""
    e = snap[(snap.status == "com_dado") & (snap.nivel >= L)]
    return set(zip(e.h3_cell, e.faixa.astype(int)))


def celulas_que_disparam(celula: str, faixa: int, eleg: set, k: int = K_ANEL) -> list:
    """Células elegíveis em grid_disk(celula, k) na faixa, ordenadas por id (determinístico)."""
    return sorted(c for c in h3.grid_disk(celula, k) if (c, faixa) in eleg)


class Avaliador:
    """Referência da semântica do app: avaliar a cada atualização de posição e na troca de faixa.
    Cooldown por célula elegível: cada uma dispara no máximo uma vez a cada COOLDOWN_MIN minutos."""

    def __init__(self, politica: dict, snap: pd.DataFrame, snapshot_sha256: str):
        self.ativa = politica["snapshot_csv_sha256"] == snapshot_sha256
        self.erro = None if self.ativa else "hash do snapshot não confere com a política; sem alerta"
        self.L, self.k, self.cooldown = politica["L"], politica["k_anel"], politica["cooldown_min"]
        self.texto = politica["texto_alerta"]
        self.eleg = elegiveis(snap, self.L) if self.ativa else set()
        self.ultimo = {}

    def avaliar(self, celula: str, instante: dt.datetime) -> dict:
        if not self.ativa:
            return dict(alerta=False, celulas=[], erro=self.erro)
        faixa = faixa_do_instante(instante)
        alvo = celulas_que_disparam(celula, faixa, self.eleg, self.k)
        novas = [c for c in alvo if c not in self.ultimo
                 or instante - self.ultimo[c] >= dt.timedelta(minutes=self.cooldown)]
        for c in novas:
            self.ultimo[c] = instante
        return dict(alerta=bool(novas), celulas=novas, faixa=faixa, texto=self.texto if novas else None, erro=None)


def tabela_por_nivel(snap: pd.DataFrame) -> list:
    """Por L: chaves com_dado com nivel >= L ÷ todas as com_dado, e fração da pontuacao_mensal somada."""
    cd = snap[snap.status == "com_dado"]
    total_p = float(cd.pontuacao_mensal.sum())
    linhas = []
    for L in (1, 2, 3):
        e = cd[cd.nivel >= L]
        linhas.append(dict(L=L, chaves_elegiveis=int(len(e)), chaves_com_dado=int(len(cd)),
                           fracao_chaves_com_dado=round(len(e) / len(cd), 6),
                           fracao_pontuacao=round(float(e.pontuacao_mensal.sum()) / total_p, 6)))
    return linhas


def sensibilidade_p90(snap: pd.DataFrame) -> dict:
    """Só registrada; a regra não a usa. Elegível se pontuacao_mensal >= P90 das chaves com_dado."""
    cd = snap[snap.status == "com_dado"]
    p90 = float(np.quantile(cd.pontuacao_mensal.values, 0.9))
    e = cd[cd.pontuacao_mensal >= p90]
    return dict(p90_pontuacao_mensal=round(p90, 6), chaves=int(len(e)),
                fracao_chaves_com_dado=round(len(e) / len(cd), 6),
                fracao_pontuacao=round(float(e.pontuacao_mensal.sum()) / float(cd.pontuacao_mensal.sum()), 6),
                uso="somente registro; não altera a regra")


def cobertura_do_anel(snap: pd.DataFrame, L: int, k: int = K_ANEL) -> list:
    """Por faixa: fração das células do snapshot em que a regra dispararia (célula ou vizinha elegível).
    Mede área do mapa, não alertas em trajetos (isso fica para a fase 2)."""
    eleg = elegiveis(snap, L)
    cels = sorted(snap.h3_cell.unique())
    out = []
    for f, nome, *_ in C.FAIXAS:
        n = sum(1 for c in cels if celulas_que_disparam(c, f, eleg, k))
        out.append(dict(faixa=f, faixa_nome=nome, celulas_que_disparam=n, celulas_snapshot=len(cels),
                        fracao=round(n / len(cels), 6)))
    return out


def montar(snap: pd.DataFrame, snapshot_sha256: str, L: int = L_PADRAO, contrato: int = 2) -> dict:
    v = VERSOES[contrato]
    niveis = sorted(int(v) for v in snap.nivel.dropna().unique())
    if L not in niveis:
        raise ValueError(f"L={L} não existe no snapshot (níveis {niveis}); a política não alerta")
    return dict(
        politica="proximidade", versao=1, natureza=NATUREZA.format(janela=v["janela"]), test_seen=True,
        snapshot_csv=f"ml/dados/{v['pasta'].name}/{v['csv']}", snapshot_csv_sha256=snapshot_sha256,
        contrato_snapshot_versao=contrato,
        L=L, k_anel=K_ANEL, cooldown_min=COOLDOWN_MIN, fuso=FUSO,
        faixas=[dict(faixa=f, faixa_nome=n, inicio_min=i, fim_min=fim) for f, n, i, fim in C.FAIXAS],
        regra=[
            "Avaliar a cada atualização de posição do aparelho e também na troca de faixa horária.",
            "Faixa vigente = hora local do aparelho convertida para America/Sao_Paulo, bordas [início, fim) do contrato v2.",
            "Célula elegível = chave (h3_cell, faixa vigente) com status com_dado e nivel >= L.",
            "Dispara se alguma célula de grid_disk(célula atual, k_anel) for elegível (anel completo, sem direção).",
            "Cada célula elegível dispara no máximo uma vez a cada cooldown_min minutos.",
            "Chave sem_dado nunca dispara e nunca é exibida como segura; na consulta mostra 'dados insuficientes para exibição'.",
            "Se snapshot_csv_sha256 não bater com o snapshot carregado, a política não alerta e registra o erro.",
        ],
        texto_alerta=TEXTO.format(janela=v["janela"]), texto_sem_dado=TEXTO_SEM_DADO,
        nao_afirma=["distância ou antecedência mínima", "segurança de qualquer área", "tempo real",
                    "orçamento de alertas em trajetos (fase 2)"],
        tabela_por_L=tabela_por_nivel(snap),
        tabela_rotulo="frações de chaves históricas (retrospectiva, test_seen=true); não é orçamento de área nem de alertas",
        cobertura_anel_por_faixa=cobertura_do_anel(snap, L),
        sensibilidade_p90=sensibilidade_p90(snap),
    )


def gravar(destino=DESTINO, L: int = L_PADRAO, contrato: int = 2) -> dict:
    v = VERSOES[contrato]
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    csv = v["pasta"] / v["csv"]
    snap = ler_snapshot(csv)
    h_snap = sha256_arquivo(csv)
    manifest = json.loads((v["pasta"] / "manifest.json").read_text())
    assert manifest["csv_sha256"] == h_snap, f"snapshot diverge do manifest v{contrato}"
    assert manifest["contrato_versao"] == contrato, "manifest de outra versão do contrato"
    pol = montar(snap, h_snap, L, contrato)
    nome = v["nome"]
    arq = destino / nome
    arq.write_text(json.dumps(pol, ensure_ascii=False, indent=2) + "\n")
    h = sha256_arquivo(arq)
    (destino / f"{nome}.sha256").write_text(f"{h}  {nome}\n")
    return dict(arquivo=str(arq), sha256=h, politica=pol)


if __name__ == "__main__":
    r = gravar(contrato=int(sys.argv[1]) if len(sys.argv) > 1 else 2)
    print(r["arquivo"], r["sha256"])
    for linha in r["politica"]["tabela_por_L"]:
        print(linha)
    print(r["politica"]["cobertura_anel_por_faixa"])
    print(r["politica"]["sensibilidade_p90"])
