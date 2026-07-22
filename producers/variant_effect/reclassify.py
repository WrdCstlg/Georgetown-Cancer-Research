"""variant_effect producer -- Phase 2: multi-tool consensus VUS reclassification.

ONE analytical job. Reads variants, applies a transparent consensus rule over
INJECTED score providers, and emits provenance-tagged, per-population-calibration-
flagged results. It never imports another producer, the query layer, or the
interface (ARCHITECTURE.md sec 4.2).

Consensus thresholds are PLACEHOLDER config pending domain confirmation; strict=True
hard-fails on placeholders so this can never silently ship on invented cutoffs (I3).
"""
from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timezone
import json
import warnings

from contracts.variant_effect import (
    VariantInput, Provenance, ReclassifiedVariant, ReclassificationResult,
    BENIGN, PATHOGENIC, CLS_BENIGN, CLS_PATHOGENIC, CLS_VUS,
)
from producers.variant_effect.calibration import CalibrationConfig

PRODUCER = "variant_effect"
VERSION = "0.1.0"


def _load_config(path):
    with open(path) as f:
        return json.load(f)


def _consensus(calls, rule):
    """calls: list[ToolCall]; rule: {min_agree}. Returns a classification.

    pathogenic if >= min_agree tools call pathogenic and none call benign;
    benign     if >= min_agree tools call benign and none call pathogenic;
    else VUS (insufficient agreement or conflict).
    """
    k = rule["min_agree"]
    p = sum(1 for c in calls if c.call == PATHOGENIC)
    b = sum(1 for c in calls if c.call == BENIGN)
    if p >= k and b == 0:
        return CLS_PATHOGENIC
    if b >= k and p == 0:
        return CLS_BENIGN
    return CLS_VUS


def reclassify(variants, providers, config_path, calibration_path, strict=False):
    cfg = _load_config(config_path)
    rule = cfg["consensus"]
    method = rule["method_id"]
    tool_versions = cfg.get("tool_versions", {})
    calib = CalibrationConfig(calibration_path)

    if cfg.get("status") == "PLACEHOLDER":
        if strict:
            raise RuntimeError(
                "Consensus config is a PLACEHOLDER; refusing strict run. "
                "A domain owner must confirm thresholds (DEFINITIONS.md).")
        warnings.warn("Consensus thresholds are PLACEHOLDER (min_agree etc.) -- pending domain confirmation.")

    records = []
    for v in variants:
        calls = [tc for pr in providers if (tc := pr.score(v)) is not None]
        new_cls = _consensus(calls, rule)

        # per-population calibration: pending dominates, then out, else in
        statuses = [calib.status_for(c.tool, v.population, strict) for c in calls] or ["calibration_pending"]
        if "calibration_pending" in statuses:
            cstatus = "calibration_pending"
        elif "out_of_calibration" in statuses:
            cstatus = "out_of_calibration"
        else:
            cstatus = "in_calibration"
        cpending = cstatus != "in_calibration"

        prov = Provenance(
            producer=PRODUCER, producer_version=VERSION, method=method,
            tools=[{"tool": c.tool, "version": tool_versions.get(c.tool, "unknown")} for c in calls],
            n_tools_fired=len(calls), population=v.population, reference=v.reference,
            calibration_status=cstatus,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        records.append(ReclassifiedVariant(
            variant_id=v.variant_id,
            original_classification=v.original_classification,
            new_classification=new_cls,
            tool_calls=[asdict(c) for c in calls],
            calibration_status=cstatus,
            calibration_pending=cpending,
            provenance=asdict(prov),
        ))

    return ReclassificationResult(
        records=[asdict(r) for r in records],
        summary=_summarize(variants, records),
    )


def _summarize(variants, records):
    by_id = {v.variant_id: v for v in variants}
    pops = {}

    def bucket(p):
        return pops.setdefault(p, {"n": 0, "vus_before": 0, "vus_after": 0, "pathogenic": 0, "benign": 0})

    for r in records:
        d = bucket(by_id[r.variant_id].population)
        d["n"] += 1
        if r.original_classification == CLS_VUS:
            d["vus_before"] += 1
        if r.new_classification == CLS_VUS:
            d["vus_after"] += 1
        elif r.new_classification == CLS_PATHOGENIC:
            d["pathogenic"] += 1
        elif r.new_classification == CLS_BENIGN:
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
