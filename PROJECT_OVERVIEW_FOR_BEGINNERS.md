# Universal Agentic Workflow 项目全景介绍

这是一份面向小白用户的项目介绍。它不假设你了解 agent、workflow、编排、provider、receipt、LangGraph 或多模态这些词。读完以后，你应该能大致明白这个项目想解决什么问题、由哪些部分组成、当前能做什么、还不能做什么。

## 一句话介绍

Universal Agentic Workflow 是一个本地优先的“智能工作流操作系统”。

它的目标不是做一个聊天机器人，而是把 AI、命令行工具、代码仓库、测试、审查、文档、证据记录和自动化执行组织成一套可追踪、可恢复、可审计的工作流。

换句话说，它想解决的问题是：

> 当 AI 不只是回答问题，而是真的参与计划、改代码、跑测试、生成证据、推进长期任务时，我们如何保证它做的事情可控、可查、可恢复？

## 它不是普通聊天工具

很多 AI 工具的工作方式是：

1. 你提出一个问题。
2. AI 给出回答。
3. 如果要改代码，就直接在当前上下文里改。
4. 成败主要靠最后的文字说明。

Universal Agentic Workflow 想做得更重一点：

1. 先把目标拆成任务。
2. 明确每个任务能读什么、能写什么。
3. 选择合适的执行方式或模型。
4. 执行时记录证据。
5. 高风险动作需要确认凭证。
6. 失败时保留恢复指针。
7. 完成后生成报告、operator packet 和可审查摘要。

所以它更像“AI 参与工作的控制台”，而不是单纯的聊天窗口。

## 适合什么人

当前最适合：

- 个人开发者。
- 研究型项目维护者。
- 需要长期迭代复杂代码库的人。
- 希望 AI 帮忙做计划、评估、修复、验证和文档收口的人。
- 希望 AI 操作有证据、有边界、有恢复点的人。

当前不适合：

- 直接拿来做公开 SaaS。
- 多租户团队平台。
- 面向外部客户的托管执行服务。
- 一键自动发布平台。
- 无监督公网 agent 执行系统。

它现在是一个本地、自用、可控优先的 workflow runtime。

## 核心思想

### 本地优先

项目默认运行在你的机器上，使用本地仓库、本地数据库、本地 CLI 和本地 Web console。

这意味着：

- 你对工作区有最终控制权。
- 默认不把 Web UI 暴露到公网。
- 默认不自动提交、推送或开 PR。
- 外部 provider 只是能力来源，不是项目控制中心。

### 证据优先

系统不满足于“我觉得完成了”。

它希望每个重要动作都有证据，例如：

- task card
- route preview
- 测试输出
- capability probe 结果
- operator packet
- execution report
- 失败原因和恢复指针

这样以后回看时，你能知道一个阶段为什么算完成，或者为什么失败。

### 安全边界优先

越是可能改变状态的动作，越要明确边界：

- 改文件前要知道 write set。
- 执行高风险动作前要有 receipt。
- provider ready 不能靠自称，要靠 live proof。
- Git commit、push、PR 需要明确操作。

这套系统不是为了“让 AI 放飞自我”，而是为了让 AI 可以更可靠地参与真实工作。

### 长程任务优先

项目特别重视长程开发：

- 能拆 milestone。
- 能拆 phase。
- 能拆 task card。
- 能记录 checkpoint。
- 能失败后恢复。
- 能多轮评估和修复。
- 能在不同能力之间路由。
- 能保留阶段报告。

这就是为什么仓库里会有 M67、M72、M76 这样的 milestone 报告。

## 项目由哪些部分组成

### CLI 命令行

入口是 `workflowctl`。

它负责让你从终端操作系统能力，例如：

- 健康检查。
- 创建和推进 run。
- 查看 task evidence。
- 运行测试矩阵。
- 查看 capability 状态。
- 运行 offline validation。
- 生成治理报告。
- 预览和执行 pipeline。
- 运行 Cocos H5 游戏 E2E。

### Web Operator Console

项目提供本地 Web 页面，例如：

- `/ui`
- `/ui/workbench`
- `/ui/reviews`
- `/ui/config`

它们主要用于查看运行状态、操作 workbench、做 review、查看配置和能力信息。

### Core Domain

这是项目的大脑。

它处理：

- run 生命周期。
- task 编排。
- review gate。
- operator action guard。
- repo mutation。
- capability projection。
- pipeline preview/run。
- scheduler lease。
- evidence 管理。
- governance 报告。

### Adapter 和 Provider

项目可以连接不同能力来源：

- Shell / Noop：本地确定性能力。
- Codex：复杂代码与架构任务。
- OpenCode：简单/低风险任务，当前默认可走 MiniMax。
- Claude：架构/审查类能力。
- MMX/MiniMax：多模态和轻量模型能力。
- Vertex：当前 Gemini-family 能力入口。
- LangChain：agent 路由实验入口。

项目不会只因为某个 provider 在配置里出现就认为它 ready。它必须通过真实 live probe。

### Pipeline

Pipeline 是更高一层的产品语义，可以理解为“计划之上的计划”。

例如 H5 游戏商业化 pipeline 可以包含：

- 需求解析。
- 游戏设计。
- 代码实现。
- 浏览器测试。
- 视觉/多模态检查。
- 广告和移动端检查。
- 最终 GO/NO-GO。

它不是新增一堆游戏专用 cluster，而是复用通用 stage。

## 当前阶段

当前已推进到 M83：

- workflow 已能参与开发。
- route preview、task card、evidence、operator packet 已成为默认要求。
- capability live proof 已成为硬门禁。
- Pipeline 有了可复用模板入口。
- Cocos H5 游戏 E2E 已有真实生成、构建和浏览器测试入口。
- MMX/MiniMax、GCP TTS、Vertex 已能参与生成或审查游戏素材。
- `commercial_cocos_game` pipeline template 已能把需求映射、asset factory、Cocos 生成/构建/playtest 和 commercial readiness gate 串起来。

但这里仍有一个重要限制：

> 当前 Cocos game pipeline 已经能产出商业化 v1 工程和复用模板，但它仍是生产线基线，不等同于最终上线运营级游戏。

M79 已把工程升级为编辑器里可见、可维护、可继续制作的 Cocos 2D 商业化 v1；M83 已把这条链路模板化。后续如果要做真正上线级项目，还需要围绕玩法深度、美术统筹、音频体验、数值和运营体系继续迭代。

## 一个最小使用路径

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" doctor --strict
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" run suggest-presets --goal "整理下一阶段计划"
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/capability_probes
```

如果要跑可复用商业 Cocos pipeline：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline run --template commercial_cocos_game --execute-capabilities --pdf-path "C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf" --creator-exe "C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe" --require-build --require-commercial
```

这个命令用于验证模板化生产线和生成 evidence。它可以生成商业化 v1 工程，但不应被理解为“无需后续制作即可直接上线运营”。
