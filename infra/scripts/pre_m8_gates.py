from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from infra.validation.doc_hygiene import check_living_doc_links
from infra.validation.source_package import export_source_package


def _run_command(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "passed": completed.returncode == 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the minimal pre-M8 hardening gates.")
    parser.add_argument("--report-path", default="state/pre_m8_gate_report.json")
    parser.add_argument(
        "--validation-report-path",
        default="state/offline_validation_report.json",
        help="Where the nested offline validation report should be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    report: dict[str, Any] = {
        "gates": {},
        "overall_passed": False,
    }

    report["gates"]["pytest"] = _run_command(["pytest", "-q"], repo_root)
    report["gates"]["offline_validation"] = _run_command(
        [
            sys.executable,
            "-m",
            "infra.scripts.offline_validation",
            "--skip-offline-probe",
            "--report-path",
            args.validation_report_path,
        ],
        repo_root,
    )
    report["gates"]["doc_links"] = check_living_doc_links(repo_root)
    report["gates"]["source_package"] = export_source_package(
        repo_root / "state" / "source_packages" / "pre_m8_source_package.zip",
        repo_root=repo_root,
        manifest_path=repo_root / "state" / "source_packages" / "pre_m8_source_package_manifest.json",
        dry_run=True,
    )

    report["overall_passed"] = all(
        [
            report["gates"]["pytest"]["passed"],
            report["gates"]["offline_validation"]["passed"],
            report["gates"]["doc_links"]["passed"],
            report["gates"]["source_package"]["passed"],
        ]
    )

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
