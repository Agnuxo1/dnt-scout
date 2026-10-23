#!/usr/bin/env python
"""Figures and the package the SciencePal agent works from.

    python scripts/03_triage_package.py --data data/processed --results results --out results

Produces:
  * `fig_enrichment.png` — the headline figure: assays needed to recover the positives.
  * `fig_calibration.png` — conformal coverage and set sizes, including the uninformative share.
  * `agent_package/` — everything the agent needs for the held-out triage decision, and nothing
    else: the training analogues with their outcome, the 20 unseen candidates, the scoring module
    and the task statement. The 20 candidates come from the wider EPA screen and were never used
    to fit or select anything, so the decision is verifiable after the fact.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dntscout.evaluation import RNG_SEED

PALETTE = {"read_across": "#1b6ca8", "fingerprint_forest": "#5aa469",
           "physchem_logistic": "#d98c3f", "prevalence": "#9aa0a6"}
LABELS = {"read_across": "Read-across (similarity)", "fingerprint_forest": "Fingerprint forest",
          "physchem_logistic": "Physicochemical logistic", "prevalence": "Prevalence baseline"}


def fig_enrichment(pred: pd.DataFrame, ev: dict, out: Path) -> None:
    y = pred.y.to_numpy().astype(int)
    n, n_pos = len(y), int(y.sum())
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.25, 1]})
    x = np.arange(0, n + 1)
    ax.plot(x, x * y.mean(), color="#888", ls="--", lw=1.4, label="Random order (expected)")
    for k in ("prevalence", "physchem_logistic", "fingerprint_forest", "read_across"):
        order = np.argsort(-pred[f"score_{k}"].to_numpy(), kind="stable")
        ax.plot(x, np.concatenate([[0], np.cumsum(y[order])]), color=PALETTE[k],
                lw=2.2 if k == "read_across" else 1.5, label=LABELS[k])
    half = int(np.ceil(n_pos / 2))
    ax.axhline(half, color="#c0392b", lw=1, ls=":")
    t_ra = ev["models"]["read_across"]["enrichment"]["tests_for_percent_of_positives"]["50"]
    t_rand = ev["models"]["prevalence"]["enrichment"]["tests_for_percent_of_positives"]["50"]
    ax.annotate(f"half the positives:\n{t_ra} assays vs {t_rand}", xy=(t_ra, half),
                xytext=(t_ra + 12, half - 11), fontsize=9, color="#c0392b",
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1))
    ax.set_xlabel("MEA assays run (chemicals tested, in ranked order)")
    ax.set_ylabel("Selective chemicals found")
    ax.set_title(f"Fewer assays to the same findings\n{n} chemicals, {n_pos} selective, scaffold-held-out")
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.grid(alpha=.25)

    ks = ("prevalence", "physchem_logistic", "fingerprint_forest", "read_across")
    ef = [ev["models"][k]["enrichment"]["enrichment_factor"]["20"] for k in ks]
    ci = [ev["models"][k]["enrichment"]["enrichment_factor_ci95"]["20"] for k in ks]
    pos = np.arange(len(ks))
    ax2.barh(pos, ef, color=[PALETTE[k] for k in ks], height=.6)
    ax2.errorbar(ef, pos, xerr=[[e - c[0] for e, c in zip(ef, ci)],
                                [c[1] - e for e, c in zip(ef, ci)]],
                 fmt="none", ecolor="#333", capsize=3, lw=1)
    ax2.axvline(1.0, color="#888", ls="--", lw=1.2)
    ax2.set_yticks(pos, [LABELS[k] for k in ks], fontsize=8)
    ax2.set_xlabel("Enrichment factor at a budget of 20 assays\n(95% CI, bootstrap over scaffold groups)")
    ax2.set_title("Only read-across clears chance")
    ax2.grid(axis="x", alpha=.25)
    fig.tight_layout()
    fig.savefig(out / "fig_enrichment.png", dpi=200)
    plt.close(fig)


def fig_calibration(pred: pd.DataFrame, ev: dict, out: Path) -> None:
    c = ev["conformal"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.0))
    names = ["All", "No effect (0)", "Selective (1)", "In domain"]
    vals = [c["coverage_all"], c["coverage_class_0"], c["coverage_class_1"], c["coverage_in_domain"]]
    ax.bar(names, vals, color=["#1b6ca8", "#9aa0a6", "#5aa469", "#8e7cc3"], width=.6)
    ax.axhline(0.90, color="#c0392b", ls="--", lw=1.3)
    ax.text(3.45, 0.905, "nominal 90%", color="#c0392b", fontsize=8, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Empirical coverage on held-out scaffolds")
    ax.set_title("Conformal coverage is measured, not assumed")
    ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="y", alpha=.25)

    shares = [c["share_singleton"], c["share_uninformative"], c["share_rejected"]]
    ax2.bar(["Decisive\n{0} or {1}", "Uninformative\n{0,1}", "Rejected\n{}"], shares,
            color=["#5aa469", "#d98c3f", "#c0392b"], width=.6)
    ax2.set_ylim(0, 1.0)
    ax2.set_ylabel("Share of chemicals")
    ax2.set_title(f"What the agent may act on\n{c['share_out_of_domain']:.0%} also fall outside the domain")
    ax2.tick_params(axis="x", labelsize=8)
    ax2.grid(axis="y", alpha=.25)
    fig.tight_layout()
    fig.savefig(out / "fig_calibration.png", dpi=200)
    plt.close(fig)


def agent_package(data: Path, results: Path, out: Path, n_candidates: int = 20) -> dict:
    """Training analogues + 20 genuinely unseen candidates + the task, ready to upload."""
    pkg = out / "agent_package"
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    labelled = pd.read_parquet(data / "chemicals_labelled.parquet")
    train = labelled[(labelled.y.notna()) & labelled.structure_ok & labelled.smiles.notna()]
    train_out = train[["PREFERRED_NAME", "Casrn", "DTXSID", "smiles", "scaffold", "label", "y",
                       "ec50_network_min", "ec50_viability_min"]].rename(
        columns={"PREFERRED_NAME": "name", "Casrn": "casrn", "y": "selective"})
    train_out.to_csv(pkg / "analogues_with_outcome.csv", index=False)

    wider = pd.read_parquet(data / "wider_screen_chemicals.parquet")
    unseen = wider[~wider.in_labelled_by_id].dropna(subset=["chnm"]).copy()
    rng = np.random.default_rng(RNG_SEED)
    cand = unseen.sample(n=min(n_candidates, len(unseen)), random_state=int(rng.integers(1 << 30)))
    cand = cand.rename(columns={"chnm": "name", "casn": "casrn",
                                "dsstox_substance_id": "dtxsid"})[["name", "casrn", "dtxsid"]]
    cand.to_csv(pkg / "candidates_unseen.csv", index=False)

    ev = json.loads((results / "evaluation.json").read_text())
    (pkg / "TASK.md").write_text(f"""# Triage task for the SciencePal agent

You are given {len(cand)} chemicals from the wider US EPA network-formation screen that were **not**
used to fit or select any part of this model, in `candidates_unseen.csv` (name, CASRN, DSSTox id).

**Decide which 5 should go to the microelectrode-array assay first, and say what you would not act on.**

Rules, which the evaluation of your answer depends on:

1. Resolve each candidate to a structure yourself (PubChem by CASRN or DSSTox id) before anything else.
   If an identifier resolves to a mixture or an inorganic, say so and treat it as undecidable.
2. Use only `analogues_with_outcome.csv` as measured evidence. It holds the {len(train_out)} chemicals
   with a known outcome: `selective` = a network effect at a concentration at least 3-fold below any
   cytotoxic concentration; `no_effect_observed` = no network response inside the tested range.
   Nothing outside this file counts as a measurement.
3. Score with `score_candidates.py`, which applies the read-across of this project
   (k=3 nearest analogues by Morgan Tanimoto similarity) and the conformal rule. Report the numbers
   it returns; do not invent them.
4. For each of the 5 you choose, give: the nearest measured analogues and their similarity, the
   score, whether the conformal set is decisive, whether it falls inside the applicability domain,
   and one sentence of mechanistic or structural reasoning. Cite any literature claim with a DOI.
5. State explicitly which candidates you refuse to rank, and why (no structure, outside the domain,
   uninformative conformal set). Refusing is a valid and expected answer.

Do not describe any chemical as safe. The question is only which assay to run next.

Reference performance of the automated ranking alone, measured on held-out scaffolds
(`evaluation.json`): read-across ROC AUC {ev['models']['read_across']['roc_auc']:.2f}, enrichment
factor at 20 assays {ev['models']['read_across']['enrichment']['enrichment_factor']['20']:.2f}
(95% CI {ev['models']['read_across']['enrichment']['enrichment_factor_ci95']['20'][0]:.2f}-{ev['models']['read_across']['enrichment']['enrichment_factor_ci95']['20'][1]:.2f}),
conformal coverage {ev['conformal']['coverage_all']:.3f} against a nominal 0.90.
""", encoding="utf-8")

    shutil.copy(Path(__file__).parent / "score_candidates.py", pkg / "score_candidates.py")
    (pkg / "README.md").write_text(
        "Self-contained package for the held-out triage decision.\n\n"
        "    pip install rdkit pandas numpy\n"
        "    python score_candidates.py --analogues analogues_with_outcome.csv "
        "--candidates candidates_unseen.csv --out scores.csv\n\n"
        "`TASK.md` states the decision to make. Data: US EPA, public domain. Code: MIT.\n",
        encoding="utf-8")
    return {"n_train": int(len(train_out)), "n_candidates": int(len(cand)), "path": str(pkg)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/processed")
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    data, results, out = Path(a.data), Path(a.results), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pred = pd.read_csv(results / "out_of_fold_predictions.csv")
    ev = json.loads((results / "evaluation.json").read_text())
    fig_enrichment(pred, ev, out)
    fig_calibration(pred, ev, out)
    info = agent_package(data, results, out)
    print(json.dumps(info, indent=1))
    print(f"figures: {out}/fig_enrichment.png, {out}/fig_calibration.png")


if __name__ == "__main__":
    main()
