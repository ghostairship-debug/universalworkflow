# M33 Phase 0: Orchestration / Service Contraction

Status: active  
Opened: 2026-04-22  
Baseline: accepted `M32 Phase 0`

## Purpose

Open the first bounded post-`M32 Phase 0` contraction line. This phase is focused on reducing the remaining structural coupling that still limits safe orchestration expansion after the interaction/profile/cluster foundation landed.

The phase has five concrete outcomes:

1. formal `M33` opening and debt-focus freeze
2. contraction of residual `project_delivery`-shaped orchestration assumptions
3. further `OrchestratorService` seam extraction without public-surface breakage
4. deeper scheduler-authority semantic cleanup behind the already-correct public claims
5. bounded validation and honest carry-forward judgment

## Why This Phase Exists

The accepted `M32 Phase 0` closeout repaid `TD-STRUCT-002`, but five structural debts remain open:

- `TD-STRUCT-001`: further `OrchestratorService` facade reduction
- `TD-STRUCT-003`: deeper scheduler-authority naming and semantic honesty cleanup
- `TD-STRUCT-004`: removal of residual `project_delivery`-shaped orchestration assumptions
- `TD-STRUCT-005`: fuller runtime-backed capability health
- `TD-STRUCT-006`: governed promotion path for future platform objects

The next bounded step should target the debts that most directly block safe follow-on expansion of the runtime core:

- `TD-STRUCT-004`
- `TD-STRUCT-001`
- `TD-STRUCT-003`

`TD-STRUCT-005` and `TD-STRUCT-006` remain intentionally deferred to a post-`M33 Phase 0` bounded follow-on unless bug-first repair work requires a narrower bounded fix sooner.

## Scope

This phase includes:

- `M33-0A` opening/governance and debt-focus freeze
- `M33-0B` shared orchestration substrate contraction
- `M33-0C` `OrchestratorService` seam extraction
- `M33-0D` scheduler-authority semantic cleanup
- `M33-0E` validation, closeout, and carry-forward judgment

This phase explicitly does not include:

- automation-plane behavior
- workbench product breadth
- large role/profile/cluster expansion
- capability-health telemetry expansion beyond bug-driven fixes
- governed promotion machinery for later bundle/platform-object material
- new `*_delivery` service special paths

## Execution Model

Development for this phase runs on the clean primary `main` worktree unless a high-risk refactor needs temporary isolation.

Rules:

- accepted `M32 Phase 0` remains the last completed freeze baseline
- bug-first remains mandatory: if workflow/runtime validation exposes a real regression, repair it before continuing refactor scope
- if a refactor becomes risky enough to justify isolation, use bounded local `worktree` lanes with isolated DB paths
- targeted regression and workflow dogfood are merge gates, not afterthought validation

## Workstreams

### Workstream A: Phase Opening And Focus Freeze

- open `M33 Phase 0` formally
- update the workflow guide, README, and debt registry so the repository now points at an active post-`M32` phase
- lock the active debt target to `TD-STRUCT-004`, `TD-STRUCT-001`, and `TD-STRUCT-003`

### Workstream B: Orchestration Substrate Contraction

- reduce preset-specific orchestration branching that still assumes a `project_delivery`-shaped flow
- keep `project_delivery`, `guarded_project_delivery`, and `DevCluster` compatibility intact
- continue converging orchestration toward one shared execution truth chain

### Workstream C: Service Boundary Extraction

- move more cross-plane helper concentration out of `OrchestratorService`
- keep the public surface stable while making the seam map more honest
- avoid facade breakage or speculative broad rewrites

### Workstream D: Scheduler-Authority Semantic Cleanup

- clean up legacy consensus-era internal wording where it overstates the actual guarantee
- preserve compatibility where migrations or public API stability require additive handling
- keep public/operator semantics aligned with the accepted `M20` and `M31` honesty baseline

### Workstream E: Validation And Closeout

- validate that orchestration contraction did not regress the shipped paths
- use workflow dogfood and regression coverage as closeout gates
- carry forward any remaining structural debt explicitly and honestly

## Entry Criteria

To remain in-bounds, the phase preserves these assumptions:

- accepted `M32 Phase 0` remains the latest completed freeze baseline
- active work is limited to the three currently targeted structural debts
- `TD-STRUCT-005` and `TD-STRUCT-006` stay deferred unless a real bug-first repair requires a bounded exception
- no automation-plane or broader product-plane breadth opens under contraction naming

## Exit Criteria

The phase is complete only when:

- `M33` phase docs and task cards are fully updated with actual outcomes
- orchestration no longer depends on the current residual `project_delivery`-shaped assumptions that block safer expansion
- `OrchestratorService` loses another bounded slice of cross-plane helper concentration without public breakage
- scheduler-authority wording is more internally honest and less legacy-loaded
- targeted regression and workflow dogfood pass without unresolved regression
- any remaining open structural debt is carried forward explicitly

## Evidence Expectations

Closeout for this phase must include:

- updated task-card status with actual results
- targeted validation around governance, orchestration, and scheduler-authority surfaces
- workflow dogfood through at least `project_delivery`, `guarded_project_delivery`, and one cluster-aware path
- explicit debt judgment for the remaining `TD-STRUCT-*` items

## Outcome

`M33 Phase 0` is now the active bounded phase.

Its immediate focus is:

- repay `TD-STRUCT-004`
- continue repaying `TD-STRUCT-001`
- continue repaying `TD-STRUCT-003`

Do not open later breadth work until this bounded contraction line is closed honestly.
