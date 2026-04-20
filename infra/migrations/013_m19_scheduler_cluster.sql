CREATE TABLE IF NOT EXISTS authority_node_identities (
  node_id TEXT PRIMARY KEY,
  bind_url TEXT NOT NULL,
  status TEXT NOT NULL,
  role TEXT NOT NULL,
  last_heartbeat_at TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_consensus_terms (
  term_id TEXT PRIMARY KEY,
  term_no INTEGER NOT NULL UNIQUE,
  leader_node_id TEXT NOT NULL,
  quorum_size INTEGER NOT NULL,
  commit_index INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  last_heartbeat_at TEXT NOT NULL,
  closed_at TEXT,
  close_reason TEXT,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduler_vote_records (
  vote_id TEXT PRIMARY KEY,
  proposal_id TEXT NOT NULL,
  term_no INTEGER NOT NULL,
  voter_node_id TEXT NOT NULL,
  vote TEXT NOT NULL,
  reason TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(proposal_id, voter_node_id)
);

CREATE TABLE IF NOT EXISTS scheduler_committed_leases (
  committed_lease_id TEXT PRIMARY KEY,
  lease_id TEXT NOT NULL UNIQUE,
  proposal_id TEXT NOT NULL,
  decision_id TEXT,
  control_plane_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  runtime_task_id TEXT NOT NULL,
  domain_kind TEXT NOT NULL,
  domain_key TEXT NOT NULL,
  term_no INTEGER NOT NULL,
  commit_index INTEGER NOT NULL,
  lease_epoch INTEGER NOT NULL,
  fencing_token TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  lease_expires_at TEXT NOT NULL,
  released_at TEXT,
  release_reason TEXT,
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scheduler_committed_leases_domain
  ON scheduler_committed_leases(domain_kind, domain_key, created_at);

CREATE INDEX IF NOT EXISTS idx_scheduler_vote_records_proposal
  ON scheduler_vote_records(proposal_id, created_at);
