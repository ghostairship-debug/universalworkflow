# M10 Phase 2 - Local Barrier And Parallel Batch Execution

**Phase status:** Complete  
**Phase position:** This phase began after `M10 Phase 1` froze explicit ownership topology. It introduced the smallest coherent concurrency slice that fit the current local-first SQLite control plane: a local batch barrier plus parallel resume for multiple prepared runs.

**Phase outcome:** `M10 Phase 2` completed the local batch-barrier and parallel batch-execution slice for the supported local control plane without broadening into multi-node scheduling or a DAG engine rewrite.

Validated during phase execution with:

- `python -m pytest tests/test_execution_loop.py tests/test_cli.py tests/test_api.py -q -k "batch or parallel or barrier or claim or lease or ownership"` -> `29 passed, 159 deselected`

Note:

- pytest again emitted the same Windows temp-directory cleanup `PermissionError` after successful completion; the green test results were not invalidated.

**Entry condition:** `M10 Phase 1` is complete, ownership topology is explicit, and the remaining `M10` execution gap is still that concurrency stays serial-first for prepared runs.

---

## 1. Reassessment

Current shipped baseline entering this phase:

- explicit claim / worker-lease ownership topology already exists
- claim / lease / attempt lineage is already persisted and projected
- reconcile and repair already understand stale or interrupted local ownership state
- CLI and API already expose prepared-run resume as the main lifecycle entry point

Current gap that still kept `TD-009` open:

- prepared runs still resumed one-at-a-time through a serial-first flow
- no local batch barrier existed to synchronize multiple prepared runs
- no parallel batch surface existed in CLI or API
- projections did not show any batch barrier context

Phase interpretation:

- `M10 Phase 2` is not a distributed scheduler phase
- it is not a branch/join DAG-runtime phase
- it is the phase that adds repository-owned local batch barrier semantics and parallel resume for the current local control plane

---

## 2. In Scope

- add local batch-barrier event types and payloads
- add a local `resume_runs_parallel(...)` lifecycle surface for prepared runs
- project `parallel_batch` state into status, inspect, summary, and replay surfaces
- expose batch resume through CLI and API
- update focused runtime, CLI, and API tests
- close `TD-009` for the supported local-first control plane

---

## 3. Out Of Scope

- external worker pools
- multi-node scheduling
- remote lease renewal arbitration
- generic DAG branch/join planning
- hosted operator dashboard work

---

## 4. Dependencies

Primary code anchors:

- `packages/contracts/events.py`
- `packages/core_domain/errors.py`
- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_projection.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`

Primary tests:

- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`

Primary governance/docs inputs:

- `docs/tech-debt-registry.md`
- `docs/governance/tech_debt_registry.json`
- `docs/reviews/m10-phase-1-ownership-topology-and-claim-domain-freeze-review.md`

---

## 5. Target Outputs

- `m10_phase_docs/phase_2_local_barrier_and_parallel_batch_execution.md`
- `docs/task_cards/m10_phase_2_task_cards.md`
- current-phase detailed task cards under `docs/task_cards/m10_phase_2/`
- local batch-barrier runtime code and focused validation
- `docs/reviews/m10-phase-2-local-barrier-and-parallel-batch-execution-review.md`

Per current protocol, this phase opened only the `M10 Phase 2` pack while active.
No `M11` task-card pack should be generated until the `M10` freeze closeout explicitly approves it.

---

## 6. Phase Breakdown Principle

This phase split into three ordered tasks:

1. add batch-barrier runtime semantics and event contracts
2. expose batch state through projection, CLI, API, and focused tests
3. close the phase and hand the repository into `M10` freeze review

This was a complex phase.
Every task therefore had its own standalone detailed card under `docs/task_cards/m10_phase_2/`.

---

## 7. Phase Gate

`M10 Phase 2` passed because all of the following became true:

- multiple prepared runs can cross one local batch barrier before execution starts
- batch resume results and errors are surfaced explicitly
- `parallel_batch` projections are visible in status, inspect, summary, and replay surfaces
- ownership topology remains coherent under the local batch path
- focused batch / barrier tests pass

---

## 8. Risks

- holding SQLite write locks across the barrier and breaking batch execution
- claiming branch/join or multi-node semantics that the repository still does not ship
- exposing a batch surface that is not visible enough for replay or operator diagnostics

Observed outcome:

- the initial barrier implementation did expose a write-lock problem; the phase resolved it by shortening transactions around the barrier boundaries instead of widening scope.

---

## 9. Next Reassessment

With this phase complete, the next approved closeout step is:

- `M10` freeze review and milestone closeout

The next milestone entry after the `M10` freeze is:

- `M11 Phase 0 - Post-M10 Rebaseline And Scope Freeze`
