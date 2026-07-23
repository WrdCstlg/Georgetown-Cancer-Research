# AGENTS.md — working rules for this repo

> This is the repo-resident manual for any coding agent (Claude Code, Cursor, etc.) and for human contributors.
> It **complements** `AfriCAN_DANCE_Coding_Agent_System_Prompt.md`: the system prompt is the contract and philosophy; this file is the concrete, repo-specific enforcement. Where they overlap, both apply.

## 0 · Ground truth

Read before acting. Never contradict these; never reconstruct a missing one from memory — **stop and request it**.

- `ARCHITECTURE.md` — the architecture and the separation-of-concerns rules (binding).
- `DEFINITIONS.md` — domain criteria. **You implement these; you never author or modify them.**
- `docs/build-plan.md` — what to build and in what order.
- `docs/risk-and-agent-control.md` — the risk register and control protocol (G1–I6).
- `docs/sources/` — the R01 grant strategy and AI-integration PDFs (grant strategy is authoritative for the science).
  **Readable copy:** `docs/sources/Domestic_Project_Research_Strategy_PF5.txt` is the dependency-free text transcription of the grant strategy — use it for grounding. The PDF remains canonical; reading any PDF requires a PDF library (e.g. pypdf) that is **not pinned** in this repo.

## Environment — read this before running anything

- **Shell: PowerShell.** On Windows, `python` fails under Git Bash with a Cygwin fork error (exit 0xC0000142). Run all Python from PowerShell, from the repo root — e.g. `python tests\test_variant_effect.py`.
- **Path: no spaces.** The repo must live at a path with no spaces (current: `C:\dev\Georgetown-Cancer-Research`).
- **Python:** 3.14.0 is installed and is what the suites were verified on. The code's actual floor is **3.8** (the walrus operator in `producers/variant_effect/reclassify.py`; everything else is 3.7-compatible). *The floor claim is under review — decision D-003 (PROPOSED); CI currently tests both 3.8 and 3.14.*
- **No install step.** The test suites are standard-library only; there is nothing to install to run them. No lockfile exists yet (tracked as a follow-up — G2).
- **Installed but NOT pinned and NOT required by the tests:** pytest 9.0.2 (convenience runner; both suites also run as plain scripts) and pypdf 6.11.0 (only needed to read the PDFs in `docs/sources/`; the `.txt` copy above is the dependency-free path). A fresh machine may lack both; the tests depend on neither.

## 1 · Separation of concerns — boundaries you must not cross

The repo is organized by concern (`ARCHITECTURE.md` §3–§5). These boundaries are hard rules; violating one is a rejected change, not a style nit.

1. **Code lives in the layer that owns its concern.** A calling change is `pipeline/calling/`; a persistence change is `core/`; an analysis is a producer. No convenience placement.
2. **Producers are isolated.** A producer may depend on: core contracts (read views + ingest), `DEFINITIONS.md`/`config`, and shared libs. **It may never import, call, or reference another producer**, the query layer, or the interface.
3. **Write path ≠ read path.** Pipeline and producers **write** to the core (via the ingest contract). Query and interface only **read**. The query layer never writes; a producer never reaches the interface.
4. **Depend on contracts, not internals.** Nothing outside `core/` may touch the core's internal tables — only the schema/ingest/read-view contracts in `contracts/`. Nothing depends on the interface.
5. **Domain criteria are injected, never hardcoded.** Thresholds, "ancestry-enriched", "actionable", calibration targets come from `DEFINITIONS.md`/`config`. A hardcoded domain constant in a producer is a rejected change.
6. **Provenance is centralized.** Every write emits lineage + model version + `n` + method + **per-population calibration status** through `core/provenance/`. No producer invents its own provenance format.
7. **Language boundaries are file contracts.** R / Python / Nextflow / SQL exchange data only via `contracts/io-contracts/` (Parquet/Arrow). No reaching into another runtime.
8. **Definitions/config reciprocity.** Any change to a domain value in `config/` requires updating `DEFINITIONS.md` in the SAME commit, and vice versa. The two never drift.

## 2 · How you work (the gates)

Condensed from the control protocol; the full statements are in `docs/risk-and-agent-control.md` and the system prompt.

**Ground the build**
- **G1 · Retrieve before edit** — quote the file/signature's actual current contents before changing it. No edits from memory.
- **G2 · Closed-world deps** — pinned/locked only; cite real signatures; if an API isn't in the pinned version, say so, don't invent it. Type-check/lint gate every symbol.
- **G3 · Execution is the arbiter** — "it works" is not evidence; attach a run / passing test / clean type-check. No artifact ⇒ SPECIFIED, not FUNCTIONAL.
- **G4 · Golden fixtures** — respect `fixtures/` (e.g. 150-tumor prelim → expected VUS reduction & driver calls). A change that alters a fixture output fails until justified.
- **G5 · Bounded diffs** — one concern per change; state blast radius; no large multi-file generative rewrites.
- **G6 · Strongest controls on the novel components** — `producers/gnn`, `producers/causal`, `producers/multimodal_predictor`: fixtures + execution evidence + expert-pinned criteria, no exceptions.

**Ground the intent**
- **I1 · Restate and halt** — echo the task and its acceptance criteria; stop for confirmation before writing code.
- **I2 · Executable acceptance criteria** — "done" is a check passing, not narration; decompose prose intent into checks first.
- **I3 · Implement definitions, never author them** — see §1.5. Missing definition ⇒ stop and request it.
- **I4 · Surface at forks** — unspecified decision ⇒ log a decision record and stop; never bury "I assumed X".
- **I5 · Adversarial review** — a separate pass hunts spec divergence; write so divergence is easy to see. Don't grade your own homework.
- **I6 · Traceability** — every module → spec item → aim → R01 objective. The registry of spec items is `SPEC.md` (repo root): every change cites a SPEC- ID from it, and new work adds its spec item to `SPEC.md` BEFORE code. Orphan code or orphan spec fails review.

## 3 · Commands

> Run from the repo root, in **PowerShell** (see §Environment). Run them and paste output — never claim done without it (G3).

```powershell
# quality gates (run before marking anything done)
python tests\test_variant_effect.py   # golden fixtures (G4) + producer guardrails
python tests\test_core_ingest.py      # core write path + provenance enforcement
# equivalent convenience runner (NOT pinned, NOT required): python -m pytest tests\ -q

# lint        — NOT CONFIGURED. Do not fabricate a command; if you need one, log a decision record and stop (I4).
# typecheck   — NOT CONFIGURED. Do not fabricate a command; if you need one, log a decision record and stop (I4).
# install     — NOT NEEDED: the test suites are standard-library only. No lockfile exists yet (follow-up — G2).

# pipeline / db / R
# NOT APPLICABLE YET — pipeline/, query/, and interface/ are empty layers; the core dev target is
# embedded SQLite exercised by the tests above; no R code exists in the repo.
```

## 4 · Definition of done

A unit of work is complete only when **all** hold:
1. it lives in the correct concern/layer (§1);
2. it traces to a confirmed spec item in `SPEC.md` (I6);
3. its executable acceptance criteria pass (I2);
4. an execution artifact is attached — test / type-check / run (G3);
5. golden fixtures still pass, or the change is justified (G4);
6. any fork was logged as a decision record (I4).

Otherwise it is **SPECIFIED, not FUNCTIONAL**.

## 5 · Commit / PR conventions

- **One concern per PR.** If it spans layers, it's too big — split it or it's a contract change (get review).
- PR description states: the spec item it satisfies, its blast radius, and the execution artifact.
- Contract changes (`contracts/`) are flagged explicitly and list every downstream layer they touch.
- Decision records for any fork resolved (I4).

## 6 · Stop and ask — do not proceed if

- a canonical file (§0) is missing from context;
- a domain definition you need is absent from `DEFINITIONS.md`/`config` (I3);
- the spec doesn't cover a fork you've hit (I4);
- a change would cross a §1 boundary;
- you cannot produce an execution artifact for a change (G3).

## 7 · Scientific guardrails you must honor

From the risk register — these are correctness requirements, not preferences:

- **Don't launder bias.** European-calibrated tools (AlphaMissense, EVE, GDSC/CCLE/DepMap, ClinVar/COSMIC) carry a per-population calibration flag; out-of-calibration results render with the caveat, never as a clean number.
- **Pre-screen only adds, never subtracts** PDO-drug combinations.
- **Confounders (SES, collection-site, environment) are modeled** wherever a causal/association claim is made.
- **No leakage** — hold out whole organoid lines; report out-of-sample intervals.
- **Causal claims carry their exact ground-truth scope** — isogenic CRISPR ≠ patient-level or immunotherapy claim.
- **Ancestry is continuous and per-population** — never silently collapse to race or a monolithic "African" group.
- **Disconfirmation is a first-class output.**
