CREATE TABLE IF NOT EXISTS generated_agent_profiles (
  generated_profile_id TEXT PRIMARY KEY,
  base_profile_id TEXT,
  source_type TEXT NOT NULL,
  public_role TEXT NOT NULL,
  role_label TEXT NOT NULL,
  session_id TEXT,
  run_id TEXT,
  cluster_template_id TEXT,
  payload_json TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_generated_agent_profiles_session_created_at
  ON generated_agent_profiles(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_generated_agent_profiles_run_created_at
  ON generated_agent_profiles(run_id, created_at DESC);
