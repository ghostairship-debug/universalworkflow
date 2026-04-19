# PM8-C1 - Service Types And Boundary Map

## Goal

Move shared service dataclasses/types out of `packages/core_domain/services.py` and define the initial decomposition boundary for the phase.

## Write Set

- `packages/core_domain/service_types.py`
- `packages/core_domain/services.py`
- `pm8_phase_docs/phase_c_service_decomposition.md`

## Verification

- targeted execution/governance tests touching `OrchestratorService`

## Done When

- shared run bundle/context dataclasses are defined outside `services.py`
- `OrchestratorService` imports those types instead of defining them inline
- the phase doc reflects the actual bounded-module split being implemented
