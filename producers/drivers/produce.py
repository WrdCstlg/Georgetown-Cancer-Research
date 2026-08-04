"""drivers producer -- positional driver EVIDENCE from IntOGen (SPEC-028).

ONE analytical job: for each variant in a core read view, intersect its residue
with what IntOGen published as significant within a stated cohort scope, and emit
a provenance-tagged, calibration-flagged evidence record via the ingest contract.

ISOLATION (ARCHITECTURE.md sec 4.2) -- this module imports:
    contracts/          (the seams: driver_evidence)
    core.ingest         (the write path)
    producers.variant_effect.*   <- NO. It does not. Nor query/, nor interface/,
                                    nor any other producer.
It reads `v_variant`, the producer-NEUTRAL view added by SPEC-029, NOT
`v_variant_effect`. Reading another producer's output view would be composing
through a producer instead of through the core, which sec 4.2 exists to forbid.

WHAT THIS IS NOT:
  * not a pathogenicity call -- that is variant_effect's axis, and this result
    is deliberately NOT routed into its consensus. `min_agree` is untouched.
  * not a driver CALL on a variant. A gene being a driver does not make every
    variant in it a driver; see contracts/driver_evidence.py.
"""
from __future__ import annotations
from datetime import datetime, timezone

from contracts.driver_evidence import RESULT_TYPE
from producers.drivers.intogen import PRODUCER, VERSION, DEFAULT_SCOPE

METHOD = "intogen_positional_v0"


def produce(variants, compendium, scope=DEFAULT_SCOPE, config=None):
    """variants: rows from v_variant (variant_id, gene, protein_change,
    population_code, reference). Returns records for the ingest contract.

    CALIBRATION -- reasoned for THIS producer, not copied from the providers.
    Every record is stamped `calibration_pending`, and the reason is specific:
    IntOGen's clusters are significant *relative to the mutation spectrum of the
    cohorts they were computed on*, which are overwhelmingly European-ancestry
    (CPTAC, Hartwig, TCGA). So for an African-ancestry variant, ABSENCE from a
    cluster is UNINFORMATIVE rather than negative -- it may reflect that the
    cohort had no power to detect recurrence at that residue in that population,
    not that the residue is unimportant. Presence is more transferable than
    absence, and this producer cannot distinguish the two. Until a domain owner
    defines per-population calibration adequacy (DEFINITIONS.md sec 4), the
    honest stamp is `calibration_pending` on both. See producers/drivers/README.md.
    """
    if config is not None:
        config.warn_if_unsigned()

    generated_at = datetime.now(timezone.utc).isoformat()
    records = []
    for v in variants:
        ev = compendium.evidence_for(
            variant_id=v["variant_id"], gene=v["gene"],
            protein_change=v["protein_change"], scope=scope)
        records.append({
            "variant_id": v["variant_id"],
            "population_code": v["population_code"],
            "payload": ev.to_payload(),          # validated at the contract seam (D-012)
            "calibration_status": "calibration_pending",
            "calibration_pending": True,
            "provenance": {
                "producer": PRODUCER,
                "producer_version": VERSION,
                "method": METHOD,
                "reference": compendium.provenance_source,
                "generated_at": generated_at,
            },
        })
    return records


def summarize(records) -> dict:
    """Distributional summary. Counts only -- no publisher payload reproduced."""
    from collections import Counter
    kinds = Counter()
    absence = Counter()
    for r in records:
        p = r["payload"]
        if p["evidence_kinds"]:
            kinds["with_positional_evidence"] += 1
            for k in p["evidence_kinds"]:
                kinds[k] += 1
        else:
            absence[p["absence_reason"]] += 1
    return {
        "n": len(records),
        "with_positional_evidence": kinds.get("with_positional_evidence", 0),
        "by_evidence_kind": {k: v for k, v in kinds.items() if k != "with_positional_evidence"},
        "without_positional_evidence": dict(absence),
        "result_type": RESULT_TYPE,
    }
