"""Shim test (SPEC-018): the read-only localhost HTTP shim over the query API.

Starts the shim on an ephemeral port in a thread and asserts: it is GET-only
(non-GET -> 405), it never writes, refusal errors surface as explanations naming
the missing definition, a summary response carries the RESULT-LEVEL calibration
flag, and the query echo + data-source label are present.

Supported: python tests/test_status_ui_shim.py  (direct execution is the
supported, CI-enforced path; pytest compatibility is UNVERIFIED — never
executed end-to-end in this environment, SPEC-016)
"""
import http.client
import json
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_shim():
    """Import the shim by path (directory name contains a hyphen)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "status_ui_serve", os.path.join(ROOT, "tools", "status-ui", "serve.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SHIM = _load_shim()

_server = None
_port = None


def _start():
    global _server, _port
    _server = SHIM.make_server(0)               # ephemeral port, 127.0.0.1 only
    _port = _server.server_address[1]
    threading.Thread(target=_server.serve_forever, daemon=True).start()


def _stop():
    if _server:
        _server.shutdown()
        _server.server_close()


def _req(method, path):
    c = http.client.HTTPConnection("127.0.0.1", _port, timeout=10)
    c.request(method, path)
    r = c.getresponse()
    body = r.read()
    c.close()
    return r.status, body


def _get(path):
    status, body = _req("GET", path)
    return status, json.loads(body)


def setup():
    if _port is None:
        _start()


def test_get_only_refuses_writes():
    setup()
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        status, body = _req(method, "/api/query")
        assert status == 405, (method, status)
        assert b"GET only" in body


def test_query_returns_rows_echo_provenance_and_source_label():
    setup()
    status, payload = _get("/api/query?population=AA")
    assert status == 200
    assert "NOT real data" in payload["data_source"]
    res = payload["result"]
    assert [r["variant_id"] for r in res["rows"]] == ["q01", "q02"]
    assert "population_code IN (:pop0)" in res["query"]["sql"]
    assert res["query"]["params"] == {"pop0": "AA"}
    assert res["provenance"]["producers"] == ["variant_effect"]
    assert res["calibration_status"] == "calibration_pending"   # q01 pending, q02 out


def test_summary_carries_result_level_calibration_flag():
    setup()
    status, payload = _get("/api/summary")
    assert status == 200
    res = payload["result"]
    # the whole toy fixture mixes pending + out + in: pending must dominate
    assert res["calibration_status"] == "calibration_pending"
    assert res["summary"]["overall"]["n"] == 8
    assert set(res["summary"]["per_population"].keys()) == {"AA", "ETH", "GHA", "NHW"}


def test_refusal_surfaces_explanation_naming_definition():
    setup()
    for flag, name in (("ancestry_enriched", "ancestry-enriched"),
                       ("actionable", "actionable/druggable"),
                       ("disconfirmation", "disconfirmation criteria")):
        status, payload = _get(f"/api/query?{flag}=true")
        assert status == 422, (flag, status)
        assert "refusal" in payload
        assert name in payload["refusal"] and "domain owner" in payload["refusal"]
        assert "Traceback" not in payload["refusal"]


def test_invalid_population_is_a_clear_error():
    setup()
    status, payload = _get("/api/query?population=AFR")
    assert status == 400
    assert "error" in payload and "AA" in payload["error"]


if __name__ == "__main__":
    try:
        for _name, _fn in list(globals().items()):
            if _name.startswith("test_"):
                _fn()
                print(f"PASS {_name}")
        print("ALL SHIM TESTS PASSED")
    finally:
        _stop()
