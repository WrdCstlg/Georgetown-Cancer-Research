# EVE data — licence, acquisition, coverage, and what this repo does not hold

> Written for SPEC-005 part 2 of 4. **This repository contains NO EVE score data.**
> It contains code that reads a locally-fetched copy, and our own assertions about what
> that copy says.

## Licence — read before fetching

evemodel.org states, on its download page: *"The downloading of this data, and of all other data
on this site, falls under the [MIT License]."* The file it links, `https://evemodel.org/LICENSE.txt`,
is a standard MIT text.

**But read the copyright line.** It says:

```
Copyright (c) 2022 Joseph Min
```

That is the **site's author** — not the Marks Lab / OATML group who built EVE and produced the
predictions. So an MIT licence covering the site *software* is being pointed at as the licence
for the prediction *data*. Whether it actually grants rights over the predictions is unsettled.

The asymmetry matters and cuts the opposite way to intuition:

- If the MIT grant **does** cover the data, EVE is far more permissive than AlphaMissense's
  CC BY-NC-SA and we could commit score slices freely.
- If it **does not**, EVE's predictions have **no stated licence at all** — which is *more*
  restrictive than AlphaMissense, not less.

Because we cannot tell which from the published artifacts, this repo applies the **same
no-commit discipline to EVE that it applies to AlphaMissense**: fetch locally, commit nothing,
keep the cache gitignored, and report distributional statistics only. That is a conservative
default chosen so the question stays open — **not** a determination that the licence forbids
anything. Settling it is part of decision **D3**.

**Citation** (the EVE model, regardless of the data licence question):

> Frazer J, Notin P, Dias M, Gomez A, Min JK, Brock K, Gal Y, Marks DS.
> *Disease variant prediction with deep generative models of evolutionary data.*
> Nature 599, 91–95 (2021). doi:10.1038/s41586-021-04043-8

## Acquiring the data

```powershell
# from the repo root (PowerShell — see AGENTS.md §Environment)
python tools/eve/fetch_scores.py
```

Writes `.cache/eve/scores.json`, which is **gitignored** (`/.cache/` in `.gitignore`).

**It is not a bulk file download.** evemodel.org is a React SPA over a JSON API — the download
page's HTML is an empty shell, and the endpoints had to be recovered from the site's JS bundle:

| Endpoint | Returns |
|---|---|
| `/api/proteins/list/` | every published protein, as UniProt **entry names** |
| `/api/proteins/web_pid/<ENTRY_NAME>/id/` | internal numeric id |
| `/api/proteins/id/<id>/` | every variant row for that protein |

A per-protein `/download/` route exists but returned an empty (22-byte) ZIP; a `bulk/download/`
route exists and is GET-only. The JSON API is the working path.

Standard library only (`urllib` + `json`) — **no new runtime dependency**. The service returns
502/504 intermittently on larger proteins, so every call retries with backoff: a transient
gateway error must never be mistaken for missing coverage.

### Fields consumed

| Field | Use |
|---|---|
| `EVE_scores_ASM` | continuous EVE score, carried as `ToolCall.raw_score` |
| `EVE_classes_75_pct_retained_ASM` | the class the provider consumes |
| `uncertainty_ASM` | EVE's own classification uncertainty |
| `ClinVar_ClinicalSignificance` | **corroboration only** — never used to form a call |
| `frequency_gv2` | gnomAD v2 frequency; **corroboration only** |

## The key differs from AlphaMissense

EVE keys on the UniProtKB **entry name** (`P53_HUMAN`). AlphaMissense keys on the UniProtKB
**accession** (`P04637`). They are different identifiers for the same protein and are not
interchangeable.

This is exactly what the identifier seam (SPEC-027) exists for. `uniprot_entry_name` was added
to `VariantIdentifiers` as an **additive optional field** — no existing consumer changed, and
`VariantInput` was not touched. A tool asking for an identifier that is absent still gets a
named `IdentifierNotFound`, never a guess.

## Vocabulary — a third one

| Source | Class labels |
|---|---|
| `AlphaMissense_hg38.tsv.gz` | `likely_benign` · `ambiguous` · `likely_pathogenic` |
| `AlphaMissense_aa_substitutions.tsv.gz` | `benign` · `ambiguous` · `pathogenic` |
| **EVE** | **`Benign` · `Uncertain` · `Pathogenic`** |

Three published vocabularies now live in this repo. **None is privileged.** Each tool's module
normalizes its own labels into the repo's `ToolCall` vocabulary and **raises** on an
unrecognised one — including on another tool's labels, so cross-contamination is loud.

EVE's class assignment is the publisher's own: *"EVE classification when only classifying the
75% most confident of all possible amino acid substitutions."* Observed class boundaries
(≈0.359 / ≈0.641) proved **identical across proteins**, i.e. effectively global rather than
fitted per protein — verified rather than assumed, and recorded in `config/eve.json` so a
future change to that behaviour becomes visible.

## Coverage — a real gap, recorded not papered over

EVE publishes **3,211 proteins**, not the proteome. Of the grant's 15 named CRC driver genes it
covers **13**. It does **not** publish **FBXW7** or **RNF43**.

RNF43 is the one that stings: the grant's own preliminary data has it mutated in **73.6% of NHW**
versus ~44% AA and ~38% Ghanaian (p = 0.0047) — a population-varying driver this study
specifically cares about. See decision **D-009** for options; none was implemented.

The provider distinguishes **three** no-coverage states, and none of them guesses:

| State | Meaning |
|---|---|
| protein not published | EVE has no model for this protein (FBXW7, RNF43) |
| row present, unscored | EVE publishes the substitution but assigned no score |
| not a single-aa substitution | outside EVE's model by construction |

All three return `None`. A key that *should* be present but is absent raises `EveScoreNotFound`.

## Calibration — unchanged by any of this

EVE is an **evolutionary** model with no per-population calibration, exactly as AlphaMissense is
a structural one without it. Wiring real data changes nothing: per-population calibration targets
remain **[TO BE DEFINED]** (DEFINITIONS.md §3), every result stays stamped `calibration_pending`,
and it renders with that caveat rather than as a clean call — guardrails **R1** and **S1**.
Asserted by `tests/test_eve_provider.py::test_calibration_pending_holds_on_real_eve_results`.
