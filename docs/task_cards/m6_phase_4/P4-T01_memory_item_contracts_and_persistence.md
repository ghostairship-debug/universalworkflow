# P4-T01 - Memory Item Contracts And Persistence Baseline

**Status:** Completed  
**Phase:** `M6 Phase 4 - Persistent Memory Item Baseline`

## Goal

Add the first durable `MemoryItem` contract and SQLite persistence layer so memory can move beyond read-only candidate projection.

## Scope

- add `MemoryItem` contract and exports
- add SQLite migration for `memory_items`
- add repository methods for create/get/list/by-run/by-namespace
- prove deduplicated persistence by `source_candidate_id`

## Primary Files

- `packages/contracts/models.py`
- `packages/contracts/__init__.py`
- `infra/migrations/008_m6_memory_items.sql`
- `packages/core_domain/repositories.py`
- `tests/test_contracts.py`
- `tests/test_repositories.py`

## Verification

- contract round-trip tests
- repository round-trip tests
- migration test includes `008_m6_memory_items.sql`

## Done When

- `MemoryItem` is a first-class persisted contract
- `memory_items` table exists and migrates cleanly
- repository can durably store and query memory items
- repeated create calls for the same `source_candidate_id` are idempotent
