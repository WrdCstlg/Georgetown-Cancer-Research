# producers/variant_effect — Phase 2: VUS reclassification (multi-tool consensus)

**One job:** take variants classified VUS and reclassify them by consensus over
**AlphaMissense + EVE** (structure/evolution, clinical-DB-independent) plus **PolyPhen + SIFT**.
This is the first shippable result — it runs on the 150-tumor preliminary VUS set and targets
the ~90% → ~25–30% VUS reduction.

## Boundaries (ARCHITECTURE.md §4)
Reads a variant view, writes a provenance-tagged result. **Never imports another producer, the
query layer, or the interface.** Score tools are **injected providers** (`providers.py`), so real
databases plug in without touching the consensus logic.

## Guardrails baked in
- **Per-population calibration** (`calibration.py`): the tools are European-calibrated. Until a
  domain owner supplies real per-population targets (`DEFINITIONS.md` §3–§4, `[TO BE DEFINED]`),
  every result is stamped `calibration_pending` and must render **with that caveat** — never as a
  clean call (guardrail R1/S1).
- **Placeholder thresholds fail loudly**: consensus cutoffs live in `config/variant_effect.json`
  marked `PLACEHOLDER`; `strict=True` hard-fails so this can never silently ship on invented
  cutoffs (control I3).
- **Circularity break**: structure/evolution tools call novel variants absent from ClinVar/COSMIC.
  The fixture includes `clinical_db_absent` variants that still get a call — proving the European-
  database circularity is broken.
- **No fabricated scores**: real providers are stubbed to raise (`NotImplementedError`) until wired
  (control G2).

## Files
```
producers/variant_effect/reclassify.py    # the consensus engine (the one job)
producers/variant_effect/providers.py     # injected score interface + fixture/real providers
producers/variant_effect/calibration.py   # per-population calibration flagging
contracts/variant_effect.py               # the seam: input view + result objects
config/variant_effect.json                # consensus thresholds (PLACEHOLDER)
config/calibration.json                   # per-population calibration targets (PLACEHOLDER)
fixtures/variant_effect/                   # golden known-input -> known-output
tests/test_variant_effect.py              # the golden fixture test (G4)
```

## Run the golden fixture
```bash
python tests/test_variant_effect.py       # direct execution is the supported path
# (pytest compatibility UNVERIFIED — never executed end-to-end here, SPEC-016)
```

## Wiring real tools (deployment)
Replace the fixture providers with the real ones in `providers.py` (`AlphaMissenseProvider`,
`EVEProvider`, `PolyPhenProvider`, `SIFTProvider`) and point them at the score sources. The
consensus engine, calibration flags, and provenance do not change. **Before a production run**,
a domain owner must fill the `PLACEHOLDER` configs and you flip `strict=True`.
