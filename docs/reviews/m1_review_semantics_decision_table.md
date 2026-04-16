# M1 Review Semantics Decision Table

## Goal

Freeze the current M1 review projection semantics before any richer review policy expansion.

## Cases

| Path | Latest Verdict | Effective Review State |
| --- | --- | --- |
| `auto_only` run completed successfully | auto pass | `auto_passed` |
| `auto_only` run completed with failing review | auto fail | `auto_failed` |
| `human_required` run waiting for operator decision | none | `human_pending` |
| `human_required` run approved by operator | human pass | `human_approved` |
| `human_required` run rejected by operator | human fail | `human_rejected` |
| no review has happened and no review is requested | none | `not_requested` |

## Notes

- The current table is projection-only.
- It does not yet introduce richer `optional / recommended / mandatory` policy enums.
- Any future expansion should preserve the current states as backward-compatible operator-facing values.
