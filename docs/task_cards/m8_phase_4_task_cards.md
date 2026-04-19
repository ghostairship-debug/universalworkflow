# M8 Phase 4 Task Cards

| Task | Size | Goal | Primary Files | Done When |
| --- | --- | --- | --- | --- |
| `M8-4A` | `medium` | Add durable pilot interface and flag-controlled builder | `packages/runtime_langgraph/durable_pilot.py` | pilot boundary exists |
| `M8-4B` | `medium` | Map durable refs into compile/resume/review flows | `service_lifecycle.py`, `services.py` | runtime refs are captured and checkpointed |
| `M8-4C` | `small` | Keep durable refs diagnostics-only | `service_projection.py` | product state stays canonical and refs stay diagnostic |

## Closeout

- The durable pilot path is now visible and testable without making external runtime state the business contract.
