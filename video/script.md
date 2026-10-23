# DNT-Scout — narration script

Target **3:35** at the measured Kokoro `bm_george` pace of ~127 wpm including pauses → **455 words**.
Word counts per scene are budgeted, not guessed; the build fails the timing check if a scene drifts
by more than 15%.

Every figure spoken aloud is also shown on screen, and every number on screen is read from a
results file by `N()` and logged to `video/numbers_onscreen.json` — nothing is typed by hand.

Register: the same as the previous film in this series — measured, precise, no salesmanship.
Claims are bounded out loud: "retrospective", "on this cohort", "not a safety verdict".

---

## S1 · The problem  `0:00 – 0:35` · tag **ILLUSTRATION** · 74 words

> Tens of thousands of chemicals are in commerce. A few hundred have been tested for their effect
> on the developing nervous system.
>
> The modern alternative to an animal study is to grow cortical neurons on a microelectrode array,
> and watch whether they organise themselves into a firing network. It is faster. It still costs
> days of culture, for every single compound.
>
> So the binding question is not "is this chemical neurotoxic". It is: which ones go on the plate
> first?

## S2 · What counts as a hit  `0:35 – 1:05` · tag **MEASURED** · 63 words

> First, the trap. A chemical that simply kills the culture flattens every electrical measurement
> you can make. Calling that neuroactive is how this kind of screen fools itself.
>
> So the outcome is defined against viability. A network effect counts only when it happens at
> least three-fold below the concentration that kills the cells. Forty-nine compounds qualify.
> Twenty-eight are inconclusive, and we publish them as inconclusive.

## S3 · How it works  `1:05 – 1:35` · tag **ILLUSTRATION** · 63 words

> From a structure alone: standardise it, fingerprint it, and find its nearest measured relatives
> among a hundred and two chemicals whose answer we already know.
>
> Their outcomes, weighted by chemical similarity, become a score. A conformal prediction set turns
> that score into a statement of confidence. And when the nearest relative is too distant to say
> anything, the tool says nothing.

## S4 · The result  `1:35 – 2:10` · tag **RESULTS** · 74 words

> Test in the order the model recommends, and half the active compounds appear after thirty-two
> assays. In a random order, fifty-one and a half. Across two hundred independent splits,
> thirty-three to thirty-four.
>
> Area under the curve: zero point eight two eight on the pre-declared split, zero point seven
> seven six as the median of twenty others.
>
> This is a retrospective evaluation, on a cohort the agency deliberately enriched with suspects.

## S5 · Is it real  `2:10 – 2:45` · tag **RESULTS** · 74 words

> We attacked it. Then somebody else did.
>
> A separate agent, which never saw our code, rebuilt the labels from the agency spreadsheet, and
> reimplemented the method from scratch. Agreement: five parts in ten to the seventeenth.
>
> Then it shuffled the labels between chemical scaffolds, nine hundred and ninety-nine times,
> refitting everything on every shuffle.
>
> Not one shuffle reached our result. p equals zero point zero zero one.

## S6 · SciencePal  `2:45 – 3:15` · tag **LIVE APP** · 63 words

> The decision itself runs inside SciencePal. The agent receives the measured analogues, twenty
> chemicals withheld from everything, and our scoring code — and not our answer.
>
> Its chemical database was blocked. It said so, found another route, and recovered a compound our
> own pipeline had thrown away: the only one of the twenty it could call with confidence.

## S7 · Next step  `3:15 – 3:35` · tag **ILLUSTRATION** · 42 words

> This does not tell you a chemical is safe. A negative result in a dish does not exclude harm in
> development.
>
> It tells you which plate to run on Monday. The five it chose are a prediction. One experiment
> would settle them.

---

## Pronunciation (applied before synthesis; subtitles keep the written form)

| Written | Spoken |
|---|---|
| `µM` | micromolar |
| `EPA` | E.P.A. |
| `MEA` | M.E.A. |
| `ROC AUC` | area under the curve |
| `DNT-Scout` | D.N.T. Scout |
| `SciencePal` | Science-Pal |
| `p = 0.001` | p equals zero point zero zero one |
| `5.55e-17` | five parts in ten to the seventeenth |

## Numbers spoken, and where each one comes from

| Spoken | Source file | Path |
|---|---|---|
| 49 selective, 28 inconclusive | `results/audit/audit_01_data.json` | `selective_total`, `inconclusive_cytotox` |
| 102 chemicals | `results/evaluation.json` | `n` |
| 32 assays | `results/evaluation.json` | `models.read_across.enrichment.tests_for_percent_of_positives.50` |
| 51.5 random | `results/audit/audit_02_validity.json` | `G_random_baseline[0].mean_assays` |
| 33–34 over 200 splits | independent audit report | quoted, attributed on screen |
| 0.828 / 0.776 | `results/evaluation.json`, `results/audit/audit_02_validity.json` | `models.read_across.roc_auc`, `B_repeated_cv_summary` |
| p = 0.001, 5.55e-17, 136/136 | independent audit report | quoted, attributed on screen |
| 20 withheld candidates, 19/20 resolved | `results/sciencepal/ABLATION.md` | quoted from the agent run |
