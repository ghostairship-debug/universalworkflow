from __future__ import annotations

import argparse
import json
import os
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


def sanitize_llm_environment() -> dict[str, str]:
    removed: dict[str, str] = {}
    for key in list(os.environ):
        upper_key = key.upper()
        if upper_key in LLM_ENV_KEYS or "LLM" in upper_key:
            removed[key] = os.environ.pop(key)
    return removed


def restore_environment(values: dict[str, str]) -> None:
    os.environ.update(values)


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
        auto_timeline = [event.event_type for event in service.get_timeline(auto_run.run_id)]
        auto_evidence = service.get_task_evidence(auto_prepared.task_packet.runtime_task_id)
        if auto_timeline != AUTO_TIMELINE:
            raise RuntimeError(f"unexpected auto timeline: {auto_timeline}")

        human_run = service.create_run("M1 smoke human path", "research_spike")
        human_prepared = service.compile_run(human_run.run_id)
        human_resumed = service.resume_run(human_run.run_id)
        if human_resumed.run.status != "awaiting_review":
            raise RuntimeError(f"human path did not enter awaiting_review: {human_resumed.run.status}")
        human_reviewed = service.approve_run_review(human_run.run_id)
        human_timeline = [event.event_type for event in service.get_timeline(human_run.run_id)]
        if human_timeline != HUMAN_TIMELINE:
            raise RuntimeError(f"unexpected human timeline: {human_timeline}")

        return {
            "db_path": db_path.as_posix(),
            "removed_env_keys": sorted(removed_env),
            "status": "completed",
            "auto_run": {
                "run_id": auto_run.run_id,
                "runtime_task_id": auto_prepared.task_packet.runtime_task_id,
                "evidence_id": auto_evidence.evidence_id,
                "review_decision": auto_executed.review_verdict.decision if auto_executed.review_verdict else None,
                "status": auto_executed.run.status,
                "timeline_events": auto_timeline,
            },
            "human_run": {
                "run_id": human_run.run_id,
                "runtime_task_id": human_prepared.task_packet.runtime_task_id,
                "evidence_id": human_reviewed.evidence.evidence_id,
                "review_decision": human_reviewed.review_verdict.decision,
                "status": human_reviewed.run.status,
                "timeline_events": human_timeline,
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
    if args.command == "logs-tail":
        logs_tail(LOG_PATH)
        return
    if args.command == "dev":
        uvicorn.run(create_app(db_path), host=args.host, port=args.port, reload=False)
        return


if __name__ == "__main__":
    main()
