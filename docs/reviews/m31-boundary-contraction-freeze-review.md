# M31 Boundary Contraction And Semantic Honesty Freeze Review

Date: 2026-04-21  
Status: accepted

## Summary

`M31 Phase 0` is accepted as a bounded closeout. The repository completed the post-`M30` contraction line without opening interaction-plane, automation-plane, or broader `M32-M36` breadth. The accepted outcome is a more explicit service-boundary seam map, semantically honest scheduler-authority wording, a shared additive orchestration graph substrate, and additive capability invocation / receipt / runtime-probe surfaces.

This is an accepted phase closeout, not a zero-debt or release-ready claim. The repository now uses the `M31 Phase 0` freeze as its latest accepted bounded baseline and carries the remaining structural debt explicitly into `M32`.

## Landed

- bounded `M31 Phase 0` phase docs and task cards were opened, executed, and closed
- `OrchestratorService` now exposes explicit delegate seams for run lifecycle, review policy, audit/replay, and ownership/lease concerns
- `mcp` import/install moved behind an optional boundary and `CapabilityPlane` now degrades cleanly when the dependency is absent
- coverage tooling is part of the dev extra and the repository enforces a coverage floor in the default pytest configuration
- scheduler-authority public wording now uses `single_store_quorum` / single-store quorum-style authority semantics
- `OrchestrationPlanGraph` gained additive `edges`, `barriers`, and `retry_policies`, and a minimum orchestration engine now routes both `project_delivery` and `guarded_project_delivery`
- additive `CapabilityInvocationEnvelope` and `CapabilityExecutionReceipt` contracts now project through compile/runtime/audit/operator surfaces
- `CapabilityHealth` now reports runtime-probe fields instead of only static descriptor enablement

## Validation

- `python -m pytest -q` passed with `278 passed` and coverage above the configured floor
- workflow self-dogfood on `state/m31_phase0_validation.db` exercised `launch`, `compile`, `resume`, `operator-packet`, `audit-report`, `replay-packet`, `plan-graph`, `approve`, and `reject` against `guarded_project_delivery`
- `powershell -ExecutionPolicy Bypass -File .\\infra\\scripts\\run_offline_validation.ps1` produced `state/offline_validation_report.json`
- the offline validation report is not fully green:
  - `offline_probe` failed because validation was run on a connected machine
  - `cli_flow` and `api_flow` intentionally remain non-green while open structural debt is still carried, because the validation harness currently treats zero open debt as a release-level expectation
- `governance release-readiness` now sees the offline-validation artifact and green cluster cutover evidence, but still reports `overall_ready: false` because validation is not fully green and six structural debt items remain open

## What Is Now True

- `M31 Phase 0` is complete as a bounded contraction/hardening phase
- `M31-D/E` were not opened as active execution phases
- no post-`M31 Phase 0` bounded phase is open yet
- the next valid expansion step is an explicitly opened `M32` phase, not a continuation of `M31`
- `interaction plane` remains the next breadth candidate and `automation plane` remains deferred behind it

## Carried Into M32

- `TD-STRUCT-001`: further `OrchestratorService` facade reduction
- `TD-STRUCT-002`: final absorption/pruning of retained opening-bundle and phase artifacts
- `TD-STRUCT-003`: deeper cleanup of consensus-era scheduler naming
- `TD-STRUCT-004`: removal of remaining `project_delivery`-shaped orchestration assumptions
- `TD-STRUCT-005`: fuller capability runtime telemetry beyond additive probe fields
- `TD-STRUCT-006`: governed promotion path for future platform objects

## Entry Gate To M32

The next bounded phase should open as an interaction-first `M32` line:

1. create the `M32` phase doc first
2. create only the `M32` task-card index and detailed cards
3. carry the open `TD-STRUCT-*` items forward explicitly
4. start with governed interaction contracts and promotion rules before any automation-plane work
