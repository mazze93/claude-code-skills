#!/usr/bin/env python3
"""Generate the marketplace from .claude-plugin/skill-map.json.

Everything this writes is derived. The map is the only file a human edits;
running this is idempotent, and `validate_marketplace.py` fails CI if the
generated artefacts drift from the map. That is the same regenerate-and-diff
discipline used for parity goldens elsewhere in the fleet: a generated file
that can be hand-edited is a generated file that will be.

Plugin skills are RELATIVE SYMLINKS back into skills/, not copies. Copies would
mean every skill exists twice in the tree, and the day the two disagree is the
day nobody can tell which one is loaded. Git stores symlinks, and relative ones
resolve correctly in a fresh clone.

Plugin VERSIONS are derived from content. Claude Code caches an installed
plugin under cache/<marketplace>/<plugin>/<version>/ and `claude plugin update`
replaces that copy only when the version string changes. A hardcoded "0.1.0"
therefore froze every install at its first download (rigor stayed at an
October copy that lacked three of its skills). Leaving `version` out does not
help here: Claude Code then uses the commit SHA of the plugin directory, and
plugins/<name>/skills/* are symlinks, so editing a SKILL.md never touches it.

So each plugin.json gets `<BASE_VERSION>-c<12 hex>`, where the hex is a SHA-256
over every file the plugin ships (read through the skill symlinks, only files
in the git index) plus the manifest itself minus `version`. It changes exactly
when the shipped content changes, needs no git history (so --check is stable
in CI and on a shallow clone), and is a semver prerelease rather than `+build`
metadata, so even a strict semver comparison sees two different versions.
The version lives in plugin.json only; the docs warn against setting it in
the marketplace entry as well (plugin.json silently wins).

    python3 scripts/build_marketplace.py [--check]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / ".claude-plugin" / "skill-map.json"
MARKET = ROOT / ".claude-plugin" / "marketplace.json"
PLUGINS = ROOT / "plugins"
# Bump by hand only to mark a deliberate change of scheme; day-to-day content
# changes move the hash suffix on their own.
BASE_VERSION = "0.2.0"
# Used only when git is unavailable (tarball): approximates .gitignore.
FALLBACK_SKIP = {".DS_Store", "__pycache__", "results"}


def shippable_files(root: Path = ROOT) -> set[str] | None:
    """Repo-relative paths in the git index: what a GitHub install can ship.

    Untracked files never reach users, so they must not move the version
    (a stray local file would otherwise make --check disagree with CI).
    Staged new files are in the index, so the pre-commit --check sees them.
    None if git is unavailable, in which case FALLBACK_SKIP is used instead.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached"],
            cwd=root, capture_output=True, timeout=30, check=True).stdout
    except Exception:
        return None
    return {p for p in out.decode("utf-8", "surrogateescape").split("\0") if p}


def content_hash(pdir: Path, manifest: dict, root: Path = ROOT,
                 shippable: set[str] | None = None) -> str:
    """SHA-256 over the plugin as it would be copied into the cache.

    Walks pdir following symlinks, skips the generated plugin.json (it holds
    the version, which would be circular) and anything outside the git index.
    Each file contributes its plugin-relative path and the hash of its bytes,
    in sorted order, so the result is independent of walk order and mtimes.
    """
    root_real = root.resolve()
    h = hashlib.sha256()
    h.update(json.dumps({k: v for k, v in manifest.items() if k != "version"},
                        sort_keys=True).encode())
    entries: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(pdir, followlinks=True):
        dirnames.sort()
        if shippable is None:
            dirnames[:] = [d for d in dirnames if d not in FALLBACK_SKIP]
        for fn in filenames:
            f = Path(dirpath) / fn
            rel = f.relative_to(pdir).as_posix()
            if rel == ".claude-plugin/plugin.json":
                continue
            if shippable is None:
                if fn in FALLBACK_SKIP:
                    continue
            else:
                try:
                    repo_rel = f.resolve().relative_to(root_real).as_posix()
                except ValueError:
                    continue          # resolves outside the repo: not shipped
                if repo_rel not in shippable:
                    continue
            entries.append((rel, hashlib.sha256(f.read_bytes()).hexdigest()))
    for rel, digest in sorted(entries):
        h.update(f"{rel}\0{digest}\n".encode())
    return h.hexdigest()


def plugin_version(pdir: Path, manifest: dict, root: Path = ROOT,
                   shippable: set[str] | None = None) -> str:
    return f"{BASE_VERSION}-c{content_hash(pdir, manifest, root, shippable)[:12]}"


def frontmatter_description(path: Path) -> str:
    """Read `description:` out of a SKILL.md's YAML frontmatter.

    Handles plain scalars and folded/literal block scalars (`>`, `>-`, `|`,
    `|-`). The indicator is not part of the value: reading it literally is what
    put a bare `>-` in INDEX.md and `">- Establish what..."` in catalog.json.
    """
    if not path.is_file():
        return ""
    parts = path.read_text(encoding="utf-8").split("---")
    if len(parts) < 2:
        return ""
    out: list[str] = []
    taking = False
    for line in parts[1].splitlines():
        if line.startswith("description:"):
            taking = True
            head = line.split(":", 1)[1].strip()
            if head.rstrip("0123456789") in (">", ">-", ">+", "|", "|-", "|+"):
                continue          # a lone indicator carries no text of its own
            out.append(head)
        elif taking:
            if re.match(r"^[A-Za-z_-]+:", line):      # next top-level key
                break
            out.append(line.strip())
    return " ".join(w for w in out if w).strip().strip('"')


def load() -> dict:
    return json.loads(MAP.read_text(encoding="utf-8"))


def marketplace_doc(m: dict) -> dict:
    return {
        "_generated": "by scripts/build_marketplace.py from skill-map.json — do not edit",
        "name": m["marketplace"]["name"],
        "owner": m["marketplace"]["owner"],
        "metadata": {"description": m["marketplace"]["description"], "version": BASE_VERSION},
        # No per-entry "version": it lives in each plugin.json (see module doc).
        "plugins": [
            {
                "name": name,
                "source": f"./plugins/{name}",
                "description": spec["description"],
            }
            for name, spec in sorted(m["plugins"].items())
        ],
    }


def plugin_doc(name: str, spec: dict, owner: dict, version: str | None = None) -> dict:
    doc = {
        "_generated": "by scripts/build_marketplace.py from skill-map.json — do not edit",
        "name": name,
        "description": spec["description"],
        "version": version,
        "author": owner,
    }
    if version is None:
        del doc["version"]
    return doc


def build(check: bool = False) -> int:
    m = load()
    owner = m["marketplace"]["owner"]
    drift: list[str] = []

    def write(path: Path, text: str) -> None:
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                drift.append(str(path.relative_to(ROOT)))
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    write(MARKET, json.dumps(marketplace_doc(m), indent=2) + "\n")

    shippable = shippable_files()
    for name, spec in sorted(m["plugins"].items()):
        pdir = PLUGINS / name
        for skill in spec["skills"]:
            link = pdir / "skills" / skill
            target = os.path.relpath(ROOT / "skills" / skill, link.parent)
            if check:
                if not link.is_symlink() or os.readlink(link) != target:
                    drift.append(str(link.relative_to(ROOT)))
                continue
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(target)

        # After the links: the version hashes the tree they resolve to.
        base = plugin_doc(name, spec, owner)
        version = plugin_version(pdir, base, shippable=shippable)
        write(pdir / ".claude-plugin" / "plugin.json",
              json.dumps(plugin_doc(name, spec, owner, version), indent=2) + "\n")

    # INDEX.md — the map, generated. A hand-maintained index of 23 skills is an
    # index that is wrong within a month.
    lines = ["# Skill index", "",
             "*Generated by `scripts/build_marketplace.py` from "
             "`.claude-plugin/skill-map.json`. Do not edit — regenerate.*", ""]
    for name, spec in sorted(m["plugins"].items()):
        lines += [f"## {name}", "", spec["description"], "",
                  "| skill | description |", "|---|---|"]
        for skill in sorted(spec["skills"]):
            desc = frontmatter_description(ROOT / "skills" / skill / "SKILL.md")
            first = desc.split(". ")[0][:150]
            lines.append(f"| [`{skill}`](skills/{skill}/SKILL.md) | {first} |")
        lines.append("")
    write(ROOT / "INDEX.md", "\n".join(lines))

    # site/src/data/catalog.json — the storefront's data, emitted here rather
    # than read at render time. The Cloudflare prerenderer runs in workerd,
    # where node:fs and node:child_process do not exist; a catalogue that
    # shells out to git cannot survive that environment. Emitting it as a plain
    # JSON artefact keeps one source of truth, puts it under the same --check
    # drift gate as everything else, and leaves the render path pure data.
    import subprocess

    def first_seen(rel: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", "log", "--diff-filter=A", "--follow", "--format=%aI", "-1", "--", rel],
                cwd=ROOT, capture_output=True, text=True, timeout=15).stdout.strip()
            return out or None
        except Exception:
            return None   # shallow clone or tarball: nothing is "new", the safe direction

    def description(skill: str) -> str:
        return frontmatter_description(ROOT / "skills" / skill / "SKILL.md")

    # No "isNew" here: it is a function of today's date, so any committed value
    # goes stale and --check fails on an untouched tree once a skill turns 30
    # days old. The site derives it from `added` at build time (src/lib/catalog.ts).
    commerce = m.get("commerce", {})
    tiers = commerce.get("tiers", {})
    every: list[dict] = []
    cat_plugins = []

    for name, spec in sorted(m["plugins"].items()):
        tier = tiers.get(spec.get("tier", "free"), {"price": 0, "label": "Open"})
        skills = []
        for skill in sorted(spec["skills"]):
            desc = description(skill)
            added = first_seen(f"skills/{skill}/SKILL.md")
            entry = {
                "name": skill, "plugin": name, "description": desc,
                "summary": re.split(r"(?<=\.)\s", desc)[0][:200],
                "added": added,
            }
            skills.append(entry)
            every.append(entry)
        cat_plugins.append({
            "name": name, "description": spec["description"],
            "tier": spec.get("tier", "free"), "price": tier["price"],
            "tierLabel": tier["label"], "checkout": spec.get("checkout"),
            "skills": skills,
        })

    recent = sorted([s for s in every if s["added"]], key=lambda s: s["added"], reverse=True)[:3]
    catalog = {
        "_generated": "by scripts/build_marketplace.py — do not edit",
        "marketplaceName": m["marketplace"]["name"],
        "currency": commerce.get("currency", "USD"),
        "licence": commerce.get("licence", ""),
        "plugins": cat_plugins,
        "recent": recent,
        "totals": {"plugins": len(cat_plugins), "skills": len(every)},
    }
    write(ROOT / "site" / "src" / "data" / "catalog.json",
          json.dumps(catalog, indent=2) + "\n")

    if check:
        if drift:
            print("DRIFT — generated artefacts do not match skill-map.json:")
            for d in drift:
                print(f"  {d}")
            print("\nRegenerate: python3 scripts/build_marketplace.py")
            return 1
        print(f"generated artefacts match the map ({len(m['plugins'])} plugins)")
        return 0

    total = sum(len(s["skills"]) for s in m["plugins"].values())
    print(f"built {len(m['plugins'])} plugins over {total} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(build(check="--check" in sys.argv))
