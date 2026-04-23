# M36-0C External Capability Slot Freeze And Bounded Pilots

Status: completed

## Goal

Freeze where stronger external capabilities should attach and land only the minimum bounded pilots needed to support later `M36` workbench execution.

## Acceptance

- land `Codex CLI` as an additive coding adapter through the existing worker-router and execution-profile seams
- allow bounded repo-mutation execution to depend on adapter capability rather than the old adapter-name special case
- expose additive `codex_model` config and compile/recompile override surfaces without breaking current CLI/API contracts
- land MiniMax MCP `web_search` and `understand_image` through the existing MCP/capability plane
- support bounded MCP startup env projection so the MiniMax profile can be seeded honestly
- keep `MMX CLI`, `gcloud` / Vertex AI, and broader capability-ecosystem productization deferred

## Notes

- this card is intentionally not a general capability-ecosystem expansion
- `Codex CLI` is added to complement the existing `opencode` lane, not replace it
- MiniMax MCP remains a bounded pilot through the current capability plane and policy preview surfaces

## Result

- added `CodexAdapter` and registered `codex` in the local and remote worker routers
- generalized repo-mutation eligibility from an `opencode` special case to patch-capable adapter behavior while preserving the current safe default path
- added additive `codex_model` support across config, compile/runtime projection, CLI, API, and read surfaces
- added bounded MCP startup-env support and seeded the `minimax_coding_plan` profile with `web_search` and `understand_image`
- kept `MMX CLI`, `gcloud` / Vertex AI, automation breadth, and broader capability productization deferred
