# M9 Phase 1 - Replay Linkage And Metrics Baseline

**Phase status:** Complete  
**Phase position:** This phase opens the feature-bearing part of `M9` after the post-`M8` rebaseline. Its job is to turn the current diagnostics surfaces into a replay-grade linkage baseline with explicit run metrics.

## Scope

- add replay-grade linkage output over timeline, state refs, attempts, claims, leases, evidence, snapshots, and review artifacts
- add first-class run metrics to operator-facing status/summary/audit surfaces
- expose the new replay/metrics surfaces through CLI and API
- add regression coverage for the new linkage and metrics outputs

## Out Of Scope

- durable checkpoint merge-policy changes beyond what is needed for linkage display
- governance alerting and dashboard automation
- `optional` review-policy runtime behavior
- distributed ownership or concurrency execution changes

## Phase Gate

This phase passes only if:

- a run can expose a coherent replay packet across its existing persisted artifacts
- status/summary/audit surfaces expose first-class run metrics
- CLI and API can project the new replay packet

## Next Reassessment

Next approved phase: `M9 Phase 2 - Durable Recovery Lineage And Reconciliation`
