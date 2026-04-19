# PM8-D5 - Governance Structured Sources

## Objective

Replace Markdown-first runtime parsing with structured canonical governance sources while keeping Markdown compatibility for overrides and tests.

## Write Set

- `docs/governance/`
- `packages/core_domain/governance.py`
- `tests/test_governance.py`

## Required Outcomes

- canonical JSON governance sources exist for tech debt and review policy cases
- governance builders prefer structured sources by default
- Markdown input still works as a compatibility path for explicit overrides/tests

## Verification

- governance tests
- CLI/API governance surfaces
