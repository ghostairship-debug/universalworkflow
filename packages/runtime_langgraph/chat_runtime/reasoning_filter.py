from __future__ import annotations

from typing import Iterable

_REASONING_OPEN_TAG = "<think"
_REASONING_CLOSE_TAG = "</think>"


def _strip_reasoning_markup(text: str) -> str:
    remaining = text or ""
    visible: list[str] = []
    while remaining:
        lower = remaining.lower()
        start = lower.find(_REASONING_OPEN_TAG)
        dangling_close = lower.find(_REASONING_CLOSE_TAG)
        if dangling_close >= 0 and (start < 0 or dangling_close < start):
            remaining = remaining[dangling_close + len(_REASONING_CLOSE_TAG) :]
            continue
        if start < 0:
            visible.append(remaining)
            break
        visible.append(remaining[:start])
        tag_end = lower.find(">", start)
        if tag_end < 0:
            break
        close_start = lower.find(_REASONING_CLOSE_TAG, tag_end + 1)
        if close_start < 0:
            break
        remaining = remaining[close_start + len(_REASONING_CLOSE_TAG) :]
    return "".join(visible).strip()


def _reasoning_open_tag_prefix_length(text: str) -> int:
    lower = text.lower()
    max_prefix = min(len(lower), len(_REASONING_OPEN_TAG))
    for size in range(max_prefix, 0, -1):
        if _REASONING_OPEN_TAG.startswith(lower[-size:]):
            return size
    return 0


def _iter_visible_text_deltas(
    deltas: Iterable[str],
    *,
    suppress_leading_dangling_reasoning: bool = False,
) -> Iterable[str]:
    pending = ""
    suppressing_reasoning = False
    emitted_visible = False
    for delta in deltas:
        pending += delta
        while pending:
            lower = pending.lower()
            if suppressing_reasoning:
                close_start = lower.find(_REASONING_CLOSE_TAG)
                if close_start < 0:
                    pending = pending[-(len(_REASONING_CLOSE_TAG) - 1) :]
                    break
                pending = pending[close_start + len(_REASONING_CLOSE_TAG) :]
                suppressing_reasoning = False
                continue

            open_start = lower.find(_REASONING_OPEN_TAG)
            dangling_close = lower.find(_REASONING_CLOSE_TAG)
            if dangling_close >= 0 and (open_start < 0 or dangling_close < open_start):
                pending = pending[dangling_close + len(_REASONING_CLOSE_TAG) :]
                suppress_leading_dangling_reasoning = False
                continue
            if suppress_leading_dangling_reasoning and not emitted_visible and open_start < 0:
                break
            if open_start < 0:
                keep = _reasoning_open_tag_prefix_length(pending)
                visible = pending[:-keep] if keep else pending
                if visible:
                    emitted_visible = True
                    yield visible
                pending = pending[-keep:] if keep else ""
                break

            visible = pending[:open_start]
            if visible:
                emitted_visible = True
                yield visible
            tag_end = lower.find(">", open_start)
            if tag_end < 0:
                pending = pending[open_start:]
                break
            pending = pending[tag_end + 1 :]
            suppressing_reasoning = True

    if pending and not suppressing_reasoning:
        visible = _strip_reasoning_markup(pending)
        if visible:
            emitted_visible = True
            yield visible
