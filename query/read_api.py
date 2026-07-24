"""query layer -- deterministic structured read API over the core's read views.

The read path (ARCHITECTURE.md sec 3, layer 4a). Ask a structured question, get
rows back with provenance and calibration caveats attached, plus the exact query
that produced them.

Hard rules (ARCHITECTURE.md sec 4.3):
  * NEVER writes -- no INSERT/UPDATE/DELETE, no DDL.
  * Reads ONLY the v_* read views, never base tables.
  * Never imports from producers/. The summary SHAPE mirrors the producer's
    (SPEC-015 -- one summary format), re-implemented here against view rows.

No natural language anywhere in this layer (docs/risk-and-agent-control.md S5):
a future NL front-end translates INTO this API, never around it.
"""
from __future__ import annotations

from contracts.query import (
    POPULATIONS, CLASSIFICATIONS, CALIBRATION_STATUSES, CALIBRATION_PRECEDENCE,
    VariantEffectFilter, QueryResult, UndefinedCriterionError,
)
from contracts.variant_effect import CLS_BENIGN, CLS_PATHOGENIC, CLS_VUS

# The only read surface this module may touch (core/schema/schema.sql).
_VIEW = "v_variant_effect"

_COLUMNS = (
    "variant_id", "gene", "protein_change", "population_code",
    "original_classification", "new_classification",
    "calibration_status", "calibration_pending",
    "producer", "producer_version", "method", "reference", "generated_at",
)

# Reserved filter flags -> the [TO BE DEFINED] definition each would require
# (DEFINITIONS.md sec 4). Setting one is a refusal, not an answer (I3).
_UNDEFINED = {
    "ancestry_enriched": 'what makes a variant "ancestry-enriched"',
    "actionable": 'what makes a target "actionable/druggable"',
    "disconfirmation": "the disconfirmation criteria",
}


def _check_refusals(filt):
    for flag, description in _UNDEFINED.items():
        if getattr(filt, flag):
            raise UndefinedCriterionError(
                f"Refusing query: '{flag}' requires {description}, which is marked "
                "[TO BE DEFINED] in DEFINITIONS.md sec 4. A domain owner must supply "
                "the definition before this query can be answered -- the query layer "
                "may not invent one (control I3).")


def _validate(filt):
    bad = [p for p in filt.populations if p not in POPULATIONS]
    if bad:
        raise ValueError(
            f"Unknown population(s) {bad}. Valid codes are {list(POPULATIONS)}; "
            "reporting is per-population -- a combined 'African' or other merged "
            "ancestry grouping is never valid here (ARCHITECTURE.md sec 8).")
    if filt.classification is not None and filt.classification not in CLASSIFICATIONS:
        raise ValueError(
            f"Unknown classification {filt.classification!r}; "
            f"valid values are {list(CLASSIFICATIONS)}.")
    if filt.calibration_status is not None and filt.calibration_status not in CALIBRATION_STATUSES:
        raise ValueError(
            f"Unknown calibration status {filt.calibration_status!r}; "
            f"valid values are {list(CALIBRATION_STATUSES)}.")


def _build_query(filt):
    """Deterministic SQL over the read view + the bound values, for the echo."""
    where, params = [], {}
    if filt.populations:
        holders = ", ".join(f":pop{i}" for i in range(len(filt.populations)))
        where.append(f"population_code IN ({holders})")
        for i, p in enumerate(filt.populations):
            params[f"pop{i}"] = p
    if filt.classification is not None:
        where.append("new_classification = :classification")
        params["classification"] = filt.classification
    if filt.calibration_status is not None:
        where.append("calibration_status = :calibration_status")
        params["calibration_status"] = filt.calibration_status
    if filt.gene is not None:
        where.append("gene = :gene")
        params["gene"] = filt.gene

    sql = f"SELECT {', '.join(_COLUMNS)} FROM {_VIEW}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY variant_id"
    return sql, params


def _result_calibration(rows):
    """Result-level caveat: the worst contributing status wins (precedence
    pending > out_of_calibration > in_calibration). Survives aggregation."""
    present = {r["calibration_status"] for r in rows}
    for status in CALIBRATION_PRECEDENCE:
        if status in present:
            return status
    return None


def _provenance_summary(rows):
    runs = {(r["producer"], r["producer_version"], r["method"], r["generated_at"])
            for r in rows}
    return {
        "producers": sorted({r["producer"] for r in rows}),
        "versions": sorted({r["producer_version"] for r in rows}),
        "methods": sorted({r["method"] for r in rows}),
        "n_distinct_runs": len(runs),
    }


def _summarize(rows):
    """The producer's exact summary shape (SPEC-015 -- no second format):
    overall + per_population, each {n, vus_before, vus_after, pathogenic, benign,
    vus_before_pct, vus_after_pct}."""
    pops = {}

    def bucket(p):
        return pops.setdefault(p, {"n": 0, "vus_before": 0, "vus_after": 0,
                                   "pathogenic": 0, "benign": 0})

    for r in rows:
        d = bucket(r["population_code"])
        d["n"] += 1
        if r["original_classification"] == CLS_VUS:
            d["vus_before"] += 1
        if r["new_classification"] == CLS_VUS:
            d["vus_after"] += 1
        elif r["new_classification"] == CLS_PATHOGENIC:
            d["pathogenic"] += 1
        elif r["new_classification"] == CLS_BENIGN:
            d["benign"] += 1

    overall = {"n": 0, "vus_before": 0, "vus_after": 0, "pathogenic": 0, "benign": 0}
    for d in pops.values():
        for k in overall:
            overall[k] += d[k]

    def with_pct(d):
        d = dict(d)
        d["vus_before_pct"] = round(100 * d["vus_before"] / d["n"], 1) if d["n"] else 0.0
        d["vus_after_pct"] = round(100 * d["vus_after"] / d["n"], 1) if d["n"] else 0.0
        return d

    return {
        "overall": with_pct(overall),
        "per_population": {p: with_pct(d) for p, d in sorted(pops.items())},
    }


def _execute(con, filt):
    _check_refusals(filt)
    _validate(filt)
    sql, params = _build_query(filt)
    rows = [dict(row) for row in con.execute(sql, params)]   # SELECT on a v_* view; never a write
    return rows, {"sql": sql, "params": params}


def _result(rows, echo, summary=None):
    return QueryResult(
        rows=rows,
        query=echo,
        provenance=_provenance_summary(rows),
        calibration_status=_result_calibration(rows),
        populations=sorted({r["population_code"] for r in rows}),
        summary=summary,
    )


def query_variant_effects(con, filt=None):
    """Filtered read over v_variant_effect. Returns a QueryResult whose query
    field echoes the exact SQL executed and the bound filter values."""
    filt = filt or VariantEffectFilter()
    rows, echo = _execute(con, filt)
    return _result(rows, echo)


def vus_summary(con, filt=None):
    """Per-population VUS summary over v_variant_effect (producer summary shape),
    with the same first-class query echo, provenance, and result-level
    calibration caveat as any other read."""
    filt = filt or VariantEffectFilter()
    rows, echo = _execute(con, filt)
    return _result(rows, echo, summary=_summarize(rows))
