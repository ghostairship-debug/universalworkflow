# M15-1B Worker Pool Contract Extension

- Goal: extend worker-pool contracts for auth, callback, and lease metadata.
- Write set: `packages/contracts/models.py`, `packages/core_domain/config.py`, seed profiles.
- Acceptance:
  - worker pool profiles encode auth mode, shared-secret env, callback base URL, heartbeat cadence, and lease TTL
