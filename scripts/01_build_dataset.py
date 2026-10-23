#!/usr/bin/env python
"""Build the modelling table from the raw public EPA files. Deterministic, re-runnable.

    python scripts/01_build_dataset.py --raw data/raw --out data/processed

Steps, in order:
 1. Read the Shafer et al. 2019 compound summary (NTP + ToxCast sets): per-parameter network EC50
    and Alamar Blue / LDH cytotoxicity EC50, with CASRN and DTXSID.
 2. Resolve each chemical to a structure through PubChem (by CASRN, then by DSSTox id, then by
    name), standardise it, and record the InChIKey and Bemis-Murcko scaffold.
 3. Classify the primary outcome (see dntscout.labels).
 4. Read the concentration-response file of the wider screen (auc.dat, 460 chemicals) and audit how
    much it overlaps the labelled set, by identifier and by structure.
 5. Write one parquet per table plus a JSON provenance record.

Nothing here is copied from any earlier project: the inputs are the public EPA files downloaded by
`scripts/00_download_raw.py`, and PubChem is queried live with its documented rate limit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
import warnings
import zipfile
from pathlib import Path

import pandas as pd

from dntscout import chem
from dntscout.labels import NETWORK_PARAMS, classify_table, sensitivity_to_fold

warnings.filterwarnings("ignore")

SUMMARY_ZIP = "epa-shafer-2019-pasteur/NTP_TC_Analysis.zip"
SUMMARY_XLSX = "All Compound Summary_correct names_updated_20181010.xlsx"
AUC_RDATA = "epa-nfa-github/source_files/auc.data.with.spids.RData"
CCD_CSV = "epa-nfa-github/source_files/CCD-Batch-Search_2025-07-18_07_43_29.csv"
PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PROPS = "ConnectivitySMILES,SMILES,InChIKey,MolecularFormula"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _pubchem(path: str) -> dict | None:
    url = f"{PUBCHEM}/{path}/property/{PROPS}/JSON"
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            return json.load(r)["PropertyTable"]["Properties"][0]
    except Exception:
        return None


def resolve_structure(casrn: str | None, dtxsid: str | None, name: str | None) -> dict:
    """Identity first, name last: names are the least reliable key for a chemical."""
    for kind, key in (("casrn", casrn), ("dtxsid", dtxsid), ("name", name)):
        if not key or not str(key).strip() or str(key).lower() == "nan":
            continue
        q = urllib.parse.quote(str(key).strip())
        rec = _pubchem(f"compound/name/{q}")
        time.sleep(0.25)                      # PubChem asks for <= 5 requests/second
        if rec:
            smi = rec.get("SMILES") or rec.get("ConnectivitySMILES")
            return {"resolved_by": kind, "cid": rec.get("CID"), "smiles_raw": smi,
                    "inchikey_pubchem": rec.get("InChIKey"), "formula": rec.get("MolecularFormula")}
    return {"resolved_by": None, "cid": None, "smiles_raw": None,
            "inchikey_pubchem": None, "formula": None}


def load_summary(raw: Path) -> pd.DataFrame:
    """The two labelled sets (NTP and ToxCast) joined, with network and viability EC50 values."""
    zp = raw / SUMMARY_ZIP
    with zipfile.ZipFile(zp) as z:
        target = raw / "epa-shafer-2019-pasteur" / "extracted"
        if not (target / SUMMARY_XLSX).exists():
            z.extract(SUMMARY_XLSX, target)
    x = pd.ExcelFile(target / SUMMARY_XLSX)
    frames = []
    for ec_tab, viab_tab, cohort in (("Tab 2-NTP AUC_EC50_summary", "Tab 4-NTP Viability_EC50", "NTP"),
                                     ("Tab 3-TC AUC_EC50_summary", "Tab 5-TC Viability_EC50", "ToxCast")):
        ec = x.parse(ec_tab)
        viab = x.parse(viab_tab)[["Casrn", "AB cytotox", "LDH cytotox"]]
        ec = ec.loc[:, ~ec.columns.astype(str).str.startswith("Unnamed")]
        keep = ["Compound", "Casrn", "DTXSID", "PREFERRED_NAME", *NETWORK_PARAMS]
        ec = ec[[c for c in keep if c in ec.columns]].copy()
        ec["cohort"] = cohort
        ec = ec.dropna(subset=["Casrn"]).drop_duplicates(subset=["Casrn"])
        viab = viab.dropna(subset=["Casrn"]).drop_duplicates(subset=["Casrn"])
        frames.append(ec.merge(viab, on="Casrn", how="left"))
    df = pd.concat(frames, ignore_index=True)
    for c in (*NETWORK_PARAMS, "AB cytotox", "LDH cytotox"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["Casrn"] = df["Casrn"].astype(str).str.strip()
    return df


def collapse_cohorts(long: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per chemical, plus the concordance of the chemicals measured in both cohorts.

    Some chemicals appear in both the NTP and the ToxCast set. They are two independent runs of the
    same assay in the same laboratory, so they are not an external validation; they do give a
    reference for how reproducible the outcome is. For modelling, the most sensitive EC50 across
    cohorts is kept (a response seen in either run counts as a response), which is the conservative
    choice for a triage tool.
    """
    num = [*NETWORK_PARAMS, "AB cytotox", "LDH cytotox"]
    first = {"Compound": "first", "DTXSID": "first", "PREFERRED_NAME": "first"}
    agg = {**{c: "min" for c in num}, **first,
           "cohort": lambda s: "+".join(sorted(set(s)))}
    wide = long.groupby("Casrn", as_index=False).agg(agg)
    wide["n_cohorts"] = wide["cohort"].str.count(r"\+") + 1
    dup = long[long.duplicated("Casrn", keep=False)].copy()
    return wide, dup


def load_auc(raw: Path):
    """The wider concentration-response screen: 17 network endpoints, no viability assay."""
    import rdata
    d = rdata.read_rda(str(raw / AUC_RDATA))["auc.dat"]
    chems = (d[["dsstox_substance_id", "casn", "chnm"]].drop_duplicates()
             .dropna(subset=["dsstox_substance_id"]).reset_index(drop=True))
    return d, chems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--limit", type=int, default=0, help="resolve only N chemicals (smoke test)")
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print("[1/5] reading the labelled compound summary")
    long = load_summary(raw)
    df, both = collapse_cohorts(long)
    n_both = int((df.n_cohorts > 1).sum())
    if a.limit:
        df = df.head(a.limit)
    print(f"      {len(long)} rows -> {len(df)} unique chemicals; "
          f"{n_both} measured in both cohorts (cross-run reference, not external validation)")

    print("[2/5] resolving structures through PubChem")
    recs = [resolve_structure(r.Casrn, r.DTXSID, r.get("PREFERRED_NAME") or r.Compound)
            for _, r in df.iterrows()]
    df = pd.concat([df.reset_index(drop=True), pd.DataFrame(recs)], axis=1)
    std = [chem.standardise(s) for s in df["smiles_raw"]]
    df["smiles"] = [s.smiles for s in std]
    df["inchikey"] = [s.inchikey for s in std]
    df["scaffold"] = [s.scaffold for s in std]
    df["chem_flags"] = [",".join(s.flags) for s in std]
    df["structure_ok"] = [s.modellable for s in std]
    print(f"      resolved {df.smiles.notna().sum()}/{len(df)}; modellable {int(df.structure_ok.sum())}")

    print("[3/5] classifying the primary outcome")
    lab = classify_table(df, structure_ok_col="structure_ok")
    df = pd.concat([df, lab], axis=1)
    print("      " + json.dumps(df.label.value_counts().to_dict()))
    sens = sensitivity_to_fold(df, structure_ok_col="structure_ok")
    print(sens.to_string(index=False))

    print("[3b/5] cross-run concordance of the outcome inside the summary")
    conc = {}
    if len(both):
        b = both.copy()
        bl = classify_table(b)
        b = pd.concat([b.reset_index(drop=True), bl], axis=1)
        pivot = b.pivot_table(index="Casrn", columns="cohort", values="y", aggfunc="first")
        pivot = pivot.dropna()
        if len(pivot) and pivot.shape[1] == 2:
            agree = (pivot.iloc[:, 0] == pivot.iloc[:, 1]).mean()
            conc = {"n_chemicals_in_both": int(len(pivot)), "label_agreement": float(agree)}
            print(f"      {len(pivot)} chemicals labelled in both runs; agreement {agree:.2f}")
    if not conc:
        print("      not enough chemicals labelled in both runs to measure agreement")

    print("[4/5] auditing overlap with the wider screen")
    auc, auc_chems = load_auc(raw)
    lab_ids = set(df.DTXSID.dropna()) | set(df.Casrn.dropna())
    auc_chems["in_labelled_by_id"] = [
        (str(r.dsstox_substance_id) in lab_ids) or (str(r.casn) in lab_ids)
        for _, r in auc_chems.iterrows()]
    overlap = {
        "labelled_chemicals": int(len(df)),
        "wider_screen_chemicals": int(len(auc_chems)),
        "overlap_by_identifier": int(auc_chems.in_labelled_by_id.sum()),
        "wider_screen_only": int((~auc_chems.in_labelled_by_id).sum()),
        "note": ("The wider screen (auc.dat) aggregates the same EPA laboratory's source files, "
                 "including the ToxCast and NTP sets that the labelled summary is built from. "
                 "It is therefore reported as cross-study concordance, not external validation."),
    }
    print("      " + json.dumps({k: v for k, v in overlap.items() if k != "note"}))

    print("[5/5] writing outputs")
    df.to_parquet(out / "chemicals_labelled.parquet", index=False)
    long.to_parquet(out / "chemicals_by_cohort.parquet", index=False)
    auc_chems.to_parquet(out / "wider_screen_chemicals.parquet", index=False)
    auc.to_parquet(out / "wider_screen_auc.parquet", index=False)
    sens.to_csv(out / "selectivity_threshold_sensitivity.csv", index=False)
    prov = {
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selectivity_fold": 3.0,
        "inputs": {str(p.relative_to(raw)): {"sha256": sha256(p), "bytes": p.stat().st_size}
                   for p in (raw / SUMMARY_ZIP, raw / AUC_RDATA, raw / CCD_CSV) if p.exists()},
        "pubchem": {"endpoint": PUBCHEM, "properties": PROPS,
                    "resolved": int(df.smiles.notna().sum()), "total": int(len(df))},
        "label_counts": {k: int(v) for k, v in df.label.value_counts().items()},
        "overlap_audit": overlap,
        "cross_run_concordance": conc,
        "chemicals_in_both_cohorts": n_both,
        "licence": ("EPA data: public domain, US Government work. PubChem: public. "
                    "Code: MIT, this repository."),
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    print(f"      {out}/chemicals_labelled.parquet and 4 more")


if __name__ == "__main__":
    main()
