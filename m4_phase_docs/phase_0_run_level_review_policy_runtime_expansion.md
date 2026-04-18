# M4 Phase 0 - Run-Level Review Policy Runtime Expansion

**Phase status:** Completed
**Phase position:** This phase starts after `M3 Phase 4` establishes policy governance and decision-table visibility. It turns a narrow slice of richer review-policy semantics into real run-level runtime behavior.

**Entry condition:** `TD-006` remains only partially repaid. Governance now explains `optional / recommended / mandatory`, but the runtime still executes only `auto_only` and `human_required`.

---

## 1. Reassessment

Current implementation status:

- The current runtime already has a stable `auto_only` path and a stable `human_required` path.
- `M3 Phase 4` made richer policies visible and referenceable, but not executable.
- The next useful move is not a broad quality-policy framework. It is a very small runtime expansion that keeps the current run model intact.

Legacy references worth absorbing now:

- `D:\AI Agent\tests\services\test_review_policy_routing.py`
- `D:\AI Agent\src\agentic_kernel\services\review_service.py`

What is worth reusing:

- route-level distinctions between optional / recommended / mandatory review intent
- test-first edge cases for escalation into human review

What must not be reused:

- legacy phase-review task mounting
- project-centric review-gate storage
- facade-style orchestration aggregation

---

## 2. In Scope

- expand run-level review policy semantics with **only** `recommended` and `mandatory`
- keep `optional` as reference-only because the current run model still lacks a clean non-blocking advisory-review terminal shape
- preserve current operator-facing review states:
  - `auto_passed`
  - `auto_failed`
  - `human_pending`
  - `human_approved`
  - `human_rejected`
- add preset coverage for the new executable policies
- update decision-table, governance report, CLI/API validation, and regression coverage

---

## 3. Out Of Scope

- adding new run statuses
- introducing new review tables or a separate review queue subsystem
- restoring legacy phase/task-card review chains
- implementing `optional`
- starting Domain Pack work

---

## 4. Target Runtime Semantics

- `auto_only`
  - execute
  - auto review
  - pass => `completed`
  - fail => `failed`
- `human_required`
  - execute
  - no auto review gate
  - always wait for human review
- `recommended`
  - execute
  - auto review
  - pass => `completed`
  - fail => escalate to human review and enter `awaiting_review`
- `mandatory`
  - execute
  - auto review
  - always require human sign-off after execution
  - `awaiting_review` regardless of auto verdict

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Contracts, presets, governance, and decision-table expansion
2. Runtime routing, projection fixes, and escalation behavior
3. CLI/API/docs/validation closeout

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- `recommended` and `mandatory` are executable review policies
- `optional` remains explicit as reference-only
- `recommended` auto-fail paths escalate into `awaiting_review`
- `mandatory` always lands in `awaiting_review` after execution
- `effective_review_state` stays backward-compatible for operator surfaces
- full verification stays green

---

## 7. Outcome

- Expanded executable run-level review policies with `recommended` and `mandatory`.
- Added `advisory_delivery` and `guarded_delivery` seed presets, updated resolver hints, and expanded the review semantics decision table and governance report.
- Implemented `recommended` auto-fail escalation into `awaiting_review` and `mandatory` always-human-signoff semantics.
- Fixed operator projections so any run still waiting for human review remains `human_pending` even if an auto verdict already exists.
- Updated README, offline validation, technical-debt notes, and legacy-reference status tracking.
- Verified with:
  - `pytest tests/test_contracts.py tests/test_repositories.py tests/test_governance.py -q` (`27 passed`)
  - `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q` (`124 passed`)
  - `pytest -q` (`153 passed`)
  - `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`)

---

## 8. Next Reassessment

- The next phase should decide whether to keep deepening review-policy execution semantics, or shift to the next M4 theme once run-level policy expansion is stable.
- The remaining gap after this phase should be smaller-scope policy ergonomics, not another broad governance-only expansion.
