# M73 Preflight 与能力层开发计划

生成日期：2026-04-26

## 1. 背景

M72 已经完成可信自开发基线：workflow dogfood、scoped receipt、provider live proof、并发执行契约、文档真相源和 self-development manifest 都已经形成可检查闭环。

随后新增了两份外部评估：

- [Opus M73 深度评估](docs/archive/evaluations/PROJECT_DEEP_EVALUATION_M73_OPUS.md)
- [GPT M73 评估](docs/archive/evaluations/GPT_EVALUATION.md)

两份报告共同指出：M73 可以进入能力层，但不能直接堆新功能。进入能力开发前必须先补一轮 preflight，确认 closeout gates、LangGraph 口径、manifest 证据链和 optional 模块治理都不会误导后续 agent。

## 2. 合并判断

### 采纳 Opus 的硬提醒

Opus 的价值在于纠正 M73 自评过度乐观：

- `self-development-manifest` 目前主要检查证据完整性，不等于代码质量评估。
- M73 R2 只跑了 doc links、doctor、manifest、unit matrix 和治理子集，不能外推为全仓库无风险。
- LangGraph M68 是 advisory comparison，不是 runtime substrate。
- 仍有 optional cluster/scheduler/remote worker 模块需要 review/delete 条件。

但 Opus 的 severity 需要校准：

- 总 LOC 增长是治理信号，不宜直接定为 P0；更适合设置 production LOC ratchet。
- `core_domain/local_game_artifacts.py` shim 可以删除，但它是 quick win，不是阻塞级风险。

### 采纳 GPT 的路线结构

GPT 的价值在于给出 M73 能力层主线：

- Capability enforcement pilot：从观察式 policy decision 推进到一条真实执行路径强制门禁。
- MCP Broker v1：从 profile 白名单升级为 per-task tool projection。
- AutomationLease v0：把无人值守授权从单次 receipt 推进到有界、可撤销 lease。
- LangGraph real-runtime spike：只做 non-mutating checkpoint/resume/interrupt 验证，不急着接 mutation。
- Manifest v2 provenance：从“文件存在”升级到“证据链可追溯”。

## 3. M73 Preflight Gate

M73 能力开发前必须完成以下 gate。失败不伪装通过，而是写入 `M73_PREFLIGHT_EXECUTION_REPORT.md` 的 blocker 表。

| Gate | 命令 | 通过条件 |
| --- | --- | --- |
| Doc links | `python -m infra.scripts.check_doc_links` | 活跃文档 0 issue |
| Doctor strict | `workflowctl ... doctor --strict` | `status=ok` |
| Unit matrix | `workflowctl ... test matrix --suite unit` | return code 0 |
| Core matrix | `workflowctl ... test matrix --suite core` | return code 0 |
| Integration matrix | `workflowctl ... test matrix --suite integration` | return code 0 |
| Full validation | `workflowctl ... validation run --suite full --skip-offline-probe` | return code 0 且 fresh report |
| Slow pytest | `python -m pytest -q --run-slow` | return code 0 |
| Capability live probe | `workflowctl ... capability probe --provider all --require-live` | 所有 required provider 真 live proof 通过 |

Evidence 统一放入：

```text
state/m73_preflight_capability/evidence/
state/m73_preflight_capability/capability_probes/
```

## 4. Preflight Quick Wins

本轮先执行这些低风险修复：

1. 明确 M68 LangGraph 口径：M68 是 advisory comparison，不是 runtime substrate。
2. 删除已无调用的 `packages/core_domain/local_game_artifacts.py` shim。
3. 新增 `docs/governance/optional_modules.json`，为 scheduler/remote worker optional 模块登记 review/delete 条件。
4. 新增 `docs/archive/evaluations/README.md`，让历史评估不再是无索引材料堆。
5. README 增加简化架构图，帮助用户理解模块分层。
6. `self-development-manifest` 增加最小 provenance 字段，保留旧 JSON 兼容。

## 5. M73 能力层路线

Preflight 通过后，M73 不直接“扩能力数量”，而是先把能力控制面做实。

### M73A Capability Enforcement Pilot

目标：选择一条最小真实执行路径，把 M69 policy decision 从 evidence/CLI gate 推进到强制门禁。

建议路径：

```text
adapter_route + patch_apply + write_set + receipt + live proof
```

验收：

- 缺 live proof：拒绝 mutation。
- 缺 write_set：拒绝 mutation。
- 缺 receipt：返回 `needs_receipt` 或结构化 forbidden。
- 允许执行时写 execution receipt 和 ledger。

### M73B MCP Broker v1

目标：把 MCP 从 enabled profile 白名单推进到 per-task broker。

最低能力：

- canonical id：`mcp:{profile_id}:{tool_name}`
- `call_tool` 支持 canonical id。
- 同名 tool collision 测试。
- projection 支持 profile/tool selector。
- `include_mcp=True` 不再等于所有 enabled profiles。
- risk tier 和 schema budget 进入 projection manifest。

### M73C AutomationLease v0

目标：支持无人值守但有边界的长程任务授权。

最小字段：

- `lease_id`
- `workspace_root`
- `allowed_actions`
- `denied_actions`
- `write_set_allowlist`
- `expires_at`
- `max_resume_count`
- `max_fix_iterations`
- `status`

第一版允许：

- `resume_run`
- `batch_resume_runs`
- `run_tests`
- `write_artifact`
- advisory review approve

第一版继续禁止：

- git push / PR / publish
- secrets 操作
- workspace root 扩大
- 未声明外部副作用

### M73D LangGraph Real-Runtime Spike

目标：承认 M68 只是 advisory comparison，后续用一个 non-mutating real-runtime spike 验证 LangGraph 是否值得进入执行底座。

流程：

```text
Plan -> Review interrupt -> Resume -> Evidence
```

验收：

- checkpoint
- interrupt
- resume
- state inspection
- streaming event

仍然不接 patch apply，不引入第二套 mutation 状态源。

### M73E Manifest V2 Provenance

目标：从“文件存在”升级为“证据链可追溯”。

最小追踪字段：

- `task_card_paths`
- `evidence_paths`
- `operator_packet_paths`
- `execution_report_path`
- `state_directory_paths`
- `evidence_category_counts`
- `traceability_status`

后续再扩展：

- `task_card_id -> run_id -> evidence -> test_result -> commit_sha`

## 6. Workflow 执行规则

M73 继续使用 workflow 共同开发：

- 每个 phase 至少多张 task card；单卡必须 `single_card_exception`。
- 每个 phase 前跑 `plan-graph`、`policy-preview`、`goal-packet`。
- artifact-only 和 disjoint write_set 才允许并发。
- write_set conflict、dirty worktree、SQLite lock、repo mutation 异常时降级串行。
- workflow 自身 bug 优先于业务 phase。
- 成功 phase 可提交；失败 phase 不提交，只保留 evidence 和恢复指针。

## 7. GO/NO-GO

M73 capability work 的 GO 条件：

- Preflight gates 全部有 fresh evidence。
- 任何失败 gate 都有 blocker 和解除条件。
- M68 口径已改为 advisory comparison。
- optional 模块已有 review/delete 条件。
- manifest provenance v1 已落地且旧 manifest 消费方不破。

如果 capability live probe 或 slow/full gate 失败，M73 仍可继续做不依赖该 provider 的本地治理/设计任务，但不得宣布“能力层全量 GO”。
