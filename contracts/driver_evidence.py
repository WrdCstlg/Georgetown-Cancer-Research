"""Contract for driver EVIDENCE: the seam between the drivers producer and the core.

SPEC-028. Nothing here is analysis logic; it is only the SHAPE of what crosses
the boundary, plus the validation the database can no longer perform for us
(decision D-012: the generic `producer_result` table keeps provenance and
calibration NOT NULL but carries the payload as JSON, so payload enforcement
moves HERE).

THE CENTRAL DISTINCTION, and the error this contract exists to prevent:

    A GENE being a driver does not make every VARIANT in it a driver.

IntOGen's compendium calls drivers at GENE level per cohort. On the golden
fixture, 15 of 15 missense variants sit in a colorectal driver gene -- a
gene-level signal would be constant and worth nothing. The information is in the
POSITIONAL layer: IntOGen also publishes, per cohort, the significant smRegions
DOMAINS, OncodriveCLUSTL 2D clusters and HotMAPS 3D clusters. Intersecting a
variant's residue with those splits the same 15 variants 10 / 5.

So this contract carries positional evidence and refuses to express a
variant-level driver CALL. There is deliberately no `is_driver` field.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

RESULT_TYPE = "driver_evidence"

# What the positional intersection found. NOT a driver call.
EV_DOMAIN = "domain"          # residue inside a significant smRegions PFAM domain
EV_CLUSTER_2D = "cluster_2d"  # inside a significant OncodriveCLUSTL linear cluster
EV_CLUSTER_3D = "cluster_3d"  # inside a significant HotMAPS 3D cluster
EVIDENCE_KINDS = (EV_DOMAIN, EV_CLUSTER_2D, EV_CLUSTER_3D)

# Why there is no positional evidence. Each means something different and none
# of them means "not a driver".
NO_GENE_ROW = "gene_not_a_driver_in_scope"   # gene absent from the cohort scope
NO_POSITIONAL = "no_positional_evidence"     # gene IS a driver; this residue is not in a cluster
NOT_MISSENSE = "not_missense"                # no residue to intersect


class DriverEvidenceError(ValueError):
    """Raised when a record would enter the core malformed.

    Exists because D-012 chose the generic `producer_result` table, which cannot
    type-check a payload. This is the enforcement that moved out of the schema;
    a contract check is weaker than a NOT NULL (it can be bypassed by writing to
    the table directly) and D-012 records that as a stated cost.
    """


@dataclass(frozen=True)
class DriverEvidence:
    """Positional driver evidence for ONE variant, under ONE cohort scope.

    `evidence_kinds` empty + `absence_reason` set is a perfectly valid record:
    "this gene is a colorectal driver and this residue is not in any significant
    cluster" is information, and it is NOT the same as "not a driver".
    """
    variant_id: str
    gene: str
    residue: Optional[int]                 # None when the change is not missense
    cohort_scope: str                      # e.g. "COAD,READ" -- recorded, never assumed
    gene_is_driver_in_scope: bool
    role_in_scope: Optional[str] = None    # IntOGen ROLE: Act | LoF | amb
    evidence_kinds: tuple = ()             # subset of EVIDENCE_KINDS
    supporting_cohorts: tuple = ()         # cohort names that supplied the hits
    n_cohorts_in_scope: int = 0
    best_qvalue: Optional[float] = None
    absence_reason: Optional[str] = None   # one of NO_GENE_ROW / NO_POSITIONAL / NOT_MISSENSE

    def to_payload(self) -> dict:
        """The `result_json` payload. Validated on the way out, because the
        database will not validate it on the way in (D-012)."""
        validate_evidence(self)
        return {
            "gene": self.gene,
            "residue": self.residue,
            "cohort_scope": self.cohort_scope,
            "gene_is_driver_in_scope": self.gene_is_driver_in_scope,
            "role_in_scope": self.role_in_scope,
            "evidence_kinds": list(self.evidence_kinds),
            "supporting_cohorts": list(self.supporting_cohorts),
            "n_cohorts_in_scope": self.n_cohorts_in_scope,
            "best_qvalue": self.best_qvalue,
            "absence_reason": self.absence_reason,
        }


def validate_evidence(ev: DriverEvidence) -> None:
    """The payload checks the schema can no longer make (D-012).

    Deliberately strict about the one conflation this producer must never
    commit: positional evidence may not be claimed without a cohort to attribute
    it to, and evidence-plus-absence-reason is contradictory.
    """
    if not ev.variant_id or not ev.gene:
        raise DriverEvidenceError("driver evidence needs a variant_id and a gene")
    if not ev.cohort_scope:
        raise DriverEvidenceError(
            f"{ev.variant_id}: cohort_scope is required. Driver evidence is only meaningful "
            "relative to the cohorts it was computed on -- PIK3CA H1047R is flagged pan-cancer "
            "and NOT flagged in COAD/READ (D-008), so an unscoped record is not interpretable.")
    bad = [k for k in ev.evidence_kinds if k not in EVIDENCE_KINDS]
    if bad:
        raise DriverEvidenceError(f"{ev.variant_id}: unknown evidence kind(s) {bad}")
    if ev.evidence_kinds and not ev.supporting_cohorts:
        raise DriverEvidenceError(
            f"{ev.variant_id}: positional evidence claimed with no supporting cohort. "
            "Evidence without attribution is exactly the bare fact the core refuses.")
    if ev.evidence_kinds and ev.absence_reason:
        raise DriverEvidenceError(
            f"{ev.variant_id}: has both evidence {list(ev.evidence_kinds)} and an "
            f"absence_reason {ev.absence_reason!r} -- contradictory.")
    if not ev.evidence_kinds and ev.absence_reason not in (NO_GENE_ROW, NO_POSITIONAL, NOT_MISSENSE):
        raise DriverEvidenceError(
            f"{ev.variant_id}: no evidence and no valid absence_reason. 'Nothing found' must say "
            "WHICH nothing: gene not a driver in scope, gene is a driver but this residue is not "
            "in a cluster, or not a missense change. Those mean different things.")
    if ev.absence_reason == NO_POSITIONAL and not ev.gene_is_driver_in_scope:
        raise DriverEvidenceError(
            f"{ev.variant_id}: absence_reason={NO_POSITIONAL!r} asserts the gene IS a driver in "
            "scope, but gene_is_driver_in_scope is False.")
