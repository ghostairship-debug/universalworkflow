# M2 Phase 1 - Local Claim Lifecycle And Lease Guard

**Phase status:** Completed
**Verification summary:** `pytest` passed with `81 passed`; `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true` and now covers claim-aware CLI, smoke, and API flows.

**Phase position:** This phase starts after `M2 Phase 0` establishes controlled reconcile / repair. It introduces a local claim / lease boundary so that runtime actions are no longer only status-guarded, but also resource-guarded.

**Entry condition:** `M2 Phase 0` is complete, reconcile / repair is stable, and the repository still uses serial local execution semantics.

---

## 1. Reassessment

Current implementation status:

- `resume`, `cancel`, and `repair` already have run-status guards.
- The repository still has no real claim / lease persistence.
- `TD-001` and `TD-009` remain open because runtime work is not yet protected by an explicit resource claim boundary.
- The next highest-value step is therefore a local, auditable claim lifecycle, not full parallel scheduling.

Legacy references worth absorbing now:

- runtime failure cases around stale execution and recovery
- cancel / resume / retry edge handling

This phase keeps the existing run-centric architecture intact:

- no distributed scheduler
- no barrier / multi-run orchestration engine
- no legacy project kernel

---

## 2. In Scope

- add a persisted local runtime claim / lease model
- acquire a claim before runtime execution
- release or expire claims explicitly
- expose claim state through status / inspection / operator surfaces
- detect and repair stale or wrongly-live claims
- add tests for claim acquisition, release, conflict, and stale repair

---

## 3. Out Of Scope

- distributed locking
- multi-worker scheduling
- barrier orchestration
- automatic retry loops
- richer review policy expansion

---

## 4. Key Constraints

- claim behavior must stay local-only and SQLite-backed
- acquisition and release must be auditable
- terminal or waiting-for-review runs must not keep live claims
- stale claims must be repairable without inventing legacy semantics
- this phase may prepare concurrency, but must not claim to implement full parallel safety

---

## 5. Phase Task Breakdown Principle

This phase is split into three complex tasks:

1. Claim contract, migration, repository, and query surfaces
2. Service integration for acquire / release / conflict / stale-repair semantics
3. CLI/API/docs/verification closeout

Each task must ship with tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- runtime claims are persisted and queryable
- `resume` acquires a claim and terminal / review-handoff paths release it
- duplicate active claim acquisition fails with a stable error
- inspection can diagnose stale or wrongly-live claims
- reconcile can safely release or expire stale claims
- CLI and API expose claim visibility
- full `pytest` passes

Gate outcome:

- Passed: runtime claims are now persisted, queryable, and exposed through status/detail plus dedicated claim query surfaces
- Passed: `resume` acquires a claim before execution, and auto-terminal, human-review handoff, cancel, and repair paths all release or expire claims explicitly
- Passed: duplicate active-claim acquisition fails with the stable `runtime_claim_conflict` error
- Passed: inspection and reconcile now diagnose and repair stale or wrongly-live claims without importing legacy kernel structure
- Passed: CLI and API both expose claim visibility and claim-aware reconcile behavior
- Passed: full `pytest` and offline validation succeeded

---

## 7. Risks And Rollback

- Risk: claim semantics look stronger than they really are
  Control: document them as local claim / lease guards only
- Risk: claims are acquired but not released on every path
  Control: test auto, human-review, cancel, and repair flows
- Risk: claim history becomes opaque
  Control: persist claim rows and audit them through events and query surfaces

## 8. Outcome

- The repository now has a local, auditable claim lifecycle instead of a claim placeholder.
- `TD-001` is materially repaid for the local runtime path; `TD-009` is partially repaid because the repository still keeps serial execution semantics and does not yet implement barrier or distributed coordination.
- The next recommended phase is `M2 Phase 2 - Run Snapshot Baseline And Recovery Projections`, so that replay-friendly checkpoints exist before deeper worker-lease or stronger concurrency work is attempted.
