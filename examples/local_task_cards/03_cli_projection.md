# CLI projection check

## Goal

Update a CLI read surface and keep JSON output stable for personal operator workflows.

## Suggested contract

- write_set: `apps/operator_cli/main.py`
- read_set: `tests/test_cli.py`
- test_command: `pytest -q tests/test_cli.py --run-slow --no-cov`
