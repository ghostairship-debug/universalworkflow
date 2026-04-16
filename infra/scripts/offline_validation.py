from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
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
    reset_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "db", "reset"],
        env,
    )
    preset_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "preset", "list", "--json"],
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
    auto_status_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status", auto_run_id],
        env,
    )
    auto_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", auto_run_id],
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
    human_inspection_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "inspect", human_run_id],
        env,
    )
    human_resume_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", human_run_id],
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
    auto_timeline_events = [item["event_type"] for item in auto_timeline_payload]
    human_timeline_events = [item["event_type"] for item in human_timeline_payload]
    result.update(
        {
            "db_reset_seeded": reset_payload.get("seeded_presets", []),
            "preset_ids": [item["preset_id"] for item in preset_payload],
            "suggest_top_preset": suggest_payload[0]["preset_id"] if suggest_payload else None,
            "auto_run_status": auto_status_payload.get("status"),
            "auto_review_decision": auto_create_payload.get("review_decision"),
            "auto_failure_reason": auto_detail_payload.get("failure_reason"),
            "auto_last_runtime_step": auto_detail_payload.get("last_runtime_state", {}).get("graph_step"),
            "auto_inspection_passed": auto_inspection_payload.get("passed"),
            "auto_inspection_problem_count": auto_inspection_payload.get("problem_count"),
            "auto_timeline_events": auto_timeline_events,
            "human_compile_status": human_compile_payload["run"]["status"],
            "human_next_action": human_detail_payload.get("next_action"),
            "human_waiting_reason": human_detail_payload.get("waiting_reason"),
            "human_last_runtime_step": human_detail_payload.get("last_runtime_state", {}).get("graph_step"),
            "human_recoverability_hint": human_detail_payload.get("recoverability_hint"),
            "human_inspection_passed": human_inspection_payload.get("passed"),
            "human_inspection_problem_count": human_inspection_payload.get("problem_count"),
            "human_resume_status": human_resume_payload["run"]["status"],
            "human_approve_status": human_approve_payload["run"]["status"],
            "human_handoffs_count": len(human_handoffs_payload),
            "human_timeline_events": human_timeline_events,
            "artifact_ref_fields": list(artifact_refs[0].keys()) if artifact_refs else [],
            "artifact_paths_exist": artifact_paths_exist,
            "cancel_status": cancel_status_payload.get("status"),
        }
    )
    result["passed"] = all(
        [
            result["db_reset_seeded"] == ["feature_delivery", "research_spike"],
            set(result["preset_ids"]) == {"feature_delivery", "research_spike"},
            result["suggest_top_preset"] == "research_spike",
            result["auto_run_status"] == "completed",
            result["auto_review_decision"] == "pass",
            result["auto_failure_reason"] is None,
            result["auto_last_runtime_step"] == "completed",
            result["auto_inspection_passed"] is True,
            result["auto_inspection_problem_count"] == 0,
            result["auto_timeline_events"] == AUTO_TIMELINE,
            result["human_compile_status"] == "prepared",
            result["human_next_action"] == "resume",
            result["human_waiting_reason"] == "awaiting_runtime_resume",
            result["human_last_runtime_step"] == "compiled",
            result["human_recoverability_hint"] == "resume_run",
            result["human_inspection_passed"] is True,
            result["human_inspection_problem_count"] == 0,
            result["human_resume_status"] == "awaiting_review",
            result["human_approve_status"] == "completed",
            result["human_handoffs_count"] == 1,
            result["human_timeline_events"] == HUMAN_TIMELINE,
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
        and payload.get("auto_run", {}).get("status") == "completed"
        and payload.get("human_run", {}).get("status") == "completed"
        and payload.get("auto_run", {}).get("timeline_events") == AUTO_TIMELINE
        and payload.get("human_run", {}).get("timeline_events") == HUMAN_TIMELINE,
        **payload,
    }


def validate_api_flow(env: dict[str, str], db_path: Path, port: int) -> dict[str, Any]:
    result: dict[str, Any] = {"passed": False}
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

        auto_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API validation", "preset_id": "feature_delivery"})
        auto_run_id = auto_run["run_id"]
        auto_compile = http_post_json(f"{base_url}/runs/{auto_run_id}/compile")
        auto_detail = http_get_json(f"{base_url}/runs/{auto_run_id}/status-detail")
        auto_inspection = http_get_json(f"{base_url}/runs/{auto_run_id}/inspection")
        auto_handoffs = http_get_json(f"{base_url}/runs/{auto_run_id}/handoffs")
        auto_resume = http_post_json(f"{base_url}/runs/{auto_run_id}/resume")
        auto_timeline = http_get_json(f"{base_url}/runs/{auto_run_id}/timeline")

        human_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API human validation", "preset_id": "research_spike"})
        human_run_id = human_run["run_id"]
        http_post_json(f"{base_url}/runs/{human_run_id}/compile")
        human_detail = http_get_json(f"{base_url}/runs/{human_run_id}/status-detail")
        human_inspection = http_get_json(f"{base_url}/runs/{human_run_id}/inspection")
        human_resume = http_post_json(f"{base_url}/runs/{human_run_id}/resume")
        human_approve = http_post_json(f"{base_url}/runs/{human_run_id}/approve")
        human_timeline = http_get_json(f"{base_url}/runs/{human_run_id}/timeline")

        auto_timeline_events = [item["event_type"] for item in auto_timeline]
        human_timeline_events = [item["event_type"] for item in human_timeline]
        result.update(
            {
                "preset_ids": [item["preset_id"] for item in presets],
                "auto_run_status": auto_resume["run"]["status"],
                "auto_compile_status": auto_compile["run"]["status"],
                "auto_next_action": auto_detail["next_action"],
                "auto_waiting_reason": auto_detail["waiting_reason"],
                "auto_last_runtime_step": auto_detail["last_runtime_state"]["graph_step"],
                "auto_inspection_passed": auto_inspection["passed"],
                "auto_inspection_problem_count": auto_inspection["problem_count"],
                "auto_handoffs_count": len(auto_handoffs),
                "auto_timeline_events": auto_timeline_events,
                "human_waiting_reason": human_detail["waiting_reason"],
                "human_last_runtime_step": human_detail["last_runtime_state"]["graph_step"],
                "human_recoverability_hint": human_detail["recoverability_hint"],
                "human_inspection_passed": human_inspection["passed"],
                "human_inspection_problem_count": human_inspection["problem_count"],
                "human_resume_status": human_resume["run"]["status"],
                "human_approve_status": human_approve["run"]["status"],
                "human_timeline_events": human_timeline_events,
            }
        )
        result["passed"] = all(
            [
                set(result["preset_ids"]) == {"feature_delivery", "research_spike"},
                result["auto_compile_status"] == "prepared",
                result["auto_next_action"] == "resume",
                result["auto_waiting_reason"] == "awaiting_runtime_resume",
                result["auto_last_runtime_step"] == "compiled",
                result["auto_inspection_passed"] is True,
                result["auto_inspection_problem_count"] == 0,
                result["auto_handoffs_count"] == 1,
                result["auto_run_status"] == "completed",
                result["auto_timeline_events"] == AUTO_TIMELINE,
                result["human_waiting_reason"] == "awaiting_runtime_resume",
                result["human_last_runtime_step"] == "compiled",
                result["human_recoverability_hint"] == "resume_run",
                result["human_inspection_passed"] is True,
                result["human_inspection_problem_count"] == 0,
                result["human_resume_status"] == "awaiting_review",
                result["human_approve_status"] == "completed",
                result["human_timeline_events"] == HUMAN_TIMELINE,
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
