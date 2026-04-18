# P1-T02 - Runtime Brief Projection

## Goal

Make the LLM contribution visible in the actual workflow, not only inside provider logs.

## Scope

- enrich runtime state with provider/model/brief metadata
- pass brief metadata into runtime execution
- reflect the brief in the generated artifact

## Guardrails

- keep the artifact readable even without LLM
- avoid schema churn outside the current run model

## Verification

- execution-loop tests
- API detail tests

## Exit Signal

- a live-gateway run produces a readable execution brief in observable surfaces

