CREATE TABLE IF NOT EXISTS capability_invocations (
  invocation_id TEXT PRIMARY KEY,
  receipt_id TEXT,
  capability_id TEXT NOT NULL,
  provider_kind TEXT NOT NULL,
  run_id TEXT,
  runtime_task_id TEXT,
  status TEXT NOT NULL,
  return_code INTEGER,
  adapter_name TEXT,
  duration_ms INTEGER NOT NULL,
  failure_class TEXT,
  payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_capability_invocations_capability_created
  ON capability_invocations(capability_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_capability_invocations_run
  ON capability_invocations(run_id, runtime_task_id);
