# M21-0A Rebaseline Evidence And Canonical Demo Matrix

Status: completed

## Goal

Refresh the post-`M20` baseline so the repository can distinguish the noisy working tree from the reproducible source-package/export baseline.

## Acceptance Criteria

- freeze evidence matrix names the required commands and evidence paths
- canonical demo targets cover `feature_delivery`, `research_spike_reviewable`, `guarded_delivery`, and `project_delivery`
- source-package/export expectations are written down separately from worktree expectations

## Evidence

- `infra/scripts/m21_rebaseline_report.py`
- regression coverage in `tests/test_release_closeout.py`
- source-package dry-run manifest recorded under `state/source_packages/`

## Result

- freeze evidence matrix now names the required validation commands and evidence paths
- canonical demo coverage now includes `feature_delivery`, `research_spike_reviewable`, `guarded_delivery`, and `project_delivery`
- the rebaseline report explicitly separates noisy worktree truth from reproducible source-package truth
