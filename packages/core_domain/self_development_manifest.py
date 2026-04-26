from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_SELF_DEVELOPMENT_MILESTONES = ["M67", "M68", "M69", "M70", "M71", "M72"]


def _execution_report_candidates(workspace_root: Path, milestone: str) -> list[Path]:
    filename = f"{milestone}_EXECUTION_REPORT.md"
    return [
        workspace_root / filename,
        workspace_root / "docs" / "archive" / "evaluations" / filename,
    ]


def _resolve_execution_report(workspace_root: Path, milestone: str) -> Path:
    candidates = _execution_report_candidates(workspace_root, milestone)
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _files_under(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.rglob("*") if item.is_file())


def _state_dirs_for_milestone(state_root: Path, milestone: str) -> list[Path]:
    prefix = milestone.lower()
    if not state_root.exists():
        return []
    return sorted(item for item in state_root.iterdir() if item.is_dir() and item.name.lower().startswith(prefix))


def _contains_single_card_exception(paths: list[Path]) -> bool:
    for path in paths:
        try:
            if "single_card_exception" in path.read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            continue
    return False


def _evidence_category(path: Path) -> str:
    name = path.name.lower()
    if "doc_links" in name:
        return "doc_links"
    if "test_matrix" in name or "pytest" in name:
        return "tests"
    if "validation" in name:
        return "validation"
    if "capability" in name or "probe" in name:
        return "capability_probe"
    if "plan_graph" in name:
        return "plan_graph"
    if "policy_preview" in name:
        return "policy_preview"
    if "goal_packet" in name:
        return "goal_packet"
    return "other"


def _evidence_category_counts(paths: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in paths:
        category = _evidence_category(path)
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _git_commits_for_milestones(workspace_root: Path, milestones: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--decorate=no", "-n", "80"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}", "commits": []}
    if result.returncode != 0:
        return {"available": False, "error": result.stderr.strip(), "commits": []}
    commits = []
    for line in result.stdout.splitlines():
        if any(milestone in line for milestone in milestones):
            commits.append(line)
    return {"available": True, "error": None, "commits": commits}


def _git_head_sha(workspace_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _file_sha256(path: Path) -> str | None:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _json_metadata(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        "run_id": payload.get("run_id") or (payload.get("run") or {}).get("run_id"),
        "evidence_id": payload.get("evidence_id") or (payload.get("evidence") or {}).get("evidence_id"),
        "status": payload.get("status") or (payload.get("run") or {}).get("status"),
        "test_result": payload.get("test_result") or payload.get("test_results"),
    }


def _provenance_trace_links(
    *,
    workspace_root: Path,
    task_cards: list[Path],
    evidence_files: list[Path],
    operator_packets: list[Path],
    commit_sha: str | None,
) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for path in task_cards:
        links.append(
            {
                "artifact_kind": "task_card",
                "path": _display_path(path, workspace_root),
                "sha256": _file_sha256(path),
                "commit_sha": commit_sha,
            }
        )
    for path in evidence_files:
        links.append(
            {
                "artifact_kind": "evidence",
                "path": _display_path(path, workspace_root),
                "sha256": _file_sha256(path),
                "commit_sha": commit_sha,
                **{key: value for key, value in _json_metadata(path).items() if value is not None},
            }
        )
    for path in operator_packets:
        links.append(
            {
                "artifact_kind": "operator_packet",
                "path": _display_path(path, workspace_root),
                "sha256": _file_sha256(path),
                "commit_sha": commit_sha,
                **{key: value for key, value in _json_metadata(path).items() if value is not None},
            }
        )
    return links


def _milestone_manifest(
    *,
    workspace_root: Path,
    state_root: Path,
    milestone: str,
    min_task_cards_per_phase: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report_path = _resolve_execution_report(workspace_root, milestone)
    state_dirs = _state_dirs_for_milestone(state_root, milestone)
    task_cards: list[Path] = []
    evidence_files: list[Path] = []
    operator_packets: list[Path] = []
    for state_dir in state_dirs:
        task_cards.extend(_files_under(state_dir / "task_cards"))
        evidence_files.extend(_files_under(state_dir / "evidence"))
        operator_packets.extend(_files_under(state_dir / "operator_packets"))

    single_card_exception = _contains_single_card_exception(task_cards)
    task_card_policy_passed = len(task_cards) >= min_task_cards_per_phase or single_card_exception
    issues: list[dict[str, Any]] = []
    if not report_path.exists():
        issues.append(
            {
                "milestone": milestone,
                "code": "missing_execution_report",
                "paths": [path.as_posix() for path in _execution_report_candidates(workspace_root, milestone)],
            }
        )
    if not state_dirs:
        issues.append({"milestone": milestone, "code": "missing_state_directory", "path": state_root.as_posix()})
    if not task_card_policy_passed:
        issues.append(
            {
                "milestone": milestone,
                "code": "task_card_policy_failed",
                "task_card_count": len(task_cards),
                "required": min_task_cards_per_phase,
            }
        )
    if not evidence_files:
        issues.append({"milestone": milestone, "code": "missing_evidence_files"})
    if not operator_packets:
        issues.append({"milestone": milestone, "code": "missing_operator_packet"})

    missing_links = []
    if not report_path.exists():
        missing_links.append("execution_report")
    if not state_dirs:
        missing_links.append("state_directories")
    if not task_cards:
        missing_links.append("task_cards")
    if not evidence_files:
        missing_links.append("evidence")
    if not operator_packets:
        missing_links.append("operator_packets")

    head_sha = _git_head_sha(workspace_root)
    milestone_payload = {
        "milestone": milestone,
        "execution_report": {
            "present": report_path.exists(),
            "path": _display_path(report_path, workspace_root),
            "lookup_paths": [
                _display_path(path, workspace_root) for path in _execution_report_candidates(workspace_root, milestone)
            ],
        },
        "state_directories": [_display_path(path, workspace_root) for path in state_dirs],
        "task_card_count": len(task_cards),
        "evidence_file_count": len(evidence_files),
        "operator_packet_count": len(operator_packets),
        "task_card_policy": {
            "status": "passed" if task_card_policy_passed else "failed",
            "min_task_cards_per_phase": min_task_cards_per_phase,
            "single_card_exception": single_card_exception,
        },
        "sample_evidence": [_display_path(path, workspace_root) for path in evidence_files[:8]],
        "provenance": {
            "schema_version": "m73_manifest_provenance_v2",
            "traceability_status": "complete" if not missing_links else "incomplete",
            "missing_links": missing_links,
            "commit_sha": head_sha,
            "execution_report_path": _display_path(report_path, workspace_root),
            "state_directory_paths": [_display_path(path, workspace_root) for path in state_dirs],
            "task_card_paths": [_display_path(path, workspace_root) for path in task_cards],
            "evidence_paths": [_display_path(path, workspace_root) for path in evidence_files],
            "operator_packet_paths": [_display_path(path, workspace_root) for path in operator_packets],
            "evidence_category_counts": _evidence_category_counts(evidence_files),
            "trace_links": _provenance_trace_links(
                workspace_root=workspace_root,
                task_cards=task_cards,
                evidence_files=evidence_files,
                operator_packets=operator_packets,
                commit_sha=head_sha,
            ),
        },
    }
    return milestone_payload, issues


def build_self_development_manifest(
    workspace_root: str | Path,
    *,
    milestones: list[str] | None = None,
    state_root: str | Path = "state",
    output_path: str | Path | None = None,
    min_task_cards_per_phase: int = 3,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    selected_milestones = list(milestones or DEFAULT_SELF_DEVELOPMENT_MILESTONES)
    resolved_state_root = Path(state_root)
    if not resolved_state_root.is_absolute():
        resolved_state_root = root / resolved_state_root

    milestone_payloads: list[dict[str, Any]] = []
    blocking_issues: list[dict[str, Any]] = []
    for milestone in selected_milestones:
        payload, issues = _milestone_manifest(
            workspace_root=root,
            state_root=resolved_state_root,
            milestone=milestone,
            min_task_cards_per_phase=min_task_cards_per_phase,
        )
        milestone_payloads.append(payload)
        blocking_issues.extend(issues)

    manifest = {
        "schema_version": "m72_self_development_manifest_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace_root": root.as_posix(),
        "state_root": resolved_state_root.as_posix(),
        "milestones": milestone_payloads,
        "task_card_mechanism": {
            "min_task_cards_per_phase": min_task_cards_per_phase,
            "rule": "Each milestone phase should have multiple task cards; single-card phases require a single_card_exception marker.",
        },
        "git": _git_commits_for_milestones(root, selected_milestones),
        "blocking_issue_count": len(blocking_issues),
        "blocking_issues": blocking_issues,
        "go_no_go": "GO" if not blocking_issues else "NO-GO",
    }
    if output_path is not None:
        resolved_output_path = Path(output_path)
        if not resolved_output_path.is_absolute():
            resolved_output_path = root / resolved_output_path
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["output_path"] = resolved_output_path.as_posix()
    return manifest
