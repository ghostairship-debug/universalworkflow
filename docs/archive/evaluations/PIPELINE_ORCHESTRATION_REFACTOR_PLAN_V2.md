# Pipeline Orchestration v2 重构方案

> 建议文件名：`PIPELINE_ORCHESTRATION_REFACTOR_PLAN_V2.md`  
> 建议位置：仓库根目录或 `docs/architecture/PIPELINE_ORCHESTRATION_REFACTOR_PLAN_V2.md`  
> 适用阶段：M73 / M74 / M75  
> 当前基线：M72 Trusted Self-Development Baseline  
> 目标：在不破坏现有 cluster / workflow dogfood 基础的前提下，建立真正的 Pipeline 编排层，使 UniversalWorkflow 从“workflow 自开发角色组”升级为“可手动/智能/混合编排的长流程 AI 工作流控制塔”。

---

## 0. 本版修正点

本版文档修正上一版方案中的几个关键问题。

### 0.1 不再新增一堆 `game_*_cluster`

上一版把 H5 游戏商业化拆成：

```text
game_intake_cluster
game_design_cluster
game_implementation_cluster
game_qa_cluster
game_art_audio_cluster
game_monetization_cluster
```

这个方向容易导致 cluster 数量膨胀，并再次把系统推向硬编码模块堆叠。

本版改为：

```text
H5 游戏商业化 = 一个专门的 Pipeline Template / Pipeline Profile
而不是一堆专门的 game clusters
```

也就是说：

```text
h5_game_commercialization_pipeline
```

可以编排：

```text
通用 role
通用 cluster
capability
human checkpoint
sub-pipeline
validation gate
```

而不是新增大量固定 game clusters。

---

### 0.2 Pipeline 不应只编排 cluster

上一版写成“Pipeline-of-Clusters”，表达不够准确。

更准确的定义应是：

```text
Pipeline = 多种执行单元的有序 / 条件 / 并行编排
```

Pipeline stage 可以是：

```text
agent_role
cluster
capability
human_checkpoint
sub_pipeline
validation_gate
external_worker
```

因此，后续可继续使用“Pipeline-of-Clusters”作为直观说法，但模型上必须支持：

```text
Pipeline-of-Execution-Units
```

---

### 0.3 Pipeline 必须支持三种编排来源

Pipeline 不应只有固定模板。必须支持：

```text
manual       手动编排
ai_generated 智能编排
hybrid       智能编排后人工调整
```

其中最重要的是：

```text
hybrid = AI 生成 pipeline draft → operator 手动调整 → policy/capability preview → 确认执行
```

这是最符合实际使用方式的模式。

---

### 0.4 LangGraph 不应替代 Pipeline 产品层

LangGraph 可以承担底层执行能力：

```text
graph execution
checkpoint
resume
interrupt
subgraph
streaming
durable state
```

但 UniversalWorkflow 仍应自研 Pipeline 产品语义：

```text
PipelineDraft
PipelineStage
PipelineAdjustment
PipelineHandoff
PolicyPreview
CapabilityProjection
OperatorPacket
Evidence
```

最终分工：

```text
Pipeline 的定义、编辑、治理：UniversalWorkflow 自研
Pipeline 的执行、暂停、恢复、状态：借用 LangGraph
```

---

## 1. 当前仓库事实基线

本节以当前 M72/M73 状态为基准。

### 1.1 当前接受基线

当前项目基线是：

```text
M72: Trusted Self-Development Baseline
```

M73 建议进入 capability-layer development。

当前项目已经具备：

```text
1. workflow dogfood 规则
2. scoped OperatorActionReceipt
3. provider live proof
4. provider contract registry
5. capability control-plane decision
6. parallel execution contract
7. self-development manifest
8. 文档真相源治理
```

但当前仍未完成：

```text
1. 真正的 Pipeline 编排层
2. 多 cluster pipeline execution
3. Pipeline draft / adjustment / approval 模型
4. LangGraph runtime substrate 化
5. MCP Broker v1
6. AutomationLease v0
7. H5 游戏商业化 pipeline
```

---

### 1.2 当前 cluster 能力

当前默认 cluster 大体包括：

```text
dev_cluster
research_cluster
architecture_delivery_cluster
search_cluster
design_cluster
multimodal_cluster
review_cluster
management_cluster
```

这些 cluster 当前更适合：

```text
workflow 自开发
代码交付
管理收口
文档治理
provider / capability / evidence 验证
```

它们不应被误认为已经是最终的业务 Pipeline 模块。

---

### 1.3 当前多 cluster 能力

当前系统已经具备：

```text
1. cluster 选择
2. preferred / preset / marker routing
3. dynamic cluster route decision
4. 多 cluster preview graph 合并
5. cluster execution plan 展示
6. 单 cluster 内 member 编排与并发
```

但当前还没有成熟的：

```text
1. 多 cluster 串行/条件/并行执行
2. cluster A 输出自动作为 cluster B 输入
3. 跨 cluster handoff schema
4. 跨 cluster stage gate
5. 跨 cluster failure recovery
6. operator 可编辑 pipeline draft
```

因此当前状态应描述为：

```text
single-cluster execution + multi-cluster preview / selection
```

而不是：

```text
mature pipeline orchestration
```

---

### 1.4 当前 LangGraph 集成

当前 LangGraph 集成是 M68 focused runtime：

```text
planning -> review -> evidence
```

它是：

```text
opt-in
advisory-only
不 compile
不 resume
不 patch apply
不作为 workflow 状态源
```

这说明 LangGraph 目前还不是 runtime substrate，只是一个安全的 advisory focused runtime。

后续如要做真正 pipeline execution，应通过：

```text
LangGraphPipelineAdapter
```

逐步接入 checkpoint / interrupt / resume / subgraph / streaming。

---

## 2. 重新定义核心概念

后续应建立四层模型：

```text
L1 AgentProfile
L2 WorkCluster
L3 PipelineStage
L4 WorkflowPipeline
```

---

### 2.1 AgentProfile

定义单个 agent 角色。

示例：

```text
search_scout
citation_checker
principal_architect
product_designer
visual_reviewer
monetization_reviewer
playwright_runner
```

AgentProfile 应包含：

```text
profile_id
role_label
capability_tags
allowed_capabilities
denied_capabilities
system_brief
termination_rule
evaluation_rubric
execution_profile
```

AgentProfile 不是 pipeline，也不是 cluster。

---

### 2.2 WorkCluster

定义一个复杂模块内部的多 agent 团队。

例如：

```text
research_cluster
design_cluster
dev_cluster
review_cluster
multimodal_cluster
architecture_delivery_cluster
```

WorkCluster 应包含：

```text
cluster_template_id
objective
member_specs
execution_mode
handoff_points
required_evidence
acceptance_criteria
review_rubric
allowed_capabilities
denied_capabilities
```

WorkCluster 是可复用团队，不应为每个业务方向无限增殖。

---

### 2.3 PipelineStage

PipelineStage 是最关键的新抽象。

它不是 cluster，也不必须是 cluster。

一个 stage 可以是：

```text
agent_role
cluster
capability
human_checkpoint
sub_pipeline
validation_gate
external_worker
```

建议 schema：

```python
class PipelineStage:
    stage_id: str
    name: str
    stage_type: Literal[
        "agent_role",
        "cluster",
        "capability",
        "human_checkpoint",
        "sub_pipeline",
        "validation_gate",
        "external_worker"
    ]

    # one-of references
    agent_profile_id: str | None
    cluster_template_id: str | None
    capability_id: str | None
    sub_pipeline_id: str | None
    external_worker_id: str | None

    # contextual profile, not a new cluster
    stage_profile: str | None
    domain_context: dict

    input_schema: str | None
    output_schema: str | None
    required_artifacts: list[str]
    acceptance_criteria: list[str]

    read_set: list[str]
    write_set: list[str]
    test_commands: list[str]

    requires_receipt: bool
    requires_human_checkpoint: bool
    allowed_capabilities: list[str]
    denied_capabilities: list[str]

    retry_policy: dict | None
    failure_policy: str
```

---

### 2.4 WorkflowPipeline

WorkflowPipeline 是多个 stage 的有序/条件/并行编排。

建议 schema：

```python
class WorkflowPipeline:
    pipeline_id: str
    name: str
    source: Literal["manual", "ai_generated", "template", "hybrid"]
    status: Literal[
        "draft",
        "reviewing",
        "approved",
        "executing",
        "paused",
        "completed",
        "failed",
        "cancelled"
    ]

    stages: list[PipelineStage]
    handoffs: list[PipelineHandoff]
    adjustments: list[PipelineAdjustment]

    policy_preview: dict | None
    capability_projection: dict | None
    operator_checkpoints: list[str]
    final_acceptance_criteria: list[str]
```

---

## 3. Pipeline 编排模式

Pipeline 必须支持三种来源。

---

### 3.1 Manual Pipeline：手动编排

用户明确指定 stages。

适合：

```text
1. 高风险任务
2. 用户非常清楚流程
3. 重复性强的固定流程
4. 需要强控制的任务
```

示例：

```text
Stage 1: research_cluster
Stage 2: architecture_design role
Stage 3: codex implementation
Stage 4: playwright capability
Stage 5: final_review_cluster
```

CLI 示例：

```powershell
workflowctl pipeline draft create --source manual --name "H5 Game Smoke"
workflowctl pipeline stage add --type cluster --cluster-template-id design_cluster
workflowctl pipeline stage add --type capability --capability-id playwright_runner
workflowctl pipeline stage add --type cluster --cluster-template-id review_cluster
workflowctl pipeline preview <pipeline_id>
```

---

### 3.2 AI-generated Pipeline：智能编排

AI 根据用户目标生成 pipeline draft。

适合：

```text
1. 用户只描述目标
2. 任务复杂
3. 流程不确定
4. 需要 AI 帮忙设计工作流
```

流程：

```text
goal
→ pipeline planner
→ PipelineDraft
→ policy preview
→ capability projection
→ operator review
```

注意：

```text
AI-generated pipeline 默认不执行。
必须经过 preview / policy / operator confirmation。
```

---

### 3.3 Hybrid Pipeline：智能编排后人工调整

这是最重要的实际模式。

流程：

```text
用户输入目标
→ AI 生成 pipeline draft
→ operator 手动调整
    - 删除 stage
    - 增加 stage
    - 替换 stage
    - 重新排序
    - cluster 换成单 role
    - role 换成 capability
    - 修改 write_set
    - 修改 test_commands
    - 修改 human checkpoint
    - 修改 adapter/model
→ 重新生成 policy preview
→ 重新生成 capability projection
→ operator 确认
→ 执行
```

Hybrid pipeline 必须记录：

```text
PipelineAdjustment
```

---

## 4. PipelineAdjustment

人工调整应成为一等对象。

建议 schema：

```python
class PipelineAdjustment:
    adjustment_id: str
    operation: Literal[
        "add_stage",
        "remove_stage",
        "replace_stage",
        "reorder_stage",
        "edit_stage",
        "split_stage",
        "merge_stage"
    ]
    target_stage_id: str | None
    before: dict
    after: dict
    rationale: str
    operator_id: str
    created_at: datetime
```

这样可以审计：

```text
AI 原本怎么编排
用户改了什么
为什么改
改后是否仍满足 policy
```

---

## 5. PipelineHandoff

Pipeline 中每个 stage 结束都必须产生结构化 handoff。

建议 schema：

```python
class PipelineHandoff:
    handoff_id: str
    from_stage_id: str
    to_stage_id: str
    artifact_refs: list[str]
    summary: str
    blocking_risks: list[str]
    next_stage_inputs: dict
    confidence: float | None
```

原则：

```text
下一个 stage 不应读取前一个 stage 的杂乱上下文；
下一个 stage 应读取结构化 handoff。
```

---

## 6. Pipeline 与 LangGraph 的分工

### 6.1 UniversalWorkflow 自研

UniversalWorkflow 应负责：

```text
PipelineTemplate
PipelineDraft
PipelineStage
PipelineAdjustment
PipelineHandoff
PipelinePolicyPreview
PipelineCapabilityProjection
OperatorActionReceipt
AutomationLease
Evidence
OperatorPacket
```

这些是产品语义和治理语义。

---

### 6.2 LangGraph 负责

LangGraph 应负责：

```text
graph execution
checkpoint
resume
interrupt
human-in-the-loop
subgraph
streaming
durable runtime state
```

---

### 6.3 通过 Adapter 借用 LangGraph

不要让业务代码到处直接 import LangGraph。

建议新增：

```text
packages/runtime_langgraph/pipeline_adapter.py
```

接口：

```python
class LangGraphPipelineAdapter:
    def compile(self, pipeline: WorkflowPipeline) -> CompiledGraph:
        ...

    def start(self, pipeline_run_id: str) -> dict:
        ...

    def resume(self, pipeline_run_id: str, resume_payload: dict) -> dict:
        ...

    def stream(self, pipeline_run_id: str):
        ...
```

---

## 7. Pipeline stage 到 LangGraph node 的映射

| stage_type | LangGraph node wrapper |
|---|---|
| `agent_role` | 调用 agent profile runner |
| `cluster` | 调用现有 cluster orchestration |
| `capability` | 调用 capability control plane / adapter / MCP |
| `human_checkpoint` | `interrupt()` |
| `sub_pipeline` | 调用 subgraph |
| `validation_gate` | 跑测试 / acceptance report |
| `external_worker` | 调用 worker router / remote worker |

---

## 8. H5 游戏商业化 Pipeline v0

H5 游戏不应拆成一堆固定 game clusters。

应新增一个 pipeline template：

```text
h5_game_commercialization_pipeline
```

它编排通用 stage。

---

### 8.1 推荐 stages

```text
project_intake
game_design
implementation
browser_smoke_test
visual_review
monetization_review
final_review
```

---

### 8.2 stage 示例

```json
{
  "pipeline_id": "h5_game_commercialization_pipeline",
  "source": "template",
  "stages": [
    {
      "stage_id": "project_intake",
      "stage_type": "agent_role",
      "agent_profile_id": "project_scanner",
      "stage_profile": "h5_game_project_intake",
      "output_schema": "GameProjectProfile"
    },
    {
      "stage_id": "game_design",
      "stage_type": "cluster",
      "cluster_template_id": "design_cluster",
      "stage_profile": "game_design",
      "output_schema": "GameDesignSpec"
    },
    {
      "stage_id": "implementation",
      "stage_type": "cluster",
      "cluster_template_id": "dev_cluster",
      "stage_profile": "game_implementation",
      "output_schema": "GamePatchSet"
    },
    {
      "stage_id": "browser_smoke_test",
      "stage_type": "capability",
      "capability_id": "playwright_runner",
      "output_schema": "GameAcceptanceReport"
    },
    {
      "stage_id": "visual_review",
      "stage_type": "agent_role",
      "agent_profile_id": "visual_reviewer",
      "stage_profile": "game_visual_review",
      "output_schema": "VisualReviewReport"
    },
    {
      "stage_id": "monetization_review",
      "stage_type": "agent_role",
      "agent_profile_id": "monetization_reviewer",
      "stage_profile": "game_monetization_review",
      "output_schema": "MonetizationFlowReview"
    },
    {
      "stage_id": "final_review",
      "stage_type": "cluster",
      "cluster_template_id": "review_cluster",
      "stage_profile": "game_final_review",
      "output_schema": "FinalReviewVerdict"
    }
  ]
}
```

关键点：

```text
game 是 pipeline profile；
不是 cluster taxonomy。
```

---

## 9. 现有 cluster 的重新定位

不要删除现有 cluster。

应重新归类：

### 9.1 Internal workflow clusters

```text
management_cluster
architecture_delivery_cluster
review_cluster
dev_cluster
```

用途：

```text
workflow 自开发
架构维护
治理收口
代码实现
```

---

### 9.2 Support clusters

```text
search_cluster
research_cluster
design_cluster
multimodal_cluster
```

用途：

```text
作为 pipeline stage 的可复用模块
```

---

### 9.3 不新增大量业务 cluster

原则：

```text
业务差异优先体现在 pipeline template / stage_profile / domain_context；
不是新增大量 cluster_template。
```

例如：

```text
design_cluster + stage_profile=game_design
design_cluster + stage_profile=ui_design
design_cluster + stage_profile=business_solution

review_cluster + stage_profile=game_final_review
review_cluster + stage_profile=security_review
review_cluster + stage_profile=release_review
```

---

## 10. Pipeline routing

当前 routing 主要是：

```text
keyword marker -> cluster
```

后续应升级为：

```text
goal -> execution_mode
```

可选 execution_mode：

```text
single_agent
single_cluster
pipeline_template
ai_generated_pipeline
manual_pipeline
```

---

### 10.1 路由规则

```text
简单任务：
    single_agent

中等任务：
    single_cluster

复杂长流程：
    pipeline_template 或 ai_generated_pipeline

用户指定流程：
    manual_pipeline

AI 生成后人工调整：
    hybrid_pipeline
```

---

### 10.2 H5 游戏路由

如果 goal 包含：

```text
H5
小游戏
商业化
游戏改造
自动试玩
广告
移动端
```

不应直接 route 到：

```text
dev_cluster
```

而应推荐：

```text
h5_game_commercialization_pipeline
```

但这只是推荐，operator 可调整。

---

## 11. 分阶段实施路线

## M73A：语义和文档收口

目标：

```text
明确 Pipeline 不等于 Cluster，Game 不等于一堆 Game Clusters。
```

任务：

```text
1. 新增本文档。
2. 更新 AGENTS.md：
   - AgentProfile = single role
   - WorkCluster = reusable multi-agent team
   - PipelineStage = role / cluster / capability / checkpoint / subpipeline / validation gate
   - WorkflowPipeline = ordered/conditional execution plan
   - Game commercialization is a pipeline template/profile, not many game clusters
3. 不改变运行逻辑。
```

验收：

```text
- 文档清晰
- 现有测试不变
- 现有 cluster routing 不变
```

---

## M73B：Pipeline contracts

目标：

```text
先有 contract，不急着执行。
```

新增：

```text
PipelineDraft
PipelineStage
PipelineHandoff
PipelineAdjustment
WorkflowPipeline
```

测试：

```text
contract round-trip
stage type validation
manual / ai_generated / hybrid source validation
adjustment audit validation
```

验收：

```text
- 不影响现有 run / cluster
- contracts round-trip passed
```

---

## M73C：Pipeline preview

目标：

```text
支持 pipeline draft 预览。
```

能力：

```text
1. manual draft preview
2. template draft preview
3. ai-generated draft preview
4. hybrid adjusted preview
5. policy preview
6. capability projection
7. risk summary
```

验收：

```text
- h5_game_commercialization_pipeline 可以 preview
- preview 不执行、不 mutation
- preview 可以展示 stage type 和 handoff
```

---

## M73D：Pipeline adjustment

目标：

```text
支持 AI 生成后人工调整。
```

能力：

```text
add_stage
remove_stage
replace_stage
reorder_stage
edit_stage
split_stage
merge_stage
```

验收：

```text
- adjustment 记录 before/after/rationale
- adjustment 后重新计算 policy preview
- adjustment 后重新计算 capability projection
```

---

## M74A：LangGraph pipeline execution spike

目标：

```text
验证借用 LangGraph 执行 pipeline 的可行性。
```

范围：

```text
非 mutation
小闭环
包含 human checkpoint
包含 resume
包含 evidence
```

示例：

```text
project_intake
-> human_checkpoint
-> browser_smoke_test
-> final_review
```

验收：

```text
- checkpoint 可恢复
- interrupt 可 resume
- streaming event 可见
- 不 patch apply
- 不改变现有 run 真相源
```

---

## M74B：最小串行 Pipeline Execution

目标：

```text
实现串行 pipeline execution。
```

要求：

```text
1. 每个 stage 产生 handoff。
2. 下一个 stage 读取 handoff。
3. stage failure 可以暂停。
4. operator 可 resume / cancel。
5. operator packet 显示 pipeline lineage。
```

验收：

```text
- 一个通用 software_delivery_pipeline 能跑通
- 一个 h5_game_commercialization_pipeline v0 能跑到 browser_smoke_test
```

---

## M75：H5 pipeline v1

目标：

```text
H5 游戏商业化 pipeline 初版。
```

不新增一堆 game clusters。

新增：

```text
h5_game_commercialization_pipeline template
project_scanner role
visual_reviewer role
monetization_reviewer role
playwright_runner capability
GameProjectProfile schema
GameAcceptanceReport schema
```

验收：

```text
- 输入一个 H5 项目
- 生成 GameProjectProfile
- 执行小改动
- 启动浏览器 smoke
- 输出 GameAcceptanceReport
- final_review 给出 GO / NO-GO
```

---

## 12. Codex 实施提示词

可以直接交给 Codex：

```text
You are working on UniversalWorkflow.

Important correction:
Do not add many game-specific clusters. H5 game commercialization should be modeled as a pipeline template/profile, not as game_intake_cluster/game_design_cluster/game_qa_cluster/etc.

Goal:
Introduce Pipeline Orchestration v2 semantics without changing runtime behavior first.

Definitions:
- AgentProfile = a single role.
- WorkCluster = a reusable multi-agent team.
- PipelineStage = an execution unit. It may be an agent_role, cluster, capability, human_checkpoint, sub_pipeline, validation_gate, or external_worker.
- WorkflowPipeline = ordered/conditional stages with handoffs, policy preview, capability projection, and operator adjustments.
- Pipeline source can be manual, ai_generated, template, or hybrid.

Tasks:
1. Add docs/architecture/PIPELINE_ORCHESTRATION_REFACTOR_PLAN_V2.md.
2. Update AGENTS.md with the corrected semantics.
3. If low risk, add contract skeletons:
   - PipelineDraft
   - PipelineStage
   - PipelineHandoff
   - PipelineAdjustment
   - WorkflowPipeline
4. Add contract round-trip tests.
5. Do not change existing cluster execution.
6. Do not delete existing clusters.
7. Do not add game_* clusters.
8. Do not make LangGraph the product model. LangGraph should only be used later through a pipeline adapter for execution/checkpoint/interrupt/resume.

Acceptance:
- Existing tests pass.
- New contract tests pass.
- Existing cluster routing remains unchanged.
- H5 game is represented as a pipeline template/profile, not a set of game clusters.
```

---

## 13. 最终结论

本阶段真正需要补的是：

```text
Pipeline 产品层
```

而不是：

```text
更多 cluster
```

最终目标：

```text
Pipeline 可以编排 role、cluster、capability、checkpoint、sub-pipeline；
Pipeline 可以手动编排、智能编排、智能编排后人工调整；
H5 游戏是 pipeline/profile，不是一堆专门 cluster；
执行层尽量借 LangGraph，产品语义留在 UniversalWorkflow。
```
