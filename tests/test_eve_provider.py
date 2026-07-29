"""EVE provider + identifier-seam extension (SPEC-005 part 2 of 4, SPEC-027).

Runs against REAL published EVE data held in a LOCAL, GITIGNORED cache -- no EVE
data is committed (licence provenance OPEN under D3; docs/eve-data.md).

Cache absent => the data-dependent tests SKIP with a populate instruction. They
never silently pass and never fabricate a score. The tests that do NOT need the
cache (vocabulary normalization, seam shape, refusal behaviour, config
transcription) always run.

Supported: python tests/test_eve_provider.py  (direct execution is the supported,
CI-enforced path; pytest compatibility is UNVERIFIED -- SPEC-016)
"""
import collections
import csv
import json
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from contracts.identifiers import (
    IdentifierMap, IdentifierNotFound, VariantIdentifiers, load_identifier_map,
)
from contracts.variant_effect import (
    VariantInput, BENIGN, PATHOGENIC, UNCERTAIN,
)
from producers.variant_effect.eve import (
    EveConfig, EveScoreCache, EveCacheMissing, EveScoreNotFound,
    build_tool_call, normalize_eve_class, to_eve_protein_variant,
    COVERAGE_GENE_ABSENT, COVERAGE_UNSCORED, COVERAGE_NOT_MISSENSE,
)
from producers.variant_effect.providers import EVEProvider
from producers.variant_effect.reclassify import reclassify

FIX = os.path.join(ROOT, "fixtures", "variant_effect")
CACHE = os.path.join(ROOT, ".cache", "eve", "scores.json")
IDENTIFIERS = os.path.join(FIX, "identifiers.json")
EXPECTED = os.path.join(FIX, "eve_expected.json")
EVE_CFG = os.path.join(ROOT, "config", "eve.json")
CFG = os.path.join(ROOT, "config", "variant_effect.json")
CAL = os.path.join(ROOT, "config", "calibration.json")

SKIP_MSG = (
    "SKIP (no EVE cache) -- this test needs REAL published EVE data, which is NOT\n"
    "      committed (licence provenance OPEN under D3).\n"
    "      Populate locally:  python tools/eve/fetch_scores.py\n"
    "      Details:           docs/eve-data.md"
)


class Skip(Exception):
    """Raised to skip a cache-dependent test. Loud, never a silent pass."""


def load_all():
    with open(EXPECTED, encoding="utf-8") as f:
        blob = json.load(f)
    return {**blob["expected"], **blob["controls"]}


def variant_for(vid, e):
    return VariantInput(variant_id=vid, gene=e["gene"], protein_change=e["protein_change"],
                        population="AA", reference="grch38")


def make_provider():
    try:
        cache = EveScoreCache(CACHE)
    except EveCacheMissing:
        raise Skip(SKIP_MSG)
    return EVEProvider(cache=cache,
                       identifiers=load_identifier_map(IDENTIFIERS),
                       config=EveConfig(EVE_CFG)), cache


# --- always run: no cache needed ---------------------------------------------

def test_eve_vocabulary_normalizes_and_is_not_privileged():
    """EVE is a THIRD published vocabulary in this repo, after AlphaMissense's
    two. Each tool normalizes its own labels; none is hardcoded as 'the' one."""
    assert normalize_eve_class("Benign") == BENIGN
    assert normalize_eve_class("Pathogenic") == PATHOGENIC
    assert normalize_eve_class("Uncertain") == UNCERTAIN
    assert normalize_eve_class("  pathogenic ") == PATHOGENIC          # case/space tolerant
    # AlphaMissense's labels are NOT silently accepted here -- different tool,
    # different published vocabulary; a cross-contaminated label must be loud.
    for foreign in ("likely_benign", "likely_pathogenic", "ambiguous", "VUS", ""):
        try:
            normalize_eve_class(foreign)
        except ValueError as e:
            assert "Unrecognised EVE class" in str(e)
        else:
            raise AssertionError(f"expected ValueError for EVE class {foreign!r}")


def test_service_of_origin_is_recorded_on_the_tool_call():
    call = build_tool_call({"eve_class": "Pathogenic", "eve_score": 0.9},
                           source="evemodel.org API (test)")
    assert call.tool == "eve" and call.call == PATHOGENIC
    assert call.source == "evemodel.org API (test)"


def test_missense_only_coverage_is_recognised():
    assert to_eve_protein_variant("p.R175H") == "R175H"
    assert to_eve_protein_variant("R175H") == "R175H"
    for non_missense in ("p.R1450*", "p.E1309fs", "p.G659fs", "", "p.?"):
        assert to_eve_protein_variant(non_missense) is None, non_missense


def test_identifier_seam_extension_is_additive():
    """SPEC-027: EVE keys on the UniProt ENTRY NAME, AlphaMissense on the
    ACCESSION. Both live on the seam; VariantInput is still untouched."""
    fields = set(VariantIdentifiers.__dataclass_fields__)
    assert {"uniprot_id", "uniprot_entry_name"} <= fields, fields
    # the analysis contract did NOT grow identifier plumbing
    vfields = set(VariantInput.__dataclass_fields__)
    for leaked in ("uniprot_id", "uniprot_entry_name", "transcript_id", "chrom"):
        assert leaked not in vfields, f"{leaked} leaked onto VariantInput"
    # asking for the identifier a tool needs, when absent, is a named refusal
    partial = IdentifierMap(entries={"v01": VariantIdentifiers(variant_id="v01",
                                                              uniprot_id="P04637")})
    try:
        partial.get("v01").require("uniprot_entry_name")
    except IdentifierNotFound as e:
        assert "uniprot_entry_name" in str(e)
    else:
        raise AssertionError("expected IdentifierNotFound for the absent entry name")


def test_identifier_fixture_carries_entry_names_for_every_variant():
    imap = load_identifier_map(IDENTIFIERS)
    for vid in load_all():
        assert vid in imap, vid
        assert imap.get(vid).require("uniprot_entry_name")
        assert imap.get(vid).require("uniprot_id")          # AlphaMissense's key still there


def test_published_class_assignment_is_transcribed_not_authored():
    """I3: the scheme is EVE's own, awaiting domain sign-off."""
    cfg = EveConfig(EVE_CFG)
    assert not cfg.is_signed_off(), "config must not claim sign-off nobody gave"
    assert cfg.retained["column"] == "EVE_classes_75_pct_retained_ASM"
    assert set(cfg.retained["classes"]) == {"Benign", "Uncertain", "Pathogenic"}
    assert "evemodel.org" in cfg.source
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cfg.warn_if_unsigned()
    assert any("AWAITING_SIGN_OFF" in str(w.message) for w in caught)


def test_fixture_has_discriminating_power():
    """AUDIT F10 CLASS: a constant-output stub must fail whatever it returns."""
    scored = [e for e in load_all().values() if e["coverage"] == "scored"]
    calls = [e["expected_call"] for e in scored]
    dist = collections.Counter(calls)
    assert set(dist) == {PATHOGENIC, BENIGN, UNCERTAIN}, dict(dist)
    top = dist.most_common(1)[0]
    assert top[1] / len(calls) <= 0.70, f"{top[0]} is {100*top[1]/len(calls):.0f}% of expectations"
    for constant in (PATHOGENIC, BENIGN, UNCERTAIN):
        wrong = sum(1 for c in calls if c != constant)
        assert wrong > len(calls) / 2, \
            f"a stub always returning {constant!r} would fail only {wrong}/{len(calls)}"


# --- cache-dependent: SKIP loudly if the cache is absent ----------------------

def test_golden_real_eve_data_produces_expected_calls():
    provider, cache = make_provider()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for vid, e in sorted(load_all().items()):
            call = provider.score(variant_for(vid, e))
            if e["coverage"] == "none":
                assert call is None, f"{vid}: expected no coverage, got {call}"
                continue
            assert call is not None, f"{vid}: expected a real EVE call, got None"
            assert call.call == e["expected_call"], (vid, e["key"], call.call, e["expected_call"])
            assert call.tool == "eve"
            assert call.raw_score is not None, f"{vid}: real score must be carried"
            assert call.source == cache.source, f"{vid}: service of origin not recorded"


def test_three_no_coverage_states_are_distinguished():
    """Not all absences are the same, and none of them is a guess."""
    _, cache = make_provider()
    assert cache.coverage_state("FBXW7_HUMAN", "R465C") == COVERAGE_GENE_ABSENT
    assert cache.coverage_state("RNF43_HUMAN", "T714A") == COVERAGE_GENE_ABSENT
    assert cache.coverage_state("BRAF_HUMAN", "I326V") == COVERAGE_UNSCORED
    assert cache.coverage_state("P53_HUMAN", None) == COVERAGE_NOT_MISSENSE
    assert cache.coverage_state("P53_HUMAN", "R175H") is None      # genuinely covered


def test_provider_raises_when_a_key_is_absent_never_guesses():
    _, cache = make_provider()
    try:
        cache.lookup("P53_HUMAN", "W999Y")
    except EveScoreNotFound as e:
        assert "P53_HUMAN/W999Y" in str(e) and "does not guess" in str(e)
    else:
        raise AssertionError("expected EveScoreNotFound, not a default call")


def test_calibration_pending_holds_on_real_eve_results():
    """EVE is an evolutionary model with no per-population calibration either.
    Real data changes nothing: every result stays calibration_pending."""
    provider, _ = make_provider()
    variants = [variant_for(vid, e) for vid, e in sorted(load_all().items())
                if e["coverage"] == "scored"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = reclassify(variants, [provider], CFG, CAL, strict=False)
    assert result.records
    assert all(r["calibration_pending"] for r in result.records)
    assert all(r["calibration_status"] == "calibration_pending" for r in result.records)
    for r in result.records:
        for tc in r["tool_calls"]:
            assert tc["source"], f"{r['variant_id']}: tool call lost its source"


def test_eve_class_vs_its_own_shipped_clinvar_is_recorded_not_resolved():
    """EVE ships ClinVar_ClinicalSignificance alongside each prediction. Where
    its own class disagrees with that record, we RECORD it -- the provider must
    not use ClinVar to adjust or override a call."""
    provider, _ = make_provider()
    disagreements = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for vid, e in sorted(load_all().items()):
            cv = e.get("eve_shipped_clinvar")
            if e["coverage"] != "scored" or not cv:
                continue
            call = provider.score(variant_for(vid, e))
            cv_low = cv.lower()
            cv_call = ("pathogenic" if cv_low.startswith("pathogenic")
                       else "benign" if cv_low.startswith("benign") else None)
            if cv_call and call.call != cv_call:
                disagreements.append((vid, e["gene"], e["protein_change"], call.call, cv))
    # the disagreements are a finding, not a failure -- assert they are present
    # and that the call is EVE's own, never ClinVar's
    assert disagreements, "expected at least one EVE-vs-shipped-ClinVar disagreement"
    for vid, gene, pc, eve_call, cv in disagreements:
        e = load_all()[vid]
        assert eve_call == e["expected_call"], \
            f"{vid}: call must be EVE's own ({e['expected_call']}), not ClinVar's ({cv})"


if __name__ == "__main__":
    _required = os.environ.get("EVE_CACHE_REQUIRED", "").strip().lower() in ("1", "true", "yes")
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
        print("ALL EVE TESTS PASSED")
    else:
        print(f"\n{len(_skipped)} data-dependent test(s) SKIPPED because the EVE cache is "
              "not populated:")
        for _n in _skipped:
            print(f"  - {_n}")
        print("\nThe cache-free tests above DID run and DID gate: EVE vocabulary "
              "normalization,\nthe additive seam extension, identifier refusals, config "
              "transcription, and\nfixture discriminating power. What is NOT proven without "
              "the cache: that real\npublished EVE data produces the expected calls. This is "
              "INCOMPLETE COVERAGE, not a pass.")
        print("Populate:  python tools/eve/fetch_scores.py")
        print("Enforce:   set EVE_CACHE_REQUIRED=1 to make a skip a failure.")
        if _required:
            print("\nEVE_CACHE_REQUIRED=1 -> treating skips as FAILURE.")
            raise SystemExit(1)
        print("EVE TESTS INCOMPLETE (cache absent)")
