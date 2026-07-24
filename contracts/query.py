"""Contract for the query layer: structured read requests + result objects.

This is the seam between the fusion core's READ views and any consumer (a future
NL front-end, the interface) (ARCHITECTURE.md sec 6). Nothing here is query logic;
it is only the SHAPE of what crosses the boundary. The query layer reads v_* views
only and NEVER writes (ARCHITECTURE.md sec 4.3).

Flat-module layout per decision D-002 (PROPOSED) — same form as
contracts/variant_effect.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# The only populations the system ever reports on -- never a monolithic "African"
# grouping (ARCHITECTURE.md sec 8; DEFINITIONS.md sec 3).
POPULATIONS = ("AA", "GHA", "ETH", "NHW")

CLASSIFICATIONS = ("benign", "pathogenic", "VUS")

# Row-level calibration statuses (core schema CHECK constraint).
CALIBRATION_STATUSES = ("in_calibration", "out_of_calibration", "calibration_pending")

# Result-level precedence (guardrail: calibration cannot be hidden by aggregation):
# pending dominates, then out-of-calibration, then in.
CALIBRATION_PRECEDENCE = ("calibration_pending", "out_of_calibration", "in_calibration")


class UndefinedCriterionError(Exception):
    """Raised when a query would require a value marked [TO BE DEFINED] in
    DEFINITIONS.md. Refusing is a feature: an invented criterion is worse than
    no answer (control I3). The message names the missing definition and states
    that a domain owner must supply it."""


@dataclass
class VariantEffectFilter:
    """A deterministic, fully-explicit filter over the v_variant_effect read view.

    Empty/None fields match everything. Reserved flags name the criteria that are
    [TO BE DEFINED] in DEFINITIONS.md; setting one raises UndefinedCriterionError
    rather than silently answering with an invented definition.
    """
    populations: tuple = ()                    # subset of POPULATIONS; empty = all four
    classification: Optional[str] = None       # one of CLASSIFICATIONS
    calibration_status: Optional[str] = None   # one of CALIBRATION_STATUSES
    gene: Optional[str] = None                 # exact gene symbol

    # --- reserved: require [TO BE DEFINED] definitions; setting any raises ---
    ancestry_enriched: bool = False            # needs DEFINITIONS.md sec 4: "ancestry-enriched"
    actionable: bool = False                   # needs DEFINITIONS.md sec 4: "actionable/druggable"
    disconfirmation: bool = False              # needs DEFINITIONS.md sec 4: disconfirmation criteria


@dataclass
class QueryResult:
    """Every read returns this. The caveat and the work shown are first-class:
    a caller can always see precisely what was asked and whether any contributing
    row is caveated -- including under aggregation."""
    rows: list                                 # [v_* row as dict]
    query: dict                                # {"sql": exact SQL executed, "params": bound filter values}
    provenance: dict                           # {"producers": [...], "versions": [...], "methods": [...],
                                               #  "n_distinct_runs": int}
    calibration_status: Optional[str]          # result-level; CALIBRATION_PRECEDENCE over rows;
                                               # None when no rows contributed
    populations: list                          # explicit populations covered by the rows;
                                               # never an implicit or merged grouping
    summary: Optional[dict] = None             # producer summary shape (overall + per_population);
                                               # present on summary queries
