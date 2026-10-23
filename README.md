# DNT-Scout

**From chemical structure to developing neural networks: an uncertainty-aware triage agent for developmental neurotoxicity, built on SciencePal.**

> Work in progress for the 2026 Global AI4Science Hackathon (SciencePal × CityUHK HKAI-Sci). New project started on 2026-10-23.

DNT-Scout asks a question that is still open: *can we predict, from structure alone, whether an untested chemical will disrupt the formation of developing neural networks measured on microelectrode arrays (US EPA Network Formation Assay), with calibrated uncertainty and an explicit applicability domain, and turn that prediction into a laboratory decision?*

- Data: public-domain US EPA datasets, downloaded from the original sources by `scripts/` (not redistributed).
- Methods: RDKit representations, read-across (GenRA) and machine-learning baselines, conformal prediction, scaffold-held-out validation.
- Agent: the SciencePal Biology Agent runs the analysis step in its sandbox and writes the triage report.

Status, results and the resource declaration will be published here before submission.

License: MIT (code). Data keep their original public-domain/US-Government terms.
