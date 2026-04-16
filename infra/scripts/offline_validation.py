from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = PROJECT_ROOT / "state" / "offline_validation_report.json"
EXPECTED_FULL_TIMELINE = [
    "run_created",
    "preset_selected",
    "phase_created",
    "runtime_task_created",
    "runtime_task_started",
    "runtime_task_completed",
    "evidence_submitted",
    "review_submitted",
    "run_completed",
]
EXPECTED_API_CREATE_TIMELINE = [
    "run_created",
    "preset_selected",
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
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_json_command(command: list[str], env: dict[str, str]) -> tuple[dict[str, Any] | list[Any], CommandResult]:
    result = run_command(command, env)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    try:
        return json.loads(result.stdout), result
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"command did not return valid JSON: {' '.join(command)}\nstdout:\n{result.stdout}"
        ) from exc


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


def http_post_json(url: str, payload: dict[str, Any], timeout: float = 3.0) -> Any:
    body = json.dumps(payload).encode("utf-8")
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
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "preset",
            "list",
            "--json",
        ],
        env,
    )
    create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation run",
            "--preset",
            "feature_delivery",
            "--prepare",
            "--execute",
        ],
        env,
    )
    run_id = create_payload["run"]["run_id"]
    runtime_task_id = create_payload["prepared_task_id"]
    status_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status", run_id],
        env,
    )
    timeline_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "timeline",
            run_id,
            "--json",
        ],
        env,
    )
    evidence_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "task",
            "evidence",
            runtime_task_id,
        ],
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
    _, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "cancel", cancel_run_id],
        env,
    )
    cancel_status_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "status",
            cancel_run_id,
        ],
        env,
    )

    artifact_refs = evidence_payload.get("artifact_refs", [])
    artifact_paths_exist = all(Path(item["path"]).exists() for item in artifact_refs)
    timeline_events = [item["event_type"] for item in timeline_payload]
    result.update(
        {
            "db_reset_seeded": reset_payload.get("seeded_presets", []),
            "preset_ids": [item["preset_id"] for item in preset_payload],
            "run_id": run_id,
            "runtime_task_id": runtime_task_id,
            "run_status": status_payload.get("status"),
            "review_decision": create_payload.get("review_decision"),
            "timeline_events": timeline_events,
            "evidence_return_code": evidence_payload.get("return_code"),
            "evidence_known_gaps": evidence_payload.get("known_gaps", []),
            "artifact_ref_fields": list(artifact_refs[0].keys()) if artifact_refs else [],
            "artifact_paths_exist": artifact_paths_exist,
            "cancel_status": cancel_status_payload.get("status"),
        }
    )
    result["passed"] = all(
        [
            result["db_reset_seeded"] == ["feature_delivery", "research_spike"],
            set(result["preset_ids"]) == {"feature_delivery", "research_spike"},
            result["run_status"] == "completed",
            result["review_decision"] == "pass",
            result["timeline_events"] == EXPECTED_FULL_TIMELINE,
            result["evidence_return_code"] == 0,
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
        and payload.get("timeline_events") == EXPECTED_FULL_TIMELINE,
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
        run = http_post_json(
            f"{base_url}/runs",
            {"goal": "Offline API validation", "preset_id": "feature_delivery"},
        )
        run_info = http_get_json(f"{base_url}/runs/{run['run_id']}")
        timeline = http_get_json(f"{base_url}/runs/{run['run_id']}/timeline")
        timeline_events = [item["event_type"] for item in timeline]
        result.update(
            {
                "preset_ids": [item["preset_id"] for item in presets],
                "run_id": run["run_id"],
                "run_status": run_info["status"],
                "timeline_events": timeline_events,
            }
        )
        result["passed"] = all(
            [
                set(result["preset_ids"]) == {"feature_delivery", "research_spike"},
                result["run_status"] == "pending",
                result["timeline_events"] == EXPECTED_API_CREATE_TIMELINE,
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
    parser = argparse.ArgumentParser(description="Offline validation runner for the M0 bootstrap.")
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT_PATH),
        help="Where to write the JSON validation report.",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=8011,
        help="Port used for the temporary API validation server.",
    )
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
