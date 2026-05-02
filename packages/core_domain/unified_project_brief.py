from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv", ".tsv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
DOCX_EXTENSION = ".docx"
XLSX_EXTENSION = ".xlsx"
PDF_EXTENSION = ".pdf"
REQUIREMENT_MATRIX_SCHEMA_VERSION = "post_m109_requirement_matrix_v1"

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "product_agent": ("玩法", "目标", "玩家", "关卡", "成长", "循环", "体验", "商业化", "gameplay", "level", "player"),
    "ui_agent": ("ui", "界面", "按钮", "面板", "皮肤", "画廊", "移动端", "交互", "布局", "visual", "screen"),
    "tech_agent": ("技术", "工程", "cocos", "构建", "脚本", "prefab", "api", "平台", "性能", "build"),
    "multimodal_agent": ("图片", "图", "美术", "资产", "音效", "音乐", "语音", "风格", "icon", "audio", "asset"),
    "qa_agent": ("验收", "测试", "检查", "质量", "bug", "修复", "go/no-go", "可玩", "可用", "acceptance"),
}
REQUIREMENT_CATEGORY_OWNERS: dict[str, str] = {
    "product": "product_gameplay_agent",
    "ui": "ui_experience_agent",
    "technical": "technical_plan_agent",
    "multimodal": "multimodal_generation_agent",
    "qa": "qa_player_perspective_agent",
    "general": "task_card_generation_agent",
}
REQUIREMENT_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "multimodal": ("图片", "图", "美术", "资产", "音效", "音乐", "语音", "风格", "icon", "audio", "music", "sfx", "asset"),
    "ui": ("ui", "界面", "按钮", "面板", "皮肤", "画廊", "交互", "布局", "视觉", "screen", "panel", "button"),
    "technical": ("技术", "工程", "cocos", "构建", "脚本", "prefab", "api", "平台", "性能", "build", "runtime"),
    "qa": ("验收", "测试", "检查", "质量", "bug", "修复", "go/no-go", "可玩", "可用", "acceptance", "review"),
    "product": ("玩法", "目标", "玩家", "关卡", "成长", "循环", "体验", "商业化", "gameplay", "level", "player", "reward"),
}
HIGH_PRIORITY_REQUIREMENT_KEYWORDS = (
    "必须",
    "不得",
    "禁止",
    "阻塞",
    "商业化",
    "可玩",
    "must",
    "required",
    "cannot",
    "block",
    "go/no-go",
)
MEDIUM_PRIORITY_REQUIREMENT_KEYWORDS = ("需要", "应", "应该", "需", "should", "need", "acceptance")
ROLE_REQUIREMENT_OWNER: dict[str, str] = {
    "product_agent": "product_gameplay_agent",
    "ui_agent": "ui_experience_agent",
    "tech_agent": "technical_plan_agent",
    "multimodal_agent": "multimodal_generation_agent",
    "qa_agent": "qa_player_perspective_agent",
}


@dataclass(slots=True)
class SourceRef:
    source_id: str
    original_path: str
    normalized_path: str | None = None
    media_id: str | None = None
    page: int | None = None
    section: str | None = None
    chunk_index: int | None = None


@dataclass(slots=True)
class ContextChunk:
    chunk_id: str
    title: str
    content_text: str
    source: SourceRef
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MediaItem:
    media_id: str
    original_path: str
    normalized_path: str
    sha256: str
    size_bytes: int
    mime_type: str
    role_hints: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceRequirement:
    req_id: str
    source_id: str
    original_path: str
    page: int | None
    section: str | None
    chunk_id: str
    chunk_index: int | None
    original_quote: str
    normalized_requirement: str
    category: str
    priority: str
    acceptance_method: str
    downstream_owner: str


def build_unified_project_brief(
    *,
    input_paths: list[str | Path],
    output_dir: str | Path,
    title: str = "Unified Project Brief",
    preserve_raw: bool = True,
) -> dict[str, Any]:
    root = Path(output_dir).resolve()
    normalized_root = root / "normalized"
    media_root = normalized_root / "media"
    agent_root = root / "agent_packets"
    raw_root = root / "raw_inputs"
    for directory in (normalized_root, media_root, agent_root):
        directory.mkdir(parents=True, exist_ok=True)
    if preserve_raw:
        raw_root.mkdir(parents=True, exist_ok=True)

    files = _expand_input_paths(input_paths)
    chunks: list[ContextChunk] = []
    media_items: list[MediaItem] = []
    source_index: list[dict[str, Any]] = []
    unsupported: list[dict[str, str]] = []
    source_receipts: list[dict[str, Any]] = []

    for file_index, path in enumerate(files, start=1):
        source_id = f"source_{file_index:03d}"
        receipt = _source_receipt(path)
        raw_input_path = None
        if preserve_raw:
            raw_input_path = _copy_raw_input(path, raw_root, source_id)
            receipt["raw_input_path"] = raw_input_path.as_posix()
        try:
            extracted = _extract_file(path, source_id=source_id, media_root=media_root)
        except Exception as exc:
            unsupported.append(
                {
                    "path": path.as_posix(),
                    "failure_class": exc.__class__.__name__,
                    "error": str(exc),
                }
            )
            continue
        if extracted["kind"] == "unsupported":
            unsupported.append(
                {
                    "path": path.as_posix(),
                    "failure_class": "unsupported_input_type",
                    "error": f"unsupported file type: {path.suffix.lower()}",
                }
            )
            continue
        chunks.extend(extracted["chunks"])
        media_items.extend(extracted["media_items"])
        source_receipts.append(receipt)
        source_index.append(
            {
                "source_id": source_id,
                "original_path": path.as_posix(),
                "kind": extracted["kind"],
                "chunk_count": len(extracted["chunks"]),
                "media_count": len(extracted["media_items"]),
                "extraction_status": "completed",
                "sha256": receipt["sha256"],
                "size_bytes": receipt["size_bytes"],
                "raw_input_path": raw_input_path.as_posix() if raw_input_path is not None else None,
            }
        )

    _validate_intake_counts(
        input_count=len(files),
        source_index=source_index,
        unsupported=unsupported,
        chunks=chunks,
        media_items=media_items,
    )
    requirements = compile_source_requirements(chunks)
    requirement_matrix = {
        "schema_version": REQUIREMENT_MATRIX_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "requirement_count": len(requirements),
        "coverage_policy": "task_cards_that_implement_source_requirements_must_carry_req_id_coverage",
        "requirements": [asdict(item) for item in requirements],
    }
    requirement_matrix_path = normalized_root / "requirement_matrix.json"
    requirement_matrix_path.write_text(json.dumps(requirement_matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    requirement_matrix_markdown_path = normalized_root / "requirement_matrix.md"
    requirement_matrix_markdown_path.write_text(_render_requirement_matrix(requirements), encoding="utf-8")

    full_brief_path = normalized_root / "project_brief.full.md"
    full_brief_path.write_text(_render_full_brief(title=title, chunks=chunks, media_items=media_items), encoding="utf-8")

    media_manifest_path = normalized_root / "media_manifest.json"
    media_manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "m109_media_manifest_v1",
                "media_count": len(media_items),
                "media": [asdict(item) for item in media_items],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    source_index_path = normalized_root / "source_index.json"
    source_index_path.write_text(json.dumps(source_index, ensure_ascii=False, indent=2), encoding="utf-8")

    packet_paths = _write_agent_packets(
        agent_root=agent_root,
        chunks=chunks,
        media_items=media_items,
        full_brief_path=full_brief_path,
        requirement_matrix_path=requirement_matrix_path,
        requirements=requirements,
    )
    manifest = {
        "schema_version": "m109_unified_project_brief_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "title": title,
        "input_count": len(files),
        "source_count": len(source_index),
        "chunk_count": len(chunks),
        "media_count": len(media_items),
        "requirement_count": len(requirements),
        "unsupported_count": len(unsupported),
        "loss_policy": "no_summary_replacement_full_text_preserved_when_extracted",
        "source_material_policy": "no_delete_no_merge_no_rename_only_augment",
        "raw_input_preserved": preserve_raw,
        "source_receipts": source_receipts,
        "source_integrity_go": True,
        "source_count_consistency": {
            "input_count": len(files),
            "completed_source_count": len(source_index),
            "unsupported_count": len(unsupported),
            "chunk_count": len(chunks),
            "media_count": len(media_items),
        },
        "project_brief_path": full_brief_path.as_posix(),
        "media_manifest_path": media_manifest_path.as_posix(),
        "source_index_path": source_index_path.as_posix(),
        "requirement_matrix_path": requirement_matrix_path.as_posix(),
        "requirement_matrix_markdown_path": requirement_matrix_markdown_path.as_posix(),
        "requirement_ids": [item.req_id for item in requirements],
        "agent_packets": packet_paths,
        "unsupported_inputs": unsupported,
    }
    manifest_path = normalized_root / "intake_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["intake_manifest_path"] = manifest_path.as_posix()
    return manifest


def compile_source_requirements(chunks: list[ContextChunk]) -> list[SourceRequirement]:
    requirements: list[SourceRequirement] = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        statement_index = 0
        for original_quote, normalized in _requirement_statements_from_text(chunk.content_text):
            key = (chunk.source.source_id, normalized.lower())
            if key in seen:
                continue
            seen.add(key)
            statement_index += 1
            category = _requirement_category(normalized, chunk.tags)
            requirements.append(
                SourceRequirement(
                    req_id=_requirement_id(chunk, statement_index),
                    source_id=chunk.source.source_id,
                    original_path=chunk.source.original_path,
                    page=chunk.source.page,
                    section=chunk.source.section,
                    chunk_id=chunk.chunk_id,
                    chunk_index=chunk.source.chunk_index,
                    original_quote=original_quote,
                    normalized_requirement=normalized,
                    category=category,
                    priority=_requirement_priority(normalized),
                    acceptance_method=_acceptance_method(normalized, category),
                    downstream_owner=REQUIREMENT_CATEGORY_OWNERS.get(category, REQUIREMENT_CATEGORY_OWNERS["general"]),
                )
            )
    return requirements


def _expand_input_paths(input_paths: list[str | Path]) -> list[Path]:
    files: list[Path] = []
    for value in input_paths:
        path = Path(value).resolve()
        if path.is_dir():
            files.extend(item for item in sorted(path.rglob("*")) if item.is_file())
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(path.as_posix())
    return files


def _copy_raw_input(path: Path, raw_root: Path, source_id: str) -> Path:
    target = raw_root / f"{source_id}{path.suffix.lower()}"
    shutil.copy2(path, target)
    return target


def _source_receipt(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "original_path": path.as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def _validate_intake_counts(
    *,
    input_count: int,
    source_index: list[dict[str, Any]],
    unsupported: list[dict[str, str]],
    chunks: list[ContextChunk],
    media_items: list[MediaItem],
) -> None:
    completed_count = len(source_index)
    if completed_count + len(unsupported) != input_count:
        raise ValueError(
            "intake source count mismatch: completed sources plus unsupported inputs must equal input count"
        )
    if sum(int(item.get("chunk_count") or 0) for item in source_index) != len(chunks):
        raise ValueError("intake chunk count mismatch between source_index and extracted chunks")
    if sum(int(item.get("media_count") or 0) for item in source_index) != len(media_items):
        raise ValueError("intake media count mismatch between source_index and media manifest")
    empty_sources = [
        str(item.get("source_id"))
        for item in source_index
        if int(item.get("chunk_count") or 0) == 0 and int(item.get("media_count") or 0) == 0
    ]
    if empty_sources:
        raise ValueError(f"intake source produced no chunks or media: {', '.join(empty_sources)}")


def _extract_file(path: Path, *, source_id: str, media_root: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return {"kind": "media", "chunks": [], "media_items": [_copy_media(path, source_id=source_id, media_root=media_root)]}
    if suffix == PDF_EXTENSION:
        return {"kind": "pdf_text", "chunks": _extract_pdf(path, source_id=source_id), "media_items": []}
    if suffix == DOCX_EXTENSION:
        return {"kind": "docx_text", "chunks": _chunks_from_text(_extract_docx_text(path), source_id=source_id, path=path), "media_items": []}
    if suffix == XLSX_EXTENSION:
        return {"kind": "xlsx_text", "chunks": _chunks_from_text(_extract_xlsx_text(path), source_id=source_id, path=path), "media_items": []}
    if suffix in TEXT_EXTENSIONS:
        text = _read_text_file(path)
        return {"kind": "text", "chunks": _chunks_from_text(text, source_id=source_id, path=path), "media_items": []}
    return {"kind": "unsupported", "chunks": [], "media_items": []}


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_pdf(path: Path, *, source_id: str) -> list[ContextChunk]:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - depends on optional environment
        raise RuntimeError("pypdf is required for PDF text extraction") from exc

    reader = PdfReader(str(path))
    chunks: list[ContextChunk] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        chunk_id = f"{source_id}_page_{page_index:04d}"
        chunks.append(
            ContextChunk(
                chunk_id=chunk_id,
                title=f"{path.name} page {page_index}",
                content_text=text.strip(),
                source=SourceRef(source_id=source_id, original_path=path.as_posix(), page=page_index, chunk_index=len(chunks) + 1),
                tags=_tags_for_text(text),
            )
        )
    return chunks


def _extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _extract_xlsx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheet_names = sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        sections: list[str] = []
        for sheet_name in sheet_names:
            root = ElementTree.fromstring(archive.read(sheet_name))
            rows = []
            for row in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                values = []
                for cell in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                    values.append(_xlsx_cell_value(cell, shared_strings))
                if any(value for value in values):
                    rows.append("\t".join(values))
            if rows:
                sections.append(f"## {sheet_name}\n" + "\n".join(rows))
    return "\n\n".join(sections)


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
        strings.append("".join(node.text or "" for node in item.iter() if node.tag.endswith("}t")))
    return strings


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    value = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        index = int(value.text)
        return shared_strings[index] if 0 <= index < len(shared_strings) else ""
    return value.text


def _chunks_from_text(text: str, *, source_id: str, path: Path, max_chars: int = 12_000) -> list[ContextChunk]:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return []
    sections = _split_markdown_sections(cleaned)
    chunks: list[ContextChunk] = []
    for section_title, section_text in sections:
        for part_index, part in enumerate(_split_text_lossless(section_text, max_chars=max_chars), start=1):
            title = section_title or path.name
            if len(section_text) > max_chars:
                title = f"{title} part {part_index}"
            chunk_id = f"{source_id}_chunk_{len(chunks) + 1:04d}"
            chunks.append(
                ContextChunk(
                    chunk_id=chunk_id,
                    title=title,
                    content_text=part.strip(),
                    source=SourceRef(
                        source_id=source_id,
                        original_path=path.as_posix(),
                        section=section_title or None,
                        chunk_index=len(chunks) + 1,
                    ),
                    tags=_tags_for_text(part),
                )
            )
    return chunks


def _split_markdown_sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^(#{1,6})\s+(.+)$", text))
    if not matches:
        return [("Full Text", text)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("Preamble", text[: matches[0].start()].strip()))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(2).strip()
        body = text[match.start() : end].strip()
        if body:
            sections.append((title, body))
    return [(title, body) for title, body in sections if body]


def _split_text_lossless(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = re.split(r"(\n\s*\n)", text)
    chunks: list[str] = []
    current = ""
    for part in paragraphs:
        if len(current) + len(part) <= max_chars:
            current += part
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(part) > max_chars:
            chunks.append(part[:max_chars])
            part = part[max_chars:]
        current = part
    if current:
        chunks.append(current)
    return chunks


def _requirement_statements_from_text(text: str) -> list[tuple[str, str]]:
    statements: list[tuple[str, str]] = []
    in_code_block = False
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if re.match(r"^#{1,6}\s+", stripped):
            continue
        normalized = _normalize_requirement_statement(stripped)
        if len(normalized) < 4:
            continue
        for part in _split_requirement_statement(normalized):
            if len(part) >= 4:
                statements.append((stripped, part))
    return statements


def _normalize_requirement_statement(value: str) -> str:
    text = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|[（(]?\d+[）)]\s*)", "", value).strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _split_requirement_statement(value: str, *, max_chars: int = 500) -> list[str]:
    if len(value) <= max_chars:
        return [value]
    parts = re.split(r"(?<=[。！？.!?])\s*", value)
    result: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current += part
            continue
        if current:
            result.append(current.strip())
        current = part
    if current:
        result.append(current.strip())
    return result or [value[:max_chars].strip()]


def _requirement_id(chunk: ContextChunk, statement_index: int) -> str:
    source_number = re.sub(r"\D+", "", chunk.source.source_id) or "0"
    chunk_index = chunk.source.chunk_index or 0
    return f"REQ-S{int(source_number):03d}-C{chunk_index:04d}-{statement_index:03d}"


def _requirement_category(text: str, tags: list[str]) -> str:
    lowered = text.lower()
    for category, keywords in REQUIREMENT_CATEGORY_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return category
    tag_category = {
        "product_agent": "product",
        "ui_agent": "ui",
        "tech_agent": "technical",
        "multimodal_agent": "multimodal",
        "qa_agent": "qa",
    }
    for tag in tags:
        if tag in tag_category:
            return tag_category[tag]
    return "general"


def _requirement_priority(text: str) -> str:
    lowered = text.lower()
    if any(keyword.lower() in lowered for keyword in HIGH_PRIORITY_REQUIREMENT_KEYWORDS):
        return "high"
    if any(keyword.lower() in lowered for keyword in MEDIUM_PRIORITY_REQUIREMENT_KEYWORDS):
        return "medium"
    return "normal"


def _acceptance_method(text: str, category: str) -> str:
    lowered = text.lower()
    if "音" in text or "audio" in lowered or "music" in lowered or "sfx" in lowered:
        return "runtime_media_evidence"
    if category == "ui" or "截图" in text or "screenshot" in lowered:
        return "player_visible_screenshot_or_visual_review"
    if category == "technical" or "build" in lowered or "构建" in text:
        return "contract_test_or_build_evidence"
    if category == "qa" or "验收" in text or "review" in lowered:
        return "qa_or_human_review_gate"
    return "task_card_acceptance_and_player_visible_evidence"


def _render_requirement_matrix(requirements: list[SourceRequirement]) -> str:
    lines = [
        "# Requirement Matrix",
        "",
        "> Generated from source-preserved intake chunks. Task cards may cite these req_ids for coverage.",
        "",
    ]
    if not requirements:
        lines.extend(["No source requirements were extracted.", ""])
        return "\n".join(lines)
    for requirement in requirements:
        lines.extend(
            [
                f"## {requirement.req_id}",
                "",
                f"- source_id: `{requirement.source_id}`",
                f"- original_path: `{requirement.original_path}`",
                f"- page: `{requirement.page if requirement.page is not None else '-'}`",
                f"- section: `{requirement.section or '-'}`",
                f"- category: `{requirement.category}`",
                f"- priority: `{requirement.priority}`",
                f"- acceptance_method: `{requirement.acceptance_method}`",
                f"- downstream_owner: `{requirement.downstream_owner}`",
                "",
                requirement.normalized_requirement,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _copy_media(path: Path, *, source_id: str, media_root: Path) -> MediaItem:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    suffix = path.suffix.lower()
    target = media_root / f"{digest}{suffix}"
    if not target.exists():
        target.write_bytes(data)
    return MediaItem(
        media_id=f"media_{digest[:16]}",
        original_path=path.as_posix(),
        normalized_path=target.as_posix(),
        sha256=digest,
        size_bytes=len(data),
        mime_type=_mime_for_suffix(suffix),
        role_hints=["ui_agent", "multimodal_agent", "qa_agent"],
    )


def _mime_for_suffix(suffix: str) -> str:
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".bmp":
        return "image/bmp"
    return "image/png"


def _tags_for_text(text: str) -> list[str]:
    lowered = text.lower()
    tags = [role for role, keywords in ROLE_KEYWORDS.items() if any(keyword.lower() in lowered for keyword in keywords)]
    return tags or ["general"]


def _render_full_brief(*, title: str, chunks: list[ContextChunk], media_items: list[MediaItem]) -> str:
    lines = [
        f"# {title}",
        "",
        "> This file is a normalized working brief. It preserves extracted text instead of replacing it with a summary.",
        "",
        "## Source Text",
        "",
    ]
    for chunk in chunks:
        lines.extend(
            [
                f"### {chunk.chunk_id}: {chunk.title}",
                "",
                f"- source_id: `{chunk.source.source_id}`",
                f"- original_path: `{chunk.source.original_path}`",
                f"- page: `{chunk.source.page if chunk.source.page is not None else '-'}`",
                f"- section: `{chunk.source.section or '-'}`",
                f"- tags: `{', '.join(chunk.tags)}`",
                "",
                chunk.content_text,
                "",
            ]
        )
    if media_items:
        lines.extend(["## Media Index", ""])
        for item in media_items:
            lines.extend(
                [
                    f"### {item.media_id}",
                    "",
                    f"- original_path: `{item.original_path}`",
                    f"- normalized_path: `{item.normalized_path}`",
                    f"- sha256: `{item.sha256}`",
                    f"- mime_type: `{item.mime_type}`",
                    f"- role_hints: `{', '.join(item.role_hints)}`",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _write_agent_packets(
    *,
    agent_root: Path,
    chunks: list[ContextChunk],
    media_items: list[MediaItem],
    full_brief_path: Path,
    requirement_matrix_path: Path,
    requirements: list[SourceRequirement],
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for role in ROLE_KEYWORDS:
        selected = [chunk for chunk in chunks if role in chunk.tags]
        if not selected:
            selected = [chunk for chunk in chunks if "general" in chunk.tags]
        packet_path = agent_root / f"{role}.md"
        packet_path.write_text(
            _render_agent_packet(
                role,
                selected,
                media_items,
                full_brief_path,
                requirement_matrix_path,
                _requirements_for_packet_role(role, requirements),
            ),
            encoding="utf-8",
        )
        paths[role] = packet_path.as_posix()
    return paths


def _requirements_for_packet_role(role: str, requirements: list[SourceRequirement]) -> list[SourceRequirement]:
    owner = ROLE_REQUIREMENT_OWNER.get(role)
    selected = [item for item in requirements if item.downstream_owner == owner]
    if not selected and role == "product_agent":
        selected = [item for item in requirements if item.category in {"product", "general"}]
    if not selected and requirements:
        selected = [item for item in requirements if item.priority == "high"] or requirements
    return selected


def _render_agent_packet(
    role: str,
    chunks: list[ContextChunk],
    media_items: list[MediaItem],
    full_brief_path: Path,
    requirement_matrix_path: Path,
    requirements: list[SourceRequirement],
) -> str:
    lines = [
        f"# {role} Context Packet",
        "",
        f"- full_brief_path: `{full_brief_path.as_posix()}`",
        f"- requirement_matrix_path: `{requirement_matrix_path.as_posix()}`",
        "- packet_policy: `selected_full_chunks_not_summary_replacement`",
        "",
        "## Requirement Trace",
        "",
    ]
    if requirements:
        lines.extend(f"- `{item.req_id}` {item.normalized_requirement}" for item in requirements)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Selected Chunks",
            "",
        ]
    )
    for chunk in chunks:
        lines.extend(
            [
                f"### {chunk.chunk_id}: {chunk.title}",
                "",
                f"- source: `{chunk.source.original_path}`",
                f"- page: `{chunk.source.page if chunk.source.page is not None else '-'}`",
                f"- section: `{chunk.source.section or '-'}`",
                "",
                chunk.content_text,
                "",
            ]
        )
    role_media = [item for item in media_items if role in item.role_hints]
    if role_media:
        lines.extend(["## Related Media", ""])
        for item in role_media:
            lines.extend(
                [
                    f"- `{item.media_id}` `{item.mime_type}` `{item.normalized_path}` sha256=`{item.sha256}`",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def parse_csv_text(text: str) -> list[list[str]]:
    return list(csv.reader(text.splitlines()))


def normalize_html_text(text: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", text))
