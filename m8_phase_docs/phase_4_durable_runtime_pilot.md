# M8 Phase 4 - Durable Runtime Pilot

**Phase status:** Completed  
**Entry condition:** standard agent and capability projection paths are in place.

## Scope

- add a durable-runtime pilot boundary
- map `run_id` to runtime refs such as `thread_id` and `checkpoint_id`
- keep external refs diagnostics-only
- keep repository state canonical
- limit the pilot to `research_spike_reviewable`

## Outputs

- `packages/runtime_langgraph/durable_pilot.py`
- durable-ref projection in compile/resume/review flows
- diagnostics-only runtime refs in status/inspection/summary

## Outcome

- Added an opt-in durable pilot contract and LangGraph-oriented implementation boundary.
- Added repository-to-runtime ref mapping without leaking external runtime state into the public business contract.
- Verified the pilot contract and diagnostics path with repository-local test doubles and feature-flag coverage.

## Next Reassessment

Next approved phase: `M8 Phase 5 - Agent Skills Alignment`
