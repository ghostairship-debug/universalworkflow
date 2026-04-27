from __future__ import annotations

import os
import re
import shlex
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any


SAFE_COMMAND_TIMEOUT_SECONDS = 120
SAFE_COMMAND_OUTPUT_LIMIT_BYTES = 64 * 1024
SAFE_COMMAND_BLOCKED_EXIT_CODE = 126
SAFE_COMMAND_NOT_FOUND_EXIT_CODE = 127
SAFE_COMMAND_TIMEOUT_EXIT_CODE = 124

_SECRET_ENV_NAME_RE = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|AUTH|COOKIE)", re.IGNORECASE)
_SHELL_METACHAR_RE = re.compile(r"[\r\n|&;<>`]|(?:\$\()|(?:\$\{)")
_ENV_ALLOWLIST = {
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
_ENV_ALLOWLIST_PREFIXES = (
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


@dataclass(frozen=True, slots=True)
class SafeCommandSpec:
    command: str | list[str]
    timeout_seconds: int = SAFE_COMMAND_TIMEOUT_SECONDS
    output_limit_bytes: int = SAFE_COMMAND_OUTPUT_LIMIT_BYTES
    env: Mapping[str, str] | None = None


def _workspace_root(path: str | Path) -> Path:
    return Path(path).resolve()


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


def redact_text(value: str | bytes | None) -> str:
    if value is None:
        text = ""
    elif isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)
    for secret_value in _secret_values_from_env():
        text = text.replace(secret_value, "[REDACTED]")
    return text


def truncate_output(value: str | bytes | None, *, limit: int) -> tuple[str, bool]:
    text = redact_text(value)
    if len(text) <= limit:
        return text, False
    marker = "\n...[truncated]"
    keep = max(limit - len(marker), 0)
    return f"{text[:keep]}{marker}", True


def build_safe_command_env(extra_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    for name, value in os.environ.items():
        upper_name = name.upper()
        if _is_secret_env_name(upper_name):
            continue
        if upper_name in _ENV_ALLOWLIST or any(upper_name.startswith(prefix) for prefix in _ENV_ALLOWLIST_PREFIXES):
            env[name] = value
    if extra_env:
        for name, value in extra_env.items():
            upper_name = str(name).upper()
            if _is_secret_env_name(upper_name):
                continue
            env[str(name)] = str(value)
    return env


def command_display(command: str | list[str]) -> str:
    if isinstance(command, str):
        return command
    return " ".join(str(part) for part in command)


def parse_safe_command(command: str | list[str]) -> list[str]:
    if isinstance(command, list):
        argv = [str(part) for part in command]
    else:
        if _SHELL_METACHAR_RE.search(command):
            raise ValueError("shell metacharacters are not allowed in commands")
        try:
            argv = shlex.split(command, posix=False)
        except ValueError as exc:
            raise ValueError(f"command could not be parsed safely: {exc}") from exc
        argv = [_strip_wrapping_quotes(part) for part in argv]
    argv = [part for part in argv if part]
    if not argv:
        raise ValueError("command is empty")
    program_name = argv[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in (".exe", ".cmd", ".bat", ".ps1"):
        if program_name.endswith(suffix):
            program_name = program_name[: -len(suffix)]
            break
    if program_name in _DANGEROUS_PROGRAMS:
        raise ValueError(f"command program `{program_name}` requires manual review")
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
    stdout_text, stdout_truncated = truncate_output(stdout, limit=output_limit_bytes)
    stderr_text, stderr_truncated = truncate_output(stderr, limit=output_limit_bytes)
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


def _coerce_spec(command: str | SafeCommandSpec) -> SafeCommandSpec:
    if isinstance(command, SafeCommandSpec):
        return command
    return SafeCommandSpec(command=command)


def run_safe_commands(commands: list[str | SafeCommandSpec], *, working_directory: str | Path) -> list[dict[str, object]]:
    attempts: list[dict[str, object]] = []
    for raw_command in commands:
        spec = _coerce_spec(raw_command)
        command = command_display(spec.command)
        started_at = perf_counter()
        try:
            argv = parse_safe_command(spec.command)
        except ValueError as exc:
            duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
            attempts.append(
                _attempt_payload(
                    command=command,
                    argv=[],
                    return_code=SAFE_COMMAND_BLOCKED_EXIT_CODE,
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
                env=build_safe_command_env(spec.env),
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
            stderr = redact_text(exc.stderr)
            timeout_message = f"command timed out after {spec.timeout_seconds}s"
            stderr = f"{stderr.rstrip()}\n{timeout_message}".strip() if stderr else timeout_message
            attempt = _attempt_payload(
                command=command,
                argv=argv,
                return_code=SAFE_COMMAND_TIMEOUT_EXIT_CODE,
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
                return_code=SAFE_COMMAND_NOT_FOUND_EXIT_CODE,
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


def run_safe_command(
    command: str | list[str],
    *,
    working_directory: str | Path,
    timeout_seconds: int = SAFE_COMMAND_TIMEOUT_SECONDS,
    output_limit_bytes: int = 12_000,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    attempts = run_safe_commands(
        [
            SafeCommandSpec(
                command=command,
                timeout_seconds=timeout_seconds,
                output_limit_bytes=output_limit_bytes,
                env=env,
            )
        ],
        working_directory=working_directory,
    )
    attempt = attempts[0]
    return {
        "command": attempt["command"],
        "argv": attempt["argv"],
        "cwd": Path(working_directory).resolve().as_posix(),
        "exit_code": attempt["return_code"],
        "stdout": attempt["stdout"],
        "stderr": attempt["stderr"],
        "status": attempt["status"],
        "duration_ms": attempt["duration_ms"],
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
    }
