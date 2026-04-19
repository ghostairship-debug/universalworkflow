# PM8 Phase E Task Cards

## Phase Intent

`PM8-E` closes the hardening gate by refreshing debt truth, automating the smallest trustworthy acceptance checks, and producing the freeze review that defines `M8` entry.

## Task Order

| Task | Status | Complexity | Objective | Depends On | Primary Write Set | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| `PM8-E1` | `completed` | `medium` | Refresh and retire debt entries with explicit evidence | `PM8-D complete` | `docs/tech-debt-registry.md`, `docs/reviews/` | governance tests |
| `PM8-E2` | `completed` | `complex` | Add minimal automated gates for validation, docs-link hygiene, and source-package hygiene/export | `PM8-D complete` | `infra/scripts/`, `infra/validation/`, `Makefile`, `README.md`, `tests/` | targeted tests + gate dry run |
| `PM8-E3` | `completed` | `small` | Document dependency lock/versioning strategy | `PM8-E2` | `docs/`, `pyproject.toml` if needed | docs review |
| `PM8-E4` | `completed` | `medium` | Produce the final pre-M8 freeze review with explicit `M8` entry criteria | `PM8-E1`, `PM8-E2`, `PM8-E3` | `docs/reviews/`, `pm8_phase_docs/`, `docs/current_development_workflow.md`, `README.md` | full `pytest` + offline validation + freeze review |

## Closeout Requirements

- all phase E tasks marked completed with evidence
- living docs show pre-M8 complete and point to the next approved milestone entry work
- `docs/reviews/pre-m8-freeze-review.md` exists and declares go/no-go criteria for `M8`

## Closeout

- `PM8-E1` completed: the debt registry now retires all debts intentionally scoped to pre-`M8` hardening and leaves only next-cycle debt open.
- `PM8-E2` completed: doc-link hygiene, source-package manifest/export, and combined `pre_m8_gates` automation are now repository-native scripts with passing tests.
- `PM8-E3` completed: dependency/version policy is explicit in `docs/dependency_locking_policy.md`, and core runtime bounds were widened selectively rather than by blanket loosening.
- `PM8-E4` completed: `docs/reviews/pre-m8-freeze-review.md` declares the gate `GO` for `M8 Phase 0`, while preserving the requirement for a new scope freeze before fresh breadth lands.
