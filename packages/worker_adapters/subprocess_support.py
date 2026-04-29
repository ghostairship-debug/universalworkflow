from __future__ import annotations

import os
import signal
import subprocess
import locale
import threading
import time
from collections.abc import Mapping
from typing import Any


TIMEOUT_EXIT_CODE = 124
DEFAULT_STREAM_PREVIEW_LIMIT = 4000

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
    timeout_type: str = "wall_timeout",
    stdout_event_count: int = 0,
    stderr_event_count: int = 0,
    last_output_age_seconds: float | None = None,
) -> subprocess.CompletedProcess[str]:
    stdout = normalize_timeout_stream(exc.stdout if hasattr(exc, "stdout") else exc.output)
    stderr = normalize_timeout_stream(exc.stderr)
    timeout_message = f"command timed out after {timeout_seconds}s ({timeout_type})"
    stderr = f"{stderr.rstrip()}\n{timeout_message}".strip() if stderr else timeout_message
    completed = subprocess.CompletedProcess(
        exc.cmd or command,
        TIMEOUT_EXIT_CODE,
        stdout=stdout,
        stderr=stderr,
    )
    _attach_watchdog_metadata(
        completed,
        timeout_type=timeout_type,
        stdout_event_count=stdout_event_count,
        stderr_event_count=stderr_event_count,
        last_output_age_seconds=last_output_age_seconds,
    )
    return completed


def _attach_watchdog_metadata(
    completed: subprocess.CompletedProcess[str],
    *,
    timeout_type: str | None,
    stdout_event_count: int,
    stderr_event_count: int,
    last_output_age_seconds: float | None,
) -> None:
    setattr(completed, "timeout_type", timeout_type)
    setattr(completed, "stdout_event_count", stdout_event_count)
    setattr(completed, "stderr_event_count", stderr_event_count)
    setattr(completed, "stream_event_count", stdout_event_count + stderr_event_count)
    setattr(completed, "last_output_age_seconds", last_output_age_seconds)


def completed_process_watchdog_metadata(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    timeout_type = getattr(completed, "timeout_type", None)
    stream_event_count = getattr(completed, "stream_event_count", None)
    stdout_event_count = getattr(completed, "stdout_event_count", None)
    stderr_event_count = getattr(completed, "stderr_event_count", None)
    last_output_age_seconds = getattr(completed, "last_output_age_seconds", None)
    metadata: dict[str, Any] = {}
    if timeout_type is not None:
        metadata["timeout_type"] = timeout_type
        metadata["timeout_failure_class"] = (
            "provider_idle_timeout" if timeout_type == "idle_timeout" else "provider_wall_timeout"
        )
    if stream_event_count is not None:
        metadata["stream_event_count"] = int(stream_event_count)
    if stdout_event_count is not None:
        metadata["stdout_event_count"] = int(stdout_event_count)
    if stderr_event_count is not None:
        metadata["stderr_event_count"] = int(stderr_event_count)
    if last_output_age_seconds is not None:
        metadata["last_output_age_seconds"] = float(last_output_age_seconds)
    if timeout_type is not None:
        metadata["recovery_suggestion"] = (
            "retry_with_higher_idle_timeout_or_split_task"
            if timeout_type == "idle_timeout"
            else "split_task_or_raise_wall_timeout_with_progress_evidence"
        )
    return metadata


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
    raw_idle_timeout = run_kwargs.pop("idle_timeout", None)
    idle_timeout_seconds = float(raw_idle_timeout) if raw_idle_timeout is not None else None
    capture_output = bool(run_kwargs.pop("capture_output", False))
    check = bool(run_kwargs.pop("check", False))
    text = bool(run_kwargs.pop("text", False))
    stdin_value = run_kwargs.pop("input", None)
    run_kwargs.pop("encoding", None)
    run_kwargs.pop("errors", None)
    run_kwargs.pop("universal_newlines", None)
    if text and isinstance(stdin_value, str):
        stdin_value = stdin_value.encode("utf-8")
    stdout_target = subprocess.PIPE if capture_output else None
    stderr_target = subprocess.PIPE if capture_output else None
    popen_kwargs: dict[str, Any] = {
        "cwd": run_kwargs.pop("cwd", None),
        "env": run_kwargs.pop("env", None),
        "stdin": subprocess.PIPE if stdin_value is not None else None,
        "stdout": stdout_target,
        "stderr": stderr_target,
        "text": False,
        **run_kwargs,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(command, **popen_kwargs)
    started_at = time.monotonic()
    last_output_at = started_at
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    stdout_event_count = 0
    stderr_event_count = 0
    stream_lock = threading.Lock()

    def _record_output(target: list[bytes], data: bytes, stream_name: str) -> None:
        nonlocal last_output_at, stdout_event_count, stderr_event_count
        if not data:
            return
        with stream_lock:
            target.append(data)
            last_output_at = time.monotonic()
            if stream_name == "stdout":
                stdout_event_count += 1
            else:
                stderr_event_count += 1

    def _read_stream(pipe: Any, target: list[bytes], stream_name: str) -> None:
        try:
            while True:
                data = pipe.readline()
                if not data:
                    break
                _record_output(target, data, stream_name)
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    def _write_stdin() -> None:
        if process.stdin is None or stdin_value is None:
            return
        try:
            process.stdin.write(stdin_value)
            process.stdin.close()
        except Exception:
            try:
                process.stdin.close()
            except Exception:
                pass

    threads: list[threading.Thread] = []
    if process.stdout is not None:
        thread = threading.Thread(target=_read_stream, args=(process.stdout, stdout_chunks, "stdout"), daemon=True)
        thread.start()
        threads.append(thread)
    if process.stderr is not None:
        thread = threading.Thread(target=_read_stream, args=(process.stderr, stderr_chunks, "stderr"), daemon=True)
        thread.start()
        threads.append(thread)
    if stdin_value is not None:
        thread = threading.Thread(target=_write_stdin, daemon=True)
        thread.start()
        threads.append(thread)

    timeout_type: str | None = None
    try:
        while process.poll() is None:
            now = time.monotonic()
            if now - started_at >= timeout_seconds:
                timeout_type = "wall_timeout"
                break
            if idle_timeout_seconds is not None and idle_timeout_seconds > 0 and now - last_output_at >= idle_timeout_seconds:
                timeout_type = "idle_timeout"
                break
            time.sleep(0.05)
    except BaseException:
        terminate_process_tree(process.pid)
        raise

    if timeout_type is not None:
        terminate_process_tree(process.pid)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    for thread in threads:
        thread.join(timeout=1)

    stdout = b"".join(stdout_chunks) if capture_output else None
    stderr = b"".join(stderr_chunks) if capture_output else None
    last_output_age_seconds = max(time.monotonic() - last_output_at, 0.0)
    if timeout_type is not None:
        completed = subprocess.CompletedProcess(
            command,
            TIMEOUT_EXIT_CODE,
            stdout=decode_subprocess_stream(stdout),
            stderr=decode_subprocess_stream(stderr),
        )
        timeout_budget = int(idle_timeout_seconds) if timeout_type == "idle_timeout" and idle_timeout_seconds else timeout_seconds
        timeout_message = f"command timed out after {timeout_budget}s ({timeout_type})"
        completed.stderr = f"{completed.stderr.rstrip()}\n{timeout_message}".strip() if completed.stderr else timeout_message
        _attach_watchdog_metadata(
            completed,
            timeout_type=timeout_type,
            stdout_event_count=stdout_event_count,
            stderr_event_count=stderr_event_count,
            last_output_age_seconds=last_output_age_seconds,
        )
        return completed

    completed = subprocess.CompletedProcess(
        command,
        process.returncode,
        stdout=decode_subprocess_stream(stdout),
        stderr=decode_subprocess_stream(stderr),
    )
    _attach_watchdog_metadata(
        completed,
        timeout_type=None,
        stdout_event_count=stdout_event_count,
        stderr_event_count=stderr_event_count,
        last_output_age_seconds=last_output_age_seconds,
    )
    if check and completed.returncode:
        completed.check_returncode()
    return completed
