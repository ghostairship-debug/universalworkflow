from __future__ import annotations

from typing import Any


__all__ = [
    "execute_contribution_capability",
    "execute_contribution_validation",
    "preview_contribution_pipeline",
    "preview_workflow_pipeline",
    "run_workflow_pipeline",
]


def __getattr__(name: str) -> Any:
    if name in {
        "execute_contribution_capability",
        "execute_contribution_validation",
        "preview_contribution_pipeline",
    }:
        from packages.contributions.pipelines import registry

        return getattr(registry, name)
    if name in {"preview_workflow_pipeline", "run_workflow_pipeline"}:
        from packages.contributions.pipelines import workflow_runtime

        return getattr(workflow_runtime, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
