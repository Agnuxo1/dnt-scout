"""Adversarial audit, part 1: the data and the label definition.

Questions, in the order a toxicology reviewer would ask them:
  Q1  Are there duplicate structures (same InChIKey) among the modelled chemicals?
      If yes, scaffold grouping does not stop a chemical being its own analogue.
  Q2  How many of the 49 "selective" got there because NO cytotoxicity EC50 was fitted
      (selectivity_fold = inf) rather than by a measured >=3x separation?
  Q3  Multiplicity: the label takes the MINIMUM EC50 over 17 parameters. How does the
      positive count move if 2 or 3 parameters must respond?
  Q4  Are the 28 inconclusive_cytotox structurally clustered (do they remove whole scaffolds)?
  Q5  Prevalence reality check: what is it, and what is the EF ceiling it implies?
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from dntscout import labels as L  # noqa: E402
from dntscout.evaluation import scaffold_groups  # noqa: E402

D = Path("data/processed")
df = pd.read_parquet(D / "chemicals_labelled.parquet")
rep = {}

print("rows=%d" % len(df))
print("columns=%s" % list(df.columns))
print()
print("label counts:")
print(df.label.value_counts().to_string())
print()

kept = df[(df.y.notna()) & (df.structure_ok) & (df.smiles.notna())].reset_index(drop=True)
rep["n_modelled"] = len(kept)
NM = "PREFERRED_NAME" if "PREFERRED_NAME" in df.columns else "Compound"


def names(sub, width=28):
    return [str(x)[:width] for x in sub[NM]]


# ---------------------------------------------------------------- Q1 duplicates
print("=" * 72)
print("Q1  duplicate structures among the modelled chemicals")
for col in ("inchikey", "smiles"):
    if col not in kept.columns:
        print("  (no column %s)" % col)
        continue
    vc = kept[col].value_counts()
    dup = vc[vc > 1]
    print("  duplicate %s: %d values covering %d rows" % (col, len(dup), int(dup.sum())))
    rep["dup_%s_groups" % col] = int(len(dup))
    rep["dup_%s_rows" % col] = int(dup.sum())
    for v, n in dup.items():
        sub = kept[kept[col] == v]
        print("    %dx %s  y=%s  names=%s" % (n, str(v)[:34], sub.y.tolist(), names(sub)))

if "inchikey" in kept.columns:
    skel = kept.inchikey.astype(str).str[:14]
    vc = skel.value_counts()
    dup = vc[vc > 1]
    print("  duplicate InChIKey SKELETON (same connectivity): %d groups, %d rows"
          % (len(dup), int(dup.sum())))
    rep["dup_skeleton_groups"] = int(len(dup))
    rep["dup_skeleton_rows"] = int(dup.sum())
    for v, n in dup.items():
        sub = kept[skel == v]
        print("    %dx %s  y=%s  same_scaffold=%s  names=%s"
              % (n, v, sub.y.tolist(), sub.scaffold.nunique() == 1, names(sub, 26)))

# ------------------------------------------------- Q2 how the positives were earned
print("=" * 72)
print("Q2  route by which each 'selective' positive was earned")
sel = df[df.label == L.SELECTIVE]
fold_f = sel.selectivity_fold.astype(float)
inf_mask = ~np.isfinite(fold_f)
print("  selective total                                  : %d" % len(sel))
print("  ... no cytotoxicity EC50 fitted (fold = inf)     : %d"
      "   <-- 'no cytotox seen in range', not a measured separation" % int(inf_mask.sum()))
print("  ... measured separation >= %gx                    : %d"
      % (L.SELECTIVITY_FOLD, int((~inf_mask).sum())))
fin = fold_f[~inf_mask]
if len(fin):
    print("  measured folds: median %.1f  quartiles %.1f/%.1f  max %.1f"
          % (fin.median(), fin.quantile(.25), fin.quantile(.75), fin.max()))
    print("  how many sit just above the line (3x to 5x)      : %d"
          % int(((fin >= 3) & (fin < 5)).sum()))
rep["selective_total"] = int(len(sel))
rep["selective_no_cytotox_fitted"] = int(inf_mask.sum())
rep["selective_measured_separation"] = int((~inf_mask).sum())
rep["selective_fold_3_to_5"] = int(((fin >= 3) & (fin < 5)).sum()) if len(fin) else 0

# ------------------------------------------------------------- Q3 multiplicity
print("=" * 72)
print("Q3  multiplicity: the label uses the MINIMUM EC50 over 17 network parameters")
print("    responding-parameter count among the selective positives:")
npr = sel.n_params_responding.astype(int)
print("      " + "  ".join("%d:%d" % (k, v) for k, v in sorted(npr.value_counts().items())))
for need in (1, 2, 3, 5):
    print("      still positive requiring >= %d responding parameter(s): %d of %d"
          % (need, int((npr >= need).sum()), len(sel)))
rep["selective_by_n_params"] = {int(k): int(v) for k, v in sorted(npr.value_counts().items())}
rep["selective_if_min_params"] = {n: int((npr >= n).sum()) for n in (1, 2, 3, 5)}

# ------------------------------------------- Q4 are the inconclusives clustered?
print("=" * 72)
print("Q4  the inconclusive_cytotox chemicals: do they remove whole scaffolds?")
inc = df[df.label == L.INCONCLUSIVE_CYTOTOX]
kept_scaf = set(kept.scaffold.dropna())
inc_scaf = set(inc.scaffold.dropna())
print("  inconclusive_cytotox                : %d" % len(inc))
print("  distinct scaffolds among them       : %d" % len(inc_scaf))
print("  scaffolds shared with modelled set  : %d" % len(inc_scaf & kept_scaf))
print("  scaffolds unique to them (lost)     : %d" % len(inc_scaf - kept_scaf))
rep["inconclusive_cytotox"] = int(len(inc))
rep["inconclusive_scaffolds_lost"] = int(len(inc_scaf - kept_scaf))
rep["inconclusive_scaffolds_shared"] = int(len(inc_scaf & kept_scaf))
print("  all of them, by potency, and whether their scaffold survives:")
for _, r in inc.sort_values("ec50_network_min").iterrows():
    print("    %-34s net=%9.3f viab=%9.3f fold=%5.2f  %s"
          % (str(r[NM])[:34], r.ec50_network_min, r.ec50_viability_min,
             float(r.selectivity_fold),
             "SHARED-with-modelled" if r.scaffold in kept_scaf else "scaffold-lost"))

# ------------------------------------------------------------- Q5 prevalence
print("=" * 72)
print("Q5  prevalence and what it implies for the enrichment claim")
y = kept.y.astype(int).to_numpy()
prev = float(y.mean())
groups = scaffold_groups(kept.scaffold.tolist())
need50 = int(np.ceil(0.5 * y.sum()))
print("  modelled chemicals        : %d   positives %d" % (len(y), int(y.sum())))
print("  prevalence                : %.3f" % prev)
print("  EF ceiling (perfect model): %.2f   <-- EF can never exceed this" % (1 / prev))
print("  assays for 50%% of positives, perfect ranking : %d" % need50)
print("  ...                        at random (expected): %d" % int(round(need50 / prev)))
print("  scaffold groups           : %d" % len(np.unique(groups)))
gs = pd.Series(groups).value_counts()
print("  group sizes: max %d  singletons %d  share of chemicals in singletons %.2f"
      % (gs.max(), (gs == 1).sum(), (gs == 1).sum() / len(y)))
acyc = int(kept.scaffold.astype(str).str.startswith("ACYCLIC::").sum())
print("  acyclic chemicals, each its OWN group by construction: %d (%.0f%%)"
      % (acyc, 100 * acyc / len(y)))
print("      ^ scaffold grouping does NOT separate acyclic homologues from each other")
rep.update(prevalence=prev, ef_ceiling=float(1 / prev), n_groups=int(len(np.unique(groups))),
           n_singleton_groups=int((gs == 1).sum()), largest_group=int(gs.max()), n_acyclic=acyc,
           assays_50pct_perfect=need50, assays_50pct_random_expected=int(round(need50 / prev)))

Path("results/audit").mkdir(parents=True, exist_ok=True)
Path("results/audit/audit_01_data.json").write_text(json.dumps(rep, indent=1))
print()
print("wrote results/audit/audit_01_data.json")
