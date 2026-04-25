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


def packet_for_mutation_attempt(
    packet: TaskPacket,
    contract: MutationContract,
    *,
    attempt_index: int,
    failure_feedback: str | None,
) -> TaskPacket:
    task_card_content = task_card_content_for_mutation(contract, working_directory=packet.working_directory)
    return TaskPacket.model_validate(
        {
            **packet.model_dump(mode="json"),
            "env": {
                **packet.env,
                "WORKFLOW_MUTATION_TASK_CARD_REF": contract.task_card_ref or "",
                "WORKFLOW_MUTATION_TASK_CARD_PATH": contract.task_card_path or "",
                "WORKFLOW_MUTATION_TASK_CARD_CONTENT": task_card_content or "",
                "WORKFLOW_MUTATION_WRITE_SET": json.dumps(contract.write_set, ensure_ascii=False),
                "WORKFLOW_MUTATION_READ_SET": json.dumps(contract.read_set, ensure_ascii=False),
                "WORKFLOW_MUTATION_TEST_COMMANDS": json.dumps(contract.test_commands, ensure_ascii=False),
                "WORKFLOW_MUTATION_ATTEMPT_INDEX": str(attempt_index),
                "WORKFLOW_MUTATION_FAILURE_FEEDBACK": failure_feedback or "",
            },
        }
    )


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
        try:
            touched_paths = extract_touched_paths(patch_text, workspace_root=packet.working_directory)
        except ValueError as exc:
            failure_feedback = str(exc)
            final_test_status = "patch_parse_failed"
            if attempt_index < attempt_limit:
                continue
            raise PatchApplyError(
                "adapter did not return a valid unified diff patch",
                {"reason": str(exc), "attempt_index": attempt_index},
            ) from exc
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
            raise PatchApplyError(
                "failed to apply the generated unified diff patch",
                {"reason": str(exc), "attempt_index": attempt_index},
            ) from exc
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
