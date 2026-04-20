CREATE TABLE IF NOT EXISTS control_plane_handoff_envelopes (
  envelope_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  runtime_task_id TEXT NOT NULL,
  from_control_plane_id TEXT NOT NULL,
  to_control_plane_id TEXT NOT NULL,
  committed_lease_id TEXT NOT NULL,
  term_no INTEGER NOT NULL,
  commit_index INTEGER NOT NULL,
  snapshot_payload_json TEXT NOT NULL,
  review_state_json TEXT NOT NULL,
  durable_refs_json TEXT NOT NULL,
  replay_excerpt_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_control_plane_handoff_run
  ON control_plane_handoff_envelopes(run_id, created_at);
