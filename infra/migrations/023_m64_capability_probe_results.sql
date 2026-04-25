CREATE TABLE IF NOT EXISTS capability_probe_results (
  probe_id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  adapter_name TEXT,
  status TEXT NOT NULL,
  live_probe INTEGER NOT NULL DEFAULT 0,
  auth_source TEXT,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  failure_class TEXT,
  evidence_path TEXT,
  fallback_route TEXT,
  return_code INTEGER,
  stdout_preview TEXT,
  stderr_preview TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_capability_probe_results_provider_created
  ON capability_probe_results (provider, created_at DESC);
