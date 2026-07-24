# query — see ARCHITECTURE.md §3

The read path (layer 4a). Deterministic structured read API over the core's
`v_*` read views — **no natural language, no LLM** (docs/risk-and-agent-control.md
S5). A future NL front-end (SPEC-009) translates INTO this API, never around it.

- `read_api.py` — `query_variant_effects(con, filter)` and `vus_summary(con, filter)`.
  Every result echoes the exact SQL + bound values, carries a provenance summary,
  a result-level calibration caveat that survives aggregation, and the explicit
  population(s) covered. Queries needing a `[TO BE DEFINED]` definition raise
  `UndefinedCriterionError` rather than answering.
- NEVER writes; reads `v_*` views only; never imports from `producers/`.
- Contract shapes: `contracts/query.py`. Tests: `tests/test_query_read_api.py`
  (seeded from the frozen fixture `fixtures/query/core_rows.json`).
