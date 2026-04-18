# M5 Phase 1 Task Cards

**Phase:** `M5 Phase 1 - OpenAI Runtime Gateway And LLM Brief Baseline`  
**Status:** Completed

## Scope Lock

- Integrate one live provider only: OpenAI.
- Keep `NullRuntimeGateway` as the fallback.
- Make LLM output observable through runtime state and artifacts.

## Task Cards

| ID | Status | Goal | Outcome |
| --- | --- | --- | --- |
| `P1-T01` | `completed` | Add provider config plus an OpenAI-backed runtime gateway behind the existing boundary | `OpenAIRuntimeGateway` is available behind env-based selection without leaking provider SDK calls into `packages/core_domain` |
| `P1-T02` | `completed` | Project the generated runtime brief into state/detail and execution artifacts | `runtime_brief`, provider metadata, and model metadata now flow into status/detail and shell artifacts |
| `P1-T03` | `completed` | Document and verify the live-gateway path, including opt-in config | README, CLI/API visibility, and test coverage now explain and protect the live-gateway path |

## Exit Criteria

- OpenAI-backed gateway is available behind config
- runtime brief appears in state/artifact when enabled
- null fallback path remains green

## Verification

- `pytest tests/test_runtime_boundary.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - targeted gateway coverage passed
- `pytest -q`
  - `170 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
