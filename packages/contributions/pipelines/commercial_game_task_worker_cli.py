from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import inspect
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from packages.worker_adapters.subprocess_support import (
    TIMEOUT_EXIT_CODE,
    completed_process_watchdog_metadata,
    run_subprocess_with_tree_timeout,
)
from packages.runtime_security.safe_command_runner import SafeCommandSpec, run_safe_commands


ISSUE_RECEIPT_IDLE_TIMEOUT_SECONDS = 60
TASK_CARD_WALL_TIMEOUT_SECONDS = 900
TASK_CARD_IDLE_TIMEOUT_SECONDS = 240
TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS = 900
TASK_CARD_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS = 720
TASK_CARD_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS = 900
TASK_CARD_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS = 1
TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS = 1800
PREVIEW_LIMIT = 2000
HUMAN_VISIBLE_CLI_MODE = "human_visible_cli_enforced"
RESIDENT_CONTROL_PLANE_PROVIDER_VISIBLE_MODE = "resident_control_plane_provider_visible_enforced"
VISIBLE_CLI_ENFORCED_MODES = {HUMAN_VISIBLE_CLI_MODE, RESIDENT_CONTROL_PLANE_PROVIDER_VISIBLE_MODE}


def _provider_direct_visible_required(*, execution_visibility_mode: str | None, adapter_name: str | None) -> bool:
    mode = str(execution_visibility_mode or "").strip()
    adapter = str(adapter_name or "").strip().lower()
    return mode in VISIBLE_CLI_ENFORCED_MODES and adapter in {"codex", "opencode"}


def run_task_card_patch_via_workflowctl(
    *,
    root: Path,
    db_path: Path | None,
    project_dir: Path,
    pipeline_id: str,
    task_card: Any,
    task_card_path: Path,
    write_set: list[str],
    read_set: list[str],
    test_commands: list[str],
    max_fix_iterations: int,
    adapter_name: str | None = None,
    execution_visibility_mode: str | None = None,
) -> dict[str, Any]:
    resolved_adapter = _resolve_task_card_adapter(task_card, adapter_name)
    if db_path is None:
        return {
            "status": "blocked",
            "failure_class": "db_path_required_for_task_card_worker",
            "recoverable_suggestion": "Rerun commercial_game_production with --db-path so task-card worker can issue receipts.",
        }
    base = [
        sys.executable,
        "-m",
        "apps.operator_cli.main",
        "--db-path",
        str(db_path),
        "--workspace-root",
        str(root),
    ]
    issue_cmd = [
        *base,
        "run",
        "issue-receipt",
        "--action-type",
        "launch_execute",
        "--goal",
        _task_card_goal(task_card_path),
        "--preset",
        "feature_delivery",
        "--adapter",
        resolved_adapter,
        "--task-card-ref",
        task_card.task_card_id,
        "--task-card-path",
        task_card_path.as_posix(),
        "--mutation-mode",
        "patch_apply",
        "--max-fix-iterations",
        str(max_fix_iterations),
        "--ttl-seconds",
        "7200",
    ]
    for item in write_set:
        issue_cmd.extend(["--write-set", _literal_cli_arg(item)])
    for item in read_set:
        issue_cmd.extend(["--read-set", _literal_cli_arg(item)])
    for item in test_commands:
        issue_cmd.extend(["--test-command", item])
    receipt = _run_json_command(
        issue_cmd,
        cwd=root,
        timeout_seconds=120,
        idle_timeout_seconds=ISSUE_RECEIPT_IDLE_TIMEOUT_SECONDS,
    )
    if receipt["status"] != "completed":
        return {
            **receipt,
            "failure_class": receipt.get("failure_class") or "task_card_receipt_issue_failed",
            "project_dir": project_dir.as_posix(),
            "pipeline_id": pipeline_id,
        }
    receipt_id = receipt["payload"].get("receipt_id")
    run_cmd = [
        *base,
        "run",
        "from-task-card",
        task_card_path.as_posix(),
        "--preset",
        "feature_delivery",
        "--adapter",
        resolved_adapter,
        "--task-card-ref",
        task_card.task_card_id,
        "--max-fix-iterations",
        str(max_fix_iterations),
        "--execute",
        "--operator-receipt-id",
        str(receipt_id),
    ]
    for item in write_set:
        run_cmd.extend(["--write-set", _literal_cli_arg(item)])
    for item in read_set:
        run_cmd.extend(["--read-set", _literal_cli_arg(item)])
    for item in test_commands:
        run_cmd.extend(["--test-command", item])
    provider_idle_budget_seconds = max(TASK_CARD_IDLE_TIMEOUT_SECONDS, TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS)
    visible_session_dir = task_card_path.parent / "visible_cli_sessions" / _safe_name(task_card.task_card_id)
    env_overrides = {
        "WORKFLOW_CODEX_TIMEOUT_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS),
        "WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS": str(provider_idle_budget_seconds),
        "WORKFLOW_OPENCODE_TIMEOUT_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS),
        "WORKFLOW_OPENCODE_IDLE_TIMEOUT_SECONDS": str(provider_idle_budget_seconds),
        "WORKFLOW_PROVIDER_TIMEOUT_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS),
        "WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS": str(provider_idle_budget_seconds),
        "WORKFLOW_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS": str(TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS),
        "WORKFLOW_PROVIDER_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS": str(TASK_CARD_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS),
        "WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_INITIAL_SECONDS": str(TASK_CARD_WALL_TIMEOUT_SECONDS),
        "WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS),
        "WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS),
        "WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS": str(TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS),
        "WORKFLOW_MUTATION_EXTERNAL_ROOTS": json.dumps([project_dir.resolve().as_posix()], ensure_ascii=False),
    }
    provider_visible_cli_required = _provider_direct_visible_required(
        execution_visibility_mode=execution_visibility_mode,
        adapter_name=resolved_adapter,
    )
    if provider_visible_cli_required:
        env_overrides.update(
            {
                "WORKFLOW_CONTROL_PLANE_VISIBILITY": "resident",
                "WORKFLOW_PROVIDER_VISIBILITY": "direct_visible",
                "WORKFLOW_PROVIDER_DIRECT_VISIBLE_CLI": "1",
                "WORKFLOW_PROVIDER_VISIBLE_CLI_REQUIRED": "1",
                "WORKFLOW_PROVIDER_VISIBLE_SESSION_ROOT": (visible_session_dir / "provider_subprocesses").as_posix(),
                "WORKFLOW_PROVIDER_VISIBLE_PARENT_TASK_CARD_ID": task_card.task_card_id,
                "WORKFLOW_PROVIDER_VISIBLE_PARENT_RECEIPT_ID": str(receipt_id),
            }
        )
    material_progress_idle_timeout = None if provider_visible_cli_required else TASK_CARD_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS
    adaptive_progress_window = (
        TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS
        if provider_visible_cli_required
        else TASK_CARD_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS
    )
    executed = _run_json_command(
        run_cmd,
        cwd=root,
        timeout_seconds=TASK_CARD_WALL_TIMEOUT_SECONDS,
        idle_timeout_seconds=TASK_CARD_IDLE_TIMEOUT_SECONDS,
        provider_output_idle_timeout_seconds=TASK_CARD_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS,
        material_progress_idle_timeout_seconds=material_progress_idle_timeout,
        adaptive_wall_timeout_extension_seconds=TASK_CARD_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS,
        adaptive_wall_timeout_max_extensions=TASK_CARD_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS,
        adaptive_wall_timeout_absolute_max_seconds=TASK_CARD_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS,
        adaptive_wall_timeout_progress_window_seconds=adaptive_progress_window,
        adaptive_wall_timeout_requires_material_progress=not provider_visible_cli_required,
        db_path=db_path,
        task_goal=_task_card_goal(task_card_path),
        receipt_id=str(receipt_id),
        execution_visibility_mode=execution_visibility_mode,
        visible_session_dir=visible_session_dir,
        visible_session_metadata={
            "receipt_id": str(receipt_id),
            "task_card_id": task_card.task_card_id,
            "pipeline_id": pipeline_id,
            "project_dir": project_dir.as_posix(),
            "window_title": f"workflowctl {task_card.task_card_id}",
        },
        env_overrides=env_overrides,
    )
    payload = executed.get("payload") if isinstance(executed.get("payload"), dict) else {}
    mutation_result = _mutation_result_from_payload(payload)
    implementation_status = _implementation_status_from_payload(
        executed=executed,
        payload=payload,
        mutation_result=mutation_result,
    )
    summary = payload.get("pr_ready_summary") if isinstance(payload, dict) and isinstance(payload.get("pr_ready_summary"), dict) else {}
    changed_files = _changed_files_from_summary(mutation_result=mutation_result, summary=summary)
    tests_status = _summary_tests_status(summary, mutation_result)
    result = {
        "status": implementation_status["status"],
        "failure_class": implementation_status["failure_class"],
        "requested_adapter": resolved_adapter,
        "receipt_id": receipt_id,
        "child_run_id": _child_run_id_from_execution(executed, payload),
        "child_attempt_id": _child_attempt_id_from_execution(executed),
        "child_workflow_state": executed.get("child_workflow_state") if isinstance(executed.get("child_workflow_state"), dict) else None,
        "worker_adapter": _worker_adapter_from_execution(executed, payload),
        "watchdog_source": executed.get("watchdog_source"),
        "evidence_id": payload.get("evidence_id") if isinstance(payload, dict) else None,
        "review_decision": payload.get("review_decision") if isinstance(payload, dict) else None,
        "implementation_readiness": implementation_status.get("readiness"),
        "mutation_result": mutation_result,
        "changed_files": changed_files,
        "final_test_status": tests_status,
        "stdout_preview": executed.get("stdout_preview"),
        "stderr_preview": executed.get("stderr_preview"),
        "watchdog": executed.get("watchdog"),
        "execution_visibility_mode": execution_visibility_mode,
        "control_plane_visibility": executed.get("control_plane_visibility"),
        "provider_visibility": executed.get("provider_visibility"),
        "provider_visible_cli_required": provider_visible_cli_required,
        "provider_visible_cli_session": executed.get("provider_visible_cli_session"),
        "provider_visible_cli_log_paths": executed.get("provider_visible_cli_log_paths"),
        "visible_cli_session": executed.get("visible_cli_session"),
        "visible_cli_log_paths": executed.get("visible_cli_log_paths"),
        "timeout_seconds": executed.get("timeout_seconds"),
        "idle_timeout_seconds": executed.get("idle_timeout_seconds"),
        "recoverable_suggestion": executed.get("recoverable_suggestion"),
        "command": run_cmd,
    }
    ts_sanity = _typescript_duplicate_declaration_check(changed_files)
    if result["status"] == "completed" and not ts_sanity["go"]:
        mutation_result = dict(result.get("mutation_result") or {})
        static_repair = _deterministic_typescript_static_sanity_repair(
            project_dir=project_dir,
            sanity=ts_sanity,
        )
        if static_repair["repaired_files"]:
            changed_files = _dedupe_strings([*changed_files, *static_repair["repaired_files"]])
            mutation_result["changed_files"] = changed_files
            ts_sanity = _typescript_duplicate_declaration_check(changed_files)
            ts_sanity["deterministic_static_sanity_repair"] = static_repair
            result["changed_files"] = changed_files
            result["mutation_result"] = mutation_result
        mutation_result["typescript_sanity"] = ts_sanity
        if not ts_sanity["go"]:
            failure_class = str((ts_sanity.get("blockers") or ["typescript_static_sanity_failed"])[0])
            result.update(
                {
                    "status": "failed",
                    "failure_class": failure_class,
                    "implementation_readiness": "blocked",
                    "mutation_result": mutation_result,
                    "final_test_status": "failed",
                    "recoverable_suggestion": "repair_typescript_static_sanity_findings_then_rerun_task_card",
                }
            )
        else:
            result["mutation_result"] = mutation_result
    finalized = _maybe_complete_evidence_finalization(
        root=root,
        project_dir=project_dir,
        task_card=task_card,
        task_card_path=task_card_path,
        write_set=write_set,
        read_set=read_set,
        test_commands=test_commands,
        receipt_id=str(receipt_id),
        execution_result=result,
    )
    return finalized or result


def _typescript_duplicate_declaration_check(changed_files: list[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for file_name in changed_files:
        path = Path(str(file_name))
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if path.suffix.lower() in {".scene", ".prefab"}:
            findings.extend(_cocos_serialized_custom_type_findings(path, text))
            continue
        if path.suffix.lower() != ".ts":
            continue
        for pattern, kind in [
            (r"\bexport\s+class\s+([A-Za-z_][A-Za-z0-9_]*)\b", "export_class"),
            (r"@ccclass\(['\"]([^'\"]+)['\"]\)", "ccclass"),
        ]:
            names = re.findall(pattern, text)
            duplicate_names = sorted({name for name in names if names.count(name) > 1})
            for name in duplicate_names:
                findings.append(
                    {
                        "path": path.as_posix(),
                        "kind": kind,
                        "name": name,
                        "count": names.count(name),
                    }
                )
        findings.extend(_typescript_missing_relative_named_exports(path, text))
    blockers = _dedupe_strings(
        [
            "typescript_duplicate_declaration"
            if item.get("kind") in {"export_class", "ccclass"}
            else str(item.get("kind"))
            for item in findings
        ]
    )
    return {
        "schema_version": "task_card_typescript_sanity_v1",
        "go": not findings,
        "blockers": blockers,
        "findings": findings,
    }


def _cocos_serialized_custom_type_findings(path: Path, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for match in re.finditer(r'"__type__"\s*:\s*"(?P<name>Workflow[A-Za-z0-9_]+)"', text):
        findings.append(
            {
                "path": path.as_posix(),
                "kind": "cocos_serialized_custom_type_uses_class_name",
                "name": match.group("name"),
                "offset": match.start(),
                "recoverable_suggestion": "replace_custom_component_class_name_with_cocos_script_rf_id",
            }
        )
    findings.extend(_cocos_serialized_cc_comp_alias_findings(path, text))
    return findings


def _deterministic_typescript_static_sanity_repair(*, project_dir: Path, sanity: dict[str, Any]) -> dict[str, Any]:
    findings = [item for item in sanity.get("findings") or [] if isinstance(item, dict)]
    cocos_findings = [
        item
        for item in findings
        if item.get("kind")
        in {
            "cocos_serialized_custom_type_uses_class_name",
            "cocos_serialized_custom_type_uses_reserved_cc_comp",
        }
    ]
    if not cocos_findings:
        return {
            "schema_version": "task_card_typescript_static_sanity_repair_v1",
            "go": False,
            "repaired_files": [],
            "blockers": ["no_deterministic_static_sanity_repair_available"],
        }
    rf_id_map = _cocos_script_rf_id_map(project_dir)
    uuid_map = _cocos_script_uuid_map(project_dir)
    repaired_files: list[str] = []
    generated_files: list[str] = []
    unresolved: list[str] = []
    processed: set[tuple[str, str, str]] = set()
    project_root = project_dir.resolve()
    for finding in cocos_findings:
        path = Path(str(finding.get("path") or ""))
        try:
            resolved = path.resolve()
            resolved.relative_to(project_root)
        except (OSError, ValueError):
            unresolved.append(f"{path}:outside_project_dir")
            continue
        class_name = str(finding.get("name") or "").strip()
        processed_key = (path.resolve().as_posix(), str(finding.get("kind") or ""), class_name)
        if processed_key in processed:
            continue
        processed.add(processed_key)
        rf_id = rf_id_map.get(class_name)
        if not rf_id:
            generated = _ensure_cocos_workflow_component_script(project_dir=project_dir, class_name=class_name)
            if generated.get("go"):
                for generated_file in generated.get("generated_files") or []:
                    generated_files.append(str(generated_file))
                rf_id_map = _cocos_script_rf_id_map(project_dir)
                uuid_map = _cocos_script_uuid_map(project_dir)
                rf_id = rf_id_map.get(class_name)
            if not rf_id:
                unresolved.append(f"{path}:{class_name}:rf_id_missing")
                continue
        if finding.get("kind") == "cocos_serialized_custom_type_uses_reserved_cc_comp":
            replaced = _replace_cocos_serialized_cc_comp_alias(
                path=path,
                workflow_component_class=class_name,
                rf_id=rf_id,
                uuid=uuid_map.get(class_name) or "",
            )
            if replaced <= 0:
                unresolved.append(f"{path}:{class_name}:cc_comp_alias_missing")
                continue
            repaired_files.append(path.as_posix())
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            unresolved.append(f"{path}:{class_name}:read_failed")
            continue
        pattern = re.compile(rf'("__type__"\s*:\s*)"{re.escape(class_name)}"')
        updated, count = pattern.subn(rf'\1"{rf_id}"', text)
        if count <= 0:
            unresolved.append(f"{path}:{class_name}:type_reference_missing")
            continue
        path.write_text(updated, encoding="utf-8")
        repaired_files.append(path.as_posix())
    return {
        "schema_version": "task_card_typescript_static_sanity_repair_v1",
        "go": bool(repaired_files) and not unresolved,
        "repair_type": "cocos_serialized_workflow_component_type_to_rf_id",
        "repaired_files": _dedupe_strings([*repaired_files, *generated_files]),
        "generated_files": _dedupe_strings(generated_files),
        "unresolved": _dedupe_strings(unresolved),
        "blockers": [] if repaired_files and not unresolved else ["cocos_serialized_custom_type_rf_id_repair_incomplete"],
    }


def _cocos_serialized_cc_comp_alias_findings(path: Path, text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    findings: list[dict[str, Any]] = []
    for item_path, item in _walk_json_objects(payload):
        if item.get("__type__") != "cc.Comp":
            continue
        workflow_component_class = str(item.get("workflowComponentClass") or "").strip()
        if not re.match(r"^Workflow[A-Za-z0-9_]+$", workflow_component_class):
            continue
        findings.append(
            {
                "path": path.as_posix(),
                "json_path": item_path,
                "kind": "cocos_serialized_custom_type_uses_reserved_cc_comp",
                "name": workflow_component_class,
                "serialized_type": "cc.Comp",
                "recoverable_suggestion": "replace_reserved_cc_comp_alias_with_cocos_script_rf_id",
            }
        )
    return findings


def _replace_cocos_serialized_cc_comp_alias(
    *,
    path: Path,
    workflow_component_class: str,
    rf_id: str,
    uuid: str,
) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    replaced = 0
    for _, item in _walk_json_objects(payload):
        if item.get("__type__") != "cc.Comp":
            continue
        if str(item.get("workflowComponentClass") or "").strip() != workflow_component_class:
            continue
        item["__type__"] = rf_id
        script_asset = item.get("__scriptAsset")
        if uuid and isinstance(script_asset, dict):
            script_asset["__uuid__"] = uuid
        replaced += 1
    if replaced:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return replaced


def _walk_json_objects(value: Any, path: str = "$") -> list[tuple[str, dict[str, Any]]]:
    result: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        result.append((path, value))
        for key, child in value.items():
            result.extend(_walk_json_objects(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(_walk_json_objects(child, f"{path}[{index}]"))
    return result


def _ensure_cocos_workflow_component_script(*, project_dir: Path, class_name: str) -> dict[str, Any]:
    if not re.match(r"^Workflow[A-Za-z0-9_]+$", class_name):
        return {
            "go": False,
            "generated_files": [],
            "blockers": ["invalid_workflow_component_class_name"],
        }
    script_dir = project_dir / "assets" / "scripts" / "runtime" / "workflow"
    script_path = script_dir / f"{class_name}.ts"
    meta_path = Path(f"{script_path.as_posix()}.meta")
    generated_files: list[str] = []
    script_dir.mkdir(parents=True, exist_ok=True)
    if not script_path.exists():
        script_path.write_text(
            "\n".join(
                [
                    "import { _decorator, Component } from 'cc';",
                    "",
                    "const { ccclass, property } = _decorator;",
                    "",
                    f"@ccclass('{class_name}')",
                    f"export class {class_name} extends Component {{",
                    "  @property",
                    f"  public workflowComponentClass = '{class_name}';",
                    "",
                    "  public getRuntimePacket(): Record<string, unknown> {",
                    "    return {",
                    "      schema_version: 'workflow_cocos_generated_component_v1',",
                    f"      component: '{class_name}',",
                    f"      workflowComponentClass: '{class_name}',",
                    "      engine_native_product_body: true,",
                    "      generated_by: 'deterministic_cocos_serialized_component_repair',",
                    "    };",
                    "  }",
                    "}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        generated_files.append(script_path.as_posix())
    if not meta_path.exists():
        component_uuid = str(uuid5(NAMESPACE_URL, f"universal-agentic-workflow:cocos-component:{class_name}"))
        meta_path.write_text(
            json.dumps(
                {
                    "ver": "4.0.24",
                    "importer": "typescript",
                    "imported": True,
                    "uuid": component_uuid,
                    "files": [],
                    "subMetas": {},
                    "userData": {},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        generated_files.append(meta_path.as_posix())
    return {
        "go": True,
        "generated_files": generated_files,
        "blockers": [],
    }


def _cocos_script_rf_id_map(project_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    script_root = project_dir / "assets" / "scripts"
    if not script_root.exists():
        return result
    for script_path in script_root.rglob("*.ts"):
        meta_path = Path(f"{script_path.as_posix()}.meta")
        if not meta_path.exists():
            continue
        try:
            script_text = script_path.read_text(encoding="utf-8")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        uuid = str(meta.get("uuid") or "").strip()
        rf_id = _compress_cocos_uuid(uuid)
        if not rf_id:
            continue
        for name in _cocos_ccclass_names(script_text):
            result[name] = rf_id
    return result


def _cocos_script_uuid_map(project_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    script_root = project_dir / "assets" / "scripts"
    if not script_root.exists():
        return result
    for script_path in script_root.rglob("*.ts"):
        meta_path = Path(f"{script_path.as_posix()}.meta")
        if not meta_path.exists():
            continue
        try:
            script_text = script_path.read_text(encoding="utf-8")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        uuid = str(meta.get("uuid") or "").strip()
        if not uuid:
            continue
        for name in _cocos_ccclass_names(script_text):
            result[name] = uuid
    return result


def _cocos_ccclass_names(text: str) -> list[str]:
    names = re.findall(r"@ccclass\(['\"]([^'\"]+)['\"]\)", text)
    if names:
        return _dedupe_strings(names)
    return _dedupe_strings(re.findall(r"\bexport\s+class\s+(Workflow[A-Za-z0-9_]+)\b", text))


_COCOS_UUID64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _compress_cocos_uuid(uuid: str) -> str:
    compact = re.sub(r"[^0-9a-fA-F]", "", uuid)
    if len(compact) != 32:
        return ""
    head = compact[:5]
    tail = compact[5:]
    chars: list[str] = []
    for index in range(0, len(tail), 3):
        chunk = tail[index : index + 3]
        if len(chunk) < 3:
            return ""
        value = int(chunk, 16)
        chars.append(_COCOS_UUID64[value >> 6])
        chars.append(_COCOS_UUID64[value & 0x3F])
    return head + "".join(chars)


def _typescript_missing_relative_named_exports(path: Path, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    import_pattern = re.compile(
        r"\bimport\s+(?:type\s+)?\{(?P<names>[^}]+)\}\s+from\s+['\"](?P<source>\.[^'\"]+)['\"]",
        re.DOTALL,
    )
    for match in import_pattern.finditer(text):
        source = match.group("source")
        target = _resolve_typescript_relative_import(path, source)
        imported_names = _typescript_named_imports(match.group("names"))
        if target is None:
            for name in imported_names:
                findings.append(
                    {
                        "path": path.as_posix(),
                        "kind": "typescript_import_target_missing",
                        "name": name,
                        "import_source": source,
                    }
                )
            continue
        try:
            target_text = target.read_text(encoding="utf-8")
        except OSError:
            continue
        for name in imported_names:
            if not _typescript_exports_symbol(target_text, name):
                findings.append(
                    {
                        "path": path.as_posix(),
                        "kind": "typescript_missing_named_export",
                        "name": name,
                        "import_source": source,
                        "resolved_path": target.as_posix(),
                    }
                )
    return findings


def _resolve_typescript_relative_import(path: Path, source: str) -> Path | None:
    base = (path.parent / source).resolve()
    candidates = [base]
    if base.suffix:
        candidates.append(base.with_suffix(".ts"))
    else:
        candidates.extend(
            [
                base.with_suffix(".ts"),
                base / "index.ts",
            ]
        )
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _typescript_named_imports(raw_names: str) -> list[str]:
    names: list[str] = []
    for raw_part in raw_names.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if part.startswith("type "):
            part = part[len("type ") :].strip()
        name = re.split(r"\s+as\s+", part, maxsplit=1)[0].strip()
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            names.append(name)
    return names


def _typescript_exports_symbol(text: str, name: str) -> bool:
    escaped = re.escape(name)
    direct_patterns = [
        rf"\bexport\s+(?:abstract\s+)?class\s+{escaped}\b",
        rf"\bexport\s+(?:async\s+)?function\s+{escaped}\b",
        rf"\bexport\s+(?:const|let|var|enum|interface|type)\s+{escaped}\b",
    ]
    if any(re.search(pattern, text) for pattern in direct_patterns):
        return True
    return bool(re.search(rf"\bexport\s*\{{[^}}]*\b{escaped}\b[^}}]*\}}", text, re.DOTALL))


def _maybe_complete_evidence_finalization(
    *,
    root: Path,
    project_dir: Path,
    task_card: Any,
    task_card_path: Path,
    write_set: list[str],
    read_set: list[str],
    test_commands: list[str],
    receipt_id: str,
    execution_result: dict[str, Any],
) -> dict[str, Any] | None:
    if execution_result.get("status") == "completed":
        return None
    metadata = _task_card_markdown_metadata(task_card_path)
    finding_id = str(metadata.get("ai_finding_id") or "").strip()
    if not finding_id.endswith("_finalize"):
        return None
    if str(metadata.get("execution_visibility_mode") or "") != "human_visible_cli_enforced":
        return None
    evidence_paths = _dedupe_strings(
        [
            *_string_list(metadata.get("evidence_paths")),
            *[item for item in read_set if str(item).lower().endswith(".json")],
        ]
    )
    required_evidence_paths = _dedupe_strings(_string_list(metadata.get("finalizer_required_evidence_paths")))
    resolved_evidence = [_resolve_evidence_path(root, item) for item in evidence_paths]
    resolved_required_evidence = [_resolve_evidence_path(root, item) for item in required_evidence_paths]
    missing = [path.as_posix() for path in [*resolved_evidence, *resolved_required_evidence] if not path.exists()]
    if missing:
        return None
    runtime_evidence = _runtime_evidence_json_paths(
        project_dir=project_dir,
        evidence_paths=resolved_required_evidence or resolved_evidence,
    )
    if not runtime_evidence:
        return None
    evidence_dir = project_dir / "workflow_runtime_evidence"
    if not _path_is_in_write_set(evidence_dir, write_set):
        return None
    tests = run_safe_commands(
        [SafeCommandSpec(command=command, timeout_seconds=180) for command in test_commands],
        working_directory=root,
    )
    tests_passed = bool(tests) and all(bool(item.get("passed")) for item in tests)
    finalization_path = evidence_dir / f"{_safe_name(getattr(task_card, 'task_card_id', task_card_path.stem))}_evidence_finalization.json"
    finalization_payload = {
        "schema_version": "commercial_game_evidence_finalization_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "task_card_id": getattr(task_card, "task_card_id", task_card_path.stem),
        "task_card_path": task_card_path.as_posix(),
        "finalization_mode": "deterministic_existing_evidence_validation",
        "source_failure_class": execution_result.get("failure_class"),
        "receipt_id": receipt_id,
        "visible_cli_session": execution_result.get("visible_cli_session"),
        "evidence_paths": [path.as_posix() for path in resolved_evidence],
        "runtime_evidence_paths": [path.as_posix() for path in runtime_evidence],
        "covered_requirement_ids": _string_list(metadata.get("covered_requirement_ids")),
        "tests": tests,
        "go": tests_passed,
        "blockers": [] if tests_passed else ["evidence_finalization_tests_failed"],
    }
    _write_json(finalization_path, finalization_payload)
    changed_files = [finalization_path.as_posix()]
    return {
        **execution_result,
        "status": "completed" if tests_passed else "failed",
        "failure_class": None if tests_passed else "evidence_finalization_tests_failed",
        "implementation_readiness": "ready" if tests_passed else "blocked",
        "mutation_result": {
            "evidence_finalization": finalization_payload,
            "changed_files": changed_files,
            "applied_patch_hash": _hash_file(finalization_path),
            "finalized_existing_evidence": True,
        },
        "changed_files": changed_files,
        "final_test_status": "passed" if tests_passed else "failed",
        "evidence_id": execution_result.get("evidence_id") or f"evidence_finalization_{_safe_name(str(getattr(task_card, 'task_card_id', task_card_path.stem)))}",
        "review_decision": "pass" if tests_passed else "fail",
        "recoverable_suggestion": None if tests_passed else "inspect_evidence_finalization_tests",
    }


def _task_card_markdown_metadata(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    marker = "## Metadata"
    marker_index = text.find(marker)
    if marker_index < 0:
        return {}
    fenced_index = text.find("```json", marker_index)
    if fenced_index < 0:
        return {}
    start = text.find("\n", fenced_index)
    end = text.find("```", start + 1)
    if start < 0 or end < 0:
        return {}
    try:
        payload = json.loads(text[start:end].strip())
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_evidence_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _runtime_evidence_json_paths(*, project_dir: Path, evidence_paths: list[Path]) -> list[Path]:
    evidence_dir = (project_dir / "workflow_runtime_evidence").resolve()
    runtime_paths: list[Path] = []
    for path in evidence_paths:
        resolved = path.resolve()
        try:
            resolved.relative_to(evidence_dir)
        except ValueError:
            continue
        if resolved.suffix.lower() != ".json":
            continue
        if resolved.name == "requirement_coverage_trace.json":
            continue
        runtime_paths.append(resolved)
    return runtime_paths


def _path_is_in_write_set(path: Path, write_set: list[str]) -> bool:
    resolved = path.resolve()
    for item in write_set:
        candidate = Path(item)
        base = candidate.resolve() if candidate.is_absolute() else candidate.resolve()
        try:
            resolved.relative_to(base)
            return True
        except ValueError:
            continue
    return False


def _hash_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def _resolve_task_card_adapter(task_card: Any, adapter_name: str | None) -> str:
    raw = adapter_name or getattr(task_card, "provider_lane", None) or "codex"
    normalized = str(raw or "codex").strip().lower()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    if normalized in {"codex_cli", "codex_cli_login"}:
        return "codex"
    if normalized == "opencode_cli":
        return "opencode"
    if normalized in {"shell", "noop", "dry_run"}:
        return "codex"
    return normalized or "codex"


def _literal_cli_arg(value: Any) -> str:
    text = str(value)
    if any(marker in text for marker in ("*", "?", "[")) and not (
        (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'"))
    ):
        return f'"{text}"'
    return text


def _run_json_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    idle_timeout_seconds: int,
    provider_output_idle_timeout_seconds: int | None = None,
    material_progress_idle_timeout_seconds: int | None = None,
    adaptive_wall_timeout_extension_seconds: int | None = None,
    adaptive_wall_timeout_max_extensions: int | None = None,
    adaptive_wall_timeout_absolute_max_seconds: int | None = None,
    adaptive_wall_timeout_progress_window_seconds: int | None = None,
    adaptive_wall_timeout_requires_material_progress: bool = True,
    db_path: Path | None = None,
    task_goal: str | None = None,
    receipt_id: str | None = None,
    execution_visibility_mode: str | None = None,
    visible_session_dir: Path | None = None,
    visible_session_metadata: dict[str, Any] | None = None,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    if execution_visibility_mode == HUMAN_VISIBLE_CLI_MODE and not _resident_control_plane_provider_visible_requested(env_overrides):
        return _run_visible_json_command(
            command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            idle_timeout_seconds=idle_timeout_seconds,
            provider_output_idle_timeout_seconds=provider_output_idle_timeout_seconds,
            material_progress_idle_timeout_seconds=material_progress_idle_timeout_seconds,
            adaptive_wall_timeout_extension_seconds=adaptive_wall_timeout_extension_seconds,
            adaptive_wall_timeout_max_extensions=adaptive_wall_timeout_max_extensions,
            adaptive_wall_timeout_absolute_max_seconds=adaptive_wall_timeout_absolute_max_seconds,
            adaptive_wall_timeout_progress_window_seconds=adaptive_wall_timeout_progress_window_seconds,
            db_path=db_path,
            task_goal=task_goal,
            receipt_id=receipt_id,
            visible_session_dir=visible_session_dir,
            visible_session_metadata=visible_session_metadata,
            env_overrides=env_overrides,
        )
    resident_session = None
    resident_output_callback = None
    if execution_visibility_mode in VISIBLE_CLI_ENFORCED_MODES and _resident_control_plane_provider_visible_requested(env_overrides):
        resident_session = _start_resident_control_plane_session(
            command=command,
            cwd=cwd,
            visible_session_dir=visible_session_dir,
            receipt_id=receipt_id,
            execution_visibility_mode=execution_visibility_mode,
            visible_session_metadata=visible_session_metadata,
        )
        resident_output_callback = resident_session["on_output"]
    run_kwargs: dict[str, Any] = {
        "cwd": str(cwd),
        "capture_output": True,
        "text": True,
        "timeout": timeout_seconds,
        "idle_timeout": idle_timeout_seconds,
        "check": False,
    }
    if resident_output_callback is not None:
        run_kwargs["on_output"] = resident_output_callback
    if provider_output_idle_timeout_seconds is not None:
        run_kwargs["provider_output_idle_timeout"] = provider_output_idle_timeout_seconds
    if material_progress_idle_timeout_seconds is not None:
        run_kwargs["material_progress_idle_timeout"] = material_progress_idle_timeout_seconds
    if (
        adaptive_wall_timeout_extension_seconds is not None
        and _runner_supports_kwarg(run_subprocess_with_tree_timeout, "adaptive_wall_timeout_extension")
    ):
        run_kwargs["adaptive_wall_timeout_extension"] = adaptive_wall_timeout_extension_seconds
        run_kwargs["adaptive_wall_timeout_max_extensions"] = adaptive_wall_timeout_max_extensions or 0
        if adaptive_wall_timeout_absolute_max_seconds is not None:
            run_kwargs["adaptive_wall_timeout_absolute_max"] = adaptive_wall_timeout_absolute_max_seconds
        if adaptive_wall_timeout_progress_window_seconds is not None:
            run_kwargs["adaptive_wall_timeout_progress_window"] = adaptive_wall_timeout_progress_window_seconds
        run_kwargs["adaptive_wall_timeout_requires_material_progress"] = adaptive_wall_timeout_requires_material_progress
    if (
        db_path is not None
        and task_goal
        and (provider_output_idle_timeout_seconds is not None or material_progress_idle_timeout_seconds is not None)
        and _runner_supports_kwarg(run_subprocess_with_tree_timeout, "activity_probe")
    ):
        run_kwargs["activity_probe"] = _child_provider_activity_probe(
            db_path=db_path,
            task_goal=task_goal,
            receipt_id=receipt_id,
        )
        run_kwargs["activity_probe_interval"] = 1.0
    if env_overrides:
        run_kwargs["env"] = {**os.environ, **{str(key): str(value) for key, value in env_overrides.items()}}
    proc = run_subprocess_with_tree_timeout(command, **run_kwargs)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if resident_session is not None:
        _finish_resident_control_plane_session(
            session_context=resident_session,
            return_code=proc.returncode,
            watchdog=completed_process_watchdog_metadata(proc),
            stdout=stdout,
            stderr=stderr,
        )
    payload = _parse_json_from_stdout(stdout)
    watchdog = completed_process_watchdog_metadata(proc)
    common = {
        "return_code": proc.returncode,
        "stdout_preview": stdout[-PREVIEW_LIMIT:],
        "stderr_preview": stderr[-PREVIEW_LIMIT:],
        "watchdog": watchdog,
        "timeout_seconds": timeout_seconds,
        "idle_timeout_seconds": idle_timeout_seconds,
        "provider_output_idle_timeout_seconds": provider_output_idle_timeout_seconds,
        "material_progress_idle_timeout_seconds": material_progress_idle_timeout_seconds,
        "adaptive_wall_timeout_extension_seconds": adaptive_wall_timeout_extension_seconds,
        "adaptive_wall_timeout_max_extensions": adaptive_wall_timeout_max_extensions,
        "adaptive_wall_timeout_absolute_max_seconds": adaptive_wall_timeout_absolute_max_seconds,
        "adaptive_wall_timeout_progress_window_seconds": adaptive_wall_timeout_progress_window_seconds,
    }
    if resident_session is not None:
        session_payload = resident_session["session"]
        log_paths = resident_session["log_paths"]
        common.update(
            {
                "control_plane_visibility": "resident",
                "provider_visibility": "direct_visible",
                "watchdog_source": "resident_control_plane_db_runtime_state",
                "visible_cli_session": session_payload,
                "visible_cli_log_paths": log_paths,
                "resident_control_plane_session": session_payload,
                "resident_control_plane_log_paths": log_paths,
            }
        )
    if proc.returncode != 0:
        child_state = (
            _inspect_child_workflow_state(db_path=db_path, task_goal=task_goal, receipt_id=receipt_id)
            if db_path is not None and task_goal
            else {}
        )
        failure_class = _classify_child_failure(
            payload=payload,
            proc=proc,
            watchdog=watchdog,
            child_state=child_state,
            idle_timeout_seconds=idle_timeout_seconds,
        )
        if child_state.get("run_id") and _child_was_terminated_by_wrapper(watchdog):
            _close_child_workflow(
                db_path=db_path,
                child_state=child_state,
                failure_class=failure_class,
                receipt_id=receipt_id,
                command=command,
            )
            for nested_state in child_state.get("nested_child_states") or []:
                if isinstance(nested_state, dict) and str(nested_state.get("run_status") or "") not in {
                    "completed",
                    "failed",
                    "blocked",
                    "cancelled",
                }:
                    _close_child_workflow(
                        db_path=db_path,
                        child_state=nested_state,
                        failure_class=failure_class,
                        receipt_id=receipt_id,
                        command=command,
                    )
        return {
            **common,
            "status": "failed",
            "failure_class": failure_class,
            "payload": payload,
            "child_workflow_state": child_state,
            "child_run_id": child_state.get("run_id"),
            "child_attempt_id": child_state.get("attempt_id"),
            "watchdog_source": common.get("watchdog_source") or ("db_runtime_state" if child_state else "process_stream"),
            "provider_visible_cli_session": child_state.get("provider_visible_cli_session"),
            "provider_visible_cli_log_paths": child_state.get("provider_visible_cli_log_paths"),
            "recoverable_suggestion": _recoverable_suggestion_for_failure(failure_class, watchdog),
        }
    if not isinstance(payload, dict):
        return {
            **common,
            "status": "failed",
            "failure_class": "workflowctl_child_json_parse_failed",
        }
    child_state = (
        _inspect_child_workflow_state(db_path=db_path, task_goal=task_goal, receipt_id=receipt_id)
        if db_path is not None and task_goal
        else {}
    )
    return {
        **common,
        "status": "completed",
        "payload": payload,
        "child_workflow_state": child_state,
        "child_run_id": (payload.get("run", {}).get("run_id") if isinstance(payload, dict) else None) or child_state.get("run_id"),
        "child_attempt_id": child_state.get("attempt_id"),
        "provider_visible_cli_session": child_state.get("provider_visible_cli_session"),
        "provider_visible_cli_log_paths": child_state.get("provider_visible_cli_log_paths"),
        "watchdog_source": common.get("watchdog_source") or "workflowctl_payload",
    }


def _truthy_value(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _resident_control_plane_provider_visible_requested(env_overrides: dict[str, str] | None) -> bool:
    env = env_overrides or {}
    return str(env.get("WORKFLOW_CONTROL_PLANE_VISIBILITY") or "").strip().lower() == "resident" and (
        _truthy_value(env.get("WORKFLOW_PROVIDER_DIRECT_VISIBLE_CLI"))
        or str(env.get("WORKFLOW_PROVIDER_VISIBILITY") or "").strip().lower() == "direct_visible"
    )


def _start_resident_control_plane_session(
    *,
    command: list[str],
    cwd: Path,
    visible_session_dir: Path | None,
    receipt_id: str | None,
    execution_visibility_mode: str | None,
    visible_session_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    session_dir = visible_session_dir or cwd / "state" / "visible_cli_sessions" / f"resident_{uuid4().hex[:12]}"
    session_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = session_dir / "stdout.log"
    stderr_path = session_dir / "stderr.log"
    stream_path = session_dir / "stream.jsonl"
    session_path = session_dir / "visible_cli_session.json"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    stream_path.write_text("", encoding="utf-8")
    metadata = dict(visible_session_metadata or {})
    now = datetime.now(UTC).isoformat()
    session = {
        "schema_version": "resident_control_plane_session_v1",
        "mode": RESIDENT_CONTROL_PLANE_PROVIDER_VISIBLE_MODE,
        "logical_execution_visibility_mode": execution_visibility_mode,
        "status": "running",
        "pid": os.getpid(),
        "control_plane_pid": os.getpid(),
        "window_title": metadata.get("window_title") or "resident workflowctl control plane",
        "argv": command,
        "cwd": cwd.as_posix(),
        "receipt_id": receipt_id,
        "task_card_id": metadata.get("task_card_id"),
        "pipeline_id": metadata.get("pipeline_id"),
        "stdout_log_path": stdout_path.as_posix(),
        "stderr_log_path": stderr_path.as_posix(),
        "stream_log_path": stream_path.as_posix(),
        "session_path": session_path.as_posix(),
        "started_at": now,
        "ended_at": None,
    }
    _write_json(session_path, session)
    _append_stream_event(
        stream_path,
        {
            "event": "resident_control_plane_started",
            "created_at": now,
            "argv": command,
            "pid": os.getpid(),
        },
    )

    def _on_output(event: dict[str, Any]) -> None:
        text = str(event.get("text") or "")
        if not text:
            return
        stream = str(event.get("stream") or "stdout")
        target = stderr_path if stream == "stderr" else stdout_path
        with target.open("a", encoding="utf-8") as handle:
            handle.write(text)
        _append_stream_event(
            stream_path,
            {
                "event": f"resident_control_plane_{stream}",
                "created_at": str(event.get("observed_at") or datetime.now(UTC).isoformat()),
                "stream": stream,
                "byte_count": event.get("byte_count"),
                "is_control": bool(event.get("is_control")),
                "is_material_progress": bool(event.get("is_material_progress")),
                "text": text.rstrip("\r\n"),
            },
        )

    log_paths = {
        "stdout_log_path": stdout_path.as_posix(),
        "stderr_log_path": stderr_path.as_posix(),
        "stream_log_path": stream_path.as_posix(),
        "session_path": session_path.as_posix(),
    }
    return {
        "session": session,
        "session_path": session_path,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "stream_path": stream_path,
        "log_paths": log_paths,
        "on_output": _on_output,
    }


def _finish_resident_control_plane_session(
    *,
    session_context: dict[str, Any],
    return_code: int,
    watchdog: dict[str, Any],
    stdout: str,
    stderr: str,
) -> None:
    stdout_path = session_context["stdout_path"]
    stderr_path = session_context["stderr_path"]
    stream_path = session_context["stream_path"]
    session_path = session_context["session_path"]
    if stdout and not stdout_path.read_text(encoding="utf-8"):
        stdout_path.write_text(stdout, encoding="utf-8")
    if stderr and not stderr_path.read_text(encoding="utf-8"):
        stderr_path.write_text(stderr, encoding="utf-8")
    ended = datetime.now(UTC).isoformat()
    timeout_type = watchdog.get("timeout_type")
    if timeout_type:
        status = "timeout"
    else:
        status = "completed" if return_code == 0 else "failed"
    session = dict(session_context["session"])
    session.update(
        {
            "status": status,
            "return_code": return_code,
            "ended_at": ended,
            "timeout_type": timeout_type,
        }
    )
    session_context["session"].clear()
    session_context["session"].update(session)
    _write_json(session_path, session)
    _append_stream_event(
        stream_path,
        {
            "event": "resident_control_plane_completed",
            "created_at": ended,
            "return_code": return_code,
            "timeout_type": timeout_type,
        },
    )


def _run_visible_json_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    idle_timeout_seconds: int,
    provider_output_idle_timeout_seconds: int | None,
    material_progress_idle_timeout_seconds: int | None,
    adaptive_wall_timeout_extension_seconds: int | None,
    adaptive_wall_timeout_max_extensions: int | None,
    adaptive_wall_timeout_absolute_max_seconds: int | None,
    adaptive_wall_timeout_progress_window_seconds: int | None,
    db_path: Path | None,
    task_goal: str | None,
    receipt_id: str | None,
    visible_session_dir: Path | None,
    visible_session_metadata: dict[str, Any] | None,
    env_overrides: dict[str, str] | None,
) -> dict[str, Any]:
    session_dir = visible_session_dir or cwd / "state" / "visible_cli_sessions" / f"session_{uuid4().hex[:12]}"
    session_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = session_dir / "stdout.log"
    stderr_path = session_dir / "stderr.log"
    stream_path = session_dir / "stream.jsonl"
    session_path = session_dir / "visible_cli_session.json"
    now = datetime.now(UTC).isoformat()
    metadata = dict(visible_session_metadata or {})
    session: dict[str, Any] = {
        "schema_version": "human_visible_cli_session_v1",
        "mode": "human_visible_cli_enforced",
        "status": "starting",
        "pid": None,
        "window_title": metadata.get("window_title") or "workflowctl visible task-card run",
        "argv": command,
        "cwd": cwd.as_posix(),
        "receipt_id": receipt_id,
        "task_card_id": metadata.get("task_card_id"),
        "pipeline_id": metadata.get("pipeline_id"),
        "stdout_log_path": stdout_path.as_posix(),
        "stderr_log_path": stderr_path.as_posix(),
        "stream_log_path": stream_path.as_posix(),
        "session_path": session_path.as_posix(),
        "started_at": now,
        "ended_at": None,
    }
    _write_json(session_path, session)
    _append_stream_event(stream_path, {"event": "visible_cli_starting", "created_at": now, "argv": command})
    command_metadata = {
        "adaptive_wall_timeout_extension_seconds": adaptive_wall_timeout_extension_seconds,
        "adaptive_wall_timeout_max_extensions": adaptive_wall_timeout_max_extensions,
        "adaptive_wall_timeout_absolute_max_seconds": adaptive_wall_timeout_absolute_max_seconds,
        "adaptive_wall_timeout_progress_window_seconds": adaptive_wall_timeout_progress_window_seconds,
    }
    if not hasattr(subprocess, "CREATE_NEW_CONSOLE"):
        session.update({"status": "unavailable", "ended_at": datetime.now(UTC).isoformat()})
        _write_json(session_path, session)
        return _visible_command_result(
            status="failed",
            failure_class="human_visible_cli_unavailable",
            return_code=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stream_path=stream_path,
            session=session,
            timeout_seconds=timeout_seconds,
            idle_timeout_seconds=idle_timeout_seconds,
            provider_output_idle_timeout_seconds=provider_output_idle_timeout_seconds,
            material_progress_idle_timeout_seconds=material_progress_idle_timeout_seconds,
            **command_metadata,
            payload=None,
            child_state={},
        )
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    stdout_ps = str(stdout_path).replace("'", "''")
    inner_command = "& " + " ".join(_powershell_quote_arg(item) for item in command)
    powershell_command = (
        f"& {{ {inner_command} 2>&1 | ForEach-Object {{ $_; "
        f"$_ | Out-File -FilePath '{stdout_ps}' -Encoding utf8 -Append }}; "
        f"$code = $LASTEXITCODE; exit $code }}"
    )
    launch_cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        powershell_command,
    ]
    env = {**os.environ, **{str(key): str(value) for key, value in (env_overrides or {}).items()}}
    try:
        proc = subprocess.Popen(
            launch_cmd,
            cwd=str(cwd),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            env=env,
        )
    except OSError as exc:
        session.update({"status": "blocked", "ended_at": datetime.now(UTC).isoformat(), "launch_error": str(exc)})
        _write_json(session_path, session)
        return _visible_command_result(
            status="failed",
            failure_class="human_visible_cli_launch_failed",
            return_code=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stream_path=stream_path,
            session=session,
            timeout_seconds=timeout_seconds,
            idle_timeout_seconds=idle_timeout_seconds,
            provider_output_idle_timeout_seconds=provider_output_idle_timeout_seconds,
            material_progress_idle_timeout_seconds=material_progress_idle_timeout_seconds,
            **command_metadata,
            payload=None,
            child_state={},
        )
    session.update({"status": "running", "pid": proc.pid})
    _write_json(session_path, session)
    _append_stream_event(stream_path, {"event": "visible_cli_started", "created_at": datetime.now(UTC).isoformat(), "pid": proc.pid})
    started = time.monotonic()
    last_activity = started
    last_provider_output = started
    last_material_progress = started
    extension_count = 0
    effective_wall_timeout = timeout_seconds
    last_stdout_size = 0
    last_stderr_size = 0
    timeout_type: str | None = None
    probe = (
        _child_provider_activity_probe(db_path=db_path, task_goal=task_goal, receipt_id=receipt_id)
        if db_path is not None and task_goal
        else None
    )
    last_probe_counts = {"provider_output_event_count": 0, "material_progress_event_count": 0}

    def _refresh_probe_activity(now_mono: float) -> None:
        nonlocal last_activity, last_material_progress, last_provider_output, last_probe_counts
        if probe is None:
            return
        probe_payload = probe()
        provider_count_changed = probe_payload.get("provider_output_event_count") != last_probe_counts.get(
            "provider_output_event_count"
        )
        material_count_changed = probe_payload.get("material_progress_event_count") != last_probe_counts.get(
            "material_progress_event_count"
        )
        if provider_count_changed:
            last_provider_output = now_mono
        if material_count_changed:
            last_material_progress = now_mono
        if provider_count_changed or material_count_changed:
            last_probe_counts = dict(probe_payload)
            last_activity = now_mono

    while proc.poll() is None:
        now_mono = time.monotonic()
        stdout_size = stdout_path.stat().st_size if stdout_path.exists() else 0
        stderr_size = stderr_path.stat().st_size if stderr_path.exists() else 0
        if stdout_size != last_stdout_size or stderr_size != last_stderr_size:
            last_stdout_size = stdout_size
            last_stderr_size = stderr_size
            last_activity = now_mono
        _refresh_probe_activity(now_mono)
        if (
            provider_output_idle_timeout_seconds is not None
            and now_mono - last_provider_output > provider_output_idle_timeout_seconds
        ):
            _refresh_probe_activity(now_mono)
            if now_mono - last_provider_output <= provider_output_idle_timeout_seconds:
                time.sleep(1.0)
                continue
            timeout_type = "provider_output_idle_timeout"
            break
        if (
            material_progress_idle_timeout_seconds is not None
            and now_mono - last_material_progress > material_progress_idle_timeout_seconds
            and now_mono - last_provider_output > material_progress_idle_timeout_seconds
        ):
            _refresh_probe_activity(now_mono)
            if (
                now_mono - last_material_progress <= material_progress_idle_timeout_seconds
                or now_mono - last_provider_output <= material_progress_idle_timeout_seconds
            ):
                time.sleep(1.0)
                continue
            timeout_type = "provider_no_material_progress_timeout"
            break
        if now_mono - started > effective_wall_timeout:
            progress_window = (
                adaptive_wall_timeout_progress_window_seconds
                or material_progress_idle_timeout_seconds
                or idle_timeout_seconds
            )
            can_extend = (
                adaptive_wall_timeout_extension_seconds is not None
                and extension_count < (adaptive_wall_timeout_max_extensions or 0)
                and (
                    (
                        last_probe_counts.get("material_progress_event_count", 0) > 0
                        and now_mono - last_material_progress <= progress_window
                    )
                    or (
                        last_probe_counts.get("provider_output_event_count", 0) > 0
                        and now_mono - last_provider_output <= progress_window
                    )
                )
            )
            next_effective = effective_wall_timeout + (adaptive_wall_timeout_extension_seconds or 0)
            within_absolute_max = (
                adaptive_wall_timeout_absolute_max_seconds is None
                or next_effective <= adaptive_wall_timeout_absolute_max_seconds
            )
            if can_extend and within_absolute_max:
                effective_wall_timeout = next_effective
                extension_count += 1
            else:
                timeout_type = "adaptive_wall_timeout_exhausted" if adaptive_wall_timeout_extension_seconds is not None else "wall_timeout"
                break
        if now_mono - last_activity > idle_timeout_seconds:
            timeout_type = "idle_timeout"
            break
        time.sleep(1.0)
    if timeout_type:
        _terminate_visible_process_tree(proc)
    return_code = proc.wait()
    ended = datetime.now(UTC).isoformat()
    stdout = _read_log_text(stdout_path)
    stderr = _read_log_text(stderr_path)
    payload = _parse_json_from_stdout(stdout)
    child_state = (
        _inspect_child_workflow_state(db_path=db_path, task_goal=task_goal, receipt_id=receipt_id)
        if db_path is not None and task_goal
        else {}
    )
    session.update(
        {
            "status": "timeout" if timeout_type else "completed",
            "return_code": return_code,
            "ended_at": ended,
            "timeout_type": timeout_type,
        }
    )
    _write_json(session_path, session)
    _append_stream_event(
        stream_path,
        {
            "event": "visible_cli_completed",
            "created_at": ended,
            "return_code": return_code,
            "timeout_type": timeout_type,
        },
    )
    watchdog = {
        "source": "human_visible_cli_mirrored_logs",
        "timeout_type": timeout_type,
        "stdout_log_path": stdout_path.as_posix(),
        "stderr_log_path": stderr_path.as_posix(),
        "stream_log_path": stream_path.as_posix(),
        "last_provider_output_age_seconds": max(0.0, time.monotonic() - last_provider_output),
        "last_material_progress_age_seconds": max(0.0, time.monotonic() - last_material_progress),
        "adaptive_wall_timeout_extension_count": extension_count,
        "adaptive_wall_timeout_effective_seconds": effective_wall_timeout,
        "adaptive_wall_timeout_absolute_max_seconds": adaptive_wall_timeout_absolute_max_seconds,
        "adaptive_wall_timeout_exhausted": timeout_type == "adaptive_wall_timeout_exhausted",
        **last_probe_counts,
    }
    status = "completed" if return_code == 0 and isinstance(payload, dict) else "failed"
    failure_class = None
    if status != "completed":
        failure_class = (
            "workflowctl_child_json_parse_failed"
            if return_code == 0
            else _classify_child_failure(
                payload=payload,
                proc=type("VisibleProcess", (), {"returncode": return_code})(),
                watchdog=watchdog,
                child_state=child_state,
                idle_timeout_seconds=idle_timeout_seconds,
            )
        )
        if child_state.get("run_id") and _child_was_terminated_by_wrapper(watchdog):
            _close_child_workflow(
                db_path=db_path,
                child_state=child_state,
                failure_class=failure_class,
                receipt_id=receipt_id,
                command=command,
            )
            for nested_state in child_state.get("nested_child_states") or []:
                if isinstance(nested_state, dict) and str(nested_state.get("run_status") or "") not in {
                    "completed",
                    "failed",
                    "blocked",
                    "cancelled",
                }:
                    _close_child_workflow(
                        db_path=db_path,
                        child_state=nested_state,
                        failure_class=failure_class,
                        receipt_id=receipt_id,
                        command=command,
                    )
    result = _visible_command_result(
        status=status,
        failure_class=failure_class,
        return_code=return_code,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        stream_path=stream_path,
        session=session,
        timeout_seconds=timeout_seconds,
        idle_timeout_seconds=idle_timeout_seconds,
        provider_output_idle_timeout_seconds=provider_output_idle_timeout_seconds,
        material_progress_idle_timeout_seconds=material_progress_idle_timeout_seconds,
        **command_metadata,
        payload=payload,
        child_state=child_state,
        watchdog=watchdog,
    )
    if isinstance(payload, dict):
        result["child_run_id"] = payload.get("run", {}).get("run_id")
    return result


def _terminate_visible_process_tree(proc: subprocess.Popen[Any]) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except OSError:
            proc.terminate()
    else:
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _visible_command_result(
    *,
    status: str,
    failure_class: str | None,
    return_code: int | None,
    stdout_path: Path,
    stderr_path: Path,
    stream_path: Path,
    session: dict[str, Any],
    timeout_seconds: int,
    idle_timeout_seconds: int,
    provider_output_idle_timeout_seconds: int | None,
    material_progress_idle_timeout_seconds: int | None,
    adaptive_wall_timeout_extension_seconds: int | None = None,
    adaptive_wall_timeout_max_extensions: int | None = None,
    adaptive_wall_timeout_absolute_max_seconds: int | None = None,
    adaptive_wall_timeout_progress_window_seconds: int | None = None,
    payload: Any = None,
    child_state: dict[str, Any] | None = None,
    watchdog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stdout = _read_log_text(stdout_path)
    stderr = _read_log_text(stderr_path)
    child_state = child_state or {}
    return {
        "return_code": return_code,
        "stdout_preview": stdout[-PREVIEW_LIMIT:],
        "stderr_preview": stderr[-PREVIEW_LIMIT:],
        "watchdog": watchdog or {"source": "human_visible_cli_mirrored_logs"},
        "timeout_seconds": timeout_seconds,
        "idle_timeout_seconds": idle_timeout_seconds,
        "provider_output_idle_timeout_seconds": provider_output_idle_timeout_seconds,
        "material_progress_idle_timeout_seconds": material_progress_idle_timeout_seconds,
        "adaptive_wall_timeout_extension_seconds": adaptive_wall_timeout_extension_seconds,
        "adaptive_wall_timeout_max_extensions": adaptive_wall_timeout_max_extensions,
        "adaptive_wall_timeout_absolute_max_seconds": adaptive_wall_timeout_absolute_max_seconds,
        "adaptive_wall_timeout_progress_window_seconds": adaptive_wall_timeout_progress_window_seconds,
        "status": status,
        "failure_class": failure_class,
        "payload": payload,
        "child_workflow_state": child_state,
        "child_run_id": child_state.get("run_id"),
        "child_attempt_id": child_state.get("attempt_id"),
        "watchdog_source": "human_visible_cli_mirrored_logs",
        "visible_cli_session": session,
        "visible_cli_log_paths": {
            "stdout_log_path": stdout_path.as_posix(),
            "stderr_log_path": stderr_path.as_posix(),
            "stream_log_path": stream_path.as_posix(),
            "session_path": session.get("session_path"),
        },
        "recoverable_suggestion": None
        if status == "completed"
        else _recoverable_suggestion_for_failure(failure_class or "", watchdog or {}),
    }


def _append_stream_event(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_log_text(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if not data:
        return ""
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    sample = data[: min(len(data), 4096)]
    if sample.count(b"\x00") > max(8, len(sample) // 8):
        return data.decode("utf-16-le", errors="replace")
    return data.decode("utf-8", errors="replace")


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value)).strip("_") or "task_card"


def _powershell_quote_arg(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _task_card_goal(task_card_path: Path) -> str:
    text = task_card_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip(" #")
        if stripped:
            return stripped[:240]
    return task_card_path.stem


def _runner_supports_kwarg(func: Any, name: str) -> bool:
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return True
    return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()) or name in signature.parameters


def _parse_json_from_stdout(stdout: str) -> dict[str, Any] | list[Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        best_payload: dict[str, Any] | list[Any] | None = None
        best_end = -1
        for index, char in enumerate(text):
            if char not in {"{", "["}:
                continue
            try:
                payload, relative_end = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            absolute_end = index + relative_end
            if absolute_end > best_end and isinstance(payload, (dict, list)):
                best_payload = payload
                best_end = absolute_end
            if not text[absolute_end:].strip():
                return payload if isinstance(payload, (dict, list)) else None
        return best_payload
    return None


def _failure_class_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or error.get("failure_class") or "") or None
    result = payload.get("result")
    if isinstance(result, dict):
        return str(result.get("failure_class") or "") or None
    return str(payload.get("failure_class") or "") or None


def _child_provider_activity_probe(
    *,
    db_path: Path,
    task_goal: str,
    receipt_id: str | None,
):
    cached: dict[str, Any] = {
        "provider_output_event_count": 0,
        "material_progress_event_count": 0,
    }
    last_probe_at = 0.0

    def _probe() -> dict[str, Any]:
        nonlocal cached, last_probe_at
        now = time.monotonic()
        if now - last_probe_at < 1.0:
            return cached
        last_probe_at = now
        child_state = _inspect_child_workflow_state(
            db_path=db_path,
            task_goal=task_goal,
            receipt_id=receipt_id,
        )
        run_ids = []
        if child_state.get("run_id"):
            run_ids.append(str(child_state["run_id"]))
        for nested in child_state.get("nested_child_states") or []:
            if isinstance(nested, dict) and nested.get("run_id"):
                run_ids.append(str(nested["run_id"]))
        if not run_ids:
            return cached
        try:
            with sqlite3.connect(db_path) as connection:
                connection.row_factory = sqlite3.Row
                placeholders = ",".join("?" for _ in run_ids)
                rows = connection.execute(
                    f"""
                    SELECT created_at, payload_json
                    FROM run_events
                    WHERE event_type = 'provider_stream_observed'
                      AND run_id IN ({placeholders})
                    ORDER BY created_at
                    """,
                    tuple(run_ids),
                ).fetchall()
        except sqlite3.Error:
            return cached
        provider_events: list[sqlite3.Row] = []
        material_events: list[sqlite3.Row] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                payload = {}
            if payload.get("classification") != "control":
                provider_events.append(row)
            if payload.get("is_material_progress"):
                material_events.append(row)
        cached = {
            "provider_output_event_count": len(provider_events),
            "material_progress_event_count": len(material_events),
            "last_provider_output_at": provider_events[-1]["created_at"] if provider_events else None,
            "last_material_progress_at": material_events[-1]["created_at"] if material_events else None,
        }
        return cached

    return _probe


def _failure_class_from_watchdog(proc: Any, watchdog: dict[str, Any]) -> str:
    failure_class = str(watchdog.get("timeout_failure_class") or "")
    if failure_class:
        return failure_class
    if int(getattr(proc, "returncode", 1)) == TIMEOUT_EXIT_CODE:
        return "workflowctl_child_timeout"
    return "workflowctl_child_failed"


def _classify_child_failure(
    *,
    payload: Any,
    proc: Any,
    watchdog: dict[str, Any],
    child_state: dict[str, Any],
    idle_timeout_seconds: int,
) -> str:
    payload_failure = _failure_class_from_payload(payload)
    if payload_failure:
        if payload_failure in {
            "provider_output_idle_timeout",
            "provider_no_material_progress_timeout",
        }:
            return payload_failure
        if payload_failure in {"provider_timeout", "provider_idle_timeout", "provider_wall_timeout"}:
            return "provider_timeout"
        return payload_failure
    timeout_type = str(watchdog.get("timeout_type") or "")
    if timeout_type in {"provider_output_idle_timeout", "provider_no_material_progress_timeout"}:
        return timeout_type
    if timeout_type == "adaptive_wall_timeout_exhausted":
        return "task_scope_too_large_after_adaptive_wall_timeout"
    if timeout_type == "idle_timeout" and child_state:
        heartbeat_age = child_state.get("heartbeat_age_seconds")
        if isinstance(heartbeat_age, (int, float)) and heartbeat_age <= max(idle_timeout_seconds * 1.5, idle_timeout_seconds + 30):
            return "child_stdout_silent"
        return "workflow_child_stalled"
    if timeout_type in {"idle_timeout", "wall_timeout"}:
        return "provider_timeout" if timeout_type == "wall_timeout" else _failure_class_from_watchdog(proc, watchdog)
    return _failure_class_from_watchdog(proc, watchdog)


def _child_was_terminated_by_wrapper(watchdog: dict[str, Any]) -> bool:
    return str(watchdog.get("timeout_type") or "") in {
        "idle_timeout",
        "wall_timeout",
        "adaptive_wall_timeout_exhausted",
        "provider_output_idle_timeout",
        "provider_no_material_progress_timeout",
    }


def _inspect_child_workflow_state(
    *,
    db_path: Path | None,
    task_goal: str | None,
    receipt_id: str | None,
) -> dict[str, Any]:
    if db_path is None or not task_goal:
        return {}
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            receipt = (
                connection.execute(
                    "SELECT created_at, consumed_at FROM operator_action_receipts WHERE receipt_id = ?",
                    (receipt_id,),
                ).fetchone()
                if receipt_id
                else None
            )
            lower_bound = receipt["created_at"] if receipt is not None else None
            if lower_bound:
                run = connection.execute(
                    """
                    SELECT run_id, status, created_at, updated_at
                    FROM runs
                    WHERE goal = ? AND created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (task_goal, lower_bound),
                ).fetchone()
            else:
                run = connection.execute(
                    """
                    SELECT run_id, status, created_at, updated_at
                    FROM runs
                    WHERE goal = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (task_goal,),
                ).fetchone()
            if run is None:
                return {}
            state = _workflow_state_for_run(connection, run)
            nested_rows = connection.execute(
                """
                SELECT run_id, status, created_at, updated_at
                FROM runs
                WHERE run_id <> ?
                  AND created_at >= ?
                  AND goal LIKE ?
                ORDER BY created_at
                """,
                (run["run_id"], run["created_at"], f"%{task_goal}%"),
            ).fetchall()
            nested_states = [_workflow_state_for_run(connection, nested) for nested in nested_rows]
    except sqlite3.Error as exc:
        return {"inspection_error": str(exc)}
    state["nested_child_states"] = nested_states
    return state


def _workflow_state_for_run(connection: sqlite3.Connection, run: sqlite3.Row) -> dict[str, Any]:
    run_id = run["run_id"]
    attempt = connection.execute(
        """
        SELECT attempt_id, runtime_task_id, status, created_at, closed_at, close_reason
        FROM runtime_attempts
        WHERE run_id = ?
        ORDER BY sequence_no DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    lease = connection.execute(
        """
        SELECT lease_id, adapter_name, status, heartbeat_at, lease_expires_at, released_at, release_reason
        FROM worker_leases
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    event = connection.execute(
        """
        SELECT created_at
        FROM run_events
        WHERE run_id = ? AND event_type = 'worker_heartbeat_received'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    provider_rows = connection.execute(
        """
        SELECT created_at, payload_json
        FROM run_events
        WHERE run_id = ? AND event_type = 'provider_stream_observed'
        ORDER BY created_at
        """,
        (run_id,),
    ).fetchall()
    provider_events: list[sqlite3.Row] = []
    material_events: list[sqlite3.Row] = []
    for provider_row in provider_rows:
        try:
            payload = json.loads(provider_row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            payload = {}
        if payload.get("classification") != "control":
            provider_events.append(provider_row)
        if payload.get("is_material_progress"):
            material_events.append(provider_row)
    heartbeat_at = lease["heartbeat_at"] if lease is not None else event["created_at"] if event is not None else None
    provider_visible_session: dict[str, Any] | None = None
    provider_visible_log_paths: dict[str, Any] | None = None
    latest_evidence = (
        connection.execute(
            """
            SELECT raw_execution_json
            FROM evidence
            WHERE run_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
        if _sqlite_table_exists(connection, "evidence")
        else None
    )
    if latest_evidence is not None:
        try:
            raw_execution = json.loads(latest_evidence["raw_execution_json"])
        except (TypeError, json.JSONDecodeError):
            raw_execution = {}
        metadata = raw_execution.get("metadata") if isinstance(raw_execution, dict) else {}
        if isinstance(metadata, dict):
            session = metadata.get("direct_visible_cli_session")
            log_paths = metadata.get("direct_visible_cli_log_paths")
            if isinstance(session, dict):
                provider_visible_session = session
            if isinstance(log_paths, dict):
                provider_visible_log_paths = log_paths
    return {
        "run_id": run_id,
        "run_status": run["status"],
        "run_created_at": run["created_at"],
        "run_updated_at": run["updated_at"],
        "attempt_id": attempt["attempt_id"] if attempt is not None else None,
        "runtime_task_id": attempt["runtime_task_id"] if attempt is not None else None,
        "attempt_status": attempt["status"] if attempt is not None else None,
        "worker_lease_id": lease["lease_id"] if lease is not None else None,
        "worker_lease_status": lease["status"] if lease is not None else None,
        "worker_adapter": lease["adapter_name"] if lease is not None else None,
        "worker_heartbeat_at": heartbeat_at,
        "heartbeat_age_seconds": _age_seconds(heartbeat_at),
        "provider_output_event_count": len(provider_events),
        "material_progress_event_count": len(material_events),
        "last_provider_output_at": provider_events[-1]["created_at"] if provider_events else None,
        "last_material_progress_at": material_events[-1]["created_at"] if material_events else None,
        "provider_visible_cli_session": provider_visible_session,
        "provider_visible_cli_log_paths": provider_visible_log_paths,
    }


def _close_child_workflow(
    *,
    db_path: Path | None,
    child_state: dict[str, Any],
    failure_class: str,
    receipt_id: str | None,
    command: list[str],
) -> None:
    if db_path is None or not child_state.get("run_id"):
        return
    now = datetime.now(UTC).isoformat()
    run_id = str(child_state["run_id"])
    runtime_task_id = str(child_state.get("runtime_task_id") or "")
    attempt_id = str(child_state.get("attempt_id") or "")
    lease_id = str(child_state.get("worker_lease_id") or "")
    payload = {
        "failure_class": failure_class,
        "receipt_id": receipt_id,
        "attempt_id": attempt_id or None,
        "worker_lease_id": lease_id or None,
        "command": command,
        "closed_by": "commercial_game_task_worker_cli",
        "reason": "outer_watchdog_terminated_child_workflow",
    }
    try:
        with sqlite3.connect(db_path) as connection:
            has_runtime_tasks = _sqlite_table_exists(connection, "runtime_tasks")
            has_runtime_claims = _sqlite_table_exists(connection, "runtime_claims")
            has_scheduler_lease_decisions = _sqlite_table_exists(connection, "scheduler_lease_decisions")
            has_scheduler_committed_leases = _sqlite_table_exists(connection, "scheduler_committed_leases")
            connection.execute(
                "UPDATE runs SET status = 'failed', updated_at = ? WHERE run_id = ? AND status NOT IN ('completed', 'failed', 'blocked')",
                (now, run_id),
            )
            if attempt_id:
                connection.execute(
                    """
                    UPDATE runtime_attempts
                    SET status = 'closed', closed_at = ?, close_reason = ?
                    WHERE attempt_id = ? AND status = 'current'
                    """,
                    (now, failure_class, attempt_id),
                )
            if runtime_task_id and has_runtime_tasks:
                connection.execute(
                    """
                    UPDATE runtime_tasks
                    SET status = 'failed'
                    WHERE runtime_task_id = ? AND status NOT IN ('completed', 'failed', 'cancelled')
                    """,
                    (runtime_task_id,),
                )
            if lease_id:
                connection.execute(
                    """
                    UPDATE worker_leases
                    SET status = 'released', released_at = ?, release_reason = ?
                    WHERE lease_id = ? AND status NOT IN ('released', 'expired')
                    """,
                    (now, failure_class, lease_id),
                )
            if runtime_task_id and has_runtime_claims:
                connection.execute(
                    """
                    UPDATE runtime_claims
                    SET status = 'released', released_at = ?, release_reason = ?
                    WHERE runtime_task_id = ? AND status = 'active'
                    """,
                    (now, failure_class, runtime_task_id),
                )
            if runtime_task_id and has_scheduler_lease_decisions:
                connection.execute(
                    """
                    UPDATE scheduler_lease_decisions
                    SET released_at = ?, release_reason = ?
                    WHERE runtime_task_id = ? AND released_at IS NULL
                    """,
                    (now, failure_class, runtime_task_id),
                )
            if runtime_task_id and has_scheduler_committed_leases:
                connection.execute(
                    """
                    UPDATE scheduler_committed_leases
                    SET status = 'released', released_at = ?, release_reason = ?
                    WHERE runtime_task_id = ? AND status = 'active'
                    """,
                    (now, failure_class, runtime_task_id),
                )
            connection.execute(
                """
                INSERT INTO run_events (
                  event_id, run_id, event_type, object_type, object_id, summary,
                  payload_json, schema_version, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"event_{uuid4().hex[:12]}",
                    run_id,
                    "watchdog_terminated_without_child_closure",
                    "runtime_task",
                    runtime_task_id or run_id,
                    "Outer task-card watchdog closed a child workflow after termination",
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    "v1",
                    now,
                ),
            )
            connection.commit()
    except sqlite3.Error:
        return


def _sqlite_table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )


def _age_seconds(timestamp: str | None) -> float | None:
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0.0, (datetime.now(UTC) - parsed.astimezone(UTC)).total_seconds())


def _child_run_id_from_execution(executed: dict[str, Any], payload: Any) -> str | None:
    if isinstance(executed.get("child_run_id"), str):
        return executed["child_run_id"]
    if isinstance(payload, dict):
        run_payload = payload.get("run")
        if isinstance(run_payload, dict):
            return run_payload.get("run_id")
    state = executed.get("child_workflow_state")
    if isinstance(state, dict):
        return state.get("run_id")
    return None


def _child_attempt_id_from_execution(executed: dict[str, Any]) -> str | None:
    if isinstance(executed.get("child_attempt_id"), str):
        return executed["child_attempt_id"]
    state = executed.get("child_workflow_state")
    if isinstance(state, dict):
        return state.get("attempt_id")
    return None


def _worker_adapter_from_execution(executed: dict[str, Any], payload: Any) -> str | None:
    state = executed.get("child_workflow_state")
    if isinstance(state, dict) and isinstance(state.get("worker_adapter"), str):
        return state["worker_adapter"]
    if isinstance(payload, dict) and isinstance(payload.get("capability_adapter"), str):
        return payload["capability_adapter"]
    return None


def _recoverable_suggestion_for_failure(failure_class: str, watchdog: dict[str, Any]) -> str:
    if failure_class == "provider_output_idle_timeout":
        return "resume_with_fresh_receipt_after_provider_output_idle_restart"
    if failure_class == "provider_no_material_progress_timeout":
        return "resume_with_fresh_receipt_or_split_task_after_no_material_progress"
    if failure_class == "child_stdout_silent":
        return "resume_with_fresh_receipt_without_treating_db_active_child_as_provider_timeout"
    if failure_class == "workflow_child_stalled":
        return "resume_from_next_incomplete_task_card_after_closed_child_run"
    if failure_class == "provider_timeout":
        return "verify_provider_live_proof_or_switch_to_verified_provider_then_resume_with_fresh_receipt"
    if failure_class == "task_scope_too_large_after_adaptive_wall_timeout":
        return "split_or_narrow_task_after_adaptive_wall_timeout_exhausted"
    return str(watchdog.get("recovery_suggestion") or "Inspect child workflow stdout/stderr and rerun the task card.")


def _mutation_result_from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("pr_ready_summary")
    if isinstance(summary, dict) and isinstance(summary.get("mutation_result"), dict):
        return summary["mutation_result"]
    orchestration = payload.get("orchestration")
    if isinstance(orchestration, dict):
        role_progress = orchestration.get("role_progress")
        if isinstance(role_progress, dict):
            coder = role_progress.get("coder")
            if isinstance(coder, dict):
                mutation_report = coder.get("mutation_report")
                if isinstance(mutation_report, dict) and isinstance(mutation_report.get("mutation_result"), dict):
                    return mutation_report["mutation_result"]
    run_payload = payload.get("run")
    if isinstance(run_payload, dict) and isinstance(run_payload.get("mutation_result"), dict):
        return run_payload["mutation_result"]
    return {}


def _implementation_status_from_payload(
    *,
    executed: dict[str, Any],
    payload: Any,
    mutation_result: dict[str, Any],
) -> dict[str, str | None]:
    if executed.get("status") != "completed":
        return {
            "status": "failed",
            "failure_class": str(executed.get("failure_class") or "task_card_patch_failed"),
            "readiness": None,
        }
    summary = payload.get("pr_ready_summary") if isinstance(payload, dict) and isinstance(payload.get("pr_ready_summary"), dict) else {}
    readiness = str(summary.get("readiness") or "")
    review_decision = str(payload.get("review_decision") or _summary_review_decision(summary) or "")
    changed_files = _changed_files_from_summary(mutation_result=mutation_result, summary=summary)
    tests_status = _summary_tests_status(summary, mutation_result)
    if tests_status == "patch_generation_failed":
        return {"status": "failed", "failure_class": "provider_execution_failed", "readiness": readiness or None}
    if tests_status == "patch_parse_failed":
        return {"status": "failed", "failure_class": "same_project_patch_parse_failed", "readiness": readiness or None}
    if tests_status == "patch_apply_failed":
        return {"status": "failed", "failure_class": "same_project_patch_apply_failed", "readiness": readiness or None}
    if readiness and readiness != "ready":
        if review_decision == "fail":
            return {"status": "failed", "failure_class": "same_project_patch_review_failed", "readiness": readiness}
        if not changed_files:
            return {"status": "failed", "failure_class": "same_project_patch_no_changed_files", "readiness": readiness}
        if tests_status not in {"passed"}:
            return {"status": "failed", "failure_class": "same_project_patch_tests_not_passed", "readiness": readiness}
        return {"status": "completed", "failure_class": None, "readiness": "ready_via_orchestration_coder"}
    if not changed_files:
        return {"status": "failed", "failure_class": "same_project_patch_no_changed_files", "readiness": readiness or None}
    if review_decision == "fail":
        return {"status": "failed", "failure_class": "same_project_patch_review_failed", "readiness": readiness or None}
    if tests_status and tests_status not in {"passed"}:
        return {"status": "failed", "failure_class": "same_project_patch_tests_not_passed", "readiness": readiness or None}
    return {"status": "completed", "failure_class": None, "readiness": readiness or "ready"}


def _changed_files_from_summary(*, mutation_result: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    changed_files = mutation_result.get("changed_files")
    if isinstance(changed_files, list):
        return [str(item) for item in changed_files if str(item)]
    bounded_patch = summary.get("bounded_patch") if isinstance(summary.get("bounded_patch"), dict) else {}
    summary_changed = bounded_patch.get("changed_files")
    if isinstance(summary_changed, list):
        return [str(item) for item in summary_changed if str(item)]
    return []


def _summary_review_decision(summary: dict[str, Any]) -> str | None:
    review = summary.get("review") if isinstance(summary.get("review"), dict) else {}
    value = review.get("latest_review_decision")
    return str(value) if value is not None else None


def _summary_tests_status(summary: dict[str, Any], mutation_result: dict[str, Any]) -> str | None:
    tests = summary.get("tests") if isinstance(summary.get("tests"), dict) else {}
    if mutation_result.get("final_test_status") is not None:
        return str(mutation_result.get("final_test_status"))
    if tests.get("status") is not None:
        return str(tests.get("status"))
    return None
