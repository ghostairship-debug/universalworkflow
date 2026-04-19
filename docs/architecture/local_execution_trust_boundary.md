# Local Execution Trust Boundary

## Purpose

This document defines the trust boundary for local subprocess execution in the current repository.

## Boundary Statement

The repository's CLI/API runtime is designed for a trusted local-machine operator workflow.

That means:

- local operators intentionally execute shell or CLI-backed tasks on their own machine
- adapters may launch local subprocesses
- subprocesses are bounded by timeout budgets and an environment allowlist
- this is **not** a multitenant sandbox or remote code execution isolation layer

## What Is Trusted

- the local machine and local workspace
- the operator choosing to compile or resume a run
- explicitly selected adapters such as `shell` or `opencode`
- explicit workflow environment values injected through task packets

## What Is Not Assumed

- arbitrary tenant isolation
- remote safety guarantees for untrusted callers
- full process sandboxing
- least-privilege OS enforcement beyond the current allowlist and timeout controls

## Current Guardrails

- subprocess-backed adapters enforce declared timeout budgets
- subprocess-backed adapters inherit only an allowlisted subset of the parent environment plus explicit packet env values
- compile-generated Python commands use the current interpreter via `sys.executable`
- README and workflow docs treat local execution as a trusted operator boundary

## Implication For Future Work

If the repository later exposes richer remote execution or multi-tenant surfaces, this trust model must be revisited explicitly rather than assumed to scale automatically.
