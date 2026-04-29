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

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "product_agent": ("玩法", "目标", "玩家", "关卡", "成长", "循环", "体验", "商业化", "gameplay", "level", "player"),
    "ui_agent": ("ui", "界面", "按钮", "面板", "皮肤", "画廊", "移动端", "交互", "布局", "visual", "screen"),
    "tech_agent": ("技术", "工程", "cocos", "构建", "脚本", "prefab", "api", "平台", "性能", "build"),
    "multimodal_agent": ("图片", "图", "美术", "资产", "音效", "音乐", "语音", "风格", "icon", "audio", "asset"),
    "qa_agent": ("验收", "测试", "检查", "质量", "bug", "修复", "go/no-go", "可玩", "可用", "acceptance"),
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


def build_unified_project_brief(
    *,
    input_paths: list[str | Path],
    output_dir: str | Path,
    title: str = "Unified Project Brief",
    preserve_raw: bool = False,
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

    for file_index, path in enumerate(files, start=1):
        source_id = f"source_{file_index:03d}"
        if preserve_raw:
            _copy_raw_input(path, raw_root, source_id)
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
        chunks.extend(extracted["chunks"])
        media_items.extend(extracted["media_items"])
        source_index.append(
            {
                "source_id": source_id,
                "original_path": path.as_posix(),
                "kind": extracted["kind"],
                "chunk_count": len(extracted["chunks"]),
                "media_count": len(extracted["media_items"]),
                "extraction_status": "completed",
            }
        )

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

    packet_paths = _write_agent_packets(agent_root=agent_root, chunks=chunks, media_items=media_items, full_brief_path=full_brief_path)
    manifest = {
        "schema_version": "m109_unified_project_brief_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "title": title,
        "input_count": len(files),
        "chunk_count": len(chunks),
        "media_count": len(media_items),
        "unsupported_count": len(unsupported),
        "loss_policy": "no_summary_replacement_full_text_preserved_when_extracted",
        "project_brief_path": full_brief_path.as_posix(),
        "media_manifest_path": media_manifest_path.as_posix(),
        "source_index_path": source_index_path.as_posix(),
        "agent_packets": packet_paths,
        "unsupported_inputs": unsupported,
    }
    manifest_path = normalized_root / "intake_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["intake_manifest_path"] = manifest_path.as_posix()
    return manifest


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


def _copy_raw_input(path: Path, raw_root: Path, source_id: str) -> None:
    target = raw_root / f"{source_id}{path.suffix.lower()}"
    shutil.copy2(path, target)


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
) -> dict[str, str]:
    paths: dict[str, str] = {}
    for role in ROLE_KEYWORDS:
        selected = [chunk for chunk in chunks if role in chunk.tags]
        if not selected:
            selected = [chunk for chunk in chunks if "general" in chunk.tags]
        packet_path = agent_root / f"{role}.md"
        packet_path.write_text(_render_agent_packet(role, selected, media_items, full_brief_path), encoding="utf-8")
        paths[role] = packet_path.as_posix()
    return paths


def _render_agent_packet(role: str, chunks: list[ContextChunk], media_items: list[MediaItem], full_brief_path: Path) -> str:
    lines = [
        f"# {role} Context Packet",
        "",
        f"- full_brief_path: `{full_brief_path.as_posix()}`",
        "- packet_policy: `selected_full_chunks_not_summary_replacement`",
        "",
        "## Selected Chunks",
        "",
    ]
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
