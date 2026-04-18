# P0-T02 - Governance DB Readiness Fix

## Goal

Ensure operator-facing governance commands behave correctly on a freshly created local DB instead of assuming prior migration side effects.

## Scope

- harden governance read paths against missing schema bootstrap
- cover the regression with focused tests

## Guardrails

- keep governance surfaces read-shaped
- do not redesign reports
- do not broaden this into a release-readiness rewrite

## Verification

- focused governance / CLI tests
- direct CLI command check on a fresh DB

## Exit Signal

- `governance release-readiness` works reliably on a fresh local database

