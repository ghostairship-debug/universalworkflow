CREATE TABLE IF NOT EXISTS budget_ledgers (
  ledger_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id) ON DELETE CASCADE,
  preset_id TEXT NOT NULL,
  max_retries INTEGER NOT NULL,
  timeout_seconds INTEGER NOT NULL,
  compile_count INTEGER NOT NULL,
  recompile_count INTEGER NOT NULL,
  execution_count INTEGER NOT NULL,
  total_runtime_ms INTEGER NOT NULL,
  last_return_code INTEGER,
  updated_at TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_budget_ledgers_run_id
  ON budget_ledgers(run_id);
