from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow end-to-end CLI/API/Web/release tests.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: slow end-to-end tests skipped by default")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-slow"):
        return
    skip_slow = pytest.mark.skip(reason="slow test skipped by default; use --run-slow for full validation")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
