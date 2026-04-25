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
| M67-SEC-001 | `OperatorActionReceipt` 缺少 request scope 绑定 | M67 P2 | 已加入 `scope_hash` / `scope_payload`，并覆盖 run/body/session/batch tamper 和 legacy receipt 拒绝 |

## 未偿还债务

M61-M66 计划内债务已经收口，但 M67 重新登记了当前仍可证实的问题。这里不再使用“项目零债”的表达；阻塞项在 M67 关闭前会让治理报告返回 blocking alert。

| ID | 描述 | 引入 | 计划偿还阶段 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- | --- | --- |
| M67-WF-001 | workflow 自身参与开发的 task-card / route / evidence / operator-packet 证据仍需跑完整 | M67 intake | M67 | blocking_open | 阻塞后续能力层开发的可信共同开发基线 |
| M67-PROBE-001 | capability live probe 对非 Codex/OpenCode provider 仍可能接受 simulated / dry-run / generic evidence | M64/M66 capability closeout | M67 P3 | blocking_open | 阻塞 provider readiness 和自适应路由可信度 |
| M67-VAL-001 | offline validation 缺少 shard/freshness/timeout 失败报告硬门禁 | M61-M66 validation closeout | M67 P4 | blocking_open | 门禁超时或中断时可能误读 stale success |
| M67-WEB-001 | Web UI 仍依赖 inline CSP 例外，contribution game template 仍有 `innerHTML` browser surface | M63/M66 Web split | M67 P5 | blocking_open | 削弱 receipt-gated 浏览器安全兜底 |
| M67-SCHED-001 | scheduler 默认文案和 flag-off boot path 尚未完全收敛到 local lease arbiter 语义 | M65/M66 scheduler rename | M67 P6 | blocking_open | 容易误解默认提供分布式 authority/consensus |
| M67-ARCH-001 | M67 指定热点文件仍需瘦身并拆出 `RepositoryBundle` / `WorkerRuntimeBundle` / infra test matrix | M62-M66 carry-forward | M67 P7 | blocking_open | 阻塞恢复能力层开发前的结构基线 |
| M67-AUTO-001 | `execute=true` / auto-apply 等自动化边界缺少统一 Command / PolicyEngine / AutomationLease 语义 | M67 autonomy-policy evaluation | M67 P2/P5 | blocking_open | 阻塞安全长程自开发，不应靠路由各自判断 |
| M67-ROUTE-001 | 动态/自适应路由只有 P0 预演，还需要 simple/medium/complex E2E 和并发 batch-resume proof | M67 workflow-dogfood plan | M67 P8 | blocking_open | 阻塞声明 MiniMax/OpenCode/adaptive routing 可支撑真实共同开发 |
| M67-CARRY-001 | `repositories.py`、`service_lifecycle.py`、`service_projection.py`、`interaction_catalog.py`、`models.py` 仍偏大 | M47-M66 structure evaluation | Post-M67 decision | carry_forward | 非阻塞维护债；M67 后按实际疼痛决定是否继续拆 |

## M67 评估吸收

- 两份根目录 M66 评估和 `AGENTS_M67_universalworkflow.md` 已被吸收到 M67 issue register；原始文件在 M67 closeout 前保留，closeout 时归档。
- M67 是一个完整 milestone，内部用 P0-P8 表达阶段；从本轮开始恢复 1 phase 1 commit 的审计纪律。
- 自适应路由和动态多集群编排本轮必须形成真实 evidence。P0 预演已经证明复杂 lane 会路由到 `opencode + minimax/MiniMax-M2.7`，P8 还必须跑 simple/medium/complex 真实任务和一次 `batch-resume --max-workers 2`。
- capability readiness 不再接受 fallback-only、generic greeting、simulated 或 dry-run 作为 `verified_ready`。
