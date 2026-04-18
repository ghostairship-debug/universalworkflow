# M2 Phase 2 - Run Snapshot Baseline And Recovery Projections

**Phase status:** Completed
**Verification summary:** `pytest` passed with `91 passed`; `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true` and now covers snapshot-aware CLI, smoke, and API flows.

**Phase position:** This phase starts after `M2 Phase 1` establishes a local claim / lease guard. It adds replay-friendly snapshot checkpoints before any deeper worker-lease or stronger concurrency work is attempted.

**Entry condition:** `M2 Phase 1` is complete, claim lifecycle semantics are stable, and operator surfaces can already diagnose and repair the current bad-state catalog.

---

## 1. Reassessment

Current implementation status:

- The repository now has claim-aware execution, inspection, and repair.
- Recovery still depends on stitching together current tables and timeline events manually.
- `TD-008` remains only partially repaid because the runtime can repair drift, but still lacks explicit checkpoint snapshots.
- The next highest-value step is therefore a lightweight `RunSnapshot` baseline, not deeper concurrency semantics yet.

Legacy references worth absorbing now:

- recovery-oriented runtime checkpoint framing
- replay / recovery projection patterns rather than project-kernel backports

This phase keeps the current run-centric architecture intact:

- no project-centric kernel
- no full replay engine
- no long-lived worker pool

---

## 2. In Scope

- add a persisted `RunSnapshot` contract and repository baseline
- capture snapshots at key lifecycle and repair boundaries
- expose latest snapshot and snapshot history through operator surfaces
- use snapshots to improve recovery projections in `status-detail` and `inspection`
- add tests for snapshot capture, listing, and projection behavior

---

## 3. Out Of Scope

- full event replay
- checkpoint merge or branch replay
- distributed worker lease heartbeat loops
- budget-ledger accounting
- legacy project-kernel adoption

---

## 4. Key Constraints

- snapshots must be additive and audit-friendly
- snapshots must summarize current repository semantics rather than copy the entire database
- capture points must stay explicit and bounded
- snapshot payloads must remain lightweight and JSON-safe
- this phase may improve recovery visibility, but must not claim to implement full replay

---

## 5. Phase Task Breakdown Principle

This phase is split into three complex tasks:

1. Snapshot contract, migration, repository, and query surfaces
2. Service capture hooks plus recovery projection integration
3. CLI/API/docs/verification closeout

Each task must ship with tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- run snapshots are persisted and queryable
- compile, resume/review, cancel, and repair paths capture snapshots explicitly
- status / inspection surfaces expose the latest snapshot in a stable operator-facing way
- snapshot payloads remain lightweight and current-architecture aligned
- CLI and API expose snapshot visibility
- full `pytest` passes

Gate outcome:

- Passed: run snapshots are now persisted, queryable, and exposed through status / inspection plus dedicated snapshot query surfaces
- Passed: compile, review-handoff, terminal, cancel, and repair paths all capture snapshots explicitly
- Passed: snapshot payloads stay lightweight and projection-oriented instead of trying to mirror the full database
- Passed: CLI and API both expose snapshot visibility and snapshot-aware operator diagnostics
- Passed: full `pytest` and offline validation succeeded

---

## 7. Risks And Rollback

- Risk: snapshots drift into a hidden replay engine
  Control: keep them projection-oriented and explicitly non-authoritative
- Risk: snapshot payloads become too heavy
  Control: store references and summary fields, not full raw execution artifacts
- Risk: capture hooks miss important transitions
  Control: test compile, human-review, auto-terminal, cancel, and repair flows

## 8. Outcome

- The repository now has a replay-friendly `RunSnapshot` baseline instead of relying only on current tables plus timeline stitching.
- `TD-008` is further repaid because recovery reasoning now has explicit checkpoints, though full replay / checkpoint merge remains out of scope.
- The next recommended phase is `M2 Phase 3 - Budget Ledger Baseline And Enforcement Projections`, so preset budget policy stops being only a schema shape and becomes operator-visible runtime accounting.
