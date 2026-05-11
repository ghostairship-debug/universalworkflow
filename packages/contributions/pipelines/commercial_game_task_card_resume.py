from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from packages.contracts import TaskCard
from packages.contributions.pipelines.commercial_game_task_worker import resume_same_project_task_card

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
    task_card = _task_card_from_markdown(
        task_card_path,
        pipeline_id=args.pipeline_id,
        task_card_ref=args.task_card_ref,
        adapter=args.adapter,
        execution_visibility_mode=args.execution_visibility_mode,
        write_set=list(args.write_set),
        read_set=list(args.read_set),
        test_commands=list(args.test_command),
    )
    result = resume_same_project_task_card(
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


def _task_card_from_markdown(
    path: Path,
    *,
    pipeline_id: str,
    task_card_ref: str,
    adapter: str,
    execution_visibility_mode: str | None,
    write_set: list[str],
    read_set: list[str],
    test_commands: list[str],
) -> TaskCard:
    title = _task_card_title(path)
    sections = _task_card_markdown_sections(path)
    goal_lines = _section_body_lines(sections, "Goal")
    goal = "\n".join(goal_lines).strip() or title
    evidence_requirements = _section_items(sections, "Evidence Requirements")
    expected_artifacts = _artifact_references(evidence_requirements)
    metadata = {
        "execution_visibility_mode": execution_visibility_mode,
        "human_visible_cli_required": execution_visibility_mode in VISIBLE_CLI_ENFORCED_MODES,
        "control_plane_visibility": "resident" if execution_visibility_mode in VISIBLE_CLI_ENFORCED_MODES else "headless",
        "provider_visibility": "direct_visible" if execution_visibility_mode in VISIBLE_CLI_ENFORCED_MODES else "headless",
    } if execution_visibility_mode else {}
    return TaskCard(
        run_id=pipeline_id,
        task_card_id=task_card_ref,
        title=title,
        description=goal,
        goal=goal,
        write_set=list(write_set),
        read_set=list(read_set),
        test_commands=list(test_commands),
        acceptance_criteria=_section_items(sections, "Acceptance Criteria") or ["resume same project task card"],
        expected_artifacts=expected_artifacts,
        evidence_requirements=evidence_requirements or ["operator receipt", "mutation result"],
        blocking_conditions=_section_items(sections, "Blocking Conditions")
        or ["provider idle timeout", "receipt issue failure"],
        model_guidance=_section_items(sections, "Model Guidance")
        or ["Resume the same task card and same project; do not create a new fixed template project."],
        execution_mode="same_project_patch",
        provider_lane=adapter,
        risk_level="high",
        exported_markdown_path=path.as_posix(),
        metadata=metadata,
    )


def _task_card_title(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip(" #")
            if stripped:
                return stripped[:240]
    except OSError:
        return path.stem
    return path.stem


def _task_card_markdown_sections(path: Path) -> dict[str, list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line.removeprefix("## ").strip()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def _section_body_lines(sections: dict[str, list[str]], name: str) -> list[str]:
    return [line.strip() for line in sections.get(name, []) if line.strip()]


def _section_items(sections: dict[str, list[str]], name: str) -> list[str]:
    items: list[str] = []
    for line in sections.get(name, []):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        items.append(stripped)
    return items


def _artifact_references(values: list[str]) -> list[str]:
    refs: list[str] = []
    for value in values:
        text = str(value).strip().strip("`")
        if not text:
            continue
        lowered = text.lower()
        if any(token in lowered for token in (".json", ".scene", ".prefab", ".png", ".jpg", ".mp3", ".wav")):
            refs.append(text)
            continue
        if "/" in text or "\\" in text:
            refs.append(text)
    return refs


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
