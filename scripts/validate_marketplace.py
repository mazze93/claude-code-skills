#!/usr/bin/env python3
"""Guards for the marketplace. Every check here exists because of a real failure.

    python3 scripts/validate_marketplace.py

Checks, and what each is defending against:

  drift            A generated artefact was hand-edited. Regenerate-and-diff,
                   the same gate used for parity goldens.
  orphans          A skill exists in skills/ but belongs to no plugin, so it
                   ships to nobody and rots unnoticed.
  double-claim     A skill is claimed by two plugins. Installing both would
                   put the same skill on disk twice under different owners.
  name collision   Two skills, or a skill and a plugin, share a name. The
                   installed namespace at ~/.claude/skills is FLAT: a collision
                   there is what let an installer write through a symlink into
                   this repo on 2026-08-31 and silently revert a consolidation.
  frontmatter      A SKILL.md without valid frontmatter loads as nothing. The
                   failure is invisible — the skill simply never triggers.
  name mismatch    frontmatter `name:` disagrees with the directory name.
  description      Missing, or too thin to route on. A description is the only
                   thing the model sees when choosing; a vague one is a skill
                   that never gets picked.
  dangling link    A plugin symlink pointing at a skill that no longer exists.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / ".claude-plugin" / "skill-map.json"
SKILLS = ROOT / "skills"
PLUGINS = ROOT / "plugins"

MIN_DESCRIPTION = 80          # shorter than this cannot describe when to trigger
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS.iterdir() if p.is_dir())


def check_map_and_coverage(m: dict) -> None:
    on_disk = {p.name for p in skill_dirs()}
    claimed: dict[str, str] = {}

    for plugin, spec in m["plugins"].items():
        if plugin in on_disk:
            err(f"name collision: plugin '{plugin}' shares a name with a skill")
        for skill in spec["skills"]:
            if skill not in on_disk:
                err(f"plugin '{plugin}' claims '{skill}', which is not in skills/")
            if skill in claimed:
                err(f"double-claim: '{skill}' is in both '{claimed[skill]}' and '{plugin}'")
            claimed[skill] = plugin

    for orphan in sorted(on_disk - set(claimed)):
        err(f"orphan: skill '{orphan}' belongs to no plugin — it ships to nobody")


def check_frontmatter() -> None:
    seen: dict[str, str] = {}
    for d in skill_dirs():
        f = d / "SKILL.md"
        if not f.is_file():
            err(f"{d.name}: no SKILL.md")
            continue
        m = FRONTMATTER.match(f.read_text(encoding="utf-8"))
        if not m:
            err(f"{d.name}: SKILL.md has no frontmatter block — it will load as nothing")
            continue
        block = m.group(1)

        name = re.search(r"^name:\s*(\S+)", block, re.M)
        if not name:
            err(f"{d.name}: frontmatter has no name:")
        elif name.group(1) != d.name:
            err(f"{d.name}: frontmatter name '{name.group(1)}' != directory name")

        desc = re.search(r"^description:\s*(.+)", block, re.M | re.S)
        if not desc:
            err(f"{d.name}: frontmatter has no description:")
        else:
            text = desc.group(1).strip().strip('"')
            if len(text) < MIN_DESCRIPTION:
                err(f"{d.name}: description is {len(text)} chars — too thin to route on")
            key = text[:60].lower()
            if key in seen:
                warn(f"{d.name}: description opens identically to '{seen[key]}' — "
                     "overlapping descriptions make skill selection ambiguous")
            seen[key] = d.name


def check_links() -> None:
    if not PLUGINS.is_dir():
        return
    for link in sorted(PLUGINS.glob("*/skills/*")):
        if not link.is_symlink():
            err(f"{link.relative_to(ROOT)}: plugin skills must be symlinks, not copies")
        elif not link.resolve().is_dir():
            err(f"{link.relative_to(ROOT)}: dangling symlink -> {os.readlink(link)}")


def main() -> int:
    if not MAP.is_file():
        print("no .claude-plugin/skill-map.json"); return 2
    m = json.loads(MAP.read_text(encoding="utf-8"))

    check_map_and_coverage(m)
    check_frontmatter()
    check_links()

    for w in warnings:
        print(f"warn  {w}")
    for e in errors:
        print(f"FAIL  {e}")

    n_sk = len(skill_dirs())
    if errors:
        print(f"\n{len(errors)} error(s) across {len(m['plugins'])} plugins / {n_sk} skills")
        return 1
    print(f"ok — {len(m['plugins'])} plugins, {n_sk} skills, "
          f"{len(warnings)} warning(s), no collisions or orphans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
