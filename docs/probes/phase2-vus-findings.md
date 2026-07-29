# Phase 2 — what the variant-effect work has established so far

**For:** Dr. Laura, Qiwu · **From:** the computational team · **Date:** 28 July 2026

A single place to read what the two completed slices actually showed. Everything here is
measured and reproducible; every claim cites where it comes from in the repository. Where a
question is yours to answer rather than ours, it is marked and pointed at the questionnaire.

---

## 0 · The one-paragraph version

We wired two independent variant-effect predictors — one **structural**, one **evolutionary** —
against their real published data, and ran the consensus rule the project already specified. On
our small test set, variants of unknown significance fell from **100% to 65%**: seven of twenty
reclassified, every one by the two tools independently agreeing. The more interesting result is
*why the other thirteen did not move*: for seven of them the two tools **disagree**, not because
data is missing. That has a direct consequence for planning — **adding the third and fourth
predictors will not reduce VUS in proportion.** Three questions now need your judgement, listed
in §7.

**Important scope statement, stated once and meant literally:** this ran on a **20-variant
synthetic test fixture**, not on the 150-tumor preliminary cohort. **No real cohort data exists
in this project's custody.** Every dataset in [`docs/DATA-INVENTORY.md`](../DATA-INVENTORY.md)
is still recorded as UNKNOWN for custody, location, and access. Nothing below is a result about
patients.

---

## 1 · What was done

Two of the four predictors named in the plan are now wired against real published data:

| Predictor | Evidence type | What it asks | Status |
|---|---|---|---|
| **AlphaMissense** (Google DeepMind) | Structural + population constraint | Is this variant clinically pathogenic? | **Wired** |
| **EVE** (Marks Lab / OATML) | Evolutionary — conservation across species | Is this variant evolutionarily intolerable? | **Wired** |
| PolyPhen | — | — | Not wired |
| SIFT | — | — | Not wired |

They were chosen to be *methodologically independent*: AlphaMissense reasons largely from
protein structure and how constrained a position is across human populations; EVE reasons from
how a position has been conserved across evolution. When two such different lines of evidence
agree, that agreement means something. When they disagree, that is informative too — see §3.

Both tools' data is fetched on demand and **never stored in the repository**, for licensing
reasons documented in [`docs/alphamissense-data.md`](../alphamissense-data.md) and
[`docs/eve-data.md`](../eve-data.md).

*Sources: [`producers/variant_effect/alphamissense.py`](../../producers/variant_effect/alphamissense.py),
[`producers/variant_effect/eve.py`](../../producers/variant_effect/eve.py),
[`SPEC.md`](../../SPEC.md) SPEC-005.*

---

## 2 · The VUS result

```
VUS before: 20/20 (100.0%)    VUS after: 13/20 (65.0%)    reclassified: 7
```

The seven reclassified as pathogenic: **SMAD4 R361H, CTNNB1 S45F, KRAS G12V, SMAD4 D351H,
TP53 Y220C, CTNNB1 T41A, BRAF V600E.** In every case both predictors independently called
pathogenic — none was reclassified on a single tool's say-so.

**Why one tool was not enough.** The consensus rule requires **two** concurring calls
(`min_agree: 2`). With AlphaMissense alone the reduction was **exactly zero** — not a failure,
but arithmetic: one caller can never reach a two-vote threshold. This is asserted by a test
rather than assumed, so it cannot quietly stop being true.

### What this number is, and is not

- It is **a 20-variant hand-built fixture** of well-characterised CRC variants, not a cohort.
- It is **not** the 150-tumor preliminary set. That data is not in our custody.
- Every result carries a **`calibration_pending`** flag, because both tools were trained largely
  on European-ancestry data and no per-population calibration target has been defined yet. No
  number here renders as a clean call. That is deliberate (guardrails R1/S1).

*Sources: [`tests/test_consensus_two_providers.py`](../../tests/test_consensus_two_providers.py)
(run in CI), [`docs/probes/consensus-two-providers.md`](consensus-two-providers.md).*

---

## 3 · The disagreement table — the central result

This is more scientifically useful than the VUS percentage. Every variant where the two
predictors diverge:

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
event**, and the distinction matters for what you decide in §7:

**Six are abstentions.** AlphaMissense is confident; EVE returns *Uncertain*. EVE assigns
`Uncertain` by design — it retains only the 75% most confident classifications and labels the
rest uncertain. So in these six cases the tools do not contradict each other: one commits, the
other declines to. Under the current rule a declining tool counts the same as a dissenting one.

**One is a genuine contradiction.** For PIK3CA H1047R, AlphaMissense leans uncertain and EVE
actively calls it **benign**. Nothing agrees, and the variant correctly stays VUS. See §5.

The rule never picks a winner where the tools differ — a test asserts that wherever they
disagree the variant remains VUS. Nothing is averaged into a falsely confident number.

---

## 4 · Why the other thirteen did not move — and what it implies

| Reason a variant is still VUS | n |
|---|---:|
| **The two predictors disagree** | **7** |
| Neither predictor covers it (nonsense / frameshift) | 5 |
| Only one predictor covers it (FBXW7 — see §6) | 1 |

**The residual is disagreement-limited, not coverage-limited.** The main blocker is not missing
data; it is that our two independent lines of evidence do not concur on canonical hotspots.

### What this implies for the grant's projection

The build plan states the Phase-2 target as a VUS-fraction reduction of **"~90% → ~25–30%,
framed as a target, not a promise"**
([`docs/build-plan.md`](../build-plan.md) line 79). We want to be careful and precise here:

- This work **does not refute that target.** A 20-variant fixture cannot; the target is stated
  about the 150-tumor cohort, which we have not seen.
- What it *does* provide is a **tested constraint on the mechanism** by which the target would be
  reached. The implicit assumption in "wire four predictors and VUS falls" is that predictors
  contribute additively. On this fixture they do not. With a two-vote threshold, a third
  predictor helps **only where it breaks a tie**. Where EVE systematically abstains on hotspots,
  a third tool agreeing with AlphaMissense would resolve those cases — but a third tool that
  also abstains would change nothing.
- So the reachable reduction depends less on *how many* predictors are wired than on **how the
  rule treats abstention**, and on whether the remaining predictors abstain on the same variants.
  That is a domain decision (§7, question A8), not an engineering one.

We are flagging this now, while it is cheap to act on, rather than after four predictors are
wired and the number has not moved as projected.

*Sources: [`docs/DECISIONS.md`](../DECISIONS.md) D-010,
[`tests/test_consensus_two_providers.py`](../../tests/test_consensus_two_providers.py).*

---

## 5 · PIK3CA H1047R — and the limit of what it means

H1047R is one of the most common activating hotspots in human cancer. Three independent sources
disagree about it:

| Source | Call |
|---|---|
| AlphaMissense (structural) | *uncertain* — just below its pathogenic cut-point |
| **EVE (evolutionary)** | **benign** |
| ClinVar record **that EVE itself distributes** alongside its prediction | **Pathogenic** |

So a second, methodologically independent model moves this variant *further* from pathogenic,
and EVE disagrees with the very clinical annotation it ships.

### The bound on that finding — a null result, reported

This raised an obvious worry: AlphaMissense and EVE both predict **pathogenicity** in roughly
the germline/Mendelian sense, whereas what matters for a tumor is whether a variant **drives**
it. Activating hotspots are common in tumors because they confer growth advantage, not because
they are rare damaging alleles. If the tools were systematically blind to activating drivers,
that would be a problem with the premise of Phase 2, not a tuning issue.

**We tested it, and it did not hold.** Using your own 15 named CRC driver genes, every
statistically significant recurrent hotspot in them (n = 178), and mechanism-of-action labels
taken from IntOGen and OncoKB rather than our own judgement:

| Group | n | called pathogenic |
|---|---:|---:|
| Activating (gain-of-function) | 77 | **93.5%** |
| Loss-of-function | 101 | **95.0%** |

No significant difference (Mann-Whitney p = 0.31; Fisher exact p = 0.75; colorectal-only subset
p = 0.70 / 1.00). **There is no class-level activating-driver blindness.** All five activating
misses were in PIK3CA specifically — a gene-level effect, not a mechanism-level one.

So the honest statement is two-part: **the general worry is not supported**, and **H1047R
remains a real, variant-level miss now reproduced across two independent models.** We have not
"fixed" it, because reporting what the tools actually say — rather than what the literature
expects — is the behaviour you asked for. Whether and how to close that gap is question A10.

*Sources: [`docs/probes/alphamissense-driver-coverage.md`](alphamissense-driver-coverage.md),
[`docs/DECISIONS.md`](../DECISIONS.md) D-008.*

---

## 6 · Coverage — a gap you should know about

EVE publishes predictions for 3,211 proteins, not the whole proteome. Of your 15 named CRC
driver genes it covers **13**. It does **not** publish:

- **RNF43**
- **FBXW7**

**Why RNF43 matters here specifically.** Your own preliminary data reports RNF43 mutation
frequency varying significantly by population (**p = 0.0047**), highest in the NHW cohort at
**73.6%** — *"a rate nearly double that seen in the other populations"*
([grant strategy](../sources/Domestic_Project_Research_Strategy_PF5.txt), lines 196–198). It is
precisely a population-varying driver, which is what this study exists to characterise. Having
only one of two predictors able to see it is a gap worth closing.

The practical effect is concrete: a variant covered by only one tool **cannot reach the two-vote
threshold**, however good that single call is. Coverage asymmetry between tools converts
silently into un-reclassifiable variants.

Options are recorded in decision D-009 and **none has been implemented** — it is a domain call.
The cheapest is worth noting: evemodel.org states *"We are adding predictions for new genes
regularly — can't find the gene/protein you are looking for? Contact us and we can run it for
you!"* That costs an email.

*Sources: [`docs/eve-data.md`](../eve-data.md), [`docs/DECISIONS.md`](../DECISIONS.md) D-009.*

---

## 7 · What we need from you

Three decisions. Each is genuinely yours — the tooling is built so it stops and asks rather than
choosing for you, and none of these has been decided in code.

**A8 · How should the consensus rule treat abstention?**
Six of the seven blocked variants are "one tool confident, one declines to commit". Should a
tool answering *Uncertain* count as a **vote against**, or as an **abstention** — so that one
confident call plus one abstention could suffice? Should the four tools be weighted rather than
counted equally? This is the single highest-leverage question for the VUS number.

**A9 / A11 · Are the publishers' cut-points right for this study?**
AlphaMissense splits its score at <0.34 benign / >0.564 pathogenic. EVE retains the 75% most
confident classifications and calls the rest uncertain. We transcribed both exactly as published
and changed nothing. Both were chosen by their publishers for a general population. A11 also
asks whether an *evolutionary* line of evidence should carry the same weight as a *structural*
one for somatic variants — that difference is precisely why the two disagree in §3.

**D-009 · What should happen about RNF43 and FBXW7?**
Accept 13/15 and record the gap; ask the EVE authors to run the two genes; substitute
PolyPhen/SIFT for those genes only; or bring in driver-oriented evidence. We have recommended
but not chosen.

All three are in [`docs/DEFINITIONS_QUESTIONNAIRE.md`](../DEFINITIONS_QUESTIONNAIRE.md), where
A8 now lists the seven concrete disagreements so you are ruling on real variants rather than an
abstraction.

---

## 8 · Reproducing this

```powershell
# from the repo root, in PowerShell
python tools\alphamissense\fetch_scores.py     # fetches into a gitignored local cache
python tools\eve\fetch_scores.py               # same
python tests\test_consensus_two_providers.py   # prints every table in §2-§4
```

Without the caches the suites **skip and report `INCOMPLETE COVERAGE`** rather than passing
silently — no result here can be produced without the real data behind it.

## 9 · What is deliberately not claimed

- **No real cohort data has been processed.** Not the 150-tumor set, not any patient data.
- **No number here is calibrated for any population.** Everything is `calibration_pending`
  because per-population calibration targets are still [TO BE DEFINED] (DEFINITIONS.md §3).
- **SPEC-005 is not complete** — two predictors of four. It remains SPECIFIED, not FUNCTIONAL.
- **No threshold, cut-point, or consensus parameter was authored or adjusted by the coding
  agent.** All are transcribed from publishers with citation and marked AWAITING SIGN-OFF.
- **Neither tool's score data is stored in this repository**, for licensing reasons that remain
  open under decision D3. Only distributional statistics appear in any committed document.
