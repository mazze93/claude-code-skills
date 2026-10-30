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

EXT = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,5}$")      # a file extension, not ".3" or "..."
DOMAIN = re.compile(r"^[\w-]+\.[a-z]{2,}$")             # github.com, ghcr.io, gcr.io


def not_a_path_claim(tok, repo_dir):
    """True for backticked tokens that can't be a claim about this repo's
    filesystem: owner/repo slugs, branch names, platforms, prose (try/catch),
    registry or domain refs, slash-separated enums. Structure-based: a token
    is dropped only if it has no file extension AND its first segment is not
    an existing directory here. Anything that could be a real path is kept."""
    if tok.endswith("/"):
        return False                                    # an explicit directory claim
    segs = tok.split("/")
    if DOMAIN.match(segs[0]):
        return True
    if os.path.isdir(os.path.join(repo_dir, segs[0])) or EXT.search(segs[-1]):
        return False
    return len(segs) == 2 or len(segs) >= 4


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
        and not not_a_path_claim(m, repo_dir)
    )
    if dead:
        issues.append("dead path refs (verify each): " + ", ".join(dead[:8]))
    dates = re.findall(r"(?:Last updated|Updated|reconciled)[:\s·]*(\d{4}-\d{2}-\d{2})", txt)
    tag = f", dated {dates[-1]}" if dates else ""
    print(f"\n## {f}  ({len(txt.splitlines())} lines{tag})")
    print("   clean" if not issues else "\n".join(f"   - {i}" for i in issues))

home_claude = os.path.expanduser("~/.claude/CLAUDE.md")
print(f"\n## ~/.claude/CLAUDE.md: {'EXISTS' if os.path.exists(home_claude) else 'MISSING — critical, reconstruct it'}")
