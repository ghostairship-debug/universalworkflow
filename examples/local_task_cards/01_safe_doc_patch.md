# Safe doc patch

## Goal

Make one bounded documentation update and prove the active links still pass.

## Suggested contract

- write_set: `README.md`
- read_set: `docs/current_development_workflow.md`
- test_command: `python -m infra.scripts.check_doc_links`
