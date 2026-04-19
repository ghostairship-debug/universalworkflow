# M8 Phase 3 Task Cards

| Task | Size | Goal | Primary Files | Done When |
| --- | --- | --- | --- | --- |
| `M8-3A` | `medium` | Add OTel-first exporter abstraction | `packages/core_domain/observability.py` | null/memory/Langfuse exporters exist |
| `M8-3B` | `small` | Extend trace context/correlation IDs | contracts + service projection | traces carry run/review/runtime correlation |
| `M8-3C` | `small` | Keep local projections authoritative | service projections | status/audit remain usable without sink |

## Closeout

- Trace export is now optional and failure-isolated, while local operator views remain canonical.
