# M8 Phase 3 - Observability Abstraction And First Sink

**Phase status:** Completed  
**Entry condition:** agent and capability planes can emit stable run/lane/projection identifiers.

## Scope

- add OTel-first trace-export abstraction
- add correlation fields for run/review/runtime/tool/thread/checkpoint context
- implement null, memory, and Langfuse exporters
- expose exporter diagnostics in operator projections

## Outputs

- `packages/core_domain/observability.py`
- `TraceContext` extensions in contracts
- trace exporter diagnostics in status/inspection/summary/audit-report

## Outcome

- External trace export is now an optional substrate rather than a built-in operator dependency.
- Local operator projections remain authoritative.
- Trace failures are isolated from run outcomes.

## Next Reassessment

Next approved phase: `M8 Phase 4 - Durable Runtime Pilot`
