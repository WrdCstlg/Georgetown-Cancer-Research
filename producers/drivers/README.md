# producers/drivers — positional driver evidence (SPEC-028)

An **isolated plugin** (ARCHITECTURE.md §4.2). One analytical job: for each variant in a core
read view, intersect its residue with what IntOGen published as significant, within a stated
cohort scope, and emit provenance-tagged evidence via the ingest contract.

## What this reports, and what it refuses to report

It reports **evidence**. It does **not** report a driver *call* on a variant, and there is
deliberately no `is_driver` field anywhere in `contracts/driver_evidence.py`.

The reason is the error this producer exists to avoid:

> **A gene being a driver does not make every variant in it a driver.**

That is measurable here, not merely a caution. On the golden fixture, `gene_is_driver_in_scope`
is **true for all 20 variants** — every one sits in a colorectal driver gene. A gene-level
signal would be constant and worth nothing. The information is entirely in the positional layer:

| Outcome | n |
|---|---:|
| Residue inside a significant domain / 2D cluster / 3D cluster | **10** |
| Gene is a driver, residue in **no** significant cluster | **5** |
| Not a missense change — no residue to intersect | 5 |

The three "nothing found" states are kept distinct on purpose, because they mean different
things and none of them means *not a driver*: `gene_not_a_driver_in_scope`,
`no_positional_evidence`, `not_missense`.

## Why every result is `calibration_pending` — reasoned, not copied

The two variant-effect providers stamp `calibration_pending` because they are European-trained
predictors. This producer is not a predictor at all — it is an evidence lookup — so the reason
has to be argued rather than inherited. It is:

**IntOGen's clusters are significant *relative to the mutation spectrum of the cohorts they were
computed on*, and those cohorts (CPTAC, Hartwig, TCGA) are overwhelmingly European-ancestry.**

The consequence is asymmetric, and it is sharper than the usual calibration caveat:

- **Presence** of positional evidence is comparatively transferable. If a residue recurs
  significantly in a European-ancestry colorectal cohort, that is a fact about the protein and
  the tumour type that plausibly carries across populations.
- **Absence** is *uninformative rather than negative* for an African-ancestry variant. A residue
  can fail to reach significance because the cohort had no power to detect recurrence at that
  position **in that population** — not because the residue is unimportant. Recurrence-based
  significance is a statement about who was sequenced.

This producer cannot distinguish "not recurrent" from "not recurrent *in these cohorts*". Until
a domain owner defines per-population calibration adequacy (DEFINITIONS.md §4, still
[TO BE DEFINED]), the honest stamp is `calibration_pending` on **both** presence and absence.

It also means a downstream consumer must not read `no_positional_evidence` as evidence *against*
a variant. That would convert a sampling artifact into a negative finding, which is precisely
the bias-laundering failure guardrails **R1** and **S1** exist to prevent — and here it would
run in the direction that most disadvantages the populations this study is about.

Whether calibration even *applies* to an evidence lookup rather than a prediction is itself a
domain question, raised as questionnaire **A12**.

## Cohort scope is load-bearing

Default scope is **colorectal (COAD/READ)**, not pan-cancer, and it is recorded in every
result's provenance rather than assumed. The scope changes the answer:

| | PIK3CA a driver? | Residue **1047** in a significant cluster? |
|---|---|---|
| COAD / READ | yes (Act, 2 cohorts) | **no — 0 of 2 rows** |
| Pan-cancer | yes (109 cohorts) | yes — 35 of 109 rows |

Colorectal PIK3CA clusters are `2D = 542:546`, `3D = {542,545,546}` — the helical-domain hotspot.
Residue 1047 is not among them. Which scope this study should use is questionnaire **A13**.

## Isolation

Imports: `contracts/` and `core.ingest` only. It imports **no other producer**, not `query/`,
not `interface/`. It reads **`v_variant`** — the producer-neutral view added by SPEC-029 — not
`v_variant_effect`, because reading another producer's output view would be composing through a
producer instead of through the core.

Its result is **not** routed into the variant_effect consensus. `min_agree` is untouched. Driver
evidence and pathogenicity are different axes (decision D-008); merging them would be the
conflation this whole slice exists to avoid.

## Data

IntOGen's compendium is **CC0 1.0** — public domain, so committing a slice *would* be permitted.
The fetch-to-gitignored-cache pattern is used anyway, deliberately, for consistency with the two
licence-encumbered providers (decision **D-013**).

```powershell
python tools\intogen\fetch_compendium.py     # ~965 KB, stdlib only, no new dependency
python tests\test_drivers_producer.py
```

Without the cache the suite **SKIPs and reports `INCOMPLETE COVERAGE`** rather than passing.
