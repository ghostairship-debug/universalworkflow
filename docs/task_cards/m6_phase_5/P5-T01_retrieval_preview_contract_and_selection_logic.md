# P5-T01 - Retrieval Preview Contract And Selection Logic

**Status:** Completed  
**Phase:** `M6 Phase 5 - Memory Retrieval Preview And Selection Baseline`

## Goal

Create one deterministic retrieval-preview baseline over stored `memory_items`, including bounded manual selection.

## Scope

- add retrieval-preview contract shape
- support selection by:
  - namespace
  - preset affinity
  - explicit `memory_item_id`
- produce a compact retrieval brief preview

## Verification

- contract round-trip tests
- service tests for preset-filtered retrieval preview
- service tests for explicit `memory_item_id` selection

## Done When

- the repository can build a read-only retrieval preview from stored memory items
- selection is deterministic and explicit
- no compile/runtime mutation is introduced
