# STATUS — AfriCAN DANCE computational layer

Generated 2026-07-24 from `main` @ `a0dd9e6`. Every claim below is grounded in a
repo artifact: SPEC.md statuses, git history, the CI workflow, or a live test run
(pasted in §3). Where this file and the code ever disagree, the code wins — say so
and fix this file, not the truth.

## 1 · What this is, and what runs today

This is the computational layer for an ancestry-aware colorectal-cancer genomics
project: a fusion core (a schema + provenance/calibration enforcement, SQLite in
dev; production substrate pending D4 — Postgres proposed), one analysis producer (multi-tool VUS
reclassification), and a deterministic read API over the core's views. What runs
today runs **on toy fixtures only**: 20 synthetic variants with mock tool scores,
and an 8-row static seed for the read API. Three standard-library test suites
(24 tests total) pass on every push and PR, in CI, on Python 3.8 and 3.14. No real
patient data has touched this system.

## 2 · SPEC items (statuses taken verbatim from SPEC.md, not assessed here)

| ID | Title | Layer | Status | Blocker (per SPEC.md) |
|----|-------|-------|--------|------------------------|
| SPEC-001 | Fusion-core slice: schema + provenance/calibration enforcement + ingest & read view | `core/` | FUNCTIONAL | — |
| SPEC-002 | variant_effect producer: consensus VUS reclassification + calibration flags | `producers/variant_effect/` | FUNCTIONAL | — |
| SPEC-003 | Ingestion adapters from pipeline outputs (sarek MAFs, DESeq2, IntOGen, MSISensor2, ADMIXTURE/RFMix, drug screens) | `core/ingest/` | SPECIFIED | unbuilt |
| SPEC-004 | Reference reconciliation (GRCh38 vs pangenome) | `pipeline/` + `core/` | SPECIFIED | unbuilt |
| SPEC-005 | Wire real score providers (AlphaMissense + EVE) | `producers/variant_effect/` | SPECIFIED | unbuilt; providers currently raise `NotImplementedError` |
| SPEC-006 | DeepSomatic alongside Mutect2; callset comparison | `pipeline/calling/` | SPECIFIED | unbuilt |
| SPEC-007 | Target nomination (elastic net + random forest) | `producers/target_nomination/` | SPECIFIED | unbuilt |
| SPEC-008 | GNN over PPI graph — NOVEL (G6) | `producers/gnn/` | SPECIFIED | unbuilt |
| SPEC-009 | Grounded text-to-SQL + interface views | `query/` + `interface/` | SPECIFIED | unbuilt; SPEC-015 is its deterministic prerequisite |
| SPEC-010 | Drug-response pre-screen (adds, never subtracts) | `producers/` | SPECIFIED | gated on wet-lab data |
| SPEC-011 | Organoid imaging (CellPose + CNN) | `producers/imaging/` | SPECIFIED | gated on wet-lab data |
| SPEC-012 | Causal layer (Double ML) — NOVEL (G6) | `producers/causal/` | SPECIFIED | gated on wet-lab data |
| SPEC-013 | Custom multimodal predictor — NOVEL (G6) | `producers/multimodal_predictor/` | SPECIFIED | gated on D5 + wet-lab data |
| SPEC-014 | CI enforcement: test gates + SPEC-id check on PRs | `.github/` | FUNCTIONAL | — |
| SPEC-015 | Query layer: deterministic structured read API over core views | `query/` | FUNCTIONAL | — |
| SPEC-016 | Repo hygiene: fixture namespaces + run-documentation honesty | `fixtures/`, docs | FUNCTIONAL | — |

Filesystem check at generation time: every FUNCTIONAL item's code exists;
`pipeline/` and `interface/` contain READMEs only; no SPEC item claims them built.
No disagreements found.

## 3 · What runs today (verbatim)

Local run on `main` @ `a0dd9e6`, 2026-07-24, direct execution (the supported path):

```
$ python tests/test_variant_effect.py
PASS test_matches_golden
PASS test_calibration_pending_on_every_result
PASS test_circularity_break_novel_variant_still_called
PASS test_strict_mode_hard_fails_on_placeholder
ALL TESTS PASSED

$ python tests/test_core_ingest.py
PASS test_ingest_writes_all_with_provenance
PASS test_calibration_pending_persisted
PASS test_core_rejects_bare_fact
PASS test_read_view_exposes_calibration_and_provenance
ALL CORE TESTS PASSED

$ python tests/test_query_read_api.py
PASS test_filter_population_single
PASS test_filter_population_multiple
PASS test_filter_population_rejects_merged_grouping
PASS test_filter_classification
PASS test_filter_calibration_status
PASS test_filter_gene
PASS test_query_echo_exact_sql_and_bound_values
PASS test_read_is_select_on_view_only
PASS test_provenance_summary_full_set
PASS test_provenance_summary_distinct_runs_subset
PASS test_summary_matches_producer_shape_and_values
PASS test_summary_carries_query_echo_and_populations
PASS test_calibration_survives_aggregation_mixed_statuses
PASS test_calibration_precedence_out_over_in
PASS test_calibration_clean_only_when_all_clean
PASS test_refusals_raise_named_error
ALL QUERY TESTS PASSED
```

CI (`.github/workflows/tests.yml`) runs all three suites on push to `main` and on
every PR, on Python 3.8 and 3.14, plus a mechanical SPEC-id gate on PR bodies.
Required checks as of the last observed run (PR #4): `test (py 3.8)` pass,
`test (py 3.14)` pass, `spec-id` pass. Suites are standard-library only; pytest
compatibility is UNVERIFIED (SPEC-016) — direct execution is the supported path.

## 4 · What is NOT built

- **No real data has been processed.** Everything above runs on two toy fixtures:
  20 synthetic variants with mock scores, and an 8-row static seed. The 150-tumor
  preliminary set has never touched this code.
- **`pipeline/` and `interface/` are empty layers** — READMEs only.
- **The real score providers do not exist.** `AlphaMissenseProvider`, `EVEProvider`,
  `PolyPhenProvider`, and `SIFTProvider` all `raise NotImplementedError`
  (`producers/variant_effect/providers.py`). AlphaMissense and EVE are not wired
  (SPEC-005). The producer has only ever seen mock scores.
- **All thresholds are PLACEHOLDER.** `config/variant_effect.json` is marked
  `"status": "PLACEHOLDER"`; strict mode hard-fails on it by design. Per-population
  calibration targets are undefined, so **every** producer result is stamped
  `calibration_pending` — correctly, but it means no result is yet a clean call.
- **The query layer reads exactly one view** (`v_variant_effect`) and has no
  natural-language anything. SPEC-009 (NL-to-SQL) is unbuilt.
- **No production database.** Dev/CI is embedded SQLite; Postgres is a schema
  target, not a running system. No lockfile, no lint, no typecheck configured
  (AGENTS.md §3 says so plainly).

## 5 · What unblocks the next step

Open decisions (docs/DECISIONS.md) — owner: **project owner** (D1–D6 await the
parties named in docs/build-plan.md §1/§5):

- **D-002** (PROPOSED): flat contract modules under `contracts/` — pending owner approval.
- **D-003** (PROPOSED): supported Python floor 3.8 vs 3.14 — pending owner approval; CI tests both meanwhile.
- **D1** ownership/IP of the substrate; **D2** compute & data residency; **D3** data
  governance (IRB/DUA/licensing); **D4** substrate DB build-vs-buy; **D5** custom
  predictor commit-or-gate (after Phase 2 data); **D6** reproducibility stack.

Missing domain definitions (DEFINITIONS.md §4, marked [TO BE DEFINED]) — owner:
**domain experts (the professor and collaborators)**. Each blocks the code that
needs it; the query layer refuses these by name rather than inventing values:

- per-population calibration targets (DEFINITIONS.md §3) — blocks any clean
  (non-`calibration_pending`) result;
- what makes a variant "ancestry-enriched";
- what makes a target "actionable/druggable";
- calibration adequacy — when a European-trained tool is in- vs out-of-calibration;
- the drug-response endpoint for differential sensitivity;
- disconfirmation criteria.

## 6 · Where a collaborator plugs in

Producer isolation (ARCHITECTURE.md §4.2) makes the producer slots independent:
each producer is a plugin that reads a core view and writes a provenance-tagged
result via the ingest contract, and **never imports another producer, the query
layer, or the interface**. So these can proceed in parallel without colliding:

- **`producers/target_nomination/`, `producers/gnn/`, `producers/causal/`,
  `producers/imaging/`** — empty slots, one analytical job each, compose only via
  the core. (G6: the three NOVEL ones carry the strongest controls — fixtures +
  execution evidence + expert-pinned criteria, no exceptions.)
- **`pipeline/`** — empty layer; owns data production only, writes to the core via
  the ingest contract.
- **`core/ingest/` adapters** (SPEC-003) — one adapter per upstream output format.
- **`interface/`** — open, but downstream: it reads via `query/` only, and nothing
  may depend on it.

Not parallel-safe without review: changes to `contracts/` (a reviewed act with
stated blast radius), the core schema, and any domain definition (DEFINITIONS.md is
expert-owned — implement, never author).
