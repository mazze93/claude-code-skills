"""core-sample command line.

  init     scaffold a session folder (annotation templates)
  capture  copy raw sources (transcript, hook ledger, export pages) into the session
  build    validate → SQLite + CSVs + workbook
  query    run SQL against the ledger database (read-only)

Side effects are limited to the paths named on the command line.
"""
import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path

from .ledger import build_ledger
from .render import render_workbook
from .store import write_csvs, write_sqlite

TEMPLATES = {
    "session.json": {"session_id": "", "title": "", "chat_title": "", "chat_url": "", "timezone": "America/New_York",
                     "date": "", "project": "", "transcript_first_exchange": "E01", "transcript_exchange_offset": 1,
                     "notes": []},
    "exchanges.json": [], "calls_manual.json": [], "failures.json": [], "findings.json": [],
    "sources.json": [], "deliverables.json": [], "open_items.json": [],
}


def cmd_init(a) -> int:
    folder = Path(a.session)
    (folder / "raw" / "export").mkdir(parents=True, exist_ok=True)
    for name, body in TEMPLATES.items():
        p = folder / name
        if not p.exists():
            if name == "session.json":
                body = dict(body, session_id=folder.name, title=a.title or folder.name)
            p.write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8")
    print(f"scaffolded {folder}")
    return 0


def cmd_capture(a) -> int:
    raw = Path(a.session) / "raw"
    (raw / "export").mkdir(parents=True, exist_ok=True)
    if a.transcript:
        shutil.copy2(a.transcript, raw / "transcript.jsonl")
    if a.hook_ledger:
        shutil.copy2(a.hook_ledger, raw / "hook-ledger.jsonl")
    for page in a.export or []:
        shutil.copy2(page, raw / "export" / Path(page).name)
    print(f"captured into {raw}: " + ", ".join(sorted(p.name for p in raw.rglob("*") if p.is_file())))
    return 0


def cmd_build(a) -> int:
    tables = build_ledger(Path(a.session))
    sid = tables["sessions"][0]["session_id"]
    # "ledger", not "out": many repos .gitignore out/ and the record silently never commits.
    out = Path(a.out or Path(a.session) / "ledger")
    write_sqlite(tables, Path(a.db or out / "core-sample.sqlite"))
    write_csvs(tables, out / "csv")
    xlsx = render_workbook(tables, out / f"{sid}_session-record_v{a.version}.xlsx")
    print(json.dumps({k: len(v) for k, v in tables.items()}))
    print(f"workbook: {xlsx}")
    return 0


def cmd_query(a) -> int:
    with sqlite3.connect(f"file:{a.db}?mode=ro", uri=True) as conn:
        cur = conn.execute(a.sql)
        print("\t".join(d[0] for d in cur.description))
        for row in cur:
            print("\t".join("" if v is None else str(v) for v in row))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="core-sample", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init"); s.add_argument("session"); s.add_argument("--title")
    s = sub.add_parser("capture"); s.add_argument("session"); s.add_argument("--transcript")
    s.add_argument("--hook-ledger"); s.add_argument("--export", nargs="*")
    s = sub.add_parser("build"); s.add_argument("session"); s.add_argument("--out"); s.add_argument("--db")
    s.add_argument("--version", default="1.0.0")
    s = sub.add_parser("query"); s.add_argument("db"); s.add_argument("sql")
    a = p.parse_args(argv)
    try:
        return {"init": cmd_init, "capture": cmd_capture, "build": cmd_build, "query": cmd_query}[a.cmd](a)
    except ValueError as exc:        # validation failures: loud, specific, non-zero
        print(f"core-sample: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
