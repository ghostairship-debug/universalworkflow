CREATE TABLE IF NOT EXISTS worker_leases (
  lease_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  runtime_task_id TEXT NOT NULL REFERENCES runtime_tasks(runtime_task_id) ON DELETE CASCADE,
  worker_name TEXT NOT NULL,
  adapter_name TEXT NOT NULL,
  status TEXT NOT NULL,
  heartbeat_at TEXT NOT NULL,
  lease_expires_at TEXT NOT NULL,
  released_at TEXT,
  release_reason TEXT,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_worker_leases_run_id_created_at
  ON worker_leases(run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_worker_leases_task_status
  ON worker_leases(runtime_task_id, status);
