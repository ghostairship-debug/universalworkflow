# Phase 3 Task Cards

## Reassessment

- Contracts, preset rules, migrations, repositories, and event schemas are now implemented and tested.
- The next phase can stay thin:
  API create/query flows on top, compile kept internal, runtime hidden behind `RuntimeGateway`.
- No new evaluator blocker appeared after Phase 2.

## Card P3-01: Add error contract and FastAPI skeleton

- Goal:
  Create the orchestrator API with stable error responses and the required M0 routes.
- Done when:
  `POST /runs`, `GET /runs/{id}`, `GET /runs/{id}/timeline`, `GET /presets`, and `GET /tasks/{id}/evidence` are callable.

## Card P3-02: Add `RuntimeGateway` placeholder

- Goal:
  Isolate runtime semantics in `packages/runtime_langgraph/`.
- Done when:
  The orchestrator can depend on a gateway interface without importing LangGraph in contracts or core-domain.

## Card P3-03: Add thin compile v0

- Goal:
  Convert `goal + preset` into one `Phase`, one `TaskCard`, one `RuntimeTask`, and one `TaskPacket`.
- Done when:
  The compile bundle is stable and persisted through the repository layer.

## Card P3-04: Add API and boundary tests

- Goal:
  Verify route behavior, error shape, internal prepare path, and import isolation.
- Done when:
  `pytest` covers both HTTP behavior and runtime boundary constraints.
