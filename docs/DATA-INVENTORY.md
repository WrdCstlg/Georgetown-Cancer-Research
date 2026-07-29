# DATA INVENTORY — what the system needs, and what we actually know

> **HUMAN-OWNED. A HUMAN OWNER MUST FILL THIS IN.**
> The agent may only transcribe from repo artifacts (with citation) — it must never
> assert that data exists, where it lives, or who controls it. Every field is
> **UNKNOWN** unless a repo artifact states otherwise; the artifact is then cited.
> The grant strategy describes *intent*, not current custody — nothing here is
> inferred from it. A page of honest UNKNOWNs is the correct current state and is
> itself the finding: custody, location, and access for every dataset are
> undetermined as of this writing.

Statuses: **AVAILABLE** (a repo artifact states the data is in hand) /
**PENDING** (a repo artifact states it is expected but not in hand) /
**UNKNOWN** (no repo artifact says either).

## Study datasets

| Dataset | Status | Location | Owner | Access constraint | Evidence |
|---------|--------|----------|-------|-------------------|----------|
| 150-tumor preliminary set (the Phase 2 target) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Mentioned as intent in SPEC.md (SPEC-002/005 acceptance) and docs/build-plan.md §3; docs/STATUS.md §4 confirms it "has never touched this code". No artifact states existence, location, or custody. |
| WES tumor-normal pairs (four cohorts: AA 300, NHW 100, Ghanaian 600, Ethiopian 400) | UNKNOWN | UNKNOWN | UNKNOWN | Cross-site (Ghana/Ethiopia) specimens "may carry data-use constraints" — docs/DECISIONS.md D2 (OPEN) | Cohort sizes are grant *intent* (docs/sources/); no artifact states the data exists locally. |
| RNA-seq / transcriptomes (DESeq2 tables) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Named as an ingestion-adapter input (SPEC-003; build plan §3 Phase 1). No custody stated. |
| Organoid drug-screen readouts (~50 lines) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Phase 5 "cannot start until organoid specimens/drug-screen data exist" (build plan §6) — i.e. the repo states they do NOT exist yet. |
| Organoid imaging (brightfield Day 0/7/14) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Same Phase 5 wet-lab gate (build plan §6). |
| CRISPR knock-in/reversion isogenics | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Same Phase 5 wet-lab gate (build plan §6). |
| Clinical data (SES, collection-site, environment confounders) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Required wherever causal/association claims are made (system prompt §7). No custody stated. |
| MSISensor2 / ADMIXTURE / RFMix / IntOGen / sarek MAF outputs | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Named as adapter inputs (SPEC-003). No custody stated. |

## Public reference resources

| Dataset | Status | Location | Owner | Access constraint | Evidence |
|---------|--------|----------|-------|-------------------|----------|
| AlphaMissense pre-scored DB (~71M missense variants) | AVAILABLE (public, fetched on demand) | Zenodo record `10.5281/zenodo.8208688`; **not held in this repo** — fetched into the gitignored `.cache/alphamissense/` per developer. Where a copy may be stored is D2 (OPEN) | Published by Google DeepMind; local custodian UNKNOWN | **CC BY-NC-SA 4.0 — NON-COMMERCIAL, SHARE-ALIKE, attribution required.** Verified: Zenodo `license.id = cc-by-nc-sa-4.0` and the header of every published `.tsv.gz`. Redistribution of any slice is **OPEN under D3**; the NC term interacts with **D1** (if the substrate becomes reusable/commercial infra); SA interacts with **D-007** (repo has no LICENSE file) | WIRED for the aa-substitutions file (SPEC-005 partial, SPEC-027, decision D-006): `producers/variant_effect/alphamissense.py`. NO score data committed — see `docs/alphamissense-data.md`. |
| EVE score set | AVAILABLE (public API, fetched on demand) | evemodel.org JSON API; **not held in this repo** — fetched into the gitignored `.cache/eve/` per developer. Where a copy may be stored is D2 (OPEN) | Published by the Marks Lab / OATML (Frazer et al., Nature 2021); site operated separately; local custodian UNKNOWN | **UNSETTLED.** The site states its data falls under the **MIT License**, but the `LICENSE.txt` it serves reads `Copyright (c) 2022 Joseph Min` — the **site's author**, not the group that produced the predictions. If MIT governs the data, it is permissive; if it does not, the predictions have **no stated licence at all**. Open under **D3**; this repo applies the same no-commit discipline as for AlphaMissense rather than relying on either reading | WIRED (SPEC-005 part 2 of 4): `producers/variant_effect/eve.py`. **Coverage gap:** EVE publishes 3,211 proteins and covers 13 of the grant's 15 CRC driver genes — **not FBXW7, not RNF43** (decision D-009). NO score data committed — see `docs/eve-data.md`. |
| PolyPhen / SIFT outputs | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `providers.py` TODOs. Not wired. |
| GDSC / CCLE / DepMap | UNKNOWN | Public resources; local copies UNKNOWN | Public; local custodian UNKNOWN | UNKNOWN | Named as pre-screen training data (SPEC-010; build plan §3 Phase 5). |
| STRING / BioGRID PPI | UNKNOWN | Public resources; local copies UNKNOWN | Public; local custodian UNKNOWN | UNKNOWN | Named for the GNN (SPEC-008; build plan §3 Phase 3). |
| ClinVar / COSMIC / CIViC / DGIdb / PubMed | UNKNOWN | Public resources; local copies UNKNOWN | Public; local custodian UNKNOWN | **COSMIC and some resources are license-gated for commercial use** — docs/DECISIONS.md D3 (OPEN); relevant if D1 lands on "owned infra" | Licensing constraint is the only access fact any artifact states. |

## Governance items that gate every row above

- **D2** (OPEN) — compute & data residency; cross-site data-use constraints unknown.
- **D3** (OPEN) — IRB scope, de-identification, DUAs, DB licensing.
- Build plan §7 lists "exact data location and cross-site governance constraints"
  and "IRB scope" as open questions.

*Fill protocol: a human owner edits this file directly (or dictates values); the
agent transcribes. Each filled cell should name its source (who confirmed it,
when). This file is read by `tools/status/` and summarized into `docs/STATUS.md`.*
