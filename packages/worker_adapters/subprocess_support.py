from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping


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
    "OPENAI_",
    "OPENCODE_",
    "PYTHON",
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


def normalize_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
