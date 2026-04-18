# P1-T01 - OpenAI Runtime Gateway

## Goal

Replace the placeholder-only runtime boundary with a real OpenAI-backed implementation while preserving the existing `NullRuntimeGateway`.

## Scope

- add provider selection/config
- implement an OpenAI Responses API backed gateway
- keep the interface orchestrator-facing only

## Guardrails

- do not import provider SDKs into `packages/core_domain`
- do not remove the null fallback
- do not turn this into a multi-provider framework

## Verification

- runtime-boundary tests
- gateway unit tests with a fake client

## Exit Signal

- the runtime boundary can run with either `null` or `openai`

