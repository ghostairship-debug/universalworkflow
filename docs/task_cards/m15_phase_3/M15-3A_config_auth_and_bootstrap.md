# M15-3A Config, Auth, And Bootstrap

- Goal: make the remote worker path configurable and deployable.
- Write set: `packages/core_domain/config.py`, `infra/seeds/worker_pool_profiles.json`, docs.
- Acceptance:
  - `workflow.toml` can express callback base URL, shared-secret presence, and remote timeout settings
