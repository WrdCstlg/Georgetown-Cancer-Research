"""IntOGen specifics for the drivers producer (SPEC-028).

Everything peculiar to IntOGen's published compendium lives here -- its cohort
scoping, its three positional evidence fields and their formats, and the local
cache -- so the producer stays about the analytical job and nothing about
IntOGen's file format leaks upward.

WHAT THIS READS, precisely (verified from the real archive, not the paper):
`Compendium_Cancer_Genes.tsv`, keyed (SYMBOL, TRANSCRIPT, COHORT), one row per
gene per cohort. Three columns carry SUB-GENE positional evidence:

    DOMAINS      PFAM_ID:START_AA:END_AA   smRegions,        q < 0.1
    2D_CLUSTERS  START_AA:END_AA           OncodriveCLUSTL,  p < 0.05
    3D_CLUSTERS  AA_1,AA_2,...             HotMAPS,          q < 0.05

Those are what make this producer worth building. The gene-level driver call is
near-constant on the fixture (15/15) and therefore carries no information; the
positional intersection splits the same variants 10/5.

LICENCE: IntOGen ships CC0 1.0 (public domain) -- committing a slice WOULD be
permitted. The cache pattern is used anyway, deliberately, for consistency with
the two licence-encumbered providers. See decision D-013.
"""
from __future__ import annotations
import json
import os
import re
import warnings

from contracts.driver_evidence import (
    DriverEvidence, EV_DOMAIN, EV_CLUSTER_2D, EV_CLUSTER_3D,
    NO_GENE_ROW, NO_POSITIONAL, NOT_MISSENSE,
)

PRODUCER = "drivers"
VERSION = "0.1.0"

# Default cohort scope. COLORECTAL, not pan-cancer -- and the choice is
# load-bearing, not incidental: PIK3CA H1047R is flagged in 35 of 109 pan-cancer
# rows and in 0 of 2 COAD/READ rows (D-008 addendum 2). Scope is recorded in
# every result's provenance so a reader never has to guess which it was.
DEFAULT_SCOPE = ("COAD", "READ")

_MISSENSE_RE = re.compile(r"^(?:p\.)?([A-Z])(\d+)([A-Z])$")


class IntogenCacheMissing(FileNotFoundError):
    """Raised when the local compendium cache has not been populated. Never
    degrades into a silent pass or a fabricated result."""


def residue_of(protein_change: str):
    """"p.G12D" -> 12. None when there is no single residue to intersect."""
    m = _MISSENSE_RE.match((protein_change or "").strip())
    return int(m.group(2)) if m else None


# --- parsing the three published positional formats --------------------------

def parse_2d_clusters(cell: str) -> set:
    """"1450:1450,213:216" -> {213,214,215,216,1450}"""
    out = set()
    for part in (cell or "").split(","):
        part = part.strip()
        if ":" not in part:
            continue
        a, _, b = part.partition(":")
        if a.strip().isdigit() and b.strip().isdigit():
            lo, hi = int(a), int(b)
            if lo <= hi:
                out |= set(range(lo, hi + 1))
    return out


def parse_3d_clusters(cell: str) -> set:
    """"546,545,542" -> {542,545,546}"""
    return {int(p.strip()) for p in (cell or "").split(",") if p.strip().isdigit()}


def parse_domains(cell: str) -> set:
    """"PF00001:120:340" -> {120..340}"""
    out = set()
    for part in (cell or "").split(","):
        bits = [b.strip() for b in part.split(":")]
        if len(bits) >= 3 and bits[1].isdigit() and bits[2].isdigit():
            lo, hi = int(bits[1]), int(bits[2])
            if lo <= hi:
                out |= set(range(lo, hi + 1))
    return out


# --- the local, gitignored cache ---------------------------------------------

DEFAULT_CACHE = os.path.join(".cache", "intogen", "compendium.json")

_POPULATE_HINT = (
    "Populate it locally (nothing is committed -- see docs/intogen-data.md):\n"
    "    python tools/intogen/fetch_compendium.py")


class IntogenCompendium:
    """Read-only view over the locally fetched compendium.

    Cache shape (written by tools/intogen/fetch_compendium.py):
      {"source": "...", "release": "...", "retrieved_on": "YYYY-MM-DD",
       "genes": {"<SYMBOL>": [ {cohort, cancer_type, role, qvalue, methods,
                                domains[], clusters_2d[], clusters_3d[]}, ... ]}}
    Publisher values are stored verbatim; interpretation happens here.
    """

    def __init__(self, path: str = DEFAULT_CACHE):
        self.path = path
        if not os.path.exists(path):
            raise IntogenCacheMissing(
                f"IntOGen compendium cache not found at {path!r}.\n" + _POPULATE_HINT)
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
        self._genes = blob.get("genes", {})
        self.source = blob.get("source", "unknown")
        self.release = blob.get("release", "unknown")
        self.retrieved_on = blob.get("retrieved_on", "unknown")

    @property
    def provenance_source(self) -> str:
        return f"{self.source} release {self.release} (retrieved {self.retrieved_on})"

    def rows_for(self, gene: str, scope=None) -> list:
        """Cohort rows for a gene. scope=None means EVERY cancer type -- used to
        inspect what other scopes would say, never to produce a result: a result
        without a recorded scope is not interpretable (see D-008 addendum 2)."""
        rows = self._genes.get(gene, [])
        return rows if scope is None else [r for r in rows if r["cancer_type"] in scope]

    def cancer_types_for(self, gene: str) -> tuple:
        return tuple(sorted({r["cancer_type"] for r in self._genes.get(gene, [])}))

    def evidence_for(self, variant_id, gene, protein_change, scope=DEFAULT_SCOPE) -> DriverEvidence:
        """The analytical job: intersect this variant's residue with what
        IntOGen published as significant, within the given cohort scope.

        Returns EVIDENCE. Never a driver call on the variant -- see
        contracts/driver_evidence.py for why there is no `is_driver` field.
        """
        scope_str = ",".join(scope)
        residue = residue_of(protein_change)
        rows = self.rows_for(gene, scope)

        if not rows:
            return DriverEvidence(
                variant_id=variant_id, gene=gene, residue=residue, cohort_scope=scope_str,
                gene_is_driver_in_scope=False, n_cohorts_in_scope=0,
                absence_reason=NO_GENE_ROW)

        roles = [r["role"] for r in rows if r.get("role")]
        role = max(set(roles), key=roles.count) if roles else None
        qs = [r["qvalue"] for r in rows if r.get("qvalue") is not None]
        best_q = min(qs) if qs else None

        if residue is None:
            return DriverEvidence(
                variant_id=variant_id, gene=gene, residue=None, cohort_scope=scope_str,
                gene_is_driver_in_scope=True, role_in_scope=role,
                n_cohorts_in_scope=len(rows), best_qvalue=best_q,
                absence_reason=NOT_MISSENSE)

        kinds, cohorts = set(), set()
        for r in rows:
            hit = False
            if residue in parse_domains(r.get("domains") or ""):
                kinds.add(EV_DOMAIN); hit = True
            if residue in parse_2d_clusters(r.get("clusters_2d") or ""):
                kinds.add(EV_CLUSTER_2D); hit = True
            if residue in parse_3d_clusters(r.get("clusters_3d") or ""):
                kinds.add(EV_CLUSTER_3D); hit = True
            if hit:
                cohorts.add(r["cohort"])

        if not kinds:
            # The gene IS a driver here and this residue is NOT in any significant
            # cluster. That is information, and it is NOT "not a driver".
            return DriverEvidence(
                variant_id=variant_id, gene=gene, residue=residue, cohort_scope=scope_str,
                gene_is_driver_in_scope=True, role_in_scope=role,
                n_cohorts_in_scope=len(rows), best_qvalue=best_q,
                absence_reason=NO_POSITIONAL)

        return DriverEvidence(
            variant_id=variant_id, gene=gene, residue=residue, cohort_scope=scope_str,
            gene_is_driver_in_scope=True, role_in_scope=role,
            evidence_kinds=tuple(sorted(kinds)), supporting_cohorts=tuple(sorted(cohorts)),
            n_cohorts_in_scope=len(rows), best_qvalue=best_q)

    def __len__(self) -> int:
        return len(self._genes)


# --- config: IntOGen's PUBLISHED significance settings (never authored) ------

class IntogenConfig:
    """Reads config/intogen.json.

    The significance settings are IntOGen's own, transcribed. This module
    neither authors nor adjusts them (control I3): it consumes rows the
    publisher already filtered, and records which thresholds produced them.
    """

    def __init__(self, path: str):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.status = cfg.get("status", "AWAITING_SIGN_OFF")
        self.thresholds = cfg.get("published_significance", {})
        self.scope = tuple(cfg.get("default_cohort_scope", DEFAULT_SCOPE))
        self.source = cfg.get("source", "")
        self._warned = False

    def is_signed_off(self) -> bool:
        return self.status == "SIGNED_OFF"

    def warn_if_unsigned(self) -> None:
        if not self.is_signed_off() and not self._warned:
            warnings.warn(
                f"IntOGen inclusion criteria are {self.status} -- publisher significance "
                "settings transcribed from the release README, pending domain-owner sign-off "
                "(DEFINITIONS.md sec 1, questionnaire A14). Results remain calibration_pending.")
            self._warned = True
