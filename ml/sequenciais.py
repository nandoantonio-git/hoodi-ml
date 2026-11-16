"""T025b/T025c: LSTM sobre a série mensal de cada chave e KMeans+PCA com nível por cluster.

Os dois seguem a interface fit(X, y) / predict(X) de `ml.modelos`, em que X é o DataFrame de
`features.exemplos` (índice celula, faixa; coluna origem). Entraram depois de ago–set ter sido visto:
são exploração adicional, nunca a escolha pré-registrada (T026).
"""
import numpy as np
import pandas as pd
import torch
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml import config as C
from ml import features

EPOCAS = 60
_MESES = {}  # (id do DataFrame, mês) → features daquele mês; o DataFrame `u` não muda durante a execução
torch.set_num_threads(4)


def _mes(u, m):
    k = (id(u), m)
    if k not in _MESES:
        _MESES[k] = (u, features.construir(u, [m]))  # guarda u para o id não ser reaproveitado
    return _MESES[k][1]


def serie(u: pd.DataFrame, X: pd.DataFrame) -> np.ndarray:
    """(n_chaves, n_meses, n_features): features de cada mês da janela de features da origem, isolado.

    Só usa meses de C.ORIGENS[origem]["features"]; chave sem registro num mês tem 0 naquele passo."""
    origem = X.origem.iloc[0]
    assert (X.origem == origem).all()
    passos = []
    for m in C.ORIGENS[origem]["features"]:
        Xm = _mes(u, m).reindex(X.index)
        Xm["faixa"] = X.index.get_level_values("faixa").astype(float)
        passos.append(Xm[features.COLUNAS_X].fillna(0.0).values)
    return np.stack(passos, axis=1).astype(np.float32)


class _Rede(torch.nn.Module):
    def __init__(self, n_in, hidden, dropout):
        super().__init__()
        self.lstm = torch.nn.LSTM(n_in, hidden, batch_first=True)
        self.drop = torch.nn.Dropout(dropout)
        self.saida = torch.nn.Linear(hidden, 4)

    def forward(self, x):
        _, (h, _) = self.lstm(x)
        return self.saida(self.drop(h[-1]))


class LSTMNivel:
    """Uma série por chave; origens com comprimentos diferentes são lotes separados (sem preenchimento)."""

    def __init__(self, u, hidden_size, learning_rate, dropout):
        self.u, self.hidden, self.lr, self.dropout = u, hidden_size, learning_rate, dropout
        self.historico = []

    def _lotes(self, X):
        return [(o, serie(self.u, X[X.origem == o])) for o in dict.fromkeys(X.origem)]

    def fit(self, X, y):
        torch.manual_seed(C.SEMENTE)
        np.random.seed(C.SEMENTE)
        lotes = self._lotes(X)
        ys = [np.asarray(y)[(X.origem == o).values] for o, _ in lotes]
        tudo = np.concatenate([s.reshape(-1, s.shape[-1]) for _, s in lotes])
        self.media, self.desvio = tudo.mean(0), tudo.std(0) + 1e-6  # só do treino
        self.rede = _Rede(tudo.shape[-1], self.hidden, self.dropout)
        cont = np.bincount(np.concatenate(ys), minlength=4).astype(float)
        peso = torch.tensor(cont.sum() / (4 * np.maximum(cont, 1)), dtype=torch.float32)
        perda = torch.nn.CrossEntropyLoss(weight=peso)
        opt = torch.optim.Adam(self.rede.parameters(), lr=self.lr)
        tens = [(torch.tensor((s - self.media) / self.desvio), torch.tensor(yy, dtype=torch.long))
                for (_, s), yy in zip(lotes, ys)]
        self.rede.train()
        for _ in range(EPOCAS):
            total = 0.0
            for xb, yb in tens:
                opt.zero_grad()
                l = perda(self.rede(xb), yb)
                l.backward()
                opt.step()
                total += float(l.detach()) * len(yb)
            self.historico.append(total / sum(len(t[1]) for t in tens))
        return self

    def predict(self, X):
        self.rede.eval()
        out = np.empty(len(X), dtype=int)
        with torch.no_grad():
            for o, s in self._lotes(X):
                xb = torch.tensor((s - self.media) / self.desvio)
                out[(X.origem == o).values] = self.rede(xb).argmax(1).numpy()
        return out


class KMeansPCANivel:
    """Padroniza → PCA → KMeans; cada cluster recebe o nível mais frequente do treino (mapa só do treino)."""

    def __init__(self, n_components, n_clusters, whiten):
        self.pipe = make_pipeline(StandardScaler(), PCA(n_components=n_components, whiten=whiten,
                                                        random_state=C.SEMENTE),
                                  KMeans(n_clusters=n_clusters, n_init=10, random_state=C.SEMENTE))

    def fit(self, X, y):
        y = np.asarray(y)
        c = self.pipe.fit_predict(X[features.COLUNAS_X].values)
        geral = int(np.bincount(y, minlength=4).argmax())
        self.mapa = {k: int(np.bincount(y[c == k], minlength=4).argmax()) if (c == k).any() else geral
                     for k in range(self.pipe[-1].n_clusters)}
        return self

    def clusters(self, X):
        return self.pipe.predict(X[features.COLUNAS_X].values)

    def predict(self, X):
        return np.array([self.mapa[k] for k in self.clusters(X)])
