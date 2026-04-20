# M15-4A Recovery, Duplicate Callback, And Release Hardening

- Goal: close the minimal production hardening loop for remote workers.
- Acceptance:
  - duplicate callbacks do not corrupt state
  - remote worker roundtrip tests cover heartbeat/completion/replay truth
