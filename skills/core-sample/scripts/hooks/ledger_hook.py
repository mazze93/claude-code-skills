#!/usr/bin/env python3
"""Explicitly armed, session-scoped Claude Code evidence hook.

The skill's frontmatter registers this hook *only after the skill is invoked*.
Run the documented arm/disarm commands through Claude's Bash tool. Those exact
successful tool calls cause the hook to transition that session's capture gate.
An unarmed session never stores its tool payload. No global hooks are required.

Hook ledgers contain redacted, length-capped observations, not complete raw
transcripts. Raw transcript archiving is separately opt-in and UNREDACTED.
"""
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("CORE_SAMPLE_HOME", Path.home() / ".claude" / "core-sample"))
MAX_TEXT = 20_000
ARM_COMMAND = 'python3 "$HOME/.claude/core-sample/toolkit/hooks/ledger_hook.py" arm'
DISARM_COMMAND = 'python3 "$HOME/.claude/core-sample/toolkit/hooks/ledger_hook.py" disarm'
SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
SECRET_KEY = re.compile(
    r"(?i)^(api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|"
    r"client[_-]?secret|password|passwd|authorization|cookie)$"
)
SECRET_PATTERNS = [
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"\b(ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|authorization)\b(\s*[:=]\s*)(\S+)"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
]


def redact(text: str) -> str:
    """Best-effort masking. The ledger remains confidential despite masking."""
    for rx in SECRET_PATTERNS:
        text = rx.sub(
            lambda m: (m.group(1) + m.group(2) + "[REDACTED]")
            if m.re.groups >= 3 else "[REDACTED]", text
        )
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + f"… [truncated {len(text) - MAX_TEXT} chars]"


def scrub(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if isinstance(k, str) and SECRET_KEY.fullmatch(k)
            else scrub(v)
            for k, v in value.items()
        }
    return value


def safe_id(value) -> str:
    """Reject ambiguous or unsafe ids instead of silently colliding filenames."""
    if not isinstance(value, str) or not SESSION_ID.fullmatch(value):
        raise ValueError("invalid or missing Claude session_id")
    return value


def _private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    for d in (HOME, path, *[p for p in path.parents if HOME in p.parents]):
        if d.is_dir():
            os.chmod(d, 0o700)


def _private_append(path: Path, line: str) -> None:
    _private_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _state_path(sid: str) -> Path:
    return HOME / "state" / (safe_id(sid) + ".state")


def _state(sid: str) -> str:
    path = _state_path(sid)
    return path.read_text(encoding="utf-8").strip() if path.is_file() else "off"


def _set_state(sid: str, status: str) -> None:
    """Private atomic state replacement. Independent for every Claude session."""
    path = _state_path(sid)
    _private_dir(path.parent)
    tmp = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(status + "\n")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _log(sid: str, event: str, payload: dict, stamp: str) -> None:
    rec = {"received_at": stamp, "event": event, "payload": scrub(payload)}
    _private_append(HOME / "ledger" / (sid + ".jsonl"), json.dumps(rec, ensure_ascii=False))


def _control_command(payload: dict) -> str:
    if payload.get("hook_event_name") != "PostToolUse" or payload.get("tool_name") != "Bash":
        return ""
    inp = payload.get("tool_input") or {}
    if not isinstance(inp, dict):
        return ""
    return inp.get("command", "")


def archive_transcript(payload: dict, event: str, stamp: str) -> None:
    """UNREDACTED raw transcript; explicit opt-in only, never a publishable file."""
    if os.environ.get("CORE_SAMPLE_ARCHIVE_RAW") != "1":
        return
    sid = safe_id(payload.get("session_id"))
    src = Path(payload.get("transcript_path") or "").resolve()
    base = (Path.home() / ".claude" / "projects").resolve()
    # Do not let an arbitrary hook payload copy files outside the Claude project.
    if src.name != sid + ".jsonl" or base not in src.parents or not src.is_file():
        raise ValueError("transcript_path is not a Claude session transcript")
    dest = HOME / "archive" / sid / f"transcript-{event}-{stamp}.jsonl"
    _private_dir(dest.parent)
    shutil.copyfile(src, dest)
    os.chmod(dest, 0o600)


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    if not isinstance(payload, dict):
        raise ValueError("hook stdin must be a JSON object")
    sid = safe_id(payload.get("session_id"))
    event = payload.get("hook_event_name", "")
    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    command = _control_command(payload)

    # Fail-closed by default. Only an actual successful Bash invocation of the
    # exact arm command can activate this session (never another session).
    if command == ARM_COMMAND:
        _set_state(sid, "active")
        _log(sid, "CaptureStarted", {"session_id": sid}, stamp)
        return
    if command == DISARM_COMMAND:
        if _state(sid) == "active":
            _log(sid, "CaptureStopped", {"session_id": sid}, stamp)
        _set_state(sid, "off")
        return
    if _state(sid) != "active":
        return
    if event not in ("PostToolUse", "PostToolUseFailure", "PreCompact", "SessionEnd"):
        return
    _log(sid, event, payload, stamp)
    if event in ("PreCompact", "SessionEnd"):
        archive_transcript(payload, event, now.strftime("%Y%m%dT%H%M%SZ"))
    if event == "SessionEnd":
        _set_state(sid, "off")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # The hook, rather than this CLI invocation, receives the authoritative
        # session_id via event stdin. Never arm a global marker from a shell.
        if sys.argv[1:] == ["arm"]:
            print("CORE_SAMPLE_ARM_REQUEST_V1")
        elif sys.argv[1:] == ["disarm"]:
            print("CORE_SAMPLE_DISARM_REQUEST_V1")
        else:
            sys.exit("usage: ledger_hook.py [arm|disarm]")
    else:
        try:
            main()
        except Exception as exc:
            try:
                _private_append(
                    HOME / "hook-errors.log",
                    f"{datetime.now(timezone.utc).isoformat()} {exc!r}"
                )
            except Exception:
                pass
        # Capture must never block the Claude Code session.
        sys.exit(0)
