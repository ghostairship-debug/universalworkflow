# PM8-D3 - Context Budget Diagnostics

## Objective

Add a lightweight, diagnostics-first preflight around runtime-brief payload assembly so live providers can see when compile/runtime context is approaching unsafe size.

## Write Set

- `packages/core_domain/`
- `packages/runtime_langgraph/gateway.py`
- `tests/`

## Required Outcomes

- compile/runtime state stores a context-budget diagnostic block
- live gateway resume path respects a conservative preflight guard
- current green paths remain within budget

## Verification

- runtime boundary tests
- execution-loop tests
