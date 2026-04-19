# M10 Phase 0 - Post-M9 Rebaseline And Scope Freeze

**Phase status:** Complete  
**Phase position:** This phase opened after the `M9` freeze review. It did not implement distributed ownership or real concurrency. Its job was to reassess the actual post-`M9` repository baseline, decide what `M10` is really allowed to mean inside a local-first SQLite control plane, and freeze the first approved `M10` slice before feature-bearing work starts.

**Phase outcome:** `M10 Phase 0` completed the post-`M9` rebaseline and froze the first approved `M10` slice without opening any future `M10` task-card pack.

Validated during phase execution with:

- `python -m pytest tests/test_execution_loop.py tests/test_cli.py tests/test_api.py -q -k "claim or lease or reconcile or repair or attempt"` -> `44 passed, 141 deselected`
- `python -m pytest tests/test_runtime_boundary.py -q` -> `4 passed`
- `python -m infra.scripts.check_doc_links` -> `passed=true`

Note:

- pytest again emitted the same Windows temp-directory cleanup `PermissionError` after successful completion; the green test results were not invalidated.

**Entry condition:** `M9` is complete, `TD-001` and `TD-009` are the only open cross-milestone debts, and the repository must not jump directly from a successful `M9` closeout into open-ended ownership/concurrency implementation.

---

## 1. Reassessment

Current confirmed post-`M9` baseline:

- the repository ships a local-first CLI/API runtime with SQLite as the only persistence layer
- `feature_delivery` remains on the native deterministic lane
- borrowed-agent, MCP source, external trace export, durable pilot, and skill export remain opt-in `M8` feature-flagged paths
- the repository now has:
  - five executable review policies
  - replay-packet projection
  - first-class run metrics
  - durable lineage and reconciliation diagnostics
  - governance metrics, alerts, and release-readiness integration
- the latest validated closeout baseline recorded in `docs/reviews/m9-freeze-review.md` is:
  - `python -m pytest -q` -> `234 passed`
  - `python -m infra.scripts.offline_validation --skip-offline-probe` -> `overall_passed=true`
  - `python -m infra.scripts.check_doc_links` -> `passed=true`

Open debt entering `M10`:

- `TD-001`: claim and worker-lease semantics remain local-only and do not provide true distributed resource ownership
- `TD-009`: execution semantics remain serial-first and do not implement real claim/lease/barrier concurrency

Current implementation reality that matters for `M10`:

- persisted `Claim`, `WorkerLease`, `RunSnapshot`, and `RuntimeAttempt` baselines already exist from earlier phases
- inspection, summary, audit, replay, and reconcile surfaces already expose ownership and attempt state in a local-first shape
- current ownership and repair logic is designed to keep one local control plane coherent, not to act as a finished distributed scheduler
- the repository still protects contracts/core-domain boundaries from importing `langgraph` directly, which reinforces that borrowed substrate must remain mapped back into repository-owned semantics

Questions that `M10 Phase 0` must answer before coding starts:

- what does "distributed ownership" mean inside this repository's current local-first and SQLite-only boundary
- whether the first `M10` slice should harden ownership topology first, or attempt barrier/parallel semantics immediately
- how much of `TD-001` and `TD-009` can be repaid inside `M10` without weakening the local-first control-plane model
- which tempting expansions must remain explicit non-goals for early `M10`

Default planning hypothesis for this phase:

- first evaluate ownership topology and cross-attempt coordination semantics before introducing real barrier/parallel execution
- treat barrier/concurrency work as dependent on a clearer ownership contract, not as the opening move
- keep true multi-node worker-pool or external scheduler ambition explicitly outside the first slice unless the rebaseline proves it is justified and still compatible with the current control-plane model

`M10 Phase 0` verified this baseline and froze the scope below.

---

## 1A. Executed Baseline Inventory

Shipped ownership, attempt, and repair surfaces confirmed during this phase:

- `packages/contracts/runtime.py` already provides persisted contract models for `RuntimeClaim`, `WorkerLease`, `RuntimeAttempt`, `RunSnapshot`, and `RuntimeStateRef`, with lifecycle validation for active, released, expired, superseded, interrupted, and terminal states.
- `packages/core_domain/repositories.py` already persists and queries claim, lease, attempt, state-ref, and snapshot history; the repository baseline is no longer a placeholder-only design.
- `packages/core_domain/services.py` already acquires and releases runtime claims, acquires and releases worker leases, creates runtime attempts, supersedes or closes attempts, and emits lifecycle events for those actions.
- `packages/core_domain/service_projection.py` already projects ownership and attempt state into `status-detail`, `summary`, `inspect`, and dashboard-friendly views, including active-count, latest-resource, expired-active-lease, and run-metrics summaries.
- `packages/core_domain/services.py` and the current CLI/API surfaces already expose reconcile and repair actions that can:
  - align terminal runtime state
  - release or expire stale claims
  - release or expire stale worker leases
  - interrupt the current attempt
  - create a repair attempt
- `tests/test_execution_loop.py`, `tests/test_cli.py`, and `tests/test_api.py` already cover the local claim lifecycle, worker-lease lifecycle, claim conflict handling, stale-resource reconcile actions, repair-attempt creation, and inspection/reporting projections.

Current local-only boundary that still blocks full `TD-001` / `TD-009` repayment:

- `RuntimeClaim.owner` still defaults to `local_orchestrator`, which reflects a local control-plane owner label rather than a true distributed lock or lease-holder identity model.
- `WorkerLease.worker_name` still defaults to `local_worker`, and the current lease model records heartbeat and expiry timestamps but does not implement cross-process renewal arbitration or an external worker-pool contract.
- claim conflict handling currently guards a local runtime task boundary; it does not provide cross-node consensus, remote reservation, or a generalized distributed scheduler protocol.
- runtime-attempt lineage currently models supersede, interrupt, close, and repair flows for one run lineage at a time; it does not model branch/join trees, barrier sets, or multiple concurrent current attempts.
- reconcile/repair logic currently restores coherence after inconsistent local state is observed; it is not a scheduler-level coordination layer for parallel workers.
- `tests/test_runtime_boundary.py` still enforces that `packages/contracts` and `packages/core_domain` do not import `langgraph` directly, which preserves the repository-owned semantic boundary.

---

## 2. In Scope

- inventory the actual post-`M9` ownership/concurrency baseline from current repository files, services, projections, and tests
- compare open-debt wording (`TD-001`, `TD-009`) with the current local-first implementation shape
- cluster the remaining `M10` debt into candidate implementation slices and rank them by dependency order, blast radius, and validation readiness
- freeze explicit non-goals for early `M10`
- decide the first approved feature-bearing `M10` slice
- create the current-phase doc pack for `M10 Phase 0` only

---

## 3. Out Of Scope

- implementing `TD-001` or `TD-009` in this phase
- generating future-phase `M10` task-card packs before they become the active phase
- replacing SQLite with a different persistence substrate
- turning borrowed-agent, MCP source, external trace export, or durable pilot into default paths
- claiming a full hosted dashboard, remote scheduler, or generic multi-agent role framework as shipped scope

---

## 4. Dependencies

Primary current-state inputs:

- `README.md`
- `docs/current_development_workflow.md`
- `docs/reviews/m9-freeze-review.md`
- `docs/tech-debt-registry.md`
- `docs/governance/tech_debt_registry.json`
- `pyproject.toml`

Primary historical implementation anchors:

- `docs/task_cards/m2_phase_1_task_cards.md`
- `docs/task_cards/m2_phase_4_task_cards.md`
- `docs/task_cards/m2_phase_5_task_cards.md`
- `docs/adrs/ADR-005.md`
- `docs/contracts/future-objects-outline.md`
- `docs/adrs/ADR-M8-009.md`

Primary code anchors:

- `packages/contracts/runtime.py`
- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/governance.py`
- `packages/core_domain/repositories.py`
- `tests/test_execution_loop.py`
- `tests/test_governance.py`
- `tests/test_api.py`
- `tests/test_cli.py`

Selective legacy references may be consulted for invariants and anti-patterns, but they must not override the current repository baseline.

---

## 5. Candidate M10 Entry Themes

### Theme A - Ownership Topology And Coordination Semantics

Primary debt:

- `TD-001`

Focus:

- define what a stronger ownership model means for claims and worker leases in the current control plane
- separate "better ownership semantics" from "full external worker pool"
- freeze the ownership invariants that later concurrency work must obey

Why it is the leading candidate:

- current concurrency debt is unsafe to open without clearer ownership rules
- the repository already exposes claim, lease, and attempt state locally, so the next step is to harden those semantics before widening scheduling behavior

### Theme B - Barrier And Parallel Execution Semantics

Primary debt:

- `TD-009`

Focus:

- define branch, barrier, join, and concurrent-attempt semantics
- decide how parallel execution interacts with claims, leases, attempts, snapshots, and reconcile

Why it should not be the opening move by default:

- current ownership semantics are still local-only
- parallel execution without a stronger ownership contract would increase blast radius quickly

### Theme C - True External Worker Pools Or Multi-Node Scheduling

Related debt lineage:

- `TD-001`
- `TD-009`

Focus:

- external workers
- cross-process or cross-node ownership
- scheduler-level scaling beyond the current local-first baseline

Why it is not auto-approved in Phase 0:

- the repository is still explicitly local-first with SQLite as the canonical persistence layer
- this theme is the easiest place to over-broaden `M10`
- it may require a later milestone or a narrower pilot boundary rather than immediate full-scope approval

Phase 0 ranking result for `M10`:

1. Theme A - Ownership Topology And Coordination Semantics
2. Theme B - Barrier And Parallel Execution Semantics
3. Theme C - Explicitly not approved as the first slice; keep as a later decision only if Phase 0 justifies it

Frozen first-slice decision:

- the first approved `M10` slice should focus on ownership topology and cross-attempt coordination on the current local-first control plane
- barrier/parallel execution is a follow-on slice, not the opening slice
- true external worker-pool or multi-node scheduler breadth is not approved by this phase pack

---

## 6. Target Outputs

- `m10_phase_docs/phase_0_post_m9_rebaseline_and_scope_freeze.md`
- `docs/task_cards/m10_phase_0_task_cards.md`
- current-phase detailed task cards under `docs/task_cards/m10_phase_0/`
- `docs/reviews/m10-phase-0-post-m9-rebaseline-and-scope-freeze-review.md`
- an explicit first-slice decision for `M10`
- explicit non-goals for early `M10`

Per current protocol, this phase does **not** pre-generate future `M10` task-card packs.
Future phases may be named here as planning placeholders, but their task cards should be created only when they become the active phase.

---

## 7. Phase Task Breakdown Principle

This phase should split into four ordered tasks:

1. inventory the post-`M9` ownership/concurrency baseline from current files and tests
2. cluster the two remaining open debts into candidate `M10` slices and rank them
3. freeze the first approved `M10` slice plus explicit non-goals
4. normalize closeout expectations and verification hooks for later `M10` execution

This phase is a complex phase.
Every task therefore requires its own standalone detailed card under `docs/task_cards/m10_phase_0/`.

---

## 8. Phase Gate

`M10 Phase 0` passes only if all of the following become true:

- the post-`M9` baseline is written from current repository evidence rather than ambition
- `TD-001` and `TD-009` are split into clear candidate slices with dependency reasoning
- one first feature-bearing `M10` slice is explicitly approved
- early `M10` non-goals are explicit enough to prevent an uncontrolled jump into hosted or multi-node scheduler breadth
- only the current phase's task-card pack is generated

Gate result:

- passed
- the first approved feature-bearing slice is frozen as ownership topology and claim-domain hardening on the current local-first control plane
- no future `M10` task-card pack was generated during this phase

---

## 9. Risks

- over-broadening `M10` into a full distributed-systems rewrite
- conflating stronger ownership semantics with immediate multi-node scheduling support
- opening parallel execution before the ownership boundary is frozen
- weakening the local-first control-plane model while trying to repay `TD-001` / `TD-009`

---

## 10. Next Reassessment

If `M10 Phase 0` passes, the next approved phase should be:

- `M10 Phase 1 - Ownership Topology And Claim Domain Freeze`

That next phase name is approved only as a planning placeholder in this document.
Its task-card pack should not be generated until `M10 Phase 1` becomes the active phase.
