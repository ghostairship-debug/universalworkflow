from __future__ import annotations

import os
import signal
import subprocess
import locale
import threading
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any


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
