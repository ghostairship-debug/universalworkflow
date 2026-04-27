# 当前开发工作流

## 当前版本说明

- 当前工作状态：M85-M90 LangGraph 与 workflow 长线收敛规划。
- 接受实现基线：M83 的 provider runtime truth、asset factory、active truth check、workflow dogfood proof、`commercial_cocos_game` pipeline 模板。
- 当前纠偏：商业化 Cocos 游戏生产线保留为正式能力，但短期不作为最高优先级；下一阶段先收敛 LangGraph 与 workflow 的编排边界，避免继续重复造轮子。
- 活跃真相集：`README.md`、`AGENTS.md`、本文件、`docs/milestone_history.md`、`docs/tech-debt-registry.md`、`docs/governance/tech_debt_registry.json`。
- 历史评估、旧路线图、旧计划和生成态 evidence 不保留为活跃工作树文档。需要逐字审计时使用 Git 历史。

本项目仍是个人自用、本地优先的 operator runtime。所有计划、文档和验证都服务于“能否稳定、诚实、可恢复地继续开发”，不服务于公开 SaaS、多租户、公共 onboarding 或第三方托管执行。

## Milestone / Phase / Task Card

- 一个 milestone 应包含多个 phase。
- 一个 phase 默认应包含多张 task card。
- task card 是最小可执行单元。
- 单卡 phase 必须显式写入 `single_card_exception` 并说明原因。
- 每个 phase 前运行并保存 `plan-graph`、`policy-preview`、`goal-packet`。
- 每个 phase 至少输出 task cards、route evidence、test evidence、operator packet 和 closeout summary。
- 成功 phase 可以 1 phase 1 commit；失败 phase 不提交，只保留 evidence 和恢复指针。

## Bug-First 规则

workflow、dogfood、receipt、probe、evidence、route、repo mutation、test matrix 任一路径出现 bug 时，暂停业务 phase：

1. 生成 workflow bug task card。
2. 修复 workflow bug。
3. 补回归测试。
4. 再恢复原 phase。

## 路由默认值

- OpenAI API 当前不是已配置主路径；OpenAI-family coding 真实入口是 Codex CLI。
- MiniMax / DeepSeek API 可以直接生成 plan、review、patch proposal；需要写仓库时必须通过受控 patch apply。
- simple 杂活：OpenCode + `minimax/MiniMax-M2.7`。
- medium review / validation：DeepSeek V4 Flash，失败直接 fallback Codex。
- complex 架构、安全协议、repo mutation：Codex CLI 或本地补丁兜底。
- MMX/MiniMax 的主要价值是 image / speech / music / future video 资产生成，不是只做文本 evidence。
- Vertex 生成能力走 API/SDK；`gcloud` 只是 Vertex/GCP 认证与环境工具。
- Cloud Text-to-Speech 使用 `gcp_tts_api`；旧 `vertex_tts` 只作为兼容 alias。
- Gemini CLI 暂不接入；Gemini-family 能力短期通过 Vertex/GCP。
- LangChain 是 experimental / opt-in agent framework，不进入默认主路由。

## Capability Truth

- Capability health 必须来自 runtime ledger / live probe，而不是 descriptor 自我声明。
- `verified_ready` 或 `recently_successful` 只能由真实 provider-specific live proof 产生。
- simulated、dry-run、generic greeting、fallback-only、非真实调用不能标记为 ready。
- text evidence、coding proposal、asset generation 必须分开声明。
- 生成类能力必须有真实二进制 artifact、mime、hash 和 evidence。

## 高风险动作边界

以下动作必须使用 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease`，并在消费时校验实际 request scope：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

GET 请求不得触发状态变更。所有文件写入必须解析明确 workspace root。

## Pipeline 规则

- `WorkflowPipeline` 是 `OrchestrationPlan` 之上的 plan-of-plans，不是 cluster 的别名。
- Pipeline preview 不直接 mutation。
- Pipeline run 必须写 stage evidence。
- 未真实执行的 capability stage 必须返回 `blocked`，不得伪装 `completed`。
- validation/capability 失败后必须短路后续 stage。
- 复杂写入仍走既有 run/control-plane、receipt/lease、write_set 和 repo mutation 语义。

## LangGraph 收敛规则

- LangGraph 适合承担状态机、checkpoint/resume、human interrupt、multi-agent/subgraph、repair loop 和 graph observability。
- LangGraph 不得绕过 `OperatorActionReceipt`、`AutomationLease`、workspace root、write_set audit、provider live proof 或 evidence/operator packet。
- 短期目标不是全量迁移，而是将 workflow 的执行内核逐步映射到 graph-backed executor。
- `workflowctl run ...`、`pipeline preview/run`、`capability probe/health`、`test matrix` 必须保持兼容。
- graph-backed phase 仍必须遵守 milestone / phase / task card 三层语义。

## 商业化 Cocos 游戏规则

商业化 H5/Cocos 游戏是正式业务需求，应作为 pipeline 场景承载，而不是新增一堆 `game_*_cluster`。

必须区分：

- 技术 smoke：工程能生成、构建能跑。
- E2E scaffold：有 Cocos 工程、资产绑定和自动试玩 evidence。
- 商业化可玩成品：真实 UI、可用面板、玩法闭环、关卡流程、皮肤/画廊、音频设计、动效反馈、移动端体验都达到玩家可接受标准。

当前结论：

- M78/M79/M83 证明了 Cocos 项目生成、asset factory、Web Mobile build、browser playtest 和 pipeline 模板可以跑通。
- M84 真实试玩反馈确认：当前产物仍是样机级，不具备商业化可玩质量。
- `workflowctl game cocos-e2e --require-commercial` 的验收门禁必须升级，不能继续只看状态变量或事件覆盖。
- 后续修复重点是可玩性与玩家视角质量，而不是再生成更多 manifest。

## 验证规则

文档变更至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

涉及运行路径、API、UI、验证脚本或活跃真相源时追加：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/<milestone>/capability_probes
python -m pytest -q
```

## 卫生清理规则

- `state/` 是生成态目录，默认不进入 Git；工作树只应保留 `.gitkeep`、必要的本地 `workflow.db` 和正在使用的短期 evidence。
- 大型 Cocos 工程、APK/HTML 包、pytest 临时目录、旧 evidence、离线验证 scratch DB 都应按需清理。
- 清理文件不等于清理功能。商业化游戏 pipeline 代码、测试和说明继续保留。
- 删除递归目录前必须确认目标解析后仍在当前 workspace 或明确目标目录内。
