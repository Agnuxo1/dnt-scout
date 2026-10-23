"""Adversarial audit, part 2: is the headline result real?

Eight questions. Each one is a way the result could be wrong, and each is answered by re-running the
project's own cross-validation with one thing changed.

  A  Pooled vs per-fold metrics. A constant-per-fold predictor must score exactly chance. The
     project reports ROC 0.473 for it, which can only come from pooling scores that five different
     models produced on five different scales. How much of every reported number is that artefact?
  B  One split, one seed, 102 chemicals. Repeat the whole evaluation over 20 fold assignments and
     look at the spread. The group bootstrap holds the split fixed, so it cannot see this.
  C  Similarity cap. Hide from the training set every analogue closer than T to the test chemical.
     If read-across keeps its lead at T = 0.7 and 0.5, it generalises; if the lead evaporates, it
     was recognising near-duplicates.
  D  Cluster split. 72% of scaffold groups hold a single chemical, so scaffold-held-out is nearly
     leave-one-out. Butina clustering at 0.6 similarity gives a genuinely harder split.
  E  The 28 excluded cytotoxicants. Never trained on, never scored — but where does the model RANK
     them? A triage tool that puts rotenone and tributyltin in the top 20 wastes assays.
  F  Stress endpoint: selective vs everything else (no effect + non-selective cytotoxicity). This
     is the decision a laboratory actually faces, and it is harder.
  G  Random baseline with a real interval, not just its expected value.
  H  Do the two kinds of positive behave the same? 27 positives have no fitted cytotoxicity, 22
     have a measured separation. If the model only finds one kind, the endpoint is two endpoints.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

from audit_lib import (MODELS, assays_for_share, assays_random, cluster_bootstrap_ci,  # noqa: E402
                       run_cv)
from dntscout import chem  # noqa: E402
from dntscout import labels as L  # noqa: E402
from dntscout.evaluation import RNG_SEED, grouped_folds, scaffold_groups  # noqa: E402

OUT = Path("results/audit")
OUT.mkdir(parents=True, exist_ok=True)
rep: dict = {}

df = pd.read_parquet("data/processed/chemicals_labelled.parquet")
kept = df[(df.y.notna()) & (df.structure_ok) & (df.smiles.notna())].reset_index(drop=True)
y = kept.y.astype(int).to_numpy()
groups = scaffold_groups(kept.scaffold.tolist())
X, _ = chem.feature_matrix(kept.smiles.tolist())
X_desc = X[:, -len(chem.DESCRIPTORS):]
sim = chem.tanimoto_matrix(kept.smiles.tolist(), kept.smiles.tolist())
np.fill_diagonal(sim, 0.0)
print("evaluation set: %d chemicals, %d positives, %d scaffold groups"
      % (len(y), y.sum(), len(np.unique(groups))))

folds0 = grouped_folds(groups, y, n_folds=5, seed=RNG_SEED)


def summarise(res, tag):
    rows = []
    for m in MODELS:
        pf = res.per_fold(roc_auc_score, m)
        rows.append({
            "model": m,
            "roc_pooled": res.pooled(roc_auc_score, m),
            "roc_pooled_rank": float(roc_auc_score(res.y, res.rank_pooled(m))),
            "roc_per_fold_mean": float(pf.mean()), "roc_per_fold_sd": float(pf.std(ddof=1)),
            "pr_pooled": res.pooled(average_precision_score, m),
            "assays_50pct": assays_for_share(res.oof[m], res.y, 0.5),
            "assays_50pct_rank": assays_for_share(res.rank_pooled(m), res.y, 0.5),
        })
    t = pd.DataFrame(rows)
    print("\n--- %s ---" % tag)
    print(t.to_string(index=False, float_format=lambda v: "%.3f" % v))
    return rows


# ===================================================== A  pooled vs per-fold
print("=" * 78)
print("A  pooled-across-folds metrics vs metrics computed inside each fold")
print("   a constant-per-fold predictor ('prevalence') must be exactly 0.500 per fold")
res0 = run_cv(X, X_desc, sim, y, groups, folds0)
rep["A_baseline_split"] = summarise(res0, "project's own split, seed %d" % RNG_SEED)
prev_pf = res0.per_fold(roc_auc_score, "prevalence")
print("\n   prevalence per-fold ROC: %s" % np.round(prev_pf, 3).tolist())
print("   prevalence pooled ROC  : %.3f   <-- the artefact, in one number"
      % res0.pooled(roc_auc_score, "prevalence"))
print("   training prevalence per fold: %s"
      % [round(float(y[tr].mean()), 3) for tr, _ in folds0])
rep["A_prevalence_per_fold_roc"] = prev_pf.tolist()
rep["A_prevalence_pooled_roc"] = res0.pooled(roc_auc_score, "prevalence")
rep["A_train_prevalence_per_fold"] = [float(y[tr].mean()) for tr, _ in folds0]

# ===================================================== B  repeated CV
print("=" * 78)
print("B  the same evaluation over 20 different fold assignments")
SEEDS = [RNG_SEED + 1000 * i for i in range(20)]
rec = {m: {"roc_pooled": [], "roc_rank": [], "roc_fold_mean": [], "assays": []} for m in MODELS}
for i, s in enumerate(SEEDS):
    f = grouped_folds(groups, y, n_folds=5, seed=s)
    r = run_cv(X, X_desc, sim, y, groups, f)
    for m in MODELS:
        rec[m]["roc_pooled"].append(r.pooled(roc_auc_score, m))
        rec[m]["roc_rank"].append(float(roc_auc_score(y, r.rank_pooled(m))))
        rec[m]["roc_fold_mean"].append(float(r.per_fold(roc_auc_score, m).mean()))
        rec[m]["assays"].append(assays_for_share(r.rank_pooled(m), y, 0.5))
    print("   seed %2d/%d done" % (i + 1, len(SEEDS)), flush=True)
rows = []
for m in MODELS:
    d = rec[m]
    rows.append({"model": m,
                 "roc_rank_median": float(np.median(d["roc_rank"])),
                 "roc_rank_p2.5": float(np.percentile(d["roc_rank"], 2.5)),
                 "roc_rank_p97.5": float(np.percentile(d["roc_rank"], 97.5)),
                 "roc_pooled_median": float(np.median(d["roc_pooled"])),
                 "assays_median": float(np.median(d["assays"])),
                 "assays_min": int(np.min(d["assays"])), "assays_max": int(np.max(d["assays"]))})
print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: "%.3f" % v))
rep["B_repeated_cv"] = {m: rec[m] for m in MODELS}
rep["B_repeated_cv_summary"] = rows

# ===================================================== C  similarity cap
print("=" * 78)
print("C  similarity cap: hide training analogues closer than T to the test chemical")
nn_all = sim.max(axis=1)
print("   nearest-analogue Tanimoto over the whole set: median %.2f  "
      "share >=0.5 %.0f%%  >=0.7 %.0f%%  >=0.9 %.0f%%"
      % (np.median(nn_all), 100 * (nn_all >= .5).mean(), 100 * (nn_all >= .7).mean(),
         100 * (nn_all >= .9).mean()))
rep["C_nn_sim_quantiles"] = {q: float(np.quantile(nn_all, q)) for q in (.1, .25, .5, .75, .9)}
cap_rows = []
for cap in (None, 0.9, 0.7, 0.5, 0.4):
    r = run_cv(X, X_desc, sim, y, groups, folds0, cap=cap)
    for m in ("read_across", "fingerprint_forest"):
        cap_rows.append({"cap": "none" if cap is None else cap, "model": m,
                         "roc_rank": float(roc_auc_score(y, r.rank_pooled(m))),
                         "roc_per_fold_mean": float(r.per_fold(roc_auc_score, m).mean()),
                         "assays_50pct": assays_for_share(r.rank_pooled(m), y, 0.5),
                         "mean_nn_sim_used": float(r.nn_sim.mean())})
    print("   cap %-5s done" % str(cap), flush=True)
print(pd.DataFrame(cap_rows).to_string(index=False, float_format=lambda v: "%.3f" % v))
rep["C_similarity_cap"] = cap_rows

# ===================================================== D  cluster split
print("=" * 78)
print("D  Butina cluster split at 0.6 similarity, instead of Bemis-Murcko scaffolds")
from rdkit.ML.Cluster import Butina  # noqa: E402

n = len(y)
dists = []
for i in range(1, n):
    dists.extend((1.0 - sim[i, :i]).tolist())
for thresh in (0.4, 0.6):
    cl = Butina.ClusterData(dists, n, 1.0 - thresh, isDistData=True)
    cgroups = np.zeros(n, dtype=int)
    for ci, members in enumerate(cl):
        for mi in members:
            cgroups[mi] = ci
    sizes = pd.Series(cgroups).value_counts()
    print("   similarity threshold %.1f -> %d clusters (largest %d, singletons %d)"
          % (thresh, len(cl), sizes.max(), (sizes == 1).sum()))
    f = grouped_folds(cgroups, y, n_folds=5, seed=RNG_SEED)
    r = run_cv(X, X_desc, sim, y, cgroups, f)
    for m in MODELS:
        rr = float(roc_auc_score(y, r.rank_pooled(m)))
        print("      %-20s roc_rank %.3f  per-fold %.3f  assays@50%% %d"
              % (m, rr, r.per_fold(roc_auc_score, m).mean(),
                 assays_for_share(r.rank_pooled(m), y, 0.5)))
        rep.setdefault("D_cluster_split", []).append(
            {"sim_threshold": thresh, "n_clusters": len(cl), "model": m, "roc_rank": rr,
             "roc_per_fold_mean": float(r.per_fold(roc_auc_score, m).mean()),
             "assays_50pct": assays_for_share(r.rank_pooled(m), y, 0.5)})

# ===================================================== E  the 28 cytotoxicants
print("=" * 78)
print("E  where does the model rank the 28 non-selective cytotoxicants it never saw?")
inc = df[(df.label == L.INCONCLUSIVE_CYTOTOX) & (df.structure_ok) & (df.smiles.notna())].copy()
print("   modellable among them: %d of 28" % len(inc))
X_inc, _ = chem.feature_matrix(inc.smiles.tolist())
sim_inc = chem.tanimoto_matrix(inc.smiles.tolist(), kept.smiles.tolist())
r = run_cv(X, X_desc, sim, y, groups, folds0, X_extra=X_inc, sim_extra=sim_inc)
NM = "PREFERRED_NAME" if "PREFERRED_NAME" in inc.columns else "Compound"
e_rows = []
for m in ("read_across", "fingerprint_forest"):
    s_eval, s_inc = r.oof[m], r.extra_scores[m]
    # percentile of each cytotoxicant within the evaluation set's score distribution
    pct = np.array([(s_eval < v).mean() for v in s_inc])
    thr20 = np.sort(s_eval)[::-1][min(19, len(s_eval) - 1)]   # score of the 20th-ranked chemical
    in_top20_band = int((s_inc >= thr20).sum())
    print("   %-20s median percentile of the 28 within the scored set: %.2f   "
          "would reach the top-20 score band: %d of %d"
          % (m, float(np.median(pct)), in_top20_band, len(inc)))
    e_rows.append({"model": m, "n_cytotox": int(len(inc)),
                   "median_percentile": float(np.median(pct)),
                   "n_in_top20_score_band": in_top20_band,
                   "mean_score_cytotox": float(s_inc.mean()),
                   "mean_score_positives": float(s_eval[y == 1].mean()),
                   "mean_score_negatives": float(s_eval[y == 0].mean())})
    if m == "read_across":
        inc["score_read_across"] = s_inc
        inc["percentile_in_eval_set"] = pct
        print("      the five it would test first:")
        for _, rr in inc.sort_values("score_read_across", ascending=False).head(5).iterrows():
            print("        %-34s score %.3f  percentile %.2f"
                  % (str(rr[NM])[:34], rr.score_read_across, rr.percentile_in_eval_set))
rep["E_cytotoxicant_ranking"] = e_rows
inc[[NM, "smiles", "score_read_across", "percentile_in_eval_set", "ec50_network_min",
     "ec50_viability_min", "selectivity_fold"]].to_csv(OUT / "cytotoxicant_ranking.csv", index=False)

# ===================================================== F  stress endpoint
print("=" * 78)
print("F  stress endpoint: selective vs everything else (no effect + non-selective cytotox)")
stress = df[(df.structure_ok) & (df.smiles.notna())
            & (df.label.isin([L.SELECTIVE, L.NO_EFFECT, L.INCONCLUSIVE_CYTOTOX]))].reset_index(drop=True)
y_s = (stress.label == L.SELECTIVE).astype(int).to_numpy()
g_s = scaffold_groups(stress.scaffold.tolist())
X_s, _ = chem.feature_matrix(stress.smiles.tolist())
sim_s = chem.tanimoto_matrix(stress.smiles.tolist(), stress.smiles.tolist())
np.fill_diagonal(sim_s, 0.0)
print("   %d chemicals, %d positives (prevalence %.3f), %d scaffold groups"
      % (len(y_s), y_s.sum(), y_s.mean(), len(np.unique(g_s))))
f_s = grouped_folds(g_s, y_s, n_folds=5, seed=RNG_SEED)
r_s = run_cv(X_s, X_s[:, -len(chem.DESCRIPTORS):], sim_s, y_s, g_s, f_s)
f_rows = []
for m in MODELS:
    rr = float(roc_auc_score(y_s, r_s.rank_pooled(m)))
    a = assays_for_share(r_s.rank_pooled(m), y_s, 0.5)
    ci = cluster_bootstrap_ci(
        lambda idx, m=m: roc_auc_score(y_s[idx], r_s.rank_pooled(m)[idx])
        if len(set(y_s[idx])) > 1 else np.nan, g_s, n_boot=1000)
    print("   %-20s roc_rank %.3f [%.3f-%.3f]  assays@50%% %d" % (m, rr, ci[0], ci[1], a))
    f_rows.append({"model": m, "roc_rank": rr, "roc_ci95": list(ci), "assays_50pct": a,
                   "n": int(len(y_s)), "n_pos": int(y_s.sum()), "prevalence": float(y_s.mean())})
rep["F_stress_endpoint"] = f_rows

# ===================================================== G  random baseline CI
print("=" * 78)
print("G  random testing order: expected assays for 50% of positives, with its real spread")
for name, yy in (("primary endpoint (102 chemicals)", y), ("stress endpoint (%d)" % len(y_s), y_s)):
    mean, lo, hi = assays_random(yy, 0.5)
    print("   %-34s %.1f assays [%d-%d]" % (name, mean, lo, hi))
    rep.setdefault("G_random_baseline", []).append(
        {"set": name, "mean_assays": mean, "p2.5": lo, "p97.5": hi})

# ===================================================== H  two kinds of positive
print("=" * 78)
print("H  are the two kinds of positive equally findable?")
fold_f = kept.selectivity_fold.astype(float).to_numpy()
measured = np.isfinite(fold_f) & (y == 1)
nocyto = ~np.isfinite(fold_f) & (y == 1)
neg = y == 0
print("   positives with a measured >=3x separation: %d   with no fitted cytotoxicity: %d"
      % (measured.sum(), nocyto.sum()))
h_rows = []
for m in ("read_across", "fingerprint_forest"):
    p = res0.rank_pooled(m)
    for tag, mask in (("measured_separation", measured), ("no_cytotox_fitted", nocyto)):
        sub = mask | neg
        a = float(roc_auc_score(y[sub], p[sub]))
        print("   %-20s %-20s n=%d  roc vs negatives %.3f"
              % (m, tag, int(sub.sum()), a))
        h_rows.append({"model": m, "positive_kind": tag, "n_pos": int(mask.sum()),
                       "roc_vs_negatives": a, "mean_score": float(p[mask].mean())})
    print("   %-20s mean rank score: measured %.3f  no-cytotox %.3f  negatives %.3f"
          % (m, p[measured].mean(), p[nocyto].mean(), p[neg].mean()))
rep["H_positive_strata"] = h_rows

(OUT / "audit_02_validity.json").write_text(json.dumps(rep, indent=1))
print("\nwrote %s/audit_02_validity.json" % OUT)
