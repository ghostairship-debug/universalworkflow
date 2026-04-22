# M31 Services Audit

Status: retained closeout artifact  
Captured: 2026-04-21  
Milestone: M31 Phase 0

## Summary

`OrchestratorService` currently defines 144 methods directly in `packages/core_domain/services.py`, while still inheriting large public surfaces from `LifecycleServiceMixin`, `ProjectionServiceMixin`, and `MemorySimulationServiceMixin`. The facade remains the true composition root, but it is also still the effective center of orchestration, ownership, inspection, repair, scheduler integration, and project-delivery control flow.

This audit is the `M31` starting point. The immediate goal is not to fully delete the facade, but to stop further uncontrolled growth and establish explicit delegation seams that later refactors can deepen safely.

## Current Seam Map

- Lifecycle / execution orchestration
  - `create_run`, `apply_run_repair`, `compile_run`, `recompile_run`, `prepare_run`, `resume_run`, `execute_run`, `resume_runs_parallel`, `cancel_run`
- Review policy / human-gate handling
  - `approve_run_review`, `reject_run_review`, `_effective_review_state`, `_review_policy_for_context`, `_finalize_human_review`
- Audit / replay / projection
  - `get_run_summary`, `get_event_inspection`, `get_run_audit_report`, `get_run_replay_packet`, `get_status_detail`, `inspect_run_state`, `reconcile_run`, `get_run_operator_packet`, `get_dashboard_snapshot`
- Ownership / lease / scheduler control
  - `list_claims`, `list_worker_leases`, `list_runtime_attempts`, `list_snapshots`, `get_budget_ledger`, `submit_scheduler_proposal`, `record_scheduler_peer_heartbeat`, `release_scheduler_lease`, `get_scheduler_lease`, `record_worker_heartbeat`, `record_worker_completion`
- Capability / memory / plan preview
  - `list_capability_sources`, `list_capability_descriptors`, `list_capability_health`, `preview_tool_projection`, `preview_orchestration_plan_graph`, `preview_capability_policy`, `preview_goal_packet`, `launch_goal`
- Project-delivery special path
  - `_default_project_delivery_plan`, `_compile_child_run_with_fallback`, `_execute_project_delivery_orchestration`, `_write_orchestration_artifact`
- Repair / reconciliation internals
  - claim release, lease release, interrupt, snapshot, inspection, and repair-selection helpers remain concentrated in the facade

## Initial Delegation Target

`M31 Phase 0` introduces four explicit boundary services:

- `RunLifecycleService`
- `ReviewPolicyService`
- `AuditReplayService`
- `OwnershipLeaseService`

These services are introduced as explicit delegation seams first. The deeper internal move of helper logic out of `services.py` can then happen without changing CLI/API/Web/TUI public signatures.

## Immediate Risks

- `project_delivery` still hard-codes orchestration execution inside the facade
- scheduler-authority payload creation and repair classification remain coupled to the same file
- compile/runtime state assembly still mixes lifecycle, orchestration, mutation, durable, and capability concerns
- projection, ownership, and repair helpers are still interleaved around the same facade object

## Recommendation

- freeze further growth of public `OrchestratorService` responsibilities
- route new public work through the new boundary services first
- use `M32` to move graph, capability, and cluster logic behind shared contracts instead of adding new special paths
