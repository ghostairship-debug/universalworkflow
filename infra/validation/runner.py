from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from infra.validation.api_flow import validate_api_flow
from infra.validation.cli_flow import validate_cli_flow
from infra.validation.common import DEFAULT_REPORT_PATH, PROJECT_ROOT, sanitized_env, tcp_probe, utc_now_iso
from infra.validation.smoke_flow import validate_smoke_flow


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
