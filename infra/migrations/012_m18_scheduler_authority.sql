CREATE TABLE IF NOT EXISTS scheduler_lease_proposals (
  proposal_id TEXT PRIMARY KEY,
  control_plane_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  runtime_task_id TEXT NOT NULL,
  domain_kind TEXT NOT NULL,
  domain_key TEXT NOT NULL,
  requested_lease_seconds INTEGER NOT NULL,
  requested_epoch INTEGER NOT NULL,
  status TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_scheduler_lease_proposals_run
  ON scheduler_lease_proposals(run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_scheduler_lease_proposals_task
  ON scheduler_lease_proposals(runtime_task_id, created_at);

CREATE INDEX IF NOT EXISTS idx_scheduler_lease_proposals_domain
  ON scheduler_lease_proposals(domain_kind, domain_key, created_at);

CREATE TABLE IF NOT EXISTS scheduler_lease_decisions (
  decision_id TEXT PRIMARY KEY,
  lease_id TEXT NOT NULL,
  proposal_id TEXT NOT NULL,
  control_plane_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  runtime_task_id TEXT NOT NULL,
  domain_kind TEXT NOT NULL,
  domain_key TEXT NOT NULL,
  lease_epoch INTEGER NOT NULL,
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  lease_expires_at TEXT NOT NULL,
  released_at TEXT,
  release_reason TEXT,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES runs(run_id),
  FOREIGN KEY(proposal_id) REFERENCES scheduler_lease_proposals(proposal_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduler_lease_decisions_lease
  ON scheduler_lease_decisions(lease_id);

CREATE INDEX IF NOT EXISTS idx_scheduler_lease_decisions_run
  ON scheduler_lease_decisions(run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_scheduler_lease_decisions_domain
  ON scheduler_lease_decisions(domain_kind, domain_key, created_at);

CREATE TABLE IF NOT EXISTS scheduler_peer_heartbeats (
  heartbeat_id TEXT PRIMARY KEY,
  control_plane_id TEXT NOT NULL,
  status TEXT NOT NULL,
  lease_count INTEGER NOT NULL,
  observed_at TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scheduler_peer_heartbeats_control_plane
  ON scheduler_peer_heartbeats(control_plane_id, observed_at);
