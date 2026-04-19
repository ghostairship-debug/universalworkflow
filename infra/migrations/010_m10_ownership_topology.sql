ALTER TABLE runtime_claims ADD COLUMN owner_kind TEXT NOT NULL DEFAULT 'control_plane';
ALTER TABLE runtime_claims ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'control_plane_local';
ALTER TABLE runtime_claims ADD COLUMN domain_kind TEXT NOT NULL DEFAULT 'runtime_task';
ALTER TABLE runtime_claims ADD COLUMN domain_key TEXT;
ALTER TABLE runtime_claims ADD COLUMN attempt_id TEXT;

UPDATE runtime_claims
SET domain_key = runtime_task_id
WHERE domain_key IS NULL;

CREATE INDEX IF NOT EXISTS idx_runtime_claims_domain_status_created_at
  ON runtime_claims(domain_kind, domain_key, status, created_at);

ALTER TABLE worker_leases ADD COLUMN worker_kind TEXT NOT NULL DEFAULT 'worker';
ALTER TABLE worker_leases ADD COLUMN worker_id TEXT NOT NULL DEFAULT 'worker_local';
ALTER TABLE worker_leases ADD COLUMN domain_kind TEXT NOT NULL DEFAULT 'runtime_task';
ALTER TABLE worker_leases ADD COLUMN domain_key TEXT;
ALTER TABLE worker_leases ADD COLUMN claim_id TEXT;
ALTER TABLE worker_leases ADD COLUMN attempt_id TEXT;

UPDATE worker_leases
SET domain_key = runtime_task_id
WHERE domain_key IS NULL;

CREATE INDEX IF NOT EXISTS idx_worker_leases_domain_status_created_at
  ON worker_leases(domain_kind, domain_key, status, created_at);
