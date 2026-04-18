# M1 Review Semantics Decision Table

## Goal

Freeze the current M1 review projection semantics before any richer review policy expansion.

## Cases

| Path | Latest Verdict | Effective Review State |
| --- | --- | --- |
| `auto_only` run completed successfully | auto pass | `auto_passed` |
| `auto_only` run completed with failing review | auto fail | `auto_failed` |
| `recommended` run completed after auto pass | auto pass | `auto_passed` |
| `recommended` run escalated after auto fail and is waiting for operator decision | auto fail | `human_pending` |
| `recommended` run escalated after auto fail and is approved by operator | human pass | `human_approved` |
| `recommended` run escalated after auto fail and is rejected by operator | human fail | `human_rejected` |
| `human_required` run waiting for operator decision | none | `human_pending` |
| `human_required` run approved by operator | human pass | `human_approved` |
| `human_required` run rejected by operator | human fail | `human_rejected` |
| `mandatory` run is waiting for operator decision after auto pass | auto pass | `human_pending` |
| `mandatory` run is waiting for operator decision after auto fail | auto fail | `human_pending` |
| `mandatory` run approved by operator | human pass | `human_approved` |
| `mandatory` run rejected by operator | human fail | `human_rejected` |
| no review has happened and no review is requested | none | `not_requested` |

## Notes

- The current table remains operator-facing and backward-compatible even after runtime policy growth.
- `recommended` and `mandatory` are now executable run-level policies.
- `optional` remains reference-only because the current run model does not yet expose a clean advisory-only terminal shape.
- Any future expansion should preserve the current states as backward-compatible operator-facing values.
- `M3 Phase 4` governance surfaces and `M4 Phase 0` runtime policy expansion consume this table as a canonical operator-facing baseline; expanding policy semantics should update this table first.
