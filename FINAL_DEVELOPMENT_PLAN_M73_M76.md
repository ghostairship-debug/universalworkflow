# M73-M76 最终开发方案

生成日期：2026-04-26

## 总体目标

M73-M76 不是继续扩散能力，而是把恢复能力层开发之前最关键的可信控制面补齐：

- 能力调用必须能被 policy、receipt、write_set 和 live proof 共同约束。
- workflow 共同开发必须真实使用编排、路由、并发和 evidence，而不是只写计划。
- Pipeline 要成为 `OrchestrationPlan` 之上的 plan-of-plans 产品层，而不是新增一组互相平行的 cluster。
- H5 游戏商业化是真实需求，应作为 pipeline/E2E 场景验证，而不是低优先级 demo。
- Cocos 产物必须是真实 Cocos Creator 项目、真实 Web Mobile build、真实浏览器 playtest，不接受 HTML 原型或 dry-run 冒充。

## 不变原则

- bug-first：workflow、receipt、repo mutation、provider probe、evidence、route、test matrix 任一路径出 bug，先修 workflow bug，再恢复业务 phase。
- 多 task card：每个 phase 默认至少 implementation、verification、review/evidence 三张 task card；单卡 phase 必须标记 `single_card_exception`。
- 高风险动作必须带 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease`。
- provider readiness 只接受 require-live evidence；fallback-only、generic greeting、simulated、dry-run 都不算 ready。
- 不自动 PR；commit/push 只在用户明确要求时执行。

## M73 Capability Control Layer

### M73A Capability Enforcement Pilot

将 `adapter_route + patch_apply + write_set + receipt + live proof` 做成强制门禁路径。缺 live proof、缺 write_set、缺 receipt 或 receipt scope 不匹配时拒绝 mutation。

### M73B MCP Broker v1

实现 canonical tool id、同名 tool collision guard、显式 profile/tool selector。`include_mcp=True` 不再等于暴露全部 enabled profile。

### M73C AutomationLease v0

新增有界无人值守授权：允许 resume、batch、test、artifact 写入；继续禁止 secrets、workspace root 扩大、未授权 publish、push、PR。

### M73D LangGraph Real-Runtime Spike

仅验证 non-mutating checkpoint / interrupt / resume / evidence。LangGraph 不成为第二套 mutation 真相源。

### M73E Manifest V2 Provenance

建立 `task_card -> run_id -> evidence -> test_result -> commit_sha` 可追溯链路。

## M74 Pipeline Product Layer

定义：

```text
WorkflowPipeline = OrchestrationPlan 之上的 plan-of-plans
```

Stage 类型固定为：

```text
agent_role | cluster | capability | human_checkpoint | sub_pipeline | validation_gate | external_worker
```

M74 只做 contracts、preview、manual/template/hybrid planning，不直接 mutation。

## M75 Pipeline Execution v0

实现最小串行 Pipeline execution：

- `workflow_self_development_pipeline`
- `h5_game_commercialization_pipeline`

该阶段只证明 pipeline 可以被预览、记录和顺序执行；复杂并发和写入仍交给既有 workflow run/control-plane。

## M76 H5 Commercialization Pipeline And Cocos E2E

增强 H5 游戏商业化 pipeline：

- browser playtest
- visual / multimodal review 入口
- 广告、移动端、留存检查项
- Cocos Creator Web Mobile 构建
- 真实浏览器交互 evidence

Cocos E2E 输入 PDF：

```text
C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf
```

明确排除：

```text
C:\Users\74755\Desktop\游戏平台demo
```

## 验收标准

- `python -m infra.scripts.check_doc_links`
- `workflowctl doctor --strict`
- `workflowctl test matrix --suite unit`
- `workflowctl test matrix --suite core`
- `workflowctl test matrix --suite integration`
- `workflowctl validation run --suite full --skip-offline-probe`
- `workflowctl capability probe --provider all --require-live`
- `python -m pytest -q --run-slow`
- Cocos Creator build 产生 Web Mobile 运行资产。
- 浏览器 playtest 证明 canvas 非空、像素变化、拖拽成功、分数变化、至少一次消除、暂停/复活/皮肤/作品界面可打开、移动端 390x844 无遮挡。

## Go / No-Go

M73-M76 收口后，若两轮深度评估均无 P0-P2 可执行建议，且所有 full gates 通过，则允许恢复能力层开发。若 provider live proof、workflow route/evidence、receipt scope、Cocos build/playtest 任一硬门禁失败，则为 NO-GO，必须先修复。
