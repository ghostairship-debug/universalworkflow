# M4 Phase 0 Review - Run-Level Review Policy Runtime Expansion

## Scope

`M4 Phase 0` converted a narrow slice of richer review-policy semantics into real run-level runtime behavior without reintroducing legacy phase-review machinery.

Implemented:

- `recommended`
  - auto pass => `completed`
  - auto fail => `awaiting_review`
- `mandatory`
  - auto review always runs
  - human sign-off is always required

Still deferred:

- `optional` remains reference-only

## Legacy References Used

- `D:\AI Agent\tests\services\test_review_policy_routing.py`
- `D:\AI Agent\src\agentic_kernel\services\review_service.py`

Absorbed value:

- richer review-policy edge cases
- escalation-focused review semantics

Explicitly not adopted:

- legacy phase review tasks
- project-centric review-gate storage
- facade-style orchestration

## Verification

- `pytest tests/test_contracts.py tests/test_repositories.py tests/test_governance.py -q`
  - `27 passed`
- `pytest tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `124 passed`
- `pytest -q`
  - `153 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

## Result

- Phase gate passed.
- `TD-006` is now narrower: `recommended` and `mandatory` are executable, while `optional` is the remaining reference-only gap.
- The next reassessment should decide whether to finish the last `optional` policy gap or pivot to the next M4 theme.
