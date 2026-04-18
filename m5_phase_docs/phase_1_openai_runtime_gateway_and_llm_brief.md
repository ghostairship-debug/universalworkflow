# M5 Phase 1 - OpenAI Runtime Gateway And LLM Brief Baseline

**Phase status:** Completed  
**Phase position:** This phase starts after `M5 Phase 0` confirms the previous cycle is still green and freezes the new scope.

**Entry condition:** The next cycle is explicitly limited to `LLM integration + minimal TUI`, and `RuntimeGateway` is still effectively a `NullRuntimeGateway`.

---

## 1. Reassessment

Current implementation status:

- `RuntimeGateway` exists and is already the orchestrator-facing runtime boundary
- the runtime still executes through local adapters only
- no shipped surface currently proves a live LLM-backed path

Legacy/reference discipline worth preserving:

- keep the boundary anti-corrupted
- do not let service code call provider SDKs directly
- keep no-LLM execution paths valid for smoke and offline validation

Decision:

- add a real OpenAI-backed `RuntimeGateway`
- keep `NullRuntimeGateway` as the safe fallback
- make the LLM contribution visible through runtime state and generated artifacts
- preserve current no-LLM validation by making the provider opt-in

---

## 2. In Scope

- add provider-backed `RuntimeGateway` implementation for OpenAI Responses API
- enrich runtime state with execution-brief metadata
- project that brief into runtime execution artifacts
- add configuration, tests, and docs for the live-gateway path

---

## 3. Out Of Scope

- tool-calling agents
- multi-provider abstraction beyond `null` and `openai`
- replacing shell/noop adapters
- LLM-driven preset selection

---

## 4. Target Baseline

- runtime gateway can be switched between `null` and `openai`
- OpenAI-backed resume path creates a short execution brief
- shell artifact captures the brief when the live gateway is enabled
- no-LLM paths still pass unchanged when the gateway stays `null`

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Provider config + gateway implementation
2. Runtime-state / artifact projection
3. Tests, CLI/API visibility, and docs

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- the live OpenAI gateway is implemented behind the runtime boundary
- the no-LLM path remains green
- tests cover both null and live gateway behavior

---

## 7. Verification Outcome

Completed in this phase:

- added `OpenAIRuntimeGateway` behind the existing runtime boundary
- preserved `NullRuntimeGateway` as the default fallback
- projected `runtime_gateway`, `runtime_brief`, `llm_model`, and `llm_response_id` into status/detail and runtime artifacts
- added opt-in env-based gateway selection through `WORKFLOW_RUNTIME_GATEWAY`

Verification:

- `pytest tests/test_runtime_boundary.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - targeted gateway and projection coverage passed
- `pytest -q`
  - `170 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- Live OpenAI-backed execution is available behind config.
- The default no-LLM path remains the shipped baseline.
