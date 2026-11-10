"""Tests for the content-derived plugin version in build_marketplace.py.

    python3 -m unittest discover -s scripts/tests

Each test builds a throwaway repo shape (plugins/<p>/skills/<s> symlinked into
skills/<s>) so it exercises the symlink-following that the real tree depends
on. The point of the version is that `claude plugin update` only refreshes a
cached plugin when the string changes, so the property that matters most is
test_changes_when_a_linked_skill_changes.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_marketplace as bm  # noqa: E402

MANIFEST = {"name": "p", "description": "d", "author": {"name": "a"}}


class Fixture:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.pdir = self.root / "plugins" / "p"
        (self.pdir / ".claude-plugin").mkdir(parents=True)
        (self.pdir / "skills").mkdir()
        for s in ("alpha", "beta"):
            (self.root / "skills" / s).mkdir(parents=True)
            (self.root / "skills" / s / "SKILL.md").write_text(f"# {s}\n")
        (self.root / "skills" / "unrelated").mkdir()
        (self.root / "skills" / "unrelated" / "SKILL.md").write_text("# u\n")
        for s in ("alpha", "beta"):
            os.symlink(os.path.join("..", "..", "..", "skills", s), self.pdir / "skills" / s)
        (self.pdir / ".claude-plugin" / "plugin.json").write_text("{}")

    def shippable(self) -> set[str]:
        out = set()
        for d, _, fs in os.walk(self.root):
            for f in fs:
                out.add((Path(d) / f).relative_to(self.root).as_posix())
        return out

    def h(self, manifest: dict = MANIFEST, shippable: set[str] | None | str = "all") -> str:
        ship = self.shippable() if shippable == "all" else shippable
        return bm.content_hash(self.pdir, manifest, self.root, ship)

    def close(self) -> None:
        self._tmp.cleanup()


class ContentHash(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()

    def tearDown(self) -> None:
        self.fx.close()

    def test_deterministic(self) -> None:
        self.assertEqual(self.fx.h(), self.fx.h())

    def test_changes_when_a_linked_skill_changes(self) -> None:
        before = self.fx.h()
        (self.fx.root / "skills" / "alpha" / "SKILL.md").write_text("# alpha v2\n")
        self.assertNotEqual(before, self.fx.h())

    def test_changes_when_a_file_is_added_to_a_linked_skill(self) -> None:
        before = self.fx.h()
        (self.fx.root / "skills" / "beta" / "ref.md").write_text("x\n")
        self.assertNotEqual(before, self.fx.h())

    def test_changes_when_plugin_local_file_changes(self) -> None:
        before = self.fx.h()
        (self.fx.pdir / "evals").mkdir()
        (self.fx.pdir / "evals" / "case.yaml").write_text("name: c\n")
        self.assertNotEqual(before, self.fx.h())

    def test_unrelated_skill_does_not_move_it(self) -> None:
        before = self.fx.h()
        (self.fx.root / "skills" / "unrelated" / "SKILL.md").write_text("# u v2\n")
        self.assertEqual(before, self.fx.h())

    def test_own_plugin_json_is_excluded(self) -> None:
        before = self.fx.h()
        (self.fx.pdir / ".claude-plugin" / "plugin.json").write_text('{"version": "x"}')
        self.assertEqual(before, self.fx.h())

    def test_version_field_is_excluded_but_description_counts(self) -> None:
        before = self.fx.h()
        self.assertEqual(before, self.fx.h({**MANIFEST, "version": "9.9.9"}))
        self.assertNotEqual(before, self.fx.h({**MANIFEST, "description": "other"}))

    def test_files_outside_the_index_do_not_count(self) -> None:
        ship = self.fx.shippable()
        before = self.fx.h(shippable=ship)
        (self.fx.root / "skills" / "alpha" / "scratch.txt").write_text("local only\n")
        self.assertEqual(before, self.fx.h(shippable=ship))

    def test_fallback_without_git_skips_junk(self) -> None:
        before = self.fx.h(shippable=None)
        (self.fx.root / "skills" / "alpha" / ".DS_Store").write_bytes(b"\0")
        self.assertEqual(before, self.fx.h(shippable=None))

    def test_version_format(self) -> None:
        v = bm.plugin_version(self.fx.pdir, MANIFEST, self.fx.root, self.fx.shippable())
        self.assertRegex(v, r"^\d+\.\d+\.\d+-c[0-9a-f]{12}$")
        self.assertTrue(v.startswith(bm.BASE_VERSION + "-c"))


class RepoInvariant(unittest.TestCase):
    def test_marketplace_entries_carry_no_version(self) -> None:
        """Version in both places is silently resolved to plugin.json; keep one."""
        import json
        doc = bm.marketplace_doc(bm.load())
        self.assertTrue(all("version" not in p for p in doc["plugins"]))
        self.assertTrue(all(json.loads(
            (bm.PLUGINS / p["name"] / ".claude-plugin" / "plugin.json").read_text()
        ).get("version", "").startswith(bm.BASE_VERSION + "-c") for p in doc["plugins"]))


if __name__ == "__main__":
    unittest.main()
