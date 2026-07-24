"""Query-layer test (SPEC-015): deterministic structured read API over the core's
read views.

Seeds an in-memory core DIRECTLY from a frozen static fixture of core-shaped rows
(fixtures/query/core_rows.json) -- never by running the producer. The query
layer's contract is with the core's read views, not with producer behavior; the
consensus rule is pending domain sign-off and will change, and these tests must
not break when it does. (The seed writes to a throwaway in-memory DB in test
setup; the query layer itself never writes -- it reads v_variant_effect only.)

Runnable: pytest tests/  OR  python tests/test_query_read_api.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from contracts.query import VariantEffectFilter, UndefinedCriterionError
from core.db import connect, apply_schema
from query.read_api import query_variant_effects, vus_summary

SCHEMA = os.path.join(ROOT, "core", "schema", "schema.sql")
FIX = os.path.join(ROOT, "fixtures", "query", "core_rows.json")


def _db():
    """Seed a throwaway in-memory core from the frozen fixture, via the base
    tables, so reads go through the real v_variant_effect view."""
    with open(FIX) as f:
        seed = json.load(f)
    con = connect(":memory:")
    apply_schema(con, SCHEMA)
    for p in seed["populations"]:
        con.execute("INSERT INTO population(code, description) VALUES (?,?)",
                    (p["code"], p["description"]))
    for v in seed["variants"]:
        con.execute(
            "INSERT INTO variant (variant_id, gene, protein_change, reference, "
            "population_code, clinical_db_absent) VALUES (?,?,?,?,?,?)",
            (v["variant_id"], v["gene"], v["protein_change"], v["reference"],
             v["population_code"], v["clinical_db_absent"]))
    for r in seed["results"]:
        con.execute(
            "INSERT INTO variant_effect_result "
            "(variant_id, original_classification, new_classification, producer, "
            " producer_version, method, n_tools_fired, reference, population_code, "
            " generated_at, calibration_status, calibration_pending, tool_calls_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["variant_id"], r["original_classification"], r["new_classification"],
             r["producer"], r["producer_version"], r["method"], 4, r["reference"],
             r["population_code"], r["generated_at"], r["calibration_status"],
             r["calibration_pending"], "[]"))
    con.commit()
    return con


def _ids(result):
    return [r["variant_id"] for r in result.rows]


# --- filters ---

def test_filter_population_single():
    res = query_variant_effects(_db(), VariantEffectFilter(populations=("AA",)))
    assert _ids(res) == ["v01", "v02"]
    assert res.populations == ["AA"]


def test_filter_population_multiple():
    res = query_variant_effects(_db(), VariantEffectFilter(populations=("ETH", "NHW")))
    assert _ids(res) == ["v05", "v06", "v07", "v08"]
    assert res.populations == ["ETH", "NHW"]


def test_filter_population_rejects_merged_grouping():
    for bad in ("AFR", "African"):
        try:
            query_variant_effects(_db(), VariantEffectFilter(populations=(bad,)))
        except ValueError as e:
            assert "AA" in str(e) and "never" in str(e)
            continue
        raise AssertionError(f"population filter must reject merged grouping {bad!r}")


def test_filter_classification():
    res = query_variant_effects(_db(), VariantEffectFilter(classification="VUS"))
    assert _ids(res) == ["v03", "v05", "v08"]


def test_filter_calibration_status():
    res = query_variant_effects(_db(), VariantEffectFilter(calibration_status="in_calibration"))
    assert _ids(res) == ["v04", "v06", "v07"]
    assert res.calibration_status == "in_calibration"


def test_filter_gene():
    res = query_variant_effects(_db(), VariantEffectFilter(gene="TP53"))
    assert _ids(res) == ["v01", "v04", "v07"]


# --- query echo (show your work) ---

def test_query_echo_exact_sql_and_bound_values():
    res = query_variant_effects(_db(), VariantEffectFilter(populations=("AA",), gene="TP53"))
    sql, params = res.query["sql"], res.query["params"]
    assert sql.startswith("SELECT") and " FROM v_variant_effect" in sql
    assert "population_code IN (:pop0)" in sql and "gene = :gene" in sql
    assert params == {"pop0": "AA", "gene": "TP53"}
    assert _ids(res) == ["v01"]


def test_read_is_select_on_view_only():
    res = query_variant_effects(_db())
    sql = res.query["sql"].upper()
    assert sql.startswith("SELECT") and "V_VARIANT_EFFECT" in sql
    for verb in ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"):
        assert verb not in sql


# --- provenance passthrough ---

def test_provenance_summary_full_set():
    res = query_variant_effects(_db())
    assert res.provenance == {
        "producers": ["variant_effect"],
        "versions": ["0.1.0"],
        "methods": ["consensus_v0_min_agree"],
        "n_distinct_runs": 2,
    }


def test_provenance_summary_distinct_runs_subset():
    res = query_variant_effects(_db(), VariantEffectFilter(populations=("AA",)))
    assert res.provenance["n_distinct_runs"] == 1   # both AA rows came from run 1


# --- per-population summary (producer shape) ---

def test_summary_matches_producer_shape_and_values():
    res = vus_summary(_db())
    s = res.summary
    assert set(s.keys()) == {"overall", "per_population"}
    assert s["overall"] == {"n": 8, "vus_before": 8, "vus_after": 3,
                            "pathogenic": 3, "benign": 2,
                            "vus_before_pct": 100.0, "vus_after_pct": 37.5}
    assert s["per_population"]["AA"] == {"n": 2, "vus_before": 2, "vus_after": 0,
                                         "pathogenic": 1, "benign": 1,
                                         "vus_before_pct": 100.0, "vus_after_pct": 0.0}
    assert s["per_population"]["GHA"]["vus_after_pct"] == 50.0
    assert sorted(s["per_population"].keys()) == ["AA", "ETH", "GHA", "NHW"]


def test_summary_carries_query_echo_and_populations():
    res = vus_summary(_db(), VariantEffectFilter(populations=("GHA",)))
    assert res.query["params"] == {"pop0": "GHA"}
    assert res.populations == ["GHA"]
    assert res.summary["overall"]["n"] == 2


# --- calibration cannot be hidden by aggregation ---

def test_calibration_survives_aggregation_mixed_statuses():
    res = vus_summary(_db())   # mix of pending + out + in across 8 rows
    assert res.calibration_status == "calibration_pending"   # pending dominates the summary


def test_calibration_precedence_out_over_in():
    res = query_variant_effects(_db(), VariantEffectFilter(populations=("ETH", "NHW")))
    statuses = {r["calibration_status"] for r in res.rows}
    assert statuses == {"out_of_calibration", "in_calibration"}   # no pending in this mix
    assert res.calibration_status == "out_of_calibration"


def test_calibration_clean_only_when_all_clean():
    res = query_variant_effects(_db(), VariantEffectFilter(calibration_status="in_calibration"))
    assert res.calibration_status == "in_calibration"


# --- required refusals ([TO BE DEFINED] criteria raise, never answer) ---

def test_refusals_raise_named_error():
    cases = {
        "ancestry_enriched": "ancestry-enriched",
        "actionable": "actionable/druggable",
        "disconfirmation": "disconfirmation criteria",
    }
    for flag, definition in cases.items():
        filt = VariantEffectFilter(**{flag: True})
        for api in (query_variant_effects, vus_summary):
            try:
                api(_db(), filt)
            except UndefinedCriterionError as e:
                msg = str(e)
                assert definition in msg and "domain owner" in msg and "TO BE DEFINED" in msg
                continue
            raise AssertionError(f"{api.__name__} must refuse when {flag} is set")


if __name__ == "__main__":
    for _name, _fn in list(globals().items()):
        if _name.startswith("test_"):
            _fn()
            print(f"PASS {_name}")
    print("ALL QUERY TESTS PASSED")
