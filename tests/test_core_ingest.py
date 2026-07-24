"""Fusion-core write-path test (Phase 1 x Phase 2 integration).

Runs the variant_effect producer, lands its output in an in-memory core, and
asserts: every result persists with provenance readable via the query view;
calibration_pending survives the round-trip; and the core REFUSES a record whose
provenance has been stripped (no bare facts).

Supported: python tests/test_core_ingest.py  (direct execution is the supported,
CI-enforced path; pytest compatibility is UNVERIFIED — never executed end-to-end
in this environment, SPEC-016)
"""
import copy
import csv
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from contracts.variant_effect import VariantInput
from producers.variant_effect.reclassify import reclassify
from producers.variant_effect.providers import FixtureScoreProvider
from core.db import connect, apply_schema
from core.ingest.variant_effect_ingest import ingest, read_view

FIX = os.path.join(ROOT, "fixtures", "variant_effect")
SCHEMA = os.path.join(ROOT, "core", "schema", "schema.sql")


def _variants():
    rows = list(csv.DictReader(open(os.path.join(FIX, "variants_input.csv"))))
    return [VariantInput(r["variant_id"], r["gene"], r["protein_change"], r["population"],
                         r["reference"], r["original_classification"],
                         r["clinical_db_absent"].lower() == "true") for r in rows]


def _result(variants):
    M = os.path.join(FIX, "mock_scores.json")
    providers = [FixtureScoreProvider("alphamissense", M, True), FixtureScoreProvider("eve", M, True),
                 FixtureScoreProvider("polyphen", M), FixtureScoreProvider("sift", M)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return reclassify(variants, providers, os.path.join(ROOT, "config", "variant_effect.json"),
                          os.path.join(ROOT, "config", "calibration.json"))


def _db():
    con = connect(":memory:")
    apply_schema(con, SCHEMA)
    return con


def test_ingest_writes_all_with_provenance():
    v = _variants(); res = _result(v); con = _db()
    n = ingest(con, v, res)
    assert n == len(res.records) == 20
    rows = read_view(con)
    assert len(rows) == 20
    assert all(row["producer"] == "variant_effect" and row["method"] for row in rows)


def test_calibration_pending_persisted():
    v = _variants(); res = _result(v); con = _db(); ingest(con, v, res)
    rows = read_view(con)
    assert all(row["calibration_status"] == "calibration_pending" for row in rows)
    assert all(row["calibration_pending"] == 1 for row in rows)


def test_core_rejects_bare_fact():
    v = _variants(); res = _result(v); con = _db()
    tampered = copy.deepcopy(res)
    tampered.records[0]["provenance"].pop("method")   # strip provenance -> must be refused
    try:
        ingest(con, v, tampered)
    except ValueError:
        assert read_view(con) == []   # nothing written on rejection
        return
    raise AssertionError("core must refuse to write a record missing provenance")


def test_read_view_exposes_calibration_and_provenance():
    v = _variants(); res = _result(v); con = _db(); ingest(con, v, res)
    cols = set(read_view(con)[0].keys())
    assert {"variant_id", "new_classification", "calibration_status", "producer", "method"} <= cols


if __name__ == "__main__":
    for _name, _fn in list(globals().items()):
        if _name.startswith("test_"):
            _fn(); print(f"PASS {_name}")
    print("ALL CORE TESTS PASSED")
