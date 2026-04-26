# 技术债登记表

本文档是人类可读的技术债摘要。结构化真相源是 [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)，治理 API/CLI 默认读取该 JSON。

## 登记规则

- 只登记已经明确接受或在仓库中清晰观察到的债务。
- 不把未分析想法塞进这里。
- 每条债务必须说明引入位置、计划偿还阶段、当前状态和阻塞影响。
- 历史债务可以汇总，但不能在没有证据的情况下静默删除。
- 不再使用“项目零债”的表达；只说明 blocking debt 是否清零，以及 carry-forward debt 是否阻塞下一阶段。

## 当前结论

- M67-M72 阻塞可信使用的债务已经收口。
- M73 可以恢复能力层开发。
- 仍保留非阻塞结构维护债：若能力开发中真实触发痛点，再按 bug-first 原则拆成新的偿还 phase。

## 已偿还债务摘要

| ID | 描述 | 偿还阶段 | 结果 |
| --- | --- | --- | --- |
| TD-STRUCT-001 | Orchestrator/CLI/Web/chat surface 过大 | M62/M63 | facade ratchet、interaction split、chat runtime package、CLI command families、Web UI split 已落地 |
| TD-STRUCT-003 | scheduler-authority 命名可能高估 consensus 语义 | M65/M66 | 已收敛为 `LocalSchedulerLeaseArbiter` local-first 语义，旧名称仅兼容 |
| TD-STRUCT-005 | capability health 缺少真实 runtime probe 支撑 | M64 | 已加入 `CapabilityProbeResult` ledger，并完成 all-provider require-live probe |
| M67-SEC-001 | `OperatorActionReceipt` 缺少 request scope 绑定 | M67 P2 | 已加入 `scope_hash` / `scope_payload` 并覆盖 tamper / legacy receipt 拒绝 |
| M67-PROBE-001 | capability live probe 可能误收 simulated / dry-run / generic / fallback-only evidence | M67 P3 | 已加入 provider-specific live-proof contract 并通过全量 require-live probe |
| M67-VAL-001 | offline validation 缺少 shard/freshness/timeout 失败报告硬门禁 | M67 P4 | 已加入 quick/full/shard、timeout trace/last-command 报告和 Windows-safe result file transfer |
| M67-WEB-001 | Web UI 仍依赖 inline CSP 例外，game template 仍有 `innerHTML` browser surface | M67 P5 | 已静态化 operator CSS/JS、移除 CSP `unsafe-inline` 并替换 `.innerHTML` 清空路径 |
| M67-SCHED-001 | scheduler 默认文案和 flag-off boot path 未完全收敛到 local lease arbiter | M67 P6 | 已改为 local scheduler lease arbiter 默认文案，并验证 flag-off 不 import legacy cluster runtime/support |
| M67-ARCH-001 | M67 热点文件和默认启动路径仍偏重 | M67 P7 | 已抽出 repository/worker bundle、service mixin、game template split 和 infra test matrix wrapper |
| M67-WF-001 | workflow 自身参与开发缺少完整 proof | M67 P8 | 已用 workflow 跑 simple/medium/complex 任务并生成 manifest/operator packet |
| M67-AUTO-001 | `execute=true` / auto-apply 等自动化边界缺少统一可审计授权 | M67 P2/P5/P8 | 高风险动作已收敛到 scoped `OperatorActionReceipt` |
| M67-ROUTE-001 | 动态/自适应路由和并发执行缺少真实 E2E proof | M67 P8 | 已完成 MiniMax/OpenCode simple、DeepSeek medium、Codex fallback、cluster_parallel complex 和 batch-resume evidence |
| M69-CONTROL-001 | capability policy/live proof/write_set/receipt 缺少统一 control-plane decision | M69 | 已新增 capability control-plane decision，并写入 invocation envelope / execution receipt |
| M70-PROVIDER-001 | Vertex、gcloud、Gemini CLI 和 provider contract 边界不清 | M70 | 已新增 provider contract registry 和 CLI，明确 Gemini CLI 未接入、gcloud 不是 worker adapter |
| M71-CONCURRENCY-001 | batch-resume 缺少并发前审计、串行降级和 partial failure resume | M71 | 已加入 parallel batch contract、write_set/dirty/SQLite 审计和恢复指针 |
| M72-GOV-001 | workflow 自开发证据和 task-card 规则缺少机器可检查入口 | M72 | 已新增 self-development manifest，检查 reports、task cards、evidence、operator packets 和 `single_card_exception` 规则 |

## 未偿还债务

| ID | 描述 | 引入 | 计划偿还阶段 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- | --- | --- |
| M67-CARRY-001 | `repositories.py`、`service_lifecycle.py`、`service_projection.py`、`interaction_catalog.py`、`models.py` 仍偏大 | M47-M66 structure evaluation | M73+ capability-driven maintenance | carry_forward | 非阻塞维护债；只有在能力开发中造成真实疼痛时才继续拆 |

## M72 收口说明

- 根目录 M66/M67 长期路线图和评估材料已归档到 [docs/archive/evaluations/](archive/evaluations/)。
- `workflowctl governance self-development-manifest` 是 M67-M72 自开发证据完整性的机器检查入口。
- capability readiness 不再接受 fallback-only、generic greeting、simulated 或 dry-run 作为 `verified_ready`。
- 动态/自适应路由仍为 opt-in；是否 default-on 必须另开 telemetry 决策。
