"""Synthetic-store tests: every verdict path, symlink detection, archive guards."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "model_inventory.py"


def blob(store: Path, data: bytes) -> str:
    d = hashlib.sha256(data).hexdigest()
    (store / "blobs").mkdir(parents=True, exist_ok=True)
    (store / "blobs" / f"sha256-{d}").write_bytes(data)
    return f"sha256:{d}"


def manifest(store: Path, name: str, tag: str, layers: list[tuple[str, str]] | None):
    mdir = store / "manifests" / "registry.ollama.ai" / "library" / name
    mdir.mkdir(parents=True, exist_ok=True)
    body = {"schemaVersion": 2,
            "config": {"mediaType": "application/vnd.docker.container.image.v1+json",
                       "digest": blob(store, f"config:{name}:{tag}".encode()), "size": 1},
            "layers": None if layers is None else
            [{"mediaType": f"application/vnd.ollama.image.{k}", "digest": d, "size": 1} for k, d in layers]}
    (mdir / tag).write_text(json.dumps(body))


class FakeRegistry(BaseHTTPRequestHandler):
    """/v2/library/<name>/manifests/<tag> → canned manifests; anything else 404."""
    routes: dict = {}

    def do_GET(self):
        body = self.routes.get(self.path)
        if body is None:
            self.send_response(404); self.end_headers(); return
        data = json.dumps(body).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def log_message(self, *a):
        pass


class ModelInventoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.users = Path(self.tmp.name) / "users"
        self.users.mkdir()
        self.store = self.home / ".ollama" / "models"
        pulled = blob(self.store, b"base weights")
        manifest(self.store, "base", "latest", [("model", pulled)])
        manifest(self.store, "tuned", "latest", [("model", pulled), ("adapter", blob(self.store, b"lora"))])
        manifest(self.store, "remote", "cloud", None)
        blob(self.store, b"orphaned bytes")
        links = self.store / ".studio_links" / "x"
        links.mkdir(parents=True)
        (links / "base.gguf").symlink_to(self.store / "blobs" / pulled.replace(":", "-"))
        run = self.home / "work" / "run1"
        run.mkdir(parents=True)
        (run / "adapter_config.json").write_text("{}")
        # real bytes, not a sparse file: the scanner sizes by allocated blocks
        (self.home / "work" / "export.gguf").write_bytes(os.urandom(60 * 1024 * 1024))
        self.env = {**os.environ, "HOME": str(self.home),
                    "MODEL_INVENTORY_USERS_ROOT": str(self.users),
                    "OLLAMA_HOST": "127.0.0.1:9"}  # nothing listens: 'not loaded'
        self.env.pop("OLLAMA_MODELS", None)
        self.env.pop("HF_HOME", None)
        self.env.pop("HF_HUB_CACHE", None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *args],
                              env=self.env, capture_output=True, text=True)

    def scan(self):
        out = Path(self.tmp.name) / "scan.json"
        r = self.run_cli("scan", "--json", str(out))
        self.assertEqual(r.returncode, 0, r.stderr)
        return {i["name"]: i for i in json.loads(out.read_text())["items"]}, out

    def test_verdicts(self):
        items, _ = self.scan()
        self.assertEqual(items["tuned:latest"]["verdict"], "keep-archive-first")
        self.assertEqual(items["base:latest"]["verdict"], "unknown-archive-first")
        self.assertEqual(items["remote:cloud"]["verdict"], "cloud-stub")
        self.assertEqual(items["run1"]["verdict"], "keep-archive-first")
        self.assertEqual(items["export.gguf"]["verdict"], "unknown-archive-first")
        orphans = [i for i in items.values() if i["kind"] == "ollama-orphans"]
        self.assertEqual(len(orphans), 1)
        self.assertIn("1 unreferenced", orphans[0]["name"])

    def test_symlink_into_blob_is_reported(self):
        items, _ = self.scan()
        self.assertTrue(any("symlink" in e for e in items["base:latest"]["evidence"]))

    def test_archive_refuses_same_disk(self):
        _, out = self.scan()
        items = json.loads(out.read_text())["items"]
        tuned = next(i for i in items if i["name"] == "tuned:latest")
        dest = Path(self.tmp.name) / "dest"
        dest.mkdir()
        r = self.run_cli("archive", "--dest", str(dest), "--from-json", str(out), "--item", tuned["id"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("same disk", r.stderr)
        self.assertEqual(list(dest.iterdir()), [], "nothing may be written on refusal")

    def test_archive_rejects_unknown_id_and_missing_dest(self):
        _, out = self.scan()
        r = self.run_cli("archive", "--dest", str(Path(self.tmp.name) / "nope"),
                         "--from-json", str(out), "--item", "x")
        self.assertEqual(r.returncode, 2)
        dest = Path(self.tmp.name) / "d2"
        dest.mkdir()
        r = self.run_cli("archive", "--dest", str(dest), "--from-json", str(out), "--item", "bogus")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown item", r.stderr)

    def test_archive_copies_and_verifies_without_deleting(self):
        _, out = self.scan()
        items = json.loads(out.read_text())["items"]
        tuned = next(i for i in items if i["name"] == "tuned:latest")
        dest = Path(self.tmp.name) / "arch"
        dest.mkdir()
        r = self.run_cli("archive", "--dest", str(dest), "--from-json", str(out),
                         "--item", tuned["id"], "--allow-same-disk")
        self.assertEqual(r.returncode, 0, r.stderr)
        run = next(dest.iterdir())
        check = subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=run,
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertEqual(json.loads((run / "MANIFEST.json").read_text())["items"][0]["name"], "tuned:latest")
        for p in tuned["paths"]:
            self.assertTrue(Path(p).exists(), f"original removed: {p}")

    def test_archive_dedups_identical_blobs_across_stores(self):
        shared = self.users / "Shared" / ".ollama" / "models"
        manifest(shared, "base", "latest", [("model", blob(shared, b"base weights"))])
        _, out = self.scan()
        items = json.loads(out.read_text())["items"]
        ids = [i["id"] for i in items if i["name"] == "base:latest"]
        self.assertEqual(len(ids), 2)
        dest = Path(self.tmp.name) / "arch3"
        dest.mkdir()
        args = ["archive", "--dest", str(dest), "--from-json", str(out), "--allow-same-disk"]
        for i in ids:
            args += ["--item", i]
        r = self.run_cli(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        run = next(dest.iterdir())
        stored = [p for p in run.rglob("sha256-*") if p.is_file()]
        names = [p.name for p in stored]
        self.assertEqual(len(names), len(set(names)), "an identical blob must be stored once")
        man = json.loads((run / "MANIFEST.json").read_text())
        self.assertEqual(len(man["dedup"]), 2, "model + config blob are both identical across stores")
        for d in man["dedup"]:
            self.assertTrue((run / d["same_as"]).exists())
        check = subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=run, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout)

    def test_archive_refuses_when_destination_too_small(self):
        _, out = self.scan()
        items = json.loads(out.read_text())["items"]
        tuned = next(i for i in items if i["name"] == "tuned:latest")
        dest = Path(self.tmp.name) / "arch4"
        dest.mkdir()
        # pretend the item is larger than any disk: point it at a huge sparse file
        big = Path(self.tmp.name) / "huge.bin"
        with open(big, "wb") as f:
            f.truncate(1 << 50)  # 1 PiB logical size, no blocks
        tuned["paths"].append(str(big))
        out.write_text(json.dumps({"items": items}))
        r = self.run_cli("archive", "--dest", str(dest), "--from-json", str(out), "--item", tuned["id"],
                         "--allow-same-disk")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Nothing was written", r.stderr)
        self.assertEqual(list(dest.iterdir()), [])

    def test_archive_includes_config_blob(self):
        _, out = self.scan()
        items = json.loads(out.read_text())["items"]
        tuned = next(i for i in items if i["name"] == "tuned:latest")
        cfg = json.loads(Path(tuned["paths"][0]).read_text())["config"]["digest"].replace(":", "-")
        self.assertTrue(any(p.endswith(cfg) for p in tuned["paths"]), "config blob missing from item")
        dest = Path(self.tmp.name) / "arch5"
        dest.mkdir()
        r = self.run_cli("archive", "--dest", str(dest), "--from-json", str(out),
                         "--item", tuned["id"], "--allow-same-disk")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(list(next(dest.iterdir()).rglob(cfg)), "config blob not archived — restore would fail")

    def test_archive_catches_corrupt_blob(self):
        _, out = self.scan()
        items = json.loads(out.read_text())["items"]
        base = next(i for i in items if i["name"] == "base:latest")
        blob_file = next(Path(p) for p in base["paths"] if "/blobs/" in p)
        blob_file.write_bytes(b"bit rot")  # content no longer matches its sha256 name
        dest = Path(self.tmp.name) / "arch2"
        dest.mkdir()
        r = self.run_cli("archive", "--dest", str(dest), "--from-json", str(out),
                         "--item", base["id"], "--allow-same-disk")
        self.assertEqual(r.returncode, 1)
        self.assertIn("hash mismatch", r.stderr)

    def test_extra_store_only_via_flag(self):
        other = self.home / "elsewhere" / "models"
        manifest(other, "side", "latest", [("model", blob(other, b"side weights"))])
        items, _ = self.scan()
        self.assertNotIn("side:latest", items, "stores must not be found by globbing --root")
        out = Path(self.tmp.name) / "scan2.json"
        r = self.run_cli("scan", "--store", str(other), "--json", str(out))
        self.assertEqual(r.returncode, 0, r.stderr)
        names = {i["name"] for i in json.loads(out.read_text())["items"]}
        self.assertIn("side:latest", names)

    def registry(self, routes):
        FakeRegistry.routes = routes
        srv = HTTPServer(("127.0.0.1", 0), FakeRegistry)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        self.env["MODEL_INVENTORY_REGISTRY_URL"] = f"http://127.0.0.1:{srv.server_port}"

    def scan_registry(self):
        out = Path(self.tmp.name) / "reg.json"
        r = self.run_cli("scan", "--check-registry", "--json", str(out))
        self.assertEqual(r.returncode, 0, r.stderr)
        return {i["name"]: i for i in json.loads(out.read_text())["items"]}

    def test_registry_match_moved_tag_and_absent(self):
        base_digest = blob(self.store, b"base weights")
        moved = blob(self.store, b"old build")
        manifest(self.store, "moved", "latest", [("model", moved)])
        lay = lambda d: {"mediaType": "application/vnd.ollama.image.model", "digest": d, "size": 1}
        self.registry({
            "/v2/library/base/manifests/latest": {"layers": [lay(base_digest)]},
            "/v2/library/moved/manifests/latest": {"layers": [lay("sha256:" + "0" * 64)]},
        })
        items = self.scan_registry()
        self.assertEqual(items["base:latest"]["verdict"], "re-downloadable")
        self.assertEqual(items["moved:latest"]["verdict"], "unknown-archive-first",
                         "a moved tag is not proof of a local build")
        self.assertTrue(any("different build upstream" in e for e in items["moved:latest"]["evidence"]))
        self.assertEqual(items["tuned:latest"]["verdict"], "keep-archive-first")  # adapter wins

    def test_registry_absent_means_keep(self):
        self.registry({})
        items = self.scan_registry()
        self.assertEqual(items["base:latest"]["verdict"], "keep-archive-first")

    def test_manifest_list_variant_inherits_parent(self):
        vlayer = blob(self.store, b"variant weights")
        variant = json.dumps({"schemaVersion": 2, "layers": [
            {"mediaType": "application/vnd.ollama.image.model", "digest": vlayer, "size": 1}]}).encode()
        vdigest = blob(self.store, variant)  # variant manifest is also stored as a blob
        vdir = self.store / "manifests" / "registry.ollama.ai" / "library" / "llamacpp"
        vdir.mkdir(parents=True)
        (vdir / vdigest.split(":")[1]).write_bytes(variant)
        lst = blob(self.store, json.dumps({"manifests": [{"digest": vdigest}]}).encode())
        mdir = self.store / "manifests" / "registry.ollama.ai" / "library" / "fam"
        mdir.mkdir(parents=True)
        (mdir / "latest").write_text(json.dumps({"layers": [
            {"mediaType": "application/vnd.ollama.image.model", "digest": blob(self.store, b"fam w"), "size": 1},
            {"mediaType": "application/vnd.ollama.manifest.list.v2+json", "digest": lst, "size": 1}]}))
        lay = lambda d: {"mediaType": "application/vnd.ollama.image.model", "digest": d, "size": 1}
        fam = json.loads((mdir / "latest").read_text())["layers"]
        self.registry({"/v2/library/fam/manifests/latest": {"layers": fam}})
        items = self.scan_registry()
        vname = "llamacpp:" + vdigest.split(":")[1]
        self.assertEqual(items["fam:latest"]["verdict"], "re-downloadable")
        self.assertEqual(items[vname]["verdict"], "re-downloadable", "variant must follow its parent")
        self.assertTrue(any("runner variant of fam:latest" in e for e in items[vname]["evidence"]))
        self.assertFalse(any(i["kind"] == "ollama-orphans" and vlayer.replace(":", "-") in " ".join(i["paths"])
                             for i in items.values()), "variant layers are referenced, not orphans")

    def test_vocab_fixtures_are_not_weights(self):
        (self.home / "work" / "ggml-vocab-x.gguf").write_bytes(b"\0" * (60 * 1024 * 1024))
        items, _ = self.scan()
        self.assertNotIn("ggml-vocab-x.gguf", items)

    def test_manifests_v2_links_are_internal(self):
        v2 = self.store / "manifests-v2" / "ollama.com" / "library" / "base"
        v2.mkdir(parents=True)
        # link a blob that belongs to a model (not an orphan), so the check is deterministic
        base = json.loads((self.store / "manifests/registry.ollama.ai/library/base/latest").read_text())
        target = self.store / "blobs" / base["layers"][0]["digest"].replace(":", "-")
        (v2 / "latest").symlink_to(target)
        (self.store / "manifests-v2" / "ollama.com" / "library" / "ghost").mkdir()
        (self.store / "manifests-v2" / "ollama.com" / "library" / "ghost" / "latest").symlink_to(target)
        items, _ = self.scan()
        self.assertFalse(any("symlink" in e and "manifests-v2" in e
                             for i in items.values() for e in i["evidence"]),
                         "Ollama's own v2 index links are not outside dependents")
        self.assertIn("ghost:latest", items, "v2-only entries must be surfaced, not skipped")
        self.assertEqual(items["ghost:latest"]["verdict"], "unknown-archive-first")

    def test_symlinked_home_does_not_walk_into_store(self):
        # $HOME reached through a symlink (like /var -> /private/var): the sweep must
        # still recognise the managed store and not report its internals as dependents.
        link = Path(self.tmp.name) / "homelink"
        link.symlink_to(self.home)
        self.env["HOME"] = str(link)
        v2 = self.store / "manifests-v2" / "ollama.com" / "library" / "base"
        v2.mkdir(parents=True)
        base = json.loads((self.store / "manifests/registry.ollama.ai/library/base/latest").read_text())
        (v2 / "latest").symlink_to(self.store / "blobs" / base["layers"][0]["digest"].replace(":", "-"))
        items, _ = self.scan()
        links = [e for e in items["base:latest"]["evidence"] if "symlink(s)" in e]
        # exactly the one outside dependent from setUp (.studio_links); a second would be
        # the store's own manifests-v2 link, picked up by a sweep that walked into the store
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0].startswith("1 symlink(s)"), links[0])

    def test_scan_never_modifies_store(self):
        before = sorted((p, p.stat().st_mtime_ns) for p in self.store.rglob("*") if not p.is_symlink())
        self.scan()
        after = sorted((p, p.stat().st_mtime_ns) for p in self.store.rglob("*") if not p.is_symlink())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
