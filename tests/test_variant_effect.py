"""Golden-fixture test for the variant_effect producer (control G4).

Runs on a known toy variant set with mock tool calls; the producer's output must
reproduce the frozen golden file exactly. Also asserts the guardrails hold:
every result is calibration_pending, a clinical-DB-absent variant is still called
by structure/evolution tools (circularity break), and strict mode hard-fails on
PLACEHOLDER config.

Runnable two ways:  pytest tests/  OR  python tests/test_variant_effect.py
"""
import csv
import json
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from contracts.variant_effect import VariantInput, CLS_VUS
from producers.variant_effect.reclassify import reclassify
from producers.variant_effect.providers import FixtureScoreProvider

FIX = os.path.join(ROOT, "fixtures", "variant_effect")
CFG = os.path.join(ROOT, "config", "variant_effect.json")
CAL = os.path.join(ROOT, "config", "calibration.json")
MOCK = os.path.join(FIX, "mock_scores.json")


def load_variants():
    out = []
    with open(os.path.join(FIX, "variants_input.csv")) as f:
        for row in csv.DictReader(f):
            out.append(VariantInput(
                variant_id=row["variant_id"], gene=row["gene"],
                protein_change=row["protein_change"], population=row["population"],
                reference=row["reference"], original_classification=row["original_classification"],
                clinical_db_absent=row["clinical_db_absent"].strip().lower() == "true"))
    return out


def _run():
    variants = load_variants()
    providers = [
        FixtureScoreProvider("alphamissense", MOCK, db_independent=True),
        FixtureScoreProvider("eve", MOCK, db_independent=True),
        FixtureScoreProvider("polyphen", MOCK),
        FixtureScoreProvider("sift", MOCK),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return variants, reclassify(variants, providers, CFG, CAL, strict=False)


def test_matches_golden():
    _, result = _run()
    with open(os.path.join(FIX, "expected_output.json")) as f:
        expected = json.load(f)
    assert result.summary == expected["summary"], (result.summary, expected["summary"])
    got = {r["variant_id"]: r["new_classification"] for r in result.records}
    assert got == expected["new_classification"], got


def test_calibration_pending_on_every_result():
    _, result = _run()
    assert all(r["calibration_pending"] for r in result.records)
    assert all(r["calibration_status"] == "calibration_pending" for r in result.records)


def test_circularity_break_novel_variant_still_called():
    variants, result = _run()
    absent = {v.variant_id for v in variants if v.clinical_db_absent}
    by_id = {r["variant_id"]: r for r in result.records}
    resolved = [vid for vid in absent if by_id[vid]["new_classification"] != CLS_VUS]
    assert resolved, "expected >=1 clinical-DB-absent variant reclassified via structure/evolution tools"


def test_strict_mode_hard_fails_on_placeholder():
    variants, _ = _run()
    providers = [FixtureScoreProvider("alphamissense", MOCK, db_independent=True)]
    try:
        reclassify(variants, providers, CFG, CAL, strict=True)
    except RuntimeError:
        return
    raise AssertionError("strict mode should have raised on PLACEHOLDER config")


if __name__ == "__main__":
    for _name, _fn in list(globals().items()):
        if _name.startswith("test_"):
            _fn()
            print(f"PASS {_name}")
    print("ALL TESTS PASSED")
