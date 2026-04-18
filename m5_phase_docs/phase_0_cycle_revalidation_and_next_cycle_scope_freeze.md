# M5 Phase 0 - Cycle Revalidation And Next-Cycle Scope Freeze

**Phase status:** Completed  
**Phase position:** This phase starts after `M4 Phase 3` closes the previous delivery cycle. It does not reopen `M4`; it verifies that the closeout is still green, fixes any operator-facing regression found during revalidation, and freezes the next-cycle scope around LLM integration plus a minimal TUI.

**Entry condition:** `M4` is documented as complete, but the next-cycle work has not yet been converted into executable phase/task cards.

---

## 1. Reassessment

Current implementation status:

- the current local-first runtime is documented as complete through `M4`
- the repository already has `pytest`, `offline_validation`, and `manage.py demo` as closeout proofs
- `RuntimeGateway` remains a placeholder in practice
- there is still no TUI or Web operator surface

What must be answered now:

- does the previous cycle still pass when rerun from the current checkout
- are there any operator-visible regressions hiding behind the green baseline
- what is the smallest next-cycle scope that adds value without reopening the milestone

Decision:

- rerun the shipped acceptance proofs first
- treat any revalidation regression as phase-0 scope, not future debt
- freeze the next cycle to:
  - real LLM integration through the existing runtime boundary
  - minimal terminal UI for operator visibility

---

## 2. In Scope

- rerun the current-cycle acceptance checks
- document the new baseline and any regression discovered during revalidation
- fix operator-facing regression if found during verification
- write the next-cycle scope freeze for LLM + TUI only

---

## 3. Out Of Scope

- expanding review-policy breadth
- new domain-pack families
- Web frontend work
- cloud deployment
- distributed runtime semantics

---

## 4. Target Baseline

- `pytest -q` is green
- `python -m infra.scripts.offline_validation --skip-offline-probe` is green
- `python -m infra.scripts.manage --db-path <db> demo` is green
- operator governance commands work on a fresh migrated DB
- next-cycle scope is frozen around `LLM runtime integration` and `minimal TUI`

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Cycle revalidation and regression capture
2. Governance/operator regression fix if revalidation exposes one
3. Scope-freeze and closeout notes for the new cycle

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- the previous cycle is rerun successfully
- any revalidation regression found is fixed
- the next cycle is explicitly frozen to LLM + TUI

---

## 7. Verification Outcome

Completed in this phase:

- reran the shipped closeout baseline from the current checkout
- found and fixed a real operator regression in governance reporting on an unbootstrapped DB
- froze the next cycle to `OpenAI RuntimeGateway + minimal operator TUI`

Verification:

- `pytest tests/test_governance.py tests/test_cli.py -q`
  - `39 passed`
- `pytest -q`
  - `170 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
- `python -m infra.scripts.manage --db-path state/cycle_validation.db demo`
  - `status=completed`
- `python -m apps.operator_cli.main --db-path state/cycle_validation.db governance release-readiness`
  - succeeded on the revalidation DB after the seed-preset fallback fix

Result:

- Phase gate passed.
- The previous cycle remains green.
- The next cycle scope is locked to LLM integration and TUI only.
