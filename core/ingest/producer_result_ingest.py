"""Write-path adapter: land ANY producer's result into the fusion core (SPEC-029).

The producer-neutral counterpart to variant_effect_ingest.py. Enforces
provenance + calibration via core.provenance.validate before writing, exactly as
the variant_effect adapter does -- the enforcement is centralized
(ARCHITECTURE.md 4.5), so a second producer cannot invent a weaker contract.

Decision D-012: the payload is opaque here on purpose. This adapter guarantees
provenance and calibration; the producer's own contract in contracts/ guarantees
the payload's shape. Read path is separate: read_producer_results().
"""
from __future__ import annotations
import json

from core.provenance.validate import require_provenance


def ingest_producer_results(con, records, result_type: str) -> int:
    """Write provenance-tagged results of one result_type. Returns rows written.

    Each record: {variant_id, population_code, payload, calibration_status,
                  calibration_pending, provenance:{producer, producer_version,
                  method, reference, generated_at}}

    Raises BEFORE writing anything if any record lacks provenance or carries an
    invalid calibration status -- no partial bare facts, matching the
    variant_effect adapter's behaviour.
    """
    for r in records:
        require_provenance(r)

    n = 0
    for r in records:
        p = r["provenance"]
        # D-005 semantics extended with result_type: one result per observation,
        # enforced by the UNIQUE constraint in the schema. Re-ingesting replaces.
        con.execute(
            "INSERT OR REPLACE INTO producer_result "
            "(variant_id, population_code, producer, producer_version, method, reference, "
            " generated_at, calibration_status, calibration_pending, result_type, result_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (r["variant_id"], r["population_code"], p["producer"], p["producer_version"],
             p["method"], p["reference"], p["generated_at"],
             r["calibration_status"], int(r["calibration_pending"]),
             result_type, json.dumps(r["payload"], sort_keys=True)))
        n += 1
    con.commit()
    return n


def read_producer_results(con, result_type=None):
    """Read path: consumers read the VIEW, never the base table."""
    if result_type is None:
        rows = con.execute("SELECT * FROM v_producer_result ORDER BY variant_id, result_type")
    else:
        rows = con.execute(
            "SELECT * FROM v_producer_result WHERE result_type = ? ORDER BY variant_id",
            (result_type,))
    out = []
    for row in rows:
        d = dict(row)
        d["payload"] = json.loads(d["result_json"])
        out.append(d)
    return out


def read_variants(con):
    """Producer-NEUTRAL variant read view (SPEC-029). A producer reads THIS, not
    another producer's output view (ARCHITECTURE.md 4.2)."""
    return [dict(row) for row in
            con.execute("SELECT * FROM v_variant ORDER BY variant_id, population_code")]
