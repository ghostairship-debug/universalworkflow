# M5 Phase 3 - CLI-First Architecture Correction And OpenCode Adapter

**Phase status:** Completed (exploratory implementation after the frozen `M5 Phase 0-2` scope)  
**Phase position:** This phase starts after `M5 Phase 2` proves the current cycle can validate, attach a live direct-API gateway, and render a minimal TUI. It corrects the execution architecture back toward the original `CLI-first` design without rolling back the already-green fallback path.

**Entry condition:** `OpenAIRuntimeGateway` exists as a live path, but worker execution is still effectively `shell/noop` only and the capability registry still models one adapter per capability.

**Scope note:** This phase was originally outside the frozen `M5` baseline, but it later landed as a real implementation lane and now reflects current repository behavior.

---

## 1. Reassessment

Current implementation status:

- the repository already has a useful `direct_api` baseline through `OpenAIRuntimeGateway`
- the worker layer already has `WorkerRouter + CapabilityRegistry`, but it still assumes one route per capability
- the original project plan explicitly wanted `CLI adapter -> MCP adapter -> direct API fallback`, not `direct API first`

Local environment facts that matter now:

- `opencode run --format json --pure` is available and works non-interactively on this machine
- `opencode` is already authenticated with `OpenAI oauth`
- `codex` is installed but not currently callable as a stable subprocess target in this shell

Legacy/reference discipline worth preserving:

- keep the direct API path as a fallback instead of deleting a green baseline
- avoid importing legacy monolithic facade patterns
- prefer a shared CLI execution shell plus thin provider-specific adapters

Decision:

- do not roll back `OpenAIRuntimeGateway`
- correct the worker architecture so one capability can expose multiple routes
- add explicit adapter selection at compile/recompile time
- ship `OpenCodeAdapter` as the first GPT-capable CLI adapter
- treat `OpenAIRuntimeGateway` as fallback/live-provider baseline, not the primary execution story

---

## 2. In Scope

- freeze the corrected `CLI-first` execution policy for the current repository
- change capability routing from single-route overwrite to multi-route selection
- add a reusable CLI adapter base
- add `OpenCodeAdapter`
- expose adapter choice through compile/recompile, status/detail, CLI, API, and docs

---

## 3. Out Of Scope

- `CodexCliAdapter`
- `ClaudeAdapter`
- `MMXAdapter`
- MCP adapter integration
- replacing `OpenAIRuntimeGateway`
- changing shipped offline smoke to depend on a live CLI provider

---

## 4. Target Baseline

- one capability can advertise multiple adapters without silent overwrite
- the selected adapter for a run is frozen at compile time and remains visible later
- `OpenCodeAdapter` can execute a minimal artifact-writing task through `opencode run`
- direct API remains available, but the architecture narrative is now `CLI-first / API-fallback`

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Route and contract freeze for `CLI-first`
2. Multi-route registry plus shared CLI execution base
3. `OpenCodeAdapter` integration, surfaces, docs, and verification

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- capability routing no longer silently collapses multiple adapters into one route
- compile/recompile can pin a chosen adapter for a run
- `OpenCodeAdapter` is available as a first-class route
- existing shell/noop behavior remains green
- the direct API path still works as fallback

---

## 7. Realized Outcome

- The repository regains its intended execution shape: `CLI-first` routing with explicit adapter selection.
- `OpenCodeAdapter` becomes the first GPT-capable CLI route.
- `OpenAIRuntimeGateway` remains useful, but is no longer the only live-model story.

Concrete repository evidence:

- `packages/worker_adapters/router.py` now wires `ShellAdapter`, `OpenCodeAdapter`, and `NoopAdapter`
- compile/recompile surfaces accept explicit adapter pinning
- CLI/API/operator projections expose the selected capability route
- adapter-selection behavior is covered in execution, CLI, and API tests
