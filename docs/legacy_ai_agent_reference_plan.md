# Legacy AI Agent Reference Plan

## Positioning

This document defines how `D:\AI Agent` should be used as a reference source for the current repository.

Historical note: this document was written before the repository milestone naming was fully normalized. Some items originally described here as `M1.5 hardening` were later implemented through the dedicated `M1 legacy hardening uplift`, while the shipped post-freeze `M1.5` phase focused on second-executor / capability-routing hardening. The canonical sequence is [docs/m1_to_m2_progression.md](/D:/Universal%20Agentic%20workflow/docs/m1_to_m2_progression.md:1).

It is intentionally **not** a migration plan.
It is also **not** part of the M1 critical path.

The core rule is:

- M1 keeps moving on its own architecture.
- The legacy project is used only as a post-M1 reference library for semantics, edge cases, and test ideas.
- Any useful legacy capability must be re-expressed in the current contracts and service boundaries instead of being copied in bulk.

## Conclusion

A reuse reference plan **is worth generating**, but only in the following form:

- `reference-only`
- `post-M1 supplement`
- `selective extraction`
- `test-first or contract-first reimplementation`

It is **not** worth generating a direct code reuse plan for bulk migration, shared runtime, or module-level porting.

## Why The Legacy Project Should Not Be Reused Directly

Compared with the current repository, `D:\AI Agent` is much broader and heavier:

- It carries a project-centric kernel, multi-role workflow runtime, repair/reconcile logic, and several historical compatibility layers.
- It contains large domain surface area that the current repository does not want to inherit.
- Its strongest parts are in workflow semantics, review loops, reconciliation, and tests, not in drop-in modules for the current M1/M2 line.

So the right stance is:

- reuse ideas
- reuse invariants
- reuse edge cases
- reuse test scenarios
- avoid direct structural inheritance

## Timing

### During M1

Do not interrupt M1 implementation for legacy code import.

Allowed:

- build and maintain the reference index
- read legacy code when writing ADRs, tests, or guard conditions
- extract anti-patterns and edge cases

Not allowed:

- port large legacy services into the current repo
- align current contracts to legacy naming only for compatibility
- introduce legacy phase/task-card architecture into the current run-centric line

### Immediately After M1 Freeze

This is the first useful window for the reference plan.

Goals:

- review M1 gaps that remain intentionally deferred
- harvest stronger validation rules from the legacy project
- decide which areas need M1.5 hardening versus true M2 expansion

Best use cases:

- stronger review semantics
- richer runtime state validation
- cancel/resume/retry edge-case handling
- better status/detail and event inspection

### M1.5 / Hardening Stage

This is the best phase for selective adoption by reimplementation.

Recommended targets:

- state guard completeness
- review gate persistence semantics
- structured completion/review summary validation
- targeted recovery and repair checklists

Reuse mode:

- mostly `semantic reuse`
- mostly `test reuse`
- very limited `code pattern reuse`

### M2

This is the first stage where some deeper legacy ideas may be worth absorbing, but still through anti-corruption boundaries.

Recommended targets:

- richer runtime snapshot lifecycle
- drift detection and reconciliation heuristics
- review-chain dependency repair ideas
- more expressive operator-facing diagnostics

Still avoid:

- full facade migration
- full project kernel migration
- doc-compile workflow transplant
- pf_content or media-specific subdomains

### M3 And Later

The legacy project becomes mostly a quality and governance reference.

Useful areas:

- observability patterns
- failure taxonomy
- review and closure discipline
- regression case mining

## Reuse Classes

### Class A: Strong Reference Candidates

These are worth indexing and revisiting later.

- runtime state semantics
- review gate semantics
- state machine transition guards
- structured completion and review output rules
- reconciliation and drift detection test cases

### Class B: Partial Reference Candidates

These can inspire current design, but should not be mirrored closely.

- operator status surfaces
- project event/timeline organization
- task descriptor enrichment
- retry context enrichment

### Class C: Avoid

These should not be adopted unless the roadmap explicitly changes.

- `facade.py` monolith style
- V1/V2 compatibility burden
- doc-driven compile pipeline as the primary execution model
- `pf_content` and media factory subdomain
- OpenCode/OMO-specific agent layering
- old migration assumptions and historical wrappers

## Reference Index Schema

Each indexed item should use the following fields:

| Field | Meaning |
| --- | --- |
| `ref_id` | Stable identifier such as `L-REVIEW-001` |
| `area` | Domain area such as `review`, `runtime`, `reconcile`, `status`, `testing` |
| `legacy_path` | Source file or test path inside `D:\AI Agent` |
| `value_type` | `semantic`, `test`, `pattern`, or `anti_pattern` |
| `recommended_phase` | `M1.5`, `M2`, `M3`, or `never` |
| `adoption_mode` | `read_only`, `rewrite`, or `guardrail_only` |
| `why_it_matters` | Short reason this item is worth keeping |
| `current_mapping` | Current repo module or concern it would inform |
| `do_not_copy` | What must not be copied over directly |
| `status` | `indexed`, `consulted`, `adopted`, `rejected`, or `deferred` |

## Seed Reference Index

| ref_id | area | legacy_path | value_type | recommended_phase | adoption_mode | why_it_matters | current_mapping | do_not_copy | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `L-STATE-001` | `state_machine` | `src/agentic_kernel/domain/project.py` | `semantic` | `M1.5` | `read_only` | Has a mature transition matrix for `planned/approved/running/paused/review_required/completed/failed/cancelled`. | run status guard design and future operator state semantics | Do not import project-centric state model wholesale. | `indexed` |
| `L-RUNTIME-001` | `runtime` | `src/agentic_kernel/domain/task_state.py` | `semantic` | `M2` | `rewrite` | Shows a fuller runtime snapshot lifecycle and terminal/non-terminal separation. | future runtime state refinement | Do not copy status names that do not fit the current run model. | `indexed` |
| `L-RUNTIME-002` | `runtime_storage` | `src/agentic_kernel/storage/task_store.py` | `pattern` | `M2` | `rewrite` | Good reference for runtime attempt persistence and latest/live lookup patterns. | runtime repository evolution | Do not copy the full schema or task-centric ownership model. | `indexed` |
| `L-REVIEW-001` | `review` | `src/agentic_kernel/storage/review_store.py` | `pattern` | `M1.5` | `rewrite` | Clean minimal persistence model for review gates and project events. | future review persistence hardening | Do not inherit project event schema verbatim. | `indexed` |
| `L-REVIEW-002` | `review` | `src/agentic_kernel/services/review_service.py` | `semantic` | `M1.5` | `rewrite` | Useful for approved/rejected/pending gate semantics and latest-gate evaluation. | human review loop expansion | Do not copy service API names directly. | `consulted` |
| `L-QUALITY-001` | `review_policy` | `tests/services/test_review_policy_routing.py` | `test` | `M1.5` | `guardrail_only` | Strong source of edge cases for optional/mandatory/recommended review policy behavior. | future review policy tests | Do not pull phase/task-card machinery into current core. | `adopted` |
| `L-QUALITY-002` | `quality_loop` | `tests/services/test_quality_loop_runtime.py` | `test` | `M2` | `guardrail_only` | Good source for structured summary validation and review-driven progression cases. | richer operator/review acceptance testing | Do not adopt legacy agent routing assumptions. | `indexed` |
| `L-RECON-001` | `reconcile` | `src/agentic_kernel/services/progression_service.py` | `semantic` | `M2` | `read_only` | Captures how review results, blocked descendants, and phase completion interact. | future progression hardening | Do not import phase/task-card progression engine into current M1 line. | `indexed` |
| `L-RECON-002` | `reconcile` | `src/agentic_kernel/services/runtime_reconcile_service.py` | `semantic` | `M2` | `read_only` | Very useful as a catalog of failure modes and repair actions for drifted workflow state. | M2+ repair/recovery design | Do not copy the service surface or broad dependency graph. | `indexed` |
| `L-RECON-003` | `reconcile_tests` | `tests/services/test_phase_task_card_runtime.py` | `test` | `M2` | `guardrail_only` | Large reservoir of realistic workflow drift and repair scenarios. | M2 regression design | Do not adopt legacy phase runtime protocol whole-cloth. | `indexed` |
| `L-DOC-001` | `documentation` | `docs/project-deep-dive.zh-CN.md` | `semantic` | `M1.5` | `read_only` | Strong narrative map of what the legacy system actually became and where its complexity came from. | architecture review and anti-scope-creep checks | Do not use it as a roadmap source of truth. | `indexed` |
| `L-ANTI-001` | `anti_pattern` | `src/agentic_kernel/facade.py` | `anti_pattern` | `never` | `read_only` | Clear warning of what happens when orchestration, state repair, review, and query logic converge into one file. | current boundary discipline | Never port this file or imitate its aggregation pattern. | `indexed` |
| `L-ANTI-002` | `anti_pattern` | `src/agentic_kernel/pf_content/` | `anti_pattern` | `never` | `read_only` | Separate product/domain line unrelated to the current repository's core roadmap. | scope control | Never import this subtree for general workflow evolution. | `indexed` |
| `L-ANTI-003` | `anti_pattern` | `docs/implementation_plan.md` | `anti_pattern` | `never` | `read_only` | Historical migration plan that assumed a different transition path; useful mainly to avoid repeating bulk-reuse thinking. | decision hygiene | Do not treat this as an implementation blueprint. | `indexed` |

## How To Use The Index

When entering a later phase:

1. Start from the target problem in the current repo, not from the legacy tree.
2. Query the index by `area` and `recommended_phase`.
3. Open only the 1 to 3 most relevant legacy files or tests.
4. Extract invariants, failure modes, and edge cases.
5. Rewrite them into the current architecture with current naming and boundaries.
6. Add tests first when possible.
7. Update the index item status to `consulted`, `adopted`, `rejected`, or `deferred`.

## Adoption Rules

- Prefer `tests` over `services`.
- Prefer `semantics` over `implementation`.
- Prefer `rewrite` over `copy`.
- Prefer `anti_pattern` notes when a legacy module is larger than the current target.
- If a legacy item requires importing phase/task-card or project-kernel assumptions, stop and downgrade it to `reference only`.

## Simple Operating Checklist

Before adopting anything from the legacy project, answer:

1. Is the thing we want a behavior invariant, or just a legacy implementation shape?
2. Can it be expressed inside the current contracts without adding legacy concepts?
3. Would a test copied in spirit give us most of the value already?
4. If we copied nothing and rewrote from scratch using only the invariant, would the result be cleaner?

If the answer to the fourth question is `yes`, rewrite from scratch and keep the legacy item as reference only.
