from __future__ import annotations

from pathlib import Path

from packages.contributions.games.local_game_artifacts import local_artifacts_for_goal as _local_artifacts_for_goal


def local_artifacts_for_goal(goal: str) -> list[tuple[Path, str]]:
    """Compatibility shim for older imports; game templates live outside core_domain."""
    return _local_artifacts_for_goal(goal)
