# M6 Phase 5 Review - Memory Retrieval Preview And Selection Baseline

## Scope

`M6 Phase 5` adds the first retrieval-preview bridge over stored `memory_items` without yet injecting memory back into compile or runtime execution.

Implemented:

- `MemoryRetrievalPreview` contract
- service-side retrieval preview
- namespace and explicit item-id selection
- CLI/API/offline-validation coverage for the new preview surface

Still deferred:

- automatic memory injection into compile/resume
- semantic retrieval, ranking, or vector search
- memory item update/delete lifecycle
- simulation memory

## Verification

- `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `171 passed`
- `pytest -q`
  - `193 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

## Result

- Phase gate passed.
- The repository now has a deterministic, operator-visible retrieval-preview baseline that can be promoted into an explicit compile bridge in the next phase.
