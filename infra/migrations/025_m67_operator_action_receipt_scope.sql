ALTER TABLE operator_action_receipts
  ADD COLUMN scope_hash TEXT;

ALTER TABLE operator_action_receipts
  ADD COLUMN scope_payload_json TEXT NOT NULL DEFAULT '{}';
