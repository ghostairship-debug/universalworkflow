# M36 Phase 0: Workbench IA And Capability Slot Freeze

Status: completed
Opened: 2026-04-24
Closed: 2026-04-24
Baseline: accepted `M35`

## Purpose

Open `M36` honestly through a bounded `Phase 0` that freezes the workbench information architecture, freezes the interaction/workbench surface map, and freezes where external capabilities should plug into the repository before broader `M36` workbench productization begins.

This phase also lands the minimum bounded capability pilots that unblock later workbench design:

- `Codex CLI` as an additive coding adapter
- MiniMax MCP `web_search` and `understand_image` as additive research/tooling capability slots

## Why This Phase Exists

Accepted `M35` made execution selection explicit and explainable, but the repository still needed one honest opening slice before deeper workbench breadth:

- the current `/ui/workbench` remained a minimum preview instead of a coherent product workbench
- the repository had no frozen answer for where stronger coding, search, or image-understanding capabilities should attach
- integrating external capabilities before freezing the workbench slot boundaries would have risked creating parallel surfaces instead of one product path

The next safe bounded step was therefore to open `M36 Phase 0`, freeze the workbench IA and capability-slot rules, and land only the minimum additive pilots needed to support later `M36` execution.

## Scope

This phase includes:

- `M36-0A` opening, truth alignment, and workflow-orchestration freeze
- `M36-0B` workbench IA and surface freeze
- `M36-0C` bounded external capability-slot freeze with additive `Codex CLI` and MiniMax MCP pilots
- `M36-0D` validation, closeout, and honest carry-forward judgment

This phase explicitly does not include:

- shipping the full `M36 Phase 1` conversational workbench flow
- replacing the current workbench/operator route families
- broader capability-ecosystem productization
- `MMX CLI` integration
- `gcloud` / Vertex AI integration
- automation-plane breadth
- full `TD-STRUCT-005` telemetry closure
- general `TD-STRUCT-006` promotion machinery
- public route, packet, or contract breaking renames

## Execution Model

Development for this phase uses the existing workflow surfaces as the bounded execution plane.

Rules:

- active phase work should use a workspace-scoped DB label such as `m36_phase0`
- phase kickoff should begin with an `interaction` session
- the default implementation path uses `project_delivery` with `dev_cluster`
- design, risk, and evidence tasks may use `research_spike_reviewable` with `research_cluster`
- every detailed task card maps to exactly one workflow run
- every mutating run must carry `task_card_ref`, `task_card_path`, bounded `write_set`, bounded `read_set`, explicit `test_command` values, bounded `max_fix_iterations`, and `mutation_mode` only when repo mutation is intended
- review gates stay explicit through `run approve` / `run reject` or the Web review surface
- rejected work continues through `interaction followup` against the same session/card path rather than through free-form replacement runs
- every completed card must record real evidence back into the task card, including at least a `run summary`, `operator-view` or `audit-report`, and the validation commands actually used

## Workstreams

### Workstream A: Phase Opening And Truth Alignment

- open `M36 Phase 0` formally
- point the workflow guide, README, root planning docs, and roadmap at an accepted `M36 Phase 0` baseline
- preserve `M35` as the latest completed milestone while making `M36 Phase 0` the latest accepted bounded freeze
- keep `TD-STRUCT-005` and `TD-STRUCT-006` deferred

### Workstream B: Workbench IA And Surface Freeze

- freeze the workbench information architecture
- freeze the separation between operator surfaces and future product workbench surfaces
- freeze the rule that `M36 Phase 0` only lands bounded workbench-facing seams, not the full conversational shell

### Workstream C: Capability Slot Freeze And Bounded Pilots

- freeze where external coding and research capabilities should attach
- land `Codex CLI` as an additive coding adapter behind the existing execution-profile and worker-router seams
- land MiniMax MCP `web_search` and `understand_image` as additive bounded capability profiles behind the existing MCP/capability plane
- keep `MMX CLI` and `gcloud` / Vertex AI deferred until a later bounded phase needs them honestly

### Workstream D: Validation And Closeout

- validate that the bounded capability pilots do not regress current CLI/API/workflow/governance behavior
- dogfood one `dev_cluster` path and one `research_cluster` path through the workflow
- close the phase with explicit debt judgment and a freeze review

## Entry Criteria

To remain in-bounds, the phase preserves these assumptions:

- accepted `M35` remains the latest completed milestone baseline
- the additive `execution_profile` family and execution-resolution trace shipped by `M35` remain the only execution truth family
- `Codex CLI` must attach through existing adapter and execution-profile seams rather than through a replacement runtime stack
- MiniMax search/image-understanding capability pilots must attach through the existing MCP/capability plane rather than through a parallel workbench back end
- `MMX CLI`, `gcloud` / Vertex AI, automation breadth, and broader capability productization remain unopened follow-on scope
- `TD-STRUCT-001` and `TD-STRUCT-003` remain bounded carry-forward debt, but they are not the main `M36 Phase 0` theme
- `TD-STRUCT-005` remains deferred and aligned mainly to `M38-M39`
- `TD-STRUCT-006` remains deferred and aligned mainly to `M39`

## Exit Criteria

The phase is complete only when:

- `M36 Phase 0` docs and task cards are fully updated with actual results
- the workbench IA and surface map are explicit and frozen
- the bounded capability-slot rules are explicit and frozen
- additive `Codex CLI` and MiniMax MCP pilots are landed without breaking current surfaces
- targeted regression, workflow dogfood, offline validation, and doc validation pass
- remaining debt and deferred integrations are carried forward explicitly and honestly

## Evidence Expectations

Closeout for this phase must include:

- updated task-card status with actual outcomes
- targeted validation around execution/capability/API/CLI/governance surfaces
- workflow dogfood through at least one `project_delivery` / `dev_cluster` path and one `research_spike_reviewable` / `research_cluster` path
- `pytest`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
- `python -m infra.scripts.check_doc_links`
- explicit carry-forward judgment for `TD-STRUCT-001`, `TD-STRUCT-003`, `TD-STRUCT-005`, and `TD-STRUCT-006`
- explicit deferral judgment for `MMX CLI` and `gcloud` / Vertex AI

## Current Outcome

`M36 Phase 0` is complete.

Its accepted result is:

- `M36` was opened honestly through the phase doc and task-card pack
- the workbench IA and interaction/workbench surface boundaries were frozen
- bounded external capability-slot rules were frozen
- `Codex CLI` landed as an additive coding adapter behind the existing execution-profile and worker-router seams
- MiniMax MCP `web_search` and `understand_image` landed as additive MCP pilot capabilities through the existing capability plane
- `MMX CLI`, `gcloud` / Vertex AI, automation breadth, and broader capability-ecosystem productization remain deferred to later bounded work
- closeout evidence, validation, and carry-forward judgment were recorded in [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](../docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md)
