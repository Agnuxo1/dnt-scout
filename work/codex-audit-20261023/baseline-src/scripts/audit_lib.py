"""One honest CV engine, reused by every audit experiment.

`02_evaluate.py` interleaves the cross-validation loop with reporting, so an audit that wants to
change one thing (the split, the similarity a model may use, which chemicals are positives) would
have to copy it and risk diverging. This module factors the loop out once, with the knobs the audit
needs, and keeps the same inner-selection rules so the comparison stays like-for-like.

Nothing here invents a new method: the models, grids and conformal procedure are the project's own.
What is new is that the caller can impose a *similarity cap* (hide training analogues that are too
close to the test chemical) and that metrics are reported both pooled across folds and per fold,
because those two disagree and the disagreement is itself a finding.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, "src")

from dntscout.evaluation import RNG_SEED, grouped_folds  # noqa: E402
from dntscout.models import Prevalence, ReadAcross, forest, logistic  # noqa: E402

MODELS = ("prevalence", "physchem_logistic", "read_across", "fingerprint_forest")


# --------------------------------------------------------------- inner selection


def _inner_readacross(sim_tr, y_tr, groups_tr, cap=None):
    best, best_score = None, -np.inf
    for k in (3, 5, 10, 20):
        for min_sim in (0.0, 0.2, 0.3):
            preds = np.zeros(len(y_tr))
            for itr, ite in grouped_folds(groups_tr, y_tr, n_folds=3, seed=RNG_SEED + 1):
                s = sim_tr[np.ix_(ite, itr)]
                if cap is not None:
                    s = np.where(s >= cap, 0.0, s)
                ra = ReadAcross(k=k, min_sim=min_sim).fit_sim(y_tr[itr])
                preds[ite] = ra.predict_proba1_sim(s)
            sc = average_precision_score(y_tr, preds) if len(set(y_tr)) > 1 else 0.0
            if sc > best_score:
                best, best_score = ReadAcross(k=k, min_sim=min_sim), sc
    return best


def _inner_sk(X_tr, y_tr, groups_tr, kind):
    grid = ([logistic(C) for C in (0.01, 0.1, 1.0)] if kind == "logistic"
            else [forest(400, leaf) for leaf in (1, 2, 4)])
    best, best_score = None, -np.inf
    for cand in grid:
        preds = np.zeros(len(y_tr))
        for itr, ite in grouped_folds(groups_tr, y_tr, n_folds=3, seed=RNG_SEED + 1):
            m = cand.__class__(cand.est, cand.name).fit(X_tr[itr], y_tr[itr])
            preds[ite] = m.predict_proba1(X_tr[ite])
        sc = average_precision_score(y_tr, preds) if len(set(y_tr)) > 1 else 0.0
        if sc > best_score:
            best, best_score = cand, sc
    return best


# ------------------------------------------------------------------------ result


@dataclass
class CVResult:
    """Out-of-fold scores plus the fold index each one came from.

    Keeping `fold_of` is the point: a pooled metric mixes scores produced by five different
    models, and without the fold index you cannot tell whether a ranking is real or an artefact of
    five incomparable score scales.
    """
    oof: dict[str, np.ndarray]
    fold_of: np.ndarray
    y: np.ndarray
    groups: np.ndarray
    nn_sim: np.ndarray
    chosen: dict[str, list] = field(default_factory=dict)
    extra_scores: dict[str, np.ndarray] = field(default_factory=dict)  # held-out extras, per model

    def pooled(self, metric, model):
        return float(metric(self.y, self.oof[model]))

    def per_fold(self, metric, model):
        """The metric computed inside each fold, where scores ARE comparable."""
        vals = []
        for f in np.unique(self.fold_of):
            m = self.fold_of == f
            if len(set(self.y[m])) < 2:
                continue
            vals.append(float(metric(self.y[m], self.oof[model][m])))
        return np.array(vals)

    def rank_pooled(self, model):
        """Scores converted to within-fold percentile ranks, then pooled.

        This is the pooled ranking a careful referee would ask for: it removes any fold-level
        offset in the score scale while preserving each model's ordering inside its own fold.
        """
        r = np.zeros(len(self.y))
        for f in np.unique(self.fold_of):
            m = self.fold_of == f
            s = self.oof[model][m]
            # average ranks for ties, mapped to (0,1]
            order = np.argsort(s, kind="stable")
            ranks = np.empty(len(s), dtype=float)
            ranks[order] = np.arange(1, len(s) + 1)
            for v in np.unique(s):
                tie = s == v
                ranks[tie] = ranks[tie].mean()
            r[m] = ranks / (len(s) + 1)
        return r


# -------------------------------------------------------------------- the engine


def run_cv(X, X_desc, sim, y, groups, folds, cap=None, X_extra=None, sim_extra=None,
           models=MODELS, verbose=False) -> CVResult:
    """One cross-validation pass.

    cap        hide any training analogue whose Tanimoto to the test chemical is >= cap.
               `None` = the project's own setting (no cap). Used to ask whether read-across wins
               because it generalises or because near-identical analogues sit in the training set.
    X_extra    optional extra chemicals that are NEVER trained on and NEVER scored as part of the
               evaluation set, only ranked by every fold's model (used for the 28 inconclusive
               cytotoxicants). Their scores are averaged over folds.
    """
    y = np.asarray(y, dtype=int)
    oof = {k: np.zeros(len(y)) for k in models}
    fold_of = np.full(len(y), -1, dtype=int)
    nn_sim = np.zeros(len(y))
    chosen = {k: [] for k in models}
    n_extra = 0 if X_extra is None else len(X_extra)
    extra = {k: np.zeros((len(folds), n_extra)) for k in models} if n_extra else {}

    for f, (tr, te) in enumerate(folds):
        y_tr, g_tr = y[tr], groups[tr]
        fold_of[te] = f
        s_te = sim[np.ix_(te, tr)]
        if cap is not None:
            s_te = np.where(s_te >= cap, 0.0, s_te)
        nn_sim[te] = s_te.max(axis=1) if s_te.shape[1] else 0.0

        if "prevalence" in models:
            oof["prevalence"][te] = Prevalence().fit(X[tr], y_tr).predict_proba1(X[te])
            chosen["prevalence"].append("prevalence")
            if n_extra:
                extra["prevalence"][f] = float(y_tr.mean())

        if "read_across" in models:
            ra = _inner_readacross(sim[np.ix_(tr, tr)], y_tr, g_tr, cap=cap).fit_sim(y_tr)
            oof["read_across"][te] = ra.predict_proba1_sim(s_te)
            chosen["read_across"].append("k=%d,min_sim=%g" % (ra.k, ra.min_sim))
            if n_extra:
                se = sim_extra[:, tr]
                if cap is not None:
                    se = np.where(se >= cap, 0.0, se)
                extra["read_across"][f] = ra.predict_proba1_sim(se)

        if "physchem_logistic" in models:
            m = _inner_sk(X_desc[tr], y_tr, g_tr, "logistic").fit(X_desc[tr], y_tr)
            oof["physchem_logistic"][te] = m.predict_proba1(X_desc[te])
            chosen["physchem_logistic"].append(m.name)
            if n_extra:
                extra["physchem_logistic"][f] = m.predict_proba1(X_extra[:, -X_desc.shape[1]:])

        if "fingerprint_forest" in models:
            sel = _inner_sk(X[tr], y_tr, g_tr, "forest")
            m = sel.__class__(sel.est, sel.name).fit(X[tr], y_tr)
            oof["fingerprint_forest"][te] = m.predict_proba1(X[te])
            chosen["fingerprint_forest"].append(m.name)
            if n_extra:
                extra["fingerprint_forest"][f] = m.predict_proba1(X_extra)
        if verbose:
            print("    fold %d: train %d test %d" % (f, len(tr), len(te)))

    assert (fold_of >= 0).all(), "every chemical must be tested exactly once"
    return CVResult(oof=oof, fold_of=fold_of, y=y, groups=groups, nn_sim=nn_sim, chosen=chosen,
                    extra_scores={k: v.mean(axis=0) for k, v in extra.items()})


# ------------------------------------------------------------------- enrichment


def assays_for_share(scores, y, share=0.5):
    """Assays needed to recover `share` of the positives when testing in score order."""
    y = np.asarray(y, dtype=int)
    total = int(y.sum())
    if total == 0:
        return -1
    hit = y[np.argsort(-np.asarray(scores, dtype=float), kind="stable")]
    need = int(np.ceil(share * total))
    return int(np.argmax(np.cumsum(hit) >= need) + 1)


def assays_random(y, share=0.5, n_rep=20000, seed=RNG_SEED):
    """The same quantity under random testing order: mean and 95% range, not just the mean."""
    y = np.asarray(y, dtype=int)
    rng = np.random.default_rng(seed)
    need = int(np.ceil(share * y.sum()))
    vals = np.empty(n_rep, dtype=int)
    for i in range(n_rep):
        hit = y[rng.permutation(len(y))]
        vals[i] = int(np.argmax(np.cumsum(hit) >= need) + 1)
    return float(vals.mean()), int(np.percentile(vals, 2.5)), int(np.percentile(vals, 97.5))


def cluster_bootstrap_ci(fn, groups, n_boot=2000, seed=RNG_SEED):
    """Percentile CI from resampling whole scaffold groups. `fn(idx) -> float or nan`."""
    rng = np.random.default_rng(seed)
    uniq = np.unique(groups)
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([np.where(groups == g)[0] for g in pick])
        v = fn(idx)
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    return tuple(float(x) for x in np.percentile(vals, [2.5, 97.5]))


def auc_safe(y, p):
    return roc_auc_score(y, p) if len(set(np.asarray(y))) > 1 else float("nan")
