from __future__ import annotations

import ast
from pathlib import Path

from packages.runtime_langgraph.gateway import NullRuntimeGateway


def test_contracts_and_core_domain_do_not_import_langgraph() -> None:
    roots = [Path("packages/contracts"), Path("packages/core_domain")]
    for root in roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert all(alias.name != "langgraph" for alias in node.names)
                if isinstance(node, ast.ImportFrom) and node.module is not None:
                    assert node.module != "langgraph"


def test_runtime_gateway_state_is_lightweight() -> None:
    gateway = NullRuntimeGateway()
    state_ref = gateway.start("run_123", "task_123")
    assert state_ref.run_id == "run_123"
    assert state_ref.runtime_task_id == "task_123"
    assert isinstance(state_ref.graph_step, str)
