"""The primary outcome: a *selective* effect on network formation, not cytotoxicity.

A chemical that kills the culture also flattens every electrophysiological parameter. Calling that
"neuroactive" is the main way a developmental-neurotoxicity screen fools itself, so the outcome used
throughout this project is defined against viability and keeps the ambiguous cases visible:

    selective            at least one network parameter responds at a concentration meaningfully
                         below any cytotoxic concentration (or with no cytotoxicity detected at all)
    no_effect_observed   no network parameter responded inside the tested concentration range
    inconclusive_cytotox a network response appears only at or above the cytotoxic concentration
    inconclusive_other   structure not modellable (mixture, inorganic, unresolved identity)

Only `selective` (1) and `no_effect_observed` (0) enter a model. The inconclusive classes are
reported, never silently dropped and never counted as negatives: that is the difference between a
screen that can be audited and one that cannot.

Source of the effect concentrations: Shafer et al. 2019, EPA ScienceHub, DOI 10.23719/1503191,
"All Compound Summary" (EC50 per network parameter per compound; Alamar Blue and LDH cytotoxicity
EC50 per compound). Public domain, US Government work.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: The 17 network parameters, in the abbreviations the EPA summary table uses.
NETWORK_PARAMS = ("MFR", "BR", "ISI", "%SiB", "BD", "IBI", "#AE", "#ABE", "#NS", "NSP",
                  "NSD", "%SiNS", "NS-ISI", "NSDsd", "#SiNS", "r", "MI")

#: How much more potent the network effect must be than cytotoxicity to count as selective.
#: 3-fold is the convention used in the MEA literature for separating specific neuroactivity from
#: cell death; `sensitivity_to_fold` reports what happens at 1x and 10x instead.
SELECTIVITY_FOLD = 3.0

SELECTIVE = "selective"
NO_EFFECT = "no_effect_observed"
INCONCLUSIVE_CYTOTOX = "inconclusive_cytotox"
INCONCLUSIVE_OTHER = "inconclusive_other"


@dataclass(frozen=True)
class Outcome:
    label: str
    ec50_network_min: float | None
    ec50_viability_min: float | None
    n_params_responding: int
    selectivity_fold: float | None

    @property
    def binary(self) -> int | None:
        """1 selective, 0 no effect observed, None for the inconclusive classes."""
        return {SELECTIVE: 1, NO_EFFECT: 0}.get(self.label)


def classify(ec50_params: dict[str, float], ab_cytotox: float | None,
             ldh_cytotox: float | None, fold: float = SELECTIVITY_FOLD,
             structure_ok: bool = True) -> Outcome:
    """Classify one chemical from its per-parameter and cytotoxicity EC50 values (micromolar).

    A missing EC50 means "no concentration-response fitted inside the tested range", which is the
    EPA table's own convention — not a missing measurement.
    """
    vals = {k: float(v) for k, v in ec50_params.items()
            if v is not None and not (isinstance(v, float) and np.isnan(v))}
    viab = [float(v) for v in (ab_cytotox, ldh_cytotox)
            if v is not None and not (isinstance(v, float) and np.isnan(v))]
    net_min = min(vals.values()) if vals else None
    viab_min = min(viab) if viab else None
    if not structure_ok:
        return Outcome(INCONCLUSIVE_OTHER, net_min, viab_min, len(vals), None)
    if net_min is None:
        return Outcome(NO_EFFECT, None, viab_min, 0, None)
    if viab_min is None:
        return Outcome(SELECTIVE, net_min, None, len(vals), float("inf"))
    sel = viab_min / net_min
    label = SELECTIVE if sel >= fold else INCONCLUSIVE_CYTOTOX
    return Outcome(label, net_min, viab_min, len(vals), float(sel))


def classify_table(df: pd.DataFrame, params=NETWORK_PARAMS, fold: float = SELECTIVITY_FOLD,
                   structure_ok_col: str | None = None) -> pd.DataFrame:
    """Apply `classify` to a table with one row per chemical. Returns the outcome columns."""
    missing = [p for p in params if p not in df.columns]
    assert not missing, f"missing network parameter columns: {missing}"
    for c in ("AB cytotox", "LDH cytotox"):
        assert c in df.columns, f"missing viability column {c}"
    rows = []
    for _, r in df.iterrows():
        ok = bool(r[structure_ok_col]) if structure_ok_col else True
        o = classify({p: r[p] for p in params}, r["AB cytotox"], r["LDH cytotox"], fold, ok)
        rows.append({"label": o.label, "y": o.binary, "ec50_network_min": o.ec50_network_min,
                     "ec50_viability_min": o.ec50_viability_min,
                     "n_params_responding": o.n_params_responding,
                     "selectivity_fold": o.selectivity_fold})
    return pd.DataFrame(rows, index=df.index)


def sensitivity_to_fold(df: pd.DataFrame, folds=(1.0, 3.0, 10.0), **kw) -> pd.DataFrame:
    """How the class counts move with the selectivity threshold. Published, not hidden."""
    out = []
    for f in folds:
        lab = classify_table(df, fold=f, **kw)["label"].value_counts()
        out.append({"fold": f, **{k: int(lab.get(k, 0)) for k in
                                  (SELECTIVE, NO_EFFECT, INCONCLUSIVE_CYTOTOX, INCONCLUSIVE_OTHER)}})
    return pd.DataFrame(out)
