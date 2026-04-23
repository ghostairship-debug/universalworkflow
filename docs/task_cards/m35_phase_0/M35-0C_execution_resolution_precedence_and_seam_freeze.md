# M35-0C Execution Resolution Precedence And Seam Freeze

Status: completed

## Goal

Freeze the exact execution-resolution precedence line and the seams where later `M35` phases will consume resolved execution decisions.

## Acceptance

- define one authoritative precedence order for execution resolution:
  1. explicit invocation override
  2. cluster-member execution configuration
  3. agent-profile execution configuration
  4. preset execution configuration
  5. cluster-template default execution configuration
  6. effective global defaults from the existing unified config system
  7. existing domain-pack and compatibility fallback behavior
- keep the existing unified config precedence unchanged inside the global-default layer:
  1. explicit config override
  2. environment
  3. `workflow.toml`
  4. built-in default
- freeze the resolved output field set for later phases:
  - `adapter_name`
  - `runtime_gateway_provider`
  - `model`
  - `model_variant`
  - `reasoning_effort`
  - `worker_pool_id`
- freeze additive provenance requirements for every resolved field so later read surfaces can explain which scope/source won
- freeze the future resolver-consumption seam list without fully rewiring runtime behavior yet:
  - interaction launch
  - compile / recompile preparation
  - cluster orchestration planning and child-run compilation
  - runtime execution selection
  - status/summary/replay/operator projection
- require later read-model expansion to remain additive under the current `execution_profile` family, using nested resolved-execution and provenance data instead of a new top-level packet family

## Notes

- do not replace the current adapter/router defaults with speculative behavior before the precedence line is frozen and reviewed
- when an explicit scope does not supply a field, the resolver should continue downward rather than manufacturing a synthetic override
- `TD-STRUCT-005` remains deferred unless a narrow explainability slice becomes necessary to make later `M35` closeout honest

## Result

- implemented one authoritative resolver in [packages/core_domain/execution_profiles.py](../../../packages/core_domain/execution_profiles.py)
- the shipped precedence order now resolves explicitly through:
  1. invocation override
  2. cluster-member execution profile
  3. agent-profile execution profile
  4. preset execution profile
  5. cluster-template default execution profile
  6. effective global defaults from the existing unified config system
  7. compatibility fallback behavior
- preserved the existing global-default precedence inside unified config:
  1. explicit override
  2. environment
  3. `workflow.toml`
  4. built-in default
- froze and shipped additive provenance for resolved execution through `source_map`, `applied_scopes`, and `scope_context`
- landed the intended resolver-consumption seams instead of leaving them aspirational:
  - compile / recompile preparation in [packages/core_domain/service_lifecycle.py](../../../packages/core_domain/service_lifecycle.py)
  - orchestration planning and child-run compilation in [packages/core_domain/service_orchestration.py](../../../packages/core_domain/service_orchestration.py)
  - runtime gateway / adapter consumption in [packages/runtime_langgraph/gateway.py](../../../packages/runtime_langgraph/gateway.py), [packages/worker_adapters/langchain_agent_adapter.py](../../../packages/worker_adapters/langchain_agent_adapter.py), and [packages/worker_adapters/opencode_adapter.py](../../../packages/worker_adapters/opencode_adapter.py)
  - additive status / summary / operator projection in [packages/core_domain/service_projection.py](../../../packages/core_domain/service_projection.py)
- kept compatibility behavior explicit:
  - unresolved adapter choice still falls back honestly through compatibility routing
  - `patch_apply` compile still auto-promotes to `opencode` when mutation mode requires it and no explicit adapter override is supplied
