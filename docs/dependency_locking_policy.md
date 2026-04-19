# Dependency Locking And Versioning Policy

## Purpose

This document records how the repository should manage dependency versions after the pre-`M8` hardening gate.

The goal is to keep runtime updates maintainable without pretending the repository already ships a single universal lockfile across all developer environments.

## 1. Current Strategy

The repository currently uses:

- `pyproject.toml` as the canonical dependency declaration
- explicit minimum versions for required features and tested baselines
- selective, moderately wide upper bounds for core runtime dependencies
- `pytest -q` and `python -m infra.scripts.offline_validation --skip-offline-probe` as the acceptance gates for bound changes

This means the project is currently **bounded, but not lockfile-driven**.

## 2. Why There Is No Canonical Committed Lockfile Yet

At the current maturity level, a committed universal lockfile would create more maintenance noise than value because the repository still supports:

- multiple local developer environments
- multiple local CLI/provider setups
- Windows/macOS/Linux shell execution

Until a future cycle standardizes the packaging toolchain further, the canonical source of dependency truth remains:

- `pyproject.toml`

## 3. Rules For Changing Dependency Bounds

When widening or adjusting a dependency bound:

1. make the change narrowly rather than sweeping every dependency at once
2. explain the reason in the active phase review or freeze review
3. run:
   - `pytest -q`
   - `python -m infra.scripts.offline_validation --skip-offline-probe`
4. if the change affects delivery claims, also run:
   - `python -m infra.scripts.pre_m8_gates`

## 4. When A Lockfile Should Be Added Later

A future cycle may introduce a canonical lockfile when all of the following are true:

- the package manager/tooling choice is explicitly frozen
- the repository wants reproducible build/install snapshots as a first-class delivery artifact
- platform variance is narrow enough that a committed lockfile helps more than it hurts

## 5. Current Interpretation

Before `M8`, the repository should treat dependency management as:

- policy-driven
- test-gated
- selectively widened

It should **not** treat missing committed lockfiles as a blocker for the current shipped local-first baseline.
