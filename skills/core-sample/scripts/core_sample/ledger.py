"""Assemble one session's ledger from raw sources + curated annotations.

Inputs (all inside the session folder):
  raw/export/*.txt       conversation-export pages (calls, no results)
  raw/transcript.jsonl   Claude Code transcript (calls WITH results)
  raw/hook-ledger.jsonl  optional: live PostToolUse/PostToolUseFailure records
  calls_manual.json      calls transcribed by hand when no file holds them
  session.json, exchanges.json, failures.json, findings.json, sources.json,
  deliverables.json, open_items.json      curated annotations
Output: a dict of tables (lists of row dicts). Pure apart from reading files.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import taxonomy as T
from .parse_export import parse_pages
from .parse_hook_ledger import parse_hook_ledger
from .parse_transcript import parse_transcript

_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>\s*", re.S)


def _load(folder: Path, name: str, default):
    p = folder / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _ex_ord(exchange: str) -> int:
    return int(exchange[1:]) if exchange and exchange[1:].isdigit() else 0


def _call(exchange, tool, description, inp, source, extra: dict | None = None) -> dict:
    row = {"exchange": exchange, "tool": tool, "tool_short": T.short_tool(tool), "family": T.family_of(tool),
           "description": description, "input": inp[:2000], "started_at": "", "ended_at": "", "duration_s": None,
           "outcome": "unrecorded", "outcome_source": "none", "error_signature": "", "error_excerpt": "",
           "record_source": source, "failure_id": ""}
    row.update({k: v for k, v in (extra or {}).items() if k in row and k not in ("exchange", "tool", "input")})
    return row


# ── Sources of calls ─────────────────────────────────────────────────────
def export_calls(folder: Path, session: dict) -> list[dict]:
    turn_map = session.get("export_turn_map", {})
    rows = []
    for turn in parse_pages(sorted((folder / "raw" / "export").glob("*.txt"))):
        if turn["role"] != "assistant":
            continue
        ex = turn_map.get(str(turn["turn"]), f"E{turn['turn'] // 2 + 1:02d}")
        rows += [_call(ex, c["tool"], c["description"], c["input"], "export") for c in turn["calls"]]
    return rows


def manual_calls(folder: Path) -> list[dict]:
    return [_call(c["exchange"], c["tool"], c.get("description", ""), c.get("input", ""), "manual")
            for c in _load(folder, "calls_manual.json", [])]


def transcript_calls(folder: Path, session: dict, tz: ZoneInfo) -> tuple[list, list, list]:
    """→ (calls, prompts, events) from raw/transcript.jsonl, exchange ids assigned."""
    path = folder / "raw" / "transcript.jsonl"
    if not path.exists():
        return [], [], []
    tr = parse_transcript(path)
    first, offset = session.get("transcript_first_exchange", "E01"), session.get("transcript_exchange_offset", 1)
    ex_of = lambda i: first if i < 0 else f"E{offset + i:02d}"
    calls = [_call(ex_of(c["prompt_index"]), c["tool"], c["description"], c["input"], "transcript", c)
             for c in tr["calls"]]
    prompts = [dict(p, exchange=ex_of(i), at_local=_local(p["at"], tz)) for i, p in enumerate(tr["prompts"])]
    events, current = [], first
    for ev in tr["events"]:
        match = next((p for p in prompts if p["at"] == ev["at"]), None)
        current = match["exchange"] if match else current
        events.append({"at_utc": ev["at"], "kind": ev["kind"], "exchange": current, "text": ev["text"]})
    return calls, prompts, events


def _local(iso: str, tz: ZoneInfo) -> str:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(tz).strftime("%H:%M")


# ── Assembly ─────────────────────────────────────────────────────────────
def number_calls(calls: list[dict]) -> list[dict]:
    """Stable order (exchange, then source order) and per-exchange seq + call_id."""
    order = {"export": 0, "manual": 0, "transcript": 1, "hook": 1}
    calls = sorted(enumerate(calls), key=lambda ic: (_ex_ord(ic[1]["exchange"]), order[ic[1]["record_source"]], ic[0]))
    seq: dict[str, int] = {}
    out = []
    for _, c in calls:
        seq[c["exchange"]] = seq.get(c["exchange"], 0) + 1
        out.append(dict(c, seq=seq[c["exchange"]], call_id=f"{c['exchange']}-{seq[c['exchange']]:03d}"))
    return out


def resolve_call(spec, calls: list[dict]) -> dict | None:
    """Find the call a failure points at: {"exchange","seq"} or {"exchange","tool","contains"}."""
    if not spec:
        return None
    pool = [c for c in calls if c["exchange"] == spec["exchange"]]
    if "seq" in spec:
        return next((c for c in pool if c["seq"] == spec["seq"]), None)
    needle = spec.get("contains", "")
    return next((c for c in pool if c["tool"] == spec["tool"]
                 and (needle in c["input"] or needle in c["description"])), None)


def link_failures(failures: list[dict], calls: list[dict]) -> list[dict]:
    """Attach failures to calls; an unrecorded call a failure names becomes attested_fail."""
    out = []
    for f in failures:
        call = resolve_call(f.get("call"), calls)
        if f.get("call") and call is None:
            raise ValueError(f"{f['failure_id']}: no call matches {f['call']}")
        row = {k: v for k, v in f.items() if k != "call"}
        row["call_id"] = call["call_id"] if call else ""
        row["exchanges_to_detect"] = _ex_ord(f["detected_in"]) - _ex_ord(f["exchange"])
        if call:
            call["failure_id"] = f["failure_id"]
            if call["outcome"] == "unrecorded":
                call.update(outcome="attested_fail", outcome_source=f["link_basis"])
        out.append(row)
    return out


def session_person(exchanges: list[dict]) -> str:
    """The human's display name, as the curated exchanges already use it (default 'Person')."""
    return next((e["initiator"] for e in exchanges if e.get("initiator") not in (None, "", "Harness")), "Person")


def merge_prompts(exchanges: list[dict], prompts: list[dict]) -> list[dict]:
    """Transcript prompts are verbatim: they replace curated prompt text and time."""
    by_ex = {p["exchange"]: p for p in prompts}
    person = session_person(exchanges)
    out = []
    for i, e in enumerate(exchanges, 1):
        e = dict(e, ordinal=i)
        p = by_ex.get(e["exchange"])
        if p:
            e.update(prompt=_REMINDER.sub("", p["text"]).strip(), prompt_provenance="Verbatim",
                     at_local=p["at_local"], initiator=person if p["initiator"] == "human" else p["initiator"])
        out.append(e)
    return out


# ── Validation: fail loudly on any value outside the vocabularies ───────
def validate(tables: dict) -> None:
    checks = [
        ("tool_calls", "outcome", T.OUTCOME_KEYS),
        ("failures", "layer", [l[0] for l in T.LAYERS]),
        ("failures", "detection", [d[0] for d in T.DETECTIONS]),
        ("failures", "detected_by", T.DETECTED_BY),
        ("failures", "caught", [c[0] for c in T.CAUGHT]),
        ("failures", "status", T.STATUSES),
        ("failures", "link_basis", [b[0] for b in T.LINK_BASIS]),
        ("failures", "severity", list(T.SEVERITY)),
        ("open_items", "status", [s[0] for s in T.OPEN_STATUSES]),
    ]
    errors = [f"{t}.{col} = {r[col]!r} (row {r.get('failure_id') or r.get('call_id') or r.get('item_id')})"
              for t, col, allowed in checks for r in tables.get(t, []) if r.get(col) not in allowed]
    exchanges = {e["exchange"] for e in tables["exchanges"]}
    errors += [f"tool_calls.exchange {c['exchange']} has no exchange row"
               for c in tables["tool_calls"] if c["exchange"] not in exchanges]
    if errors:
        raise ValueError("Ledger validation failed:\n  " + "\n  ".join(sorted(set(errors))))


def build_ledger(folder: Path) -> dict:
    """Read every source in a session folder → validated tables (row dicts, session_id on each)."""
    folder = Path(folder)
    session = _load(folder, "session.json", {})
    tz = ZoneInfo(session.get("timezone", "UTC"))
    t_calls, prompts, events = transcript_calls(folder, session, tz)
    hook_calls = [_call(c["exchange"], c["tool"], c["description"], c["input"], "hook", c)
                  for c in parse_hook_ledger(folder / "raw" / "hook-ledger.jsonl", session)] if not t_calls else []
    calls = number_calls(export_calls(folder, session) + manual_calls(folder) + t_calls + hook_calls)
    tables = {
        "sessions": [dict(session_id=session["session_id"], title=session.get("title"), chat_title=session.get("chat_title"),
                          chat_url=session.get("chat_url"), project=session.get("project"), date=session.get("date"),
                          timezone=session.get("timezone"), how_found_sets=session.get("how_found_sets", []), as_of=datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z"),
                          notes=" ".join(session.get("notes", [])))],
        "exchanges": merge_prompts(_load(folder, "exchanges.json", []), prompts),
        "events": events,
        "tool_calls": calls,
        "failures": link_failures(_load(folder, "failures.json", []), calls),
        "findings": _load(folder, "findings.json", []),
        "sources": _load(folder, "sources.json", []),
        "deliverables": _load(folder, "deliverables.json", []),
        "open_items": _load(folder, "open_items.json", []),
    }
    for rows in tables.values():
        for r in rows:
            r["session_id"] = session["session_id"]
    validate(tables)
    return tables
