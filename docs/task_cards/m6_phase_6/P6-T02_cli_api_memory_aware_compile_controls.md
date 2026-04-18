# P6-T02 - CLI And API Memory-Aware Compile Controls

**Status:** Completed  
**Phase:** `M6 Phase 6 - Compile-Time Memory Brief Injection Baseline`

## Goal

Expose explicit memory-item selection for compile/recompile through CLI and API.

## Scope

- add repeated `memory_item_id` controls to compile/recompile surfaces
- surface injected memory context in compile responses
- keep the interface opt-in and non-breaking

## Verification

- CLI tests cover `run compile --memory-item-id`
- API tests cover `POST /runs/{id}/compile` with `memory_item_ids`

## Done When

- operators can compile or recompile with explicit memory items
- compile responses show the resulting memory selection/brief context
- CLI/API tests cover both default and memory-aware paths
