#!/usr/bin/env python
"""Score untested chemicals against the measured analogues. Standalone: rdkit, pandas, numpy.

    python score_candidates.py --analogues analogues_with_outcome.csv \
                               --candidates candidates_unseen.csv --out scores.csv

This is the scoring step of DNT-Scout, extracted so it can run anywhere, including inside a
SciencePal sandbox. It is the read-across that won the held-out comparison (k = 3 nearest analogues
by Morgan Tanimoto similarity), with the conformal rule and the applicability domain fitted on the
same analogue table.

It reports, per candidate: the similarity-weighted score, the nearest measured analogues, whether
the 90% conformal set is decisive, and whether the candidate lies inside the applicability domain.
A candidate with no structure, or outside the domain, is returned as `undecidable` — that is an
answer, not a failure.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")
K = 3                      # chosen inside the training folds of the published evaluation
ALPHA = 0.10               # 90% confidence
PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def standardise(smiles):
    if not smiles or not isinstance(smiles, str):
        return None, ("no_structure",)
    m = Chem.MolFromSmiles(smiles.strip())
    if m is None:
        return None, ("parse_failed",)
    flags = []
    if len(Chem.GetMolFrags(m)) > 1:
        flags.append("multicomponent")
    m = rdMolStandardize.Uncharger().uncharge(rdMolStandardize.FragmentParent(rdMolStandardize.Cleanup(m)))
    if m is None or m.GetNumAtoms() == 0:
        return None, ("empty_after_cleanup",)
    if not any(a.GetSymbol() == "C" for a in m.GetAtoms()):
        flags.append("no_carbon")
    return Chem.MolToSmiles(m), tuple(flags)


def resolve(casrn, dtxsid, name):
    """PubChem lookup by identifier first, name last."""
    for key in (casrn, dtxsid, name):
        if not key or str(key).lower() in ("nan", "none", ""):
            continue
        url = f"{PUBCHEM}/compound/name/{urllib.parse.quote(str(key).strip())}/property/SMILES,ConnectivitySMILES/JSON"
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                p = json.load(r)["PropertyTable"]["Properties"][0]
            time.sleep(0.25)
            return p.get("SMILES") or p.get("ConnectivitySMILES")
        except Exception:
            time.sleep(0.25)
    return None


def fp(smiles):
    gen = AllChem.GetMorganGenerator(radius=2, fpSize=2048)
    return gen.GetFingerprint(Chem.MolFromSmiles(smiles))


def conformal_quantiles(sim: np.ndarray, y: np.ndarray, k: int = K, alpha: float = ALPHA):
    """Leave-one-out read-across on the analogue table, then class-conditional quantiles."""
    n = len(y)
    p = np.empty(n)
    for i in range(n):
        row = sim[i].copy()
        row[i] = -1
        idx = np.argsort(-row)[:k]
        w = row[idx]
        p[i] = float(np.average(y[idx], weights=w)) if w.sum() > 0 else float(y.mean())
    q = {}
    for c in (0, 1):
        s = 1.0 - np.where(y[y == c] == 1, p[y == c], 1 - p[y == c])
        j = min(max(int(np.ceil((len(s) + 1) * (1 - alpha))) - 1, 0), len(s) - 1)
        q[c] = float(np.sort(s)[j])
    return q, p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analogues", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", default="scores.csv")
    ap.add_argument("--k", type=int, default=K)
    a = ap.parse_args()

    tr = pd.read_csv(a.analogues).dropna(subset=["smiles"])
    y = tr["selective"].to_numpy().astype(int)
    tr_fps = [fp(s) for s in tr.smiles]
    sim_tr = np.array([DataStructs.BulkTanimotoSimilarity(f, tr_fps) for f in tr_fps])
    q, _ = conformal_quantiles(sim_tr, y, a.k)
    ad_threshold = float(np.percentile([np.sort(r)[-2] for r in sim_tr], 10))
    print(f"analogues: {len(tr)} ({y.sum()} selective) | conformal q={q} | "
          f"applicability domain: nearest-analogue Tanimoto >= {ad_threshold:.2f}", file=sys.stderr)

    cand = pd.read_csv(a.candidates)
    rows = []
    for _, c in cand.iterrows():
        smi_raw = c.get("smiles") if isinstance(c.get("smiles"), str) else resolve(
            c.get("casrn"), c.get("dtxsid"), c.get("name"))
        smi, flags = standardise(smi_raw)
        base = {"name": c.get("name"), "casrn": c.get("casrn"), "dtxsid": c.get("dtxsid"),
                "smiles": smi, "flags": ",".join(flags) if flags else ""}
        if smi is None or "multicomponent" in flags or "no_carbon" in flags:
            rows.append({**base, "score": np.nan, "decision": "undecidable",
                         "reason": "structure not modellable", "in_domain": False})
            continue
        s = np.array(DataStructs.BulkTanimotoSimilarity(fp(smi), tr_fps))
        idx = np.argsort(-s)[: a.k]
        w = s[idx]
        score = float(np.average(y[idx], weights=w)) if w.sum() > 0 else float(y.mean())
        nn = float(s.max())
        in_dom = nn >= ad_threshold
        sets = set()
        if (1.0 - score) <= q[1]:
            sets.add(1)
        if score <= q[0]:
            sets.add(0)
        if not in_dom:
            decision, reason = "undecidable", f"outside applicability domain (nearest analogue {nn:.2f})"
        elif sets == {1}:
            decision, reason = "test_first", "conformal set decisive for a selective effect"
        elif sets == {0}:
            decision, reason = "deprioritise", "conformal set decisive for no observed effect"
        else:
            decision, reason = "uninformative", "90% conformal set contains both outcomes"
        rows.append({**base, "score": round(score, 4), "nearest_analogue_tanimoto": round(nn, 3),
                     "conformal_set": "{" + ",".join(str(x) for x in sorted(sets)) + "}",
                     "in_domain": bool(in_dom), "decision": decision, "reason": reason,
                     "analogues": "; ".join(
                         f"{tr.iloc[j]['name']} (T={s[j]:.2f}, {'selective' if y[j] else 'no effect'})"
                         for j in idx)})
    out = pd.DataFrame(rows)
    # Ranking and decision are two different things, and the report must keep them apart:
    # the ranking says what to run first with a fixed assay budget, the conformal decision says
    # whether the evidence is strong enough to call the outcome. A candidate can be worth testing
    # first precisely because the evidence is thin.
    rank_ok = out.in_domain.fillna(False) & out.score.notna()
    out["rank"] = pd.Series(np.nan, index=out.index)
    out.loc[rank_ok, "rank"] = out.loc[rank_ok, "score"].rank(ascending=False, method="first")
    out["recommended_for_assay"] = out["rank"] <= 5
    out = out.sort_values(["rank", "score"], ascending=[True, False], na_position="last")
    out.to_csv(a.out, index=False)
    cols = ["name", "score", "nearest_analogue_tanimoto", "in_domain", "decision",
            "rank", "recommended_for_assay"]
    print(out[[c for c in cols if c in out.columns]].to_string(index=False))
    n_dec = int((out.decision == "test_first").sum())
    print("")
    print(f"{int(out.recommended_for_assay.sum())} chemicals recommended for the next assay round; "
          f"{n_dec} of them have a decisive 90% conformal set "
          f"({int((out.decision == 'undecidable').sum())} undecidable, "
          f"{int((out.decision == 'uninformative').sum())} uninformative).")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
