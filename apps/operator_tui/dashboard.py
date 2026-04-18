from __future__ import annotations

from time import sleep
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from packages.core_domain.services import OrchestratorService


def _build_runs_table(snapshot: dict[str, Any]) -> Table:
    table = Table(title="Recent Runs", expand=True)
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Preset", style="magenta")
    table.add_column("Status")
    table.add_column("Review")
    table.add_column("Next")
    table.add_column("Adapter")
    table.add_column("Goal", overflow="fold")
    for run in snapshot["runs"]:
        status = Text(str(run["status"]))
        if run["run_id"] == snapshot["selected_run_id"]:
            status.stylize("bold green")
        table.add_row(
            run["run_id"],
            str(run["preset_id"]),
            status,
            str(run["effective_review_state"]),
            str(run["next_action"]),
            str(run["capability_adapter"] or "-"),
            str(run["goal"]),
        )
    if not snapshot["runs"]:
        table.add_row("-", "-", "no runs", "-", "-", "-", "create a run first")
    return table


def _build_focus_panel(snapshot: dict[str, Any]) -> Panel:
    detail = snapshot["focus_detail"]
    summary = snapshot["focus_summary"]
    if detail is None or summary is None:
        return Panel("No focused run.", title="Focus", border_style="yellow")

    run = detail["run"]
    lines = [
        f"run_id: {run['run_id']}",
        f"goal: {run['goal']}",
        f"status: {run['status']}",
        f"review_policy: {detail['review_policy']}",
        f"effective_review_state: {detail['effective_review_state']}",
        f"next_action: {detail['next_action']}",
        f"domain_pack: {detail['domain_pack']['domain_pack_id'] if detail['domain_pack'] else '-'}",
        f"adapter: {detail['capability_resolution']['adapter_name'] if detail['capability_resolution'] else '-'}",
        f"failure_reason: {detail['failure_reason'] or '-'}",
        f"waiting_reason: {detail['waiting_reason'] or '-'}",
        f"recoverability_hint: {detail['recoverability_hint']}",
        f"runtime_gateway: {detail['runtime_gateway']['provider']}",
        f"summary_category: {summary['failure_taxonomy']['category']}",
    ]
    state_payload = detail["last_runtime_state"]["state_payload"] if detail["last_runtime_state"] is not None else {}
    if state_payload.get("runtime_brief"):
        lines.append(f"runtime_brief: {state_payload['runtime_brief']}")
    return Panel("\n".join(lines), title="Focus", border_style="blue")


def _build_timeline_panel(snapshot: dict[str, Any]) -> Panel:
    table = Table(expand=True)
    table.add_column("Event", style="green")
    table.add_column("Summary")
    for event in snapshot["timeline_tail"]:
        table.add_row(str(event["event_type"]), str(event["summary"]))
    if not snapshot["timeline_tail"]:
        table.add_row("-", "no timeline yet")
    return Panel(table, title="Timeline Tail", border_style="magenta")


def render_dashboard(snapshot: dict[str, Any]) -> Group:
    gateway = snapshot["runtime_gateway"]
    header = Panel(
        "\n".join(
            [
                "Universal Agentic Workflow OS TUI",
                f"runtime_gateway={gateway['provider']} | live={gateway['live']} | model={gateway['model'] or '-'}",
                f"run_count={snapshot['run_count']} | selected_run={snapshot['selected_run_id'] or '-'}",
            ]
        ),
        border_style="green",
    )
    return Group(
        header,
        _build_runs_table(snapshot),
        _build_focus_panel(snapshot),
        _build_timeline_panel(snapshot),
    )


def run_dashboard(
    service: OrchestratorService,
    *,
    run_id: str | None = None,
    limit: int = 8,
    refresh_seconds: float = 2.0,
    once: bool = False,
    cycles: int | None = None,
    console: Console | None = None,
) -> None:
    active_console = console or Console()
    if once:
        active_console.print(render_dashboard(service.get_dashboard_snapshot(focus_run_id=run_id, limit=limit)))
        return

    remaining_cycles = cycles
    with Live(console=active_console, screen=True, auto_refresh=False) as live:
        try:
            while remaining_cycles is None or remaining_cycles > 0:
                live.update(render_dashboard(service.get_dashboard_snapshot(focus_run_id=run_id, limit=limit)), refresh=True)
                if remaining_cycles is not None:
                    remaining_cycles -= 1
                    if remaining_cycles <= 0:
                        break
                sleep(refresh_seconds)
        except KeyboardInterrupt:
            pass
