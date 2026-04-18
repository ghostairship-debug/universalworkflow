# P1-T03 - Docs And Phase Closeout

## Goal

Update repository-facing documentation so the shipped behavior matches the real M4 runtime baseline.

## Scope

- update README usage and API notes
- add phase closeout and review notes
- record next reassessment direction

## Guardrails

- document only shipped behavior
- keep the next-phase recommendation narrow

## Verification

- `pytest -q`
- `python -m infra.scripts.offline_validation --skip-offline-probe`

## Exit Signal

- docs describe the actual capability/domain-pack baseline
- phase can be closed without ambiguity
