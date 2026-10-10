#!/usr/bin/env python3
"""tool-ledger: make tool results survive Claude Code context compaction.

Two modes, wired as hooks in ~/.claude/settings.json:

  capture   PostToolUse hook. Appends every tool call (name, input summary,
            truncated result) to ~/.claude/tool-ledger/<session_id>.jsonl.
  restore   SessionStart hook with matcher "compact". After compaction, reads
            that session's ledger and injects a digest of the most recent tool
            results back into context via hookSpecificOutput.additionalContext,
            plus the ledger path so Claude can Read the full entries.

Stdlib only. Never blocks a tool call: every failure path exits 0 and writes
a line to ~/.claude/tool-ledger/_errors.log instead.

Tunables (env vars, optional):
  TOOL_LEDGER_DIR          default ~/.claude/tool-ledger
  TOOL_LEDGER_STORE_CHARS  max chars of each result kept on disk (default 20000)
  TOOL_LEDGER_BUDGET       max chars injected after compaction (default 9000;
                           Claude Code caps additionalContext at 10000)
  TOOL_LEDGER_ENTRY_CHARS  max result chars per entry in the digest (default 700)
  TOOL_LEDGER_KEEP_DAYS    ledgers older than this are pruned on restore (default 14)
"""
import datetime as _dt
import fcntl
import json
import os
import re
import sys
import time

LEDGER_DIR = os.path.expanduser(os.environ.get("TOOL_LEDGER_DIR", "~/.claude/tool-ledger"))
STORE_CHARS = int(os.environ.get("TOOL_LEDGER_STORE_CHARS", "20000"))
BUDGET = int(os.environ.get("TOOL_LEDGER_BUDGET", "9000"))
ENTRY_CHARS = int(os.environ.get("TOOL_LEDGER_ENTRY_CHARS", "700"))
KEEP_DAYS = int(os.environ.get("TOOL_LEDGER_KEEP_DAYS", "14"))


def _log_error(msg):
    try:
        os.makedirs(LEDGER_DIR, mode=0o700, exist_ok=True)
        fd = os.open(os.path.join(LEDGER_DIR, "_errors.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(f"{_dt.datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass


def _safe_session(sid):
    # session_id becomes a filename; refuse anything path-like.
    sid = str(sid or "unknown")
    return re.sub(r"[^A-Za-z0-9._-]", "_", sid)[:128] or "unknown"


def _ledger_path(sid):
    return os.path.join(LEDGER_DIR, _safe_session(sid) + ".jsonl")


def _clip(text, limit):
    if len(text) <= limit:
        return text
    head = int(limit * 0.7)
    tail = limit - head
    return f"{text[:head]}\n...[{len(text) - limit} chars elided]...\n{text[-tail:]}"


def _flatten_response(resp):
    """Turn the various tool_response shapes into plain text."""
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp
    if isinstance(resp, list):  # MCP-style content blocks
        parts = []
        for block in resp:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(json.dumps(block, ensure_ascii=False, default=str))
        return "\n".join(parts)
    if isinstance(resp, dict):
        if "stdout" in resp or "stderr" in resp:  # Bash
            out = str(resp.get("stdout") or "")
            err = str(resp.get("stderr") or "")
            return out + (f"\n[stderr]\n{err}" if err.strip() else "")
        f = resp.get("file")
        if isinstance(f, dict) and "content" in f:  # Read
            return str(f.get("content", ""))
        if "content" in resp and isinstance(resp["content"], (str, list)):
            return _flatten_response(resp["content"])
        return json.dumps(resp, ensure_ascii=False, default=str)
    return str(resp)


def _summarize_input(tool, inp):
    if not isinstance(inp, dict):
        return str(inp)
    for key in ("command", "file_path", "path", "url", "pattern", "query", "prompt"):
        if key in inp and inp[key]:
            extra = ""
            if key == "pattern" and inp.get("path"):
                extra = f" in {inp['path']}"
            return f"{key}={inp[key]}{extra}"
    return json.dumps(inp, ensure_ascii=False, default=str)


def capture(payload):
    sid = payload.get("session_id")
    tool = payload.get("tool_name", "?")
    inp = payload.get("tool_input", {})
    result = _flatten_response(payload.get("tool_response"))
    entry = {
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "tool": tool,
        "tool_use_id": payload.get("tool_use_id"),
        "cwd": payload.get("cwd"),
        "input": _clip(_summarize_input(tool, inp), 500),
        "result_chars": len(result),
        "result": _clip(result, STORE_CHARS),
    }
    os.makedirs(LEDGER_DIR, mode=0o700, exist_ok=True)
    path = _ledger_path(sid)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # parallel tool calls append concurrently
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)


def _prune():
    cutoff = time.time() - KEEP_DAYS * 86400
    try:
        for name in os.listdir(LEDGER_DIR):
            p = os.path.join(LEDGER_DIR, name)
            if name.endswith(".jsonl") and os.path.getmtime(p) < cutoff:
                os.remove(p)
    except Exception as e:
        _log_error(f"prune: {e!r}")


def restore(payload):
    sid = payload.get("session_id")
    path = _ledger_path(sid)
    if not os.path.exists(path):
        return  # nothing captured this session; inject nothing
    entries = []
    with open(path) as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue  # a torn line never breaks restore
    if not entries:
        return

    header = (
        "[tool-ledger] Context was just compacted. Below are the most recent tool "
        f"results from this session ({len(entries)} captured in total), recovered "
        f"from {path}. Results are truncated here; Read that file (JSONL, one "
        "entry per tool call, `result` field) for the stored text.\n"
    )
    footer_tpl = "\n[tool-ledger] {shown} of {total} entries shown; {omitted} older entries only in the file."

    budget = BUDGET - len(header) - 120
    chosen = []
    for e in reversed(entries):  # newest first until the budget is spent
        block = (
            f"\n--- {e.get('ts', '?')} {e.get('tool', '?')}: {e.get('input', '')}\n"
            f"{_clip(str(e.get('result', '')), ENTRY_CHARS)}"
            + (f"\n(full result was {e.get('result_chars')} chars)" if e.get("result_chars", 0) > ENTRY_CHARS else "")
            + "\n"
        )
        if len(block) > budget:
            break
        budget -= len(block)
        chosen.append(block)
    chosen.reverse()  # present chronologically

    text = header + "".join(chosen) + footer_tpl.format(
        shown=len(chosen), total=len(entries), omitted=len(entries) - len(chosen)
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": text,
        }
    }))
    _prune()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        _log_error(f"{mode}: bad stdin: {e!r}")
        return 0
    try:
        if mode == "capture":
            capture(payload)
        elif mode == "restore":
            if payload.get("source", "compact") == "compact":
                restore(payload)
        else:
            _log_error(f"unknown mode {mode!r}")
    except Exception as e:
        _log_error(f"{mode}: {e!r}")
    return 0  # never block Claude Code


if __name__ == "__main__":
    sys.exit(main())
