# P3-T03 - OpenCode Adapter And Surfaces

## Goal

Add `OpenCodeAdapter` as the first GPT-capable CLI route and expose it through the existing operator surfaces.

## Scope

- add a non-interactive `opencode run` backed adapter
- add CLI/API compile-time adapter selection
- update docs and verification for the new route

## Guardrails

- do not rely on live `opencode` in unit tests
- keep direct API and local shell paths valid
- keep the adapter narrowly scoped to the current artifact-writing baseline

## Verification

- fake-runner adapter tests
- CLI/API route-selection tests
- one real local `opencode` smoke run

## Exit Signal

- a run can be compiled and executed via `OpenCodeAdapter`, and the chosen route is visible in status/detail
