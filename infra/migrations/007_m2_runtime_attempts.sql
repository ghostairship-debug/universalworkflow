CREATE TABLE IF NOT EXISTS runtime_attempts (
  attempt_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  runtime_task_id TEXT NOT NULL,
  sequence_no INTEGER NOT NULL,
  trigger TEXT NOT NULL,
  status TEXT NOT NULL,
  superseded_by_attempt_id TEXT,
  superseded_at TEXT,
  supersede_reason TEXT,
  closed_at TEXT,
  close_reason TEXT,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_attempts_run_sequence
  ON runtime_attempts(run_id, sequence_no);

CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_attempts_current_run
  ON runtime_attempts(run_id)
  WHERE status = 'current';

CREATE INDEX IF NOT EXISTS idx_runtime_attempts_run_status_created_at
  ON runtime_attempts(run_id, status, created_at);

CREATE INDEX IF NOT EXISTS idx_runtime_attempts_runtime_task_id_created_at
  ON runtime_attempts(runtime_task_id, created_at);
