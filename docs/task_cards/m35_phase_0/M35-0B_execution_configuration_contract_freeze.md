# M35-0B Execution Configuration Contract Freeze

Status: completed

## Goal

Freeze the additive execution-configuration contract across the shipped role/profile/cluster surfaces without yet shipping the full execution-profile implementation.

## Acceptance

- introduce one reusable additive execution-configuration contract model for scope-level overrides
- attach that contract additively, not destructively, to the shipped scope objects that will own execution defaults:
  - `PresetDefinition`
  - `AgentProfileDefinition`
  - `ExecutionClusterTemplate`
  - `ClusterMemberSpec`
- keep global defaults inside the existing unified config system rather than persisting a second root config object
- freeze the minimum field set for the reusable execution-configuration contract:
  - `adapter_name`
  - `runtime_gateway_provider`
  - `model`
  - `model_variant`
  - `reasoning_effort`
  - `worker_pool_id`
- keep `review_policy` as the existing sibling decision surface rather than making execution profiles a second review-policy authority
- preserve the current interaction/run/governance/Web public route set unchanged
- preserve the current `execution_profile` read-model family as the only public projection family; do not create a parallel execution packet surface
- document the frozen contract in the active phase materials before later phases begin implementation

## Notes

- current helper-driven adapter defaults such as cluster-member preferred/fallback adapter logic remain compatibility behavior until later `M35` phases move them behind the frozen contract
- do not implement the full authoritative resolver here beyond what is required to make the contract unambiguous
- do not open `TD-STRUCT-006` promotion work here

## Result

- added reusable additive execution-profile contract models in [packages/contracts/models.py](../../../packages/contracts/models.py):
  - `ExecutionProfileDefinition`
  - `ExecutionScopeContext`
  - `ResolvedExecutionProfile`
- attached `execution_profile` additively to the shipped scope objects that now own execution defaults:
  - `PresetDefinition`
  - `AgentProfileDefinition`
  - `GeneratedAgentProfile`
  - `ExecutionClusterTemplate`
  - `ClusterMemberSpec`
- extended orchestration-side contracts additively so the same family can carry resolved execution and scope context through planning and read models:
  - `RoleAssignment`
  - `OrchestrationStep`
  - `OrchestrationGraphNode`
- kept global defaults inside the existing unified config chain and exposed them additively as `execution_defaults` in [packages/core_domain/config.py](../../../packages/core_domain/config.py)
- preserved review-policy separation and all current CLI/API/Web routes while freezing the field family around adapter, model, variant, reasoning effort, runtime gateway, and worker-pool choices
