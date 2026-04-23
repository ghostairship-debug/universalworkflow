# M36-0D Validation, Closeout, And Carry-Forward

Status: completed

## Goal

Close `M36 Phase 0` with validation evidence, workflow dogfood, and an honest carry-forward judgment for remaining structural debt and deferred external integrations.

## Acceptance

- targeted execution/capability/API/CLI/governance validation passes
- workflow dogfood covers at least one implementation-oriented `dev_cluster` path and one evidence-oriented `research_cluster` path
- full `pytest` passes
- offline validation passes
- doc link validation passes
- phase closeout/freeze review is written
- debt registry guidance remains honest about what is still deferred or carried forward
- no later `M36` phase is opened until `M36 Phase 0` closeout evidence is recorded honestly

## Notes

- closeout is not complete unless the repository can explain the frozen workbench boundary, the bounded capability-slot decision, the validation evidence, and the remaining deferred integrations in one coherent story
- the expected closeout validation set is:
  - targeted execution/capability/API/CLI/governance regression
  - `pytest`
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `python -m infra.scripts.check_doc_links`
- the expected workflow dogfood set is:
  - one `interaction create-session` path using `project_delivery` with `dev_cluster`
  - one `interaction create-session` path using `research_spike_reviewable` with `research_cluster`

## Result

- full repository regression passed:
  - `pytest --basetemp state/.pytest-tmp-m36-all`
  - `296 passed`
- offline validation passed:
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed: true`
- doc link validation passed:
  - `python -m infra.scripts.check_doc_links`
  - `passed: true`
- workflow dogfood used the dedicated phase DB at `state/workspaces/ed57374f70/m36_phase0.db` and covered both required kickoff paths:
  - `intent_session_d1e62123648f` with `project_delivery` + `dev_cluster`
  - `intent_session_c18998538cf1` with `research_spike_reviewable` + `research_cluster`
- wrote the accepted bounded closeout in [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](../../reviews/m36-workbench-ia-capability-slot-freeze-review.md)
- carry-forward remains explicit and unchanged:
  - `TD-STRUCT-001`: bounded carry-forward, partially repaid
  - `TD-STRUCT-003`: bounded carry-forward, partially repaid
  - `TD-STRUCT-005`: deferred to `M38-M39`
  - `TD-STRUCT-006`: deferred to `M39`
- deferred external integrations remain explicit:
  - `MMX CLI`: deferred
  - `gcloud` / Vertex AI: deferred
