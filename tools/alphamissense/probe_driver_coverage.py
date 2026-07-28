"""PROBE: does AlphaMissense systematically miss ACTIVATING somatic drivers?

DEV TOOLING / investigation script. Imports nothing from producers/, core/, or
query/ (ARCHITECTURE.md sec 5). Reproduces the table in
docs/probes/alphamissense-driver-coverage.md. Not part of any suite, not on any
gate -- it exists so the finding is auditable rather than asserted.

Design choices made to keep this from being a hand-picked result:
  * GENE SET is not mine. It is the 15 "well-established, frequently mutated CRC
    driver mountains" named in the grant strategy itself
    (docs/sources/Domestic_Project_Research_Strategy_PF5.txt line 332).
  * VARIANT SET is not mine. Every probe variant is a statistically significant
    recurrent somatic hotspot residue from cancerhotspots.org (Chang et al.,
    Nat Biotechnol 2016; Cancer Discov 2018), and the specific substitution at
    each residue is the MOST OBSERVED one in their tumor data -- chosen by
    frequency, not by me.
  * GROUP ASSIGNMENT is not mine. Mechanism of action comes from IntOGen's
    Compendium_Cancer_Genes.tsv ROLE column (COAD cohort where present) and is
    cross-checked against OncoKB's geneType. The activating / loss-of-function /
    ambiguous scheme is the grant's own (same source, line 357).

Scores come from the LOCAL, GITIGNORED cache. No AlphaMissense data is committed.
Populate first:
    python tools/alphamissense/fetch_scores.py --all-substitutions \
        --accessions <the 15 accessions> --out .cache/alphamissense/probe_all.json
"""
from __future__ import annotations
import json
import math
import os
import re
import statistics
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHES = [os.path.join(ROOT, ".cache", "alphamissense", "probe_all.json"),
          os.path.join(ROOT, ".cache", "alphamissense", "probe_mmr.json")]

HOTSPOTS_API = "https://www.cancerhotspots.org/api/hotspots/single"

# Published cutoffs (config/alphamissense.json) -- the publisher's, not ours.
BENIGN_BELOW, PATHOGENIC_ABOVE = 0.34, 0.564

# UniProtKB accessions, reviewed/Swiss-Prot, organism 9606 (rest.uniprot.org, 2026-07-28)
ACCESSION = {
    "APC": "P25054", "BRAF": "P15056", "CTNNB1": "P35222", "FBXW7": "Q969H0",
    "KRAS": "P01116", "MLH1": "P40692", "MSH2": "P43246", "MSH6": "P52701",
    "NRAS": "P01111", "PIK3CA": "P42336", "PMS2": "P54278", "RNF43": "Q68DV7",
    "SMAD4": "Q13485", "TGFBR2": "P37173", "TP53": "P04637",
}

# Mechanism of action. IntOGen Compendium_Cancer_Genes.tsv (2024-06-18 release),
# ROLE column, COAD cohort where the gene is called there; OncoKB geneType as the
# independent cross-check. Both retrieved 2026-07-28.
#   ACT = activating / gain-of-function ; LOF = loss-of-function
#   EXCLUDED = no citable CRC mechanism call, or the sources disagree
ROLE = {
    "KRAS":   ("ACT", "IntOGen COAD Act x2; OncoKB ONCOGENE"),
    "NRAS":   ("ACT", "IntOGen COAD Act x2; OncoKB ONCOGENE"),
    "BRAF":   ("ACT", "IntOGen COAD Act x1; OncoKB ONCOGENE"),
    "PIK3CA": ("ACT", "IntOGen COAD Act x2; OncoKB ONCOGENE"),
    "CTNNB1": ("ACT", "IntOGen COAD Act x1; OncoKB ONCOGENE"),
    "TP53":   ("LOF", "IntOGen COAD LoF x2; OncoKB TSG"),
    "APC":    ("LOF", "IntOGen COAD LoF x2; OncoKB TSG"),
    "FBXW7":  ("LOF", "IntOGen COAD LoF x2; OncoKB TSG"),
    "RNF43":  ("LOF", "IntOGen COAD LoF x1; OncoKB TSG"),
    "TGFBR2": ("LOF", "IntOGen LoF x11 vs Act x3 (no COAD row); OncoKB TSG"),
    "MLH1":   ("LOF", "OncoKB TSG only -- no IntOGen driver row (SINGLE SOURCE)"),
    "MSH2":   ("LOF", "OncoKB TSG only -- no IntOGen driver row (SINGLE SOURCE)"),
    "MSH6":   ("LOF", "OncoKB TSG only -- no IntOGen driver row (SINGLE SOURCE)"),
    # Excluded on purpose -- stated in the write-up rather than silently dropped:
    "SMAD4":  ("EXCLUDED", "IntOGen COAD is SPLIT (LoF x1, Act x1) -- no unambiguous call"),
    "PMS2":   ("EXCLUDED", "IntOGen role is 'ambiguous'; the grant's own third category"),
}

_RESIDUE_RE = re.compile(r"^([A-Z])(\d+)$")


def load_scores():
    scores = {}
    for path in CACHES:
        if not os.path.exists(path):
            sys.exit(f"missing cache {path}\nSee this file's docstring to populate it.")
        with open(path, encoding="utf-8") as f:
            scores.update(json.load(f)["scores"])
    return scores


def load_hotspots():
    req = urllib.request.Request(
        HOTSPOTS_API, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())


def call_of(score):
    if score < BENIGN_BELOW:
        return "benign"
    if score > PATHOGENIC_ABOVE:
        return "pathogenic"
    return "AMBIGUOUS"


def main():
    scores = load_scores()
    hotspots = load_hotspots()

    probes = []
    for h in hotspots:
        gene = h.get("hugoSymbol")
        if gene not in ACCESSION or ROLE[gene][0] == "EXCLUDED":
            continue
        m = _RESIDUE_RE.match(h.get("residue") or "")
        if not m:
            continue                       # splice/indel hotspot, not a missense residue
        ref_aa, pos = m.group(1), m.group(2)
        counts = h.get("variantAminoAcid") or {}
        # the substitution actually observed most often at this residue
        alt_aa = max(counts, key=counts.get) if counts else None
        if not alt_aa or len(alt_aa) != 1 or alt_aa == ref_aa:
            continue
        pv = f"{ref_aa}{pos}{alt_aa}"
        rec = scores.get(f"{ACCESSION[gene]}/{pv}")
        if rec is None:
            continue                       # not in AlphaMissense's canonical isoform
        bowel = (h.get("tumorTypeComposition") or {}).get("bowel", 0)
        probes.append({
            "gene": gene, "role": ROLE[gene][0], "variant": pv,
            "key": f"{ACCESSION[gene]}/{pv}",
            "tumors": h.get("tumorCount", 0), "bowel": bowel,
            "obs_at_residue": counts.get(alt_aa, 0),
            "score": rec["am_pathogenicity"], "am_class": rec["am_class"],
            "call": call_of(rec["am_pathogenicity"]),
        })

    probes.sort(key=lambda p: (p["role"], -p["tumors"]))
    return probes, scores


def report(probes, bowel_only=False):
    label = "COLORECTAL-OBSERVED SUBSET (bowel tumors > 0)" if bowel_only else "FULL PROBE SET (pan-cancer hotspots)"
    rows = [p for p in probes if p["bowel"] > 0] if bowel_only else probes
    print("=" * 100)
    print(label)
    print("=" * 100)
    print(f"{'gene':<8}{'variant':<9}{'role':<6}{'tumors':>7}{'bowel':>7}{'score':>9}  "
          f"{'am_class':<18}{'call':<11}")
    print("-" * 100)
    for p in rows:
        print(f"{p['gene']:<8}{p['variant']:<9}{p['role']:<6}{p['tumors']:>7}{p['bowel']:>7}"
              f"{p['score']:>9.4f}  {p['am_class']:<18}{p['call']:<11}")
    print("-" * 100)
    for role in ("ACT", "LOF"):
        g = [p for p in rows if p["role"] == role]
        if not g:
            continue
        n = len(g)
        path = sum(1 for p in g if p["call"] == "pathogenic")
        amb = sum(1 for p in g if p["call"] == "AMBIGUOUS")
        ben = sum(1 for p in g if p["call"] == "benign")
        sc = [p["score"] for p in g]
        print(f"{role}: n={n:<3} pathogenic={path:<3}({100*path/n:5.1f}%)  "
              f"ambiguous={amb:<3}({100*amb/n:5.1f}%)  benign={ben:<3}({100*ben/n:5.1f}%)  "
              f"median={statistics.median(sc):.4f}  mean={statistics.fmean(sc):.4f}  "
              f"min={min(sc):.4f}")
    print()


def mann_whitney_u(a, b):
    """Two-sided Mann-Whitney U with tie correction, normal approximation.
    Implemented here because the repo has no scipy and adds no dependency."""
    n1, n2 = len(a), len(b)
    combined = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks, i, tie_term = [0.0] * len(combined), 0, 0.0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = avg
        t = j - i + 1
        tie_term += t ** 3 - t
        i = j + 1
    r1 = sum(r for r, (_, grp) in zip(ranks, combined) if grp == 0)
    u1 = r1 - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    N = n1 + n2
    var = (n1 * n2 / 12.0) * ((N + 1) - tie_term / (N * (N - 1.0)))
    if var <= 0:
        return u1, float("nan")
    z = (u1 - mu) / math.sqrt(var)
    p = math.erfc(abs(z) / math.sqrt(2))          # two-sided
    return u1, p


def fisher_exact(a, b, c, d):
    """Two-sided Fisher's exact on [[a,b],[c,d]] by summing tables no more
    likely than the observed one."""
    def prob(x, y, z, w):
        return (math.comb(x + y, x) * math.comb(z + w, z)) / math.comb(x + y + z + w, x + z)
    obs = prob(a, b, c, d)
    row1, col1, total = a + b, a + c, a + b + c + d
    p = 0.0
    for x in range(max(0, col1 - (total - row1)), min(row1, col1) + 1):
        cur = prob(x, row1 - x, col1 - x, total - row1 - col1 + x)
        if cur <= obs * (1 + 1e-9):
            p += cur
    return min(p, 1.0)


def stats_block(probes, label):
    act = [p["score"] for p in probes if p["role"] == "ACT"]
    lof = [p["score"] for p in probes if p["role"] == "LOF"]
    u, p_mw = mann_whitney_u(act, lof)
    a = sum(1 for x in probes if x["role"] == "ACT" and x["call"] == "pathogenic")
    b = len(act) - a
    c = sum(1 for x in probes if x["role"] == "LOF" and x["call"] == "pathogenic")
    d = len(lof) - c
    p_f = fisher_exact(a, b, c, d)
    print(f"--- {label} ---")
    print(f"  Mann-Whitney U (scores, ACT vs LOF): U={u:.1f}  p={p_mw:.3f}")
    print(f"  Fisher exact (pathogenic vs not):    [[{a},{b}],[{c},{d}]]  p={p_f:.3f}")
    print(f"  => {'NO significant difference' if min(p_mw, p_f) > 0.05 else 'DIFFERENCE at p<0.05'}"
          " between activating and loss-of-function hotspots\n")


def burden_weighted(probes):
    """Per-VARIANT rates treat a 6-tumor hotspot and a 647-tumor hotspot alike.
    What matters operationally is what fraction of actual TUMORS carry a driver
    the tool would not call pathogenic."""
    print("--- recurrence-weighted (what fraction of TUMORS carry a missed driver) ---")
    for scope, rows in (("pan-cancer", probes), ("bowel only", [p for p in probes if p["bowel"] > 0])):
        for role in ("ACT", "LOF"):
            g = [p for p in rows if p["role"] == role]
            if not g:
                continue
            field = "tumors" if scope == "pan-cancer" else "bowel"
            tot = sum(p[field] for p in g)
            miss = sum(p[field] for p in g if p["call"] != "pathogenic")
            print(f"  {scope:<11}{role:<5} tumors={tot:>6}  carried by a NON-pathogenic call="
                  f"{miss:>5}  ({100*miss/tot:5.1f}%)")
    print()


def per_gene(probes):
    print("--- per-gene breakdown (where the misses actually are) ---")
    print(f"{'gene':<9}{'role':<6}{'n':>4}{'pathogenic':>12}{'not-path':>10}{'median':>9}{'min':>9}")
    by = {}
    for p in probes:
        by.setdefault((p["gene"], p["role"]), []).append(p)
    for (gene, role), g in sorted(by.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        sc = [x["score"] for x in g]
        np_ = sum(1 for x in g if x["call"] != "pathogenic")
        print(f"{gene:<9}{role:<6}{len(g):>4}{len(g)-np_:>12}{np_:>10}"
              f"{statistics.median(sc):>9.4f}{min(sc):>9.4f}")
    print()


if __name__ == "__main__":
    probes, _ = main()
    report(probes, bowel_only=False)
    report(probes, bowel_only=True)
    stats_block(probes, "FULL PROBE SET")
    stats_block([p for p in probes if p["bowel"] > 0], "COLORECTAL-OBSERVED SUBSET")
    burden_weighted(probes)
    per_gene(probes)
    print("--- every non-pathogenic call, both groups ---")
    for p in sorted(probes, key=lambda x: x["score"]):
        if p["call"] != "pathogenic":
            print(f"  {p['role']:<5}{p['gene']:<9}{p['variant']:<9}{p['score']:.4f}  "
                  f"{p['am_class']:<12} tumors={p['tumors']} bowel={p['bowel']}")
    print()
    print(f"probe variants: {len(probes)} "
          f"(ACT={sum(1 for p in probes if p['role']=='ACT')}, "
          f"LOF={sum(1 for p in probes if p['role']=='LOF')})")
