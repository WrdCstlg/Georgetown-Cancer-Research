-- Fusion core schema.  Dev/target: SQLite (embedded, runnable in fixtures/CI).
-- Production substrate: PENDING decision D4 (PostgreSQL + pgvector proposed).
-- Deltas noted inline are for the proposed target.
--
-- Design invariant (ARCHITECTURE.md 4.5): a prediction is NEVER stored as a bare
-- fact.  Provenance and per-population calibration are FIRST-CLASS, NOT NULL
-- columns -- the database itself refuses to accept a result that lacks them.

CREATE TABLE IF NOT EXISTS population (
  code        TEXT PRIMARY KEY,          -- AA | GHA | ETH | NHW  (never a monolithic "African")
  description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS variant (
  variant_id         TEXT PRIMARY KEY,
  gene               TEXT NOT NULL,
  protein_change     TEXT NOT NULL,
  reference          TEXT NOT NULL CHECK (reference IN ('grch38','pangenome')),
  clinical_db_absent INTEGER NOT NULL DEFAULT 0    -- Postgres: BOOLEAN
  -- D-004 (PROPOSED): a variant is a genomic fact. Population is a property of the
  -- OBSERVATION and lives only on variant_effect_result -- never an overwritable
  -- attribute here. `reference` stays: it is part of variant identity (SPEC-004).
);

CREATE TABLE IF NOT EXISTS variant_effect_result (
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,   -- Postgres: GENERATED ALWAYS AS IDENTITY
  variant_id              TEXT NOT NULL REFERENCES variant(variant_id),
  original_classification TEXT NOT NULL,
  new_classification      TEXT NOT NULL CHECK (new_classification IN ('benign','pathogenic','VUS')),

  -- provenance (first-class, NOT NULL) --
  producer          TEXT    NOT NULL,
  producer_version  TEXT    NOT NULL,
  method            TEXT    NOT NULL,
  n_tools_fired     INTEGER NOT NULL,
  reference         TEXT    NOT NULL,
  population_code   TEXT    NOT NULL REFERENCES population(code),
  generated_at      TEXT    NOT NULL,                          -- Postgres: TIMESTAMPTZ

  -- calibration (first-class, NOT NULL) --
  calibration_status  TEXT    NOT NULL
      CHECK (calibration_status IN ('in_calibration','out_of_calibration','calibration_pending')),
  calibration_pending INTEGER NOT NULL,                        -- Postgres: BOOLEAN

  tool_calls_json     TEXT    NOT NULL,                         -- detail; Postgres: JSONB

  -- D-005 (PROPOSED): one result per (variant, population, producer, method) — the
  -- natural key of an OBSERVATION (D-004). Re-ingesting the same key REPLACES (upsert);
  -- the database refuses duplicate facts the way it refuses missing provenance.
  -- Run history is deferred to D6.
  UNIQUE (variant_id, population_code, producer, method)
);

CREATE INDEX IF NOT EXISTS ix_ver_variant ON variant_effect_result(variant_id);
CREATE INDEX IF NOT EXISTS ix_ver_population ON variant_effect_result(population_code);

-- ---------------------------------------------------------------------------
-- Multi-producer results (SPEC-029, decision D-012 PROPOSED).
--
-- variant_effect_result above is shaped for ONE producer.  Seven more are
-- planned (drivers, expression, target_nomination, gnn, causal, imaging,
-- multimodal_predictor) and had nowhere to write.  This is the generic landing
-- table: the CROSS-CUTTING provenance and calibration columns stay NOT NULL --
-- so the database refuses a second producer's bare fact exactly as it already
-- refuses variant_effect's (ARCHITECTURE.md 4.5) -- while the producer-specific
-- payload lives in result_json, whose SHAPE is enforced at the contracts/ seam.
--
-- The trade is stated in D-012 and not glossed: the database can no longer
-- type-check a producer's domain fields.  What it still guarantees is exactly
-- what the design invariant names -- provenance and per-population calibration
-- on every stored result.  (Precedent: variant_effect_result.tool_calls_json is
-- already an untyped payload beside typed provenance.)
--
-- variant_effect_result is deliberately NOT migrated into this table: its
-- natural key and upsert semantics are pinned by D-004/D-005 and tested by
-- SPEC-025.  Two shapes coexist for now; unifying is a separate change.
CREATE TABLE IF NOT EXISTS producer_result (
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,
  variant_id              TEXT NOT NULL REFERENCES variant(variant_id),
  population_code         TEXT NOT NULL REFERENCES population(code),

  -- provenance (first-class, NOT NULL) --
  producer          TEXT    NOT NULL,
  producer_version  TEXT    NOT NULL,
  method            TEXT    NOT NULL,
  reference         TEXT    NOT NULL,
  generated_at      TEXT    NOT NULL,

  -- calibration (first-class, NOT NULL) --
  calibration_status  TEXT    NOT NULL
      CHECK (calibration_status IN ('in_calibration','out_of_calibration','calibration_pending')),
  calibration_pending INTEGER NOT NULL,

  -- payload: what KIND of result, and the producer-specific detail --
  result_type       TEXT NOT NULL,   -- e.g. 'driver_evidence'
  result_json       TEXT NOT NULL,   -- shape enforced in contracts/, not here

  -- D-005 semantics, extended with result_type: one result per observation
  UNIQUE (variant_id, population_code, producer, method, result_type)
);

CREATE INDEX IF NOT EXISTS ix_pr_variant ON producer_result(variant_id);
CREATE INDEX IF NOT EXISTS ix_pr_type    ON producer_result(result_type);

-- Producer-NEUTRAL variant read view.  Without this a second producer would
-- have to read v_variant_effect -- one producer reading another producer's
-- output -- which ARCHITECTURE.md 4.2 exists to forbid.
CREATE VIEW IF NOT EXISTS v_variant AS
SELECT v.variant_id, v.gene, v.protein_change, v.reference, v.clinical_db_absent,
       r.population_code
FROM variant v
JOIN (SELECT DISTINCT variant_id, population_code FROM variant_effect_result
      UNION
      SELECT DISTINCT variant_id, population_code FROM producer_result) r
  ON r.variant_id = v.variant_id;

-- Read surface for any producer_result, with provenance + calibration attached.
CREATE VIEW IF NOT EXISTS v_producer_result AS
SELECT p.variant_id, v.gene, v.protein_change, p.population_code,
       p.result_type, p.result_json,
       p.calibration_status, p.calibration_pending,
       p.producer, p.producer_version, p.method, p.reference, p.generated_at
FROM producer_result p
JOIN variant v ON v.variant_id = p.variant_id;

-- Read surface for the query layer (read path).  The query layer reads THIS,
-- never the base tables -- keeping the read/write seam clean (ARCHITECTURE.md 4.3).
CREATE VIEW IF NOT EXISTS v_variant_effect AS
SELECT r.variant_id, v.gene, v.protein_change, r.population_code,
       r.original_classification, r.new_classification,
       r.calibration_status, r.calibration_pending,
       r.producer, r.producer_version, r.method, r.reference, r.generated_at
FROM variant_effect_result r
JOIN variant v ON v.variant_id = r.variant_id;
