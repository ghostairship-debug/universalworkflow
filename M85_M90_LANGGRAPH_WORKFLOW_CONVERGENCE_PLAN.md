# M85-M90 LangGraph 与 Workflow 长线收敛开发方案

## Summary

本方案把下一阶段主线从“继续堆垂直能力”调整为“先收敛编排底座”。商业化 Cocos/H5 游戏仍是正式业务方向，但不作为 M85-M90 的优先目标；它会在编排底座稳定后作为压力测试和业务验证场景。

核心判断：

- 当前仓库已经自研了大量调度、checkpoint、review gate、恢复、并发、route/evidence/operator packet 能力。
- LangGraph 已经提供状态图、checkpoint/persistence、human-in-the-loop、time travel、fault tolerance、subgraph、多 agent 编排、streaming 等通用能力。
- 继续纯自研会继续重复造轮子；但完全替换 workflow 也不合理，因为本项目的安全边界、provider truth、repo mutation、evidence/governance 是本地产品核心。

长期架构目标：

```text
Universal Workflow = 本地安全控制面 + provider truth + repo mutation + evidence/governance + CLI/Web 产品壳
LangGraph = 状态机 + checkpoint/resume + human interrupt + multi-agent/subgraph + repair loop + graph observability
```

M85-M90 的目标不是大规模新增 provider，也不是马上交付商业化游戏成品，而是建立一个能长期承载代码开发、游戏生产、资产生成、评审返工和长程自动化的可恢复编排内核。

## Non-Goals

- 不把本项目改成公开 SaaS、多租户平台或 LangGraph Platform 托管服务。
- 不用 LangGraph 替代 `OperatorActionReceipt`、`AutomationLease`、workspace root、write_set audit、provider live proof。
- 不在本阶段接入 OpenCode 免费模型池管理、Gemini CLI、视频生成、真实广告 SDK、IAP、在线排行榜或后端账号系统。
- 不把当前 Cocos scaffold 声明为商业化可玩成品。
- 不为了“迁移”而删除稳定运行的 workflow CLI/API/Web 外壳。

## Current State

### Workflow 已有能力

- run 生命周期、task card、route preview、operator packet、evidence。
- receipt/lease 高风险动作门禁。
- repo mutation / patch apply / write_set。
- provider live proof、capability health、route stats。
- pipeline preview/run 和 stage evidence。
- test matrix、offline validation、active truth check。
- Cocos game pipeline scaffold、asset factory、MMX/GCP/Vertex 资产链路。

### LangGraph 当前接入

- `ChatControlGraph`：聊天控制路径，能用 LangGraph 编译，失败时回退线性图。
- `FocusedLangGraphRuntime`：planning/review/evidence advisory comparison，不允许 mutation。
- `LangGraphDurableRuntimePilot`：flag-gated checkpoint pilot，当前仍是局部试点。
- `pyproject.toml` 已依赖 `langgraph>=1.0.0,<2.0.0`。

### 当前主要风险

- 编排能力继续自研会和 LangGraph 的 checkpoint、interrupt、subgraph、multi-agent、time travel 重叠。
- workflow 的本地安全控制面和 LangGraph 的执行图边界尚未形成清晰合同。
- LangGraph 目前没有接入 provider truth、receipt、write_set 和 evidence 语义，不能直接接管高风险执行。
- 商业化游戏 pipeline 的质量问题更多来自生产线结构和验收闭环，不是单纯缺模型。

## Migration Principles

| 能力 | 策略 | 说明 |
| --- | --- | --- |
| receipt / lease | keep | 本项目安全协议，不迁移给 LangGraph |
| workspace root / write_set audit | keep | repo mutation 安全核心 |
| provider live proof / capability health | keep | LangGraph 不负责 provider 真实性 |
| task card / operator packet / evidence manifest | keep + map | 保留治理格式，映射为 graph state/evidence |
| CLI/API/Web local control plane | keep | 产品外壳与本地运行入口 |
| phase 状态推进 | migrate gradually | 用 `StateGraph`/conditional edges 承担可恢复状态机 |
| checkpoint/resume | migrate gradually | 用 LangGraph checkpointer 承担图状态恢复 |
| review gate / human approval | wrap | LangGraph interrupt 暂停，workflow receipt 授权 |
| 并发 task cards | wrap/migrate | graph fan-out 可用，但 write_set 冲突仍由 workflow 判断 |
| repair loop | migrate | 用 conditional routing 和 checkpoint 分叉表达返工循环 |
| multi-agent 编排 | migrate | supervisor/subgraph/handoff 比继续手写 cluster 更合适 |
| long-term memory | evaluate | LangGraph Store 可用，但不替代 active truth/governance |

## Milestone Plan

### M85: LangGraph Fit Audit And Boundary Contract

目标：停止盲目扩功能，先建立“哪些迁移、哪些保留、哪些包一层”的事实表。

Phase 1：能力盘点

- 读取 services、pipeline、scheduler、interaction、capability、worker adapter、test matrix。
- 输出 `docs/architecture/langgraph_fit_matrix.md`。
- 每个现有编排能力标记 `keep / wrap / migrate / delete / later`。

Phase 2：边界合同

- 新增 `WorkflowGraphState` 草案：run_id、phase_id、task_cards、write_set、receipt_state、capability_proof、evidence_refs、failure_class。
- 新增 `WorkflowGraphNodeResult` 草案：status、side_effect_level、evidence_path、next_action。
- 明确 graph node 不直接绕过 workflow 高风险动作。

Phase 3：兼容策略

- 定义 LangGraph execution kernel 与现有 `WorkflowPipeline` 的映射关系。
- 保留 `workflowctl run plan-graph / policy-preview / goal-packet`，新增 graph preview 作为补充。
- 验证 active truth、doc links、targeted tests。

Acceptance：

- 有迁移矩阵。
- 有边界合同。
- 没有高风险动作被 LangGraph 直接执行。
- 文档明确商业游戏不是当前优先主线。

### M86: LangGraph Execution Kernel v1

目标：让一个低风险 pipeline 真正跑在 LangGraph execution kernel 上，但仍由 workflow 记录 evidence。

Phase 1：最小图内核

- 实现 `packages/runtime_langgraph/execution_kernel.py`。
- 节点：`plan -> policy_review -> execute_artifact_only -> validate -> evidence -> closeout`。
- 默认只允许 artifact-only；patch/repo mutation 直接 blocked。

Phase 2：CLI 入口

- 新增或扩展：`workflowctl graph preview`、`workflowctl graph run --artifact-only`。
- 输出 graph state snapshot、node timings、evidence manifest。

Phase 3：与现有 pipeline 对齐

- 选择一个 docs/governance 低风险任务作为 dogfood。
- task card、operator packet、route evidence 仍按 workflow 规则输出。

Acceptance：

- LangGraph kernel 能真实执行一个 artifact-only 流程。
- graph evidence 与 workflow evidence 可互相追踪。
- 失败不会留下半执行状态。

### M87: Human-In-Loop Interrupt And Receipt Fusion

目标：把 LangGraph interrupt 与 workflow receipt/lease 融合，解决“暂停/恢复/审批”重复造轮子问题。

Phase 1：interrupt contract

- 定义 `HumanApprovalInterrupt`：requested_action、scope_payload、write_set、risk_level、operator_hint。
- LangGraph 只负责暂停和恢复；授权仍由 receipt/lease 判断。

Phase 2：receipt fusion

- graph resume 时必须消费 scope-bound receipt。
- receipt scope mismatch、expired、workspace mismatch、write_set mismatch 均拒绝。

Phase 3：UI/API/CLI 映射

- Web/CLI 展示 interrupt pending 状态。
- 保留现有高风险 action API 兼容。

Acceptance：

- 无 receipt 的 mutation graph 不能继续。
- 错 receipt 不能继续。
- 正确 receipt 可恢复 graph 并写 evidence。

### M88: Checkpoint, Time Travel, And Repair Loop

目标：用 LangGraph checkpoint/time travel 表达长期任务恢复、失败返工和分叉探索。

Phase 1：persistent checkpointer

- 从当前 in-memory pilot 升级到可持久化 checkpointer。
- 初期可用 SQLite/file-backed adapter；如 LangGraph 官方 checkpointer 满足需求，优先复用。

Phase 2：time travel / fork

- 支持从某个 checkpoint 重新进入 review 或 validation。
- 不重放已成功且不需要重跑的 evidence-only 节点。

Phase 3：repair loop

- 建立通用循环：`execute -> validate -> diagnose -> repair_plan -> execute`。
- 设置最大修复轮次、失败分类、人工介入条件。

Acceptance：

- 中断后可恢复。
- validation 失败可进入修复循环。
- 失败 evidence 不被覆盖。
- 能从 checkpoint 生成分叉 evidence。

### M89: Multi-Agent Subgraph And Routing Convergence

目标：把 simple/medium/complex lane、review agent、validation agent 从手写 cluster 逐步收敛到 graph/subgraph。

Phase 1：agent role graph

- 定义 `PlannerAgent`、`ImplementerAgent`、`ReviewerAgent`、`ValidatorAgent` 的 graph state contract。
- agent 输出只允许 proposal/evidence；repo mutation 仍走 workflow gate。

Phase 2：routing integration

- simple lane：OpenCode/MiniMax 仍可用，但免费模型池管理暂不接入。
- medium lane：DeepSeek V4 Flash；失败直接 Codex。
- complex lane：Codex。
- route decision 写入 provider route stats。

Phase 3：parallelism

- artifact-only subgraph 可以并发。
- disjoint write_set patch 仍必须通过 workflow conflict audit。
- SQLite lock、dirty write_set、repo mutation 异常时降级串行。

Acceptance：

- 至少一个 multi-agent graph 真正跑完。
- 至少一次 artifact-only 并发成功。
- 至少一次 write_set conflict 被拒绝或降级。
- provider readiness 不因 graph route 自动变成 ready。

### M90: Vertical Pipeline Rebase And Cocos As Pressure Test

目标：把商业化游戏等垂直业务 pipeline 迁移到新编排底座之上，而不是继续堆一次性脚本。

Phase 1：pipeline rebase

- `WorkflowPipeline` stage 可选择 graph-backed executor。
- 未执行 stage 不得标记 completed。
- graph-backed stage 必须写 stage evidence、checkpoint refs、operator packet refs。

Phase 2：Cocos capability contract

- 定义但不急着完全实现：
  - `CocosSceneGenerator`
  - `CocosPrefabGenerator`
  - `CocosAssetImporter`
  - `CocosBuildPackager`
  - `CocosProjectInspector`
  - `GamePlaytestQA`
  - `CommercialReadinessJudge`

Phase 3：商业游戏压力测试

- 用一个小型 Cocos 改进任务测试新 graph repair loop。
- 不以“完整商业化成品”作为 M90 验收。
- 只验证：设计 -> 资产 -> 工程 -> build -> QA -> repair decision 的图式闭环可工作。

Acceptance：

- `commercial_cocos_game` 不再只是 serial script pipeline。
- 至少一个 stage 由 LangGraph-backed executor 驱动。
- 商业化 GO/NO-GO 分层更严格：`technical_smoke / production_scaffold / commercial_playable`。

## Long-Term Future After M90

### M91-M93: Commercial Game Production Quality

在 LangGraph 编排底座稳定后，再集中优化商业游戏：

- Cocos-native Scene/Prefab/UI Kit。
- Style Bible / Asset Bible / Audio Bible。
- MMX 资产批量生成与风格一致性。
- Vertex/Gemini visual review。
- 玩家视角 Playwright + screenshot/VLM QA。
- Android/Web packaging 质量门禁。

### M94-M95: External Capability Expansion

在主线稳定后再接：

- OpenCode 免费模型池发现、probe、分层、成本/限额追踪。
- Gemini CLI 候选评估。
- video generation 候选。
- 真实广告 SDK、IAP、排行榜等商业化接入。

## Public Interfaces

候选新增接口：

```powershell
workflowctl graph preview --goal "..." --preset ...
workflowctl graph run --goal "..." --artifact-only --evidence-dir ...
workflowctl graph resume --thread-id ... --checkpoint-id ... --receipt-id ...
workflowctl graph checkpoints list --run-id ...
workflowctl graph fork --checkpoint-id ... --reason ...
```

候选新增结构：

- `WorkflowGraphState`
- `WorkflowGraphNodeResult`
- `HumanApprovalInterrupt`
- `GraphCheckpointRef`
- `GraphEvidenceManifest`
- `GraphRepairDecision`

兼容要求：

- 现有 `workflowctl run ...`、`pipeline preview/run`、`capability probe/health`、`test matrix` 不破。
- 旧 task card / operator packet / evidence manifest 继续可读。
- 高风险动作仍必须通过 receipt/lease。

## Test Plan

每个 milestone closeout：

```powershell
python -m infra.scripts.check_doc_links
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json
python -m pytest tests/test_active_truth_check.py -q
```

涉及 LangGraph kernel 时追加：

```powershell
python -m pytest tests/test_langgraph_focused_runtime.py -q
python -m pytest tests/test_chat_llm_runtime.py -q
```

涉及高风险路径时追加：

- missing receipt 拒绝。
- wrong scope receipt 拒绝。
- expired receipt 拒绝。
- workspace mismatch 拒绝。
- write_set mismatch 拒绝。
- 成功路径写 evidence。

涉及 pipeline / Cocos 时追加：

```powershell
python -m pytest tests/test_pipeline_and_automation_cli.py tests/test_cocos_e2e.py -q
```

## Governance Rules

- 一个 milestone 必须包含多个 phase。
- 一个 phase 默认包含多张 task card。
- 单卡 phase 必须写 `single_card_exception`。
- 每个 graph-backed phase 必须输出 task cards、graph state snapshot、checkpoint refs、evidence、operator packet。
- workflow 自身 bug 继续 bug-first：receipt、route、probe、evidence、repo mutation、test matrix、graph checkpoint 任一出 bug，先修 workflow。
- 不再声明“零债”；只声明 blocking debt 是否阻塞下一阶段。

## References

- LangGraph persistence / checkpoint / memory / time travel。
- LangGraph human-in-the-loop interrupt。
- LangGraph subgraph / multi-agent supervisor。
- LangGraph Platform threads / runs / assistants / cron / streaming / concurrency controls 作为长期参考，不作为本地产品立即托管目标。
