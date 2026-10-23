# YouTube metadata — DNT-Scout film

**Published:** https://www.youtube.com/watch?v=uJkbKtojOMc (public, 2026-10-23)

Written out here so the published description is reviewable and reproducible, and so every claim in
it can be checked against a file in the repository.

## Title

```
DNT-Scout — which chemicals deserve a neurotoxicity assay first? (SciencePal AI4Science Hackathon 2026)
```

## Description

```
From a chemical structure alone, DNT-Scout ranks compounds by how likely they are to SELECTIVELY
disrupt the formation of neuronal networks in development — and refuses to answer when the
structural evidence is too thin to decide.

On the US EPA microelectrode-array network-formation assay, half the active compounds are found
after 32 assays instead of 51.5 in a random order: about a third of the laboratory work removed.
An independent audit, by a separate agent that never saw the code, reproduced all 185 numeric
fields, rebuilt the labels from the agency spreadsheet (136/136 identical), and ran 999 label
permutations with the whole learning procedure refitted each time. None of them reached the
observed result — p = 0.001.

This is a retrospective evaluation on a cohort the agency deliberately enriched with suspects, and
it is a laboratory prioritisation tool, not a safety verdict: a negative result in a dish does not
exclude harm in development, as the OECD guidance says directly.

── CHAPTERS ──
0:00  The problem — which chemical goes on the plate first?
0:33  What counts as a hit, and the trap this endpoint avoids
1:04  From a structure to a decision
1:30  The result
2:03  Then somebody else tried to break it
2:35  The decision runs inside SciencePal
3:00  What it tells you, and what it does not

── LINKS ──
Code, data and every number in this film:  https://github.com/Agnuxo1/dnt-scout
The SciencePal agent run, replayable:      https://sciencepal.ai/share/248df9d7-b3aa-4607-8e4c-c4de1a9abc5e
Source data — Shafer et al. 2019, US EPA:  https://doi.org/10.23719/1503191

── HOW THIS FILM WAS MADE ──
Every scene declares what it is showing with a tag in the corner: MEASURED, RESULTS, ILLUSTRATION
or LIVE APP. No number is typed into a frame by hand — all 13 figures on screen are read from a
results file and logged, with their source path, to video/numbers_onscreen.json; the six quoted
from the independent audit rather than recomputed are flagged as such.

Narration: the stock voice bm_george of Kokoro-82M v1.0 (Apache-2.0), synthesised offline on CPU.
Not a clone or imitation of any person. Score: three sine chords written in code, so the film owes
nothing to a music licence. SciencePal footage: headless 1920×1080 captures of the public share
link above. No stock footage, no AI-generated imagery.

Full credits and licences: https://github.com/Agnuxo1/dnt-scout/blob/main/video/CREDITS.md

── ENTRY ──
2026 Global AI4Science Hackathon (SciencePal × CityUHK HKAI-Sci × Tencent Cloud).
Solo entry by Francisco Angulo de Lafuente. All code, figures, results and text created during the
event; data are public domain and re-downloaded from source. Built with assistance from Claude
(Anthropic) under the author's direction; every scientific claim was checked against executed code.
```

## Tags

```
computational toxicology, developmental neurotoxicity, read-across, cheminformatics, RDKit,
conformal prediction, trustworthy AI, microelectrode array, new approach methodologies, US EPA,
AI4Science, SciencePal, drug screening, QSAR, machine learning
```

## Settings

| Setting | Value | Why |
|---|---|---|
| Visibility | **Public** | Fran's decision, 2026-10-23. The repository is already public and the hackathon rules do not restrict publishing before submission. |
| Category | Science & Technology | |
| Made for kids | **No** | |
| Subtitles | upload `video/subs_en.srt` as English | The film already carries burned-in captions; the uploaded track adds selectable, indexable and auto-translatable subtitles. |
| Language | English | |
| Altered content disclosure | **No** — the film contains no synthetic depiction of a real person, place or event. The narration is a disclosed synthetic voice and is described as such in the description. | |

## Chapter timings

Derived from `video/narration.json` (scene durations plus the 0.55 s tail). If the film is
re-rendered, regenerate these rather than trusting the list above.
