# M34 Phase 0: Facade Reduction / Authority Interior Cleanup

Status: completed
Opened: 2026-04-22
Closed: 2026-04-22
Baseline: accepted `M33 Phase 0`

## Purpose

Open the next bounded post-`M33` phase. This line continues the structural contraction work that `M33` started, but narrows the focus to the two debts that most directly block a cleaner core boundary story:

1. further `OrchestratorService` facade reduction
2. deeper scheduler-authority interior honesty cleanup
3. bounded validation and honest carry-forward

## Why This Phase Exists

Accepted `M33 Phase 0` repaid `TD-STRUCT-004`, but four structural debts remain open:

- `TD-STRUCT-001`: `OrchestratorService` still concentrates too much cross-plane wiring
- `TD-STRUCT-003`: scheduler-authority interior naming still retains legacy semantics beyond the public honesty fixes
- `TD-STRUCT-005`: capability health still needs fuller runtime-backed telemetry
- `TD-STRUCT-006`: governed promotion of future platform objects still lacks a fuller reusable mechanism

The next safest bounded step is to finish another slice of service-boundary reduction and continue the scheduler-authority honesty cleanup before opening broader telemetry or promotion work.

## Scope

This phase includes:

- `M34-0A` opening/governance and debt-focus freeze
- `M34-0B` further `OrchestratorService` facade reduction
- `M34-0C` scheduler-authority interior naming / event / diagnostic cleanup
- `M34-0D` validation, closeout, and carry-forward judgment

This phase explicitly does not include:

- automation-plane behavior
- product-breadth workbench expansion beyond the current minimum preview
- broader role/profile/cluster expansion
- capability-health telemetry expansion beyond bug-driven fixes
- governed promotion machinery for future platform objects
- public API / packet / route breaking renames

## Execution Model

Development for this phase runs on the clean primary `main` worktree.

Rules:

- accepted `M33 Phase 0` remains the latest completed freeze baseline
- bug-first remains mandatory: if workflow/runtime validation exposes a real regression, repair it before continuing refactor scope
- the repository should prefer additive or delegate-based cleanup over speculative large rewrites
- targeted regression and workflow dogfood remain merge gates, not afterthought validation

## Workstreams

### Workstream A: Phase Opening And Focus Freeze

- open `M34 Phase 0` formally
- update the workflow guide, README, and debt registry so the repository now points at an active post-`M33` phase
- lock the active debt target to `TD-STRUCT-001` and `TD-STRUCT-003`

### Workstream B: Facade Reduction

- continue extracting bounded orchestration-adjacent and cross-plane helper concentration out of `OrchestratorService`
- keep current CLI/API/service entry points stable
- avoid deleting the facade until the seam map is honest enough to do so safely

### Workstream C: Authority Interior Cleanup

- continue semantic honesty cleanup behind the accepted public authority wording
- prefer additive aliases, wrappers, and bounded interior renames over storage migrations unless a migration becomes both necessary and safe
- preserve existing `/healthz`, scheduler/authority cluster surfaces, operator views, and compatibility keys

### Workstream D: Validation And Closeout

- validate that facade reduction and authority cleanup did not regress shipped execution paths
- use workflow dogfood and governance/readiness coverage as closeout gates
- carry forward any remaining structural debt explicitly and honestly

## Entry Criteria

To remain in-bounds, the phase preserves these assumptions:

- accepted `M33 Phase 0` remains the latest completed freeze baseline
- active work is limited to `TD-STRUCT-001` and `TD-STRUCT-003`
- `TD-STRUCT-005` and `TD-STRUCT-006` stay deferred unless a real bug-first repair requires a narrower bounded exception
- no automation-plane or broader product-plane breadth opens under cleanup naming

## Exit Criteria

The phase is complete only when:

- `M34` phase docs and task cards are fully updated with actual outcomes
- `OrchestratorService` loses another honest bounded slice of helper concentration without public breakage
- scheduler-authority interior naming is less legacy-loaded and better aligned with the already-correct public semantics
- targeted regression and workflow dogfood pass without unresolved regression
- any remaining open structural debt is carried forward explicitly

## Evidence Expectations

Closeout for this phase must include:

- updated task-card status with actual results
- targeted validation around orchestration/service and scheduler-authority surfaces
- workflow dogfood through at least one shipped orchestration path and one scheduler-authority/operator read path
- explicit debt judgment for the remaining `TD-STRUCT-*` items

## Outcome

`M34 Phase 0` is complete as a bounded cleanup phase.

Its net result is:

- `TD-STRUCT-001` further partially repaid through another bounded scheduler-authority support seam extracted out of `OrchestratorService`
- `TD-STRUCT-003` further partially repaid through safe internal authority-oriented helper renames and additive alias propagation across committed-lease, projection, dispatch, and worker diagnostic payloads
- `TD-STRUCT-005` and `TD-STRUCT-006` remain deferred to a post-`M34` bounded follow-on

No post-`M34` bounded phase is open yet. Do not resume later breadth work until the next bounded phase is explicitly opened.
