"""Payload validators, keyed by result_type (decision D-012).

WHY THIS EXISTS
D-012 chose a generic `producer_result` table: provenance and calibration stay
NOT NULL columns, but each producer's domain payload is JSON. The database
therefore cannot refuse, say, a driver-evidence record with no cohort attached.
That guarantee did not disappear -- it MOVED, deliberately, from the database to
application code. This registry is where it now lives, and
`core/ingest/producer_result_ingest.py` applies it at the write boundary.

The trade is stated plainly in D-012 and repeated here because it matters: a
check in application code is WEAKER than a NOT NULL. It can be bypassed by
writing to the table directly, where a schema constraint cannot. This registry
narrows that gap; it does not close it.

Keeping the map HERE rather than in the ingest adapter is what lets the adapter
stay genuinely producer-neutral: the adapter looks a validator up by
result_type, and never learns any producer's payload shape.
"""
from __future__ import annotations

from contracts.driver_evidence import (
    RESULT_TYPE as _DRIVER_EVIDENCE,
    validate_payload as _validate_driver_evidence,
)

PAYLOAD_VALIDATORS = {
    _DRIVER_EVIDENCE: _validate_driver_evidence,
}


def validate_payload(result_type: str, payload, variant_id: str = "<unknown>") -> None:
    """Apply the registered validator for `result_type`, if there is one.

    KNOWN GAP, stated rather than hidden: a result_type with no registered
    validator is NOT validated. A new producer gets provenance and calibration
    enforcement from the schema for free, but gets no payload enforcement until
    it registers here. That is a deliberate consequence of D-012's generic table
    and should be part of any new producer's checklist.
    """
    validator = PAYLOAD_VALIDATORS.get(result_type)
    if validator is None:
        return
    validator(payload, variant_id)


def is_registered(result_type: str) -> bool:
    return result_type in PAYLOAD_VALIDATORS
