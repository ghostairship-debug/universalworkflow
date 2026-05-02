from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from packages.worker_adapters.subprocess_support import (
    TIMEOUT_EXIT_CODE,
    completed_process_watchdog_metadata,
    run_subprocess_with_tree_timeout,
)


ISSUE_RECEIPT_IDLE_TIMEOUT_SECONDS = 60
TASK_CARD_WALL_TIMEOUT_SECONDS = 900
TASK_CARD_IDLE_TIMEOUT_SECONDS = 240
TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS = 480
TASK_CARD_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS = 720
TASK_CARD_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS = 900
TASK_CARD_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS = 1
TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS = 1800
PREVIEW_LIMIT = 2000


def run_task_card_patch_via_workflowctl(
    *,
    root: Path,
    db_path: Path | None,
    project_dir: Path,
    pipeline_id: str,
    task_card: Any,
    task_card_path: Path,
    write_set: list[str],
    read_set: list[str],
    test_commands: list[str],
    max_fix_iterations: int,
    adapter_name: str | None = None,
) -> dict[str, Any]:
    resolved_adapter = _resolve_task_card_adapter(task_card, adapter_name)
    if db_path is None:
        return {
            "status": "blocked",
            "failure_class": "db_path_required_for_task_card_worker",
            "recoverable_suggestion": "Rerun commercial_game_production with --db-path so task-card worker can issue receipts.",
        }
    base = [
        sys.executable,
        "-m",
        "apps.operator_cli.main",
        "--db-path",
        str(db_path),
        "--workspace-root",
        str(root),
    ]
    issue_cmd = [
        *base,
        "run",
        "issue-receipt",
        "--action-type",
        "launch_execute",
        "--goal",
        _task_card_goal(task_card_path),
        "--preset",
        "feature_delivery",
        "--adapter",
        resolved_adapter,
        "--task-card-ref",
        task_card.task_card_id,
        "--task-card-path",
        task_card_path.as_posix(),
        "--mutation-mode",
        "patch_apply",
        "--max-fix-iterations",
        str(max_fix_iterations),
        "--ttl-seconds",
        "7200",
    ]
    for item in write_set:
        issue_cmd.extend(["--write-set", item])
    for item in read_set:
        issue_cmd.extend(["--read-set", item])
    for item in test_commands:
        issue_cmd.extend(["--test-command", item])
    receipt = _run_json_command(
        issue_cmd,
        cwd=root,
        timeout_seconds=120,
        idle_timeout_seconds=ISSUE_RECEIPT_IDLE_TIMEOUT_SECONDS,
    )
    if receipt["status"] != "completed":
        return {
            **receipt,
            "failure_class": receipt.get("failure_class") or "task_card_receipt_issue_failed",
            "project_dir": project_dir.as_posix(),
            "pipeline_id": pipeline_id,
        }
    receipt_id = receipt["payload"].get("receipt_id")
    run_cmd = [
        *base,
        "run",
        "from-task-card",
        task_card_path.as_posix(),
        "--preset",
        "feature_delivery",
        "--adapter",
        resolved_adapter,
        "--task-card-ref",
        task_card.task_card_id,
        "--max-fix-iterations",
        str(max_fix_iterations),
        "--execute",
        "--operator-receipt-id",
        str(receipt_id),
    ]
    for item in write_set:
        run_cmd.extend(["--write-set", item])
    for item in read_set:
        run_cmd.extend(["--read-set", item])
    for item in test_commands:
        run_cmd.extend(["--test-command", item])
    provider_idle_budget_seconds = max(TASK_CARD_IDLE_TIMEOUT_SECONDS, TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS)
    executed = _run_json_command(
        run_cmd,
        cwd=root,
        timeout_seconds=TASK_CARD_WALL_TIMEOUT_SECONDS,
        idle_timeout_seconds=TASK_CARD_IDLE_TIMEOUT_SECONDS,
        provider_output_idle_timeout_seconds=TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS,
        material_progress_idle_timeout_seconds=TASK_CARD_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS,
        adaptive_wall_timeout_extension_seconds=TASK_CARD_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS,
        adaptive_wall_timeout_max_extensions=TASK_CARD_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS,
        adaptive_wall_timeout_absolute_max_seconds=TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS,
        adaptive_wall_timeout_progress_window_seconds=TASK_CARD_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS,
        db_path=db_path,
        task_goal=_task_card_goal(task_card_path),
        receipt_id=str(receipt_id),
        env_overrides={
            "WORKFLOW_CODEX_TIMEOUT_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS),
            "WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS": str(provider_idle_budget_seconds),
            "WORKFLOW_OPENCODE_TIMEOUT_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS),
            "WORKFLOW_OPENCODE_IDLE_TIMEOUT_SECONDS": str(provider_idle_budget_seconds),
            "WORKFLOW_PROVIDER_TIMEOUT_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS),
            "WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS": str(provider_idle_budget_seconds),
            "WORKFLOW_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS": str(TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS),
            "WORKFLOW_PROVIDER_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS": str(TASK_CARD_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS),
            "WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_INITIAL_SECONDS": str(TASK_CARD_WALL_TIMEOUT_SECONDS),
            "WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS),
            "WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS),
            "WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS),
        },
    )
    payload = executed.get("payload") if isinstance(executed.get("payload"), dict) else {}
    mutation_result = _mutation_result_from_payload(payload)
    implementation_status = _implementation_status_from_payload(
        executed=executed,
        payload=payload,
        mutation_result=mutation_result,
    )
    summary = payload.get("pr_ready_summary") if isinstance(payload, dict) and isinstance(payload.get("pr_ready_summary"), dict) else {}
    changed_files = _changed_files_from_summary(mutation_result=mutation_result, summary=summary)
    tests_status = _summary_tests_status(summary, mutation_result)
    return {
        "status": implementation_status["status"],
        "failure_class": implementation_status["failure_class"],
        "requested_adapter": resolved_adapter,
        "receipt_id": receipt_id,
        "child_run_id": _child_run_id_from_execution(executed, payload),
        "child_attempt_id": _child_attempt_id_from_execution(executed),
        "child_workflow_state": executed.get("child_workflow_state") if isinstance(executed.get("child_workflow_state"), dict) else None,
        "worker_adapter": _worker_adapter_from_execution(executed, payload),
        "watchdog_source": executed.get("watchdog_source"),
        "evidence_id": payload.get("evidence_id") if isinstance(payload, dict) else None,
        "review_decision": payload.get("review_decision") if isinstance(payload, dict) else None,
        "implementation_readiness": implementation_status.get("readiness"),
        "mutation_result": mutation_result,
        "changed_files": changed_files,
        "final_test_status": tests_status,
        "stdout_preview": executed.get("stdout_preview"),
        "stderr_preview": executed.get("stderr_preview"),
        "watchdog": executed.get("watchdog"),
        "timeout_seconds": executed.get("timeout_seconds"),
        "idle_timeout_seconds": executed.get("idle_timeout_seconds"),
        "recoverable_suggestion": executed.get("recoverable_suggestion"),
        "command": run_cmd,
    }


def _resolve_task_card_adapter(task_card: Any, adapter_name: str | None) -> str:
    raw = adapter_name or getattr(task_card, "provider_lane", None) or "codex"
    normalized = str(raw or "codex").strip().lower()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    if normalized in {"codex_cli", "codex_cli_login"}:
        return "codex"
    if normalized == "opencode_cli":
        return "opencode"
    if normalized in {"shell", "noop", "dry_run"}:
        return "codex"
    return normalized or "codex"


def _run_json_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    idle_timeout_seconds: int,
    provider_output_idle_timeout_seconds: int | None = None,
    material_progress_idle_timeout_seconds: int | None = None,
    adaptive_wall_timeout_extension_seconds: int | None = None,
    adaptive_wall_timeout_max_extensions: int | None = None,
    adaptive_wall_timeout_absolute_max_seconds: int | None = None,
    adaptive_wall_timeout_progress_window_seconds: int | None = None,
    db_path: Path | None = None,
    task_goal: str | None = None,
    receipt_id: str | None = None,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    run_kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "capture_output": True,
        "text": True,
        "timeout": timeout_seconds,
        "idle_timeout": idle_timeout_seconds,
        "check": False,
    }
    if provider_output_idle_timeout_seconds is not None:
        run_kwargs["provider_output_idle_timeout"] = provider_output_idle_timeout_seconds
    if material_progress_idle_timeout_seconds is not None:
        run_kwargs["material_progress_idle_timeout"] = material_progress_idle_timeout_seconds
    if (
        adaptive_wall_timeout_extension_seconds is not None
        and _runner_supports_kwarg(run_subprocess_with_tree_timeout, "adaptive_wall_timeout_extension")
    ):
        run_kwargs["adaptive_wall_timeout_extension"] = adaptive_wall_timeout_extension_seconds
        run_kwargs["adaptive_wall_timeout_max_extensions"] = adaptive_wall_timeout_max_extensions or 0
        if adaptive_wall_timeout_absolute_max_seconds is not None:
            run_kwargs["adaptive_wall_timeout_absolute_max"] = adaptive_wall_timeout_absolute_max_seconds
        if adaptive_wall_timeout_progress_window_seconds is not None:
            run_kwargs["adaptive_wall_timeout_progress_window"] = adaptive_wall_timeout_progress_window_seconds
        run_kwargs["adaptive_wall_timeout_requires_material_progress"] = True
    if (
        db_path is not None
        and task_goal
        and (provider_output_idle_timeout_seconds is not None or material_progress_idle_timeout_seconds is not None)
        and _runner_supports_kwarg(run_subprocess_with_tree_timeout, "activity_probe")
    ):
        run_kwargs["activity_probe"] = _child_provider_activity_probe(
            db_path=db_path,
            task_goal=task_goal,
            receipt_id=receipt_id,
        )
        run_kwargs["activity_probe_interval"] = 1.0
    if env_overrides:
        run_kwargs["env"] = {**os.environ, **{str(key): str(value) for key, value in env_overrides.items()}}
    proc = run_subprocess_with_tree_timeout(command, **run_kwargs)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    payload = _parse_json_from_stdout(stdout)
    watchdog = completed_process_watchdog_metadata(proc)
    common = {
        "return_code": proc.returncode,
        "stdout_preview": stdout[-PREVIEW_LIMIT:],
        "stderr_preview": stderr[-PREVIEW_LIMIT:],
        "watchdog": watchdog,
        "timeout_seconds": timeout_seconds,
        "idle_timeout_seconds": idle_timeout_seconds,
        "provider_output_idle_timeout_seconds": provider_output_idle_timeout_seconds,
        "material_progress_idle_timeout_seconds": material_progress_idle_timeout_seconds,
        "adaptive_wall_timeout_extension_seconds": adaptive_wall_timeout_extension_seconds,
        "adaptive_wall_timeout_max_extensions": adaptive_wall_timeout_max_extensions,
        "adaptive_wall_timeout_absolute_max_seconds": adaptive_wall_timeout_absolute_max_seconds,
        "adaptive_wall_timeout_progress_window_seconds": adaptive_wall_timeout_progress_window_seconds,
    }
    if proc.returncode != 0:
        child_state = (
            _inspect_child_workflow_state(db_path=db_path, task_goal=task_goal, receipt_id=receipt_id)
            if db_path is not None and task_goal
            else {}
        )
        failure_class = _classify_child_failure(
            payload=payload,
            proc=proc,
            watchdog=watchdog,
            child_state=child_state,
            idle_timeout_seconds=idle_timeout_seconds,
        )
        if child_state.get("run_id") and _child_was_terminated_by_wrapper(watchdog):
            _close_child_workflow(
                db_path=db_path,
                child_state=child_state,
                failure_class=failure_class,
                receipt_id=receipt_id,
                command=command,
            )
            for nested_state in child_state.get("nested_child_states") or []:
                if isinstance(nested_state, dict) and str(nested_state.get("run_status") or "") not in {
                    "completed",
                    "failed",
                    "blocked",
                    "cancelled",
                }:
                    _close_child_workflow(
                        db_path=db_path,
                        child_state=nested_state,
                        failure_class=failure_class,
                        receipt_id=receipt_id,
                        command=command,
                    )
        return {
            **common,
            "status": "failed",
            "failure_class": failure_class,
            "payload": payload,
            "child_workflow_state": child_state,
            "child_run_id": child_state.get("run_id"),
            "child_attempt_id": child_state.get("attempt_id"),
            "watchdog_source": "db_runtime_state" if child_state else "process_stream",
            "recoverable_suggestion": _recoverable_suggestion_for_failure(failure_class, watchdog),
        }
    if not isinstance(payload, dict):
        return {
            **common,
            "status": "failed",
            "failure_class": "workflowctl_child_json_parse_failed",
        }
    return {
        **common,
        "status": "completed",
        "payload": payload,
        "child_run_id": payload.get("run", {}).get("run_id") if isinstance(payload, dict) else None,
        "watchdog_source": "workflowctl_payload",
    }


def _task_card_goal(task_card_path: Path) -> str:
    text = task_card_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip(" #")
        if stripped:
            return stripped[:240]
    return task_card_path.stem


def _runner_supports_kwarg(func: Any, name: str) -> bool:
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return True
    return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()) or name in signature.parameters


def _parse_json_from_stdout(stdout: str) -> dict[str, Any] | list[Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _failure_class_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or error.get("failure_class") or "") or None
    result = payload.get("result")
    if isinstance(result, dict):
        return str(result.get("failure_class") or "") or None
    return str(payload.get("failure_class") or "") or None


def _child_provider_activity_probe(
    *,
    db_path: Path,
    task_goal: str,
    receipt_id: str | None,
):
    cached: dict[str, Any] = {
        "provider_output_event_count": 0,
        "material_progress_event_count": 0,
    }
    last_probe_at = 0.0

    def _probe() -> dict[str, Any]:
        nonlocal cached, last_probe_at
        now = time.monotonic()
        if now - last_probe_at < 1.0:
            return cached
        last_probe_at = now
        child_state = _inspect_child_workflow_state(
            db_path=db_path,
            task_goal=task_goal,
            receipt_id=receipt_id,
        )
        run_ids = []
        if child_state.get("run_id"):
            run_ids.append(str(child_state["run_id"]))
        for nested in child_state.get("nested_child_states") or []:
            if isinstance(nested, dict) and nested.get("run_id"):
                run_ids.append(str(nested["run_id"]))
        if not run_ids:
            return cached
        try:
            with sqlite3.connect(db_path) as connection:
                connection.row_factory = sqlite3.Row
                placeholders = ",".join("?" for _ in run_ids)
                rows = connection.execute(
                    f"""
                    SELECT created_at, payload_json
                    FROM run_events
                    WHERE event_type = 'provider_stream_observed'
                      AND run_id IN ({placeholders})
                    ORDER BY created_at
                    """,
                    tuple(run_ids),
                ).fetchall()
        except sqlite3.Error:
            return cached
        provider_events: list[sqlite3.Row] = []
        material_events: list[sqlite3.Row] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                payload = {}
            if payload.get("classification") != "control":
                provider_events.append(row)
            if payload.get("is_material_progress"):
                material_events.append(row)
        cached = {
            "provider_output_event_count": len(provider_events),
            "material_progress_event_count": len(material_events),
            "last_provider_output_at": provider_events[-1]["created_at"] if provider_events else None,
            "last_material_progress_at": material_events[-1]["created_at"] if material_events else None,
        }
        return cached

    return _probe


def _failure_class_from_watchdog(proc: Any, watchdog: dict[str, Any]) -> str:
    failure_class = str(watchdog.get("timeout_failure_class") or "")
    if failure_class:
        return failure_class
    if int(getattr(proc, "returncode", 1)) == TIMEOUT_EXIT_CODE:
        return "workflowctl_child_timeout"
    return "workflowctl_child_failed"


def _classify_child_failure(
    *,
    payload: Any,
    proc: Any,
    watchdog: dict[str, Any],
    child_state: dict[str, Any],
    idle_timeout_seconds: int,
) -> str:
    payload_failure = _failure_class_from_payload(payload)
    if payload_failure:
        if payload_failure in {
            "provider_output_idle_timeout",
            "provider_no_material_progress_timeout",
        }:
            return payload_failure
        if payload_failure in {"provider_timeout", "provider_idle_timeout", "provider_wall_timeout"}:
            return "provider_timeout"
        return payload_failure
    timeout_type = str(watchdog.get("timeout_type") or "")
    if timeout_type in {"provider_output_idle_timeout", "provider_no_material_progress_timeout"}:
        return timeout_type
    if timeout_type == "adaptive_wall_timeout_exhausted":
        return "task_scope_too_large_after_adaptive_wall_timeout"
    if timeout_type == "idle_timeout" and child_state:
        heartbeat_age = child_state.get("heartbeat_age_seconds")
        if isinstance(heartbeat_age, (int, float)) and heartbeat_age <= max(idle_timeout_seconds * 1.5, idle_timeout_seconds + 30):
            return "child_stdout_silent"
        return "workflow_child_stalled"
    if timeout_type in {"idle_timeout", "wall_timeout"}:
        return "provider_timeout" if timeout_type == "wall_timeout" else _failure_class_from_watchdog(proc, watchdog)
    return _failure_class_from_watchdog(proc, watchdog)


def _child_was_terminated_by_wrapper(watchdog: dict[str, Any]) -> bool:
    return str(watchdog.get("timeout_type") or "") in {
        "idle_timeout",
        "wall_timeout",
        "adaptive_wall_timeout_exhausted",
        "provider_output_idle_timeout",
        "provider_no_material_progress_timeout",
    }


def _inspect_child_workflow_state(
    *,
    db_path: Path | None,
    task_goal: str | None,
    receipt_id: str | None,
) -> dict[str, Any]:
    if db_path is None or not task_goal:
        return {}
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            receipt = (
                connection.execute(
                    "SELECT created_at, consumed_at FROM operator_action_receipts WHERE receipt_id = ?",
                    (receipt_id,),
                ).fetchone()
                if receipt_id
                else None
            )
            lower_bound = receipt["created_at"] if receipt is not None else None
            if lower_bound:
                run = connection.execute(
                    """
                    SELECT run_id, status, created_at, updated_at
                    FROM runs
                    WHERE goal = ? AND created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (task_goal, lower_bound),
                ).fetchone()
            else:
                run = connection.execute(
                    """
                    SELECT run_id, status, created_at, updated_at
                    FROM runs
                    WHERE goal = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (task_goal,),
                ).fetchone()
            if run is None:
                return {}
            state = _workflow_state_for_run(connection, run)
            nested_rows = connection.execute(
                """
                SELECT run_id, status, created_at, updated_at
                FROM runs
                WHERE run_id <> ?
                  AND created_at >= ?
                  AND goal LIKE ?
                ORDER BY created_at
                """,
                (run["run_id"], run["created_at"], f"%{task_goal}%"),
            ).fetchall()
            nested_states = [_workflow_state_for_run(connection, nested) for nested in nested_rows]
    except sqlite3.Error as exc:
        return {"inspection_error": str(exc)}
    state["nested_child_states"] = nested_states
    return state


def _workflow_state_for_run(connection: sqlite3.Connection, run: sqlite3.Row) -> dict[str, Any]:
    run_id = run["run_id"]
    attempt = connection.execute(
        """
        SELECT attempt_id, runtime_task_id, status, created_at, closed_at, close_reason
        FROM runtime_attempts
        WHERE run_id = ?
        ORDER BY sequence_no DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    lease = connection.execute(
        """
        SELECT lease_id, adapter_name, status, heartbeat_at, lease_expires_at, released_at, release_reason
        FROM worker_leases
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    event = connection.execute(
        """
        SELECT created_at
        FROM run_events
        WHERE run_id = ? AND event_type = 'worker_heartbeat_received'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    provider_rows = connection.execute(
        """
        SELECT created_at, payload_json
        FROM run_events
        WHERE run_id = ? AND event_type = 'provider_stream_observed'
        ORDER BY created_at
        """,
        (run_id,),
    ).fetchall()
    provider_events: list[sqlite3.Row] = []
    material_events: list[sqlite3.Row] = []
    for provider_row in provider_rows:
        try:
            payload = json.loads(provider_row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            payload = {}
        if payload.get("classification") != "control":
            provider_events.append(provider_row)
        if payload.get("is_material_progress"):
            material_events.append(provider_row)
    heartbeat_at = lease["heartbeat_at"] if lease is not None else event["created_at"] if event is not None else None
    return {
        "run_id": run_id,
        "run_status": run["status"],
        "run_created_at": run["created_at"],
        "run_updated_at": run["updated_at"],
        "attempt_id": attempt["attempt_id"] if attempt is not None else None,
        "runtime_task_id": attempt["runtime_task_id"] if attempt is not None else None,
        "attempt_status": attempt["status"] if attempt is not None else None,
        "worker_lease_id": lease["lease_id"] if lease is not None else None,
        "worker_lease_status": lease["status"] if lease is not None else None,
        "worker_adapter": lease["adapter_name"] if lease is not None else None,
        "worker_heartbeat_at": heartbeat_at,
        "heartbeat_age_seconds": _age_seconds(heartbeat_at),
        "provider_output_event_count": len(provider_events),
        "material_progress_event_count": len(material_events),
        "last_provider_output_at": provider_events[-1]["created_at"] if provider_events else None,
        "last_material_progress_at": material_events[-1]["created_at"] if material_events else None,
    }


def _close_child_workflow(
    *,
    db_path: Path | None,
    child_state: dict[str, Any],
    failure_class: str,
    receipt_id: str | None,
    command: list[str],
) -> None:
    if db_path is None or not child_state.get("run_id"):
        return
    now = datetime.now(UTC).isoformat()
    run_id = str(child_state["run_id"])
    runtime_task_id = str(child_state.get("runtime_task_id") or "")
    attempt_id = str(child_state.get("attempt_id") or "")
    lease_id = str(child_state.get("worker_lease_id") or "")
    payload = {
        "failure_class": failure_class,
        "receipt_id": receipt_id,
        "attempt_id": attempt_id or None,
        "worker_lease_id": lease_id or None,
        "command": command,
        "closed_by": "commercial_game_task_worker_cli",
        "reason": "outer_watchdog_terminated_child_workflow",
    }
    try:
        with sqlite3.connect(db_path) as connection:
            has_runtime_tasks = _sqlite_table_exists(connection, "runtime_tasks")
            has_runtime_claims = _sqlite_table_exists(connection, "runtime_claims")
            has_scheduler_lease_decisions = _sqlite_table_exists(connection, "scheduler_lease_decisions")
            has_scheduler_committed_leases = _sqlite_table_exists(connection, "scheduler_committed_leases")
            connection.execute(
                "UPDATE runs SET status = 'failed', updated_at = ? WHERE run_id = ? AND status NOT IN ('completed', 'failed', 'blocked')",
                (now, run_id),
            )
            if attempt_id:
                connection.execute(
                    """
                    UPDATE runtime_attempts
                    SET status = 'closed', closed_at = ?, close_reason = ?
                    WHERE attempt_id = ? AND status = 'current'
                    """,
                    (now, failure_class, attempt_id),
                )
            if runtime_task_id and has_runtime_tasks:
                connection.execute(
                    """
                    UPDATE runtime_tasks
                    SET status = 'failed'
                    WHERE runtime_task_id = ? AND status NOT IN ('completed', 'failed', 'cancelled')
                    """,
                    (runtime_task_id,),
                )
            if lease_id:
                connection.execute(
                    """
                    UPDATE worker_leases
                    SET status = 'released', released_at = ?, release_reason = ?
                    WHERE lease_id = ? AND status NOT IN ('released', 'expired')
                    """,
                    (now, failure_class, lease_id),
                )
            if runtime_task_id and has_runtime_claims:
                connection.execute(
                    """
                    UPDATE runtime_claims
                    SET status = 'released', released_at = ?, release_reason = ?
                    WHERE runtime_task_id = ? AND status = 'active'
                    """,
                    (now, failure_class, runtime_task_id),
                )
            if runtime_task_id and has_scheduler_lease_decisions:
                connection.execute(
                    """
                    UPDATE scheduler_lease_decisions
                    SET released_at = ?, release_reason = ?
                    WHERE runtime_task_id = ? AND released_at IS NULL
                    """,
                    (now, failure_class, runtime_task_id),
                )
            if runtime_task_id and has_scheduler_committed_leases:
                connection.execute(
                    """
                    UPDATE scheduler_committed_leases
                    SET status = 'released', released_at = ?, release_reason = ?
                    WHERE runtime_task_id = ? AND status = 'active'
                    """,
                    (now, failure_class, runtime_task_id),
                )
            connection.execute(
                """
                INSERT INTO run_events (
                  event_id, run_id, event_type, object_type, object_id, summary,
                  payload_json, schema_version, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"event_{uuid4().hex[:12]}",
                    run_id,
                    "watchdog_terminated_without_child_closure",
                    "runtime_task",
                    runtime_task_id or run_id,
                    "Outer task-card watchdog closed a child workflow after termination",
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    "v1",
                    now,
                ),
            )
            connection.commit()
    except sqlite3.Error:
        return


def _sqlite_table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )


def _age_seconds(timestamp: str | None) -> float | None:
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0.0, (datetime.now(UTC) - parsed.astimezone(UTC)).total_seconds())


def _child_run_id_from_execution(executed: dict[str, Any], payload: Any) -> str | None:
    if isinstance(executed.get("child_run_id"), str):
        return executed["child_run_id"]
    if isinstance(payload, dict):
        run_payload = payload.get("run")
        if isinstance(run_payload, dict):
            return run_payload.get("run_id")
    state = executed.get("child_workflow_state")
    if isinstance(state, dict):
        return state.get("run_id")
    return None


def _child_attempt_id_from_execution(executed: dict[str, Any]) -> str | None:
    if isinstance(executed.get("child_attempt_id"), str):
        return executed["child_attempt_id"]
    state = executed.get("child_workflow_state")
    if isinstance(state, dict):
        return state.get("attempt_id")
    return None


def _worker_adapter_from_execution(executed: dict[str, Any], payload: Any) -> str | None:
    state = executed.get("child_workflow_state")
    if isinstance(state, dict) and isinstance(state.get("worker_adapter"), str):
        return state["worker_adapter"]
    if isinstance(payload, dict) and isinstance(payload.get("capability_adapter"), str):
        return payload["capability_adapter"]
    return None


def _recoverable_suggestion_for_failure(failure_class: str, watchdog: dict[str, Any]) -> str:
    if failure_class == "provider_output_idle_timeout":
        return "resume_with_fresh_receipt_after_provider_output_idle_restart"
    if failure_class == "provider_no_material_progress_timeout":
        return "resume_with_fresh_receipt_or_split_task_after_no_material_progress"
    if failure_class == "child_stdout_silent":
        return "resume_with_fresh_receipt_without_treating_db_active_child_as_provider_timeout"
    if failure_class == "workflow_child_stalled":
        return "resume_from_next_incomplete_task_card_after_closed_child_run"
    if failure_class == "provider_timeout":
        return "verify_provider_live_proof_or_switch_to_verified_provider_then_resume_with_fresh_receipt"
    if failure_class == "task_scope_too_large_after_adaptive_wall_timeout":
        return "split_or_narrow_task_after_adaptive_wall_timeout_exhausted"
    return str(watchdog.get("recovery_suggestion") or "Inspect child workflow stdout/stderr and rerun the task card.")


def _mutation_result_from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("pr_ready_summary")
    if isinstance(summary, dict) and isinstance(summary.get("mutation_result"), dict):
        return summary["mutation_result"]
    orchestration = payload.get("orchestration")
    if isinstance(orchestration, dict):
        role_progress = orchestration.get("role_progress")
        if isinstance(role_progress, dict):
            coder = role_progress.get("coder")
            if isinstance(coder, dict):
                mutation_report = coder.get("mutation_report")
                if isinstance(mutation_report, dict) and isinstance(mutation_report.get("mutation_result"), dict):
                    return mutation_report["mutation_result"]
    run_payload = payload.get("run")
    if isinstance(run_payload, dict) and isinstance(run_payload.get("mutation_result"), dict):
        return run_payload["mutation_result"]
    return {}


def _implementation_status_from_payload(
    *,
    executed: dict[str, Any],
    payload: Any,
    mutation_result: dict[str, Any],
) -> dict[str, str | None]:
    if executed.get("status") != "completed":
        return {
            "status": "failed",
            "failure_class": str(executed.get("failure_class") or "task_card_patch_failed"),
            "readiness": None,
        }
    summary = payload.get("pr_ready_summary") if isinstance(payload, dict) and isinstance(payload.get("pr_ready_summary"), dict) else {}
    readiness = str(summary.get("readiness") or "")
    review_decision = str(payload.get("review_decision") or _summary_review_decision(summary) or "")
    changed_files = _changed_files_from_summary(mutation_result=mutation_result, summary=summary)
    tests_status = _summary_tests_status(summary, mutation_result)
    if tests_status == "patch_generation_failed":
        return {"status": "failed", "failure_class": "provider_execution_failed", "readiness": readiness or None}
    if tests_status == "patch_parse_failed":
        return {"status": "failed", "failure_class": "same_project_patch_parse_failed", "readiness": readiness or None}
    if tests_status == "patch_apply_failed":
        return {"status": "failed", "failure_class": "same_project_patch_apply_failed", "readiness": readiness or None}
    if readiness and readiness != "ready":
        if review_decision == "fail":
            return {"status": "failed", "failure_class": "same_project_patch_review_failed", "readiness": readiness}
        if not changed_files:
            return {"status": "failed", "failure_class": "same_project_patch_no_changed_files", "readiness": readiness}
        if tests_status not in {"passed"}:
            return {"status": "failed", "failure_class": "same_project_patch_tests_not_passed", "readiness": readiness}
        return {"status": "completed", "failure_class": None, "readiness": "ready_via_orchestration_coder"}
    if not changed_files:
        return {"status": "failed", "failure_class": "same_project_patch_no_changed_files", "readiness": readiness or None}
    if review_decision == "fail":
        return {"status": "failed", "failure_class": "same_project_patch_review_failed", "readiness": readiness or None}
    if tests_status and tests_status not in {"passed"}:
        return {"status": "failed", "failure_class": "same_project_patch_tests_not_passed", "readiness": readiness or None}
    return {"status": "completed", "failure_class": None, "readiness": readiness or "ready"}


def _changed_files_from_summary(*, mutation_result: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    changed_files = mutation_result.get("changed_files")
    if isinstance(changed_files, list):
        return [str(item) for item in changed_files if str(item)]
    bounded_patch = summary.get("bounded_patch") if isinstance(summary.get("bounded_patch"), dict) else {}
    summary_changed = bounded_patch.get("changed_files")
    if isinstance(summary_changed, list):
        return [str(item) for item in summary_changed if str(item)]
    return []


def _summary_review_decision(summary: dict[str, Any]) -> str | None:
    review = summary.get("review") if isinstance(summary.get("review"), dict) else {}
    value = review.get("latest_review_decision")
    return str(value) if value is not None else None


def _summary_tests_status(summary: dict[str, Any], mutation_result: dict[str, Any]) -> str | None:
    tests = summary.get("tests") if isinstance(summary.get("tests"), dict) else {}
    if mutation_result.get("final_test_status") is not None:
        return str(mutation_result.get("final_test_status"))
    if tests.get("status") is not None:
        return str(tests.get("status"))
    return None
