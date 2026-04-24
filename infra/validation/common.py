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
from contextlib import closing
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
    with closing(sqlite3.connect(db_path)) as connection:
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
    with closing(sqlite3.connect(db_path)) as connection:
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


def http_get_json(url: str, timeout: float = 10.0) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def http_get_text(url: str, timeout: float = 10.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        return response.read().decode("utf-8")


def http_post_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 10.0) -> Any:
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
