# Source Package Export Policy

## Purpose

This document defines what the repository should consider a clean, handoff-ready source package before a freeze review or external delivery claims the project is in a trustworthy export state.

## 1. What A Clean Source Package Includes

A clean source package should include only repository sources required to understand, run, and review the project, such as:

- application code
- package code
- tests
- migrations
- seeds
- scripts required for validation/demo
- living docs
- relevant historical review docs needed for milestone traceability

## 2. What Must Be Excluded

A handoff-ready source package should exclude machine-local or runtime-generated noise, including:

- `state/*.db`
- `state/artifacts/`
- transient validation outputs unless explicitly requested as evidence
- caches such as `__pycache__`, `.pytest_cache`, `.mypy_cache`
- local virtual environments
- OS/editor noise
- ad hoc temporary files

## 3. Worktree Hygiene Gate

Before a freeze or external handoff may claim the repository is clean:

- the worktree should be clean or have explicitly documented exceptions
- any remaining modified or untracked files must be explained in the handoff/review record
- local state and generated artifacts must not be silently bundled with source

Allowed exceptions may include:

- evaluator-supplied reports used as inputs to a reassessment
- active phase docs and reviews that are themselves part of the pending source change

## 4. Required Export Manifest

Until export automation exists, a clean source-package handoff should be accompanied by a small manifest stating:

- repository location / branch / commit if applicable
- whether the worktree was clean
- any explicit exceptions
- validation evidence used to support the handoff
- whether DBs/artifacts were excluded

## 5. Automation Status

`Pre-M8 Phase A` introduced this policy as guidance.
`Pre-M8 Phase E` turns it into a minimal automated gate through:

- `python -m infra.scripts.check_doc_links`
- `python -m infra.scripts.export_source_package --dry-run`
- `python -m infra.scripts.pre_m8_gates`

The source-package gate remains intentionally minimal:

- it validates exclusion rules and writes a manifest
- it does not require a clean worktree to pass
- it expects freeze reviews to explain any remaining modified or untracked files explicitly
