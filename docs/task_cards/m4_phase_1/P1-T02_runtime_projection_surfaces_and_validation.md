# P1-T02 - Runtime Projection Surfaces And Validation

## Goal

Expose capability and domain-pack resolution through operator surfaces and acceptance tooling so the `M4 Smoke` gate can be proven mechanically.

## Scope

- add service projections for selected domain pack and capability route
- add CLI commands:
  - `domain-pack list`
  - `capability list`
- add API endpoints:
  - `GET /domain-packs`
  - `GET /capability-routes`
- update smoke and offline validation assertions

## Guardrails

- do not add a new governance subsystem for domain packs
- keep outputs lightweight and machine-readable

## Verification

- CLI tests
- API tests
- offline validation

## Exit Signal

- operator surfaces show the selected domain pack and capability route
- smoke and validation prove both shell and noop baselines
