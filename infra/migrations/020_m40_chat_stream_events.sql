CREATE TABLE IF NOT EXISTS chat_stream_events (
  event_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  run_id TEXT,
  message_id TEXT,
  event_type TEXT NOT NULL,
  sequence_no INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_stream_events_session_sequence
  ON chat_stream_events(session_id, sequence_no ASC, event_id ASC);

CREATE INDEX IF NOT EXISTS idx_chat_stream_events_message
  ON chat_stream_events(message_id);
