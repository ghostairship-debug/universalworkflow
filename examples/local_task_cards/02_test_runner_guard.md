# Test runner guard

## Goal

Adjust repo mutation test runner behavior without leaking secrets or using shell metacharacters.

## Suggested contract

- write_set: `packages/core_domain/repo_mutation.py`
- read_set: `tests/test_execution_loop.py`
- test_command: `pytest -q tests/test_execution_loop.py --no-cov`
