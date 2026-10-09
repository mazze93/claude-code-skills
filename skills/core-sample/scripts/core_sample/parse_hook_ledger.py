"""Parse explicitly armed Claude Code PostToolUse evidence.

The hook ledger contains control events as well as tool outcomes. Only actual
tool observations enter this table; each uses Claude's stable tool_use_id so
transcript records can be reconciled without guessing from tool names/times.
"""
import json
from pathlib import Path

from .parse_export import primary_input
from .parse_transcript import classify_result


def _text(value) -> str:
    """Flatten Claude's nested text blocks and execution output for classification."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_text(item) for item in value)
    if isinstance(value, dict):
        pieces = [value.get(k) for k in ("text", "stdout", "stderr", "content", "error")]
        return "\n".join(_text(p) for p in pieces if p is not None)
    return ""


def parse_hook_ledger(path: Path, session: dict) -> list[dict]:
    """Return calls recorded while armed; prompt-free hooks require an exchange map."""
    if not Path(path).exists():
        return []
    calls = []
    seen = {}
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        event = rec.get("event")
        if event not in ("PostToolUse", "PostToolUseFailure"):
            continue
        p = rec.get("payload", {})
        tool_input = p.get("tool_input") or {}
        response = p.get("tool_response")
        if not isinstance(tool_input, dict):
            tool_input = {}
        call = {
            "exchange": rec.get("exchange") or session.get("hook_exchange", "E01"),
            "tool_use_id": p.get("tool_use_id") or "",
            "tool": p.get("tool_name", "?"),
            "description": tool_input.get("description", ""),
            "input": primary_input(tool_input),
            "ended_at": rec.get("received_at", ""),
        }
        flagged = event == "PostToolUseFailure" or (
            isinstance(response, dict) and bool(response.get("is_error"))
        )
        result_text = str(p.get("error", "")) if event == "PostToolUseFailure" else _text(response)
        call.update(classify_result(call["tool"], result_text, flagged))
        uid = call["tool_use_id"]
        if uid and uid in seen:
            previous = seen[uid]
            check = ("tool", "input", "outcome", "error_signature", "error_excerpt")
            if any(previous[k] != call[k] for k in check):
                raise ValueError(f"conflicting duplicate hook evidence for {uid} at line {lineno}")
            continue  # repeated skill registration may emit the same hook twice
        if uid:
            seen[uid] = call
        calls.append(call)
    return calls
