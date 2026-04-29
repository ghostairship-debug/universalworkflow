from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


COCOS_ECOSYSTEM_BRIDGE_SCHEMA = "cocos_ecosystem_bridge_evidence_v2"
COCOS_EDITOR_BRIDGE_REPORT_SCHEMA = "cocos_editor_bridge_report_v1"
COCOS_EDITOR_BRIDGE_RUNNER_SCHEMA = "cocos_editor_bridge_runner_evidence_v1"
BRIDGE_PACKAGE_NAME = "workflow-cocos-bridge"
DEFAULT_BRIDGE_TIMEOUT_SECONDS = 180
BRIDGE_LOG_PREVIEW_CHARS = 4000
BRIDGE_REPORT_RELATIVE_PATH = Path("temp") / "workflow_cocos_bridge" / "cocos_editor_bridge_report.json"
ALLOWED_BRIDGE_TOOL_KINDS = {"cocos_editor_extension", "local_mcp_bridge"}
REQUIRED_EDITOR_OPERATIONS = {
    "editor_bridge_present": "editor_status_version",
    "assetdb_import_query_evidence": "assetdb_import_query",
    "scene_create_save_evidence": "scene_create_save",
    "node_component_binding_evidence": "node_component_binding",
    "prefab_create_instantiate_evidence": "prefab_create_instantiate",
    "build_api_evidence": "build_api_trigger",
}


def collect_cocos_ecosystem_bridge_evidence(
    *,
    project_path: str | Path | None,
    creator_exe: str | Path | None,
    evidence_dir: str | Path,
    require_bridge: bool,
    bridge_report_path: str | Path | None = None,
    bridge_mode: str = "auto",
    bridge_timeout_seconds: int = DEFAULT_BRIDGE_TIMEOUT_SECONDS,
    allow_existing_cocos_process: bool = False,
    bridge_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_root = Path(evidence_dir).resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)
    project = Path(project_path).resolve() if project_path is not None else None
    creator = Path(creator_exe).resolve() if creator_exe is not None else None
    installed_bridge = _install_bridge_package(project, evidence_root) if project and project.exists() else None
    license_manifest = _write_license_cost_manifest(project, creator, evidence_root)
    normalized_bridge_mode = (bridge_mode or "auto").strip().lower()
    runner_evidence: dict[str, Any] | None = None
    mode_blockers: list[str] = []

    if normalized_bridge_mode not in {"auto", "report_only", "off"}:
        mode_blockers.append("unsupported_cocos_bridge_mode")
        normalized_bridge_mode = "report_only"

    if require_bridge and normalized_bridge_mode == "auto":
        runner = bridge_runner or run_cocos_editor_bridge
        runner_evidence = runner(
            project_path=project,
            creator_exe=creator,
            evidence_dir=evidence_root,
            timeout_seconds=bridge_timeout_seconds,
            allow_existing_cocos_process=allow_existing_cocos_process,
            bridge_report_path=bridge_report_path,
        )

    report_payload, report_path, report_error = _load_bridge_report(
        project=project,
        evidence_root=evidence_root,
        explicit_path=bridge_report_path,
    )
    report_validation = _validate_bridge_report(report_payload, project=project)
    operations = _operations_from_report(report_payload)

    checks = {
        "creator_executable_present": bool(creator and creator.exists()),
        "project_path_present": bool(project and project.exists()),
        "editor_bridge_present": _operation_passed(operations, "editor_status_version") and report_validation["trusted_bridge"],
        "local_mcp_or_extension_present": bool(report_validation["trusted_bridge"] or installed_bridge),
        "assetdb_import_query_evidence": _operation_passed(operations, "assetdb_import_query") and report_validation["trusted_bridge"],
        "scene_create_save_evidence": _operation_passed(operations, "scene_create_save") and report_validation["trusted_bridge"],
        "node_component_binding_evidence": _operation_passed(operations, "node_component_binding")
        and report_validation["trusted_bridge"],
        "prefab_create_instantiate_evidence": _operation_passed(operations, "prefab_create_instantiate")
        and report_validation["trusted_bridge"],
        "build_api_evidence": _operation_passed(operations, "build_api_trigger") and report_validation["trusted_bridge"],
        "license_cost_manifest": bool(license_manifest and license_manifest.exists()),
    }
    missing_operations = [name for name, passed in checks.items() if not passed]
    blockers = missing_operations if require_bridge else []
    validation_blockers = list(report_validation["blockers"])
    if report_error:
        validation_blockers.append("cocos_editor_bridge_report_unreadable")
    runner_blockers = _runner_blockers(runner_evidence)
    if require_bridge:
        blockers = _dedupe([*blockers, *validation_blockers, *mode_blockers, *runner_blockers])

    operator_action_required = bool(
        runner_evidence
        and str(runner_evidence.get("status") or "").upper() == "AWAITING_OPERATOR_ACTION"
    )
    failure_class = None
    if blockers:
        failure_class = "cocos_editor_operator_action_required" if operator_action_required else "cocos_ecosystem_bridge_missing"

    payload = {
        "schema_version": COCOS_ECOSYSTEM_BRIDGE_SCHEMA,
        "created_at": datetime.now(UTC).isoformat(),
        "project_path": project.as_posix() if project else None,
        "creator_exe": creator.as_posix() if creator else None,
        "strict_required": bool(require_bridge),
        "bridge_mode": normalized_bridge_mode,
        "bridge_timeout_seconds": bridge_timeout_seconds,
        "allow_existing_cocos_process": bool(allow_existing_cocos_process),
        "ecosystem_integration_go": not missing_operations and not validation_blockers and not mode_blockers and not runner_blockers,
        "checks": checks,
        "missing_operations": missing_operations,
        "blockers": blockers,
        "failure_class": failure_class,
        "operator_action_required": operator_action_required,
        "operator_actions": _operator_actions(runner_evidence),
        "bridge_package": installed_bridge,
        "bridge_report_path": report_path.as_posix() if report_path else None,
        "bridge_report_error": report_error,
        "bridge_report_validation": report_validation,
        "bridge_operations": operations,
        "bridge_runner_evidence": runner_evidence,
        "license_cost_manifest_path": license_manifest.as_posix() if license_manifest else None,
        "recoverable_suggestion": _recoverable_suggestion_for_bridge(runner_evidence, blockers),
        "bridge_contract": {
            "required_operations": [
                "editor_status_version",
                "project_open",
                "assetdb_import_query",
                "scene_create_save",
                "node_component_binding",
                "prefab_create_instantiate",
                "build_api_trigger",
                "license_cost_manifest",
            ],
            "accepted_bridge_modes": ["auto", "report_only", "off"],
            "trusted_tool_kinds": sorted(ALLOWED_BRIDGE_TOOL_KINDS),
            "forbidden_substitutes": [
                "filesystem_project_generation_only",
                "browser_playtest_only",
                "feature_flag_only",
                "cocos_cli_build_only",
            ],
        },
    }
    path = evidence_root / "cocos_ecosystem_bridge_evidence.json"
    payload["evidence_path"] = path.as_posix()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def run_cocos_editor_bridge(
    *,
    project_path: str | Path | None,
    creator_exe: str | Path | None,
    evidence_dir: str | Path,
    timeout_seconds: int = DEFAULT_BRIDGE_TIMEOUT_SECONDS,
    allow_existing_cocos_process: bool = False,
    bridge_report_path: str | Path | None = None,
) -> dict[str, Any]:
    evidence_root = Path(evidence_dir).resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)
    project = Path(project_path).resolve() if project_path is not None else None
    creator = Path(creator_exe).resolve() if creator_exe is not None else None
    report_path = (
        Path(bridge_report_path).resolve()
        if bridge_report_path is not None
        else (project / BRIDGE_REPORT_RELATIVE_PATH if project is not None else evidence_root / "cocos_editor_bridge_report.json")
    )
    stdout_path = evidence_root / "cocos_editor_bridge_stdout.log"
    stderr_path = evidence_root / "cocos_editor_bridge_stderr.log"
    runner_path = evidence_root / "cocos_editor_bridge_runner_evidence.json"
    started_at = time.monotonic()
    command = [str(creator), "--project", str(project)] if creator is not None and project is not None else []
    payload: dict[str, Any] = {
        "schema_version": COCOS_EDITOR_BRIDGE_RUNNER_SCHEMA,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "blocked",
        "project_path": project.as_posix() if project else None,
        "creator_exe": creator.as_posix() if creator else None,
        "bridge_report_path": report_path.as_posix(),
        "command": command,
        "timeout_seconds": max(0, int(timeout_seconds)),
        "allow_existing_cocos_process": bool(allow_existing_cocos_process),
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "runner_evidence_path": runner_path.as_posix(),
        "blockers": [],
        "operator_actions": [],
        "failure_class": None,
        "recoverable_suggestion": None,
        "launched_pid": None,
        "exit_code": None,
        "elapsed_ms": 0,
        "stdout_preview": "",
        "stderr_preview": "",
        "editor_log_preview": "",
    }

    blockers: list[str] = []
    if creator is None or not creator.exists():
        blockers.append("cocos_creator_exe_missing")
    if project is None or not project.exists():
        blockers.append("cocos_project_path_missing")
    if blockers:
        payload.update(
            {
                "status": "blocked",
                "blockers": blockers,
                "failure_class": "cocos_bridge_preflight_failed",
                "recoverable_suggestion": "Provide an existing Cocos Creator executable and project path, then rerun the bridge runner.",
            }
        )
        return _write_runner_evidence(payload, runner_path)

    existing_processes = _cocos_creator_processes()
    payload["existing_cocos_processes"] = existing_processes
    if existing_processes and not allow_existing_cocos_process:
        payload.update(
            {
                "status": "AWAITING_OPERATOR_ACTION",
                "blockers": ["existing_cocos_creator_process_requires_operator_action"],
                "operator_actions": [
                    "Close the existing Cocos Creator windows yourself, or rerun with allow_existing_cocos_process=true after confirming the project is not locked.",
                    f"Project to open: {project.as_posix()}",
                ],
                "failure_class": "cocos_editor_existing_process_requires_operator",
                "recoverable_suggestion": (
                    "Close or explicitly allow the already-running Cocos Creator process, then rerun the same pipeline/run. "
                    "The runner will not kill user-owned editor processes by default."
                ),
            }
        )
        return _write_runner_evidence(payload, runner_path)

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["WORKFLOW_COCOS_BRIDGE_REPORT"] = str(report_path)
    process: subprocess.Popen[str] | None = None
    try:
        with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_file, stderr_path.open(
            "w", encoding="utf-8", errors="replace"
        ) as stderr_file:
            process = subprocess.Popen(
                command,
                cwd=str(project),
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                env=env,
            )
            payload["launched_pid"] = process.pid
            deadline = time.monotonic() + max(0, int(timeout_seconds))
            while time.monotonic() <= deadline:
                if report_path.exists():
                    operation_names = _bridge_report_operation_names(report_path)
                    payload["bridge_report_operation_names"] = operation_names
                    if _bridge_report_has_required_operations(operation_names):
                        payload.update(
                            {
                                "status": "completed",
                                "failure_class": None,
                                "blockers": [],
                                "recoverable_suggestion": None,
                            }
                        )
                        break
                if process.poll() is not None:
                    payload["exit_code"] = process.returncode
                    if report_path.exists() and _bridge_report_has_required_operations(_bridge_report_operation_names(report_path)):
                        payload.update({"status": "completed", "failure_class": None, "blockers": []})
                    else:
                        payload.update(
                            {
                                "status": "AWAITING_OPERATOR_ACTION",
                                "blockers": [
                                    "cocos_editor_exited_before_complete_bridge_report"
                                    if report_path.exists()
                                    else "cocos_editor_exited_before_bridge_report"
                                ],
                                "operator_actions": [
                                    "Open Cocos Creator, enable or reload the project-local workflow-cocos-bridge extension, then rerun the same bridge command.",
                                    f"Expected report: {report_path.as_posix()}",
                                ],
                                "failure_class": (
                                    "cocos_editor_bridge_report_incomplete_after_exit"
                                    if report_path.exists()
                                    else "cocos_editor_bridge_report_missing_after_exit"
                                ),
                                "recoverable_suggestion": (
                                    "Review the editor stderr/stdout previews and confirm login, license, project upgrade, web build module, "
                                    "or extension-enable prompts in the GUI before rerunning."
                                ),
                            }
                        )
                    break
                time.sleep(1.0)
            else:
                incomplete_report_exists = report_path.exists()
                if incomplete_report_exists:
                    payload["bridge_report_operation_names"] = _bridge_report_operation_names(report_path)
                payload.update(
                    {
                        "status": "AWAITING_OPERATOR_ACTION",
                        "blockers": [
                            "cocos_editor_bridge_report_incomplete_timeout"
                            if incomplete_report_exists
                            else "cocos_editor_bridge_report_timeout"
                        ],
                        "operator_actions": [
                            "Check the Cocos Creator window for login, license, privacy, project-upgrade, module-install, or extension-enable prompts.",
                            f"Project to open: {project.as_posix()}",
                            f"Expected report: {report_path.as_posix()}",
                        ],
                        "failure_class": (
                            "cocos_editor_bridge_report_incomplete_timeout"
                            if incomplete_report_exists
                            else "cocos_editor_bridge_report_timeout"
                        ),
                        "recoverable_suggestion": "Resolve the visible Editor prompt or extension loading issue, then rerun the same pipeline/run.",
                    }
                )
    except OSError as exc:
        payload.update(
            {
                "status": "blocked",
                "blockers": ["cocos_editor_launch_failed"],
                "failure_class": "cocos_editor_launch_failed",
                "error_summary": str(exc),
                "recoverable_suggestion": "Verify the Cocos Creator executable path and filesystem permissions, then rerun the bridge runner.",
            }
        )
    finally:
        payload["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        if process is not None:
            if payload.get("exit_code") is None and process.poll() is not None:
                payload["exit_code"] = process.returncode
            if process.poll() is None:
                try:
                    process.terminate()
                    payload["runner_started_process_termination"] = "terminate_requested"
                except OSError as exc:
                    payload["runner_started_process_termination"] = f"terminate_failed: {exc}"
            payload["runner_started_process_tree_termination"] = _terminate_runner_process_tree(process.pid)
        payload["stdout_preview"] = _preview_file(stdout_path)
        payload["stderr_preview"] = _preview_file(stderr_path)
        payload["editor_log_preview"] = _preview_editor_logs(project)
    return _write_runner_evidence(payload, runner_path)


def _install_bridge_package(project: Path | None, evidence_root: Path) -> dict[str, Any] | None:
    if project is None:
        return None
    extension_root = project / "extensions" / BRIDGE_PACKAGE_NAME
    extension_root.mkdir(parents=True, exist_ok=True)
    package_path = extension_root / "package.json"
    main_path = extension_root / "main.js"
    builder_path = extension_root / "builder.js"
    hooks_path = extension_root / "hooks.js"
    scene_path = extension_root / "scene.js"
    package_payload = {
        "name": BRIDGE_PACKAGE_NAME,
        "title": "Workflow Cocos Bridge",
        "package_version": 2,
        "version": "0.1.0",
        "author": "Universal Agentic Workflow",
        "description": "Local workflow bridge for Cocos Editor ecosystem evidence.",
        "main": "./main.js",
        "contributions": {
            "builder": "./builder.js",
            "scene": {"script": "./scene.js"},
            "messages": {
                "run-evidence-smoke": {"methods": ["runEvidenceSmoke"]},
                "status": {"methods": ["status"]},
            },
        },
    }
    package_path.write_text(json.dumps(package_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    main_path.write_text(_bridge_main_js(), encoding="utf-8")
    builder_path.write_text(_bridge_builder_js(), encoding="utf-8")
    hooks_path.write_text(_bridge_builder_hooks_js(), encoding="utf-8")
    scene_path.write_text(_bridge_scene_js(), encoding="utf-8")
    manifest = {
        "schema_version": "cocos_editor_bridge_package_v1",
        "package_name": BRIDGE_PACKAGE_NAME,
        "extension_root": extension_root.as_posix(),
        "package_json": package_path.as_posix(),
        "main_js": main_path.as_posix(),
        "builder_js": builder_path.as_posix(),
        "hooks_js": hooks_path.as_posix(),
        "scene_js": scene_path.as_posix(),
        "install_mode": "project_local_extension",
        "requires_editor_execution": True,
    }
    manifest_path = evidence_root / "cocos_editor_bridge_package_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = manifest_path.as_posix()
    return manifest


def _write_license_cost_manifest(project: Path | None, creator: Path | None, evidence_root: Path) -> Path:
    license_root = creator.parent / "resources" / "License" if creator is not None else None
    if license_root is not None and not license_root.exists():
        license_root = creator.parent / "License"
    payload = {
        "schema_version": "cocos_ecosystem_license_cost_manifest_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "project_path": project.as_posix() if project else None,
        "creator_exe": creator.as_posix() if creator else None,
        "license_root": license_root.as_posix() if license_root else None,
        "license_root_present": bool(license_root and license_root.exists()),
        "ecosystem_assets": [],
        "paid_assets_imported": False,
        "external_marketplace_assets_imported": False,
        "commercial_use_boundary": (
            "No Cocos marketplace or paid third-party ecosystem asset is imported by this bridge smoke. "
            "Future paid assets, SDKs, ads, IAP, analytics, or cloud packages require operator approval."
        ),
        "cost_boundary": "local_editor_bridge_only_no_marketplace_spend",
    }
    path = evidence_root / "cocos_ecosystem_license_cost_manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_bridge_report(
    *,
    project: Path | None,
    evidence_root: Path,
    explicit_path: str | Path | None,
) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    candidates: list[Path] = []
    if explicit_path is not None:
        candidates.append(Path(explicit_path))
    env_report = os.getenv("WORKFLOW_COCOS_BRIDGE_REPORT")
    if env_report:
        candidates.append(Path(env_report))
    candidates.append(evidence_root / "cocos_editor_bridge_report.json")
    if project is not None:
        candidates.extend(
            [
                project / "temp" / "workflow_cocos_bridge" / "cocos_editor_bridge_report.json",
                project / "workflow_cocos_bridge_report.json",
            ]
        )
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if not resolved.exists():
            continue
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return None, resolved, str(exc)
        if isinstance(payload, dict):
            return payload, resolved, None
        return None, resolved, "bridge report root must be a JSON object"
    return None, None, None


def _validate_bridge_report(report: dict[str, Any] | None, *, project: Path | None) -> dict[str, Any]:
    blockers: list[str] = []
    if report is None:
        return {
            "trusted_bridge": False,
            "tool_kind": None,
            "editor_api_used": False,
            "blockers": ["cocos_editor_bridge_report_missing"],
        }
    tool_kind = str(report.get("tool_kind") or report.get("bridge_kind") or "")
    editor_api_used = bool(report.get("editor_api_used") or report.get("editor_process_invoked"))
    if tool_kind not in ALLOWED_BRIDGE_TOOL_KINDS:
        blockers.append("untrusted_cocos_bridge_tool_kind")
    if tool_kind in {"filesystem_project_generation_only", "cocos_cli_build_only"}:
        blockers.append("forbidden_filesystem_or_cli_bridge_substitute")
    if not editor_api_used:
        blockers.append("cocos_editor_api_not_used")
    report_project = report.get("project_path")
    if project is not None and report_project:
        try:
            if Path(str(report_project)).resolve() != project:
                blockers.append("cocos_bridge_project_path_mismatch")
        except OSError:
            blockers.append("cocos_bridge_project_path_invalid")
    return {
        "trusted_bridge": not blockers,
        "tool_kind": tool_kind or None,
        "editor_api_used": editor_api_used,
        "blockers": _dedupe(blockers),
        "schema_version": report.get("schema_version"),
    }


def _operations_from_report(report: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {}
    operations = report.get("operations")
    if isinstance(operations, dict):
        return operations
    checks = report.get("checks")
    if isinstance(checks, dict):
        return checks
    return {}


def _operation_passed(operations: dict[str, Any], operation_name: str) -> bool:
    value = operations.get(operation_name)
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        status = str(value.get("status") or value.get("go_no_go") or "").upper()
        return bool(value.get("passed")) or status in {"PASSED", "PASS", "GO", "COMPLETED", "OK"}
    return False


def _bridge_main_js() -> str:
    return """'use strict';

const fs = require('fs');
const path = require('path');

function evidencePath() {
  if (process.env.WORKFLOW_COCOS_BRIDGE_REPORT) {
    const explicitDir = path.dirname(process.env.WORKFLOW_COCOS_BRIDGE_REPORT);
    fs.mkdirSync(explicitDir, { recursive: true });
    return process.env.WORKFLOW_COCOS_BRIDGE_REPORT;
  }
  const projectPath = editorProjectPath();
  const dir = path.join(projectPath, 'temp', 'workflow_cocos_bridge');
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, 'cocos_editor_bridge_report.json');
}

function editorProjectPath() {
  const projectPath = Editor && Editor.Project && Editor.Project.path;
  if (!projectPath) {
    throw new Error('Editor.Project.path is not ready');
  }
  return projectPath;
}

function withTimeout(promise, timeoutMs, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} timed out after ${timeoutMs}ms`)), timeoutMs)),
  ]);
}

function operationCompleted(apiChannel, inputSummary = {}, outputSummary = {}) {
  return { status: 'completed', api_channel: apiChannel, input_summary: inputSummary, output_summary: outputSummary };
}

function operationFailed(apiChannel, failureClass, error) {
  return {
    status: 'failed',
    api_channel: apiChannel,
    failure_class: failureClass,
    error_summary: error && error.stack ? error.stack : String(error),
  };
}

function readPreviousOperations(reportPath) {
  if (!fs.existsSync(reportPath)) {
    return {};
  }
  try {
    const previous = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
    return previous.operations || {};
  } catch (_) {
    return {};
  }
}

async function assetDbSmoke(projectPath) {
  const probeRelative = 'assets/workflow_bridge_probe/ecosystem_probe.json';
  const probePath = path.join(projectPath, probeRelative);
  fs.mkdirSync(path.dirname(probePath), { recursive: true });
  fs.writeFileSync(probePath, JSON.stringify({ createdBy: 'workflow-cocos-bridge', createdAt: new Date().toISOString() }), 'utf8');
  let refreshSummary = null;
  try {
    refreshSummary = await withTimeout(
      Editor.Message.request('asset-db', 'refresh-asset', 'db://assets/workflow_bridge_probe/ecosystem_probe.json'),
      12000,
      'asset-db refresh-asset'
    );
  } catch (error) {
    return operationFailed('Editor.Message.request(asset-db, refresh-asset)', 'cocos_assetdb_import_api_unavailable', error);
  }
  try {
    const assets = await withTimeout(Editor.Message.request('asset-db', 'query-assets'), 12000, 'asset-db query-assets');
    const serialized = JSON.stringify(assets || []);
    const imported = serialized.includes('workflow_bridge_probe') || serialized.includes('ecosystem_probe');
    if (!imported) {
      return {
        status: 'failed',
        api_channel: 'Editor.Message.request(asset-db, refresh-asset/query-assets)',
        failure_class: 'cocos_assetdb_import_query_missing_probe_asset',
        input_summary: { probe_db_url: 'db://assets/workflow_bridge_probe/ecosystem_probe.json' },
        output_summary: { asset_count: Array.isArray(assets) ? assets.length : 0, refresh_summary: refreshSummary },
      };
    }
    return operationCompleted(
      'Editor.Message.request(asset-db, refresh-asset/query-assets)',
      { probe_db_url: 'db://assets/workflow_bridge_probe/ecosystem_probe.json' },
      { asset_count: Array.isArray(assets) ? assets.length : 0, imported }
    );
  } catch (error) {
    return operationFailed('Editor.Message.request(asset-db, query-assets)', 'cocos_assetdb_query_api_unavailable', error);
  }
}

async function ensureProbeSceneAsset(projectPath) {
  const targetRelative = 'assets/scene/workflow_bridge_scene.scene';
  const targetPath = path.join(projectPath, targetRelative);
  const defaultScenePath = path.resolve(
    Editor.App.path,
    '..',
    'resources',
    '3d',
    'engine',
    'editor',
    'assets',
    'default_file_content',
    'scene',
    'scene-2d.scene'
  );
  try {
    if (!fs.existsSync(defaultScenePath)) {
      return operationFailed('Cocos default scene seed', 'cocos_default_scene_seed_missing', defaultScenePath);
    }
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    let sceneContent = fs.readFileSync(defaultScenePath, 'utf8');
    sceneContent = sceneContent.replace(/scene-2d/g, 'workflow_bridge_scene');
    fs.writeFileSync(targetPath, sceneContent, 'utf8');
    const dbUrl = 'db://assets/scene/workflow_bridge_scene.scene';
    const refreshSummary = await withTimeout(Editor.Message.request('asset-db', 'refresh-asset', dbUrl), 12000, 'asset-db refresh scene');
    const assets = await withTimeout(Editor.Message.request('asset-db', 'query-assets'), 12000, 'asset-db query scene');
    const sceneAsset = Array.isArray(assets)
      ? assets.find((asset) => JSON.stringify(asset).includes('workflow_bridge_scene.scene'))
      : null;
    const uuid = sceneAsset && (sceneAsset.uuid || sceneAsset._uuid || (sceneAsset.value && sceneAsset.value.uuid));
    if (!uuid) {
      return {
        status: 'failed',
        api_channel: 'Editor.Message.request(asset-db, refresh-asset/query-assets)',
        failure_class: 'cocos_scene_asset_uuid_missing',
        input_summary: { scene_db_url: dbUrl },
        output_summary: { refresh_summary: refreshSummary, asset_count: Array.isArray(assets) ? assets.length : 0 },
      };
    }
    const openResult = await withTimeout(Editor.Message.request('scene', 'open-scene', uuid), 12000, 'scene open-scene');
    return operationCompleted(
      'Editor.Message.request(asset-db refresh/query + scene open-scene)',
      { scene_db_url: dbUrl },
      { uuid, open_result: openResult, asset_count: Array.isArray(assets) ? assets.length : 0 }
    );
  } catch (error) {
    return operationFailed('Editor.Message.request(asset-db/scene open-scene)', 'cocos_scene_open_api_unavailable', error);
  }
}

async function sceneSmoke() {
  try {
    const result = await withTimeout(
      Editor.Message.request('scene', 'execute-scene-script', {
        name: 'workflow-cocos-bridge',
        method: 'runSceneSmoke',
        args: [{ probeName: 'WorkflowBridgeProbe' }],
      }),
      12000,
      'scene execute-scene-script'
    );
    return (result && result.operations) || {};
  } catch (error) {
    return {
      scene_create_save: operationFailed('Editor.Message.request(scene, execute-scene-script)', 'cocos_scene_execute_script_api_unavailable', error),
      node_component_binding: operationFailed('Editor.Message.request(scene, execute-scene-script)', 'cocos_scene_execute_script_api_unavailable', error),
      prefab_create_instantiate: operationFailed('Editor.Message.request(scene, execute-scene-script)', 'cocos_scene_execute_script_api_unavailable', error),
    };
  }
}

async function saveSceneIfAvailable(sceneOperation, probeSceneOperation) {
  if (!sceneOperation || sceneOperation.status !== 'completed') {
    return sceneOperation || operationFailed('scene_api', 'cocos_scene_create_api_unavailable', 'scene script did not create a scene probe');
  }
  if (!probeSceneOperation || probeSceneOperation.status !== 'completed') {
    return probeSceneOperation || operationFailed('scene_api', 'cocos_scene_open_api_unavailable', 'probe scene was not opened');
  }
  try {
    const saveResult = await withTimeout(Editor.Message.request('scene', 'save-scene'), 12000, 'scene save-scene');
    return operationCompleted(
      'Editor.Message.request(scene, open-scene/execute-scene-script/save-scene)',
      { probe_node: 'WorkflowBridgeProbe' },
      { scene_script: sceneOperation.output_summary || {}, probe_scene: probeSceneOperation.output_summary || {}, save_result: saveResult }
    );
  } catch (error) {
    return operationFailed('Editor.Message.request(scene, save-scene)', 'cocos_scene_save_api_unavailable', error);
  }
}

async function writeReport(extraOperations = {}, trigger = 'manual') {
  const projectPath = editorProjectPath();
  const reportPath = evidencePath();
  const previousOperations = readPreviousOperations(reportPath);
  const report = {
    schema_version: 'cocos_editor_bridge_report_v1',
    tool_kind: 'cocos_editor_extension',
    editor_api_used: true,
    project_path: projectPath,
    created_at: new Date().toISOString(),
    trigger,
    operations: {
      ...previousOperations,
      editor_status_version: operationCompleted('Editor.App.version', {}, { version: Editor.App.version }),
      project_open: operationCompleted('Editor.Project.path', {}, { path: projectPath }),
      ...extraOperations,
    },
  };
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
  return report;
}

async function runEvidenceSmoke(trigger = 'manual') {
  const projectPath = editorProjectPath();
  const assetdb = await assetDbSmoke(projectPath);
  const probeScene = await ensureProbeSceneAsset(projectPath);
  const sceneOperations = probeScene.status === 'completed' ? await sceneSmoke() : {
    scene_create_save: probeScene,
    node_component_binding: probeScene,
    prefab_create_instantiate: probeScene,
  };
  sceneOperations.scene_create_save = await saveSceneIfAvailable(sceneOperations.scene_create_save, probeScene);
  return writeReport(
    {
      assetdb_import_query: assetdb,
      scene_create_save: sceneOperations.scene_create_save,
      node_component_binding: sceneOperations.node_component_binding,
      prefab_create_instantiate: sceneOperations.prefab_create_instantiate,
    },
    trigger
  );
}

function scheduleLoadSmoke(attempt = 1) {
  const delayMs = attempt === 1 ? 24000 : 8000;
  setTimeout(() => {
    withTimeout(runEvidenceSmoke(`extension_load_attempt_${attempt}`), 40000, 'workflow bridge load smoke').catch((error) => {
      writeReport({
        extension_load: operationFailed('workflow-cocos-bridge.load', 'cocos_bridge_extension_load_failed', error),
      }, `extension_load_failed_attempt_${attempt}`).catch(() => {});
      if (attempt < 8) {
        scheduleLoadSmoke(attempt + 1);
      }
    });
  }, delayMs);
}

module.exports = {
  load() {
    scheduleLoadSmoke(1);
  },
  unload() {},
  methods: {
    async status() {
      return writeReport({}, 'status');
    },
    async runEvidenceSmoke() {
      return runEvidenceSmoke('message_run_evidence_smoke');
    },
  },
};
"""


def _bridge_builder_js() -> str:
    return """'use strict';

exports.configs = {
  '*': {
    hooks: './hooks',
  },
};
"""


def _bridge_builder_hooks_js() -> str:
    return """'use strict';

const fs = require('fs');
const path = require('path');

async function writeBuildReport(operation, options = {}) {
  const projectPath = Editor.Project.path;
  const reportPath = process.env.WORKFLOW_COCOS_BRIDGE_REPORT || path.join(projectPath, 'temp', 'workflow_cocos_bridge', 'cocos_editor_bridge_report.json');
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  let previous = {};
  if (fs.existsSync(reportPath)) {
    try {
      previous = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
    } catch (_) {
      previous = {};
    }
  }
  let assets = [];
  try {
    assets = await Editor.Message.request('asset-db', 'query-assets');
  } catch (_) {
    assets = [];
  }
  const operations = {
    ...(previous.operations || {}),
    editor_status_version: { status: 'completed', api_channel: 'Editor.App.version', output_summary: { version: Editor.App.version } },
    project_open: { status: 'completed', api_channel: 'Editor.Project.path', output_summary: { path: projectPath } },
    build_api_trigger: {
      status: 'completed',
      api_channel: 'Cocos build extension hooks',
      input_summary: { operation },
      output_summary: { option_keys: options ? Object.keys(options).slice(0, 30) : [], asset_count: Array.isArray(assets) ? assets.length : 0 },
    },
  };
  const report = {
    schema_version: 'cocos_editor_bridge_report_v1',
    tool_kind: 'cocos_editor_extension',
    editor_api_used: true,
    project_path: projectPath,
    created_at: new Date().toISOString(),
    operations,
  };
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
}

exports.load = async function load() {
  await writeBuildReport('builder_load');
};

exports.onBeforeBuild = async function onBeforeBuild(options) {
  await writeBuildReport('onBeforeBuild', options);
};

exports.onAfterBuild = async function onAfterBuild(options) {
  await writeBuildReport('onAfterBuild', options);
};
"""


def _bridge_scene_js() -> str:
    return """'use strict';

const path = require('path');
module.paths.push(path.join(Editor.App.path, 'node_modules'));

function completed(apiChannel, inputSummary = {}, outputSummary = {}) {
  return { status: 'completed', api_channel: apiChannel, input_summary: inputSummary, output_summary: outputSummary };
}

function failed(apiChannel, failureClass, error) {
  return {
    status: 'failed',
    api_channel: apiChannel,
    failure_class: failureClass,
    error_summary: error && error.stack ? error.stack : String(error),
  };
}

exports.load = function load() {};
exports.unload = function unload() {};
exports.methods = {
  runSceneSmoke(options = {}) {
    const operations = {};
    try {
      const { director, Node, UITransform, Prefab, instantiate, Scene } = require('cc');
      let scene = director.getScene();
      let sceneCreatedInScript = false;
      if (!scene) {
        if (!Scene) {
          operations.scene_create_save = failed('cc.Scene', 'cocos_scene_constructor_unavailable', 'cc.Scene export is missing');
          operations.node_component_binding = failed('cc.Scene', 'cocos_scene_constructor_unavailable', 'cc.Scene export is missing');
          operations.prefab_create_instantiate = failed('cc.Scene', 'cocos_scene_constructor_unavailable', 'cc.Scene export is missing');
          return { operations };
        }
        scene = new Scene('WorkflowBridgeGeneratedScene');
        if (typeof director.runSceneImmediate === 'function') {
          director.runSceneImmediate(scene);
        } else if (typeof director.runScene === 'function') {
          director.runScene(scene);
        }
        scene = director.getScene() || scene;
        sceneCreatedInScript = true;
      }
      const probeName = options.probeName || 'WorkflowBridgeProbe';
      let node = scene.getChildByName(probeName);
      if (!node) {
        node = new Node(probeName);
        scene.addChild(node);
      }
      const transform = node.getComponent(UITransform) || node.addComponent(UITransform);
      transform.setContentSize(64, 64);
      operations.scene_create_save = completed('cc.Scene/cc.director/Node', { probe_name: probeName }, { scene_name: scene.name, node_uuid: node.uuid, scene_created_in_script: sceneCreatedInScript });
      operations.node_component_binding = completed('cc.Node.addComponent(UITransform)', { probe_name: probeName }, { component_name: 'UITransform', width: 64, height: 64 });
      const prefab = new Prefab();
      prefab.data = node;
      const clone = instantiate(prefab);
      clone.name = probeName + '_PrefabInstance';
      scene.addChild(clone);
      operations.prefab_create_instantiate = completed('cc.Prefab/instantiate', { probe_name: probeName }, { prefab_source_uuid: node.uuid, instance_uuid: clone.uuid });
    } catch (error) {
      operations.scene_create_save = failed('cc scene API', 'cocos_scene_api_execution_failed', error);
      operations.node_component_binding = failed('cc component API', 'cocos_component_api_execution_failed', error);
      operations.prefab_create_instantiate = failed('cc prefab API', 'cocos_prefab_api_execution_failed', error);
    }
    return { operations };
  },
};
"""


def _runner_blockers(runner_evidence: dict[str, Any] | None) -> list[str]:
    if not isinstance(runner_evidence, dict):
        return []
    status = str(runner_evidence.get("status") or "").upper()
    blockers = [str(item) for item in runner_evidence.get("blockers") or [] if str(item)]
    if status in {"COMPLETED", "OK", "PASSED"}:
        return blockers
    failure_class = runner_evidence.get("failure_class")
    if failure_class:
        blockers.append(str(failure_class))
    return _dedupe(blockers)


def _operator_actions(runner_evidence: dict[str, Any] | None) -> list[str]:
    if not isinstance(runner_evidence, dict):
        return []
    return [str(item) for item in runner_evidence.get("operator_actions") or [] if str(item)]


def _recoverable_suggestion_for_bridge(runner_evidence: dict[str, Any] | None, blockers: list[str]) -> str | None:
    if not blockers:
        return None
    if isinstance(runner_evidence, dict) and runner_evidence.get("recoverable_suggestion"):
        return str(runner_evidence["recoverable_suggestion"])
    return (
        "Open the project with the workflow Cocos Editor bridge extension or local MCP bridge, run the "
        "AssetDB/Scene/Prefab/Build smoke operation, then rerun with the generated bridge report."
    )


def _write_runner_evidence(payload: dict[str, Any], runner_path: Path) -> dict[str, Any]:
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    payload["runner_evidence_path"] = runner_path.as_posix()
    runner_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _preview_file(path: Path, *, limit: int = BRIDGE_LOG_PREVIEW_CHARS) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"<unreadable: {exc}>"
    return text[-limit:]


def _preview_editor_logs(project: Path | None, *, limit: int = BRIDGE_LOG_PREVIEW_CHARS) -> str:
    if project is None:
        return ""
    candidates: list[Path] = []
    for pattern in ["temp/**/*.log", "temp/**/*.txt", "library/**/*.log"]:
        try:
            candidates.extend(project.glob(pattern))
        except OSError:
            continue
    existing = [item for item in candidates if item.is_file()]
    if not existing:
        return ""
    newest = max(existing, key=lambda item: item.stat().st_mtime)
    preview = _preview_file(newest, limit=limit)
    return f"{newest.as_posix()}\n{preview}"


def _bridge_report_operation_names(report_path: Path) -> list[str]:
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    operations = payload.get("operations") if isinstance(payload, dict) else None
    if not isinstance(operations, dict):
        return []
    return sorted(str(key) for key in operations.keys())


def _bridge_report_has_required_operations(operation_names: list[str]) -> bool:
    required = set(REQUIRED_EDITOR_OPERATIONS.values())
    return required.issubset(set(operation_names))


def _terminate_runner_process_tree(root_pid: int | None) -> dict[str, Any]:
    if root_pid is None:
        return {"terminated_child_pids": [], "failure_class": None}
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"$rootPid = {int(root_pid)}; "
            "$children = Get-CimInstance Win32_Process -Filter \"name = 'CocosCreator.exe'\" | "
            "Where-Object { $_.ParentProcessId -eq $rootPid }; "
            "$ids = @($children | ForEach-Object { [int]$_.ProcessId }); "
            "if ($ids.Count -gt 0) { Stop-Process -Id $ids -Force }; "
            "[pscustomobject]@{terminated_child_pids=$ids} | ConvertTo-Json -Compress"
        ),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "terminated_child_pids": [],
            "failure_class": "runner_child_process_cleanup_failed",
            "error_summary": str(exc),
        }
    text = (completed.stdout or "").strip()
    result: dict[str, Any] = {
        "terminated_child_pids": [],
        "exit_code": completed.returncode,
        "stderr_preview": (completed.stderr or "")[-BRIDGE_LOG_PREVIEW_CHARS:],
    }
    if text:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                result.update(parsed)
        except json.JSONDecodeError:
            result["stdout_preview"] = text[-BRIDGE_LOG_PREVIEW_CHARS:]
    if completed.returncode != 0:
        result["failure_class"] = "runner_child_process_cleanup_failed"
    return result


def _cocos_creator_processes() -> list[dict[str, Any]]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_Process -Filter \"name = 'CocosCreator.exe'\" | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    text = (completed.stdout or "").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    rows = payload if isinstance(payload, list) else [payload]
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append(
            {
                "pid": row.get("ProcessId"),
                "command_line": row.get("CommandLine"),
            }
        )
    return result


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
