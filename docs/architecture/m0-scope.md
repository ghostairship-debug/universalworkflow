# M0 Scope

## Goal

M0 exists to freeze the contract surface and bootstrap a local-first execution skeleton. It is the stage where the system becomes internally coherent, testable, and ready for a narrow M1 vertical spine.

## In Scope

- Freeze Wave 1 object semantics and schema v1.
- Establish preset bootstrap with manual selection only.
- Create SQLite migration, repository, and timeline foundations.
- Stand up the orchestrator API skeleton and the runtime boundary.
- Provide operator-facing CLI and smoke automation.
- Prove the control loop works without any LLM dependency.

## Out of Scope

- Web control console.
- Automatic preset classification or recommendation.
- Multi-task DAG planning.
- A second worker adapter.
- Claim, lease, or barrier as real concurrency machinery.
- Cloud deployment and multi-machine coordination.
- Rich memory, retrieval, or domain packs.
- LangGraph-first system ownership.

## Success Criteria

- Wave 1 contracts are stable and serializable.
- Presets can be seeded and must be selected manually.
- SQLite can be migrated, reset, and queried locally.
- `POST /runs` creates a run and records preset selection.
- CLI can inspect run status, timeline, and evidence.
- Smoke passes in a disconnected environment with no LLM API key set.

## Inputs

- The v2.1 project plan.
- The M0 task breakdown.
- The phase-specific execution plans.
- The Gemini and Opus evaluation reports.

## Outputs

- Governance docs and ADRs.
- Executable Python repo skeleton.
- Contracts, persistence, API, runtime boundary, worker adapter, CLI, and smoke flow.
- Freeze review output with an explicit `go` or `no-go`.

## Boundary to M1

M0 stops once the local-first skeleton is stable, reproducible, and reviewable. M1 starts when the project expands beyond bootstrap into a true vertical spine with richer runtime behavior, delayed M0 debts, and more expressive planning.
