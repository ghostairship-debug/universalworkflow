# P3-T02 - Multi-Route Registry And CLI Base

## Goal

Correct the worker layer so one capability can expose multiple adapters and the selected adapter survives later status/detail reads.

## Scope

- replace single-route overwrite in the capability registry
- add explicit adapter selection/pinning at compile time
- add a reusable CLI adapter base for subprocess-backed AI CLIs

## Guardrails

- keep `shell` and `noop` behavior stable
- avoid schema churn that requires a migration for this batch
- do not let status/detail drift when default routing changes later

## Verification

- worker-router tests
- execution-loop projection tests

## Exit Signal

- the selected capability route is stable per compiled run and multiple routes can co-exist

