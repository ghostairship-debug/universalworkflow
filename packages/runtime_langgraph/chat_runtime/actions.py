from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SUPPORTED_CHAT_ACTIONS = {
    "answer_only",
    "plan_preview",
    "launch_prepare",
    "launch_execute",
    "resume_run",
    "approve_run",
    "reject_run",
    "cancel_run",
    "summarize_run",
    "diagnose_failure",
    "pr_ready_summary",
    "create_followup",
}

HIGH_RISK_CHAT_ACTIONS = {
    "launch_execute",
    "resume_run",
    "approve_run",
    "reject_run",
    "cancel_run",
    "repo_mutation",
    "git_commit",
    "git_push",
    "github_pr",
}


@dataclass(frozen=True)
class ChatActionDecision:
    action_type: str = "answer_only"
    confidence: float = 0.0
    rationale: str = ""
    requires_confirmation: bool = False
    degraded: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


def _contains_any(value: str, markers: set[str]) -> bool:
    normalized = value.strip().lower()
    return any(marker in normalized for marker in markers)


def infer_rule_based_chat_action(content: str) -> ChatActionDecision:
    normalized = content.strip().lower()
    action_type = "answer_only"
    if _contains_any(normalized, {"通过", "同意", "approve"}):
        action_type = "approve_run"
    elif _contains_any(normalized, {"拒绝", "驳回", "reject"}):
        action_type = "reject_run"
    elif _contains_any(normalized, {"取消", "停止", "终止", "cancel"}):
        action_type = "cancel_run"
    elif _contains_any(normalized, {"继续", "执行下一步", "resume", "continue"}):
        action_type = "resume_run"
    elif _contains_any(normalized, {"并执行", "直接执行", "execute"}):
        action_type = "launch_execute"
    elif _contains_any(normalized, {"启动", "开始", "launch", "start"}):
        action_type = "launch_prepare"
    elif _contains_any(normalized, {"pr summary", "pr-ready", "pr 摘要", "pr摘要", "pr 总结"}):
        action_type = "pr_ready_summary"
    elif _contains_any(normalized, {"排查失败", "失败原因", "diagnose", "failure"}):
        action_type = "diagnose_failure"
    elif _contains_any(normalized, {"总结", "状态", "summary", "status"}):
        action_type = "summarize_run"
    elif _contains_any(normalized, {"follow-up", "followup", "后续", "待办", "加入"}):
        action_type = "create_followup"
    elif _contains_any(normalized, {"预览", "计划", "plan"}):
        action_type = "plan_preview"
    return ChatActionDecision(
        action_type=action_type,
        confidence=0.72 if action_type != "answer_only" else 0.45,
        rationale="rule-based fallback",
        requires_confirmation=action_type in HIGH_RISK_CHAT_ACTIONS,
        degraded=True,
    )


def chunk_text(text: str, *, chunk_size: int = 28) -> list[str]:
    clean = text or ""
    if not clean:
        return []
    return [clean[index : index + chunk_size] for index in range(0, len(clean), chunk_size)]
