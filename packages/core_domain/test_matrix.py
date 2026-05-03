from __future__ import annotations

from infra.test_matrix import (
    COMMERCIAL_FAST_TARGETS,
    COMMERCIAL_INTEGRATION_TARGETS,
    COMMERCIAL_COCOS_BROWSER_TARGETS,
    COMMERCIAL_PROVIDER_CONTRACT_TARGETS,
    COMMERCIAL_FULL_TARGETS,
    COMMERCIAL_FULL_WITH_BROWSER_TARGETS,
    CORE_TARGETS,
    INTEGRATION_TARGETS,
    SLOW_TARGETS,
    UNIT_TARGETS,
    MatrixSelection,
    build_pytest_command,
    prune_pytest_temp_workspace,
    run_matrix,
    select_matrix,
)

__all__ = [
    "CORE_TARGETS",
    "COMMERCIAL_FAST_TARGETS",
    "COMMERCIAL_INTEGRATION_TARGETS",
    "COMMERCIAL_COCOS_BROWSER_TARGETS",
    "COMMERCIAL_PROVIDER_CONTRACT_TARGETS",
    "COMMERCIAL_FULL_TARGETS",
    "COMMERCIAL_FULL_WITH_BROWSER_TARGETS",
    "INTEGRATION_TARGETS",
    "SLOW_TARGETS",
    "UNIT_TARGETS",
    "MatrixSelection",
    "build_pytest_command",
    "prune_pytest_temp_workspace",
    "run_matrix",
    "select_matrix",
]
