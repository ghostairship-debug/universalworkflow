from __future__ import annotations

import json
from typing import Any, Iterable

def _load_json_object(raw_text: str) -> dict[str, Any]:
    try:
        loaded = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start < 0 or end <= start:
            raise
        loaded = json.loads(raw_text[start : end + 1])
    if not isinstance(loaded, dict):
        raise ValueError("chat action response must be a JSON object")
    return loaded


def _iter_response_text_deltas(response_stream: Any) -> Iterable[str]:
    for event in response_stream:
        event_type = str(getattr(event, "type", ""))
        delta = getattr(event, "delta", None)
        if delta is None and hasattr(event, "model_dump"):
            data = event.model_dump(mode="json")
            event_type = str(data.get("type", event_type))
            delta = data.get("delta")
        if event_type == "response.output_text.delta" and delta:
            yield str(delta)


def _extract_chat_completion_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if content:
            return str(content)
    if hasattr(response, "model_dump"):
        data = response.model_dump(mode="json")
        for choice in data.get("choices", []):
            message = choice.get("message", {})
            content = message.get("content")
            if content:
                return str(content)
    if isinstance(response, dict):
        for choice in response.get("choices", []):
            message = choice.get("message", {})
            content = message.get("content")
            if content:
                return str(content)
    return ""


def _iter_chat_completion_deltas(response_stream: Any) -> Iterable[str]:
    for event in response_stream:
        choices = getattr(event, "choices", None) or []
        yielded_from_attributes = False
        for choice in choices:
            delta = getattr(choice, "delta", None)
            content = getattr(delta, "content", None)
            if content:
                yielded_from_attributes = True
                yield str(content)
        if yielded_from_attributes:
            continue
        if hasattr(event, "model_dump"):
            data = event.model_dump(mode="json")
            for choice in data.get("choices", []):
                content = choice.get("delta", {}).get("content")
                if content:
                    yield str(content)
        elif isinstance(event, dict):
            for choice in event.get("choices", []):
                content = choice.get("delta", {}).get("content")
                if content:
                    yield str(content)


def _coalesce_text_deltas(deltas: Iterable[str], *, min_chars: int = 18) -> Iterable[str]:
    buffer = ""
    for delta in deltas:
        buffer += delta
        if len(buffer) >= min_chars or buffer.endswith(("\n", "。", "！", "？", ".", "!", "?")):
            yield buffer
            buffer = ""
    if buffer:
        yield buffer

def _extract_response_text(response: Any) -> str:
    helper_text = getattr(response, "output_text", None)
    if helper_text:
        return str(helper_text)
    output = getattr(response, "output", None) or []
    parts: list[str] = []
    for item in output:
        content = getattr(item, "content", None) or []
        for part in content:
            if getattr(part, "type", None) == "output_text":
                text = getattr(part, "text", None)
                if text:
                    parts.append(str(text))
    if parts:
        return "\n".join(parts)
    if hasattr(response, "model_dump"):
        data = response.model_dump(mode="json")
        return str(data.get("output_text", ""))
    return ""
