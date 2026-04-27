from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ACTIVE_TRUTH_FILES = [
    "README.md",
    "AGENTS.md",
    "CURRENT_DEVELOPMENT_WORKFLOW.md",
    "docs/milestone_history.md",
    "docs/tech-debt-registry.md",
]

STALE_M79_PATTERNS = [
    ("m79_planned_title", re.compile(r"M79\s+Cocos\s+Commercial\s+Pipeline\s+Repair\s+Planned", re.IGNORECASE)),
    ("m79_pre_completion_gate", re.compile(r"M79[^\n]*(?:通过前|完成前|鍓|planned|before completion)", re.IGNORECASE)),
    ("m79_current_priority", re.compile(r"M79[^\n]*(?:当前最优先|当前主线|focused on true commercial)", re.IGNORECASE)),
    ("m79_open_acceptance", re.compile(r"(?:remain open M79|M79 acceptance work)", re.IGNORECASE)),
]


def build_active_truth_check(
    workspace_root: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    docs = _load_active_docs(root)
    tech_debt = _load_tech_debt(root)
    facts = {
        "current_version": _extract_current_version(docs.get("README.md", "")),
        "latest_milestone_baseline": _extract_latest_baseline(docs.get("docs/milestone_history.md", "")),
        "git_head": _git_head(root),
        "m79_evidence_present": (root / "state" / "m79_cocos_commercial_pipeline" / "checkpoint.json").exists(),
        "m80_commit_present": _git_log_contains(root, "M80"),
        "m81_commit_present": _git_log_contains(root, "M81"),
    }
    issues: list[dict[str, Any]] = []
    issues.extend(_check_stale_m79_truth(docs, facts))
    issues.extend(_check_current_version(facts))
    issues.extend(_check_tech_debt_consistency(tech_debt))
    payload = {
        "schema_version": "m82_active_truth_check_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "workspace_root": root.as_posix(),
        "status": "passed" if not issues else "failed",
        "go_no_go": "GO" if not issues else "NO-GO",
        "issue_count": len(issues),
        "issues": issues,
        "facts": facts,
        "checked_files": sorted(docs),
    }
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["output_path"] = target.resolve().as_posix()
    return payload


def _load_active_docs(root: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for relative in ACTIVE_TRUTH_FILES:
        path = root / relative
        if path.exists():
            docs[relative] = path.read_text(encoding="utf-8")
    return docs


def _load_tech_debt(root: Path) -> dict[str, Any]:
    path = root / "docs" / "governance" / "tech_debt_registry.json"
    if not path.exists():
        return {"repaid_items": [], "open_items": [], "missing": True}
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_current_version(readme_text: str) -> str | None:
    match = re.search(r"^## (?:Current Version|当前状态)[:：]\s*(.+)$", readme_text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _extract_latest_baseline(history_text: str) -> str | None:
    match = re.search(r"(?:Latest accepted baseline|最新接受实现基线)[:：]\s*`([^`]+)`", history_text)
    if match:
        return match.group(1).strip()
    legacy = re.search(r"`(M[0-9]+)`", history_text)
    return legacy.group(1).strip() if legacy else None


def _check_stale_m79_truth(docs: dict[str, str], facts: dict[str, Any]) -> list[dict[str, Any]]:
    if not facts.get("m79_evidence_present") and not _commit_subject_contains(facts, "M79"):
        return []
    issues: list[dict[str, Any]] = []
    for relative, text in docs.items():
        for code, pattern in STALE_M79_PATTERNS:
            match = pattern.search(text)
            if match is None:
                continue
            issues.append(
                {
                    "code": code,
                    "severity": "P1",
                    "file": relative,
                    "detail": "M79 has completion evidence, but an active truth file still describes M79 as planned/current/open.",
                    "match": match.group(0),
                }
            )
    return issues


def _check_current_version(facts: dict[str, Any]) -> list[dict[str, Any]]:
    current_version = str(facts.get("current_version") or "")
    issues: list[dict[str, Any]] = []
    if facts.get("m81_commit_present") and not _mentions_milestone_at_least(current_version, 81):
        issues.append(
            {
                "code": "current_version_not_m81_after_m81_commit",
                "severity": "P2",
                "file": "README.md",
                "detail": "git history contains M81, but README current version does not mention M81 or newer.",
                "current_version": current_version,
            }
        )
    elif facts.get("m80_commit_present") and not _mentions_milestone_at_least(current_version, 80):
        issues.append(
            {
                "code": "current_version_stale_after_m80_commit",
                "severity": "P2",
                "file": "README.md",
                "detail": "git history contains M80, but README current version is still older.",
                "current_version": current_version,
            }
        )
    if facts.get("latest_milestone_baseline") == "M78" and facts.get("m79_evidence_present"):
        issues.append(
            {
                "code": "milestone_baseline_stale_after_m79",
                "severity": "P1",
                "file": "docs/milestone_history.md",
                "detail": "M79 evidence exists, but milestone history still says the accepted baseline is M78.",
            }
        )
    return issues


def _mentions_milestone_at_least(text: str, minimum: int) -> bool:
    return any(int(match.group(1)) >= minimum for match in re.finditer(r"\bM([0-9]+)\b", text))


def _check_tech_debt_consistency(payload: dict[str, Any]) -> list[dict[str, Any]]:
    repaid_ids = {str(item.get("debt_id")) for item in payload.get("repaid_items", [])}
    open_items = [dict(item) for item in payload.get("open_items", [])]
    open_ids = {str(item.get("debt_id")) for item in open_items}
    issues: list[dict[str, Any]] = []
    for debt_id in sorted(repaid_ids & open_ids):
        issues.append(
            {
                "code": "debt_id_in_repaid_and_open",
                "severity": "P1",
                "file": "docs/governance/tech_debt_registry.json",
                "detail": f"{debt_id} appears in both repaid_items and open_items.",
                "debt_id": debt_id,
            }
        )
    for item in open_items:
        status = str(item.get("current_status") or "").strip().lower()
        if status == "repaid":
            issues.append(
                {
                    "code": "repaid_status_inside_open_items",
                    "severity": "P1",
                    "file": "docs/governance/tech_debt_registry.json",
                    "detail": "An open_items entry claims current_status=repaid.",
                    "debt_id": item.get("debt_id"),
                }
            )
    return issues


def _git_head(root: Path) -> dict[str, str | None]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True).strip()
        subject = subprocess.check_output(["git", "log", "-1", "--pretty=%s"], cwd=root, text=True).strip()
    except Exception:
        return {"sha": None, "subject": None}
    return {"sha": sha, "subject": subject}


def _git_log_contains(root: Path, token: str) -> bool:
    try:
        output = subprocess.check_output(["git", "log", "--oneline", "-20"], cwd=root, text=True)
    except Exception:
        return False
    return token in output


def _commit_subject_contains(facts: dict[str, Any], token: str) -> bool:
    git_head = facts.get("git_head")
    if not isinstance(git_head, dict):
        return False
    return token in str(git_head.get("subject") or "")
