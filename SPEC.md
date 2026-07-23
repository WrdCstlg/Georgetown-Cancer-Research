# SPEC.md — spec-item registry (control I6)

> The referent for "traces to a spec item" (system prompt prime directive; AGENTS.md §2 I6, §4).
> Every change cites a SPEC- ID from this registry. **New work adds its spec item here BEFORE code.**
> Orphan code (no SPEC parent) and orphan specs (no aim/R01 objective parent) both fail review.
>
> Status ladder (docs/build-plan.md §3): **SPECIFIED** (reasoned, decision-recorded, unbuilt) →
> **FUNCTIONAL** (runs end-to-end, acceptance met). Acceptance criteria are executable — each maps
> to a check that runs, not narration (I2). Scope below is taken from `docs/build-plan.md`; nothing
> here invents scope beyond it.

| ID | Title | Owning layer | Aim / R01 objective | Status |
|----|-------|--------------|---------------------|--------|
| SPEC-001 | Fusion-core slice: schema + provenance/calibration enforcement + variant_effect ingest & read view | `core/` | Substrate precondition for all aims (build plan Phase 1) | FUNCTIONAL |
| SPEC-002 | variant_effect producer: multi-tool consensus VUS reclassification with per-population calibration flags | `producers/variant_effect/` | Aim 1 assist (build plan Phase 2 — first shippable win) | FUNCTIONAL |
| SPEC-003 | Ingestion adapters from existing pipeline outputs (sarek MAFs, DESeq2 tables, IntOGen, MSISensor2, ADMIXTURE/RFMix, drug-screen readouts) | `core/ingest/` | Substrate for all aims (Phase 1) | SPECIFIED |
| SPEC-004 | Reference reconciliation: key variants by (locus, ref-context); reconcile GRCh38 vs. pangenome callsets; flag pangenome-only-in-African-ancestry candidates | `pipeline/` + `core/` | Aim 1 (Phase 1; load-bearing against reference bias) | SPECIFIED |
| SPEC-005 | Wire real score providers (AlphaMissense + EVE pre-computed scores; retain PolyPhen/SIFT) behind the existing provider interface | `producers/variant_effect/` | Aim 1 (Phase 2) | SPECIFIED |
| SPEC-006 | DeepSomatic added at the calling step, run in parallel with Mutect2; callset comparison to quantify reference/caller bias | `pipeline/calling/` | Aim 1 (Phase 2) | SPECIFIED |
| SPEC-007 | Target nomination: elastic-net + random-forest ensemble; DGIdb (druggability), MatrixEQTL (eQTL), Cox (survival) as edges on target nodes | `producers/target_nomination/` | Aim 2a (Phase 3) | SPECIFIED |
| SPEC-008 | GNN over the PPI graph (STRING/BioGRID tagged with study mutation + expression data) — NOVEL, strongest controls (G6) | `producers/gnn/` | Aim 2a (Phase 3) | SPECIFIED |
| SPEC-009 | Query layer: grounded text-to-SQL with schema validation + literature retrieval; interface views (cohort explorer, evidence-chain viewer, target dashboard) | `query/` + `interface/` | The distillation deliverable (Phase 4) | SPECIFIED |
| SPEC-010 | Drug-response pre-screen (GDSC/CCLE/DepMap-trained) as triage that only adds, never subtracts | `producers/` (Phase 5) | Aim 2b (Phase 5 — gated on wet-lab data) | SPECIFIED |
| SPEC-011 | Organoid imaging: CellPose segmentation + CNN morphological features | `producers/imaging/` | Aim 2b (Phase 5 — gated on wet-lab data) | SPECIFIED |
| SPEC-012 | Causal layer: Double ML / causal forests, validated against CRISPR knock-in/reversion isogenics — NOVEL, strongest controls (G6) | `producers/causal/` | Aim 2b (Phase 5 — gated on wet-lab data) | SPECIFIED |
| SPEC-013 | Custom multi-modal variant predictor (decision D5: commit only if Phase 2 leaves meaningful residual VUS) — NOVEL, strongest controls (G6) | `producers/multimodal_predictor/` | Aim 2b (Phase 5 — gated on D5 + wet-lab data) | SPECIFIED |
| SPEC-014 | Agent-control CI enforcement: test gates on push/PR + mechanical SPEC-id check on every PR | repo tooling (`.github/`) | Cross-cutting — the control protocol itself (docs/risk-and-agent-control.md Part 3) | FUNCTIONAL |

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
