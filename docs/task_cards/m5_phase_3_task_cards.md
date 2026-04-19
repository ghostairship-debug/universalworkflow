# M5 Phase 3 Task Cards

**Phase:** `M5 Phase 3 - CLI-First Architecture Correction And OpenCode Adapter`  
**Status:** Completed (exploratory implementation outside the frozen `M5 Phase 0-2` scope)

## Historical Scope Note

- This phase was not part of the original frozen `M5` baseline.
- It later landed as an exploratory but real implementation lane and now matches the repository's current execution reality.
- Read it as implemented architecture correction, not as unfinished work.

## Scope Lock

- Keep `OpenAIRuntimeGateway`; downgrade it to fallback in architecture language, not code removal.
- Do not pull `codex`, `claude`, or `mmx` into this first correction batch.
- Make `opencode` the first GPT-capable CLI adapter.

## Task Cards

| ID | Status | Goal | Outcome |
| --- | --- | --- | --- |
| `P3-T01` | `completed` | Freeze the corrected `CLI-first` policy and the minimum routing contract changes | The repository now has an explicit CLI-first / direct-API-fallback execution story |
| `P3-T02` | `completed` | Replace single-route overwrite with multi-route capability selection and shared CLI adapter mechanics | One capability can expose multiple routes, and the selected route is stable per compiled run |
| `P3-T03` | `completed` | Add `OpenCodeAdapter`, expose it through operator surfaces, and verify the new lane | `OpenCodeAdapter` is callable, documented, and covered without breaking shell/noop or direct API fallback |

## Exit Criteria

- capability routes show more than one route for `shell_exec`
- compile/recompile can pin an adapter
- `opencode` becomes a first-class GPT-capable adapter
- shell/noop and direct API fallback remain green

## Verification

- `tests/test_execution_loop.py` covers pinned-route compile behavior and fake-runner `OpenCodeAdapter` execution
- `tests/test_cli.py` and `tests/test_api.py` cover adapter selection and capability-route visibility
- `packages/worker_adapters/router.py` now exposes `shell`, `opencode`, and `noop` as concrete routes
