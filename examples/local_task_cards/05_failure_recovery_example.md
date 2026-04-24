# Failure recovery example

## Goal

Exercise a failing safe-test path and produce a recovery-oriented PR-ready summary.

## Suggested contract

- write_set: `examples/local_task_cards/05_failure_recovery_example.md`
- read_set: `packages/core_domain/repo_mutation.py`
- test_command: `python -c "import sys; sys.exit(1)"`
- expected_summary: `blocked`
