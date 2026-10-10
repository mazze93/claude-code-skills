"""Parse a Claude Code transcript (.jsonl) into prompts, events and tool calls.

Unlike the conversation export, the transcript keeps each tool's RESULT, so
outcomes here are observed: the tool's own error flag, plus an error-signature
scan of the output (which catches failures a pipe hid from the flag).
Reads one file; no other side effects.
"""
import json
from datetime import datetime
from pathlib import Path

from .parse_export import primary_input
from .taxonomy import scan_errors


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _text_of(content) -> str:
    """Flatten a message or tool_result content (str | list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def _result_text(block: dict, extra) -> str:
    """Everything the tool returned: the block content plus stdout/stderr if present."""
    parts = [_text_of(block.get("content"))]
    if isinstance(extra, dict):
        parts += [str(extra.get(k, "")) for k in ("stdout", "stderr") if extra.get(k)]
    return "\n".join(p for p in parts if p)


def classify_prompt(entry: dict, text: str) -> str:
    """human | stop-hook | compaction | context — only the first two open an exchange."""
    if (entry.get("origin") or {}).get("kind") == "human":
        return "human"
    if entry.get("isCompactSummary"):
        return "compaction"
    if text.startswith("Stop hook feedback"):
        return "stop-hook"
    return "context"


def _iter_entries(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def parse_transcript(path: Path) -> dict:
    """→ {"prompts": [...], "events": [...], "calls": [...]} in file order.

    Each call carries `prompt_index`: the index into prompts of the exchange it
    belongs to, or -1 when it precedes the first prompt in this file (a
    session resumed after compaction starts mid-exchange).
    """
    prompts, events, calls, by_id = [], [], [], {}
    for e in _iter_entries(path):
        msg = e.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        blocks = content if isinstance(content, list) else []
        if e.get("type") == "user" and not any(b.get("type") == "tool_result" for b in blocks):
            _record_prompt(e, _text_of(content), prompts, events)
            continue
        for b in blocks:
            if b.get("type") == "tool_use":
                call = {"use_id": b["id"], "tool": b["name"], "input": primary_input(b.get("input") or {}),
                        "description": (b.get("input") or {}).get("description", ""),
                        "started_at": e["timestamp"], "prompt_index": len(prompts) - 1}
                by_id[b["id"]] = call
                calls.append(call)
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in by_id:
                _attach_result(by_id[b["tool_use_id"]], b, e)
    return {"prompts": prompts, "events": events, "calls": calls}


def _record_prompt(entry: dict, text: str, prompts: list, events: list) -> None:
    kind = classify_prompt(entry, text)
    if kind in ("human", "stop-hook"):
        prompts.append({"at": entry["timestamp"], "initiator": "human" if kind == "human" else "Harness",
                        "kind": kind, "text": text})
    events.append({"at": entry["timestamp"], "kind": kind, "text": text[:400]})


# Only execution output is scanned for error signatures. A Read of a file that
# happens to contain "Error:" is file content, not a failure.
SCANNED_TOOLS = ("Bash", "BashOutput", "mcp__claude-code-remote__", "mcp__remote-devices__device_bash")


def _scans(tool: str) -> bool:
    return any(tool == t or (t.endswith("__") and tool.startswith(t)) for t in SCANNED_TOOLS)


def classify_result(tool: str, output: str, flagged_error: bool) -> dict:
    """One outcome policy for transcript and hook evidence.

    Scan execution output only: a successful Read of source containing "Error:"
    is not itself a tool failure. Flagged errors always outrank text heuristics.
    """
    sig, line = scan_errors(output) if _scans(tool) else ("", "")
    if not sig and _scans(tool) and output.lstrip().startswith(("Error:", "<tool_use_error>")):
        sig, line = "tool-error", output.strip().splitlines()[0][:300]
    if flagged_error:
        return dict(outcome="error", outcome_source="tool-flag",
                    error_signature=sig or "tool-error",
                    error_excerpt=(line or output.strip())[:300])
    if sig:
        return dict(outcome="error_unflagged", outcome_source="output-scan",
                    error_signature=sig, error_excerpt=line)
    return dict(outcome="ok", outcome_source="tool-flag",
                error_signature="", error_excerpt="")


def _attach_result(call: dict, block: dict, entry: dict) -> None:
    """Set observed outcome, time and duration on the matching tool use."""
    out = _result_text(block, entry.get("toolUseResult"))
    call["ended_at"] = entry["timestamp"]
    call["duration_s"] = round((_ts(entry["timestamp"]) - _ts(call["started_at"])).total_seconds(), 2)
    call.update(classify_result(call["tool"], out, bool(block.get("is_error"))))
