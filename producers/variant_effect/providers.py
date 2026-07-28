"""Score providers for the variant_effect producer.

Real tools (AlphaMissense, EVE, PolyPhen, SIFT) plug in here behind ONE interface,
so the reclassification logic never changes when real databases are wired in.
The fixture provider supplies mock calls for the golden test.

Wiring status (SPEC-005 is NOT complete -- one provider of four):
  * AlphaMissense -- WIRED against real published scores (D-006, SPEC-027).
  * EVE, PolyPhen, SIFT -- still raise NotImplementedError.

An unwired provider raises (control G2): the pipeline can never silently run on
fabricated scores. A WIRED provider refuses just as loudly -- it returns None only
for variants its tool does not model, and raises rather than defaulting when a
score it expected is missing.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import json

from contracts.variant_effect import VariantInput, ToolCall
from producers.variant_effect.alphamissense import (
    build_tool_call, to_am_protein_variant,
)


class ScoreProvider(ABC):
    tool: str
    db_independent: bool = False

    @abstractmethod
    def score(self, v: VariantInput) -> Optional[ToolCall]:
        """Return a ToolCall, or None if this tool has no coverage for the variant."""


class FixtureScoreProvider(ScoreProvider):
    """Reads mock calls from a fixture file: {variant_id: {tool: call}}."""

    def __init__(self, tool: str, mock_path: str, db_independent: bool = False):
        self.tool = tool
        self.db_independent = db_independent
        with open(mock_path) as f:
            self._calls = json.load(f)

    def score(self, v: VariantInput) -> Optional[ToolCall]:
        call = self._calls.get(v.variant_id, {}).get(self.tool)
        if call is None:
            return None
        return ToolCall(tool=self.tool, call=call, db_independent=self.db_independent)


# --- Real providers: wire at deployment. Raise until wired (G2). ---

class AlphaMissenseProvider(ScoreProvider):
    """WIRED (SPEC-005 / SPEC-027, decision D-006).

    Keys on `(uniprot_id, protein_variant)` against the published
    AlphaMissense aa-substitutions data. The UniProt accession is LOOKED UP
    through the identifier seam (`contracts.identifiers`) -- this producer never
    derives an identifier, because producing them is the pipeline's concern
    (ARCHITECTURE.md sec 3 layer 1; SPEC-004).

    Three outcomes, deliberately distinct:
      * a ToolCall            -- a real published score was found;
      * None                  -- NO COVERAGE: not a single-aa substitution, so
                                 AlphaMissense does not model it by construction
                                 (nonsense, frameshift, indel);
      * ScoreNotFound raised  -- we expected a score and the cache has none.
                                 Never a guess, never a default call.

    Scores come from a LOCAL, GITIGNORED cache: AlphaMissense is CC BY-NC-SA 4.0
    and no score data is committed (docs/alphamissense-data.md; D3 OPEN).
    """
    tool = "alphamissense"
    db_independent = True

    def __init__(self, cache, identifiers, config=None):
        """cache: AlphaMissenseScoreCache · identifiers: IdentifierMap ·
        config: AlphaMissenseConfig | None (warns once while unsigned)."""
        self._cache = cache
        self._identifiers = identifiers
        self._config = config

    def score(self, v: VariantInput) -> Optional[ToolCall]:
        protein_variant = to_am_protein_variant(v.protein_change)
        if protein_variant is None:
            return None                     # no coverage -- not a missense substitution
        if self._config is not None:
            self._config.warn_if_unsigned()
        uniprot_id = self._identifiers.get(v.variant_id).require("uniprot_id")
        record = self._cache.lookup(uniprot_id, protein_variant)   # raises ScoreNotFound
        return build_tool_call(record, source=self._cache.source,
                               db_independent=self.db_independent)


class EVEProvider(ScoreProvider):
    tool = "eve"
    db_independent = True

    def __init__(self, db_path: str):
        self.db_path = db_path

    def score(self, v):  # pragma: no cover
        raise NotImplementedError("Wire the EVE score set. TODO.")


class PolyPhenProvider(ScoreProvider):
    tool = "polyphen"

    def score(self, v):  # pragma: no cover
        raise NotImplementedError("Wire PolyPhen output. TODO.")


class SIFTProvider(ScoreProvider):
    tool = "sift"

    def score(self, v):  # pragma: no cover
        raise NotImplementedError("Wire SIFT output. TODO.")
