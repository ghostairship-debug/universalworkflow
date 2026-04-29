from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from packages.contracts import TaskCard
from packages.contributions.games.cocos.e2e import build_cocos_project
from packages.contributions.games.cocos.playtest import playtest_cocos_build
from packages.contributions.pipelines.commercial_game_task_worker_cli import run_task_card_patch_via_workflowctl


def same_project_business_task_cards(task_cards: list[TaskCard]) -> list[TaskCard]:
    return [card for card in task_cards if str(card.execution_mode or "").strip() == "same_project_patch"]


def bootstrap_cocos_project_shell(
    *,
    project_dir: Path,
    source_path: Path,
    creator_exe: Path,
    asset_manifest: dict[str, Any] | None,
) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    for relative in [
        "assets/scripts",
        "assets/scene",
        "assets/resources/commercial_assets",
        "settings",
        "temp/workflow_task_card_worker",
    ]:
        (project_dir / relative).mkdir(parents=True, exist_ok=True)
    package_json = project_dir / "package.json"
    if not package_json.exists():
        package_json.write_text(
            json.dumps(
                {
                    "name": "workflow-commercial-game-project",
                    "uuid": "workflow-commercial-game-project",
                    "creator": {"version": "3.8.8"},
                    "dependencies": {},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    (project_dir / "workflow_project_source.json").write_text(
        json.dumps(
            {
                "schema_version": "commercial_game_same_project_bootstrap_v1",
                "source_path": source_path.resolve().as_posix(),
                "creator_exe": creator_exe.resolve().as_posix(),
                "asset_manifest_path": asset_manifest.get("manifest_path") if isinstance(asset_manifest, dict) else None,
                "bootstrap_mode": "empty_cocos_project_shell_for_task_card_patches",
                "forbidden_delivery_claim": "bootstrap_shell_is_not_commercial_game",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def execute_same_project_task_cards(
    *,
    root: Path,
    run_root: Path,
    project_dir: Path,
    pipeline_id: str,
    db_path: Path | None,
    task_cards: list[TaskCard],
    max_repair_attempts: int,
    task_card_runner: Callable[..., dict[str, Any]] | None,
) -> dict[str, Any]:
    ledger_root = run_root / "task_card_worker"
    card_root = ledger_root / "cards"
    card_root.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    if not task_cards:
        return _write_ledger(
            ledger_root,
            {
                "schema_version": "commercial_game_same_project_patch_ledger_v1",
                "pipeline_id": pipeline_id,
                "project_dir": project_dir.as_posix(),
                "same_project_worker_patch_go": False,
                "entries": [],
                "blockers": ["same_project_business_task_cards_missing"],
            },
        )
    runner = task_card_runner or run_task_card_patch_via_workflowctl
    for card in task_cards:
        materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=pipeline_id)
        card_path = card_root / f"{_safe_id(card.task_card_id)}.md"
        card_path.write_text(_task_card_markdown(card, materialized), encoding="utf-8")
        entry = runner(
            root=root,
            db_path=db_path,
            project_dir=project_dir,
            pipeline_id=pipeline_id,
            task_card=card,
            task_card_path=card_path,
            write_set=materialized["write_set"],
            read_set=materialized["read_set"],
            test_commands=materialized["test_commands"],
            max_fix_iterations=max_repair_attempts,
        )
        entries.append(_normalize_patch_ledger_entry(card, materialized, entry))
        if entries[-1]["status"] != "completed":
            break
    blockers = _patch_ledger_blockers(entries, expected_count=len(task_cards))
    return _write_ledger(
        ledger_root,
        {
            "schema_version": "commercial_game_same_project_patch_ledger_v1",
            "pipeline_id": pipeline_id,
            "project_dir": project_dir.as_posix(),
            "same_project_worker_patch_go": not blockers,
            "task_card_count": len(task_cards),
            "completed_count": sum(1 for entry in entries if entry["status"] == "completed"),
            "entries": entries,
            "blockers": blockers,
        },
    )


def collect_project_runtime_evidence(
    *,
    project_dir: Path,
    creator_exe: Path,
    require_build: bool,
    require_playtest: bool,
) -> dict[str, Any]:
    build: dict[str, Any] | None = None
    playtest: dict[str, Any] | None = None
    blockers: list[str] = []
    if require_build:
        build = build_cocos_project(project_path=project_dir, creator_exe=creator_exe)
        if not build.get("artifact_success"):
            blockers.append("cocos_build_no_artifact_success")
        build_output = build.get("build_output_path")
        if require_playtest and build_output:
            playtest = playtest_cocos_build(build_output_path=build_output, evidence_dir=project_dir / "playtest_evidence")
            if not playtest.get("playtest_go"):
                blockers.append("browser_playtest_no_go")
        elif require_playtest:
            blockers.append("browser_playtest_missing_build_output")
    feature_evidence = _load_project_feature_evidence(project_dir)
    return {
        "schema_version": "commercial_game_same_project_runtime_evidence_v1",
        "technical_smoke_go": project_dir.exists(),
        "production_scaffold_go": False,
        "commercial_playable_go": False,
        "commercial_playable_blockers": blockers,
        "commercial_feature_coverage": feature_evidence.get("commercial_feature_coverage", {}),
        "player_visible_checks": feature_evidence.get("player_visible_checks", {}),
        "manual_player_evidence": feature_evidence.get("manual_player_evidence", {}),
        "manifest_path": (project_dir / "workflow_project_manifest.json").as_posix(),
        "build": build,
        "playtest": playtest,
    }


def production_payload_from_worker(
    *,
    schema_version: str,
    created_at: str,
    pipeline_id: str,
    project_dir: Path,
    task_card_quality: dict[str, Any],
    runtime_evidence: dict[str, Any],
    assets_stage: dict[str, Any],
    ecosystem_evidence: dict[str, Any] | None,
    patch_ledger: dict[str, Any],
    skipped_task_cards: list[str],
    max_repair_attempts: int,
    dedupe_strings: Callable[[list[Any]], list[str]],
    blocker_details: Callable[[list[str]], list[dict[str, str]]],
    recoverable_suggestions: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    blockers = list(runtime_evidence.get("commercial_playable_blockers") or [])
    ecosystem_payload = dict(ecosystem_evidence or {})
    if assets_stage.get("placeholder_only"):
        blockers.append("placeholder_assets_only")
    if assets_stage and not assets_stage.get("commercial_assets_go"):
        blockers.extend(assets_stage.get("commercial_asset_blockers") or ["commercial_assets_no_go"])
    if not patch_ledger.get("same_project_worker_patch_go"):
        blockers.extend(patch_ledger.get("blockers") or ["same_project_worker_patch_missing"])
    if ecosystem_payload and ecosystem_payload.get("strict_required") and not ecosystem_payload.get("ecosystem_integration_go"):
        blockers.extend(ecosystem_payload.get("blockers") or ["cocos_ecosystem_bridge_missing"])
    blockers = dedupe_strings(blockers)
    commercial_playable_go = (
        bool(runtime_evidence.get("commercial_playable_go"))
        and bool(patch_ledger.get("same_project_worker_patch_go"))
        and not blockers
    )
    return {
        "schema_version": schema_version,
        "created_at": created_at,
        "pipeline_id": pipeline_id,
        "project_dir": project_dir.as_posix(),
        "persistent_project_per_run": True,
        "task_card_quality": task_card_quality,
        "task_card_count": int(task_card_quality.get("task_card_count") or 0),
        "technical_smoke_go": bool(runtime_evidence.get("technical_smoke_go")),
        "production_scaffold_go": bool(runtime_evidence.get("production_scaffold_go")),
        "commercial_playable_go": commercial_playable_go,
        "ecosystem_integration_go": bool(ecosystem_payload.get("ecosystem_integration_go")),
        "live_role_provider_proof_go": False,
        "same_project_worker_patch_go": bool(patch_ledger.get("same_project_worker_patch_go")),
        "human_player_review_go": False,
        "degradation_findings": [],
        "commercial_playable_blockers": blockers,
        "commercial_playable_blocker_details": blocker_details(blockers),
        "recoverable_suggestions": recoverable_suggestions(blockers),
        "commercial_feature_coverage": runtime_evidence.get("commercial_feature_coverage") or {},
        "player_visible_checks": runtime_evidence.get("player_visible_checks") or {},
        "manual_player_evidence": runtime_evidence.get("manual_player_evidence") or {},
        "same_project_patch_ledger": patch_ledger,
        "skipped_non_worker_task_cards": skipped_task_cards,
        "cocos_ecosystem_evidence": ecosystem_payload,
        "manifest_path": runtime_evidence.get("manifest_path"),
        "build": runtime_evidence.get("build"),
        "playtest": runtime_evidence.get("playtest"),
        "assets": assets_stage,
        "max_repair_attempts": max_repair_attempts,
        "repair_policy": "same_project_incremental_repair",
        "forbids_fixed_template": True,
    }


def _write_ledger(ledger_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    ledger_path = ledger_root / "same_project_patch_ledger.json"
    ledger_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["ledger_path"] = ledger_path.as_posix()
    return payload


def _materialize_task_card(card: TaskCard, *, project_dir: Path, pipeline_id: str) -> dict[str, list[str]]:
    return {
        "write_set": [_materialize_project_path(item, project_dir=project_dir, pipeline_id=pipeline_id) for item in card.write_set],
        "read_set": [_materialize_project_path(item, project_dir=project_dir, pipeline_id=pipeline_id) for item in card.read_set],
        "test_commands": [_materialize_project_path(item, project_dir=project_dir, pipeline_id=pipeline_id) for item in card.test_commands],
    }


def _materialize_project_path(value: str, *, project_dir: Path, pipeline_id: str) -> str:
    text = str(value)
    project = project_dir.as_posix()
    safe_pipeline = _safe_id(pipeline_id)
    return (
        text.replace("state/pipeline_runs/<run>/cocos_project", project)
        .replace("state\\pipeline_runs\\<run>\\cocos_project", project)
        .replace("<run>", safe_pipeline)
    )


def _task_card_markdown(card: TaskCard, materialized: dict[str, list[str]]) -> str:
    lines = [f"# {card.title}", "", f"task_card_id: `{card.task_card_id}`", "", "## Goal", "", card.goal or card.description, ""]
    for title, values in [
        ("Write Set", materialized["write_set"]),
        ("Read Set", materialized["read_set"]),
        ("Acceptance Criteria", card.acceptance_criteria),
        ("Evidence Requirements", card.evidence_requirements),
        ("Blocking Conditions", card.blocking_conditions),
        ("Model Guidance", card.model_guidance),
        ("Test Commands", materialized["test_commands"]),
    ]:
        lines.extend([f"## {title}", "", *[f"- {value}" for value in values], ""])
    return "\n".join(lines).rstrip() + "\n"


def _normalize_patch_ledger_entry(card: TaskCard, materialized: dict[str, list[str]], entry: dict[str, Any]) -> dict[str, Any]:
    mutation_result = entry.get("mutation_result") if isinstance(entry.get("mutation_result"), dict) else {}
    return {
        "task_card_id": card.task_card_id,
        "title": card.title,
        "status": str(entry.get("status") or "failed"),
        "failure_class": entry.get("failure_class"),
        "receipt_id": entry.get("receipt_id"),
        "child_run_id": entry.get("child_run_id"),
        "evidence_id": entry.get("evidence_id"),
        "review_decision": entry.get("review_decision"),
        "write_set": materialized["write_set"],
        "read_set": materialized["read_set"],
        "test_commands": materialized["test_commands"],
        "mutation_result": mutation_result,
        "changed_files": mutation_result.get("changed_files") or entry.get("changed_files") or [],
        "applied_patch_hash": mutation_result.get("applied_patch_hash") or entry.get("applied_patch_hash"),
        "stdout_preview": entry.get("stdout_preview"),
        "stderr_preview": entry.get("stderr_preview"),
        "watchdog": entry.get("watchdog") if isinstance(entry.get("watchdog"), dict) else {},
        "timeout_seconds": entry.get("timeout_seconds"),
        "idle_timeout_seconds": entry.get("idle_timeout_seconds"),
        "recoverable_suggestion": entry.get("recoverable_suggestion"),
    }


def _patch_ledger_blockers(entries: list[dict[str, Any]], *, expected_count: int) -> list[str]:
    blockers: list[str] = []
    if len(entries) < expected_count:
        blockers.append("same_project_task_card_patch_incomplete")
    if any(entry.get("status") != "completed" for entry in entries):
        blockers.append("same_project_task_card_patch_failed")
    if not entries:
        blockers.append("same_project_worker_patch_missing")
    return _dedupe_strings(blockers)


def _load_project_feature_evidence(project_dir: Path) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for path in [
        project_dir / "workflow_commercial_feature_evidence.json",
        project_dir / "player_visible_evidence" / "cocos_player_visible_evidence.json",
    ]:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        for key in ("commercial_feature_coverage", "feature_coverage", "player_visible_checks", "manual_player_evidence"):
            value = payload.get(key)
            if isinstance(value, dict):
                target_key = "commercial_feature_coverage" if key == "feature_coverage" else key
                merged.setdefault(target_key, {}).update(value)
    return merged


def _safe_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_") or "pipeline"


def _dedupe_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result
