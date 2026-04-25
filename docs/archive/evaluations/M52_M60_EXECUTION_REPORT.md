# M52-M60 Bug-First Execution Report

Generated: 2026-04-25

## Summary

Executed the M52-M60 bug-first cleanup plan as a controlled implementation pass. The work prioritized confirmed blockers and verification contracts over new capability breadth. Existing root evaluation files and M48-M51 artifacts were preserved as external inputs.

This pass does not claim the whole M52-M60 plan is fully retired. It closes the high-confidence scheduler, boundary, decomposition, test, capability-health, and route-config slices, and leaves the larger interaction/CLI/Web/chat-runtime decompositions as explicit carry-forward debt.

## Implemented Scope

- M52: fixed scheduler flag-off isolation. `OrchestratorService` now uses `LocalSchedulerLeaseArbiter` without importing `packages.core_domain.scheduler_authority`; cluster mode still lazy-imports the cluster runtime.
- M53: added remote worker callback origin allowlisting, Web/API security headers, lazy ASGI app wrappers to avoid import-time DB migration, and doctor reporting for worker callback boundaries.
- M54: extracted scheduler facade methods and worker callback handling into dedicated mixins. `OrchestratorService` is now ratcheted to 137 direct methods and `services.py` is 2983 lines.
- M56: added test entrypoint layering in `Makefile` (`test-unit`, `test-core`, `test-integration`, `test-full`), doc command smoke, and CI coverage for docs, doctor strict, core tests, and offline validation.
- M57: extended capability health with `readiness_state`, `runtime_ledger_summary`, `provider_route`, `fallback_route`, and richer recent invocation ledger fields while preserving the old `status` field.
- M58: moved cluster routing markers into `infra/seeds/cluster_route_markers.json`; dynamic routing remains opt-in.
- M60: updated the canonical tech-debt registry and active workflow guide with the new truth set and carry-forward boundaries.

## Validation Evidence

- `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict`: passed, status `ok`.
- Targeted M52-M58 suite: 26 passed, 2 skipped.
- `test-unit` equivalent: 49 passed in 15.74s. Local `make` is unavailable in this PowerShell environment.
- `test-core` equivalent: 77 passed in 66.39s.
- `python -m infra.scripts.check_doc_links`: passed, 0 issues.
- `python -m infra.scripts.offline_validation --skip-offline-probe`: `overall_passed=true`.
- Default pytest: 258 passed, 134 skipped in 459.67s.
- Full single-command slow suite timed out after 1204s; split slow closeout passed:
  - `tests/test_web_ui.py tests/test_release_closeout.py`: 5 passed.
  - `tests/test_api.py`: 73 passed.
  - `tests/test_cli.py`: 56 passed.

## Remaining Carry-Forward

- M55 is not complete: `service_interaction.py` still needs a deeper split into chat command, session, generated-profile, and watchdog services.
- M58 is not complete: MMX/Vertex real multimodal evidence smokes and 30-day cluster route statistics remain open.
- M59 is not complete: CLI command families, Web UI static assets/templates, and `runtime_langgraph/chat_runtime.py` module splitting remain open.
- Capability health is more honest, but provider probes are still incomplete for all credential-gated lanes.
- Full `pytest --run-slow` should be made shard-aware; split slow runs pass, but one monolithic command exceeded 20 minutes.

## M61 Recommendation

Do not resume feature milestones yet. M61 should finish the remaining decomposition and maintainability debt: interaction service split, CLI/Web/chat-runtime split, real multimodal probe evidence, and slow-suite sharding.
