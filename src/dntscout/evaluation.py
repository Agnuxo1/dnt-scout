"""Validation that answers the laboratory question: how many assays to find the positives.

Three pieces, in the order the plan ranks them:

1. `enrichment_curve` — the headline result. Given a ranking of untested chemicals, how many MEA
   runs are needed to recover the positives, against random selection and against read-across.
2. `scaffold_groups` / `grouped_cv` — Bemis-Murcko groups, so a model is never scored on a
   scaffold it was trained on, and every bootstrap resamples *groups*, not rows.
3. `MondrianConformal` — class-conditional conformal prediction with an explicit applicability
   domain, reporting the set sizes honestly, including when they are uninformative.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

RNG_SEED = 20261023


# --------------------------------------------------------------------------- splits


def scaffold_groups(scaffolds) -> np.ndarray:
    """Map scaffold strings to integer group ids (stable, sorted by first appearance)."""
    seen: dict[str, int] = {}
    out = []
    for s in scaffolds:
        out.append(seen.setdefault(s, len(seen)))
    return np.asarray(out, dtype=int)


def grouped_folds(groups: np.ndarray, y: np.ndarray, n_folds: int = 5, seed: int = RNG_SEED):
    """Group k-fold that keeps whole scaffolds together and balances *both* positives and size.

    Two passes, because balancing only one of the two corrupts the comparison: unequal fold sizes
    make the training prevalence swing between folds, and a model with a per-fold intercept (the
    prevalence baseline, for one) then scores far from chance for a purely bookkeeping reason.

    Pass 1 spreads the groups that contain positives over the folds with the fewest positives so
    far. Pass 2 fills with the positive-free groups, largest first, into the fold holding the
    fewest chemicals. Ties are broken by the other quantity, so neither drifts.
    """
    y = np.asarray(y)
    uniq = np.unique(groups)
    rng = np.random.default_rng(seed)
    rng.shuffle(uniq)
    pos = {g: int(y[groups == g].sum()) for g in uniq}
    size = {g: int((groups == g).sum()) for g in uniq}
    fold_pos = np.zeros(n_folds, dtype=int)
    fold_n = np.zeros(n_folds, dtype=int)
    assign: dict[int, int] = {}
    for g in sorted([g for g in uniq if pos[g] > 0], key=lambda g: (-pos[g], -size[g])):
        k = int(np.lexsort((fold_n, fold_pos))[0])          # fewest positives, then fewest rows
        assign[g] = k
        fold_pos[k] += pos[g]
        fold_n[k] += size[g]
    for g in sorted([g for g in uniq if pos[g] == 0], key=lambda g: -size[g]):
        k = int(np.lexsort((fold_pos, fold_n))[0])          # fewest rows, then fewest positives
        assign[g] = k
        fold_n[k] += size[g]
    fold_of = np.array([assign[g] for g in groups], dtype=int)
    return [(np.where(fold_of != k)[0], np.where(fold_of == k)[0]) for k in range(n_folds)]


# --------------------------------------------------------------------- enrichment


@dataclass
class Enrichment:
    """Assays needed to find a given share of the positives, for one ranking strategy."""
    name: str
    n: int
    n_pos: int
    tests_for: dict[int, int] = field(default_factory=dict)   # % of positives -> assays needed
    hits_at: dict[int, int] = field(default_factory=dict)     # budget (assays) -> positives found
    ef_at: dict[int, float] = field(default_factory=dict)     # budget -> enrichment factor
    ci_ef: dict[int, tuple[float, float]] = field(default_factory=dict)


def _tests_needed(hit_order: np.ndarray, share: float) -> int:
    """Index (1-based) of the assay at which `share` of all positives has been recovered."""
    total = int(hit_order.sum())
    if total == 0:
        return -1
    need = int(np.ceil(share * total))
    cum = np.cumsum(hit_order)
    return int(np.argmax(cum >= need) + 1)


def enrichment_curve(scores: np.ndarray, y: np.ndarray, groups: np.ndarray | None = None,
                     name: str = "model", budgets=(10, 20, 30, 50),
                     shares=(50, 80, 100), n_boot: int = 2000, seed: int = RNG_SEED) -> Enrichment:
    """Rank chemicals by `scores` (high = test first) and measure the assay budget needed.

    `ef_at[b]` is the enrichment factor: positives found in the first `b` assays divided by the
    positives a random order would find on average. Confidence intervals resample *groups*
    (scaffolds) when given, because chemicals from one scaffold are not independent evidence.
    """
    scores, y = np.asarray(scores, dtype=float), np.asarray(y, dtype=int)
    assert scores.shape == y.shape and scores.ndim == 1
    n, n_pos = len(y), int(y.sum())
    order = np.argsort(-scores, kind="stable")
    hit = y[order]
    e = Enrichment(name=name, n=n, n_pos=n_pos)
    if n_pos == 0:
        return e
    prevalence = n_pos / n
    for s in shares:
        e.tests_for[s] = _tests_needed(hit, s / 100)
    rng = np.random.default_rng(seed)
    g = np.asarray(groups) if groups is not None else np.arange(n)
    uniq = np.unique(g)
    for b in budgets:
        b_eff = min(b, n)
        found = int(hit[:b_eff].sum())
        e.hits_at[b] = found
        expected = prevalence * b_eff
        e.ef_at[b] = float(found / expected) if expected > 0 else float("nan")
        boot = np.empty(n_boot)
        for i in range(n_boot):
            pick = rng.choice(uniq, size=len(uniq), replace=True)
            idx = np.concatenate([np.where(g == gg)[0] for gg in pick])
            o = idx[np.argsort(-scores[idx], kind="stable")]
            hb = y[o]
            bb = min(b_eff, len(hb))
            prev_b = y[idx].mean()
            boot[i] = (hb[:bb].sum() / (prev_b * bb)) if prev_b > 0 and bb > 0 else np.nan
        lo, hi = np.nanpercentile(boot, [2.5, 97.5])
        e.ci_ef[b] = (float(lo), float(hi))
    return e


def random_baseline_ef(y: np.ndarray, budgets=(10, 20, 30, 50), n_rep: int = 2000,
                       seed: int = RNG_SEED) -> dict[int, tuple[float, float, float]]:
    """Enrichment factor of random selection: mean and 95% range. Should straddle 1.0."""
    y = np.asarray(y, dtype=int)
    rng = np.random.default_rng(seed)
    prevalence = y.mean()
    out = {}
    for b in budgets:
        b_eff = min(b, len(y))
        vals = np.array([y[rng.permutation(len(y))][:b_eff].sum() / (prevalence * b_eff)
                         for _ in range(n_rep)])
        lo, hi = np.percentile(vals, [2.5, 97.5])
        out[b] = (float(vals.mean()), float(lo), float(hi))
    return out


# ---------------------------------------------------------------------- conformal


@dataclass
class MondrianConformal:
    """Class-conditional (Mondrian) conformal prediction for a binary outcome.

    Calibrated per class so that coverage holds for positives and negatives separately — the
    relevant guarantee when positives are scarce. `predict_set` returns one of {0}, {1}, {0,1}
    (uninformative) or set() (rejected: the label is implausible at this confidence), plus an
    applicability-domain decision based on similarity to the training set.

    The exchangeability assumption behind the guarantee is weakened by a scaffold shift; that is
    exactly why `report` prints the empirical coverage on held-out scaffolds instead of claiming it.
    """
    alpha: float = 0.10
    ad_threshold: float | None = None   # minimum max-Tanimoto to training to accept a prediction
    q: dict[int, float] = field(default_factory=dict)

    def fit(self, p_cal: np.ndarray, y_cal: np.ndarray) -> "MondrianConformal":
        """`p_cal` = predicted probability of the positive class on a calibration split."""
        p_cal, y_cal = np.asarray(p_cal, dtype=float), np.asarray(y_cal, dtype=int)
        for c in (0, 1):
            s = 1.0 - np.where(y_cal[y_cal == c] == 1, p_cal[y_cal == c], 1 - p_cal[y_cal == c])
            if len(s) == 0:
                self.q[c] = 1.0
                continue
            k = int(np.ceil((len(s) + 1) * (1 - self.alpha))) - 1
            k = min(max(k, 0), len(s) - 1)
            self.q[c] = float(np.sort(s)[k])
        return self

    def predict_set(self, p: np.ndarray, similarity: np.ndarray | None = None):
        """Return (sets, in_domain). `similarity` = max Tanimoto of each query to the training set."""
        p = np.asarray(p, dtype=float)
        sets = []
        for pi in p:
            s = set()
            if (1.0 - pi) <= self.q.get(1, 1.0):
                s.add(1)
            if (1.0 - (1.0 - pi)) <= self.q.get(0, 1.0):
                s.add(0)
            sets.append(s)
        if similarity is None or self.ad_threshold is None:
            in_dom = np.ones(len(p), dtype=bool)
        else:
            in_dom = np.asarray(similarity, dtype=float) >= self.ad_threshold
        return sets, in_dom

    @staticmethod
    def report(sets, in_dom, y_true) -> dict:
        """Empirical coverage and set sizes — including how often the set is uninformative."""
        y_true = np.asarray(y_true, dtype=int)
        sizes = np.array([len(s) for s in sets])
        covered = np.array([int(y in s) for s, y in zip(sets, y_true)])
        out = {
            "n": int(len(y_true)),
            "coverage_all": float(covered.mean()) if len(y_true) else float("nan"),
            "mean_set_size": float(sizes.mean()) if len(sizes) else float("nan"),
            "share_singleton": float((sizes == 1).mean()) if len(sizes) else float("nan"),
            "share_uninformative": float((sizes == 2).mean()) if len(sizes) else float("nan"),
            "share_rejected": float((sizes == 0).mean()) if len(sizes) else float("nan"),
            "share_out_of_domain": float(1 - np.mean(in_dom)) if len(in_dom) else float("nan"),
        }
        for c in (0, 1):
            m = y_true == c
            out[f"coverage_class_{c}"] = float(covered[m].mean()) if m.any() else float("nan")
            out[f"n_class_{c}"] = int(m.sum())
        if np.any(in_dom):
            out["coverage_in_domain"] = float(covered[in_dom].mean())
            out["mean_set_size_in_domain"] = float(sizes[in_dom].mean())
        return out
