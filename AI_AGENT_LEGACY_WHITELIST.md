# AI Agent 遗产白名单

> 形成日期：2026-04-21  
> 适用对象：`D:\AI Agent` 旧仓库遗产  
> 使用原则：**白名单仅代表“值得继续参考”**，不代表“应该直接回收代码”。

## 1. 白名单目的

这份清单用于回答一个很具体的问题：

当前 `D:\AI Agent` 这套遗产里，哪些内容对 `D:\Universal Agentic workflow` 未来仍有参考价值？

结论不是“整体回收”或“整体放弃”，而是分三类看待：

1. 可作为长期产品形态参考
2. 可作为协议/控制面设计参考
3. 可作为未来特定 Domain Pack 的前期思想样本

默认使用方式：

- 参考其设计思想、协议边界、能力拆分方式
- 不直接复制其大块实现代码
- 不把旧仓库重新并回当前主仓

## 2. 入选标准

只有满足至少一条的内容才进入白名单：

1. 对当前项目的长期产品形态仍有指导价值
2. 提供了当前仓库尚未完全吸收的协议设计或控制面思路
3. 对未来多 agent、外部能力接入、自然语言控制、自我升级、Domain Pack 扩展有现实参考意义
4. 能作为未来方案评审时的“已想过/已踩坑”证据

## 3. 白名单

### A1. 总体架构蓝图

- 路径：`D:\AI Agent\universal_agentic_workflow_os_local_first_plan_v2_1.md`
- 类型：长期产品形态蓝图
- 价值等级：高
- 推荐用途：
  - 参考通用内核、控制面、能力面、调度面、记忆面、Domain Pack 这些长期抽象
  - 参考 local-first / cloud-ready 的演进思路
  - 参考“通用工程操作系统”而不是“单一 agent 工具”的产品定位
- 当前仍有价值的原因：
  - 这份文档已经明确提出了 `Domain Pack`、多运行时统一调度、MCP 只是接入总线而不是主状态机、通用内核 + 领域扩展这些关键方向
  - 当前仓库已经吸收了其中相当一部分，但它仍然是长期产品形态最完整的一份早期蓝图
- 使用边界：
  - 只用于长期路线评审和架构抽象对齐
  - 不按这份文档逐条恢复历史实施计划

### A2. Commander 去裁量化协议

- 路径：
  - `D:\AI Agent\.opencode\agents\workflow-commander.md`
  - `D:\AI Agent\src\agentic_kernel\mcp_server.py`
- 类型：多 agent 协作控制协议
- 价值等级：高
- 推荐用途：
  - 参考如何把 commander 从“自己做判断的智能调度者”收敛成“消费合法动作描述的协议执行器”
  - 参考 pre-runtime 阶段如何限制 planner / researcher 的合法路由
  - 参考自然语言入口如何落到安全的结构化动作链
- 当前仍有价值的原因：
  - 它已经把 `workflow_find_related_projects`、`workflow_select_authoring_target`、`descriptor.subagent_type` 这类控制信号工具化
  - 这正对应你关心的未来多 agent 协作和自然语言控制问题
- 使用边界：
  - 参考协议设计，不直接迁入 OpenCode 专用 prompt 细节
  - 不直接把旧 MCP tool surface 整包恢复到当前仓库

### A3. 文档驱动 phase/task-card 样板

- 路径：
  - `D:\AI Agent\.kernel\PROJECT.md`
  - `D:\AI Agent\.kernel\PHASES.md`
  - `D:\AI Agent\.kernel\phase-*`
- 类型：worked example / 样板遗产
- 价值等级：中高
- 推荐用途：
  - 参考 phase/task-card 驱动 workflow 在真实仓库中的落地样式
  - 参考 phase closeout、summary、final acceptance 这些文档对象怎样组织
  - 参考未来如果要重启“文档驱动协作链”，最小文档集应该长什么样
- 当前仍有价值的原因：
  - 当前仓库保留了 phase/task-card 精神，但工作树已做文档极限收敛
  - 旧 `.kernel` 是现成的历史样板，可供未来做精简版协议复盘
- 使用边界：
  - 只作样板，不恢复整套 phase 文档体系进当前工作树
  - 需要历史细节时查阅，不作为当前权威文档源

### A4. 未来多模态/内容型 Domain Pack 思想库

- 路径：
  - `D:\AI Agent\agentic_workflow_quality_roadmap.md`
  - `D:\AI Agent\README.md` 中 `pf_content` 相关部分
- 类型：未来扩展方向设计稿
- 价值等级：高
- 推荐用途：
  - 参考未来如果当前项目扩到多模态内容生产、资产池、设计验收、质量记忆时，应该有哪些服务和对象
  - 参考 `asset_rag`、`PlaytestService`、`QualityMemoryService`、`VisualCriticService` 这些能力拆分
  - 参考“复用优先、检索优先、设计真相源优先”的内容系统思路
- 当前仍有价值的原因：
  - 这部分并没有被当前软件交付主线完全吸收
  - 它不是当前主仓要立刻做的内容，但很适合作为未来 `multimodal_content` 或其他 domain pack 的设计预研素材
- 使用边界：
  - 只在明确开启相关 Domain Pack 时参考
  - 不把 `pf_content` 代码直接并入当前软件交付主线

### A5. 路由、续跑、回滚的控制面思路

- 路径：
  - `D:\AI Agent\src\agentic_kernel\mcp_server.py`
  - `D:\AI Agent\src\agentic_kernel\facade.py`
- 重点关注的能力：
  - `workflow_find_related_projects`
  - `workflow_select_authoring_target`
  - `workflow_git_prepare`
  - `workflow_phase_rollback`
- 类型：控制面能力原型
- 价值等级：中高
- 推荐用途：
  - 参考“项目续跑判定”“authoring target 选择”“受控 git 安全护栏”“phase 级回滚”这几类能力的产品定义
  - 用来补当前项目未来在 continuation / rollback / authoring delegation 方面的产品思考
- 当前仍有价值的原因：
  - 当前仓库已经有更强的主干 runtime、governance、scheduler、worker-pool 能力，但这几类更偏交互控制面的产品定义并没有完全等价继承
- 使用边界：
  - 参考能力边界和 API 语义
  - 不直接复用旧 facade 实现

### A6. 质量闭环与 reviewer/researcher 分工思路

- 路径：`D:\AI Agent\docs\roadmap_v2_and_beyond.md`
- 类型：中长期能力路线设计稿
- 价值等级：中
- 推荐用途：
  - 参考 reviewer / researcher / commander 的职责分离
  - 参考质量闭环、自动重试、心跳、验证步骤、知识积累等能力如何分阶段引入
  - 参考“先让系统会验证和纠偏，再让系统会扩张”的顺序
- 当前仍有价值的原因：
  - 它对“如何从执行系统走向自治协作系统”有比较清晰的中间层设计
  - 与你现在强调的中长期能力方向有连续性
- 使用边界：
  - 用于路线设计，不用于恢复其阶段计划编号

### A7. debt-first 与 living docs 收敛经验

- 路径：
  - `D:\AI Agent\DEVELOPMENT_MASTER_PLAN.md`
  - `D:\AI Agent\README.md`
- 类型：过程经验遗产
- 价值等级：中
- 推荐用途：
  - 参考“先收结构债、再开新广度”的决策方式
  - 参考如何把主计划、状态摘要、phase 文档、debt 文档分工清楚
  - 参考如何把路线从多条并行叙事收敛成单一主线
- 当前仍有价值的原因：
  - 当前仓库正在经历非常相似的文档收敛和基线重建阶段
  - 这部分经验已经部分被当前仓库继承，但仍可作为路线判断的佐证材料
- 使用边界：
  - 只参考方法，不复活旧的 phase 文档体系

### A8. 行为规格级测试样本

- 路径：
  - `D:\AI Agent\tests\services\test_agent_definition_consistency.py`
  - `D:\AI Agent\tests\services\test_phase_rollback.py`
  - `D:\AI Agent\tests\services\test_phase_task_card_runtime.py`
  - `D:\AI Agent\tests\services\test_project_lineage.py`
- 类型：行为规格参考
- 价值等级：中
- 推荐用途：
  - 参考未来如果要引入续跑、phase rollback、planner/researcher 路由、agent tier 约束，测试应该怎样写成行为规格
  - 作为未来补测试时的思路样本
- 当前仍有价值的原因：
  - 旧仓库很多有价值的东西未必在实现里，而是在“它曾经试图保证什么行为”
- 使用边界：
  - 参考测试意图和覆盖方式
  - 不直接照搬旧测试到当前仓库

## 4. 暂不进入白名单的内容

以下内容不建议作为当前项目的继续参考重点：

1. `D:\AI Agent\src\agentic_kernel\facade.py` 的大块实现
   - 原因：实现形态过于绑定旧仓库和旧 MCP/OpenCode 运行方式

2. `D:\AI Agent\src\agentic_kernel\pf_content\` 全套实现
   - 原因：领域过专，且当前主仓主线不是内容工厂

3. `D:\AI Agent\data\agentic_kernel.db` 与 `data/artifacts/`
   - 原因：属于运行残留，不是设计资产

4. `D:\AI Agent\docs\archive\root-plans-2026-04-13\`
   - 原因：历史价值大于现实价值，除非做专门考古，否则不建议继续投入

## 5. 使用规则

后续如果要引用 `D:\AI Agent` 遗产，建议按下面规则执行：

1. 先问这是“架构参考”还是“代码回收”
   - 默认只能是架构参考

2. 先问它服务于哪条未来路线
   - 多 agent 协作
   - 自然语言控制面
   - 外部能力接入
   - 自我优化/质量记忆
   - 特定 Domain Pack 扩展

3. 没有明确路线归属时，不引用

4. 即使在白名单里，也优先抽取：
   - 术语
   - 协议
   - 状态机
   - API 语义
   - 测试意图
   - 能力拆分

5. 不优先抽取：
   - 旧 prompt 文本
   - 旧大文件实现
   - 旧仓库运行数据
   - 历史 phase 执行细节

## 6. 一句话结论

`D:\AI Agent` 仍然值得保留为“长期产品形态与协议设计参考库”，但不再适合作为当前项目的代码母仓；后续只有白名单中的条目值得继续系统性参考，且默认只能参考其设计思想与能力边界，不能整包回收实现。
