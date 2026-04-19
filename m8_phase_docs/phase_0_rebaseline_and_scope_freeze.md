# M8 Phase 0 - Rebaseline And Scope Freeze

**Phase status:** Completed  
**Entry condition:** `Pre-M8` hardening is complete and `M8` must start with an explicit rebaseline instead of direct breadth expansion.

## Scope

- freeze `Borrow / Wrap / Own`
- freeze execution lanes
- freeze canonical IDs and state-mapping rules
- freeze MCP trust tiers and server-profile policy
- freeze fallback / degradation policy
- freeze `M8` feature flags and pilot run classes

## Outputs

- `docs/adrs/ADR-M8-001.md` through `ADR-M8-009.md`
- `m8_phase_docs/phase_0_rebaseline_and_scope_freeze.md`
- `docs/task_cards/m8_phase_0_task_cards.md`
- updated `README.md`
- updated `docs/current_development_workflow.md`

## Outcome

- Opened `M8` as a real implemented phase series.
- Froze the repository's external-integration boundary before code implementation claimed new breadth.
- Locked the first pilot classes to `research_spike` and `research_spike_reviewable` while preserving `feature_delivery` on the native deterministic lane.

## Next Reassessment

Next approved phase: `M8 Phase 1 - Borrowed Agent Foundation`
