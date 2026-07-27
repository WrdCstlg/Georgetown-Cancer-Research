# Decision records

## D-001 — Repo layout
Adopt the ARCHITECTURE.md §5 module map as canonical. src/ deleted (code lives in layers);
env/ -> config/; notebooks/ scratch-only; real/raw data NOT committed (referenced via config/ + DVC);
golden test data -> fixtures/. METHODS.md / DATA-DICTIONARY.md deprecated.

## D-002 — contracts/ layout: flat contract modules vs. subdirectories only
Status: **PROPOSED — pending approval.**
Fork: ARCHITECTURE.md §5 historically showed `contracts/` containing only subdirectories
(`core-schema/`, `io-contracts/`), but a flat contract module exists on disk:
`contracts/variant_effect.py` (imported as `contracts.variant_effect` by the producer and tests).
Options:
  (a) Permit flat contract modules directly under `contracts/` and document the map accordingly.
  (b) Relocate `contracts/variant_effect.py` into a subdirectory — touches the import seam and is
      out of scope for a docs-only change.
Recommendation: (a). No code movement; the seam stays stable and the map documents both forms.
Until approved, ARCHITECTURE.md §5 marks the flat form as PROPOSED (see D-002 reference there).

## D-003 — Supported Python floor: keep 3.8 or raise to the dev version
Status: **PROPOSED — pending owner approval.**
Fork: AGENTS.md §Environment documents a Python floor of 3.8, derived from a single walrus
operator in `producers/variant_effect/reclassify.py` — an accident of implementation, not a
deliberate support decision. Development actually runs on 3.14, and 3.8 is past end-of-life,
so a floor pin is fragile for reasons unrelated to this code.
Options:
  (a) Keep the 3.8 floor and test it in CI — the floor claim stays honest, but CI spends
      cycles validating a version nobody runs, on an EOL interpreter.
  (b) Raise the floor to the dev version (3.14) and drop the 3.8 claim — one supported
      version, matching reality; the "runs anywhere ≥3.8" property is forfeited as a claim.
Recommendation: (b). A documented support floor should be a decision, not an accident of one
operator; if broad-version compatibility is ever needed, that is its own stated requirement.
Until decided, CI tests BOTH versions (matrix in .github/workflows/tests.yml) so the docs are
honest under either outcome.

## D-004 — Where does population live in the core model?
Status: **PROPOSED — pending owner approval.**
Fork (audit F2): `variant.population_code` + lone `variant_id` PK + `INSERT OR REPLACE` means
the same variant seen in two populations keeps one row and silently loses the first association.
Options:
  (a) Composite PK `(variant_id, population_code)` on `variant` — keeps population on the entity,
      widens the key. Simple, but encodes that a variant *belongs to* a population, and every
      future per-population attribute re-raises the same modeling question.
  (b) Population is a property of the OBSERVATION, not the variant: a variant is a genomic fact;
      observing it in a cohort is not. `population_code` leaves `variant` entirely and lives only
      on `variant_effect_result` (which already carries it). The overwrite class of bug becomes
      structurally impossible instead of merely avoided.
Recommendation: **(b).** The project's premise is per-population fidelity; the model should make
the wrong state unrepresentable, not just handled. On `reference`: it currently sits on BOTH
tables. That is duplication, but of a different kind — `reference` is part of a variant's identity
(SPEC-004 keys variants by locus + ref-context; the same locus on GRCh38 vs the pangenome is
deliberately a different entity for the reconciliation work). So `reference` stays on `variant`
(identity) and also stays on the result as write-time provenance snapshot; the duplication is
acknowledged and intentional, unlike population's, which was incidental.

## D-005 — What does re-ingesting mean?
Status: **PROPOSED — pending owner approval.**
Fork (audit F3): `variant_effect_result` has no uniqueness over its natural key; re-running the
same ingest silently doubles every count downstream.
Options:
  (a) Upsert — one result per observation, natural key `(variant_id, population_code,
      producer, method)` — population is in the key because D-004 makes it part of the
      observation's identity (the first draft of this key omitted it and the F2 test
      immediately caught the collision: AA and GHA observations of one variant upserted
      over each other). Enforced by a UNIQUE constraint in the schema; re-running replaces.
      Simple; read surface stays "current state"; loses run history.
  (b) Run-scoped — results carry a run identity; re-running creates a new run; history kept;
      reads default to latest run. Provenance-aligned, but adds run resolution to every read
      and "latest by generated_at string" is fragile.
Recommendation: **(a), with history explicitly deferred to D6.** Provenance
(producer_version, method, generated_at) already records WHICH run produced the current row;
longitudinal run history is exactly what the OPEN reproducibility-contract decision (D6:
DVC/lakeFS + MLflow) exists to answer, at the data/model-registry layer where it belongs —
not by allowing duplicate facts in the substrate. The schema enforces the natural key the same
way it already refuses missing provenance. If D6 later lands run-scoped storage, the natural
key becomes part of the run identity instead.

## D1 — Ownership / IP of the substrate
Status: **OPEN.**
Question: who owns the fusion substrate?
Options (per docs/build-plan.md §1): (a) Senan/Qiwu-owned infrastructure reused across projects;
(b) grant deliverable owned by the institution.
Why it gates: determines whether the substrate is a reusable asset or billed hours; changes what
gets built and how it is licensed. Build plan: "Settle this before anything."
Decision: OPEN — awaiting the parties named in docs/build-plan.md §1/§5.

## D2 — Compute & data residency
Status: **OPEN.**
Question: where do compute and data live?
Options (per docs/build-plan.md §1): institutional HPC / lab cluster / cloud (GPU tier for the nets).
Why it gates: cross-site (Ghana/Ethiopia) specimens may carry data-use constraints; PHI vs.
de-identified location dictates architecture.
Decision: OPEN — awaiting Phase-0 settlement (see docs/build-plan.md §1).

## D3 — Data governance
Status: **OPEN.**
Question: IRB scope, de-identification, DUAs, DB licensing (ClinVar/COSMIC/CIViC/DGIdb).
Options (per docs/build-plan.md §1): as scoped by IRB/DUAs; note COSMIC and some resources are
license-gated for commercial use — relevant if D1 lands on "owned infra."
Decision: OPEN — awaiting Phase-0 settlement (see docs/build-plan.md §1).

## D4 — Substrate DB: build vs. buy
Status: **OPEN.**
Question: which database substrate?
Options (per docs/build-plan.md §1): self-hosted Postgres+pgvector / managed Postgres /
DuckDB (single-analyst). Build plan carries a recommendation but states "this is a real call."
Decision: OPEN — awaiting Phase-0 settlement (see docs/build-plan.md §1).

## D5 — Custom multi-modal predictor: commit or gate
Status: **OPEN.**
Question: build the custom predictor now, or gate it?
Options (per docs/build-plan.md §1): build now / gate on whether AlphaMissense+EVE already clears
the VUS bar. Build plan: decide AFTER Phase 2 data — the 4–6 month ML build is only worth it if the
cheap join leaves meaningful residual VUS.
Decision: OPEN — awaiting Phase-2 results (see docs/build-plan.md §1).

## D6 — Reproducibility contract
Status: **OPEN.**
Question: what is the reproducibility stack?
Options (per docs/build-plan.md §1): Nextflow provenance + DVC or lakeFS (data) + MLflow (models)
+ a provenance schema. Build plan: for an R01, lineage is what makes a reviewer/clinician trust the
chain — "Non-optional."
Decision: OPEN — awaiting Phase-0 settlement (see docs/build-plan.md §1).
