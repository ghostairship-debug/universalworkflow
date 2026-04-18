# P2-T01 - Dashboard Data Projection

## Goal

Expose recent-run and focused-run snapshots in one place so the TUI can stay thin.

## Scope

- add run-list query support
- build compact dashboard payloads from existing status/summary methods

## Guardrails

- keep business logic in the service layer
- do not build UI formatting into repositories

## Verification

- repository tests
- service projection tests

## Exit Signal

- the TUI can render from one compact dashboard payload

