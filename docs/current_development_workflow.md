# 当前开发工作流

## Current Version: M79 Cocos Commercial Pipeline Repair Planned

- Package version: `0.66.0`.
- Accepted implementation baseline: `M78` real provider/asset repair plus Cocos E2E scaffold.
- Active repair entry: [M77+ integrated repair plan](../M77_PLUS_INTEGRATED_REPAIR_AND_DEVELOPMENT_PLAN.md), with M79 focused on true commercial Cocos production.
- Active truth set: [README.md](../README.md), this workflow guide, [M77 issue register](../M77_ISSUE_REGISTER.md), [milestone history](milestone_history.md), [tech debt registry](tech-debt-registry.md), and [structured governance registry](governance/tech_debt_registry.json).
- Historical evaluations, long-term roadmaps, old recovery plans, stage reports, and duplicate root docs are removed from the active worktree. Use git history for exact archival text.
- Scheduler semantics are local-first. `LocalSchedulerLeaseArbiter` is the default local lease arbiter; `scheduler-authority` names are legacy compatibility surfaces unless the cluster flag is explicitly enabled.
- PR publication remains manual unless the operator explicitly asks for commit, push, or PR creation.

本文档是后续开发的最高优先级操作说明。项目当前仍是个人自用、本地优先的 operator runtime；所有计划、文档和验证都服务于“能否稳定继续使用它”，不服务于外部 SaaS、多租户、公开 onboarding 或第三方生态。

## M76+ Development Rules

- 新能力开发可以恢复，但必须继续使用 workflow 共同开发。
- 一个 milestone 应包含多个 phase；一个 phase 默认应包含多张 task card，task card 是最小可执行单元。
- 单卡 phase 必须显式写入 `single_card_exception`，并说明为什么不能拆分。
- 每个 phase 前运行 `plan-graph`、`policy-preview`、`goal-packet` 并保存 evidence。
- 每个 phase 至少输出 task cards、route evidence、test evidence、operator packet 和 closeout summary。
- workflow、dogfood、receipt、probe、evidence、route、repo mutation、test matrix 任一路径出现 bug，先修 workflow bug 并补回归测试，再继续原 phase。
- artifact-only 与 disjoint write_set 任务可以并发；patch apply 只有 write_set 不相交时才能并发，最多 `--max-workers 2`。
- SQLite lock、dirty worktree 命中 write_set、write_set conflict 或 repo mutation 异常时自动降级串行。
- 成功 phase 可以 1 phase 1 commit；失败 phase 不提交，只保留 evidence 和恢复指针。

## Routing Defaults

- OpenAI API 当前不是已配置主路径；OpenAI-family coding 真实入口是 Codex CLI。
- MiniMax / DeepSeek API 可以直接生成 plan、review、patch proposal；需要写仓库时必须通过 `workflowctl capability coding-apply`，并携带允许 `coding_patch_apply` 的 `AutomationLease` 与明确 `write_set`。
- simple 杂活：可走 OpenCode + `minimax/MiniMax-M2.7`，但 OpenCode 当前主要是低成本 coding CLI 壳，不宣称 OMO 生态已接入。
- medium review / validation / security：优先 DeepSeek API 或 `deepseek/deepseek-v4-flash`；失败直接 fallback Codex，不 fallback MiniMax。
- complex 架构、安全协议、repo mutation：Codex CLI 或本地补丁兜底；workflow 仍负责 task card、route evidence 和 operator packet。
- MMX/MiniMax 的主要新增价值是 image / speech / music / future video 资产生成，而不是只做文本 evidence 或视觉提取。
- Vertex 生成能力应走 API/SDK；`gcloud` 是 Vertex/GCP 凭据与环境工具，不是独立 worker adapter。
- Cloud Text-to-Speech 不是 Vertex AI 本体，能力名使用 `gcp_tts_api`；旧 `vertex_tts` 仅保留为兼容 alias。
- Gemini CLI 暂不接入；Gemini-family 能力短期通过 Vertex/GCP。
- LangChain 是 experimental / opt-in agent framework，不进入默认主路由。

## Capability Truth

- Capability health 必须来自 runtime ledger / live probe，而不是 descriptor 自我声明。
- `verified_ready` 或 `recently_successful` 只能由真实 provider-specific live proof 产生。
- simulated、dry-run、generic greeting、fallback-only、非真实调用不能标记为 ready。
- text evidence、coding proposal、asset generation 必须分开声明；生成类能力必须有真实二进制 artifact、mime、hash 和 evidence。
- `workflowctl capability probe --provider all --require-live` 是能力 closeout 的硬门禁。
- GCP 本地开发需设置 ADC quota project，并给 ADC 实际账号授予 `roles/serviceusage.serviceUsageConsumer` 或等价 `serviceusage.services.use` 权限。

## High-Risk Action Boundary

以下动作必须由 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease` 授权，并且消费时校验实际 request scope：

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

## Pipeline Rules

- `WorkflowPipeline` 是 `OrchestrationPlan` 之上的 plan-of-plans，不是 cluster 的别名。
- Pipeline stage 类型固定为 `agent_role | cluster | capability | human_checkpoint | sub_pipeline | validation_gate | external_worker`。
- Pipeline preview 不直接 mutation；execution 当前只支持受控串行 stage，未真实执行的 capability stage 必须返回 `blocked`，不得伪装 `completed`。
- Pipeline run 需要写 stage evidence，并在 validation/capability 失败后短路后续 stage；复杂写入仍走既有 run/control-plane。
- H5 游戏商业化是正式业务需求，应作为 pipeline 场景承载，而不是新增一堆 `game_*_cluster`。
- Cocos 技术 smoke 与商业化验收必须分开；`workflowctl game cocos-e2e --require-commercial` 缺真实美术/音效/UI/动画/粒子/皮肤/关卡闭环时必须 NO-GO。
- M78 的真实结论是“E2E scaffold 通过”，不是“完整商业化游戏完成”。`commercial_go_no_go=GO`、canvas 非空、事件覆盖、截图变化都只能证明当前验证门槛通过，不能证明 Cocos 编辑器工程已达到商业化制作标准。
- M79 前不得恢复大规模能力层扩张；优先把 game pipeline 产物升级为真实 Cocos Scene / Node / Prefab / Component / UI、SpriteFrame/AudioClip 绑定、Animation/Particle、皮肤/关卡/广告/道具闭环。

## Validation Rules

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
python -m pytest -q --run-slow
```

## M77 Provider And Asset Generation Notes

- Vertex/GCP routes are split by real execution surface: `vertex_imagen` uses Vertex AI Imagen REST, `vertex_gemini_review` uses Vertex Gemini visual review over an image, and `gcp_tts_api` uses Google Cloud Text-to-Speech.
- `gcloud` remains an authentication and environment helper, not a worker adapter. Local workflow probes prefer the active `gcloud auth print-access-token` user and fall back to ADC; set `WORKFLOW_GCP_AUTH_MODE=adc` when ADC must be forced.
- MMX/MiniMax generation is the preferred commercial game asset path for image, speech, and music. Vertex is a fallback/review path, and GCP TTS is a voice fallback.
- `workflowctl game cocos-assets` is the asset-manifest batch step. It does not by itself make the Cocos game commercial-ready unless `cocos-e2e --require-commercial` also passes the UI, animation, level, and playtest gates.
- Provider health must still come from live proof. Descriptor presence, dry-runs, fallback-only output, or generated manifests with blocked assets do not count as `verified_ready`.

## M78/M79 Game Pipeline Notes

- M78 committed and pushed a real Cocos E2E scaffold: real project generation, real Web Mobile build, real browser playtest, MMX image/speech/music, GCP TTS, and Vertex review evidence.
- The generated Cocos project still uses a scaffold-like structure and runtime/canvas-heavy game body; opening it in Cocos Creator does not show a finished commercial game.
- M79 acceptance must include editor-visible production evidence, not only browser feature flags: scene hierarchy, prefab/component structure, imported and bound generated art/audio, UI panels, animations, particles, level/skin switching, mobile visual polish, and rejection of half-finished projects.
