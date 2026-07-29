"""Score providers for the variant_effect producer.

Real tools (AlphaMissense, EVE, PolyPhen, SIFT) plug in here behind ONE interface,
so the reclassification logic never changes when real databases are wired in.
The fixture provider supplies mock calls for the golden test.

Wiring status (SPEC-005 is NOT complete -- TWO providers of four):
  * AlphaMissense -- WIRED against real published scores (D-006, SPEC-027).
  * EVE           -- WIRED against real published data (SPEC-027 seam extension).
  * PolyPhen, SIFT -- still raise NotImplementedError.

The two wired providers key on DIFFERENT identifiers (AlphaMissense on the
UniProt accession, EVE on the UniProt entry name) and speak DIFFERENT class
vocabularies. Both are resolved through the identifier seam and normalized in
their own modules; nothing about that leaks into the consensus engine.

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
from producers.variant_effect.eve import (
    build_tool_call as eve_build_tool_call, to_eve_protein_variant,
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
    """WIRED (SPEC-005 part 2 of 4, SPEC-027 seam extension).

    Keys on `(uniprot_entry_name, protein_variant)` against EVE's published
    per-protein data. NOTE the key differs from AlphaMissense's: EVE uses the
    UniProtKB ENTRY NAME (`P53_HUMAN`), not the ACCESSION (`P04637`). Both are
    looked up through the identifier seam; neither is derived here.

    Three distinct NO-COVERAGE states, all returning None and none of them a guess:
      * the protein is not published by EVE at all (EVE covers ~3,200 proteins,
        not the proteome -- FBXW7 and RNF43 are absent, see D-009);
      * EVE publishes the row but assigned it no score;
      * the change is not a single-aa substitution.
    A key that should be present but is missing raises EveScoreNotFound.

    Scores come from a LOCAL, GITIGNORED cache -- no EVE data is committed
    (docs/eve-data.md; licence provenance OPEN under D3).
    """
    tool = "eve"
    db_independent = True

    def __init__(self, cache, identifiers, config=None):
        """cache: EveScoreCache · identifiers: IdentifierMap ·
        config: EveConfig | None (warns once while unsigned)."""
        self._cache = cache
        self._identifiers = identifiers
        self._config = config

    def score(self, v: VariantInput) -> Optional[ToolCall]:
        protein_variant = to_eve_protein_variant(v.protein_change)
        if protein_variant is None:
            return None                     # no coverage -- not a missense substitution
        if self._config is not None:
            self._config.warn_if_unsigned()
        entry_name = self._identifiers.get(v.variant_id).require("uniprot_entry_name")
        if self._cache.coverage_state(entry_name, protein_variant) is not None:
            return None                     # gene unpublished, or row present but unscored
        record = self._cache.lookup(entry_name, protein_variant)   # raises if truly absent
        return eve_build_tool_call(record, source=self._cache.source,
                                   db_independent=self.db_independent)


class PolyPhenProvider(ScoreProvider):
    tool = "polyphen"

    def score(self, v):  # pragma: no cover
        raise NotImplementedError("Wire PolyPhen output. TODO.")


class SIFTProvider(ScoreProvider):
    tool = "sift"

    def score(self, v):  # pragma: no cover
        raise NotImplementedError("Wire SIFT output. TODO.")
