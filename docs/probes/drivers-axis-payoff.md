# Drivers producer — what the driver axis adds, and what it does not

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

## 2 · What it adds beyond the pathogenicity axis

**Six variants carry positional driver evidence where the pathogenicity consensus did *not*
reach `pathogenic`** — and they are *exactly* the six abstention disagreements from decision
**D-010**:

> KRAS G12D · KRAS G13D · KRAS A146T · TP53 R175H · TP53 R248Q · PIK3CA E545K

Every one is a case where AlphaMissense said pathogenic, EVE declined to commit, and consensus
therefore left the variant VUS. On all six, an independent, methodologically unrelated line of
evidence — recurrent somatic clustering in colorectal cohorts — supports them.

That is a genuinely different axis doing what a different axis should: speaking where the first
axis was deadlocked. **It does not resolve them**, and deliberately so — this evidence is not
routed into the variant_effect consensus, `min_agree` is untouched, and driver evidence is not a
pathogenicity vote. Whether it *should* count is a domain question (A8/A13), not ours.

**The gene-level signal, by contrast, adds nothing at all.** `gene_is_driver_in_scope` is `true`
for all 20 golden variants. A gene-level driver producer would have emitted a constant and been
worth building only as a lesson. All the information is positional: 10 with evidence, 5 in a
driver gene with no positional support, 5 not missense.

## 3 · PIK3CA H1047R — the direct D-008 test

| Axis | Verdict on H1047R |
|---|---|
| AlphaMissense (structural) | `uncertain` |
| EVE (evolutionary) | `benign` |
| **IntOGen, colorectal (COAD/READ)** | gene **is** a driver; residue 1047 in **no** significant cluster |
| IntOGen, pan-cancer | residue 1047 flagged in **35 of 109** cohort rows |

**A driver-oriented signal does not rescue H1047R either — under colorectal scope.** The
colorectal clusters IntOGen publishes for PIK3CA are `2D = 542:546` and `3D = {542,545,546}`,
the helical-domain hotspot. Residue 1047 (kinase domain) is absent from both colorectal cohorts.

The finding is therefore **not** "the tools have a driver blind spot" — the 178-hotspot probe
tested that and it failed (p = 0.31 / 0.75). It is that **H1047R's driver status is strongly
cohort-dependent**: overwhelming pan-cancer, unestablished in colorectal cohorts of the size
IntOGen has. Consistent with CRC PIK3CA mutation being helical-domain-weighted, and now measured
from a citable in-repo source rather than assumed. Recorded as D-008 addendum 2; the scope choice
is questionnaire **A13**.

## 4 · What this producer does NOT establish

Stated explicitly, because each is a conclusion someone could wrongly draw:

1. **It does not establish that any variant is a driver.** It reports evidence. There is no
   `is_driver` field in the contract, by construction.
2. **`no_positional_evidence` is not evidence against a variant.** IntOGen's clusters are
   significant relative to the mutation spectrum of overwhelmingly European-ancestry cohorts, so
   absence is **uninformative, not negative** — especially for African-ancestry variants, where
   a residue may fail significance for lack of power rather than lack of importance. Treating
   absence as negative would convert a sampling artifact into a finding, in the direction that
   most disadvantages the populations this study exists to serve. This is why every result is
   `calibration_pending` (questionnaire A12).
3. **It says nothing about pathogenicity**, and is not wired into the variant_effect consensus.
4. **It has not run on this project's cohort.** This is IntOGen's *published* compendium,
   computed on other people's cohorts. Running IntOGen over our own mutations is SPEC-020, which
   is **GATED** — no cohort data exists (D-011).
5. **Coverage is partial.** IntOGen has no colorectal rows for 5 of the grant's 15 driver genes
   (MLH1, MSH2, MSH6, PMS2, TGFBR2). Those variants get "no evidence in scope", which is again
   not "not a driver".
6. **It is a 20-variant fixture plus 4 controls**, not a cohort. No real patient data has
   touched this system.
