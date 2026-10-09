"""Parse claude.ai conversation-export pages (read_conversation output).

The export keeps each tool call's name and parameters but NOT its result, so
every call parsed here starts as outcome "unrecorded". Pure parsing; the only
side effect is reading the files passed in.
"""
import html
import re
from pathlib import Path

_TURN = re.compile(r'<turn n="(\d+)">(Human|Assistant): (.*?)</turn>', re.S)
_TURN_OPEN = re.compile(r'<turn n="(\d+)">(Human|Assistant): (.*)', re.S)   # last turn of a truncated page
_TOOL = re.compile(r'<tool name="([^"]+)">(.*?)</tool>', re.S)
_PARAM = re.compile(r'<parameter name="([^"]+)">(.*?)</parameter>', re.S)
_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>\s*", re.S)

# Which parameter best identifies what a call did, in priority order.
PRIMARY_PARAMS = ("command", "file_path", "url", "query", "skill", "pattern", "prompt",
                  "message", "files", "path", "page_token", "action", "subject", "taskId")


def primary_input(params: dict) -> str:
    """The one parameter that says what the call did, whitespace-collapsed."""
    for key in PRIMARY_PARAMS:
        if params.get(key):
            return " ".join(str(params[key]).split())
    return ""


def parse_calls(body: str) -> list[dict]:
    """Every <tool> block in an assistant turn, in order, with its parameters."""
    calls = []
    for seq, (name, inner) in enumerate(_TOOL.findall(body), start=1):
        params = {k: v.strip() for k, v in _PARAM.findall(inner)}
        calls.append({"seq": seq, "tool": name, "description": params.get("description", ""),
                      "input": primary_input(params)})
    return calls


def parse_page(text: str) -> list[dict]:
    """One export page → list of turns: {turn, role, text, calls}."""
    text = html.unescape(text)
    turns = [m.groups() for m in _TURN.finditer(text)]
    if not turns:                                   # a single, truncated turn
        m = _TURN_OPEN.search(text)
        turns = [m.groups()] if m else []
    out = []
    for n, role, body in turns:
        prose = _REMINDER.sub("", _TOOL.sub("", body)).strip()
        out.append({"turn": int(n), "role": role.lower(), "text": prose,
                    "calls": parse_calls(body) if role == "Assistant" else []})
    return out


def parse_pages(paths: list[Path]) -> list[dict]:
    """All pages, de-duplicated by turn number (the longest copy wins), sorted."""
    best: dict[int, dict] = {}
    for p in paths:
        for t in parse_page(Path(p).read_text(encoding="utf-8")):
            if t["turn"] not in best or len(t["calls"]) > len(best[t["turn"]]["calls"]):
                best[t["turn"]] = t
    return [best[k] for k in sorted(best)]
