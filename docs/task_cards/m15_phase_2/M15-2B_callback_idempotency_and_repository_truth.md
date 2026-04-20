# M15-2B Callback Idempotency And Repository Truth

- Goal: record heartbeat and completion callbacks idempotently without losing controller-owned truth.
- Write set: `apps/orchestrator_api/main.py`, `packages/core_domain/repositories.py`, `packages/core_domain/services.py`.
- Acceptance:
  - callbacks touch leases and state payloads safely
  - duplicate completion callbacks are accepted idempotently
  - SQLite lock contention is handled by tighter transaction boundaries
