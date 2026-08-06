# STATUS — AfriCAN DANCE computational layer

> GENERATED FILE — do not edit by hand. Regenerate with `python tools/status/generate_status.py` and commit both artifacts. CI fails on drift (job `status-drift`). Prose lives in the generator; every fact is transcribed from repo state. Grounding: SPEC.md statuses verbatim, docs/DECISIONS.md, DEFINITIONS.md, docs/DATA-INVENTORY.md, .github/workflows/tests.yml, and filesystem checks — never assessed.

## 1 · What this is, and what runs today

This is the computational layer for an ancestry-aware colorectal-cancer genomics project: a fusion core (a schema + provenance/calibration enforcement, SQLite in dev; production substrate pending D4 — Postgres proposed), one analysis producer (multi-tool VUS reclassification), and a deterministic read API over the core's views. What runs today runs **on toy fixtures only**: synthetic variants with mock tool scores, and a small static seed for the read API. The test suites pass in CI on every push and PR, on Python 3.8 and 3.14. No real patient data has touched this system.

## 2 · SPEC items (statuses taken verbatim from SPEC.md, not assessed here)

Status = where the work is (SPECIFIED → FUNCTIONAL). Readiness = whether it can start now (AVAILABLE / GATED with named gate / UNKNOWN) — the two axes are orthogonal.

| ID | Title | Layer | Status | Readiness |
|----|-------|-------|--------|-----------|
| SPEC-001 | Fusion-core slice: schema + provenance/calibration enforcement + variant_effect ingest & read view | `core/` | FUNCTIONAL | AVAILABLE |
| SPEC-002 | variant_effect producer: multi-tool consensus VUS reclassification with per-population calibration flags | `producers/variant_effect/` | FUNCTIONAL | AVAILABLE |
| SPEC-003 | Ingestion adapters from existing pipeline outputs (sarek MAFs, DESeq2 tables, IntOGen, MSISensor2, ADMIXTURE/RFMix, drug-screen readouts) | `core/ingest/` | SPECIFIED | AVAILABLE (Phase 1 is "Now" per build plan §6) |
| SPEC-004 | Reference reconciliation: key variants by (locus, ref-context); reconcile GRCh38 vs. pangenome callsets; flag pangenome-only-in-African-ancestry candidates | `pipeline/` + `core/` | SPECIFIED | AVAILABLE (Phase 1 is "Now" per build plan §6) |
| SPEC-005 | Wire real score providers (AlphaMissense + EVE pre-computed scores; retain PolyPhen/SIFT) behind the existing provider interface | `producers/variant_effect/` | SPECIFIED | AVAILABLE (Phase 2 "quick win" per build plan §6) |
| SPEC-006 | DeepSomatic added at the calling step, run in parallel with Mutect2; callset comparison to quantify reference/caller bias | `pipeline/calling/` | SPECIFIED | AVAILABLE (Phase 2 per build plan §6) |
| SPEC-007 | Target nomination: elastic-net + random-forest ensemble; DGIdb (druggability), MatrixEQTL (eQTL), Cox (survival) as edges on target nodes | `producers/target_nomination/` | SPECIFIED | UNKNOWN (build plan §6: "once the substrate is FUNCTIONAL" — substrate = Phase 1, whose SPEC-003/004 are still SPECIFIED; whether the precondition is met is ambiguous) |
| SPEC-008 | GNN over the PPI graph (STRING/BioGRID tagged with study mutation + expression data) — NOVEL, strongest controls (G6) | `producers/gnn/` | SPECIFIED | UNKNOWN (same §6 precondition as SPEC-007) |
| SPEC-009 | Query layer: grounded text-to-SQL with schema validation + literature retrieval; interface views (cohort explorer, evidence-chain viewer, target dashboard) | `query/` + `interface/` | SPECIFIED | UNKNOWN (same §6 precondition as SPEC-007) |
| SPEC-010 | Drug-response pre-screen (GDSC/CCLE/DepMap-trained) as triage that only adds, never subtracts | `producers/` (Phase 5) | SPECIFIED | GATED — organoid specimens / drug-screen data do not exist yet (build plan §6: "Phase 5 cannot start until organoid specimens/drug-screen data exist") |
| SPEC-011 | Organoid imaging: CellPose segmentation + CNN morphological features | `producers/imaging/` | SPECIFIED | GATED — same wet-lab data gate (build plan §6) |
| SPEC-012 | Causal layer: Double ML / causal forests, validated against CRISPR knock-in/reversion isogenics — NOVEL, strongest controls (G6) | `producers/causal/` | SPECIFIED | GATED — same wet-lab data gate (build plan §6) |
| SPEC-013 | Custom multi-modal variant predictor (decision D5: commit only if Phase 2 leaves meaningful residual VUS) — NOVEL, strongest controls (G6) | `producers/multimodal_predictor/` | SPECIFIED | GATED — decision D5 (OPEN, after Phase 2 data) + wet-lab data (build plan §6) |
| SPEC-014 | Agent-control CI enforcement: test gates on push/PR + mechanical SPEC-id check on every PR | repo tooling (`.github/`) | FUNCTIONAL | AVAILABLE |
| SPEC-015 | Query layer: deterministic structured read API over core read views (no NL) — filters, per-population VUS summary, query/provenance echo, result-level calibration caveat, named refusals for undefined criteria | `query/` | FUNCTIONAL | AVAILABLE |
| SPEC-016 | Repo hygiene: disjoint fixture ID namespaces across fixture directories + run/documentation honesty (docs claim only what was executed) | repo tooling (`fixtures/`, docs) | FUNCTIONAL | AVAILABLE |
| SPEC-017 | Status truthfulness: docs never assert undecided decisions; Readiness axis; human-owned data inventory; generated STATUS + CI drift gate | repo tooling (`docs/`, `tools/status/`) | FUNCTIONAL | AVAILABLE |
| SPEC-018 | Local dev dashboard: static status.json renderer (architecture + SPEC/phase views, blockers) + read-only localhost shim over the query API | dev tooling (`tools/status-ui/`) | FUNCTIONAL | AVAILABLE |
| SPEC-019 | Collaborator-map correctness: STATUS §6 producer slots derive from the single source (ARCHITECTURE.md §5 via producer_slots[]) and carry their Readiness — no hand-maintained lists | repo tooling (`tools/status/`) | FUNCTIONAL | AVAILABLE |
| SPEC-020 | drivers producer: IntOGen driver identification on the reclassified variant table — i.e. RUNNING the IntOGen pipeline (dNdScv, cBaSE, OncodriveCLUSTL, smRegions, HotMAPS, OncodriveFML, MutPanning) over this project's own cohort mutations | `producers/drivers/` | SPECIFIED | GATED — requires cohort mutation data, which does not exist (docs/DATA-INVENTORY.md: 7 of 8 study datasets UNKNOWN in every field); and IntOGen-plus is a Nextflow/container pipeline, i.e. `pipeline/` work, not a Python producer. Readiness corrected from AVAILABLE — decision D-011 |
| SPEC-021 | expression producer: DESeq2 / GSEA / DoRothEA transcriptomic path (R/Bioconductor). KNOWN PREREQUISITE GAP: the repo has no R tooling, no renv.lock, and Python-only CI — flagged, not solved | `producers/expression/` | SPECIFIED | UNKNOWN (same build plan §6 "once the substrate is FUNCTIONAL" precondition as SPEC-007/008, plus the R-tooling gap) |
| SPEC-022 | Close loose ends: register orphan producer slots (I6) + finish the D4 demotion sweep in core/db.py and core/README.md | repo tooling (`SPEC.md`, `core/` docs) | FUNCTIONAL | AVAILABLE |
| SPEC-023 | Drift-gate determinism: STATUS artifacts byte-identical across platforms (LF-pinned via .gitattributes) so local git-status noise cannot mask real drift | repo tooling (`.gitattributes`, `tools/status/`) | FUNCTIONAL | AVAILABLE |
| SPEC-024 | Dashboard information hierarchy: Section 1 dominates, boilerplate deduplicated, file:line evidence in not_built, reference sections collapsed, print stylesheet | dev tooling (`tools/status-ui/`, `tools/status/`) | FUNCTIONAL | AVAILABLE |
| SPEC-025 | Core data integrity: per-population variant identity (population is a property of the observation, D-004) + idempotent ingest via schema-enforced natural key (D-005) | `core/` | FUNCTIONAL | AVAILABLE |
| SPEC-028 | drivers producer (reference signal): POSITIONAL driver evidence from IntOGen's published compendium — join by gene, intersect the variant's residue with the published significant domains / 2D clusters / 3D clusters, emit evidence with cohort provenance. A distinct capability from SPEC-020, which RUNS the pipeline; this one LOOKS UP results computed on other cohorts. Reports evidence, never a driver call on a variant | `producers/drivers/` + `core/` | FUNCTIONAL | AVAILABLE |
| SPEC-029 | Multi-producer core: a producer-neutral `producer_result` table + `v_producer_result` / `v_variant` read views, so a second producer has somewhere to write and something producer-neutral to read | `core/` | FUNCTIONAL | AVAILABLE |
| SPEC-027 | Identifier-mapping seam: `variant_id` → external identifiers (UniProt accession, transcript, locus) as its own contract, so a producer LOOKS UP identifiers and never derives them; unblocks real score providers without waiting on SPEC-004 | `contracts/` + `producers/variant_effect/` | FUNCTIONAL | AVAILABLE |

## 3 · What runs today

Test suites (standard-library only, direct execution — the supported path):

- `python tests/test_alphamissense_provider.py` — 13 tests
- `python tests/test_consensus_two_providers.py` — 5 tests
- `python tests/test_core_ingest.py` — 4 tests
- `python tests/test_core_integrity.py` — 2 tests
- `python tests/test_drivers_producer.py` — 16 tests
- `python tests/test_eve_provider.py` — 12 tests
- `python tests/test_query_read_api.py` — 16 tests
- `python tests/test_status_ui_shim.py` — 5 tests
- `python tests/test_variant_effect.py` — 4 tests

CI checks (from `.github/workflows/tests.yml`): `spec-id`, `status-drift`, `test (py 3.14)`, `test (py 3.8)`. Suites are standard-library only and run by direct execution (the supported path; pytest compatibility UNVERIFIED — SPEC-016). This file does not run them: CI is the source of truth for pass/fail.

## 4 · What is NOT built

- **No real data has been processed.** No data/ directory exists; only fixtures/variant_effect/ and fixtures/query/ have ever run.
- **Empty layers (README only):** `pipeline/`, `interface/`.
- **Producers present:** `drivers/`, `variant_effect/` — every other producer slot is unbuilt.
- **Real score providers — 2 still unwired** (`raise NotImplementedError`): `PolyPhenProvider (producers/variant_effect/providers.py:151)`, `SIFTProvider (producers/variant_effect/providers.py:158)`. AlphaMissense IS wired against its real published scores (SPEC-005 partial, SPEC-027, decision D-006) — but that data is CC BY-NC-SA 4.0 and is NOT committed; it is fetched into a gitignored local cache, so CI exercises the provider's logic without the data (docs/alphamissense-data.md). SPEC-005 stays SPECIFIED until all four providers are wired.
- **All thresholds are PLACEHOLDER:** `config/calibration.json:2 ("status": "PLACEHOLDER")`, `config/variant_effect.json:2 ("status": "PLACEHOLDER")`. Strict mode hard-fails on them by design; every producer result is stamped `calibration_pending` — correctly, but no result is yet a clean call.
- **No natural-language query.** SPEC-009 is SPECIFIED (SPEC.md registry); the query layer reads one view (query/read_api.py: _VIEW = v_variant_effect); the query layer reads exactly one view (`v_variant_effect`).
- **No production database.** Dev/CI is embedded SQLite (core/db.py); production substrate pending D4 (docs/DECISIONS.md D4) — Postgres proposed, not decided (core/db.py:3-4). No lockfile, no lint, no typecheck configured (AGENTS.md §3).

## 5 · What unblocks the next step

Open decisions (docs/DECISIONS.md, transcribed — owners as stated there; D1–D6 await the parties named in docs/build-plan.md §1/§5):

- **D-002** — contracts/ layout: flat contract modules vs. subdirectories only: PROPOSED — pending approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-003** — Supported Python floor: keep 3.8 or raise to the dev version: PROPOSED — pending owner approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-004** — Where does population live in the core model?: PROPOSED — pending owner approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-005** — What does re-ingesting mean?: PROPOSED — pending owner approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-006** — How does a variant reach an AlphaMissense score? (SPEC-005 blocker): PROPOSED — pending owner approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-007** — The repository has no LICENSE file: PROPOSED — pending owner approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-008** — Pathogenicity prediction vs. somatic driver identification (SPEC-005 / Phase 2): PROPOSED — pending domain-owner decision — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-009** — EVE does not cover FBXW7 or RNF43 (SPEC-005 coverage gap): PROPOSED — pending domain-owner decision — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-010** — The residual VUS fraction is disagreement-limited, not coverage-limited: PROPOSED — pending domain-owner decision — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-011** — SPEC-020's Readiness was wrong: it is GATED, not AVAILABLE: PROPOSED — pending owner approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-012** — Where does a second producer's result go? (core schema shape): PROPOSED — pending owner approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D-013** — IntOGen is CC0, and we are choosing not to commit it anyway: PROPOSED — pending owner approval — owner: project owner (status: pending approval — docs/DECISIONS.md)
- **D1** — Ownership / IP of the substrate: OPEN — owner: project owner + parties named in docs/build-plan.md §1/§5 (docs/DECISIONS.md)
- **D2** — Compute & data residency: OPEN — owner: project owner + parties named in docs/build-plan.md §1/§5 (docs/DECISIONS.md)
- **D3** — Data governance: OPEN — owner: project owner + parties named in docs/build-plan.md §1/§5 (docs/DECISIONS.md)
- **D4** — Substrate DB: build vs. buy: OPEN — owner: project owner + parties named in docs/build-plan.md §1/§5 (docs/DECISIONS.md)
- **D5** — Custom multi-modal predictor: commit or gate: OPEN — owner: project owner + parties named in docs/build-plan.md §1/§5 (docs/DECISIONS.md)
- **D6** — Reproducibility contract: OPEN — owner: project owner + parties named in docs/build-plan.md §1/§5 (docs/DECISIONS.md)

Missing domain definitions (DEFINITIONS.md §4, marked [TO BE DEFINED]). The query layer refuses these by name rather than inventing values:

- Per-population calibration targets — owner: domain experts — the professor and collaborators (DEFINITIONS.md header: agent implements, never authors)
- What makes a variant "ancestry-enriched" (effect size, frequency-delta, significance, per-population) — owner: domain experts — the professor and collaborators (DEFINITIONS.md header: agent implements, never authors)
- What makes a target "actionable" / "druggable" (DGIdb evidence tier, druggability score cutoff) — owner: domain experts — the professor and collaborators (DEFINITIONS.md header: agent implements, never authors)
- Calibration adequacy — when a European-trained tool is "in-" vs "out-of-calibration" for a population — owner: domain experts — the professor and collaborators (DEFINITIONS.md header: agent implements, never authors)
- Drug-response endpoint for differential sensitivity (IC50 fold-change, Emax delta, significance) — owner: domain experts — the professor and collaborators (DEFINITIONS.md header: agent implements, never authors)
- Disconfirmation criteria — what counts as "ancestry effect smaller than the pilot suggested" — owner: domain experts — the professor and collaborators (DEFINITIONS.md header: agent implements, never authors)

**Data inventory (F3):** `docs/DATA-INVENTORY.md` (human-owned) tracks 8 study datasets + 6 public reference resources; 8 rows are UNKNOWN in every field. Custody, location, and access are undetermined for everything the system needs — a human owner must fill it before any real-data claim can be made.

## 6 · Where a collaborator plugs in

Producer isolation (ARCHITECTURE.md §4.2) makes the producer slots independent: each producer is a plugin that reads a core view and writes a provenance-tagged result via the ingest contract, and **never imports another producer, the query layer, or the interface**.

Producer slots — derived from the ARCHITECTURE.md §5 map (the single source of truth; `producer_slots[]` in status.json parses the same map, so this list cannot diverge from it). Each slot carries its SPEC Readiness, so GATED slots are not presented as available work:

- `variant_effect/` — **BUILT** (SPEC-002 FUNCTIONAL)
- `drivers/` — PLANNED, SPEC-020 — Readiness: **GATED — requires cohort mutation data, which does not exist (docs/DATA-INVENTORY.md: 7 of 8 study datasets UNKNOWN in every field); and IntOGen-plus is a Nextflow/container pipeline, i.e. `pipeline/` work, not a Python producer. Readiness corrected from AVAILABLE — decision D-011**
- `expression/` — PLANNED, SPEC-021 — Readiness: **UNKNOWN (same build plan §6 "once the substrate is FUNCTIONAL" precondition as SPEC-007/008, plus the R-tooling gap)**
- `target_nomination/` — PLANNED, SPEC-007 — Readiness: **UNKNOWN (build plan §6: "once the substrate is FUNCTIONAL" — substrate = Phase 1, whose SPEC-003/004 are still SPECIFIED; whether the precondition is met is ambiguous)**
- `gnn/` — PLANNED, SPEC-008 — Readiness: **UNKNOWN (same §6 precondition as SPEC-007)**
- `causal/` — PLANNED, SPEC-012 — Readiness: **GATED — same wet-lab data gate (build plan §6)**
- `imaging/` — PLANNED, SPEC-011 — Readiness: **GATED — same wet-lab data gate (build plan §6)**
- `multimodal_predictor/` — PLANNED, SPEC-013 — Readiness: **GATED — decision D5 (OPEN, after Phase 2 data) + wet-lab data (build plan §6)**

Also parallel-safe: `pipeline/`, `core/ingest/` adapters (SPEC-003), and `interface/` (downstream of `query/`). Not parallel-safe without review: `contracts/`, the core schema, and DEFINITIONS.md (expert-owned).
