#!/usr/bin/env python3
"""Deterministic CLAUDE.md staleness scan. Usage: scan.py <workspace-root>
Flags dead path refs, stale roots, old model strings, and dates. Verify hits
by hand — shorthand component refs and enum-like tokens are false positives."""
import re, os, sys, glob

root = sys.argv[1] if len(sys.argv) > 1 else "."
os.chdir(root)
files = sorted(glob.glob("*/*/CLAUDE.md") + glob.glob("CLAUDE.md"))

CHECKS = [
    (r"🚀 PROJECTS", "old root 🚀 PROJECTS"),
    (r"submodule", "submodule-era reference"),
    (r"claude-3|claude 3|sonnet[- ]3|opus[- ]3|haiku[- ]3", "old Claude model gen"),
]

for f in files:
    txt = open(f).read()
    repo_dir = os.path.dirname(f) or "."
    issues = []
    for pat, label in CHECKS:
        hits = [i + 1 for i, l in enumerate(txt.splitlines()) if re.search(pat, l)]
        if hits:
            issues.append(f"{label}: lines {hits[:6]}")
    dead = sorted(
        m for m in set(re.findall(r"`([\w./-]+/[\w./-]+)`", txt))
        if not m.startswith(("http", "~", "/"))
        and not os.path.exists(os.path.join(repo_dir, m)) and not os.path.exists(m)
    )
    if dead:
        issues.append("dead path refs (verify each): " + ", ".join(dead[:8]))
    dates = re.findall(r"(?:Last updated|Updated|reconciled)[:\s·]*(\d{4}-\d{2}-\d{2})", txt)
    tag = f", dated {dates[-1]}" if dates else ""
    print(f"\n## {f}  ({len(txt.splitlines())} lines{tag})")
    print("   clean" if not issues else "\n".join(f"   - {i}" for i in issues))

home_claude = os.path.expanduser("~/.claude/CLAUDE.md")
print(f"\n## ~/.claude/CLAUDE.md: {'EXISTS' if os.path.exists(home_claude) else 'MISSING — critical, reconstruct it'}")
