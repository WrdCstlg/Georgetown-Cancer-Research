"""Populate the LOCAL EVE score cache (SPEC-005 part 2, SPEC-027).

DEV TOOLING -- outside the five-layer model (ARCHITECTURE.md sec 5). Imports
nothing from producers/, core/, or query/: it writes a documented JSON file and
the producer reads it. The seam between them is the FILE FORMAT, not shared code.

WHY A FETCHER AND NOT A COMMITTED FIXTURE
evemodel.org states its data falls under the MIT License, but the LICENSE.txt it
serves is copyrighted to the SITE's author rather than to the Marks Lab / OATML
who produced the predictions -- so whether it governs the prediction DATA is
unsettled (decision D3). This repo therefore applies the SAME no-commit
discipline it applies to AlphaMissense: fetch locally, commit nothing.

RETRIEVAL
Not a bulk file. evemodel.org is a React SPA over a JSON API:
    /api/proteins/list/                      -> every published protein (entry names)
    /api/proteins/web_pid/<ENTRY_NAME>/id/   -> internal numeric id
    /api/proteins/id/<id>/                   -> every variant for that protein
Standard library only (urllib + json): no new runtime dependency. The service
returns 502/504 intermittently on larger proteins, so every call retries with
backoff -- a transient gateway error must never look like missing coverage.

Usage (from the repo root):
    python tools/eve/fetch_scores.py
    python tools/eve/fetch_scores.py --entry-names P53_HUMAN,RASK_HUMAN
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "https://evemodel.org"
SERVICE = "evemodel.org API (/api/proteins/id/<id>/)"
LICENCE = "MIT as stated by the site -- provenance caveat in docs/eve-data.md; OPEN under D3"

DEFAULT_OUT = os.path.join(ROOT, ".cache", "eve", "scores.json")
IDENTIFIERS = os.path.join(ROOT, "fixtures", "variant_effect", "identifiers.json")

_requests = 0
_bytes = 0


def _get(path, tries=5, timeout=300):
    global _requests, _bytes
    last = None
    for attempt in range(tries):
        _requests += 1
        try:
            req = urllib.request.Request(
                BASE + path,
                headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            _bytes += len(data)
            return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if attempt == tries - 1:
                break
            wait = 3 * (attempt + 1)
            print(f"    (retry {attempt + 1}/{tries - 1} after {type(e).__name__}; "
                  f"sleeping {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"{path} failed after {tries} attempts: {type(last).__name__}: {last}")


def published_proteins():
    return json.loads(_get("/api/proteins/list/"))


def protein_rows(entry_name):
    pid = int(_get(f"/api/proteins/web_pid/{entry_name}/id/", timeout=120))
    blob = json.loads(_get(f"/api/proteins/id/{pid}/"))
    return blob.get("protein_position_variants", [])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--entry-names", default=None,
                    help="comma-separated UniProt entry names; default: those in "
                         "the identifier fixture")
    ap.add_argument("--retrieved-on", default=None,
                    help="ISO date recorded in the cache (default: today, UTC)")
    args = ap.parse_args()

    if args.retrieved_on:
        retrieved_on = args.retrieved_on
    else:
        from datetime import datetime, timezone
        retrieved_on = datetime.now(timezone.utc).date().isoformat()

    if args.entry_names:
        wanted = [e.strip() for e in args.entry_names.split(",") if e.strip()]
    else:
        with open(IDENTIFIERS, encoding="utf-8") as f:
            variants = json.load(f)["variants"]
        wanted = sorted({v["uniprot_entry_name"] for v in variants.values()
                         if v.get("uniprot_entry_name")})

    print(f"source  : {SERVICE}")
    print(f"licence : {LICENCE}")
    print(f"fetching: {len(wanted)} proteins\n")

    available = set(published_proteins())
    scores, absent, unscored_keys = {}, [], []
    for entry in wanted:
        if entry not in available:
            absent.append(entry)
            print(f"  {entry:<16} NOT PUBLISHED BY EVE (recorded as no-coverage)")
            continue
        rows = protein_rows(entry)
        kept = 0
        for r in rows:
            pv = f"{r['wt_aa']}{r['position']}{r['mt_aa']}"
            s = r.get("EVE_scores_ASM")
            if s in ("", None):
                # RECORD these. EVE publishing a row but assigning no score is a
                # distinct no-coverage state from "protein absent" and from
                # "not missense"; dropping them would make it indistinguishable
                # from a key that is genuinely missing, which must RAISE.
                unscored_keys.append(f"{entry}/{pv}")
                continue
            scores[f"{entry}/{pv}"] = {
                "eve_score": float(s),
                "eve_class": r.get("EVE_classes_75_pct_retained_ASM"),
                "uncertainty": float(r["uncertainty_ASM"]) if r.get("uncertainty_ASM") not in ("", None) else None,
                "clinvar": r.get("ClinVar_ClinicalSignificance") or "",
                "gnomad_freq": r.get("frequency_gv2") or "",
            }
            kept += 1
        print(f"  {entry:<16} {kept} scored substitutions ({len(rows) - kept} rows unscored)")

    blob = {
        "_licence": LICENCE,
        "_warning": "EVE prediction data. DO NOT COMMIT. This path is gitignored "
                    "(see .gitignore, docs/eve-data.md).",
        "source": SERVICE,
        "retrieved_on": retrieved_on,
        "proteins_published": sorted(available & set(wanted)),
        "proteins_requested_but_absent": absent,
        "unscored_keys": sorted(unscored_keys),
        "scores": scores,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(blob, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"\nwrote {len(scores)} scored substitutions to {args.out}")
    if absent:
        print(f"NOT PUBLISHED BY EVE ({len(absent)}): {', '.join(absent)}")
        print("  -> these are a COVERAGE fact, not a fetch failure (decision D-009).")
    print(f"rows EVE published but left unscored: {len(unscored_keys)} (recorded as a distinct no-coverage state)")
    print(f"HTTP requests: {_requests}, {_bytes / 1e6:.1f} MB transferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
