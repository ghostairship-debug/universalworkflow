# M10 Phase 1 - Ownership Topology And Claim Domain Freeze

**Phase status:** Complete  
**Phase position:** This phase began after `M10 Phase 0` froze ownership topology as the first approved feature-bearing `M10` slice. It did not implement barrier/join or multi-node breadth. Its job was to turn claim and worker-lease ownership into explicit repository-owned topology semantics that later concurrency work can rely on.

**Phase outcome:** `M10 Phase 1` completed the ownership-topology freeze for the local-first control plane and made claim / worker-lease lineage explicit across contracts, persistence, lifecycle, and projection surfaces.

Validated during phase execution with:

- `python -m pytest tests/test_contracts.py tests/test_repositories.py -q` -> `34 passed`
- `python -m pytest tests/test_execution_loop.py tests/test_cli.py tests/test_api.py -q -k "claim or lease or ownership or projection"` -> `33 passed, 152 deselected`
- `python -m pytest tests/test_runtime_boundary.py -q` -> `4 passed`
- `python -m infra.scripts.check_doc_links` -> `passed=true`

Note:

- pytest again emitted the same Windows temp-directory cleanup `PermissionError` after successful completion; the green test results were not invalidated.

**Entry condition:** `M10 Phase 0` is complete, `TD-001` and `TD-009` remain open, and the first approved `M10` slice is ownership topology and claim-domain hardening on the existing local-first SQLite control plane.

---

## 1. Reassessment

Current shipped baseline entering this phase:

- persisted `RuntimeClaim`, `WorkerLease`, and `RuntimeAttempt` objects already exist
- claim conflict detection already prevents duplicate active claims for one runtime task
- worker leases already record adapter, heartbeat, expiry, and release/expiry outcomes
- reconcile and repair already understand stale claims, stale leases, interrupted attempts, and terminal-state mismatches
- status, inspection, summary, replay, and audit projections already expose ownership and attempt history

Current gap that kept `TD-001` open entering this phase:

- claim ownership is still modeled as a single legacy `owner` label
- worker ownership is still modeled as a single legacy `worker_name` label
- claim and lease records do not freeze an explicit ownership topology contract for:
  - owner kind
  - owner identity
  - claim domain kind
  - claim domain key
  - attempt linkage
  - claim-to-lease linkage
- later concurrency work therefore has no stable claim-domain contract to build on

Phase interpretation that governed execution:

- `M10 Phase 1` was not the phase that added barrier or branch/join execution
- it was the phase that froze the ownership grammar those later semantics must obey
- this phase repaid the ownership-topology portion of `TD-001` without broadening into hosted or multi-node scheduling

---

## 2. In Scope

- add explicit ownership-topology fields to `RuntimeClaim` and `WorkerLease`
- persist those fields in SQLite and repository mapping code
- link claims and worker leases to the current runtime attempt where applicable
- expose ownership-topology projections through service, CLI, API, and replay/status surfaces
- update focused tests and current docs for the new ownership contract

Completed result:

- `RuntimeClaim` now records explicit owner kind / identity, claim domain kind / key, and attempt linkage.
- `WorkerLease` now records explicit worker kind / identity, claim linkage, attempt linkage, and claim-domain alignment.
- lifecycle events, status-detail, summary, inspect, replay, CLI, and API surfaces now expose `ownership_topology`.
- the repository still remained local-first and did not claim distributed or batch execution scope in this phase.

---

## 3. Out Of Scope

- barrier, branch, join, or parallel-attempt execution semantics
- multi-node scheduling
- hosted scheduler or external queue integration
- generic multi-agent role modeling
- retiring `TD-009` in this phase

---

## 4. Dependencies

Primary code anchors:

- `packages/contracts/runtime.py`
- `packages/contracts/events.py`
- `packages/core_domain/repositories.py`
- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/errors.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`

Primary tests:

- `tests/test_contracts.py`
- `tests/test_repositories.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`

Primary governance/docs inputs:

- `docs/tech-debt-registry.md`
- `docs/reviews/m10-phase-0-post-m9-rebaseline-and-scope-freeze-review.md`
- `docs/adrs/ADR-005.md`

---

## 5. Target Outputs

- `m10_phase_docs/phase_1_ownership_topology_and_claim_domain_freeze.md`
- `docs/task_cards/m10_phase_1_task_cards.md`
- current-phase detailed task cards under `docs/task_cards/m10_phase_1/`
- runtime ownership-topology code changes plus focused validation

Per current protocol, this phase opened only the `M10 Phase 1` pack while active.
`M10 Phase 2` was opened only after this phase closed.

---

## 6. Phase Breakdown Principle

This phase split into three ordered tasks:

1. freeze the ownership contract and persistence shape
2. wire lifecycle, projection, CLI, and API surfaces to the new topology
3. update docs, tests, and closeout evidence

This was a complex phase.
Every task therefore had its own standalone detailed card under `docs/task_cards/m10_phase_1/`.

---

## 7. Phase Gate

`M10 Phase 1` passed because all of the following became true:

- claims and worker leases record explicit owner/worker topology rather than legacy labels alone
- claim and worker-lease records are attempt-aware where the current runtime flow can prove linkage
- status, inspection, replay, CLI, and API surfaces expose the new topology coherently
- focused ownership tests passed
- the phase closed before `M10 Phase 2` was opened

---

## 8. Risks

- adding too many speculative topology fields that current services cannot populate coherently
- breaking legacy claim/lease payload assumptions in CLI/API/tests
- pretending this phase delivers real concurrency when it only freezes ownership semantics

Observed outcome:

- those risks stayed contained; the phase closed as an ownership-topology freeze rather than a hidden concurrency expansion.

---

## 9. Next Reassessment

The next approved phase after this closeout was:

- `M10 Phase 2 - Local Barrier And Parallel Batch Execution`

That next phase was later opened as the next active pack and is now part of the historical `M10` record.
