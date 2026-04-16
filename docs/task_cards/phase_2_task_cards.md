# Phase 2 Task Cards

## Reassessment

- Phase 1 contracts, presets, and manual resolver are now executable and tested.
- Pydantic v2 is confirmed, so `extra="allow"` is implemented with `ConfigDict`.
- The next critical dependency is persistence: all later phases need a stable SQLite and repository layer.

## Card P2-01: Build SQLite migration scaffold

- Source refs:
  `m0_phase_docs/phase_2_persistence_and_timeline_foundation.md`
- Goal:
  Create the initial schema, migration runner, and reset path.
- Done when:
  A fresh database can be migrated repeatedly and WAL is enabled.

## Card P2-02: Implement repository layer

- Goal:
  Add repository classes for runs, presets, tasks, evidence, review, and events.
- Done when:
  Upper layers no longer need direct SQL for M0 CRUD paths.

## Card P2-03: Lock `run_events` payload schemas and timeline query

- Goal:
  Validate the ten M0 event types and expose a time-ordered timeline query.
- Done when:
  Timeline returns summary-first events without storing large stdout or stderr payloads.

## Card P2-04: Add persistence tests

- Goal:
  Verify migration, WAL, seed loading, repository round-trips, and timeline order.
- Done when:
  `pytest` covers database initialization and repository behavior.
