"""AlphaMissense provider + identifier seam (SPEC-005 partial, SPEC-027).

Runs against REAL published AlphaMissense scores held in a LOCAL, GITIGNORED
cache -- no score data is committed (CC BY-NC-SA 4.0; docs/alphamissense-data.md).

Cache absent => the score-dependent tests SKIP with a populate instruction. They
never silently pass and never fabricate a score. The tests that do NOT need the
cache (vocabulary normalization, contract shape, refusal behaviour) always run.

Supported: python tests/test_alphamissense_provider.py  (direct execution is the
supported, CI-enforced path; pytest compatibility is UNVERIFIED -- never executed
end-to-end in this environment, SPEC-016)
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
    VariantInput, ToolCall, BENIGN, PATHOGENIC, UNCERTAIN,
)
from producers.variant_effect.alphamissense import (
    AlphaMissenseConfig, AlphaMissenseScoreCache, ScoreCacheMissing, ScoreNotFound,
    build_tool_call, normalize_am_class, to_am_protein_variant,
)
from producers.variant_effect.providers import AlphaMissenseProvider
from producers.variant_effect.reclassify import reclassify

FIX = os.path.join(ROOT, "fixtures", "variant_effect")
CACHE = os.path.join(ROOT, ".cache", "alphamissense", "scores.json")
IDENTIFIERS = os.path.join(FIX, "identifiers.json")
EXPECTED = os.path.join(FIX, "alphamissense_expected.json")
VARIANTS = os.path.join(FIX, "variants_input.csv")
AM_CFG = os.path.join(ROOT, "config", "alphamissense.json")
CFG = os.path.join(ROOT, "config", "variant_effect.json")
CAL = os.path.join(ROOT, "config", "calibration.json")

SKIP_MSG = (
    "SKIP (no AlphaMissense cache) -- this test needs REAL published scores, which "
    "are NOT committed (CC BY-NC-SA 4.0).\n"
    "      Populate locally:  python tools/alphamissense/fetch_scores.py\n"
    "      Details:           docs/alphamissense-data.md"
)


class Skip(Exception):
    """Raised to skip a cache-dependent test. Loud, never a silent pass."""


def load_expected():
    """Golden entries drawn from the producer's variants_input.csv (v* ids)."""
    with open(EXPECTED, encoding="utf-8") as f:
        return json.load(f)["expected"]


def load_controls():
    """Benign / ambiguous controls (c* ids). NOT in variants_input.csv -- that is
    the golden producer fixture and its expected_output.json pins n=20 (G4)."""
    with open(EXPECTED, encoding="utf-8") as f:
        return json.load(f).get("controls", {})


def control_variants():
    """VariantInputs for the controls, built from the fixture itself."""
    return [VariantInput(variant_id=vid, gene=e["gene"], protein_change=e["protein_change"],
                         population="AA", reference="grch38")
            for vid, e in sorted(load_controls().items())]


def load_variants():
    out = []
    with open(VARIANTS, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(VariantInput(
                variant_id=row["variant_id"], gene=row["gene"],
                protein_change=row["protein_change"], population=row["population"],
                reference=row["reference"], original_classification=row["original_classification"],
                clinical_db_absent=row["clinical_db_absent"].strip().lower() == "true"))
    return out


def make_provider():
    """Build the provider against the real cache, or raise Skip."""
    try:
        cache = AlphaMissenseScoreCache(CACHE)
    except ScoreCacheMissing:
        raise Skip(SKIP_MSG)
    return AlphaMissenseProvider(
        cache=cache,
        identifiers=load_identifier_map(IDENTIFIERS),
        config=AlphaMissenseConfig(AM_CFG),
    ), cache


# --- always run: no cache needed ---------------------------------------------

def test_both_published_vocabularies_normalize_identically():
    """REGRESSION (decision D-006): AlphaMissense ships TWO class vocabularies for
    the SAME thresholds -- AlphaMissense_hg38.tsv.gz says likely_benign /
    likely_pathogenic, AlphaMissense_aa_substitutions.tsv.gz says benign /
    pathogenic. Verified against the real files. Neither is hardcoded: both must
    normalize to the same call, so switching source files can never silently
    change what a call means."""
    assert normalize_am_class("likely_benign") == normalize_am_class("benign") == BENIGN
    assert normalize_am_class("likely_pathogenic") == normalize_am_class("pathogenic") == PATHOGENIC
    assert normalize_am_class("ambiguous") == UNCERTAIN
    # case/whitespace tolerance, since these come out of a TSV
    assert normalize_am_class("  Likely_Pathogenic ") == PATHOGENIC
    # an unknown label must RAISE, never be coerced into a call
    for bad in ("likely_ambiguous", "VUS", "", "pathogenic_high"):
        try:
            normalize_am_class(bad)
        except ValueError as e:
            assert "Unrecognised AlphaMissense am_class" in str(e)
        else:
            raise AssertionError(f"expected ValueError for am_class {bad!r}")


def test_file_of_origin_is_recorded_on_the_tool_call():
    """A file switch must be VISIBLE in provenance, not silent (D-006)."""
    call = build_tool_call({"am_class": "pathogenic", "am_pathogenicity": 0.99},
                           source="AlphaMissense_aa_substitutions.tsv.gz (test)")
    assert call.source == "AlphaMissense_aa_substitutions.tsv.gz (test)"
    assert call.tool == "alphamissense" and call.call == PATHOGENIC
    # the same score under the OTHER vocabulary yields the same call, different origin
    other = build_tool_call({"am_class": "likely_pathogenic", "am_pathogenicity": 0.99},
                            source="AlphaMissense_hg38.tsv.gz (test)")
    assert other.call == call.call
    assert other.source != call.source


def test_missense_only_coverage_is_recognised():
    """Nonsense/frameshift are outside AlphaMissense's domain BY CONSTRUCTION."""
    assert to_am_protein_variant("p.G12D") == "G12D"
    assert to_am_protein_variant("G12D") == "G12D"
    assert to_am_protein_variant("p.H1047R") == "H1047R"
    for non_missense in ("p.R1450*", "p.E1309fs", "p.T1556fs", "p.Q1367*", "", "p.?"):
        assert to_am_protein_variant(non_missense) is None, non_missense


def test_variant_input_contract_is_unchanged():
    """SPEC-027 / D-006 option (c): identifiers live in their OWN seam. The
    analysis contract must not have accumulated identifier plumbing."""
    fields = set(VariantInput.__dataclass_fields__)
    assert fields == {"variant_id", "gene", "protein_change", "population",
                      "reference", "original_classification", "clinical_db_absent"}, fields
    for leaked in ("uniprot_id", "transcript_id", "chrom", "pos", "ref_allele", "alt_allele"):
        assert leaked not in fields, f"{leaked} leaked onto VariantInput"


def test_identifier_miss_refuses_by_name():
    """A producer never invents an identifier: a miss is a named refusal."""
    empty = IdentifierMap(entries={}, source="test map")
    try:
        empty.get("v99")
    except IdentifierNotFound as e:
        assert "v99" in str(e) and "never invents" in str(e)
    else:
        raise AssertionError("expected IdentifierNotFound")

    # present in the map but missing the field we need -> still a refusal
    partial = IdentifierMap(entries={"v01": VariantIdentifiers(variant_id="v01")})
    try:
        partial.get("v01").require("uniprot_id")
    except IdentifierNotFound as e:
        assert "uniprot_id" in str(e)
    else:
        raise AssertionError("expected IdentifierNotFound for the absent field")


def test_identifier_fixture_covers_every_golden_variant():
    imap = load_identifier_map(IDENTIFIERS)
    for v in load_variants():
        assert v.variant_id in imap, v.variant_id
        assert imap.get(v.variant_id).require("uniprot_id")
        assert imap.get(v.variant_id).source, f"{v.variant_id} has no source citation"


def test_published_cutoffs_are_transcribed_not_authored():
    """I3: the cutoffs are AlphaMissense's own, awaiting domain sign-off."""
    cfg = AlphaMissenseConfig(AM_CFG)
    assert not cfg.is_signed_off(), "config must not claim sign-off nobody gave"
    assert cfg.cutoffs["benign_below"] == 0.34
    assert cfg.cutoffs["pathogenic_above"] == 0.564
    assert "zenodo" in cfg.source.lower()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cfg.warn_if_unsigned()
    assert any("AWAITING_SIGN_OFF" in str(w.message) for w in caught), \
        "an unsigned config must warn"


# --- cache-dependent: SKIP loudly if the cache is absent ----------------------

def test_fixture_has_discriminating_power():
    """AUDIT F10 CLASS: a fixture whose expectations are nearly all one value
    cannot detect a constant-output stub. Before controls were added, 14 of 15
    covered entries expected 'pathogenic' -- a stub returning 'pathogenic'
    unconditionally scored 14/15. Enforce a genuine mix so that can never
    silently return: no single expected call may exceed 70% of scored entries,
    and every call the provider can emit must appear."""
    scored = [e for e in {**load_expected(), **load_controls()}.values()
              if e["coverage"] == "scored"]
    calls = [e["expected_call"] for e in scored]
    dist = collections.Counter(calls)
    assert set(dist) == {PATHOGENIC, BENIGN, UNCERTAIN}, \
        f"every possible call must be represented; got {dict(dist)}"
    top = dist.most_common(1)[0]
    assert top[1] / len(calls) <= 0.70, \
        f"'{top[0]}' is {100*top[1]/len(calls):.0f}% of expectations -- a constant stub would mostly pass"
    # a constant-output stub must be wrong on a majority of entries, whatever it returns
    for constant in (PATHOGENIC, BENIGN, UNCERTAIN):
        wrong = sum(1 for c in calls if c != constant)
        assert wrong > len(calls) / 2, \
            f"a stub always returning {constant!r} would fail only {wrong}/{len(calls)}"


def test_golden_real_scores_produce_expected_calls():
    provider, cache = make_provider()
    expected = load_expected()
    variants = {v.variant_id: v for v in load_variants()}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for vid, exp in sorted(expected.items()):
            call = provider.score(variants[vid])
            if exp["coverage"] == "none":
                assert call is None, f"{vid}: expected no coverage, got {call}"
                continue
            assert call is not None, f"{vid}: expected a real score, got None"
            assert call.call == exp["expected_call"], (vid, call.call, exp["expected_call"])
            assert call.tool == "alphamissense"
            assert call.raw_score is not None, f"{vid}: real score must be carried"
            assert call.source == cache.source, f"{vid}: file of origin not recorded"


def test_benign_and_ambiguous_controls_produce_expected_calls():
    """The controls carry the discriminating power: real ClinVar Benign /
    Likely-benign variants that AlphaMissense also scores below the benign
    cut-point, plus recurrent somatic hotspots that land inside the ambiguous
    band. A provider that cannot distinguish these is broken even if every
    pathogenic expectation passes."""
    provider, _ = make_provider()
    controls = load_controls()
    assert controls, "controls block missing from the fixture"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for v in control_variants():
            exp = controls[v.variant_id]
            call = provider.score(v)
            assert call is not None, f"{v.variant_id}: expected a real score, got None"
            assert call.call == exp["expected_call"], \
                (v.variant_id, exp["key"], call.call, exp["expected_call"])
            assert call.raw_score is not None
    # every benign control must actually sit below the published cut-point,
    # and every ambiguous control inside the band -- not merely be labelled so
    cutoffs = AlphaMissenseConfig(AM_CFG).cutoffs
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for v in control_variants():
            exp, call = controls[v.variant_id], provider.score(v)
            if exp["expected_call"] == BENIGN:
                assert call.raw_score < cutoffs["benign_below"], (v.variant_id, call.raw_score)
            elif exp["expected_call"] == UNCERTAIN:
                assert cutoffs["benign_below"] <= call.raw_score <= cutoffs["pathogenic_above"], \
                    (v.variant_id, call.raw_score)


def test_provider_raises_when_a_score_is_absent_never_guesses():
    provider, _ = make_provider()
    ghost = VariantInput(variant_id="v02", gene="KRAS", protein_change="p.W99Y",
                         population="AA", reference="grch38")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            provider.score(ghost)
        except ScoreNotFound as e:
            assert "P01116/W99Y" in str(e)
            assert "does not guess" in str(e)
        else:
            raise AssertionError("expected ScoreNotFound, not a default call")


def test_calibration_pending_holds_on_real_scored_results():
    """The point of the whole exercise: AlphaMissense is European-calibrated and
    per-population targets are [TO BE DEFINED] (DEFINITIONS.md sec 3). Real scores
    change NOTHING about that -- every result stays calibration_pending."""
    provider, _ = make_provider()
    variants = [v for v in load_variants()
                if to_am_protein_variant(v.protein_change) is not None]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = reclassify(variants, [provider], CFG, CAL, strict=False)

    assert result.records, "expected real-scored records"
    assert all(r["calibration_pending"] for r in result.records)
    assert all(r["calibration_status"] == "calibration_pending" for r in result.records)
    # and the file of origin survives into the stored provenance payload
    for r in result.records:
        for tc in r["tool_calls"]:
            assert tc["source"], f"{r['variant_id']}: tool call lost its source"
    # per-population coverage is intact -- no population silently dropped
    assert {p for p in result.summary["per_population"]} == {"AA", "ETH", "GHA", "NHW"}


def test_pangenome_variants_resolve_without_spec_004():
    """D-006's reason for choosing the (uniprot_id, protein_variant) key: it
    carries no genomic coordinates, so pangenome-called variants resolve without
    GRCh38 reference reconciliation."""
    provider, _ = make_provider()
    pangenome = [v for v in load_variants()
                 if v.reference == "pangenome" and to_am_protein_variant(v.protein_change)]
    assert pangenome, "fixture should contain pangenome missense variants"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for v in pangenome:
            assert provider.score(v) is not None, v.variant_id


if __name__ == "__main__":
    # Opt-in strictness: with ALPHAMISSENSE_CACHE_REQUIRED=1 a skip becomes a
    # FAILURE. Off by default because CI has no cache (the data cannot be
    # committed -- CC BY-NC-SA 4.0), on for anyone who has fetched locally and
    # wants the full gate. Whether CI should fetch is a D2/D3 question and is
    # deliberately left to the owner, not decided here.
    _required = os.environ.get("ALPHAMISSENSE_CACHE_REQUIRED", "").strip().lower() \
        in ("1", "true", "yes")
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
        print("ALL ALPHAMISSENSE TESTS PASSED")
    else:
        print(f"\n{len(_skipped)} of the score-dependent test(s) SKIPPED because the "
              "AlphaMissense cache is not populated:")
        for _n in _skipped:
            print(f"  - {_n}")
        print("\nThe cache-free tests above DID run and DID gate: vocabulary "
              "normalization,\nthe VariantInput contract shape, identifier refusals, and "
              "cutoff transcription.\nWhat is NOT proven without the cache: that real "
              "published scores produce the\nexpected calls. This is INCOMPLETE COVERAGE, "
              "not a pass.")
        print("Populate:  python tools/alphamissense/fetch_scores.py")
        print("Enforce:   set ALPHAMISSENSE_CACHE_REQUIRED=1 to make a skip a failure.")
        if _required:
            print("\nALPHAMISSENSE_CACHE_REQUIRED=1 -> treating skips as FAILURE.")
            raise SystemExit(1)
        print("ALPHAMISSENSE TESTS INCOMPLETE (cache absent)")
