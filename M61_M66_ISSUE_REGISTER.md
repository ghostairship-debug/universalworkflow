# M61-M66 Issue Register

Generated: 2026-04-25

This register absorbs the still-provable issues from `docs/governance/tech_debt_registry.json`, archived M48-M60 reports/plans, [GPTPRO_EVALUATION.md](docs/archive/evaluations/GPTPRO_EVALUATION.md), [PROJECT_DEEP_EVALUATION_M47_OPUS.md](docs/archive/evaluations/PROJECT_DEEP_EVALUATION_M47_OPUS.md), and [PROJECT_DEEP_EVALUATION_M48_TRIAGE.md](docs/archive/evaluations/PROJECT_DEEP_EVALUATION_M48_TRIAGE.md).

Status values: `open`, `repaid`, `obsolete`, `blocked`.

| ID | Source | Issue | Status | Acceptance |
| --- | --- | --- | --- | --- |
| M61-REL-001 | M52-M60 / M47 Opus / M48 Triage | Slow suite is not shard-aware; single `pytest --run-slow` exceeded 20 minutes. | repaid | `workflowctl test matrix` supports unit/core/integration/slow/full and `--shard N/M`; unit/core validated, slow shard closeout still recommended before M66 final. |
| M61-REL-002 | M47 Opus / M48 Triage | Windows pytest interruption can leave SQLite/WAL temp pollution. | repaid | Matrix runs use unique basetemp under `state/.pytest-tmp-m61m66/`; probe timeout leaks were fixed in BUG-007/BUG-008. |
| M61-DOC-001 | GPT Pro / M47 Opus | Root evaluation docs and active truth set are still mixed. | repaid | Historical evaluations are absorbed into this register/report and archived under `docs/archive/evaluations/`; root keeps active M61-M66 entry/report files. |
| M62-STRUCT-001 | Tech debt / M52-M60 | `service_interaction.py` remains oversized and owns chat/session/profile/watchdog logic. | repaid | `service_interaction.py` is now a thin facade; logic moved into chat/cluster/session modules and decomposition tests pass. |
| M62-STRUCT-002 | Tech debt / GPT Pro | `OrchestratorService` still centralizes repository wiring and too many facade methods. | repaid | `services.py` is below 2600 lines and direct-method ratchet is <=120; deeper repository bundle cleanup can continue as non-blocking M67 debt. |
| M63-CLI-001 | M47 Opus / M52-M60 | `apps/operator_cli/main.py` remains a 1500+ line all-command module. | repaid | Command families moved to modules; command names remain compatible; `main.py <= 500` ratchet is covered. |
| M63-WEB-001 | GPT Pro / M48 Triage | Web UI remains a large Python HTML/CSS/JS string surface. | repaid | Render surface split into shell/components; `web_ui.py <= 700`, no `innerHTML`, and high-risk UI actions require receipt confirmation. |
| M63-CHAT-001 | M47 Opus / M52-M60 | `chat_runtime.py` still combines providers, fallback, builder, and reasoning filtering. | repaid | `packages.runtime_langgraph.chat_runtime` is now a package facade with old import compatibility and a facade line ratchet. |
| M63-CODEX-001 | Tech debt registry | Codex artifact-only dogfood roles could remain slow without role-level telemetry. | repaid | Dogfood artifact prompt is capped and Codex execution metadata records prompt family, prompt length, role, cluster, and member. |
| M64-CAP-001 | Tech debt / GPT Pro / M48 Triage | Capability health still lacks live probe evidence for every provider lane. | repaid | `CapabilityProbeResult` ledger, CLI, API health evidence, and live evidence paths are implemented. |
| M64-CAP-002 | User decision | MMX/Vertex/Claude/Codex/OpenCode/LangChain must be truly smoke-tested; degraded fallback is not completion. | repaid | `workflowctl capability probe --provider all --require-live` passed for shell, Codex, OpenCode, MMX, Vertex, Claude, and LangChain. |
| M65-SCHED-001 | Tech debt / GPT Pro | Scheduler-authority naming still overstates the real local lease semantics. | repaid | Public docs use `LocalSchedulerLeaseArbiter` local lease semantics; legacy scheduler-authority names are compatibility only. |
| M65-ROUTE-001 | M47 Opus / M52-M60 | Cluster route decisions are not persisted for 30-day stats. | repaid | Route decision ledger, `/cluster-routes/stats`, and `workflowctl scheduler route-stats` are implemented and tested. |
| M66-GOV-001 | M47 Opus / GPT Pro | GitHub/PR automation boundary can be overstated in docs. | repaid | Docs state the manual PR boundary: summaries can be generated, but commit/push/PR require explicit operator action. |
