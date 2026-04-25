from __future__ import annotations

from pathlib import Path
import re


def _pdf_paths_for_goal(goal: str) -> list[Path]:
    return [
        Path(match.strip().strip("`'\"“”‘’"))
        for match in re.findall(r"([A-Za-z]:[\\/][^\n\r`\"'“”]+?\.pdf)", goal, flags=re.IGNORECASE)
    ]


def _read_pdf_text(path: Path, *, max_chars: int = 4000) -> tuple[int, str, str | None]:
    if not path.exists():
        return 0, "", "文件不存在"
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - optional dependency varies by local runtime.
        return 0, "", f"pypdf 不可用：{exc}"
    try:
        reader = PdfReader(str(path))
        chunks: list[str] = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
            if sum(len(chunk) for chunk in chunks) >= max_chars:
                break
        text = re.sub(r"\s+", " ", "\n".join(chunks)).strip()
        return len(reader.pages), text[:max_chars], None
    except Exception as exc:  # pragma: no cover - depends on external PDF validity.
        return 0, "", f"读取失败：{exc}"


def _pdf_context_for_goal(goal: str) -> tuple[str, str]:
    paths = _pdf_paths_for_goal(goal)
    if not paths:
        return "- 未在目标中找到可读取 PDF 路径，使用聊天目标中的需求描述。", ""

    sections: list[str] = []
    combined: list[str] = []
    for path in paths:
        page_count, text, error = _read_pdf_text(path)
        if error:
            sections.append(f"- `{path.as_posix()}`：{error}。")
            continue
        combined.append(text)
        excerpt = text[:900] + ("..." if len(text) > 900 else "")
        sections.append(
            f"- `{path.as_posix()}`：已读取 {page_count} 页，提取摘要：{excerpt}"
        )
    return "\n".join(sections), "\n".join(combined)
