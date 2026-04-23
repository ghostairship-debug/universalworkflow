# M35 Phase 0: Role / Execution Productization Opening And Contract Freeze

Status: completed
Opened: 2026-04-23
Closed: 2026-04-24
Baseline: accepted `M34 Phase 0`

## Purpose

Open the next bounded post-`M34` phase. This line does not yet ship the full `M35` execution-profile product surface; it opens the milestone honestly, freezes the execution-configuration contract, freezes the execution-resolution precedence line, and defines the workflow-driven way the repository will execute the rest of `M35`.

## Why This Phase Exists

Accepted `M34 Phase 0` left the repository with an interaction-first, role-profile-aware, cluster-aware foundation and a shared orchestration substrate, but the execution-selection story is still only partly productized:

- execution defaults exist today across config, domain-pack, role helper, and adapter-routing layers, but not as one explicit product contract
- cluster members and agent profiles exist, but do not yet carry first-class execution-profile metadata
- current read surfaces can show execution shape, but cannot yet explain override precedence and provenance field by field

The pre-open hardening gate has already been cleared:

- the governance tech-debt report regressions are repaired
- the root planning docs are aligned
- the no-behavior-change `APIRouter` split was absorbed as pre-open work

The next safe bounded step is to open `M35 Phase 0`, freeze the contract and precedence line, then implement the profile/resolver work in later `M35` phases.

## Scope

This phase includes:

- `M35-0A` opening, workflow-orchestration freeze, and debt-position alignment
- `M35-0B` execution-configuration contract freeze
- `M35-0C` execution-resolution precedence and seam freeze
- `M35-0D` validation, closeout, and honest carry-forward judgment

This phase explicitly does not include:

- shipping the full role/profile execution-profile implementation from `M35 Phase 1`
- exposing the full execution-default config/read surface set from `M35 Phase 2`
- opening `M36` workbench breadth
- automation-plane expansion
- full `TD-STRUCT-005` telemetry closure
- general `TD-STRUCT-006` promotion machinery
- public route or packet breaking renames

## Execution Model

Development for this phase uses the existing workflow surfaces as the bounded execution plane.

Rules:

- active phase work should use a workspace-scoped DB label such as `m35_phase0`
- phase kickoff should begin with an `interaction` session
- the default implementation path uses `project_delivery` with `dev_cluster`
- design, risk, and evidence tasks may use `research_spike_reviewable` with `research_cluster`
- every detailed task card maps to exactly one workflow run
- every mutating run must carry `task_card_ref`, `task_card_path`, bounded `write_set`, bounded `read_set`, explicit `test_command` values, bounded `max_fix_iterations`, and `mutation_mode` only when repo mutation is intended
- review gates stay explicit through `run approve` / `run reject` or the Web review surface
- rejected work continues through `interaction followup` against the same session/card path rather than through free-form replacement runs
- every completed card must record real evidence back into the task card, including at least a `run summary`, `operator-view` or `audit-report`, and the validation commands actually used

## Workstreams

### Workstream A: Phase Opening And Workflow Freeze

- open `M35 Phase 0` formally
- point the workflow guide, README, root planning docs, and debt registry at an active `M35` phase
- freeze the workflow-driven execution model for `M35`
- keep `TD-STRUCT-005` and `TD-STRUCT-006` deferred while the phase opens

### Workstream B: Execution-Configuration Contract Freeze

- define the additive execution-configuration contract across global defaults, preset, agent profile, cluster template, and cluster member scopes
- keep current CLI/API/Web surfaces stable
- keep the current `execution_profile` read-model family as the only public projection family for execution explanation

### Workstream C: Resolution Precedence And Consumption Seam Freeze

- define the exact override order for execution resolution
- keep the existing unified config precedence unchanged inside the global-default layer
- define where later `M35` phases will consume resolved execution decisions without implementing the whole behavior yet

### Workstream D: Validation And Closeout

- validate that the contract and precedence freeze did not regress the current interaction/config/API/CLI/Web surfaces
- dogfood one `dev_cluster` path and one `research_cluster` path through the workflow
- close the phase with explicit debt judgment and a freeze review

## Entry Criteria

To remain in-bounds, the phase preserves these assumptions:

- accepted `M34 Phase 0` remains the latest completed freeze baseline
- the pre-open hardening gate is already complete and should be treated as absorbed context, not reopened work
- `TD-STRUCT-001` and `TD-STRUCT-003` remain carry-forward structural debt, but they are not the main `M35` productization theme
- `TD-STRUCT-005` remains deferred and aligned mainly to `M38-M39`, unless a narrow explainability slice becomes necessary for honest `M35` closeout
- `TD-STRUCT-006` remains deferred and aligned mainly to `M39`
- later `M35` phases and all `M36+` breadth remain unopened active work

## Exit Criteria

The phase is complete only when:

- `M35` phase docs and task cards are fully updated with actual results
- the execution-configuration contract is explicit and frozen
- the execution-resolution precedence line is explicit and frozen
- the intended future resolver-consumption seams are defined without public breakage
- targeted regression, workflow dogfood, and doc validation pass
- remaining debt is carried forward explicitly and honestly

## Evidence Expectations

Closeout for this phase must include:

- updated task-card status with actual outcomes
- targeted validation around interaction/config/API/CLI/Web surfaces
- workflow dogfood through at least one `project_delivery` / `dev_cluster` path and one `research_spike_reviewable` / `research_cluster` path
- `python -m infra.scripts.check_doc_links`
- explicit debt judgment for `TD-STRUCT-001`, `TD-STRUCT-003`, `TD-STRUCT-005`, and `TD-STRUCT-006`

## Current Outcome

`M35 Phase 0` is complete.

Its accepted result is:

- `M35` was opened formally through the phase doc and task-card pack
- the execution-configuration contract and execution-resolution precedence line were frozen explicitly
- the workflow-driven execution, review, and evidence model for the `M35` line was frozen and dogfooded through a dedicated workspace DB
- closeout evidence, validation, and carry-forward judgment were recorded in [docs/reviews/m35-role-execution-productization-freeze-review.md](../docs/reviews/m35-role-execution-productization-freeze-review.md)
