from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from packages.runtime_security.safe_command_runner import (
    SAFE_COMMAND_BLOCKED_EXIT_CODE as TEST_COMMAND_BLOCKED_EXIT_CODE,
    SAFE_COMMAND_NOT_FOUND_EXIT_CODE as TEST_COMMAND_NOT_FOUND_EXIT_CODE,
    SAFE_COMMAND_OUTPUT_LIMIT_BYTES as TEST_COMMAND_OUTPUT_LIMIT_BYTES,
    SAFE_COMMAND_TIMEOUT_EXIT_CODE as TEST_COMMAND_TIMEOUT_EXIT_CODE,
    SAFE_COMMAND_TIMEOUT_SECONDS as TEST_COMMAND_TIMEOUT_SECONDS,
    SafeCommandSpec as TestCommandSpec,
    run_safe_commands as run_test_commands,
)


_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)
_APPLY_PATCH_FILE_HEADER_RE = re.compile(r"^\*\*\* (?P<action>Update|Add|Delete) File: (?P<path>.+)$", re.MULTILINE)


@dataclass(slots=True)
class SnapshotEntry:
    path: str
    exists: bool
    content: str | None
    content_bytes: bytes | None = None
    binary: bool = False


@dataclass(slots=True)
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]


@dataclass(slots=True)
class FilePatch:
    old_path: str | None
    new_path: str | None
    hunks: list[DiffHunk]

    @property
    def touched_path(self) -> str:
        return self.new_path or self.old_path or ""


def _workspace_root(path: str | Path) -> Path:
    return Path(path).resolve()


def _normalize_external_roots(external_roots: list[str | Path] | None) -> list[Path]:
    roots: list[Path] = []
    for raw_root in external_roots or []:
        root = Path(raw_root).resolve()
        if root not in roots:
            roots.append(root)
    return roots


def _path_is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _absolute_for_normalized_path(workspace_root: Path, path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (workspace_root / candidate).resolve()


def _normalize_rel_path(
    workspace_root: Path,
    raw_path: str | Path,
    *,
    external_roots: list[Path] | None = None,
) -> str:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (workspace_root / candidate).resolve()
    try:
        return resolved.relative_to(workspace_root).as_posix()
    except ValueError as exc:
        for external_root in external_roots or []:
            try:
                resolved.relative_to(external_root)
            except ValueError:
                continue
            return resolved.as_posix()
        raise ValueError(f"path `{raw_path}` is outside the workspace root") from exc


def normalize_allowed_paths(
    workspace_root: str | Path,
    write_set: list[str],
    *,
    external_roots: list[str | Path] | None = None,
) -> list[str]:
    root = _workspace_root(workspace_root)
    external = _normalize_external_roots(external_roots)
    normalized: list[str] = []
    for item in write_set:
        rel_path = _normalize_rel_path(root, item, external_roots=external)
        if rel_path not in normalized:
            normalized.append(rel_path)
    return normalized


def is_path_allowed(path: str, allowed_paths: list[str]) -> bool:
    normalized = path.strip("/").replace("\\", "/")
    for allowed in allowed_paths:
        candidate = allowed.strip("/").replace("\\", "/")
        if normalized == candidate or normalized.startswith(candidate.rstrip("/") + "/"):
            return True
    return False


def capture_workspace_snapshot(
    workspace_root: str | Path,
    write_set: list[str],
    *,
    external_roots: list[str | Path] | None = None,
) -> dict[str, SnapshotEntry]:
    root = _workspace_root(workspace_root)
    external = _normalize_external_roots(external_roots)
    snapshot: dict[str, SnapshotEntry] = {}
    for raw_path in write_set:
        rel_path = _normalize_rel_path(root, raw_path, external_roots=external)
        absolute = _absolute_for_normalized_path(root, rel_path)
        if absolute.exists() and absolute.is_dir():
            for child in absolute.rglob("*"):
                if child.is_dir():
                    continue
                child_resolved = child.resolve()
                child_rel = (
                    child_resolved.relative_to(root).as_posix()
                    if _path_is_under(child_resolved, root)
                    else child_resolved.as_posix()
                )
                snapshot[child_rel] = _snapshot_file(child, child_rel)
            continue
        snapshot[rel_path] = _snapshot_file(absolute, rel_path) if absolute.exists() else SnapshotEntry(path=rel_path, exists=False, content=None)
    return snapshot


def _snapshot_file(path: Path, rel_path: str) -> SnapshotEntry:
    content_bytes = path.read_bytes()
    try:
        content = content_bytes.decode("utf-8")
        binary = False
    except UnicodeDecodeError:
        content = None
        binary = True
    return SnapshotEntry(path=rel_path, exists=True, content=content, content_bytes=content_bytes, binary=binary)


def restore_workspace_snapshot(
    workspace_root: str | Path,
    snapshot: dict[str, SnapshotEntry],
    *,
    extra_paths: list[str] | None = None,
    external_roots: list[str | Path] | None = None,
) -> None:
    root = _workspace_root(workspace_root)
    external = _normalize_external_roots(external_roots)
    restored_paths = set(snapshot)
    for entry in snapshot.values():
        absolute = _absolute_for_normalized_path(root, entry.path)
        if entry.exists:
            absolute.parent.mkdir(parents=True, exist_ok=True)
            if entry.content_bytes is not None:
                absolute.write_bytes(entry.content_bytes)
            else:
                absolute.write_text(entry.content or "", encoding="utf-8", newline="\n")
            continue
        if absolute.exists():
            absolute.unlink()
    for raw_path in extra_paths or []:
        rel_path = _normalize_rel_path(root, raw_path, external_roots=external)
        if rel_path in restored_paths:
            continue
        absolute = _absolute_for_normalized_path(root, rel_path)
        if absolute.exists():
            absolute.unlink()


def hash_patch_text(patch_text: str) -> str:
    return hashlib.sha256(patch_text.encode("utf-8")).hexdigest()


def _normalize_diff_path(raw_path: str) -> str | None:
    path = raw_path.strip().split("\t", 1)[0]
    if path == "/dev/null":
        return None
    if path.startswith("a/") or path.startswith("b/"):
        path = path[2:]
    return path.strip()


def _parse_apply_patch_blocks(patch_text: str) -> list[FilePatch]:
    def flush_hunk() -> None:
        nonlocal current_hunk_lines
        if current_file is None or not current_hunk_lines:
            current_hunk_lines = []
            return
        old_count = sum(1 for line in current_hunk_lines if not line.startswith("+"))
        new_count = sum(1 for line in current_hunk_lines if not line.startswith("-"))
        current_file.hunks.append(
            DiffHunk(
                old_start=1,
                old_count=old_count,
                new_start=1,
                new_count=new_count,
                lines=current_hunk_lines,
            )
        )
        current_hunk_lines = []

    def flush_file() -> None:
        nonlocal current_file
        flush_hunk()
        if current_file is None:
            return
        if current_file.new_path is not None and not current_file.hunks:
            raise ValueError("apply_patch file update contained no hunks")
        patches.append(current_file)
        current_file = None

    patches: list[FilePatch] = []
    current_file: FilePatch | None = None
    current_hunk_lines: list[str] = []
    in_patch = False
    for line in patch_text.splitlines():
        if line == "*** Begin Patch":
            in_patch = True
            continue
        if line == "*** End Patch":
            flush_file()
            in_patch = False
            continue
        if not in_patch:
            continue
        header_match = _APPLY_PATCH_FILE_HEADER_RE.match(line)
        if header_match is not None:
            flush_file()
            action = header_match.group("action")
            path = header_match.group("path").strip()
            old_path = None if action == "Add" else path
            new_path = None if action == "Delete" else path
            current_file = FilePatch(old_path=old_path, new_path=new_path, hunks=[])
            continue
        if current_file is None:
            continue
        if line.startswith("*** Move to: "):
            current_file.new_path = line.removeprefix("*** Move to: ").strip()
            continue
        if line.startswith("@@"):
            flush_hunk()
            continue
        if line[:1] in {" ", "+", "-"}:
            current_hunk_lines.append(line)
    if current_file is not None:
        flush_file()
    if not patches:
        raise ValueError("no file patches were found in the apply_patch block")
    return patches


def parse_unified_diff(patch_text: str) -> list[FilePatch]:
    if "*** Begin Patch" in patch_text and _APPLY_PATCH_FILE_HEADER_RE.search(patch_text):
        return _parse_apply_patch_blocks(patch_text)
    lines = patch_text.splitlines()
    patches: list[FilePatch] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("diff --git ") or line.startswith("index ") or line.startswith("new file mode ") or line.startswith("deleted file mode "):
            index += 1
            continue
        if not line.startswith("--- "):
            index += 1
            continue
        old_path = _normalize_diff_path(line[4:])
        index += 1
        if index >= len(lines) or not lines[index].startswith("+++ "):
            raise ValueError("unified diff is missing a `+++` header")
        new_path = _normalize_diff_path(lines[index][4:])
        index += 1
        hunks: list[DiffHunk] = []
        while index < len(lines):
            candidate = lines[index]
            if candidate.startswith("--- "):
                break
            if candidate.startswith("diff --git ") or candidate.startswith("index "):
                index += 1
                continue
            if not candidate.startswith("@@ "):
                index += 1
                continue
            match = _HUNK_HEADER_RE.match(candidate)
            if match is None:
                raise ValueError(f"invalid hunk header: {candidate}")
            index += 1
            hunk_lines: list[str] = []
            while index < len(lines):
                hunk_line = lines[index]
                if hunk_line.startswith("--- ") or hunk_line.startswith("@@ "):
                    break
                if hunk_line == r"\ No newline at end of file":
                    index += 1
                    continue
                prefix = hunk_line[:1]
                if prefix not in {" ", "+", "-"}:
                    break
                hunk_lines.append(hunk_line)
                index += 1
            hunks.append(
                DiffHunk(
                    old_start=int(match.group("old_start")),
                    old_count=int(match.group("old_count") or "1"),
                    new_start=int(match.group("new_start")),
                    new_count=int(match.group("new_count") or "1"),
                    lines=hunk_lines,
                )
            )
        if not hunks:
            raise ValueError("unified diff contained no hunks")
        patches.append(FilePatch(old_path=old_path, new_path=new_path, hunks=hunks))
    if not patches:
        raise ValueError("no file patches were found in the unified diff")
    return patches


def extract_touched_paths(
    patch_text: str,
    *,
    workspace_root: str | Path,
    external_roots: list[str | Path] | None = None,
) -> list[str]:
    root = _workspace_root(workspace_root)
    external = _normalize_external_roots(external_roots)
    return [
        _normalize_rel_path(root, file_patch.touched_path, external_roots=external)
        for file_patch in parse_unified_diff(patch_text)
        if file_patch.touched_path
    ]


def extract_deleted_paths(
    patch_text: str,
    *,
    workspace_root: str | Path,
    external_roots: list[str | Path] | None = None,
) -> list[str]:
    root = _workspace_root(workspace_root)
    external = _normalize_external_roots(external_roots)
    return [
        _normalize_rel_path(root, file_patch.touched_path, external_roots=external)
        for file_patch in parse_unified_diff(patch_text)
        if file_patch.touched_path and file_patch.new_path is None
    ]


def _apply_hunks(original_lines: list[str], hunks: list[DiffHunk]) -> list[str]:
    output: list[str] = []
    cursor = 0
    for hunk in hunks:
        target_index = max(hunk.old_start - 1, 0)
        if not _hunk_matches_at(original_lines, target_index, hunk.lines):
            matched_index = _find_hunk_context(original_lines, hunk.lines, start=cursor)
            if matched_index is not None:
                target_index = matched_index
        if target_index < cursor:
            raise ValueError("overlapping or out-of-order hunks are not supported")
        output.extend(original_lines[cursor:target_index])
        cursor = target_index
        for raw_line in hunk.lines:
            prefix = raw_line[:1]
            content = raw_line[1:]
            current = original_lines[cursor] if cursor < len(original_lines) else None
            if prefix == " ":
                if current != content:
                    raise ValueError(f"context mismatch while applying patch: expected `{content}`")
                output.append(content)
                cursor += 1
                continue
            if prefix == "-":
                if current != content:
                    raise ValueError(f"remove mismatch while applying patch: expected `{content}`")
                cursor += 1
                continue
            if prefix == "+":
                output.append(content)
                continue
            raise ValueError(f"unsupported patch prefix `{prefix}`")
    output.extend(original_lines[cursor:])
    return output


def _hunk_matches_at(original_lines: list[str], index: int, hunk_lines: list[str]) -> bool:
    if index < 0:
        return False
    cursor = index
    matched_existing_line = False
    for raw_line in hunk_lines:
        prefix = raw_line[:1]
        if prefix == "+":
            continue
        if prefix not in {" ", "-"}:
            return False
        matched_existing_line = True
        if cursor >= len(original_lines) or original_lines[cursor] != raw_line[1:]:
            return False
        cursor += 1
    return matched_existing_line


def _find_hunk_context(original_lines: list[str], hunk_lines: list[str], *, start: int) -> int | None:
    for candidate in range(max(start, 0), len(original_lines) + 1):
        if _hunk_matches_at(original_lines, candidate, hunk_lines):
            return candidate
    return None


def apply_unified_diff(
    workspace_root: str | Path,
    patch_text: str,
    *,
    allowed_paths: list[str],
    external_roots: list[str | Path] | None = None,
) -> list[str]:
    root = _workspace_root(workspace_root)
    external = _normalize_external_roots(external_roots)
    touched_paths: list[str] = []
    planned_writes: list[tuple[Path, str | None]] = []
    for file_patch in parse_unified_diff(patch_text):
        if not file_patch.touched_path:
            raise ValueError("patch is missing a target path")
        rel_path = _normalize_rel_path(root, file_patch.touched_path, external_roots=external)
        if not is_path_allowed(rel_path, allowed_paths):
            raise ValueError(f"patch attempted to modify out-of-scope path `{rel_path}`")
        target = _absolute_for_normalized_path(root, rel_path)
        touched_paths.append(rel_path)
        if file_patch.new_path is None:
            planned_writes.append((target, None))
            continue
        if file_patch.old_path is None and target.exists():
            raise ValueError(f"new-file patch target already exists `{rel_path}`")
        original_text = "" if file_patch.old_path is None else (target.read_text(encoding="utf-8") if target.exists() else "")
        original_lines = original_text.splitlines()
        updated_lines = _apply_hunks(original_lines, file_patch.hunks)
        new_text = "\n".join(updated_lines)
        if updated_lines:
            new_text += "\n"
        planned_writes.append((target, new_text))
    for target, new_text in planned_writes:
        if new_text is None:
            if target.exists():
                target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_text, encoding="utf-8", newline="\n")
    return sorted(set(touched_paths))
