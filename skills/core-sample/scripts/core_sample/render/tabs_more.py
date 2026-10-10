"""The remaining data tabs: exchanges, findings, sources, deliverables, open items,
events, and the data dictionary. Same anatomy as tables.py; side effects only on
the workbook passed in."""
from collections import Counter

from openpyxl.worksheet.datavalidation import DataValidation

from .. import taxonomy as T
from . import styles as S
from .tables import FIRST, chip_by, col_letter, link_to, tint_rows_by, url_link, write_table

def set_colours(findings) -> dict:
    """Finding sets take categorical slots in order of first appearance (never by rank)."""
    order = list(dict.fromkeys(f["set"] for f in findings))
    return {s: T.FAMILIES[i % len(T.FAMILIES)][1] for i, s in enumerate(order)}
OPEN_COLOUR = {"Open": "D03B3B", "Decision needed": "EC835A", "Unverified": "FAB219", "Idea": "898781", "Done": "0CA30C"}


def exchanges_tab(wb, exchanges, calls_by_ex, pos):
    spec = [
        ("Exchange", lambda r: r["exchange"], 9, link_to("Tool Calls", pos["first_call"], "exchange")),
        ("Time", lambda r: r["at_local"], 7, None),
        ("Who asked", lambda r: ("🪝 " if r["initiator"] == "Harness" else "🧑 ") + r["initiator"], 12, None),
        ("Kind", lambda r: r["kind"], 11, None),
        ("Prompt (verbatim)", lambda r: r["prompt"], 60, None),
        ("Response", lambda r: r["response_summary"], 60, None),
        ("Outputs", lambda r: r["outputs"], 30, None),
        ("Tool calls", lambda r: f'=COUNTIF(\'Tool Calls\'!${pos["calls_ex_col"]}:${pos["calls_ex_col"]},"{r["exchange"]}")', 9, None),
        ("Failures begun here", lambda r: f'=COUNTIF(Failures!${pos["fail_ex_col"]}:${pos["fail_ex_col"]},"{r["exchange"]}")', 10, None),
    ]
    ws = write_table(wb, "Exchanges", "💬 Exchanges — each prompt and what came back",
                     "Prompts are verbatim. Responses are Claude's one-paragraph summaries. Click an exchange id to jump "
                     "to its first tool call.", spec, exchanges, "ledger", "tblExchanges")
    for i, r in enumerate(exchanges):
        if r["initiator"] != "Harness":
            ws.cell(row=FIRST + i, column=5).fill = S.fill(S.tint(S.GOLD, 0.85))
    return spec


def findings_tab(wb, findings):
    spec = [
        ("Finding", lambda r: r["finding_id"], 8, None),
        ("Set", lambda r: r["set"], 15, chip_by(set_colours(findings), "set")),
        ("Ref", lambda r: r["ref"], 16, None),
        ("Subject", lambda r: r["subject"], 40, None),
        ("Detail", lambda r: r["detail"], 56, None),
        ("How found", lambda r: r["how_found"], 26, None),
        ("Resolution", lambda r: r["resolution"], 40, None),
        ("Status", lambda r: r["status"], 16, None),
        ("Exchange", lambda r: r["exchange"], 9, None),
    ]
    write_table(wb, "Findings", "🔍 Findings — defects in the work itself",
                "Sets: " + ", ".join(f"{s} ({n})" for s, n in Counter(f["set"] for f in findings).items()) + ". Filter by Set.",
                spec, findings, "work", "tblFindings")


def sources_tab(wb, sources):
    spec = [
        ("Source", lambda r: r["source_id"], 7, None),
        ("Title", lambda r: r["title"], 40, None),
        ("Year", lambda r: r["year"], 6, None),
        ("Link", lambda r: r["url"], 36, url_link),
        ("Key finding", lambda r: r["finding"], 56, None),
        ("Bearing on the essay", lambda r: r["bearing"], 40, None),
        ("How checked", lambda r: r["checked"], 22, None),
    ]
    ws = write_table(wb, "Sources", "📚 Sources — and how far each was actually read",
                     "'Not read' and 'Excluded' rows are kept so nothing looks more checked than it was.",
                     spec, sources, "work", "tblSources")
    tint_rows_by(ws, spec, "How checked", {"Not read": "FAB219", "Excluded": "898781"}, len(sources))


def deliverables_tab(wb, rows):
    spec = [
        ("Id", lambda r: r["deliverable_id"], 6, None),
        ("Name", lambda r: r["name"], 52, None),
        ("Version", lambda r: r["version"], 8, None),
        ("Type", lambda r: r["type"], 24, None),
        ("Where it went", lambda r: r["destination"], 52, url_link),
        ("Exchange", lambda r: r["exchange"], 9, None),
    ]
    write_table(wb, "Deliverables", "📦 Deliverables — every file, artifact, commit and branch",
                "Semantic versions; names are taxonomy-based.", spec, rows, "work", "tblDeliverables")


def open_items_tab(wb, rows):
    spec = [
        ("", lambda r: dict(T.OPEN_STATUSES).get(r["status"], ""), 4, None),
        ("Item", lambda r: r["item"], 52, None),
        ("Kind", lambda r: r["kind"], 14, None),
        ("Status", lambda r: r["status"], 16, None),
        ("Owner", lambda r: r["owner"], 9, None),
        ("Next action", lambda r: r["next_action"], 52, url_link),
        ("From", lambda r: r["exchange"], 8, None),
    ]
    ws = write_table(wb, "Open Items", "✅ Open items — what's left, and whose it is",
                     "Edit Status from its dropdown; row colour and the index counts follow.", spec, rows, "action", "tblOpen")
    col = col_letter(spec, "Status")
    dv = DataValidation(type="list", formula1='"' + ",".join(s for s, _ in T.OPEN_STATUSES) + '"', allow_blank=True)
    dv.add(f"{col}{FIRST}:{col}{FIRST + len(rows) + 200}")
    ws.add_data_validation(dv)
    tint_rows_by(ws, spec, "Status", OPEN_COLOUR, len(rows))


def events_tab(wb, events):
    spec = [
        ("At (UTC)", lambda r: r["at_utc"], 26, None),
        ("Kind", lambda r: r["kind"], 13, None),
        ("Exchange", lambda r: r["exchange"], 9, None),
        ("Text (first 400 characters)", lambda r: r["text"], 100, None),
    ]
    write_table(wb, "Events", "⏱ Events — what entered the context besides prompts",
                "Compaction, stop hooks, skill loads. Compaction is where the transcript lost its earlier tool results.",
                spec, events, "ledger", "tblEvents")
