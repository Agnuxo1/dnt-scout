"""The lower bound the toxicologist's question actually needs.

"No cytotoxicity EC50 was fitted" can mean two different things, and they carry different weight:
the compound was genuinely non-cytotoxic across the whole tested range, or the viability curve
simply never fell far enough before the top dose. The dose tables settle it. For every positive
with no fitted cytotoxicity, the highest concentration actually tested puts a LOWER BOUND on the
selectivity ratio:

    bound = top tested concentration / network EC50

If that bound is >= 3 the selectivity claim is supported inside the tested range, whatever the
missing EC50 would have been. If it is < 3 the ratio is genuinely indeterminate, and those
chemicals are re-tested as inconclusive in a sensitivity analysis.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
RAW = Path("data/raw/epa-shafer-2019-pasteur")
SUMM = RAW / "extracted" / "All Compound Summary_correct names_updated_20181010.xlsx"
OUT = Path("results/audit")
OUT.mkdir(parents=True, exist_ok=True)

def norm(s):
    return (str(s).lower().replace("-", "").replace(" ", "").replace(",", "")
            .replace("'", "").replace("(", "").replace(")", ""))

top = {}
for sh in ("Tab 11-NTP Alamar Blue Data", "Tab 12-NTP LDH_Data",
           "Tab 13-TC AB_Data", "Tab 14-TC LDH_Data"):
    try:
        d = pd.read_excel(SUMM, sheet_name=sh)
    except Exception as e:
        print("  (skipped %s: %s)" % (sh, e)); continue
    cc = [c for c in d.columns if str(c).strip().lower() == "compound"][0]
    dc = [c for c in d.columns if str(c).strip().lower() == "dose"][0]
    g = d.groupby(d[cc].map(norm))[dc].max()
    for k, v in g.items():
        top[k] = max(top.get(k, 0.0), float(v))
print("top tested concentration recovered for %d compounds" % len(top))
vals = np.array(list(top.values()))
print("  distribution of top doses: median %.1f uM, min %.1f, max %.1f"
      % (np.median(vals), vals.min(), vals.max()))

df = pd.read_parquet("data/processed/chemicals_labelled.parquet")
NM = "PREFERRED_NAME" if "PREFERRED_NAME" in df.columns else "Compound"
sel = df[df.label == "selective"].copy()
fold = sel.selectivity_fold.astype(float)
nocyt = sel[~np.isfinite(fold)].copy()
nocyt["key"] = nocyt["Compound"].map(norm)
nocyt["top_dose"] = nocyt.key.map(top)
got = nocyt.dropna(subset=["top_dose"])
print("\npositives with no fitted cytotoxicity: %d, of which %d have a recoverable top dose"
      % (len(nocyt), len(got)))
b = got.top_dose.astype(float) / got.ec50_network_min.astype(float)
print("  lower bound on the selectivity ratio = top tested dose / network EC50")
print("    >= 3x  : %d of %d   <-- selectivity supported inside the tested range"
      % (int((b >= 3).sum()), len(got)))
print("    >= 10x : %d" % int((b >= 10).sum()))
print("    <  3x  : %d   <-- genuinely indeterminate" % int((b < 3).sum()))
print("    median bound %.1fx  (quartiles %.1f / %.1f)"
      % (b.median(), b.quantile(.25), b.quantile(.75)))
print("\n  the ones whose ratio is indeterminate (<3x):")
for _, r in got.assign(bound=b).query("bound < 3").sort_values("bound").iterrows():
    print("    %-34s net EC50 %7.3f  top dose %7.2f  bound %4.1fx"
          % (str(r[NM])[:34], r.ec50_network_min, r.top_dose, r.bound))

rep = {"n_no_cytotox": int(len(nocyt)), "n_with_top_dose": int(len(got)),
       "bound_ge_3": int((b >= 3).sum()), "bound_ge_10": int((b >= 10).sum()),
       "bound_lt_3": int((b < 3).sum()), "bound_median": float(b.median()),
       "indeterminate_names": got.assign(bound=b).query("bound < 3")[NM].tolist()}
got.assign(lower_bound_ratio=b)[[NM, "Compound", "ec50_network_min", "top_dose",
                                 "lower_bound_ratio", "n_params_responding"]] \
    .sort_values("lower_bound_ratio").to_csv(OUT / "positives_without_cytotoxicity.csv", index=False)
(OUT / "audit_04_bound.json").write_text(json.dumps(rep, indent=1))
print("\nwrote results/audit/audit_04_bound.json")
