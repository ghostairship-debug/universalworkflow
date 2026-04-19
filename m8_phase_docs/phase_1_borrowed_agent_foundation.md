# M8 Phase 1 - Borrowed Agent Foundation

**Phase status:** Completed  
**Entry condition:** `M8` scope, lane policy, and fallback rules are frozen.

## Scope

- introduce `ExecutionLaneType`
- add a standard borrowed agent lane
- add read-only built-in agent tools
- make `research_spike_reviewable` the first agent-lane preset path
- project execution lane and tool manifest into compile/runtime surfaces

## Outputs

- `packages/contracts/models.py`
- `packages/core_domain/agent_tools.py`
- `packages/worker_adapters/langchain_agent_adapter.py`
- compile/status/API/CLI execution-lane projections

## Outcome

- Added a standard agent lane through `LangChainAgentAdapter`.
- Added built-in read-only agent tools for safe workspace inspection and execution-brief access.
- Added execution-lane projection so compile/resume/status surfaces expose which lane is in use.
- Kept the native deterministic lane unchanged for `feature_delivery`.

## Next Reassessment

Next approved phase: `M8 Phase 2 - MCP Capability Pilot`
