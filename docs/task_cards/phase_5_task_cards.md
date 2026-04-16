# Phase 5 Task Cards

## Reassessment

- The internal control loop is now executable end to end.
- The remaining work is delivery-facing:
  operator commands, repeatable setup, smoke proof, and freeze-review evidence.
- This machine does not currently have a `make` binary, so Phase 5 must provide both a `Makefile` and a Python command path.

## Card P5-01: Replace placeholder CLI with operator commands

- Goal:
  Add the required `workflowctl` commands and allow local prepare/execute flows for smoke.
- Done when:
  Run, task, preset, and db commands are usable from the terminal.

## Card P5-02: Add DX command runner and `Makefile`

- Goal:
  Provide stable command entry points for dev, migrate, reset-db, smoke, and logs-tail.
- Done when:
  The Python command path works locally and `Makefile` mirrors it.

## Card P5-03: Add smoke documentation and automation

- Goal:
  Document and automate the no-LLM local smoke path.
- Done when:
  Smoke resets the DB, sanitizes LLM API keys, seeds presets, executes one run, and checks the timeline.

## Card P5-04: Add README and freeze review

- Goal:
  Make the M0 bootstrap understandable and formally reviewable.
- Done when:
  A new teammate can start the project and the review doc ends with an explicit `go` or `no-go`.

## Card P5-05: Add CLI verification

- Goal:
  Cover the main operator commands with tests.
- Done when:
  `preset list`, `run create`, `run status`, `run timeline`, `task evidence`, `run cancel`, and `db reset` are exercised.
