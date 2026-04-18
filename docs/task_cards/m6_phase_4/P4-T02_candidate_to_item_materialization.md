# P4-T02 - Candidate To Item Materialization

**Status:** Completed  
**Phase:** `M6 Phase 4 - Persistent Memory Item Baseline`

## Goal

Create one bounded materialization path from selected run memory candidates to stored memory items.

## Scope

- make run memory candidate IDs stable across repeated reads
- add `materialize_run_memory_candidate(run_id, candidate_id)`
- persist selected candidate content into `memory_items`
- append timeline evidence for materialization
- keep the flow bounded and idempotent

## Primary Files

- `packages/core_domain/services.py`
- `packages/contracts/events.py`
- `tests/test_execution_loop.py`

## Verification

- service tests prove candidate IDs are stable
- service tests prove a selected candidate becomes a stored memory item
- repeated materialization of the same candidate returns the same stored item
- run timeline includes `memory_item_materialized`

## Done When

- a selected candidate can be turned into a durable `MemoryItem`
- the path is explicit and operator-triggered
- the repository has audit-visible proof that materialization happened
