"""Per-population calibration flagging.

The tools are European-calibrated; whether one is trusted for a given population
is a DOMAIN definition (DEFINITIONS.md, [TO BE DEFINED]). This module reads that
config and refuses to treat a PLACEHOLDER as truth: every result is stamped
'calibration_pending' until a domain owner supplies real per-population targets.

This is control I3 + guardrail R1/S1 made mechanical: a European-trained tool's
output can never render as a clean call for an African-ancestry population until
someone has established it is in-calibration for that population.
"""
from __future__ import annotations
import json
import warnings


class CalibrationConfig:
    def __init__(self, path: str):
        with open(path) as f:
            cfg = json.load(f)
        self.status = cfg.get("status", "PLACEHOLDER")
        self.table = cfg.get("per_population", {})   # {tool: {population: in_calibration|out_of_calibration}}
        self._warned = False

    def is_placeholder(self) -> bool:
        return self.status == "PLACEHOLDER"

    def status_for(self, tool: str, population: str, strict: bool) -> str:
        if self.is_placeholder():
            if strict:
                raise RuntimeError(
                    "Calibration config is a PLACEHOLDER; refusing to run in strict mode. "
                    "A domain owner must supply per-population calibration targets "
                    "(DEFINITIONS.md sec 3 / sec 4).")
            if not self._warned:
                warnings.warn(
                    "Calibration PLACEHOLDER: every result stamped 'calibration_pending' "
                    "(domain owner must set real per-population targets).")
                self._warned = True
            return "calibration_pending"
        return self.table.get(tool, {}).get(population, "out_of_calibration")
