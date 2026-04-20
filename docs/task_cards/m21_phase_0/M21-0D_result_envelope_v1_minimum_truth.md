# M21-0D ResultEnvelope v1 Minimum Truth

Status: completed

## Goal

Land a minimum internal `ResultEnvelope v1` so operator-facing reports stop depending only on free-form markdown artifacts and raw execution blobs.

## Acceptance Criteria

- `ResultEnvelope v1` contract exists with `summary`, `raw_ref`, `artifacts`, `verification`, and `provenance`
- `mutations`, `usage`, and `confidence` are reserved as optional fields
- evidence, audit-report, and mutation-report expose the envelope additively
- existing evidence/raw execution storage remains backward compatible

## Evidence

- contracts and builder updates in `packages/contracts/models.py` and `packages/core_domain/evidence_builder.py`
- additive projection updates in `packages/core_domain/service_projection.py`
- regression coverage in CLI/API/execution tests

## Result

- completed in the first `M21 Phase 0` implementation slice
