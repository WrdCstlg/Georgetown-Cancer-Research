# AfriCAN DANCE — Insight-Distillation System
## Build Plan (v0.1)

**What this builds:** the computational layer that lets the research team ask cross-modal questions of the AfriCAN DANCE data and get grounded, traceable answers — and the AI producers that feed it. Not the wet lab, not the sequencing core; that stays with Dr. Laura's team.

**The thesis in one line:** the bottleneck to "seeing clearly" is not a shortage of models — it is that WES, RNA-seq, organoid, and clinical results live in separate files and separate manuscripts, and nothing lets a researcher join them. So the spine is a *fusion substrate with provenance*. Fast probabilistic producers (variant predictors, target-nominators, GNN, causal models) hang off it; a grounded query layer sits on top; the wet lab is the physical ground-truth layer. Qiwu's doc is a good menu of producers — this plan is the substrate that turns their outputs into insight.

---

## 0. Orienting principles

1. **Substrate first.** Every producer is worthless for *distillation* until there is one object to write into. Build the spine before the models.
2. **Fast / slow separation.** Probabilistic layers (ML) produce candidates; the authoritative layer (the graph + provenance) is what you trust and query; the wet lab is what you believe. Never let a prediction masquerade as a fact — carry its model version, n, and method as first-class properties.
3. **De-risking build order.** Cheapest highest-leverage move first (the AlphaMissense/EVE join), substrate early (it is the precondition), ambitious models last (they earn their place against ground truth).
4. **Reviewer-legible.** Frame everything as *method in service of the science* — closing the VUS gap, improving screen efficiency — not as ML for its own sake. This wins the study section and keeps the substrate reusable rather than branded as a CRC-specific tool.
5. **Ancestry continuous, everywhere.** AFR proportion (ADMIXTURE global + RFMix local) is the covariate, not self-reported race. The system should make the binary framing hard to reach for by accident.
6. **Measure before you mutate.** Build ingestion adapters and schema against *existing* pipeline outputs and validate them before touching the live nf-core pipeline. Price the blast radius of any change to the calling step before authorizing it.

---

## 1. Decisions to settle before code (Phase 0)

These gate the build. Each is a decision record — question, options, why it matters.

| # | Decision | Options | Why it gates the build |
|---|----------|---------|------------------------|
| D1 | **Ownership / IP of the substrate** | (a) Senan/Qiwu-owned infrastructure reused across projects; (b) grant deliverable owned by the institution | Determines whether you walk away with a reusable asset or billed hours. Changes what you build and how you license it. **Settle this before anything.** |
| D2 | **Compute & data residency** | Institutional HPC / lab cluster / cloud (GPU tier for the nets) | Cross-site (Ghana/Ethiopia) specimens may carry data-use constraints; PHI vs. de-identified location dictates architecture. |
| D3 | **Data governance** | IRB scope, de-identification, DUAs, DB licensing (ClinVar/COSMIC/CIViC/DGIdb) | COSMIC and some resources are license-gated for commercial use; relevant if D1 lands on "owned infra." |
| D4 | **Substrate DB: build vs. buy** | Self-hosted Postgres+pgvector / managed Postgres / DuckDB (single-analyst) | Ops burden vs. control. Recommendation below, but this is a real call. |
| D5 | **Custom multi-modal predictor: commit or gate** | Build now / gate on whether AlphaMissense+EVE already clears the VUS bar | The 4–6 month ML build is only worth it if the cheap join leaves meaningful residual VUS. Decide *after* Phase 2 data. |
| D6 | **Reproducibility contract** | Nextflow provenance + DVC or lakeFS (data) + MLflow (models) + a provenance schema | For an R01, lineage is what makes a reviewer/clinician trust the chain. Non-optional. |

---

## 2. Architecture

### Layers

- **Ingestion / pipeline** — Nextflow + nf-core/sarek, containerized (Singularity on HPC). Keep what the team has. Two corrections at the calling step (see Phase 2): DeepSomatic (not DeepVariant) for somatic tumor-normal; a graph-genome toolchain (vg/Giraffe) for the pangenome arm.
- **Fusion core** — the spine. Postgres + pgvector as the shared, persistent asset; graph modeled *logically* on top; a PPI-annotated graph export materialized only where the GNN needs it. DuckDB for local analytical work.
- **Producers** — R/Bioconductor for statistical genomics (DESeq2, MAFtools, fgsea, limma); Python for everything new (PyTorch, PyTorch Geometric, scikit-learn, CellPose); EconML/DoubleML for causal.
- **Reasoning / query** — grounded text-to-SQL/Cypher over the substrate + a literature vector index, every claim linked to a provenance edge.
- **Interface** — Streamlit/Dash for an internal tool (fast), or FastAPI + React/Next for the durable shared asset.

### Languages

| Language | Role | Keep / new |
|----------|------|-----------|
| Nextflow (Groovy DSL) | pipeline orchestration | keep |
| Python | ML, glue, API, causal, imaging | new — center of gravity |
| R / Bioconductor | statistical genomics | keep |
| SQL | the fusion core | new |
| TypeScript / React | durable UI (optional) | new, only if D-interface = durable |

**Interop:** Parquet / Arrow as the lingua franca between R and Python so they stop fighting over formats.

### The two payoff objects

1. **Unified cohort table** — one row per tumor, all modalities joined, ancestry as continuous AFR proportion.
2. **Per-variant evidence chain** — raw calls on both references → reclassified pathogenicity → cross-ancestry frequency deltas → IntOGen driver q-values → expression consequence (MatrixEQTL) → Cox survival association → DGIdb druggability → organoid variant-dependent sensitivity. That chain, per variant, in one place, is the feature that does the distilling. Today it is a seven-way join across seven people's outputs.

---

## 3. Phased build

Each phase carries a maturity gate: **SPECIFIED** (reasoned, decision-recorded, unbuilt) → **FUNCTIONAL** (runs end-to-end, acceptance met).

### Phase 1 — Fusion substrate *(the spine)*
- Schema: entities (variant, gene, pathway, patient, ancestry-stratum, signature, organoid line, drug) + edges whose properties carry provenance (pipeline version, reference used, QC status, model version, n, method, timestamp).
- Ingestion adapters from existing outputs: sarek MAFs, DESeq2 tables, IntOGen results, MSISensor2, ADMIXTURE/RFMix, drug-screen readouts. Build and validate against current outputs *before* wiring into the live pipeline.
- Reference reconciliation: key variants by (locus, ref-context); reconcile GRCh38 vs. pangenome callsets; flag pangenome-only-in-African-ancestry as candidate ancestry-enriched drivers vs. reference artifacts. This is where real ancestry signal — and a lot of false signal — lives.
- **Acceptance (FUNCTIONAL):** a researcher runs one query joining ≥3 modalities and gets a provenance-tagged result.

### Phase 2 — Aim 1 assists *(cheap, highest leverage — first shippable win)*
- **AlphaMissense + EVE join.** Pre-computed scores → annotate variant nodes. Near-zero effort, directly attacks the 87–92% VUS wall. Multi-tool consensus (retain PolyPhen/SIFT), stratified by ancestry.
- **DeepSomatic** added at the calling step for somatic tumor-normal, run in parallel with Mutect2; compare callsets to quantify reference/caller bias. (Qiwu's doc says "DeepVariant" — that is a germline caller; DeepSomatic is the somatic counterpart.)
- Reclassified variant table feeds the IntOGen driver-identification step.
- **Acceptance (FUNCTIONAL):** reclassification pipeline runs end-to-end on the 150-tumor preliminary data; VUS-fraction reduction measured (target ~90% → ~25–30%, framed as a target, not a promise). This is the result that converts "guaranteed pathway" into a demonstrated contribution.

### Phase 3 — Aim 2a assists *(target nomination + network)*
- Keep the elastic-net + random-forest ensemble (reimplement in Python to consolidate ML lineage, or keep glmnet/ranger and bridge via Arrow).
- Add a **GNN** over the PPI graph (STRING/BioGRID tagged with the study's mutation + expression data; PyTorch Geometric) to surface collectively-rewired neighborhoods a single-gene ranking misses.
- Wire DGIdb (druggability), MatrixEQTL (eQTL), and Cox (survival) as edges on the target nodes → the multi-criterion ranked target object becomes interactive and sortable with drill-down.
- **Acceptance (FUNCTIONAL):** a ranked druggable-target list that reproduces/extends the "12 candidates," each with its full evidence chain visible.

### Phase 4 — Reasoning / query layer *(the "distill" deliverable)*
- Grounded NL query: text-to-SQL/Cypher with schema validation; retrieval over the graph + literature (ClinVar/COSMIC/CIViC/DGIdb/PubMed via pgvector); every claim linked to a provenance edge; the query is shown. Lean orchestration (LangGraph or direct API calls — skip the heavy framework). **Guardrail:** no ungrounded clinical claims — an ungrounded model that invents a survival association is worse than no tool.
- Interface views: cohort explorer, per-variant evidence-chain viewer, target dashboard — all sliceable by continuous AFR proportion, with robust-vs-exploratory visually encoded (the grant already flags NHW N=100 comparisons as exploratory; the UI should make over-reading a thin cell hard).
- **Acceptance (FUNCTIONAL):** a cross-modal NL question ("which druggable, ancestry-enriched drivers have both a survival association in high-AFR patients and organoid evidence?") returns a cited, query-backed answer.

### Phase 5 — Aim 2b assists *(gated on wet-lab data availability)*
- **Drug-response pre-screen** (GDSC/CCLE/DepMap-trained) as *triage under wide uncertainty*, not a screen replacement — framed honestly for 50 lines with cross-domain transfer.
- **Organoid imaging:** CellPose segmentation + CNN morphological features (brightfield Day 0/7/14) to catch sub-lethal structural effects the CellTiter-Glo viability readout is blind to.
- **Causal layer (elevated to headline):** Double ML / causal forests (EconML/DoubleML) estimating variant→drug-response causal effects, validated against the CRISPR knock-in/reversion isogenics. The CRISPR arm is interventional ground truth — the difference between "correlates with resistance" and "causes resistance," which is the actionable-vs-descriptive line the grant keeps drawing. This is the strongest novel-methods contribution.
- **Custom multi-modal variant predictor (D5, if committed):** trained on the study's globally-unique matched data + organoid ground truth. **Leakage warning:** hold out whole organoid *lines* — if the predictor trains on organoid data and then nominates targets that get organoid-validated, the validation is contaminated.
- **Acceptance (FUNCTIONAL):** imaging pipeline quantifies morphology; causal estimates bidirectionally validated against CRISPR isogenics.

---

## 4. Risks & guardrails (cross-cutting)

- **Leakage / circularity** — hold out whole organoid lines; keep the custom predictor's training strictly separated from the validation it will be judged against.
- **Small-N honesty** — 50 lines, some strata n<4 (hence CRISPR augmentation). Frame the drug-response pre-screen as prioritization with wide error bars.
- **Ancestry continuous** — bake AFR proportion into every view; never collapse to self-reported race in the analytics.
- **Reference bias** — the GRCh38-vs-pangenome reconciliation is load-bearing; getting it wrong manufactures spurious African-specific drivers, the exact failure the grant is trying to avoid.
- **Provenance = trust** — surface confidence and lineage on every number.
- **Reviewer framing** — method in service of science; the VUS gap is the compelling, grounded hook.

---

## 5. Roles & staffing

| Workstream | Skill needed | Likely owner |
|-----------|--------------|--------------|
| Architecture, substrate design, causal layer, specs | systems + causal inference | Senan |
| Producer pipeline (variant reclass, GNN, imaging) | bioinformatics + ML eng | Qiwu / +1 ML engineer *(scope TBD — see open questions)* |
| Statistical genomics (DE, drivers, signatures) | R/Bioconductor | lab bioinformatician |
| Wet lab, organoids, CRISPR, sequencing | wet-lab | Dr. Laura's team |

Qiwu's doc names the needs directly: a dedicated ML engineer (custom predictor), graph-ML expertise (GNN), causal-inference expertise (Innovation 3). The build sequence lets one strong bioinformatician + one ML engineer cover Phases 1–4; Phase 5's causal/imaging work is where the specialized skill pays off.

---

## 6. Sequencing & dependencies

- **Now (weeks):** Phase 0 decisions (esp. D1 ownership) → Phase 1 substrate → Phase 2 AlphaMissense/EVE quick win. Phase 2 is the demonstrated result that anchors the collaboration.
- **Then (months):** Phase 3 (target nomination + GNN) and Phase 4 (query layer) can overlap once the substrate is FUNCTIONAL.
- **Later (gated):** Phase 5 cannot start until organoid specimens/drug-screen data exist. Do not commit the ML-engineer hire to Phase 5 timing until that data pipeline is real.
- Qiwu's doc effort estimates are reasonable *inputs* (AlphaMissense 2–3 wks; DeepSomatic 1–2 wks; imaging 2–3 mo; custom predictor 4–6 mo) — treat them as relative sizing, not calendar commitments, because they assume data and staff that D0 has to confirm.

---

## 7. Open questions / to verify

- **D1 ownership** — the single most important unresolved item.
- **Qiwu's scope** — which producers he owns vs. a new hire; this shapes Phases 2–5 staffing.
- Exact **data location** and cross-site governance constraints.
- **IRB scope** for the computational reuse of specimens' derived data.
- Whether the **custom multi-modal predictor** is worth building — decide after Phase 2 shows the residual VUS.
- **Current SOTA** on variant-effect and somatic-calling tools shifts fast; re-verify the specific tool picks at build time (happy to run that check).
