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
    "docs/development/commercial_game_production_next_sequence_2026_04_29.md",
]

LEGACY_ACTIVE_WORKFLOW_FILES = [
    "docs/current_development_workflow.md",
]

STALE_ACTIVE_WORKFLOW_PATTERNS = [
    ("stale_m34_current_workflow", re.compile(r"(?:no post-M34|M34[^\n]*(?:current|currently|active))", re.IGNORECASE)),
]

STALE_M79_PATTERNS = [
    ("m79_planned_title", re.compile(r"M79\s+Cocos\s+Commercial\s+Pipeline\s+Repair\s+Planned", re.IGNORECASE)),
    ("m79_pre_completion_gate", re.compile(r"M79[^\n]*(?:通过前|完成前|鍓|planned|before completion)", re.IGNORECASE)),
    ("m79_current_priority", re.compile(r"M79[^\n]*(?:当前最优先|当前主线|focused on true commercial)", re.IGNORECASE)),
    ("m79_open_acceptance", re.compile(r"(?:remain open M79|M79 acceptance work)", re.IGNORECASE)),
]

COMMERCIAL_GO_CLAIM_PATTERNS = [
    (
        "commercial_playable_go_true_claim_without_guard",
        re.compile(r"commercial_playable_go\s*[:=]\s*(?:true|GO)\b", re.IGNORECASE),
    ),
    (
        "commercial_playable_completion_claim_without_guard",
        re.compile(r"(?:完整商业化游戏已完成|commercial playable(?: game)?\s+(?:completed|ready|delivered|GO))", re.IGNORECASE),
    ),
]

COMMERCIAL_GO_GUARD_MARKERS = (
    "不得",
    "不能",
    "禁止",
    "仍为",
    "保持 false",
    "阻塞",
    "缺",
    "未",
    "必须",
    "才允许",
    "no-go",
    "not ",
    "cannot",
    "without",
    "unless",
    "only if",
    "requires",
    "required",
    "must not",
    "false",
    "awaiting",
    "blocked",
    "failed",
    "missing",
)


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
    issues.extend(_check_active_workflow_uniqueness(root))
    issues.extend(_check_stale_active_workflow_patterns(docs))
    issues.extend(_check_current_version(facts))
    issues.extend(_check_latest_baseline_consistency(docs, facts))
    issues.extend(_check_m109_pipeline_truth_docs(docs, facts))
    issues.extend(_check_commercial_ready_claims(_load_commercial_claim_scan_docs(root, docs)))
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
    for relative in LEGACY_ACTIVE_WORKFLOW_FILES:
        path = root / relative
        if path.exists():
            docs[relative] = path.read_text(encoding="utf-8")
    return docs


def _load_commercial_claim_scan_docs(root: Path, active_docs: dict[str, str]) -> dict[str, str]:
    docs = dict(active_docs)
    for path in sorted(root.glob("*.md")):
        relative = path.relative_to(root).as_posix()
        docs.setdefault(relative, path.read_text(encoding="utf-8", errors="replace"))
    for folder in ["docs/development", "docs/evaluations"]:
        directory = root / folder
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            relative = path.relative_to(root).as_posix()
            docs.setdefault(relative, path.read_text(encoding="utf-8", errors="replace"))
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


def _check_latest_baseline_consistency(docs: dict[str, str], facts: dict[str, Any]) -> list[dict[str, Any]]:
    latest_baseline = str(facts.get("latest_milestone_baseline") or "")
    latest_number = _latest_milestone_number(latest_baseline)
    if latest_number is None:
        return []
    issues: list[dict[str, Any]] = []
    current_version = str(facts.get("current_version") or "")
    current_number = _latest_milestone_number(current_version)
    if current_number is None or current_number < latest_number:
        issues.append(
            {
                "code": "readme_current_version_behind_latest_baseline",
                "severity": "P1",
                "file": "README.md",
                "detail": "README current version is behind the latest accepted milestone baseline.",
                "current_version": current_version,
                "latest_milestone_baseline": latest_baseline,
            }
        )
    baseline_pattern = re.compile(r"(?:Accepted baseline|当前接受实现基线)[^\n]*\bM([0-9]+)\b", re.IGNORECASE)
    for relative, text in docs.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = baseline_pattern.search(line)
            if match is None:
                continue
            line_milestones = [int(item) for item in re.findall(r"\bM([0-9]+)\b", line)]
            if line_milestones and max(line_milestones) < latest_number:
                issues.append(
                    {
                        "code": "active_doc_baseline_conflicts_with_latest",
                        "severity": "P1",
                        "file": relative,
                        "line": line_number,
                        "detail": "An active truth document names an older accepted baseline than milestone history.",
                        "match": line.strip(),
                        "latest_milestone_baseline": latest_baseline,
                    }
                )
        if latest_number >= 109:
            stale_m108_mainline = re.search(r"当前主线[^\n]*M108[^\n]*不得自动进入\s*M109", text)
            if stale_m108_mainline:
                issues.append(
                    {
                        "code": "active_doc_m109_reentry_conflict",
                        "severity": "P1",
                        "file": relative,
                        "detail": "An active truth document still says the project must not enter M109 even though M109 is the accepted baseline.",
                        "match": stale_m108_mainline.group(0),
                    }
                )
    return issues


def _check_m109_pipeline_truth_docs(docs: dict[str, str], facts: dict[str, Any]) -> list[dict[str, Any]]:
    latest_number = _latest_milestone_number(str(facts.get("latest_milestone_baseline") or ""))
    if latest_number is None or latest_number < 109:
        return []
    issues: list[dict[str, Any]] = []
    required_docs = ["README.md", "AGENTS.md", "CURRENT_DEVELOPMENT_WORKFLOW.md"]
    for relative in required_docs:
        text = docs.get(relative, "")
        if not text:
            continue
        if "commercial_game_production" not in text:
            issues.append(
                {
                    "code": "m109_commercial_game_production_entry_missing",
                    "severity": "P1",
                    "file": relative,
                    "detail": "M109 active truth docs must name commercial_game_production as the real commercial game entry.",
                }
            )
        if "legacy_cocos_template_removed" not in text:
            issues.append(
                {
                    "code": "m109_legacy_cocos_template_blocker_missing",
                    "severity": "P1",
                    "file": relative,
                    "detail": "M109 active truth docs must state that the legacy commercial_cocos_game path blocks with legacy_cocos_template_removed.",
                }
            )
    return issues


def _check_commercial_ready_claims(docs: dict[str, str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for relative, text in docs.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            if _line_has_commercial_go_guard(line):
                continue
            for code, pattern in COMMERCIAL_GO_CLAIM_PATTERNS:
                match = pattern.search(line)
                if match is None:
                    continue
                issues.append(
                    {
                        "code": code,
                        "severity": "P1",
                        "file": relative,
                        "line": line_number,
                        "detail": "A design/evaluation/active truth document appears to claim commercial playable GO without a local no-go or human-review guard.",
                        "match": match.group(0),
                    }
                )
    return issues


def _check_active_workflow_uniqueness(root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    canonical = root / "CURRENT_DEVELOPMENT_WORKFLOW.md"
    if not canonical.exists():
        issues.append(
            {
                "code": "missing_canonical_active_workflow",
                "severity": "P1",
                "file": "CURRENT_DEVELOPMENT_WORKFLOW.md",
                "detail": "The canonical active workflow file is missing.",
            }
        )
    for relative in LEGACY_ACTIVE_WORKFLOW_FILES:
        legacy = root / relative
        if not legacy.exists():
            continue
        text = legacy.read_text(encoding="utf-8")
        if _is_active_workflow_redirect(text):
            continue
        issues.append(
            {
                "code": "duplicate_active_workflow_source",
                "severity": "P1",
                "file": relative,
                "detail": "A legacy active workflow file exists without a redirect/archive notice, which can split the source of truth.",
            }
        )
    return issues


def _is_active_workflow_redirect(text: str) -> bool:
    lowered = text.lower()
    return "current_development_workflow.md" in lowered and (
        "redirect" in lowered or "archived" in lowered or "moved" in lowered or "canonical" in lowered
    )


def _check_stale_active_workflow_patterns(docs: dict[str, str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for relative, text in docs.items():
        for code, pattern in STALE_ACTIVE_WORKFLOW_PATTERNS:
            match = pattern.search(text)
            if match is None:
                continue
            issues.append(
                {
                    "code": code,
                    "severity": "P1",
                    "file": relative,
                    "detail": "An active truth file still contains an obsolete workflow baseline statement.",
                    "match": match.group(0),
                }
            )
    return issues


def _mentions_milestone_at_least(text: str, minimum: int) -> bool:
    return any(int(match.group(1)) >= minimum for match in re.finditer(r"\bM([0-9]+)\b", text))


def _latest_milestone_number(text: str) -> int | None:
    numbers = [int(match.group(1)) for match in re.finditer(r"\bM([0-9]+)\b", text)]
    return max(numbers) if numbers else None


def _line_has_commercial_go_guard(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in COMMERCIAL_GO_GUARD_MARKERS)


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
