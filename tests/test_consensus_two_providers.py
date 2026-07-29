"""Consensus payoff with TWO wired providers (SPEC-005, 2 of 4).

This is the measurement slice: AlphaMissense alone could reclassify nothing,
because `min_agree: 2` makes consensus unreachable with a single caller. EVE is
the second independent signal, so this is where Phase 2's headline number first
moves.

It lives in tests/ rather than tools/ deliberately: it must import
`producers/`, and ARCHITECTURE.md sec 5 forbids tools/ from doing that. Being a
suite also means the numbers are gated in CI rather than asserted in prose.

The consensus engine, `min_agree`, calibration and provenance are UNTOUCHED --
this measures the existing rule, it does not change it.

Run directly to print the full report:
    python tests/test_consensus_two_providers.py

Needs BOTH caches. Absent => SKIP with populate instructions, reported as
INCOMPLETE. Never a silent pass.
"""
import collections
import json
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from contracts.identifiers import load_identifier_map
from contracts.variant_effect import VariantInput, CLS_VUS
from producers.variant_effect.alphamissense import (
    AlphaMissenseConfig, AlphaMissenseScoreCache, ScoreCacheMissing,
)
from producers.variant_effect.eve import EveConfig, EveScoreCache, EveCacheMissing
from producers.variant_effect.providers import AlphaMissenseProvider, EVEProvider
from producers.variant_effect.reclassify import reclassify

FIX = os.path.join(ROOT, "fixtures", "variant_effect")
IDENTIFIERS = os.path.join(FIX, "identifiers.json")
AM_EXPECTED = os.path.join(FIX, "alphamissense_expected.json")
EVE_EXPECTED = os.path.join(FIX, "eve_expected.json")
AM_CACHE = os.path.join(ROOT, ".cache", "alphamissense", "scores.json")
EVE_CACHE = os.path.join(ROOT, ".cache", "eve", "scores.json")
CFG = os.path.join(ROOT, "config", "variant_effect.json")
CAL = os.path.join(ROOT, "config", "calibration.json")
AM_CFG = os.path.join(ROOT, "config", "alphamissense.json")
EVE_CFG = os.path.join(ROOT, "config", "eve.json")

SKIP_MSG = (
    "SKIP -- needs BOTH real caches; neither tool's data is committed.\n"
    "      python tools/alphamissense/fetch_scores.py\n"
    "      python tools/eve/fetch_scores.py"
)


class Skip(Exception):
    """Loud skip. Never a silent pass."""


def _golden():
    """The 20 golden-fixture variants, as the producer sees them."""
    import csv
    out = []
    with open(os.path.join(FIX, "variants_input.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(VariantInput(
                variant_id=row["variant_id"], gene=row["gene"],
                protein_change=row["protein_change"], population=row["population"],
                reference=row["reference"],
                original_classification=row["original_classification"],
                clinical_db_absent=row["clinical_db_absent"].strip().lower() == "true"))
    return out


def _providers():
    try:
        am = AlphaMissenseScoreCache(AM_CACHE)
        eve = EveScoreCache(EVE_CACHE)
    except (ScoreCacheMissing, EveCacheMissing):
        raise Skip(SKIP_MSG)
    imap = load_identifier_map(IDENTIFIERS)
    return [AlphaMissenseProvider(am, imap, AlphaMissenseConfig(AM_CFG)),
            EVEProvider(eve, imap, EveConfig(EVE_CFG))]


def measure():
    """Run the real consensus over the golden fixture with both providers."""
    variants = _golden()
    provs = _providers()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        per_tool = {v.variant_id: {p.tool: p.score(v) for p in provs} for v in variants}
        result = reclassify(variants, provs, CFG, CAL, strict=False)
    by_id = {r["variant_id"]: r for r in result.records}
    return variants, per_tool, by_id, result


def _call(tc):
    return tc.call if tc is not None else None


# --- the measurement, as assertions -------------------------------------------

def test_two_providers_move_the_vus_number():
    variants, per_tool, by_id, result = measure()
    n = len(variants)
    after = sum(1 for r in by_id.values() if r["new_classification"] == CLS_VUS)
    reclassified = n - after
    # every golden variant starts as VUS
    assert all(v.original_classification == CLS_VUS for v in variants)
    # with two independent callers, consensus becomes reachable at all
    assert reclassified > 0, "two providers should reclassify at least one variant"
    # and the summary the producer emits agrees with the row-level counts
    assert result.summary["overall"]["n"] == n
    assert result.summary["overall"]["vus_after"] == after


def test_single_provider_still_reclassifies_nothing():
    """The premise of this slice, asserted rather than asserted-in-prose:
    min_agree=2 makes consensus unreachable with one caller."""
    variants = _golden()
    provs = _providers()
    for p in provs:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = reclassify(variants, [p], CFG, CAL, strict=False)
        assert all(r["new_classification"] == CLS_VUS for r in res.records), \
            f"{p.tool} alone must not reach consensus at min_agree=2"


def test_disagreements_are_surfaced_not_averaged():
    """Where the two tools diverge, the rule must leave the variant VUS rather
    than picking a winner. That is the whole point of a consensus rule."""
    variants, per_tool, by_id, _ = measure()
    for v in variants:
        am, eve = _call(per_tool[v.variant_id]["alphamissense"]), _call(per_tool[v.variant_id]["eve"])
        if am and eve and am != eve:
            assert by_id[v.variant_id]["new_classification"] == CLS_VUS, \
                f"{v.variant_id}: tools disagree ({am} vs {eve}) but was reclassified"


def test_calibration_pending_survives_two_providers():
    _, _, by_id, result = measure()
    assert all(r["calibration_pending"] for r in by_id.values())
    assert all(r["calibration_status"] == "calibration_pending" for r in by_id.values())
    for r in by_id.values():
        for tc in r["tool_calls"]:
            assert tc["source"], f"{r['variant_id']}: tool call lost its source"


def test_h1047r_is_not_rescued_by_the_second_tool():
    """Bears on D-008: AlphaMissense called PIK3CA H1047R uncertain; EVE calls it
    BENIGN. A second independent signal moves it further from pathogenic, not
    closer. Recorded as a fact, not treated as a defect."""
    _, per_tool, by_id, _ = measure()
    am, eve = _call(per_tool["v14"]["alphamissense"]), _call(per_tool["v14"]["eve"])
    assert am == "uncertain", am
    assert eve == "benign", eve
    assert by_id["v14"]["new_classification"] == CLS_VUS


# --- report -------------------------------------------------------------------

def report():
    variants, per_tool, by_id, result = measure()
    n = len(variants)
    after = sum(1 for r in by_id.values() if r["new_classification"] == CLS_VUS)

    print("=" * 78)
    print("CONSENSUS PAYOFF -- two providers, golden fixture, min_agree=2 (unchanged)")
    print("=" * 78)
    print(f"{'id':<5}{'gene':<8}{'change':<12}{'AlphaMissense':<15}{'EVE':<12}{'consensus'}")
    print("-" * 78)
    for v in variants:
        am, eve = _call(per_tool[v.variant_id]["alphamissense"]), _call(per_tool[v.variant_id]["eve"])
        print(f"{v.variant_id:<5}{v.gene:<8}{v.protein_change:<12}"
              f"{str(am or '-- no coverage'):<15}{str(eve or '-- none'):<12}"
              f"{by_id[v.variant_id]['new_classification']}")
    print("-" * 78)
    print(f"VUS before: {n}/{n} (100.0%)    VUS after: {after}/{n} ({100*after/n:.1f}%)    "
          f"reclassified: {n - after}")
    print()

    print("--- DISAGREEMENTS (both tools called it, and they differ) ---")
    dis = []
    for v in variants:
        am, eve = _call(per_tool[v.variant_id]["alphamissense"]), _call(per_tool[v.variant_id]["eve"])
        if am and eve and am != eve:
            dis.append((v.variant_id, v.gene, v.protein_change, am, eve))
    print(f"{'id':<5}{'gene':<8}{'change':<12}{'AlphaMissense':<15}{'EVE':<12}")
    for d in dis:
        print(f"{d[0]:<5}{d[1]:<8}{d[2]:<12}{d[3]:<15}{d[4]:<12}")
    print(f"  {len(dis)} disagreement(s)")
    print()

    print("--- COVERAGE OVERLAP ---")
    both = one = neither = 0
    only = collections.Counter()
    for v in variants:
        am, eve = _call(per_tool[v.variant_id]["alphamissense"]), _call(per_tool[v.variant_id]["eve"])
        if am and eve:
            both += 1
        elif am or eve:
            one += 1
            only[("alphamissense" if am else "eve")] += 1
        else:
            neither += 1
    print(f"  scored by BOTH    : {both:>2}/{n}  (consensus is reachable)")
    print(f"  scored by ONE only: {one:>2}/{n}  (cannot reach min_agree=2) -> {dict(only)}")
    print(f"  scored by NEITHER : {neither:>2}/{n}")
    print()

    agree_path = sum(1 for v in variants
                     if _call(per_tool[v.variant_id]["alphamissense"]) == "pathogenic"
                     and _call(per_tool[v.variant_id]["eve"]) == "pathogenic")
    print("--- WHY THE REMAINING VUS ARE STILL VUS ---")
    print(f"  both agree pathogenic (reclassified) : {agree_path}")
    print(f"  tools DISAGREE (disagreement-limited): {len(dis)}")
    print(f"  only one tool covers it              : {one}")
    print(f"  neither tool covers it               : {neither}")
    print()


if __name__ == "__main__":
    _required = os.environ.get("CONSENSUS_CACHES_REQUIRED", "").strip().lower() in ("1", "true", "yes")
    _skipped = []
    for _name, _fn in list(globals().items()):
        if _name.startswith("test_"):
            try:
                _fn()
            except Skip as s:
                _skipped.append(_name)
                print(f"SKIP {_name}\n      {s}")
            else:
                print(f"PASS {_name}")
    if not _skipped:
        print()
        report()
        print("ALL CONSENSUS TESTS PASSED")
    else:
        print(f"\n{len(_skipped)} test(s) SKIPPED -- caches absent. This is INCOMPLETE "
              "COVERAGE, not a pass.")
        print("Enforce: set CONSENSUS_CACHES_REQUIRED=1 to make a skip a failure.")
        if _required:
            raise SystemExit(1)
        print("CONSENSUS TESTS INCOMPLETE (caches absent)")
