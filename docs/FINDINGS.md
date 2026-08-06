# Phase 2 — what the variant work has established

**For:** Dr. Laura, Qiwu · **From:** the computational team · **Date:** 5 August 2026

> **This is the canonical findings document.** It replaces `docs/probes/phase2-vus-findings.md`
> (same file, moved out of `probes/` and rewritten) and sits **above** the three probe records in
> [`docs/probes/`](probes/), which are retained as run artifacts only. Where this document and a
> probe record differ in wording, **this one is canonical**; where a probe record carries a
> per-variant table or a method detail not reproduced here, that table is the measured source and
> is cited inline. See §9.

Everything below is measured and reproducible. Every claim cites where in the repository it
comes from. Where a question is yours to answer rather than ours, it is marked and pointed at
its questionnaire item.

---

## 0 · The one-paragraph version

Three methodologically independent signals are now wired against their real published data: a
**structural** predictor (AlphaMissense), an **evolutionary** predictor (EVE), and a
**positional / driver** evidence lookup (IntOGen, colorectal cohorts). On our small test set the
first two took variants of unknown significance from **100% to 65%** — seven of twenty
reclassified, every one by both tools independently agreeing. Thirteen did not move, and *why*
is the useful part: for seven of them the two predictors **disagree**, not because data is
missing. Then the third signal was wired, and it produced the result this document exists to
report: **the six variants where the pathogenicity axis deadlocked are exactly the six that
carry positional driver evidence.** Not five, not four — the same six. That suggests the
deadlock may not be a threshold problem at all, but a question the pathogenicity axis cannot
answer. Four decisions now need your judgement (§8), and two of them must be answered together.

**Scope statement, stated here and repeated throughout because it bounds every number below:**
this ran on a **20-variant synthetic test fixture**. It is **not** the 150-tumor preliminary
cohort. **No real cohort data exists in this project's custody** — every dataset in
[`docs/DATA-INVENTORY.md`](DATA-INVENTORY.md) is still recorded UNKNOWN for custody, location,
and access. Nothing below is a result about patients.

---

## 1 · What was wired, and against what

| Signal | Evidence type | The question it answers | Source of record | Status |
|---|---|---|---|---|
| **AlphaMissense** (Google DeepMind) | Structural + population constraint | Is this variant clinically pathogenic? | Zenodo `10.5281/zenodo.8208688` | **Wired** |
| **EVE** (Marks Lab / OATML) | Evolutionary conservation across species | Is this variant evolutionarily intolerable? | evemodel.org JSON API | **Wired** |
| **IntOGen** (Lopez-Bigas lab) | Positional recurrence in sequenced tumours | Does this residue fall in a region significantly mutated in colorectal tumours? | `2024-06-18_IntOGen-Drivers` compendium | **Wired** |
| PolyPhen | — | — | — | Not wired |
| SIFT | — | — | — | Not wired |

The first two were chosen to be *methodologically independent*: AlphaMissense reasons largely
from protein structure and how constrained a position is across human populations; EVE reasons
from how a position has been conserved across evolution. When two such different lines of
evidence agree, that agreement means something. When they disagree, that is informative too
(§3).

The third is independent of both in a stronger sense — it is **not a predictor at all**. It does
not model the protein; it looks up whether the variant's residue falls inside a region IntOGen
found significantly mutated in real sequenced tumours. That makes it a different *kind* of
evidence, not a third opinion of the same kind, which is why §5 is worth your attention.

**None of the three sources' data is stored in this repository.** All are fetched into a
gitignored local cache; only distributional statistics appear in any committed document. The
reasons are per-source and are recorded in [`docs/alphamissense-data.md`](alphamissense-data.md)
(CC BY-NC-SA 4.0 — redistribution not permitted), [`docs/eve-data.md`](eve-data.md) (licence
provenance unsettled), and [`docs/intogen-data.md`](intogen-data.md) (CC0 — redistribution *is*
permitted, and we are declining anyway, for the reasons in decision D-013).

*Sources: [`producers/variant_effect/alphamissense.py`](../producers/variant_effect/alphamissense.py),
[`producers/variant_effect/eve.py`](../producers/variant_effect/eve.py),
[`producers/drivers/README.md`](../producers/drivers/README.md), [`SPEC.md`](../SPEC.md) —
SPEC-005 (partial), SPEC-027, SPEC-028, SPEC-029.*

---

## 2 · The VUS result, and what moved it

```
VUS before: 20/20 (100.0%)    VUS after: 13/20 (65.0%)    reclassified: 7
```

The seven reclassified as pathogenic: **SMAD4 R361H, CTNNB1 S45F, KRAS G12V, SMAD4 D351H,
TP53 Y220C, CTNNB1 T41A, BRAF V600E.** In every case both predictors independently called
pathogenic — none was reclassified on a single tool's say-so.

**Why one tool was not enough.** The consensus rule requires **two** concurring calls
(`min_agree: 2`). With AlphaMissense alone the reduction was **exactly zero** — not a failure but
arithmetic: one caller can never reach a two-vote threshold. This is asserted by a test rather
than assumed, so it cannot quietly stop being true
(`test_single_provider_still_reclassifies_nothing`).

### What this number is, and is not

- It is **a 20-variant hand-built fixture** of well-characterised CRC variants, **not a cohort**.
- It is **not** the 150-tumor preliminary set. That data is not in our custody.
- Every result carries a **`calibration_pending`** flag, because both tools were trained largely
  on European-ancestry data and no per-population calibration target has been defined yet. No
  number here renders as a clean call. That is deliberate (guardrails R1/S1), and the caveat does
  not weaken because two tools happen to concur
  (`test_calibration_pending_survives_two_providers`).

*Sources: [`tests/test_consensus_two_providers.py`](../tests/test_consensus_two_providers.py)
(run in CI), [`docs/probes/consensus-two-providers.md`](probes/consensus-two-providers.md).*

---

## 3 · The disagreement table, and the distinction that matters

Every variant where the two predictors diverge:

| Variant | Gene | AlphaMissense (structural) | EVE (evolutionary) | Outcome |
|---|---|---|---|---|
| G12D | KRAS | pathogenic | *uncertain* | VUS |
| G13D | KRAS | pathogenic | *uncertain* | VUS |
| A146T | KRAS | pathogenic | *uncertain* | VUS |
| R175H | TP53 | pathogenic | *uncertain* | VUS |
| R248Q | TP53 | pathogenic | *uncertain* | VUS |
| E545K | PIK3CA | pathogenic | *uncertain* | VUS |
| **H1047R** | **PIK3CA** | *uncertain* | **benign** | VUS |

Every one is a canonical recurrent somatic hotspot. But the seven are **not the same kind of
event**, and the distinction is load-bearing for what you decide in §8:

**Six are abstentions.** AlphaMissense is confident; EVE returns *Uncertain*. EVE assigns
`Uncertain` **by design** — it retains only the 75% most confident classifications over all
possible amino-acid substitutions and labels the rest uncertain. So in these six cases the tools
do not contradict each other: one commits, the other declines to. **Under the current rule a
declining tool counts the same as a dissenting one.**

**One is a genuine contradiction.** For PIK3CA H1047R, AlphaMissense leans uncertain and EVE
actively calls it **benign**. Nothing agrees, and the variant correctly stays VUS. See §6.

The rule never picks a winner where the tools differ —
`test_disagreements_are_surfaced_not_averaged` asserts that wherever they disagree the variant
remains VUS. Nothing is averaged into a falsely confident number.

### Why the other thirteen did not move

| Reason a variant is still VUS | n |
|---|---:|
| **The two predictors disagree** | **7** |
| Neither predictor covers it (nonsense / frameshift) | 5 |
| Only one predictor covers it (FBXW7 — see §7) | 1 |

**The residual is disagreement-limited, not coverage-limited.** The main blocker is not missing
data; it is that two independent lines of evidence do not concur on canonical hotspots.

That has a direct planning consequence, and it is why we flagged it early rather than after four
predictors were wired: **adding the third and fourth predictors will not reduce VUS in
proportion.** With a two-vote threshold, a further caller helps *only where it breaks a tie*.
Where EVE systematically abstains on hotspots, a third tool agreeing with AlphaMissense would
resolve those cases — a third tool that also abstains would change nothing. The reachable
reduction therefore depends less on *how many* predictors are wired than on **how the rule treats
abstention** (questionnaire A8).

This does **not** refute the build plan's Phase-2 target of ~90% → ~25–30%, itself stated there
as "a target, not a promise" ([`docs/build-plan.md`](build-plan.md) line 79). A 20-variant
fixture cannot: the target is stated about the 150-tumor cohort, which we have not seen. What
this provides is a **tested constraint on the mechanism** by which that target would be reached.

*Sources: [`docs/DECISIONS.md`](DECISIONS.md) D-010,
[`tests/test_consensus_two_providers.py`](../tests/test_consensus_two_providers.py).*

---

## 4 · The third signal — and why the gene-level answer was worthless

The drivers step (SPEC-028) takes a variant's residue and intersects it with what IntOGen
published as significant within a stated cohort scope — a significant PFAM domain (smRegions,
q < 0.1), a linear 2D cluster (OncodriveCLUSTL, p < 0.05), or a 3D structural cluster (HotMAPS,
q < 0.05).

The first thing it established was a negative one, and it is worth stating because it is the
error the design exists to avoid: **a gene being a driver does not make every variant in it a
driver.** On this fixture `gene_is_driver_in_scope` is **true for all 20 variants** — a
gene-level driver signal would have emitted a constant and been worth nothing at all. All of the
information is positional:

| Outcome | n |
|---|---:|
| Residue inside a significant domain / 2D cluster / 3D cluster | **10** |
| Gene is a driver, residue in **no** significant cluster | **5** |
| Not a missense change — no residue to intersect | 5 |

The three "nothing found" states are kept distinct on purpose, because they mean different
things and **none of them means "not a driver"**: `gene_not_a_driver_in_scope`,
`no_positional_evidence`, `not_missense`.

*Sources: [`producers/drivers/README.md`](../producers/drivers/README.md),
[`docs/probes/drivers-axis-payoff.md`](probes/drivers-axis-payoff.md) §1 (the per-variant table),
[`tests/test_drivers_producer.py`](../tests/test_drivers_producer.py).*

---

## 5 · The central result — the deadlock and the driver evidence are the same six variants

Of the ten variants carrying positional driver evidence, four had already been reclassified
pathogenic by the two predictors agreeing (SMAD4 R361H, KRAS G12V, TP53 Y220C, BRAF V600E). The
remaining **six carry positional driver evidence where the pathogenicity consensus did *not*
reach pathogenic** — and they are **exactly** the six abstention disagreements from §3:

> **KRAS G12D · KRAS G13D · KRAS A146T · TP53 R175H · TP53 R248Q · PIK3CA E545K**

Not a subset. Not five of six with a near-miss. The same six.

| Variant | AlphaMissense | EVE | IntOGen positional evidence (COAD/READ) |
|---|---|---|---|
| KRAS G12D | pathogenic | *uncertain* | 2D + 3D + domain |
| KRAS G13D | pathogenic | *uncertain* | 2D + 3D + domain |
| KRAS A146T | pathogenic | *uncertain* | domain |
| TP53 R175H | pathogenic | *uncertain* | 2D + 3D + domain |
| TP53 R248Q | pathogenic | *uncertain* | 2D + 3D + domain |
| PIK3CA E545K | pathogenic | *uncertain* | 2D + 3D |

**And the correspondence extends to the negative case.** The seventh disagreement — PIK3CA
H1047R, the one *genuine contradiction* rather than an abstention — carries
`no_positional_evidence` in colorectal scope. So the driver axis speaks on all six cases where
the pathogenicity axis was **deadlocked**, and is silent on the single case where the
pathogenicity axis was **contradicted**. The abstention/contradiction distinction drawn in §3 on
one axis reappears, unprompted, on a completely different axis.

### What this suggests — and the words are chosen carefully

The natural reading of six variants stuck at a two-vote threshold is that the threshold is
slightly wrong: relax it and they resolve. This result suggests a different reading.

**The deadlock may not be a threshold problem. It may be a question the pathogenicity axis
cannot answer.** EVE is an evolutionary model; it infers damage from conservation across
species. A somatic hotspot is recurrent in tumours because it confers a growth advantage — not
because it is a rare deleterious allele at a deeply conserved position. Asking an evolutionary
conservation model whether KRAS G12D is "intolerable" may simply be the wrong question, and
*Uncertain* may be the correct and honest answer to it. If so, the six are not evidence that the
rule is mis-tuned; they are evidence that a **second, different axis** is where their answer
lives — and that axis, independently and without being tuned to do so, supports all six.

That reading has a concrete consequence for §8: **relaxing the consensus threshold and admitting
driver evidence as its own line of evidence are not two routes to the same place.** One resolves
these variants by lowering the bar on an axis that may not be able to answer them; the other
resolves them on an axis that already has. A third independent method agreeing is stronger
evidence than relaxing a threshold until two methods suffice.

### The bound on this result, stated as plainly as the result itself

**This is a 20-variant observation. It is not an established pattern.**

- n = 6 out of 20. A correspondence this clean at that size can arise **by construction**: the
  fixture is built from canonical, well-characterised CRC hotspots, and canonical hotspots are
  *precisely* the variants that tend to be both (a) structurally predicted pathogenic and (b)
  positionally recurrent enough for IntOGen to find. The two sets may coincide because of how the
  fixture was chosen, not because of anything about the biology.
- **Nothing was tested.** No hypothesis was pre-registered, no null model was specified, and no
  significance was computed — because at n = 20 on a hand-picked fixture, none would mean
  anything.
- The mechanism proposed above is a **hypothesis consistent with the observation**, not a
  demonstrated cause. It also does not fit all six equally well: four sit in genes IntOGen calls
  activating (KRAS ×3, PIK3CA ×1), but **two are TP53** — a loss-of-function gene, where the
  "growth advantage rather than conserved-position damage" story does not straightforwardly
  apply. Whatever is happening to those two needs a different explanation.
- **What would make it a finding:** the same comparison on the 150-tumor cohort, or on any
  variant set not selected for canonical hotspots, with the coincidence rate compared against a
  null drawn from variants matched on gene and recurrence. None of that is possible today — no
  cohort data is in this project's custody.

We are reporting it now, at this strength, because it bears directly on a decision you are about
to make (A8/A15), and because reporting it later would not make it stronger.

**Nothing has been built toward either resolution.** Driver evidence is **not** routed into the
variant_effect consensus, `min_agree` is untouched, the drivers step emits *evidence* and never a
*call*, and there is deliberately no `is_driver` field anywhere in
[`contracts/driver_evidence.py`](../contracts/driver_evidence.py).

*Sources: [`docs/probes/drivers-axis-payoff.md`](probes/drivers-axis-payoff.md) §1–§2,
[`docs/DECISIONS.md`](DECISIONS.md) D-010 and D-012,
[`docs/DEFINITIONS_QUESTIONNAIRE.md`](DEFINITIONS_QUESTIONNAIRE.md) A15,
[`tests/test_drivers_producer.py`](../tests/test_drivers_producer.py).*

---

## 6 · PIK3CA H1047R across all four axes

H1047R is one of the most common activating hotspots in human cancer. Four independent sources
now speak to it, and three of the four decline to call it pathogenic:

| Axis | Verdict on H1047R |
|---|---|
| AlphaMissense (structural) | *uncertain* — just below its published pathogenic cut-point |
| **EVE (evolutionary)** | **benign** |
| **IntOGen, colorectal (COAD/READ)** | gene **is** a driver; residue 1047 in **no** significant cluster (0 of 2 rows) |
| ClinVar record **that EVE itself distributes** alongside its prediction | **Pathogenic** |

So a second, methodologically independent model moves this variant *further* from pathogenic;
EVE disagrees with the very clinical annotation it ships; and the driver axis — which speaks on
all six of the §5 deadlocks — does **not** rescue this one.

### The colorectal-vs-pan-cancer split

The reason the driver axis is silent here is **cohort scope**, and it is measurable:

| Cohort scope | PIK3CA a driver? | Residue **1047** in a significant cluster? |
|---|---|---|
| **COAD / READ (colorectal)** | Yes — Act, 2 cohorts | **NO — 0 of 2 rows** |
| Pan-cancer | Yes — 109 cohorts | **YES — 35 of 109 rows** |

The colorectal clusters IntOGen actually publishes for PIK3CA are `2D = 542:546` and
`3D = {542, 545, 546}` — the **helical-domain** hotspot. Residue **1047 (kinase domain) is not
among them in either colorectal cohort.** This is consistent with CRC PIK3CA mutation being
helical-domain-weighted, and it is now measured from a citable source in-repo rather than
assumed.

Note the direct contrast with §5: **PIK3CA E545K — residue 545, inside that colorectal helical
cluster — is one of the six the driver axis supports.** Same gene, same fixture, opposite
answers, decided entirely by which residue and which cohort scope.

### The bound — a null result, reported

This raised an obvious worry: AlphaMissense and EVE both predict **pathogenicity** in roughly the
germline/Mendelian sense, whereas what matters for a tumour is whether a variant **drives** it.
If the tools were systematically blind to activating drivers *as a class*, that would be a
problem with the premise of Phase 2, not a tuning issue.

**We tested it, and it did not hold.** Using your own 15 named CRC driver genes, every
statistically significant recurrent hotspot in them (n = 178, from cancerhotspots.org), and
mechanism-of-action labels taken from IntOGen and OncoKB rather than our own judgement:

| Group | n | called pathogenic |
|---|---:|---:|
| Activating (gain-of-function) | 77 | **93.5%** |
| Loss-of-function | 101 | **95.0%** |

No significant difference (Mann-Whitney U p = 0.312; Fisher exact p = 0.748; colorectal-observed
subset p = 0.700 / 1.000). **There is no class-level activating-driver blindness.** All five
activating misses were in PIK3CA specifically — a gene-level effect, not a mechanism-level one.

So the honest statement is three-part:

1. **The class-level worry is not supported.** The Phase-2 premise survives that test.
2. **H1047R is a real, variant-level miss**, now reproduced across two predictors and not
   rescued by the driver axis under colorectal scope. Because it is so common it carries
   **96.1%** of the missed activating tumour burden pan-cancer (647 of 673 tumours); in bowel
   tumours specifically the gap narrows to 4.3% vs 2.8% for loss-of-function.
3. **The finding is therefore not "the tools have a driver blind spot" — it is that H1047R's
   driver status is strongly cohort-dependent**: overwhelming pan-cancer (largely contributed by
   breast tumours), unestablished in colorectal cohorts of the size IntOGen has. That is a
   *scope* question, not a *tool* question, and it is yours to answer (A13).

The 178-hotspot probe carries eight stated limitations, and two of them matter here: it tests
**recurrent hotspots only** — rare drivers, exactly what the ancestry-enriched arm is looking
for, are not tested at all — and it is **not ancestry-stratified in any way**, so it says nothing
about whether AlphaMissense behaves differently in AA / Ghanaian / Ethiopian tumours, which is
the actual concern of guardrails R1 and S1. A null result there is not a clean bill of health.

*Sources: [`docs/probes/alphamissense-driver-coverage.md`](probes/alphamissense-driver-coverage.md),
[`docs/DECISIONS.md`](DECISIONS.md) D-008 and its two addenda,
[`tests/test_consensus_two_providers.py`](../tests/test_consensus_two_providers.py)
(`test_h1047r_is_not_rescued_by_the_second_tool`).*

---

## 7 · Coverage gaps, per signal

Each signal is blind in a different place, and the blindnesses do not overlap — which is both the
argument for using three and the reason coverage has to be reported per signal rather than in
aggregate.

### AlphaMissense — non-missense variants, by construction

AlphaMissense covers **single amino-acid missense substitutions only**. Five of the twenty
fixture variants are nonsense or frameshift (`APC R1450*`, `APC E1309fs`, `RNF43 G659fs`,
`APC T1556fs`, `APC Q1367*`) and are outside the tool's domain entirely. Those five yield **"no
coverage"**, never a call — a state deliberately kept distinct from "not found", which raises.

One gap was **closed** rather than accepted, and it is worth recording because it removed a
dependency: the three fixture variants called against the pangenome reference have no
AlphaMissense genomic coordinates at all. Keying the lookup on `(uniprot_id, protein_variant)`
rather than on genomic position makes it reference-build independent, so they resolve without
waiting on SPEC-004's reference reconciliation
(`test_pangenome_variants_resolve_without_spec_004`; decision D-006 option (c), built as
SPEC-027).

### EVE — two of your fifteen driver genes are not published at all

EVE publishes predictions for **3,211 proteins**, not the proteome. Of your 15 named CRC driver
genes it covers **13**. It does **not** publish:

- **RNF43**
- **FBXW7**

**Why RNF43 matters here specifically.** Your own preliminary data reports RNF43 mutation
frequency varying significantly by population (**p = 0.0047**), highest in the NHW cohort at
**73.6%** — *"a rate nearly double that seen in the other populations"*
([grant strategy](sources/Domestic_Project_Research_Strategy_PF5.txt), lines 196–198, quoted
verbatim). It is precisely a population-varying driver, which is what this study exists to
characterise. Having only one of two predictors able to see it is a gap worth closing.

The practical effect is concrete: **a variant covered by only one tool cannot reach the two-vote
threshold**, however good that single call is. On this fixture the cost is exactly one variant —
FBXW7 R465C, which AlphaMissense calls pathogenic and EVE cannot see, so it stays VUS with one
excellent call and one absent tool. To the rule, that is indistinguishable from a variant nothing
understands. (Across the wider 35-entry expectation set the gap costs six entries: four FBXW7,
two RNF43.)

Options are recorded in decision D-009 and **none has been implemented** — it is a domain call.
The cheapest is worth noting: evemodel.org states *"We are adding predictions for new genes
regularly — can't find the gene/protein you are looking for? Contact us and we can run it for
you!"* That costs an email.

### IntOGen — five of your fifteen genes have no colorectal rows

IntOGen has colorectal (COAD/READ) rows for **10 of your 15** named CRC driver genes. Absent from
colorectal scope entirely:

- **MLH1, MSH2, MSH6, PMS2** — the four mismatch-repair genes
- **TGFBR2**

This is consistent with their drivers being **truncating or germline rather than clustered
missense**, and it is not a retrieval failure. Variants in those genes yield
`gene_not_a_driver_in_scope`, which is **not** "not a driver".

**The direction of this gap matters more than its size.** Absence of positional evidence is
*uninformative, not negative* — a residue can fail to reach significance because the cohort had
no power to detect recurrence at that position **in that population**, not because the residue is
unimportant. IntOGen's clusters are significant relative to the mutation spectrum of the cohorts
they were computed on (CPTAC, Hartwig, TCGA — overwhelmingly European ancestry). Recurrence-based
significance is partly a statement about **who was sequenced**. Treating absence as negative
would convert a sampling artifact into a finding, in the direction that most disadvantages the
populations this study exists to serve. The system is built so a downstream reader cannot do
that; whether that is the right treatment is questionnaire A12.

*Sources: [`docs/eve-data.md`](eve-data.md), [`docs/intogen-data.md`](intogen-data.md),
[`docs/alphamissense-data.md`](alphamissense-data.md), [`docs/DECISIONS.md`](DECISIONS.md)
D-006 and D-009, [`producers/drivers/README.md`](../producers/drivers/README.md).*

---

## 8 · What we need from you

Four decisions. Each is genuinely yours — the tooling is built so it stops and asks rather than
choosing for you, and **none of these has been decided in code**. All are in
[`docs/DEFINITIONS_QUESTIONNAIRE.md`](DEFINITIONS_QUESTIONNAIRE.md), where you can reply inline.

### A8 + A15 — please answer these two together

They are the same decision seen from two sides, and answering one without the other could produce
a rule that contradicts itself.

**A8 · How should the consensus rule treat abstention?** Six of the seven blocked variants are
"one tool confident, one declines to commit" (§3). Should a tool answering *Uncertain* count as a
**vote against**, or as an **abstention** — so that one confident call plus one abstention could
suffice? Should the four tools be weighted rather than counted equally?

**A15 · The six deadlocked variants are exactly the six with driver evidence. Does that change
how they should be resolved?** There are two non-equivalent ways to stop leaving them as VUS:
**(i)** adjust the consensus rule, resolving them on the *pathogenicity* axis via a threshold
change — that is A8; or **(ii)** treat independent driver evidence as its own qualifying line of
evidence, resolving them on the *driver* axis and leaving the pathogenicity rule untouched. §5
sets out why we think these are genuinely different, and why (ii) may be the more honest reading
of what the data shows — while also setting out why a 20-variant observation should not by itself
settle it.

*Note the caveats from A12/A13 apply to option (ii): driver evidence is `calibration_pending`,
and absence of it is uninformative rather than negative.*

### A9 / A11 / A14 — are the publishers' cut-points right for this study?

We transcribed all three exactly as published and **changed nothing** (control I3). All three
were chosen by their publishers for a general setting, not for this one.

- **A9 · AlphaMissense** splits its score at `< 0.34` benign / `> 0.564` pathogenic, an operating
  point the publisher chose for roughly 90% precision on a general population. H1047R falls just
  under the 0.564 line (§6).
- **A11 · EVE** publishes no threshold; it retains the **75% most confident** classifications and
  labels the rest *Uncertain*. A11 also asks the question §5 turns on: should an *evolutionary*
  line of evidence carry the same weight as a *structural* one for **somatic** variants? That
  difference is precisely why the two disagree in §3.
- **A14 · IntOGen** inclusion criteria — driver methods q < 0.1, smRegions domains q < 0.1,
  OncodriveCLUSTL 2D clusters p < 0.05, HotMAPS 3D clusters q < 0.05. We consume rows as the
  publisher filtered them and do not re-filter.

### A13 — should driver evidence be colorectal-specific or pan-cancer?

This changes real answers (§6): H1047R falls inside a significant cluster in **35 of 109
pan-cancer** rows and **0 of 2 colorectal** rows. Colorectal scope is fewer, smaller, on-target
cohorts; pan-cancer is far more evidence but imports tumour types this study is not about. We
default to colorectal and record the scope on every result, so the choice is visible and
reversible.

### A12 — does "calibration" even apply to an evidence lookup, rather than a prediction?

AlphaMissense and EVE are predictors trained largely on European-ancestry data, so stamping their
output `calibration_pending` is straightforward. The drivers step is different in kind — it
predicts nothing, it looks up. We stamped it `calibration_pending` anyway, for the asymmetry
argued in §7: **presence** of evidence is fairly transferable; **absence** is uninformative
rather than negative. The specific question: should a downstream reader ever be allowed to treat
"no driver evidence" as evidence **against** a variant? We have built it so they cannot.

---

## 9 · Which document is canonical

Four documents now touch this material. Their relationship, stated so no two of them can be read
as competing:

| Document | Role | Canonical for |
|---|---|---|
| **`docs/FINDINGS.md`** (this file) | **Reader-facing consolidated findings** | **Every interpretive claim above.** Where any other document's narrative differs, this one governs. |
| [`docs/probes/consensus-two-providers.md`](probes/consensus-two-providers.md) | Run record — SPEC-005 (2 of 4) | The measured consensus output; the coverage-overlap table; the EVE-vs-shipped-ClinVar table |
| [`docs/probes/drivers-axis-payoff.md`](probes/drivers-axis-payoff.md) | Run record — SPEC-028 | The **per-variant evidence table** (all 20 rows across three axes), not reproduced in full here |
| [`docs/probes/alphamissense-driver-coverage.md`](probes/alphamissense-driver-coverage.md) | Run record — 178-hotspot probe | The probe's method, per-gene breakdown, and its eight stated limitations |

**This document supersedes the narrative of all three probe records and sits above them.** They
are retained deliberately, not left as duplicates: each is the run artifact for a specific test,
carries method detail and per-variant tables this summary compresses, and is where a reviewer
goes to check a number rather than to read an argument.
[`docs/probes/drivers-axis-payoff.md`](probes/drivers-axis-payoff.md) has been reduced to exactly
that role in the same change that created this file — its interpretive sections were removed and
now point here, so the cross-axis argument lives in one place only.

`docs/probes/phase2-vus-findings.md` no longer exists: this file **is** that document, moved out
of `probes/` (it was never a probe record) and rewritten to cover all three signals.

---

## 10 · What is NOT established — all of it, in one place

Each of these is a conclusion someone could reasonably but wrongly draw from the sections above.

**About the data**

1. **No real cohort data has been processed.** Not the 150-tumor preliminary set, not any patient
   data. Everything above is a **20-variant synthetic fixture** (plus four controls for the
   drivers step). All 8 study datasets in [`docs/DATA-INVENTORY.md`](DATA-INVENTORY.md) remain
   UNKNOWN for custody, location, and access.
2. **No number here is calibrated for any population.** Everything is stamped
   `calibration_pending` because per-population calibration targets are still **[TO BE DEFINED]**
   ([`DEFINITIONS.md`](../DEFINITIONS.md) §3). Two European-centric models agreeing does not
   constitute calibration.
3. **Nothing here is ancestry-stratified.** Not the fixture, not the 178-hotspot probe, not
   IntOGen's cohorts. This work says **nothing** about whether any of these tools behaves
   differently in AA / Ghanaian / Ethiopian tumours — the actual concern of guardrails R1 and S1.

**About the central result (§5)**

4. **The six-and-six correspondence is an observation, not an established pattern.** n = 20,
   hand-picked canonical hotspots, no hypothesis pre-registered, no null model, no significance
   computed. The two sets may coincide because of how the fixture was built.
5. **The proposed mechanism is a hypothesis, not a demonstrated cause.** "The pathogenicity axis
   cannot answer this question" is *consistent with* the observation; it has not been tested, and
   it does not fit all six variants equally well.

**About the driver evidence**

6. **It does not establish that any variant is a driver.** It reports evidence. There is no
   `is_driver` field in the contract, by construction.
7. **`no_positional_evidence` is not evidence against a variant** (§7). Nor is
   `gene_not_a_driver_in_scope`, nor `not_missense`. Three distinct states, none of them negative.
8. **It says nothing about pathogenicity**, and is not wired into the variant_effect consensus.
   `min_agree` is untouched.
9. **IntOGen has not been run on this project's cohort.** This is IntOGen's *published*
   compendium, computed on other people's cohorts. Running IntOGen over our own mutations is
   SPEC-020, which is **GATED** — no cohort data exists (decision D-011).

**About the pathogenicity axis**

10. **The 178-hotspot null is not a clean bill of health.** It tests recurrent hotspots only, so
    rare drivers — exactly what the ancestry-enriched arm looks for — are untested; mechanism
    labels are gene-level, not variant-level; and each group is dominated by one gene
    (loss-of-function is 83% TP53, activating is 56% PIK3CA). Eight limitations are stated in
    full in the probe record.
11. **SPEC-005 is not complete** — two predictors of four. `PolyPhenProvider` and `SIFTProvider`
    still `raise NotImplementedError`. It remains SPECIFIED, not FUNCTIONAL.

**About what we changed**

12. **No threshold, cut-point, or consensus parameter was authored or adjusted by the coding
    agent.** All are transcribed from publishers with citation and registered AWAITING SIGN-OFF
    in [`DEFINITIONS.md`](../DEFINITIONS.md) (control I3).
13. **Every decision record referenced here is PROPOSED, not approved** — D-006 through D-013 all
    await owner or domain-owner sign-off, and D1–D6 are OPEN
    ([`docs/DECISIONS.md`](DECISIONS.md)).
14. **No third-party score or compendium data is stored in this repository.** Only distributional
    statistics appear in any committed document, including this one. The governing question is
    decision D3, still OPEN.

---

## 11 · Reproducing all of this

```powershell
# from the repo root, in PowerShell (see AGENTS.md §Environment)
python tools\alphamissense\fetch_scores.py            # fetches into a gitignored local cache
python tools\eve\fetch_scores.py                      # same
python tools\intogen\fetch_compendium.py              # same (~965 KB, one request)

python tests\test_consensus_two_providers.py          # prints §2 and §3
python tests\test_drivers_producer.py                 # prints §4 and §5
python tools\alphamissense\probe_driver_coverage.py   # reproduces §6's 178-hotspot probe
```

Without the caches the suites **skip and report `INCOMPLETE COVERAGE`** rather than passing
silently — no result here can be produced without the real published data behind it. Set
`ALPHAMISSENSE_CACHE_REQUIRED=1`, `EVE_CACHE_REQUIRED=1`, `CONSENSUS_CACHES_REQUIRED=1` and
`INTOGEN_CACHE_REQUIRED=1` to make a skip a hard failure.

All nine suites (**77 tests**) run in CI on every push and pull request, on Python 3.8 and 3.14
([`.github/workflows/tests.yml`](../.github/workflows/tests.yml)).
