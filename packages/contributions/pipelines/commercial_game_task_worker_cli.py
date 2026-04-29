from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from packages.worker_adapters.subprocess_support import (
    TIMEOUT_EXIT_CODE,
    completed_process_watchdog_metadata,
    run_subprocess_with_tree_timeout,
)


ISSUE_RECEIPT_IDLE_TIMEOUT_SECONDS = 60
TASK_CARD_IDLE_TIMEOUT_SECONDS = 240
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
) -> dict[str, Any]:
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
        "project_delivery",
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
        "project_delivery",
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
    executed = _run_json_command(
        run_cmd,
        cwd=root,
        timeout_seconds=900,
        idle_timeout_seconds=TASK_CARD_IDLE_TIMEOUT_SECONDS,
    )
    payload = executed.get("payload") if isinstance(executed.get("payload"), dict) else {}
    return {
        "status": "completed" if executed["status"] == "completed" else "failed",
        "failure_class": None if executed["status"] == "completed" else executed.get("failure_class") or "task_card_patch_failed",
        "receipt_id": receipt_id,
        "child_run_id": payload.get("run", {}).get("run_id") if isinstance(payload, dict) else None,
        "evidence_id": payload.get("evidence_id") if isinstance(payload, dict) else None,
        "review_decision": payload.get("review_decision") if isinstance(payload, dict) else None,
        "mutation_result": _mutation_result_from_payload(payload),
        "stdout_preview": executed.get("stdout_preview"),
        "stderr_preview": executed.get("stderr_preview"),
        "watchdog": executed.get("watchdog"),
        "timeout_seconds": executed.get("timeout_seconds"),
        "idle_timeout_seconds": executed.get("idle_timeout_seconds"),
        "recoverable_suggestion": executed.get("recoverable_suggestion"),
        "command": run_cmd,
    }


def _run_json_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    idle_timeout_seconds: int,
) -> dict[str, Any]:
    proc = run_subprocess_with_tree_timeout(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        idle_timeout=idle_timeout_seconds,
        check=False,
    )
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
    }
    if proc.returncode != 0:
        return {
            **common,
            "status": "failed",
            "failure_class": _failure_class_from_payload(payload) or _failure_class_from_watchdog(proc, watchdog),
            "payload": payload,
            "recoverable_suggestion": _recoverable_suggestion_from_watchdog(watchdog),
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
    }


def _task_card_goal(task_card_path: Path) -> str:
    text = task_card_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip(" #")
        if stripped:
            return stripped[:240]
    return task_card_path.stem


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


def _failure_class_from_watchdog(proc: Any, watchdog: dict[str, Any]) -> str:
    failure_class = str(watchdog.get("timeout_failure_class") or "")
    if failure_class:
        return failure_class
    if int(getattr(proc, "returncode", 1)) == TIMEOUT_EXIT_CODE:
        return "workflowctl_child_timeout"
    return "workflowctl_child_failed"


def _recoverable_suggestion_from_watchdog(watchdog: dict[str, Any]) -> str:
    return str(watchdog.get("recovery_suggestion") or "Inspect child workflow stdout/stderr and rerun the task card.")


def _mutation_result_from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("pr_ready_summary")
    if isinstance(summary, dict) and isinstance(summary.get("mutation_result"), dict):
        return summary["mutation_result"]
    run_payload = payload.get("run")
    if isinstance(run_payload, dict) and isinstance(run_payload.get("mutation_result"), dict):
        return run_payload["mutation_result"]
    return {}
