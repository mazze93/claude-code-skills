#!/usr/bin/env python3
"""Refuse a commit that silently restores an older version of a file.

    python3 scripts/check_revert.py            # staged files
    python3 scripts/check_revert.py --all      # working tree

This is the guard for the failure that produced it. On 2026-08-31 a skill
install wrote through a symlink into this repo and replaced two consolidated
SKILL.md files with their pre-consolidation copies. The result was a large,
plausible diff — one of them +149/-16 — that looked like substantial new work
and was in fact a revert of a 10-into-2 consolidation. It sat undetected for
six days and was caught only by hand, by searching git history for the exact
added strings.

A revert and a rewrite are indistinguishable by shape. They are trivially
distinguishable by provenance: if the incoming content is byte-identical to a
version this file already had, it is not new work.

Exit 0 clean, 1 if a staged file exactly matches an older commit of itself.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

LOOKBACK = 60          # commits per file; deep enough for a stale vendored copy


def sh(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout


def digest(text: str) -> str:
    return hashlib.blake2s(text.encode("utf-8", "replace"), digest_size=16).hexdigest()


def changed(all_files: bool) -> list[str]:
    cmd = ["git", "diff", "--name-only", "--diff-filter=M"]
    if not all_files:
        cmd.insert(2, "--cached")
    return [f for f in sh(*cmd).splitlines() if f.strip()]


def main(argv: list[str]) -> int:
    all_files = "--all" in argv
    hits: list[str] = []

    for path in changed(all_files):
        p = Path(path)
        if not p.is_file():
            continue
        try:
            incoming = digest(p.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue

        head = sh("git", "show", f"HEAD:{path}")
        if head and digest(head) == incoming:
            continue   # unchanged relative to HEAD

        for commit in sh("git", "log", f"-{LOOKBACK}", "--format=%H", "--", path).split():
            old = sh("git", "show", f"{commit}:{path}")
            if old and digest(old) == incoming:
                subject = sh("git", "log", "-1", "--format=%h %ad %s",
                             "--date=short", commit).strip()
                hits.append(f"{path}\n    is byte-identical to {subject}")
                break

    if not hits:
        print("ok — no staged file restores an older version of itself")
        return 0

    print("REVERT DETECTED — these changes restore content this file already had:\n")
    for h in hits:
        print(f"  {h}")
    print("""
That is not proof of a mistake — a deliberate revert looks the same. It is
proof that this is NOT new work, so the commit message should say so.

If an installer or sync wrote this over your changes, discard rather than
commit. Content that exists in git history is safe to discard; content that
exists nowhere else is not.

Override once with:  git commit --no-verify""")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
