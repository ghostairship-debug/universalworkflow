# AGENTS.md

## 0. Purpose of This File

This file gives Codex and other coding agents the project-specific instructions for working on this repository.

Codex should read this file before making changes. The current milestone is:

```text
M67: Autonomy Policy + Service Slimming
```

The repository is `ghostairship-debug/universalworkflow`.

The goal of M67 is **not** to add more features aggressively. The goal is to make the current workflow runtime safer, thinner, easier to extend, and better suited for long-running self-development tasks.

---

## 1. Project Context

UniversalWorkflow is a **personal / local-first agentic workflow runtime**.

It is intended to help a human operator coordinate long-running agentic development workflows, including workflows that participate in developing and improving this repository itself.

The system is not currently intended to be:

- a public SaaS product
- a multi-tenant enterprise platform
- a public plugin marketplace
- an externally hosted agent execution service
- an automatic GitHub PR / release publisher

The system should remain local-first and operator-controlled while gradually supporting stronger automation.

---

## 2. Current Strategic Problem

The repository already has an `OperatorActionGuard` and an operator receipt mechanism for high-risk actions.

However, the current implementation has a conceptual mismatch:

```text
Some paths require explicit operator confirmation.
Some paths allow similar actions to execute directly.
Long-running workflows need more automation than one-click-per-step confirmation.
```

The problem is not simply “security is weak”.

The real problem is:

```text
The project lacks a unified bounded-autonomy policy layer.
```

Current high-risk behavior should not be decided separately by API routes, Web UI routes, chat helpers, and service methods.

Instead, all high-risk or state-changing actions should go through a shared policy decision path.

---

## 3. M67 North Star

M67 should establish the following architecture:

```text
API / CLI / UI / Chat / Scheduler
        ↓
Command
        ↓
PolicyEngine
        ↓
PolicyDecision
   ┌────┼────┐
 allow require_confirmation deny
   ↓       ↓                 ↓
Executor  Receipt / Lease    Error
   ↓
Application Service
   ↓
Repositories / RuntimePorts / WorkerAdapters
   ↓
Evidence / Events / Audit / Operator Packet
```

The most important architectural change is:

```text
Old:
- Router / UI / chat decides whether an action is safe.
- Then it calls OrchestratorService directly.

New:
- Router / UI / chat creates a Command.
- PolicyEngine decides allow / require_confirmation / deny.
- Executor / service executes only after policy approval.
```

---

## 4. Core M67 Concepts

### 4.1 Command

A `Command` is a structured representation of an intended action.

Examples:

- `LaunchExecuteCommand`
- `ResumeRunCommand`
- `ApproveRunCommand`
- `RejectRunCommand`
- `CancelRunCommand`
- `BatchResumeRunsCommand`
- `ReconcileApplyCommand`
- `WatchdogAutoApplyCommand`

Commands should include at least:

```text
command_id
command_type
source: api | ui | cli | chat | scheduler | service
actor_id
workspace_root
receipt_id
lease_id
metadata
```

### 4.2 PolicyEngine

`PolicyEngine` is the single place that decides whether a command can execute.

It should return a `PolicyDecision`:

```text
allow
require_confirmation
deny
```

Routes, UI forms, chat handlers, and service convenience methods should not independently decide whether a high-risk action is allowed.

### 4.3 OperatorActionReceipt

The existing operator receipt mechanism should remain.

In M67, treat receipt as:

```text
single-use explicit human confirmation
```

It is appropriate for:

- manual operator approval
- Web UI confirmation cards
- API calls where the human explicitly confirms one action
- one-time high-risk transitions

Do not delete or bypass the existing receipt system.

### 4.4 AutomationLease

M67 should introduce `AutomationLease`.

An automation lease is:

```text
bounded multi-use authorization for a limited time, workspace, action set, and write set
```

It exists because long-running self-development workflows cannot require the human operator to approve every resume, retry, test, and internal review.

A lease should define:

```text
lease_id
mode
workspace_root
allowed_actions
denied_actions
write_set_allowlist
denied_paths
max_duration_seconds
max_resume_count
max_fix_iterations
expires_at
status
metadata
```

Receipt and lease relationship:

```text
OperatorActionReceipt = single-use confirmation
AutomationLease       = bounded multi-use authorization
```

---

## 5. Autonomy Modes

### 5.1 manual

Use this for sensitive or normal operator-driven work.

Default behavior:

```text
High-risk actions require explicit confirmation.
No automatic self-development behavior.
No automatic approval of reviews.
No automatic launch_execute.
```

### 5.2 dev_autopilot

Use this for repository self-development and long-running local development tasks.

Allowed under lease:

```text
launch_execute
resume_run
approve_run
batch_resume_runs
run_tests
write_artifact
reconcile_apply
limited write-set mutation
```

Still blocked or requiring confirmation:

```text
git_push
open_pr
publish_release
modify_secret
expand_workspace_root
modify deployment credentials
modify CI secrets
```

### 5.3 long_run_lease

Use this for unattended long-running tasks.

It should be stricter than `dev_autopilot`.

Recommended constraints:

```text
explicit duration
explicit workspace_root
explicit write_set_allowlist
explicit denied_paths
explicit max_resume_count
explicit max_fix_iterations
audit everything
```

---

## 6. Actions That May Be Automated Under Lease

Under a valid `dev_autopilot` or `long_run_lease`, the system may automatically perform these actions when policy allows:

```text
resume_run
approve_run, if automated review verdict is passed
batch_resume_runs
launch_execute, if lease explicitly allows it
run_tests
write_artifact
generate evidence
generate operator packet
generate PR-ready summary
limited code changes inside allowed write set
limited repair attempts
```

The policy engine must still check:

```text
lease is active
lease is not expired
workspace_root matches
action is allowed
action is not denied
write path is allowed
path is not denied
budget / iteration limits are not exhausted
```

---

## 7. Actions That Must Not Be Fully Automated

These actions must remain denied or require explicit human confirmation, even during development:

```text
git_push
open_pr
publish_release
modify_secret
modify .env
modify API keys
modify credentials
modify SSH keys
modify deployment credentials
modify CI/CD secrets
expand_workspace_root
delete many files
large-scale destructive rename
external upload of artifacts
unknown external side effects
```

If there is any doubt, prefer:

```text
require_confirmation
```

over:

```text
allow
```

---

## 8. Current High-Priority Inconsistencies to Fix

Codex should inspect and fix these carefully.

### 8.1 `/runs/launch` with `execute=true`

Expected behavior:

```text
execute=false:
- no high-risk confirmation needed

execute=true:
- requires valid launch_execute receipt
  OR
- requires active lease allowing launch_execute
```

Do not allow `execute=true` to bypass policy.

### 8.2 Web UI workbench launch with `execute=true`

Expected behavior:

```text
execute=true:
- if valid lease exists, allow
- otherwise route to confirmation card / receipt flow
```

Do not let UI form submission directly execute high-risk launch behavior.

### 8.3 Chat confirmation fallback

Current chat behavior may interpret generic words like:

```text
ok
continue
run
好的
继续
执行
```

as permission to resume or approve an active run.

Expected behavior:

```text
Without active valid lease:
- generic confirmation words must not directly resume or approve a run.
- create a confirmation card or ask for explicit confirmation.

With active valid lease:
- may execute only if PolicyEngine allows the resulting command.
```

### 8.4 State-changing GET endpoints

GET routes must not mutate state.

Known suspect:

```text
/interaction/watchdogs/evaluate?auto_apply=true
```

Expected behavior:

```text
GET /interaction/watchdogs/evaluate:
- preview / dry-run only
- no mutation

POST /interaction/watchdogs/apply:
- state-changing
- must go through PolicyEngine
```

---

## 9. Architecture Slimming Priorities

The current `OrchestratorService` should become thinner over time.

Do not perform a risky full rewrite.

Instead, gradually extract:

```text
RepositoryBundle
RuntimePorts
PolicyEngine
AutomationLeaseService
RunCommandService
InteractionCommandService
ExecutionService
ReviewService
GovernanceService
```

### 9.1 RepositoryBundle

Create a bundle for repositories that are currently initialized directly inside `OrchestratorService`.

Potential fields include:

```text
run_repo
preset_repo
budget_repo
task_repo
event_repo
evidence_repo
review_repo
handoff_repo
runtime_state_repo
runtime_attempt_repo
runtime_claim_repo
worker_lease_repo
scheduler_proposal_repo
scheduler_decision_repo
scheduler_peer_heartbeat_repo
snapshot_repo
memory_item_repo
intent_session_repo
followup_request_repo
chat_message_repo
chat_stream_event_repo
cluster_route_decision_repo
capability_invocation_repo
capability_probe_result_repo
operator_action_receipt_repo
generated_agent_profile_repo
automation_watchdog_repo
simulation_record_repo
```

Keep existing legacy attributes for compatibility:

```python
self.run_repo = self.repos.run_repo
self.preset_repo = self.repos.preset_repo
```

Do not break existing tests.

### 9.2 RuntimePorts

Create a bundle for runtime and external integration ports.

Potential fields include:

```text
runtime_gateway
chat_llm_runtime
chat_control_graph
capability_plane
worker_router
domain_pack_registry
simulation_policy_registry
evidence_builder
auto_review
simulation_runner
trace_exporter
durable_runtime_pilot
external_worker_gateway
orchestration_engine
worker_pool_profiles
```

This prepares future integration with:

```text
LangGraph
MCP
Codex CLI
opencode
Claude Code CLI
Gemini / gcloud CLI
remote workers
multi-agent routing
capability plane extensions
```

### 9.3 OrchestratorService Compatibility

Do not break public service methods immediately.

Allowed approach:

```text
Keep OrchestratorService as a compatibility façade.
Move new logic into smaller services.
Gradually route old methods through command/policy.
```

---

## 10. Implementation Phases

### Phase M67A: Documentation and Inventory

Create or update:

```text
AGENTS.md
M67_DEV_PLAN.md
docs/architecture/M67_AUTONOMY_POLICY.md
```

Do not change runtime behavior in this phase.

### Phase M67B: RepositoryBundle and RuntimePorts

Add bundles and migrate construction logic.

Rules:

```text
preserve legacy attributes
preserve public methods
preserve tests
avoid behavior changes
```

### Phase M67C: Command and Policy Skeleton

Add package:

```text
packages/core_domain/policy/
```

Files:

```text
__init__.py
commands.py
decisions.py
leases.py
engine.py
```

Implement:

```text
BaseCommand
concrete high-risk commands
PolicyDecision
PolicyContext
AutomationLease model
PolicyEngine skeleton
```

### Phase M67D: Minimal AutomationLeaseService

Add:

```text
packages/core_domain/service_automation_lease.py
```

Implement:

```text
create_lease
get_lease
validate_lease
revoke_lease
mark_exhausted
```

Persistence can start minimal.

Prefer:

```text
small, testable implementation
```

over:

```text
large DB migration
```

If persistence is in-memory or JSON-file based, document the limitation.

### Phase M67E: Migrate High-Risk Entry Points

Migrate these first:

```text
/runs/launch execute=true
/ui/workbench launch execute=true
chat continue / ok / run fallback
resume_run
approve_run_review
reject_run_review
cancel_run
batch_resume_runs
```

All should go through:

```text
Command → PolicyEngine → allow / require_confirmation / deny
```

### Phase M67F: Fix State-Changing GET

Split watchdog evaluation:

```text
GET  /interaction/watchdogs/evaluate  => preview only
POST /interaction/watchdogs/apply     => state-changing apply
```

The POST path must go through PolicyEngine.

### Phase M67G: Closeout

Update docs and tests.

Closeout should honestly state what is complete and what remains.

Do not claim enterprise-grade security.

Do not claim all safety is solved.

State that M67 establishes:

```text
bounded autonomy foundation
service slimming foundation
policy boundary regression tests
```

---

## 11. Test Requirements

Add tests for every policy boundary change.

Recommended test files:

```text
tests/test_policy_engine.py
tests/test_automation_lease.py
tests/test_high_risk_policy_boundaries.py
tests/test_watchdog_policy_boundaries.py
```

### 11.1 PolicyEngine tests

Required cases:

```text
no lease + ResumeRunCommand => require_confirmation
no lease + LaunchExecuteCommand => require_confirmation
dev_autopilot lease allowing resume_run => allow
dev_autopilot lease denying resume_run => deny or require_confirmation
workspace mismatch => deny
git_push pseudo-command => deny or require_confirmation
unknown high-risk command => require_confirmation
```

### 11.2 AutomationLease tests

Required cases:

```text
create lease
expired lease rejected
revoked lease rejected
denied action rejected
allowed action accepted
denied path rejected
workspace mismatch rejected
```

### 11.3 High-risk boundary tests

Required cases:

```text
POST /runs/launch execute=true without receipt or lease => fails or requires confirmation
POST /runs/launch execute=true with valid receipt => succeeds
POST /runs/launch execute=true with valid dev_autopilot lease => succeeds
POST /runs/launch execute=false => succeeds without receipt
chat "continue" without pending confirmation and without lease => does not execute resume/approve
chat "continue" with valid dev_autopilot lease => may execute if run status allows
resume API without receipt/lease => fails
resume API with receipt => succeeds
resume API with lease => succeeds
approve API with wrong lease action => rejected
```

### 11.4 Watchdog tests

Required cases:

```text
GET evaluate never mutates state
GET evaluate?auto_apply=true does not mutate state
POST apply without receipt/lease => fails or requires confirmation
POST apply with valid lease => applies
POST apply with wrong lease => rejected
```

---

## 12. Suggested Commands

Use existing project commands if they differ.

Try these first:

```bash
pytest -q tests/test_service_decomposition.py
pytest -q tests/test_operator_action_receipt.py
pytest -q tests/test_policy_engine.py
pytest -q tests/test_automation_lease.py
pytest -q tests/test_high_risk_policy_boundaries.py
pytest -q tests/test_watchdog_policy_boundaries.py
pytest -q
```

If available:

```bash
python -m infra.scripts.check_doc_links
python -m infra.scripts.offline_validation --skip-offline-probe
```

Do not invent expensive external setup unless necessary.

If tests cannot run in the current environment, report exactly:

```text
which command was attempted
what failed
whether failure is environment-related or code-related
what still needs human/local verification
```

---

## 13. Coding Style and Change Control

Prefer:

```text
small changes
explicit types
compatibility shims
new tests near changed behavior
clear names
domain-specific language
boring implementation
```

Avoid:

```text
large rewrites
hidden global state
implicit bypasses
magic strings scattered across routers
new dependencies without strong reason
complex frontend migration
unreviewed DB migrations
```

If adding a new dependency, explain why.

If changing public behavior, add tests.

If touching security/autonomy behavior, add regression tests.

---

## 14. Router / UI / Chat Rules

### Router layer

Routers should:

```text
parse request
construct command or call thin service method that constructs command
return response
```

Routers should not:

```text
make independent high-risk allow/deny decisions
silently bypass receipt or lease
mutate state from GET
```

### UI layer

UI should:

```text
render state
collect operator intent
show confirmation cards when needed
submit receipt or lease context
```

UI should not:

```text
directly bypass policy for convenience
hide high-risk execution behind generic buttons
```

### Chat layer

Chat should:

```text
infer operator intent
create commands
ask for confirmation when policy requires it
use active lease only when valid
```

Chat should not:

```text
treat generic "ok" / "continue" / "run" as execution permission without policy approval
```

---

## 15. Safety Rules

The goal is not maximum lock-down.

The goal is:

```text
bounded autonomy
consistent policy
recoverable automation
auditable execution
```

Always block or require human confirmation for:

```text
git_push
open_pr
publish_release
modify_secret
modify .env
modify credentials
modify deployment permissions
modify CI/CD secrets
expand workspace_root
external upload
unknown external side effect
large destructive file operation
```

State-changing GET is not allowed.

Policy bypass is a P0/P1 issue.

Secret exposure is a P0 issue.

Automatic external publication is a P0 issue.

---

## 16. Done Definition for M67

M67 is acceptable when:

```text
1. RepositoryBundle exists and OrchestratorService construction is thinner.
2. RuntimePorts exists and external/runtime integrations are grouped.
3. PolicyEngine skeleton exists.
4. AutomationLease model/service exists.
5. launch_execute / resume / approve / reject / cancel / batch_resume have policy path.
6. /runs/launch execute=true cannot bypass receipt or lease.
7. workbench execute=true cannot bypass receipt or lease.
8. chat generic confirmation cannot bypass policy.
9. state-changing GET behavior is removed or blocked.
10. New policy boundary tests exist.
11. Receipt still works as single-use confirmation.
12. dev_autopilot lease works for bounded long-running automation.
13. git push / PR / publish / secrets remain non-automated by default.
14. Docs clearly state what is complete and what is not complete.
```

---

## 17. Non-Goals

Do not implement these in M67 unless explicitly instructed:

```text
full RBAC
multi-user auth
public SaaS auth
plugin marketplace
full React/Vue frontend rewrite
complete DB migration system
full remote worker security model
automatic GitHub PR creation
automatic git push
automatic release publish
enterprise compliance
```

---

## 18. Recommended First Task for Codex

Start with this:

```text
Read AGENTS.md, README.md, M61_M66_EXECUTION_REPORT.md, M61_M66_ISSUE_REGISTER.md, packages/core_domain/services.py, packages/core_domain/service_operator_action_guard.py, apps/orchestrator_api/routers/runs.py, apps/orchestrator_api/routers/interaction.py, apps/orchestrator_api/routers/ui.py, and packages/core_domain/service_interaction_chat.py.

Then produce a short implementation plan for M67A-M67C only.

Do not change runtime behavior until the plan is accepted.
```

After the plan is accepted, proceed with:

```text
M67A docs
M67B RepositoryBundle / RuntimePorts
M67C Command / PolicyEngine skeleton
```

Only after those are merged should Codex start migrating high-risk runtime behavior.

---

## 19. Review Checklist

When reviewing Codex changes, check:

```text
Does this introduce a new policy bypass?
Does this route mutate state from GET?
Does this make chat execution too implicit?
Does this make long-running automation impossible?
Does this preserve receipt compatibility?
Does this preserve current API behavior where possible?
Does this add tests for new policy behavior?
Does this make OrchestratorService thinner or fatter?
Does this hard-code action rules in router/UI/chat instead of PolicyEngine?
Does this accidentally allow git push / PR / publish / secrets modification?
```

---

## 20. Final Instruction to Codex

Prefer a conservative implementation that creates the right architecture seam.

Do not try to solve all autonomy, security, UI, and service decomposition problems in one diff.

The correct direction is:

```text
bounded autonomy first
policy consistency second
service slimming third
feature expansion later
```
