# M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze

**Phase status:** Completed  
**Phase position:** This phase opens after the `M8` freeze review and the follow-up dependency-baseline alignment. It does not implement new `M9` breadth. It verifies the actual post-`M8` repository baseline, clusters the carry-over debt, and freezes the first approved `M9` slice before feature work starts.

**Entry condition:** `M8` is complete, the next approved work is still `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`, and the repository must make a fresh scope decision from current files rather than from pre-implementation `M8` assumptions.

---

## 1. Reassessment

Current confirmed post-`M8` baseline:

- the repository ships a local-first CLI/API runtime with SQLite as the only persistence layer
- `feature_delivery` still has a preserved native deterministic lane
- borrowed agent, MCP capability projection, external trace export, durable pilot, and skill export remain opt-in paths behind `UAWO_ENABLE_*` flags
- the direct OpenAI runtime gateway remains optional, with the base package now aligned to `openai>=2.26.0,<3.0.0`
- `langchain`, `langchain-openai`, and `langgraph` stay in the optional `m8` dependency group rather than becoming unconditional runtime requirements
- service logic has already been decomposed into bounded modules such as `service_lifecycle`, `service_projection`, and `service_memory_simulation`; `M9` should build on that split rather than reopening a broad service-refactor cycle
- the last validated closeout baseline recorded in `docs/reviews/m8-freeze-review.md` remains:
  - `pytest -q` -> `225 passed`
  - `python -m infra.scripts.offline_validation --skip-offline-probe` -> `overall_passed=true`
  - `python -m infra.scripts.check_doc_links` -> `passed=true`
  - `python -m pip install -e . --no-deps` -> succeeded

Carry-over debt explicitly still open for `M9`:

- `TD-001`: local-only claim and worker-lease semantics
- `TD-006`: `optional` review policy remains reference-only
- `TD-007`: replay-grade observability and first-class metrics are incomplete
- `TD-008`: durable interrupt / resume / checkpoint merge semantics are incomplete
- `TD-009`: execution remains serial-first rather than claim/lease/barrier concurrent
- `TD-010`: governance visibility is still document-centric rather than quantitatively automated

What must be answered before `M9` code starts:

- which debt cluster is the smallest justified first `M9` slice
- which `M8` pilots remain opt-in experiments versus candidates for later promotion
- which large expansions must stay explicitly deferred even if they are tempting after `M8`
- whether the best early-`M9` focus is post-`M8` observability/recovery/governance hardening, a narrower policy-breadth slice, or something else grounded in the current repository

Default planning hypothesis for this phase:

- first evaluate `TD-007`, `TD-008`, and `TD-010` as the leading `M9` entry cluster because they sit directly on top of `M8` pilot surfaces and improve diagnosability before any promotion or concurrency expansion
- keep `TD-006` visible as a bounded follow-on candidate, not as the automatic first step
- keep `TD-001` and `TD-009` visible but treat them as the highest-blast-radius expansion candidates, not the default opening move

This hypothesis is only a starting point. `M9 Phase 0` exists to verify or replace it with a repository-grounded freeze decision.

Phase-0 decision:

- keep Theme A as the first approved `M9` slice
- keep `TD-006` as the second approved `M9` slice because it is now implementable once the repository gains a clean advisory-only terminal shape
- explicitly defer Theme C (`TD-001` + `TD-009`) to the next milestone because it changes execution semantics and would over-broaden `M9`

---

## 2. In Scope

- inventory the actual post-`M8` shipped surfaces, flags, optional dependency tiers, and validation anchors from the current repository
- compare `M8` freeze-review claims with current files such as `README.md`, `pyproject.toml`, `packages/`, `apps/`, `infra/`, and `tests/`
- cluster the open debt items into candidate `M9` entry themes and rank them by dependency order, architectural blast radius, and validation readiness
- freeze explicit non-goals so early `M9` does not reopen distributed coordination, default external-lane promotion, or unrelated architecture churn
- decide the first approved feature-bearing `M9` slice, or explicitly record why no slice is yet approved
- produce task-card-ready boundaries for the next feature-bearing phase
- freeze the complete `M9` phase sequence around diagnostics/recovery/governance hardening plus optional review-policy completion

---

## 3. Out Of Scope

- implementing `TD-001`, `TD-006`, `TD-007`, `TD-008`, `TD-009`, or `TD-010` in this phase
- promoting borrowed agent, MCP, external trace export, durable pilot, or skill export to default paths
- distributed worker pools, multi-node scheduling, or true cross-process resource ownership
- real claim / lease / barrier concurrency semantics
- broad runtime-policy expansion beyond the current four executable review policies
- replacing local operator surfaces with an external dashboard stack
- large refactors that are not required to freeze the next approved `M9` slice

---

## 4. Dependencies

Primary current-state inputs:

- `README.md`
- `docs/current_development_workflow.md`
- `docs/reviews/m8-freeze-review.md`
- `docs/tech-debt-registry.md`
- `docs/governance/README.md`
- `pyproject.toml`

Primary implementation anchors:

- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/service_memory_simulation.py`
- `packages/core_domain/capability_plane.py`
- `packages/core_domain/observability.py`
- `packages/core_domain/m8_flags.py`
- `packages/core_domain/skills.py`
- `packages/runtime_langgraph/gateway.py`
- `packages/runtime_langgraph/durable_pilot.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`
- `tests/test_governance.py`
- `tests/test_runtime_boundary.py`

Selective historical references may be consulted for invariants or debt lineage, but they must not override the current repository baseline.

---

## 5. Candidate M9 Entry Themes

### Theme A - Observability, Durable Recovery, And Governance Hardening

Primary debts:

- `TD-007`
- `TD-008`
- `TD-010`

Why it is a strong entry candidate:

- `M8` added new pilot-grade observability, runtime-ref, and governance surfaces, but those surfaces remain intentionally incomplete
- better linkage, metrics, checkpoint semantics, and reporting would make later promotion decisions and later concurrency work safer
- it strengthens current post-`M8` truth without reopening the architecture into distributed execution immediately

### Theme B - Review Policy Breadth Completion

Primary debt:

- `TD-006`

Why it stays visible but not automatically first:

- it is bounded and operator-visible
- it does not block the current shipped baseline
- it is smaller than Theme C, but less directly tied to the new post-`M8` pilot surfaces than Theme A

### Theme C - Distributed Ownership And Concurrent Execution

Primary debts:

- `TD-001`
- `TD-009`

Why it is the highest-risk opening move:

- it changes execution semantics rather than only enriching projections, governance, or recovery detail
- it would expand the blast radius across claims, leases, runtime lifecycle, and validation strategy
- it should not begin before the repository has stronger observability and recovery evidence on the current local-first baseline

`M9 Phase 0` must freeze an explicit ordering across these themes instead of allowing them to blur into one large milestone.

Frozen ordering for `M9`:

1. Theme A: `TD-007` + `TD-008` + `TD-010`
2. Theme B: `TD-006`
3. Theme C: defer beyond `M9`

Frozen `M9` milestone scope:

- in scope for `M9`: replay-grade linkage and first-class run metrics, durable checkpoint lineage and reconciliation hardening, quantitative governance automation/alerts, and executable `optional` review policy support
- out of scope for `M9`: distributed worker ownership and real concurrent claim/lease/barrier scheduling

---

## 6. Target Outputs

- `m9_phase_docs/phase_0_post_m8_rebaseline_and_scope_freeze.md`
- `docs/task_cards/m9_phase_0_task_cards.md`
- `m9_phase_docs/phase_1_replay_linkage_and_metrics_baseline.md`
- `m9_phase_docs/phase_2_durable_recovery_lineage_and_reconciliation.md`
- `m9_phase_docs/phase_3_governance_metrics_and_alerting.md`
- `m9_phase_docs/phase_4_optional_review_policy_completion.md`
- `m9_phase_docs/phase_5_freeze_review_and_scope_closure.md`
- `docs/task_cards/m9_phase_1_task_cards.md`
- `docs/task_cards/m9_phase_2_task_cards.md`
- `docs/task_cards/m9_phase_3_task_cards.md`
- `docs/task_cards/m9_phase_4_task_cards.md`
- `docs/task_cards/m9_phase_5_task_cards.md`
- an explicit first-slice decision recorded in this phase doc
- explicit deferred items and preserved non-goals for the rest of `M9`
- a later closeout review for the phase once execution is complete

---

## 7. Phase Task Breakdown Principle

This phase should split into four ordered tasks:

1. inventory the actual post-`M8` baseline from current files and tests
2. cluster open debt and rank entry candidates
3. freeze the first approved `M9` slice plus explicit non-goals
4. normalize closeout expectations and verification hooks for the next phase

Because this phase freezes a multi-phase milestone boundary, debt ordering, and later execution sequence, it must be treated as a complex phase.
Each task therefore requires its own standalone execution card under `docs/task_cards/m9_phase_0/`, even when the task itself is doc-only.

---

## 8. Phase Gate

`M9 Phase 0` passes only if all of the following are true:

- the post-`M8` baseline is written from current repository evidence rather than generic milestone language
- the open debt set is clustered into clear candidate themes with dependency and blast-radius reasoning
- one first feature-bearing `M9` slice is explicitly approved, or the phase records why approval is still blocked
- external lanes remain explicitly opt-in unless a later phase proves otherwise
- the resulting next phase can be split into implementation task cards without reopening scope debate

---

## 9. Risks

- treating the `M8` plan as if it were enough evidence for post-`M8` reality
- letting distributed concurrency ambitions pull `M9` open too early
- solving the smallest visible debt first while leaving the newest `M8` pilot risks underspecified
- promoting experimental external lanes to default behavior without new evidence
- letting Markdown and structured governance sources drift while replanning the next cycle

---

## 10. Expected Next Reassessment

Default target for the next feature-bearing phase, unless this phase disproves it:

- `M9 Phase 1 - Observability, Durable Recovery, And Governance Hardening`

If `M9 Phase 0` concludes that another slice should go first, this document must be updated with the exact replacement scope and the reason the default target was rejected.

## 11. Outcome

`M9 Phase 0` is now closed with the following milestone freeze:

- `M9 Phase 1 - Replay Linkage And Metrics Baseline`
- `M9 Phase 2 - Durable Recovery Lineage And Reconciliation`
- `M9 Phase 3 - Governance Metrics And Alerting`
- `M9 Phase 4 - Optional Review Policy Completion`
- `M9 Phase 5 - Freeze Review And Scope Closure`

The concurrency/ownership debts `TD-001` and `TD-009` remain visible, but they are explicitly excluded from `M9` and must be reassessed again only after this narrower milestone closes.
