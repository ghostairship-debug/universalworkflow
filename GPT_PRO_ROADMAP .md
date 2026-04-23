我给你的不是再写一版“路线图”，而是一套**按当前仓库状态直接开工、最后能收束成完整产品**的开发方案。先说结论：这套仓库已经不是 0 到 1 的原型了，它已经有本地优先运行时、SQLite 单存储、RuntimeGateway 边界、多适配器执行、治理报表、remote worker、single-store scheduler-authority、Web/TUI operator surface；但当前官方真相也很明确：主线仍停在 accepted `M34`，`M35` 还没正式打开，且开相前必须先修治理报告回归。也就是说，下一步不是再发散造新层，而是把现有控制平面**产品化、解释化、入口化、评估化**。([GitHub][1])

我建议把最终产品目标定义为两层。第一层是**平台产品闭环**：角色/配置可解释、自然语言入口可用、remote worker 可管、能力生态可接、评估与 promotion 可闭环，这一层对应 `M35-M39`。第二层是**面向高质量游戏/设计交付的增强闭环**：`DesignCluster` 加多模态视觉验证，这一层对应可选的 `M40`。仓库自己的 post-`M34` 路线图也明确写了，`M35-M39` 才是达到原平台目标的现实补完线，而如果目标包含 domain-grade design 和 visual verification，还需要 `M40`。([GitHub][2])

先定三条硬约束。第一，**到 `M39` 之前继续坚持 SQLite 单真相源，不做真分布式共识重构**。仓库自己的 scheduler-authority 文件已经明确说明当前实现是 “single-store quorum-style”，不是 peer-replicated distributed consensus；SQLite 官方也明确说明 WAL 模式的优势是读写并发更好，但前提是**同机**，而且**同一时刻仍只有一个 writer**。这意味着你现在最正确的策略不是把调度层讲成分布式，而是继续把它当成“诚实的单存储控制平面”，然后围绕写争用、回调乱序、幂等恢复做硬化。([GitHub][3])

第二，**LangGraph 继续留在边界后面，不进入 contracts 和 core_domain 的主语义层**。LangGraph 官方把自己定位为低层 orchestration runtime，核心价值是 durable execution、human-in-the-loop、memory；它的 durable execution 明确要求 checkpointer、thread_id，以及把副作用和非确定性操作包进可重放、最好幂等的任务边界里。它非常适合做你现有 runtime boundary 后面的一个可插拔执行后端，但不适合反向吞掉你仓库已经建立的控制平面契约。([LangChain 文档][4])

第三，**API 入口必须从“大单文件总控”改成 transport-thin**。FastAPI 官方对稍大的应用明确推荐 multiple files 和 `APIRouter`；而你当前 `apps/orchestrator_api/main.py` 已经同时承载 governance、interaction sessions、runs、scheduler、worker callbacks、UI 等多种 surface。后面如果还把新产品能力继续直接堆在这里，维护成本会比功能收益增长得更快。([FastAPI][5])

---

## 1. 先做 G0，不开新功能，只把主线拉平

这个阶段只做 4 件事。

第一，修掉 `M35` 的前置 gate。现在仓库自己记录的已知问题，就是治理技术债报表的两个回归；`M34_POST_EVALUATION` 还明确给出了判断：大概率是 registry 内容变了，但测试仍在吃旧的硬编码期望。这里不要只改快照文本，而是把 `governance.py` 的测试基准彻底切到**结构化 canonical source contract** 上。具体做法是：`build_tech_debt_report()` 只以 `docs/governance/tech_debt_registry.json` 为主真相，Markdown 只保留 compatibility fallback；API/CLI 的断言改为校验 `source_contract`、`open_items`、`repaid_items`、`status_counts`，不要再校验 prose 句子。([GitHub][6])

第二，清文档治理噪音。`current_development_workflow.md` 已经把 active truth set 规则写得很明确：最新 freeze review、README、workflow guide、living debt registry、当前 phase 材料才是活跃真相；而 `M34_POST_EVALUATION` 又明确指出 `NEXT_DEVELOPMENT_PLAN.md` 现在是过时的。我的建议是：把 `NEXT_DEVELOPMENT_PLAN.md` 归档出活跃真相集合，把根目录 zip bundle 也移出主分支活跃面，别让历史计划继续和 current truth 打架。([GitHub][7])

第三，做一次**无行为变更的入口拆壳**。`apps/orchestrator_api/main.py` 先拆成 `routers/runs.py`、`routers/interaction.py`、`routers/governance.py`、`routers/scheduler.py`、`routers/workers.py`、`routers/config.py`、`routers/ui.py`，但内部仍调用同一批 service。目的不是重构业务，而是先把 transport 层变薄。FastAPI 官方本来就是这样建议的。([FastAPI][5])

第四，补一个最小坏天气基线：SQLite contention、worker callback duplicate/out-of-order、`resume/approve/reject/cancel/reconcile` 幂等。因为当前控制平面的瓶颈不是功能缺失，而是 SQLite 单 writer 和多条控制流争用时的恢复成本。([SQLite首页][8])

G0 的完成标准只有四条：全量测试回绿；治理报表不再依赖 prose；活跃真相集合对齐；API router 拆壳完成但行为不变。做完这一步，才正式开 `M35`。([GitHub][2])

---

## 2. M35：把“谁用什么执行路径”做成一等产品面

这一阶段的目标不是再加 adapter，而是把**执行配置产品化**。路线图已经把 `M35` 说得很清楚：它的主题就是把 execution selection 变成 first-class product surface，并在 `Phase 0/1/2` 里分别完成 contract freeze、role/profile execution profiles、以及 config surfaces + dogfood。`M35` 的 exit 也定义得很清楚：系统必须能解释哪个 role 用哪条 lane，哪个 profile 覆盖了什么，cluster member 如何继承/覆盖默认值。([GitHub][2])

我建议你在代码上新增三组核心对象，而不是继续把新类型塞进现在已经很重的中心文件里。

第一组是契约层，新增：
`packages/contracts/execution_profiles.py`
包含 `ExecutionProfile`、`LaneSelection`、`ModelPolicy`、`ExecutionDefaultSet`、`ExecutionResolutionTrace`、`ClusterExecutionOverride`。

第二组是解析层，新增：
`packages/core_domain/execution_profile_resolver.py`
`packages/core_domain/service_execution_profiles.py`
`packages/core_domain/repositories_execution_profiles.py`

第三组是读面层，新增：
`packages/core_domain/service_capability_health.py`
负责把 `TD-STRUCT-005` 的窄切片 telemetry 做出来。仓库的 debt registry 已经明确写了，当前 capability health 还不是 runtime telemetry-backed，这会直接阻塞“可信的 readiness 和 routing 决策”。([GitHub][9])

解析优先级我建议定死为：

`built-in seed defaults → public role default → agent profile default → cluster member override → workflow.toml → env → explicit launch override`

这样做有三个好处。第一，它和 README 现有的 `workflow.toml + env + explicit override` 规则不冲突。第二，它能把目前散落在 `WorkerRouter`、gateway、环境变量里的默认选择统一收口。第三，它天然生成 `ExecutionResolutionTrace`，后面 UI、CLI、API 都能直接解释“为什么选了这条 lane”。([GitHub][1])

这一阶段最重要的重构动作，是**把执行选择从 `WorkerRouter` 和 gateway 的隐式默认里抽出来**。当前 router 仍然通过 capability 名称和环境变量挑默认 adapter；当前 runtime gateway 也还是一个 provider-aware 的独立边界。我的建议是：之后 router 和 gateway 都只消费**已解析完成的 execution decision**，不再自己猜默认值。这样 `coder` 用 `opencode`、`planner/researcher/reviewer` 走 `agent` 或 fallback、cluster member override 等逻辑，都会从“代码习惯”升级为“产品配置”。

`M35` 的 API/CLI/UI 也要一起补齐，不然它只是后端契约，不是产品。建议新增：

API：
`GET /config/effective-execution`
`GET /runs/{run_id}/execution`
`GET /interaction/sessions/{session_id}/execution-preview`
`GET /capability-health/lane-stats`

CLI：
`workflowctl config show-execution`
`workflowctl run explain-lane <run_id>`
`workflowctl interaction explain-session <session_id>`

Web UI：
在 `/ui/config` 显示 effective execution defaults 和 resolution trace；
在 `/ui/workbench` 显示 cluster、plan graph、selected lanes、review path。当前 API 已经有 governance 和 interaction session surface，说明这层入口基础是存在的。([GitHub][10])

`M35` 的验收不要空泛。我建议就用三条：

1. `DevCluster` 和 `ResearchCluster` 能在新默认值下完整跑通。
2. 任一 run 都能给出可解释的 execution trace。
3. capability health 至少对 shipped lanes 提供最近成功、最近失败、freshness、timeout rate、latency 中位数。

做完 `M35` 后，这个产品就第一次真正具备“不同角色不同执行路径，而且用户能看懂”的能力。([GitHub][2])

---

## 3. M36：把最小 preview 变成可用 workbench

路线图对 `M36` 的定义我基本原样赞成：不是做 operator console 2.0，而是把现在的 minimum preview 做成**usable natural-language workbench v1**，并且继续和 operator surface 分离。路线图还明确写了，当前的事实是 back-end interaction plane 已经存在，但 user-facing front-end workbench 还没有；`M36` 的目标是 guided goal input、clarification、plan draft、launch flow，以及 coherent 地显示 selected clusters、plan graph、review state。([GitHub][2])

你当前最省力、也最正确的做法，不是再造一套后端，而是**直接吃现有 interaction session API**。现在 API 已经有：
`POST /interaction/sessions`、`GET /interaction/sessions/{id}`、`POST /clarifications`、`POST /plan-draft`、`POST /launch`、`POST /followups`。这意味着 workbench 的主流程后端已经在了，缺的是前端信息架构、状态展示和操作闭环。([GitHub][10])

我建议把 workbench 做成 6 步固定流程：

1. Goal：输入自然语言目标。
2. Clarification：系统提出需要补齐的限制、假设、参考材料。
3. Plan Draft：展示推荐 preset、cluster、plan graph、review path。
4. Execution Preview：展示这次会用哪些 roles / profiles / lanes / defaults。
5. Launch：允许 `preview` 或 `execute`。
6. Follow-up：把后续补充问题、追加任务、人工批准、驳回都收回到同一会话线程。

这里不要一开始做真正流式聊天终端。先做**guided workbench**，用 polling 或 SSE 更新状态就够了。因为路线图自己也说了，这一阶段的目标是 usable workbench，不是无约束 conversational shell。([GitHub][2])

`M36` 还必须做一个产品级解释层：workbench 不只是“能发起 run”，而是要能告诉用户三件事——我选了什么 cluster、为什么选、下一步谁会做什么。否则它只是把 CLI 包了一层皮。做完 `M35` 后你已经会有 execution defaults 和 resolution trace；`M36` 只需要把这两块翻译成普通用户看得懂的语言即可。([GitHub][2])

`M36` 的完成标准也直接按路线图来定：workbench v1 可用、cluster-aware natural-language launch 成立、前端能 coherent 地进入现有控制平面。做到这里，产品第一次有了“不是给开发者，而是给普通操作者”的入口。([GitHub][2])

---

## 4. M37：有边界的生成角色与自动化平面

`M37` 的正确做法不是“放飞多 agent 自主运行”，而是按路线图说的那样，加**bounded autonomy**：generated profiles / role factory + automation controller / watchdog，而且始终保留 review gate 和审计线。([GitHub][2])

我建议这一阶段只做两类自动化：

第一类，**低风险自动化**：
定时生成 plan draft、整理 follow-up、检查待审 run、发出 capability 探针、生成 release readiness 草稿。
这类动作可以直接自动执行。

第二类，**高风险自动化**：
会触发 repo mutation、外部执行、worker dispatch、profile promotion 的动作。
这类动作只能自动生成**待批准的 intent / run**，不能直接越过 review gate 执行。

同时做一个 `ProfileFactory`，允许系统基于已有 public role 和 cluster context 生成受约束的内部 profile，但必须有：
生命周期、review、cleanup、promotion 规则。不要一开始让生成角色直接进入主 contracts；先停留在 governed generated profile 层。这样既符合路线图，也能避免把 `TD-STRUCT-006` 提前做成“动态对象泛滥”。([GitHub][2])

---

## 5. M38：把能力生态和工程流程真正产品化

路线图对 `M38` 的定义很准：统一 MCP、worker pools、sessions、connector-style capabilities，并把 preset 示例推进到 serious engineering-task product surfaces。([GitHub][2])

这一阶段我建议做四件事。

第一，定义 `CapabilitySDK`。
统一 capability descriptor、health、invocation envelope、execution receipt、auth、scope、timeout、cost hint、telemetry fields。现在治理和能力层 already 在 API 里有 surface，但还缺统一扩展模型。([GitHub][10])

第二，补 observability 正式路径。
OpenTelemetry 官方对生产环境的建议非常明确：应用 telemetry 应优先发到 Collector，使用 OTLP 是最佳实践，批量处理是推荐方式；Collector 本身也有明确的安全建议，包括最小权限、保护敏感数据和防 DoS。你的仓库已经有 trace-export abstraction，这一步应该把它升级成“默认 OTLP → Collector → backend”的标准线路。([OpenTelemetry][11])

第三，补 remote worker 安全和治理。
把现有 shared secret、worker pool、lease callback、dispatch envelope 进一步产品化成：
worker identity、secret rotation、pool health、callback replay protection、rate limiting、scope policy。因为你现在的 control plane 已经支持 remote worker，但产品级运营还差一层安全与治理闭环。([GitHub][1])

第四，增加真正可卖的工程 workflow preset。
至少补四个：`code_fix`、`refactor_slice`、`repo_audit`、`research_report`。
这样 `M38` 结束时，这套系统不再只有 demo/preset baseline，而是真能覆盖几类高频工程任务。([GitHub][2])

---

## 6. M39：评估、promotion、产品收口

`M39` 的主题就是 platform product closure。路线图写得很直接：它要完成 governed promotion、eval/canary、以及稳定产品 surface 的收口。([GitHub][2])

这一阶段必须上三套东西。

第一套，**EvalStore**。
把真实 run history、golden tasks、failure taxonomy、review outcomes 组织成评估数据集。以后每次 profile/prompt/route/preset 调整，都先过 eval 再 promotion。没有这层，自动化和 generated profiles 都会变成不可控漂移。

第二套，**Promotion Pipeline**。
对象包括 execution profiles、prompt bundles、capability routes、generated profiles。
状态至少有：`draft → canary → staged → stable → deprecated`。
每次 promotion 都要带：
eval 结果、回滚点、owner、审批记录、影响面说明。

第三套，**Release Closure**。
到 `M39` 结束时，必须能给出一个真正能装、能跑、能验、能观测的产品包：
`pip install` 本地安装仍保留；
再补一个 `docker compose` 本地栈，至少包括 API/Web UI、remote worker、OTel Collector、Jaeger/Prometheus 任选其一。
这样本地优先的产品面才算闭环，而不是“源码仓库可运行”。([GitHub][1])

`M39` 的 done 定义，我建议定成一句话：
**一个新用户拿到仓库后，不读历史 phase docs，也能在 30 分钟内启动 workbench、发起自然语言任务、看到执行解释、通过 review gate、回放审计、查看 telemetry。**
做到这点，才叫“完整产品”，不是“方向正确”。

---

## 7. 如果你的终点包含高质量游戏/设计交付，再加 M40

这个阶段不是平台必须项，但如果你的目标是高质量游戏内容、设计图、视觉风格一致性，那它就是必须项。路线图自己也说了，`M40` 是 `DesignCluster + multimodal visual verification`，这是通往 game-development-quality target 的额外里程碑。([GitHub][2])

我建议 `M40` 只做三件事：

1. `DesignCluster`：designer / art-director / visual-reviewer 三角色集群。
2. 多模态验证：参考图一致性、风格偏差、构图/色彩/角色轮廓检查。
3. 设计 promotion：设计规范、参考集、审美打分和回滚。

如果你不做这一步，`M39` 后的平台可以是完整的 agentic workflow 产品，但还不是你理想里的高质量游戏生产系统。([GitHub][2])

---

## 8. 代码结构怎么改，给你直接的落地版本

目标结构我建议变成这样：

* `apps/orchestrator_api/main.py`：只保留 app 装配和 router 注册
* `apps/orchestrator_api/routers/`：`runs.py`、`interaction.py`、`governance.py`、`scheduler.py`、`workers.py`、`config.py`、`ui.py`
* `packages/contracts/execution_profiles.py`
* `packages/contracts/capability_health.py`
* `packages/core_domain/bootstrap/`：container、factories、service wiring
* `packages/core_domain/service_execution_profiles.py`
* `packages/core_domain/service_capability_health.py`
* `packages/core_domain/service_workbench.py`
* `packages/core_domain/evals/`
* `packages/core_domain/promotion/`

`OrchestratorService` 之后只保留 façade 和兼容入口；新增业务逻辑不准再直接进它。这个要求不是审美问题，而是因为仓库自己已经把 `TD-STRUCT-001` 定义成“public facade 仍集中 cross-plane wiring 和大量 helper logic”，如果还继续往这个中心层加东西，后面的每一步都会更贵。([GitHub][9])

---

## 9. 你明天就可以按这个顺序开工

第 1 步：修治理回归，归档旧计划，开 `G0/hardening` 分支。
第 2 步：把 API 拆 router，但不改行为。
第 3 步：建 execution profile 契约和 resolver。
第 4 步：让 router/gateway 改为消费“已解析执行决策”。
第 5 步：补 effective execution / resolution trace 的 API、CLI、UI。
第 6 步：给 shipped lanes 加 runtime telemetry 窄切片。
第 7 步：做 `DevCluster` / `ResearchCluster` dogfood。
第 8 步：做 guided workbench 六步流。
第 9 步：加 generated profiles 与 bounded automation。
第 10 步：接 CapabilitySDK、OTLP Collector、eval/promotion、发布收口。

如果你按这个顺序推进，`M39` 结束时拿到的是一个**可安装、可解释、可启动、可审计、可扩展、可 promotion 的本地优先 agentic workflow 产品**；如果再加 `M40`，才是更接近你最终内容/游戏生产目标的系统。([GitHub][2])

一句话收束：**不要再把后续开发理解成“继续堆能力”，而要理解成“先把执行选择产品化，再把交互入口产品化，再把自动化、能力生态、promotion 收成完整产品”。** 当前仓库已经有足够强的内核，真正决定成败的，是你能不能在不继续做胖中心层的前提下，把它收成一个可以被正常人使用和运营的产品。([GitHub][7])

[1]: https://github.com/ghostairship-debug/universalworkflow/blob/main/README.md "https://github.com/ghostairship-debug/universalworkflow/blob/main/README.md"
[2]: https://github.com/ghostairship-debug/universalworkflow/blob/main/POST_M34_MULTIPHASE_ROADMAP.md "universalworkflow/POST_M34_MULTIPHASE_ROADMAP.md at main · ghostairship-debug/universalworkflow · GitHub"
[3]: https://github.com/ghostairship-debug/universalworkflow/blob/main/packages/core_domain/scheduler_authority.py "https://github.com/ghostairship-debug/universalworkflow/blob/main/packages/core_domain/scheduler_authority.py"
[4]: https://docs.langchain.com/oss/python/langgraph/overview "https://docs.langchain.com/oss/python/langgraph/overview"
[5]: https://fastapi.tiangolo.com/tutorial/bigger-applications/ "https://fastapi.tiangolo.com/tutorial/bigger-applications/"
[6]: https://github.com/ghostairship-debug/universalworkflow/blob/main/M34_POST_EVALUATION.md "https://github.com/ghostairship-debug/universalworkflow/blob/main/M34_POST_EVALUATION.md"
[7]: https://github.com/ghostairship-debug/universalworkflow/blob/main/docs/current_development_workflow.md "https://github.com/ghostairship-debug/universalworkflow/blob/main/docs/current_development_workflow.md"
[8]: https://sqlite.org/wal.html "https://sqlite.org/wal.html"
[9]: https://github.com/ghostairship-debug/universalworkflow/blob/main/docs/tech-debt-registry.md "https://github.com/ghostairship-debug/universalworkflow/blob/main/docs/tech-debt-registry.md"
[10]: https://github.com/ghostairship-debug/universalworkflow/blob/main/apps/orchestrator_api/main.py "https://github.com/ghostairship-debug/universalworkflow/blob/main/apps/orchestrator_api/main.py"
[11]: https://opentelemetry.io/docs/languages/python/exporters/ "https://opentelemetry.io/docs/languages/python/exporters/"
