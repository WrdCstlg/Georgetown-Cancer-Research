"""Centralized provenance + calibration enforcement (ARCHITECTURE.md 4.5).

A prediction is never stored as a bare fact. Every result record entering the
core must carry producer, producer_version, method, generated_at, and a valid
calibration_status. This is the one place that rule lives; the ingest adapter
calls it, so no producer can invent its own (weaker) provenance contract.
"""
from __future__ import annotations

REQUIRED_PROVENANCE = ("producer", "producer_version", "method", "generated_at")
VALID_CALIBRATION = ("in_calibration", "out_of_calibration", "calibration_pending")


def require_provenance(record: dict) -> None:
    prov = record.get("provenance") or {}
    missing = [k for k in REQUIRED_PROVENANCE if not prov.get(k)]
    if missing:
        raise ValueError(f"{record.get('variant_id')}: missing provenance fields {missing}")
    cs = record.get("calibration_status")
    if cs not in VALID_CALIBRATION:
        raise ValueError(f"{record.get('variant_id')}: invalid/missing calibration_status {cs!r}")
