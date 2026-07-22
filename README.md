# AfriCAN DANCE — Insight-Distillation System

The computational layer for the AfriCAN DANCE study: an **ancestry-aware colorectal-cancer genomics** platform that fuses whole-exome, transcriptomic, organoid, and clinical data into one queryable, provenance-tagged substrate — so researchers can distil cross-modal insight instead of joining seven separate outputs by hand.

**Status:** early build. Phase 2 (VUS reclassification on the 150-tumor preliminary data) ships first; see the build plan.

## The idea in two sentences

The bottleneck to seeing clearly isn't a shortage of models — it's that every modality lives in a separate file. So the spine is a **fusion substrate with provenance**; fast probabilistic producers hang off it, a grounded query layer reads it, and the wet lab is the physical ground truth.

## Canonical documents — read these first

| Doc | What it governs |
|-----|-----------------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture, layer boundaries, separation-of-concerns rules, module map |
| [`docs/build-plan.md`](docs/build-plan.md) | What gets built, in what order, with phase gates |
| [`docs/risk-and-agent-control.md`](docs/risk-and-agent-control.md) | Risk register, second-order failure modes, the control protocol |
| [`AGENTS.md`](AGENTS.md) | How to work in this repo (humans and coding agents) |
| [`DEFINITIONS.md`](DEFINITIONS.md) | Domain criteria — **owned by domain experts; the agent must not author them** |
| [`docs/sources/`](docs/sources/) | The R01 grant strategy and AI-integration source PDFs |

## Repository structure

Organized strictly by **concern** (see `ARCHITECTURE.md` §5). The five layers:

```
pipeline/    1 · data production        (Nextflow / nf-core)
core/        2 · persistence + provenance (Postgres — the substrate)
producers/   3 · analysis — isolated plugins, compose only via the core
query/       4a · read path — grounded NL to SQL (never writes)
interface/   4b · presentation
```

Plus `contracts/` (the seams between layers), `DEFINITIONS.md` + `config/` (domain criteria + reproducibility), `fixtures/` (golden test data), `tests/`, `docs/`.

## Getting started

> Toolchain versions are pinned in `config/`. Specifics land as Phase 0/1 is implemented — this is the shape, not final commands.

Prerequisites:
- **Nextflow** + a container runtime (Singularity/Docker) for the pipeline
- **Python** (pinned via lockfile) for producers, query, ML
- **R / Bioconductor** for statistical genomics
- **PostgreSQL** (+ `pgvector`) for the fusion core

```bash
# 1 · clone and enter
git clone <repo> && cd africandance

# 2 · pinned environments (exact commands in config/)
#     python: <locked install>      r: <renv restore>      db: <migrations>

# 3 · bring up the core schema
#     apply core/schema migrations against a local Postgres

# 4 · run the golden fixtures (must pass before anything else is trusted)
#     <fixture command>   # see fixtures/ and AGENTS.md §Commands
```

## Build order

Substrate first, cheapest high-leverage win next, ambitious models last (gated on wet-lab data). Full sequence and phase gates in [`docs/build-plan.md`](docs/build-plan.md). **Phase 2 runs on data that already exists** (the 150-tumor preliminary set) — it's the first demonstrated result.

## Working in this repo

This project runs on a verification discipline, not on trust. Every change must:
- live in the layer that **owns its concern** (no cross-boundary code),
- **trace to a spec item**,
- pass its **executable acceptance criteria** and the **golden fixtures**,
- ship with an **execution artifact** (test / type-check / run).

Until those hold, a change is **SPECIFIED, not FUNCTIONAL**. Full rules — including the separation-of-concerns boundaries a coding agent must never cross — are in [`AGENTS.md`](AGENTS.md).

## License / data governance

Human-subjects data under IRB; cross-site (Ghana/Ethiopia) specimens carry data-use constraints. See `docs/` and settle Phase-0 decisions before ingesting real data.
