from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.contracts import MutationContract, MutationMode, RepoMutationResult, TaskPacket
from packages.core_domain.errors import (
    MutationContractError,
    PatchApplyError,
    RepoMutationScopeError,
)
from packages.core_domain.repo_mutation import (
    apply_unified_diff,
    capture_workspace_snapshot,
    extract_touched_paths,
    hash_patch_text,
    is_path_allowed,
    normalize_allowed_paths,
    restore_workspace_snapshot,
    run_test_commands,
)
from packages.worker_adapters.base import ExecutionResult

PATCH_ONLY_PROVIDER_COMMAND_POLICY = "patch_only_no_shell"
MUTATION_CONTEXT_FILE_PREVIEW_LIMIT = 20000
MUTATION_CONTEXT_TOTAL_PREVIEW_LIMIT = 60000
MUTATION_CONTEXT_DIRECTORY_CHILD_LIMIT = 80
MUTATION_CONTEXT_INLINE_ENV_LIMIT = 12000


class RepoMutationCoordinator:
    """Coordinates guarded patch application outside the OrchestratorService facade."""

    def execute(self, adapter: Any, packet: TaskPacket) -> ExecutionResult:
        return execute_repo_mutation(adapter, packet)


def task_card_content_for_mutation(contract: MutationContract | None, *, working_directory: str) -> str | None:
    if contract is None or not contract.task_card_path:
        return None
    task_card_path = Path(contract.task_card_path)
    if not task_card_path.is_absolute():
        task_card_path = Path(working_directory) / task_card_path
    resolved = task_card_path.resolve()
    if not resolved.exists():
        raise MutationContractError(
            "task_card_path does not exist for mutation contract",
            {"task_card_path": contract.task_card_path},
        )
    return resolved.read_text(encoding="utf-8")


def read_set_context_for_mutation(contract: MutationContract | None, *, working_directory: str) -> list[dict[str, Any]]:
    if contract is None:
        return []
    root = Path(working_directory).resolve()
    remaining = MUTATION_CONTEXT_TOTAL_PREVIEW_LIMIT
    context: list[dict[str, Any]] = []
    for item in contract.read_set:
        if remaining <= 0:
            context.append({"path": item, "kind": "truncated", "exists": None})
            continue
        raw_path = Path(item)
        path = raw_path if raw_path.is_absolute() else root / raw_path
        try:
            resolved = path.resolve()
        except OSError:
            context.append({"path": item, "kind": "unknown", "exists": False})
            continue
        if not _is_relative_to(resolved, root):
            context.append({"path": item, "kind": "outside_workspace", "exists": resolved.exists()})
            continue
        if not resolved.exists():
            context.append({"path": item, "kind": "missing", "exists": False})
            continue
        if resolved.is_dir():
            children = _directory_children_preview(resolved, root=root)
            context.append(
                {
                    "path": item,
                    "kind": "directory",
                    "exists": True,
                    "children": children,
                    "truncated": len(children) >= MUTATION_CONTEXT_DIRECTORY_CHILD_LIMIT,
                }
            )
            continue
        if not resolved.is_file():
            context.append({"path": item, "kind": "other", "exists": True})
            continue
        preview_limit = min(MUTATION_CONTEXT_FILE_PREVIEW_LIMIT, remaining)
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            context.append({"path": item, "kind": "file", "exists": True, "read_error": str(exc)})
            continue
        preview = content[:preview_limit]
        remaining -= len(preview)
        context.append(
            {
                "path": item,
                "kind": "file",
                "exists": True,
                "relative_path": resolved.relative_to(root).as_posix(),
                "content_preview": preview,
                "truncated": len(content) > len(preview),
            }
        )
    return context


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _directory_children_preview(path: Path, *, root: Path) -> list[str]:
    children: list[str] = []
    try:
        for child in path.rglob("*"):
            if len(children) >= MUTATION_CONTEXT_DIRECTORY_CHILD_LIMIT:
                break
            if child.is_file():
                children.append(child.resolve().relative_to(root).as_posix())
    except OSError:
        return children
    return children


def packet_for_mutation_attempt(
    packet: TaskPacket,
    contract: MutationContract,
    *,
    attempt_index: int,
    failure_feedback: str | None,
) -> TaskPacket:
    task_card_content = task_card_content_for_mutation(contract, working_directory=packet.working_directory)
    read_set_context = read_set_context_for_mutation(contract, working_directory=packet.working_directory)
    task_card_env = _inline_or_file_env(
        packet=packet,
        name="task_card_content",
        content=task_card_content or "",
        attempt_index=attempt_index,
    )
    read_set_context_env = _inline_or_file_env(
        packet=packet,
        name="read_set_context",
        content=json.dumps(read_set_context, ensure_ascii=False),
        attempt_index=attempt_index,
    )
    return TaskPacket.model_validate(
        {
            **packet.model_dump(mode="json"),
            "env": {
                **packet.env,
                "WORKFLOW_MUTATION_TASK_CARD_REF": contract.task_card_ref or "",
                "WORKFLOW_MUTATION_TASK_CARD_PATH": contract.task_card_path or "",
                "WORKFLOW_MUTATION_WRITE_SET": json.dumps(contract.write_set, ensure_ascii=False),
                "WORKFLOW_MUTATION_READ_SET": json.dumps(contract.read_set, ensure_ascii=False),
                "WORKFLOW_MUTATION_TEST_COMMANDS": json.dumps(contract.test_commands, ensure_ascii=False),
                "WORKFLOW_MUTATION_ATTEMPT_INDEX": str(attempt_index),
                "WORKFLOW_MUTATION_FAILURE_FEEDBACK": failure_feedback or "",
                "WORKFLOW_MUTATION_PROVIDER_COMMAND_POLICY": PATCH_ONLY_PROVIDER_COMMAND_POLICY,
                "WORKFLOW_MUTATION_TASK_CARD_CONTENT": task_card_env["inline"],
                "WORKFLOW_MUTATION_TASK_CARD_CONTENT_FILE": task_card_env["file"],
                "WORKFLOW_MUTATION_READ_SET_CONTEXT": read_set_context_env["inline"],
                "WORKFLOW_MUTATION_READ_SET_CONTEXT_FILE": read_set_context_env["file"],
            },
        }
    )


def _inline_or_file_env(
    *,
    packet: TaskPacket,
    name: str,
    content: str,
    attempt_index: int,
) -> dict[str, str]:
    if len(content.encode("utf-8")) <= MUTATION_CONTEXT_INLINE_ENV_LIMIT:
        return {"inline": content, "file": ""}
    root = Path(packet.working_directory).resolve()
    context_dir = root / "state" / "artifacts" / "mutation_context"
    context_dir.mkdir(parents=True, exist_ok=True)
    safe_run = _safe_context_name(packet.run_id or "run")
    safe_task = _safe_context_name(packet.runtime_task_id or "task")
    path = context_dir / f"{safe_run}_{safe_task}_attempt_{attempt_index}_{name}.txt"
    path.write_text(content, encoding="utf-8", newline="\n")
    return {"inline": "", "file": path.resolve().as_posix()}


def _safe_context_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return cleaned[:96] or "unknown"


def merge_test_feedback(attempts: list[dict[str, Any]]) -> str:
    if not attempts:
        return ""
    chunks: list[str] = []
    for attempt in attempts[-3:]:
        chunks.append(
            "\n".join(
                [
                    f"command: {attempt['command']}",
                    f"return_code: {attempt['return_code']}",
                    f"stdout:\n{attempt['stdout']}",
                    f"stderr:\n{attempt['stderr']}",
                ]
            ).strip()
        )
    return "\n\n".join(chunks)


def execute_repo_mutation(adapter: Any, packet: TaskPacket) -> ExecutionResult:
    contract = packet.mutation_contract
    if contract is None or contract.mutation_mode != MutationMode.patch_apply:
        return adapter.launch(packet)
    if not adapter.supports_mutation_mode(MutationMode.patch_apply):
        raise MutationContractError(
            "repo mutation execution requires a patch-capable adapter",
            {"adapter_name": adapter.normalized_name()},
        )
    allowed_paths = normalize_allowed_paths(packet.working_directory, contract.write_set)
    baseline_snapshot = capture_workspace_snapshot(packet.working_directory, contract.write_set)
    attempt_limit = max(contract.max_fix_iterations, 0)
    failure_feedback: str | None = None
    aggregated_test_attempts: list[dict[str, Any]] = []
    out_of_scope_rejections: list[str] = []
    last_result: ExecutionResult | None = None
    last_patch_hash: str | None = None
    last_touched_paths: list[str] = []
    final_test_status = "patch_generation_failed"

    for attempt_index in range(attempt_limit + 1):
        if attempt_index > 0:
            restore_workspace_snapshot(
                packet.working_directory,
                baseline_snapshot,
                extra_paths=last_touched_paths,
            )
            last_touched_paths = []
        attempt_packet = packet_for_mutation_attempt(
            packet,
            contract,
            attempt_index=attempt_index,
            failure_feedback=failure_feedback,
        )
        execution_result = adapter.launch(attempt_packet)
        last_result = execution_result
        patch_text = ""
        if execution_result.artifact_paths:
            patch_path = Path(execution_result.artifact_paths[0])
            if patch_path.exists():
                patch_text = patch_path.read_text(encoding="utf-8")
        if execution_result.return_code != 0 and not patch_text.strip():
            failure_feedback = execution_result.stderr or execution_result.stdout or "patch generation failed"
            final_test_status = "patch_generation_failed"
            if attempt_index < attempt_limit:
                continue
            break
        patch_text = _rewrite_patch_paths_to_allowed_scope(patch_text, allowed_paths)
        try:
            touched_paths = extract_touched_paths(patch_text, workspace_root=packet.working_directory)
        except ValueError as exc:
            failure_feedback = str(exc)
            final_test_status = "patch_parse_failed"
            if attempt_index < attempt_limit:
                continue
            break
        rejected_paths = [path for path in touched_paths if not is_path_allowed(path, allowed_paths)]
        if rejected_paths:
            out_of_scope_rejections.extend(rejected_paths)
            failure_feedback = f"patch touched out-of-scope paths: {', '.join(rejected_paths)}"
            final_test_status = "patch_rejected"
            if attempt_index < attempt_limit:
                continue
            raise RepoMutationScopeError(
                "patch attempted to modify files outside the allowed write_set",
                {
                    "rejected_paths": rejected_paths,
                    "allowed_paths": allowed_paths,
                },
            )
        try:
            last_patch_hash = hash_patch_text(patch_text)
            last_touched_paths = apply_unified_diff(
                packet.working_directory,
                patch_text,
                allowed_paths=allowed_paths,
            )
        except ValueError as exc:
            restore_workspace_snapshot(
                packet.working_directory,
                baseline_snapshot,
                extra_paths=last_touched_paths,
            )
            last_touched_paths = []
            failure_feedback = str(exc)
            final_test_status = "patch_apply_failed"
            if attempt_index < attempt_limit:
                continue
            break
        command_attempts = []
        if contract.test_commands:
            command_attempts = run_test_commands(contract.test_commands, working_directory=packet.working_directory)
            for command_attempt in command_attempts:
                aggregated_test_attempts.append({"iteration": attempt_index, **command_attempt})
        if command_attempts and any(not bool(item["passed"]) for item in command_attempts):
            failure_feedback = merge_test_feedback(command_attempts)
            final_test_status = "failed"
            if attempt_index < attempt_limit:
                continue
            restore_workspace_snapshot(
                packet.working_directory,
                baseline_snapshot,
                extra_paths=last_touched_paths,
            )
            break
        final_test_status = "passed" if contract.test_commands else "not_requested"
        mutation_result = RepoMutationResult(
            changed_files=sorted(set(last_touched_paths)),
            applied_patch_hash=last_patch_hash,
            out_of_scope_rejections=sorted(set(out_of_scope_rejections)),
            test_attempts=aggregated_test_attempts,
            fix_iteration_count=attempt_index,
            final_test_status=final_test_status,
        )
        return ExecutionResult(
            runtime_task_id=execution_result.runtime_task_id,
            return_code=0,
            stdout=execution_result.stdout,
            stderr=execution_result.stderr,
            started_at=execution_result.started_at,
            finished_at=execution_result.finished_at,
            duration_ms=execution_result.duration_ms,
            artifact_paths=execution_result.artifact_paths,
            adapter_name=execution_result.adapter_name,
            metadata={
                **execution_result.metadata,
                "mutation_contract": contract.model_dump(mode="json"),
                "mutation_result": mutation_result.model_dump(mode="json"),
            },
        )

    failed_result = last_result or adapter.launch(packet)
    mutation_result = RepoMutationResult(
        changed_files=[],
        applied_patch_hash=last_patch_hash,
        out_of_scope_rejections=sorted(set(out_of_scope_rejections)),
        test_attempts=aggregated_test_attempts,
        fix_iteration_count=attempt_limit,
        final_test_status=final_test_status,
        failure_reason=failure_feedback,
    )
    return ExecutionResult(
        runtime_task_id=failed_result.runtime_task_id,
        return_code=failed_result.return_code or 1,
        stdout=failed_result.stdout,
        stderr=failed_result.stderr or failure_feedback or "repo mutation failed",
        started_at=failed_result.started_at,
        finished_at=failed_result.finished_at,
        duration_ms=failed_result.duration_ms,
        artifact_paths=failed_result.artifact_paths,
        adapter_name=failed_result.adapter_name,
        metadata={
            **failed_result.metadata,
            "mutation_contract": contract.model_dump(mode="json"),
            "mutation_result": mutation_result.model_dump(mode="json"),
        },
    )


def _rewrite_patch_paths_to_allowed_scope(patch_text: str, allowed_paths: list[str]) -> str:
    """Map provider project-relative diff paths onto their unique allowed repo path.

    Same-project workers often prompt providers with Cocos project paths, so a
    valid patch may use `assets/...` while the guarded write_set is
    `state/.../cocos_project/assets/...`. This rewrite is deliberately narrow:
    it only maps a diff path when the path has exactly one allowed-scope match.
    """

    rewritten: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                parts[2] = _rewrite_diff_path_token(parts[2], allowed_paths)
                parts[3] = _rewrite_diff_path_token(parts[3], allowed_paths)
                rewritten.append(" ".join(parts))
                continue
        if line.startswith("--- ") or line.startswith("+++ "):
            marker = line[:4]
            raw_path = line[4:]
            path, suffix = _split_diff_path_suffix(raw_path)
            rewritten.append(marker + _rewrite_diff_path_token(path, allowed_paths) + suffix)
            continue
        rewritten.append(line)
    return "\n".join(rewritten) + ("\n" if patch_text.endswith("\n") else "")


def _split_diff_path_suffix(raw_path: str) -> tuple[str, str]:
    if "\t" not in raw_path:
        return raw_path, ""
    path, suffix = raw_path.split("\t", 1)
    return path, "\t" + suffix


def _rewrite_diff_path_token(raw_path: str, allowed_paths: list[str]) -> str:
    prefix = ""
    path = raw_path
    if path in {"/dev/null", "dev/null"}:
        return raw_path
    if path.startswith("a/") or path.startswith("b/"):
        prefix, path = path[:2], path[2:]
    normalized = path.strip("/").replace("\\", "/")
    if is_path_allowed(normalized, allowed_paths):
        return prefix + normalized
    matches = _allowed_scope_matches_for_project_relative_path(normalized, allowed_paths)
    if len(matches) != 1:
        return raw_path
    return prefix + matches[0]


def _allowed_scope_matches_for_project_relative_path(path: str, allowed_paths: list[str]) -> list[str]:
    matches: list[str] = []
    for raw_allowed in allowed_paths:
        allowed = raw_allowed.strip("/").replace("\\", "/")
        allowed_parts = allowed.split("/")
        for index in range(len(allowed_parts)):
            suffix = "/".join(allowed_parts[index:])
            prefix = "/".join(allowed_parts[:index])
            if suffix == path:
                candidate = allowed
            elif path.startswith(suffix.rstrip("/") + "/"):
                candidate = f"{prefix}/{path}" if prefix else path
            else:
                continue
            if is_path_allowed(candidate, allowed_paths) and candidate not in matches:
                matches.append(candidate)
            break
    return matches
