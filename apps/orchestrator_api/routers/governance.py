from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter

from packages.core_domain.governance import (
    build_domain_pack_platform_report,
    build_governance_alert_report,
    build_governance_metrics_report,
    build_release_readiness_report,
    build_review_policy_report,
    build_tech_debt_report,
)


def build_governance_reports(resolved_db_path: Path) -> dict[str, dict[str, Any]]:
    return {
        "tech_debt": build_tech_debt_report(),
        "review_policy": build_review_policy_report(db_path=resolved_db_path),
        "metrics": build_governance_metrics_report(db_path=resolved_db_path),
        "alerts": build_governance_alert_report(db_path=resolved_db_path),
        "release_readiness": build_release_readiness_report(db_path=resolved_db_path),
        "domain_packs": build_domain_pack_platform_report(),
    }


def build_governance_router(resolved_db_path: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/governance/tech-debt")
    def get_governance_tech_debt() -> dict:
        return build_tech_debt_report()

    @router.get("/governance/review-policy")
    def get_governance_review_policy() -> dict:
        return build_review_policy_report(db_path=resolved_db_path)

    @router.get("/governance/metrics")
    def get_governance_metrics(
        validation_report_path: str | None = None,
        decision_table_path: str | None = None,
        registry_path: str | None = None,
    ) -> dict:
        return build_governance_metrics_report(
            db_path=resolved_db_path,
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )

    @router.get("/governance/alerts")
    def get_governance_alerts(
        validation_report_path: str | None = None,
        decision_table_path: str | None = None,
        registry_path: str | None = None,
    ) -> dict:
        return build_governance_alert_report(
            db_path=resolved_db_path,
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )

    @router.get("/governance/release-readiness")
    def get_governance_release_readiness(
        validation_report_path: str | None = None,
        decision_table_path: str | None = None,
        registry_path: str | None = None,
    ) -> dict:
        return build_release_readiness_report(
            db_path=resolved_db_path,
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )

    @router.get("/governance/domain-packs")
    def get_governance_domain_packs() -> dict:
        return build_domain_pack_platform_report()

    return router
