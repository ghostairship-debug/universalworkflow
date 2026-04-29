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
    "MINIMAX_API_KEY",
    "MINIMAX_TOKEN",
    "MINIMAX_BASE_URL",
    "MINIMAX_API_HOST",
    "WORKFLOW_MINIMAX_MODEL",
}


def review_policy_debt_linkage_is_current(debt_id: str | None) -> bool:
    return debt_id in {None, "TD-006"}


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


def run_command(command: list[str], env: dict[str, str], *, timeout_seconds: float = 120.0) -> CommandResult:
    trace_path = env.get("WORKFLOW_OFFLINE_VALIDATION_TRACE")
    trace_event_id = f"{int(time.time() * 1000)}-{os.getpid()}"
    _append_command_trace(
        trace_path,
        {
            "event": "command_started",
            "event_id": trace_event_id,
            "command": command,
            "started_at": utc_now_iso(),
            "timeout_seconds": timeout_seconds,
        },
    )
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _append_command_trace(
            trace_path,
            {
                "event": "command_timeout",
                "event_id": trace_event_id,
                "command": command,
                "finished_at": utc_now_iso(),
                "returncode": 124,
            },
        )
        return CommandResult(
            command=command,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=f"{exc.stderr or ''}\ncommand timed out after {timeout_seconds}s".strip(),
        )
    _append_command_trace(
        trace_path,
        {
            "event": "command_finished",
            "event_id": trace_event_id,
            "command": command,
            "finished_at": utc_now_iso(),
            "returncode": completed.returncode,
        },
    )
    return CommandResult(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def _append_command_trace(trace_path: str | None, event: dict[str, Any]) -> None:
    if not trace_path:
        return
    path = Path(trace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


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


def http_get_json(url: str, timeout: float = 30.0) -> Any:
    body = _http_open("GET", url, timeout=timeout)
    return json.loads(body)


def http_get_text(url: str, timeout: float = 30.0) -> str:
    return _http_open("GET", url, timeout=timeout)


def http_post_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 30.0) -> Any:
    headers = {"Content-Type": "application/json"}
    receipt_action = _operator_action_for_post(url, payload)
    if receipt_action is not None:
        parsed = urllib.parse.urlparse(url)
        receipt_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/operator-action-receipts", "", "", ""))
        receipt = http_post_json(
            receipt_url,
            {
                "action_type": receipt_action,
                "risk_level": "high",
                "scope_payload": _operator_action_scope_for_post(url, payload),
                "metadata": {"source": "offline_validation"},
            },
            timeout=timeout,
        )
        headers["X-Operator-Action-Receipt"] = receipt["receipt_id"]
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    return json.loads(_http_open("POST", url, request=request, timeout=timeout))


def _http_open(
    method: str,
    url: str,
    *,
    request: urllib.request.Request | None = None,
    timeout: float,
) -> str:
    trace_path = os.getenv("WORKFLOW_OFFLINE_VALIDATION_TRACE")
    trace_event_id = f"{int(time.time() * 1000)}-{os.getpid()}-{method.lower()}"
    started = time.monotonic()
    _append_command_trace(
        trace_path,
        {
            "event": "http_started",
            "event_id": trace_event_id,
            "method": method,
            "url": url,
            "started_at": utc_now_iso(),
            "timeout_seconds": timeout,
        },
    )
    try:
        target = request if request is not None else url
        with urllib.request.urlopen(target, timeout=timeout) as response:  # noqa: S310
            text = response.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        failure_class = _http_failure_class(exc)
        _append_command_trace(
            trace_path,
            {
                "event": "http_failed",
                "event_id": trace_event_id,
                "method": method,
                "url": url,
                "finished_at": utc_now_iso(),
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "failure_class": failure_class,
                "error": str(exc),
            },
        )
        raise RuntimeError(
            f"validation_http_{method.lower()}_failed "
            f"failure_class={failure_class} timeout_seconds={timeout} url={url}: {exc}"
        ) from exc
    _append_command_trace(
        trace_path,
        {
            "event": "http_finished",
            "event_id": trace_event_id,
            "method": method,
            "url": url,
            "finished_at": utc_now_iso(),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "response_chars": len(text),
        },
    )
    return text


def _http_failure_class(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "validation_http_timeout"
    reason = getattr(exc, "reason", None)
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "validation_http_timeout"
    return "validation_http_error"


def _operator_action_for_post(url: str, payload: dict[str, Any] | None = None) -> str | None:
    path = urllib.parse.urlparse(url).path.rstrip("/")
    if path == "/operator-action-receipts":
        return None
    if path == "/runs/batch-resume":
        return "batch_resume_runs"
    if path.endswith("/resume") and path.startswith("/runs/"):
        return "resume_run"
    if path.endswith("/approve") and path.startswith("/runs/"):
        return "approve_run"
    if path.endswith("/reject") and path.startswith("/runs/"):
        return "reject_run"
    if path.endswith("/cancel") and path.startswith("/runs/"):
        return "cancel_run"
    if path.endswith("/reconcile") and path.startswith("/runs/") and payload and payload.get("apply"):
        return "reconcile_apply"
    if "/interaction/sessions/" in path and path.endswith("/launch") and payload and payload.get("execute"):
        return "launch_execute"
    return None


def _operator_action_scope_for_post(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.rstrip("/")
    payload = payload or {}
    parts = [item for item in path.split("/") if item]
    if path == "/runs/batch-resume":
        return {"run_ids": payload.get("run_ids", []), "max_workers": payload.get("max_workers")}
    if len(parts) >= 3 and parts[0] == "runs":
        run_id = parts[1]
        action = parts[2]
        if action in {"resume", "approve", "reject", "cancel"}:
            return {"run_id": run_id}
        if action == "reconcile" and payload.get("apply"):
            return {"run_id": run_id, "apply": True, "action": payload.get("action")}
    if path == "/runs/launch" and payload.get("execute"):
        return {"goal": payload.get("goal"), "preset_id": payload.get("preset_id"), "execute": True}
    if len(parts) >= 4 and parts[0] == "interaction" and parts[1] == "sessions" and parts[3] == "launch":
        return {
            "session_id": parts[2],
            "execute": True,
            "selected_preset_id": payload.get("selected_preset_id"),
            "selected_cluster_template_ids": payload.get("selected_cluster_template_ids", []),
        }
    return {}


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
