# P1-T02 - Stable Projection And Operator Surfaces

## Objective

Make compile/runtime/operator surfaces reuse the stored domain-pack resolution instead of depending only on late registry recomputation.

## Scope

- store the resolved pack snapshot with compile/runtime context
- use it in:
  - compile artifact generation
  - `status-detail`
  - `summary`
  - `inspection`
  - timeline/event payload where appropriate

## Non-Goals

- dynamic pack lifecycle
- full multi-pack projection logic
- TUI mutation workflows

## Verification

- execution-loop tests for compile/resume paths
- CLI/API tests proving stable pack projection
- regression test that pack projection remains available from stored context

## Done When

- compile-time domain-pack resolution is stored and reused
- operator surfaces expose the richer pack projection consistently
