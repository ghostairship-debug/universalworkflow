CREATE TABLE IF NOT EXISTS intent_sessions (
  session_id TEXT PRIMARY KEY,
  goal TEXT NOT NULL,
  status TEXT NOT NULL,
  active_run_id TEXT,
  payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_intent_sessions_status_created_at
  ON intent_sessions(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_intent_sessions_active_run
  ON intent_sessions(active_run_id);
