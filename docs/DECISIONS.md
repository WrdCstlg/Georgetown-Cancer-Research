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
   emits `benign` / `ambiguous` / `pathogenic` — verified by reading real rows of both files
   (labels quoted here; the score values themselves are not reproduced). The bundled README
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

## D-007 — The repository has no LICENSE file
Status: **PROPOSED — pending owner approval.**

Fork (surfaced while wiring SPEC-005): `git ls-files` shows **no LICENSE, COPYING, or
licence header anywhere in the repo**. It is a public repository
(github.com/WrdCstlg/Georgetown-Cancer-Research) with no stated terms.

This is a problem **independent of AlphaMissense** and would exist if SPEC-005 were never
built. Stating it plainly:

- Under the Berne Convention and US copyright law, "no licence" is not "public domain" — it
  is **all rights reserved**. Nobody, including collaborators and the institution, has an
  express right to use, copy, modify, or redistribute this code.
- That directly undercuts R6 ("platform outlives its operator") and the stated goal of the
  team running it without us: a handover has no legal basis.
- It collides with **D1** (ownership / IP of the substrate, OPEN), because the licence is the
  instrument that *expresses* whichever ownership answer D1 lands on. D1 should be decided
  first, or at least jointly — the licence is downstream of it.
- Federal funding may attach its own obligations (e.g. public-access or data-sharing terms
  under the award). Those are stated in the award, which is not in this repo.
- It interacts with **D3** (data governance / licensing): AlphaMissense predictions are
  **CC BY-NC-SA 4.0**. Share-alike attaches to *adapted* material, and NC restricts commercial
  use. A permissive code licence sitting next to NC-SA data needs the boundary between "our
  code" and "their data" to be explicit, or the NC/SA terms can be read to reach further than
  intended. (This build commits **no** AlphaMissense data, precisely to avoid pre-empting it.)

Options:
  (a) **Permissive (MIT / BSD-3 / Apache-2.0).** Maximises reuse and handover; Apache-2.0 adds
      an express patent grant, which matters for a genomics method that may be patentable.
      Compatible with D1(a) "owned infrastructure reused across projects".
  (b) **Copyleft (GPL-3.0 / AGPL-3.0).** Keeps derivatives open; aligns with a share-alike data
      ecosystem. But it constrains institutional or commercial downstream use, which may
      conflict with whatever D1 decides.
  (c) **Explicit proprietary / all-rights-reserved with a written collaborator grant.**
      Makes the current de-facto state deliberate instead of accidental, and hands the
      access question to a separate agreement.
  (d) **Dual: code licence + a separate data-terms file** stating that third-party data
      (AlphaMissense CC BY-NC-SA, COSMIC, ClinVar) keeps its own terms and is not covered by
      the code licence.

Recommendation: **(d) layered on top of whatever (a)–(c) D1 implies — and (d) regardless.**
Separating code terms from third-party data terms is correct under every outcome of D1 and
costs nothing to state now. The choice *between* (a), (b), and (c) is **not mine to make**:
it is an ownership and institutional question (D1), likely with grant terms and a technology-
transfer office attached. I am recording the gap and the options; the owner chooses.

No licence file is added by this change.

## D-008 — Pathogenicity prediction vs. somatic driver identification (SPEC-005 / Phase 2)
Status: **PROPOSED — pending domain-owner decision.** This is a DOMAIN-MODEL question; the
recommendation below is a recommendation only.

Fork: SPEC-005 wires AlphaMissense, which predicts **clinical pathogenicity**, into a pipeline
whose Phase-2 purpose is **somatic driver** reclassification. Those are different questions.
The concern was raised concretely by PIK3CA H1047R — a canonical activating hotspot —
landing in AlphaMissense's `ambiguous` band, below the published pathogenic cut-point.

### What the probe found (docs/probes/alphamissense-driver-coverage.md, run 2026-07-28)

The hypothesis "AlphaMissense systematically misses activating drivers" was tested against 178
recurrent somatic hotspots in the grant's own 15 CRC driver genes, grouped by IntOGen/OncoKB
mechanism of action. **It was NOT supported:**

- activating: 93.5% called pathogenic (median ~0.98); loss-of-function: 95.0% (median ~0.99);
- Mann-Whitney U p = 0.312, Fisher exact p = 0.748; colorectal-only subset p = 0.700 / 1.000;
- all five activating misses are **PIK3CA** — KRAS, NRAS, BRAF and CTNNB1 hotspots are called
  pathogenic without exception. The effect is gene-specific, not mechanism-specific.

Two caveats survive the null result:
1. **Recurrence weighting.** 8.9% of activating-hotspot tumor burden pan-cancer sits behind a
   non-pathogenic call vs 2.0% for LoF — but **96.1% of that is H1047R alone**, and in bowel
   tumors the gap narrows to 4.3% vs 2.8%.
2. **The probe tests recurrent hotspots only, and is not ancestry-stratified.** It says nothing
   about rare drivers or about R1/S1 ancestry-fairness. A null here is not a clean bill of health.

### Options

  (a) **Status quo.** AlphaMissense is one of four consensus tools; `min_agree: 2` already means
      no single call reclassifies anything. Cheapest, and defensible given the null result — but
      it leaves "pathogenicity ≠ driver" unaddressed as a stated modelling position.
  (b) **Pair AlphaMissense with a driver-oriented signal** — hotspot recurrence (cancerhotspots /
      COSMIC) or the IntOGen producer already registered as **SPEC-020** — so that a variant with
      strong somatic recurrence is not left VUS purely on pathogenicity scores. Directly addresses
      the H1047R case. Costs a new signal in the consensus, which is a domain decision about what
      "reclassified" means.
  (c) **Add a driver-specific predictor** (CHASMplus, boostDM, or IntOGen per-variant scores) as a
      distinct producer, keeping pathogenicity and driver-ness as separate reported axes rather
      than blending them into one call. Most faithful to the science; most work; needs its own
      SPEC item and its own calibration story.
  (d) **Restrict SPEC-005's claim.** Keep AlphaMissense but state explicitly, in DEFINITIONS.md
      and wherever results render, that the reclassification axis is *pathogenicity*, not
      *driver status*, and that Phase 2's VUS-reduction target is measured on that axis.

### Recommendation: **(d) now, and (b) when SPEC-020 lands — RECOMMENDATION ONLY**

(d) costs nothing, is true today, and is the honest framing regardless of what else is chosen —
it prevents a pathogenicity number being read as a driver claim, which is exactly the **S4**
failure mode (provenance making a subtly-wrong answer more credible). (b) is the natural pairing
because SPEC-020 (IntOGen driver identification) is **already registered and AVAILABLE**, so the
driver-oriented signal is coming anyway; the question is only whether it feeds reclassification
or stays a separate output.

**Not recommended without more evidence:** (c). The probe gives no basis for asserting a
driver-specific predictor would do better here, and G6 would require fixtures and execution
evidence this project cannot yet produce.

**Explicitly NOT done by this change:** Phase 2 was not re-scoped, the consensus rule was not
touched, `min_agree` was not changed, and no [TO BE DEFINED] value was filled. Raised for the
domain owner as questionnaire **A10**.

### Addendum (2026-07-28) — a second independent signal on the same variant

Wiring EVE (SPEC-005 part 2) gave PIK3CA H1047R a second, methodologically independent read.
It does **not** move toward pathogenic:

| Source | Call on PIK3CA H1047R |
|---|---|
| AlphaMissense (structure/population-constraint) | `uncertain` (ambiguous band) |
| EVE (evolutionary model) | **`benign`** |
| ClinVar record **EVE itself ships** alongside its prediction | `Pathogenic` |

So two independent predictors decline to call the most common activating hotspot in CRC
pathogenic, and EVE disagrees with the very ClinVar annotation it distributes. Under the
consensus rule this variant stays VUS — correctly, since nothing agrees.

This does **not** revive the class-level hypothesis the probe rejected: the probe tested 178
hotspots and found no activating-vs-LoF difference (p = 0.31/0.75), and that null stands. What
it does is strengthen the narrow, variant-level form of the concern in the options above,
because the miss is now reproduced across two models rather than being one tool's quirk.
Recorded as evidence; the options and recommendation are unchanged and still the owner's call.

## D-009 — EVE does not cover FBXW7 or RNF43 (SPEC-005 coverage gap)
Status: **PROPOSED — pending domain-owner decision.** Recommendation only; nothing implemented.

Fork: EVE publishes a curated set of **3,211 proteins**, not the proteome. Of the grant
strategy's 15 named CRC driver "mountains" (`docs/sources/...PF5.txt` line 332), EVE covers
**13**. It does **not** publish:

| Gene | Why it matters here |
|---|---|
| **RNF43** | The grant's OWN preliminary data reports RNF43 mutation frequency varying significantly by population (**p = 0.0047**), highest in the NHW cohort at **73.6%**, "a rate nearly double that seen in the other populations" (`...PF5.txt` lines 196–198, quoted verbatim). This is a **population-varying driver the study specifically cares about** — precisely the kind of gene an ancestry-aware analysis cannot afford to be blind in. *(Correction, 2026-07-28: an earlier revision of this record cited "~44% AA and ~38% Ghanaian" for RNF43. Those figures are not in the source — 38.1% Ghanaian is **APC's** rate. The grant gives only the NHW figure and the "nearly double" comparison for RNF43.)* |
| **FBXW7** | A confirmed CRC driver in the grant's own mountain list; IntOGen COAD calls it LoF. Less central to the ancestry story than RNF43, but a real gap. |

Consequence, measured rather than asserted: in the golden fixture, EVE returns no coverage for
6 of 35 fixture entries on this basis (4 FBXW7, 2 RNF43). For `v10` (FBXW7 R465C) AlphaMissense
*does* produce a call, so the variant has exactly one caller and **cannot reach `min_agree: 2`**
however good that single call is. Coverage asymmetry between tools silently becomes
un-reclassifiable variants.

Options:
  (a) **Accept 13/15 and record the gap** (what this change does). Honest, cheap, and the
      remaining coverage is good. But RNF43 stays un-second-sourced indefinitely.
  (b) **Substitute a third signal for the uncovered genes only** — e.g. PolyPhen or SIFT
      (already in SPEC-005's scope, still unwired) restricted to FBXW7/RNF43. Restores
      two-caller consensus where EVE cannot reach, without changing the rule.
  (c) **A driver-oriented signal for the gap** — hotspot recurrence / COSMIC / the IntOGen
      producer (SPEC-020). Overlaps decision D-008's option (b).
  (d) **Request EVE coverage.** evemodel.org states: *"We are adding predictions for new genes
      regularly — can't find the gene/protein you are looking for? Contact us and we can run it
      for you!"* Zero engineering cost, unknown latency, outside our control.

Recommendation: **(a) now, and (d) in parallel because it costs nothing** — ask the EVE authors
for RNF43 and FBXW7. If that does not land, **(b)** is the natural fallback since PolyPhen and
SIFT are already in SPEC-005's scope and wiring them is planned work, not new scope.

**Not recommended:** widening the consensus rule or lowering `min_agree` to paper over the gap.
That would trade a coverage problem for an evidence problem, and `min_agree` is a domain
decision (questionnaire A8), not an engineering convenience.

Nothing here is implemented. No substitute signal was wired.

## D-010 — The residual VUS fraction is disagreement-limited, not coverage-limited
Status: **PROPOSED — pending domain-owner decision.** This records a measured property of the
consensus rule. It recommends **nothing** about `min_agree`; that is a domain decision and it is
already questionnaire **A8**.

Finding (measured, `tests/test_consensus_two_providers.py`, 2026-07-28): with AlphaMissense and
EVE both wired, the golden fixture moves from **20/20 VUS (100%) to 13/20 (65%)** — 7 variants
reclassified. Decomposing the 13 that remain:

| Reason a variant is still VUS | n |
|---|---:|
| **The two tools DISAGREE** | **7** |
| Neither tool covers it (nonsense/frameshift) | 5 |
| Only one tool covers it (FBXW7, D-009) | 1 |

So the single largest blocker is **tool disagreement**, not missing data. Concretely, every one
of those 7 is a canonical somatic hotspot where a structural model and an evolutionary model
diverge:

| Variant | AlphaMissense | EVE |
|---|---|---|
| KRAS G12D | pathogenic | uncertain |
| KRAS G13D | pathogenic | uncertain |
| KRAS A146T | pathogenic | uncertain |
| TP53 R175H | pathogenic | uncertain |
| TP53 R248Q | pathogenic | uncertain |
| PIK3CA E545K | pathogenic | uncertain |
| PIK3CA H1047R | uncertain | **benign** |

Why this is a finding and not a defect: the rule is doing exactly what it exists to do —
refusing to reclassify where independent evidence conflicts. Six of the seven are
AlphaMissense-pathogenic vs EVE-uncertain, i.e. one tool is confident and the other declines to
commit; that is a *different* situation from two tools actively contradicting each other, which
happens only for H1047R.

The consequence for planning is concrete and worth stating plainly: **adding a third and fourth
provider will not automatically improve the number in proportion.** With `min_agree: 2`, another
caller helps only where it breaks a tie; where EVE is systematically "Uncertain" on hotspots, a
third tool agreeing with AlphaMissense would resolve it, but a third tool that also declines
would not. Phase 2's VUS-reduction target should be read against that, not against an assumption
that more tools monotonically reduce VUS.

**No recommendation is made about `min_agree`, tie-breaking, weighting tools differently, or
treating "Uncertain" as abstention rather than a vote.** All of those are domain decisions. The
concrete disagreement list above has been added to questionnaire **A8** so the domain owner is
ruling on real cases rather than an abstraction.

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

**Third-party prediction data now in scope (added 2026-07-28 as encountered, not decided):**

| Resource | Stated terms | Open question |
|---|---|---|
| **AlphaMissense** | **CC BY-NC-SA 4.0** — non-commercial, share-alike. Verified from the Zenodo record and the header of every published `.tsv.gz`. | May any slice be redistributed? Does NC permit our use if D1 lands on reusable/commercial infrastructure? Does SA reach derived artifacts? (D-006, D-007) |
| **EVE** | **MIT, as asserted by evemodel.org** — but the `LICENSE.txt` the site serves is `Copyright (c) 2022 Joseph Min`, i.e. the **site's author**, not the Marks Lab / OATML who produced the predictions. An MIT text covering the site *software* is being pointed at as the licence for the prediction *data*. | Does that MIT grant actually govern the predictions? If it does, redistribution is permitted; if it does not, EVE's data has **no stated licence at all**, which is more restrictive than AlphaMissense, not less. |

Because EVE's licence provenance is unsettled in exactly this way, the repo applies the **same
no-commit discipline to both**: no AlphaMissense and no EVE score data is committed, both caches
are gitignored, and prose carries distributional statistics only. That is a conservative default
chosen so the decision stays open, **not** a determination that either licence forbids it.
Settling this is part of D3.

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
