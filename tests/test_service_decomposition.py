from __future__ import annotations

import inspect
from pathlib import Path

from packages.core_domain.services import OrchestratorService


def test_orchestrator_service_direct_method_count_is_ratcheted() -> None:
    direct_methods = [
        name for name, value in OrchestratorService.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    ]

    assert len(direct_methods) <= 120


def test_orchestrator_service_file_size_is_ratcheted() -> None:
    line_count = sum(1 for _ in Path("packages/core_domain/services.py").open(encoding="utf-8"))

    assert line_count <= 2600


def test_chat_runtime_facade_and_operator_cli_main_are_ratcheted() -> None:
    chat_facade_lines = sum(1 for _ in Path("packages/runtime_langgraph/chat_runtime/__init__.py").open(encoding="utf-8"))
    cli_main_lines = sum(1 for _ in Path("apps/operator_cli/main.py").open(encoding="utf-8"))

    assert chat_facade_lines <= 120
    assert cli_main_lines <= 500


def test_web_ui_shell_is_ratcheted_and_dom_safe() -> None:
    web_ui_path = Path("apps/orchestrator_api/web_ui.py")
    component_path = Path("apps/orchestrator_api/web_ui_components.py")
    web_ui_lines = sum(1 for _ in web_ui_path.open(encoding="utf-8"))
    combined_source = web_ui_path.read_text(encoding="utf-8") + component_path.read_text(encoding="utf-8")

    assert web_ui_lines <= 700
    assert "innerHTML" not in combined_source
