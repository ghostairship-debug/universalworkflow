# M2 Phase 5 - Runtime Attempt Lifecycle And Interrupted Recovery

**Phase status:** Completed
**Phase position:** This phase starts after `M2 Phase 4` establishes the local worker-lease baseline. It introduces explicit runtime-attempt semantics so interrupted or superseded execution stops being inferred only from snapshots, claims, and worker leases.

**Entry condition:** `M2 Phase 4` is complete, worker-lease visibility is stable, and operator surfaces can already inspect claims, worker leases, snapshots, budgets, and reconcile outcomes.

---

## 1. Reassessment

Current implementation status:

- The repository now has local claim, snapshot, budget, and worker-lease baselines.
- `recompile` and repair flows can recover some bad states, but they still do not express explicit attempt lineage or interrupted-attempt semantics.
- `TD-008` remains only partially repaid because resumable execution exists, but complex interrupted / superseded attempt handling is still implicit.
- `TD-009` also remains open, but stronger barrier or concurrency semantics would be premature before attempt ownership is explicit.

Legacy references worth absorbing now:

- runtime attempt / stale-execution framing
- interrupted or superseded recovery heuristics
- bad-state regression cases for drifted live-vs-latest runtime state

This phase keeps the current run-centric architecture intact:

- no distributed scheduler
- no barrier orchestration engine
- no checkpoint merge or replay engine

---

## 2. In Scope

- add an explicit local runtime-attempt baseline for compile / recompile / resume flows
- mark current vs superseded attempt ownership clearly
- detect interrupted-attempt shapes through inspection and status surfaces
- add bounded repairs for safe attempt-lineage cleanup where current semantics allow it
- add tests for attempt creation, supersede, interruption diagnostics, and recovery projections

---

## 3. Out Of Scope

- distributed concurrency control
- real barrier coordination
- checkpoint merge or replay branching
- background recovery daemons
- richer review policy expansion

---

## 4. Key Constraints

- attempt semantics must stay local, explicit, and SQLite-backed
- supersede and interrupted markers must describe current repository behavior, not legacy project kernels
- repairs must remain bounded to current run-centric semantics
- this phase may improve interrupted-run recovery, but must not claim full multi-worker safety

---

## 5. Phase Task Breakdown Principle

This phase is split into three complex tasks:

1. Runtime-attempt contract, migration, repository, and query surfaces
2. Service integration for attempt creation, supersede / interruption diagnostics, and bounded repair
3. CLI/API/docs/verification closeout

Each task must ship with tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- runtime attempts are persisted and queryable
- compile / recompile / resume update attempt lineage explicitly
- inspection can diagnose interrupted or superseded attempt mismatches
- CLI and API expose attempt visibility
- full `pytest` passes

---

## 7. Risks And Rollback

- Risk: attempt lineage becomes a hidden second runtime model
  Control: keep attempts as explicit local metadata attached to the current run-centric flow
- Risk: interrupted recovery overclaims correctness
  Control: limit repairs to safe supersede / interruption cleanup and keep manual-only cases explicit
- Risk: this phase drifts into true concurrency work too early
  Control: defer barrier, distributed claim, and multi-run scheduling semantics to later phases

## 8. Expected Outcome

- The repository should gain an explicit local runtime-attempt baseline that clarifies interruption and supersede semantics.
- `TD-008` should move materially closer to closure without importing checkpoint-merge complexity.
- The remaining `TD-009` work should be easier to reassess from a cleaner attempt / ownership model.

---

## 9. Outcome

- Runtime attempts are now persisted as an explicit local lineage layer with `compile`, `recompile`, `resume`, and `repair` triggers.
- Compile / recompile / resume / terminal transitions now update attempt lineage directly, including supersede and bounded interruption repair semantics.
- CLI and API now expose attempt visibility through `run attempts`, `/runs/{run_id}/attempts`, and attempt-aware `status-detail` / `inspection` payloads.
- Verification passed with `pytest -q` (`126 passed`) and `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`).

## 10. Next Reassessment

- The next phase should reassess whether the remaining gap is still inside `M2` around stronger ownership / concurrency semantics, or whether the project is ready to shift to the next milestone boundary.
- The immediate debt focus is no longer missing attempt lineage; it is the remaining gap between local ownership diagnostics and true claim / lease / barrier concurrency guarantees.
