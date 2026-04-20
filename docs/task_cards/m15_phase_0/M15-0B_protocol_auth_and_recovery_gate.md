# M15-0B Protocol, Auth, And Recovery Gate

- Goal: freeze protocol, auth, lease, callback, and recovery expectations before implementation breadth.
- Acceptance:
  - `dispatches`, `worker-callbacks/heartbeat`, and `worker-callbacks/completion` are the authoritative HTTP contract
  - shared-secret auth and callback idempotency are mandatory
