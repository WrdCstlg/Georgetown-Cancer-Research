# Drivers producer — run record (SPEC-028)

> **This is a run record, not a findings document.** The interpretation of these numbers — what
> the driver axis adds, the six-and-six correspondence, the H1047R cohort-scope argument, and
> what none of it establishes — lives in [`docs/FINDINGS.md`](../FINDINGS.md), which is
> **canonical**. This file exists so a reviewer can check a measured number against the run that
> produced it. It deliberately makes no argument.
>
> **Measured, not asserted.** Every number comes from `python tests/test_drivers_producer.py`
> and the fixture it gates. **Run 2026-08-02**, IntOGen release `2024-06-18_IntOGen-Drivers`,
> cohort scope **COAD/READ**.
>
> Distributional statistics only; no IntOGen payload is reproduced here. (IntOGen is CC0 and
> reproducing it *would* be permitted — decision **D-013** explains why we don't anyway.)

## 1 · Driver evidence per fixture variant

| id | gene | change | AlphaMissense | EVE | IntOGen positional evidence | new? |
|---|---|---|---|---|---|---|
| v01 | APC | p.R1450* | — | — | not_missense | |
| v02 | KRAS | p.G12D | pathogenic | *uncertain* | 2D + 3D + domain | **✔** |
| v03 | TP53 | p.R175H | pathogenic | *uncertain* | 2D + 3D + domain | **✔** |
| v04 | PIK3CA | p.E545K | pathogenic | *uncertain* | 2D + 3D | **✔** |
| v05 | SMAD4 | p.R361H | pathogenic | pathogenic | 3D | |
| v06 | APC | p.E1309fs | — | — | not_missense | |
| v07 | KRAS | p.G13D | pathogenic | *uncertain* | 2D + 3D + domain | **✔** |
| v08 | CTNNB1 | p.S45F | pathogenic | pathogenic | no_positional_evidence | |
| v09 | RNF43 | p.G659fs | — | — | not_missense | |
| v10 | FBXW7 | p.R465C | pathogenic | — | no_positional_evidence | |
| v11 | KRAS | p.G12V | pathogenic | pathogenic | 2D + 3D + domain | |
| v12 | TP53 | p.R248Q | pathogenic | *uncertain* | 2D + 3D + domain | **✔** |
| v13 | APC | p.T1556fs | — | — | not_missense | |
| **v14** | **PIK3CA** | **p.H1047R** | *uncertain* | **benign** | **no_positional_evidence** | |
| v15 | SMAD4 | p.D351H | pathogenic | pathogenic | no_positional_evidence | |
| v16 | KRAS | p.A146T | pathogenic | *uncertain* | domain | **✔** |
| v17 | TP53 | p.Y220C | pathogenic | pathogenic | domain | |
| v18 | APC | p.Q1367* | — | — | not_missense | |
| v19 | CTNNB1 | p.T41A | pathogenic | pathogenic | no_positional_evidence | |
| v20 | BRAF | p.V600E | pathogenic | pathogenic | 2D + 3D + domain | |

**`new?`** marks a variant carrying positional driver evidence where the pathogenicity consensus
did *not* reach `pathogenic`. Six rows: `v02 v03 v04 v07 v12 v16`. What that correspondence means
is argued in [`docs/FINDINGS.md`](../FINDINGS.md) §5, not here.

## 2 · Measured splits

| Outcome | n |
|---|---:|
| Residue inside a significant domain / 2D cluster / 3D cluster | 10 |
| Gene is a driver, residue in no significant cluster (`no_positional_evidence`) | 5 |
| Not a missense change (`not_missense`) | 5 |

`gene_is_driver_in_scope` is `true` for **all 20** variants — the gene-level signal is constant
on this fixture and carries no information. All discrimination is positional.

## 3 · PIK3CA H1047R — the measured scope rows

| Scope | PIK3CA a driver? | Residue 1047 in a significant cluster? |
|---|---|---|
| COAD / READ (colorectal) | yes — Act, 2 cohorts | **no — 0 of 2 rows** |
| Pan-cancer | yes — 109 cohorts | yes — 35 of 109 rows |

Colorectal PIK3CA clusters as published: `2D = 542:546`, `3D = {542, 545, 546}`.

Interpretation — including the 178-hotspot null that bounds it — is in
[`docs/FINDINGS.md`](../FINDINGS.md) §6. Scope is questionnaire **A13**; decision **D-008**
addendum 2.

## 4 · Scope of this run

20-variant golden fixture plus 4 controls. **Not** a cohort; no real patient data has touched
this system. Every result is stamped `calibration_pending`. Running IntOGen over this project's
own mutations is SPEC-020, which is GATED (decision D-011).

The three "nothing found" states — `gene_not_a_driver_in_scope`, `no_positional_evidence`,
`not_missense` — are distinct and **none of them means "not a driver"**. The reasoning is in
[`producers/drivers/README.md`](../../producers/drivers/README.md); the consequences for a reader
are in [`docs/FINDINGS.md`](../FINDINGS.md) §7 and §10.

## 5 · Reproducing

```powershell
python tools\intogen\fetch_compendium.py
python tests\test_drivers_producer.py
```
