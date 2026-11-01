#!/usr/bin/env python3
"""Deterministic CLAUDE.md staleness scan. Usage: scan.py [--json] <root>
Flags dead path refs, stale roots, old model strings, and dates. Verify hits
by hand: shorthand component refs and enum-like tokens are false positives.

<root> is the workspace (scans <root>/CLAUDE.md and <root>/*/*/CLAUDE.md) or a
single project. The SessionStart drift hook runs this unattended against
whatever repository a session opens, so the repository is untrusted input:
  - only regular, non-symlinked files whose real path stays inside <root> are
    read, capped at MAX_BYTES and decoded with errors="replace";
  - paths are escaped before printing, so a file or directory name can't
    start a line of its own (forging a finding);
  - --json emits structured findings for machine consumers; the hook parses
    that, never the human-readable text."""
import glob
import json
import os
import re
import sys

MAX_BYTES = 1 << 20     # a CLAUDE.md is a few KB; anything bigger is not one

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


def escape(s):
    """Render a repository-controlled string on one line: control and format
    characters (newline, CR, bidi overrides, zero-width) become escapes."""
    return "".join(c if c.isprintable() else ascii(c)[1:-1] for c in s)


def unsafe_reason(rel, root_real):
    """Why <rel> must not be read, or None if it is safe. Symlinks are refused
    at every component, so neither a symlinked CLAUDE.md (to /dev/zero, a
    FIFO, or a file elsewhere) nor a symlinked directory is followed."""
    parts = rel.split(os.sep)
    for i in range(1, len(parts) + 1):
        if os.path.islink(os.path.join(*parts[:i])):
            return "symlink"
    real = os.path.realpath(rel)
    if os.path.commonpath([real, root_real]) != root_real:
        return "outside root"
    if not os.path.isfile(real):
        return "not a regular file"
    if os.path.getsize(real) > MAX_BYTES:
        return "over size cap"
    return None


def read_text(rel):
    with open(rel, encoding="utf-8", errors="replace") as fh:
        return fh.read(MAX_BYTES)


def scan_file(rel):
    txt = read_text(rel)
    repo_dir = os.path.dirname(rel) or "."
    issues = []
    lines = txt.splitlines()
    for pat, label in CHECKS:
        hits = [i + 1 for i, l in enumerate(lines) if re.search(pat, l)]
        if hits:
            issues.append({"kind": "pattern", "label": label, "lines": hits[:6]})
    dead = sorted(
        m for m in set(re.findall(r"`([\w./-]+/[\w./-]+)`", txt))
        if not m.startswith(("http", "~", "/"))
        and not os.path.exists(os.path.join(repo_dir, m)) and not os.path.exists(m)
        and not not_a_path_claim(m, repo_dir)
    )
    if dead:
        issues.append({"kind": "dead_paths", "tokens": dead[:8]})
    dates = re.findall(r"(?:Last updated|Updated|reconciled)[:\s·]*(\d{4}-\d{2}-\d{2})", txt)
    return {"path": rel, "lines": len(lines), "date": dates[-1] if dates else None,
            "issues": issues}


def scan(root):
    os.chdir(root)
    root_real = os.path.realpath(".")
    out = []
    for rel in sorted(glob.glob("*/*/CLAUDE.md") + glob.glob("CLAUDE.md")):
        reason = unsafe_reason(rel, root_real)
        if reason:
            out.append({"path": rel, "skipped": reason, "issues": []})
        else:
            out.append(scan_file(rel))
    return out


def issue_text(i):
    if i["kind"] == "pattern":
        return f"{i['label']}: lines {i['lines']}"
    return "dead path refs (verify each): " + ", ".join(i["tokens"])


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    root = args[0] if args else "."
    files = scan(root)
    if as_json:
        print(json.dumps({"root": os.path.realpath("."), "files": files}))
        return
    for f in files:
        if "skipped" in f:
            print(f"\n## {escape(f['path'])}  (skipped: {f['skipped']})")
            continue
        tag = f", dated {f['date']}" if f["date"] else ""
        print(f"\n## {escape(f['path'])}  ({f['lines']} lines{tag})")
        print("   clean" if not f["issues"]
              else "\n".join(f"   - {issue_text(i)}" for i in f["issues"]))
    home_claude = os.path.expanduser("~/.claude/CLAUDE.md")
    print(f"\n## ~/.claude/CLAUDE.md: {'EXISTS' if os.path.exists(home_claude) else 'MISSING — critical, reconstruct it'}")


if __name__ == "__main__":
    main(sys.argv[1:])
