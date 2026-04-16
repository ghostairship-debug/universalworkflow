CREATE TABLE IF NOT EXISTS _migrations (
  migration_id TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  goal TEXT NOT NULL,
  preset_id TEXT NOT NULL,
  status TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS phases (
  phase_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  order_index INTEGER NOT NULL,
  status TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_cards (
  task_card_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  acceptance_criteria_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_tasks (
  runtime_task_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  phase_id TEXT NOT NULL REFERENCES phases(phase_id) ON DELETE CASCADE,
  task_card_id TEXT NOT NULL REFERENCES task_cards(task_card_id) ON DELETE CASCADE,
  task_kind TEXT NOT NULL,
  status TEXT NOT NULL,
  summary TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_packets (
  task_packet_id TEXT PRIMARY KEY,
  runtime_task_id TEXT NOT NULL REFERENCES runtime_tasks(runtime_task_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  task_kind TEXT NOT NULL,
  command_json TEXT NOT NULL,
  working_directory TEXT NOT NULL,
  env_json TEXT NOT NULL,
  expected_artifacts_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  runtime_task_id TEXT NOT NULL REFERENCES runtime_tasks(runtime_task_id) ON DELETE CASCADE,
  summary TEXT NOT NULL,
  changed_files_json TEXT NOT NULL,
  checks_json TEXT NOT NULL,
  known_gaps_json TEXT NOT NULL,
  artifact_refs_json TEXT NOT NULL,
  return_code INTEGER NOT NULL,
  raw_execution_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_verdicts (
  verdict_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
  decision TEXT NOT NULL,
  rationale TEXT NOT NULL,
  reviewer_type TEXT NOT NULL,
  reviewed_at TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS preset_definitions (
  preset_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  allowed_task_kinds_json TEXT NOT NULL,
  default_review_policy TEXT NOT NULL,
  default_budget_policy_json TEXT NOT NULL,
  requires_manual_approval INTEGER NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_events (
  event_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);
CREATE INDEX IF NOT EXISTS idx_runtime_tasks_run_id ON runtime_tasks(run_id);
CREATE INDEX IF NOT EXISTS idx_task_packets_runtime_task_id ON task_packets(runtime_task_id);
CREATE INDEX IF NOT EXISTS idx_evidence_runtime_task_id ON evidence(runtime_task_id);
CREATE INDEX IF NOT EXISTS idx_run_events_run_id_created_at ON run_events(run_id, created_at);
