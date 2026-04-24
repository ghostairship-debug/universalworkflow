from __future__ import annotations

import hashlib
import os
import re
import shlex
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter


_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)
TEST_COMMAND_TIMEOUT_SECONDS = 120
TEST_COMMAND_OUTPUT_LIMIT_BYTES = 64 * 1024
TEST_COMMAND_BLOCKED_EXIT_CODE = 126
TEST_COMMAND_NOT_FOUND_EXIT_CODE = 127
TEST_COMMAND_TIMEOUT_EXIT_CODE = 124

_SECRET_ENV_NAME_RE = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|AUTH|COOKIE)", re.IGNORECASE)
_SHELL_METACHAR_RE = re.compile(r"[\r\n|&;<>`]|(?:\$\()|(?:\$\{)")
_TEST_ENV_ALLOWLIST = {
    "APPDATA",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "SYSTEMROOT",
    "TEMP",
    "TERM",
    "TMP",
    "TZ",
    "USER",
    "USERNAME",
    "USERPROFILE",
    "VIRTUAL_ENV",
    "WINDIR",
}
_TEST_ENV_ALLOWLIST_PREFIXES = (
    "CONDA",
    "PIP_",
    "PYTEST_",
    "PYTHON",
    "UV_",
)
_DANGEROUS_PROGRAMS = {
    "bash",
    "cmd",
    "curl",
    "del",
    "erase",
    "nc",
    "netcat",
    "powershell",
    "pwsh",
    "rd",
    "rmdir",
    "rm",
    "scp",
    "sftp",
    "sh",
    "ssh",
    "telnet",
    "wget",
}


@dataclass(slots=True)
class SnapshotEntry:
    path: str
    exists: bool
    content: str | None


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


@dataclass(frozen=True, slots=True)
class TestCommandSpec:
    command: str | list[str]
    timeout_seconds: int = TEST_COMMAND_TIMEOUT_SECONDS
    output_limit_bytes: int = TEST_COMMAND_OUTPUT_LIMIT_BYTES
    env: Mapping[str, str] | None = None


def _workspace_root(path: str | Path) -> Path:
    return Path(path).resolve()


def _normalize_rel_path(workspace_root: Path, raw_path: str | Path) -> str:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (workspace_root / candidate).resolve()
    try:
        return resolved.relative_to(workspace_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path `{raw_path}` is outside the workspace root") from exc


def normalize_allowed_paths(workspace_root: str | Path, write_set: list[str]) -> list[str]:
    root = _workspace_root(workspace_root)
    normalized: list[str] = []
    for item in write_set:
        rel_path = _normalize_rel_path(root, item)
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


def capture_workspace_snapshot(workspace_root: str | Path, write_set: list[str]) -> dict[str, SnapshotEntry]:
    root = _workspace_root(workspace_root)
    snapshot: dict[str, SnapshotEntry] = {}
    for raw_path in write_set:
        rel_path = _normalize_rel_path(root, raw_path)
        absolute = root / rel_path
        if absolute.exists() and absolute.is_dir():
            for child in absolute.rglob("*"):
                if child.is_dir():
                    continue
                child_rel = child.resolve().relative_to(root).as_posix()
                snapshot[child_rel] = SnapshotEntry(
                    path=child_rel,
                    exists=True,
                    content=child.read_text(encoding="utf-8"),
                )
            continue
        snapshot[rel_path] = SnapshotEntry(
            path=rel_path,
            exists=absolute.exists(),
            content=absolute.read_text(encoding="utf-8") if absolute.exists() else None,
        )
    return snapshot


def restore_workspace_snapshot(
    workspace_root: str | Path,
    snapshot: dict[str, SnapshotEntry],
    *,
    extra_paths: list[str] | None = None,
) -> None:
    root = _workspace_root(workspace_root)
    restored_paths = set(snapshot)
    for entry in snapshot.values():
        absolute = root / entry.path
        if entry.exists:
            absolute.parent.mkdir(parents=True, exist_ok=True)
            absolute.write_text(entry.content or "", encoding="utf-8")
            continue
        if absolute.exists():
            absolute.unlink()
    for raw_path in extra_paths or []:
        rel_path = _normalize_rel_path(root, raw_path)
        if rel_path in restored_paths:
            continue
        absolute = root / rel_path
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


def parse_unified_diff(patch_text: str) -> list[FilePatch]:
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


def extract_touched_paths(patch_text: str, *, workspace_root: str | Path) -> list[str]:
    root = _workspace_root(workspace_root)
    return [
        _normalize_rel_path(root, file_patch.touched_path)
        for file_patch in parse_unified_diff(patch_text)
        if file_patch.touched_path
    ]


def _apply_hunks(original_lines: list[str], hunks: list[DiffHunk]) -> list[str]:
    output: list[str] = []
    cursor = 0
    for hunk in hunks:
        target_index = max(hunk.old_start - 1, 0)
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


def apply_unified_diff(
    workspace_root: str | Path,
    patch_text: str,
    *,
    allowed_paths: list[str],
) -> list[str]:
    root = _workspace_root(workspace_root)
    touched_paths: list[str] = []
    for file_patch in parse_unified_diff(patch_text):
        if not file_patch.touched_path:
            raise ValueError("patch is missing a target path")
        rel_path = _normalize_rel_path(root, file_patch.touched_path)
        if not is_path_allowed(rel_path, allowed_paths):
            raise ValueError(f"patch attempted to modify out-of-scope path `{rel_path}`")
        target = root / rel_path
        touched_paths.append(rel_path)
        if file_patch.new_path is None:
            if target.exists():
                target.unlink()
            continue
        original_text = target.read_text(encoding="utf-8") if target.exists() else ""
        original_lines = original_text.splitlines()
        updated_lines = _apply_hunks(original_lines, file_patch.hunks)
        target.parent.mkdir(parents=True, exist_ok=True)
        new_text = "\n".join(updated_lines)
        if updated_lines:
            new_text += "\n"
        target.write_text(new_text, encoding="utf-8")
    return sorted(set(touched_paths))


def _is_secret_env_name(name: str) -> bool:
    return bool(_SECRET_ENV_NAME_RE.search(name))


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _secret_values_from_env() -> list[str]:
    values = {
        value
        for name, value in os.environ.items()
        if value and len(value) >= 4 and _is_secret_env_name(name.upper())
    }
    return sorted(values, key=len, reverse=True)


def _redact_text(value: str | bytes | None) -> str:
    if value is None:
        text = ""
    elif isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)
    for secret_value in _secret_values_from_env():
        text = text.replace(secret_value, "[REDACTED]")
    return text


def _truncate_output(value: str | bytes | None, *, limit: int) -> tuple[str, bool]:
    text = _redact_text(value)
    if len(text) <= limit:
        return text, False
    marker = "\n...[truncated]"
    keep = max(limit - len(marker), 0)
    return f"{text[:keep]}{marker}", True


def _build_test_command_env(extra_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    for name, value in os.environ.items():
        upper_name = name.upper()
        if _is_secret_env_name(upper_name):
            continue
        if upper_name in _TEST_ENV_ALLOWLIST or any(upper_name.startswith(prefix) for prefix in _TEST_ENV_ALLOWLIST_PREFIXES):
            env[name] = value
    if extra_env:
        for name, value in extra_env.items():
            upper_name = str(name).upper()
            if _is_secret_env_name(upper_name):
                continue
            env[str(name)] = str(value)
    return env


def _command_display(command: str | list[str]) -> str:
    if isinstance(command, str):
        return command
    return " ".join(str(part) for part in command)


def _parse_test_command(command: str | list[str]) -> list[str]:
    if isinstance(command, list):
        argv = [str(part) for part in command]
    else:
        if _SHELL_METACHAR_RE.search(command):
            raise ValueError("shell metacharacters are not allowed in test commands")
        try:
            argv = shlex.split(command, posix=False)
        except ValueError as exc:
            raise ValueError(f"test command could not be parsed safely: {exc}") from exc
        argv = [_strip_wrapping_quotes(part) for part in argv]
    argv = [part for part in argv if part]
    if not argv:
        raise ValueError("test command is empty")
    program_name = argv[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in (".exe", ".cmd", ".bat", ".ps1"):
        if program_name.endswith(suffix):
            program_name = program_name[: -len(suffix)]
            break
    if program_name in _DANGEROUS_PROGRAMS:
        raise ValueError(f"test command program `{program_name}` requires manual review")
    return argv


def _attempt_payload(
    *,
    command: str,
    argv: list[str],
    return_code: int,
    stdout: str | bytes | None,
    stderr: str | bytes | None,
    duration_ms: int,
    output_limit_bytes: int,
    status: str,
    blocked_reason: str | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, object]:
    stdout_text, stdout_truncated = _truncate_output(stdout, limit=output_limit_bytes)
    stderr_text, stderr_truncated = _truncate_output(stderr, limit=output_limit_bytes)
    payload: dict[str, object] = {
        "command": command,
        "argv": argv,
        "return_code": return_code,
        "stdout": stdout_text,
        "stderr": stderr_text,
        "duration_ms": duration_ms,
        "passed": return_code == 0,
        "status": status,
        "timeout_seconds": timeout_seconds,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "output_limit_bytes": output_limit_bytes,
    }
    if blocked_reason is not None:
        payload["blocked_reason"] = blocked_reason
        payload["review_required"] = True
    return payload


def _coerce_test_command_spec(command: str | TestCommandSpec) -> TestCommandSpec:
    if isinstance(command, TestCommandSpec):
        return command
    return TestCommandSpec(command=command)


def run_test_commands(commands: list[str | TestCommandSpec], *, working_directory: str | Path) -> list[dict[str, object]]:
    attempts: list[dict[str, object]] = []
    for raw_command in commands:
        spec = _coerce_test_command_spec(raw_command)
        command = _command_display(spec.command)
        started_at = perf_counter()
        try:
            argv = _parse_test_command(spec.command)
        except ValueError as exc:
            duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
            attempts.append(
                _attempt_payload(
                    command=command,
                    argv=[],
                    return_code=TEST_COMMAND_BLOCKED_EXIT_CODE,
                    stdout="",
                    stderr=str(exc),
                    duration_ms=duration_ms,
                    output_limit_bytes=spec.output_limit_bytes,
                    status="blocked",
                    blocked_reason=str(exc),
                    timeout_seconds=spec.timeout_seconds,
                )
            )
            break
        try:
            completed = subprocess.run(
                argv,
                cwd=str(_workspace_root(working_directory)),
                shell=False,
                capture_output=True,
                text=True,
                env=_build_test_command_env(spec.env),
                timeout=spec.timeout_seconds,
                check=False,
            )
            duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
            attempt = _attempt_payload(
                command=command,
                argv=argv,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_ms=duration_ms,
                output_limit_bytes=spec.output_limit_bytes,
                status="passed" if completed.returncode == 0 else "failed",
                timeout_seconds=spec.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
            stderr = _redact_text(exc.stderr)
            timeout_message = f"command timed out after {spec.timeout_seconds}s"
            stderr = f"{stderr.rstrip()}\n{timeout_message}".strip() if stderr else timeout_message
            attempt = _attempt_payload(
                command=command,
                argv=argv,
                return_code=TEST_COMMAND_TIMEOUT_EXIT_CODE,
                stdout=exc.stdout if hasattr(exc, "stdout") else exc.output,
                stderr=stderr,
                duration_ms=duration_ms,
                output_limit_bytes=spec.output_limit_bytes,
                status="timeout",
                timeout_seconds=spec.timeout_seconds,
            )
        except FileNotFoundError:
            duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
            attempt = _attempt_payload(
                command=command,
                argv=argv,
                return_code=TEST_COMMAND_NOT_FOUND_EXIT_CODE,
                stdout="",
                stderr=f"command not found: {argv[0]}",
                duration_ms=duration_ms,
                output_limit_bytes=spec.output_limit_bytes,
                status="not_found",
                timeout_seconds=spec.timeout_seconds,
            )
        attempts.append(attempt)
        if not bool(attempt["passed"]):
            break
    return attempts
