CREATE TABLE IF NOT EXISTS runtime_claims (
  claim_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  runtime_task_id TEXT NOT NULL,
  owner TEXT NOT NULL,
  status TEXT NOT NULL,
  lease_expires_at TEXT NOT NULL,
  released_at TEXT,
  release_reason TEXT,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runtime_claims_run_id_created_at
  ON runtime_claims(run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_runtime_claims_runtime_task_id_created_at
  ON runtime_claims(runtime_task_id, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_claims_active_runtime_task
  ON runtime_claims(runtime_task_id)
  WHERE status = 'active';
