"""Populate the LOCAL IntOGen compendium cache (SPEC-028).

DEV TOOLING -- outside the five-layer model (ARCHITECTURE.md sec 5). Imports
nothing from producers/, core/, or query/: it writes a documented JSON file and
the producer reads it. The seam is the FILE FORMAT, not shared code.

Retrieval is a single ~965 KB archive; standard library only (urllib + zipfile +
csv). NO new runtime dependency, and no range requests needed.

LICENCE: the archive bundles LICENSE.txt = CC0 1.0 Universal, a public-domain
dedication. Committing a slice WOULD be permitted -- unlike AlphaMissense
(CC BY-NC-SA) or EVE (unsettled). The cache pattern is used anyway, deliberately,
for consistency across providers; see decision D-013.

Usage (from the repo root):
    python tools/intogen/fetch_compendium.py
    python tools/intogen/fetch_compendium.py --genes KRAS,TP53 --scope COAD,READ
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

URL = "https://www.intogen.org/download?file=IntOGen-Drivers-20240920.zip"
SOURCE = "IntOGen Compendium_Cancer_Genes.tsv (intogen.org)"
LICENCE = "CC0 1.0 Universal (public domain) -- committing would be permitted; see D-013"

DEFAULT_OUT = os.path.join(ROOT, ".cache", "intogen", "compendium.json")

# The grant strategy's 15 named CRC driver "mountains"
# (docs/sources/Domestic_Project_Research_Strategy_PF5.txt line 332).
GRANT_GENES = ["APC", "BRAF", "CTNNB1", "FBXW7", "KRAS", "MLH1", "MSH2", "MSH6",
               "NRAS", "PIK3CA", "PMS2", "RNF43", "SMAD4", "TGFBR2", "TP53"]


def _download(tries=4):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if attempt == tries - 1:
                break
            wait = 3 * (attempt + 1)
            print(f"  (retry {attempt + 1}/{tries - 1} after {type(e).__name__}; "
                  f"sleeping {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"download failed after {tries} attempts: {last}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--genes", default=None,
                    help="comma-separated HGNC symbols; default: the grant's 15 CRC drivers")
    ap.add_argument("--scope", default=None,
                    help="comma-separated CANCER_TYPE values to keep; default: all "
                         "(the producer scopes at read time)")
    ap.add_argument("--retrieved-on", default=None)
    args = ap.parse_args()

    genes = [g.strip() for g in args.genes.split(",")] if args.genes else GRANT_GENES
    scope = set(s.strip() for s in args.scope.split(",")) if args.scope else None
    if args.retrieved_on:
        retrieved_on = args.retrieved_on
    else:
        from datetime import datetime, timezone
        retrieved_on = datetime.now(timezone.utc).date().isoformat()

    print(f"source  : {SOURCE}")
    print(f"licence : {LICENCE}")
    print(f"genes   : {len(genes)}\n")

    raw = _download()
    z = zipfile.ZipFile(io.BytesIO(raw))
    member = [n for n in z.namelist() if n.endswith("Compendium_Cancer_Genes.tsv")][0]
    release = member.split("/")[0]
    rows = list(csv.DictReader(
        io.TextIOWrapper(z.open(member), encoding="utf-8"), delimiter="\t"))

    out, kept_types = {}, set()
    for r in rows:
        g = r["SYMBOL"]
        if g not in genes:
            continue
        ct = r["CANCER_TYPE"]
        if scope and ct not in scope:
            continue
        kept_types.add(ct)
        try:
            q = float(r["QVALUE_COMBINATION"])
        except (TypeError, ValueError):
            q = None
        out.setdefault(g, []).append({
            "cohort": r["COHORT"],
            "cancer_type": ct,
            "role": r["ROLE"],
            "qvalue": q,
            "methods": r["METHODS"],
            "samples": r["SAMPLES"],
            "mutations": r["MUTATIONS"],
            "domains": r["DOMAINS"],
            "clusters_2d": r["2D_CLUSTERS"],
            "clusters_3d": r["3D_CLUSTERS"],
        })

    for g in genes:
        n = len(out.get(g, []))
        colo = sum(1 for r in out.get(g, []) if r["cancer_type"] in ("COAD", "READ"))
        print(f"  {g:<8} {n:>4} cohort rows   ({colo} colorectal)"
              + ("   -- ABSENT from colorectal" if colo == 0 else ""))

    blob = {
        "_licence": LICENCE,
        "_warning": "IntOGen compendium data. Not committed by convention (D-013), though CC0 "
                    "would permit it. This path is gitignored -- see docs/intogen-data.md.",
        "source": SOURCE,
        "release": release,
        "retrieved_on": retrieved_on,
        "cancer_types_present": sorted(kept_types),
        "genes": out,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(blob, f, indent=2, sort_keys=True)
        f.write("\n")

    total = sum(len(v) for v in out.values())
    print(f"\nwrote {total} cohort rows across {len(out)} genes to {args.out}")
    print(f"release: {release}   archive: {len(raw):,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
