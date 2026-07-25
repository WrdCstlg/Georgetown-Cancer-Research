# tools/status-ui — local dev dashboard (SPEC-018)

A LOCAL DEV DASHBOARD for the two developers on this repo. Not a product, not the
researcher UI — `interface/` stays empty and reserved (R7). Dev tooling, same
category as `tools/status/` (ARCHITECTURE.md §5).

## Run it (verified)

```powershell
# from the repo root
python tools/status-ui/serve.py        # serves on http://127.0.0.1:8017/
# then open http://127.0.0.1:8017/ in a browser
```

The shim is the only supported way to view the page: it serves `index.html`,
`docs/status.json` (`/api/status`), repo meta (`/api/meta`), and the read-only
query endpoints (`/api/query`, `/api/summary`). Opening `index.html` via
`file://` does NOT work (browsers block fetch from file) — the page detects this
and prints the shim command instead.

## What it renders, and from where

- **Section 1** — two toggled views over `docs/status.json` ONLY. No state is
  computed in the browser: node colors come from `layers[]`, producer slots from
  `producer_slots[]`, the SPEC table from `spec_items[]`. The header shows the
  current HEAD and whether committed status.json matches a fresh regeneration
  (`/api/meta`, computed by the shim in memory — nothing written).
- **Section 2** — `not_built`, fact + basis, unsoftened.
- **Section 3** — `open_decisions` + `undefined_definitions`, each with its
  owner, marked human-owned.
- **Section 4** — a form over the deterministic query API. The result panel
  shows, with equal prominence: the result-level calibration flag (top banner),
  the exact SQL + bound values, the provenance summary, and the rows. Refusals
  (undefined criteria) render as explanations naming the missing definition.
  Data source is labelled as the toy fixture throughout.

## The shim (serve.py)

Standard library `http.server` only; binds 127.0.0.1; GET-only (anything else →
405); never writes to the core or any repo file; seeds a fresh throwaway
in-memory core from `fixtures/query/core_rows.json` per request. Imports
`query/` + `core/db.py` only — never `producers/` or `core/ingest`.

Tests: `python tests/test_status_ui_shim.py` (CI-enforced like the others).
