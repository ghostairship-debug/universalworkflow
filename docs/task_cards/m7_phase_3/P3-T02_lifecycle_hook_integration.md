# P3-T02 - Lifecycle Hook Integration

## Goal

Record simulation automatically at selected stable lifecycle points without widening simulation to every runtime transition.

## Scope

- hook `cancel_run`
- hook `awaiting_review` transitions
- hook terminal auto/human review closure
- keep hook recording policy-gated
- keep manual recording available

## Done When

- selected lifecycle transitions create simulation records automatically
- `latest_simulation_record` reflects the correct lifecycle source
- manual recording still appends history after lifecycle-generated records
