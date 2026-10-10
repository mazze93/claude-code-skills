"""Persist a ledger: SQLite (for analysis across sessions) and CSV (for anything else).

Side effects: writes the database file and a folder of CSVs. Re-running for the
same session replaces that session's rows only, so one database accumulates
every session you capture.
"""
import csv
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def write_sqlite(tables: dict, db_path: Path) -> None:
    """Upsert one session's tables into db_path (created with schema.sql if new)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    session_id = tables["sessions"][0]["session_id"]
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA.read_text())
        # Existing cross-session ledgers predate tool-use provenance fields.
        # Migrate in place rather than silently dropping evidence on INSERT.
        columns = _columns(conn, "tool_calls")
        for column in ("tool_use_id", "evidence_sources"):
            if column not in columns:
                conn.execute(f'ALTER TABLE tool_calls ADD COLUMN "{column}" TEXT')
        for table, rows in tables.items():
            cols = _columns(conn, table)
            conn.execute(f'DELETE FROM "{table}" WHERE session_id = ?', (session_id,))
            if not rows:
                continue
            placeholders = ", ".join("?" for _ in cols)
            quoted = ", ".join(f'"{c}"' for c in cols)
            conn.executemany(f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})',
                             [tuple(r.get(c) for c in cols) for r in rows])


def write_csvs(tables: dict, out_dir: Path) -> list[Path]:
    """One CSV per table, columns in schema order. Returns the paths written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(":memory:") as conn:
        conn.executescript(SCHEMA.read_text())
        written = []
        for table, rows in tables.items():
            cols = _columns(conn, table)
            path = out_dir / f"{table}.csv"
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
            written.append(path)
    return written
