# Current Development Workflow Guide

## Purpose

This is the canonical operator-facing guide for the **current** repository development flow.

Use this document when answering any of these questions:

- What phase are we currently in?
- What should be done next?
- How should a new phase be started?
- How are task cards written and executed?
- What tests and reviews are required before moving on?
- Which documents must be updated during implementation?

This guide does **not** replace historical phase reviews.
It tells contributors how to move the repository forward **from the current state**.

---

## 1. Canonical Documents

Use the following documents in this order.

### A. Current-state and next-step truth

- `README.md`
- `docs/reviews/m8-freeze-review.md`
- `docs/reviews/m7-freeze-review.md`
- `docs/tech-debt-registry.md`

These documents answer:

- what the repository already ships
- what the latest completed milestone is
- what the next approved work is
- which debts block the next milestone gate

### B. Execution protocol

- `docs/task_cards/m1_execution_loop_protocol.md`

This is the repository's detailed execution protocol for:

- phase reassessment
- phase-doc creation
- task-card splitting
- complex-task write-set / read-set discipline
- test-before-advance discipline
- phase-gate review

Even though the filename says `M1`, it is the repository's reusable execution standard for later cycles too.

### C. Historical implementation records

- `m*_phase_docs/`
- `docs/task_cards/m*_phase_*`
- `docs/reviews/*`

These are historical milestone and phase records.
They are useful as evidence and implementation references, but they are **not** the first source for current next-step decisions.

### D. Legacy reference policy

- `docs/legacy_ai_agent_reference_plan.md`
- `docs/legacy_project_reference_uplift_plan.md`
- `docs/m1_legacy_reference_uplift_plan.md`

These documents do **not** define the current roadmap.
They define how the legacy project should be consulted as a:

- semantics reference
- edge-case and test-case source
- anti-pattern catalog
- quality/governance reference for later cycles

Use them selectively and only when the current phase touches areas such as:

- runtime semantics
- review policy and review gates
- reconcile/repair behavior
- operator diagnostics
- regression coverage or governance hardening

Do **not** use them as permission to import legacy architecture, naming, or phase/task-card assumptions into the current repository.

---

## 2. Current Repository Position

Current confirmed status:

- milestone baseline: through `M8`, complete
- current cycle state: shipped local-first runtime baseline exists
- `M8` integration cycle: **complete**
- next approved work: **`M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`**
- integrated root-level `M8` plan:
  - `universal_agentic_workflow_os_M8_phase_plan_v1_0.md`
- supporting `M8` planning inputs:
  - `docs/reviews/m8-ecosystem-reuse-and-wheel-reinvention-assessment.md`
  - `docs/reviews/m8-external-tool-integration-and-self-build-plan.md`
  - `docs/reviews/m8-pre-entry-extra-optimization-assessment.md`
  - `docs/reviews/m8-gpt-pro-reassessment-and-plan-update.md`

The current controlling closeout record is:

- `docs/reviews/m8-freeze-review.md`

That record says the repository has completed the `M8` integration cycle and must open a fresh post-`M8` rebaseline before new breadth is approved.

Current next approved phase:

- **`M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`**

This means the repository is currently at:

1. `M7` complete
2. `Pre-M8` hardening complete
3. `M8 Phase 0` through `M8 Phase 7` complete
4. the next required step is a post-`M8` rebaseline for `M9`

---

## 3. Standard Development Loop

Every new phase should follow this exact loop.

### Step 1. Reassess the current baseline

Before writing code:

- read `README.md`
- read the latest freeze review
- read the current active plan
- read `docs/tech-debt-registry.md`
- read the immediately previous phase review and closeout notes
- if the phase touches runtime/review/reconcile/diagnostics/governance, query the legacy reference docs and open only the 1 to 3 most relevant indexed items

Goal:

- confirm what is already true
- confirm what is blocked
- confirm what the next phase is actually allowed to do
- decide whether legacy consultation is helpful for invariants, tests, or anti-pattern checks

### Step 2. Write or refresh the phase document

Create or update the phase doc first.

The phase doc must define:

- phase goal
- in-scope items
- out-of-scope items
- dependencies
- target outputs
- phase gate
- risks
- expected next reassessment

### Step 3. Split the phase into task cards

Create or update the phase task-card index.

The phase task-card index must define:

- task order
- dependencies
- complexity level
- write set
- test expectations
- closeout requirements

### Step 4. Create separate docs for complex tasks

If a task touches any of these, it should get its own task-card file:

- contracts
- migrations
- repositories
- service boundaries
- CLI/API surfaces
- runtime semantics
- state transitions
- review gates
- validation flow

### Step 5. Execute one task at a time

Do not implement a whole phase in one pass.

The expected loop is:

1. open task card
2. implement the smallest coherent slice
3. run the task-level tests
4. update the task card with actual result
5. only then move to the next task

### Step 6. Run phase-level verification

After all tasks in a phase are done:

- run the targeted phase test set
- run any required governance or validation checks
- update phase closeout text
- write the phase review

### Step 7. Reassess before the next phase

Do not auto-continue based only on the old plan.

Before the next phase starts:

- compare actual implementation with the phase doc
- update scope if reality changed
- confirm the next phase is still the right one

---

## 4. Required Test And Review Flow

The expected validation stack is layered.

### Task-level tests

Run the smallest relevant test set for the task:

- contract tests
- repository tests
- execution-loop tests
- CLI tests
- API tests
- governance tests

### Phase-level verification

At phase closeout, run the phase-appropriate combined checks.
Typical examples:

- targeted `pytest` suites
- `pytest -q` when the phase changes shared behavior
- `python -m infra.scripts.offline_validation --skip-offline-probe` when operator/runtime behavior changes
- specific smoke/demo commands if the phase changes shipped workflow paths

### Review documents

The normal documentation outputs are:

- updated phase doc
- updated phase task-card index
- updated complex task cards
- phase review document in `docs/reviews/`

If the phase closes a milestone or a hardening gate, also write:

- freeze review

---

## 5. Document Update Rules

This is the current rule of thumb for documentation maintenance.

### Always update these when behavior changes

- `README.md`
  - if user-visible commands, routes, runtime lanes, or current-state claims changed
- active phase doc
  - if scope, gate, or implementation reality changed
- active phase task-card index
  - if task status or dependencies changed
- complex task docs
  - if the actual implementation differs from the plan

### Update these when governance or roadmap meaning changes

- `docs/tech-debt-registry.md`
  - when a debt is created, repaid, renamed, or re-scoped
- `docs/reviews/...`
  - when a phase closes or a new planning/reassessment decision is made

### Do not rewrite these as if they were current-state docs

- old freeze reviews
- old phase reviews
- old milestone task-card indexes

Those are historical records and should stay historically accurate.

If a historical record needs reinterpretation, add a new current document that explains the reinterpretation instead of rewriting history.

---

## 6. How To Decide “What Should Be Done Next”

Use this priority order:

1. latest active synthesis or reassessment doc
2. latest freeze review
3. tech-debt items marked as blocking the next gate
4. current README status
5. historical milestone records

For the repository **right now**, the answer is:

- do **not** jump straight into unconstrained `M9` feature breadth
- treat `M8` as a completed integration cycle
- begin with an explicit `M9 Phase 0` reassessment and scope freeze

That means the next concrete work should be:

1. read `docs/reviews/m8-freeze-review.md`
2. open `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`
3. reassess what breadth is actually approved before writing feature code

---

## 7. What “Done” Means

### A task is done when:

- code is implemented
- the declared tests for that task pass
- the task card status is updated
- any planned documentation delta is written

### A phase is done when:

- every task is completed
- phase-level verification passes
- the phase review is written
- next-step reassessment is recorded

### A milestone or gate is done when:

- the freeze review exists
- the debt implications are updated
- the repository can clearly state what is complete and what is deferred

---

## 8. Current One-Line Instruction

If you need a single current instruction for the repository, use this:

> Follow the task-card protocol, but do not begin open-ended `M9` feature expansion yet; start with `M9 Phase 0 - Post-M8 Rebaseline And Scope Freeze`.
