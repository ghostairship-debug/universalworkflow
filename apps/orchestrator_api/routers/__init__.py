from apps.orchestrator_api.routers.catalog import build_catalog_router
from apps.orchestrator_api.routers.governance import build_governance_reports, build_governance_router
from apps.orchestrator_api.routers.interaction import build_interaction_router
from apps.orchestrator_api.routers.runs import build_runs_router
from apps.orchestrator_api.routers.scheduler import build_scheduler_router
from apps.orchestrator_api.routers.ui import build_ui_router
from apps.orchestrator_api.routers.workers import build_workers_router

__all__ = [
    "build_catalog_router",
    "build_governance_reports",
    "build_governance_router",
    "build_interaction_router",
    "build_runs_router",
    "build_scheduler_router",
    "build_ui_router",
    "build_workers_router",
]
