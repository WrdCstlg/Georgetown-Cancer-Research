"""EVE specifics for the variant_effect producer (SPEC-005, part 2 of 4).

ONE job: turn a variant into an EVE ToolCall. Everything peculiar to EVE lives
here -- its own class vocabulary, its entry-name key, its three distinct
no-coverage states, and the local score cache -- so `providers.py` stays a thin
interface and `reclassify.py` never learns about any tool's data format.

Keying: `(uniprot_entry_name, protein_variant)`. EVE keys on the UniProtKB ENTRY
NAME (`P53_HUMAN`), NOT the accession (`P04637`) that AlphaMissense uses. The
entry name is LOOKED UP through `contracts.identifiers`, never derived here
(SPEC-027; the seam was extended additively for exactly this).

LICENCE: evemodel.org states its data falls under the MIT License. NOTE the
provenance caveat recorded in docs/eve-data.md and under decision D3: the
LICENSE.txt served by the site is copyrighted to the site's author, not to the
Marks Lab / OATML who produced the predictions. This repo therefore applies the
SAME no-commit discipline it applies to AlphaMissense: no EVE score data is
committed, the cache is gitignored, and the licensing question stays OPEN under
D3 rather than being resolved by convenience.
"""
from __future__ import annotations
import json
import os
import re
import warnings

from contracts.variant_effect import ToolCall, BENIGN, PATHOGENIC, UNCERTAIN

TOOL = "eve"

# --- EVE's published class vocabulary -----------------------------------------
#
# VERIFIED against live API responses (2026-07-28), not from the paper: the
# `EVE_classes_75_pct_retained_ASM` column takes exactly these three values.
# This is a THIRD vocabulary in this repo, after AlphaMissense's two
# (likely_benign/likely_pathogenic and benign/pathogenic). None of the three is
# privileged: each tool's module normalizes its own labels into the repo's
# ToolCall vocabulary, and an unrecognised label RAISES rather than being
# coerced into a call.
_EVE_CLASS_TO_CALL = {
    "benign":     BENIGN,
    "pathogenic": PATHOGENIC,
    "uncertain":  UNCERTAIN,
}


class EveScoreNotFound(LookupError):
    """Raised when the cache should hold an EVE record for a key and does not.

    Distinct from the three NO-COVERAGE states (see `coverage_state`): those are
    facts about what EVE publishes and yield None. This is "we expected a score
    and did not get one" -- the provider refuses rather than guessing.
    """


class EveCacheMissing(FileNotFoundError):
    """Raised when the local EVE cache has not been populated. Never degrades
    into a silent pass or a fabricated score; the message says how to fix it."""


def normalize_eve_class(eve_class: str) -> str:
    """Map EVE's published class onto the repo's ToolCall vocabulary.

    `Benign` -> BENIGN, `Pathogenic` -> PATHOGENIC, `Uncertain` -> UNCERTAIN.
    An unrecognised label RAISES: a new vocabulary is a fact about the data we
    must notice, not something to coerce.
    """
    key = (eve_class or "").strip().lower()
    try:
        return _EVE_CLASS_TO_CALL[key]
    except KeyError:
        raise ValueError(
            f"Unrecognised EVE class {eve_class!r}. Known values are "
            f"{sorted(_EVE_CLASS_TO_CALL)} (column "
            "EVE_classes_75_pct_retained_ASM). A new label means the published "
            "format changed -- do not map it to a call without checking the source."
        ) from None


# --- protein-change format ----------------------------------------------------
# EVE, like AlphaMissense, models single amino-acid substitutions only. The repo
# writes HGVS-p short form ("p.R175H"); EVE's rows carry wt_aa/position/mt_aa,
# which the fetcher joins into the same bare form ("R175H").
_MISSENSE_RE = re.compile(r"^(?:p\.)?([A-Z])(\d+)([A-Z])$")


def to_eve_protein_variant(protein_change: str):
    """"p.R175H" -> "R175H". None if not a single-aa substitution."""
    m = _MISSENSE_RE.match((protein_change or "").strip())
    return f"{m.group(1)}{m.group(2)}{m.group(3)}" if m else None


# --- the local, gitignored cache ----------------------------------------------

DEFAULT_CACHE = os.path.join(".cache", "eve", "scores.json")

_POPULATE_HINT = (
    "Populate it locally (nothing is committed -- see docs/eve-data.md):\n"
    "    python tools/eve/fetch_scores.py"
)

# The three ways EVE can have nothing for a variant. Kept separate because they
# mean different things and only one of them is a gap in OUR wiring.
COVERAGE_GENE_ABSENT = "gene_not_published"    # EVE publishes no such protein at all
COVERAGE_UNSCORED = "row_present_unscored"     # EVE has the row but assigned no score
COVERAGE_NOT_MISSENSE = "not_missense"         # outside EVE's model by construction


class EveScoreCache:
    """Read-only view over the locally fetched EVE cache.

    Cache shape (written by tools/eve/fetch_scores.py):
      {"source": "...", "retrieved_on": "YYYY-MM-DD",
       "proteins_published": [...entry names EVE covers...],
       "scores": {"<entry_name>/<protein_variant>": {
            "eve_score": float, "eve_class": "<raw label>",
            "uncertainty": float|None,
            "clinvar": "<ClinVar_ClinicalSignificance as shipped by EVE>",
            "gnomad_freq": "<frequency_gv2 as shipped by EVE>"}}}
    Publisher values are stored verbatim; normalization happens here so the
    cache never bakes in an interpretation.
    """

    def __init__(self, path: str = DEFAULT_CACHE):
        self.path = path
        if not os.path.exists(path):
            raise EveCacheMissing(
                f"EVE score cache not found at {path!r}.\n" + _POPULATE_HINT)
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
        self._scores = blob.get("scores", {})
        self._published = set(blob.get("proteins_published", []))
        # Keys EVE publishes a row for but assigned NO score. Recorded so this
        # state stays distinguishable from "key genuinely absent" -- the latter
        # must raise, the former is no-coverage.
        self._unscored = set(blob.get("unscored_keys", []))
        self.source_service = blob.get("source", "unknown")
        self.retrieved_on = blob.get("retrieved_on", "unknown")

    @property
    def source(self) -> str:
        """Provenance string stamped onto every ToolCall from this cache."""
        return f"{self.source_service} (retrieved {self.retrieved_on})"

    def publishes(self, entry_name: str) -> bool:
        return entry_name in self._published

    def coverage_state(self, entry_name: str, protein_variant):
        """Why there is no call, or None if there IS one. Never a guess."""
        if protein_variant is None:
            return COVERAGE_NOT_MISSENSE
        if not self.publishes(entry_name):
            return COVERAGE_GENE_ABSENT
        if f"{entry_name}/{protein_variant}" in self._unscored:
            return COVERAGE_UNSCORED
        return None

    def lookup(self, entry_name: str, protein_variant: str) -> dict:
        key = f"{entry_name}/{protein_variant}"
        try:
            rec = self._scores[key]
        except KeyError:
            raise EveScoreNotFound(
                f"No EVE record for {key!r} in {self.path!r}. The provider does not guess "
                "and does not return a default call. If this variant should be scored, add "
                "its protein to the fetch list and re-run the fetcher."
            ) from None
        if rec.get("eve_score") in (None, ""):
            raise EveScoreNotFound(
                f"EVE publishes a row for {key!r} but assigned it no score. That is a "
                "no-coverage fact, not a call -- callers should use coverage_state() first.")
        return rec

    def __len__(self) -> int:
        return len(self._scores)


# --- config: EVE's PUBLISHED class assignment (never authored here) ----------

class EveConfig:
    """Reads config/eve.json.

    EVE publishes the class directly (column
    `EVE_classes_75_pct_retained_ASM`), so the provider consumes the publisher's
    own assignment rather than re-deriving it from the continuous score. The
    cut-points are carried in config so the rule is auditable and so a domain
    owner has something concrete to sign off on or override (I3).
    """

    def __init__(self, path: str):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.status = cfg.get("status", "AWAITING_SIGN_OFF")
        self.cutoffs = cfg.get("observed_class_boundaries", {})
        self.retained = cfg.get("published_class_assignment", {})
        self.source = cfg.get("source", "")
        self._warned = False

    def is_signed_off(self) -> bool:
        return self.status == "SIGNED_OFF"

    def warn_if_unsigned(self) -> None:
        if not self.is_signed_off() and not self._warned:
            warnings.warn(
                f"EVE class assignment is {self.status} -- publisher default "
                "(75% most confident retained) transcribed from evemodel.org, pending "
                "domain-owner sign-off (DEFINITIONS.md sec 1). Results remain "
                "calibration_pending regardless.")
            self._warned = True


def build_tool_call(record: dict, source: str, db_independent: bool = True) -> ToolCall:
    """One cache record -> one ToolCall, with the service of origin recorded."""
    return ToolCall(
        tool=TOOL,
        call=normalize_eve_class(record["eve_class"]),
        raw_score=record.get("eve_score"),
        db_independent=db_independent,
        source=source,
    )
