from __future__ import annotations

import argparse
import json
import os
import sqlite3
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = PROJECT_ROOT / "state" / "offline_validation_report.json"
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


@dataclass(slots=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def timeline_contains_required_events(actual: list[str], required: list[str]) -> bool:
    cursor = 0
    for event in actual:
        if cursor < len(required) and event == required[cursor]:
            cursor += 1
    return cursor == len(required)


def sanitized_env() -> tuple[dict[str, str], list[str]]:
    env = dict(os.environ)
    removed: list[str] = []
    for key in list(env):
        upper_key = key.upper()
        if upper_key in LLM_ENV_KEYS or "LLM" in upper_key:
            removed.append(key)
            env.pop(key, None)
    return env, sorted(removed)


def run_command(command: list[str], env: dict[str, str]) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def run_json_command(command: list[str], env: dict[str, str]) -> tuple[dict[str, Any] | list[Any], CommandResult]:
    result = run_command(command, env)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    try:
        return json.loads(result.stdout), result
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"command did not return valid JSON: {' '.join(command)}\nstdout:\n{result.stdout}") from exc


def corrupt_runtime_state_for_run(
    db_path: Path,
    run_id: str,
    *,
    graph_step: str,
    is_terminal: bool,
    extra_payload: dict[str, Any] | None = None,
) -> str:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT state_ref_id, runtime_task_id, state_payload_json
            FROM runtime_state_refs
            WHERE run_id = ?
            ORDER BY updated_at DESC, created_at DESC, state_ref_id DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"no runtime_state_ref found for run {run_id}")
        payload = json.loads(row["state_payload_json"])
        payload.update(extra_payload or {})
        connection.execute(
            """
            UPDATE runtime_state_refs
            SET graph_step = ?, state_payload_json = ?, is_terminal = ?, updated_at = CURRENT_TIMESTAMP
            WHERE state_ref_id = ?
            """,
            (
                graph_step,
                json.dumps(payload, ensure_ascii=False),
                1 if is_terminal else 0,
                row["state_ref_id"],
            ),
        )
        connection.commit()
        return str(row["runtime_task_id"])


def mutate_task_packet_command(
    db_path: Path,
    runtime_task_id: str,
    command: list[str],
) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE task_packets SET command_json = ? WHERE runtime_task_id = ?",
            (json.dumps(command, ensure_ascii=False), runtime_task_id),
        )
        connection.commit()


def tcp_probe(host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return {"target": f"{host}:{port}", "reachable": True, "elapsed_ms": elapsed_ms, "error": None}
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return {"target": f"{host}:{port}", "reachable": False, "elapsed_ms": elapsed_ms, "error": str(exc)}


def http_get_json(url: str, timeout: float = 3.0) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def http_post_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 3.0) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def wait_for_api(base_url: str, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            http_get_json(f"{base_url}/presets")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(0.5)
    raise RuntimeError(f"API server did not become ready: {last_error}")


def validate_cli_flow(env: dict[str, str], db_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"passed": False}
    release_validation_report_path = PROJECT_ROOT / "state" / "offline_validate_release_readiness.json"
    release_validation_report_path.write_text(
        json.dumps(
            {
                "overall_passed": True,
                "checks": {
                    "cli_flow": {"passed": True},
                    "smoke_flow": {"passed": True},
                    "api_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    reset_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "db", "reset"],
        env,
    )
    preset_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "preset", "list", "--json"],
        env,
    )
    domain_pack_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "domain-pack", "list", "--json"],
        env,
    )
    domain_pack_preview_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "domain-pack",
            "resolve",
            "--preset",
            "feature_delivery",
            "--task-kind",
            "shell_exec",
        ],
        env,
    )
    domain_pack_validate_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "domain-pack", "validate"],
        env,
    )
    memory_namespace_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "memory", "namespace", "list"],
        env,
    )
    capability_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "capability", "list"],
        env,
    )
    simulation_policy_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "simulation", "policy", "list"],
        env,
    )
    governance_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "governance", "tech-debt"],
        env,
    )
    governance_review_policy_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "governance", "review-policy"],
        env,
    )
    governance_release_readiness_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "governance",
            "release-readiness",
            "--validation-report-path",
            release_validation_report_path.as_posix(),
        ],
        env,
    )
    governance_domain_pack_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "governance", "domain-pack"],
        env,
    )
    suggest_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "suggest-presets",
            "--goal",
            "Research runtime architecture",
        ],
        env,
    )

    auto_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation auto run",
            "--preset",
            "feature_delivery",
            "--prepare",
            "--execute",
        ],
        env,
    )
    auto_run_id = auto_create_payload["run"]["run_id"]
    auto_runtime_task_id = auto_create_payload["prepared_task_id"]
    auto_memory_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "memory-candidates",
            auto_run_id,
        ],
        env,
    )
    auto_selected_memory_candidate = next(item for item in auto_memory_payload if item["namespace_id"] == "policy")
    auto_materialized_memory_item_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "materialize-memory",
            auto_run_id,
            "--candidate-id",
            auto_selected_memory_candidate["candidate_id"],
        ],
        env,
    )
    auto_memory_items_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "memory-items",
            auto_run_id,
        ],
        env,
    )
    auto_namespace_memory_items_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "memory",
            "item",
            "list",
            "--namespace",
            "policy",
        ],
        env,
    )
    auto_retrieval_preview_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "memory",
            "retrieve-preview",
            "--preset",
            "feature_delivery",
            "--namespace",
            "policy",
            "--memory-item-id",
            auto_materialized_memory_item_payload["memory_item_id"],
        ],
        env,
    )
    bridge_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation memory-aware compile",
            "--preset",
            "feature_delivery",
        ],
        env,
    )
    bridge_run_id = bridge_create_payload["run"]["run_id"]
    bridge_compile_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "compile",
            bridge_run_id,
            "--memory-item-id",
            auto_materialized_memory_item_payload["memory_item_id"],
        ],
        env,
    )
    bridge_detail_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "status-detail",
            bridge_run_id,
        ],
        env,
    )
    bridge_resume_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "resume",
            bridge_run_id,
        ],
        env,
    )
    bridge_evidence_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "task",
            "evidence",
            bridge_compile_payload["runtime_task_id"],
        ],
        env,
    )
    auto_status_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status", auto_run_id],
        env,
    )
    auto_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", auto_run_id],
        env,
    )
    auto_summary_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "summary", auto_run_id],
        env,
    )
    auto_simulation_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "simulation", auto_run_id],
        env,
    )
    auto_recorded_simulation_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "record-simulation",
            auto_run_id,
        ],
        env,
    )
    auto_post_record_detail_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "status-detail",
            auto_run_id,
        ],
        env,
    )
    auto_simulation_records_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "simulations",
            auto_run_id,
        ],
        env,
    )
    auto_event_inspection_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "event-inspection",
            auto_run_id,
        ],
        env,
    )
    auto_audit_report_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "audit-report", auto_run_id],
        env,
    )
    auto_inspection_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "inspect", auto_run_id],
        env,
    )
    auto_timeline_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "timeline", auto_run_id, "--json"],
        env,
    )
    auto_evidence_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "task", "evidence", auto_runtime_task_id],
        env,
    )
    auto_claims_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "claims", auto_run_id],
        env,
    )
    auto_leases_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "leases", auto_run_id],
        env,
    )
    auto_attempts_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "attempts", auto_run_id],
        env,
    )
    auto_snapshots_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "snapshots", auto_run_id],
        env,
    )
    auto_budget_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "budget", auto_run_id],
        env,
    )
    auto_artifact_path = Path(auto_create_payload["expected_artifacts"][0])
    if not auto_artifact_path.is_absolute():
        auto_artifact_path = PROJECT_ROOT / auto_artifact_path
    auto_artifact_text = auto_artifact_path.read_text(encoding="utf-8")

    human_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation human run",
            "--preset",
            "research_spike",
        ],
        env,
    )
    human_run_id = human_create_payload["run"]["run_id"]
    human_compile_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "compile", human_run_id],
        env,
    )
    human_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", human_run_id],
        env,
    )
    human_summary_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "summary", human_run_id],
        env,
    )
    human_simulation_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "simulation", human_run_id],
        env,
    )
    human_inspection_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "inspect", human_run_id],
        env,
    )
    human_resume_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", human_run_id],
        env,
    )
    human_event_inspection_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "event-inspection",
            human_run_id,
        ],
        env,
    )
    human_audit_report_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "audit-report", human_run_id],
        env,
    )
    human_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "approve", human_run_id],
        env,
    )
    human_handoffs_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "handoffs", human_run_id],
        env,
    )
    human_timeline_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "timeline", human_run_id, "--json"],
        env,
    )
    human_claims_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "claims", human_run_id],
        env,
    )
    human_leases_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "leases", human_run_id],
        env,
    )
    human_attempts_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "attempts", human_run_id],
        env,
    )
    human_snapshots_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "snapshots", human_run_id],
        env,
    )
    human_budget_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "budget", human_run_id],
        env,
    )

    recommended_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation recommended run",
            "--preset",
            "advisory_delivery",
        ],
        env,
    )
    recommended_run_id = recommended_create_payload["run"]["run_id"]
    recommended_compile_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "compile", recommended_run_id],
        env,
    )
    mutate_task_packet_command(
        db_path,
        recommended_compile_payload["runtime_task_id"],
        ["python", "-c", "import sys; sys.exit(2)"],
    )
    recommended_resume_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", recommended_run_id],
        env,
    )
    recommended_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", recommended_run_id],
        env,
    )
    recommended_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "approve", recommended_run_id],
        env,
    )

    mandatory_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation mandatory run",
            "--preset",
            "guarded_delivery",
            "--prepare",
            "--execute",
        ],
        env,
    )
    mandatory_run_id = mandatory_create_payload["run"]["run_id"]
    mandatory_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", mandatory_run_id],
        env,
    )
    mandatory_simulations_before_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "simulations", mandatory_run_id],
        env,
    )
    mandatory_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "approve", mandatory_run_id],
        env,
    )
    mandatory_simulations_after_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "simulations", mandatory_run_id],
        env,
    )

    noop_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation noop run",
            "--preset",
            "research_spike",
        ],
        env,
    )
    noop_run_id = noop_create_payload["run"]["run_id"]
    noop_compile_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "compile",
            noop_run_id,
            "--task-kind",
            "noop",
        ],
        env,
    )
    noop_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", noop_run_id],
        env,
    )
    noop_runtime_task_id = noop_detail_payload["runtime_tasks"][0]["runtime_task_id"]
    noop_resume_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", noop_run_id],
        env,
    )
    noop_evidence_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "task", "evidence", noop_runtime_task_id],
        env,
    )
    noop_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "approve", noop_run_id],
        env,
    )

    repair_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation repair run",
            "--preset",
            "feature_delivery",
        ],
        env,
    )
    repair_run_id = repair_create_payload["run"]["run_id"]
    run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "compile", repair_run_id],
        env,
    )
    run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", repair_run_id],
        env,
    )
    corrupt_runtime_state_for_run(
        db_path,
        repair_run_id,
        graph_step="awaiting_review",
        is_terminal=False,
        extra_payload={"corrupted": True},
    )
    repair_plan_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "reconcile", repair_run_id],
        env,
    )
    repair_apply_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "reconcile",
            repair_run_id,
            "--apply",
        ],
        env,
    )
    repair_inspection_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "inspect", repair_run_id],
        env,
    )

    cancel_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation cancel run",
            "--preset",
            "feature_delivery",
        ],
        env,
    )
    cancel_run_id = cancel_create_payload["run"]["run_id"]
    run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "cancel", cancel_run_id],
        env,
    )
    run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "cancel", cancel_run_id],
        env,
    )
    cancel_status_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status", cancel_run_id],
        env,
    )

    artifact_refs = auto_evidence_payload.get("artifact_refs", [])
    artifact_paths_exist = all(Path(item["path"]).exists() for item in artifact_refs)
    bridge_artifact_refs = bridge_evidence_payload.get("artifact_refs", [])
    bridge_artifact_text = (
        Path(bridge_artifact_refs[0]["path"]).read_text(encoding="utf-8")
        if bridge_artifact_refs and Path(bridge_artifact_refs[0]["path"]).exists()
        else ""
    )
    auto_timeline_events = [item["event_type"] for item in auto_timeline_payload]
    human_timeline_events = [item["event_type"] for item in human_timeline_payload]
    result.update(
        {
            "db_reset_seeded": reset_payload.get("seeded_presets", []),
            "preset_ids": [item["preset_id"] for item in preset_payload],
            "domain_pack_ids": [item["domain_pack_id"] for item in domain_pack_payload],
            "domain_pack_preview_id": (
                domain_pack_preview_payload.get("domain_pack", {}).get("domain_pack_id")
                if domain_pack_preview_payload.get("resolved")
                else None
            ),
            "domain_pack_preview_adapter": (
                domain_pack_preview_payload.get("capability_resolution", {}).get("adapter_name")
            ),
            "domain_pack_validation_passed": domain_pack_validate_payload.get("passed"),
            "domain_pack_validation_issue_count": domain_pack_validate_payload.get("issue_count"),
            "memory_namespace_ids": [item["namespace_id"] for item in memory_namespace_payload],
            "capability_routes": capability_payload,
            "simulation_policy_ids": [item["policy_id"] for item in simulation_policy_payload],
            "governance_open_debt_count": governance_payload["open_debt_count"],
            "governance_m3_focus_ids": [item["debt_id"] for item in governance_payload["m3_focus_items"]],
            "governance_supported_review_policies": [
                item["policy"] for item in governance_review_policy_payload["supported_policies"]
            ],
            "governance_review_policy_debt_id": (
                governance_review_policy_payload["debt_linkage"]["debt_id"]
                if governance_review_policy_payload["debt_linkage"] is not None
                else None
            ),
            "governance_release_ready": governance_release_readiness_payload["overall_ready"],
            "governance_release_domain_pack_ids": [
                item["domain_pack_id"] for item in governance_release_readiness_payload["domain_packs"]
            ],
            "governance_domain_pack_platformized": governance_domain_pack_payload["overall_platformized"],
            "suggest_top_preset": suggest_payload[0]["preset_id"] if suggest_payload else None,
            "auto_run_status": auto_status_payload.get("status"),
            "auto_review_decision": auto_create_payload.get("review_decision"),
            "auto_domain_pack_id": auto_status_payload.get("domain_pack", {}).get("domain_pack_id"),
            "auto_capability_adapter": auto_status_payload.get("capability_resolution", {}).get("adapter_name"),
            "auto_memory_namespace_ids": [item["namespace_id"] for item in auto_memory_payload],
            "auto_materialized_memory_namespace": auto_materialized_memory_item_payload["namespace_id"],
            "auto_materialized_memory_source_candidate_id": auto_materialized_memory_item_payload["source_candidate_id"],
            "auto_memory_item_namespace_ids": [item["namespace_id"] for item in auto_memory_items_payload],
            "auto_policy_memory_item_run_ids": [item["run_id"] for item in auto_namespace_memory_items_payload],
            "auto_retrieval_preview_item_count": auto_retrieval_preview_payload["item_count"],
            "auto_retrieval_preview_namespace_ids": auto_retrieval_preview_payload["namespace_ids"],
            "auto_retrieval_preview_selected_ids": auto_retrieval_preview_payload["selected_memory_item_ids"],
            "bridge_compile_status": bridge_compile_payload["run"]["status"],
            "bridge_resume_status": bridge_resume_payload["run"]["status"],
            "bridge_memory_preview_selected_ids": bridge_compile_payload["memory_preview"]["selected_memory_item_ids"],
            "bridge_detail_memory_preview_selected_ids": bridge_detail_payload["memory_retrieval_preview"][
                "selected_memory_item_ids"
            ],
            "bridge_artifact_contains_memory_item_ids": "memory_item_ids:" in bridge_artifact_text,
            "bridge_artifact_contains_memory_brief": "memory_brief:" in bridge_artifact_text,
            "auto_artifact_contains_domain_pack": "domain_pack: software_delivery_pack" in auto_artifact_text,
            "auto_artifact_contains_goal_prefix": "goal: [software-delivery]" in auto_artifact_text,
            "auto_failure_reason": auto_detail_payload.get("failure_reason"),
            "auto_last_runtime_step": auto_detail_payload.get("last_runtime_state", {}).get("graph_step"),
            "auto_summary_category": auto_summary_payload["failure_taxonomy"]["category"],
            "auto_simulation_status": auto_simulation_payload["status"],
            "auto_simulation_policy_id": auto_simulation_payload["policy_id"],
            "auto_recorded_simulation_status": auto_recorded_simulation_payload["status"],
            "auto_recorded_simulation_sources": [item["recorded_from"] for item in auto_simulation_records_payload],
            "auto_recorded_simulation_record_count": len(auto_simulation_records_payload),
            "auto_latest_simulation_record_id": (
                auto_post_record_detail_payload.get("latest_simulation_record") or {}
            ).get("record_id"),
            "auto_event_inspection_passed": auto_event_inspection_payload["closure_audit"]["passed"],
            "auto_event_closure_state": auto_event_inspection_payload["closure_audit"]["state"],
            "auto_audit_closure_state": auto_audit_report_payload["review_packet"]["closure_summary"]["state"],
            "auto_inspection_passed": auto_inspection_payload.get("passed"),
            "auto_inspection_problem_count": auto_inspection_payload.get("problem_count"),
            "auto_timeline_events": auto_timeline_events,
            "auto_active_claims": auto_status_payload.get("active_claims", []),
            "auto_latest_claim": auto_status_payload.get("latest_claim"),
            "auto_active_worker_leases": auto_status_payload.get("active_worker_leases", []),
            "auto_latest_worker_lease": auto_status_payload.get("latest_worker_lease"),
            "auto_claim_statuses": [item["status"] for item in auto_claims_payload],
            "auto_attempt_statuses": [item["status"] for item in auto_attempts_payload],
            "auto_attempt_triggers": [item["trigger"] for item in auto_attempts_payload],
            "auto_worker_lease_statuses": [item["status"] for item in auto_leases_payload],
            "auto_snapshot_stages": [item["stage"] for item in auto_snapshots_payload],
            "auto_remaining_retries": auto_budget_payload["budget_projection"]["remaining_retries"],
            "human_compile_status": human_compile_payload["run"]["status"],
            "human_next_action": human_detail_payload.get("next_action"),
            "human_waiting_reason": human_detail_payload.get("waiting_reason"),
            "human_last_runtime_step": human_detail_payload.get("last_runtime_state", {}).get("graph_step"),
            "human_summary_category": human_summary_payload["failure_taxonomy"]["category"],
            "human_simulation_status": human_simulation_payload["status"],
            "human_simulation_policy_id": human_simulation_payload["policy_id"],
            "human_event_inspection_passed": human_event_inspection_payload["closure_audit"]["passed"],
            "human_event_closure_state": human_event_inspection_payload["closure_audit"]["state"],
            "human_audit_closure_state": human_audit_report_payload["review_packet"]["closure_summary"]["state"],
            "human_recoverability_hint": human_detail_payload.get("recoverability_hint"),
            "human_inspection_passed": human_inspection_payload.get("passed"),
            "human_inspection_problem_count": human_inspection_payload.get("problem_count"),
            "human_resume_status": human_resume_payload["run"]["status"],
            "human_approve_status": human_approve_payload["run"]["status"],
            "human_handoffs_count": len(human_handoffs_payload),
            "human_timeline_events": human_timeline_events,
            "human_claim_statuses": [item["status"] for item in human_claims_payload],
            "human_attempt_statuses": [item["status"] for item in human_attempts_payload],
            "human_attempt_triggers": [item["trigger"] for item in human_attempts_payload],
            "human_worker_lease_statuses": [item["status"] for item in human_leases_payload],
            "human_snapshot_stages": [item["stage"] for item in human_snapshots_payload],
            "human_remaining_retries": human_budget_payload["budget_projection"]["remaining_retries"],
            "recommended_resume_status": recommended_resume_payload["run"]["status"],
            "recommended_review_decision": recommended_resume_payload["review_decision"],
            "recommended_review_policy": recommended_detail_payload["review_policy"],
            "recommended_effective_review_state": recommended_detail_payload["effective_review_state"],
            "recommended_latest_reviewer_type": recommended_detail_payload["latest_review_verdict"]["reviewer_type"],
            "recommended_latest_decision": recommended_detail_payload["latest_review_verdict"]["decision"],
            "recommended_approve_status": recommended_approve_payload["run"]["status"],
            "mandatory_run_status": mandatory_create_payload["run"]["status"],
            "mandatory_review_decision": mandatory_create_payload["review_decision"],
            "mandatory_review_policy": mandatory_detail_payload["review_policy"],
            "mandatory_effective_review_state": mandatory_detail_payload["effective_review_state"],
            "mandatory_latest_reviewer_type": mandatory_detail_payload["latest_review_verdict"]["reviewer_type"],
            "mandatory_latest_decision": mandatory_detail_payload["latest_review_verdict"]["decision"],
            "mandatory_latest_simulation_record_source": (
                mandatory_detail_payload.get("latest_simulation_record") or {}
            ).get("recorded_from"),
            "mandatory_simulation_sources_before_approve": [
                item["recorded_from"] for item in mandatory_simulations_before_approve_payload
            ],
            "mandatory_approve_status": mandatory_approve_payload["run"]["status"],
            "mandatory_simulation_sources_after_approve": [
                item["recorded_from"] for item in mandatory_simulations_after_approve_payload
            ],
            "noop_compile_status": noop_compile_payload["run"]["status"],
            "noop_task_kind": noop_detail_payload["runtime_tasks"][0]["task_kind"],
            "noop_resume_status": noop_resume_payload["run"]["status"],
            "noop_approve_status": noop_approve_payload["run"]["status"],
            "noop_adapter_name": noop_evidence_payload.get("raw_execution", {}).get("adapter_name"),
            "noop_artifact_paths_exist": all(
                Path(item["path"]).exists() for item in noop_evidence_payload.get("artifact_refs", [])
            ),
            "repair_plan_action": repair_plan_payload["problems"][0]["repair_action"],
            "repair_apply_action": repair_apply_payload["action"],
            "repair_inspection_passed": repair_inspection_payload["passed"],
            "artifact_ref_fields": list(artifact_refs[0].keys()) if artifact_refs else [],
            "artifact_paths_exist": artifact_paths_exist,
            "cancel_status": cancel_status_payload.get("status"),
        }
    )
    result["passed"] = all(
        [
            result["db_reset_seeded"]
            == ["feature_delivery", "research_spike", "advisory_delivery", "guarded_delivery"],
            set(result["preset_ids"])
            == {"feature_delivery", "research_spike", "advisory_delivery", "guarded_delivery"},
            result["domain_pack_ids"] == ["software_delivery_pack"],
            result["domain_pack_preview_id"] == "software_delivery_pack",
            result["domain_pack_preview_adapter"] == "shell",
            result["domain_pack_validation_passed"] is True,
            result["domain_pack_validation_issue_count"] == 0,
            result["memory_namespace_ids"] == ["repo", "failure", "policy", "release"],
            result["capability_routes"]
            == [
                {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
                {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
                {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
            ],
            result["simulation_policy_ids"]
            == [
                "advisory_failure_simulation",
                "delivery_consistency_simulation",
                "research_no_simulation",
            ],
            result["governance_open_debt_count"] >= 1,
            "TD-010" in result["governance_m3_focus_ids"],
            result["governance_supported_review_policies"]
            == ["auto_only", "recommended", "human_required", "mandatory"],
            result["governance_review_policy_debt_id"] == "TD-006",
            result["governance_release_ready"] is True,
            result["governance_release_domain_pack_ids"] == ["software_delivery_pack"],
            result["governance_domain_pack_platformized"] is True,
            result["suggest_top_preset"] == "research_spike",
            result["auto_run_status"] == "completed",
            result["auto_review_decision"] == "pass",
            result["auto_domain_pack_id"] == "software_delivery_pack",
            result["auto_capability_adapter"] == "shell",
            set(result["auto_memory_namespace_ids"]) == {"repo", "policy", "release"},
            result["auto_materialized_memory_namespace"] == "policy",
            result["auto_materialized_memory_source_candidate_id"].endswith("_policy"),
            result["auto_memory_item_namespace_ids"] == ["policy"],
            result["auto_policy_memory_item_run_ids"] == [auto_run_id],
            result["auto_retrieval_preview_item_count"] == 1,
            result["auto_retrieval_preview_namespace_ids"] == ["policy"],
            len(result["auto_retrieval_preview_selected_ids"]) == 1,
            result["bridge_compile_status"] == "prepared",
            result["bridge_resume_status"] == "completed",
            len(result["bridge_memory_preview_selected_ids"]) == 1,
            result["bridge_detail_memory_preview_selected_ids"] == result["bridge_memory_preview_selected_ids"],
            result["bridge_artifact_contains_memory_item_ids"] is True,
            result["bridge_artifact_contains_memory_brief"] is True,
            result["auto_artifact_contains_domain_pack"] is True,
            result["auto_artifact_contains_goal_prefix"] is True,
            result["auto_failure_reason"] is None,
            result["auto_last_runtime_step"] == "completed",
            result["auto_summary_category"] == "success",
            result["auto_simulation_status"] == "passed",
            result["auto_simulation_policy_id"] == "delivery_consistency_simulation",
            result["auto_recorded_simulation_status"] == "passed",
            result["auto_recorded_simulation_sources"] == ["lifecycle_terminal", "manual_request"],
            result["auto_recorded_simulation_record_count"] == 2,
            result["auto_latest_simulation_record_id"] == auto_recorded_simulation_payload["record_id"],
            result["auto_event_inspection_passed"] is True,
            result["auto_event_closure_state"] == "closed",
            result["auto_audit_closure_state"] == "closed",
            result["auto_inspection_passed"] is True,
            result["auto_inspection_problem_count"] == 0,
            timeline_contains_required_events(result["auto_timeline_events"], AUTO_TIMELINE),
            CLAIM_EVENTS.issubset(set(result["auto_timeline_events"])),
            LEASE_EVENTS.issubset(set(result["auto_timeline_events"])),
            ATTEMPT_EVENTS.issubset(set(result["auto_timeline_events"])),
            result["auto_active_claims"] == [],
            result["auto_latest_claim"] is not None,
            result["auto_latest_claim"]["status"] == "released",
            result["auto_active_worker_leases"] == [],
            result["auto_latest_worker_lease"] is not None,
            result["auto_latest_worker_lease"]["status"] == "released",
            result["auto_claim_statuses"] == ["released"],
            result["auto_attempt_statuses"] == ["superseded", "completed"],
            result["auto_attempt_triggers"] == ["compile", "resume"],
            result["auto_worker_lease_statuses"] == ["released"],
            result["auto_snapshot_stages"] == ["compiled", "completed"],
            result["auto_remaining_retries"] == 1,
            result["human_compile_status"] == "prepared",
            result["human_next_action"] == "resume",
            result["human_waiting_reason"] == "awaiting_runtime_resume",
            result["human_last_runtime_step"] == "compiled",
            result["human_summary_category"] == "pending_work",
            result["human_simulation_status"] == "skipped",
            result["human_simulation_policy_id"] == "research_no_simulation",
            result["human_event_inspection_passed"] is True,
            result["human_event_closure_state"] == "awaiting_review",
            result["human_audit_closure_state"] == "awaiting_review",
            result["human_recoverability_hint"] == "resume_run",
            result["human_inspection_passed"] is True,
            result["human_inspection_problem_count"] == 0,
            result["human_resume_status"] == "awaiting_review",
            result["human_approve_status"] == "completed",
            result["human_handoffs_count"] == 1,
            timeline_contains_required_events(result["human_timeline_events"], HUMAN_TIMELINE),
            CLAIM_EVENTS.issubset(set(result["human_timeline_events"])),
            LEASE_EVENTS.issubset(set(result["human_timeline_events"])),
            ATTEMPT_EVENTS.issubset(set(result["human_timeline_events"])),
            result["human_claim_statuses"] == ["released"],
            result["human_attempt_statuses"] == ["superseded", "completed"],
            result["human_attempt_triggers"] == ["compile", "resume"],
            result["human_worker_lease_statuses"] == ["released"],
            result["human_snapshot_stages"] == ["compiled", "awaiting_review", "completed"],
            result["human_remaining_retries"] == 0,
            result["recommended_resume_status"] == "awaiting_review",
            result["recommended_review_decision"] == "fail",
            result["recommended_review_policy"] == "recommended",
            result["recommended_effective_review_state"] == "human_pending",
            result["recommended_latest_reviewer_type"] == "auto",
            result["recommended_latest_decision"] == "fail",
            result["recommended_approve_status"] == "completed",
            result["mandatory_run_status"] == "awaiting_review",
            result["mandatory_review_decision"] == "pass",
            result["mandatory_review_policy"] == "mandatory",
            result["mandatory_effective_review_state"] == "human_pending",
            result["mandatory_latest_reviewer_type"] == "auto",
            result["mandatory_latest_decision"] == "pass",
            result["mandatory_latest_simulation_record_source"] == "lifecycle_awaiting_review",
            result["mandatory_simulation_sources_before_approve"] == ["lifecycle_awaiting_review"],
            result["mandatory_approve_status"] == "completed",
            result["mandatory_simulation_sources_after_approve"]
            == ["lifecycle_awaiting_review", "lifecycle_terminal"],
            result["noop_compile_status"] == "prepared",
            result["noop_task_kind"] == "noop",
            result["noop_resume_status"] == "awaiting_review",
            result["noop_approve_status"] == "completed",
            result["noop_adapter_name"] == "noop",
            result["noop_artifact_paths_exist"],
            result["repair_plan_action"] == "align_completed_runtime_state",
            result["repair_apply_action"] == "align_completed_runtime_state",
            result["repair_inspection_passed"] is True,
            set(result["artifact_ref_fields"]) == {"path", "sha256", "mtime", "size_bytes"},
            result["artifact_paths_exist"],
            result["cancel_status"] == "cancelled",
        ]
    )
    return result


def validate_smoke_flow(env: dict[str, str], db_path: Path) -> dict[str, Any]:
    payload, _ = run_json_command(
        [sys.executable, "-m", "infra.scripts.manage", "--db-path", db_path.as_posix(), "smoke"],
        env,
    )
    return {
        "passed": payload.get("status") == "completed"
        and [item["domain_pack_id"] for item in payload.get("domain_packs", [])] == ["software_delivery_pack"]
        and payload.get("capability_routes", [])
        == [
            {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
            {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
            {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
        ]
        and payload.get("auto_run", {}).get("status") == "completed"
        and payload.get("human_run", {}).get("status") == "completed"
        and payload.get("auto_run", {}).get("domain_pack", {}).get("domain_pack_id") == "software_delivery_pack"
        and payload.get("auto_run", {}).get("capability_resolution", {}).get("adapter_name") == "shell"
        and timeline_contains_required_events(payload.get("auto_run", {}).get("timeline_events", []), AUTO_TIMELINE)
        and timeline_contains_required_events(payload.get("human_run", {}).get("timeline_events", []), HUMAN_TIMELINE)
        and CLAIM_EVENTS.issubset(set(payload.get("auto_run", {}).get("timeline_events", [])))
        and CLAIM_EVENTS.issubset(set(payload.get("human_run", {}).get("timeline_events", [])))
        and LEASE_EVENTS.issubset(set(payload.get("auto_run", {}).get("timeline_events", [])))
        and LEASE_EVENTS.issubset(set(payload.get("human_run", {}).get("timeline_events", [])))
        and ATTEMPT_EVENTS.issubset(set(payload.get("auto_run", {}).get("timeline_events", [])))
        and ATTEMPT_EVENTS.issubset(set(payload.get("human_run", {}).get("timeline_events", [])))
        and [item["status"] for item in payload.get("auto_run", {}).get("claims", [])] == ["released"]
        and [item["status"] for item in payload.get("human_run", {}).get("claims", [])] == ["released"]
        and [item["status"] for item in payload.get("auto_run", {}).get("attempts", [])] == ["superseded", "completed"]
        and [item["status"] for item in payload.get("human_run", {}).get("attempts", [])] == ["superseded", "completed"]
        and [item["status"] for item in payload.get("auto_run", {}).get("worker_leases", [])] == ["released"]
        and [item["status"] for item in payload.get("human_run", {}).get("worker_leases", [])] == ["released"]
        and [item["stage"] for item in payload.get("auto_run", {}).get("snapshots", [])] == ["compiled", "completed"]
        and [item["stage"] for item in payload.get("human_run", {}).get("snapshots", [])]
        == ["compiled", "awaiting_review", "completed"]
        and payload.get("auto_run", {}).get("budget_projection", {}).get("remaining_retries") == 1
        and payload.get("human_run", {}).get("budget_projection", {}).get("remaining_retries") == 0,
        **payload,
    }


def validate_api_flow(env: dict[str, str], db_path: Path, port: int) -> dict[str, Any]:
    result: dict[str, Any] = {"passed": False}
    release_validation_report_path = PROJECT_ROOT / "state" / "offline_validate_release_readiness_api.json"
    release_validation_report_path.write_text(
        json.dumps(
            {
                "overall_passed": True,
                "checks": {
                    "cli_flow": {"passed": True},
                    "smoke_flow": {"passed": True},
                    "api_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    run_json_command(
        [sys.executable, "-m", "infra.scripts.manage", "--db-path", db_path.as_posix(), "reset-db"],
        env,
    )
    base_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "infra.scripts.manage",
            "--db-path",
            db_path.as_posix(),
            "dev",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_api(base_url)
        presets = http_get_json(f"{base_url}/presets")
        domain_packs = http_get_json(f"{base_url}/domain-packs")
        domain_pack_preview = http_get_json(
            f"{base_url}/domain-packs/resolve?preset_id=feature_delivery&task_kind=shell_exec"
        )
        domain_pack_validation = http_get_json(f"{base_url}/domain-packs/validate")
        capability_routes = http_get_json(f"{base_url}/capability-routes")
        simulation_policies = http_get_json(f"{base_url}/simulation/policies")
        memory_namespaces = http_get_json(f"{base_url}/memory/namespaces")
        governance = http_get_json(f"{base_url}/governance/tech-debt")
        governance_review_policy = http_get_json(f"{base_url}/governance/review-policy")
        governance_domain_packs = http_get_json(f"{base_url}/governance/domain-packs")
        encoded_validation_report_path = urllib.parse.quote(release_validation_report_path.as_posix(), safe="")
        governance_release_readiness = http_get_json(
            f"{base_url}/governance/release-readiness?validation_report_path="
            f"{encoded_validation_report_path}"
        )

        auto_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API validation", "preset_id": "feature_delivery"})
        auto_run_id = auto_run["run_id"]
        auto_compile = http_post_json(f"{base_url}/runs/{auto_run_id}/compile")
        auto_detail = http_get_json(f"{base_url}/runs/{auto_run_id}/status-detail")
        auto_inspection = http_get_json(f"{base_url}/runs/{auto_run_id}/inspection")
        auto_handoffs = http_get_json(f"{base_url}/runs/{auto_run_id}/handoffs")
        auto_resume = http_post_json(f"{base_url}/runs/{auto_run_id}/resume")
        auto_summary = http_get_json(f"{base_url}/runs/{auto_run_id}/summary")
        auto_simulation = http_get_json(f"{base_url}/runs/{auto_run_id}/simulation")
        auto_recorded_simulation = http_post_json(f"{base_url}/runs/{auto_run_id}/simulation-records")
        auto_post_record_detail = http_get_json(f"{base_url}/runs/{auto_run_id}/status-detail")
        auto_simulation_records = http_get_json(f"{base_url}/runs/{auto_run_id}/simulation-records")
        auto_memory_candidates = http_get_json(f"{base_url}/runs/{auto_run_id}/memory-candidates")
        auto_selected_memory_candidate = next(item for item in auto_memory_candidates if item["namespace_id"] == "policy")
        auto_materialized_memory_item = http_post_json(
            f"{base_url}/runs/{auto_run_id}/memory-items",
            {"candidate_id": auto_selected_memory_candidate["candidate_id"]},
        )
        auto_memory_items = http_get_json(f"{base_url}/runs/{auto_run_id}/memory-items")
        auto_policy_memory_items = http_get_json(f"{base_url}/memory/items?namespace_id=policy")
        encoded_memory_item_id = urllib.parse.quote(auto_materialized_memory_item["memory_item_id"], safe="")
        auto_retrieval_preview = http_get_json(
            f"{base_url}/memory/retrieval-preview?preset_id=feature_delivery&namespace_id=policy"
            f"&memory_item_id={encoded_memory_item_id}"
        )
        bridge_run = http_post_json(
            f"{base_url}/runs",
            {"goal": "Offline API memory-aware compile", "preset_id": "feature_delivery"},
        )
        bridge_run_id = bridge_run["run_id"]
        bridge_compile = http_post_json(
            f"{base_url}/runs/{bridge_run_id}/compile",
            {"memory_item_ids": [auto_materialized_memory_item["memory_item_id"]]},
        )
        bridge_detail = http_get_json(f"{base_url}/runs/{bridge_run_id}/status-detail")
        bridge_resume = http_post_json(f"{base_url}/runs/{bridge_run_id}/resume")
        bridge_evidence = http_get_json(f"{base_url}/tasks/{bridge_compile['runtime_task_id']}/evidence")
        auto_event_inspection = http_get_json(f"{base_url}/runs/{auto_run_id}/event-inspection")
        auto_audit_report = http_get_json(f"{base_url}/runs/{auto_run_id}/audit-report")
        auto_timeline = http_get_json(f"{base_url}/runs/{auto_run_id}/timeline")
        auto_claims = http_get_json(f"{base_url}/runs/{auto_run_id}/claims")
        auto_leases = http_get_json(f"{base_url}/runs/{auto_run_id}/leases")
        auto_attempts = http_get_json(f"{base_url}/runs/{auto_run_id}/attempts")
        auto_snapshots = http_get_json(f"{base_url}/runs/{auto_run_id}/snapshots")
        auto_budget = http_get_json(f"{base_url}/runs/{auto_run_id}/budget")

        human_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API human validation", "preset_id": "research_spike"})
        human_run_id = human_run["run_id"]
        http_post_json(f"{base_url}/runs/{human_run_id}/compile")
        human_detail = http_get_json(f"{base_url}/runs/{human_run_id}/status-detail")
        human_inspection = http_get_json(f"{base_url}/runs/{human_run_id}/inspection")
        human_resume = http_post_json(f"{base_url}/runs/{human_run_id}/resume")
        human_summary = http_get_json(f"{base_url}/runs/{human_run_id}/summary")
        human_simulation = http_get_json(f"{base_url}/runs/{human_run_id}/simulation")
        human_event_inspection = http_get_json(f"{base_url}/runs/{human_run_id}/event-inspection")
        human_audit_report = http_get_json(f"{base_url}/runs/{human_run_id}/audit-report")
        human_approve = http_post_json(f"{base_url}/runs/{human_run_id}/approve")
        human_claims = http_get_json(f"{base_url}/runs/{human_run_id}/claims")
        human_leases = http_get_json(f"{base_url}/runs/{human_run_id}/leases")
        human_attempts = http_get_json(f"{base_url}/runs/{human_run_id}/attempts")
        human_snapshots = http_get_json(f"{base_url}/runs/{human_run_id}/snapshots")
        human_budget = http_get_json(f"{base_url}/runs/{human_run_id}/budget")
        human_timeline = http_get_json(f"{base_url}/runs/{human_run_id}/timeline")

        recommended_run = http_post_json(
            f"{base_url}/runs",
            {"goal": "Offline API recommended validation", "preset_id": "advisory_delivery"},
        )
        recommended_run_id = recommended_run["run_id"]
        recommended_compile = http_post_json(f"{base_url}/runs/{recommended_run_id}/compile")
        mutate_task_packet_command(
            db_path,
            recommended_compile["runtime_task_id"],
            ["python", "-c", "import sys; sys.exit(2)"],
        )
        recommended_resume = http_post_json(f"{base_url}/runs/{recommended_run_id}/resume")
        recommended_detail = http_get_json(f"{base_url}/runs/{recommended_run_id}/status-detail")
        recommended_approve = http_post_json(f"{base_url}/runs/{recommended_run_id}/approve")

        mandatory_run = http_post_json(
            f"{base_url}/runs",
            {"goal": "Offline API mandatory validation", "preset_id": "guarded_delivery"},
        )
        mandatory_run_id = mandatory_run["run_id"]
        http_post_json(f"{base_url}/runs/{mandatory_run_id}/compile")
        mandatory_resume = http_post_json(f"{base_url}/runs/{mandatory_run_id}/resume")
        mandatory_detail = http_get_json(f"{base_url}/runs/{mandatory_run_id}/status-detail")
        mandatory_simulations_before_approve = http_get_json(f"{base_url}/runs/{mandatory_run_id}/simulation-records")
        mandatory_approve = http_post_json(f"{base_url}/runs/{mandatory_run_id}/approve")
        mandatory_simulations_after_approve = http_get_json(f"{base_url}/runs/{mandatory_run_id}/simulation-records")

        noop_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API noop validation", "preset_id": "research_spike"})
        noop_run_id = noop_run["run_id"]
        noop_compile = http_post_json(f"{base_url}/runs/{noop_run_id}/compile", {"task_kind": "noop"})
        noop_detail = http_get_json(f"{base_url}/runs/{noop_run_id}/status-detail")
        noop_runtime_task_id = noop_detail["runtime_tasks"][0]["runtime_task_id"]
        noop_resume = http_post_json(f"{base_url}/runs/{noop_run_id}/resume")
        noop_evidence = http_get_json(f"{base_url}/tasks/{noop_runtime_task_id}/evidence")
        noop_approve = http_post_json(f"{base_url}/runs/{noop_run_id}/approve")

        repair_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API repair validation", "preset_id": "feature_delivery"})
        repair_run_id = repair_run["run_id"]
        http_post_json(f"{base_url}/runs/{repair_run_id}/compile")
        http_post_json(f"{base_url}/runs/{repair_run_id}/resume")
        corrupt_runtime_state_for_run(
            db_path,
            repair_run_id,
            graph_step="awaiting_review",
            is_terminal=False,
            extra_payload={"corrupted": True},
        )
        repair_plan = http_post_json(f"{base_url}/runs/{repair_run_id}/reconcile")
        repair_apply = http_post_json(f"{base_url}/runs/{repair_run_id}/reconcile", {"apply": True})
        repair_inspection = http_get_json(f"{base_url}/runs/{repair_run_id}/inspection")

        auto_timeline_events = [item["event_type"] for item in auto_timeline]
        human_timeline_events = [item["event_type"] for item in human_timeline]
        bridge_artifact_refs = bridge_evidence.get("artifact_refs", [])
        bridge_artifact_text = (
            Path(bridge_artifact_refs[0]["path"]).read_text(encoding="utf-8")
            if bridge_artifact_refs and Path(bridge_artifact_refs[0]["path"]).exists()
            else ""
        )
        result.update(
            {
                "preset_ids": [item["preset_id"] for item in presets],
                "domain_pack_ids": [item["domain_pack_id"] for item in domain_packs],
                "domain_pack_preview_id": (
                    domain_pack_preview.get("domain_pack", {}).get("domain_pack_id")
                    if domain_pack_preview.get("resolved")
                    else None
                ),
                "domain_pack_preview_adapter": domain_pack_preview.get("capability_resolution", {}).get("adapter_name"),
                "domain_pack_validation_passed": domain_pack_validation.get("passed"),
                "domain_pack_validation_issue_count": domain_pack_validation.get("issue_count"),
                "memory_namespace_ids": [item["namespace_id"] for item in memory_namespaces],
                "capability_routes": capability_routes,
                "simulation_policy_ids": [item["policy_id"] for item in simulation_policies],
                "governance_open_debt_count": governance["open_debt_count"],
                "governance_m3_focus_ids": [item["debt_id"] for item in governance["m3_focus_items"]],
                "governance_supported_review_policies": [
                    item["policy"] for item in governance_review_policy["supported_policies"]
                ],
                "governance_review_policy_debt_id": (
                    governance_review_policy["debt_linkage"]["debt_id"]
                    if governance_review_policy["debt_linkage"] is not None
                    else None
                ),
                "governance_release_ready": governance_release_readiness["overall_ready"],
                "governance_release_domain_pack_ids": [
                    item["domain_pack_id"] for item in governance_release_readiness["domain_packs"]
                ],
                "governance_domain_pack_platformized": governance_domain_packs["overall_platformized"],
                "auto_run_status": auto_resume["run"]["status"],
                "auto_compile_status": auto_compile["run"]["status"],
                "auto_domain_pack_id": auto_detail["domain_pack"]["domain_pack_id"],
                "auto_capability_adapter": auto_detail["capability_resolution"]["adapter_name"],
                "auto_memory_namespace_ids": [item["namespace_id"] for item in auto_memory_candidates],
                "auto_materialized_memory_namespace": auto_materialized_memory_item["namespace_id"],
                "auto_materialized_memory_source_candidate_id": auto_materialized_memory_item["source_candidate_id"],
                "auto_memory_item_namespace_ids": [item["namespace_id"] for item in auto_memory_items],
                "auto_policy_memory_item_run_ids": [item["run_id"] for item in auto_policy_memory_items],
                "auto_retrieval_preview_item_count": auto_retrieval_preview["item_count"],
                "auto_retrieval_preview_namespace_ids": auto_retrieval_preview["namespace_ids"],
                "auto_retrieval_preview_selected_ids": auto_retrieval_preview["selected_memory_item_ids"],
                "bridge_compile_status": bridge_compile["run"]["status"],
                "bridge_resume_status": bridge_resume["run"]["status"],
                "bridge_memory_preview_selected_ids": bridge_compile["memory_preview"]["selected_memory_item_ids"],
                "bridge_detail_memory_preview_selected_ids": bridge_detail["memory_retrieval_preview"][
                    "selected_memory_item_ids"
                ],
                "bridge_artifact_contains_memory_item_ids": "memory_item_ids:" in bridge_artifact_text,
                "bridge_artifact_contains_memory_brief": "memory_brief:" in bridge_artifact_text,
                "auto_next_action": auto_detail["next_action"],
                "auto_waiting_reason": auto_detail["waiting_reason"],
                "auto_last_runtime_step": auto_detail["last_runtime_state"]["graph_step"],
                "auto_summary_category": auto_summary["failure_taxonomy"]["category"],
                "auto_simulation_status": auto_simulation["status"],
                "auto_simulation_policy_id": auto_simulation["policy_id"],
                "auto_recorded_simulation_status": auto_recorded_simulation["status"],
                "auto_recorded_simulation_sources": [item["recorded_from"] for item in auto_simulation_records],
                "auto_recorded_simulation_record_count": len(auto_simulation_records),
                "auto_latest_simulation_record_id": (auto_post_record_detail.get("latest_simulation_record") or {}).get(
                    "record_id"
                ),
                "auto_event_inspection_passed": auto_event_inspection["closure_audit"]["passed"],
                "auto_event_closure_state": auto_event_inspection["closure_audit"]["state"],
                "auto_audit_closure_state": auto_audit_report["review_packet"]["closure_summary"]["state"],
                "auto_inspection_passed": auto_inspection["passed"],
                "auto_inspection_problem_count": auto_inspection["problem_count"],
                "auto_handoffs_count": len(auto_handoffs),
                "auto_timeline_events": auto_timeline_events,
                "auto_active_claims": auto_detail.get("active_claims", []),
                "auto_active_worker_leases": auto_detail.get("active_worker_leases", []),
                "auto_claim_statuses": [item["status"] for item in auto_claims],
                "auto_attempt_statuses": [item["status"] for item in auto_attempts],
                "auto_attempt_triggers": [item["trigger"] for item in auto_attempts],
                "auto_worker_lease_statuses": [item["status"] for item in auto_leases],
                "auto_snapshot_stages": [item["stage"] for item in auto_snapshots],
                "auto_remaining_retries": auto_budget["budget_projection"]["remaining_retries"],
                "human_waiting_reason": human_detail["waiting_reason"],
                "human_last_runtime_step": human_detail["last_runtime_state"]["graph_step"],
                "human_summary_category": human_summary["failure_taxonomy"]["category"],
                "human_simulation_status": human_simulation["status"],
                "human_simulation_policy_id": human_simulation["policy_id"],
                "human_event_inspection_passed": human_event_inspection["closure_audit"]["passed"],
                "human_event_closure_state": human_event_inspection["closure_audit"]["state"],
                "human_audit_closure_state": human_audit_report["review_packet"]["closure_summary"]["state"],
                "human_recoverability_hint": human_detail["recoverability_hint"],
                "human_inspection_passed": human_inspection["passed"],
                "human_inspection_problem_count": human_inspection["problem_count"],
                "human_resume_status": human_resume["run"]["status"],
                "human_approve_status": human_approve["run"]["status"],
                "human_timeline_events": human_timeline_events,
                "human_claim_statuses": [item["status"] for item in human_claims],
                "human_attempt_statuses": [item["status"] for item in human_attempts],
                "human_attempt_triggers": [item["trigger"] for item in human_attempts],
                "human_worker_lease_statuses": [item["status"] for item in human_leases],
                "human_snapshot_stages": [item["stage"] for item in human_snapshots],
                "human_remaining_retries": human_budget["budget_projection"]["remaining_retries"],
                "recommended_resume_status": recommended_resume["run"]["status"],
                "recommended_review_decision": recommended_resume["review_decision"],
                "recommended_review_policy": recommended_detail["review_policy"],
                "recommended_effective_review_state": recommended_detail["effective_review_state"],
                "recommended_latest_reviewer_type": recommended_detail["latest_review_verdict"]["reviewer_type"],
                "recommended_latest_decision": recommended_detail["latest_review_verdict"]["decision"],
                "recommended_approve_status": recommended_approve["run"]["status"],
                "mandatory_resume_status": mandatory_resume["run"]["status"],
                "mandatory_review_decision": mandatory_resume["review_decision"],
                "mandatory_review_policy": mandatory_detail["review_policy"],
                "mandatory_effective_review_state": mandatory_detail["effective_review_state"],
                "mandatory_latest_reviewer_type": mandatory_detail["latest_review_verdict"]["reviewer_type"],
                "mandatory_latest_decision": mandatory_detail["latest_review_verdict"]["decision"],
                "mandatory_latest_simulation_record_source": (
                    mandatory_detail.get("latest_simulation_record") or {}
                ).get("recorded_from"),
                "mandatory_simulation_sources_before_approve": [
                    item["recorded_from"] for item in mandatory_simulations_before_approve
                ],
                "mandatory_approve_status": mandatory_approve["run"]["status"],
                "mandatory_simulation_sources_after_approve": [
                    item["recorded_from"] for item in mandatory_simulations_after_approve
                ],
                "noop_compile_status": noop_compile["run"]["status"],
                "noop_task_kind": noop_detail["runtime_tasks"][0]["task_kind"],
                "noop_resume_status": noop_resume["run"]["status"],
                "noop_approve_status": noop_approve["run"]["status"],
                "noop_adapter_name": noop_evidence.get("raw_execution", {}).get("adapter_name"),
                "repair_plan_action": repair_plan["problems"][0]["repair_action"],
                "repair_apply_action": repair_apply["action"],
                "repair_inspection_passed": repair_inspection["passed"],
            }
        )
        result["passed"] = all(
            [
                set(result["preset_ids"])
                == {"feature_delivery", "research_spike", "advisory_delivery", "guarded_delivery"},
                result["domain_pack_ids"] == ["software_delivery_pack"],
                result["domain_pack_preview_id"] == "software_delivery_pack",
                result["domain_pack_preview_adapter"] == "shell",
                result["domain_pack_validation_passed"] is True,
                result["domain_pack_validation_issue_count"] == 0,
                result["memory_namespace_ids"] == ["repo", "failure", "policy", "release"],
                result["capability_routes"]
                == [
                    {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
                    {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
                    {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
                ],
                result["simulation_policy_ids"]
                == [
                    "advisory_failure_simulation",
                    "delivery_consistency_simulation",
                    "research_no_simulation",
                ],
                result["governance_open_debt_count"] >= 1,
                "TD-010" in result["governance_m3_focus_ids"],
                result["governance_supported_review_policies"]
                == ["auto_only", "recommended", "human_required", "mandatory"],
                result["governance_review_policy_debt_id"] == "TD-006",
                result["governance_release_ready"] is True,
                result["governance_release_domain_pack_ids"] == ["software_delivery_pack"],
                result["governance_domain_pack_platformized"] is True,
                result["auto_compile_status"] == "prepared",
                result["auto_domain_pack_id"] == "software_delivery_pack",
                result["auto_capability_adapter"] == "shell",
                set(result["auto_memory_namespace_ids"]) == {"repo", "policy", "release"},
                result["auto_materialized_memory_namespace"] == "policy",
                result["auto_materialized_memory_source_candidate_id"].endswith("_policy"),
                result["auto_memory_item_namespace_ids"] == ["policy"],
                result["auto_policy_memory_item_run_ids"] == [auto_run_id],
                result["auto_retrieval_preview_item_count"] == 1,
                result["auto_retrieval_preview_namespace_ids"] == ["policy"],
                len(result["auto_retrieval_preview_selected_ids"]) == 1,
                result["bridge_compile_status"] == "prepared",
                result["bridge_resume_status"] == "completed",
                len(result["bridge_memory_preview_selected_ids"]) == 1,
                result["bridge_detail_memory_preview_selected_ids"] == result["bridge_memory_preview_selected_ids"],
                result["bridge_artifact_contains_memory_item_ids"] is True,
                result["bridge_artifact_contains_memory_brief"] is True,
                result["auto_next_action"] == "resume",
                result["auto_waiting_reason"] == "awaiting_runtime_resume",
                result["auto_last_runtime_step"] == "compiled",
                result["auto_summary_category"] == "success",
                result["auto_simulation_status"] == "passed",
                result["auto_simulation_policy_id"] == "delivery_consistency_simulation",
                result["auto_recorded_simulation_status"] == "passed",
                result["auto_recorded_simulation_sources"] == ["lifecycle_terminal", "manual_request"],
                result["auto_recorded_simulation_record_count"] == 2,
                result["auto_latest_simulation_record_id"] == auto_recorded_simulation["record_id"],
                result["auto_event_inspection_passed"] is True,
                result["auto_event_closure_state"] == "closed",
                result["auto_audit_closure_state"] == "closed",
                result["auto_inspection_passed"] is True,
                result["auto_inspection_problem_count"] == 0,
                result["auto_handoffs_count"] == 1,
                result["auto_run_status"] == "completed",
                timeline_contains_required_events(result["auto_timeline_events"], AUTO_TIMELINE),
                CLAIM_EVENTS.issubset(set(result["auto_timeline_events"])),
                LEASE_EVENTS.issubset(set(result["auto_timeline_events"])),
                ATTEMPT_EVENTS.issubset(set(result["auto_timeline_events"])),
                result["auto_active_claims"] == [],
                result["auto_active_worker_leases"] == [],
                result["auto_claim_statuses"] == ["released"],
                result["auto_attempt_statuses"] == ["superseded", "completed"],
                result["auto_attempt_triggers"] == ["compile", "resume"],
                result["auto_worker_lease_statuses"] == ["released"],
                result["auto_snapshot_stages"] == ["compiled", "completed"],
                result["auto_remaining_retries"] == 1,
                result["human_waiting_reason"] == "awaiting_runtime_resume",
                result["human_last_runtime_step"] == "compiled",
                result["human_summary_category"] == "review_pending",
                result["human_simulation_status"] == "skipped",
                result["human_simulation_policy_id"] == "research_no_simulation",
                result["human_event_inspection_passed"] is True,
                result["human_event_closure_state"] == "awaiting_review",
                result["human_audit_closure_state"] == "awaiting_review",
                result["human_recoverability_hint"] == "resume_run",
                result["human_inspection_passed"] is True,
                result["human_inspection_problem_count"] == 0,
                result["human_resume_status"] == "awaiting_review",
                result["human_approve_status"] == "completed",
                timeline_contains_required_events(result["human_timeline_events"], HUMAN_TIMELINE),
                CLAIM_EVENTS.issubset(set(result["human_timeline_events"])),
                LEASE_EVENTS.issubset(set(result["human_timeline_events"])),
                ATTEMPT_EVENTS.issubset(set(result["human_timeline_events"])),
                result["human_claim_statuses"] == ["released"],
                result["human_attempt_statuses"] == ["superseded", "completed"],
                result["human_attempt_triggers"] == ["compile", "resume"],
                result["human_worker_lease_statuses"] == ["released"],
                result["human_snapshot_stages"] == ["compiled", "awaiting_review", "completed"],
                result["human_remaining_retries"] == 0,
                result["recommended_resume_status"] == "awaiting_review",
                result["recommended_review_decision"] == "fail",
                result["recommended_review_policy"] == "recommended",
                result["recommended_effective_review_state"] == "human_pending",
                result["recommended_latest_reviewer_type"] == "auto",
                result["recommended_latest_decision"] == "fail",
                result["recommended_approve_status"] == "completed",
                result["mandatory_resume_status"] == "awaiting_review",
                result["mandatory_review_decision"] == "pass",
                result["mandatory_review_policy"] == "mandatory",
                result["mandatory_effective_review_state"] == "human_pending",
                result["mandatory_latest_reviewer_type"] == "auto",
                result["mandatory_latest_decision"] == "pass",
                result["mandatory_latest_simulation_record_source"] == "lifecycle_awaiting_review",
                result["mandatory_simulation_sources_before_approve"] == ["lifecycle_awaiting_review"],
                result["mandatory_approve_status"] == "completed",
                result["mandatory_simulation_sources_after_approve"]
                == ["lifecycle_awaiting_review", "lifecycle_terminal"],
                result["noop_compile_status"] == "prepared",
                result["noop_task_kind"] == "noop",
                result["noop_resume_status"] == "awaiting_review",
                result["noop_approve_status"] == "completed",
                result["noop_adapter_name"] == "noop",
                result["repair_plan_action"] == "align_completed_runtime_state",
                result["repair_apply_action"] == "align_completed_runtime_state",
                result["repair_inspection_passed"] is True,
            ]
        )
        return result
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    env, removed_env_keys = sanitized_env()
    report: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "project_root": PROJECT_ROOT.as_posix(),
        "python_executable": sys.executable,
        "removed_env_keys": removed_env_keys,
        "checks": {},
        "overall_passed": False,
    }

    checks: dict[str, Any] = {}
    if args.skip_offline_probe:
        checks["offline_probe"] = {
            "passed": None,
            "skipped": True,
            "results": [],
            "note": "offline probe skipped by flag",
        }
    else:
        probes = [
            tcp_probe("1.1.1.1", 443),
            tcp_probe("www.baidu.com", 443),
            tcp_probe("www.qq.com", 443),
        ]
        checks["offline_probe"] = {
            "passed": not any(item["reachable"] for item in probes),
            "skipped": False,
            "results": probes,
        }

    cli_db_path = PROJECT_ROOT / "state" / "offline_validate_cli.db"
    smoke_db_path = PROJECT_ROOT / "state" / "offline_validate_smoke.db"
    api_db_path = PROJECT_ROOT / "state" / "offline_validate_api.db"

    for key, fn, fn_args in [
        ("cli_flow", validate_cli_flow, (env, cli_db_path)),
        ("smoke_flow", validate_smoke_flow, (env, smoke_db_path)),
        ("api_flow", validate_api_flow, (env, api_db_path, args.api_port)),
    ]:
        try:
            checks[key] = fn(*fn_args)
        except Exception as exc:  # noqa: BLE001
            checks[key] = {"passed": False, "error": str(exc)}

    report["checks"] = checks
    offline_probe_pass = checks["offline_probe"]["passed"]
    report["overall_passed"] = all(
        [
            offline_probe_pass is not False,
            bool(checks["cli_flow"].get("passed")),
            bool(checks["smoke_flow"].get("passed")),
            bool(checks["api_flow"].get("passed")),
        ]
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline validation runner for the M1 local-first runtime.")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH), help="Where to write the JSON validation report.")
    parser.add_argument("--api-port", type=int, default=8011, help="Port used for the temporary API validation server.")
    parser.add_argument(
        "--skip-offline-probe",
        action="store_true",
        help="Skip the outbound TCP probe. Useful only for a connected dry run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(args)
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nValidation report written to: {report_path.as_posix()}")


if __name__ == "__main__":
    main()
