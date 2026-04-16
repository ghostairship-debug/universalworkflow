# Phase 0 Task Cards

## Reassessment

- Latest Gemini and Opus reassessments are green.
- No new blockers were introduced after the document integration pass.
- Phase 0 can proceed without further planning edits.

## Card P0-01: Freeze M0 scope

- Source refs:
  `universal_agentic_workflow_os_local_first_plan_v2_1.md`
  `universal_agentic_workflow_os_M0_task_breakdown_v2_1.md`
  `m0_phase_docs/phase_0_scope_and_governance.md`
- Goal:
  Produce a single M0 scope document with explicit goals, non-goals, success criteria, and M1 boundary.
- Deliverable:
  `docs/architecture/m0-scope.md`
- Done when:
  The document clearly states what M0 does, what it does not do, and what prevents closure.

## Card P0-02: Freeze Wave 1 object responsibilities

- Source refs:
  `universal_agentic_workflow_os_M0_task_breakdown_v2_1.md`
  `m0_phase_docs/phase_0_scope_and_governance.md`
- Goal:
  Write the canonical object responsibility guide for Wave 1 and the deferred object outline for Wave 2/3.
- Deliverables:
  `docs/contracts/wave1-objects.md`
  `docs/contracts/future-objects-outline.md`
- Done when:
  Responsibilities and anti-responsibilities are explicit and HandoffLite is frozen as schema-only in M0.

## Card P0-03: Lock architecture decisions

- Source refs:
  `m0_phase_docs/phase_0_scope_and_governance.md`
  `M0_Evaluation_and_Suggestions.md`
  `M0_Evaluation_Claude_Opus.md`
- Goal:
  Capture ADR-001 to ADR-005 using one shared structure and the updated runtime constraints.
- Deliverables:
  `docs/adrs/ADR-001.md` to `docs/adrs/ADR-005.md`
- Done when:
  ADR-004 includes `RuntimeGateway`, import isolation, and "state stores refs only"; ADR-005 fixes serial M0 execution and rejects a global mutex.

## Phase 0 exit check

- `m0-scope` is written and matches the M0 task breakdown.
- Wave 1 and future object docs are consistent with the integrated naming.
- ADR-001 to ADR-005 are complete and non-conflicting.
