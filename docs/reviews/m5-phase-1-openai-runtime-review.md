# M5 Phase 1 Review - OpenAI Runtime Gateway And LLM Brief Baseline

## Scope

`M5 Phase 1` turns the placeholder runtime boundary into an opt-in live provider path without breaking the no-LLM baseline.

Implemented:

- added `OpenAIRuntimeGateway` behind `RuntimeGateway`
- preserved `NullRuntimeGateway` as the default fallback
- projected live gateway metadata and `runtime_brief` into runtime state, status/detail, and shell artifacts
- documented env-based activation through `WORKFLOW_RUNTIME_GATEWAY=openai`

Explicitly not adopted:

- multi-provider expansion beyond `null` and `openai`
- tool-calling agent orchestration
- any removal of the no-LLM smoke path

## Verification

- `pytest tests/test_runtime_boundary.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - targeted gateway coverage passed
- `pytest -q`
  - `170 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

## Result

- Phase gate passed.
- Live LLM integration now exists behind config.
- Offline and no-LLM paths remain the default supported baseline.
