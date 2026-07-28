"""Populate the LOCAL AlphaMissense score cache (SPEC-005, decision D-006).

DEV TOOLING -- outside the five-layer model (ARCHITECTURE.md sec 5). Imports
nothing from producers/, core/, or query/: it writes a documented JSON file and
the producer reads it. The seam between them is the FILE FORMAT, not shared code
(the same discipline as contracts/io-contracts/).

WHY A FETCHER AND NOT A COMMITTED FIXTURE
AlphaMissense predictions are CC BY-NC-SA 4.0 -- non-commercial, share-alike.
This repo commits NO AlphaMissense score data. Each developer fetches their own
copy into a gitignored cache. Redistribution and the NC term are OPEN under
decision D3; NC interacts with D1. See docs/alphamissense-data.md.

HOW IT AVOIDS A MULTI-GIGABYTE DOWNLOAD
`AlphaMissense_aa_substitutions.tsv.gz` is 1.2 GB, bgzip-compressed (a series of
independently-decompressable gzip members) and sorted lexicographically by
uniprot_id -- both VERIFIED against the published file, not assumed. So a binary
search over HTTP Range requests converges on the block range holding one
accession and decompresses only that. Fetching the whole file is never required.

Standard library only (urllib + zlib): no new runtime dependency.

Usage (from the repo root):
    python tools/alphamissense/fetch_scores.py
    python tools/alphamissense/fetch_scores.py --out .cache/alphamissense/scores.json
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RECORD = "Zenodo 10.5281/zenodo.8208688"
SOURCE_FILE = "AlphaMissense_aa_substitutions.tsv.gz"
URL = f"https://zenodo.org/records/8208688/files/{SOURCE_FILE}?download=1"
SIZE = 1207278510                       # bytes, from the Zenodo file manifest
LICENCE = "CC BY-NC-SA 4.0 (non-commercial, share-alike)"

WINDOW = 1 << 16                        # 64 KB probe window
SWEEP = 6 << 20                         # 6 MB contiguous sweep around a hit
BGZF_MAGIC = b"\x1f\x8b\x08\x04"

DEFAULT_OUT = os.path.join(ROOT, ".cache", "alphamissense", "scores.json")
IDENTIFIERS = os.path.join(ROOT, "fixtures", "variant_effect", "identifiers.json")
VARIANTS = os.path.join(ROOT, "fixtures", "variant_effect", "variants_input.csv")

# Deliberately duplicated from producers/variant_effect/alphamissense.py rather
# than imported: tools/ must not import producers/ (ARCHITECTURE.md sec 5). The
# seam between fetcher and producer is the cache FILE FORMAT, not shared code.
_MISSENSE_RE = re.compile(r"^(?:p\.)?([A-Z])(\d+)([A-Z])$")

_requests = 0
_bytes = 0


def _get(offset: int, length: int, attempts: int = 5) -> bytes:
    """One ranged read, with backoff. Zenodo intermittently returns 502/503/504
    on long sweeps; a transient gateway error must not look like missing data,
    because "no rows here" silently changes what the binary search concludes."""
    global _requests, _bytes
    end = min(offset + length - 1, SIZE - 1)
    req = urllib.request.Request(URL, headers={"Range": f"bytes={offset}-{end}"})
    last = None
    for attempt in range(attempts):
        _requests += 1
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                if r.status not in (200, 206):
                    raise RuntimeError(f"unexpected HTTP {r.status} for range {offset}-{end}")
                data = r.read()
            _bytes += len(data)
            return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if attempt == attempts - 1:
                break
            wait = 2 ** attempt
            print(f"    (retry {attempt + 1}/{attempts - 1} after {type(e).__name__}; "
                  f"sleeping {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(
        f"range {offset}-{end} failed after {attempts} attempts: {type(last).__name__}: {last}"
    ) from last


def _rows(raw: bytes, skip_leading: bool) -> list:
    """Decompress EVERY bgzip member in `raw` and return parsed data rows.

    Only the first member would be decoded by a single decompressobj; bgzip
    concatenates members, so we must follow `unused_data` to the next one.
    """
    start = raw.find(BGZF_MAGIC, 1 if skip_leading else 0)
    if start < 0:
        return []
    buf, chunks = raw[start:], []
    while buf:
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            chunks.append(d.decompress(buf))
        except zlib.error:
            break
        if not d.eof:
            break
        buf = d.unused_data
        if not buf.startswith(BGZF_MAGIC):
            break
    text = b"".join(chunks).decode("utf-8", "replace")
    out = []
    for line in text.splitlines()[1:-1]:            # drop possibly-partial first/last
        if not line or line.startswith("#") or line.startswith("uniprot_id"):
            continue
        f = line.split("\t")
        if len(f) == 4:
            out.append(f)
    return out


def _first_accession(offset: int):
    rows = _rows(_get(offset, WINDOW), skip_leading=bool(offset))
    return rows[0][0] if rows else None


def fetch_accession(uniprot_id: str) -> dict:
    """Return {protein_variant: {am_pathogenicity, am_class}} for one accession."""
    lo, hi = 0, SIZE
    while hi - lo > WINDOW:
        mid = (lo + hi) // 2
        acc = _first_accession(mid)
        if acc is None:
            lo = mid + WINDOW
            continue
        if acc < uniprot_id:
            lo = mid
        else:
            hi = mid
    found, offset = {}, max(0, lo - WINDOW)
    while offset < SIZE:
        rows = _rows(_get(offset, SWEEP), skip_leading=bool(offset))
        if not rows:
            break
        for acc, pv, score, cls in rows:
            if acc == uniprot_id:
                found[pv] = {"am_pathogenicity": float(score), "am_class": cls}
        if rows[-1][0] > uniprot_id:
            break
        offset += SWEEP
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--retrieved-on", default=None,
                    help="ISO date recorded in the cache (default: today, UTC)")
    ap.add_argument("--accessions", default=None,
                    help="comma-separated UniProt accessions; default: those in "
                         "the identifier fixture")
    ap.add_argument("--all-substitutions", action="store_true",
                    help="cache EVERY substitution for each accession, not just the "
                         "golden-fixture variants. Used by the driver-coverage probe "
                         "(docs/probes/) and to source benign controls. Still local and "
                         "gitignored -- nothing is redistributed.")
    args = ap.parse_args()

    if args.retrieved_on:
        retrieved_on = args.retrieved_on
    else:
        from datetime import datetime, timezone
        retrieved_on = datetime.now(timezone.utc).date().isoformat()

    with open(IDENTIFIERS, encoding="utf-8") as f:
        identifiers = json.load(f)["variants"]

    # (accession -> {protein_variant, ...}) for exactly the golden fixture's
    # MISSENSE variants. Non-missense rows (nonsense, frameshift) are skipped:
    # AlphaMissense does not model them, so "no record" is expected, not a miss.
    need, skipped = {}, []
    if args.accessions:
        for acc in args.accessions.split(","):
            need.setdefault(acc.strip(), set())
    else:
        with open(VARIANTS, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                vid = row["variant_id"]
                m = _MISSENSE_RE.match(row["protein_change"].strip())
                if not m:
                    skipped.append(f"{vid} {row['gene']} {row['protein_change']}")
                    continue
                acc = identifiers[vid]["uniprot_id"]
                need.setdefault(acc, set()).add(f"{m.group(1)}{m.group(2)}{m.group(3)}")

    print(f"source   : {SOURCE_FILE} ({RECORD})")
    print(f"licence  : {LICENCE} -- NOT redistributed; this cache stays local")
    print(f"fetching : {sum(len(v) for v in need.values())} missense variants "
          f"across {len(need)} accessions")
    if skipped:
        print(f"skipping : {len(skipped)} non-missense (outside AlphaMissense's domain) -- "
              + ", ".join(skipped))
    print()

    scores, missing = {}, []
    for acc in sorted(need):
        table = fetch_accession(acc)
        if not table:
            missing.append(f"{acc} (accession not found in {SOURCE_FILE})")
            continue
        if args.all_substitutions:
            for pv, rec in table.items():
                scores[f"{acc}/{pv}"] = rec
            print(f"  {acc}: cached all {len(table)} substitutions")
            continue
        for pv in sorted(need[acc]):
            if pv in table:
                scores[f"{acc}/{pv}"] = table[pv]
                print(f"  {acc}/{pv:<8} -> {table[pv]['am_pathogenicity']:<8} {table[pv]['am_class']}")
            else:
                missing.append(f"{acc}/{pv}")

    if missing:
        print("\nNOT FOUND (cache written WITHOUT these; tests will refuse, not guess):",
              file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    blob = {
        "_licence": LICENCE,
        "_warning": "AlphaMissense data - CC BY-NC-SA 4.0. DO NOT COMMIT. "
                    "This path is gitignored (see .gitignore, docs/alphamissense-data.md).",
        "source_file": SOURCE_FILE,
        "source_record": RECORD,
        "retrieved_on": retrieved_on,
        "scores": scores,
    }
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(blob, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"\nwrote {len(scores)} scores to {args.out}")
    print(f"HTTP range requests: {_requests}, {_bytes / 1e6:.1f} MB transferred "
          f"({100 * _bytes / SIZE:.1f}% of the {SIZE / 1e9:.1f} GB file)")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
