# Probe — does AlphaMissense systematically miss activating somatic drivers?

> **Investigation, not a code change.** No producer, consensus rule, calibration flag, or
> provenance behaviour was modified as a result of this. It changes nothing about SPEC-005
> except what we are entitled to claim for it.
>
> Reproduce: `python tools/alphamissense/probe_driver_coverage.py` (needs the local,
> gitignored score cache — see `docs/alphamissense-data.md`). **Run 2026-07-28.**

## 1 · The question

Wiring AlphaMissense (SPEC-005) surfaced one uncomfortable data point: **PIK3CA H1047R lands in the `ambiguous` band**, below the publisher's 0.564 pathogenic cut-point. It is one of
the most common activating hotspots in human cancer.

The hypothesis that raises:

> AlphaMissense predicts **clinical pathogenicity** in the Mendelian/germline sense — trained
> substantially on population frequency and structural constraint. Somatic **oncogenic driver**
> status is a different question: activating gain-of-function hotspots are common in tumors
> because they confer growth advantage, not because they are rare deleterious alleles. If that
> is right, a germline-oriented pathogenicity predictor is a **category mismatch** for somatic
> driver reclassification — the core premise of Phase 2.

If true, this would be a premise-level problem, not a tuning problem.

## 2 · Method

The probe was built so that **none of the three selection steps was mine**:

| Step | Source | Why it is not my judgement |
|---|---|---|
| **Gene set** | The grant strategy's own 15 "well-established, frequently mutated CRC driver mountains" — APC, BRAF, CTNNB1, FBXW7, KRAS, MLH1, MSH2, MSH6, NRAS, PIK3CA, PMS2, RNF43, SMAD4, TGFBR2, TP53 (`docs/sources/Domestic_Project_Research_Strategy_PF5.txt` line 332) | The project's own authoritative document |
| **Variant set** | Every statistically significant single-residue hotspot in those genes from **cancerhotspots.org** (Chang et al., *Nat Biotechnol* 2016; *Cancer Discov* 2018), with the substitution at each residue chosen as the **most observed** in their tumor data | Selection by recurrence and by observed frequency, not by me |
| **Group assignment** | **IntOGen** `Compendium_Cancer_Genes.tsv` ROLE column (2024-06-18 release, COAD cohort where present), cross-checked against **OncoKB** `geneType` | Two independent sources; the activating / loss-of-function / ambiguous scheme is the grant's own (line 357) |

The two role sources agreed on **10 of 10** genes where both had a call.

**Excluded, and why — stated rather than silently dropped:**

| Gene | Reason |
|---|---|
| **SMAD4** | IntOGen's COAD calls are **split** (LoF ×1, Act ×1). No unambiguous mechanism call, so it is not in either group. |
| **PMS2** | IntOGen role is literally `ambiguous` — the grant's own third category. |
| **MLH1, MSH2, MSH6** | Classified LoF on **OncoKB alone** (no IntOGen driver row). They contributed **zero** probe variants anyway: their drivers are truncating/germline, not recurrent missense. |
| APC, TGFBR2, NRAS, RNF43 | Included, but contributed few or no significant missense hotspots (APC 0, TGFBR2 0, RNF43 1, NRAS 3). |

Scores: real `am_pathogenicity` values from `AlphaMissense_aa_substitutions.tsv.gz`
(Zenodo `10.5281/zenodo.8208688`), fetched into the local gitignored cache. Calls use the
publisher's own cut-points (`< 0.34` benign, `> 0.564` pathogenic, ambiguous between).

**Final probe set: 178 variants — 77 activating, 101 loss-of-function.**

## 3 · Result — the hypothesis is NOT supported

> **On numbers in this document.** AlphaMissense predictions are CC BY-NC-SA 4.0 and this repo
> redistributes none of them. What follows are **distributional statistics** — counts,
> percentages, medians, means, test statistics — which are derived summaries, not the data. Medians and means are ROUNDED so that no exact published score value is reproduced.
> Per-variant score lookups are deliberately **not** reproduced here; run the probe locally
> against your own cache to see them.

### Group summary

| Scope | Group | n | pathogenic | ambiguous | benign | median | mean |
|---|---|---:|---:|---:|---:|---:|---:|
| Pan-cancer | **ACT** | 77 | 72 (93.5%) | 2 (2.6%) | 3 (3.9%) | 0.98 | 0.89 |
| Pan-cancer | **LOF** | 101 | 96 (95.0%) | 3 (3.0%) | 2 (2.0%) | 0.99 | 0.92 |
| Colorectal-observed | **ACT** | 63 | 60 (95.2%) | 2 (3.2%) | 1 (1.6%) | 0.98 | 0.91 |
| Colorectal-observed | **LOF** | 91 | 86 (94.5%) | 3 (3.3%) | 2 (2.2%) | 0.98 | 0.91 |

### Statistics

| Scope | Test | Result |
|---|---|---|
| Full probe set | Mann-Whitney U (scores) | U = 3544.0, **p = 0.312** |
| Full probe set | Fisher exact (pathogenic vs not) | [[72,5],[96,5]], **p = 0.748** |
| Colorectal-observed | Mann-Whitney U (scores) | U = 2761.5, **p = 0.700** |
| Colorectal-observed | Fisher exact | [[60,3],[86,5]], **p = 1.000** |

*(Both tests implemented in-repo from stdlib — no scipy, no new dependency.)*

**No significant difference on any measure.** AlphaMissense calls ~94% of recurrent somatic
hotspots pathogenic, and it does so at the *same rate* for activating and loss-of-function
drivers. In the colorectal-observed subset the activating group is marginally *better* called
than the loss-of-function group.

### Plain answer

**The hypothesis does not hold. PIK3CA H1047R is an outlier, not the tip of a pattern.**

There is no evidence here that AlphaMissense is systematically blind to activating drivers as a
class. The category-mismatch concern, as stated, is **not supported by this probe**. The Phase 2
premise survives.

### Where the misses actually are

Every miss, both groups, ordered by score (band, not value):

| Group | Gene | Variant | Call | Tumors | Bowel |
|---|---|---|---|---:|---:|
| ACT | PIK3CA | M1V | benign | 6 | 0 |
| LOF | FBXW7 | R14Q | benign | 9 | 4 |
| ACT | PIK3CA | H1065Y | benign | 5 | 1 |
| LOF | TP53 | R110L | benign | 43 | 3 |
| ACT | PIK3CA | N107S | benign | 6 | 0 |
| LOF | TP53 | P152L | ambiguous | 38 | 10 |
| LOF | TP53 | L130V | ambiguous | 30 | 5 |
| LOF | FBXW7 | R224Q | ambiguous | 10 | 3 |
| ACT | PIK3CA | E970K | ambiguous | 9 | 2 |
| **ACT** | **PIK3CA** | **H1047R** | **ambiguous** | **647** | **54** |

Per gene:

| Gene | Role | n | pathogenic | missed | median |
|---|---|---:|---:|---:|---:|
| KRAS | ACT | 10 | 10 | 0 | ~0.996 |
| NRAS | ACT | 3 | 3 | 0 | — † |
| BRAF | ACT | 9 | 9 | 0 | ~0.999 |
| CTNNB1 | ACT | 12 | 12 | 0 | ~0.995 |
| **PIK3CA** | ACT | 43 | 38 | **5** | ~0.936 |
| TP53 | LOF | 84 | 81 | 3 | ~0.973 |
| FBXW7 | LOF | 16 | 14 | 2 | ~0.999 |
| RNF43 | LOF | 1 | 1 | 0 | — † |

† Median omitted where n ≤ 3: with so few values the "median" is effectively an individual
score, and this document reports distributional statistics only (see the note above).

**All five activating misses are PIK3CA.** KRAS, NRAS, BRAF and CTNNB1 hotspots are called
pathogenic without exception. Whatever is happening is **gene-specific, not mechanism-specific** —
which is a different, narrower, and more tractable finding than the hypothesis proposed.

### The one caveat that survives: recurrence weighting

Per-variant rates treat a 6-tumor hotspot and a 647-tumor hotspot alike. Weighted by how many
tumors actually carry each variant:

| Scope | Group | Tumors | Carried by a non-pathogenic call | % |
|---|---|---:|---:|---:|
| Pan-cancer | ACT | 7,528 | 673 | **8.9%** |
| Pan-cancer | LOF | 6,375 | 130 | 2.0% |
| Bowel only | ACT | 1,326 | 57 | **4.3%** |
| Bowel only | LOF | 895 | 25 | 2.8% |

The pan-cancer gap looks alarming until you decompose it: **647 of the 673 activating missed-tumor
burden (96.1%) is H1047R alone.** Remove that one variant and the gap disappears. In colorectal
tumors specifically it narrows to 4.3% vs 2.8%.

So the honest two-part statement:

1. **As a class-level claim, the hypothesis fails.** No systematic activating-driver blindness.
2. **As a variant-level observation, the concern is real but narrow.** The single most consequential
   miss in the entire probe is an activating hotspot, and because recurrence is heavily skewed, one
   miss carries disproportionate operational weight. No other missed variant exceeds 43 tumors.

## 4 · Limitations — this is suggestive, not conclusive

Stated plainly, because several of these are serious:

1. **Both groups are recurrent by construction.** cancerhotspots defines membership *by* recurrence,
   so this measures calibration on recurrent variants, not on somatic drivers generally. Rare
   drivers — exactly what the ancestry-enriched arm is looking for — are **not tested at all**.
2. **Mechanism labels are gene-level, not variant-level.** IntOGen's ROLE is a property of the gene.
   A gene labelled `Act` can carry LoF variants and vice versa. A proper test needs per-variant
   functional labels.
3. **Both groups are dominated by one gene each.** LOF is 83% TP53 (84/101); ACT is 56% PIK3CA
   (43/77). This is closer to a TP53-vs-PIK3CA comparison than a mechanism-class comparison, and
   the PIK3CA-specific result above is probably the real signal.
4. **One substitution per residue.** Taking only the most-observed alt allele ignores the allelic
   spectrum; KRAS G12C/G12V/G12A behave differently from G12D clinically.
5. **Canonical-isoform restriction.** Hotspots absent from AlphaMissense's canonical isoform were
   silently unavailable and dropped from the probe.
6. **No ancestry stratification whatsoever.** cancerhotspots is not ancestry-resolved. This probe
   says **nothing** about whether AlphaMissense behaves differently in AA / Ghanaian / Ethiopian
   tumors — which is the actual concern of guardrails **R1** and **S1**. A null result here is
   *not* evidence of ancestry-fair behaviour.
7. **Limited power.** At n = 77 / 101 with rates near 94%, only a large difference would be
   detectable. A modest real effect would not show up.
8. **Circularity risk.** AlphaMissense's training data and ClinVar/COSMIC-derived hotspot sets are
   not fully independent of each other.

### What a proper test would require

- **Variant-level functional labels** — deep mutational scanning / MAVE data (e.g. saturation
  mutagenesis of TP53, PIK3CA) rather than gene-level mechanism roles.
- **Ancestry-stratified evaluation** on cohorts with resolved continuous ancestry — the question
  this project actually needs answered.
- **A driver-oriented baseline** — CHASMplus, boostDM, or IntOGen's own per-variant driver scores —
  so "does a pathogenicity predictor underperform a driver predictor?" is measured, not assumed.
- **A pre-registered held-out set** of functionally validated GoF vs LoF variants, with a power
  analysis done before looking.
- **Rare-variant coverage**, since the recurrent-hotspot restriction is the probe's biggest blind spot.

## 5 · What follows

Since the hypothesis failed, **nothing in Phase 2 needs re-scoping on the strength of this probe**,
and none was done. Two things nonetheless remain true and are captured in decision **D-008**:

- AlphaMissense is a **pathogenicity** predictor being used to inform **driver** reclassification.
  The probe found no class-level penalty for that, but it also did not validate the equivalence —
  it only failed to find a difference on recurrent hotspots.
- The consensus rule already requires **≥2 concurring tools** (`min_agree: 2`), so no single
  AlphaMissense call reclassifies anything on its own. H1047R would remain VUS regardless.

Options and a recommendation are in **D-008**. The choice is a domain-model question and is
**not the coding agent's to make**; it is also raised for the professor as questionnaire **A10**.
