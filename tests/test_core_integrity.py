"""Core data-integrity regression tests (SPEC-025) — F2 and F3 from the audit.

F2: the same variant_id ingested under two populations must keep BOTH population
associations. F3: re-ingesting identical records must not change the row count.

COMMIT A STATE: these tests are written against the CURRENT schema and are
EXPECTED TO FAIL — they reproduce the two audit findings. Do not "fix" them by
editing the assertions; fix the schema (Commit B) so they pass.

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
    """Same variant observed in AA and GHA: both associations must survive."""
    con = connect(":memory:")
    apply_schema(con, SCHEMA)
    _ingest_one(con, "vX", "AA")
    _ingest_one(con, "vX", "GHA")
    pairs = {(row["variant_id"], row["population_code"])
             for row in con.execute("SELECT variant_id, population_code FROM variant")}
    assert pairs == {("vX", "AA"), ("vX", "GHA")}, \
        f"F2: population associations lost — variant table holds only {pairs}"


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
        print(f"{failures} INTEGRITY TEST(S) FAILED (expected against the current schema)")
        sys.exit(1)
    print("ALL INTEGRITY TESTS PASSED")
