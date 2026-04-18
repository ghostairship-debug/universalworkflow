# P1-T03 - Live Gateway Docs And Visibility

## Goal

Make the live-gateway path operable by documenting the opt-in contract and exposing enough status for operators to tell whether the gateway is active.

## Scope

- document env/config for the OpenAI gateway
- expose gateway status through CLI-visible surfaces
- add closeout notes

## Guardrails

- keep offline validation no-LLM safe
- do not require the provider for ordinary local use

## Verification

- CLI tests
- targeted live-path verification with a fake client

## Exit Signal

- operators can tell when the live gateway is active and how to enable it

