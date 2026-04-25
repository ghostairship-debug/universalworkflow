from __future__ import annotations

from pathlib import Path
import re

from packages.contributions.games.local_game_arcade_templates import _block_puzzle_html, _snake_game_html
from packages.contributions.games.local_game_pdf_templates import _pdf_context_for_goal


def _requested_folder_for_goal(goal: str, *, default_name: str) -> Path:
    output_match = re.search(
        r"(?:输出(?:到(?:目录|文件夹)?|目录|文件夹)?|保存到|生成到|output(?:_dir| directory| folder)?|save to|write to)\s*[：:]\s*([^\n，,。；;]+)",
        goal,
        flags=re.IGNORECASE,
    )
    if output_match:
        output_name = output_match.group(1).strip().strip("`'\"“”‘’")
        if re.match(r"^[A-Za-z]:[\\/]", output_name) or "/" in output_name or "\\" in output_name:
            return Path(output_name)
        return Path("state") / "artifacts" / "generated" / output_name
    folder_match = re.search(r"(?:文件夹|目录)\s*[：:]\s*([^\s，,。；;]+)", goal)
    folder_name = folder_match.group(1).strip("`'\"“”‘’") if folder_match else ""
    if re.match(r"^[A-Za-z]:[\\/]", folder_name):
        return Path(folder_name)
    if ("D盘" in goal or "D 盘" in goal or re.search(r"\bD:\b", goal, flags=re.IGNORECASE)) and folder_name:
        return Path("D:/") / folder_name
    if "D盘" in goal or "D 盘" in goal:
        return Path("D:/") / default_name
    if folder_name:
        return Path("state") / "artifacts" / "generated" / folder_name
    return Path("state") / "artifacts" / "generated" / default_name


def _snake_artifacts(goal: str) -> list[tuple[Path, str]]:
    folder = _requested_folder_for_goal(goal, default_name="snake_game")
    return [
        (folder / "index.html", _snake_game_html()),
        (
            folder / "README.md",
            "# 贪吃蛇小游戏\n\n"
            "这是由 Universal Agentic Workflow 本地聊天工作台生成的小游戏。\n\n"
            "打开 `index.html` 即可运行，使用方向键或 WASD 控制蛇移动。\n",
        ),
    ]


def _block_puzzle_artifacts(
    goal: str,
    *,
    pdf_context: tuple[str, str] | None = None,
) -> list[tuple[Path, str]]:
    folder = _requested_folder_for_goal(goal, default_name="俄罗斯方块消除商业化小游戏")
    pdf_section, pdf_text = pdf_context or _pdf_context_for_goal(goal)
    source_line = "来源：目标中的 PDF 策划文档与聊天需求提炼。"
    if pdf_text:
        source_line = "来源：已自动读取目标中的 PDF 策划文档，并结合聊天需求提炼。"
    readme = (
        "# 方块艺境 - 商业化 1010 Block Puzzle 原型\n\n"
        f"{source_line}\n\n"
        "## 运行方式\n"
        "直接用浏览器打开 `index.html`。\n\n"
        "## 已覆盖功能\n"
        "- 10x10 棋盘和底部 3 个候选方块。\n"
        "- 桌面真实拖拽、移动端触控拖动、防遮挡 ghost、绿色/红色放置预览。\n"
        "- 全部候选块用完后刷新。\n"
        "- 行/列填满消除，包含 Combo 和 Streak 反馈。\n"
        "- 经典模式与前 7 关闯关配置。\n"
        "- 失败弹窗、模拟激励广告复活、结算广告点位。\n"
        "- 刷新方块、横竖排消除、打乱重排三类广告道具。\n"
        "- 皮肤、背景/棋盘装饰、作品/拼图收集外围系统。\n"
        "- 响应式商业化视觉包装。\n"
    )
    trace = (
        "# 信息检索与策划映射\n\n"
        "## 信息来源\n"
        f"{pdf_section}\n\n"
        "## 从 PDF 提取的关键需求\n"
        "- 10x10 网格，底部 3 个候选方块。\n"
        "- 放置后按格数得分，行列填满消除。\n"
        "- 3 个候选方块全部用完后刷新。\n"
        "- 没有剩余候选方块可放时 Game Over。\n"
        "- 空位超过 40% 时避免随机刷出全都放不下的死局。\n"
        "- 经典模式追求高分，闯关模式有前 7 关目标。\n"
        "- Combo、Streak、放置预览、震动反馈、广告复活、插屏广告、皮肤、背景、棋盘图和拼图收集。\n"
        "- 三类道具：刷新方块、横竖排消除、打乱重排。\n\n"
        "## 原型实现取舍\n"
        "- 浏览器原型同时支持点击选择、真实拖拽和触控拖动；触控拖动使用上移 ghost 避免遮挡。\n"
        "- 广告和震动以本地模拟形式呈现，不接真实广告 SDK。\n"
        "- 所有状态保存在前端内存，适合商业化 vertical slice 和玩法验证。\n"
    )
    return [
        (folder / "index.html", _block_puzzle_html()),
        (folder / "README.md", readme),
        (folder / "design_trace.md", trace),
    ]


def local_artifacts_for_goal(goal: str) -> list[tuple[Path, str]]:
    normalized = goal.lower()
    pdf_context = _pdf_context_for_goal(goal)
    searchable = f"{normalized}\n{pdf_context[1].lower()}"
    block_markers = ("1010", "block puzzle", "俄罗斯方块", "方块消除", "消除策划", "商业化小游戏")
    if any(marker in searchable or marker in goal for marker in block_markers):
        return _block_puzzle_artifacts(goal, pdf_context=pdf_context)
    if "贪吃蛇" in goal or "snake" in normalized:
        return _snake_artifacts(goal)
    return []
