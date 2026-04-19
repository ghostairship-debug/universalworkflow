# M8 Phase 1 Task Cards

| Task | Size | Goal | Primary Files | Done When |
| --- | --- | --- | --- | --- |
| `M8-1A` | `medium` | Add lane and manifest contracts | `packages/contracts/models.py`, `packages/contracts/__init__.py` | execution-lane and projection contracts exist |
| `M8-1B` | `medium` | Add built-in read-only agent tools | `packages/core_domain/agent_tools.py` | safe built-in tool set exists |
| `M8-1C` | `medium` | Add borrowed agent adapter | `packages/worker_adapters/langchain_agent_adapter.py` | standard agent lane exists behind flags |
| `M8-1D` | `small` | Project lane/manifests into compile and status surfaces | `compile.py`, `services.py`, CLI/API` | operator surfaces show lane/projection metadata |

## Closeout

- `research_spike_reviewable` now defaults into the borrowed agent lane when the lane is enabled.
