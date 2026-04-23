# M36 Workbench IA / Capability Slot Freeze Review

Date: 2026-04-24  
Status: accepted

## Summary

`M36 Phase 0` is accepted as the workbench IA and bounded capability-slot freeze baseline. Starting from accepted `M35`, the repository froze the workbench/product-surface boundaries, kept the operator/workbench split explicit, and landed only the minimum bounded external capability pilots needed to support deeper `M36` workbench execution.

This closeout is intentionally narrow. It does not claim that `M36` is complete, that the conversational workbench flow already ships, or that the broader capability ecosystem has been productized. It does establish one honest attachment path for stronger coding, search, and image-understanding capabilities.

## Landed

- froze the bounded `M36 Phase 0` scope and aligned repository truth through:
  - [m36_phase_docs/phase_0_workbench_ia_and_capability_slot_freeze.md](../../m36_phase_docs/phase_0_workbench_ia_and_capability_slot_freeze.md)
  - [docs/task_cards/m36_phase_0_task_cards.md](../task_cards/m36_phase_0_task_cards.md)
  - [docs/current_development_workflow.md](../current_development_workflow.md)
  - [README.md](../../README.md)
  - [NEXT_DEVELOPMENT_PLAN.md](../../NEXT_DEVELOPMENT_PLAN.md)
  - [POST_M34_MULTIPHASE_ROADMAP.md](../../POST_M34_MULTIPHASE_ROADMAP.md)
- preserved the additive `execution_profile` family from `M35` as the only execution truth family and extended it additively for `codex_model` in:
  - [packages/contracts/models.py](../../packages/contracts/models.py)
  - [packages/core_domain/execution_profiles.py](../../packages/core_domain/execution_profiles.py)
  - [packages/core_domain/config.py](../../packages/core_domain/config.py)
  - [packages/core_domain/service_projection.py](../../packages/core_domain/service_projection.py)
- added `CodexAdapter` as an additive coding lane through the existing worker-router/runtime seams in:
  - [packages/worker_adapters/codex_adapter.py](../../packages/worker_adapters/codex_adapter.py)
  - [packages/worker_adapters/router.py](../../packages/worker_adapters/router.py)
  - [apps/remote_worker_api/main.py](../../apps/remote_worker_api/main.py)
- generalized bounded repo-mutation eligibility from a hard-coded adapter-name rule to patch-capable adapter behavior in:
  - [packages/worker_adapters/base.py](../../packages/worker_adapters/base.py)
  - [packages/worker_adapters/opencode_adapter.py](../../packages/worker_adapters/opencode_adapter.py)
  - [packages/core_domain/service_lifecycle.py](../../packages/core_domain/service_lifecycle.py)
  - [packages/core_domain/services.py](../../packages/core_domain/services.py)
- exposed additive `codex_model` compile/runtime controls through:
  - [apps/operator_cli/main.py](../../apps/operator_cli/main.py)
  - [apps/orchestrator_api/request_models.py](../../apps/orchestrator_api/request_models.py)
  - [apps/orchestrator_api/routers/runs.py](../../apps/orchestrator_api/routers/runs.py)
  - [packages/core_domain/compile.py](../../packages/core_domain/compile.py)
- extended the capability plane so bounded MCP profiles can carry startup env and seeded MiniMax search/image-understanding capability through:
  - [packages/core_domain/capability_plane.py](../../packages/core_domain/capability_plane.py)
  - [infra/seeds/mcp_server_profiles.json](../../infra/seeds/mcp_server_profiles.json)
- updated governance/release-readiness expectations and regression coverage so the new adapter/capability surfaces are reflected in:
  - [packages/core_domain/governance.py](../../packages/core_domain/governance.py)
  - [tests/test_execution_loop.py](../../tests/test_execution_loop.py)
  - [tests/test_api.py](../../tests/test_api.py)
  - [tests/test_cli.py](../../tests/test_cli.py)
  - [tests/test_governance.py](../../tests/test_governance.py)
  - [tests/test_release_closeout.py](../../tests/test_release_closeout.py)

## Validation

- focused compile/import validation passed:
  - `python -m compileall packages apps infra`
- targeted execution-loop validation for `codex` and MCP startup-env behavior passed:
  - `pytest tests/test_execution_loop.py -k "codex or capability_registry_routes or preview_tool_projection_includes_mcp_subset_for_reviewable_pilot or mcp_profile_startup_env_resolves_env_placeholders or explicit_execution_overrides_drive_runtime_gateway_and_adapter_model or compile_run_accepts_repo_mutation_contract_and_projects_it" --no-cov --basetemp state/.pytest-tmp-codex-loop`
- targeted API validation passed:
  - `pytest tests/test_api.py -k "capability_routes or compile_can_pin_codex_adapter or compile_rejects_unknown_adapter" --no-cov --basetemp state/.pytest-tmp-codex-api`
- targeted CLI validation passed:
  - `pytest tests/test_cli.py -k "compile_can_pin_codex_adapter or compile_rejects_unknown_adapter or db_reset_and_preset_list" --no-cov --basetemp state/.pytest-tmp-codex-cli`
- targeted governance and closeout validation passed:
  - `pytest tests/test_governance.py::test_build_release_readiness_report_projects_current_closeout_gates --no-cov --basetemp state/.pytest-tmp-codex-gov2`
  - `pytest tests/test_release_closeout.py -k "canonical_closeout_packet" --no-cov --basetemp state/.pytest-tmp-codex-gov`
- full repository regression passed:
  - `pytest --basetemp state/.pytest-tmp-m36-all`
  - `296 passed`
- offline validation passed:
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed: true`
- documentation link validation passed:
  - `python -m infra.scripts.check_doc_links`
  - `passed: true`

## Workflow Dogfood

Using the dedicated workspace DB at `state/workspaces/ed57374f70/m36_phase0.db`, workflow dogfood covered the required kickoff paths:

- implementation-oriented path
  - session: `intent_session_d1e62123648f`
  - status: `ready_to_launch`
  - preset: `project_delivery`
  - cluster: `dev_cluster`
  - plan draft projected the existing multi-role execution path while surfacing the additive `codex_model` and the new `codex` route in capability policy preview
- evidence-oriented path
  - session: `intent_session_c18998538cf1`
  - status: `ready_to_launch`
  - preset: `research_spike_reviewable`
  - cluster: `research_cluster`
  - plan draft projected the bounded MiniMax MCP profile in the capability policy preview and kept the phase kickoff on the existing interaction/session surface

## What Is Now True

- accepted `M35` remains the latest completed milestone
- accepted `M36 Phase 0` is now the latest accepted bounded freeze
- the current workbench is still a minimum preview rather than a completed conversational workbench v1
- the workbench IA and operator/workbench surface boundaries are now explicit and frozen for later `M36` work
- stronger coding capability can now attach through `codex` as an additive adapter under the existing execution-profile/router system
- bounded search and image-understanding capability can now attach through the seeded MiniMax MCP profile under the existing capability plane
- `MMX CLI`, `gcloud` / Vertex AI, automation-plane breadth, and broader capability-ecosystem productization remain deferred
- no post-`M36 Phase 0` bounded phase is open yet

## Repaid In M36 Phase 0

- no structural debt item was fully repaid in `M36 Phase 0`

## Carried Forward

- `TD-STRUCT-001`
  - partially repaid
  - `OrchestratorService` still concentrates wider cross-plane wiring beyond the bounded capability-slot freeze
- `TD-STRUCT-003`
  - partially repaid
  - internal tables, events, and legacy wording still retain consensus-era naming even though public semantics are more honest
- `TD-STRUCT-005`
  - deferred
  - bounded MiniMax MCP capability slots now exist, but capability health still lacks full runtime telemetry closure across every provider lane
- `TD-STRUCT-006`
  - partially repaid and deferred
  - future platform objects still need a governed promotion path into current contracts

## Residual Risk

- `M36 Phase 0` intentionally does not ship the guided clarification, follow-up, execution-preview, or launch UX from later `M36` phases
- the `codex` and MiniMax pilots are bounded capability-slot landings, not a finished capability-ecosystem product surface
- `MMX CLI` and `gcloud` / Vertex AI may still become useful later, but they are intentionally deferred until a later bounded phase can justify them honestly
