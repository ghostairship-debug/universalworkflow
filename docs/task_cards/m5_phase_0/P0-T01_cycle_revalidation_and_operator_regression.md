# P0-T01 - Cycle Revalidation And Operator Regression Capture

## Goal

Re-run the shipped closeout proofs so the next cycle starts from a real, current green baseline instead of stale phase notes.

## Scope

- run `pytest -q`
- run `offline_validation --skip-offline-probe`
- run `manage.py demo`
- record any regression that appears during operator usage

## Guardrails

- do not reinterpret the previous cycle’s scope
- do not add new behavior yet
- treat discovered regressions as current work, not future debt

## Verification

- green verification commands
- revalidation evidence captured in phase notes

## Exit Signal

- the previous cycle is proved green from the current checkout

