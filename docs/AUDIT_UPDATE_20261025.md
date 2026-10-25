# Audit update - 25 October 2026

This update accompanies the original SciencePal run and film, which record the
23 October implementation. Historical files remain available in Git. The
corrected evaluation is `results/validation_20261025/`; the original `results/`
evaluation is retained for comparison.

## What changed, and what did not

Calibration and test applicability-domain similarities now use the same fit-only
reference. The forest's ranking still uses the full training fold. The CPU rerun
has **88/102 chemicals in-domain** (previously 94/102), 13.7% out-of-domain,
87.5% coverage in-domain and unchanged 89.2% overall coverage. All read-across
predictions are identical; forest ranking differs by at most 3.34e-16 from
floating-point computation. Read-across ROC is 0.8276857913 and half the 49
positives are recovered in 32 assays. These remain local retrospective results.
Coverage is 91/102 overall and 77/88 in-domain; the same prediction sets cover
14/14 outside-domain cases in this sample. Both overall and in-domain estimates
fall below the nominal 90%; the audit does not causally attribute that deficit
to filtering or scaffold shift.

Core and portable chemistry now apply one policy: remove inorganic counterions
when there is exactly one carbon-containing fragment; reject multiple
carbon-containing fragments as ambiguous. A known organic salt can be assessed
only after a parent structure has been explicitly curated and declared.
`CCO.CCCCC` is rejected by both implementations; sodium acetate is accepted.
This addresses consistency, not validation of every salt or mixture.

The portable scorer uses leave-one-out nonconformity quantiles. Its nominal 90%
sets have empirical coverage in the reported experiments; they do not carry an
unconditional split-conformal guarantee for new chemistry. Scaffold distribution
shift and applicability-domain filtering also limit coverage guarantees. No
chemical is described as safe from this result.

## API ablation: protocol deviations and negative result

The original failed/refused arm is preserved in the sprint evidence. Subsequent
Haiku arms reformulated or repaired that arm despite the no-retry rule. Both
are therefore **exploratory**, not replacements for a successful preregistered
arm. None is represented as an execution of SciencePal. No further retry was
performed in this audit.

| Arm | Repeats | ROC of averaged scores | Mean of per-repeat ROC | Assays for half the positives from averaged scores |
|---|---:|---:|---:|---:|
| A: read-across | fixed | 0.827686 | 0.827686 | 32 |
| Reformulated B: ranking + Haiku | 3 | 0.817674 | 0.820883 | 32 |
| B-prime: Haiku without ranking score | 10 | 0.788987 | 0.779553 | 37 |

The ROC of averaged scores differs from the average of ROC values. The 10 repeats
reuse the same chemicals and folds and are not ten independent cohorts. The
deterministic A score vector is fixed in every repeat, so averaging it leaves A
unchanged; the same within-fold rank aggregation and candidate folds are used
for all rows in the table. This is a comparison of point estimates, not a paired
test proving that one method is worse.
The table establishes no predictive improvement from LLM reranking. It does not
establish that all possible agents are worse. The SciencePal demonstration on
20 candidates without observed outcomes measures execution and structure
resolution, not predictive accuracy.

The API summaries have 15 and 50 successful requests, respectively. The 5-request
pending section-writing batch was recovered and settled on 25 October at an
estimated USD 0.0047. Its prose is not scientific evidence. The accounting ledger
is local; it is not a confirmed provider balance.

## Resources and provenance

Registered team: **NeuroChip Twin**. Submitted project materials: **DNT-Scout**.
These names must not be confused with reuse of the separate Pazhou project.
The operational deadline of 31 October 15:59 UTC is derived from the end of
31 October in Hong Kong; it is not an independently confirmed cutoff minute.
The official page says questionnaire timestamps govern. No official receipt
of project submission was available during this audit.

The automated prediction models are trained from scratch and need no external
inference service. Proprietary LLMs were used: SciencePal's Biology Agent,
Anthropic Claude for development, and paid Haiku API calls for the exploratory
arms. Their contribution is disclosed separately from the numerical models.
No code, model, preprocessing, text, figures or video from NeuroChip Twin/Pazhou
is introduced by this update.

The corrections pass 31 project tests. An independent behavioural review passes
18 tests covering the LMC aggregator and DNT fixes, including an instrumented
execution of all five DNT folds. The complete scientific CPU rerun was also
executed, separately, on servidor-ia; the independent reviewer did not rerun that
scientific experiment.

Source summaries are in `results/validation_20261025/ablation_B_summary.json` and
`ablation_Bprime_summary.json`; source hashes and numeric comparison are in
`verification.json`. The raw original and replacement batches are preserved in
the sprint's audit directory. This update changes evidence and documentation;
it does not prove an official competition submission or judging outcome.

## Primary references

- Shafer et al. (2019), Evaluation of Chemical Effects on Network Formation in
  Cortical Neurons Grown on Microelectrode Arrays.
  [Article](https://doi.org/10.1093/toxsci/kfz052);
  [EPA data](https://doi.org/10.23719/1503191).
- Angelopoulos and Bates, A Gentle Introduction to Conformal Prediction and
  Distribution-Free Uncertainty Quantification.
  [arXiv:2107.07511](https://arxiv.org/abs/2107.07511).
- [Official SciencePal requirements](https://sciencepal.ai/hackathon?lang=en):
  substantive platform use, 3-5 minute video, overview of at most 5 pages, and
  resource disclosure.
