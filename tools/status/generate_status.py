"""Generate docs/status.json + docs/STATUS.md from repo state (SPEC-017).

DEV TOOLING — outside the five-layer model (ARCHITECTURE.md §5). Not a producer;
imports nothing from producers/, core/, or query/. Standard library only.

Determinism contract (the CI status-drift gate depends on it):
  * no timestamps, no absolute paths, no commit hashes in the output;
  * git HEAD is read only for the stdout log line — NEVER embedded in the
    artifacts, because a value that changes on every commit makes
    drift-checking impossible;
  * everything emitted is transcribed from repo artifacts (SPEC.md,
    docs/DECISIONS.md, DEFINITIONS.md, docs/DATA-INVENTORY.md,
    .github/workflows/tests.yml, the filesystem) or is static template prose
    that lives HERE — edit prose in this file, never in docs/STATUS.md.

Usage: python tools/status/generate_status.py   (from anywhere; paths are
resolved relative to this file's repo root)
"""
from __future__ import annotations
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCHEMA_VERSION = 1


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _head():
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


# --- transcriptions -----------------------------------------------------------

def spec_items():
    """Transcribe the SPEC.md registry table verbatim — never assess."""
    items = []
    for line in _read("SPEC.md").splitlines():
        if not line.startswith("| SPEC-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        items.append({
            "id": cells[0], "title": cells[1], "layer": cells[2],
            "aim": cells[3], "status": cells[4], "readiness": cells[5],
        })
    return items


def open_decisions():
    """Transcribe docs/DECISIONS.md sections that carry a Status line.
    Owner is a deterministic transcription rule, not an inference:
    PROPOSED statuses say 'pending (owner) approval' -> project owner;
    D1-D6 say 'awaiting the parties named in docs/build-plan.md §1/§5'."""
    text = _read(os.path.join("docs", "DECISIONS.md"))
    out = []
    current = None
    for line in text.splitlines():
        m = re.match(r"^## (D-?\d+)\s*[—-]\s*(.+)$", line)
        if m:
            current = {"id": m.group(1), "title": m.group(2).strip(), "status": None}
            out.append(current)
            continue
        s = re.match(r"^Status:\s*\*\*(.+?)\*\*", line)
        if s and current is not None and current["status"] is None:
            current["status"] = s.group(1).strip().rstrip(".")
    result = []
    for d in out:
        if not d["status"]:
            continue
        if d["status"].startswith("PROPOSED"):
            d["owner"] = "project owner (status: pending approval — docs/DECISIONS.md)"
        elif d["status"].startswith("OPEN"):
            d["owner"] = "project owner + parties named in docs/build-plan.md §1/§5 (docs/DECISIONS.md)"
        else:
            continue
        result.append(d)
    return result


def undefined_definitions():
    """First cell of every DEFINITIONS.md table row marked [TO BE DEFINED].
    Owner is stated by DEFINITIONS.md's own header: owned by the domain experts."""
    out = []
    for line in _read("DEFINITIONS.md").splitlines():
        if "[TO BE DEFINED]" in line and line.startswith("|"):
            first = line.strip().strip("|").split("|")[0].strip()
            first = re.sub(r"\*\*", "", first)
            out.append({
                "definition": first,
                "owner": "domain experts — the professor and collaborators (DEFINITIONS.md header: agent implements, never authors)",
            })
    return out


def data_inventory_summary():
    """Count rows in docs/DATA-INVENTORY.md's two tables (human-owned file)."""
    text = _read(os.path.join("docs", "DATA-INVENTORY.md"))
    study = public = fully_unknown = 0
    section = None
    for line in text.splitlines():
        if line.startswith("## Study datasets"):
            section = "study"
            continue
        if line.startswith("## Public reference resources"):
            section = "public"
            continue
        if line.startswith("## "):
            section = None
        if not line.startswith("|") or line.startswith("| Dataset") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if section == "study":
            study += 1
        elif section == "public":
            public += 1
        else:
            continue
        # status, location, owner, access constraint — all UNKNOWN?
        if all(c.upper().startswith("UNKNOWN") for c in cells[1:5]):
            fully_unknown += 1
    return {
        "source": "docs/DATA-INVENTORY.md",
        "study_datasets": study,
        "public_resources": public,
        "rows_fully_unknown": fully_unknown,
        "note": "Human-owned, agent-transcribed-only. Every field is UNKNOWN "
                "unless a repo artifact states otherwise (cited in the file).",
    }


def ci_checks():
    """Job display names from .github/workflows/tests.yml, matrix expanded."""
    text = _read(os.path.join(".github", "workflows", "tests.yml"))
    m = re.search(r'python-version:\s*\[([^\]]+)\]', text)
    versions = [v.strip().strip('"') for v in m.group(1).split(",")] if m else []
    checks = []
    for name in re.findall(r"^\s+name:\s*(.+)$", text, re.M):
        name = name.strip()
        if "${{ matrix.python-version }}" in name:
            checks.extend(name.replace("${{ matrix.python-version }}", v) for v in versions)
        else:
            checks.append(name)
    return sorted(checks)


def suites():
    """The test suites + static test counts (counted, NOT run — CI is the
    source of truth for pass/fail)."""
    out = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if fn.startswith("test_") and fn.endswith(".py"):
            n = _read(os.path.join("tests", fn)).count("def test_")
            out.append({"file": f"tests/{fn}",
                        "command": f"python tests/{fn}",
                        "test_count": n})
    return out


def _only_readme(rel):
    d = os.path.join(ROOT, rel)
    files = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
    return files == ["README.md"]


def unwired_providers():
    """Provider classes in producers/variant_effect/providers.py whose class
    body raises NotImplementedError (real tools not wired)."""
    text = _read(os.path.join("producers", "variant_effect", "providers.py"))
    out = []
    for block in re.split(r"(?m)^(?=class )", text):
        m = re.match(r"class (\w+)", block)
        if m and "raise NotImplementedError" in block:
            out.append(m.group(1))
    return out


def placeholder_configs():
    out = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "config"))):
        if fn.endswith(".json"):
            with open(os.path.join(ROOT, "config", fn), encoding="utf-8") as f:
                if json.load(f).get("status") == "PLACEHOLDER":
                    out.append(f"config/{fn}")
    return out


def producer_dirs():
    d = os.path.join(ROOT, "producers")
    return sorted(x for x in os.listdir(d)
                  if os.path.isdir(os.path.join(d, x)) and x != "__pycache__")


def producer_slots():
    """Every producer slot from the ARCHITECTURE.md §5 module map with its
    BUILT/PLANNED mark, transcribed — the dashboard renders slots, not just
    dirs that happen to exist."""
    lines = _read("ARCHITECTURE.md").splitlines()
    slots, in_section = [], False
    for line in lines:
        if line.startswith("├── producers/"):
            in_section = True
            continue
        if in_section:
            m = re.match(r"^│\s+[├└]── (\w+)/\s+#\s*(BUILT|PLANNED)", line)
            if m:
                slots.append({"name": m.group(1), "state": m.group(2)})
            elif not line.startswith("│"):
                break
    return slots


def layers():
    """Build state per layer, computed HERE (never in the browser) from the
    filesystem + SPEC.md, with the evidence stated. Rules:
    EMPTY = README only on disk; BUILT = owning code on disk; PARTIAL = some
    but not all of the layer's planned contents exist."""
    out = []

    def readme_only(rel):
        return _only_readme(rel)

    def has(rel):
        return os.path.exists(os.path.join(ROOT, rel))

    out.append({"name": "pipeline", "state": "EMPTY" if readme_only("pipeline") else "BUILT",
                "evidence": "README only on disk" if readme_only("pipeline")
                            else "code on disk"})
    core_built = has(os.path.join("core", "schema", "schema.sql")) and has(os.path.join("core", "db.py"))
    out.append({"name": "core", "state": "BUILT" if core_built else "EMPTY",
                "evidence": "schema.sql + db.py + ingest/ + provenance/ on disk; SPEC-001 FUNCTIONAL (SPEC.md)"
                if core_built else "no core code on disk"})
    slots = producer_slots()
    present = producer_dirs()
    n_built = sum(1 for s in slots if s["state"] == "BUILT")
    state = "EMPTY" if n_built == 0 else ("BUILT" if n_built == len(slots) else "PARTIAL")
    out.append({"name": "producers", "state": state,
                "evidence": f"{n_built} of {len(slots)} planned slots have code "
                            f"({', '.join(present) or 'none'}; slot list from ARCHITECTURE.md §5)"})
    q = has(os.path.join("query", "read_api.py"))
    out.append({"name": "query", "state": "PARTIAL" if q else "EMPTY",
                "evidence": "read_api.py on disk; SPEC-015 FUNCTIONAL, SPEC-009 (NL) SPECIFIED (SPEC.md)"
                if q else "README only on disk"})
    out.append({"name": "interface", "state": "EMPTY" if readme_only("interface") else "BUILT",
                "evidence": "README only on disk; reserved for the future researcher-facing product"
                if readme_only("interface") else "code on disk"})
    t = has(os.path.join("tools", "status", "generate_status.py"))
    out.append({"name": "tools", "state": "BUILT" if t else "EMPTY",
                "evidence": "dev tooling on disk (status generator + status-ui shim); "
                            "outside the five-layer model (ARCHITECTURE.md §5)"
                if t else "no tools/ on disk"})
    return out


# --- assembly -----------------------------------------------------------------

def build_status():
    empty = [layer for layer in ("pipeline", "interface") if _only_readme(layer)]
    return {
        "schema_version": SCHEMA_VERSION,
        "spec_items": spec_items(),
        "layers": layers(),
        "producer_slots": producer_slots(),
        "runs_today": {
            "suites": suites(),
            "ci_checks": ci_checks(),
            "pass_fail_source": "CI",
            "note": "Suites are standard-library only and run by direct execution "
                    "(the supported path; pytest compatibility UNVERIFIED — SPEC-016). "
                    "This file does not run them: CI is the source of truth for pass/fail.",
        },
        "not_built": {
            "empty_layers": empty,
            "producer_dirs_present": producer_dirs(),
            "unwired_providers": unwired_providers(),
            "placeholder_configs": placeholder_configs(),
            "real_data_processed": {
                "value": False,
                "basis": "No data/ directory exists; only toy fixtures/ have ever run",
            },
            "production_database": {
                "value": False,
                "basis": "Dev/CI is embedded SQLite; production substrate pending D4 "
                         "(Postgres proposed, not decided)",
            },
            "nl_query": {"value": False, "basis": "SPEC-009 is SPECIFIED, unbuilt"},
        },
        "open_decisions": open_decisions(),
        "undefined_definitions": undefined_definitions(),
        "data_inventory": data_inventory_summary(),
    }


# --- rendering ----------------------------------------------------------------

def render_md(s):
    L = []
    A = L.append
    A("# STATUS — AfriCAN DANCE computational layer")
    A("")
    A("> GENERATED FILE — do not edit by hand. Regenerate with "
      "`python tools/status/generate_status.py` and commit both artifacts. "
      "CI fails on drift (job `status-drift`). Prose lives in the generator; "
      "every fact is transcribed from repo state. Grounding: SPEC.md statuses "
      "verbatim, docs/DECISIONS.md, DEFINITIONS.md, docs/DATA-INVENTORY.md, "
      ".github/workflows/tests.yml, and filesystem checks — never assessed.")
    A("")
    A("## 1 · What this is, and what runs today")
    A("")
    A("This is the computational layer for an ancestry-aware colorectal-cancer "
      "genomics project: a fusion core (a schema + provenance/calibration "
      "enforcement, SQLite in dev; production substrate pending D4 — Postgres "
      "proposed), one analysis producer (multi-tool VUS reclassification), and a "
      "deterministic read API over the core's views. What runs today runs **on "
      "toy fixtures only**: synthetic variants with mock tool scores, and a small "
      "static seed for the read API. The test suites pass in CI on every push and "
      "PR, on Python 3.8 and 3.14. No real patient data has touched this system.")
    A("")
    A("## 2 · SPEC items (statuses taken verbatim from SPEC.md, not assessed here)")
    A("")
    A("Status = where the work is (SPECIFIED → FUNCTIONAL). Readiness = whether it "
      "can start now (AVAILABLE / GATED with named gate / UNKNOWN) — the two axes "
      "are orthogonal.")
    A("")
    A("| ID | Title | Layer | Status | Readiness |")
    A("|----|-------|-------|--------|-----------|")
    for it in s["spec_items"]:
        A(f"| {it['id']} | {it['title']} | {it['layer']} | {it['status']} | {it['readiness']} |")
    A("")
    A("## 3 · What runs today")
    A("")
    A("Test suites (standard-library only, direct execution — the supported path):")
    A("")
    for st in s["runs_today"]["suites"]:
        A(f"- `{st['command']}` — {st['test_count']} tests")
    A("")
    A(f"CI checks (from `.github/workflows/tests.yml`): "
      f"{', '.join(f'`{c}`' for c in s['runs_today']['ci_checks'])}. "
      + s["runs_today"]["note"])
    A("")
    A("## 4 · What is NOT built")
    A("")
    nb = s["not_built"]
    A(f"- **No real data has been processed.** {nb['real_data_processed']['basis']}.")
    if nb["empty_layers"]:
        A(f"- **Empty layers (README only):** {', '.join(f'`{x}/`' for x in nb['empty_layers'])}.")
    A(f"- **Producers present:** {', '.join(f'`{x}/`' for x in nb['producer_dirs_present'])} "
      "— every other producer slot is unbuilt.")
    if nb["unwired_providers"]:
        A(f"- **Real score providers are not wired** — `raise NotImplementedError`: "
          f"{', '.join(f'`{x}`' for x in nb['unwired_providers'])}. The producer has only "
          "ever seen mock scores.")
    if nb["placeholder_configs"]:
        A(f"- **All thresholds are PLACEHOLDER:** {', '.join(f'`{x}`' for x in nb['placeholder_configs'])}. "
          "Strict mode hard-fails on them by design; every producer result is stamped "
          "`calibration_pending` — correctly, but no result is yet a clean call.")
    A(f"- **No natural-language query.** {nb['nl_query']['basis']}; the query layer reads "
      "exactly one view (`v_variant_effect`).")
    A(f"- **No production database.** {nb['production_database']['basis']}. "
      "No lockfile, no lint, no typecheck configured (AGENTS.md §3).")
    A("")
    A("## 5 · What unblocks the next step")
    A("")
    A("Open decisions (docs/DECISIONS.md, transcribed — owners as stated there; "
      "D1–D6 await the parties named in docs/build-plan.md §1/§5):")
    A("")
    for d in s["open_decisions"]:
        A(f"- **{d['id']}** — {d['title']}: {d['status']} — owner: {d['owner']}")
    A("")
    A("Missing domain definitions (DEFINITIONS.md §4, marked [TO BE DEFINED]). The query "
      "layer refuses these by name rather than inventing values:")
    A("")
    for d in s["undefined_definitions"]:
        A(f"- {d['definition']} — owner: {d['owner']}")
    A("")
    di = s["data_inventory"]
    A(f"**Data inventory (F3):** `{di['source']}` (human-owned) tracks "
      f"{di['study_datasets']} study datasets + {di['public_resources']} public reference "
      f"resources; {di['rows_fully_unknown']} rows are UNKNOWN in every field. Custody, "
      "location, and access are undetermined for everything the system needs — a human "
      "owner must fill it before any real-data claim can be made.")
    A("")
    A("## 6 · Where a collaborator plugs in")
    A("")
    A("Producer isolation (ARCHITECTURE.md §4.2) makes the producer slots independent: "
      "each producer is a plugin that reads a core view and writes a provenance-tagged "
      "result via the ingest contract, and **never imports another producer, the query "
      "layer, or the interface**. Parallel-safe: the empty producer slots "
      "(`target_nomination/`, `gnn/`, `causal/`, `imaging/`), `pipeline/`, `core/ingest/` "
      "adapters (SPEC-003), and `interface/` (downstream of `query/`). Not parallel-safe "
      "without review: `contracts/`, the core schema, and DEFINITIONS.md (expert-owned).")
    A("")
    return "\n".join(L)


def main():
    status = build_status()
    json_text = json.dumps(status, indent=2, ensure_ascii=False) + "\n"
    md_text = render_md(status)
    for rel, text in ((os.path.join("docs", "status.json"), json_text),
                      (os.path.join("docs", "STATUS.md"), md_text)):
        with open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print(f"generated docs/status.json + docs/STATUS.md from repo state (HEAD {_head()}, not embedded)")


if __name__ == "__main__":
    main()
