# M76 后深度评估 R1

生成日期：2026-04-26

## 总结

本轮评估覆盖架构、功能、安全边界、workflow dogfood、provider 真实性、测试可靠性、Cocos/H5 pipeline 和治理文档八类问题。

结论：发现并修复 2 个 P2 可执行问题；未发现 P0/P1。

## P2-1：活跃文档存在编码乱码，影响交接可读性

范围：

- `README.md`
- `AGENTS.md`
- `docs/current_development_workflow.md`
- `docs/tech-debt-registry.md`
- `docs/milestone_history.md`
- `PROJECT_OVERVIEW_FOR_BEGINNERS.md`
- `FINAL_DEVELOPMENT_PLAN_M73_M76.md`

影响：这些文件是活跃真相源或新用户入口；乱码会直接破坏后续开发者、operator 和评估流程对当前规则的理解。

处置：已重写为可读中文，并将当前版本、M76 closeout、workflow dogfood、多 task card、provider live proof、Pipeline 和 Cocos E2E 规则统一到文档中。

状态：`repaid`

## P2-2：living-doc hygiene 仍指向 M72/M73 preflight，而不是 M76 当前入口

范围：

- `infra/validation/doc_hygiene.py`

影响：文档语义检查会继续把旧 M72/M73 材料当作活跃入口，降低治理收口可信度。

处置：已把 living docs 更新为 M73-M76 最终方案、M73-M76 执行报告、M76 后两轮深评、项目全景介绍和当前开发工作流。

状态：`repaid`

## 架构评估

优点：

- `WorkflowPipeline` 没有替代既有 `OrchestrationPlan`，避免出现第二套执行真相源。
- `AutomationLease` 与 `OperatorActionReceipt` 分工清晰：前者用于有界无人值守授权，后者用于具体高风险动作确认。
- MCP broker 的 selector 机制比 profile 白名单更接近可审计的 per-task capability exposure。

剩余建议：

- `repositories.py`、`service_projection.py`、`service_lifecycle.py` 仍偏大，但当前属于 P3 结构维护项，不阻塞能力层开发。

## 功能实现评估

优点：

- CLI/API/Pipeline/Game Cocos E2E 都有最小公共入口。
- Cocos E2E 不复用桌面 `游戏平台demo`，并生成真实 Cocos Creator 项目。

剩余建议：

- 后续可以把 Cocos 生成逻辑拆成 design mapping、project scaffold、build runner、browser playtest 四个模块；当前不阻塞。

## 安全边界评估

优点：

- 高风险 resume/batch 路径支持 receipt id 进入执行 envelope。
- capability enforcement pilot 覆盖 live proof、write_set 和 receipt。
- AutomationLease 明确禁止 secrets、workspace root 扩大、未授权 publish/push/PR。

剩余建议：

- 后续应把 AutomationLease 与 receipt consumption 的审计视图合并到 Web UI。

## Workflow Dogfood 评估

优点：

- 已生成 task cards、route previews、operator packet 和并发 batch-resume evidence。
- slow suite 暴露 CLI projection bug 后按 bug-first 修复，证明测试不是摆设。

剩余建议：

- 继续增加 disjoint write_set 并发的真实 mutation 类 evidence；当前 artifact-only 并发已通过，mutation 并发仍应谨慎保持 opt-in。

## Provider 真实性评估

优点：

- `workflowctl capability probe --provider all --require-live` 全通过，blocked_count 为 0。
- Codex、OpenCode、MMX、Vertex、Claude、LangChain 均返回 provider-specific live proof。

剩余建议：

- 后续应把 probe latency 和 failure taxonomy 做成趋势图，而不是只看最近一次。

## 测试可靠性评估

优点：

- doc links、doctor strict、unit/core/integration matrix、workflowctl validation full、capability all live、slow suite 全绿。
- pytest 默认 basetemp 已修成 repo-scoped unique path，降低 Windows 临时目录污染。

剩余建议：

- slow suite 仍需要 12 分钟左右；可继续按 shard 优化，但当前不是阻塞项。

## Cocos/H5 Pipeline 评估

优点：

- 真实使用 Cocos Creator 3.8，构建 Web Mobile，并跑移动端浏览器 playtest。
- feature coverage 覆盖 10x10、候选块、拖拽、消除、分数、暂停、复活、皮肤、作品界面。

剩余建议：

- Cocos Creator 原始 exit code 与 artifact/browser evidence 的关系需要继续审计记录；当前 manifest 已记录原始码和实际 GO/NO-GO。

## 治理文档评估

优点：

- Active truth set 已更新到 M76。
- 技术债摘要不再声称“零债”，而是区分 blocking debt 和 carry-forward debt。

处置：

- 根目录旧 M72/M73/preflight/pipeline 文档已移入 `docs/archive/evaluations/`；根目录只保留当前 M73-M76 方案、执行报告、两轮深评、项目介绍和入口说明。

## 结论

本轮 P2 已修复。没有剩余 P0-P2 可执行建议。进入 R2 复评。
