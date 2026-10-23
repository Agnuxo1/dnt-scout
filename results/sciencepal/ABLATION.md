# E9 — Ranking alone versus ranking + SciencePal agent

**Pre-declared in `PLAN.md` before any result was seen:** *"The agent takes a verifiable decision:
given 20 unseen chemicals, choose 5 to assay, using only analogues from the training set, with a
structured report (evidence, uncertainty, reason, next assay) and a reproducible trace. Ablation:
automatic ranking alone vs ranking + agent."*

The point was never for the agent to beat the ranking's accuracy — with 20 chemicals and no
measured outcomes for them, there is nothing to score accuracy against. The question is narrower
and answerable: **does reasoning over the analogues, the literature and the applicability domain
produce a better-justified shortlist than the ranking alone, and does it decline the right
candidates?**

## The two arms

| | **A — ranking alone** | **B — ranking + SciencePal Biology Agent** |
|---|---|---|
| Where | our machine, `scripts/score_candidates.py` | SciencePal sandbox, [thread](https://sciencepal.ai/projects/3a2ef4ae-6cf9-4ec7-9129-a43bd06963ba/thread/248df9d7-b3aa-4607-8e4c-c4de1a9abc5e) |
| Given | the same 4 files | the same 4 files |
| PubChem PUG-REST | reachable | **IP-blocked by NCBI** |
| Output | `results/agent_package/scores.csv` | `AGENT_REPORT.md` (verbatim) |

Both arms were given `TASK.md`, `analogues_with_outcome.csv`, `candidates_unseen.csv` and
`score_candidates.py`. **`scores.csv` — arm A's answer — was deliberately withheld from arm B**, so
the agent could not copy it.

## What changed

| | A: ranking alone | B: ranking + agent |
|---|---|---|
| Candidates resolved to a structure | **16 / 20** | **19 / 20** |
| Chemicals with a decisive 90% conformal set | **0** | **1** |
| Shortlist of 5 | top 5 by score | top 4 by score **+ one reasoned substitution** |
| Refusals | 9, one undifferentiated category | 6, separated into **three distinct reasons** |
| Literature support | none | 4 DOI-cited mechanistic claims |

### 1 · It recovered the best candidate in the set, under worse conditions

Arm A discarded four candidates as unresolvable — three salts/hydrates and a botanical. Arm B, with
PubChem *blocked*, noticed the block, said so plainly rather than silently returning nothing, and
resolved the structures through the NCI CACTUS resolver and the US EPA Substance Registry Service
instead. It resolved **19 of 20**, correctly keeping only guarana seed — a genuine botanical
mixture — as unresolvable.

One of the three it recovered was **doxylamine succinate**, and it turns out to be the single
strongest candidate in the whole set: score **1.000**, and the **only** chemical of the twenty with
a decisive conformal set. Arm A never saw it, because it could not get past the succinate salt.

> **This is the ablation's clearest result.** The ranking alone missed the best candidate in the
> set for a cheminformatics reason that has nothing to do with the science — a salt it could not
> strip — and the agent recovered it by going around a blocked data source.

### 2 · It overruled the ranking, for a reason that holds up

The agent dropped **oxytetracycline** from the ranking's top five and put **trichlorfon** in its
place, on this argument: oxytetracycline's nearest measured analogue is **tetracycline at
T = 0.50 — the highest single similarity anywhere in the candidate set — and tetracycline shows no
effect.** Its score of 0.378 is propped up by two *low*-similarity selective analogues (T = 0.16
and T = 0.15), so the similarity-weighted average is being pulled away from much the strongest
piece of evidence it holds.

That is a defect of the k = 3 weighted mean that the score cannot report about itself, and seeing
it requires looking at the neighbour list rather than the number.

### 3 · Its refusals are better structured

Arm A returns one bucket of 9 "undecidable". Arm B separates them, which is what a laboratory
actually needs in order to act:

- **no resolvable structure** (1: guarana, a botanical mixture) — nothing to put on a plate;
- **outside the applicability domain** (5 fluorinated/ether compounds, nearest-analogue Tanimoto
  0.107–0.160) — a structure exists, but no evidence supports a prediction;
- **deprioritised on a decisive negative** (7 with a {0} conformal set) — not refused at all, just
  not first.

It also flagged, unprompted, that mifepristone's domain margin is thin (0.167 against a 0.16
threshold) while still keeping it — the kind of caveat a ranking has no way to express.

## Verification: the agent's numbers were checked, not trusted

Everything above would be worthless if the agent had invented its figures, so the three headline
claims were recomputed independently with this project's own code
(`scripts/verify_agent.py`), from parent structures written out by hand:

| Candidate | Agent reported | Recomputed here |
|---|---|---|
| Doxylamine | score 1.0000, T = 0.372 to diphenhydramine (selective) | **1.0000, T = 0.372** ✓ |
| Atorvastatin | score 0.6884, T = 0.237 to pravastatin (selective) | **0.6884, T = 0.237** ✓ |
| Oxytetracycline | score 0.3778, T = 0.50 to tetracycline (no effect) | **0.3792, T = 0.493** ✓ |

The oxytetracycline figure differs by 0.4%, from standardising the dihydrate slightly differently.
Nothing was fabricated, and the reasoning behind the substitution is correct.

## What this ablation does *not* show

Stated plainly, because the asymmetry is real:

- **The two arms did not face identical conditions.** PubChem was reachable for arm A and blocked
  for arm B. That handicapped arm B, so "19 versus 16" understates rather than overstates the
  agent's contribution — but it is not a controlled comparison, and we do not present it as one.
- **No accuracy was measured.** None of the 20 candidates has a measured MEA outcome, so neither
  arm can be scored for correctness. The five recommendations are a falsifiable prediction awaiting
  one plate; see "Next steps".
- **One run, one agent, one model.** This is a demonstration on 20 chemicals, not a benchmark.
- **The agent's own resolved structures are its own work** and could in principle be wrong. The
  three that matter were checked above; the other sixteen were verified only to the extent that the
  agent reports RDKit parsing them as single organic molecules.

## Bottom line

The platform's contribution is not a better number. It is **three structures the automated pipeline
threw away — one of them the only confident call in the set — one correction to the ranking that is
right for a stated and checkable reason, and refusals separated into categories a laboratory can
act on.** The ranking supplies the evidence; the agent is what reads it.
