# M21 Phase 0 - Post-M20 Rebaseline And Expansion Freeze

Status: completed
Opened: 2026-04-21
Milestone: M21

## Purpose

Open the first post-`M20` phase without starting new breadth. This phase exists to turn the `v1 core complete` worktree into a trustworthy rebaseline and an extensible control-plane floor for later ecosystem and autonomy work.

## Inputs

- [docs/reviews/m20-freeze-review.md](../docs/reviews/m20-freeze-review.md)
- [docs/tech-debt-registry.md](../docs/tech-debt-registry.md)
- [docs/current_development_workflow.md](../docs/current_development_workflow.md)
- [EVALUATION_REPORT.md](../EVALUATION_REPORT.md)
- [EVALUATION_gptpro.md](../EVALUATION_gptpro.md)
- [NEXT_DEVELOPMENT_PLAN.md](../NEXT_DEVELOPMENT_PLAN.md)

## Scope

- rebuild a trustworthy validation and export baseline
- keep `OrchestratorService` as the facade while tightening short-term boundary seams
- productize migration and validation operations instead of relying on implicit startup behavior
- land a minimum internal `ResultEnvelope v1` truth object and project it additively through evidence and operator reports

## Non-Goals

- new providers
- sessionful `opencode`
- plugin-preserving execution mode
- planner DAG autonomy
- multimodal expansion
- large Web UI redesign

## Active Task Cards

- [M21-0A Rebaseline Evidence And Canonical Demo Matrix](../docs/task_cards/m21_phase_0/M21-0A_rebaseline_evidence_and_canonical_demo_matrix.md)
- [M21-0B Control-Plane Boundary Hardening](../docs/task_cards/m21_phase_0/M21-0B_control_plane_boundary_hardening.md)
- [M21-0C Migration And Validation Productization](../docs/task_cards/m21_phase_0/M21-0C_migration_and_validation_productization.md)
- [M21-0D ResultEnvelope v1 Minimum Truth](../docs/task_cards/m21_phase_0/M21-0D_result_envelope_v1_minimum_truth.md)

## Exit Criteria

- `M21` closeout can cite a repeatable source-package/export baseline
- `workflowctl db migrate` and `workflowctl db migration-status` exist with regression coverage
- `ResultEnvelope v1` is present in task evidence and projected through audit and mutation reports without breaking existing consumers
- phase assets and living docs identify `M21 Phase 0` as the active bounded work

## Outcome

- rebaseline evidence is now produced through `infra/scripts/m21_rebaseline_report.py`
- compile/recompile preparation no longer duplicates the prepared-run persistence path
- migration operations and `ResultEnvelope v1` landed as additive productized surfaces

## Validation Targets

- `pytest -q`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
- `python -m infra.scripts.check_doc_links`
- `python -m infra.scripts.export_source_package --dry-run`
- `python -m infra.scripts.run_cluster_cutover_demo --db-path state/cluster_cutover_demo.db --report-path state/cluster_cutover_demo_report.json`
