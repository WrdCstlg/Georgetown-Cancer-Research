# core — the fusion substrate (persistence + provenance)

The stable center. Holds the canonical data model; enforces provenance +
per-population calibration on every write; exposes read views. Contains NO
analysis, ML, or presentation logic (ARCHITECTURE.md §3).

- `schema/schema.sql` — the data model. Provenance + calibration are NOT NULL,
  first-class columns: the DB refuses to store a prediction as a bare fact.
- `ingest/` — the WRITE path. The only way producer output enters the core;
  validates provenance before writing (`core/provenance/validate.py`).
- `provenance/` — the centralized provenance/calibration rule (cross-cutting).
- read path is `read_view()` / the `v_*` views — the query layer reads these,
  never the base tables.

Dev/CI runs on SQLite (embedded). Production is PostgreSQL (+ pgvector); the
schema is portable modulo the deltas noted in `schema/schema.sql`.

Run:  python tests/test_core_ingest.py   (direct execution is the supported path;
pytest compatibility UNVERIFIED — never executed end-to-end here, SPEC-016)
