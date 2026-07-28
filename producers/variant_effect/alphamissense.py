"""AlphaMissense specifics for the variant_effect producer (SPEC-005, D-006).

ONE job: turn a variant into an AlphaMissense ToolCall. Everything peculiar to
AlphaMissense lives here -- its two class vocabularies, its bare protein-variant
format, its missense-only coverage, and the local score cache -- so
`providers.py` stays a thin interface and `reclassify.py` never learns about any
tool's file format.

Keying (decision D-006, option (c) + (b)): `(uniprot_id, protein_variant)`
against `AlphaMissense_aa_substitutions.tsv.gz`. That file carries no genomic
coordinates, so the lookup is reference-build independent and does not wait on
SPEC-004's GRCh38/pangenome reconciliation. The accession is LOOKED UP through
`contracts.identifiers`, never derived here.

LICENCE: AlphaMissense predictions are CC BY-NC-SA 4.0 (non-commercial,
share-alike). NO score data is committed to this repo. The cache this module
reads is populated locally by `tools/alphamissense/fetch_scores.py` and is
gitignored. See docs/alphamissense-data.md; redistribution and the NC term
remain open under D3.
"""
from __future__ import annotations
import json
import os
import re
import warnings

from contracts.variant_effect import ToolCall, BENIGN, PATHOGENIC, UNCERTAIN

TOOL = "alphamissense"

# --- the two published class vocabularies -------------------------------------
#
# VERIFIED against the real files (D-006), not from the bundled README, which
# documents only the `likely_*` form and whose own sample block for the
# aa-substitutions file contradicts that file's actual rows:
#
#   AlphaMissense_hg38.tsv.gz              -> likely_benign | ambiguous | likely_pathogenic
#   AlphaMissense_aa_substitutions.tsv.gz  -> benign        | ambiguous | pathogenic
#
# Same numeric thresholds in both; only the labels differ. Neither vocabulary is
# hardcoded as "the" one: both normalize to the same ToolCall.call so a switch
# between files can never silently change what a call means.
_AM_CLASS_TO_CALL = {
    "likely_benign":     BENIGN,
    "benign":            BENIGN,
    "likely_pathogenic": PATHOGENIC,
    "pathogenic":        PATHOGENIC,
    "ambiguous":         UNCERTAIN,
}


class ScoreNotFound(LookupError):
    """Raised when the cache holds no AlphaMissense record for a key.

    Distinct from "no coverage" (`None`, returned for variants outside
    AlphaMissense's missense-only domain). Not-found means we expected a score
    and did not get one -- the provider refuses rather than guessing or
    returning a default call.
    """


class ScoreCacheMissing(FileNotFoundError):
    """Raised when the local score cache has not been populated.

    Never degrades into a silent pass or a fabricated score: the message says
    exactly how to populate the cache.
    """


def normalize_am_class(am_class: str) -> str:
    """Map either published vocabulary onto the repo's ToolCall vocabulary.

    Both `benign` and `likely_benign` -> BENIGN; both `pathogenic` and
    `likely_pathogenic` -> PATHOGENIC; `ambiguous` -> UNCERTAIN.
    An unrecognised label RAISES: a new vocabulary is a fact about the data we
    must notice, not something to coerce into a call.
    """
    key = (am_class or "").strip().lower()
    try:
        return _AM_CLASS_TO_CALL[key]
    except KeyError:
        raise ValueError(
            f"Unrecognised AlphaMissense am_class {am_class!r}. Known vocabularies are "
            f"{sorted(_AM_CLASS_TO_CALL)} (the hg38 file uses likely_benign/likely_pathogenic; "
            "the aa-substitutions file uses benign/pathogenic). A new label means the published "
            "format changed -- do not map it to a call without checking the source."
        ) from None


# --- protein-change format ----------------------------------------------------
#
# The repo writes HGVS-p short form ("p.G12D"); AlphaMissense writes the bare
# substitution ("G12D"). Only SINGLE AMINO-ACID SUBSTITUTIONS are in scope:
# AlphaMissense covers missense only, so nonsense ("p.R1450*") and frameshift
# ("p.E1309fs") have no record BY CONSTRUCTION and must read as no-coverage,
# not as a lookup failure.
_MISSENSE_RE = re.compile(r"^(?:p\.)?([A-Z])(\d+)([A-Z])$")


def to_am_protein_variant(protein_change: str):
    """"p.G12D" -> "G12D". Returns None if this is not a single-aa substitution
    (nonsense, frameshift, indel, anything else AlphaMissense does not model)."""
    m = _MISSENSE_RE.match((protein_change or "").strip())
    return f"{m.group(1)}{m.group(2)}{m.group(3)}" if m else None


# --- the local, gitignored score cache ----------------------------------------

DEFAULT_CACHE = os.path.join(".cache", "alphamissense", "scores.json")

_POPULATE_HINT = (
    "Populate it locally (nothing is committed -- AlphaMissense is CC BY-NC-SA 4.0):\n"
    "    python tools/alphamissense/fetch_scores.py\n"
    "See docs/alphamissense-data.md for licence terms and what the fetch does."
)


class AlphaMissenseScoreCache:
    """Read-only view over the locally fetched score cache.

    Cache shape (written by tools/alphamissense/fetch_scores.py):
      {"source_file": "...", "source_record": "...", "retrieved_on": "YYYY-MM-DD",
       "scores": {"<uniprot_id>/<protein_variant>": {"am_pathogenicity": float,
                                                     "am_class": "<raw label>"}}}
    Raw publisher values are stored verbatim; normalization happens here, so the
    cache never bakes in an interpretation.
    """

    def __init__(self, path: str = DEFAULT_CACHE):
        self.path = path
        if not os.path.exists(path):
            raise ScoreCacheMissing(
                f"AlphaMissense score cache not found at {path!r}.\n" + _POPULATE_HINT)
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
        self._scores = blob.get("scores", {})
        self.source_file = blob.get("source_file", "unknown")
        self.retrieved_on = blob.get("retrieved_on", "unknown")
        self.source_record = blob.get("source_record", "")

    @property
    def source(self) -> str:
        """The provenance string stamped onto every ToolCall from this cache."""
        return f"{self.source_file} ({self.source_record}; retrieved {self.retrieved_on})"

    def lookup(self, uniprot_id: str, protein_variant: str) -> dict:
        key = f"{uniprot_id}/{protein_variant}"
        try:
            return self._scores[key]
        except KeyError:
            raise ScoreNotFound(
                f"No AlphaMissense record for {key!r} in {self.path!r} "
                f"(source: {self.source_file}). The provider does not guess and does not "
                "return a default call. If this variant should be scored, add its key to the "
                "fetch list and re-run the fetcher."
            ) from None

    def __len__(self) -> int:
        return len(self._scores)


# --- config: the tool's PUBLISHED cutoffs (never authored here) ---------------

class AlphaMissenseConfig:
    """Reads config/alphamissense.json.

    The score-to-class cutoffs are a DOMAIN criterion (DEFINITIONS.md sec 1).
    They are AlphaMissense's own published defaults, transcribed -- this module
    neither authors nor adjusts them (control I3). Until a domain owner signs
    off, the config is stamped AWAITING_SIGN_OFF and the producer warns once.

    Note the cutoffs are NOT applied here: the published files ship `am_class`
    already computed by the publisher, so we consume the publisher's own
    classification rather than re-deriving it. The cutoffs are carried in config
    so the rule is auditable and so a domain owner has something concrete to
    sign off on or override.
    """

    def __init__(self, path: str):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.status = cfg.get("status", "AWAITING_SIGN_OFF")
        self.cutoffs = cfg.get("published_cutoffs", {})
        self.source = cfg.get("source", "")
        self._warned = False

    def is_signed_off(self) -> bool:
        return self.status == "SIGNED_OFF"

    def warn_if_unsigned(self) -> None:
        if not self.is_signed_off() and not self._warned:
            warnings.warn(
                f"AlphaMissense class cutoffs are {self.status} -- publisher defaults "
                "transcribed from the AlphaMissense README, pending domain-owner sign-off "
                "(DEFINITIONS.md sec 1). Results remain calibration_pending regardless.")
            self._warned = True


def build_tool_call(record: dict, source: str, db_independent: bool = True) -> ToolCall:
    """One cache record -> one ToolCall, with the file of origin recorded."""
    return ToolCall(
        tool=TOOL,
        call=normalize_am_class(record["am_class"]),
        raw_score=record.get("am_pathogenicity"),
        db_independent=db_independent,
        source=source,
    )
