"""tools/status-ui shim — read-only localhost HTTP over the query API (SPEC-018).

DEV TOOLING, not the interface/ layer. Standard library only; binds to
127.0.0.1; GET-only; never writes to the core or to any repo file. It MAY
import from query/ and core/db.py (persistence plumbing); it MUST NOT import
from producers/ or core/ingest (the write path).

Data source is the TOY FIXTURE (fixtures/query/core_rows.json), seeded into a
throwaway in-memory SQLite at startup — never real data. Every API response
says so.

Run from the repo root:  python tools/status-ui/serve.py [port]   (default 8017)
Then open http://127.0.0.1:8017/
"""
from __future__ import annotations
import json
import os
import sys
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from contracts.query import VariantEffectFilter, UndefinedCriterionError
from core.db import connect, apply_schema
from query.read_api import query_variant_effects, vus_summary

SCHEMA = os.path.join(ROOT, "core", "schema", "schema.sql")
SEED = os.path.join(ROOT, "fixtures", "query", "core_rows.json")
INDEX = os.path.join(ROOT, "tools", "status-ui", "index.html")
STATUS_JSON = os.path.join(ROOT, "docs", "status.json")

DATA_SOURCE = "toy fixture — fixtures/query/core_rows.json (NOT real data)"


def seed_core():
    """Build a throwaway in-memory core from the frozen fixture. Writes go to
    RAM only; the query API then reads v_variant_effect, never base tables."""
    with open(SEED, encoding="utf-8") as f:
        seed = json.load(f)
    con = connect(":memory:")
    apply_schema(con, SCHEMA)
    for p in seed["populations"]:
        con.execute("INSERT INTO population(code, description) VALUES (?,?)",
                    (p["code"], p["description"]))
    for v in seed["variants"]:
        con.execute(
            "INSERT INTO variant (variant_id, gene, protein_change, reference, "
            "population_code, clinical_db_absent) VALUES (?,?,?,?,?,?)",
            (v["variant_id"], v["gene"], v["protein_change"], v["reference"],
             v["population_code"], v["clinical_db_absent"]))
    for r in seed["results"]:
        con.execute(
            "INSERT INTO variant_effect_result "
            "(variant_id, original_classification, new_classification, producer, "
            " producer_version, method, n_tools_fired, reference, population_code, "
            " generated_at, calibration_status, calibration_pending, tool_calls_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["variant_id"], r["original_classification"], r["new_classification"],
             r["producer"], r["producer_version"], r["method"], 4, r["reference"],
             r["population_code"], r["generated_at"], r["calibration_status"],
             r["calibration_pending"], "[]"))
    con.commit()
    return con


def _meta():
    """Current HEAD + whether the committed status.json matches a fresh
    in-memory build. Read-only: build_status() writes nothing."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "generate_status", os.path.join(ROOT, "tools", "status", "generate_status.py"))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    fresh = gen.build_status()
    with open(STATUS_JSON, encoding="utf-8") as f:
        committed = json.load(f)
    return {"current_head": gen._head(), "status_in_sync": fresh == committed}


def _filter_from(params):
    """Map query-string params to a VariantEffectFilter. Refusal flags pass
    through — the query layer raises UndefinedCriterionError on them (I3)."""
    pops = params.get("population", [])
    truthy = lambda vals: any(v.strip().lower() in ("1", "true", "yes") for v in vals)
    return VariantEffectFilter(
        populations=tuple(p for p in pops if p),
        classification=(params.get("classification", [None])[0] or None),
        calibration_status=(params.get("calibration_status", [None])[0] or None),
        gene=(params.get("gene", [None])[0] or None),
        ancestry_enriched=truthy(params.get("ancestry_enriched", [])),
        actionable=truthy(params.get("actionable", [])),
        disconfirmation=truthy(params.get("disconfirmation", [])),
    )


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, ctype="application/json; charset=utf-8"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)
        if path == "/":
            with open(INDEX, "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif path == "/api/status":
            with open(STATUS_JSON, "rb") as f:
                self._send(200, f.read())
        elif path == "/api/meta":
            self._send(200, _meta())
        elif path in ("/api/query", "/api/summary"):
            self._query(path, params)
        else:
            self._send(404, {"error": f"no such route: {path}"})

    def _query(self, path, params):
        try:
            filt = _filter_from(params)
            # a fresh throwaway in-memory core per request: the seeded
            # connection is thread-local (sqlite3 forbids cross-thread use),
            # and the shim keeps no state between requests
            con = seed_core()
            res = vus_summary(con, filt) if path == "/api/summary" \
                else query_variant_effects(con, filt)
        except UndefinedCriterionError as e:
            # a refusal is an explanation, not a failure (I3)
            self._send(422, {"refusal": str(e), "data_source": DATA_SOURCE})
            return
        except ValueError as e:
            self._send(400, {"error": str(e), "data_source": DATA_SOURCE})
            return
        self._send(200, {"data_source": DATA_SOURCE, "result": asdict(res)})

    # read-only: everything that is not GET is refused
    def _method_not_allowed(self):
        self._send(405, {"error": "read-only shim: GET only"})

    do_POST = do_PUT = do_PATCH = do_DELETE = _method_not_allowed

    def log_message(self, fmt, *args):
        sys.stderr.write("shim: " + fmt % args + "\n")


def make_server(port=8017):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8017
    srv = make_server(port)
    print(f"serving on http://127.0.0.1:{port}/  (data source: {DATA_SOURCE})")
    srv.serve_forever()
