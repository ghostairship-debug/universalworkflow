# Architecture Notes

This directory records architecture decisions that must stay stable across milestone work. M84-M104 graph/runtime changes are historical baseline notes; new Cocos real-project work should link here when it changes state ownership, execution boundaries, or compatibility policy.

## Current Notes

| Note | Purpose |
| --- | --- |
| [LangGraph Runtime Notes](langgraph_runtime_notes.md) | Consolidates graph authority, fit matrix, boundary contract, checkpoint/repair, subgraph, and Cocos pressure-test notes from M84-M104. |

## Rules

- Architecture notes describe authority and boundaries, not only implementation details.
- New LangGraph-backed execution must preserve `OperatorActionReceipt`, `AutomationLease`, workspace root, write set, provider live proof, and evidence/operator packet semantics.
- Compatibility shims need an explicit removal milestone and a ratchet or test that keeps them thin.
