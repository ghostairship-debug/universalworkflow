# PM8-D2 - Trace And Correlation Context

## Objective

Expose a stable trace/correlation block across service projections and event/report surfaces without introducing a heavy observability stack.

## Write Set

- `packages/contracts/`
- `packages/core_domain/`
- `tests/`

## Required Outcomes

- event payloads can carry a structured `trace_context`
- status/detail, inspection, summary, audit/report, and timeline-related surfaces expose trace linkage
- CLI/API projections inherit that linkage without separate ad hoc logic

## Verification

- execution-loop tests
- CLI/API tests
