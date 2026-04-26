from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.core_domain.automation_lease import record_automation_lease_use, validate_automation_lease
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


CODING_PATCH_APPLY_ACTION = "coding_patch_apply"


@dataclass(slots=True)
class CodingProposalRequest:
    provider: str
    goal: str
    task_card: str | None = None
    read_set: list[str] = field(default_factory=list)
    write_set: list[str] = field(default_factory=list)
    context: str | None = None
    model: str | None = None
    max_tokens: int = 1800


@dataclass(slots=True)
class CodingProposalResult:
    provider: str
    model: str | None
    status: str
    proposal_text: str = ""
    failure_class: str | None = None
    evidence_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CodingPatchApplyResult:
    provider: str
    model: str | None
    status: str
    changed_files: list[str] = field(default_factory=list)
    patch_hash: str | None = None
    test_attempts: list[dict[str, Any]] = field(default_factory=list)
    failure_class: str | None = None
    evidence_path: str | None = None
    proposal_evidence_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _provider_settings(provider: str, model: str | None) -> dict[str, str | None]:
    normalized = provider.strip().lower()
    if normalized in {"minimax", "minimax_api", "mmx_text"}:
        base_url = os.getenv("MINIMAX_BASE_URL") or os.getenv("MINIMAX_API_HOST") or "https://api.minimax.io/v1"
        if not base_url.rstrip("/").endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        return {
            "provider": "minimax_api",
            "api_key_env": "MINIMAX_API_KEY" if os.getenv("MINIMAX_API_KEY") else "MINIMAX_TOKEN",
            "base_url": base_url.rstrip("/"),
            "model": _provider_api_model(model or os.getenv("WORKFLOW_MINIMAX_MODEL") or "MiniMax-M2.7", {"minimax", "mmx"}),
        }
    if normalized in {"deepseek", "deepseek_api"}:
        return {
            "provider": "deepseek_api",
            "api_key_env": "DEEPSEEK_API_KEY",
            "base_url": (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/"),
            "model": _provider_api_model(
                model or os.getenv("WORKFLOW_DEEPSEEK_MODEL") or "deepseek-v4-flash",
                {"deepseek", "deepseek_api"},
            ),
        }
    raise ValueError(f"unsupported coding API provider: {provider}")


def _provider_api_model(model: str, provider_prefixes: set[str]) -> str:
    """Normalize router-style provider/model ids for direct provider APIs."""

    if "/" not in model:
        return model
    prefix, value = model.split("/", 1)
    if prefix.strip().lower() in provider_prefixes and value.strip():
        return value.strip()
    return model


def _proposal_prompt(request: CodingProposalRequest) -> str:
    return (
        "You are producing a coding proposal for Universal Agentic Workflow.\n"
        "Do not mutate files. Do not claim that changes were applied.\n"
        "Return a concise markdown proposal with these sections: Summary, Patch Plan, Tests, Risks.\n"
        "If a patch is useful, include exactly one unified diff proposal in a fenced diff block.\n"
        "The diff must only touch files inside the allowed write set.\n"
        f"Goal:\n{request.goal}\n\n"
        f"Task card:\n{request.task_card or 'none'}\n\n"
        f"Read set JSON: {json.dumps(request.read_set, ensure_ascii=False)}\n"
        f"Allowed write set JSON: {json.dumps(request.write_set, ensure_ascii=False)}\n\n"
        f"Context:\n{request.context or 'none'}\n"
    )


_DIFF_FENCE_RE = re.compile(r"```(?:diff|patch)?\s*\n(?P<diff>.*?)(?:\n```|$)", re.IGNORECASE | re.DOTALL)


def extract_unified_diff_from_proposal(proposal_text: str) -> str:
    for match in _DIFF_FENCE_RE.finditer(proposal_text):
        candidate = match.group("diff").strip()
        if "\n--- " in f"\n{candidate}" and "\n+++ " in f"\n{candidate}":
            return candidate
    lines = proposal_text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("--- "):
            candidate = "\n".join(lines[index:]).strip()
            if "\n+++ " in f"\n{candidate}":
                return candidate
    raise ValueError("proposal did not include a unified diff")


def _extract_chat_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if content:
            return str(content)
    if hasattr(response, "model_dump"):
        payload = response.model_dump(mode="json")
        try:
            return str(payload["choices"][0]["message"]["content"])
        except Exception:
            return ""
    return ""


def generate_coding_proposal(
    request: CodingProposalRequest,
    *,
    evidence_dir: str | Path | None = None,
    client: Any | None = None,
) -> CodingProposalResult:
    try:
        settings = _provider_settings(request.provider, request.model)
    except ValueError as exc:
        return CodingProposalResult(
            provider=request.provider,
            model=request.model,
            status="blocked",
            failure_class="unsupported_provider",
            metadata={"error": str(exc)},
        )

    api_key_env = str(settings["api_key_env"])
    api_key = os.getenv(api_key_env)
    if client is None and not api_key:
        return CodingProposalResult(
            provider=str(settings["provider"]),
            model=str(settings["model"]),
            status="blocked",
            failure_class="provider_auth_missing",
            metadata={"api_key_env": api_key_env},
        )

    try:
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=str(settings["base_url"]))
        response = client.chat.completions.create(
            model=str(settings["model"]),
            messages=[
                {
                    "role": "system",
                    "content": "Return a patch/review proposal only. Never claim repository mutation.",
                },
                {"role": "user", "content": _proposal_prompt(request)},
            ],
            temperature=0.1,
            max_tokens=request.max_tokens,
        )
        text = _extract_chat_text(response).strip()
        if not text:
            raise ValueError("provider returned empty proposal")
        result = CodingProposalResult(
            provider=str(settings["provider"]),
            model=str(settings["model"]),
            status="completed",
            proposal_text=text,
            metadata={"transport": "api", "mutation_mode": "proposal_only"},
        )
    except Exception as exc:
        result = CodingProposalResult(
            provider=str(settings["provider"]),
            model=str(settings["model"]),
            status="blocked",
            failure_class=exc.__class__.__name__,
            metadata={"error": str(exc), "transport": "api"},
        )

    if evidence_dir is not None:
        target_dir = Path(evidence_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        output = target_dir / f"{result.provider}_coding_proposal.json"
        output.write_text(
            json.dumps(
                {
                    **result.to_dict(),
                    "request": asdict(request),
                    "created_at": datetime.now(UTC).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result.evidence_path = output.as_posix()
    return result


def apply_coding_proposal_patch(
    request: CodingProposalRequest,
    *,
    workspace_root: str | Path,
    automation_lease_id: str | None,
    evidence_dir: str | Path | None = None,
    test_commands: list[str] | None = None,
    client: Any | None = None,
) -> CodingPatchApplyResult:
    root = Path(workspace_root).resolve()
    settings: dict[str, str | None]
    try:
        settings = _provider_settings(request.provider, request.model)
    except ValueError as exc:
        return CodingPatchApplyResult(
            provider=request.provider,
            model=request.model,
            status="blocked",
            failure_class="unsupported_provider",
            metadata={"error": str(exc)},
        )
    if not request.write_set:
        return CodingPatchApplyResult(
            provider=str(settings["provider"]),
            model=str(settings["model"]),
            status="blocked",
            failure_class="write_set_required",
            metadata={"action": CODING_PATCH_APPLY_ACTION},
        )
    if not automation_lease_id:
        return CodingPatchApplyResult(
            provider=str(settings["provider"]),
            model=str(settings["model"]),
            status="blocked",
            failure_class="automation_lease_required",
            metadata={
                "action": CODING_PATCH_APPLY_ACTION,
                "required_lease_allowed_action": CODING_PATCH_APPLY_ACTION,
                "write_set": list(request.write_set),
            },
        )
    try:
        validate_automation_lease(
            workspace_root=root,
            lease_id=automation_lease_id,
            action=CODING_PATCH_APPLY_ACTION,
            write_set=request.write_set,
        )
    except Exception as exc:
        return CodingPatchApplyResult(
            provider=str(settings["provider"]),
            model=str(settings["model"]),
            status="blocked",
            failure_class=exc.__class__.__name__,
            metadata={"error": str(exc), "action": CODING_PATCH_APPLY_ACTION},
        )

    proposal_evidence_dir = Path(evidence_dir) / "proposal" if evidence_dir is not None else None
    proposal = generate_coding_proposal(request, evidence_dir=proposal_evidence_dir, client=client)
    if proposal.status != "completed":
        return CodingPatchApplyResult(
            provider=proposal.provider,
            model=proposal.model,
            status="blocked",
            failure_class=proposal.failure_class or "proposal_generation_failed",
            proposal_evidence_path=proposal.evidence_path,
            metadata={"proposal": proposal.to_dict()},
        )

    try:
        patch_text = extract_unified_diff_from_proposal(proposal.proposal_text)
        allowed_paths = normalize_allowed_paths(root, request.write_set)
        touched_paths = extract_touched_paths(patch_text, workspace_root=root)
        rejected = [path for path in touched_paths if not is_path_allowed(path, allowed_paths)]
        if rejected:
            return CodingPatchApplyResult(
                provider=proposal.provider,
                model=proposal.model,
                status="blocked",
                failure_class="write_set_scope_violation",
                proposal_evidence_path=proposal.evidence_path,
                metadata={"rejected_paths": rejected, "allowed_paths": allowed_paths},
            )
        baseline = capture_workspace_snapshot(root, request.write_set)
        changed_files = apply_unified_diff(root, patch_text, allowed_paths=allowed_paths)
        attempts = run_test_commands(list(test_commands or []), working_directory=root) if test_commands else []
        if attempts and any(not bool(item.get("passed")) for item in attempts):
            restore_workspace_snapshot(root, baseline, extra_paths=changed_files)
            status = "failed"
            failure_class = "test_failed"
            changed_files = []
        else:
            status = "completed"
            failure_class = None
        patch_hash = hash_patch_text(patch_text)
        record_automation_lease_use(root, automation_lease_id, action=CODING_PATCH_APPLY_ACTION)
        result = CodingPatchApplyResult(
            provider=proposal.provider,
            model=proposal.model,
            status=status,
            changed_files=changed_files,
            patch_hash=patch_hash,
            test_attempts=attempts,
            failure_class=failure_class,
            proposal_evidence_path=proposal.evidence_path,
            metadata={
                "mutation_mode": "patch_apply",
                "action": CODING_PATCH_APPLY_ACTION,
                "automation_lease_id": automation_lease_id,
                "write_set": list(request.write_set),
            },
        )
    except Exception as exc:
        result = CodingPatchApplyResult(
            provider=proposal.provider,
            model=proposal.model,
            status="blocked",
            failure_class=exc.__class__.__name__,
            proposal_evidence_path=proposal.evidence_path,
            metadata={"error": str(exc), "action": CODING_PATCH_APPLY_ACTION},
        )

    if evidence_dir is not None:
        target_dir = Path(evidence_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        output = target_dir / f"{result.provider}_coding_patch_apply.json"
        output.write_text(
            json.dumps(
                {
                    **result.to_dict(),
                    "request": asdict(request),
                    "created_at": datetime.now(UTC).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        result.evidence_path = output.as_posix()
    return result
