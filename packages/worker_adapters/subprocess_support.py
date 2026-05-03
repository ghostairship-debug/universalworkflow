from __future__ import annotations

import os
import json
import signal
import subprocess
import locale
import sys
import threading
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


TIMEOUT_EXIT_CODE = 124
DEFAULT_STREAM_PREVIEW_LIMIT = 4000
CONTROL_OUTPUT_PREFIXES = ("workflow_progress",)
MATERIAL_PROGRESS_TOKENS = (
    "applied_patch_hash",
    "changed_files",
    "evidence_id",
    "final_test_status",
    "mutation_result",
    "runtime_task_completed",
    "Repo mutation completed successfully",
    "Execution completed successfully",
)

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
    provider_output_event_count: int | None = None,
    control_output_event_count: int | None = None,
    material_progress_event_count: int | None = None,
    last_provider_output_age_seconds: float | None = None,
    last_material_progress_age_seconds: float | None = None,
    last_provider_output_at: str | None = None,
    last_material_progress_at: str | None = None,
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
        provider_output_event_count=provider_output_event_count,
        control_output_event_count=control_output_event_count,
        material_progress_event_count=material_progress_event_count,
        last_provider_output_age_seconds=last_provider_output_age_seconds,
        last_material_progress_age_seconds=last_material_progress_age_seconds,
        last_provider_output_at=last_provider_output_at,
        last_material_progress_at=last_material_progress_at,
    )
    return completed


def _attach_watchdog_metadata(
    completed: subprocess.CompletedProcess[str],
    *,
    timeout_type: str | None,
    stdout_event_count: int,
    stderr_event_count: int,
    last_output_age_seconds: float | None,
    provider_output_event_count: int | None = None,
    control_output_event_count: int | None = None,
    material_progress_event_count: int | None = None,
    last_provider_output_age_seconds: float | None = None,
    last_material_progress_age_seconds: float | None = None,
    last_provider_output_at: str | None = None,
    last_material_progress_at: str | None = None,
    adaptive_wall_timeout_extension_count: int = 0,
    adaptive_wall_timeout_effective_seconds: int | None = None,
    adaptive_wall_timeout_absolute_max_seconds: int | None = None,
    adaptive_wall_timeout_exhausted: bool = False,
) -> None:
    setattr(completed, "timeout_type", timeout_type)
    setattr(completed, "stdout_event_count", stdout_event_count)
    setattr(completed, "stderr_event_count", stderr_event_count)
    setattr(completed, "stream_event_count", stdout_event_count + stderr_event_count)
    setattr(completed, "last_output_age_seconds", last_output_age_seconds)
    if provider_output_event_count is not None:
        setattr(completed, "provider_output_event_count", provider_output_event_count)
    if control_output_event_count is not None:
        setattr(completed, "control_output_event_count", control_output_event_count)
    if material_progress_event_count is not None:
        setattr(completed, "material_progress_event_count", material_progress_event_count)
    if last_provider_output_age_seconds is not None:
        setattr(completed, "last_provider_output_age_seconds", last_provider_output_age_seconds)
    if last_material_progress_age_seconds is not None:
        setattr(completed, "last_material_progress_age_seconds", last_material_progress_age_seconds)
    if last_provider_output_at is not None:
        setattr(completed, "last_provider_output_at", last_provider_output_at)
    if last_material_progress_at is not None:
        setattr(completed, "last_material_progress_at", last_material_progress_at)
    setattr(completed, "adaptive_wall_timeout_extension_count", int(adaptive_wall_timeout_extension_count))
    if adaptive_wall_timeout_effective_seconds is not None:
        setattr(completed, "adaptive_wall_timeout_effective_seconds", int(adaptive_wall_timeout_effective_seconds))
    if adaptive_wall_timeout_absolute_max_seconds is not None:
        setattr(completed, "adaptive_wall_timeout_absolute_max_seconds", int(adaptive_wall_timeout_absolute_max_seconds))
    setattr(completed, "adaptive_wall_timeout_exhausted", bool(adaptive_wall_timeout_exhausted))


def completed_process_watchdog_metadata(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    timeout_type = getattr(completed, "timeout_type", None)
    stream_event_count = getattr(completed, "stream_event_count", None)
    stdout_event_count = getattr(completed, "stdout_event_count", None)
    stderr_event_count = getattr(completed, "stderr_event_count", None)
    last_output_age_seconds = getattr(completed, "last_output_age_seconds", None)
    provider_output_event_count = getattr(completed, "provider_output_event_count", None)
    control_output_event_count = getattr(completed, "control_output_event_count", None)
    material_progress_event_count = getattr(completed, "material_progress_event_count", None)
    last_provider_output_age_seconds = getattr(completed, "last_provider_output_age_seconds", None)
    last_material_progress_age_seconds = getattr(completed, "last_material_progress_age_seconds", None)
    last_provider_output_at = getattr(completed, "last_provider_output_at", None)
    last_material_progress_at = getattr(completed, "last_material_progress_at", None)
    adaptive_wall_timeout_extension_count = getattr(completed, "adaptive_wall_timeout_extension_count", None)
    adaptive_wall_timeout_effective_seconds = getattr(completed, "adaptive_wall_timeout_effective_seconds", None)
    adaptive_wall_timeout_absolute_max_seconds = getattr(completed, "adaptive_wall_timeout_absolute_max_seconds", None)
    adaptive_wall_timeout_exhausted = getattr(completed, "adaptive_wall_timeout_exhausted", None)
    metadata: dict[str, Any] = {}
    if timeout_type is not None:
        metadata["timeout_type"] = timeout_type
        metadata["timeout_failure_class"] = {
            "idle_timeout": "provider_idle_timeout",
            "wall_timeout": "provider_wall_timeout",
            "adaptive_wall_timeout_exhausted": "task_scope_too_large_after_adaptive_wall_timeout",
            "provider_output_idle_timeout": "provider_output_idle_timeout",
            "provider_no_material_progress_timeout": "provider_no_material_progress_timeout",
        }.get(str(timeout_type), "provider_wall_timeout")
    if stream_event_count is not None:
        metadata["stream_event_count"] = int(stream_event_count)
    if stdout_event_count is not None:
        metadata["stdout_event_count"] = int(stdout_event_count)
    if stderr_event_count is not None:
        metadata["stderr_event_count"] = int(stderr_event_count)
    if last_output_age_seconds is not None:
        metadata["last_output_age_seconds"] = float(last_output_age_seconds)
    if provider_output_event_count is not None:
        metadata["provider_output_event_count"] = int(provider_output_event_count)
    if control_output_event_count is not None:
        metadata["control_output_event_count"] = int(control_output_event_count)
    if material_progress_event_count is not None:
        metadata["material_progress_event_count"] = int(material_progress_event_count)
    if last_provider_output_age_seconds is not None:
        metadata["last_provider_output_age_seconds"] = float(last_provider_output_age_seconds)
    if last_material_progress_age_seconds is not None:
        metadata["last_material_progress_age_seconds"] = float(last_material_progress_age_seconds)
    if last_provider_output_at is not None:
        metadata["last_provider_output_at"] = str(last_provider_output_at)
    if last_material_progress_at is not None:
        metadata["last_material_progress_at"] = str(last_material_progress_at)
    if adaptive_wall_timeout_extension_count is not None:
        metadata["adaptive_wall_timeout_extension_count"] = int(adaptive_wall_timeout_extension_count)
    if adaptive_wall_timeout_effective_seconds is not None:
        metadata["adaptive_wall_timeout_effective_seconds"] = int(adaptive_wall_timeout_effective_seconds)
    if adaptive_wall_timeout_absolute_max_seconds is not None:
        metadata["adaptive_wall_timeout_absolute_max_seconds"] = int(adaptive_wall_timeout_absolute_max_seconds)
    if adaptive_wall_timeout_exhausted is not None:
        metadata["adaptive_wall_timeout_exhausted"] = bool(adaptive_wall_timeout_exhausted)
    if timeout_type is not None:
        metadata["recovery_suggestion"] = {
            "idle_timeout": "retry_with_higher_idle_timeout_or_split_task",
            "wall_timeout": "split_task_or_raise_wall_timeout_with_progress_evidence",
            "adaptive_wall_timeout_exhausted": "split_or_narrow_task_after_adaptive_wall_timeout_exhausted",
            "provider_output_idle_timeout": "restart_with_fresh_receipt_after_provider_output_idle",
            "provider_no_material_progress_timeout": "restart_or_split_after_no_material_progress",
        }.get(str(timeout_type), "inspect_process_watchdog_metadata")
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


def run_subprocess_with_direct_visible_cli(command: list[str], **run_kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a provider CLI in a real Windows console while mirroring logs.

    This is intentionally separate from ``run_subprocess_with_tree_timeout``: the
    provider process should be human-visible, but the workflow still needs
    machine-readable stdout/stderr/session evidence and watchdog metadata.
    """

    if os.name != "nt" or not hasattr(subprocess, "CREATE_NEW_CONSOLE"):
        raise RuntimeError("direct_visible_cli_unavailable")
    timeout_seconds = int(run_kwargs.pop("timeout"))
    raw_idle_timeout = run_kwargs.pop("idle_timeout", None)
    raw_provider_output_idle_timeout = run_kwargs.pop("provider_output_idle_timeout", None)
    raw_material_progress_idle_timeout = run_kwargs.pop("material_progress_idle_timeout", None)
    on_output = run_kwargs.pop("on_output", None)
    provider_name = str(run_kwargs.pop("provider_name", "provider"))
    visible_session_dir = Path(
        str(run_kwargs.pop("visible_session_dir", "") or Path.cwd() / "state" / "provider_visible_cli_sessions" / f"session_{uuid4().hex[:12]}")
    )
    visible_session_metadata = run_kwargs.pop("visible_session_metadata", None)
    stdin_value = run_kwargs.pop("input", None)
    run_kwargs.pop("capture_output", None)
    text = bool(run_kwargs.pop("text", False))
    run_kwargs.pop("check", None)
    run_kwargs.pop("encoding", None)
    run_kwargs.pop("errors", None)
    run_kwargs.pop("universal_newlines", None)
    cwd = Path(str(run_kwargs.pop("cwd", None) or Path.cwd())).resolve()
    env = run_kwargs.pop("env", None)
    idle_timeout_seconds = float(raw_idle_timeout) if raw_idle_timeout is not None else None
    provider_output_idle_timeout_seconds = (
        float(raw_provider_output_idle_timeout) if raw_provider_output_idle_timeout is not None else None
    )
    material_progress_idle_timeout_seconds = (
        float(raw_material_progress_idle_timeout) if raw_material_progress_idle_timeout is not None else None
    )
    if text and isinstance(stdin_value, bytes):
        stdin_text = decode_subprocess_stream(stdin_value)
    elif stdin_value is None:
        stdin_text = None
    else:
        stdin_text = str(stdin_value)

    visible_session_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = visible_session_dir / "stdout.log"
    stderr_path = visible_session_dir / "stderr.log"
    stream_path = visible_session_dir / "stream.jsonl"
    session_path = visible_session_dir / "visible_cli_session.json"
    script_path = visible_session_dir / "run_provider_visible.py"
    stdin_path = visible_session_dir / "stdin.txt"
    pid_path = visible_session_dir / "provider_pid.json"
    exit_path = visible_session_dir / "exit_code.json"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    stream_path.write_text("", encoding="utf-8")
    if stdin_text is not None:
        stdin_path.write_text(stdin_text, encoding="utf-8", newline="\n")

    metadata = dict(visible_session_metadata or {})
    started_wall_at = datetime.now(UTC)
    session: dict[str, Any] = {
        "schema_version": "direct_provider_visible_cli_session_v1",
        "mode": "direct_provider_visible_cli_enforced",
        "status": "starting",
        "provider": provider_name,
        "wrapper_pid": None,
        "provider_pid": None,
        "window_title": metadata.get("window_title") or f"{provider_name} direct visible CLI",
        "argv": command,
        "cwd": cwd.as_posix(),
        "stdout_log_path": stdout_path.as_posix(),
        "stderr_log_path": stderr_path.as_posix(),
        "stream_log_path": stream_path.as_posix(),
        "session_path": session_path.as_posix(),
        "script_path": script_path.as_posix(),
        "stdin_path": stdin_path.as_posix() if stdin_text is not None else None,
        "started_at": started_wall_at.isoformat(),
        "ended_at": None,
        **metadata,
    }
    _write_json_file(session_path, session)
    _append_jsonl(stream_path, {"event": "direct_provider_visible_cli_starting", "created_at": started_wall_at.isoformat(), "argv": command})
    script_path.write_text(
        _direct_visible_provider_python_script(
            command=command,
            cwd=cwd,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stream_path=stream_path,
            pid_path=pid_path,
            exit_path=exit_path,
            stdin_path=stdin_path if stdin_text is not None else None,
        ),
        encoding="utf-8",
    )
    launch_cmd = [
        sys.executable,
        str(script_path),
    ]
    wrapper = subprocess.Popen(
        launch_cmd,
        cwd=str(cwd),
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    session.update({"status": "running", "wrapper_pid": wrapper.pid})
    _write_json_file(session_path, session)
    _append_jsonl(
        stream_path,
        {"event": "direct_provider_visible_cli_started", "created_at": datetime.now(UTC).isoformat(), "wrapper_pid": wrapper.pid},
    )

    started = time.monotonic()
    last_output_at = started
    last_provider_output_at = started
    last_material_progress_at = started
    last_stdout_pos = 0
    last_stderr_pos = 0
    stdout_event_count = 0
    stderr_event_count = 0
    material_progress_event_count = 0
    timeout_type: str | None = None

    def _consume_new(path: Path, start: int, stream_name: str) -> tuple[int, int, int]:
        if not path.exists():
            return start, 0, 0
        data = path.read_bytes()
        if len(data) <= start:
            return start, 0, 0
        chunk = data[start:]
        text_chunk = decode_subprocess_stream(chunk)
        event_count = 0
        material_count = 0
        for line in text_chunk.splitlines():
            if not line.strip():
                continue
            event_count += 1
            is_material = _is_material_progress_output(line.encode("utf-8", errors="replace"))
            if is_material:
                material_count += 1
            if callable(on_output):
                try:
                    on_output(
                        {
                            "stream": stream_name,
                            "text": line + "\n",
                            "byte_count": len(line.encode("utf-8", errors="replace")),
                            "observed_at": datetime.now(UTC).isoformat(),
                            "is_control": False,
                            "is_material_progress": is_material,
                        }
                    )
                except Exception:
                    pass
        return len(data), event_count, material_count

    while wrapper.poll() is None:
        now = time.monotonic()
        last_stdout_pos, new_stdout_events, new_stdout_material = _consume_new(stdout_path, last_stdout_pos, "stdout")
        last_stderr_pos, new_stderr_events, new_stderr_material = _consume_new(stderr_path, last_stderr_pos, "stderr")
        new_events = new_stdout_events + new_stderr_events
        if new_events:
            stdout_event_count += new_stdout_events
            stderr_event_count += new_stderr_events
            material_progress_event_count += new_stdout_material + new_stderr_material
            last_output_at = now
            last_provider_output_at = now
            if new_stdout_material or new_stderr_material:
                last_material_progress_at = now
        if session.get("provider_pid") is None and pid_path.exists():
            pid_payload = _read_json_file(pid_path)
            provider_pid = pid_payload.get("provider_pid") if isinstance(pid_payload, dict) else None
            if provider_pid:
                session["provider_pid"] = provider_pid
                _write_json_file(session_path, session)
        if provider_output_idle_timeout_seconds is not None and now - last_provider_output_at > provider_output_idle_timeout_seconds:
            timeout_type = "provider_output_idle_timeout"
            break
        if (
            material_progress_idle_timeout_seconds is not None
            and now - last_material_progress_at > material_progress_idle_timeout_seconds
            and now - last_provider_output_at > material_progress_idle_timeout_seconds
        ):
            timeout_type = "provider_no_material_progress_timeout"
            break
        if idle_timeout_seconds is not None and now - last_output_at > idle_timeout_seconds:
            timeout_type = "idle_timeout"
            break
        if now - started > timeout_seconds:
            timeout_type = "wall_timeout"
            break
        time.sleep(1.0)
    if timeout_type:
        terminate_process_tree(wrapper.pid)
    return_code = wrapper.wait()
    last_stdout_pos, new_stdout_events, new_stdout_material = _consume_new(stdout_path, last_stdout_pos, "stdout")
    last_stderr_pos, new_stderr_events, new_stderr_material = _consume_new(stderr_path, last_stderr_pos, "stderr")
    stdout_event_count += new_stdout_events
    stderr_event_count += new_stderr_events
    material_progress_event_count += new_stdout_material + new_stderr_material
    ended = datetime.now(UTC)
    if timeout_type:
        return_code = TIMEOUT_EXIT_CODE
    exit_payload = _read_json_file(exit_path)
    if not timeout_type and isinstance(exit_payload.get("exit_code"), int):
        return_code = int(exit_payload["exit_code"])
    session.update(
        {
            "status": "timeout" if timeout_type else "completed",
            "return_code": return_code,
            "ended_at": ended.isoformat(),
            "timeout_type": timeout_type,
        }
    )
    if session.get("provider_pid") is None and pid_path.exists():
        pid_payload = _read_json_file(pid_path)
        if isinstance(pid_payload.get("provider_pid"), int):
            session["provider_pid"] = pid_payload["provider_pid"]
    _write_json_file(session_path, session)
    _append_jsonl(
        stream_path,
        {
            "event": "direct_provider_visible_cli_completed",
            "created_at": ended.isoformat(),
            "return_code": return_code,
            "timeout_type": timeout_type,
        },
    )
    completed = subprocess.CompletedProcess(
        command,
        return_code,
        stdout=decode_subprocess_stream(stdout_path.read_bytes() if stdout_path.exists() else b""),
        stderr=decode_subprocess_stream(stderr_path.read_bytes() if stderr_path.exists() else b""),
    )
    _attach_watchdog_metadata(
        completed,
        timeout_type=timeout_type,
        stdout_event_count=stdout_event_count,
        stderr_event_count=stderr_event_count,
        last_output_age_seconds=max(0.0, time.monotonic() - last_output_at),
        provider_output_event_count=stdout_event_count + stderr_event_count,
        control_output_event_count=0,
        material_progress_event_count=material_progress_event_count,
        last_provider_output_age_seconds=max(0.0, time.monotonic() - last_provider_output_at),
        last_material_progress_age_seconds=max(0.0, time.monotonic() - last_material_progress_at),
    )
    setattr(completed, "direct_visible_cli_session", session)
    setattr(
        completed,
        "direct_visible_cli_log_paths",
        {
            "stdout_log_path": stdout_path.as_posix(),
            "stderr_log_path": stderr_path.as_posix(),
            "stream_log_path": stream_path.as_posix(),
            "session_path": session_path.as_posix(),
            "script_path": script_path.as_posix(),
        },
    )
    return completed


def _direct_visible_provider_python_script(
    *,
    command: list[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    stream_path: Path,
    pid_path: Path,
    exit_path: Path,
    stdin_path: Path | None,
) -> str:
    command_json = json.dumps([str(item) for item in command], ensure_ascii=False)
    stdin_literal = "None" if stdin_path is None else repr(stdin_path.as_posix())
    return f"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

COMMAND = json.loads({command_json!r})
CWD = {cwd.as_posix()!r}
STDOUT_PATH = Path({stdout_path.as_posix()!r})
STDERR_PATH = Path({stderr_path.as_posix()!r})
STREAM_PATH = Path({stream_path.as_posix()!r})
PID_PATH = Path({pid_path.as_posix()!r})
EXIT_PATH = Path({exit_path.as_posix()!r})
STDIN_PATH = {stdin_literal}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(payload: dict) -> None:
    with STREAM_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\\n")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def resolve_executable(executable: str) -> str:
    if os.path.isabs(executable) or "/" in executable or "\\\\" in executable:
        return executable
    resolved = shutil.which(executable)
    if not resolved:
        raise FileNotFoundError(f"provider executable not found on PATH: {{executable}}")
    return resolved


def set_console_title() -> None:
    if os.name != "nt":
        return
    title = "direct provider visible CLI"
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        return


def pump_stream(pipe, log_path: Path, stream_name: str, console_stream) -> None:
    try:
        for line in iter(pipe.readline, ""):
            if line == "":
                break
            console_stream.write(line)
            console_stream.flush()
            text = line.rstrip("\\r\\n")
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(text + "\\n")
            append_jsonl({{"event": f"provider_{{stream_name}}", "created_at": now(), "text": text}})
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def fail(message: str) -> int:
    sys.stderr.write(message + "\\n")
    sys.stderr.flush()
    with STDERR_PATH.open("a", encoding="utf-8") as handle:
        handle.write(message + "\\n")
    append_jsonl({{"event": "provider_wrapper_exception", "created_at": now(), "text": message}})
    write_json(EXIT_PATH, {{"exit_code": 1, "ended_at": now(), "wrapper_exception": message}})
    return 1


def main() -> int:
    set_console_title()
    try:
        argv = [str(item) for item in COMMAND]
        argv[0] = resolve_executable(argv[0])
        stdin_text = None
        if STDIN_PATH is not None:
            stdin_text = Path(STDIN_PATH).read_text(encoding="utf-8")
        proc = subprocess.Popen(
            argv,
            cwd=CWD,
            stdin=subprocess.PIPE if stdin_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        write_json(PID_PATH, {{"provider_pid": proc.pid, "started_at": now()}})
        threads = [
            threading.Thread(target=pump_stream, args=(proc.stdout, STDOUT_PATH, "stdout", sys.stdout), daemon=True),
            threading.Thread(target=pump_stream, args=(proc.stderr, STDERR_PATH, "stderr", sys.stderr), daemon=True),
        ]
        for thread in threads:
            thread.start()
        if stdin_text is not None and proc.stdin is not None:
            try:
                proc.stdin.write(stdin_text)
                proc.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                append_jsonl({{"event": "provider_stdin_closed_early", "created_at": now(), "text": str(exc)}})
            finally:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
        return_code = proc.wait()
        for thread in threads:
            thread.join(timeout=5)
        write_json(EXIT_PATH, {{"exit_code": int(return_code), "ended_at": now()}})
        return 0 if return_code == 0 else 1
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
""".lstrip()


def _direct_visible_provider_powershell_script(
    *,
    command: list[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    stream_path: Path,
    pid_path: Path,
    exit_path: Path,
    stdin_path: Path | None,
) -> str:
    command_json = json.dumps([str(item) for item in command], ensure_ascii=False)
    stdin_literal = "$null" if stdin_path is None else _ps_quote(stdin_path.as_posix())
    return f"""
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
$argvJson = @'
{command_json}
'@
$stdoutPath = {_ps_quote(stdout_path.as_posix())}
$stderrPath = {_ps_quote(stderr_path.as_posix())}
$streamPath = {_ps_quote(stream_path.as_posix())}
$pidPath = {_ps_quote(pid_path.as_posix())}
$exitPath = {_ps_quote(exit_path.as_posix())}
$stdinPath = {stdin_literal}
try {{
$parsedProviderArgv = ConvertFrom-Json -InputObject $argvJson
if ($parsedProviderArgv -is [System.Array]) {{
  $providerArgv = [object[]]$parsedProviderArgv
}} else {{
  $providerArgv = @($parsedProviderArgv)
}}
function ConvertTo-ProcessArgument {{
  param([AllowNull()][string]$Arg)
  if ($null -eq $Arg) {{
    return '""'
  }}
  if ($Arg.Length -eq 0) {{
    return '""'
  }}
  if ($Arg -notmatch '[\\s"]') {{
    return $Arg
  }}
  $builder = [System.Text.StringBuilder]::new()
  [void]$builder.Append('"')
  $backslashes = 0
  foreach ($ch in $Arg.ToCharArray()) {{
    if ($ch -eq '\\') {{
      $backslashes += 1
      continue
    }}
    if ($ch -eq '"') {{
      if ($backslashes -gt 0) {{
        [void]$builder.Append(('\\' * ($backslashes * 2)))
        $backslashes = 0
      }}
      [void]$builder.Append('\\"')
      continue
    }}
    if ($backslashes -gt 0) {{
      [void]$builder.Append(('\\' * $backslashes))
      $backslashes = 0
    }}
    [void]$builder.Append($ch)
  }}
  if ($backslashes -gt 0) {{
    [void]$builder.Append(('\\' * ($backslashes * 2)))
  }}
  [void]$builder.Append('"')
  return $builder.ToString()
}}
function Resolve-ProviderExecutable {{
  param([string]$Executable)
  if ([System.IO.Path]::IsPathRooted($Executable) -or $Executable.Contains('\\') -or $Executable.Contains('/')) {{
    return $Executable
  }}
  $commandInfo = Get-Command -CommandType Application -Name $Executable -ErrorAction Stop
  return [string]$commandInfo.Source
}}
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = Resolve-ProviderExecutable ([string]$providerArgv[0])
$argumentParts = @()
for ($i = 1; $i -lt $providerArgv.Count; $i++) {{
  $argumentParts += ConvertTo-ProcessArgument ([string]$providerArgv[$i])
}}
$psi.Arguments = ($argumentParts -join ' ')
$psi.WorkingDirectory = {_ps_quote(cwd.as_posix())}
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.RedirectStandardInput = $true
$proc = [System.Diagnostics.Process]::new()
$proc.StartInfo = $psi
$outHandler = {{
  param($sender, $eventArgs)
  if ($null -ne $eventArgs.Data) {{
    $line = [string]$eventArgs.Data
    Write-Host $line
    Add-Content -LiteralPath $stdoutPath -Value $line -Encoding UTF8
    (@{{ event = "provider_stdout"; created_at = [DateTime]::UtcNow.ToString("o"); text = $line }} | ConvertTo-Json -Compress) | Add-Content -LiteralPath $streamPath -Encoding UTF8
  }}
}}
$errHandler = {{
  param($sender, $eventArgs)
  if ($null -ne $eventArgs.Data) {{
    $line = [string]$eventArgs.Data
    Write-Host $line -ForegroundColor Red
    Add-Content -LiteralPath $stderrPath -Value $line -Encoding UTF8
    (@{{ event = "provider_stderr"; created_at = [DateTime]::UtcNow.ToString("o"); text = $line }} | ConvertTo-Json -Compress) | Add-Content -LiteralPath $streamPath -Encoding UTF8
  }}
}}
$proc.add_OutputDataReceived($outHandler)
$proc.add_ErrorDataReceived($errHandler)
[void]$proc.Start()
(@{{ provider_pid = $proc.Id; started_at = [DateTime]::UtcNow.ToString("o") }} | ConvertTo-Json -Compress) | Set-Content -LiteralPath $pidPath -Encoding UTF8
$proc.BeginOutputReadLine()
$proc.BeginErrorReadLine()
if ($null -ne $stdinPath) {{
  $inputText = Get-Content -LiteralPath $stdinPath -Raw -Encoding UTF8
  $proc.StandardInput.Write($inputText)
}}
$proc.StandardInput.Close()
$proc.WaitForExit()
$proc.WaitForExit()
(@{{ exit_code = $proc.ExitCode; ended_at = [DateTime]::UtcNow.ToString("o") }} | ConvertTo-Json -Compress) | Set-Content -LiteralPath $exitPath -Encoding UTF8
exit $proc.ExitCode
}} catch {{
  $message = $_ | Out-String
  Write-Host $message -ForegroundColor Red
  Add-Content -LiteralPath $stderrPath -Value $message -Encoding UTF8
  (@{{ event = "provider_wrapper_exception"; created_at = [DateTime]::UtcNow.ToString("o"); text = $message }} | ConvertTo-Json -Compress) | Add-Content -LiteralPath $streamPath -Encoding UTF8
  (@{{ exit_code = 1; ended_at = [DateTime]::UtcNow.ToString("o"); wrapper_exception = $message }} | ConvertTo-Json -Compress) | Set-Content -LiteralPath $exitPath -Encoding UTF8
  exit 1
}}
""".lstrip()


def _ps_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def run_subprocess_with_tree_timeout(command: list[str], **run_kwargs: Any) -> subprocess.CompletedProcess[str]:
    timeout_seconds = int(run_kwargs.pop("timeout"))
    raw_idle_timeout = run_kwargs.pop("idle_timeout", None)
    raw_provider_output_idle_timeout = run_kwargs.pop("provider_output_idle_timeout", None)
    raw_material_progress_idle_timeout = run_kwargs.pop("material_progress_idle_timeout", None)
    raw_adaptive_wall_extension = run_kwargs.pop("adaptive_wall_timeout_extension", None)
    raw_adaptive_wall_max_extensions = run_kwargs.pop("adaptive_wall_timeout_max_extensions", 0)
    raw_adaptive_wall_absolute_max = run_kwargs.pop("adaptive_wall_timeout_absolute_max", None)
    raw_adaptive_wall_progress_window = run_kwargs.pop("adaptive_wall_timeout_progress_window", None)
    adaptive_wall_requires_material_progress = bool(
        run_kwargs.pop("adaptive_wall_timeout_requires_material_progress", True)
    )
    on_output = run_kwargs.pop("on_output", None)
    activity_probe = run_kwargs.pop("activity_probe", None)
    raw_activity_probe_interval = run_kwargs.pop("activity_probe_interval", 1.0)
    idle_timeout_seconds = float(raw_idle_timeout) if raw_idle_timeout is not None else None
    provider_output_idle_timeout_seconds = (
        float(raw_provider_output_idle_timeout) if raw_provider_output_idle_timeout is not None else None
    )
    material_progress_idle_timeout_seconds = (
        float(raw_material_progress_idle_timeout) if raw_material_progress_idle_timeout is not None else None
    )
    adaptive_wall_extension_seconds = (
        float(raw_adaptive_wall_extension) if raw_adaptive_wall_extension is not None else 0.0
    )
    adaptive_wall_max_extensions = max(int(raw_adaptive_wall_max_extensions or 0), 0)
    adaptive_wall_absolute_max_seconds = (
        float(raw_adaptive_wall_absolute_max) if raw_adaptive_wall_absolute_max is not None else float(timeout_seconds)
    )
    adaptive_wall_progress_window_seconds = (
        float(raw_adaptive_wall_progress_window)
        if raw_adaptive_wall_progress_window is not None
        else material_progress_idle_timeout_seconds
        or provider_output_idle_timeout_seconds
        or float(timeout_seconds)
    )
    adaptive_wall_absolute_max_seconds = max(float(timeout_seconds), adaptive_wall_absolute_max_seconds)
    activity_probe_interval_seconds = max(float(raw_activity_probe_interval or 1.0), 0.1)
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
    started_wall_at = datetime.now(UTC)
    last_output_at = started_at
    last_provider_output_at = started_at
    last_material_progress_at = started_at
    last_provider_output_wall_at = started_wall_at
    last_material_progress_wall_at = started_wall_at
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    stdout_event_count = 0
    stderr_event_count = 0
    provider_output_event_count = 0
    control_output_event_count = 0
    material_progress_event_count = 0
    stream_lock = threading.Lock()
    last_activity_probe_at = 0.0
    adaptive_wall_extension_count = 0
    effective_wall_timeout_seconds = float(timeout_seconds)

    def _coerce_wall_time(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, str) and value.strip():
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                return datetime.now(UTC)
        return datetime.now(UTC)

    def _emit_output_callback(data: bytes, stream_name: str, *, is_control: bool, is_material_progress: bool) -> None:
        if not callable(on_output):
            return
        payload = {
            "stream": stream_name,
            "text": decode_subprocess_stream(data),
            "byte_count": len(data),
            "observed_at": datetime.now(UTC).isoformat(),
            "is_control": is_control,
            "is_material_progress": is_material_progress,
        }
        try:
            on_output(payload)
        except Exception:
            return

    def _apply_activity_probe(now: float) -> None:
        nonlocal last_activity_probe_at
        nonlocal last_material_progress_at, last_material_progress_wall_at
        nonlocal last_provider_output_at, last_provider_output_wall_at
        nonlocal material_progress_event_count, provider_output_event_count
        if not callable(activity_probe) or now - last_activity_probe_at < activity_probe_interval_seconds:
            return
        last_activity_probe_at = now
        try:
            payload = activity_probe()
        except Exception:
            return
        if not isinstance(payload, Mapping):
            return
        provider_count = payload.get("provider_output_event_count")
        if isinstance(provider_count, (int, float)) and int(provider_count) > provider_output_event_count:
            provider_output_event_count = int(provider_count)
            last_provider_output_at = now
            last_provider_output_wall_at = _coerce_wall_time(payload.get("last_provider_output_at"))
        material_count = payload.get("material_progress_event_count")
        if isinstance(material_count, (int, float)) and int(material_count) > material_progress_event_count:
            material_progress_event_count = int(material_count)
            last_material_progress_at = now
            last_material_progress_wall_at = _coerce_wall_time(payload.get("last_material_progress_at"))

    def _can_extend_wall_timeout(now: float) -> bool:
        if adaptive_wall_extension_seconds <= 0 or adaptive_wall_max_extensions <= 0:
            return False
        if adaptive_wall_extension_count >= adaptive_wall_max_extensions:
            return False
        if effective_wall_timeout_seconds >= adaptive_wall_absolute_max_seconds:
            return False
        provider_recent = provider_output_event_count > 0 and (
            provider_output_idle_timeout_seconds is None
            or provider_output_idle_timeout_seconds <= 0
            or now - last_provider_output_at < provider_output_idle_timeout_seconds
        )
        material_recent = material_progress_event_count > 0 and (
            adaptive_wall_progress_window_seconds <= 0
            or now - last_material_progress_at <= adaptive_wall_progress_window_seconds
        )
        return provider_recent and (material_recent or not adaptive_wall_requires_material_progress)

    def _record_output(target: list[bytes], data: bytes, stream_name: str) -> None:
        nonlocal control_output_event_count
        nonlocal last_material_progress_at, last_material_progress_wall_at, last_output_at
        nonlocal last_provider_output_at, last_provider_output_wall_at
        nonlocal material_progress_event_count, provider_output_event_count, stderr_event_count, stdout_event_count
        if not data:
            return
        is_control = _is_control_output(data)
        is_material_progress = (not is_control) and _is_material_progress_output(data)
        with stream_lock:
            target.append(data)
            last_output_at = time.monotonic()
            if stream_name == "stdout":
                stdout_event_count += 1
            else:
                stderr_event_count += 1
            if is_control:
                control_output_event_count += 1
            else:
                provider_output_event_count += 1
                last_provider_output_at = last_output_at
                last_provider_output_wall_at = datetime.now(UTC)
            if is_material_progress:
                material_progress_event_count += 1
                last_material_progress_at = last_output_at
                last_material_progress_wall_at = datetime.now(UTC)
        _emit_output_callback(
            data,
            stream_name,
            is_control=is_control,
            is_material_progress=is_material_progress,
        )

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
            _apply_activity_probe(now)
            if now - started_at >= effective_wall_timeout_seconds:
                if _can_extend_wall_timeout(now):
                    adaptive_wall_extension_count += 1
                    effective_wall_timeout_seconds = min(
                        effective_wall_timeout_seconds + adaptive_wall_extension_seconds,
                        adaptive_wall_absolute_max_seconds,
                    )
                    continue
                timeout_type = "adaptive_wall_timeout_exhausted" if adaptive_wall_extension_count > 0 else "wall_timeout"
                break
            if (
                provider_output_idle_timeout_seconds is not None
                and provider_output_idle_timeout_seconds > 0
                and now - last_provider_output_at >= provider_output_idle_timeout_seconds
            ):
                timeout_type = "provider_output_idle_timeout"
                break
            if (
                material_progress_idle_timeout_seconds is not None
                and material_progress_idle_timeout_seconds > 0
                and now - last_material_progress_at >= material_progress_idle_timeout_seconds
            ):
                timeout_type = "provider_no_material_progress_timeout"
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
    final_now = time.monotonic()
    last_output_age_seconds = max(final_now - last_output_at, 0.0)
    last_provider_output_age_seconds = max(final_now - last_provider_output_at, 0.0)
    last_material_progress_age_seconds = max(final_now - last_material_progress_at, 0.0)
    if timeout_type is not None:
        completed = subprocess.CompletedProcess(
            command,
            TIMEOUT_EXIT_CODE,
            stdout=decode_subprocess_stream(stdout),
            stderr=decode_subprocess_stream(stderr),
        )
        timeout_budget = _timeout_budget_seconds(
            timeout_type=timeout_type,
            timeout_seconds=timeout_seconds,
            effective_wall_timeout_seconds=int(effective_wall_timeout_seconds),
            idle_timeout_seconds=idle_timeout_seconds,
            provider_output_idle_timeout_seconds=provider_output_idle_timeout_seconds,
            material_progress_idle_timeout_seconds=material_progress_idle_timeout_seconds,
        )
        timeout_message = f"command timed out after {timeout_budget}s ({timeout_type})"
        completed.stderr = f"{completed.stderr.rstrip()}\n{timeout_message}".strip() if completed.stderr else timeout_message
        _attach_watchdog_metadata(
            completed,
            timeout_type=timeout_type,
            stdout_event_count=stdout_event_count,
            stderr_event_count=stderr_event_count,
            last_output_age_seconds=last_output_age_seconds,
            provider_output_event_count=provider_output_event_count,
            control_output_event_count=control_output_event_count,
            material_progress_event_count=material_progress_event_count,
            last_provider_output_age_seconds=last_provider_output_age_seconds,
            last_material_progress_age_seconds=last_material_progress_age_seconds,
            last_provider_output_at=last_provider_output_wall_at.isoformat(),
            last_material_progress_at=last_material_progress_wall_at.isoformat(),
            adaptive_wall_timeout_extension_count=adaptive_wall_extension_count,
            adaptive_wall_timeout_effective_seconds=int(effective_wall_timeout_seconds),
            adaptive_wall_timeout_absolute_max_seconds=int(adaptive_wall_absolute_max_seconds),
            adaptive_wall_timeout_exhausted=timeout_type == "adaptive_wall_timeout_exhausted",
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
        provider_output_event_count=provider_output_event_count,
        control_output_event_count=control_output_event_count,
        material_progress_event_count=material_progress_event_count,
        last_provider_output_age_seconds=last_provider_output_age_seconds,
        last_material_progress_age_seconds=last_material_progress_age_seconds,
        last_provider_output_at=last_provider_output_wall_at.isoformat(),
        last_material_progress_at=last_material_progress_wall_at.isoformat(),
        adaptive_wall_timeout_extension_count=adaptive_wall_extension_count,
        adaptive_wall_timeout_effective_seconds=int(effective_wall_timeout_seconds),
        adaptive_wall_timeout_absolute_max_seconds=int(adaptive_wall_absolute_max_seconds),
        adaptive_wall_timeout_exhausted=False,
    )
    if check and completed.returncode:
        completed.check_returncode()
    return completed


def _is_control_output(data: bytes) -> bool:
    text = decode_subprocess_stream(data).strip()
    return any(text == prefix or text.startswith(f"{prefix} ") for prefix in CONTROL_OUTPUT_PREFIXES)


def _is_material_progress_output(data: bytes) -> bool:
    text = decode_subprocess_stream(data)
    return any(token in text for token in MATERIAL_PROGRESS_TOKENS)


def _timeout_budget_seconds(
    *,
    timeout_type: str,
    timeout_seconds: int,
    effective_wall_timeout_seconds: int,
    idle_timeout_seconds: float | None,
    provider_output_idle_timeout_seconds: float | None,
    material_progress_idle_timeout_seconds: float | None,
) -> int:
    if timeout_type == "idle_timeout" and idle_timeout_seconds:
        return int(idle_timeout_seconds)
    if timeout_type == "provider_output_idle_timeout" and provider_output_idle_timeout_seconds:
        return int(provider_output_idle_timeout_seconds)
    if timeout_type == "provider_no_material_progress_timeout" and material_progress_idle_timeout_seconds:
        return int(material_progress_idle_timeout_seconds)
    if timeout_type == "adaptive_wall_timeout_exhausted":
        return int(effective_wall_timeout_seconds)
    return timeout_seconds
