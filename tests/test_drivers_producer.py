"""drivers producer + multi-producer core (SPEC-028, SPEC-029).

Runs against REAL published IntOGen data held in a LOCAL, GITIGNORED cache.
IntOGen is CC0 so committing would be permitted; the cache pattern is a
deliberate consistency choice (D-013). Cache absent => the data-dependent tests
SKIP with a populate instruction, reported as INCOMPLETE. Never a silent pass.

Supported: python tests/test_drivers_producer.py  (direct execution is the
supported, CI-enforced path; pytest compatibility UNVERIFIED -- SPEC-016)
"""
import collections
import json
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from contracts.driver_evidence import (
    DriverEvidence, DriverEvidenceError, RESULT_TYPE, validate_evidence,
    EV_DOMAIN, EV_CLUSTER_2D, EV_CLUSTER_3D,
    NO_GENE_ROW, NO_POSITIONAL, NOT_MISSENSE,
)
from core.db import connect, apply_schema
from core.ingest.producer_result_ingest import (
    ingest_producer_results, read_producer_results, read_variants,
)
from producers.drivers.intogen import (
    IntogenCompendium, IntogenCacheMissing, IntogenConfig, DEFAULT_SCOPE,
    parse_2d_clusters, parse_3d_clusters, parse_domains, residue_of,
)
from producers.drivers.produce import produce, summarize, METHOD

FIX = os.path.join(ROOT, "fixtures")
SCHEMA = os.path.join(ROOT, "core", "schema", "schema.sql")
CACHE = os.path.join(ROOT, ".cache", "intogen", "compendium.json")
EXPECTED = os.path.join(FIX, "drivers", "intogen_expected.json")
SEED = os.path.join(FIX, "query", "core_rows.json")
INTOGEN_CFG = os.path.join(ROOT, "config", "intogen.json")

SKIP_MSG = (
    "SKIP (no IntOGen cache) -- this test needs REAL published data, which is not\n"
    "      committed (D-013: CC0 would permit it; consistency chosen instead).\n"
    "      Populate locally:  python tools/intogen/fetch_compendium.py")


class Skip(Exception):
    """Loud skip. Never a silent pass."""


def load_expected():
    """Golden variants PLUS the d-prefixed controls. The controls exercise the
    gene_not_a_driver_in_scope state, which the 20 golden variants never reach
    because all 20 sit in colorectal driver genes."""
    with open(EXPECTED, encoding="utf-8") as f:
        blob = json.load(f)
    return {**blob["expected"], **blob.get("controls", {})}


def compendium():
    try:
        return IntogenCompendium(CACHE)
    except IntogenCacheMissing:
        raise Skip(SKIP_MSG)


def seeded_core():
    """A throwaway in-memory core seeded from the frozen query fixture, so the
    producer reads a real core view rather than a hand-built list."""
    with open(SEED, encoding="utf-8") as f:
        seed = json.load(f)
    con = connect(":memory:")
    apply_schema(con, SCHEMA)
    for p in seed["populations"]:
        con.execute("INSERT INTO population(code, description) VALUES (?,?)",
                    (p["code"], p["description"]))
    for v in seed["variants"]:
        con.execute("INSERT INTO variant (variant_id, gene, protein_change, reference, "
                    "clinical_db_absent) VALUES (?,?,?,?,?)",
                    (v["variant_id"], v["gene"], v["protein_change"], v["reference"],
                     v["clinical_db_absent"]))
    for r in seed["results"]:
        con.execute(
            "INSERT INTO variant_effect_result (variant_id, original_classification, "
            "new_classification, producer, producer_version, method, n_tools_fired, reference, "
            "population_code, generated_at, calibration_status, calibration_pending, "
            "tool_calls_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["variant_id"], r["original_classification"], r["new_classification"],
             r["producer"], r["producer_version"], r["method"], 4, r["reference"],
             r["population_code"], r["generated_at"], r["calibration_status"],
             r["calibration_pending"], "[]"))
    con.commit()
    return con


# --- always run: no cache needed ---------------------------------------------

def test_producer_is_isolated():
    """ARCHITECTURE.md 4.2, asserted rather than trusted.

    Checked by parsing the AST, not by grepping text: these modules DISCUSS the
    forbidden imports in their docstrings (deliberately -- that is where the
    boundary is explained), so a textual search reports false violations. Only
    real import statements count.
    """
    import ast
    import producers.drivers.produce as prod
    import producers.drivers.intogen as intg

    for mod in (prod, intg):
        tree = ast.parse(open(mod.__file__, encoding="utf-8").read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        for name in imported:
            root = name.split(".")[0]
            assert root != "query", f"{mod.__name__} imports query/: {name}"
            assert root != "interface", f"{mod.__name__} imports interface/: {name}"
            if name.startswith("producers."):
                assert name.startswith("producers.drivers"), \
                    f"{mod.__name__} imports another producer: {name}"
        # a producer may depend on contracts + core, and on nothing else in-repo
        for name in imported:
            root = name.split(".")[0]
            assert root in ("contracts", "core", "producers", "__future__",
                            "json", "os", "re", "warnings", "datetime", "collections"), \
                f"{mod.__name__} has an unexpected dependency: {name}"


def test_producer_reads_the_neutral_view_not_variant_effects():
    """It must compose through the CORE, not through another producer's output.
    Asserted by what the read path actually queries."""
    import inspect
    from core.ingest import producer_result_ingest as pri
    src = inspect.getsource(pri.read_variants)
    assert "v_variant" in src and "v_variant_effect" not in src, src
    # and the producer's own entry point takes rows, issuing no SQL of its own
    import producers.drivers.produce as prod
    psrc = inspect.getsource(prod.produce)
    assert "SELECT" not in psrc.upper(), "the producer must not reach around the core view"


def test_positional_parsers_match_the_published_formats():
    assert parse_2d_clusters("1450:1450,213:216") == {213, 214, 215, 216, 1450}
    assert parse_3d_clusters("546,545,542") == {542, 545, 546}
    assert parse_domains("PF00001:120:123") == {120, 121, 122, 123}
    for empty in ("", None, "-"):
        assert parse_2d_clusters(empty) == set()
        assert parse_3d_clusters(empty) == set()
        assert parse_domains(empty) == set()
    assert residue_of("p.G12D") == 12 and residue_of("H1047R") == 1047
    for non_missense in ("p.R1450*", "p.E1309fs", "", "p.?"):
        assert residue_of(non_missense) is None


def test_contract_refuses_the_conflations_the_schema_no_longer_can():
    """D-012 moved payload enforcement from the DB to the contract. These are
    the checks that moved."""
    ok = DriverEvidence(variant_id="v1", gene="KRAS", residue=12, cohort_scope="COAD",
                        gene_is_driver_in_scope=True, evidence_kinds=(EV_CLUSTER_2D,),
                        supporting_cohorts=("X",))
    validate_evidence(ok)                                   # baseline: valid

    def refuses(ev, needle):
        try:
            validate_evidence(ev)
        except DriverEvidenceError as e:
            assert needle in str(e), (needle, str(e))
        else:
            raise AssertionError(f"expected refusal for {needle!r}")

    refuses(DriverEvidence("v1", "KRAS", 12, "", True, evidence_kinds=(EV_CLUSTER_2D,),
                           supporting_cohorts=("X",)), "cohort_scope is required")
    refuses(DriverEvidence("v1", "KRAS", 12, "COAD", True, evidence_kinds=(EV_CLUSTER_2D,)),
            "no supporting cohort")
    refuses(DriverEvidence("v1", "KRAS", 12, "COAD", True, evidence_kinds=(EV_CLUSTER_2D,),
                           supporting_cohorts=("X",), absence_reason=NO_POSITIONAL),
            "contradictory")
    refuses(DriverEvidence("v1", "KRAS", 12, "COAD", True), "must say")
    refuses(DriverEvidence("v1", "KRAS", 12, "COAD", False, absence_reason=NO_POSITIONAL),
            "gene_is_driver_in_scope is False")


def test_there_is_no_variant_level_driver_call():
    """The conflation guard, structurally: the contract has no is_driver field."""
    fields = set(DriverEvidence.__dataclass_fields__)
    for banned in ("is_driver", "driver", "is_pathogenic", "call", "classification"):
        assert banned not in fields, f"{banned!r} must not exist on DriverEvidence"


def test_fixture_has_discriminating_power():
    """A constant-output stub must be wrong on a majority, whatever it returns.
    Note the gene-level signal is CONSTANT (20/20 driver) -- all discrimination
    is positional, which is the point of SPEC-028."""
    with open(EXPECTED, encoding="utf-8") as f:
        blob = json.load(f)
    # The GOLDEN 20 are all in colorectal driver genes -- gene-level is constant
    # over them, which is precisely why a gene-level producer would be worthless.
    assert all(e["gene_is_driver_in_scope"] for e in blob["expected"].values()), \
        "gene-level is expected to be constant over the golden 20 -- that is the point"
    exp = load_expected()
    outcomes = [tuple(e["expected_evidence_kinds"]) if e["expected_evidence_kinds"]
                else e["expected_absence_reason"] for e in exp.values()]
    dist = collections.Counter("evidence" if isinstance(o, tuple) and o else o for o in outcomes)
    # all FOUR outcomes must be represented, including gene_not_a_driver_in_scope
    assert len(dist) == 4, dict(dist)
    top = dist.most_common(1)[0]
    assert top[1] / len(outcomes) <= 0.70, f"{top[0]} is {100*top[1]/len(outcomes):.0f}%"
    for constant in dist:
        wrong = sum(1 for o in outcomes
                    if ("evidence" if isinstance(o, tuple) and o else o) != constant)
        assert wrong > len(outcomes) / 2, \
            f"a stub always returning {constant!r} would fail only {wrong}/{len(outcomes)}"


def test_published_criteria_are_transcribed_not_authored():
    cfg = IntogenConfig(INTOGEN_CFG)
    assert not cfg.is_signed_off()
    assert cfg.scope == ("COAD", "READ")
    assert "q-value < 0.05" in cfg.thresholds["3D_CLUSTERS"]
    assert "intogen" in cfg.source.lower()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cfg.warn_if_unsigned()
    assert any("AWAITING_SIGN_OFF" in str(w.message) for w in caught)


# --- SPEC-029: the core must compose ------------------------------------------

def test_core_refuses_a_second_producers_bare_fact():
    """The design invariant must hold for producer #2 exactly as for producer #1."""
    con = seeded_core()
    bad = [{"variant_id": "q01", "population_code": "AA", "payload": {"x": 1},
            "calibration_status": "calibration_pending", "calibration_pending": True,
            "provenance": {"producer": "drivers", "producer_version": "0.1.0"}}]  # no method/time
    try:
        ingest_producer_results(con, bad, RESULT_TYPE)
    except ValueError as e:
        assert "missing provenance" in str(e)
    else:
        raise AssertionError("core accepted a bare fact from the second producer")
    assert read_producer_results(con) == [], "nothing may be written on rejection"


def test_adapter_refuses_a_driver_record_missing_required_payload_fields():
    """D-012's mitigation, pinned.

    The generic producer_result table cannot enforce payload shape as NOT NULL
    columns, so that guarantee moved from the DATABASE to APPLICATION CODE --
    deliberately, and weaker for it. This is where a reviewer confirms it still
    holds, because the schema will no longer tell them.
    """
    base_prov = {"producer": "drivers", "producer_version": "0.1.0", "method": METHOD,
                 "reference": "test", "generated_at": "2026-01-01"}

    def record(payload):
        return [{"variant_id": "q01", "population_code": "AA", "payload": payload,
                 "calibration_status": "calibration_pending", "calibration_pending": True,
                 "provenance": dict(base_prov)}]

    good = DriverEvidence("q01", "TP53", 175, "COAD", True,
                          evidence_kinds=(EV_DOMAIN,), supporting_cohorts=("C1",)).to_payload()

    # each of these is a state the DATABASE would have refused under a typed table
    cases = [
        ("missing cohort_scope", {k: v for k, v in good.items() if k != "cohort_scope"}),
        ("missing gene", {k: v for k, v in good.items() if k != "gene"}),
        ("missing evidence_kinds", {k: v for k, v in good.items() if k != "evidence_kinds"}),
        ("empty cohort_scope", {**good, "cohort_scope": ""}),
        ("evidence with no supporting cohort", {**good, "supporting_cohorts": []}),
        ("evidence AND an absence_reason", {**good, "absence_reason": NO_POSITIONAL}),
        ("no evidence and no absence_reason",
         {**good, "evidence_kinds": [], "supporting_cohorts": [], "absence_reason": None}),
        ("payload is not a dict", ["not", "a", "dict"]),
    ]
    for label, payload in cases:
        con = seeded_core()
        try:
            ingest_producer_results(con, record(payload), RESULT_TYPE)
        except DriverEvidenceError:
            pass
        else:
            raise AssertionError(f"adapter accepted a malformed driver payload: {label}")
        assert read_producer_results(con) == [], \
            f"nothing may be written on rejection ({label})"

    # and the well-formed record still goes in
    con = seeded_core()
    assert ingest_producer_results(con, record(good), RESULT_TYPE) == 1
    assert len(read_producer_results(con, RESULT_TYPE)) == 1


def test_payload_registry_gap_is_explicit():
    """The mitigation only covers registered result_types. A new producer gets
    provenance enforcement free and payload enforcement only once it registers --
    a known gap (D-012), asserted so it cannot be forgotten silently."""
    from contracts.payload_registry import is_registered, validate_payload as reg_validate
    assert is_registered(RESULT_TYPE), "driver_evidence must have a registered validator"
    assert not is_registered("some_future_producer_result")
    # an unregistered type is NOT validated -- that is the documented gap
    reg_validate("some_future_producer_result", {"anything": True})


def test_producer_neutral_view_exists_and_does_not_require_variant_effect():
    con = seeded_core()
    rows = read_variants(con)
    assert rows, "v_variant must expose variants"
    for r in rows:
        for k in ("variant_id", "gene", "protein_change", "population_code"):
            assert k in r, k
        assert "new_classification" not in r, "v_variant must not leak variant_effect's payload"


def test_second_producer_ingest_is_idempotent():
    con = seeded_core()
    ev = DriverEvidence("q01", "TP53", 175, "COAD", True, evidence_kinds=(EV_DOMAIN,),
                        supporting_cohorts=("C1",))
    rec = [{"variant_id": "q01", "population_code": "AA", "payload": ev.to_payload(),
            "calibration_status": "calibration_pending", "calibration_pending": True,
            "provenance": {"producer": "drivers", "producer_version": "0.1.0",
                           "method": METHOD, "reference": "test", "generated_at": "2026-01-01"}}]
    ingest_producer_results(con, rec, RESULT_TYPE)
    n1 = len(read_producer_results(con, RESULT_TYPE))
    ingest_producer_results(con, rec, RESULT_TYPE)
    n2 = len(read_producer_results(con, RESULT_TYPE))
    assert n1 == n2 == 1, (n1, n2)


# --- cache-dependent ----------------------------------------------------------

def test_golden_real_intogen_evidence():
    comp = compendium()
    exp = load_expected()
    for vid, e in sorted(exp.items()):
        ev = comp.evidence_for(vid, e["gene"], e["protein_change"], DEFAULT_SCOPE)
        p = ev.to_payload()
        assert p["gene_is_driver_in_scope"] == e["gene_is_driver_in_scope"], vid
        assert p["evidence_kinds"] == e["expected_evidence_kinds"], (vid, p["evidence_kinds"])
        assert p["absence_reason"] == e["expected_absence_reason"], vid
        assert p["residue"] == e["residue"], vid
        assert p["cohort_scope"] == "COAD,READ", vid


def test_h1047r_has_no_colorectal_positional_evidence_but_does_pan_cancer():
    """The direct D-008 test. Reported either way; this is the measured result."""
    comp = compendium()

    colo = comp.evidence_for("v14", "PIK3CA", "p.H1047R", ("COAD", "READ")).to_payload()
    assert colo["gene_is_driver_in_scope"] is True, "PIK3CA IS a colorectal driver"
    assert colo["evidence_kinds"] == [], colo
    assert colo["absence_reason"] == NO_POSITIONAL, colo
    assert colo["cohort_scope"] == "COAD,READ"

    # Pan-cancer scope: every cancer type the cache holds for PIK3CA.
    all_types = comp.cancer_types_for("PIK3CA")
    pan = comp.evidence_for("v14", "PIK3CA", "p.H1047R", all_types).to_payload()
    assert pan["evidence_kinds"], "pan-cancer SHOULD flag residue 1047"
    assert pan["supporting_cohorts"], pan
    assert pan["n_cohorts_in_scope"] > colo["n_cohorts_in_scope"]


def test_calibration_pending_on_every_driver_result():
    """Reasoned in producers/drivers/README.md, not copied: absence from a
    cluster is UNINFORMATIVE for an African-ancestry variant, not negative."""
    comp = compendium()
    con = seeded_core()
    variants = read_variants(con)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        recs = produce(variants, comp, DEFAULT_SCOPE, IntogenConfig(INTOGEN_CFG))
    assert recs
    assert all(r["calibration_status"] == "calibration_pending" for r in recs)
    assert all(r["calibration_pending"] for r in recs)
    assert all(r["provenance"]["reference"].startswith("IntOGen") for r in recs)
    # and the cohort scope is recorded on every payload, never assumed
    assert all(r["payload"]["cohort_scope"] == "COAD,READ" for r in recs)
    n = ingest_producer_results(con, recs, RESULT_TYPE)
    assert n == len(recs)
    stored = read_producer_results(con, RESULT_TYPE)
    assert all(s["calibration_status"] == "calibration_pending" for s in stored)


def test_end_to_end_summary_is_distributional_only():
    comp = compendium()
    con = seeded_core()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        recs = produce(read_variants(con), comp, DEFAULT_SCOPE)
    s = summarize(recs)
    assert s["n"] == len(recs) and s["result_type"] == RESULT_TYPE
    assert s["with_positional_evidence"] + sum(s["without_positional_evidence"].values()) == s["n"]


if __name__ == "__main__":
    _required = os.environ.get("INTOGEN_CACHE_REQUIRED", "").strip().lower() in ("1", "true", "yes")
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
        print("ALL DRIVERS TESTS PASSED")
    else:
        print(f"\n{len(_skipped)} data-dependent test(s) SKIPPED -- IntOGen cache absent.")
        print("The cache-free tests above DID gate: producer isolation, the positional parsers,")
        print("the contract's conflation refusals, absence of any variant-level driver call,")
        print("fixture discriminating power, and SPEC-029's core composition.")
        print("What is NOT proven without the cache: that real published IntOGen data yields the")
        print("expected evidence. This is INCOMPLETE COVERAGE, not a pass.")
        print("Populate:  python tools/intogen/fetch_compendium.py")
        print("Enforce:   set INTOGEN_CACHE_REQUIRED=1 to make a skip a failure.")
        if _required:
            raise SystemExit(1)
        print("DRIVERS TESTS INCOMPLETE (cache absent)")
