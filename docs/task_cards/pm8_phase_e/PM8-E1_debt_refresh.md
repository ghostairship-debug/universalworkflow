# PM8-E1 - Debt Refresh

## Objective

Update the debt registry so it reflects the repository after `PM8-A` through `PM8-D`.

## Required Outcomes

- retired debts moved to the repaid section with explicit evidence
- remaining open debts re-scoped if they now belong to `Next Cycle`
- freeze review references are aligned with the registry

## Result

- retired all debts intentionally scoped to pre-`M8` hardening: `TD-012`, `TD-013`, `TD-014`, `TD-015`, `TD-017`, and `TD-018`
- re-scoped `TD-007` to `Next Cycle` because trace/correlation hardening landed, but replay-grade observability did not
- aligned the canonical JSON governance source with the Markdown debt registry so runtime reporting and operator docs point at the same debt truth
