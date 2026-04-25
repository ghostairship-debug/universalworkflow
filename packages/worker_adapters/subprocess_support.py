from __future__ import annotations

import os
import signal
import subprocess
import locale
from collections.abc import Mapping
from typing import Any


TIMEOUT_EXIT_CODE = 124

_ENV_ALLOWLIST = {
    "APPDATA",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "LOGNAME",
    "NO_PROXY",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "REQUESTS_CA_BUNDLE",
    "SSL_CERT_FILE",
    "SYSTEMROOT",
    "TEMP",
    "TERM",
    "TMP",
    "TZ",
    "USER",
    "USERNAME",
    "USERPROFILE",
    "WINDIR",
    "HTTP_PROXY",
    "HTTPS_PROXY",
}
_ENV_ALLOWLIST_PREFIXES = (
    "ANTHROPIC_",
    "CLAUDE_",
    "CLOUDSDK_",
    "CODEX_",
    "DEEPSEEK_",
    "GOOGLE_",
    "MINIMAX_",
    "OPENAI_",
    "OPENCODE_",
    "PYTHON",
    "VERTEX_",
    "WORKFLOW_",
)


def build_subprocess_env(packet_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    for name, value in os.environ.items():
        upper_name = name.upper()
        if upper_name in _ENV_ALLOWLIST or any(upper_name.startswith(prefix) for prefix in _ENV_ALLOWLIST_PREFIXES):
            env[name] = value
    if packet_env:
        env.update({str(name): str(value) for name, value in packet_env.items()})
    return env


def decode_subprocess_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if not isinstance(value, bytes):
        return str(value)
    encodings = ["utf-8", locale.getpreferredencoding(False)]
    if os.name == "nt":
        encodings.append("mbcs")
    seen: set[str] = set()
    for encoding in encodings:
        if not encoding or encoding.lower() in seen:
            continue
        seen.add(encoding.lower())
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", errors="replace")


def normalize_timeout_stream(value: str | bytes | None) -> str:
    return decode_subprocess_stream(value)


def completed_process_from_timeout(
    exc: subprocess.TimeoutExpired,
    *,
    command: list[str] | str,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    stdout = normalize_timeout_stream(exc.stdout if hasattr(exc, "stdout") else exc.output)
    stderr = normalize_timeout_stream(exc.stderr)
    timeout_message = f"command timed out after {timeout_seconds}s"
    stderr = f"{stderr.rstrip()}\n{timeout_message}".strip() if stderr else timeout_message
    return subprocess.CompletedProcess(
        exc.cmd or command,
        TIMEOUT_EXIT_CODE,
        stdout=stdout,
        stderr=stderr,
    )


def terminate_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def run_subprocess_with_tree_timeout(command: list[str], **run_kwargs: Any) -> subprocess.CompletedProcess[str]:
    timeout_seconds = int(run_kwargs.pop("timeout"))
    capture_output = bool(run_kwargs.pop("capture_output", False))
    check = bool(run_kwargs.pop("check", False))
    text = bool(run_kwargs.pop("text", False))
    stdin_value = run_kwargs.pop("input", None)
    stdout_target = subprocess.PIPE if capture_output else None
    stderr_target = subprocess.PIPE if capture_output else None
    popen_kwargs: dict[str, Any] = {
        "cwd": run_kwargs.pop("cwd", None),
        "env": run_kwargs.pop("env", None),
        "stdin": subprocess.PIPE if stdin_value is not None else None,
        "stdout": stdout_target,
        "stderr": stderr_target,
        "text": text,
        **run_kwargs,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(command, **popen_kwargs)
    try:
        stdout, stderr = process.communicate(stdin_value, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        terminate_process_tree(process.pid)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        exc.stdout = stdout if stdout is not None else exc.stdout
        exc.stderr = stderr if stderr is not None else exc.stderr
        return completed_process_from_timeout(exc, command=command, timeout_seconds=timeout_seconds)

    completed = subprocess.CompletedProcess(command, process.returncode, stdout=stdout or "", stderr=stderr or "")
    if check and completed.returncode:
        completed.check_returncode()
    return completed
