# M21-0B Control-Plane Boundary Hardening

Status: completed

## Goal

Reduce short-term boundary risk around composition, compile/recompile preparation, and capability/worker seams while preserving `OrchestratorService` as the public facade.

## Acceptance Criteria

- a bounded seam is extracted or documented for composition/bootstrap responsibilities
- compile/recompile shared preparation work stops diverging further
- any public CLI/API behavior changes remain backward compatible

## Evidence

- shared compile/recompile preparation persistence extracted in `packages/core_domain/service_lifecycle.py`
- orchestration plan graph compile context now lands without facade breakage
- regression coverage proved compile/recompile and operator projections stayed backward compatible

## Result

- compile/recompile now share a bounded prepared-run persistence path instead of duplicating setup logic
- orchestration plan graph context was added as an internal additive projection without breaking existing CLI/API behavior
