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

## 未偿还债务

| ID | 描述 | 引入 | 计划偿还阶段 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- | --- | --- |
| TD-STRUCT-001 | `OrchestratorService` 仍是大型 facade，集中跨平面 wiring 和大量 helper 逻辑 | M31 | 持续偿还 | partially_repaid | 阻塞服务边界诚实性和后续安全抽取 |
| TD-STRUCT-003 | scheduler-authority 内部表名、事件名和旧措辞仍带有过强 consensus 暗示 | M20-M31 | bounded carry-forward | partially_repaid | 阻塞语义诚实和 operator 理解 |
| TD-STRUCT-005 | capability health 仍部分依赖 descriptor，尚未被完整 runtime telemetry 支撑 | M30-M31 | M43+ | active | 阻塞可信 capability readiness 和路由决策 |
| TD-STRUCT-006 | M31 bundle/ZIP 的未来平台对象仍是 reference material，缺少治理式 promotion path | M31 | M43+ | partially_repaid | 阻塞未来对象安全进入主线类型系统 |
| TD-DOGFOOD-001 | workflow dogfood 已有真实 Codex CLI E2E 和 M42 cluster smoke，但 MMX/Claude 仍主要是 degraded/fallback 验证 | M41 | M43+ | partially_repaid | 阻塞声称完整多 agent 能力层已经生产可用 |
| TD-CODEX-LATENCY-001 | Codex CLI review/doc artifact-only 角色仍可能慢，当前靠 timeout/fallback 控制风险 | M41 Phase 13 | M43+ | active | 放慢个人 dogfood loop，影响 role-level telemetry 解读 |
| TD-MULTIMODAL-001 | MMX/Vertex 已建模为多模态 evidence lane，但真实 PDF/image 提取尚未完整 E2E 验收 | M41 | M43+ | active | 阻塞复杂多模态项目输入的自动可信处理 |

## M42 新观察

- 五类新 cluster 已完成 catalog、router、强 dogfood 解析和 smoke 验证，但它们仍是“可路由、可执行、可 fallback”的第一版，不代表每个角色的 prompt 都已经高质量。
- `management_cluster` 已完成真实 smoke：`run_665006c2016d` 根 run completed；失败 Codex 子 run 会在约 8 秒硬超时并 fallback，不再残留子进程。
- 下一轮优先级建议：先用真实 PDF/截图做 `multimodal_cluster` 验收，再用低频 Claude gate 验证 architecture handoff，最后继续收缩 `OrchestratorService`。
