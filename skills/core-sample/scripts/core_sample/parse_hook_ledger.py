"""Parse the live hook ledger written by hooks/ledger_hook.py.

Each line is one hook firing: {"received_at", "event", "payload"} where payload
is the raw stdin JSON Claude Code sent. PostToolUse = the call succeeded;
PostToolUseFailure = it failed (the docs' event table; payload field names are
read defensively because the shell-hook schema isn't fully documented).
Used only when no transcript is available. Reads one file.
"""
import json
from pathlib import Path

from .parse_export import primary_input
from .taxonomy import scan_errors


def _text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(str(value.get(k, "")) for k in ("stdout", "stderr", "content", "error") if value.get(k))
    return json.dumps(value)[:2000] if value is not None else ""


def parse_hook_ledger(path: Path, session: dict) -> list[dict]:
    """→ call dicts with observed outcomes. Prompts aren't in the hook ledger, so every
    call goes to session["hook_exchange"] (default E01) unless the record carries one."""
    if not Path(path).exists():
        return []
    calls = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        rec = json.loads(line) if line.strip() else None
        if not rec or rec.get("event") not in ("PostToolUse", "PostToolUseFailure"):
            continue
        p = rec.get("payload", {})
        tool_input = p.get("tool_input") or {}
        call = {"exchange": rec.get("exchange") or session.get("hook_exchange", "E01"), "tool": p.get("tool_name", "?"),
                "description": tool_input.get("description", "") if isinstance(tool_input, dict) else "",
                "input": primary_input(tool_input) if isinstance(tool_input, dict) else str(tool_input)[:500],
                "ended_at": rec.get("received_at", "")}
        if rec["event"] == "PostToolUseFailure":
            call.update(outcome="error", outcome_source="tool-flag", error_signature="tool-error",
                        error_excerpt=str(p.get("error", ""))[:300])
        else:
            sig, line_ = scan_errors(_text(p.get("tool_response")))
            call.update(outcome="error_unflagged" if sig else "ok",
                        outcome_source="output-scan" if sig else "tool-flag",
                        error_signature=sig, error_excerpt=line_)
        calls.append(call)
    return calls
