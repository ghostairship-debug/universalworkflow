# P5-T02 - Retrieval Preview CLI And API Surfaces

**Status:** Completed  
**Phase:** `M6 Phase 5 - Memory Retrieval Preview And Selection Baseline`

## Goal

Expose the new retrieval preview through operator-facing surfaces.

## Scope

- add CLI retrieval-preview surface
- add API retrieval-preview surface
- support namespace and explicit item-id filters

## Verification

- CLI tests for `memory retrieve-preview`
- API tests for `GET /memory/retrieval-preview`

## Done When

- operators can inspect retrieval preview from the terminal and API
- the surface remains read-only
- selection filters are visible and test-covered
