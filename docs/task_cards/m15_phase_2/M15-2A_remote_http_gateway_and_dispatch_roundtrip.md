# M15-2A Remote HTTP Gateway And Dispatch Roundtrip

- Goal: upgrade the external worker gateway from loopback-only to real HTTP dispatch.
- Write set: `packages/core_domain/external_workers.py`, `packages/core_domain/service_lifecycle.py`.
- Acceptance:
  - control plane can dispatch to remote worker and continue the normal lifecycle
  - dispatch acceptance is recorded as an event
