# PM8-E2 - Minimal Automation And Source Hygiene

## Objective

Add the smallest reliable automation gates needed to trust a pre-`M8` handoff.

## Required Outcomes

- docs-link hygiene check for living docs
- source-package export or hygiene check that excludes local state/artifacts
- runnable pre-`M8` gate entry point

## Verification

- targeted tests
- gate dry run

## Result

- added `python -m infra.scripts.check_doc_links`
- added `python -m infra.scripts.export_source_package --dry-run`
- added `python -m infra.scripts.pre_m8_gates`
- extended the living-doc check to cover the active dependency policy and the controlling pre-`M8` freeze review
