"""Contract for the variant_effect producer: the input view + result objects.

This is the seam between the fusion core and the producer (ARCHITECTURE.md sec 6).
Nothing here is analysis logic; it is only the SHAPE of what crosses the boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# --- a single tool's call for a variant ---
BENIGN = "benign"
PATHOGENIC = "pathogenic"
UNCERTAIN = "uncertain"

# --- a variant's classification ---
CLS_BENIGN = "benign"
CLS_PATHOGENIC = "pathogenic"
CLS_VUS = "VUS"


@dataclass
class VariantInput:
    variant_id: str
    gene: str
    protein_change: str
    population: str                       # AA | GHA | ETH | NHW  (never a monolithic "African")
    reference: str                        # grch38 | pangenome
    original_classification: str = CLS_VUS
    clinical_db_absent: bool = False      # True = absent from ClinVar/COSMIC (structure tools still call it)


@dataclass
class ToolCall:
    tool: str                             # alphamissense | eve | polyphen | sift
    call: str                             # BENIGN | PATHOGENIC | UNCERTAIN
    raw_score: Optional[float] = None
    db_independent: bool = False          # True for structure/evolution tools (no clinical DB needed)


@dataclass
class Provenance:
    producer: str
    producer_version: str
    method: str                           # consensus rule id
    tools: list                           # [{tool, version}]
    n_tools_fired: int
    population: str
    reference: str
    calibration_status: str               # in_calibration | out_of_calibration | calibration_pending
    generated_at: str


@dataclass
class ReclassifiedVariant:
    variant_id: str
    original_classification: str
    new_classification: str
    tool_calls: list                      # [ToolCall as dict]
    calibration_status: str
    calibration_pending: bool             # True => render WITH caveat, never as a clean call
    provenance: dict


@dataclass
class ReclassificationResult:
    records: list                         # [ReclassifiedVariant as dict]
    summary: dict                         # per-population + overall VUS before/after
