from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from packages.contracts import TaskCard
from packages.contributions.pipelines.commercial_game_task_worker_cli import run_task_card_patch_via_workflowctl

VISIBLE_CLI_ENFORCED_MODES = {"human_visible_cli_enforced", "resident_control_plane_provider_visible_enforced"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resume one commercial game same-project task card with a fresh receipt.")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--pipeline-id", required=True)
    parser.add_argument("--task-card-path", required=True)
    parser.add_argument("--task-card-ref", required=True)
    parser.add_argument("--adapter", default="codex")
    parser.add_argument("--execution-visibility-mode", default=None)
    parser.add_argument("--max-fix-iterations", type=int, default=3)
    parser.add_argument("--write-set", action="append", default=[])
    parser.add_argument("--read-set", action="append", default=[])
    parser.add_argument("--test-command", action="append", default=[])
    args = parser.parse_args(argv)

    task_card_path = Path(args.task_card_path)
    task_card = TaskCard(
        run_id=args.pipeline_id,
        task_card_id=args.task_card_ref,
        title=_task_card_title(task_card_path),
        description=_task_card_title(task_card_path),
        goal=_task_card_title(task_card_path),
        write_set=list(args.write_set),
        read_set=list(args.read_set),
        test_commands=list(args.test_command),
        acceptance_criteria=["resume same project task card", "fresh receipt issued"],
        evidence_requirements=["operator receipt", "mutation result"],
        blocking_conditions=["provider idle timeout", "receipt issue failure"],
        model_guidance=["Resume the same task card and same project; do not create a new fixed template project."],
        execution_mode="same_project_patch",
        provider_lane=args.adapter,
        risk_level="high",
        metadata={
            "execution_visibility_mode": args.execution_visibility_mode,
            "human_visible_cli_required": args.execution_visibility_mode in VISIBLE_CLI_ENFORCED_MODES,
            "control_plane_visibility": "resident"
            if args.execution_visibility_mode in VISIBLE_CLI_ENFORCED_MODES
            else "headless",
            "provider_visibility": "direct_visible"
            if args.execution_visibility_mode in VISIBLE_CLI_ENFORCED_MODES
            else "headless",
        }
        if args.execution_visibility_mode
        else {},
    )
    result = run_task_card_patch_via_workflowctl(
        root=Path(args.workspace_root),
        db_path=Path(args.db_path),
        project_dir=Path(args.project_dir),
        pipeline_id=args.pipeline_id,
        task_card=task_card,
        task_card_path=task_card_path,
        write_set=list(args.write_set),
        read_set=list(args.read_set),
        test_commands=list(args.test_command),
        max_fix_iterations=args.max_fix_iterations,
        adapter_name=args.adapter,
        execution_visibility_mode=args.execution_visibility_mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "completed" else 1


def _task_card_title(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip(" #")
            if stripped:
                return stripped[:240]
    except OSError:
        return path.stem
    return path.stem


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
