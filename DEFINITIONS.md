# DEFINITIONS.md — domain criteria

> **OWNED BY THE DOMAIN EXPERTS** (the professor and collaborators).
> The coding agent **implements** these; it **must not author or modify** them (control I3).
> Producers and the query layer read these as **injected, fixed input** — never hardcode them (see `ARCHITECTURE.md` §4.4).
>
> Values marked **[from grant strategy]** are transcribed from `docs/sources/Domestic_Project_Research_Strategy_PF5.pdf` as candidate defaults and still need domain sign-off for the ancestry-aware context. Values marked **[TO BE DEFINED]** are not specified for this context and **block** any code that needs them until a domain owner fills them in.
>
> **Reciprocity rule:** any change to a domain value in `config/` requires updating this file in the SAME commit, and vice versa. The two never drift (AGENTS.md §1.8).

---

## 1 · Statistical thresholds

| Criterion | Value | Status |
|-----------|-------|--------|
| Driver gene FDR (q) | `< 0.05`, support from ≥2 independent methods | [from grant strategy] — confirm |
| Driver, COSMIC Cancer Gene Census (relaxed) | CGC q `< 0.25` | [from grant strategy] — confirm |
| Differential expression significance | `p < 0.05` and `|log2 fold-change| > 0.5` | [from grant strategy] — confirm |
| Multiple-testing correction | Benjamini-Hochberg, FDR `< 0.05` | [from grant strategy] — confirm |
| Germline MAF filter (somatic calling) | `< 1%` in ExAC / gnomAD / 1000G | [from grant strategy] — confirm |
| Minimum sequencing depth | `20x` | [from grant strategy] — confirm |
| VUS consensus rule (`producers/variant_effect`) | A variant is called **pathogenic** if ≥ `2` tools call pathogenic and none call benign; **benign** if ≥ `2` call benign and none call pathogenic; otherwise it remains **VUS** (`method_id: consensus_v0_min_agree`, `min_agree: 2` — controls how the four tool calls are combined into a reclassification) | **AWAITING SIGN-OFF** — currently a PLACEHOLDER in `config/variant_effect.json`; authored during the Phase-2 build and transcribed here per the reciprocity rule. Domain owner must confirm or adjust |
| IntOGen driver-evidence inclusion criteria (`producers/drivers`) | Rows are consumed as the publisher filtered them: driver methods at q `< 0.1`; smRegions significant domains q `< 0.1`; OncodriveCLUSTL linear (2D) clusters p `< 0.05`; HotMAPS 3D clusters q `< 0.05`. Default cohort scope: **colorectal (COAD/READ)**, recorded on every result | **AWAITING SIGN-OFF** — these are **IntOGen's OWN PUBLISHED settings**, transcribed verbatim from the release README into `config/intogen.json`; the producer consumes pre-filtered rows and does **not** re-filter or adjust them (control I3). Two domain questions attach: whether the cohort scope should be colorectal or pan-cancer (questionnaire **A13** — it changes the answer for PIK3CA H1047R), and whether the settings are acceptable (**A14**). Separately, whether *calibration* applies to an evidence lookup at all is **A12**. Results are stamped `calibration_pending` regardless (§3) |
| EVE class assignment (`producers/variant_effect`) | EVE's published classes are `Benign` / `Uncertain` / `Pathogenic`, assigned by **retaining the 75% most confident class assignments** over all possible amino-acid substitutions and labelling the remaining 25% `Uncertain`. Observed class boundaries (not published as thresholds, and effectively global rather than per-protein): benign ≤ ~0.359, pathogenic ≥ ~0.641 | **AWAITING SIGN-OFF** — this is **EVE's OWN PUBLISHED SCHEME**, transcribed verbatim from evemodel.org into `config/eve.json`, **not authored by the agent** (control I3). The 75%-retained operating point was chosen by the publisher for a general setting; whether it is right for AA / Ghanaian / Ethiopian cohorts is a domain question — see questionnaire A11. **Separate from calibration**: results stay `calibration_pending` regardless (§3) |
| AlphaMissense score→class cutoffs (`producers/variant_effect`) | `likely_benign` if `am_pathogenicity < 0.34`; `likely_pathogenic` if `> 0.564`; `ambiguous` otherwise. These map onto the repo's tool-call vocabulary as benign / pathogenic / uncertain respectively | **AWAITING SIGN-OFF** — these are **AlphaMissense's OWN PUBLISHED DEFAULTS**, transcribed verbatim from the publisher's README (Zenodo `10.5281/zenodo.8208688`) into `config/alphamissense.json`, **not authored by the agent** (control I3). The publisher chose this operating point for a general population; whether it is the right one for AA / Ghanaian / Ethiopian cohorts is a domain question — see questionnaire A9. Note this is **separate from calibration**: results stay `calibration_pending` regardless of these cutoffs (§3) |

## 2 · Tumor subtyping

| Criterion | Value | Status |
|-----------|-------|--------|
| MSI status (from WES) | MSISensor2 `≥ 3.5` = MSI-H, else MSS | [from grant strategy] — confirm |
| Tumor mutation burden | TMB-high `≥ 10 mut/Mb`, else TMB-low | [from grant strategy] — confirm |
| Combined subtypes | TMB-H/MSI-H, TMB-H/MSS, TMB-L/MSI-H, TMB-L/MSS | [from grant strategy] — confirm |

## 3 · Ancestry

| Criterion | Value | Status |
|-----------|-------|--------|
| Continuous ancestry | AFR proportion, ADMIXTURE (K=5) global + RFMix local | [from grant strategy] — confirm |
| Discrete AFR strata (if/when used) | Low `≤ 30%` · Medium `30–80%` · High `≥ 80%` | [from grant strategy] — confirm; and note: a continuous→discrete step is its own reviewed component |
| Populations (never a monolithic "African") | Ghanaian · Ethiopian · African American · Non-Hispanic White | fixed |
| Per-population calibration targets | — | **[TO BE DEFINED]** — required before any tool's calibration flag can be set |

## 4 · Operational domain definitions (not in the grant — required from domain owners)

These are the definitions the agent is explicitly forbidden to invent. Each **blocks** the code that depends on it until defined.

| Definition | Needed by | Status |
|------------|-----------|--------|
| What makes a variant **"ancestry-enriched"** (effect size, frequency-delta, significance, per-population) | `producers/variant_effect`, `producers/drivers`, query | **[TO BE DEFINED]** |
| What makes a target **"actionable" / "druggable"** (DGIdb evidence tier, druggability score cutoff) | `producers/target_nomination`, query | **[TO BE DEFINED]** |
| **Calibration adequacy** — when a European-trained tool is "in-" vs "out-of-calibration" for a population | `core/provenance`, all producers | **[TO BE DEFINED]** |
| **Drug-response endpoint** for differential sensitivity (IC50 fold-change, Emax delta, significance) | `producers/causal`, `producers/imaging` | **[TO BE DEFINED]** |
| **Disconfirmation criteria** — what counts as "ancestry effect smaller than the pilot suggested" | query, interface | **[TO BE DEFINED]** |

---

*If a producer or the query layer needs a value marked **[TO BE DEFINED]**, the agent must stop and request it from a domain owner (AGENTS.md §6). It may not choose a value to unblock itself.*
