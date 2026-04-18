from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

import uvicorn

from apps.orchestrator_api.main import create_app
from packages.core_domain.db import DEFAULT_DB_PATH, migrate, reset_db
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService


LOG_PATH = Path("state/workflow.log")
LLM_ENV_KEYS = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DASHSCOPE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
    "DEEPSEEK_API_KEY",
}
AUTO_TIMELINE = [
    "run_created",
    "preset_selected",
    "phase_created",
    "phase_created",
    "handoff_created",
    "runtime_task_created",
    "run_compiled",
    "runtime_resumed",
    "runtime_task_started",
    "runtime_task_completed",
    "evidence_submitted",
    "review_submitted",
    "run_completed",
]
HUMAN_TIMELINE = [
    "run_created",
    "preset_selected",
    "phase_created",
    "phase_created",
    "handoff_created",
    "runtime_task_created",
    "run_compiled",
    "runtime_resumed",
    "runtime_task_started",
    "runtime_task_completed",
    "evidence_submitted",
    "review_requested",
    "review_submitted",
    "run_completed",
]
CLAIM_EVENTS = {"claim_acquired", "claim_released"}
LEASE_EVENTS = {"worker_lease_acquired", "worker_lease_released"}
ATTEMPT_EVENTS = {"runtime_attempt_created", "runtime_attempt_superseded", "runtime_attempt_closed"}


def timeline_contains_required_events(actual: list[str], required: list[str]) -> bool:
    cursor = 0
    for event in actual:
        if cursor < len(required) and event == required[cursor]:
            cursor += 1
    return cursor == len(required)


def sanitize_llm_environment() -> dict[str, str]:
    removed: dict[str, str] = {}
    for key in list(os.environ):
        upper_key = key.upper()
        if upper_key in LLM_ENV_KEYS or "LLM" in upper_key:
            removed[key] = os.environ.pop(key)
    return removed


def restore_environment(values: dict[str, str]) -> None:
    os.environ.update(values)


def mutate_task_packet_command(db_path: Path, runtime_task_id: str, command: list[str]) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE task_packets SET command_json = ? WHERE runtime_task_id = ?",
            (json.dumps(command, ensure_ascii=False), runtime_task_id),
        )
        connection.commit()


def run_smoke(db_path: Path) -> dict:
    removed_env = sanitize_llm_environment()
    try:
        reset_db(db_path)
        migrate(db_path)
        PresetRepository(db_path).seed_defaults()
        service = OrchestratorService(db_path)

        auto_run = service.create_run("M1 smoke auto path", "feature_delivery")
        auto_prepared = service.compile_run(auto_run.run_id)
        auto_executed = service.resume_run(auto_run.run_id)
        auto_detail = service.get_status_detail(auto_run.run_id)
        auto_timeline = [event.event_type for event in service.get_timeline(auto_run.run_id)]
        auto_evidence = service.get_task_evidence(auto_prepared.task_packet.runtime_task_id)
        auto_claims = service.list_claims(auto_run.run_id)
        auto_attempts = service.list_runtime_attempts(auto_run.run_id)
        auto_worker_leases = service.list_worker_leases(auto_run.run_id)
        auto_snapshots = service.list_snapshots(auto_run.run_id)
        auto_budget = auto_detail["budget_projection"]
        if not timeline_contains_required_events(auto_timeline, AUTO_TIMELINE):
            raise RuntimeError(f"unexpected auto timeline: {auto_timeline}")
        if {claim.status for claim in auto_claims} != {"released"}:
            raise RuntimeError(f"unexpected auto claim history: {[claim.model_dump(mode='json') for claim in auto_claims]}")
        if {lease.status for lease in auto_worker_leases} != {"released"}:
            raise RuntimeError(
                f"unexpected auto worker-lease history: {[lease.model_dump(mode='json') for lease in auto_worker_leases]}"
            )
        if not CLAIM_EVENTS.issubset(set(auto_timeline)):
            raise RuntimeError(f"missing auto claim events: {auto_timeline}")
        if not LEASE_EVENTS.issubset(set(auto_timeline)):
            raise RuntimeError(f"missing auto worker-lease events: {auto_timeline}")
        if not ATTEMPT_EVENTS.issubset(set(auto_timeline)):
            raise RuntimeError(f"missing auto runtime-attempt events: {auto_timeline}")
        if [snapshot.stage for snapshot in auto_snapshots] != ["compiled", "completed"]:
            raise RuntimeError(f"unexpected auto snapshot history: {[snapshot.model_dump(mode='json') for snapshot in auto_snapshots]}")
        if [attempt.status for attempt in auto_attempts] != ["superseded", "completed"]:
            raise RuntimeError(f"unexpected auto attempt history: {[attempt.model_dump(mode='json') for attempt in auto_attempts]}")
        if auto_detail["domain_pack"] is None or auto_detail["domain_pack"]["domain_pack_id"] != "software_delivery_pack":
            raise RuntimeError(f"unexpected auto domain pack projection: {auto_detail['domain_pack']}")
        if auto_detail["capability_resolution"] is None or auto_detail["capability_resolution"]["adapter_name"] != "shell":
            raise RuntimeError(f"unexpected auto capability resolution: {auto_detail['capability_resolution']}")

        human_run = service.create_run("M1 smoke human path", "research_spike")
        human_prepared = service.compile_run(human_run.run_id)
        human_resumed = service.resume_run(human_run.run_id)
        if human_resumed.run.status != "awaiting_review":
            raise RuntimeError(f"human path did not enter awaiting_review: {human_resumed.run.status}")
        human_reviewed = service.approve_run_review(human_run.run_id)
        human_timeline = [event.event_type for event in service.get_timeline(human_run.run_id)]
        human_claims = service.list_claims(human_run.run_id)
        human_attempts = service.list_runtime_attempts(human_run.run_id)
        human_worker_leases = service.list_worker_leases(human_run.run_id)
        human_snapshots = service.list_snapshots(human_run.run_id)
        human_budget = service.get_status_detail(human_run.run_id)["budget_projection"]
        if not timeline_contains_required_events(human_timeline, HUMAN_TIMELINE):
            raise RuntimeError(f"unexpected human timeline: {human_timeline}")
        if {claim.status for claim in human_claims} != {"released"}:
            raise RuntimeError(f"unexpected human claim history: {[claim.model_dump(mode='json') for claim in human_claims]}")
        if {lease.status for lease in human_worker_leases} != {"released"}:
            raise RuntimeError(
                f"unexpected human worker-lease history: {[lease.model_dump(mode='json') for lease in human_worker_leases]}"
            )
        if not CLAIM_EVENTS.issubset(set(human_timeline)):
            raise RuntimeError(f"missing human claim events: {human_timeline}")
        if not LEASE_EVENTS.issubset(set(human_timeline)):
            raise RuntimeError(f"missing human worker-lease events: {human_timeline}")
        if not ATTEMPT_EVENTS.issubset(set(human_timeline)):
            raise RuntimeError(f"missing human runtime-attempt events: {human_timeline}")
        if [snapshot.stage for snapshot in human_snapshots] != ["compiled", "awaiting_review", "completed"]:
            raise RuntimeError(
                f"unexpected human snapshot history: {[snapshot.model_dump(mode='json') for snapshot in human_snapshots]}"
            )
        if [attempt.status for attempt in human_attempts] != ["superseded", "completed"]:
            raise RuntimeError(f"unexpected human attempt history: {[attempt.model_dump(mode='json') for attempt in human_attempts]}")

        return {
            "db_path": db_path.as_posix(),
            "removed_env_keys": sorted(removed_env),
            "status": "completed",
            "capability_routes": service.list_capability_routes(),
            "domain_packs": [domain_pack.model_dump(mode="json") for domain_pack in service.list_domain_packs()],
            "auto_run": {
                "run_id": auto_run.run_id,
                "runtime_task_id": auto_prepared.task_packet.runtime_task_id,
                "evidence_id": auto_evidence.evidence_id,
                "review_decision": auto_executed.review_verdict.decision if auto_executed.review_verdict else None,
                "status": auto_executed.run.status,
                "domain_pack": auto_detail["domain_pack"],
                "capability_resolution": auto_detail["capability_resolution"],
                "timeline_events": auto_timeline,
                "claims": [claim.model_dump(mode="json") for claim in auto_claims],
                "attempts": [attempt.model_dump(mode="json") for attempt in auto_attempts],
                "worker_leases": [lease.model_dump(mode="json") for lease in auto_worker_leases],
                "snapshots": [snapshot.model_dump(mode="json") for snapshot in auto_snapshots],
                "budget_projection": auto_budget,
            },
            "human_run": {
                "run_id": human_run.run_id,
                "runtime_task_id": human_prepared.task_packet.runtime_task_id,
                "evidence_id": human_reviewed.evidence.evidence_id,
                "review_decision": human_reviewed.review_verdict.decision,
                "status": human_reviewed.run.status,
                "timeline_events": human_timeline,
                "claims": [claim.model_dump(mode="json") for claim in human_claims],
                "attempts": [attempt.model_dump(mode="json") for attempt in human_attempts],
                "worker_leases": [lease.model_dump(mode="json") for lease in human_worker_leases],
                "snapshots": [snapshot.model_dump(mode="json") for snapshot in human_snapshots],
                "budget_projection": human_budget,
            },
        }
    finally:
        restore_environment(removed_env)


def run_demo(db_path: Path) -> dict:
    removed_env = sanitize_llm_environment()
    try:
        reset_db(db_path)
        migrate(db_path)
        PresetRepository(db_path).seed_defaults()
        service = OrchestratorService(db_path)

        auto_run = service.create_run("M4 demo auto path", "feature_delivery")
        auto_prepared = service.compile_run(auto_run.run_id)
        auto_executed = service.resume_run(auto_run.run_id)
        auto_detail = service.get_status_detail(auto_run.run_id)
        auto_evidence = service.get_task_evidence(auto_prepared.task_packet.runtime_task_id)

        human_run = service.create_run("M4 demo human path", "research_spike")
        human_prepared = service.compile_run(human_run.run_id)
        human_resumed = service.resume_run(human_run.run_id)
        human_waiting_detail = service.get_status_detail(human_run.run_id)
        human_reviewed = service.approve_run_review(human_run.run_id)

        recommended_run = service.create_run("M4 demo recommended path", "advisory_delivery")
        recommended_prepared = service.compile_run(recommended_run.run_id)
        mutate_task_packet_command(
            db_path,
            recommended_prepared.task_packet.runtime_task_id,
            ["python", "-c", "import sys; sys.exit(2)"],
        )
        recommended_resumed = service.resume_run(recommended_run.run_id)
        recommended_waiting_detail = service.get_status_detail(recommended_run.run_id)
        recommended_reviewed = service.approve_run_review(recommended_run.run_id)

        mandatory_run = service.create_run("M4 demo mandatory path", "guarded_delivery")
        mandatory_prepared = service.compile_run(mandatory_run.run_id)
        mandatory_resumed = service.resume_run(mandatory_run.run_id)
        mandatory_waiting_detail = service.get_status_detail(mandatory_run.run_id)
        mandatory_reviewed = service.approve_run_review(mandatory_run.run_id)

        noop_run = service.create_run("M4 demo noop path", "research_spike")
        noop_prepared = service.compile_run(noop_run.run_id, task_kind="noop")
        noop_resumed = service.resume_run(noop_run.run_id)
        noop_waiting_detail = service.get_status_detail(noop_run.run_id)
        noop_reviewed = service.approve_run_review(noop_run.run_id)
        noop_evidence = service.get_task_evidence(noop_prepared.task_packet.runtime_task_id)

        return {
            "db_path": db_path.as_posix(),
            "removed_env_keys": sorted(removed_env),
            "status": "completed",
            "capability_routes": service.list_capability_routes(),
            "domain_packs": [domain_pack.model_dump(mode="json") for domain_pack in service.list_domain_packs()],
            "paths": {
                "auto": {
                    "run_id": auto_run.run_id,
                    "status": auto_executed.run.status,
                    "review_decision": auto_executed.review_verdict.decision if auto_executed.review_verdict else None,
                    "domain_pack": auto_detail["domain_pack"],
                    "capability_resolution": auto_detail["capability_resolution"],
                    "artifact_path": auto_evidence.artifact_refs[0].path if auto_evidence.artifact_refs else None,
                },
                "human_review": {
                    "run_id": human_run.run_id,
                    "intermediate_status": human_resumed.run.status,
                    "intermediate_review_state": human_waiting_detail["effective_review_state"],
                    "status": human_reviewed.run.status,
                    "domain_pack": human_waiting_detail["domain_pack"],
                },
                "recommended": {
                    "run_id": recommended_run.run_id,
                    "intermediate_status": recommended_resumed.run.status,
                    "latest_auto_decision": recommended_resumed.review_verdict.decision if recommended_resumed.review_verdict else None,
                    "intermediate_review_state": recommended_waiting_detail["effective_review_state"],
                    "status": recommended_reviewed.run.status,
                    "domain_pack": recommended_waiting_detail["domain_pack"],
                },
                "mandatory": {
                    "run_id": mandatory_run.run_id,
                    "intermediate_status": mandatory_resumed.run.status,
                    "latest_auto_decision": mandatory_resumed.review_verdict.decision if mandatory_resumed.review_verdict else None,
                    "intermediate_review_state": mandatory_waiting_detail["effective_review_state"],
                    "status": mandatory_reviewed.run.status,
                    "domain_pack": mandatory_waiting_detail["domain_pack"],
                },
                "noop": {
                    "run_id": noop_run.run_id,
                    "task_kind": noop_prepared.task_packet.task_kind,
                    "intermediate_status": noop_resumed.run.status,
                    "status": noop_reviewed.run.status,
                    "adapter_name": noop_evidence.raw_execution.get("adapter_name"),
                    "domain_pack": noop_waiting_detail["domain_pack"],
                },
            },
        }
    finally:
        restore_environment(removed_env)


def logs_tail(log_path: Path) -> None:
    if not log_path.exists():
        print(f"no log file found at {log_path.as_posix()}")
        return
    print(log_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Development commands for the M1 local-first runtime.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate")
    subparsers.add_parser("reset-db")
    subparsers.add_parser("seed-presets")
    subparsers.add_parser("smoke")
    subparsers.add_parser("demo")
    subparsers.add_parser("logs-tail")
    dev_parser = subparsers.add_parser("dev")
    dev_parser.add_argument("--host", default="127.0.0.1")
    dev_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    db_path = Path(args.db_path)

    if args.command == "migrate":
        applied = migrate(db_path)
        print(json.dumps({"db_path": db_path.as_posix(), "applied": applied}, ensure_ascii=False))
        return
    if args.command == "reset-db":
        reset_db(db_path)
        migrate(db_path)
        seeded = [preset.preset_id for preset in PresetRepository(db_path).seed_defaults()]
        print(json.dumps({"db_path": db_path.as_posix(), "seeded": seeded}, ensure_ascii=False))
        return
    if args.command == "seed-presets":
        seeded = [preset.preset_id for preset in PresetRepository(db_path).seed_defaults()]
        print(json.dumps({"db_path": db_path.as_posix(), "seeded": seeded}, ensure_ascii=False))
        return
    if args.command == "smoke":
        print(json.dumps(run_smoke(db_path), ensure_ascii=False))
        return
    if args.command == "demo":
        print(json.dumps(run_demo(db_path), ensure_ascii=False))
        return
    if args.command == "logs-tail":
        logs_tail(LOG_PATH)
        return
    if args.command == "dev":
        uvicorn.run(create_app(db_path), host=args.host, port=args.port, reload=False)
        return


if __name__ == "__main__":
    main()
