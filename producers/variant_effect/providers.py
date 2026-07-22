"""Score providers for the variant_effect producer.

Real tools (AlphaMissense, EVE, PolyPhen, SIFT) plug in here behind ONE interface,
so the reclassification logic never changes when real databases are wired in.
The fixture provider supplies mock calls for the golden test.

Real providers raise until wired (control G2): the pipeline can never silently run
on fabricated scores.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import json

from contracts.variant_effect import VariantInput, ToolCall


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
    tool = "alphamissense"
    db_independent = True

    def __init__(self, db_path: str):
        self.db_path = db_path

    def score(self, v):  # pragma: no cover
        raise NotImplementedError(
            "Wire the AlphaMissense pre-scored DB (71M missense variants). TODO.")


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
