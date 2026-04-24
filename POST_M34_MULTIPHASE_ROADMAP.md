# Post-M34 Multi-Phase Roadmap

Status: reference-only
Date: 2026-04-24
Baseline: accepted `M37`
Scope: roadmap guidance only; not active execution truth until the next bounded phase opens

## 1. Relationship To Current Truth

This document is a planning input first created after accepted `M34 Phase 0` and now retained after accepted `M37`.

The archived external roadmap input [docs/archive/GPT_PRO_ROADMAP.md](docs/archive/GPT_PRO_ROADMAP.md) has been assessed and absorbed here where it aligns, so it should not remain a competing roadmap source.

It does **not** override:

1. [docs/current_development_workflow.md](docs/current_development_workflow.md)
2. [docs/reviews/m37-generated-roles-and-automation-plane-freeze-review.md](docs/reviews/m37-generated-roles-and-automation-plane-freeze-review.md)
3. [docs/tech-debt-registry.md](docs/tech-debt-registry.md)

Use this file to rebuild the post-`M37` roadmap shape, not to claim that later `M38+` work is already open.

## 2. Why The Roadmap Must Be Rebuilt

From `M21` through `M34`, the repository mostly evolved through single bounded `Phase 0` closeouts.

That kept the execution discipline strong, but it also caused two kinds of drift:

1. `M` numbers kept advancing while the actual work often behaved like one debt-bounded slice per milestone.
2. earlier product expectations from the pre-`M32` planning material were repeatedly deferred into later bounded cleanup work.

As a result:

- the repository gained strong architecture and runtime foundations
- but the milestone naming lost part of its original multi-phase product-program meaning

The post-`M34` line should correct that drift.

## 3. What Was Actually Achieved By M32-M36 Phase 0

Accepted `M32-M36 Phase 0` did real work and should not be described as failure.

### Landed

- interaction / profile / cluster foundation
- `DevCluster` and `ResearchCluster` templates
- shared orchestration plan builder for shipped multi-role presets
- deeper scheduler-authority honesty cleanup
- minimum `/ui/workbench` preview
- explicit execution-profile contracts, resolver precedence, additive config defaults, and read-side execution explainability
- bounded workbench IA / surface freeze
- additive `codex` routing plus bounded MiniMax MCP search/image-understanding pilot support

### Still Missing Relative To The Earlier Product Vision

- full chat-style or guided natural-language workbench v1
- generated-role lifecycle
- automation plane
- broader capability ecosystem productization
- eval / promotion / self-upgrade closure
- domain-grade `DesignCluster` and multimodal visual verification

## 4. Honest Comparison To The Earlier M32-M36 Vision

The earlier planning material under [docs/archive/M31_FUTURE_IMPLEMENTATION_PLAN.md](docs/archive/M31_FUTURE_IMPLEMENTATION_PLAN.md) and related evaluation notes imagined a faster move into:

- workbench UI v1
- fixed-role runtime productization
- generated roles
- automation controller
- broader capability ecosystem
- product closure by `M36`

That did **not** happen on the original numbering schedule.

What happened instead:

- old `M32` ideas were only partially absorbed by accepted `M32`
- old `M33` and `M34` product expectations were largely deferred
- accepted `M33` and `M34` prioritized structural contraction and honesty cleanup instead
- accepted `M35` productized execution selection first
- accepted `M36 Phase 0` froze workbench/capability boundaries before broader workbench implementation

Therefore the correct statement is:

> accepted `M36 Phase 0` has restored an honest product path, but it has **not** yet reached the earlier productization expectation that older planning material associated with a fully completed `M36`.

## 5. How Many Additional Milestones Are Still Needed

Two different target lines should be separated.

### 5.1 To Reach The Earlier Platform Product Goal

Update after accepted `M37`:

- the remaining platform-productization line is now `M38-M39`

To reach the older post-`M36` platform aspiration in a realistic way from the accepted `M37` baseline, the repository still needs **at least 2 milestone numbers**:

- `M38`
- `M39`

This is the minimum realistic count for:

- broader capability ecosystem productization
- eval/promotion/product closure

### 5.2 To Reach The Higher-Quality Game Development Goal

If the target is not just the platform vision, but also the previously discussed game-development quality bar, one more milestone is likely needed after that:

- `M40` for `DesignCluster` plus multimodal visual verification

So the practical answer is:

- original platform target from the current baseline: **2 more M numbers**
- game-development-quality target from the current baseline: **3 more M numbers**

## 6. Rules For Restoring Meaningful Milestones

From post-`M34` onward, a milestone should normally meet one of these two rules:

### Rule A: Real Product Milestone

- the milestone has a clear theme
- the milestone is expected to contain multiple phases
- the phases express meaningful progression, not just one slice and immediate closeout

### Rule B: Explicit Debt-Only Bounded Slice

- the work is intentionally narrow
- the milestone is explicitly declared debt-focused
- the single-phase shape is part of the design, not accidental drift

For the productization line, the repository should prefer **Rule A**.

## 7. Pre-Open Gates Before M35 (Closed)

The repository cleared the small bug-first pre-open gate before opening `M35 Phase 0`:

1. the known governance-report expectation regressions were repaired
2. the root planning docs were aligned with the accepted `M34` baseline
3. the no-behavior-change `APIRouter` transport split was absorbed as pre-open hardening work
4. the carry-forward treatment of `TD-STRUCT-005` and `TD-STRUCT-006` remained deferred rather than being pulled into the opening slice

This pre-open gate was not `M35 Phase 0` itself. It was the bug-first cleanup required before `M35` could be opened honestly.

## 8. Rebuilt Roadmap

## M35: Role / Execution Productization

Theme:

- turn execution selection into a first-class product surface

Why this milestone exists:

- the repository had the architectural objects but not a productized role/profile execution configuration model

Accepted status:

- `M35` closeout was accepted on 2026-04-24 in [docs/reviews/m35-role-execution-productization-freeze-review.md](docs/reviews/m35-role-execution-productization-freeze-review.md)
- the accepted result includes explicit execution-profile contracts, an authoritative resolver, additive config/read surfaces, compile/runtime/orchestration consumption, and shipped execution explainability

### M35 Phase 0: Opening / Bug-First Gate / Config Contract Freeze

Goals:

- formally open the post-`M34` line
- freeze the role/profile/cluster execution configuration contract
- define the execution-resolution precedence line explicitly instead of relying on scattered defaults
- decide the carry-forward treatment of `TD-STRUCT-005` and `TD-STRUCT-006`
- freeze the workflow-driven execution, review, and evidence model for the rest of `M35`

Historical status:

- `M35 Phase 0` was opened on 2026-04-23 through the phase doc and task-card pack
- `M35 Phase 0` was closed on 2026-04-24 through the accepted `M35` freeze review

### M35 Phase 1: Role/Profile Execution Profiles

Goals:

- introduce explicit execution profiles for public roles, agent profiles, and cluster members
- support role-specific adapter / model / variant / policy selection
- make different-role LLM selection real rather than aspirational
- pull execution selection out of implicit `WorkerRouter` and runtime-gateway defaults so those layers consume resolved execution decisions

### M35 Phase 2: Config Surfaces / Dogfood / Closeout

Goals:

- expose effective execution defaults through `workflow.toml`, env, CLI, API, and read surfaces
- expose an execution-resolution trace that explains why a lane was selected
- prove `DevCluster` and `ResearchCluster` under the new defaults
- if needed for explainability, add narrow lane-stat read surfaces without claiming full `TD-STRUCT-005` closure
- close the milestone with clear validation and debt judgment

### M35 Exit

After `M35`, the repository should be able to explain:

- which role uses which lane
- which profile overrides what
- how cluster members inherit or override defaults

## M36: Natural-Language Workbench V1

Theme:

- turn the current minimum preview into a usable product workbench

Why this milestone exists:

- the back-end interaction plane already exists, but the user-facing front-end workbench still does not

### M36 Phase 0: Workbench Opening / IA / Surface Freeze

Goals:

- define the workbench information architecture
- freeze the interaction/workbench surface map
- keep operator views and product workbench separated
- freeze where stronger external capabilities should attach before broader workbench productization

Accepted status:

- `M36 Phase 0` was accepted on 2026-04-24 in [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md)
- the accepted result froze the workbench IA/surface map, landed additive `codex` adapter support, landed a bounded MiniMax MCP `web_search` / `understand_image` pilot profile, and explicitly deferred `MMX CLI` plus `gcloud` / Vertex AI

### M36 Phase 1: Conversational Workbench Flow

Goals:

- implement guided goal input, clarification, plan draft, execution preview, and launch flow on top of the existing interaction-session APIs
- show selected clusters, plan graph, and review state coherently
- add workbench-level visibility into the execution defaults shipped by `M35`
- consume the frozen capability-slot rules from accepted `M36 Phase 0` rather than inventing parallel capability entry points

Accepted status:

- `M36 Phase 1` was completed on 2026-04-24 through [m36_phase_docs/phase_1_conversational_workbench_flow.md](m36_phase_docs/phase_1_conversational_workbench_flow.md) and [docs/task_cards/m36_phase_1_task_cards.md](docs/task_cards/m36_phase_1_task_cards.md)
- the accepted result turned the minimum workbench preview into a usable guided workbench flow with richer goal intake, recent sessions, execution-default projection, and active run checkpoint visibility

### M36 Phase 2: Follow-Up / Review / Polish / Closeout

Goals:

- finish follow-up, review, and launch checkpoints
- validate operator/workbench consistency
- ship a real natural-language workbench v1 and close the milestone honestly

Accepted status:

- `M36 Phase 2` was completed on 2026-04-24 through [m36_phase_docs/phase_2_followup_review_and_closeout.md](m36_phase_docs/phase_2_followup_review_and_closeout.md) and [docs/task_cards/m36_phase_2_task_cards.md](docs/task_cards/m36_phase_2_task_cards.md)
- `M36` milestone closeout was accepted in [docs/reviews/m36-natural-language-workbench-v1-freeze-review.md](docs/reviews/m36-natural-language-workbench-v1-freeze-review.md)

### M36 Exit

After `M36`, the repository should have:

- a usable workbench v1
- cluster-aware natural-language launch
- coherent product-level front-end entry into the existing control plane

## M37: Generated Roles And Automation Plane

Theme:

- add bounded autonomy on top of the now-productized execution and workbench layers

Why this milestone exists:

- older planning material expected generated roles and automation before product closure, and that still remains unbuilt

### M37 Phase 0: Opening / Safety / Scope Freeze

Goals:

- define the generated-role and automation boundaries
- keep bounded execution and review gates explicit

Accepted status:

- `M37 Phase 0` was completed on 2026-04-24 through [m37_phase_docs/phase_0_generated_roles_and_automation_scope_freeze.md](m37_phase_docs/phase_0_generated_roles_and_automation_scope_freeze.md) and [docs/task_cards/m37_phase_0_task_cards.md](docs/task_cards/m37_phase_0_task_cards.md)

### M37 Phase 1: Generated Profiles / Role Factory

Goals:

- support governed generated roles or generated profiles
- define lifecycle, review, and cleanup rules

Accepted status:

- `M37 Phase 1` was completed on 2026-04-24 through [m37_phase_docs/phase_1_generated_profiles_and_role_factory.md](m37_phase_docs/phase_1_generated_profiles_and_role_factory.md) and [docs/task_cards/m37_phase_1_task_cards.md](docs/task_cards/m37_phase_1_task_cards.md)

### M37 Phase 2: Automation Controller / Watchdog / Closeout

Goals:

- add bounded background automation primitives with a clear split between low-risk automatic actions and high-risk review-gated actions
- support event-driven or schedule-driven controller actions
- keep automation-plane behavior governed and auditable

Accepted status:

- `M37 Phase 2` was completed on 2026-04-24 through [m37_phase_docs/phase_2_automation_controller_watchdog_and_closeout.md](m37_phase_docs/phase_2_automation_controller_watchdog_and_closeout.md) and [docs/task_cards/m37_phase_2_task_cards.md](docs/task_cards/m37_phase_2_task_cards.md)
- `M37` milestone closeout was accepted in [docs/reviews/m37-generated-roles-and-automation-plane-freeze-review.md](docs/reviews/m37-generated-roles-and-automation-plane-freeze-review.md)

## M38: Capability Ecosystem And Product-Grade Engineering Workflows

Theme:

- widen the external capability ecosystem without losing control-plane honesty

### M38 Phase 0: Capability Ecosystem Opening

Goals:

- freeze the capability-SDK and connector-extension direction

### M38 Phase 1: Unified Capability Productization

Goals:

- unify MCP, worker pools, sessions, and connector-style capabilities under a more productized runtime surface
- define a stronger capability/product contract around health, invocation envelopes, auth/scope, and telemetry fields

### M38 Phase 2: Arbitrary Engineering Workflow Productization

Goals:

- move from shipped preset examples toward more serious engineering-task product surfaces
- strengthen observability and remote-worker productization with a clearer OTLP/collector path plus worker identity, replay protection, and pool health expectations

## M39: Eval / Promotion / Product Closure

Theme:

- finish the platform line with governed improvement and promotion machinery

### M39 Phase 0: Opening / Governance / Promotion Scope Freeze

Goals:

- define the governed promotion scope
- decide what product closure actually means for the platform

### M39 Phase 1: Eval / Canary / Promotion

Goals:

- add eval-backed promotion mechanics
- organize real run history, golden tasks, failure taxonomy, and review outcomes into a reusable eval store
- give `TD-STRUCT-006` a real reusable promotion path
- decide whether `TD-STRUCT-005` closes here or remains on a later telemetry line

### M39 Phase 2: Stable Product Surfaces / Closeout

Goals:

- finalize stable product surfaces
- close the local-first product with install/run/observe packaging expectations rather than source-only success criteria
- close the platform line as a coherent local-first product

## M40: Domain-Grade Design / Visual Verification

This milestone is **not** required for the original platform target, but it is likely required for the user-facing game-development-quality target.

Theme:

- `DesignCluster` plus multimodal visual verification

Expected scope:

- design-specific cluster contracts
- visual or multimodal validation loops
- stronger game-development or design-delivery product quality

## 9. Mapping The Remaining Structural Debt

The current debt picture suggests:

- `TD-STRUCT-001` and `TD-STRUCT-003` should continue as bounded carry-forward or bug-driven cleanup, not as the main productization theme
- `TD-STRUCT-005` most naturally aligns with `M38-M39`
- `TD-STRUCT-006` most naturally aligns with `M39`

The key change is:

- post-`M34` should no longer be organized primarily around architecture debt names
- it should be organized around productization milestones, with debt retired inside them

## 10. What Should Change In Repository Practice

From `M35` onward:

1. stop treating every milestone as a single `Phase 0` by default
2. define milestone themes first, then phase progression inside each milestone
3. use phases to express meaningful product progression, not only administrative opening and closeout
4. keep bug-first active, but do not let it collapse every future milestone back into debt-only mode unless the scope truly warrants it

## 11. One-Line Conclusion

Accepted `M36` and `M37` completed the workbench-v1 plus generated-role/bounded-automation line. The honest rebaseline is: `M38-M39` are still needed to reach the earlier platform product target, and `M40` is likely needed if the target includes domain-grade design and visual validation.
