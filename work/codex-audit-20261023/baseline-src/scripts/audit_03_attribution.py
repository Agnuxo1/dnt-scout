"""Adversarial audit, part 3: who invented what, and what the 27 un-cytotoxic positives really mean.

Two questions raised by an external review of the results, both of which change what this project
may claim:

  A  The selectivity ratio. Shafer et al. 2019 publish a "Selectivity Score" of their own. If the
     quantity this project computes is the same one, then the ratio is THEIRS and must be credited;
     what remains ours is the binary label, the inconclusive classes and the triage system. The
     check is also worth doing in the other direction: if our independently recomputed ratio
     reproduces their published score, that is evidence the data pipeline is right.
  B  The 27 positives with no fitted cytotoxicity EC50. "No cytotoxicity fitted" can mean either
     "the compound is genuinely selective across the whole tested range" or merely "the viability
     curve never reached 50% before the top concentration". Those are different claims. With the
     top tested concentration we can put a LOWER BOUND on each ratio: top_conc / network_EC50. If
     that bound is >= 3 the selectivity is supported within the tested range; if it is < 3 the
     ratio is indeterminate and the chemical should be treated as inconclusive in a sensitivity
     analysis.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

RAW = Path("data/raw/epa-shafer-2019-pasteur")
OUT = Path("results/audit")
OUT.mkdir(parents=True, exist_ok=True)
rep: dict = {}

df = pd.read_parquet("data/processed/chemicals_labelled.parquet")
NM = "PREFERRED_NAME" if "PREFERRED_NAME" in df.columns else "Compound"


def norm(s):
    return (str(s).lower().replace("-", "").replace(" ", "").replace(",", "")
            .replace("'", "").replace("(", "").replace(")", ""))


# ========================================================== A  whose selectivity ratio is it?
print("=" * 78)
print("A  is our selectivity ratio the same quantity Shafer et al. already published?")
f = RAW / "Excel_selectivity_Oct_26_2018_alt.xlsx"
sheet = "Excel scatter plot potency vs s"
sh = pd.read_excel(f, sheet_name=sheet)
sh.columns = [str(c).strip() for c in sh.columns]
name_col = [c for c in sh.columns if "name" in c.lower() or c == "Compound"][0]
score_col = [c for c in sh.columns if "selectivity" in c.lower()][0]
sh = sh[[name_col, score_col]].dropna()
sh["key"] = sh[name_col].map(norm)
print("  Shafer's published Selectivity Score: %d compounds, range %.2f - %.2f"
      % (len(sh), sh[score_col].min(), sh[score_col].max()))

ours = df[[NM, "Compound", "selectivity_fold", "label"]].copy()
ours["key"] = ours["Compound"].map(norm)
m = ours.merge(sh, on="key", how="inner", suffixes=("", "_shafer"))
m["ours"] = m.selectivity_fold.astype(float)
both = m[np.isfinite(m.ours)]
print("  matched by compound name: %d; with a finite ratio on our side: %d" % (len(m), len(both)))
if len(both) >= 5:
    r = float(np.corrcoef(np.log10(both.ours.clip(1e-6)),
                          np.log10(both[score_col].clip(1e-6)))[0, 1])
    close = float((np.abs(both.ours - both[score_col]) <= 0.01 * np.maximum(both.ours, 1)).mean())
    print("  Pearson r on log10 of the two ratios : %.4f" % r)
    print("  share agreeing to within 1%%          : %.3f" % close)
    print("  worked examples:")
    for _, rr in both.sort_values("ours", ascending=False).head(6).iterrows():
        print("    %-34s ours %10.3f   Shafer %10.3f" % (str(rr[NM])[:34], rr.ours, rr[score_col]))
    rep["A_log_correlation"] = r
    rep["A_share_within_1pct"] = close
    rep["A_n_matched"] = int(len(both))
    verdict = ("SAME QUANTITY - the ratio is Shafer's; credit it, and claim only the binary label, "
               "the inconclusive classes and the triage system"
               if r > 0.95 else "DIFFERENT - our ratio is not their published score")
    print("\n  VERDICT: %s" % verdict)
    rep["A_verdict"] = verdict

# ====================================== B  what the 27 "no cytotoxicity fitted" positives mean
print("=" * 78)
print("B  the positives with no fitted cytotoxicity EC50: bound, not assumption")
summ = RAW / "extracted" / "All Compound Summary_correct names_updated_20181010.xlsx"
xl = pd.ExcelFile(summ)
print("  sheets in the EPA summary workbook: %s" % xl.sheet_names)
conc_col = None
for shname in xl.sheet_names:
    d = pd.read_excel(summ, sheet_name=shname, nrows=3)
    cands = [c for c in d.columns
             if any(k in str(c).lower() for k in ("top", "max", "highest", "conc"))]
    if cands:
        print("    sheet %-28s candidate concentration columns: %s" % (shname, cands[:6]))
        conc_col = conc_col or (shname, cands)
if conc_col is None:
    print("  No top-tested-concentration column found in the summary workbook.")
    print("  -> The lower bound cannot be computed from the summary table alone. What CAN be said")
    print("     is reported instead: the distribution of network EC50 among these 27, and how far")
    print("     below the highest network EC50 observed anywhere they sit.")
    rep["B_top_concentration_available"] = False

sel = df[df.label == "selective"].copy()
fold = sel.selectivity_fold.astype(float)
nocyt = sel[~np.isfinite(fold)]
meas = sel[np.isfinite(fold)]
allnet = df.ec50_network_min.astype(float).dropna()
top_obs = float(allnet.max())
print("\n  the 27 with no fitted cytotoxicity, by network potency:")
print("    median network EC50 %.3f uM  (quartiles %.3f / %.3f)"
      % (nocyt.ec50_network_min.median(), nocyt.ec50_network_min.quantile(.25),
         nocyt.ec50_network_min.quantile(.75)))
print("    the 22 with a measured separation: median network EC50 %.3f uM"
      % meas.ec50_network_min.median())
print("    highest network EC50 fitted anywhere in the study: %.3f uM" % top_obs)
bound = top_obs / nocyt.ec50_network_min.astype(float)
print("    implied lower bound on the ratio, taking the highest fitted network EC50 in the study")
print("    as a conservative stand-in for the top tested concentration:")
print("      >= 3x for %d of %d   |   >= 10x for %d   |   median bound %.1fx"
      % (int((bound >= 3).sum()), len(nocyt), int((bound >= 10).sum()), float(bound.median())))
rep["B_n_no_cytotox"] = int(len(nocyt))
rep["B_bound_ge_3"] = int((bound >= 3).sum())
rep["B_bound_ge_10"] = int((bound >= 10).sum())
rep["B_bound_median"] = float(bound.median())
rep["B_top_network_ec50_observed"] = top_obs
print("\n    (This is a bound derived from what was fitted, not from the protocol's top dose.")
print("     It is reported as such; the genuine top-dose check needs the dose tables.)")

nocyt_out = nocyt[[NM, "Compound", "ec50_network_min", "n_params_responding"]].copy()
nocyt_out["lower_bound_ratio_vs_highest_fitted"] = bound.values
nocyt_out.sort_values("lower_bound_ratio_vs_highest_fitted").to_csv(
    OUT / "positives_without_cytotoxicity.csv", index=False)

(OUT / "audit_03_attribution.json").write_text(json.dumps(rep, indent=1))
print("\nwrote %s/audit_03_attribution.json and positives_without_cytotoxicity.csv" % OUT)
