"""The questions the workbook answers, as Chart Data blocks + charts + takeaways.

Takeaways are generated from the same ledger the formulas read, so the sentence
and the chart can't disagree. Side effects: writes to the two sheets passed in.
"""
from collections import Counter

from .. import taxonomy as T
from . import charts as C

FAMILIES = [f[0] for f in T.FAMILIES]
OUTCOMES = T.OUTCOME_KEYS
LAYERS = [l[0] for l in T.LAYERS]
TTD_BUCKETS = [("same exchange", 0, 0), ("1 later", 1, 1), ("2–3 later", 2, 3), ("4+ later", 4, 999)]


def _rng(sheet, col):
    return f"'{sheet}'!${col}:${col}"


def q_work_by_exchange(B, cols, tables):
    ex = [e["exchange"] for e in tables["exchanges"]]
    rows = [[e] + [f'=COUNTIFS({_rng("Tool Calls", cols["c_ex"])},$A{{r}},{_rng("Tool Calls", cols["c_fam"])},"*"&{h}{{hdr}})'
                   for h in "BCDEFGH"] for e in ex]
    block = _materialise(B, "work", "Tool calls per exchange, by family", ["Exchange"] + FAMILIES, rows)
    per = Counter(c["exchange"] for c in tables["tool_calls"])
    top = per.most_common(1)[0]
    talk = sum(1 for e in ex if per.get(e, 0) == 0)
    return block, (f"{top[0]} alone holds {top[1]} of {len(tables['tool_calls'])} calls. "
                   f"{talk} of {len(ex)} exchanges used no tools at all: conversation, not work.")


def q_visibility(B, cols, tables):
    ex = [e["exchange"] for e in tables["exchanges"]]
    rows = [[e] + [f'=COUNTIFS({_rng("Tool Calls", cols["c_ex"])},$A{{r}},{_rng("Tool Calls", cols["c_out"])},{h}{{hdr}})'
                   for h in "BCDEF"] for e in ex]
    block = _materialise(B, "visibility", "Tool calls per exchange, by what we know of the result",
                         ["Exchange"] + OUTCOMES, rows)
    calls = tables["tool_calls"]
    unrec = [c for c in calls if c["outcome"] == "unrecorded"]
    blind = Counter(c["record_source"] for c in unrec).most_common()
    where = ", ".join(f"{n} from {src}" for src, n in blind) or "none"
    return block, (f"{len(unrec)} of {len(calls)} calls ({len(unrec) / len(calls):.0%}) have no recorded result ({where}). "
                   f"Every grey bar is a call whose result nobody can check now.")


def q_tools(B, cols, tables):
    counts = Counter(c["tool_short"] for c in tables["tool_calls"]).most_common(12)
    rows = [[t, f'=COUNTIF({_rng("Tool Calls", cols["c_tool"])},$A{{r}})'] for t, _ in counts]
    block = _materialise(B, "tools", "Top 12 tools by calls", ["Tool", "Calls"], rows)
    total = len(tables["tool_calls"])
    share = (counts[0][1] + counts[1][1]) / total
    fams = Counter(c["family"] for c in tables["tool_calls"]).most_common(2)
    return block, (f"{counts[0][0]} and {counts[1][0]} carry {share:.0%} of all calls; by family, "
                   f"{fams[0][0]} ({fams[0][1]}) and {fams[1][0]} ({fams[1][1]}) lead.")


def q_layers(B, cols, tables):
    caught = [c[0] for c in T.CAUGHT]
    rows = [[l] + [f'=COUNTIFS({_rng("Failures", cols["f_layer"])},"*"&$A{{r}},{_rng("Failures", cols["f_when"])},"*"&{h}{{hdr}})'
                   for h in "BC"] for l in LAYERS]
    block = _materialise(B, "layers", "Failures by layer and when they were caught", ["Layer"] + caught, rows)
    f = tables["failures"]
    late = [x for x in f if x["caught"] == "after-delivery"]
    late_layers = Counter(x["layer"] for x in late).most_common(2)
    lead = " and ".join(f"{l} ({n})" for l, n in late_layers) or "none"
    return block, f"{len(late)} of {len(f)} failures were caught only after delivery; the largest layers among them: {lead}."


def q_detection(B, cols, tables):
    counts = Counter(x["detection"] for x in tables["failures"]).most_common()
    rows = [[d, f'=COUNTIF({_rng("Failures", cols["f_det"])},"*"&$A{{r}})'] for d, _ in counts]
    block = _materialise(B, "detection", "What caught each failure", ["Detection", "Failures"], rows)
    flag = sum(1 for x in tables["failures"] if x["detection"] == "error-flag")
    rest = ", ".join(f"{d} ({n})" for d, n in counts if d != "error-flag")[:160]
    return block, f"The tool's own error flag caught {flag} of {len(tables['failures'])}. The rest: {rest}."


def q_latency(B, cols, tables):
    rng = _rng("Failures", cols["f_ttd"])
    rows = [[label, f'=COUNTIFS({rng},">={lo}",{rng},"<={hi}")'] for label, lo, hi in TTD_BUCKETS]
    block = _materialise(B, "latency", "Exchanges between a failure and its detection", ["Caught", "Failures"], rows)
    f = tables["failures"]
    same = sum(1 for x in f if x["exchanges_to_detect"] == 0)
    worst = max(f, key=lambda x: x["exchanges_to_detect"])
    return block, (f"{same} of {len(f)} failures were caught in the exchange they happened in. The slowest, "
                   f"{worst['failure_id']}, took {worst['exchanges_to_detect']} exchanges: {worst['summary'][:90]}…")


def _materialise(B, key, title, headers, rows):
    """Fill the {r} row and {hdr} header-row placeholders, then write the block."""
    first = B.row + 2
    head = B.row + 1
    out = []
    for i, row in enumerate(rows):
        r = first + i
        out.append([v.replace("{r}", str(r)).replace("{hdr}", f"${head}") if isinstance(v, str) else v for v in row])
    return B.add(key, title, headers, out)


FAILED_PREFIXES = ("failed", "partly failed", "overclaim")


def iteration_sets(tables) -> list[str]:
    """Finding sets whose refs are 'iter N' (a render/inspect loop worth charting)."""
    sets = Counter(f["set"] for f in tables["findings"] if str(f["ref"]).startswith("iter "))
    return [s for s, n in sets.items() if n >= 5]


def q_iterations(B, tables, set_name):
    rows_in = [f for f in tables["findings"] if f["set"] == set_name]
    rows, ok, bad, failed_at = [], 0, 0, []
    for f in rows_in:
        is_bad = f["status"].lower().startswith(FAILED_PREFIXES)
        ok, bad = ok + (not is_bad), bad + is_bad
        failed_at += [f["ref"].replace("iter ", "")] if is_bad else []
        rows.append([f["ref"].replace("iter ", ""), ok, bad])
    block = B.add(f"iter-{set_name}", f"{set_name}: cumulative accepted vs failed (computed at build)",
                  ["Iter", "Accepted", "Failed"], rows)
    return block, (f"{bad} of {len(rows_in)} iterations failed; failures at {', '.join(failed_at)}. "
                   f"A flat red line means the loop stopped producing failures.")


HOW_FOUND = [("composite only", ("composite",)), ("zoomed crop", ("crop", "zoom")), ("measured", ("measur", "computed")),
             ("render", ("render",)), ("linter", ("linter",)), ("reading", ("read", "code"))]


def bucket(how: str) -> str:
    low = how.lower()
    return next((label for label, needles in HOW_FOUND if any(n in low for n in needles)), "other")


def q_how_found(B, tables, set_name):
    defects = [f for f in tables["findings"] if f["set"] == set_name and f["status"] != "false-alarm"]
    counts = Counter(bucket(f["how_found"]) for f in defects)
    rows = [[label, counts.get(label, 0)] for label, _ in HOW_FOUND + [("other", ())] if counts.get(label)]
    block = B.add(f"how-{set_name}", f"{set_name}: defects by how they were found (computed at build)",
                  ["How found", "Defects"], rows)
    top, n = counts.most_common(1)[0]
    return block, f"{n} of {len(defects)} {set_name} defects were found by: {top}."


def q_time(B, cols, tables):
    rows = [[fam, f'=SUMIFS({_rng("Tool Calls", cols["c_sec"])},{_rng("Tool Calls", cols["c_fam"])},"*"&$A{{r}})']
            for fam in FAMILIES]
    block = _materialise(B, "time", "Seconds of tool time by family (calls with a recorded duration)",
                         ["Family", "Seconds"], rows)
    timed = [c for c in tables["tool_calls"] if c["duration_s"]]
    by = Counter()
    for c in timed:
        by[c["family"]] += c["duration_s"]
    top = by.most_common(1)[0] if by else ("—", 0)
    return block, (f"Only {len(timed)} calls carry a duration (the transcript part). Of their "
                   f"{sum(by.values()) / 60:.0f} minutes, {top[0]} took {top[1] / 60:.0f}.")
