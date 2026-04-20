from __future__ import annotations

import argparse
import json
from pathlib import Path

from infra.validation.source_package import export_source_package
from packages.core_domain.db import get_migration_status, migrate, reset_db
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService


DEFAULT_REPORT_PATH = Path("state/m21_rebaseline_report.json")
DEFAULT_SOURCE_PACKAGE_PATH = Path("state/source_packages/m21_source_package.zip")
DEFAULT_SOURCE_PACKAGE_MANIFEST_PATH = Path("state/source_packages/m21_source_package_manifest.json")


def _finalize_if_waiting(service: OrchestratorService, run_id: str):
    detail = service.get_status_detail(run_id)
    if detail["run"]["status"] != "awaiting_review":
        return service.get_run(run_id), detail
    reviewed = service.approve_run_review(run_id)
    return reviewed.run, service.get_status_detail(run_id)


def build_m21_rebaseline_report(db_path: Path) -> dict:
    reset_db(db_path)
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    demo_specs = [
        ("feature_delivery", "Build a trusted baseline artifact"),
        ("research_spike_reviewable", "Investigate the next ecosystem integration seam"),
        ("guarded_delivery", "Ship a guarded delivery slice"),
        ("project_delivery", "Coordinate a multi-role project delivery slice"),
    ]
    demo_matrix: dict[str, dict] = {}
    for preset_id, goal in demo_specs:
        run = service.create_run(goal, preset_id)
        prepared = service.compile_run(run.run_id)
        service.resume_run(run.run_id)
        final_run, detail = _finalize_if_waiting(service, run.run_id)
        demo_matrix[preset_id] = {
            "run_id": run.run_id,
            "goal": goal,
            "status": final_run.status,
            "runtime_task_id": prepared.task_packet.runtime_task_id,
            "execution_lane": detail["execution_lane"],
            "capability_resolution": detail["capability_resolution"],
            "effective_review_state": detail["effective_review_state"],
            "orchestration_enabled": detail["orchestration"] is not None,
            "orchestration_plan_graph": detail["orchestration_plan_graph"],
            "result_envelope": detail["result_envelope"],
        }

    source_package = export_source_package(
        DEFAULT_SOURCE_PACKAGE_PATH,
        manifest_path=DEFAULT_SOURCE_PACKAGE_MANIFEST_PATH,
        dry_run=True,
    )
    migration_status = get_migration_status(db_path)
    return {
        "report_version": "m21_phase_0_rebaseline_v1",
        "status": "completed",
        "db_path": db_path.as_posix(),
        "migration_status": migration_status,
        "baseline_contract": {
            "working_tree_truth": "developer workspace may be noisy and is not the release baseline",
            "source_package_truth": "export manifest is the reproducible baseline for external review",
        },
        "evidence_matrix": {
            "validation_commands": [
                {
                    "name": "pytest",
                    "command": "python -m pytest -q",
                    "evidence_path": None,
                },
                {
                    "name": "offline_validation",
                    "command": "python -m infra.scripts.offline_validation --skip-offline-probe",
                    "evidence_path": "state/offline_validation_report.json",
                },
                {
                    "name": "doc_links",
                    "command": "python -m infra.scripts.check_doc_links",
                    "evidence_path": None,
                },
                {
                    "name": "source_package_dry_run",
                    "command": "python -m infra.scripts.export_source_package --dry-run",
                    "evidence_path": DEFAULT_SOURCE_PACKAGE_MANIFEST_PATH.as_posix(),
                },
                {
                    "name": "cluster_cutover",
                    "command": "python -m infra.scripts.run_cluster_cutover_demo --db-path state/cluster_cutover_demo.db --report-path state/cluster_cutover_demo_report.json",
                    "evidence_path": "state/cluster_cutover_demo_report.json",
                },
            ],
            "canonical_demo_targets": list(demo_matrix),
        },
        "canonical_demo_matrix": demo_matrix,
        "source_package": source_package,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the M21 rebaseline and canonical demo report.")
    parser.add_argument("--db-path", default="state/m21_rebaseline.db")
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH.as_posix())
    args = parser.parse_args()
    report = build_m21_rebaseline_report(Path(args.db_path))
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
