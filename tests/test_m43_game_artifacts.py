from __future__ import annotations

from pathlib import Path

from packages.contributions.games.local_game_artifacts import local_artifacts_for_goal


def _artifact_map(goal: str) -> dict[str, str]:
    return {path.as_posix(): content for path, content in local_artifacts_for_goal(goal)}


def test_m43_block_puzzle_uses_pdf_and_supports_real_drag() -> None:
    goal = (
        "基于俄罗斯方块消除策划文档做商业化小游戏，"
        "输出到目录: examples/block_puzzle_shop"
    )

    artifacts = _artifact_map(goal)
    html = artifacts["examples/block_puzzle_shop/index.html"]
    trace = artifacts["examples/block_puzzle_shop/design_trace.md"]
    readme = artifacts["examples/block_puzzle_shop/README.md"]

    assert "data-testid=\"game-board\"" in html
    assert "data-testid=\"drag-ghost\"" in html
    assert "shell.draggable = true" in html
    assert "dragstart" in html
    assert "pointermove" in html
    assert "paintPreview" in html
    assert "preview-ok" in html
    assert "preview-bad" in html
    assert "真实拖拽" in trace
    assert "桌面真实拖拽" in readme


def test_m43_block_puzzle_commercial_systems_are_present() -> None:
    html = _artifact_map("俄罗斯方块消除商业化小游戏")[
        "state/artifacts/generated/俄罗斯方块消除商业化小游戏/index.html"
    ]

    assert "data-testid=\"booster-refresh\"" in html
    assert "data-testid=\"booster-line\"" in html
    assert "data-testid=\"booster-shuffle\"" in html
    assert "data-testid=\"revive-button\"" in html
    assert "data-testid=\"skin-panel\"" in html
    assert "data-testid=\"works-panel\"" in html
    assert "Combo/Streak" in html
    assert "结算插屏广告" in html


def test_m43_relative_output_directory_is_respected() -> None:
    artifacts = local_artifacts_for_goal(
        "生成商业化方块消除小游戏，输出到目录: examples/block_puzzle_shop"
    )

    paths = {path for path, _content in artifacts}
    assert Path("examples/block_puzzle_shop/index.html") in paths
    assert Path("examples/block_puzzle_shop/README.md") in paths
    assert Path("examples/block_puzzle_shop/design_trace.md") in paths


def test_m43_machine_readable_output_dir_is_supported() -> None:
    artifacts = local_artifacts_for_goal(
        "Build a commercial 1010 block puzzle; output_dir: examples/block_puzzle_shop"
    )

    paths = {path for path, _content in artifacts}
    assert Path("examples/block_puzzle_shop/index.html") in paths
