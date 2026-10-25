# Originality and resource declaration

**Project:** DNT-Scout — structure-based triage for developmental neurotoxicity screening, with
calibrated abstention
**Event:** 2026 Global AI4Science Hackathon (SciencePal × CityUHK HKAI-Sci × Tencent Cloud)
**Team:** NeuroChip Twin — solo entry. Francisco Angulo de Lafuente, independent researcher.
**Repository:** https://github.com/Agnuxo1/dnt-scout (public, MIT)
**Date of this declaration:** 2026-10-23

---

## 1 · Prior work versus work created during the event

**Everything in the submitted repository was created during the event.** There is no prior codebase,
no carried-over model, no reused preprocessing and no recycled text or figure.

### Declared prior work by the same author

The author has a separate project in computational neuroscience, **NeuroChip Twin**, which is a
finalist in a different competition (AI4S Open Innovation, Pazhou, hosted on Kaggle), with an online
defence scheduled for 2026-10-30. It is declared here in the interest of full transparency, and the
relationship to this submission is stated precisely:

| | |
|---|---|
| Scientific question | **Different.** NeuroChip Twin is not about chemical triage for developmental neurotoxicity. |
| Code | **None reused.** DNT-Scout was written from scratch in a new repository. |
| Models and checkpoints | **None reused.** |
| Preprocessing pipelines | **None reused.** Data were re-downloaded from the original EPA source and processed by new code. |
| Text, figures, video | **None reused.** Every figure and every word in this submission is new. |
| Datasets | No overlap other than both being in the public domain; this project uses only the EPA network-formation assay and PubChem. |

This was handled deliberately as a **clean-room project**: a new scientific question, a new
repository and new code, specifically so that no material submitted to one competition is submitted
to another. The author's prior work in the field is cited as background and context, not as a
contribution to this entry.

## 2 · Data

| Resource | Source | Licence / status | How it was obtained |
|---|---|---|---|
| Network-formation assay EC50 values for 136 chemicals across 17 network parameters and 2 viability assays | Shafer *et al.* 2019, US EPA ScienceHub, DOI [10.23719/1503191](https://doi.org/10.23719/1503191) | **US Government work — public domain** | Re-downloaded from the official EPA source during the event; SHA256 recorded |
| Wider EPA network-formation screen (460 chemicals) used to draw genuinely unseen candidates | USEPA/CompTox-DNT-NFA-Refinement | **Public domain** | Re-downloaded during the event |
| Chemical structures (SMILES, InChIKey) | PubChem PUG-REST | **Public domain** | Resolved during the event by CASRN / DSSTox identifier |

**Raw data are not redistributed in this repository.** `scripts/01_build_dataset.py` fetches them
from the original sources and verifies them against the SHA256 manifest in `docs/provenance.json`.
Nothing in the repository is downstream of a file a reviewer cannot re-fetch and check.

**No private, proprietary, licensed or personal data of any kind were used.**

## 3 · Software and models

| Resource | Version policy | Licence | Role |
|---|---|---|---|
| RDKit | declared, not version-pinned in `pyproject.toml` | BSD-3-Clause | structure standardisation, fingerprints, scaffolds, Butina clustering |
| scikit-learn | declared, not pinned | BSD-3-Clause | logistic regression, random forest, metrics |
| NumPy, pandas, pyarrow | declared, not pinned | BSD-3-Clause / Apache-2.0 | numerics and tabular data |
| Matplotlib | declared, not pinned | PSF-based | every figure |
| pytest | optional development dependency, not pinned | MIT | the 31-test suite |

**No pretrained weights or external inference services are required by the automated ranking.**
SciencePal's Biology Agent and Anthropic's proprietary LLMs were used for agent work, development
and exploratory paid-API ablations. The latter are disclosed in `AUDIT_UPDATE_20261025.md`; they
are not a SciencePal execution and do not establish improvement. The numerical ranking models
are small, trained from scratch on the 102 modelled chemicals, and
reproducible on a laptop CPU in minutes. The read-across implementation is **of the GenRA kind** —
written here from the published method — and is **not** the US EPA GenRA service.

## 4 · SciencePal

SciencePal is used **substantively in the core step**, not for description, copy-editing or slides.

The central decision of the project — choosing which chemicals go to the laboratory — is executed
inside the SciencePal **Biology Agent** sandbox. The agent is given the 102 measured analogues with
their outcomes, 20 chemicals from the wider EPA screen that were withheld from every stage of model
fitting, selection and calibration, the project's scoring script and a task specification. Inside
the platform it executes that code, resolves structures, applies the model and the conformal rule,
and returns a structured triage report with its refusals.

- **SciencePal project link:** https://sciencepal.ai/share/248df9d7-b3aa-4607-8e4c-c4de1a9abc5e
- **Execution trace:** visible in the linked thread, including the shell commands run in the sandbox.
- **Pre-declared ablation (E9):** automatic ranking alone versus ranking + agent, scored on the same
  20 withheld chemicals, so the platform's contribution is *measured* rather than asserted.

## 4b · The demo film

The 3–5 minute demonstration video — **https://www.youtube.com/watch?v=uJkbKtojOMc** — is produced entirely from this repository by
`video/tools/`, and its own credits are in `video/CREDITS.md`. The points that matter for this
declaration:

- **Narration** is the stock voice `bm_george` of **Kokoro-82M v1.0** (hexgrad), Apache-2.0,
  synthesised offline on CPU. It is **not a clone or imitation of any real person**, and it is not
  an extract of any other recording. The same voice appears in an earlier film by this author; it
  is regenerated here from the model, so no audio from that production is reused.
- **Music** is synthesised in code (three sine chords, low-passed) — no licensed track.
- **Footage** is of two kinds only: frames drawn by our own code from our own results, and
  headless 1920×1080 captures of the **public** SciencePal share link, taken by
  `video/tools/capture_sciencepal.py`. No stock footage, no AI-generated imagery.
- **Every number shown on screen** is read from a results file and logged, with its source path,
  to `video/numbers_onscreen.json`. Figures quoted from the independent audit rather than
  recomputed here are flagged `quoted_not_recomputed` in that log.
- **Subtitles** are generated from the narration timings and keep the written form of every figure.

## 5 · AI assistance

**Claude (Anthropic), via Claude Code, was used as a programming and writing assistant throughout**,
under the author's direction. This is declared plainly because it is material to how the work was
produced:

- It wrote code, which the author directed, reviewed and ran.
- It ran the adversarial audit described in §4 of the project overview, which found and fixed three
  real defects in the evaluation (a cross-fold pooling artefact, an invalid conformal calibration,
  and a decision threshold taken from the evaluation labels).
- It drafted documentation and figures.

**Every scientific claim in this submission was checked against executed code, not against a model's
assertion.** Every number in the overview, the README and the video script is produced by a script
in the public repository and can be regenerated by a reviewer with four commands. Where a result was
weaker than first reported, the weaker number is the one published — see the corrections in the
project overview and in the repository's commit history.

## 6 · Compliance

- The work is original to this event, with the single prior-work relationship declared in §1.
- All data are public domain and are cited to their source with a DOI.
- All software dependencies are open-source under permissive licences, and are listed in §3.
- No personal data, no human subjects, no animal experiments were involved: this project is a
  retrospective analysis of published *in vitro* measurements.
- The submission makes no safety claim about any chemical. It is explicitly framed as a laboratory
  prioritisation tool, and the limitation that a negative *in vitro* result does not exclude
  developmental neurotoxicity is stated in the overview, the README and the video.
- The repository is public under the MIT licence, so every claim here is independently checkable.

## 7 · Team contributions

Solo entry. Francisco Angulo de Lafuente: scientific question and framing, experimental design,
implementation, analysis, interpretation, writing, and the decision on every scientific claim made.
