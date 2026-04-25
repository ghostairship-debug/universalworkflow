CREATE TABLE IF NOT EXISTS operator_action_receipts (
  receipt_id TEXT PRIMARY KEY,
  action_type TEXT NOT NULL,
  workspace_root TEXT NOT NULL,
  risk_level TEXT NOT NULL,
  operator_id TEXT NOT NULL,
  requested_write_set_json TEXT NOT NULL,
  nonce TEXT NOT NULL,
  status TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  consumed_at TEXT,
  metadata_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  audit_timestamp TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_operator_action_receipts_nonce
  ON operator_action_receipts(nonce);

CREATE INDEX IF NOT EXISTS idx_operator_action_receipts_action_status
  ON operator_action_receipts(action_type, status, expires_at);
