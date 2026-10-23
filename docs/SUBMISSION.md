# Submission pack — ready to paste

The hackathon's checklist has four numbered items. Each is below, in the order and wording the
official page uses, so it can be copied straight into the form. Nothing here needs editing; the
only thing still missing is the video, which Fran records from `video_script.md`.

**Checked against the rules page as read on 2026-10-23.** Materials are in English, which the rules
accept ("Submit materials in Chinese or English").

---

## 01 · Project information

**Project name:** DNT-Scout

**Summary** *(paste as-is)*

> DNT-Scout decides which untested chemicals deserve a microelectrode-array run for developmental
> neurotoxicity, using chemical structure alone — and says plainly when the structural evidence is
> too thin to decide. On the US EPA network-formation assay it recovers half the selectively active
> compounds in 32 assays against an exact random-order mean of 51.5, with 33–34 assays typical
> across 200 independent splits. An independent audit's 999-permutation test, refitting the entire
> learning procedure each time, puts the signal at p = 0.001. Every prediction carries a conformal
> prediction set at 90% confidence and an applicability-domain check, and the tool abstains on 63%
> of queries rather than guessing. It is a laboratory prioritisation tool, not a safety verdict.

**The scientific question or research pain point**

> Developmental neurotoxicity is one of the most expensive endpoints in regulatory toxicology and
> one of the least covered: tens of thousands of chemicals are in commerce and a few hundred have
> been through a full battery. The OECD's *in vitro* alternative — growing cortical neurons on a
> microelectrode array and watching whether they organise into a firing network — is far faster
> than an animal study but still costs days of culture per compound. With the US EPA moving to
> phase out mammalian testing, the binding constraint stops being "is this chemical neurotoxic?"
> and becomes a scheduling problem: **of the compounds nobody has tested, which ones go on the
> plate first, and when is the structural evidence too thin to say?** That phrasing makes the
> question measurable — the answer is not an accuracy figure, it is how many assays you must run
> to find the actives.

**Target users**

> Regulatory and academic toxicologists who run or commission *in vitro* developmental-neurotoxicity
> batteries; screening groups at agencies such as the US EPA and their contract laboratories; and
> computational-toxicology teams building read-across evidence for new approach methodologies.

**Use cases**

> 1. **Ordering a screening campaign.** Given a list of untested chemicals, return the order in
>    which to run them so the actives surface earliest, with the assay budget stated.
> 2. **Deciding what *not* to run yet.** Flag the chemicals whose structure sits outside the
>    applicability domain, where any prediction would be uncalibrated, so the budget is not spent
>    on them.
> 3. **Building a read-across case.** For any candidate, return the nearest measured analogues,
>    their similarity and their measured outcomes, so a human can audit the recommendation rather
>    than trust a score.

## 02 · A working project link

> **https://sciencepal.ai/share/248df9d7-b3aa-4607-8e4c-c4de1a9abc5e**

A shared, view-only SciencePal Biology Agent run. SciencePal serves it as a replayable 147-step
recording of the whole execution. **Verified accessible from a browser with no session on
2026-10-23.**

What a judge sees: the task specification, the four uploaded files, the shell commands the agent
ran in its own sandbox (including this project's `score_candidates.py`), the structure resolution
it performed when PubChem returned HTTP 403, and the triage report it produced.

## 03 · Demo and project overview

| | |
|---|---|
| **Project overview** | `docs/DNT-Scout_overview.pdf` — **5 pages exactly** (the build script fails if it ever runs longer). Covers the technical approach, innovation, validation, limitations and next steps, as the rules require. |
| **Demo video** | `video/dnt_scout_film.mp4` — a 3:17 documentary short, 1920×1080, narrated, subtitled, built from this repository by `video/tools/`. Credits and licences in `video/CREDITS.md`. |

## 04 · Originality and resource declaration

> **`docs/resource_declaration.md`** — full version, and summarised on page 5 of the overview.

Covers: models, data, code, APIs and external tools; what is prior work versus created during the
event; team contributions; originality; and compliance. The short form:

> All code, figures, results and text were created during the event. The author has a separate,
> unrelated project (NeuroChip Twin) entered in another competition; **no code, model,
> preprocessing, text, figure or video from it is used here** — DNT-Scout is a clean-room project
> with a new scientific question, a new repository and new code written from scratch. Data: the US
> EPA network-formation assay (Shafer et al. 2019, DOI 10.23719/1503191) and PubChem, both public
> domain, re-downloaded from source and pinned by SHA256; raw data are not redistributed. Software:
> RDKit, scikit-learn, NumPy, pandas, Matplotlib, all open-source and permissively licensed. No
> pretrained models, no proprietary models, no paid APIs. Claude (Anthropic) assisted with
> programming and writing under the author's direction; every scientific claim was checked against
> executed code, and where a result turned out weaker than first reported, the weaker number is the
> one published. Solo entry.

## Going further with the evidence

The rules encourage code repositories, technical reports, agent configurations, user tests and
reproducible experiments. All five are available:

| | |
|---|---|
| **Code repository** | https://github.com/Agnuxo1/dnt-scout — public, MIT, 23 tests |
| **Technical report** | the 5-page overview, plus `README.md` at greater length |
| **Agent configuration and trace** | `results/sciencepal/AGENT_REPORT.md` (verbatim agent output) and the shared thread |
| **Controlled experiment** | `results/sciencepal/ABLATION.md` — ranking alone versus ranking + agent, pre-declared |
| **Reproducible experiments** | `pip install -e .` then four scripts regenerate every number and figure; raw data are fetched from source and verified against a SHA256 manifest |
| **Independent verification** | a separate agent reproduced all 185 numeric fields, re-implemented the method from scratch (agreement 5.55 × 10⁻¹⁷) and ran a 999-permutation significance test |

## Before submitting — checklist for Fran

- [ ] Watch `video/dnt_scout_film.mp4` end to end and confirm you are happy with it (3:17, inside the 3–5 min window; it shows the real SciencePal run, not a screenshot)
- [ ] Confirm the SciencePal share link still resolves (it is revocable — do not revoke it)
- [ ] Confirm the GitHub repository is still public
- [ ] Attach `docs/DNT-Scout_overview.pdf` and `docs/resource_declaration.md`
- [ ] Submit before **31 October, Hong Kong time (UTC+8)** — aim for 30 October, outside the Pazhou defence window
