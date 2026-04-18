CREATE TABLE IF NOT EXISTS memory_items (
  memory_item_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  namespace_id TEXT NOT NULL,
  source_candidate_id TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  source_refs_json TEXT NOT NULL,
  materialized_from TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_items_run_id
  ON memory_items(run_id);

CREATE INDEX IF NOT EXISTS idx_memory_items_namespace_id
  ON memory_items(namespace_id);

CREATE INDEX IF NOT EXISTS idx_memory_items_run_namespace
  ON memory_items(run_id, namespace_id);
