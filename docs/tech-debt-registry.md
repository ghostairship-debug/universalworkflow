# M1 技术债登记簿

**文档定位：** 记录在 M1 结束时仍然被显式接受、但延后到后续阶段偿还的技术债务，同时保留已在 M1 偿还的 M0 债务历史。  
**使用方式：** 本文档应在 `M1 freeze review` 中作为必审材料，所有 `go / no-go` 结论都必须显式检查本表是否完整。

---

# 1. 登记规则

- 只登记已经被明确接受的延后项
- 不登记“尚未分析清楚”的开放问题
- 每条债务都必须标明引入阶段、计划偿还阶段和阻塞影响
- 如偿还阶段变化，必须更新本表而不是只在会议中口头说明

---

# 2. M1 已偿还债务

| ID | 债务描述 | 引入阶段 | 偿还阶段 | 结果 |
| --- | --- | --- | --- | --- |
| TD-002 | `PresetResolver` 仅支持 `manual_select`，不提供建议 | M0 | M1 | 已补齐确定性离线 `suggest()`，但仍不做自动代选 |
| TD-003 | `HandoffLite` 仅冻结语义，不进入持久化范围 | M0 | M1 | 已持久化并进入 `status-detail`、`handoffs`、smoke 与 offline validation |
| TD-004 | thin compile 仅是内部占位能力，不暴露公共 compile API | M0 | M1 | 已补齐 `compile / recompile / resume` 公共生命周期接口 |

---

# 3. M1 后仍然有效的技术债

| ID | 债务描述 | 引入阶段 | 计划偿还阶段 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- | --- | --- |
| TD-001 | 仅有本地 claim / worker-lease 基线，仍未执行真实分布式资源占用控制 | M0 | M2 | 部分偿还 | 已具备本地 ownership 守卫与诊断，但仍阻塞真正的并发安全与冲突调度 |
| TD-005 | 仅接入 `ShellAdapter`，未接第二执行器与能力路由 | M0 | M1.5 | 已偿还 | 已补齐 `NoopAdapter`、`WorkerRouter` 与显式 task-kind 路由验证 |
| TD-006 | review policy 仍然缺少完整 richer policy 体系 | M0 | Next Cycle | 部分偿还 | 已补齐结构化 review-policy governance report、decision-table 基线，以及 `recommended` / `mandatory` 的 run-level runtime 语义；`optional` 在当前周期 freeze 时明确保留为 next-cycle candidate |
| TD-007 | `run_events` 仍然只承载最小摘要 payload，不承载完整 trace 与 metrics | M0 | M3 | 部分偿还 | 已补齐 summary / timeline digest、richer event inspection、closure-audit 与 run audit-report 基线，但仍阻塞深度 observability 与 replay 能力 |
| TD-008 | 运行时只实现本地 resumable 主链，不实现复杂 interrupt / resume / checkpoint merge | M0 | M2 | 部分偿还 | 已补齐 reconcile、snapshot、claim、worker-lease 与 runtime-attempt 基线，但仍阻塞复杂运行时恢复 |
| TD-009 | 系统仍采用串行执行语义，尚未进入 Claim / Lease / Barrier 的真实并发实现 | M0 | M2 | 部分偿还 | 已具备本地 claim / worker-lease 语义，但仍阻塞安全并发执行 |
| TD-010 | 技术债只以本登记簿管理，尚未接入自动化校验或 dashboard | M0 | M3 | 部分偿还 | 已通过结构化 governance report、summary、event inspection、run audit-report、review materials、release-readiness report 与 offline validation 补强治理基线，但仍阻塞技术债量化跟踪与 dashboard 化 |

---

# 4. Freeze Review 必查问题

在 M1 Freeze Review 中，必须逐条回答：

1. 当前延后项是否都已经登记
2. 是否存在未登记但实际被后移的工作
3. 每条债务的偿还阶段是否仍然合理
4. 是否有任何债务已经从“可接受”升级为“阻塞进入 M2”

---

# 5. 更新约束

- 新增债务时必须补充 ID、阶段和影响
- 偿还债务时不得直接删除，应先在 review 中确认，再从表中移除或转入历史记录
- 如果 M1 结束时本表为空，通常说明文档登记不完整，而不是技术债真的不存在
