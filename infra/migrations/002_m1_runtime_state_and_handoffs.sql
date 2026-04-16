CREATE TABLE IF NOT EXISTS handoff_lite (
  handoff_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  from_phase_id TEXT NOT NULL REFERENCES phases(phase_id) ON DELETE CASCADE,
  to_phase_id TEXT NOT NULL REFERENCES phases(phase_id) ON DELETE CASCADE,
  summary TEXT NOT NULL,
  blocking_risks_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_state_refs (
  state_ref_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  runtime_task_id TEXT NOT NULL REFERENCES runtime_tasks(runtime_task_id) ON DELETE CASCADE,
  graph_step TEXT NOT NULL,
  state_payload_json TEXT NOT NULL,
  is_terminal INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_state_refs_runtime_task_id
  ON runtime_state_refs(runtime_task_id);

CREATE INDEX IF NOT EXISTS idx_handoff_lite_run_id_created_at
  ON handoff_lite(run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_runtime_state_refs_run_id_updated_at
  ON runtime_state_refs(run_id, updated_at);
