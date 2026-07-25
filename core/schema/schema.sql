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
  population_code    TEXT NOT NULL REFERENCES population(code),
  clinical_db_absent INTEGER NOT NULL DEFAULT 0    -- Postgres: BOOLEAN
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

  tool_calls_json     TEXT    NOT NULL                         -- detail; Postgres: JSONB
);

CREATE INDEX IF NOT EXISTS ix_ver_variant ON variant_effect_result(variant_id);
CREATE INDEX IF NOT EXISTS ix_ver_population ON variant_effect_result(population_code);

-- Read surface for the query layer (read path).  The query layer reads THIS,
-- never the base tables -- keeping the read/write seam clean (ARCHITECTURE.md 4.3).
CREATE VIEW IF NOT EXISTS v_variant_effect AS
SELECT r.variant_id, v.gene, v.protein_change, r.population_code,
       r.original_classification, r.new_classification,
       r.calibration_status, r.calibration_pending,
       r.producer, r.producer_version, r.method, r.reference, r.generated_at
FROM variant_effect_result r
JOIN variant v ON v.variant_id = r.variant_id;
