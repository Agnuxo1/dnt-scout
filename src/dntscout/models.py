"""Models, in increasing order of ambition. With ~240 chemicals, the baselines matter most.

- `Prevalence`: predicts the training positive rate. The floor any claim must clear.
- `ReadAcross`: similarity-weighted nearest neighbours on Morgan fingerprints — the approach US EPA
  generalised read-across (GenRA) is built on, and the reference a structural model has to beat.
  This is a read-across *of the GenRA kind*, re-implemented here; it is not the EPA GenRA service.
- `Structural`: regularised logistic regression and a random forest over fingerprints + MACCS +
  physicochemical descriptors.

Every model exposes `fit(X, y)` and `predict_proba1(X)`, so the evaluation code never needs to know
which one it is holding. Model selection happens inside each training fold, never on the test split.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .evaluation import RNG_SEED


class Prevalence:
    name = "prevalence"

    def fit(self, X, y):
        self.p_ = float(np.mean(y))
        return self

    def predict_proba1(self, X):
        return np.full(len(X), self.p_, dtype=float)


@dataclass
class ReadAcross:
    """GenRA-style similarity-weighted kNN over a precomputed Tanimoto similarity matrix.

    Unlike the sklearn models, this one consumes similarities rather than features, because that is
    what read-across is: a weighted vote of the measured analogues. `k` and the similarity floor are
    chosen inside the training fold.
    """
    k: int = 10
    min_sim: float = 0.0
    name: str = "read_across"

    def fit_sim(self, y_train: np.ndarray) -> "ReadAcross":
        self.y_train_ = np.asarray(y_train, dtype=float)
        return self

    def predict_proba1_sim(self, sim: np.ndarray) -> np.ndarray:
        """`sim` = (n_query, n_train) Tanimoto similarities to the training chemicals."""
        sim = np.asarray(sim, dtype=float)
        assert sim.shape[1] == len(self.y_train_), (sim.shape, len(self.y_train_))
        out = np.empty(sim.shape[0], dtype=float)
        base = float(self.y_train_.mean())
        for i, row in enumerate(sim):
            idx = np.argsort(-row)[: self.k]
            w = row[idx]
            keep = w >= self.min_sim
            if not keep.any() or w[keep].sum() <= 0:
                out[i] = base          # no analogue above the floor: fall back to prevalence
                continue
            out[i] = float(np.average(self.y_train_[idx][keep], weights=w[keep]))
        return out

    @staticmethod
    def max_similarity(sim: np.ndarray) -> np.ndarray:
        """Applicability-domain signal: similarity to the nearest training analogue."""
        return np.asarray(sim, dtype=float).max(axis=1)


def logistic(C: float = 1.0):
    m = make_pipeline(StandardScaler(with_mean=False),
                      LogisticRegression(C=C, max_iter=5000, class_weight="balanced",
                                         random_state=RNG_SEED))
    return _SkWrap(m, f"logistic_C{C:g}")


def forest(n_estimators: int = 500, min_samples_leaf: int = 2):
    m = RandomForestClassifier(n_estimators=n_estimators, min_samples_leaf=min_samples_leaf,
                               class_weight="balanced_subsample", n_jobs=4, random_state=RNG_SEED)
    return _SkWrap(m, f"forest_{n_estimators}_{min_samples_leaf}")


class _SkWrap:
    def __init__(self, est, name):
        self.est, self.name = est, name

    def fit(self, X, y):
        self.est.fit(X, y)
        return self

    def predict_proba1(self, X):
        p = self.est.predict_proba(X)
        classes = getattr(self.est, "classes_", None)
        if classes is None:
            classes = self.est[-1].classes_
        j = int(np.where(classes == 1)[0][0])
        return p[:, j]


def physchem_only(X: np.ndarray, n_desc: int) -> np.ndarray:
    """The last `n_desc` columns of the feature matrix: the cheap physicochemical baseline."""
    return X[:, -n_desc:]
