# P6-T01 - Compile Memory Brief Injection

**Status:** Completed  
**Phase:** `M6 Phase 6 - Compile-Time Memory Brief Injection Baseline`

## Goal

Inject a selected memory brief into compile context while keeping the path explicit and opt-in.

## Scope

- accept selected `memory_item_id` values at compile time
- build a retrieval brief from those items
- persist the selection/brief in task-packet and snapshot-visible context
- keep the default compile path unchanged when no memory items are provided

## Verification

- execution/service tests cover compile-time selection
- artifact content proves the brief survives into runtime execution

## Done When

- compile can optionally carry a bounded memory brief
- operator surfaces can inspect the injected selection and brief
- compile without memory selection still behaves exactly as before
