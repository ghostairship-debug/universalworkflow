CREATE TABLE IF NOT EXISTS run_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  stage TEXT NOT NULL,
  run_status TEXT NOT NULL,
  runtime_task_id TEXT REFERENCES runtime_tasks(runtime_task_id) ON DELETE SET NULL,
  summary TEXT NOT NULL,
  snapshot_payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_run_snapshots_run_id_created_at
  ON run_snapshots(run_id, created_at);
