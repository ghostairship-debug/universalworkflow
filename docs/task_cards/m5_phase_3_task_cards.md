# M5 Phase 3 Task Cards

**Phase:** `M5 Phase 3 - CLI-First Architecture Correction And OpenCode Adapter`  
**Status:** In Progress

## Scope Lock

- Keep `OpenAIRuntimeGateway`; downgrade it to fallback in architecture language, not code removal.
- Do not pull `codex`, `claude`, or `mmx` into this first correction batch.
- Make `opencode` the first GPT-capable CLI adapter.

## Task Cards

| ID | Status | Goal | Outcome |
| --- | --- | --- | --- |
| `P3-T01` | `in_progress` | Freeze the corrected `CLI-first` policy and the minimum routing contract changes | This batch has an explicit, non-destructive correction scope and a stable adapter-selection story |
| `P3-T02` | `pending` | Replace single-route overwrite with multi-route capability selection and shared CLI adapter mechanics | One capability can expose multiple routes, and the selected route is stable per compiled run |
| `P3-T03` | `pending` | Add `OpenCodeAdapter`, expose it through operator surfaces, and verify the new lane | `OpenCodeAdapter` is callable, documented, and covered without breaking shell/noop or direct API fallback |

## Exit Criteria

- capability routes show more than one route for `shell_exec`
- compile/recompile can pin an adapter
- `opencode` becomes a first-class GPT-capable adapter
- shell/noop and direct API fallback remain green

## Verification

- targeted worker/router/CLI/API tests
- full `pytest -q`
- one real `opencode` smoke run on this machine

