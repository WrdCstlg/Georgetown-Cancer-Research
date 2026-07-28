"""Independently corroborate fixture expectations against the OTHER published file.

DEV TOOLING. Imports nothing from producers/, core/, or query/.

The fixture's expected calls were derived from AlphaMissense_aa_substitutions.tsv.gz,
keyed by (uniprot_id, protein_variant). Derived once and frozen, a parsing bug at
derivation time would be baked into the fixture and every test would agree with it.

This cross-checks the SAME predictions in AlphaMissense_hg38.tsv.gz -- a different
file, keyed by genomic coordinate, that also carries uniprot_id + protein_variant.
Agreement between the two is genuine independent corroboration; disagreement means
the derivation is wrong, not that the tool changed its mind.

It also re-verifies the vocabulary divergence in situ: the hg38 file should report
likely_benign / likely_pathogenic where the aa file reports benign / pathogenic,
for identical scores.

Gene coordinates: Ensembl REST (GRCh38), retrieved 2026-07-28.
Scores: local gitignored cache. Nothing is committed.

Usage:  python tools/alphamissense/corroborate_hg38.py
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPECTED = os.path.join(ROOT, "fixtures", "variant_effect", "alphamissense_expected.json")
IDENTIFIERS = os.path.join(ROOT, "fixtures", "variant_effect", "identifiers.json")

SOURCE_FILE = "AlphaMissense_hg38.tsv.gz"
URL = f"https://zenodo.org/records/8208688/files/{SOURCE_FILE}?download=1"
SIZE = 642961469
WINDOW = 1 << 16
SWEEP = 8 << 20
MAGIC = b"\x1f\x8b\x08\x04"

# Ensembl REST (GRCh38), retrieved 2026-07-28. Used only to seek into a
# coordinate-sorted file -- never to derive a variant's identity.
GENE_SPAN = {
    "KRAS":   ("chr12", 25205246, 25326473),
    "TP53":   ("chr17", 7661779, 7687546),
    "PIK3CA": ("chr3", 179148114, 179240093),
    "BRAF":   ("chr7", 140719327, 140925199),
    "APC":    ("chr5", 112707452, 112846239),
    "CTNNB1": ("chr3", 41194741, 41260096),
    "SMAD4":  ("chr18", 51028528, 51085045),
    "FBXW7":  ("chr4", 152320544, 152536353),
    "RNF43":  ("chr17", 58353671, 58417735),
}

_requests = 0
_bytes = 0


def _get(offset, length, attempts=5):
    global _requests, _bytes
    end = min(offset + length - 1, SIZE - 1)
    req = urllib.request.Request(URL, headers={"Range": f"bytes={offset}-{end}"})
    last = None
    for attempt in range(attempts):
        _requests += 1
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            _bytes += len(data)
            return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if attempt == attempts - 1:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"range {offset}-{end} failed: {last}")


def _rows(raw, skip_leading):
    start = raw.find(MAGIC, 1 if skip_leading else 0)
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
        if not buf.startswith(MAGIC):
            break
    text = b"".join(chunks).decode("utf-8", "replace")
    out = []
    for line in text.splitlines()[1:-1]:
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) == 10:
            out.append(f)
    return out


def collect(gene, wanted):
    """Sweep this gene's span in the hg38 file; return {protein_variant: row}."""
    chrom, gstart, gend = GENE_SPAN[gene]
    lo, hi = 0, SIZE
    while hi - lo > WINDOW:                       # bisect on (chrom lexicographic, pos)
        mid = (lo + hi) // 2
        rows = _rows(_get(mid, WINDOW), skip_leading=bool(mid))
        if not rows:
            lo = mid + WINDOW
            continue
        if (rows[0][0], int(rows[0][1])) < (chrom, gstart):
            lo = mid
        else:
            hi = mid
    found, offset = {}, max(0, lo - WINDOW)
    while offset < SIZE:
        rows = _rows(_get(offset, SWEEP), skip_leading=bool(offset))
        if not rows:
            break
        for f in rows:
            if f[0] == chrom and gstart <= int(f[1]) <= gend and f[7] in wanted:
                found.setdefault(f[7], f)
        last = rows[-1]
        if (last[0], int(last[1])) > (chrom, gend):
            break
        offset += SWEEP
        if len(found) == len(wanted):
            break
    return found


def main():
    with open(EXPECTED, encoding="utf-8") as f:
        exp = json.load(f)
    with open(IDENTIFIERS, encoding="utf-8") as f:
        idmap = json.load(f)["variants"]

    cache = {}
    for p in ("scores.json", "probe_all.json", "probe_mmr.json"):
        path = os.path.join(ROOT, ".cache", "alphamissense", p)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                cache.update(json.load(f)["scores"])
    if not cache:
        sys.exit("no local cache; run tools/alphamissense/fetch_scores.py first")

    # one entry per gene: the highest-recurrence / first scored variant we hold
    targets = {}
    for section in ("expected", "controls"):
        for vid, e in exp.get(section, {}).items():
            if e.get("coverage") != "scored":
                continue
            gene = e["gene"]
            if gene in GENE_SPAN:
                targets.setdefault(gene, []).append((vid, e))

    print(f"corroborating against {SOURCE_FILE} (Zenodo 10.5281/zenodo.8208688)")
    print(f"{'gene':<8}{'variant':<9}{'aa-file':<10}{'hg38':<10}{'aa am_class':<14}"
          f"{'hg38 am_class':<20}{'agree'}")
    print("-" * 92)
    ok = bad = 0
    results = {}
    for gene in sorted(targets):
        entries = targets[gene]
        wanted = {}
        for vid, e in entries:
            acc = idmap[vid]["uniprot_id"]
            pv = e["key"].split("/")[1]
            wanted[pv] = (vid, acc, e)
        rows = collect(gene, set(wanted))
        for pv, (vid, acc, e) in sorted(wanted.items()):
            row = rows.get(pv)
            aa = cache.get(f"{acc}/{pv}")
            if row is None or aa is None:
                print(f"{gene:<8}{pv:<9}{'-':<10}{'NOT FOUND':<10}")
                bad += 1
                continue
            hg_score, hg_class, hg_uniprot = float(row[8]), row[9], row[5]
            agree = (abs(hg_score - aa["am_pathogenicity"]) < 1e-9
                     and hg_uniprot == acc
                     and hg_class.replace("likely_", "") == aa["am_class"].replace("likely_", ""))
            print(f"{gene:<8}{pv:<9}{aa['am_pathogenicity']:<10.4f}{hg_score:<10.4f}"
                  f"{aa['am_class']:<14}{hg_class:<20}{'YES' if agree else 'NO'}")
            results[vid] = {
                "variant": pv, "hg38_score": hg_score, "hg38_class": hg_class,
                "hg38_uniprot": hg_uniprot, "hg38_locus": f"{row[0]}:{row[1]} {row[2]}>{row[3]}",
                "hg38_transcript": row[6], "agree": agree,
            }
            ok += agree
            bad += not agree
    print("-" * 92)
    print(f"agreeing: {ok}   disagreeing/missing: {bad}")
    print(f"HTTP range requests: {_requests}, {_bytes/1e6:.1f} MB "
          f"({100*_bytes/SIZE:.1f}% of the {SIZE/1e9:.2f} GB file)")
    out = os.path.join(ROOT, ".cache", "alphamissense", "corroboration_hg38.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"source_file": SOURCE_FILE, "results": results}, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"wrote {out} (gitignored)")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
