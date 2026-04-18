CREATE TABLE simulation_records (
  record_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  policy_id TEXT NOT NULL,
  status TEXT NOT NULL,
  triggered INTEGER NOT NULL,
  summary TEXT NOT NULL,
  recorded_from TEXT NOT NULL,
  report_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX idx_simulation_records_run_created
  ON simulation_records(run_id, created_at, record_id);

CREATE INDEX idx_simulation_records_policy
  ON simulation_records(policy_id, created_at, record_id);
