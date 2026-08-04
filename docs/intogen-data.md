# IntOGen data — licence, acquisition, and what this repo does not hold

> For SPEC-028. **This repository contains no IntOGen data.** It contains code that reads a
> locally-fetched copy, and our own assertions about what that copy says.

## Licence — CC0, and we are still not committing it

The release archive bundles `LICENSE.txt` = **CC0 1.0 Universal**, a public-domain dedication.
Verified from inside the archive, not from the website.

That makes IntOGen the **least** encumbered of the three external sources:

| Source | Terms | Could we commit a slice? |
|---|---|---|
| AlphaMissense | CC BY-NC-SA 4.0 | No — non-commercial, share-alike |
| EVE | MIT *as asserted*, copyright names the site author not the model authors | Unsettled |
| **IntOGen** | **CC0 1.0 (public domain)** | **Yes — permitted** |

We keep the fetch-to-gitignored-cache pattern anyway. The reasoning is in decision **D-013**:
one uniform rule ("no third-party prediction data in the repo") is harder to erode than three
per-source exceptions; the retrieval cost is a single ~965 KB download; and D3 is still open.

**This is a choice, not a constraint** — recorded so it reads as one. Reversing it would make
the drivers fixture self-contained and let CI exercise real data instead of skipping. That is a
legitimate call and costs nothing to make.

**Citation:** Martínez-Jiménez F, Muiños F, Sentís I, Deu-Pons J, Reyes-Salazar I, Arnedo-Pac C,
Mularoni L, Pich O, Bonet J, Kranas H, Gonzalez-Perez A, Lopez-Bigas N. *A compendium of
mutational cancer driver genes.* Nature Reviews Cancer 20, 555–572 (2020).

## Acquiring the data

```powershell
# from the repo root (PowerShell — see AGENTS.md §Environment)
python tools\intogen\fetch_compendium.py
```

Writes `.cache/intogen/compendium.json`, **gitignored** via `/.cache/`.

One HTTPS download of `IntOGen-Drivers-20240920.zip` (964,758 bytes), extracted in memory.
Standard library only — `urllib` + `zipfile` + `csv`. **No new runtime dependency**, and no
range requests: unlike AlphaMissense's 1.2 GB file, this fits in one request.

### Source of record

| | |
|---|---|
| Archive | `IntOGen-Drivers-20240920.zip` — 964,758 bytes |
| Directory | `2024-06-18_IntOGen-Drivers/` |
| File used | `Compendium_Cancer_Genes.tsv` — 790,207 bytes, **4,478 rows** |
| Key | `(SYMBOL, TRANSCRIPT, COHORT)` — one row per gene per cohort |
| Cancer types | 86 distinct; **COAD 55 rows, READ 15** |

*Publisher inconsistency, recorded not resolved:* the bundled `README.txt` says
`# IntOGen RELEASE 20230531`, the archive is named `20240920`, and the directory is
`2024-06-18`. Three dates for one release. The fetcher stamps the directory name it actually
reads, so provenance stays honest whichever is authoritative.

## What makes this worth consuming: the positional columns

The compendium is **gene-level for the driver call** — which on our fixture is constant
(20/20 driver) and therefore worthless on its own. Three columns carry **sub-gene positional**
evidence, and that is where the information is:

| Column | Method | Threshold | Format |
|---|---|---|---|
| `DOMAINS` | smRegions | q < 0.1 | `PFAM_ID:START_AA:END_AA` |
| `2D_CLUSTERS` | OncodriveCLUSTL | p < 0.05 | `START_AA:END_AA` |
| `3D_CLUSTERS` | HotMAPS | q < 0.05 | `AA_1,AA_2,…` |

Intersecting a variant's residue with those splits the same 20 variants **10 / 5 / 5**. See
`producers/drivers/README.md` for why a gene-level producer would have been worth nothing.

## Coverage

Colorectal (COAD/READ) rows exist for **10 of the grant's 15** named CRC driver genes.

**Absent from colorectal:** MLH1, MSH2, MSH6, PMS2, TGFBR2 — the four MMR genes plus TGFBR2.
Consistent with their drivers being truncating or germline rather than clustered missense; not a
retrieval failure. Those variants yield `gene_not_a_driver_in_scope`, which is **not**
"not a driver".

## Scope is load-bearing

Default is **colorectal**, and it is recorded on every result rather than assumed, because it
changes answers. PIK3CA H1047R: flagged in 35 of 109 pan-cancer rows, 0 of 2 colorectal rows.
Colorectal-vs-pan-cancer is questionnaire **A13**.

## Calibration

Every result is stamped `calibration_pending`, for a reason argued specifically for this
producer rather than copied from the variant-effect providers: IntOGen's clusters are
significant *relative to the mutation spectrum of overwhelmingly European-ancestry cohorts*, so
**absence from a cluster is uninformative rather than negative** for an African-ancestry
variant. Full reasoning in `producers/drivers/README.md`; raised as questionnaire **A12**.
