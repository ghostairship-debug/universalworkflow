from __future__ import annotations

import json
from typing import Any


DEFAULT_CONTEXT_WARN_CHARS = 2400
DEFAULT_CONTEXT_HARD_LIMIT_CHARS = 4000


def _serialized_chars(value: Any) -> int:
    if value in (None, "", [], {}):
        return 0
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True))


def build_context_budget_report(
    state_payload: dict[str, Any],
    *,
    prompt_text: str | None = None,
    warn_limit_chars: int = DEFAULT_CONTEXT_WARN_CHARS,
    hard_limit_chars: int = DEFAULT_CONTEXT_HARD_LIMIT_CHARS,
) -> dict[str, Any]:
    sections = {
        "goal_chars": len(state_payload.get("goal", "") or ""),
        "expected_artifacts_chars": _serialized_chars(state_payload.get("expected_artifacts") or []),
        "domain_pack_chars": _serialized_chars(state_payload.get("domain_pack_resolution")),
        "memory_preview_chars": _serialized_chars(state_payload.get("memory_retrieval_preview")),
        "runtime_brief_chars": len(state_payload.get("runtime_brief", "") or ""),
    }
    total_context_chars = sum(sections.values())
    prompt_chars = len(prompt_text or "")
    combined_chars = total_context_chars + prompt_chars
    if combined_chars > hard_limit_chars:
        status = "over_budget"
        recommended_action = "reduce memory_preview/domain_pack context before live runtime resume"
    elif combined_chars > warn_limit_chars:
        status = "warning"
        recommended_action = "keep live runtime brief short and avoid growing memory/domain-pack context"
    else:
        status = "ok"
        recommended_action = "none"
    return {
        "status": status,
        "warn_limit_chars": warn_limit_chars,
        "hard_limit_chars": hard_limit_chars,
        "total_context_chars": total_context_chars,
        "runtime_brief_prompt_chars": prompt_chars,
        "combined_chars": combined_chars,
        "over_budget": combined_chars > hard_limit_chars,
        "section_sizes": sections,
        "recommended_action": recommended_action,
    }
