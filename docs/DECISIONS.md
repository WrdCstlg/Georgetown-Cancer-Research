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

## D-006 — How does a variant reach an AlphaMissense score? (SPEC-005 blocker)
Status: **PROPOSED — pending owner approval.**

Fork: `VariantInput` (contracts/variant_effect.py:22-29) carries `gene` + `protein_change`.
AlphaMissense's published files are keyed by neither. Wiring the provider (SPEC-005) cannot
proceed until we decide where the lookup key comes from.

### What the published files actually key on (verified against the real files, not from memory)

Zenodo record 10.5281/zenodo.8208688, headers read by HTTP range request + partial gunzip:

| File | Size | Key columns (verbatim header) |
|------|------|-------------------------------|
| `AlphaMissense_hg38.tsv.gz` | 642,961,469 B | `#CHROM POS REF ALT genome uniprot_id transcript_id protein_variant am_pathogenicity am_class` |
| `AlphaMissense_aa_substitutions.tsv.gz` | 1,207,278,510 B | `uniprot_id protein_variant am_pathogenicity am_class` |
| `AlphaMissense_isoforms_aa_substitutions.tsv.gz` | 2,461,351,945 B | `transcript_id protein_variant am_pathogenicity am_class` |
| `AlphaMissense_gene_hg38.tsv.gz` | 253,636 B | `transcript_id mean_am_pathogenicity` (gene-level mean only — no per-variant score) |

So there are exactly three usable per-variant keys: `(CHROM, POS, REF, ALT)`,
`(uniprot_id, protein_variant)`, or `(transcript_id, protein_variant)`. The repo holds none
of them. `gene` is an HGNC symbol; AlphaMissense never keys on gene symbol.

Three further facts established from the real data, each of which changes the implementation:

1. **`protein_variant` is bare, not HGVS.** The files use `G12D`; the repo uses `p.G12D`
   (fixtures/variant_effect/variants_input.csv). Mechanical, but it is a format contract.
2. **The two files disagree on the `am_class` vocabulary.** `AlphaMissense_hg38.tsv.gz` emits
   `likely_benign` / `ambiguous` / `likely_pathogenic`. `AlphaMissense_aa_substitutions.tsv.gz`
   emits `benign` / `ambiguous` / `pathogenic` — verified verbatim rows
   (`A0A024R1R8 M1D 0.8267 pathogenic`, `A0A024R1R8 M1F 0.2753 benign`). The bundled README
   documents only the `likely_*` form and its own sample block for that file is wrong. The
   numeric thresholds are identical in both; only the labels differ. A provider that switches
   files must not assume one vocabulary.
3. **AlphaMissense covers single amino-acid missense substitutions ONLY.** Of the 20 variants
   in the golden fixture: 12 are missense on grch38 (directly lookupable given a key), 3 are
   missense on `pangenome` (no AlphaMissense coordinates exist — see below), and 5 are
   nonsense or frameshift (`v01 p.R1450*`, `v06 p.E1309fs`, `v09 p.G659fs`, `v13 p.T1556fs`,
   `v18 p.Q1367*`) and are outside the tool's domain entirely. Those 5 must yield "no
   coverage", never a call.

### Is this a contract deficiency or a missing upstream step?

Mostly the latter, and the repo already says where the key belongs:

- `pipeline/annotation/` (Funcotator) is PLANNED (ARCHITECTURE.md:148). Annotation is the step
  that emits genomic coordinates, transcript, and protein consequence. Producing that is the
  pipeline's concern (ARCHITECTURE.md:71, layer 1) — a producer that derived coordinates from a
  gene symbol would be doing annotation inside layer 3, crossing AGENTS.md §1.1.
- **SPEC-004** is literally this: "key variants by (locus, ref-context); reconcile GRCh38 vs.
  pangenome callsets". It is SPECIFIED / AVAILABLE.
- **D-004** already reasons that `reference` is "part of variant identity (SPEC-004)".
- `reference` is `grch38 | pangenome` (contracts/variant_effect.py:27). AlphaMissense publishes
  hg19 and hg38 only. **Pangenome-called variants have no AlphaMissense coordinates at all**
  until SPEC-004's reconciliation exists. This is not a gap the provider can close.

Demonstrated concretely: retrieving the real KRAS G12D row required supplying
`chr12:25245350 C>T` from outside the system. Nothing in the repo can produce that string.

### Options

  (a) **Add `chrom/pos/ref_allele/alt_allele` to `VariantInput`.** Matches the hg38 file's
      primary key exactly; no mapping layer, no ambiguity. But it is a contract change with
      blast radius into contracts/, producers/, fixtures, and tests — and *nothing currently
      produces those values* (pipeline/ is empty), so the fields would be fixture-only:
      a contract widened ahead of any real producer. Still leaves pangenome unsolved.

  (b) **Add `uniprot_id` to `VariantInput`; key `(uniprot_id, protein_variant)` against
      `AlphaMissense_aa_substitutions.tsv.gz`.** Smaller contract delta (one field), and that
      file carries **no genomic coordinates**, so it is reference-build independent — it
      sidesteps the grch38-vs-pangenome problem rather than blocking on SPEC-004. Cost: needs
      an HGNC→UniProt canonical mapping (UniProt release 2021_02, per the bundled README),
      which is itself a versioned identifier-mapping concern, and still puts an identifier
      field on the analysis contract.

  (c) **Leave `VariantInput` unchanged; introduce an explicit identifier-mapping seam.**
      A new contract (`contracts/identifiers.py`) maps `variant_id -> {uniprot_id,
      transcript_id, chrom, pos, ref, alt}`. `VariantInput` keeps describing the *analysis*
      view of a variant; identifiers are a separate concern with their own seam. The mapping
      is populated by pipeline annotation / SPEC-004 when those exist, and by a small committed
      fixture until then. The provider consumes the seam, never derives identifiers itself.
      Cost: one new contract module and its own spec item.

  (d) **Declare SPEC-005 BLOCKED on SPEC-004 and build nothing.** The most literal reading of
      the gates. But SPEC-005 is registered AVAILABLE, and the published scores are real and
      obtainable today, so this forfeits a genuine win over a gap that is real but bounded.

### Recommendation: **(c), consuming the `(uniprot_id, protein_variant)` key of option (b).**

Reasons, in order:
1. It keeps annotation out of the producer. The provider looks a key *up*; it never derives
   one. No AGENTS.md §1.1 boundary is crossed.
2. `VariantInput` is untouched, so contracts/, core/, and query/ take zero blast radius — the
   analysis contract does not accumulate identifier plumbing.
3. The aa-substitutions key is build-independent, so SPEC-005 does not have to wait on
   SPEC-004, and no one has to decide the pangenome-coordinate question to ship this.
4. When `pipeline/annotation/` and SPEC-004 land, they become the producer of that mapping.
   The seam is already the right shape; the provider does not change.
5. Honest about coverage: the 5 non-missense fixture variants return "no coverage" (`None`),
   which `reclassify()` already handles (producers/variant_effect/reclassify.py:65) and which
   the consensus engine already treats correctly. No engine change required.

Deliberately NOT decided here (they are not mine to decide):
- **Licence.** All AlphaMissense predictions are **CC BY-NC-SA 4.0 — non-commercial only,
  share-alike** (verified: Zenodo `license.id = cc-by-nc-sa-4.0`; the file headers themselves
  carry "Licensed under CC BY-NC-SA 4.0 license"). Committing even a small score slice
  redistributes CC-BY-NC-SA material from a repo that currently has no LICENSE file. NC
  interacts with **D1** (if the substrate becomes reusable/commercial infrastructure) and the
  whole question sits inside **D3** (data governance / DB licensing), which is OPEN — the same
  class of constraint docs/DATA-INVENTORY.md already records for COSMIC.
- **Residency.** Acquiring and storing the score data touches **D2** (compute & data
  residency), OPEN. Note the mitigation available: the file is bgzip-compressed and
  coordinate-sorted, so targeted retrieval by HTTP range + binary search fetches a few MB
  rather than 643 MB (demonstrated: 30 range requests). That shrinks but does not remove the
  D2 question.
- **Score-to-call cutoffs.** AlphaMissense's published thresholds (`< 0.34` benign,
  `> 0.564` pathogenic, ambiguous otherwise) are the tool's own defaults, to be transcribed as
  AWAITING SIGN-OFF — never authored or adjusted here (I3).

Whether option (c) needs its own SPEC item (identifier mapping is arguably its own concern
under I6, not part of SPEC-005) is part of what is being approved.

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
