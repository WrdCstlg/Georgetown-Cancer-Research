"""Contract for the identifier-mapping seam: variant_id -> external identifiers.

The seam between a variant as the ANALYSIS layer knows it (`VariantInput`:
gene + protein_change + population + reference) and a variant as EXTERNAL
RESOURCES key it (UniProt accession, Ensembl transcript, genomic locus).
Decision D-006, option (c); SPEC-027.

Why this is its own contract and not more fields on `VariantInput`
(ARCHITECTURE.md sec 6, sec 4.1):

  * Producing identifiers is the PIPELINE's concern -- `pipeline/annotation/`
    (Funcotator) and SPEC-004 ("key variants by (locus, ref-context)") are the
    proper source. A producer that DERIVED a locus from a gene symbol would be
    doing annotation inside layer 3, crossing AGENTS.md sec 1.1.
  * So a producer LOOKS UP identifiers through this seam and never computes
    them. Absent identifier => a named refusal, never a guess (I3 in spirit:
    the layer that owns the fact supplies it).
  * `VariantInput` stays a description of the analysis view. Identifier plumbing
    does not accumulate on the analysis contract, so core/ and query/ take zero
    blast radius from this change.

Today the map is loaded from a small committed JSON fixture. When
`pipeline/annotation/` and SPEC-004 exist they populate the SAME shape and the
consuming producer does not change.

Nothing here is a domain criterion -- identifiers are facts, not thresholds.
No value in this module needs domain-owner sign-off (contrast DEFINITIONS.md).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import json


class IdentifierNotFound(LookupError):
    """Raised when a variant has no entry in the identifier map.

    A miss is a REFUSAL, not a default: the producer cannot invent a UniProt
    accession or a locus, and silently skipping the variant would understate
    coverage. The message names the variant and the map so the fix is obvious
    (add the variant upstream, or extend the fixture).
    """


@dataclass(frozen=True)
class VariantIdentifiers:
    """External identifiers for one variant. Every field is optional because
    different upstream sources supply different subsets: annotation gives locus
    + transcript, a UniProt mapping gives the accession. A consumer asks for
    what IT needs and refuses clearly if that field is absent.
    """
    variant_id: str
    uniprot_id: Optional[str] = None          # UniProtKB accession, e.g. P01116
    transcript_id: Optional[str] = None       # Ensembl, e.g. ENST00000256078.9
    chrom: Optional[str] = None               # e.g. chr12
    pos: Optional[int] = None                 # 1-based
    ref_allele: Optional[str] = None
    alt_allele: Optional[str] = None
    source: Optional[str] = None              # where this row came from (citation)

    def require(self, field_name: str) -> str:
        """Return an identifier field or refuse by name. Never returns a default."""
        value = getattr(self, field_name, None)
        if value in (None, ""):
            raise IdentifierNotFound(
                f"{self.variant_id}: identifier map has no {field_name!r}. "
                "The producer may not derive it -- it is supplied upstream "
                "(pipeline/annotation, SPEC-004) or by the identifier fixture.")
        return value


@dataclass
class IdentifierMap:
    """variant_id -> VariantIdentifiers. A read-only lookup, nothing more."""
    entries: dict = field(default_factory=dict)
    source: Optional[str] = None              # provenance of the map as a whole

    def get(self, variant_id: str) -> VariantIdentifiers:
        try:
            return self.entries[variant_id]
        except KeyError:
            raise IdentifierNotFound(
                f"{variant_id!r} is not in the identifier map"
                f"{f' ({self.source})' if self.source else ''}. "
                "Identifiers come from upstream (pipeline/annotation, SPEC-004) "
                "or the committed fixture -- a producer never invents one."
            ) from None

    def __contains__(self, variant_id: str) -> bool:
        return variant_id in self.entries

    def __len__(self) -> int:
        return len(self.entries)


def load_identifier_map(path: str) -> IdentifierMap:
    """Load the JSON identifier fixture.

    Shape:
      {"source": "<citation for the map>",
       "variants": {"<variant_id>": {"uniprot_id": "...", "source": "...", ...}}}
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    entries = {}
    for vid, rec in raw.get("variants", {}).items():
        entries[vid] = VariantIdentifiers(
            variant_id=vid,
            uniprot_id=rec.get("uniprot_id"),
            transcript_id=rec.get("transcript_id"),
            chrom=rec.get("chrom"),
            pos=rec.get("pos"),
            ref_allele=rec.get("ref_allele"),
            alt_allele=rec.get("alt_allele"),
            source=rec.get("source"),
        )
    return IdentifierMap(entries=entries, source=raw.get("source"))
