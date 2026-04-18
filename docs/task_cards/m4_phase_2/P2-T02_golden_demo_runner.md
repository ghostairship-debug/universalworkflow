# P2-T02 - Golden Demo Runner

## Goal

Create one canonical demo command that replays the representative runtime paths on a fresh database and produces a structured packet that can be reviewed or shared internally.

## Scope

- add `manage.py demo`
- cover:
  - auto
  - human review
  - recommended escalation
  - mandatory sign-off
  - noop
  - capability/domain-pack summary

## Guardrails

- keep it local-only
- keep it deterministic
- use the current runtime surfaces instead of bespoke demo-only logic

## Verification

- demo-oriented tests
- full pytest

## Exit Signal

- one command produces a stable demo packet on a clean DB
