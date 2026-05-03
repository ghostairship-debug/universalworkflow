# UniversalWorkflow 仓库深度评估报告

> 评估对象：<https://github.com/ghostairship-debug/universalworkflow/tree/main>
> 评估日期：2026-04-29
> 评估范围：当前状态、风险项、架构设计、商业游戏生产线、测试与 CI、开发方案、优化方案、后续优先级

---

## 0. 总体结论

这个仓库更像一个 **本地优先的 agentic workflow 控制平面 / 工作流运行时**，而不是单纯的游戏生成项目。

它的强项在于：

- 已经形成了任务卡、证据、回执、租约、路由、写入边界、provider 能力证明、离线验证、治理文档等体系；
- 对“AI 自动修改工程文件”这件事有较强的安全边界意识；
- 不再把普通 scaffold / smoke test 冒充商业级游戏结果；
- 已经开始从 demo 工程走向长期 agentic workflow runtime 的治理结构。

它的弱项也很明确：

- 当前主线声明的“商业级游戏生产”仍处于 **NO-GO**；
- 商业可玩性、Cocos 真实构建 / 游玩证据、产品深度、人工评审闭环还没有达标；
- README、pipeline、evaluation、active truth、task card、历史文档之间仍存在真相源漂移风险；
- 核心服务和核心领域模型正在变大，长期维护风险开始出现；
- provider / CLI / worker / Cocos Editor 等真实外部依赖还没有被稳定纳入可复现验证体系。

最关键的一句话：

> **这个仓库的“工作流控制系统”比“商业游戏生产结果”成熟得多。下一阶段应少做新 demo，多做真相源收敛、V2 合同落地、same-project patch 稳定化、Cocos 可信证据和 final gate 防误判。**

---

## 1. 当前状态评估

### 1.1 项目定位

当前仓库公开页面显示其定位已经比较清楚：它不是一个普通游戏项目，而是一个 local-first agentic workflow runtime。

从顶层结构看，项目包含：

- `.github/workflows`：CI 配置；
- `apps`：operator CLI、TUI、orchestrator API、remote worker API、scheduler authority API 等；
- `packages`：核心领域模型、runtime 集成、安全模块、worker adapters、contributions 等；
- `docs`：架构、评估、技术债、商业游戏生产线等文档；
- `infra`：基础设施配置；
- `tests`：核心、API、pipeline、LangGraph、Cocos、worker、repo mutation 等测试；
- `state`：运行证据、状态、产物；
- `examples/local_task_cards`：本地任务卡样例；
- `Makefile`、`pyproject.toml`、`requirements.lock`、`langgraph.json` 等工程配置。

项目已经不是脚本集合，而是一个具有控制面、运行面、证据面、治理面的复杂系统。

### 1.2 当前可用能力

从 README 和代码结构看，当前已经具备以下能力雏形：

- 本地 CLI；
- 本地 API；
- Web 控制台页面；
- run lifecycle；
- task card；
- route preview；
- evidence；
- operator packet；
- receipt / lease；
- repo mutation；
- test matrix；
- offline validation；
- pipeline preview / run；
- provider / worker 能力注册与路由；
- LangGraph runtime 试验性集成；
- remote worker / scheduler authority 相关 API。

这些能力说明项目已经进入“工作流控制系统”的早期成型阶段。

### 1.3 商业游戏方向当前状态

商业游戏方向目前仍不能判定为商业可交付。

已有文档已经主动修正了过去的误判：

- 旧的 `commercial_cocos_game` 固定模板路线已经被声明为移除或阻断；
- Cocos E2E / scaffold diagnostics 不允许再被当作商业游戏交付证明；
- 当前只能证明 technical smoke、E2E scaffold、局部原型或小目标 closeout；
- `commercial_playable_go` 仍然应保持为 false。

从最新评估看，关键缺口包括：

- same-project worker patch 未稳定成功；
- provider idle timeout；
- 产品深度 gate 缺失；
- 8 个 distinct level goals 未满足；
- shop / skin 未满足；
- 音频运行时证据不足；
- 音量切换证据不足；
- build / playtest 不足；
- 人工评审闭环不足。

因此，当前不能对外宣称“已经实现 AI 自动生产商业级 Cocos 游戏”。更准确的说法是：

> 已经形成商业游戏生产线 V2 的控制面设计和部分工程基础，但还没有形成稳定可复现的商业游戏生产能力。

---

## 2. 架构设计评估

## 2.1 分层结构

当前仓库分层大体合理：

```text
apps/
  operator_cli/
  operator_tui/
  orchestrator_api/
  remote_worker_api/
  scheduler_authority_api/

packages/
  contracts/
  core_domain/
  runtime_integrations/
  runtime_langgraph/
  runtime_security/
  worker_adapters/
  contributions/
```

这个结构体现了几条重要边界：

- `apps` 偏应用入口；
- `packages/core_domain` 偏核心领域能力；
- `packages/contracts` 偏共享合同；
- `packages/runtime_integrations` 偏外部运行时集成；
- `packages/runtime_security` 偏运行安全；
- `packages/worker_adapters` 偏 provider / worker 适配。

整体方向是对的。

但问题是：`core_domain` 已经非常大，长期有形成“上帝核心域”的风险。

建议后续按 bounded context 继续拆分：

- run lifecycle；
- task card；
- evidence；
- operator receipt；
- lease / scheduler；
- provider routing；
- repo mutation；
- pipeline execution；
- review / final gate；
- external worker gateway。

---

## 2.2 OrchestratorService 评估

当前 `OrchestratorService` 是系统事实上的应用服务门面。

它承担了大量职责：

- config；
- repositories；
- worker runtime；
- domain pack registry；
- simulation policy；
- evidence；
- auto review；
- durable runtime pilot；
- external worker gateway；
- orchestration engine；
- worker pools；
- scheduler authority；
- lease arbiter；
- repo mutation coordinator；
- operator action guard。

这个设计的优点是集中统一，方便 CLI / API 调用。

但它的风险也很明显：

- 编排、权限、证据、调度、worker、审计、修复等职责容易耦合；
- 新功能容易继续往 service 里塞；
- 一旦服务对象变成“万能门面”，后续拆分成本会快速上升；
- 测试会越来越偏集成测试，单元测试难度变大。

建议：

> 后续把 `OrchestratorService` 视为应用服务门面，而不是继续扩大它的领域职责。

具体拆分方向：

- `LeaseService`；
- `ReceiptService`；
- `RepoMutationService`；
- `ProviderRoutingService`；
- `PipelineExecutionService`；
- `ReviewPolicyService`；
- `SchedulerAuthorityService`；
- `EvidenceService`。

`OrchestratorService` 只负责事务性编排和入口聚合。

---

## 2.3 任务卡、证据与回执模型

这是当前仓库最值得保留和强化的部分。

项目已经形成了比较成熟的思路：

- task cards 以 DB 为权威，markdown 只是 snapshot；
- 每张卡需要 objective、owner、lease、write set、verification commands、acceptance gate、evidence requirements；
- 失败阶段不能随意提交；
- 业务 pipeline 必须通过 `workflowctl run from-task-card`；
- workflow bug 才能走 bug-first repair；
- operator receipt 作为人工 / 系统操作的可追踪回执；
- automation lease 用于防止多个 agent / worker 互相踩踏。

这套设计对于 agentic workflow 非常关键。

因为 agentic workflow 最大的问题不是“AI 能不能写代码”，而是：

- AI 为什么改？
- 改了哪里？
- 有没有授权？
- 有没有越界？
- 谁验收？
- 证据在哪里？
- 失败后怎么恢复？
- 多个 agent 是否互相冲突？

当前项目在这些问题上已经比普通 agent demo 更成熟。

---

## 2.4 Repo mutation 安全边界

`repo_mutation` 相关设计是当前系统的另一个重要优势。

已有能力大致包括：

- workspace root 限制；
- 路径归一化；
- allowed paths / write set；
- snapshot capture；
- restore / rollback；
- patch hash；
- unified diff 解析；
- 应用 diff 时的路径检查；
- 变更证据记录。

这说明项目没有简单地让 agent 直接获得无限制文件写入权限。

这是正确方向。

但后续要防止一个很大的漏洞：

> 只有所有入口都强制走同一套 repo mutation coordinator，这套安全边界才真的可靠。

需要重点防止以下入口绕过 write set：

- shell adapter；
- external worker；
- provider callback；
- Cocos bridge；
- 临时脚本；
- AI 生成的 build / repair script；
- 直接调用 git / filesystem 的工具层。

建议把“所有写入必须经过 repo mutation coordinator”写成硬性架构规则，并在 CI / static check 中验证。

---

## 2.5 Pipeline 设计状态

当前 pipeline 已经有框架，但还没有完全成熟。

从结构看，pipeline 已经覆盖：

- pipeline preview；
- stage 构造；
- Cocos readiness；
- capability stage；
- Cocos asset factory；
- Cocos graph pressure test；
- Cocos creator CLI；
- commercial game production 相关 stage。

问题在于：

- 部分 stage executor 仍类似 `stage_executor_not_registered` / `artifact_only_planning`；
- 有些阶段更像“规划产物”而不是真实执行器；
- 真实多阶段执行器、专业 worker、监督修复、最终 gate 的成熟度仍不足；
- 旧 pipeline 路线残留可能导致误用。

尤其需要核验：

> 文档宣称旧 `commercial_cocos_game` 路线已移除或阻断，但代码中仍可能有旧 template / old stage 函数残留。

这些残留即使是死代码，也会带来风险：

- 新 agent 可能误用旧路线；
- 新评估可能误读旧 artifact；
- README 与代码不一致；
- CI 不能阻止旧路径被重新激活。

建议将旧路线处理为以下三种之一：

1. 完全删除；
2. 保留但显式标记 deprecated，并在运行时 hard fail；
3. 转为历史 fixture，不允许进入真实 pipeline registry。

---

## 3. 测试、CI 与质量保障

### 3.1 测试覆盖现状

当前测试目录覆盖面比较广，包括：

- API；
- CLI；
- asset factory；
- capability；
- chat / LLM runtime；
- Cocos E2E；
- core domain purity；
- execution loop；
- governance；
- LangGraph；
- MCP broker；
- operator receipt；
- pipeline CLI；
- production LOC；
- remote worker；
- repo mutation；
- scheduler；
- web UI。

这说明作者已经意识到该项目不是单点功能，而是一套运行系统。

### 3.2 CI 现状

当前 CI 主要运行：

- Python 3.13 环境；
- lockfile 安装；
- package 安装；
- doc links；
- doctor strict；
- core tests；
- test matrix smoke；
- capability probe parser；
- scoped receipt smoke；
- offline validation。

这对核心治理和离线验证有价值。

但它还不能证明：

- 完整商业 pipeline 可运行；
- Cocos Creator 真实构建成功；
- 浏览器 playtest 成功；
- 多 provider 集成稳定；
- 慢速集成测试通过；
- 商业 final gate 可靠；
- 真实外部 worker 在超时 / 失败 / 部分修改情况下可恢复。

### 3.3 测试体系建议

建议将测试分为四层：

#### 第一层：Fast Core Tests

每次提交都跑。

覆盖：

- contracts；
- task card；
- receipt；
- lease；
- repo mutation；
- evidence；
- active truth；
- pipeline preview；
- final gate negative tests。

#### 第二层：Integration Tests

PR 或主分支合并时跑。

覆盖：

- orchestrator API；
- operator CLI；
- scheduler authority；
- remote worker API；
- fake provider contract；
- worker lease / heartbeat / timeout / retry。

#### 第三层：Cocos / Browser Tests

手动或 nightly 跑。

覆盖：

- Cocos bridge；
- Cocos build；
- browser launch；
- screenshot capture；
- audio event；
- volume toggle；
- mobile viewport；
- runtime assertions。

#### 第四层：Provider Contract Tests

不依赖真实强模型能力，只验证适配器合同。

覆盖：

- timeout；
- bad diff；
- forbidden path；
- partial patch；
- empty response；
- provider idle；
- retry budget；
- operator escalation。

---

## 4. 主要风险项

| 风险 | 严重度 | 说明 | 建议 |
|---|---:|---|---|
| 商业游戏能力过度宣称 | 高 | 当前文档已经修正为 NO-GO，但只要 README、pipeline、evaluation、artifact 名称不一致，就容易再次把 scaffold 当成 commercial playable。 | 强制 final gate negative tests，禁止 scaffold 进入 commercial GO。 |
| 真相源漂移 | 高 | README、CURRENT_DEVELOPMENT_WORKFLOW、evaluation、design doc、pipeline、active truth、DB task card 都在表达状态。 | 建立 active-truth-check，让不一致直接 CI fail。 |
| same-project worker patch 不稳定 | 高 | 最新 strict rerun 中 same-project patch 仍受 provider idle timeout、任务过大影响。 | 将大任务卡拆成小任务卡 DAG，支持 partial evidence 和 continuation。 |
| Cocos 真实交付证据不足 | 高 | 缺少真实构建、浏览器 playtest、runtime audio、UI/UX、shop/skin、人工评审证据。 | 建立 Cocos bridge ledger、build ledger、playtest ledger。 |
| 核心服务复杂度 | 中高 | `core_domain` 和 `OrchestratorService` 承载过多职责。 | 拆成独立 domain services 和 ports/adapters。 |
| CI 与真实运行差距 | 中高 | CI 偏核心 / offline validation，无法证明真实 provider / Cocos / commercial gate。 | 分层 CI：fast、integration、nightly Cocos、provider contract。 |
| 本地环境依赖强 | 中 | 依赖本地 Cocos Creator、provider CLI/API、各种模型账户和 CLI。 | 增加 doctor、capability probe、fixture、环境矩阵。 |
| 状态与产物膨胀 | 中 | `state`、pytest、Cocos artifacts 可能造成 repo bloat。 | 建立 artifact retention 和 `.gitignore` 策略。 |
| 适配器 / 文档一致性疑点 | 中 | 文档中 adapter 路径、测试路径、实际文件可能存在迁移残留。 | 加文档引用检查和 adapter registry check。 |
| 外部 worker 安全 | 中高 | remote worker / shell / provider callback 可能绕过写入边界。 | 所有写入强制经过 repo mutation coordinator。 |

---

## 5. 商业游戏生产线专项评估

### 5.1 V2 方向是正确的

`COMMERCIAL_GAME_PRODUCTION_V2_PIPELINE_DESIGN` 的方向是对的。

它没有继续把 pipeline 当成简单线性 stage，而是设计为：

```text
pipeline
  -> stage
    -> stage-internal phase graph
      -> DB task cards
        -> specialized worker
          -> supervisor / review / repair
            -> build / playtest / human review
```

这比“一个 prompt 让 AI 生成完整游戏”成熟得多。

它也明确了一个关键原则：

> Workflow 只作为控制平面，Cocos 才是生产表面。

这非常重要。

因为商业游戏最终不是看 markdown、JSON 或状态变量，而是看：

- Cocos 项目是否真实可构建；
- 构建后是否真实可打开；
- 玩家是否能玩；
- 游戏循环是否成立；
- UI、关卡、音效、反馈、商店、皮肤是否可见；
- 人工评审是否认为具备商业 demo 价值。

### 5.2 V2 应包含的核心阶段

建议保留并强化以下阶段：

#### Stage 0：Preflight / Truth

目标：确认环境、能力、版本、Cocos、provider、workspace、历史状态。

输出：

- active truth；
- capability report；
- environment report；
- pipeline route decision；
- GO / NO-GO 前置条件。

#### Stage 1：Product Architecture

目标：不是直接写代码，而是先定义产品方案。

输出：

- genre；
- core loop；
- player fantasy；
- art direction；
- level structure；
- progression；
- economy；
- UI map；
- audio plan；
- acceptance criteria。

#### Stage 2：Multimodal Asset Plan / Asset Graph

目标：生成或引用资产，但必须建立资产图。

输出：

- asset graph；
- asset license note；
- style guide；
- sprite / audio / UI asset list；
- required / optional asset distinction。

#### Stage 3：Cocos Editor Bridge Composition

目标：通过可信 Cocos bridge 建立项目结构。

输出：

- scene graph；
- node hierarchy；
- prefab / component binding；
- editor operation ledger；
- before / after validation。

#### Stage 4：Same-project Gameplay Implementation

目标：在同一个 Cocos 项目中实现真实 gameplay。

输出：

- core loop；
- levels；
- player control；
- enemies / obstacles；
- scoring；
- win / fail / restart；
- shop；
- skins；
- collection / economy；
- audio hooks。

#### Stage 5：Integration Repair

目标：修复构建、场景、资源、事件绑定、脚本错误。

输出：

- patch ledger；
- test result；
- build fix evidence；
- runtime fix evidence。

#### Stage 6：Build / Browser Playtest

目标：证明游戏真实可运行。

输出：

- Cocos build log；
- browser launch；
- screenshot；
- runtime assertions；
- audio runtime proof；
- volume toggle proof；
- player flow proof。

#### Stage 7：Commercial QA / Human Review

目标：防止机器自嗨。

输出：

- machine QA report；
- human review packet；
- reviewer decision；
- GO / NO-GO；
- rejection reasons；
- repair task cards。

### 5.3 当前最大差距

当前真正的问题不在设计，而在落地。

缺口包括：

- stage-internal phase graph 还没有完全工程化；
- DB task cards 还没有覆盖完整商业生产链路；
- specialized worker 还不够稳定；
- same-project patch 仍容易超时；
- Cocos bridge 可信证据不足；
- browser playtest 不足；
- 产品深度 gate 不足；
- human review 没有成为硬门槛；
- final gate 缺少足够 negative tests。

---

## 6. 建议开发方案

## 阶段 0：真相源收敛

第一优先级不是继续加功能，而是统一真相源。

需要统一的对象包括：

- README；
- CURRENT_DEVELOPMENT_WORKFLOW；
- evaluation reports；
- design docs；
- pipeline preview；
- active truth；
- DB task cards；
- CLI 输出；
- CI 检查。

建议新增一个强制检查：

```text
active-truth-check
```

它需要验证：

- 旧 pipeline 是否还可运行；
- commercial playable 状态是否与 evidence 一致；
- README 是否引用过期状态；
- evaluation 是否与 pipeline registry 一致；
- adapter 文档路径是否真实存在；
- deprecated route 是否会 hard fail；
- final gate 是否不能被 scaffold 通过。

交付标准：

- 不一致直接 CI fail；
- README 中的当前状态尽可能由机器生成；
- 手工维护的状态减少到最低。

---

## 阶段 1：V2 Contract 先行

不要先写更多 worker，而要先把 V2 设计变成稳定合同。

建议落地以下数据对象：

```text
StagePhase
TaskCard
AssetGraph
CocosBridgeLedger
SameProjectPatchLedger
BuildLedger
BrowserPlaytestLedger
CommercialFinalGateEvidence
HumanReviewPacket
```

每个对象都应该有：

- typed schema；
- JSON schema；
- golden fixture；
- negative fixture；
- validation function；
- CLI preview；
- evidence serialization；
- test coverage。

原因是：

> 没有合同，worker 越多越乱；合同稳定后，worker 才能自由替换。

---

## 阶段 2：same-project worker 稳定化

当前最大执行瓶颈是 same-project patch。

不要继续让 provider 一次性完成巨大任务。

建议改成“小任务卡 DAG”：

```text
Game Implementation DAG
  -> scene structure card
  -> core loop card
  -> player control card
  -> level goals card
  -> obstacle/enemy card
  -> scoring/progression card
  -> shop card
  -> skin card
  -> collection/economy card
  -> audio binding card
  -> volume toggle card
  -> build fix card
  -> playtest fix card
```

每张任务卡都必须包含：

- objective；
- allowed write set；
- max diff budget；
- max runtime；
- expected files；
- forbidden files；
- verification command；
- evidence requirements；
- rollback strategy；
- escalation rule。

这样可以解决几个问题：

- provider idle timeout；
- patch 过大；
- diff 难审查；
- 失败难定位；
- 多 agent 冲突；
- 证据不清晰。

---

## 阶段 3：Cocos Bridge 与真实构建

Cocos bridge 不能只看文件系统写入。

必须建立可信 ledger：

```text
CocosBridgeLedger
  operation_id
  operation_type
  target_scene
  target_node
  target_asset
  before_state
  after_state
  editor_report
  validation_result
  screenshot_optional
  error_optional
```

需要明确规则：

> filesystem-only 写入不能作为 commercial composition evidence。

也就是说，只是写了 `.ts`、`.prefab`、`.json` 文件，不等于 Cocos Editor 真实接受了项目结构。

真实商业 gate 至少需要：

- Cocos Editor / CLI 可识别；
- scene graph 可读取；
- script binding 可验证；
- asset reference 不丢失；
- build 可完成；
- browser 可打开。

---

## 阶段 4：产品深度 Gate

商业游戏不能只证明“项目能启动”。

建议 final gate 至少检查：

- 8 个 distinct level goals；
- 核心循环完整；
- 开始 / 游玩 / 胜利 / 失败 / 重开路径；
- 商店可见；
- 皮肤选择可见；
- 不同皮肤截图差异；
- 收集 / 经济闭环；
- BGM runtime event；
- SFX runtime event；
- 音量切换有效；
- 移动端 / Web 视口适配；
- 至少一轮浏览器 playtest；
- 至少一份人工评审。

final gate 必须避免以下误判：

- 有文件 ≠ 有游戏；
- 有场景 ≠ 可玩；
- 有构建 ≠ 商业可玩；
- 有截图 ≠ 玩家体验成立；
- 有内部状态变量 ≠ 玩家可见；
- 有 scaffold ≠ commercial playable。

---

## 阶段 5：人工评审闭环

建议增加明确状态：

```text
AWAITING_HUMAN_REVIEW
```

规则：

- 机器证据全部通过，但缺少人工评审：不能 GO；
- 人工评审不通过：进入 repair task cards；
- 人工评审通过，但机器证据缺失：不能 GO；
- 机器证据和人工评审都通过：才允许 commercial playable GO。

人工评审包应包含：

- 游戏说明；
- 核心循环说明；
- 操作方式；
- build 链接或本地路径；
- 截图；
- playtest 录像或日志；
- 已知问题；
- 评审 checklist；
- 评审结论。

---

## 阶段 6：CI 与发布硬化

CI 不应该试图每次都跑完整商业生产线，但需要分层。

建议：

```text
ci-fast
  contracts
  core_domain
  repo_mutation
  task_card
  final_gate_negative
  active_truth

ci-integration
  orchestrator_api
  operator_cli
  remote_worker
  scheduler_authority
  fake_provider

ci-nightly-cocos
  cocos_bridge
  cocos_build
  browser_playtest
  screenshot
  audio_runtime

ci-provider-contract
  codex/opencode/shell/noop adapters
  timeout
  partial_patch
  bad_diff
  forbidden_path
```

这比“要么全跑，要么都不跑”更适合当前项目。

---

## 7. 优化方案

### 7.1 架构优化

建议把当前大服务拆成更清晰的边界：

```text
Application Layer
  OrchestratorService
  OperatorCommandService

Domain Services
  TaskCardService
  EvidenceService
  ReceiptService
  LeaseService
  RepoMutationService
  PipelineExecutionService
  ProviderRoutingService
  ReviewGateService
  SchedulerAuthorityService

Ports
  ProviderPort
  WorkerPort
  FilesystemPort
  CocosBridgePort
  BrowserPlaytestPort
  ArtifactStorePort

Adapters
  CodexAdapter
  OpenCodeAdapter
  ShellAdapter
  NoopAdapter
  CocosCreatorAdapter
  BrowserAdapter
```

目标不是为了抽象而抽象，而是为了：

- 降低 `core_domain` 膨胀；
- 降低 service 耦合；
- 让 provider 可替换；
- 让 pipeline 可测试；
- 让 final gate 不依赖具体 worker；
- 让本地和云端部署路径一致。

---

### 7.2 Pipeline 优化

当前 pipeline 应从“线性 stage”升级为“stage 内部 phase graph”。

每个 phase 应定义：

- input contract；
- output contract；
- required evidence；
- failure class；
- retry policy；
- timeout policy；
- operator escalation；
- rollback strategy；
- downstream dependency。

这样失败时可以明确知道：

- 是 asset 失败；
- 是 bridge 失败；
- 是 patch 失败；
- 是 build 失败；
- 是 playtest 失败；
- 是 final gate 失败；
- 是 human review 失败。

而不是只看到一个大 stage failed。

---

### 7.3 安全优化

已有 repo mutation 安全基础不错，但需要继续强化。

建议增加：

- 所有写入入口强制经过 mutation coordinator；
- shell command allowlist；
- secret scanning；
- forbidden path policy；
- external worker callback HMAC；
- local API 默认只绑定 localhost；
- operator action guard；
- mutation diff size limit；
- generated script sandbox；
- artifact quarantine；
- rollback verification。

尤其注意：

> agentic workflow 的真正风险不是 AI 不够聪明，而是 AI 在不该写的地方写了东西，还被系统误判为成功。

---

### 7.4 文档优化

README 当前信息太重。

建议拆成：

```text
README.md
  项目定位
  安装
  快速开始
  当前 truth 摘要
  常用命令

/docs/status/current_truth.md
  机器生成的当前状态

/docs/design/
  架构设计
  pipeline 设计
  V2 design

/docs/evaluations/
  历史评估

/docs/runbooks/
  操作手册
  故障处理

/docs/history/
  M108/M109 等历史记录
```

这样可以降低 README 人工维护负担。

### 7.5 产物与 state 优化

建议对 `state`、pytest、Cocos artifacts 设置保留策略。

规则可以是：

- 仓库内只保留最小 golden evidence；
- 大型运行产物默认 `.gitignore`；
- 重要产物进入 artifact store；
- 每次 run 生成 manifest；
- 评估报告引用 manifest，而不是直接引用散乱文件；
- 定期清理过期 state。

---

## 8. 建议优先级清单

### P0：必须马上做

1. 建立 active truth check，统一 README、evaluation、pipeline、CLI、DB task card 状态。
2. 核验并清理旧 `commercial_cocos_game` 路线。
3. 建立 final gate negative tests，确保 scaffold 永远不能被判定为 commercial playable。
4. 把 V2 设计中的核心合同落地为代码对象。
5. 将 same-project gameplay implementation 拆成多张小 task card。
6. 修复 provider idle timeout 后的 partial evidence / continuation 机制。
7. 禁止 filesystem-only evidence 进入 commercial final gate。

### P1：下一阶段重点

1. 建立 CocosBridgeLedger。
2. 建立 SameProjectPatchLedger。
3. 建立 BrowserPlaytestLedger。
4. 增加音频 runtime proof。
5. 增加 volume toggle proof。
6. 建立 8 个 distinct level goals 的检查器。
7. 建立 shop / skin / economy 的玩家可见性检查。
8. 增加 `AWAITING_HUMAN_REVIEW` 状态。
9. 拆分 `OrchestratorService` 的部分职责。
10. 分层 CI。

### P2：中期优化

1. 引入更清晰的 ports/adapters。
2. 优化 Web 控制台，展示 evidence、lease、task card、run graph。
3. 增加 provider performance dashboard。
4. 增加 artifact retention。
5. 增加多 agent 冲突检测。
6. 增加自动 repair DAG。
7. 建立 game template / asset library / style guide registry。
8. 建立人工评审样本库。

---

## 9. 建议开发路线图

### M0：Truth & Safety Freeze

目标：停止真相源漂移，防止误判。

交付：

- active truth check；
- deprecated route hard fail；
- final gate negative tests；
- README 状态自动化；
- old artifacts 标注历史状态。

### M1：V2 Contracts

目标：把商业生产线从文档变成代码合同。

交付：

- StagePhase；
- AssetGraph；
- CocosBridgeLedger；
- SameProjectPatchLedger；
- BuildLedger；
- BrowserPlaytestLedger；
- CommercialFinalGateEvidence。

### M2：Task Card DAG

目标：解决大任务卡和 provider timeout。

交付：

- stage-internal phase graph；
- child task cards；
- partial evidence；
- retry budget；
- lease heartbeat；
- operator escalation。

### M3：Cocos Trusted Bridge

目标：从“文件存在”升级到“Cocos 可信接受”。

交付：

- editor report；
- scene graph validation；
- component binding validation；
- asset reference validation；
- build preflight。

### M4：Playable Evidence

目标：证明玩家真的可以玩。

交付：

- build；
- browser launch；
- screenshot；
- runtime assertions；
- audio proof；
- volume proof；
- mobile viewport proof。

### M5：Commercial Gate

目标：建立商业可玩判断。

交付：

- product depth gate；
- shop / skin / economy gate；
- 8 level goals gate；
- human review；
- GO / NO-GO report。

---

## 10. 综合评分

| 维度 | 评分 | 判断 |
|---|---:|---|
| 架构方向 | 7.5 / 10 | local-first 控制面、证据、回执、租约、write set 方向正确，但核心服务复杂度偏高。 |
| 工程治理 | 8 / 10 | task cards、evidence、operator receipt、active truth、tech debt registry 很强。 |
| 可维护性 | 6 / 10 | 模块很多，文档很多，核心域偏大，真相源漂移风险明显。 |
| 测试与 CI | 6.5 / 10 | 测试面广，CI 有核心验证，但真实 Cocos / provider / commercial gate 仍不足。 |
| 安全边界 | 7 / 10 | repo mutation 边界设计不错，但需要确认所有外部入口都强制经过它。 |
| 商业游戏生产能力 | 3.5 / 10 | 设计清楚，但当前 strict rerun 仍 NO-GO，不能宣称商业可玩。 |
| 文档可信度 | 6.5 / 10 | 文档非常诚实，但状态更新密集，代码 / 文档一致性需机器化保障。 |
| 综合成熟度 | 6.5 / 10 | 作为 agentic workflow runtime 已有较好基础；作为商业游戏自动生产线仍处验证阶段。 |

---

## 11. 最终建议

当前最不应该做的是继续堆新 demo。

更应该做的是：

1. **收敛真相源**：先保证系统不会再把 scaffold 误判成商业游戏。
2. **落地 V2 合同**：把设计文档里的核心对象变成代码和测试。
3. **拆分任务卡**：解决 same-project worker patch 超时和不可控问题。
4. **建立 Cocos 可信证据**：从文件级证明升级到 Editor / build / browser / player 级证明。
5. **强化 final gate**：商业可玩必须同时满足机器证据和人工评审。
6. **降低核心复杂度**：把 `OrchestratorService` 和 `core_domain` 的职责逐步拆开。

如果这几步完成，这个项目会从“架构很宏大的 agentic workflow 实验系统”进入“有可信控制面和可验证产出的生产系统雏形”。

如果继续绕过这些问题直接追求“更大的自动生成 demo”，很可能会进入：

- 产物越来越多；
- 文档越来越多；
- 状态越来越乱；
- agent 改动越来越不可控；
- 但真实商业可玩能力没有明显提升。

因此，下一阶段的核心关键词应该是：

> **truth、contract、evidence、small task cards、trusted Cocos bridge、final gate。**
