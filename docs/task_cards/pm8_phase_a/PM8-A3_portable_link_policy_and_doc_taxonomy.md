# PM8-A3 - Portable-Link Policy And Document Taxonomy

**Phase:** `Pre-M8 Phase A - Trust Recovery And Scope Freeze`  
**Status:** Completed

## Goal

Define which documents are living/current, which are historical review records, and which are reference-only. At the same time, define how living docs should link to each other without depending on local-machine absolute paths.

## Deliverables

- `docs/documentation_governance.md`
  - document taxonomy
  - canonical-doc map
  - portable-link rules for living docs

## Notes

- Historical docs are not bulk-rewritten here.
- The policy applies to newly written or newly updated living docs first.
- Absolute local paths remain acceptable in assistant responses, but repository docs should prefer portable repo-local links going forward.

## Verification

- documentation audit

## Outcome

- The repository now has a written taxonomy for current/living, active phase execution, historical review, and legacy/reference docs.
- Living-doc portability is now governed by an explicit forward-looking rule.
