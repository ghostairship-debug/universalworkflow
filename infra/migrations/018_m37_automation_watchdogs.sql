CREATE TABLE IF NOT EXISTS automation_watchdogs (
  watchdog_id TEXT PRIMARY KEY,
  session_id TEXT,
  run_id TEXT,
  trigger TEXT NOT NULL,
  status TEXT NOT NULL,
  objective TEXT NOT NULL,
  auto_action_enabled INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_automation_watchdogs_session_created_at
  ON automation_watchdogs(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_watchdogs_run_created_at
  ON automation_watchdogs(run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_watchdogs_status_created_at
  ON automation_watchdogs(status, created_at DESC);
