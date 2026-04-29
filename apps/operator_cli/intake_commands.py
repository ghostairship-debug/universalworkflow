from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json
from packages.core_domain.unified_project_brief import build_unified_project_brief

intake_app = typer.Typer(help="Input intake and unified project brief commands.")


@intake_app.command("package")
def intake_package(
    input_path: list[Path] = typer.Option(..., "--input", "-i", help="Input file or directory. Repeatable."),
    output_dir: Path = typer.Option(..., "--output-dir", help="Directory for normalized brief and agent packets."),
    title: Optional[str] = typer.Option(None, "--title", help="Human-readable brief title."),
    preserve_raw: bool = typer.Option(False, "--preserve-raw", help="Copy raw inputs into the output bundle."),
) -> None:
    payload = build_unified_project_brief(
        input_paths=input_path,
        output_dir=output_dir,
        title=title or "Unified Project Brief",
        preserve_raw=preserve_raw,
    )
    _emit_json(payload)
