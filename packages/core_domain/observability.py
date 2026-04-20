from __future__ import annotations

import json
import os
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4

from packages.core_domain.config import build_effective_config
from packages.core_domain.m8_flags import is_external_trace_export_enabled


def trace_utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class TraceRecord:
    run_id: str
    name: str
    lane_type: str
    status: str
    attributes: dict[str, Any] = field(default_factory=dict)
    trace_id: str = field(default_factory=lambda: f"trace_{uuid4().hex[:16]}")
    created_at: str = field(default_factory=trace_utc_now)


class TraceExporter(ABC):
    @abstractmethod
    def describe(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def export(self, record: TraceRecord) -> str | None:
        raise NotImplementedError


class NullTraceExporter(TraceExporter):
    def describe(self) -> dict[str, Any]:
        return {"provider": "null", "enabled": False}

    def export(self, record: TraceRecord) -> str | None:
        return None


class InMemoryTraceExporter(TraceExporter):
    def __init__(self):
        self.records: list[TraceRecord] = []

    def describe(self) -> dict[str, Any]:
        return {"provider": "memory", "enabled": True, "record_count": len(self.records)}

    def export(self, record: TraceRecord) -> str | None:
        self.records.append(record)
        return record.trace_id


class LangfuseTraceExporter(TraceExporter):
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        public_key: str | None = None,
        sender: Callable[[str, dict[str, str], bytes], None] | None = None,
    ):
        self.endpoint = endpoint or os.getenv("LANGFUSE_OTEL_ENDPOINT") or os.getenv("LANGFUSE_ENDPOINT")
        self.api_key = api_key or os.getenv("LANGFUSE_API_KEY")
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self._sender = sender or self._send
        self.success_count = 0
        self.failure_count = 0
        self.last_trace_id: str | None = None
        self.last_error: str | None = None
        if not self.endpoint:
            raise ValueError("langfuse trace exporter requires LANGFUSE_OTEL_ENDPOINT or LANGFUSE_ENDPOINT")

    def describe(self) -> dict[str, Any]:
        return {
            "provider": "langfuse",
            "enabled": True,
            "endpoint": self.endpoint,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_trace_id": self.last_trace_id,
            "last_error": self.last_error,
        }

    def export(self, record: TraceRecord) -> str | None:
        redacted_attributes = {
            key: ("[redacted]" if any(token in key.lower() for token in ("api_key", "authorization", "secret")) else value)
            for key, value in record.attributes.items()
        }
        payload = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "uawo"}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "uawo-control-plane"},
                            "spans": [
                                {
                                    "traceId": record.trace_id,
                                    "spanId": record.trace_id[-16:],
                                    "name": record.name,
                                    "kind": 1,
                                    "startTimeUnixNano": "0",
                                    "endTimeUnixNano": "0",
                                    "attributes": [
                                        {"key": "uawo.run_id", "value": {"stringValue": record.run_id}},
                                        {"key": "uawo.lane_type", "value": {"stringValue": record.lane_type}},
                                        {"key": "uawo.status", "value": {"stringValue": record.status}},
                                        {
                                            "key": "uawo.attributes_json",
                                            "value": {"stringValue": json.dumps(redacted_attributes, ensure_ascii=False)},
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.public_key:
            headers["X-Langfuse-Public-Key"] = self.public_key
        try:
            self._sender(self.endpoint, headers, json.dumps(payload).encode("utf-8"))
        except Exception as exc:
            self.failure_count += 1
            self.last_error = str(exc)
            raise
        self.success_count += 1
        self.last_trace_id = record.trace_id
        self.last_error = None
        return record.trace_id

    def _send(self, url: str, headers: dict[str, str], body: bytes) -> None:
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()


def build_trace_exporter_from_env() -> TraceExporter:
    if not is_external_trace_export_enabled():
        return NullTraceExporter()
    effective = build_effective_config()
    provider = str(effective["trace_exporter"]["provider"]).strip().lower()
    if provider in {"", "null", "none"}:
        return NullTraceExporter()
    if provider == "langfuse":
        return LangfuseTraceExporter(
            endpoint=effective["trace_exporter"]["langfuse_endpoint"],
            api_key=os.getenv("LANGFUSE_API_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        )
    return NullTraceExporter()
