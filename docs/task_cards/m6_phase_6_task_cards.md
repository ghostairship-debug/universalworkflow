# M6 Phase 6 Task Cards

**Phase:** `M6 Phase 6 - Compile-Time Memory Brief Injection Baseline`  
**Goal:** Turn retrieval preview into one explicit, opt-in compile-time memory bridge while keeping the default runtime path unchanged.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P6-T01` | `complex` | Inject selected memory brief into compile context and project it through snapshots/status surfaces | `Phase 6 entry` | `packages/core_domain/compile.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py` | service/execution tests | compile can optionally carry a memory brief |
| `P6-T02` | `complex` | Add explicit compile/recompile controls for memory item selection through CLI/API | `P6-T01` | `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_api.py`, `tests/test_cli.py` | CLI/API tests | operators can opt into memory-aware compile without changing defaults |
| `P6-T03` | `medium` | Update docs/offline validation and close the phase | `P6-T01`, `P6-T02` | `infra/scripts/offline_validation.py`, `README.md`, `m6_phase_docs/*` | offline validation + docs review | memory-brief injection is documented and validated end-to-end |

## Closeout

- `P6-T01` completed: selected memory items now inject a bounded memory brief into compile context and artifacts.
- `P6-T02` completed: CLI/API compile surfaces support explicit `memory_item_id` selection without changing defaults.
- `P6-T03` completed: docs and offline validation now prove the memory-aware compile bridge end-to-end.
