# AlphaMissense data — licence, acquisition, and what this repo does not hold

> Written for SPEC-005 (real score providers) under decision **D-006**.
> **This repository contains NO AlphaMissense score data.** It contains code that
> reads a locally-fetched copy, and our own assertions about what that copy says.

## Licence — read before fetching

AlphaMissense predictions are published under **CC BY-NC-SA 4.0**:

- **BY** — attribution required.
- **NC** — **non-commercial use only.**
- **SA** — **share-alike**: adapted material must carry the same licence.

Verified, not assumed: the Zenodo record reports `license.id = cc-by-nc-sa-4.0`, and every
published `.tsv.gz` carries the header lines

```
# Copyright 2023 DeepMind Technologies Limited
#
# Licensed under CC BY-NC-SA 4.0 license
```

Publisher's own disclaimer (from the bundled README): *"The AlphaMissense Database and other
information provided on this site is for theoretical modelling only, caution should be
exercised in use… not intended to be a substitute for professional medical advice, diagnosis,
or treatment."*

**Citation** (required by BY):

> Cheng J, Novati G, Pan J, Bycroft C, Žemgulytė A, Applebaum T, Pritzel A, Wong LH,
> Zielinski M, Sargeant T, Schneider RG, Senior AW, Jumper J, Hassabis D, Kohli P, Avsec Ž.
> *Accurate proteome-wide missense variant effect prediction with AlphaMissense.*
> Science (2023). doi:10.1126/science.adg7492

### Open governance questions — NOT decided here

| Question | Where it lives |
|---|---|
| May we redistribute any AlphaMissense-derived data (even a small slice)? | **D3** — data governance / DB licensing — **OPEN** |
| Does **NC** permit our use if the substrate becomes reusable or commercial infrastructure? | **D3 × D1** — D1 (substrate ownership) is **OPEN** |
| Does **SA** reach our derived artifacts, and where is the boundary between our code and their data? | **D3**, and **D-007** (the repo has no LICENSE file at all) |
| Where may a fetched copy be stored (institutional HPC / cloud / laptop)? | **D2** — compute & data residency — **OPEN** |

Because those are open, this build takes the conservative route: **fetch locally, commit
nothing, redistribute nothing.** That decision is reversible in either direction once D1–D3
are settled.

## What IS committed, and why that is not redistribution

| File | Contents | Licence status |
|---|---|---|
| `fixtures/variant_effect/identifiers.json` | UniProtKB accessions per variant | UniProtKB is **CC BY 4.0** (attribution only). Accessions are identifiers, not predictions. |
| `fixtures/variant_effect/alphamissense_expected.json` | Lookup keys + **our expected call** per variant | Our own assertion about what the tool reports for a named key. **No scores, no publisher class labels.** |
| `config/alphamissense.json` | The publisher's three cut-points, quoted with citation | A short factual quotation of a documented threshold, attributed. |

The actual predictions — `am_pathogenicity` values and the publisher's `am_class` labels —
are **never** written into the repository.

## Acquiring the data

```powershell
# from the repo root (PowerShell — see AGENTS.md §Environment)
python tools/alphamissense/fetch_scores.py
```

Writes `.cache/alphamissense/scores.json`, which is **gitignored** (`/.cache/` in
`.gitignore`, alongside `*.tsv.gz`).

**It does not download the 1.2 GB file.** `AlphaMissense_aa_substitutions.tsv.gz` is
bgzip-compressed (independently-decompressable members) and sorted lexicographically by
`uniprot_id` — both verified against the published file. The fetcher binary-searches with
HTTP Range requests and decompresses only the blocks holding the accessions it needs:
roughly **200 MB transferred instead of 1.2 GB**, standard library only (`urllib` + `zlib`),
**no new runtime dependency**.

If you would rather hold the whole file, download it from the Zenodo record and point the
fetcher at a local copy — but note that storing the full set is squarely a **D2** question.

### Source of record

| | |
|---|---|
| Record | Zenodo **10.5281/zenodo.8208688** — "Predictions for AlphaMissense" |
| File used | `AlphaMissense_aa_substitutions.tsv.gz` (1,207,278,510 bytes; md5 `b9ccb339e0de6cb0a8d1973ad2026576`) |
| Key | `(uniprot_id, protein_variant)` — **no genomic coordinates**, hence reference-build independent (D-006) |
| Columns | `uniprot_id  protein_variant  am_pathogenicity  am_class` |

## Two traps in the published data

**1 · Two class vocabularies for the same thresholds.** Verified from the real files:

| File | `am_class` values |
|---|---|
| `AlphaMissense_hg38.tsv.gz` | `likely_benign` · `ambiguous` · `likely_pathogenic` |
| `AlphaMissense_aa_substitutions.tsv.gz` | `benign` · `ambiguous` · `pathogenic` |

The numeric cut-points are identical; only the labels differ. **The bundled README documents
only the `likely_*` form, and its own sample block for the aa-substitutions file contradicts
that file's actual rows.** The provider therefore normalizes both vocabularies and privileges
neither, records the file of origin on every `ToolCall`, and **raises** on an unrecognised
label rather than coercing it. Regression test:
`tests/test_alphamissense_provider.py::test_both_published_vocabularies_normalize_identically`.

**2 · Missense only.** AlphaMissense models single amino-acid substitutions. Nonsense
(`p.R1450*`), frameshift (`p.E1309fs`), and indels have no record **by construction**. The
provider returns `None` ("no coverage") for these — deliberately distinct from `ScoreNotFound`
("we expected a score and did not get one"), which raises.

## Calibration — unchanged by any of this

AlphaMissense is **European-calibrated**. Wiring real scores does not change that, and
per-population calibration targets remain **[TO BE DEFINED]** (DEFINITIONS.md §3). Every
result stays stamped `calibration_pending` and renders with that caveat, never as a clean
call — guardrails **R1** and **S1**. Asserted on real-scored results by
`tests/test_alphamissense_provider.py::test_calibration_pending_holds_on_real_scored_results`.
