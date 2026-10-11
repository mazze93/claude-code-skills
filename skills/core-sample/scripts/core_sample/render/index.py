"""The Index (front page) and the Dictionary.

Index anatomy, top to bottom: title band → six KPI tiles (live formulas) →
'Read this first' (generated takeaways) → where-to-go table (hyperlinks, live
row counts) → legends for every icon and colour used anywhere in the book.
Side effects: writes to the sheets passed in.
"""
from openpyxl.styles import Border, Side
from openpyxl.utils import get_column_letter

from .. import taxonomy as T
from . import styles as S
from .tables import FIRST

NAV = [
    # (icon, tab, what it answers)
    ("📊", "Charts", "Where the work went, what we can see of it, what failed and what caught it."),
    ("💬", "Exchanges", "Every prompt (verbatim) and what came back."),
    ("🧾", "Tool Calls", "Every tool call, its outcome, and how we know the outcome."),
    ("🚨", "Failures", "What went wrong, at which layer, what caught it, how late."),
    ("🔍", "Findings", "Defects in the work itself, by set."),
    ("📚", "Sources", "What was read, and how far."),
    ("📦", "Deliverables", "Everything delivered, with versions."),
    ("✅", "Open Items", "What's left, and whose it is."),
    ("⏱", "Events", "Compaction, hooks and other context injections."),
    ("📖", "Dictionary", "What every column means and which values it allows."),
    ("🧮", "Chart Data", "The numbers behind every chart (live formulas)."),
]


def kpi_tiles(ws, row, tiles):
    """tiles: [(label, formula, caption, colour, number_format)] — two columns each, from column B."""
    for i, (label, formula, caption, colour, fmt) in enumerate(tiles):
        c1 = 2 + i * 2
        for r in range(row, row + 3):
            ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c1 + 1)
            for c in (c1, c1 + 1):
                ws.cell(row=r, column=c).fill = S.fill(S.tint(colour, 0.9))
        top = ws.cell(row=row, column=c1, value=label.upper())
        top.font, top.alignment = S.font(8, True, S.INK_2), S.LEFT_MID
        for c in (c1, c1 + 1):
            ws.cell(row=row, column=c).border = Border(top=Side(style="thick", color=colour))
        val = ws.cell(row=row + 1, column=c1, value=formula)
        val.font, val.alignment, val.number_format = S.font(24, True, S.NAVY), S.LEFT_MID, fmt
        cap = ws.cell(row=row + 2, column=c1, value=caption)
        cap.font, cap.alignment = S.font(8, italic=True, color=S.INK_2), S.WRAP
    ws.row_dimensions[row + 1].height, ws.row_dimensions[row + 2].height = 34, 30


def nav_table(ws, row, counts):
    ws.cell(row=row, column=2, value="Where to go").font = S.H_SECTION
    for col, text in ((2, ""), (3, "Tab"), (4, ""), (5, "What it answers"), (10, "Rows")):
        h = ws.cell(row=row + 1, column=col, value=text)
        h.font, h.fill = S.HEAD_FONT, S.HEAD_FILL
    for col in range(6, 10):
        ws.cell(row=row + 1, column=col).fill = S.HEAD_FILL
    for i, (icon, tab, what) in enumerate(NAV):
        r = row + 2 + i
        ws.cell(row=r, column=2, value=icon).alignment = S.CENTER
        link = ws.cell(row=r, column=3, value=tab)
        link.hyperlink, link.font = f"#'{tab}'!A1", S.font(11, True, "1C5CAB")
        ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=9)
        ws.cell(row=r, column=5, value=what).font = S.font(10)
        ws.cell(row=r, column=10, value=counts.get(tab, "")).font = S.font(10, True)
    return row + 3 + len(NAV)


def legend(ws, row, title, items):
    """items: [(icon, label, meaning, colour|None)]. Returns the next free row."""
    ws.cell(row=row, column=2, value=title).font = S.H_SECTION
    for i, (icon, label, meaning, colour) in enumerate(items, start=1):
        r = row + i
        ws.cell(row=r, column=2, value=icon).alignment = S.CENTER
        tag = ws.cell(row=r, column=3, value=label)
        if colour:
            S.chip(tag, colour)
        ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=13)
        m = ws.cell(row=r, column=5, value=meaning)
        m.font, m.alignment = S.font(9, color=S.INK_2), S.LEFT_MID
    return row + len(items) + 2


def build_index(ws, tables, tiles, headlines, counts):
    session = tables["sessions"][0]
    ws.sheet_properties.tabColor = S.TAB_GROUP["overview"]
    S.band(ws, f"{session['title']} — session core sample",
           f"{session.get('chat_title', '')} · {session['date']} · ledger built {session['as_of']}", 14, back_link=False)
    S.set_widths(ws, [2, 6, 18, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 2])
    kpi_tiles(ws, 4, tiles)
    ws.cell(row=8, column=2, value="Read this first").font = S.H_SECTION
    for i, text in enumerate(headlines):
        ws.merge_cells(start_row=9 + i, start_column=2, end_row=9 + i, end_column=13)
        c = ws.cell(row=9 + i, column=2, value=f"▸  {text}")
        c.font, c.alignment = S.font(10, color=S.INK), S.LEFT_MID
        ws.row_dimensions[9 + i].height = 30
    row = nav_table(ws, 10 + len(headlines), counts)
    row = legend(ws, row, "Tool-call outcomes",
                 [(o[2], o[3], o[4], o[1]) for o in T.OUTCOMES])
    row = legend(ws, row, "Failure layers", [(l[2], l[0], l[3], l[1]) for l in T.LAYERS])
    row = legend(ws, row, "What caught a failure", [(d[1], d[0], d[2], None) for d in T.DETECTIONS])
    row = legend(ws, row, "How a failure is tied to a call", [("🔗", b, m, None) for b, m in T.LINK_BASIS])
    row = legend(ws, row, "Tool families (chart colours)",
                 [(f[2], f[0], ", ".join(sorted(f[3])) or ", ".join(f[4]), f[1]) for f in T.FAMILIES])
    if session.get("notes"):
        ws.cell(row=row, column=2, value="About this record").font = S.H_SECTION
        ws.merge_cells(start_row=row + 1, start_column=2, end_row=row + 1, end_column=13)
        note = ws.cell(row=row + 1, column=2, value=session["notes"])
        note.font, note.alignment = S.font(9, italic=True, color=S.INK_2), S.WRAP
        ws.row_dimensions[row + 1].height = 48
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation, ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = "landscape", 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


DICTIONARY = [
    ("tool_calls", "call_id", "Exchange id + sequence within the exchange, e.g. E04-018.", ""),
    ("tool_calls", "outcome", "What happened to the call.", ", ".join(T.OUTCOME_KEYS)),
    ("tool_calls", "outcome_source", "How the outcome is known.", "tool-flag, output-scan, a link basis, none"),
    ("tool_calls", "record_source", "Which raw source holds the call.", "export, manual, transcript, hook"),
    ("tool_calls", "error_signature", "First error pattern found in the output (Bash/remote only, or a leading 'Error:').",
     ", ".join(s for s, _ in T.ERROR_SIGNATURES)),
    ("tool_calls", "family", "Tool family; fixes the chart colour.", ", ".join(f[0] for f in T.FAMILIES) + ", Other"),
    ("failures", "layer", "Where the failure lives.", ", ".join(l[0] for l in T.LAYERS)),
    ("failures", "detection", "What caught it.", ", ".join(d[0] for d in T.DETECTIONS)),
    ("failures", "detected_by", "Who caught it.", ", ".join(T.DETECTED_BY)),
    ("failures", "caught", "Before or after a deliverable carried it to the person.", ", ".join(c[0] for c in T.CAUGHT)),
    ("failures", "severity", "1 noise · 2 wrong output, caught · 3 would ship a false claim or broken page.", "1, 2, 3"),
    ("failures", "exchanges_to_detect", "Detected-in exchange minus happened-in exchange.", "integer ≥ 0"),
    ("failures", "link_basis", "How firmly the failure is tied to its call.", ", ".join(b for b, _ in T.LINK_BASIS)),
    ("failures", "status", "Where it stands.", ", ".join(T.STATUSES)),
    ("exchanges", "prompt_provenance", "Verbatim when copied from the transcript or export.", ", ".join(p for p, _ in T.PROVENANCE)),
    ("open_items", "status", "Editable from the dropdown.", ", ".join(s for s, _ in T.OPEN_STATUSES)),
]


def build_dictionary(wb):
    from .tables import write_table
    rows = [dict(zip(("table", "column", "meaning", "values"), r)) for r in DICTIONARY]
    spec = [("Table", lambda r: r["table"], 14, None), ("Column", lambda r: r["column"], 20, None),
            ("Meaning", lambda r: r["meaning"], 70, None), ("Allowed values", lambda r: r["values"], 70, None)]
    write_table(wb, "Dictionary", "📖 Dictionary — what every coded column means",
                "The same vocabularies the build validates against: an unknown value fails the build, loudly.",
                spec, rows, "reference", "tblDictionary")
