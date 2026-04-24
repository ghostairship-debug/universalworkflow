CREATE TABLE IF NOT EXISTS followup_requests (
  request_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  run_id TEXT,
  intent TEXT NOT NULL,
  blocking INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  instruction TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_followup_requests_session_created_at
  ON followup_requests(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_followup_requests_run_created_at
  ON followup_requests(run_id, created_at DESC);
