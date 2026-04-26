# 技术债登记表

结构化真相源是 [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)。本文档只提供人类可读摘要；治理 API/CLI 默认读取 JSON。

## 登记规则

- 只登记已经明确接受或在仓库中清晰观察到的债务。
- 不把未分析想法塞进登记表。
- 每条债务必须说明引入位置、计划偿还阶段、当前状态和阻塞影响。
- 历史债务可以汇总，但不能在没有证据的情况下静默删除。
- 不再使用“项目零债”的表达；只说明 blocking debt 是否清零，以及 carry-forward debt 是否阻塞下一阶段。

## 当前结论

- M73-M76 已补齐 workflow dogfood、capability control、MCP broker、AutomationLease、Pipeline 最小入口、Cocos E2E 生成与验证路径。
- 所有 closeout 硬闸门已通过：doc links、doctor strict、unit/core/integration test matrix、workflowctl validation full、all-provider require-live probe、`pytest --run-slow`。
- 当前仍保留非阻塞结构维护债：大型 repository/service 文件仍偏大，但没有阻塞能力层继续开发；后续应在真实能力开发触发痛点时按 bug-first 原则继续偿还。

## 已偿还债务摘要

| ID | 描述 | 偿还阶段 | 结果 |
| --- | --- | --- | --- |
| TD-STRUCT-001 | Orchestrator/CLI/Web/chat surface 过大 | M62/M63 | facade ratchet、interaction split、chat runtime package、CLI command family、Web UI split 已落地 |
| TD-STRUCT-003 | scheduler-authority 命名可能高估 consensus 语义 | M65/M66 | 已收敛为 `LocalSchedulerLeaseArbiter` local-first 语义，旧名称仅兼容 |
| TD-STRUCT-005 | capability health 缺少 runtime probe 支撑 | M64 | 已加入 `CapabilityProbeResult` ledger，并完成 all-provider require-live probe |
| M67-SEC-001 | `OperatorActionReceipt` 缺少 request scope 绑定 | M67 P2 | 已加入 `scope_hash` / `scope_payload` 并覆盖 tamper / legacy receipt 拒绝 |
| M67-PROBE-001 | capability probe 可能误收 simulated/dry-run/fallback evidence | M67 P3 | 已加入 provider-specific live-proof contract |
| M67-VAL-001 | offline validation 缺少 shard/freshness/timeout 失败报告 | M67 P4 | 已加入 quick/full/shard、timeout trace、last-command 报告 |
| M67-WEB-001 | Web UI 仍依赖 inline CSP 例外和 `innerHTML` 路径 | M67 P5 | 已静态化 operator CSS/JS、移除 CSP `unsafe-inline`、替换 `.innerHTML` 清空路径 |
| M67-SCHED-001 | scheduler 默认文档和 flag-off boot path 未完全 local lease 化 | M67 P6 | 已改为 local scheduler lease arbiter 默认语义，并验证 flag-off 不进入 legacy cluster runtime |
| M67-WF-001 | workflow 自身参与开发缺少完整 proof | M67 P8 | 已用 workflow 跑 simple/medium/complex 任务并生成 manifest/operator packet |
| M73-CAP-001 | capability policy/live proof/write_set/receipt 缺少统一强制入口 | M73 | 已加入 capability enforcement pilot 和 `CapabilityInvocation` contract |
| M73-MCP-001 | MCP include_mcp 可能暴露全部 profile | M73 | 已加入 canonical tool id、selector、collision guard，未显式 selector 时不暴露全部 MCP |
| M73-AUTO-001 | 无人值守 resume/batch/test/artifact 写入缺少有界授权 | M73 | 已加入 file-backed `AutomationLease` |
| M74-PIPE-001 | Pipeline 概念缺少正式 contract | M74 | 已加入 `WorkflowPipeline` / `PipelineStage` contract 与 preview |
| M75-PIPE-EXEC-001 | Pipeline 缺少最小执行入口 | M75 | 已加入串行 `workflowctl pipeline run` |
| M76-COCOS-001 | H5 游戏 pipeline 缺少真实 Cocos E2E evidence | M76 | 已加入 `workflowctl game cocos-e2e`，生成 Cocos Creator 项目、构建 Web Mobile、浏览器 playtest |

## 当前未偿还债务

| ID | 描述 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- |
| M67-CARRY-001 | `repositories.py`、`service_lifecycle.py`、`service_projection.py`、`interaction_catalog.py`、`models.py` 仍偏大 | carry_forward | 非阻塞维护债；只有在后续能力开发中造成真实痛点时继续拆分 |

## M76 收口说明

- 根目录当前保留 M73-M76 最终方案、执行报告和两轮 M76 后评估。
- capability readiness 不接受 fallback-only、generic greeting、simulated 或 dry-run 作为 `verified_ready`。
- 动态/自适应路由仍为 opt-in；是否 default-on 必须另开 telemetry 决策。
- GitHub/PR 能力边界保持诚实：系统可生成 PR-ready summary，但不会自动 commit/push/PR，除非 operator 明确要求。
