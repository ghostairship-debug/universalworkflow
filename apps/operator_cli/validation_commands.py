from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json, _workspace_root_from_context

validation_app = typer.Typer(help="Offline validation commands.")


@validation_app.command("run")
def validation_run(
    ctx: typer.Context,
    suite: str = typer.Option("full", "--suite", help="Validation suite: quick or full."),
    shard: Optional[str] = typer.Option(None, "--shard", help="Optional N/M shard selector."),
    report_path: Optional[str] = typer.Option(None, "--report-path", help="Where to write the JSON validation report."),
    api_port: int = typer.Option(8011, "--api-port", help="Port used for the temporary API validation server."),
    timeout_seconds: float = typer.Option(180.0, "--timeout-seconds", help="Per-flow timeout. Use 0 to disable."),
    skip_offline_probe: bool = typer.Option(False, "--skip-offline-probe", help="Skip outbound TCP isolation probe."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    workspace_root_text = workspace_root.as_posix()
    if workspace_root_text not in sys.path:
        sys.path.insert(0, workspace_root_text)
    from infra.validation.runner import build_report, write_report

    resolved_report_path = Path(report_path) if report_path is not None else workspace_root / "state" / "offline_validation_report.json"
    args = SimpleNamespace(
        report_path=str(resolved_report_path),
        api_port=api_port,
        suite=suite,
        shard=shard,
        timeout_seconds=timeout_seconds,
        skip_offline_probe=skip_offline_probe,
    )
    try:
        payload = build_report(args)
    except ValueError as exc:
        payload = {
            "generated_at": None,
            "project_root": workspace_root.as_posix(),
            "python_executable": None,
            "suite": suite,
            "shard": shard,
            "checks": {},
            "overall_passed": False,
            "error": str(exc),
        }
    payload["report_path"] = resolved_report_path.as_posix()
    write_report(payload, resolved_report_path)
    _emit_json(payload)
    if not payload.get("overall_passed"):
        raise typer.Exit(code=1)
