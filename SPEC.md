# SPEC.md — spec-item registry (control I6)

> The referent for "traces to a spec item" (system prompt prime directive; AGENTS.md §2 I6, §4).
> Every change cites a SPEC- ID from this registry. **New work adds its spec item here BEFORE code.**
> Orphan code (no SPEC parent) and orphan specs (no aim/R01 objective parent) both fail review.
>
> Status ladder (docs/build-plan.md §3): **SPECIFIED** (reasoned, decision-recorded, unbuilt) →
> **FUNCTIONAL** (runs end-to-end, acceptance met). Acceptance criteria are executable — each maps
> to a check that runs, not narration (I2). Scope below is taken from `docs/build-plan.md`; nothing
> here invents scope beyond it.
>
> **Readiness is a second, independent axis** (orthogonal to Status — an item can be SPECIFIED and
> AVAILABLE, or SPECIFIED and GATED): **AVAILABLE** = could be started now, no external dependency;
> **GATED** = cannot start regardless of effort, gate named; **UNKNOWN** = the repo states no basis
> either way (never guessed). Gates are cited, not invented.

| ID | Title | Owning layer | Aim / R01 objective | Status | Readiness |
|----|-------|--------------|---------------------|--------|-----------|
| SPEC-001 | Fusion-core slice: schema + provenance/calibration enforcement + variant_effect ingest & read view | `core/` | Substrate precondition for all aims (build plan Phase 1) | FUNCTIONAL | AVAILABLE |
| SPEC-002 | variant_effect producer: multi-tool consensus VUS reclassification with per-population calibration flags | `producers/variant_effect/` | Aim 1 assist (build plan Phase 2 — first shippable win) | FUNCTIONAL | AVAILABLE |
| SPEC-003 | Ingestion adapters from existing pipeline outputs (sarek MAFs, DESeq2 tables, IntOGen, MSISensor2, ADMIXTURE/RFMix, drug-screen readouts) | `core/ingest/` | Substrate for all aims (Phase 1) | SPECIFIED | AVAILABLE (Phase 1 is "Now" per build plan §6) |
| SPEC-004 | Reference reconciliation: key variants by (locus, ref-context); reconcile GRCh38 vs. pangenome callsets; flag pangenome-only-in-African-ancestry candidates | `pipeline/` + `core/` | Aim 1 (Phase 1; load-bearing against reference bias) | SPECIFIED | AVAILABLE (Phase 1 is "Now" per build plan §6) |
| SPEC-005 | Wire real score providers (AlphaMissense + EVE pre-computed scores; retain PolyPhen/SIFT) behind the existing provider interface | `producers/variant_effect/` | Aim 1 (Phase 2) | SPECIFIED | AVAILABLE (Phase 2 "quick win" per build plan §6) |
| SPEC-006 | DeepSomatic added at the calling step, run in parallel with Mutect2; callset comparison to quantify reference/caller bias | `pipeline/calling/` | Aim 1 (Phase 2) | SPECIFIED | AVAILABLE (Phase 2 per build plan §6) |
| SPEC-007 | Target nomination: elastic-net + random-forest ensemble; DGIdb (druggability), MatrixEQTL (eQTL), Cox (survival) as edges on target nodes | `producers/target_nomination/` | Aim 2a (Phase 3) | SPECIFIED | UNKNOWN (build plan §6: "once the substrate is FUNCTIONAL" — substrate = Phase 1, whose SPEC-003/004 are still SPECIFIED; whether the precondition is met is ambiguous) |
| SPEC-008 | GNN over the PPI graph (STRING/BioGRID tagged with study mutation + expression data) — NOVEL, strongest controls (G6) | `producers/gnn/` | Aim 2a (Phase 3) | SPECIFIED | UNKNOWN (same §6 precondition as SPEC-007) |
| SPEC-009 | Query layer: grounded text-to-SQL with schema validation + literature retrieval; interface views (cohort explorer, evidence-chain viewer, target dashboard) | `query/` + `interface/` | The distillation deliverable (Phase 4) | SPECIFIED | UNKNOWN (same §6 precondition as SPEC-007) |
| SPEC-010 | Drug-response pre-screen (GDSC/CCLE/DepMap-trained) as triage that only adds, never subtracts | `producers/` (Phase 5) | Aim 2b (Phase 5 — gated on wet-lab data) | SPECIFIED | GATED — organoid specimens / drug-screen data do not exist yet (build plan §6: "Phase 5 cannot start until organoid specimens/drug-screen data exist") |
| SPEC-011 | Organoid imaging: CellPose segmentation + CNN morphological features | `producers/imaging/` | Aim 2b (Phase 5 — gated on wet-lab data) | SPECIFIED | GATED — same wet-lab data gate (build plan §6) |
| SPEC-012 | Causal layer: Double ML / causal forests, validated against CRISPR knock-in/reversion isogenics — NOVEL, strongest controls (G6) | `producers/causal/` | Aim 2b (Phase 5 — gated on wet-lab data) | SPECIFIED | GATED — same wet-lab data gate (build plan §6) |
| SPEC-013 | Custom multi-modal variant predictor (decision D5: commit only if Phase 2 leaves meaningful residual VUS) — NOVEL, strongest controls (G6) | `producers/multimodal_predictor/` | Aim 2b (Phase 5 — gated on D5 + wet-lab data) | SPECIFIED | GATED — decision D5 (OPEN, after Phase 2 data) + wet-lab data (build plan §6) |
| SPEC-014 | Agent-control CI enforcement: test gates on push/PR + mechanical SPEC-id check on every PR | repo tooling (`.github/`) | Cross-cutting — the control protocol itself (docs/risk-and-agent-control.md Part 3) | FUNCTIONAL | AVAILABLE |
| SPEC-015 | Query layer: deterministic structured read API over core read views (no NL) — filters, per-population VUS summary, query/provenance echo, result-level calibration caveat, named refusals for undefined criteria | `query/` | The distillation deliverable (Phase 4 precursor — the deterministic layer SPEC-009's NL front-end must translate INTO, never around; docs/risk-and-agent-control.md S5) | FUNCTIONAL | AVAILABLE |
| SPEC-016 | Repo hygiene: disjoint fixture ID namespaces across fixture directories + run/documentation honesty (docs claim only what was executed) | repo tooling (`fixtures/`, docs) | Cross-cutting — fixture integrity (G4) and execution-honesty (G3) | FUNCTIONAL | AVAILABLE |
| SPEC-017 | Status truthfulness: docs never assert undecided decisions; Readiness axis; human-owned data inventory; generated STATUS + CI drift gate | repo tooling (`docs/`, `tools/status/`) | Cross-cutting — execution-honesty (G3) and no-drift discipline (docs/risk-and-agent-control.md) | FUNCTIONAL | AVAILABLE |
| SPEC-018 | Local dev dashboard: static status.json renderer (architecture + SPEC/phase views, blockers) + read-only localhost shim over the query API | dev tooling (`tools/status-ui/`) | Cross-cutting — developer ergonomics only; NOT the researcher UI (R7 — interface/ stays empty and reserved) | FUNCTIONAL | AVAILABLE |
| SPEC-019 | Collaborator-map correctness: STATUS §6 producer slots derive from the single source (ARCHITECTURE.md §5 via producer_slots[]) and carry their Readiness — no hand-maintained lists | repo tooling (`tools/status/`) | Cross-cutting — no-drift discipline (G3) + I6 traceability | FUNCTIONAL | AVAILABLE |

## Acceptance criteria for FUNCTIONAL items

### SPEC-001 — fusion-core slice
Executable acceptance (all in `tests/test_core_ingest.py`, run per `AGENTS.md` §3):
- ingest writes every producer record, each retrievable via the read view with producer + method populated;
- `calibration_pending` survives the write→read round-trip on every record;
- the core **refuses** a record with stripped provenance and writes nothing on rejection (no bare facts);
- the read view exposes calibration status and provenance fields (this is the only surface the query layer may read).

### SPEC-002 — variant_effect producer
Executable acceptance (all in `tests/test_variant_effect.py`, run per `AGENTS.md` §3):
- output on the golden fixture reproduces `fixtures/variant_effect/expected_output.json` exactly (G4);
- every result is stamped `calibration_pending` while per-population calibration targets remain [TO BE DEFINED];
- a clinical-DB-absent variant is still reclassified by structure/evolution tools (circularity break);
- strict mode hard-fails on PLACEHOLDER config, so invented cutoffs can never silently ship (I3).

### SPEC-014 — agent-control CI enforcement
Executable acceptance (observed, not asserted):
- both test suites run in CI on push to `main` and on every pull request, on both documented
  Python versions (floor + dev version, per AGENTS.md §Environment / D-003);
- a pull request whose body contains no `SPEC-NNN` reference FAILS the `spec-id` check, and the
  failure message names the fix and points at SPEC.md;
- the gate was observed failing on a SPEC-less PR body and passing after the body was corrected
  (demonstrated on the PR that introduced it).
Known gap (follow-up): the check matches the SPEC-NNN pattern only; it does not yet validate
that the cited ID exists in SPEC.md.

### SPEC-015 — query layer: deterministic structured read API
Executable acceptance (all in `tests/test_query_read_api.py`, run per `AGENTS.md` §3):
- each filter (population, classification, calibration status, gene) returns exactly the matching
  `v_variant_effect` rows — and the population filter accepts ONLY `AA/GHA/ETH/NHW`, rejecting any
  combined-ancestry grouping;
- every result object carries, as first-class fields: the rows, the EXACT SQL executed with its
  bound filter values, a provenance summary (producer, version, method, distinct-run count), a
  result-level calibration flag, and the explicit population(s) covered;
- the result-level calibration flag follows precedence `calibration_pending > out_of_calibration >
  in_calibration`, including when a summary aggregates a MIX of row statuses — the caveat survives
  aggregation (counts and percentages never render clean when any contributing row is caveated);
- the per-population VUS summary reuses the producer's exact summary shape (n, vus_before/after
  (+pct), pathogenic, benign; overall + per_population) — no second summary format exists;
- a query requiring a `[TO BE DEFINED]` definition (ancestry-enriched, actionable/druggable,
  disconfirmation criteria) raises a named error identifying the missing definition and stating a
  domain owner must supply it — each refusal is tested;
- the suite runs in CI like the others (`.github/workflows/tests.yml`).

### SPEC-016 — repo hygiene: fixture namespaces + run-documentation honesty
Executable acceptance:
- variant IDs in `fixtures/query/` are q-prefixed and share NO identifier with
  `fixtures/variant_effect/` — checked by diffing the two fixtures' ID sets;
- `tests/test_query_read_api.py` passes with identical semantics after the rename
  (same test count, same assertions, same pass/fail behavior — before/after output
  pasted on the PR);
- every run-command claim in AGENTS.md §3 and test docstrings names a path that was
  actually executed end-to-end; unverified paths are labelled unverified, not claimed.

### SPEC-017 — status truthfulness
Executable acceptance:
- no doc asserts PostgreSQL (or any D4 option) as the decided production substrate while D4 is
  OPEN — grep `postgres|pgvector` shows only proposed/pending-D4 framings or option lists;
- every SPEC item carries a Readiness value (AVAILABLE / GATED-with-named-gate / UNKNOWN) in the
  registry table, and Status values are unchanged by its introduction;
- `docs/DATA-INVENTORY.md` exists, is human-owned, and asserts no custody the repo does not state
  (UNKNOWN by default);
- `python tools/status/generate_status.py` regenerates `docs/status.json` and `docs/STATUS.md`
  deterministically from repo state (no timestamps, no absolute paths);
- the CI `status-drift` job fails when the committed artifacts differ from a fresh regeneration,
  and passes after regeneration — observed failing once on a deliberate edit.

### SPEC-018 — local dev dashboard
Executable acceptance (shim checks in `tests/test_status_ui_shim.py`; UI checks verified by
running the shim and exercising the page — commands in `tools/status-ui/README.md`):
- the page renders every Section-1 fact from `docs/status.json` only — no state is computed in
  the browser (View A node states and View B rows both trace to status.json fields);
- View B shows Status AND Readiness for all 17 items, with UNKNOWN visually distinct from GATED,
  and filters by Readiness;
- Section 2 renders each `not_built` entry as fact + basis, unsoftened; Section 3 renders
  decisions and undefined definitions with owners, marked human-owned;
- the shim is stdlib-only, localhost-bound, GET-only (non-GET → 405), never writes, imports
  `query/` but never `producers/` or `core/ingest`;
- a summary response carries the result-level calibration flag and the UI renders it as a
  top-of-panel banner, not a footer;
- a refusal (undefined criterion) returns and renders as an explanation naming the missing
  definition, not a stack trace;
- the data source is visibly labelled as the toy fixture;
- the suite runs in CI like the others; the drift check stays green after regenerating.

### SPEC-019 — collaborator-map correctness
Executable acceptance:
- no hand-maintained producer-slot list exists in `tools/status/generate_status.py` — §6 is
  generated from `producer_slots[]`, which parses the ARCHITECTURE.md §5 map (single source);
- every slot in STATUS.md §6 renders with its SPEC Readiness (or "no SPEC item" for orphans),
  so GATED slots are never presented as available work;
- a slot added or renamed in ARCHITECTURE.md §5 changes §6 on regeneration (and the drift gate
  then enforces committing the regeneration) — demonstrated by the four-vs-seven fix itself;
- artifacts regenerated; `status-drift` green.

## Acceptance criteria for SPECIFIED items

Taken from the phase gates in `docs/build-plan.md`; to be decomposed into executable checks when the
work starts (I2), before any code:
- SPEC-003/004 (Phase 1): a researcher runs one query joining ≥3 modalities and gets a provenance-tagged result.
- SPEC-005/006 (Phase 2): reclassification runs end-to-end on the 150-tumor preliminary data; VUS-fraction
  reduction measured (target ~90% → ~25–30%, a target, not a promise).
- SPEC-007/008 (Phase 3): a ranked druggable-target list that reproduces/extends the "12 candidates," each
  with its full evidence chain visible.
- SPEC-009 (Phase 4): a cross-modal NL question returns a cited, query-backed answer.
- SPEC-010/011/012/013 (Phase 5): imaging pipeline quantifies morphology; causal estimates bidirectionally
  validated against CRISPR isogenics. Phase 5 does not start until organoid/drug-screen data exist.
