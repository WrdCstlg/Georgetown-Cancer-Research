# tools/status — STATUS generator (SPEC-017)

`generate_status.py` regenerates `docs/status.json` and `docs/STATUS.md` from
repo state. Dev tooling, outside the five-layer model (ARCHITECTURE.md §5); not a
producer; imports nothing from `producers/`, `core/`, or `query/`. Standard
library only, no install step.

```bash
python tools/status/generate_status.py
```

**Determinism contract:** no timestamps, no absolute paths, no commit hashes in
the output — a value that changes on every commit would make drift-checking
impossible. `docs/STATUS.md` is a generated file: never edit it by hand; edit
this generator (prose lives here) and regenerate.

## `docs/status.json` — the stable contract (schema_version 1)

A UI consumes this file; the shape is designed for that consumer. Additive
changes only within a schema version; bump `schema_version` for anything else.

| Key | Type | Meaning |
|-----|------|---------|
| `schema_version` | int | Contract version (currently 1). |
| `spec_items` | array | Transcribed verbatim from SPEC.md: `{id, title, layer, aim, status, readiness}`. Status/Readiness are never assessed by the generator. |
| `layers` | array | `{name, state, evidence}` per layer (pipeline, core, producers, query, interface, tools); state = EMPTY/BUILT/PARTIAL computed from the filesystem + SPEC.md (rules in the generator docstring), evidence stated. |
| `producer_slots` | array | `{name, state}` for every producer slot in the ARCHITECTURE.md §5 map (BUILT/PLANNED transcribed). |
| `runs_today.suites` | array | `{file, command, test_count}` per suite; `test_count` is counted statically, never executed. |
| `runs_today.ci_checks` | array | CI job display names from `.github/workflows/tests.yml` (matrix expanded). CI is the source of truth for pass/fail. |
| `runs_today.pass_fail_source` | string | Always `"CI"`. |
| `runs_today.note` | string | Human-readable caveat (direct execution, pytest unverified). |
| `not_built.empty_layers` | array | Layer dirs containing only a README (verified on disk). |
| `not_built.producer_dirs_present` | array | Producer slots that exist on disk. |
| `not_built.unwired_providers` | array | Provider classes whose body raises `NotImplementedError`, each with a file:line citation. |
| `not_built.placeholder_configs` | array | `config/*.json` files marked `"status": "PLACEHOLDER"`, with file:line citation. |
| `not_built.real_data_processed` | object | `{value, basis}` — false while no `data/` directory exists. |
| `not_built.production_database` | object | `{value, basis}` — false; substrate pending D4. |
| `not_built.nl_query` | object | `{value, basis}` — false while SPEC-009 is SPECIFIED. |
| `open_decisions` | array | `{id, title, status, owner}` from docs/DECISIONS.md sections with an OPEN/PROPOSED status line; owner transcribed per the documented rule (generator docstring). |
| `undefined_definitions` | array | `{definition, owner}` — first cell of each DEFINITIONS.md row marked `[TO BE DEFINED]`; owner from DEFINITIONS.md's header (domain experts). |
| `data_inventory` | object | `{source, study_datasets, public_resources, rows_fully_unknown, note}` — counts from the human-owned `docs/DATA-INVENTORY.md`. |

## The drift gate

The CI job `status-drift` (`.github/workflows/tests.yml`) runs the generator and
fails if either artifact differs from the committed version. Fix by running the
generator and committing the result — never by editing the artifacts.
