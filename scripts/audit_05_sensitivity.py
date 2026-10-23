"""Does the result survive the strictest reading of the endpoint?

Nine positives have no fitted cytotoxicity EC50 *and* a network EC50 so close to the 20 uM top
dose that the selectivity ratio cannot be bounded above 3x from the data. Under the strictest
reading they are not positives at all, they are inconclusive. This re-runs the whole evaluation
with those nine removed. If the headline moves materially, the endpoint was carrying them.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, "src"); sys.path.insert(0, "scripts")
from audit_lib import MODELS, assays_for_share, assays_random, run_cv  # noqa: E402
from dntscout import chem  # noqa: E402
from dntscout.evaluation import RNG_SEED, grouped_folds, scaffold_groups  # noqa: E402

OUT = Path("results/audit"); OUT.mkdir(parents=True, exist_ok=True)
drop = set(json.loads((OUT / "audit_04_bound.json").read_text())["indeterminate_names"])
print("dropping %d positives whose selectivity ratio cannot be bounded above 3x:" % len(drop))
for d in sorted(drop):
    print("   -", d)

df = pd.read_parquet("data/processed/chemicals_labelled.parquet")
NM = "PREFERRED_NAME" if "PREFERRED_NAME" in df.columns else "Compound"
base = df[(df.y.notna()) & (df.structure_ok) & (df.smiles.notna())].reset_index(drop=True)
rep = {}
for tag, kept in (("as published (102 chemicals)", base),
                  ("strict (the 9 unbounded positives removed)",
                   base[~base[NM].isin(drop)].reset_index(drop=True))):
    y = kept.y.astype(int).to_numpy()
    g = scaffold_groups(kept.scaffold.tolist())
    X, _ = chem.feature_matrix(kept.smiles.tolist())
    sim = chem.tanimoto_matrix(kept.smiles.tolist(), kept.smiles.tolist())
    np.fill_diagonal(sim, 0.0)
    rows = []
    med = {m: [] for m in MODELS}; ass = {m: [] for m in MODELS}
    for s in [RNG_SEED + 1000 * i for i in range(10)]:
        r = run_cv(X, X[:, -len(chem.DESCRIPTORS):], sim, y, g,
                   grouped_folds(g, y, n_folds=5, seed=s))
        for m in MODELS:
            med[m].append(float(roc_auc_score(y, r.rank_pooled(m))))
            ass[m].append(assays_for_share(r.rank_pooled(m), y, 0.5))
    rnd = assays_random(y, 0.5)
    print("\n--- %s: %d chemicals, %d positives (prevalence %.3f) ---"
          % (tag, len(y), y.sum(), y.mean()))
    print("    random testing order needs %.1f assays [%d-%d]" % rnd)
    for m in MODELS:
        v = np.array(med[m]); a = np.array(ass[m])
        print("    %-20s ROC %.3f [%.3f-%.3f]   assays %d [%d-%d]"
              % (m, np.median(v), v.min(), v.max(), int(np.median(a)), a.min(), a.max()))
        rows.append({"model": m, "roc_median": float(np.median(v)), "roc_min": float(v.min()),
                     "roc_max": float(v.max()), "assays_median": int(np.median(a)),
                     "assays_min": int(a.min()), "assays_max": int(a.max())})
    rep[tag] = {"n": int(len(y)), "n_pos": int(y.sum()), "prevalence": float(y.mean()),
                "random_assays": rnd, "models": rows}
(OUT / "audit_05_sensitivity.json").write_text(json.dumps(rep, indent=1))
print("\nwrote results/audit/audit_05_sensitivity.json")
