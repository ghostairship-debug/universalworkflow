# 技术债登记表

本文档是人类可读的技术债摘要。结构化真相源是 [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)，治理 API/CLI 默认读取该 JSON；本文档用于快速理解当前还剩什么债、下一步为什么要先做 M38 自用硬化。

# 1. 登记规则

- 只记录已经明确接受或在仓库中清楚观察到的债务。
- 不把未分诊想法塞进这里。
- 每条债务必须说明引入位置、计划偿还阶段、当前状态和阻塞影响。
- 历史债务可以汇总，但不能在没有证据的情况下静默删除。
- 当前没有打开 post-`M37` phase；下一阶段建议通过 `M38 Phase 0` 正式打开。

# 2. 已偿还债务

| ID | 描述 | 引入 | 偿还 | 结果 |
| --- | --- | --- | --- | --- |
| TD-002 | preset 缺少确定性 suggestion 路径 | M0 | M1 | 已加入离线 deterministic suggestion |
| TD-003 | `HandoffLite` 只有契约没有持久化 | M0 | M1 | 已加入持久化和状态查询 |
| TD-004 | compile 只是内部占位 | M0 | M1 | 已加入公开 lifecycle surface |
| TD-005 | 执行路径过度依赖 shell-only lane | M0 | M5 Phase 3 | 已形成多 adapter baseline |
| TD-011 | `services.py` 过度集中编排、投影、生命周期逻辑 | M2-M7 | Pre-M8 Phase C | 已抽出部分 service modules，但 facade 债务仍以 `TD-STRUCT-001` 继续存在 |
| TD-016 | subprocess adapter 缺少 timeout 和环境隔离 | M5-M7 | Pre-M8 Phase B | 已加入 timeout、env allowlist 和 trust-boundary 说明 |
| TD-012 | offline validation 脚本过大 | M5-M7 | Pre-M8 Phase D | 已拆为 `infra/validation/` |
| TD-013 | runtime brief / memory retrieval 缺少 context-budget preflight | M5-M7 | Pre-M8 Phase D | 已加入 context budget 和 gateway preflight |
| TD-014 | 依赖上界过窄 | M5-M7 | Pre-M8 Phase E | 已选择性放宽核心运行依赖 |
| TD-015 | governance report 直接解析 Markdown prose | M3-M7 | Pre-M8 Phase D | 已加入 canonical JSON source |
| TD-017 | source-package/export 会带入本地噪音 | M5-M7 | Pre-M8 Phase E | 已加入 manifest/export 工具 |
| TD-018 | 文档混用绝对链接和历史/当前说明 | M1-M7 | Pre-M8 Phase E | 已清理 portable links 并建立文档治理规则 |
| TD-006 | `optional` review policy 只是 reference-only | M0 | M9 | 已加入可执行 optional advisory review |
| TD-007 | run events / trace 缺少 replay-grade linkage | M0 | M9 | 已加入 replay packet 和 run metrics |
| TD-008 | durable pilot 缺少 interrupt/resume/checkpoint lineage | M0 | M9 | 已加入 durable lineage 和 reconciliation |
| TD-010 | governance visibility 缺少量化指标 | M0 | M9 | 已加入 governance metrics / alerts |
| TD-001 | claim/worker lease 缺少 ownership topology | M0 | M10 | 已加入 claim/worker ownership topology |
| TD-009 | 执行语义 serial-first，缺少 local batch barrier | M0 | M10 | 已加入 local batch barrier 和 batch resume |
| TD-020 | Web operator UI 缺失 | M5-M13 | M14 | 已加入 FastAPI Web operator surface |
| TD-019 | remote worker pool 不成熟 | M10 | M15 | 已加入单 control-plane remote HTTP worker pools |
| TD-021 | scheduler authority 第一片不完整 | M15 | M20 | 已加入 single-store quorum-style authority、fencing 和 cutover validation |
| TD-STRUCT-002 | M31 后 truth 分散在多个文档 | M31 | M32 Phase 0 | 已吸收到 freeze review / archive；本轮又进一步收束为中文活跃真相集 |
| TD-STRUCT-004 | orchestration 仍携带 `project_delivery` 假设 | M30-M31 | M33 Phase 0 | 已收缩到 shared orchestration service 和 canonical plan builder |

# 3. 未偿还债务

| ID | 描述 | 引入 | 计划偿还阶段 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- | --- | --- |
| TD-STRUCT-001 | `OrchestratorService` 仍是巨型 facade，集中跨平面 wiring 和大量 helper 逻辑 | M31 | M38 | partially_repaid | 阻塞服务边界诚实性和后续安全抽取 |
| TD-STRUCT-003 | scheduler-authority 内部表名、事件名和旧措辞仍带有过强 consensus 暗示 | M20-M31 | bounded carry-forward | partially_repaid | 阻塞语义诚实和 operator 理解 |
| TD-STRUCT-005 | capability health 仍部分依赖 descriptor，尚未被完整 runtime telemetry 支撑 | M30-M31 | M38-M39 | active | 阻塞可信 capability readiness 和路由决策 |
| TD-STRUCT-006 | M31 bundle/ZIP 的未来平台对象仍是 reference material，缺少治理式 promotion path | M31 | M39 | partially_repaid | 阻塞未来对象安全进入主线类型系统 |

# 4. Freeze Review 问题

1. 当前 active phase 是否已经正式打开？
2. 是否有未偿还技术债阻塞下一阶段入口？
3. 新功能是否会继续扩大 `OrchestratorService`？
4. capability health、执行证据和失败原因是否足够支持个人长期自用？
5. 已关闭阶段的历史结论是否已经吸收到活跃中文文档，而不是继续保留分散材料？
