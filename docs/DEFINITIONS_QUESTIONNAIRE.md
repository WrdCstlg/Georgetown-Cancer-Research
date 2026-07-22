# AfriCAN DANCE — Definitions the analysis needs from you

**For:** Dr. Laura · **From:** the computational team · **Purpose:** a short set of domain definitions that the AI/analysis layer needs pinned before it can run on real data.

The tools are built so they **cannot invent these values** — they stop and ask rather than guess. Where the grant already states a threshold, we've pre-filled it below so you can simply confirm (or adjust). The second set are genuinely open — only you can set them. Anywhere you're unsure, write *"field default, flag for review"* and we'll proceed conservatively (results marked provisional) until you confirm.

You can reply inline in this document.

---

## Part A — Confirm the grant's thresholds (quick)

Do these hold for the ancestry-aware analysis, or would you adjust any?

| # | Threshold (from the grant) | Confirm / adjust |
|---|----------------------------|------------------|
| A1 | Driver gene significance: FDR **q < 0.05**, support from ≥2 methods; COSMIC CGC genes relaxed to **q < 0.25** | |
| A2 | Differential expression: **p < 0.05** and **|log₂FC| > 0.5** | |
| A3 | Germline filter for somatic calls: population MAF **< 1%** (ExAC / gnomAD / 1000G) | |
| A4 | Minimum sequencing depth: **20×** | |
| A5 | MSI status: MSISensor2 **≥ 3.5 = MSI-H**, else MSS | |
| A6 | Tumor mutation burden: **≥ 10 mut/Mb = TMB-high** | |
| A7 | Discrete AFR strata (if used): **Low ≤30% · Medium 30–80% · High ≥80%** — note we default to *continuous* AFR proportion; is a discrete cut ever needed, and if so are these the right bins? | |

---

## Part B — Definitions only you can set (the ones currently blocking)

These aren't in the grant and the analysis can't proceed to conclusions without them.

**B1 · When is a variant-effect tool trustworthy for a given population?**
The tools we use to reclassify "unknown" variants (AlphaMissense, EVE, and the older SIFT/PolyPhen) were trained mostly on European-ancestry data. Until we know a tool is validated for African American, Ghanaian, and Ethiopian tumors, every call it makes is currently stamped *"calibration pending"* and shown **with that caveat rather than as a confident result**.
*What we need:* is there a benchmark or bar you'd accept for saying a tool is "in-calibration" for a population (e.g., agreement with a set of known variants in that population, a minimum sample, a concordance level)? Or should everything stay provisional until we generate that evidence from the organoid arm?

**B2 · What makes a variant or target "ancestry-enriched"?**
The whole pipeline hinges on this phrase, and it can mean different things.
*What we need:* the operational definition you'd defend to a reviewer — a frequency **difference** between populations (how large?), a **continuous** correlation with AFR proportion (how strong?), and at what significance. And should this be judged **per population** (Ghanaian vs Ethiopian vs AA) or against continuous ancestry?

**B3 · What makes a target "actionable / druggable"?**
For nominating drug targets.
*What we need:* the evidence bar — e.g., a DGIdb interaction tier, an existing drug in development, inclusion in a clinical guideline, or something stricter. Where's the line between "interesting" and "actionable"?

**B4 · What counts as a meaningful differential drug response in the organoids?**
For the PDO screen comparing AA- vs NHW-derived organoids.
*What we need:* the endpoint that defines a real ancestry-linked difference — an IC50 fold-change threshold, an Emax difference, and the significance you'd require to call it a hit.

**B5 · What result would you accept as disconfirmation?**
We're building the system so it can report an honest null — *"the ancestry effect is smaller than the pilot suggested"* — rather than only finding what we expect.
*What we need:* what would that look like to you? (e.g., effect sizes below the Part-B2 threshold across the primary comparisons, or a specific pre-registered bar.) This protects the work from being a confirmation engine.

---

*Thank you — even partial answers unblock the corresponding pieces. Each item maps to a specific gate in the pipeline, so anything you confirm here directly turns on the next stage of analysis.*
