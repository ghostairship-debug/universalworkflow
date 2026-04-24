CREATE TABLE IF NOT EXISTS chat_messages (
  message_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  run_id TEXT,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  message_type TEXT NOT NULL,
  action_type TEXT,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created_at
  ON chat_messages(session_id, created_at ASC, message_id ASC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_run_created_at
  ON chat_messages(run_id, created_at ASC, message_id ASC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_status_created_at
  ON chat_messages(status, created_at DESC);
