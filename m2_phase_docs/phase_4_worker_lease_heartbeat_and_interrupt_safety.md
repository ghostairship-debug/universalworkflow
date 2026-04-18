# M2 Phase 4 - Worker Lease Heartbeat And Interrupt Safety

**Phase status:** Completed
**Verification summary:** `pytest` passed with `115 passed`; `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true` and now covers worker-lease visibility through CLI, smoke, and API flows.

**Phase position:** This phase starts after `M2 Phase 3` establishes budget accounting. It introduces an explicit local worker-lease baseline so runtime ownership and heartbeat state stop being implicit.

**Entry condition:** `M2 Phase 3` is complete, claim / snapshot / budget projections are stable, and operator surfaces can already inspect and reconcile current run state.

---

## 1. Reassessment

Current implementation status:

- Claims protect runtime ownership at the resource level, but worker identity and heartbeat semantics are still implicit.
- Long-running ownership still lacks an explicit lease object for operator diagnostics and future interrupt safety.
- The next highest-value step is therefore a local `WorkerLease` baseline, not distributed scheduling or barrier orchestration.

Legacy references worth absorbing now:

- worker heartbeat and lease-expiry framing
- interrupt-safety diagnostics without importing a project kernel

This phase keeps the current run-centric architecture intact:

- no distributed lease manager
- no asynchronous worker pool
- no multi-run scheduler

---

## 2. In Scope

- add a persisted `WorkerLease` contract and repository baseline
- create and release worker leases on runtime execution paths
- capture heartbeat / expiry diagnostics for current local semantics
- expose worker-lease state through operator surfaces
- add tests for lease creation, release, expiry detection, and visibility

---

## 3. Out Of Scope

- distributed lock or lease coordination
- background heartbeat daemons
- true interrupt/resume checkpoints
- barrier scheduling
- multi-host worker routing

---

## 4. Key Constraints

- lease semantics must stay local and SQLite-backed
- ownership and heartbeat must be auditable
- leases must not pretend to guarantee distributed safety
- heartbeat behavior must match the current synchronous execution model
- operator diagnostics must remain explicit and bounded

---

## 5. Phase Task Breakdown Principle

This phase is split into three complex tasks:

1. Worker-lease contract, migration, repository, and query surfaces
2. Service heartbeat / release integration plus interrupt-safety diagnostics
3. CLI/API/docs/verification closeout

Each task must ship with tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- worker leases are persisted and queryable
- runtime execution creates and releases worker leases explicitly
- inspection can diagnose expired or wrongly-live worker leases
- CLI and API expose worker-lease visibility
- full `pytest` passes

Gate outcome:

- Passed: worker leases are persisted, auditable, and queryable
- Passed: runtime execution now creates and releases worker leases explicitly on shell and noop paths
- Passed: inspection diagnoses expired or wrongly-live worker leases and reconcile exposes bounded repair actions
- Passed: CLI and API expose worker-lease visibility through `run leases` and `GET /runs/{id}/leases`
- Passed: full `pytest` and offline validation succeeded

---

## 7. Risks And Rollback

- Risk: worker leases look like distributed safety guarantees
  Control: document them as local worker ownership only
- Risk: heartbeat semantics exceed what sync execution can really support
  Control: tie heartbeat to explicit lifecycle boundaries and diagnostics
- Risk: claim and worker-lease semantics diverge confusingly
  Control: keep responsibilities separate and visible in status surfaces

## 8. Outcome

- The repository now has an explicit local worker-lease baseline in addition to runtime claims, snapshots, and budget projections.
- Worker-lease history is visible through operator surfaces without claiming distributed heartbeat guarantees.
- The next recommended step is to reassess the remaining M2 / M3 boundary from the now-stable claim + snapshot + budget + worker-lease baseline, rather than broadening interrupt semantics blindly.
