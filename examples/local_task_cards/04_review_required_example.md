# Review-required example

## Goal

Create a deliberately review-gated change where evidence should be inspected before acceptance.

## Suggested contract

- write_set: `docs/current_development_workflow.md`
- read_set: `docs/milestone_history.md`
- test_command: `python -m infra.scripts.check_doc_links`
- review_policy: `human_required`
