#!/usr/bin/env python
"""Can structure prioritise which chemicals deserve an MEA run? Scaffold-held-out evaluation.

    python scripts/02_evaluate.py --data data/processed --out results

Every number this project reports comes from here. The design follows the rules the plan fixed
*before* any result was seen:

* Chemicals are grouped by Bemis-Murcko scaffold; a model is never scored on a scaffold it trained
  on, and the 5 folds are balanced on positives so that no fold is scored with none.
* Hyperparameters and the conformal calibration split are chosen strictly inside each training
  fold. The test fold is touched once, to predict.
* The headline result is the enrichment curve: assays needed to recover the positives, against
  random selection and against similarity read-across of the GenRA kind.
* Confidence intervals resample scaffold groups, never individual chemicals.
* Conformal coverage is *measured* on held-out scaffolds, not assumed: a scaffold shift breaks the
  exchangeability the theory needs, and the report says so by showing the empirical number.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score

from dntscout import chem
from dntscout.evaluation import (RNG_SEED, MondrianConformal, enrichment_curve, grouped_folds,
                                 random_baseline_ef, scaffold_groups)
from dntscout.models import Prevalence, ReadAcross, forest, logistic

BUDGETS = (10, 20, 30, 50)
N_FOLDS = 5
ALPHA = 0.10            # 90% conformal confidence, fixed in the plan


def inner_select_readacross(sim_tr: np.ndarray, y_tr: np.ndarray, groups_tr: np.ndarray) -> ReadAcross:
    """Choose k and the similarity floor by grouped CV inside the training fold only."""
    best, best_score = None, -np.inf
    for k in (3, 5, 10, 20):
        for min_sim in (0.0, 0.2, 0.3):
            preds = np.zeros(len(y_tr))
            for itr, ite in grouped_folds(groups_tr, y_tr, n_folds=3, seed=RNG_SEED + 1):
                ra = ReadAcross(k=k, min_sim=min_sim).fit_sim(y_tr[itr])
                preds[ite] = ra.predict_proba1_sim(sim_tr[np.ix_(ite, itr)])
            s = average_precision_score(y_tr, preds) if len(set(y_tr)) > 1 else 0.0
            if s > best_score:
                best, best_score = ReadAcross(k=k, min_sim=min_sim), s
    return best


def inner_select_sk(X_tr: np.ndarray, y_tr: np.ndarray, groups_tr: np.ndarray, kind: str):
    """Small, pre-declared grid. Selection by grouped PR-AUC inside the training fold."""
    grid = ([logistic(C) for C in (0.01, 0.1, 1.0)] if kind == "logistic"
            else [forest(400, leaf) for leaf in (1, 2, 4)])
    best, best_score = None, -np.inf
    for cand in grid:
        preds = np.zeros(len(y_tr))
        for itr, ite in grouped_folds(groups_tr, y_tr, n_folds=3, seed=RNG_SEED + 1):
            m = cand.__class__(cand.est, cand.name).fit(X_tr[itr], y_tr[itr])
            preds[ite] = m.predict_proba1(X_tr[ite])
        s = average_precision_score(y_tr, preds) if len(set(y_tr)) > 1 else 0.0
        if s > best_score:
            best, best_score = cand, s
    return best


def group_bootstrap_ci(metric, y: np.ndarray, p: np.ndarray, groups: np.ndarray,
                       n_boot: int = 2000, seed: int = RNG_SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    uniq = np.unique(groups)
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([np.where(groups == g)[0] for g in pick])
        if len(set(y[idx])) < 2:
            continue
        vals.append(metric(y[idx], p[idx]))
    if not vals:
        return (float("nan"), float("nan"))
    return tuple(float(v) for v in np.percentile(vals, [2.5, 97.5]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/processed")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    data, out = Path(a.data), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(data / "chemicals_labelled.parquet")
    kept = df[(df.y.notna()) & (df.structure_ok) & (df.smiles.notna())].reset_index(drop=True)
    y = kept.y.astype(int).to_numpy()
    groups = scaffold_groups(kept.scaffold.tolist())
    print(f"modelling {len(kept)} chemicals ({y.sum()} selective, {len(y) - y.sum()} no effect) "
          f"in {len(np.unique(groups))} scaffold groups")
    print(f"excluded and reported, never counted as negatives: "
          f"{json.dumps(df[df.y.isna()].label.value_counts().to_dict())}")

    X, names = chem.feature_matrix(kept.smiles.tolist())
    n_desc = len(chem.DESCRIPTORS)
    X_desc = X[:, -n_desc:]
    sim = chem.tanimoto_matrix(kept.smiles.tolist(), kept.smiles.tolist())
    np.fill_diagonal(sim, 0.0)          # a chemical is never its own analogue

    folds = grouped_folds(groups, y, n_folds=N_FOLDS)
    oof = {k: np.zeros(len(y)) for k in
           ("prevalence", "physchem_logistic", "read_across", "fingerprint_forest")}
    chosen: dict[str, list[str]] = {k: [] for k in oof}
    cp_sets: list[set] = [set()] * len(y)
    cp_indomain = np.zeros(len(y), dtype=bool)
    nn_sim = np.zeros(len(y))

    for f, (tr, te) in enumerate(folds):
        y_tr, g_tr = y[tr], groups[tr]
        oof["prevalence"][te] = Prevalence().fit(X[tr], y_tr).predict_proba1(X[te])
        chosen["prevalence"].append("prevalence")

        ra = inner_select_readacross(sim[np.ix_(tr, tr)], y_tr, g_tr).fit_sim(y_tr)
        oof["read_across"][te] = ra.predict_proba1_sim(sim[np.ix_(te, tr)])
        chosen["read_across"].append(f"k={ra.k},min_sim={ra.min_sim}")
        nn_sim[te] = ReadAcross.max_similarity(sim[np.ix_(te, tr)])

        m_desc = inner_select_sk(X_desc[tr], y_tr, g_tr, "logistic").fit(X_desc[tr], y_tr)
        oof["physchem_logistic"][te] = m_desc.predict_proba1(X_desc[te])
        chosen["physchem_logistic"].append(m_desc.name)

        # the structural model, with an inner calibration split for conformal prediction
        m_fp = inner_select_sk(X[tr], y_tr, g_tr, "forest")
        inner = grouped_folds(g_tr, y_tr, n_folds=4, seed=RNG_SEED + 2)
        fit_idx, cal_idx = inner[0][0], inner[0][1]
        m_cal = m_fp.__class__(m_fp.est, m_fp.name).fit(X[tr][fit_idx], y_tr[fit_idx])
        p_cal = m_cal.predict_proba1(X[tr][cal_idx])
        ad_thr = float(np.percentile(ReadAcross.max_similarity(sim[np.ix_(tr[cal_idx], tr[fit_idx])]), 10))
        cp = MondrianConformal(alpha=ALPHA, ad_threshold=ad_thr).fit(p_cal, y_tr[cal_idx])
        m_full = m_fp.__class__(m_fp.est, m_fp.name).fit(X[tr], y_tr)
        p_te = m_full.predict_proba1(X[te])
        oof["fingerprint_forest"][te] = p_te
        chosen["fingerprint_forest"].append(f"{m_fp.name},ad>={ad_thr:.2f}")
        s, d = cp.predict_set(p_te, similarity=nn_sim[te])
        for j, i in enumerate(te):
            cp_sets[i] = s[j]
        cp_indomain[te] = d
        print(f"  fold {f}: train {len(tr)} test {len(te)} | "
              f"read-across {chosen['read_across'][-1]} | forest {chosen['fingerprint_forest'][-1]}")

    # ------------------------------------------------------------------ metrics
    results = {"n": int(len(y)), "n_positive": int(y.sum()), "prevalence": float(y.mean()),
               "n_scaffold_groups": int(len(np.unique(groups))), "n_folds": N_FOLDS,
               "alpha": ALPHA, "seed": RNG_SEED, "models": {}}
    for k, p in oof.items():
        thr = float(np.quantile(p, 1 - y.mean()))
        row = {
            "selected_per_fold": chosen[k],
            "roc_auc": float(roc_auc_score(y, p)),
            "pr_auc": float(average_precision_score(y, p)),
            "balanced_accuracy_at_prevalence": float(balanced_accuracy_score(y, (p >= thr).astype(int))),
        }
        row["roc_auc_ci95"] = group_bootstrap_ci(roc_auc_score, y, p, groups)
        row["pr_auc_ci95"] = group_bootstrap_ci(average_precision_score, y, p, groups)
        e = enrichment_curve(p, y, groups=groups, name=k, budgets=BUDGETS)
        row["enrichment"] = {"tests_for_percent_of_positives": e.tests_for,
                             "positives_found_at_budget": e.hits_at,
                             "enrichment_factor": e.ef_at,
                             "enrichment_factor_ci95": {str(b): e.ci_ef[b] for b in e.ci_ef}}
        results["models"][k] = row
        print(f"{k:>20}  ROC {row['roc_auc']:.3f}  PR {row['pr_auc']:.3f}  "
              f"EF@20 {e.ef_at[20]:.2f}  tests for 50% of positives: {e.tests_for[50]}")

    results["random_selection"] = {str(b): v for b, v in random_baseline_ef(y, budgets=BUDGETS).items()}
    results["conformal"] = MondrianConformal.report(cp_sets, cp_indomain, y)
    print("conformal: " + json.dumps({k: round(v, 3) if isinstance(v, float) else v
                                      for k, v in results["conformal"].items()}))

    # performance as a function of distance to the training set: where it can be trusted
    bands = [(0.0, 0.3), (0.3, 0.5), (0.5, 1.0)]
    by_sim = []
    p_best = oof["fingerprint_forest"]
    for lo, hi in bands:
        m = (nn_sim >= lo) & (nn_sim < hi) if hi < 1.0 else (nn_sim >= lo)
        if m.sum() >= 10 and len(set(y[m])) > 1:
            by_sim.append({"nearest_analogue_tanimoto": f"[{lo},{hi})", "n": int(m.sum()),
                           "n_positive": int(y[m].sum()),
                           "roc_auc": float(roc_auc_score(y[m], p_best[m])),
                           "pr_auc": float(average_precision_score(y[m], p_best[m]))})
    results["by_similarity_to_training"] = by_sim
    for b in by_sim:
        print(f"  similarity {b['nearest_analogue_tanimoto']}: n={b['n']} ROC {b['roc_auc']:.3f}")

    pred = kept[["Casrn", "DTXSID", "PREFERRED_NAME", "Compound", "smiles", "scaffold",
                 "label", "y", "ec50_network_min", "ec50_viability_min", "cohort"]].copy()
    for k, p in oof.items():
        pred[f"score_{k}"] = p
    pred["nearest_analogue_tanimoto"] = nn_sim
    pred["conformal_set"] = ["{" + ",".join(str(x) for x in sorted(s)) + "}" for s in cp_sets]
    pred["in_applicability_domain"] = cp_indomain
    pred.to_csv(out / "out_of_fold_predictions.csv", index=False)

    results["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out / "evaluation.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nwrote {out}/evaluation.json and {out}/out_of_fold_predictions.csv")


if __name__ == "__main__":
    main()
