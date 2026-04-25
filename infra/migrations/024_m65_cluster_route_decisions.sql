CREATE TABLE IF NOT EXISTS cluster_route_decisions (
  decision_id TEXT PRIMARY KEY,
  goal TEXT NOT NULL,
  preset_id TEXT,
  selected_template_ids_json TEXT NOT NULL,
  preferred_template_ids_json TEXT NOT NULL,
  source TEXT NOT NULL,
  dynamic_enabled INTEGER NOT NULL DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cluster_route_decisions_created
  ON cluster_route_decisions (created_at DESC);
