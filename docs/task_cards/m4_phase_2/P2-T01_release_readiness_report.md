# P2-T01 - Release Readiness Report

## Goal

Expose the current milestone baseline as a machine-readable readiness report instead of relying on scattered test output and narrative docs.

## Scope

- add release-readiness projection logic
- expose it through CLI and API
- prove it with governance + surface tests

## Guardrails

- do not hide open debt
- do not require a Web UI
- do not make this depend on cloud services

## Verification

- governance tests
- CLI/API tests

## Exit Signal

- release readiness can be queried directly and explains current milestone gates
