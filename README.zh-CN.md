# Universal Agentic Workflow OS 中文说明

这份文档是当前仓库的中文总览入口，面向中文读者说明：

- 现在项目已经做到什么程度
- 当前 Web UI / TUI 分别是什么形态
- 自然语言接入能力做到哪一层
- 现在应该如何启动和使用

如果中文说明与英文最小真相集冲突，请以这些文件为准：

1. [README.md](README.md)
2. [docs/current_development_workflow.md](docs/current_development_workflow.md)
3. [docs/reviews/m30-operator-control-freeze-review.md](docs/reviews/m30-operator-control-freeze-review.md)
4. [docs/reviews/m20-freeze-review.md](docs/reviews/m20-freeze-review.md)
5. [docs/tech-debt-registry.md](docs/tech-debt-registry.md)

## 1. 当前仓库位置

截至当前工作树，仓库已经完成：

- `M8` 到 `M30`
- `v1 core complete` 主线
- runtime / governance / orchestration / remote worker / multi-control-plane 共识闭环
- capability descriptors / health
- sessionful external-agent lane
- orchestration plan graph
- natural-language `plan-graph / policy-preview / goal-packet / launch`
- operator packet / goal packet
- dashboard 与 operator view 的读模型收口

当前没有再打开新的 post-`M30` phase。下一阶段还没有正式启动。

## 2. 现在的产品形态

当前产品不是“一个零散 agent 脚本集合”，而是一个本地优先的 workflow control plane。

已经具备的核心能力包括：

- 本地优先持久化，SQLite 仍然是主真相源
- CLI / API / Web UI / TUI 多入口
- `shell / opencode / noop / agent` 多执行通道
- review policy、audit report、replay packet、governance metrics 等治理面
- `project_delivery` 多角色 orchestration 基线
- 受控 repo mutation、write-set、bounded test/fix loop
- remote worker 与多控制面 lease ownership / takeover 保护

## 3. Web UI 和 TUI 的当前定位

### Web UI

当前 Web UI 是 **operator console**，已经可以用于：

- 浏览 dashboard / runs / reviews / governance / config
- 查看 run focus detail、inspection、operator view
- 执行 `resume / approve / reject / reconcile / cancel / batch-resume`

它已经是可用的运维与控制台界面，但它 **还不是聊天式自然语言工作台**。

现在缺少的仍然包括：

- 类似 chat 的输入框和会话线程
- 流式输出
- 运行中补充上下文和插话
- 一边对话一边重规划一边执行的 workbench 体验

### TUI

当前 TUI 是 **read-mostly terminal dashboard**，主要用于：

- recent runs
- focus detail
- runtime gateway 状态
- timeline tail

它是一个轻量观察面，不是完整交互 shell，也不是自然语言聊天终端。

## 4. 自然语言能力现在做到哪一层

这个能力已经开始落地，但主要落在 **后端入口**，还没有完整前端化。

现在已经有的自然语言相关 surface：

- `run suggest-presets`
- `run plan-graph`
- `run policy-preview`
- `run goal-packet`
- `run launch`
- `run operator-packet`

也就是说：

- 后端已经可以接收自然语言 goal
- 可以产出 preset 建议、plan graph、policy preview、goal packet
- 可以进一步 create / compile / optional execute

但目前这些能力主要暴露在：

- CLI
- API

而不是 Web UI / TUI 的聊天式交互面。

## 5. 现在还没开始正式部署的长期能力

虽然长期能力的底座已经开始部署，但下面这些还没有全面展开：

- preview-only policy 升级为真正的 enforced gating
- 自动化与长时间后台控制循环
- Web 聊天式 / workbench 式自然语言交互面
- 更广的 hosted provider / multimodal 主线
- 自我升级与更深层自治

这些内容目前仍然属于 `M31+` 之后才应正式打开的范围。

## 6. 快速启动

安装：

```bash
pip install -e .
```

如需开发依赖：

```bash
pip install -e ".[dev]"
```

初始化数据库与 smoke：

```bash
python -m infra.scripts.manage --db-path state/workflow.db reset-db
python -m infra.scripts.manage --db-path state/workflow.db smoke
```

启动本地 API + Web UI：

```bash
python -m infra.scripts.manage --db-path state/workflow.db dev --host 127.0.0.1 --port 8000
```

打开：

- `http://127.0.0.1:8000/ui`
- `http://127.0.0.1:8000/ui/runs`
- `http://127.0.0.1:8000/ui/reviews`
- `http://127.0.0.1:8000/ui/governance`
- `http://127.0.0.1:8000/ui/config`

启动 TUI：

```bash
python -m apps.operator_cli.main --db-path state/workflow.db tui
```

## 7. 当前推荐使用方式

如果你现在想直接使用 workflow，推荐分两种：

### 1. Operator 模式

适合：

- 查看 run
- 做 approve / reject / reconcile
- 看治理和运行态

入口：

- Web UI
- TUI

### 2. Natural-language launch 模式

适合：

- 给一个自然语言目标
- 先看系统打算怎么做
- 再决定是否执行

CLI 示例：

```bash
workflowctl --db-path state/workflow.db run suggest-presets --goal "Research runtime strategy"
workflowctl --db-path state/workflow.db run plan-graph --goal "Ship a guarded delivery slice"
workflowctl --db-path state/workflow.db run policy-preview --goal "Ship a guarded delivery slice"
workflowctl --db-path state/workflow.db run goal-packet --goal "Ship a guarded delivery slice"
workflowctl --db-path state/workflow.db run launch --goal "Ship a guarded delivery slice" --execute
workflowctl --db-path state/workflow.db run operator-packet <run_id>
```

## 8. 一句话总结

当前仓库已经不是原型，而是完成到 `M30` 的 operator-control baseline：

- Web UI 已经是可用的 operator console
- TUI 已经是可用的观察面
- 自然语言 goal 的后端入口已经有了
- 但真正的聊天式人机交互 workbench 还没有做出来
