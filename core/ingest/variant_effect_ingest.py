"""Write-path adapter: land a ReclassificationResult into the fusion core.

This is the ONLY way variant_effect results enter the core. It enforces
provenance + calibration on every record (via core.provenance.validate) before
writing, and upserts the variant entities. Read path is separate: read_view().
"""
from __future__ import annotations
import json

from core.provenance.validate import require_provenance

POP_DESC = {
    "AA": "African American (US)",
    "GHA": "Ghanaian",
    "ETH": "Ethiopian",
    "NHW": "Non-Hispanic White (US)",
}


def ingest(con, variants, result) -> int:
    """Write variants + provenance-tagged results into the core. Returns rows written.

    Raises before any results are written if a record lacks provenance/calibration.
    """
    # validate everything first -- fail before writing a single result (no partial bare facts)
    for r in result.records:
        require_provenance(r)

    for code in sorted({v.population for v in variants}):
        con.execute("INSERT OR IGNORE INTO population(code, description) VALUES (?,?)",
                    (code, POP_DESC.get(code, code)))

    for v in variants:
        con.execute(
            "INSERT OR REPLACE INTO variant "
            "(variant_id, gene, protein_change, reference, population_code, clinical_db_absent) "
            "VALUES (?,?,?,?,?,?)",
            (v.variant_id, v.gene, v.protein_change, v.reference, v.population, int(v.clinical_db_absent)))

    n = 0
    for r in result.records:
        p = r["provenance"]
        con.execute(
            "INSERT INTO variant_effect_result "
            "(variant_id, original_classification, new_classification, producer, producer_version, "
            " method, n_tools_fired, reference, population_code, generated_at, "
            " calibration_status, calibration_pending, tool_calls_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["variant_id"], r["original_classification"], r["new_classification"],
             p["producer"], p["producer_version"], p["method"], p["n_tools_fired"],
             p["reference"], p["population"], p["generated_at"],
             r["calibration_status"], int(r["calibration_pending"]), json.dumps(r["tool_calls"])))
        n += 1
    con.commit()
    return n


def read_view(con):
    """Read path: the query layer reads this view, never the base tables."""
    return [dict(row) for row in con.execute("SELECT * FROM v_variant_effect ORDER BY variant_id")]
