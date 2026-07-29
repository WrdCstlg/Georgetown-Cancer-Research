# Consensus payoff — two providers wired

> **Measured, not asserted.** Every number here comes from
> `python tests/test_consensus_two_providers.py`, which runs the real consensus engine over the
> golden fixture with both real providers and is gated in CI. **Run 2026-07-28.**
>
> The consensus engine, `min_agree`, calibration flagging and provenance are **untouched** —
> this measures the existing rule, it does not change it.

## Why this slice existed

AlphaMissense alone reduced VUS by **exactly zero**. That was not a defect: `min_agree: 2`
makes consensus unreachable with a single caller, so one wired provider can never reclassify
anything. EVE is the second independent signal that makes the rule function at all.

This is asserted, not just narrated — `test_single_provider_still_reclassifies_nothing` runs
each provider alone and requires that every variant stays VUS.

## 1 · The number moves

```
VUS before: 20/20 (100.0%)    VUS after: 13/20 (65.0%)    reclassified: 7
```

Seven variants reach `pathogenic`: SMAD4 R361H, CTNNB1 S45F, KRAS G12V, SMAD4 D351H,
TP53 Y220C, CTNNB1 T41A, BRAF V600E. In every case both tools independently called pathogenic.

That is the first real movement of Phase 2's headline number. It is also, deliberately, a
modest one — see §4.

## 2 · The disagreement table — the actual scientific output

More informative than the VUS number. Two independent signals, one **structural**
(AlphaMissense) and one **evolutionary** (EVE), diverging on the same variant is exactly what a
consensus rule exists to surface.

| Variant | Gene | AlphaMissense | EVE | Consensus |
|---|---|---|---|---|
| G12D | KRAS | pathogenic | *uncertain* | VUS |
| G13D | KRAS | pathogenic | *uncertain* | VUS |
| A146T | KRAS | pathogenic | *uncertain* | VUS |
| R175H | TP53 | pathogenic | *uncertain* | VUS |
| R248Q | TP53 | pathogenic | *uncertain* | VUS |
| E545K | PIK3CA | pathogenic | *uncertain* | VUS |
| **H1047R** | **PIK3CA** | *uncertain* | **benign** | VUS |

**7 disagreements.** Every one is a canonical recurrent somatic hotspot.

Six of the seven share a shape: AlphaMissense is confident, EVE declines to commit. Only
**H1047R** is a true contradiction — one tool leaning uncertain, the other actively calling it
benign.

`test_disagreements_are_surfaced_not_averaged` asserts that wherever the tools differ the
variant stays VUS. The rule never picks a winner, and nothing is averaged into a
false-confidence number.

## 3 · Coverage overlap

| | n / 20 | Consequence |
|---|---:|---|
| Scored by **both** tools | 14 | consensus is reachable |
| Scored by **one** only (AlphaMissense; FBXW7 R465C) | 1 | **cannot reach `min_agree: 2`** however good that call is |
| Scored by **neither** (nonsense/frameshift) | 5 | outside both models by construction |

The single-coverage case is decision **D-009**: EVE does not publish FBXW7 or RNF43. Coverage
asymmetry between tools silently converts into un-reclassifiable variants — a variant with one
excellent call and one absent tool is indistinguishable, to the rule, from a variant nothing
understands.

## 4 · Why the remaining 13 are still VUS

| Reason | n |
|---|---:|
| **The two tools disagree** | **7** |
| Neither tool covers it | 5 |
| Only one tool covers it | 1 |

**The residual VUS fraction is disagreement-limited, not coverage-limited.** That is the
finding of decision **D-010**, and it has a concrete planning consequence: adding the third and
fourth providers will **not** improve the number in proportion. With `min_agree: 2`, another
caller helps only where it breaks a tie. Where EVE is systematically "Uncertain" on hotspots, a
third tool agreeing with AlphaMissense resolves it; a third tool that also declines does not.

Phase 2's VUS-reduction target should be read against that, rather than against an assumption
that more tools monotonically reduce VUS.

**No recommendation is made here** about `min_agree`, tie-breaking, tool weighting, or whether
"Uncertain" should count as a vote against or as an abstention. Those are domain decisions. The
disagreement list above has been added verbatim to questionnaire **A8** so the domain owner
rules on real cases rather than an abstraction.

## 5 · PIK3CA H1047R specifically

Asked because it bears on **D-008**. The answer is the opposite of a rescue:

| Source | Call |
|---|---|
| AlphaMissense (structural / population constraint) | `uncertain` |
| **EVE (evolutionary)** | **`benign`** |
| ClinVar record **EVE itself ships** alongside its prediction | `Pathogenic` |

A second, methodologically independent model moves H1047R **further from** pathogenic, and EVE
disagrees with the very ClinVar annotation it distributes.

This does **not** revive the class-level hypothesis rejected in
[`alphamissense-driver-coverage.md`](alphamissense-driver-coverage.md) — that probe tested 178
hotspots and found no activating-vs-loss-of-function difference (p = 0.31 / 0.75), and that null
stands. It strengthens only the narrow, variant-level form of the concern, because the miss is
now reproduced across two models rather than being one tool's quirk. Recorded in D-008 as
evidence; the recommendation there is unchanged and remains the owner's call.

`test_h1047r_is_not_rescued_by_the_second_tool` pins this so a future data refresh that changes
it is loud rather than silent.

## 6 · A third axis: EVE vs the ClinVar it ships

EVE distributes `ClinVar_ClinicalSignificance` alongside each prediction. Comparing EVE's own
class to that record gives a third, free axis of disagreement — **recorded, not resolved**, and
never used to form or adjust a call:

| Variant | EVE class | ClinVar as shipped by EVE |
|---|---|---|
| KRAS G12D, G13D · TP53 R175H, R248Q · PIK3CA E545K | `Uncertain` | Pathogenic (or P/LP) |
| **PIK3CA H1047R** | **`benign`** | **Pathogenic** |
| TP53 L130V | `Pathogenic` | Uncertain significance |
| CTNNB1 T41A | `Pathogenic` | Conflicting interpretations |

Both directions occur, so this is not a simple conservatism bias in one tool.
`test_eve_class_vs_its_own_shipped_clinvar_is_recorded_not_resolved` asserts the disagreements
exist **and** that the emitted call is always EVE's own, never ClinVar's.

## 7 · What did not change

- `min_agree` is still `2`; the consensus engine, calibration flagging and provenance are untouched.
- Every result is still stamped `calibration_pending` — asserted with two providers wired
  (`test_calibration_pending_survives_two_providers`). Two European-centric models agreeing does
  not constitute per-population calibration, and the caveat does not weaken because two tools
  concur.
- **SPEC-005 remains SPECIFIED.** Two of four providers are wired; PolyPhen and SIFT still
  `raise NotImplementedError`.
- No EVE or AlphaMissense score data is committed.
