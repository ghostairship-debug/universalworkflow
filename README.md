# Universal Agentic Workflow OS

## 当前状态：M105-M108 Cocos 真实工程接入计划

- 包版本：`0.66.0`。
- 当前接受实现基线：M104 已完成本地 LangGraph 运行时接入、SQLite checkpoint、interrupt/resume、repair loop、subgraph/supervisor 探针、stream evidence 和 Cocos graph pressure test。
- 当前质量结论：商业化 Cocos 游戏生成是正式需求，功能代码和 pipeline 继续保留；但最近一次真实生成结果只达到“可构建技术样机/生产线验证”，没有达到商业化可玩成品质量。
- 当前工作重点：用已接入的 LangGraph 底座推进 Cocos 真实工程接入，先从 Cocos command、构建配置、工程检查和玩家视角证据开始。
- 活跃开发方案见：[CURRENT_DEVELOPMENT_WORKFLOW.md](CURRENT_DEVELOPMENT_WORKFLOW.md)。
- 历史收敛方案已压缩进里程碑历史和架构笔记，不再在根目录保留散装计划书。
- 治理真相源：[docs/governance/tech_debt_registry.json](docs/governance/tech_debt_registry.json)。

Universal Agentic Workflow 是一个本地优先的 agentic workflow runtime。它的目标不是公开 SaaS、多租户平台或插件市场，而是让个人开发者把 AI、CLI、代码仓库、测试、审查、证据和自动化任务组织成可恢复、可审计、可长期推进的工作流。

## 项目全景

一句话说，它是一个本地优先的“AI 工作流控制台”。它不是单纯聊天机器人，而是把 AI、命令行工具、代码仓库、测试、审查、文档、证据记录和自动化执行组织成一套可追踪、可恢复、可审计的工作流。

它适合个人开发者、研究型项目维护者和需要长期迭代复杂代码库的人；当前不适合作为公开 SaaS、多租户团队平台、外部托管执行服务或一键自动发布平台。

核心设计原则：

- 本地优先：默认使用本地仓库、本地数据库、本地 CLI 和本地 Web console。
- 证据优先：重要动作需要 task card、route preview、测试输出、capability probe、operator packet 或恢复指针。
- 安全边界优先：高风险动作需要 receipt 或 lease，provider ready 需要真实 live proof。
- 长程任务优先：plan、milestone、phase、task card、checkpoint、评估与修复循环都必须可恢复。

项目主要由 `workflowctl` CLI、本地 FastAPI/Web operator console、core domain、adapter/provider、pipeline 和治理文档组成。Pipeline 是“计划之上的计划”，用于把需求解析、资产生成、代码实现、构建、浏览器测试和 GO/NO-GO 串成可审计流程。

## 活跃真相集

后续开发优先参考这些文件：

- [当前开发工作流](CURRENT_DEVELOPMENT_WORKFLOW.md)
- [里程碑历史](docs/milestone_history.md)
- [技术债登记表](docs/tech-debt-registry.md)
- [结构化技术债 JSON](docs/governance/tech_debt_registry.json)

历史评估、旧恢复计划、旧路线图、重复阶段报告和临时 evidence 不再作为当前判断来源。需要逐字审计时使用 Git 历史。

## 当前能力

- 本地 CLI：`workflowctl`
- 本地 API：FastAPI orchestrator API
- 本地 Web operator console：`/ui`、`/ui/workbench`、`/ui/reviews`、`/ui/config`
- 核心能力：run 生命周期、task card、route preview、evidence、operator packet、receipt/lease 高风险门禁、repo mutation、test matrix、offline validation、pipeline preview/run
- LangGraph 本地能力：SQLite checkpoint、interrupt/resume、repair loop、subgraph/supervisor 探针、stream evidence、Studio graph 配置和 Cocos graph pressure test
- 已接入 provider/adapter：Codex CLI、OpenCode CLI、Claude CLI、MMX/MiniMax、Vertex/GCP、LangChain、Shell/Noop
- OpenAI API 当前不声明 ready；OpenAI-family coding 主路径是 Codex CLI
- Gemini CLI 暂未接入；Gemini-family 能力短期通过 Vertex/GCP
- `gcloud` 是 Vertex/GCP 认证与环境工具，不是独立 worker adapter
- LangChain 是 experimental / opt-in agent framework，不是默认主路由

## 商业化游戏生产线真实状态

商业化 H5/Cocos 游戏生成仍然是正式业务方向，但必须诚实区分三层结果：

1. **技术 smoke**：工程能生成、能构建、浏览器能打开。
2. **E2E scaffold**：有 Cocos 工程、资产绑定、自动试玩和 feature coverage。
3. **商业化可玩成品**：有完整 UI、美术统筹、可用面板、真实关卡流程、音频设计、动效反馈、可玩性和移动端体验。

当前代码已经具备前两层的生产线能力，但最近一次真实 Cocos 生成暴露了第三层不足：

- UI 仍像调试面板，缺少成品级界面设计。
- 关卡切换、皮肤、画廊、复活等功能更多是事件标记或浅交互。
- 自动化测试过度依赖状态变量，未严格验证玩家视角的可用性和美观度。
- 音频和配音缺少产品设计、触发策略和混音控制。
- Web Mobile 构建需要 HTTP 服务运行，不能保证解压后双击 `index.html` 即可游玩。

因此，后续不得把 `commercial_go_no_go=GO`、feature flag、canvas 非空、事件覆盖、APK/HTML 打包成功写成“完整商业化游戏已生成”。商业化 pipeline 需要继续优化，而不是删除。

## 快速开始

```powershell
pip install -e ".[dev]"
python -m infra.scripts.manage --db-path state/workflow.db reset-db
python -m infra.scripts.manage --db-path state/workflow.db smoke
```

启动本地 Web operator console：

```powershell
uvicorn apps.orchestrator_api.main:app --host 127.0.0.1 --port 8000
```

常用页面：

- `http://127.0.0.1:8000/ui`
- `http://127.0.0.1:8000/ui/workbench`
- `http://127.0.0.1:8000/ui/reviews`
- `http://127.0.0.1:8000/ui/config`

## 常用命令

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run plan-graph --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run policy-preview --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run goal-packet --goal "实现一个受控能力切片" --preset project_delivery
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/capability_probes
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability health --verified-only
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability routes stats --days 30
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json
```

通用资产工厂：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" asset factory run --style-guide "premium neon casual puzzle" --manifest state/asset_factory/prompt_manifest.json --output-dir state/asset_factory/run
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" asset factory qa --asset-manifest state/asset_factory/run/asset_factory_manifest.json --evidence-dir state/asset_factory/qa
```

Cocos 生产线入口仍保留，但当前不能代表最终商业化成品：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline preview --template commercial_cocos_game
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline run --template commercial_cocos_game --execute-capabilities --pdf-path "C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf" --creator-exe "C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe" --require-build --require-commercial
```

## Workflow Dogfood 规则

- 一个 plan 应包含多个 milestone。
- 一个 milestone 应包含多个 phase。
- 开发计划文档只写到 milestone 和 phase，不提前生成 task card。
- 只有 active phase 才生成 task card。
- 一个 phase 默认应包含多张 task card；单卡 phase 必须标记 `single_card_exception`。
- phase 前运行并保存 `plan-graph`、`policy-preview`、`goal-packet`。
- 简单低风险任务优先交给 workflow + OpenCode/MiniMax。
- 中等 review/validation 可走 DeepSeek V4 Flash，失败直接 fallback Codex。
- 复杂架构、安全协议、repo mutation 使用 Codex 或本地补丁兜底。
- artifact-only 和 disjoint write_set task card 可以并发；write_set 冲突、dirty worktree、SQLite lock 或 repo mutation 异常时降级串行。
- workflow 自身 bug 优先级高于业务 phase：先登记、修复、补回归测试，再恢复原 phase。

## 安全边界

高风险动作必须通过 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease`：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

GET 请求不得产生状态变更。所有文件写入必须解析明确 workspace root。

## 验证

文档变更至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

常规开发收口：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe
python -m pytest -q
```
