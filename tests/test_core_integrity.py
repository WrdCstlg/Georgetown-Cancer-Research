"""Core data-integrity regression tests (SPEC-025) — F2 and F3 from the audit.

F2: the same variant_id ingested under two populations must keep BOTH population
associations. F3: re-ingesting identical records must not change the row count.

History: the Commit-A form of test_f2 asserted the old (broken) invariant —
that the variant ENTITY preserves both populations — and FAILED against the old
schema ("variant table holds only {('vX', 'GHA')}"). After D-004 (PROPOSED), the
invariant moved: population is a property of the observation, so the test now
asserts (a) the variant table carries NO population column to lose, and (b) both
observations survive with their populations intact on the read view. That is the
same scientific guarantee — no silent loss of a population association — made
structurally unbreakable instead of overwrite-prone.

Runnable: python tests/test_core_integrity.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from contracts.variant_effect import VariantInput
from core.db import connect, apply_schema
from core.ingest.variant_effect_ingest import ingest

SCHEMA = os.path.join(ROOT, "core", "schema", "schema.sql")


class _Res:
    pass


def _record(vid, pop):
    return {"variant_id": vid, "original_classification": "VUS", "new_classification": "benign",
            "calibration_status": "calibration_pending", "calibration_pending": 1, "tool_calls": [],
            "provenance": {"producer": "variant_effect", "producer_version": "0.1.0",
                           "method": "consensus_v0_min_agree", "n_tools_fired": 4,
                           "reference": "grch38", "population": pop,
                           "generated_at": "2026-01-01T00:00:00+00:00"}}


def _ingest_one(con, vid, pop):
    r = _Res()
    r.records = [_record(vid, pop)]
    v = VariantInput(vid, "KRAS", "p.G12D", pop, "grch38", "VUS", False)
    ingest(con, [v], r)


def test_f2_both_population_associations_survive():
    """Same variant observed in AA and GHA: both associations must survive — on the
    observation (result), never as an overwritable attribute of the variant entity."""
    con = connect(":memory:")
    apply_schema(con, SCHEMA)
    _ingest_one(con, "vX", "AA")
    _ingest_one(con, "vX", "GHA")

    cols = {row["name"] for row in con.execute("PRAGMA table_info(variant)")}
    assert "population_code" not in cols, \
        f"F2: variant entity still carries population_code {cols} — the overwrite vector remains"

    variant_rows = con.execute("SELECT * FROM variant WHERE variant_id = 'vX'").fetchall()
    assert len(variant_rows) == 1, "F2: the genomic fact must be one row"

    observed = {row["population_code"] for row in con.execute(
        "SELECT population_code FROM v_variant_effect WHERE variant_id = 'vX'")}
    assert observed == {"AA", "GHA"}, \
        f"F2: population associations lost — observations hold only {observed}"


def test_f3_reingest_is_idempotent():
    """Re-running the same ingest must not duplicate result rows."""
    con = connect(":memory:")
    apply_schema(con, SCHEMA)
    _ingest_one(con, "vY", "AA")
    n1 = con.execute("SELECT COUNT(*) AS c FROM variant_effect_result").fetchone()["c"]
    _ingest_one(con, "vY", "AA")
    n2 = con.execute("SELECT COUNT(*) AS c FROM variant_effect_result").fetchone()["c"]
    assert n2 == n1, f"F3: re-ingest duplicated rows — {n1} before, {n2} after"


if __name__ == "__main__":
    failures = 0
    for _name, _fn in list(globals().items()):
        if _name.startswith("test_"):
            try:
                _fn()
                print(f"PASS {_name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL {_name}: {e}")
    if failures:
        print(f"{failures} INTEGRITY TEST(S) FAILED")
        sys.exit(1)
    print("ALL INTEGRITY TESTS PASSED")
