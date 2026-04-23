# M35 Role / Execution Productization Freeze Review

Date: 2026-04-24  
Status: accepted

## Summary

`M35` is accepted as the role / execution productization closeout. Starting from the accepted `M34 Phase 0` baseline and the cleared pre-open hardening gate, the repository turned execution selection into a first-class product surface across preset, role-profile, cluster, compile/runtime, CLI/API, and read-model layers without breaking the shipped operator-facing routes.

This closeout is not a zero-debt claim. No structural debt item is fully retired in `M35`, but the repository can now explain resolved execution honestly and carry the remaining debt forward explicitly.

## Landed

- added additive execution-profile contracts in [packages/contracts/models.py](../../packages/contracts/models.py):
  - `ExecutionProfileDefinition`
  - `ExecutionScopeContext`
  - `ResolvedExecutionProfile`
- attached execution-profile metadata to the shipped scope objects that now own execution defaults:
  - preset definitions
  - agent profiles
  - generated profiles
  - cluster templates and cluster members
  - role assignments, orchestration steps, and orchestration graph nodes
- implemented one authoritative execution resolver in [packages/core_domain/execution_profiles.py](../../packages/core_domain/execution_profiles.py) with explicit precedence, per-field provenance, and compatibility fallback behavior
- exposed additive global execution defaults through [packages/core_domain/config.py](../../packages/core_domain/config.py) and preserved the existing unified config precedence chain
- switched compile, recompile, resume, orchestration planning, and child-run compilation onto resolved execution decisions in:
  - [packages/core_domain/service_lifecycle.py](../../packages/core_domain/service_lifecycle.py)
  - [packages/core_domain/service_orchestration.py](../../packages/core_domain/service_orchestration.py)
  - [packages/core_domain/compile.py](../../packages/core_domain/compile.py)
- made runtime consumption respect resolved execution decisions in:
  - [packages/runtime_langgraph/gateway.py](../../packages/runtime_langgraph/gateway.py)
  - [packages/worker_adapters/langchain_agent_adapter.py](../../packages/worker_adapters/langchain_agent_adapter.py)
  - [packages/worker_adapters/opencode_adapter.py](../../packages/worker_adapters/opencode_adapter.py)
- extended read-side explanation additively through:
  - [packages/core_domain/service_projection.py](../../packages/core_domain/service_projection.py)
  - [packages/core_domain/service_memory_simulation.py](../../packages/core_domain/service_memory_simulation.py)
  - `resolved_execution`
  - `execution_resolution_trace`
- extended shipped API and CLI surfaces additively so compile/recompile can accept explicit execution overrides and surface the resolved result:
  - [apps/orchestrator_api/routers/runs.py](../../apps/orchestrator_api/routers/runs.py)
  - [apps/operator_cli/main.py](../../apps/operator_cli/main.py)
- seeded shipped defaults for the productized surfaces:
  - [infra/seeds/presets.json](../../infra/seeds/presets.json)
  - [packages/core_domain/interaction_catalog.py](../../packages/core_domain/interaction_catalog.py)
  - [packages/core_domain/repositories.py](../../packages/core_domain/repositories.py)

## Validation

- targeted execution-loop regression passed:
  - `pytest tests/test_execution_loop.py --no-cov --basetemp state/.pytest-tmp-m35-loop -q`
  - `104 passed`
- targeted API regression for additive execution-profile surfaces passed:
  - `pytest tests/test_api.py -k "api_exposes_effective_config_and_worker_pools or api_compile_and_status_detail_are_public_in_m1 or api_exposes_capability_mcp_sources_for_agent_lane" --no-cov --basetemp state/.pytest-tmp-m35-api -q`
- targeted CLI regression for additive execution-profile surfaces passed:
  - `pytest tests/test_cli.py -k "cli_config_show_reads_workflow_toml_and_worker_pools or cli_compile_recompile_status_detail_and_handoffs or projection" --no-cov --basetemp state/.pytest-tmp-m35-cli -q`
  - `6 passed`
- full repository regression passed:
  - `pytest --basetemp state/.pytest-tmp-m35-all`
  - `289 passed`
- offline validation passed:
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed: true`
- documentation link validation passed:
  - `python -m infra.scripts.check_doc_links`

## Workflow Dogfood

Using the dedicated workspace DB at `state/workspaces/ed57374f70/m35_phase0.db`, workflow dogfood covered the required phase kickoff paths:

- implementation-oriented path
  - session: `intent_session_259ebdada96e`
  - status: `ready_to_launch`
  - preset: `project_delivery`
  - cluster: `dev_cluster`
  - plan draft projected resolved execution for planner, coder, researcher, and reviewer roles
- evidence-oriented path
  - session: `intent_session_60b818313eb1`
  - status: `ready_to_launch`
  - preset: `research_spike_reviewable`
  - cluster: `research_cluster`
  - plan draft projected resolved execution and provenance for the research-led path

## What Is Now True

- roles, presets, agent profiles, cluster templates, and cluster members can now own additive execution defaults
- one authoritative precedence line now explains which scope won and why
- compile/runtime/orchestration no longer rely only on implicit router defaults; they consume resolved execution decisions directly
- CLI, API, and current read surfaces can expose both the resolved execution payload and the resolution trace without breaking existing route families
- accepted `M35` is now the latest completed bounded baseline
- no post-`M35` bounded phase is open yet

## Repaid In M35

- no structural debt item was fully repaid in `M35`

## Carried Forward

- `TD-STRUCT-001`
  - partially repaid
  - `OrchestratorService` still concentrates wider cross-plane wiring beyond the execution-profile work
- `TD-STRUCT-003`
  - partially repaid
  - internal tables, events, and legacy wording still retain consensus-era naming even though public semantics are now more honest
- `TD-STRUCT-005`
  - deferred
  - capability health still lacks full runtime telemetry closure across every provider lane
- `TD-STRUCT-006`
  - partially repaid and deferred
  - governed promotion of future platform objects still needs a later milestone path

## Residual Risk

- execution explainability is now honest for the shipped resolution chain, but `TD-STRUCT-005` remains open because capability health telemetry is still not fully runtime-backed
- `M35` intentionally does not open automation-plane breadth, generated-role lifecycle, or `M36` workbench productization
