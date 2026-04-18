# P3-T01 - CLI-First Policy Freeze

## Goal

Freeze the correction scope so this batch restores the intended routing policy without destabilizing the already-green runtime.

## Scope

- document `CLI-first / direct API fallback`
- define how adapter choice is pinned per compiled run
- define the first-batch adapter order

## Guardrails

- do not delete `OpenAIRuntimeGateway`
- do not make `codex` a blocker for this phase
- do not turn this into a broad multi-provider refactor

## Verification

- phase doc
- task-card index

## Exit Signal

- the correction boundary is explicit and the first implementation batch is frozen

