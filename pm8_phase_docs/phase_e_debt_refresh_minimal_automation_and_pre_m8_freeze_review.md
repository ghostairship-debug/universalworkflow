# Pre-M8 Phase E - Debt Refresh, Minimal Automation, And Pre-M8 Freeze Review

## Goal

Close the pre-`M8` hardening gate and prove the repository is ready to re-enter feature-bearing milestone work.

## Status

- Current state: `Completed`
- Depends on: `Pre-M8 Phase D`
- Next reassessment point: `M8 Phase 0 - Feature Rebaseline And Scope Freeze`

## In Scope

- refresh debt registry and retire pre-`M8` debts with explicit evidence
- add minimal automation for canonical pre-`M8` gates
- document dependency locking/versioning policy
- implement source-package hygiene/export check
- produce final pre-`M8` freeze review and `M8` entry criteria

## Out Of Scope

- new `M8` feature work
- broad CI platform expansion
- full release engineering platform rebuild

## Phase Gate

This phase closes only when:

1. the debt registry reflects the post-hardening repository reality
2. minimal automated gates exist for validation, living-doc hygiene, and source-package hygiene
3. dependency locking/version policy is explicit
4. a pre-`M8` freeze review records hard go/no-go criteria

## Risks

- source-package automation can accidentally include local state if exclusion rules are too loose
- debt retirement can overclaim if not tied back to explicit review evidence
- new automation gates can be too brittle if they overfit transient worktree noise

## Outcome Summary

- retired the remaining pre-`M8` hardening debts tied to validation modularization, context-budget guarding, governance canonicalization, dependency policy, source-package hygiene, and living-doc portability
- added minimal automation entry points for document-link checks, source-package manifest/export checks, and combined pre-`M8` gate execution
- documented dependency/version policy explicitly before re-entering `M8`
- wrote the final freeze review that approves `M8 Phase 0` as the next entry step

## Verification

- `pytest -q`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
- `python -m infra.scripts.check_doc_links`
- `python -m infra.scripts.export_source_package --dry-run`
- `python -m infra.scripts.pre_m8_gates`
