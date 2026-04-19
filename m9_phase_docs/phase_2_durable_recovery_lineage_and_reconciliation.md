# M9 Phase 2 - Durable Recovery Lineage And Reconciliation

**Phase status:** Complete  
**Phase position:** This phase builds on the replay/metrics baseline and deepens the durable pilot from "current refs only" into explicit lineage and reconciliation-aware checkpoint semantics.

## Scope

- add durable checkpoint lineage/history to runtime state payloads and projections
- make review/terminal/cancel flows preserve durable transition metadata instead of only overwriting the latest refs
- add durable-specific inspection/reconciliation signals where lineage is missing or inconsistent
- extend regression coverage for durable lifecycle transitions

## Out Of Scope

- promotion of the durable pilot to default runtime behavior
- remote/distributed checkpoint backends
- governance alerting work
- `optional` review-policy runtime behavior

## Phase Gate

This phase passes only if:

- durable runs expose an inspectable lineage rather than only the latest refs
- reconciliation surfaces can identify missing or inconsistent durable linkage
- durable review/terminal transitions preserve checkpoint evolution consistently

## Next Reassessment

Next approved phase: `M9 Phase 3 - Governance Metrics And Alerting`
