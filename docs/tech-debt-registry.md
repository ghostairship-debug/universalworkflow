# 技术债登记表

本文档是人类可读的技术债摘要。结构化真相源是 [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)，治理 API/CLI 默认读取该 JSON；本文档用于快速理解当前还剩什么债、下一步为什么要处理它。

## 登记规则

- 只记录已经明确接受或在仓库中清晰观察到的债务。
- 不把未分析想法塞进这里。
- 每条债务必须说明引入位置、计划偿还阶段、当前状态和阻塞影响。
- 历史债务可以汇总，但不能在没有证据的情况下静默删除。

## 已偿还债务摘要

| ID | 描述 | 偿还阶段 | 结果 |
| --- | --- | --- | --- |
| TD-002 | preset 缺少确定性 suggestion 路径 | M1 | 已加入离线 deterministic suggestion |
| TD-003 | `HandoffLite` 只有契约没有持久化 | M1 | 已加入持久化和状态查询 |
| TD-005 | 执行路径过度依赖 shell-only lane | M5 | 已形成多 adapter baseline |
| TD-012 | offline validation 脚本过大 | Pre-M8 | 已拆为 `infra/validation/` |
| TD-018 | 文档混用绝对链接和历史/当前说明 | Pre-M8 | 已建立 portable links 和当前文档治理规则 |
| TD-006 | `optional` review policy 只是 reference-only | M9 | 已加入可执行 optional advisory review |
| TD-007 | run events / trace 缺少 replay-grade linkage | M9 | 已加入 replay packet 和 run metrics |
| TD-008 | durable pilot 缺少 interrupt/resume/checkpoint lineage | M9 | 已加入 durable lineage 和 reconciliation |
| TD-020 | Web operator UI 缺失 | M14 | 已加入 FastAPI Web operator surface |
| TD-021 | scheduler authority 第一版不完整 | M20 | 已加入 single-store quorum-style authority、fencing 和 cutover validation |
| TD-STRUCT-002 | M31 后 truth 分散在多个文档 | M32 / M38 | 已吸收到活跃中文真相源 |
| TD-STRUCT-004 | orchestration 仍携带 `project_delivery` 假设 | M33 | 已收缩到 shared orchestration service 和 canonical plan builder |
| TD-CODEX-CLI-001 | CodexAdapter prompt/参数顺序和 Windows 文本处理可能破坏模型选择或 artifact 输出 | M41 Phase 13 | 已改为 options-before-prompt、stdin prompt、UTF-8 decode 和 artifact 目录创建 |
| TD-DOGFOOD-002 | orchestration child failures 可被静默 approve | M41 Phase 13 | 已确保失败 child 在 fallback 前保留 failed/rejected 证据 |
| TD-MODEL-ACCESS-001 | 本机 Codex CLI 曾无法访问目标 dogfood 模型 | M41 Phase 13 | 已升级 npm `@openai/codex` 到 `0.125.0` 并完成 `gpt-5.5` smoke |
| TD-CODEX-PROCESS-001 | Windows 上 Codex CLI 的 node/native 子进程可能在 timeout 后残留并卡住 workflow | M42 | 已为真实 Codex CLI 路径加入进程树 timeout 清理，并用 8 秒 tree-timeout smoke 验证 |
| TD-SHELL-UTF8-001 | Windows ShellAdapter 用系统默认文本模式捕获输出，遇到中文/UTF-8 artifact stdout 可能解码失败 | M43 | 已改为 bytes 捕获并按 UTF-8/系统编码 fallback 解码 |
| TD-CLUSTER-GRAPH-001 | 动态多集群目标在 status detail 中只投影首个 cluster graph | M45/M46 | 已改为 composite cluster graph，保留全部 selected cluster |
| TD-STRUCT-001 | Orchestrator/CLI/Web/chat surface 过大 | M62/M63 | 已用 facade ratchet、interaction split、chat runtime package、CLI command families 和 Web UI receipt split 收口 |
| TD-STRUCT-003 | scheduler-authority 命名可能高估 consensus 语义 | M65/M66 | 已收敛为 `LocalSchedulerLeaseArbiter` local-first 语义，旧名称仅兼容 |
| TD-STRUCT-005 | capability health 缺少真实 runtime probe 支撑 | M64 | 已加入 `CapabilityProbeResult` ledger，并完成 all-provider require-live probe |
| TD-STRUCT-006 | M31 future platform objects 缺少 promotion path | M66 | 已归类为 archive/reference material；未来采用前必须另开治理任务 |
| TD-DOGFOOD-001 | 多 provider dogfood 仍依赖 degraded/fallback | M64 | 已完成 shell/Codex/OpenCode/MMX/Vertex/Claude/LangChain require-live probes |
| TD-CODEX-LATENCY-001 | Codex artifact-only prompt 偏大且缺少 role telemetry | M66 | 已收缩 dogfood artifact prompt，并在 metadata 中记录 role/prompt telemetry |
| TD-MULTIMODAL-001 | MMX/Vertex 缺少 live multimodal evidence | M64 | 已通过 require-live probe 产生真实 evidence，fallback 不再算完成 |

## 未偿还债务

| ID | 描述 | 引入 | 计划偿还阶段 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- | --- | --- |
| 无 | M61-M66 范围内可证实的阻塞性 open debt 已清零 | M66 | N/A | repaid | 新债务必须先进入 issue register，并附 evidence / unblock condition |

## M47 新观察

- M43 已用真实 PDF 生成商业化 HTML 游戏 vertical slice，并完成浏览器 smoke；这偿还了“PDF 输入能否转 artifact”的一部分债务。
- 自适应路由和动态多集群编排当前都是 opt-in。默认关闭是刻意选择，避免低成本模型在核心路径上静默改变行为。
- 下一轮优先级建议：真实 MMX/Vertex 输入、Workbench 中展示动态 route、继续收缩 `OrchestratorService`，以及让 adaptive route 采集真实成功率后再考虑默认启用。
