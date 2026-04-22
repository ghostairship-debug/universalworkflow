# M33-0B Orchestration Substrate Contraction

Status: active

## Goal

Reduce the remaining `project_delivery`-shaped assumptions in orchestration execution so more of the runtime can rely on a genuinely shared substrate rather than preset-specific branching.

## Acceptance

- identify the current orchestration points that still assume a `project_delivery`-style flow
- extract or contract those assumptions behind a more shared orchestration path
- preserve shipped compatibility for `project_delivery`, `guarded_project_delivery`, and `DevCluster`
- avoid introducing any new `*_delivery` service special path
- update regression coverage and closeout evidence for the contracted path

## Notes

- changes here must be bug-first and compatibility-first
- if a contraction attempt exposes a real regression, repair it before widening the refactor
