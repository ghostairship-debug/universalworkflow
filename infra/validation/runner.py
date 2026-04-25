from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from infra.validation.api_flow import validate_api_flow
from infra.validation.cli_flow import validate_cli_flow, validate_cli_quick_flow
from infra.validation.cluster_flow import validate_cluster_flow
from infra.validation.common import DEFAULT_REPORT_PATH, PROJECT_ROOT, sanitized_env, tcp_probe, utc_now_iso
from infra.validation.smoke_flow import validate_smoke_flow


@dataclass(frozen=True)
class FlowSpec:
    key: str
    fn: Callable[..., dict[str, Any]]
    args: tuple[Any, ...]
    trace_path: Path


def _run_flow_child(fn: Callable[..., dict[str, Any]], fn_args: tuple[Any, ...], output_path: str) -> None:
    try:
        payload = fn(*fn_args)
        if not isinstance(payload, dict):
            payload = {"passed": False, "error": "flow did not return a dict"}
        output = {"ok": True, "payload": payload}
    except Exception as exc:  # noqa: BLE001
        output = {"ok": False, "error": str(exc)}
    resolved = Path(output_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")


def _terminate_process(process: mp.Process) -> None:
    process.terminate()
    process.join(timeout=5)
    if process.is_alive() and hasattr(process, "kill"):
        process.kill()
        process.join(timeout=5)


def _with_elapsed(
    key: str,
    fn: Callable[..., dict[str, Any]],
    fn_args: tuple[Any, ...],
    *,
    timeout_seconds: float | None = None,
    trace_path: Path | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    result_path = _flow_result_path(key, trace_path)
    if timeout_seconds is not None and timeout_seconds > 0:
        context = mp.get_context("spawn")
        process = context.Process(
            target=_run_flow_child,
            args=(fn, fn_args, result_path.as_posix()),
            name=f"offline-validation-{key}",
        )
        try:
            process.start()
        except Exception as exc:  # noqa: BLE001
            payload = {"passed": False, "error": f"{key} could not start validation subprocess: {exc}"}
        else:
            process.join(timeout=timeout_seconds)
            if process.is_alive():
                _terminate_process(process)
                payload = {
                    "passed": False,
                    "timed_out": True,
                    "error": f"{key} timed out after {timeout_seconds}s",
                }
            else:
                child_payload = _read_flow_result(result_path)
                if child_payload is None:
                    payload = {
                        "passed": False,
                        "error": f"{key} validation subprocess exited without a report",
                        "return_code": process.exitcode,
                    }
                else:
                    payload = child_payload["payload"] if child_payload.get("ok") else {"passed": False, "error": child_payload.get("error")}
    else:
        try:
            payload = fn(*fn_args)
            if not isinstance(payload, dict):
                payload = {"passed": False, "error": f"{key} did not return a dict"}
        except Exception as exc:  # noqa: BLE001
            payload = {"passed": False, "error": str(exc)}
    payload["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    if trace_path is not None:
        payload["trace_path"] = trace_path.as_posix()
        payload["last_command"] = _last_command_from_trace(trace_path)
    payload["flow_result_path"] = result_path.as_posix()
    return payload


def _flow_result_path(key: str, trace_path: Path | None) -> Path:
    if trace_path is not None:
        return trace_path.with_suffix(".result.json")
    return PROJECT_ROOT / "state" / "offline_validation_traces" / f"{key}.result.json"


def _read_flow_result(result_path: Path) -> dict[str, Any] | None:
    if not result_path.exists():
        return None
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "error": f"could not parse validation subprocess report: {result_path.as_posix()}"}


def _db_path_for(args: argparse.Namespace, flow_key: str) -> Path:
    if args.suite == "full" and args.shard is None:
        suffix = flow_key.replace("_flow", "")
        return PROJECT_ROOT / "state" / f"offline_validate_{suffix}.db"
    shard_label = (args.shard or "all").replace("/", "of")
    return PROJECT_ROOT / "state" / f"offline_validate_{args.suite}_{shard_label}_{flow_key}.db"


def _parse_shard(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    if "/" not in value:
        raise ValueError("--shard must use N/M form")
    raw_index, raw_total = value.split("/", 1)
    index = int(raw_index)
    total = int(raw_total)
    if index < 1 or total < 1 or index > total:
        raise ValueError("--shard must satisfy 1 <= N <= M")
    return index, total


def _apply_shard(flows: list[FlowSpec], shard: str | None) -> list[FlowSpec]:
    parsed = _parse_shard(shard)
    if parsed is None:
        return flows
    index, total = parsed
    return [flow for position, flow in enumerate(flows, start=1) if ((position - 1) % total) + 1 == index]


def _flow_specs(args: argparse.Namespace, env: dict[str, str]) -> list[FlowSpec]:
    def _spec(key: str, fn: Callable[..., dict[str, Any]], *fn_args: Any) -> FlowSpec:
        trace_path = _trace_path_for(args, key)
        flow_env = {**env, "WORKFLOW_OFFLINE_VALIDATION_TRACE": trace_path.as_posix()}
        return FlowSpec(key, fn, (flow_env, *fn_args), trace_path)

    cli_fn = validate_cli_quick_flow if args.suite == "quick" else validate_cli_flow
    return [
        _spec("cli_flow", cli_fn, _db_path_for(args, "cli_flow")),
        _spec("smoke_flow", validate_smoke_flow, _db_path_for(args, "smoke_flow")),
        _spec("api_flow", validate_api_flow, _db_path_for(args, "api_flow"), args.api_port),
        _spec("cluster_flow", validate_cluster_flow, _db_path_for(args, "cluster_flow")),
    ]


def _trace_path_for(args: argparse.Namespace, flow_key: str) -> Path:
    shard_label = (args.shard or "all").replace("/", "of")
    return PROJECT_ROOT / "state" / "offline_validation_traces" / f"{args.suite}_{shard_label}_{flow_key}.jsonl"


def _last_command_from_trace(trace_path: Path) -> dict[str, Any] | None:
    if not trace_path.exists():
        return None
    last_started: dict[str, Any] | None = None
    last_event: dict[str, Any] | None = None
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "command_started":
            last_started = event
        last_event = event
    if last_started is None:
        return None
    return {
        "command": last_started.get("command"),
        "started_at": last_started.get("started_at"),
        "last_event": last_event.get("event") if last_event else None,
        "last_returncode": last_event.get("returncode") if last_event else None,
    }


def _select_flows(args: argparse.Namespace, env: dict[str, str]) -> list[FlowSpec]:
    flows = _flow_specs(args, env)
    if args.suite == "quick":
        flows = [flow for flow in flows if flow.key in {"cli_flow", "smoke_flow"}]
    elif args.suite == "full":
        flows = flows
    else:
        raise ValueError(f"unsupported validation suite: {args.suite}")
    return _apply_shard(flows, args.shard)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    env, removed_env_keys = sanitized_env()
    report: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "project_root": PROJECT_ROOT.as_posix(),
        "python_executable": sys.executable,
        "suite": args.suite,
        "shard": args.shard,
        "flow_timeout_seconds": args.timeout_seconds,
        "removed_env_keys": removed_env_keys,
        "checks": {},
        "overall_passed": False,
    }

    checks: dict[str, Any] = {}
    if args.skip_offline_probe:
        checks["offline_probe"] = {
            "passed": None,
            "skipped": True,
            "results": [],
            "note": "offline probe skipped by flag",
        }
    else:
        probes = [
            tcp_probe("1.1.1.1", 443),
            tcp_probe("www.baidu.com", 443),
            tcp_probe("www.qq.com", 443),
        ]
        checks["offline_probe"] = {
            "passed": not any(item["reachable"] for item in probes),
            "skipped": False,
            "results": probes,
        }

    all_flow_keys = [flow.key for flow in _flow_specs(args, env)]
    selected_flows = _select_flows(args, env)
    selected_flow_keys = [flow.key for flow in selected_flows]
    for key in all_flow_keys:
        if key not in selected_flow_keys:
            checks[key] = {
                "passed": None,
                "skipped": True,
                "selected": False,
                "reason": f"not selected by suite={args.suite} shard={args.shard or 'all'}",
            }
    timeout_seconds = args.timeout_seconds if args.timeout_seconds and args.timeout_seconds > 0 else None
    for flow in selected_flows:
        checks[flow.key] = _with_elapsed(
            flow.key,
            flow.fn,
            flow.args,
            timeout_seconds=timeout_seconds,
            trace_path=flow.trace_path,
        )
        checks[flow.key]["selected"] = True

    report["checks"] = checks
    report["selected_flows"] = selected_flow_keys
    offline_probe_pass = checks["offline_probe"]["passed"]
    selected_passed = all(bool(checks[key].get("passed")) for key in selected_flow_keys)
    report["overall_passed"] = offline_probe_pass is not False and selected_passed
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline validation runner for the local-first workflow runtime.")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH), help="Where to write the JSON validation report.")
    parser.add_argument("--api-port", type=int, default=8011, help="Port used for the temporary API validation server.")
    parser.add_argument("--suite", choices=["quick", "full"], default="full", help="Validation suite to run.")
    parser.add_argument("--shard", help="Optional N/M shard selector over the selected validation flows.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=180.0,
        help="Per-flow timeout. Use 0 to disable subprocess timeout isolation.",
    )
    parser.add_argument(
        "--skip-offline-probe",
        action="store_true",
        help="Skip the outbound TCP probe. Useful only for a connected dry run.",
    )
    return parser.parse_args(argv)


def write_report(report: dict[str, Any], report_path: str | Path) -> Path:
    resolved = Path(report_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return resolved


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        report = build_report(args)
    except ValueError as exc:
        report = {
            "generated_at": utc_now_iso(),
            "project_root": PROJECT_ROOT.as_posix(),
            "python_executable": sys.executable,
            "suite": getattr(args, "suite", None),
            "shard": getattr(args, "shard", None),
            "checks": {},
            "overall_passed": False,
            "error": str(exc),
        }
    report_path = Path(args.report_path)
    write_report(report, report_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nValidation report written to: {report_path.as_posix()}")
