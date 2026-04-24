from __future__ import annotations

import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIVING_DOCS = [
    Path("README.md"),
    Path("M38_REPAIR_AND_DEVELOPMENT_PLAN.md"),
    Path("docs/current_development_workflow.md"),
    Path("docs/tech-debt-registry.md"),
    Path("docs/milestone_history.md"),
    Path("PROJECT_DEEP_EVALUATION_M37.md"),
]
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _normalize_markdown_target(target: str) -> str:
    normalized = target.strip()
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1]
    return normalized.split("#", 1)[0].strip()


def _is_absolute_local_target(target: str) -> bool:
    return bool(re.match(r"^/?[A-Za-z]:[/\\]", target))


def _iter_targets(text: str) -> list[str]:
    return [match.group(1) for match in MARKDOWN_LINK_PATTERN.finditer(text)]


def check_living_doc_links(
    repo_root: Path | str | None = None,
    living_docs: list[Path] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    docs = living_docs or DEFAULT_LIVING_DOCS
    issues: list[dict[str, str]] = []

    for relative_doc in docs:
        doc_path = root / relative_doc
        if not doc_path.exists():
            issues.append(
                {
                    "doc_path": relative_doc.as_posix(),
                    "kind": "missing_doc",
                    "detail": "living doc does not exist",
                }
            )
            continue

        text = doc_path.read_text(encoding="utf-8")
        for raw_target in _iter_targets(text):
            target = _normalize_markdown_target(raw_target)
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if _is_absolute_local_target(target):
                issues.append(
                    {
                        "doc_path": relative_doc.as_posix(),
                        "kind": "absolute_local_link",
                        "detail": target,
                    }
                )
                continue
            resolved = (doc_path.parent / target).resolve()
            if not resolved.exists():
                issues.append(
                    {
                        "doc_path": relative_doc.as_posix(),
                        "kind": "missing_target",
                        "detail": target,
                    }
                )

    return {
        "passed": not issues,
        "checked_doc_count": len(docs),
        "checked_docs": [path.as_posix() for path in docs],
        "issue_count": len(issues),
        "issues": issues,
    }
