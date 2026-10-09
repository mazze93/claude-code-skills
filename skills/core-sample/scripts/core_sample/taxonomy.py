"""Controlled vocabularies for a core sample.

Everything a chart groups by, or a validator checks, is defined here once:
tool families, call outcomes, failure layers and detection methods, plus the
icon and colour each one wears. Pure data and pure functions; no I/O.
"""
import re

# ── Tool families ────────────────────────────────────────────────────────
# Order is the categorical palette order (dataviz reference palette, slots
# 1–7, validated for adjacent pairs). Never reorder without re-validating.
FAMILIES = [
    # (family, colour, icon, exact tool names, name prefixes)
    ("Shell", "2A78D6", "⌨️", {"Bash", "BashOutput", "KillShell"}, ()),
    ("Files", "EB6834", "📄", {"Read", "Write", "Edit", "Glob", "Grep", "NotebookEdit"}, ()),
    ("Research", "1BAF7A", "🔎", {"WebSearch", "WebFetch"},
     ("mcp__alphaXiv__", "mcp__claude_ai__read_conversation", "mcp__claude_ai__conversation_search",
      "mcp__Exa__", "mcp__Context7__", "mcp__Elicit__")),
    ("Delivery", "EDA100", "📦", {"SendUserFile", "SendUserMessage", "Artifact", "ArtifactData",
                                 "ArtifactComments", "propose_skills"}, ()),
    ("Repo & device", "E87BA4", "🔌", set(),
     ("mcp__claude-code-remote__", "mcp__remote-devices__", "mcp__github__", "mcp__GitHub")),
    ("Planning & meta", "008300", "🧭", {"TaskCreate", "TaskUpdate", "TaskGet", "TaskList", "ToolSearch",
                                         "Skill", "Agent", "AskUserQuestion", "SendMessage"}, ()),
    ("Memory", "4A3AA7", "🧠", set(), ("mcp__memory__",)),
]
OTHER_FAMILY = ("Other", "898781", "•")


def family_of(tool: str) -> str:
    """Map a tool name to its family name. Unknown tools fall to 'Other'."""
    for name, _colour, _icon, exact, prefixes in FAMILIES:
        if tool in exact or any(tool.startswith(p) for p in prefixes):
            return name
    return OTHER_FAMILY[0]


def short_tool(tool: str) -> str:
    """mcp__server__tool → server·tool, for readable charts."""
    if not tool.startswith("mcp__"):
        return tool
    parts = tool.split("__")
    return f"{parts[1]}·{parts[-1]}" if len(parts) >= 3 else tool


# ── Call outcomes ────────────────────────────────────────────────────────
# Status palette (dataviz): a status colour never appears without its icon
# and label. `source` says how the outcome is known.
OUTCOMES = [
    # (outcome, colour, icon, label, meaning)
    ("ok", "0CA30C", "✅", "OK", "Result recorded; no error flag and no error signature in the output."),
    ("error", "D03B3B", "❌", "Error (flagged)", "The tool itself flagged the result as an error."),
    ("error_unflagged", "EC835A", "⚠️", "Error (unflagged)",
     "The tool reported success, but the output carries an error signature (e.g. a pipe masked the exit code)."),
    ("attested_fail", "FAB219", "🟡", "Failed (attested)",
     "No result recorded, but a log, a later call's description or a reply says this call failed."),
    ("unrecorded", "C3C2B7", "❔", "Unrecorded", "The source keeps the call but not its result."),
]
OUTCOME_KEYS = [o[0] for o in OUTCOMES]

# Error signatures scanned in tool output. Anchored to line starts or exact
# phrases so that words like "error_summary" or "total_errors: 0" don't match.
ERROR_SIGNATURES = [
    ("python-traceback", r"^Traceback \(most recent call last\)"),
    ("python-exception", r"^\w*(Error|Exception): \S"),
    ("git-fatal", r"^fatal: "),
    ("http-status", r"returned error: [45]\d\d|\b(403 Forbidden|404 Not Found|429 Too Many)"),
    ("proxy-denied", r"access denied by the git proxy"),
    ("npm-error", r"^npm (ERR!|error) "),
    ("command-not-found", r"command not found"),
    ("no-such-file", r"No such file or directory"),
    ("permission-denied", r"Permission denied|Operation not permitted"),
    ("output-too-large", r"exceeds maximum allowed tokens"),
    ("test-failure", r"^\s*(FAIL|×|✗) "),
    ("tool-error", r"^<tool_use_error>|^Error: "),
]
_COMPILED = [(name, re.compile(rx, re.M)) for name, rx in ERROR_SIGNATURES]


def scan_errors(text: str) -> tuple[str, str]:
    """Return (signature name, matching line) for the first error signature, or ("", "")."""
    if not text:
        return "", ""
    for name, rx in _COMPILED:
        m = rx.search(text)
        if m:
            start = text.rfind("\n", 0, m.start()) + 1
            end = text.find("\n", m.end())
            return name, text[start: end if end != -1 else None].strip()[:300]
    return "", ""


# ── Failures ─────────────────────────────────────────────────────────────
LAYERS = [
    # (layer, colour, icon, meaning) — categorical slots 1–6
    ("environment", "2A78D6", "🌐", "Missing dependency, permission, unreachable device, version mismatch."),
    ("tool-use", "EB6834", "🔧", "The call itself was wrong: bad API name, self-matching kill, masked exit code."),
    ("artifact", "1BAF7A", "🖼️", "A defect in the thing being made: geometry, contrast, layout."),
    ("claim", "EDA100", "💬", "A sentence that said more than was checked: overstatement, stale description."),
    ("perception", "E87BA4", "👁️", "Looking was wrong: a false alarm or a misleading capture."),
    ("process", "008300", "🔁", "How the work was run: lost evidence, wrong-level fixes, unasked decisions."),
    ("record", "4A3AA7", "🗂️", "The record of the session itself: summaries, memory of what was said."),
]
DETECTIONS = [
    # (method, icon, meaning) — what actually caught it
    ("error-flag", "❌", "The tool's own error flag."),
    ("output-read", "📜", "Reading the tool's output."),
    ("render-look", "🖼️", "Rendering and looking."),
    ("second-engine", "🔀", "A second renderer or environment disagreed."),
    ("measure", "📏", "A number: pixels, contrast, counts, a readback."),
    ("reread", "🔁", "Re-reading a claim against the artifact or source."),
    ("gate", "🚦", "A test, build or docs gate."),
    ("probe", "🧪", "An adversarial probe of a 'done' claim."),
    ("linter", "📐", "A purpose-built linter."),
    ("person", "🧑", "The person you were working with, or another human."),
]
DETECTED_BY = ["self", "tool", "harness", "person"]
CAUGHT = [("before-delivery", "🛡️"), ("after-delivery", "🚨")]
SEVERITY = {1: "Low — noise or cosmetic", 2: "Medium — wrong output, caught", 3: "High — would ship, or shipped, a false claim or broken page"}
STATUSES = ["fixed", "open", "accepted", "false-alarm"]
LINK_BASIS = [
    ("observed", "The call's own recorded result shows it."),
    ("log", "A build log written during the work names it."),
    ("description-chain", "The next call's description (retry / see why / rebuild) implies it."),
    ("reply", "Claude's reply text says it."),
    ("summary", "Only the post-compaction summary says it. Weakest basis: a reconstruction."),
]

OPEN_STATUSES = [("Open", "🔴"), ("Decision needed", "🟠"), ("Unverified", "🟡"), ("Idea", "💡"), ("Done", "🟢")]
PROVENANCE = [
    ("Verbatim", "Copied exactly from the conversation, a log or tool output."),
    ("Log", "From a build log or note written during the work."),
    ("Reply", "From Claude's reply text in the conversation."),
    ("Tool", "From the tool-call record, git or a file listing."),
    ("Summary", "Condensed by Claude afterwards. Check the source before quoting."),
]


# ── Lookup maps (derived once; renderers read these, never the tuples) ──
FAMILY_COLOUR = {f[0]: f[1] for f in FAMILIES} | {OTHER_FAMILY[0]: OTHER_FAMILY[1]}
FAMILY_ICON = {f[0]: f[2] for f in FAMILIES} | {OTHER_FAMILY[0]: OTHER_FAMILY[2]}
OUTCOME_COLOUR = {o[0]: o[1] for o in OUTCOMES}
OUTCOME_ICON = {o[0]: o[2] for o in OUTCOMES}
OUTCOME_LABEL = {o[0]: o[3] for o in OUTCOMES}
LAYER_COLOUR = {l[0]: l[1] for l in LAYERS}
LAYER_ICON = {l[0]: l[2] for l in LAYERS}
DETECTION_ICON = {d[0]: d[1] for d in DETECTIONS}
CAUGHT_ICON = dict(CAUGHT)
OPEN_STATUS_ICON = dict(OPEN_STATUSES)
