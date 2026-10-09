#!/usr/bin/env python3
"""core-sample capture hook for Claude Code.

Register for PostToolUse, PostToolUseFailure, PreCompact and SessionEnd (see
SKILL.md). Every firing appends one line to
  $CORE_SAMPLE_HOME/ledger/<session_id>.jsonl      (default ~/.claude/core-sample)
and PreCompact / SessionEnd also copy the transcript to
  $CORE_SAMPLE_HOME/archive/<session_id>/transcript-<event>-<utc>.jsonl
so tool results survive compaction.

Data classification: CONFIDENTIAL-LOCAL. Tool inputs and outputs can contain
anything the session touched. Files are created mode 0600, obvious secrets are
redacted (patterns below; not exhaustive), large outputs are truncated, and
nothing leaves the machine. The hook never blocks Claude Code: it always exits 0
and writes its own errors to $CORE_SAMPLE_HOME/hook-errors.log.
"""
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("CORE_SAMPLE_HOME", Path.home() / ".claude" / "core-sample"))
MAX_TEXT = 20_000          # characters kept per string field in a payload
# Order matters: whole-token patterns run first, so "Authorization: Bearer <t>"
# loses the token itself, not just the word "Bearer" (a test caught that leak).
SECRET_PATTERNS = [
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"\b(ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|authorization)\b(\s*[:=]\s*)(\S+)"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
]


def redact(text: str) -> str:
    """Mask obvious secrets and cap length. Pure."""
    for rx in SECRET_PATTERNS:
        text = rx.sub(lambda m: (m.group(1) + m.group(2) + "[REDACTED]") if m.re.groups >= 3 else "[REDACTED]", text)
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + f"… [truncated {len(text) - MAX_TEXT} chars]"


def scrub(value):
    """Apply redact() to every string inside a JSON value. Pure."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


def _private_append(path: Path, line: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def archive_transcript(payload: dict, event: str, stamp: str) -> None:
    """Copy the transcript before compaction or at session end (side effect: one file)."""
    src = Path(payload.get("transcript_path") or "")
    if not src.is_file():
        return
    dest = HOME / "archive" / payload.get("session_id", "unknown") / f"transcript-{event}-{stamp}.jsonl"
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    os.chmod(dest, 0o600)


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    event = payload.get("hook_event_name", "unknown")
    now = datetime.now(timezone.utc)
    record = {"received_at": now.isoformat(), "event": event, "payload": scrub(payload)}
    _private_append(HOME / "ledger" / f"{payload.get('session_id', 'unknown')}.jsonl", json.dumps(record, ensure_ascii=False))
    if event in ("PreCompact", "SessionEnd"):
        archive_transcript(payload, event, now.strftime("%Y%m%dT%H%M%SZ"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never block the session; leave a trace instead
        try:
            _private_append(HOME / "hook-errors.log", f"{datetime.now(timezone.utc).isoformat()} {exc!r}")
        except Exception:
            pass
    sys.exit(0)
