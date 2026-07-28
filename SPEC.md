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
| SPEC-020 | drivers producer: IntOGen driver identification on the reclassified variant table | `producers/drivers/` | Aim 1 (build plan Phase 2 — "reclassified variant table feeds the IntOGen driver-identification step") | SPECIFIED | AVAILABLE (Phase 2 per build plan §6) |
| SPEC-021 | expression producer: DESeq2 / GSEA / DoRothEA transcriptomic path (R/Bioconductor). KNOWN PREREQUISITE GAP: the repo has no R tooling, no renv.lock, and Python-only CI — flagged, not solved | `producers/expression/` | Aim 2a (build plan §2 producers layer; Phase 3) | SPECIFIED | UNKNOWN (same build plan §6 "once the substrate is FUNCTIONAL" precondition as SPEC-007/008, plus the R-tooling gap) |
| SPEC-022 | Close loose ends: register orphan producer slots (I6) + finish the D4 demotion sweep in core/db.py and core/README.md | repo tooling (`SPEC.md`, `core/` docs) | Cross-cutting — I6 traceability + decision-state honesty (SPEC-017) | FUNCTIONAL | AVAILABLE |
| SPEC-023 | Drift-gate determinism: STATUS artifacts byte-identical across platforms (LF-pinned via .gitattributes) so local git-status noise cannot mask real drift | repo tooling (`.gitattributes`, `tools/status/`) | Cross-cutting — a gate that cries wolf gets ignored (G3 discipline) | FUNCTIONAL | AVAILABLE |
| SPEC-024 | Dashboard information hierarchy: Section 1 dominates, boilerplate deduplicated, file:line evidence in not_built, reference sections collapsed, print stylesheet | dev tooling (`tools/status-ui/`, `tools/status/`) | Cross-cutting — developer ergonomics (R7: still not the researcher UI) | FUNCTIONAL | AVAILABLE |
| SPEC-025 | Core data integrity: per-population variant identity (population is a property of the observation, D-004) + idempotent ingest via schema-enforced natural key (D-005) | `core/` | Substrate precondition for all aims — per-population fidelity is the project's premise | FUNCTIONAL | AVAILABLE |
| SPEC-027 | Identifier-mapping seam: `variant_id` → external identifiers (UniProt accession, transcript, locus) as its own contract, so a producer LOOKS UP identifiers and never derives them; unblocks real score providers without waiting on SPEC-004 | `contracts/` + `producers/variant_effect/` | Aim 1 — decision D-006 option (c); precondition for SPEC-005's real score providers | FUNCTIONAL | AVAILABLE |

> **SPEC-026 is reserved** — registered on branch `test/generator-parsers` (generator parser
> safety), parked and unmerged. Not duplicated here; the next free id after that branch is SPEC-028.

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

### SPEC-022 — close loose ends
Executable acceptance:
- `producers/drivers/` and `producers/expression/` each trace to a registry item (SPEC-020,
  SPEC-021) — STATUS.md §6 no longer renders them as orphan slots;
- no file in the repo asserts PostgreSQL as the decided production substrate while D4 is OPEN —
  `core/db.py` and `core/README.md` carry the same pending-D4 wording as commit 21a7d74
  (comments/prose only; no code, DDL, or behavior change);
- artifacts regenerated; `status-drift` green; all four suites unchanged (29 PASS).

### SPEC-023 — drift-gate determinism
Executable acceptance (observed on the PR):
- mechanism diagnosed and stated: `core.autocrlf=true`, no `.gitattributes`, index blobs LF;
  the generator writes LF (`newline="\n"`) into a CRLF-normalized checkout, so `git status`
  flags the artifacts while `git diff` is empty;
- after the fix, regeneration on Windows leaves BOTH `git status --porcelain` and
  `git diff --exit-code` clean;
- the gate still fails on a deliberate content edit to an artifact and passes after
  regeneration — the fix must not weaken it into always-passing;
- `.gitattributes` pins only the two generated artifacts (no repo-wide renormalization).

### SPEC-024 — dashboard information hierarchy
Executable acceptance:
- Section 1 fills the viewport on load; Sections 2–4 begin below the fold; View A reads as a
  node graph (geometry, directed edges, build-state colors) at 1440px, with the core visually
  dominant and producer slots rendered as slots (one filled, seven visibly empty);
- no prose string repeats verbatim more than twice on the page (owner attributions are
  section-level, listed once);
- `not_built` evidence strings are specific and checkable — file:line where derivable
  (e.g. `providers.py:53`) — or omitted; nothing generic;
- Sections 2–3 render collapsed-by-default (`<details>`) with count summary lines;
- `@media print` keeps the diagram a diagram and prints expanded content;
- all four suites pass; `status-drift` green after regeneration.

### SPEC-025 — core data integrity
Executable acceptance (all in `tests/test_core_integrity.py`):
- F2 regression: the same `variant_id` ingested under two populations keeps BOTH population
  associations — population is a property of the observation (result), never an overwritable
  attribute of the variant entity (D-004, PROPOSED); the `variant` table carries no
  `population_code` column (schema-enforced);
- F3 regression: re-ingesting identical records leaves the row count unchanged — one result
  per observation, natural key (variant, population, producer, method), enforced by a UNIQUE
  constraint in the SCHEMA, so the database refuses the duplicate the way it already refuses
  missing provenance (D-005, PROPOSED);
- both tests were observed FAILING against the old schema before the fix;
- all four suites pass after the change; `status-drift` green.

### SPEC-027 — identifier-mapping seam
Executable acceptance (all in `tests/test_alphamissense_provider.py`, run per `AGENTS.md` §3):
- `contracts/identifiers.py` exists as its own seam; `VariantInput` is UNCHANGED — the analysis
  contract carries no external identifier fields (asserted by a test that inspects its fields);
- a producer resolves a variant's external identifiers by LOOKUP through the seam and never
  derives them; a variant absent from the map raises `IdentifierNotFound` naming the variant
  and the map, never a guess or a default;
- the map is loadable from a committed JSON fixture today and is the same shape
  `pipeline/annotation/` + SPEC-004 will populate later — the producer does not change when
  the upstream source does;
- the seam carries no domain criteria (identifiers are facts, not thresholds — I3).

### SPEC-005 — real score providers (PARTIAL: AlphaMissense only)
> Status stays **SPECIFIED**: SPEC-005 covers AlphaMissense **+ EVE + PolyPhen + SIFT**.
> One of four is wired. `EVEProvider`, `PolyPhenProvider`, and `SIFTProvider` still
> `raise NotImplementedError`. This item does not become FUNCTIONAL until all four are wired —
> a partially-satisfied item is not a satisfied one (AGENTS.md §4).

Executable acceptance for the AlphaMissense portion (all in
`tests/test_alphamissense_provider.py`):
- the provider returns a `ToolCall` built from REAL published AlphaMissense scores, keyed by
  `(uniprot_id, protein_variant)` per decision D-006 — never a mock and never a default;
- **both** published `am_class` vocabularies normalize identically: `likely_benign`/`benign`
  and `likely_pathogenic`/`pathogenic` map to the same `ToolCall.call`, so a future switch
  between `AlphaMissense_hg38.tsv.gz` and `AlphaMissense_aa_substitutions.tsv.gz` cannot
  silently change a call (regression test for the vocabulary divergence found in D-006);
- the file of origin is recorded on every `ToolCall` (`source`) so a file switch is visible in
  stored provenance rather than silent;
- a variant with no AlphaMissense record raises `ScoreNotFound` — never guesses, never returns
  a default call; a non-missense variant (nonsense/frameshift) is "no coverage" (`None`),
  which is distinct from "not found";
- every result carries `calibration_pending`: AlphaMissense is European-calibrated and
  per-population targets are [TO BE DEFINED] (DEFINITIONS.md §3). Asserted on real-scored
  results, not only on mock ones;
- score cutoffs are AlphaMissense's PUBLISHED defaults transcribed into
  `config/alphamissense.json` and registered AWAITING SIGN-OFF in DEFINITIONS.md — not
  authored, not adjusted (I3);
- NO AlphaMissense score data is committed (CC BY-NC-SA 4.0). Tests read a gitignored local
  cache and **SKIP with a populate instruction when it is absent** — never silently pass,
  never fabricate a score;
- the fixture has **discriminating power** (audit F10 class): expectations span all three
  calls, no single expected call exceeds 70% of scored entries, and a constant-output stub
  is wrong on a MAJORITY of entries whatever it returns — enforced by
  `test_fixture_has_discriminating_power`, and demonstrated by stubbing the provider to a
  constant and observing each of the three stubs fail;
- benign controls are doubly sourced: ClinVar classifies each **Benign** or **Likely benign**
  (taken from the returned `germline_classification`, not the esearch term) AND the
  AlphaMissense score is below the published benign cut-point;
- every scored expectation is **independently corroborated** against a DIFFERENT published
  file (`AlphaMissense_hg38.tsv.gz`, keyed by genomic coordinate) so a parsing bug at
  derivation time cannot be frozen into the fixture — `tools/alphamissense/corroborate_hg38.py`,
  30/30 agreeing at 2026-07-28.

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
- SPEC-020 (Phase 2): IntOGen driver identification runs on the reclassified variant table (build plan
  §3 Phase 2); driver thresholds per DEFINITIONS.md §1 (grant-strategy values pending domain confirmation).
- SPEC-021 (Phase 3): the DESeq2 / GSEA / DoRothEA transcriptomic path runs and feeds target nomination;
  prerequisite gap — no R tooling, renv.lock, or R CI exists in the repo yet (flagged, not solved).
