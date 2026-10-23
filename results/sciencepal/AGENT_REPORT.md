# SciencePal Biology Agent — triage report (verbatim agent output)

> **Provenance.** This is the output of the SciencePal **Biology Agent** (execution model Kimi K3),
> run on 2026-10-23 inside the SciencePal sandbox, reproduced here unedited. It is the agent's own
> text and its own numbers, not ours, and it is kept verbatim so the ablation in
> `ABLATION.md` can be checked against it.
>
> **Thread:** https://sciencepal.ai/share/248df9d7-b3aa-4607-8e4c-c4de1a9abc5e
> **Inputs uploaded:** `TASK.md`, `analogues_with_outcome.csv`, `candidates_unseen.csv`,
> `score_candidates.py`. `scores.csv` — the answer from our own external run — was deliberately
> **not** uploaded, so the agent could not copy it.
> **Artifacts the agent produced in its sandbox:** `DNT_triage_report.md`, `scores_resolved.csv`,
> `candidates_resolved.csv` (plus PDF and DOCX renderings), all visible in the thread.

---

# Developmental-Neurotoxicity Triage: Which 5 Candidates Go to the MEA Assay First

## 1. What the scoring script returned

I ran `score_candidates.py` (RDKit 2025.09.3, pandas, numpy) against `analogues_with_outcome.csv`
and `candidates_unseen.csv`. The script's own PubChem resolver is unreachable from this sandbox
(NCBI returns a "WWW Error Blocked Diagnostic" page for every PUG-REST call, even with a browser
User-Agent), so I resolved each candidate to a structure myself and passed the resolved structures
in via the `smiles` column, which the script reads before falling back to its resolver. The
analogue table and all scoring logic are unchanged.

The script reported, on stderr:

```
analogues: 102 (49 selective) | conformal q={0: 0.822429906542056, 1: 0.7313432835820896} | applicability domain: nearest-analogue Tanimoto >= 0.16
```

and, on the ranked table:

```
5 chemicals recommended for the next assay round; 1 of them have a decisive 90% conformal set (6 undecidable, 6 uninformative).
```

The automated ranking (in-domain candidates only, ranked by similarity-weighted score) is:

| rank | candidate | score | nearest-analogue Tanimoto | in-domain | decision | conformal set |
|---|---|---|---|---|---|---|
| 1 | Doxylamine succinate | 1.0000 | 0.372 | True | test_first | {1} |
| 2 | Atorvastatin calcium | 0.6884 | 0.237 | True | uninformative | {0,1} |
| 3 | Mifepristone | 0.6765 | 0.167 | True | uninformative | {0,1} |
| 4 | Haloperidol | 0.3950 | 0.224 | True | uninformative | {0,1} |
| 5 | Oxytetracycline dihydrate | 0.3778 | 0.500 | True | uninformative | {0,1} |
| 6 | Trichlorfon | 0.3750 | 0.235 | True | uninformative | {0,1} |
| 7 | 2,4-Dichlorophenoxyacetic acid | 0.2814 | 0.310 | True | uninformative | {0,1} |
| 8 | Perfluorooctanoic acid | 0.2632 | 0.200 | True | deprioritise | {0} |
| 9 | Perfluoroundecanoic acid | 0.2632 | 0.200 | True | deprioritise | {0} |
| 10 | Dibutyl 1,2-benzenedicarboxylate | 0.2456 | 0.583 | True | deprioritise | {0} |
| 11 | Ethylbenzene | 0.0000 | 0.300 | True | deprioritise | {0} |
| 12 | 4:4 Fluorotelomer alcohol | 0.0000 | 0.185 | True | deprioritise | {0} |
| 13 | Terbufos | 0.0000 | 0.516 | True | deprioritise | {0} |
| 14 | Diazoxon | 0.0000 | 0.304 | True | deprioritise | {0} |
| — | Difluoromethyl 1H,1H-perfluoropropyl ether | 0.6468 | 0.107 | False | undecidable | — |
| — | tris(Trifluoroethoxy)methane | 0.3315 | 0.137 | False | undecidable | — |
| — | Heptafluorobutyramide | 0.3041 | 0.150 | False | undecidable | — |
| — | Perfluorobutanesulfonyl fluoride | 0.0000 | 0.107 | False | undecidable | — |
| — | Fluorotelomer alcohol 4:2 | 0.0000 | 0.160 | False | undecidable | — |
| — | Guarana from ground, unprocessed seed | NaN | NaN | False | undecidable | — |

These are the numbers the script returned; I did not invent any of them.

## 2. Structure resolution

I resolved each candidate to a single-parent structure. Because PubChem PUG-REST is IP-blocked from
this sandbox, I used the NCI CACTUS Chemical Identifier Resolver (which returned HTTP 200) and, for
the one compound CACTUS could not resolve, the US EPA Substance Registry Service and multiple
independent vendor/registry records. All resolved structures parse cleanly in RDKit as single
organic molecules (one fragment, carbon present). The three salts/hydrates were resolved to their
single organic parent, which the task's rule permits (they are not "salts with no single parent").

- **Oxytetracycline dihydrate** (6153-64-6) → parent oxytetracycline, C22H24N2O9. A hydrate, not a
  salt; single parent. Decidable.
- **Doxylamine succinate** (562-10-7) → parent doxylamine, C17H22N2O. Salt with a single parent.
  Decidable.
- **Atorvastatin calcium** (134523-03-8) → parent atorvastatin, C33H34FN2O5⁻. Salt with a single
  parent. Decidable.
- **4:4 Fluorotelomer alcohol** (3792-02-7) → 5,5,6,6,7,7,8,8,8-nonafluorooctan-1-ol, C8H9F9O,
  SMILES `OCCCCC(F)(F)C(F)(F)C(F)(F)C(F)(F)F` (EPA SRS record 1844529; confirmed by ChemBlink, Alfa
  Chemistry, AChemBlock). A single organic PFAS molecule. Decidable.
- **Guarana from ground, unprocessed seed** (NOCAS_1336160) → a botanical plant material (guarana
  seed), a complex mixture with no single structure. Undecidable (mixture).

## 3. The five I would send to the MEA assay first

My shortlist is the ranking's top four plus **Trichlorfon** in place of **Oxytetracycline**. I drop
Oxytetracycline because its single closest measured analogue is a no-effect compound at very high
similarity (T = 0.50), which is the strongest read-across signal in the whole set and points toward
no-effect — spending an assay slot on it first is poorly justified. Trichlorfon, by contrast, has a
selective analogue among its nearest neighbours and is a mechanistically neuroactive class.

### 1. Doxylamine succinate (rank 1, score 1.0000)
- **Nearest measured analogues:** Diphenhydramine hydrochloride (T = 0.37, selective); Tamoxifen
  (T = 0.33, selective); Methadone hydrochloride (T = 0.25, selective).
- **Read-across score:** 1.0000.
- **Conformal set decisive?** Yes — the 90% Mondrian conformal set is {1} (decisive for a selective
  effect); the script labels it `test_first`.
- **Applicability domain:** Inside (nearest-analogue Tanimoto 0.372 ≥ 0.16).
- **Reasoning:** Doxylamine is a first-generation H1 antihistamine of the ethanolamine class,
  structurally very close to diphenhydramine (both are diphenylmethane aminoethers), and all three
  nearest measured analogues are selective. First-generation H1 antihistamines cross the
  blood–brain barrier and carry central anticholinergic/sedative activity, a plausible route to
  disrupting neuronal network formation. Doxylamine is described as structurally similar to
  diphenhydramine and used as a sedative/hypnotic (Słomczyńska et al., *Prospects in Pharmaceutical
  Sciences* 22(4):44–50, 2024, DOI 10.56782/pps.216); the ethanolamine-class H1 antihistamines cross
  the BBB and exert CNS/anticholinergic effects ("Classics in Chemical Neuroscience: Deliriant
  Antihistaminic Drugs", *ACS Chem. Neurosci.*, DOI 10.1021/acschemneuro.4c00505). This is the
  single most confident pick.

### 2. Atorvastatin calcium (rank 2, score 0.6884)
- **Nearest measured analogues:** Pravastatin sodium (T = 0.24, selective); Flufenacet (T = 0.19,
  no effect); CP-409092 (T = 0.17, selective).
- **Read-across score:** 0.6884.
- **Conformal set decisive?** No — {0,1} (uninformative).
- **Applicability domain:** Inside (0.237 ≥ 0.16).
- **Reasoning:** Atorvastatin is an HMG-CoA reductase inhibitor (statin); its closest measured
  analogue, pravastatin, is also a statin and is selective in this assay, and two of three nearest
  analogues are selective. Statins can affect neuronal morphology and neurite integrity in culture
  — e.g. fluvastatin depletes cultured spinal motor neurons and causes neurite loss (Murinson
  et al., *BMC Musculoskelet Disord* 13:100, 2012, DOI 10.1186/1471-2474-13-100), and mevastatin
  accelerates loss of synaptic proteins and neurite degeneration in cortical neurons (Kannan
  et al., *Neurobiol Aging* 31(9):1543–53, 2010, DOI 10.1016/j.neurobiolaging.2008.09.004). The
  read-across to a selective statin analogue and the shared mechanism justify testing it early.

### 3. Mifepristone (rank 3, score 0.6765)
- **Nearest measured analogues:** 17β-Estradiol (T = 0.17, selective); Tetracycline (T = 0.15,
  no effect); Enadoline (T = 0.15, selective).
- **Read-across score:** 0.6765.
- **Conformal set decisive?** No — {0,1} (uninformative).
- **Applicability domain:** Inside, but only just (nearest-analogue Tanimoto 0.167, just above the
  0.16 threshold). This is the weakest domain position of my five.
- **Reasoning:** Mifepristone is a steroidal antiprogestin/antiglucocorticoid; its nearest selective
  analogue, 17β-estradiol, is also a steroid, and two of three nearest analogues are selective.
  Steroid nuclear-receptor modulation is a plausible route to altered neuronal network formation.
  I keep it in the shortlist because the read-across is positive and it is inside the domain, but I
  flag that its domain margin is thin and its conformal set is uninformative.

### 4. Haloperidol (rank 4, score 0.3950)
- **Nearest measured analogues:** p,p'-DDE (T = 0.22, selective); Spirodiclofen (T = 0.17, no
  effect); Clodinafop-propargyl (T = 0.17, no effect).
- **Read-across score:** 0.3950.
- **Conformal set decisive?** No — {0,1} (uninformative).
- **Applicability domain:** Inside (0.224 ≥ 0.16).
- **Reasoning:** Haloperidol is a butyrophenone antipsychotic and a potent D2 dopamine-receptor
  antagonist, a directly neuroactive mechanism; its nearest selective analogue p,p'-DDE is a known
  neuroactive organochlorine. The read-across is mixed (two of three nearest analogues are
  no-effect), so the conformal set is uninformative, but the mechanism and the selective analogue
  justify testing it early.

### 5. Trichlorfon (rank 6, score 0.3750) — my swap for Oxytetracycline
- **Nearest measured analogues:** Methoxychlor (T = 0.24, selective); 1-Ethyl-3-methylimidazolium
  diethylphosphate (T = 0.21, no effect); 2-Methoxyethanol (T = 0.19, no effect).
- **Read-across score:** 0.3750.
- **Conformal set decisive?** No — {0,1} (uninformative).
- **Applicability domain:** Inside (0.235 ≥ 0.16).
- **Reasoning:** Trichlorfon is an organophosphate insecticide and acetylcholinesterase inhibitor, a
  mechanistically neuroactive class; its nearest selective analogue methoxychlor is a neuroactive
  insecticide. The read-across is mixed, but testing it is more informative for finding a selective
  network effect than testing Oxytetracycline, whose closest analogue (tetracycline, T = 0.50) is a
  no-effect compound.

### Why I dropped Oxytetracycline dihydrate (rank 5, score 0.3778)
- **Nearest measured analogues:** Tetracycline (T = 0.50, no effect); Resmethrin (T = 0.16,
  selective); 17β-Estradiol (T = 0.15, selective).
- **Read-across score:** 0.3778.
- **Conformal set decisive?** No — {0,1} (uninformative).
- **Applicability domain:** Inside (0.500 ≥ 0.16).
- **Reasoning:** Oxytetracycline's single closest measured analogue is tetracycline at T = 0.50 —
  the highest similarity in the entire candidate set — and that analogue showed no effect. The
  read-across therefore points strongly toward no-effect, and the score of 0.3778 is inflated only
  by two low-similarity selective analogues (resmethrin T = 0.16, estradiol T = 0.15). Testing it
  first is a poor use of the assay budget; I would deprioritise it and run it only after the five
  above.

## 4. Candidates I refuse to rank

I refuse to rank six candidates, for three distinct reasons:

**No resolvable structure (mixture):**
- Guarana from ground, unprocessed seed (NOCAS_1336160). This is a botanical plant material
  (guarana seed), a complex mixture with no single structure. The script returns it as undecidable
  (reason: "structure not modellable"). I refuse to rank it because there is no single chemical to
  assay.

**Outside the applicability domain** (nearest-analogue Tanimoto below the 0.16 threshold):
- Difluoromethyl 1H,1H-perfluoropropyl ether (nn = 0.107)
- tris(Trifluoroethoxy)methane (nn = 0.137)
- Heptafluorobutyramide (nn = 0.150)
- Perfluorobutanesulfonyl fluoride (nn = 0.107)
- Fluorotelomer alcohol 4:2 (nn = 0.160, borderline — the script's unrounded threshold sits just
  above 0.16, so it is flagged outside)

These five are all small fluorinated/ether molecules with no measured analogue closer than the
domain boundary; the read-across has no support there, so any score would be uncalibrated. The
script returns each as undecidable (reason: "outside applicability domain"). I refuse to rank them.

**Deprioritised (decisive no-effect conformal set) — not refused, but not sent first:**
The seven in-domain candidates with a decisive {0} conformal set — Perfluorooctanoic acid,
Perfluoroundecanoic acid, Dibutyl 1,2-benzenedicarboxylate, Ethylbenzene, 4:4 Fluorotelomer
alcohol, Terbufos, Diazoxon — are not refused (they are inside the domain and have a structure),
but the conformal evidence is decisive for no observed effect, so they are not candidates for the
first assay round. I would run them only after the five above, if at all.

## 5. Bottom line

Send to the MEA assay first: **Doxylamine succinate, Atorvastatin calcium, Mifepristone,
Haloperidol, Trichlorfon.** Refuse to rank: **Guarana** (mixture, no structure) and the **five
outside-domain fluorinated/ether compounds**. Deprioritise (decisive no-effect): the seven
compounds with a {0} conformal set. I do not describe any of these as safe — the only question is
which assay to run next, and the read-across, the conformal rule and the applicability domain
together justify this shortlist and these refusals.
