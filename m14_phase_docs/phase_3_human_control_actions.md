# M14 Phase 3 - Human Control Actions

Status: complete

## Goal

Let the Web operator surface perform the existing lifecycle actions directly while keeping the service/API semantics canonical.

## Completed Outputs

- Web action routes for `resume`, `approve`, `reject`, `reconcile`, `cancel`, and `batch-resume`
- redirect-with-notice pattern for action feedback
- human-review flows preserved for `human_required`, `mandatory`, and recommended-fail escalation

## Verification

- `tests/test_web_ui.py`
- `tests/test_api.py`

## Next Phase

- `M14 Phase 4 - Governance, Config, And UX Hardening`
