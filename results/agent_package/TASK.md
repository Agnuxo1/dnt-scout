# Triage task for the SciencePal agent

You are given 20 chemicals from the wider US EPA network-formation screen that were **not**
used to fit or select any part of this model, in `candidates_unseen.csv` (name, CASRN, DSSTox id).

**Decide which 5 should go to the microelectrode-array assay first, and say what you would not act on.**

Rules, which the evaluation of your answer depends on:

1. Resolve each candidate to a structure yourself (PubChem by CASRN or DSSTox id) before anything else.
   If an identifier resolves to a mixture or an inorganic, say so and treat it as undecidable.
2. Use only `analogues_with_outcome.csv` as measured evidence. It holds the 102 chemicals
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
(`evaluation.json`), after the methodological audit of 2026-10-23:

* read-across ROC AUC **0.828** on the pre-declared scaffold split; **0.776 (0.703-0.828)** as the
  median over 20 independent fold assignments, which is the figure to quote;
* **32** assays to recover half the selective compounds against **52** in a random order
  (31-37 across the 20 splits); enrichment factor at 20 assays **1.67**, against a ceiling of 2.08;
* Mondrian conformal coverage **0.892** against a nominal 0.90, measured on held-out scaffolds.

Beating the ranking is not the point. The point is whether reasoning over the analogues, the
literature and the applicability domain produces a *better-justified* shortlist than the ranking
alone, and whether it declines the right candidates.
