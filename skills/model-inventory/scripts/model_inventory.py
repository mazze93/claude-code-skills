#!/usr/bin/env python3
"""model_inventory — find on-device AI models, judge what deleting each would lose.

    model_inventory.py scan    [--root DIR ...] [--refs DIR ...] [--check-registry] [--json OUT]
    model_inventory.py archive --dest DIR --item ID [--item ID ...] [--from-json SCAN.json]

`scan` is read-only. `archive` only copies, then verifies every byte by SHA-256;
it never deletes, and it refuses a destination on the same disk as the source
(archiving there frees nothing). No paths are assumed beyond the tools' own
documented defaults and the env vars that override them; the archive
destination is always supplied by the caller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

HOME = Path.home()

# Files whose presence marks local training work rather than a downloaded model.
TRAINING_MARKERS = {
    "adapter_config.json", "adapter_model.safetensors", "adapter_model.bin",
    "trainer_state.json", "training_args.bin", "optimizer.pt", "scheduler.pt",
}
WEIGHT_SUFFIXES = {".gguf", ".safetensors", ".bin", ".pt", ".pth", ".mlx", ".npz", ".onnx"}
# Skipped by the loose-file sweep: managed stores are inventoried separately,
# and these trees are large and never hold user training output.
SWEEP_SKIP = {"node_modules", ".git", "Library", ".Trash", ".npm", ".cargo",
              ".rustup", "site-packages", ".venv", "venv", "blobs", "hub"}
MIN_WEIGHT_BYTES = 50 * 1024 * 1024  # smaller .bin/.pt files are rarely weights

VERDICT_ORDER = ["keep-archive-first", "unknown-archive-first", "orphan",
                 "re-downloadable", "cloud-stub"]


@dataclass
class Item:
    id: str
    kind: str            # ollama-model | ollama-orphans | hf-repo | training-run | loose-weights | lmstudio-model
    store: str
    name: str
    bytes: int
    verdict: str
    evidence: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    shared_with: list[str] = field(default_factory=list)
    in_use: str = "unknown"


def human(n: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return f"{n}"


def allocated(p: Path) -> int:
    """Bytes actually on disk (0 for evicted cloud placeholders)."""
    try:
        return p.stat().st_blocks * 512
    except OSError:
        return 0


def tree_bytes(p: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(p, onerror=lambda e: None):
        for f in files:
            fp = Path(root, f)
            if not fp.is_symlink():
                total += allocated(fp)
    return total


# ---------------------------------------------------------------- Ollama

def ollama_stores(extra: list[Path]) -> tuple[list[Path], list[Path]]:
    """(readable stores, stores that exist but this user cannot read).

    Discovery is by documented location plus explicit --store dirs only. It never
    globs a whole tree: a recursive glob over $HOME descends into
    ~/Library/CloudStorage, where SSH/S3 File Provider mounts can hang lstat()
    indefinitely (observed 2026-10-23: a scan stuck >20 min at 0% CPU)."""
    cands = []
    if os.environ.get("OLLAMA_MODELS"):
        cands.append(Path(os.environ["OLLAMA_MODELS"]))
    cands.append(HOME / ".ollama" / "models")
    users = Path(os.environ.get("MODEL_INVENTORY_USERS_ROOT", "/Users"))  # override for tests
    if users.is_dir():
        for u in sorted(users.iterdir()):
            cands.append(u / ".ollama" / "models")
    if "MODEL_INVENTORY_USERS_ROOT" not in os.environ:
        cands.append(Path("/usr/share/ollama/.ollama/models"))  # Linux service default
    cands.extend(extra)
    seen, out, blocked = set(), [], []
    for c in cands:
        try:
            key = c.resolve()
            if key in seen:
                continue
            seen.add(key)
            if (c / "manifests").is_dir() or (c / "blobs").is_dir():
                next(os.scandir(c / "manifests"), None)
                out.append(c)
        except PermissionError:
            blocked.append(c)
        except OSError:
            continue
    return out, blocked


def blob_path(store: Path, digest: str) -> Path:
    return store / "blobs" / digest.replace(":", "-")


def ollama_running() -> set[str]:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    if not host.startswith("http"):
        host = "http://" + host
    try:
        with urllib.request.urlopen(host + "/api/ps", timeout=2) as r:
            return {m["name"] for m in json.load(r).get("models", [])}
    except (urllib.error.URLError, OSError, ValueError):
        return set()


def registry_match(host: str, repo: str, tag: str, layer_digests: set[str]) -> str:
    """'match' | 'differs' | 'absent' | 'error:<why>' — compares layer digests."""
    base = os.environ.get("MODEL_INVENTORY_REGISTRY_URL", f"https://{host}")  # override for tests
    url = f"{base}/v2/{repo}/manifests/{tag}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.docker.distribution.manifest.v2+json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            remote = json.load(r)
    except urllib.error.HTTPError as e:
        return "absent" if e.code == 404 else f"error:http-{e.code}"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return f"error:{type(e).__name__}"
    remote_digests = {l["digest"] for l in remote.get("layers") or []}
    if remote_digests and remote_digests == layer_digests:
        return "match"
    return "differs:" + summarize_kinds(remote.get("layers") or [])


def summarize_kinds(layers: list[dict]) -> str:
    """'model 5.1G, projector 945M, license' — compact, counts repeated kinds."""
    out: dict[str, list[int]] = {}
    for l in layers:
        out.setdefault(l.get("mediaType", "").rsplit(".", 1)[-1], []).append(int(l.get("size") or 0))
    parts = []
    for k, sizes in out.items():
        label = k if len(sizes) == 1 else f"{len(sizes)}×{k}"
        total = sum(sizes)
        parts.append(f"{label} {human(total)}" if total >= 1 << 20 else label)
    return ", ".join(parts) or "none"


def read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def file_digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def scan_ollama(stores: list[Path], check_registry: bool, items: list[Item]) -> dict[str, set[str]]:
    loaded = ollama_running()
    digest_owners: dict[str, set[str]] = {}
    for store in stores:
        mroot = store / "manifests"
        referenced: set[str] = set()
        try:
            manifests = [p for p in mroot.rglob("*") if p.is_file()]
        except PermissionError:
            items.append(Item(f"ollama:{store}", "ollama-store", str(store), "(unreadable)",
                              0, "unknown-archive-first",
                              ["store not readable as this user — rerun with sudo"]))
            continue
        # Pass 1 — manifest lists. Newer pulls store a list blob naming per-runner
        # variant manifests; a variant can also be written as its own manifest with
        # a 64-hex tag (e.g. `llamacpp:<digest>`). Map each variant digest to its
        # parent so it isn't mistaken for a local build, and count the variants'
        # layers as referenced so they aren't flagged orphan.
        variant_of: dict[str, str] = {}
        for mf in manifests:
            m = read_json(mf)
            if not m:
                continue
            parent = "/".join(mf.relative_to(mroot).parts[1:-1]).removeprefix("library/") + ":" + mf.name
            for l in m.get("layers") or []:
                if not l.get("mediaType", "").endswith("manifest.list.v2+json"):
                    continue
                lst = read_json(blob_path(store, l["digest"])) or {}
                for v in lst.get("manifests") or []:
                    variant_of[v["digest"]] = parent
                    vm = read_json(blob_path(store, v["digest"])) or {}
                    referenced |= {x["digest"] for x in vm.get("layers") or []}
                    if (vm.get("config") or {}).get("digest"):
                        referenced.add(vm["config"]["digest"])
                    referenced.add(v["digest"])
        for mf in manifests:
            rel = mf.relative_to(mroot).parts  # host / namespace... / model / tag
            if len(rel) < 3:
                continue
            host, repo_parts, tag = rel[0], rel[1:-1], rel[-1]
            repo = "/".join(repo_parts)
            short = repo.removeprefix("library/")
            name = f"{short}:{tag}" if host == "registry.ollama.ai" else f"{host}/{repo}:{tag}"
            try:
                m = json.loads(mf.read_text())
            except (OSError, ValueError):
                continue
            layers = m.get("layers") or []
            digests = {l["digest"] for l in layers}
            cfg = (m.get("config") or {}).get("digest")
            referenced |= digests | ({cfg} if cfg else set())
            for d in digests:
                digest_owners.setdefault(d, set()).add(str(store))
            size = sum(allocated(blob_path(store, d)) for d in digests)
            kinds = [l.get("mediaType", "").rsplit(".", 1)[-1] for l in layers]
            ev = [f"layers: {summarize_kinds(layers)}",
                  f"manifest written {time.strftime('%Y-%m-%d', time.localtime(mf.stat().st_mtime))}"]
            paths = [str(mf)] + [str(blob_path(store, d)) for d in digests]
            if not layers:
                verdict = "cloud-stub"
                ev.append("no local layers — runs remotely, nothing to lose or reclaim")
            elif "adapter" in kinds:
                verdict = "keep-archive-first"
                ev.append("contains a LoRA adapter layer — local training output")
            elif (parent := variant_of.get(file_digest(mf))):
                verdict = f"@variant:{parent}"  # resolved to the parent's verdict below
                ev.append(f"runner variant of {parent}: listed in its manifest list and written by "
                          "the same pull — not a local build; judge it with its parent")
            else:
                verdict = "unknown-archive-first"
                if check_registry:
                    res = registry_match(host, repo, tag, digests)
                    ev.append(f"registry {host}/{repo}:{tag} → {res}")
                    if res == "match":
                        verdict = "re-downloadable"
                    elif res == "absent":
                        verdict = "keep-archive-first"
                        ev.append("registry has no such model/tag — locally built (`ollama create`) "
                                  "or from a registry that has since dropped it")
                    elif res.startswith("differs"):
                        ev.append("tag now points to a different build upstream. The current build "
                                  "is re-downloadable; this exact build is not. Usually a moved tag, "
                                  "not your work — ask before treating it as either")
                else:
                    ev.append("registry not checked (--check-registry) — treat as irreplaceable")
                if len(tag) == 64:
                    ev.append("tag is a content hash — `ollama list` may hide it")
            items.append(Item(f"ollama:{store}:{name}", "ollama-model", str(store), name, size,
                              verdict, ev, paths,
                              in_use="loaded now" if name in loaded else "not loaded"))
        # manifests-v2 (Ollama 0.40+) mirrors manifests/ as links to manifest(-list)
        # blobs. Surface any entry with no v1 counterpart rather than skip it.
        v1_names = {i.name for i in items if i.store == str(store)}
        v2root = store / "manifests-v2"
        if v2root.is_dir():
            for e in v2root.rglob("*"):
                if e.is_dir():
                    continue
                parts = e.relative_to(v2root).parts
                if len(parts) < 3:
                    continue
                name = "/".join(parts[1:-1]).removeprefix("library/") + ":" + parts[-1]
                if name not in v1_names:
                    items.append(Item(f"ollama-v2:{e}", "ollama-model", str(store), name, 0,
                                      "unknown-archive-first",
                                      ["listed only in manifests-v2 (newer Ollama index); this "
                                       "scanner doesn't size v2-only entries — check `ollama list`"],
                                      [str(e)]))
        parents = {i.name: i.verdict for i in items if i.store == str(store)}
        for i in items:
            if i.store == str(store) and i.verdict.startswith("@variant:"):
                i.verdict = parents.get(i.verdict.split(":", 1)[1], "unknown-archive-first")
        blobs = store / "blobs"
        if blobs.is_dir():
            orphans = [b for b in blobs.iterdir()
                       if b.name.startswith("sha256-")
                       and b.name.replace("-", ":", 1) not in referenced]
            if orphans:
                items.append(Item(f"ollama-orphans:{store}", "ollama-orphans", str(store),
                                  f"{len(orphans)} unreferenced blobs",
                                  sum(allocated(b) for b in orphans), "orphan",
                                  ["no manifest in this store references these blobs; "
                                   "`ollama rm` leftovers or interrupted pulls",
                                   "check symlinks below before removing"],
                                  [str(b) for b in orphans]))
    return digest_owners


def note_symlink(fp: Path, blob_dirs: list[str], links: dict[str, list[str]]) -> None:
    try:
        t = str(fp.resolve())
    except OSError:
        return
    if any(t.startswith(b) for b in blob_dirs):
        links.setdefault(t, []).append(str(fp))


def store_symlinks(stores: list[Path], blob_dirs: list[str], links: dict[str, list[str]]) -> None:
    """Symlinks kept inside a store but outside blobs/manifests (e.g. Unsloth Studio's
    .studio_links) — the main sweep skips managed stores, so walk them here."""
    for s in stores:
        for dirpath, dirnames, filenames in os.walk(s, onerror=lambda e: None):
            # manifests-v2/ and metadata/ are Ollama's own index (0.40+): its links into
            # blobs are internal, not outside tools that a removal would break.
            dirnames[:] = [d for d in dirnames if d not in ("blobs", "manifests", "manifests-v2", "metadata")]
            for f in filenames:
                fp = Path(dirpath, f)
                if fp.is_symlink():
                    note_symlink(fp, blob_dirs, links)


# ---------------------------------------------------------------- Hugging Face / LM Studio

def hf_hub_dirs() -> list[Path]:
    c = []
    if os.environ.get("HF_HUB_CACHE"):
        c.append(Path(os.environ["HF_HUB_CACHE"]))
    if os.environ.get("HF_HOME"):
        c.append(Path(os.environ["HF_HOME"]) / "hub")
    c.append(HOME / ".cache" / "huggingface" / "hub")
    return [p for p in dict.fromkeys(c) if p.is_dir()]


def scan_hf(items: list[Item]) -> None:
    for hub in hf_hub_dirs():
        for repo in sorted(hub.glob("models--*")):
            name = repo.name.removeprefix("models--").replace("--", "/")
            ev, verdict = ["Hugging Face hub cache; re-download with `hf download`"], "re-downloadable"
            marks = {p.name for p in repo.rglob("*") if p.name in TRAINING_MARKERS}
            if marks:
                verdict = "keep-archive-first"
                ev = [f"training files inside a hub cache entry: {', '.join(sorted(marks))}"]
            size = tree_bytes(repo)
            if size < 1 << 20:
                ev.append("no weights on disk (refs/metadata only) — an aborted or evicted download")
            refs = repo / "refs"
            if refs.is_dir():
                ev.append("refs: " + ", ".join(sorted(p.name for p in refs.iterdir())))
            items.append(Item(f"hf:{repo}", "hf-repo", str(hub), name, size,
                              verdict, ev, [str(repo)]))


def scan_lmstudio(items: list[Item]) -> None:
    for root in (HOME / ".lmstudio" / "models", HOME / ".cache" / "lm-studio" / "models"):
        if not root.is_dir():
            continue
        for pub in root.iterdir():
            for model in (pub.iterdir() if pub.is_dir() else []):
                items.append(Item(f"lmstudio:{model}", "lmstudio-model", str(root),
                                  f"{pub.name}/{model.name}", tree_bytes(model),
                                  "re-downloadable",
                                  ["LM Studio download; re-download from its catalog "
                                   "(unless you placed a local file here yourself)"],
                                  [str(model)]))


# ---------------------------------------------------------------- training runs & loose weights

SKIP_BUNDLE_SUFFIXES = (".photoslibrary", ".musiclibrary", ".tvlibrary", ".bundle", ".app")


def walk_local(root: Path):
    """os.walk that stays on root's filesystem (like `du -x`) and skips SWEEP_SKIP,
    media bundles and cloud mounts — network/File Provider trees can hang stat()."""
    try:
        dev = os.lstat(root).st_dev
    except OSError:
        return
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        keep = []
        for d in dirnames:
            if d in SWEEP_SKIP or d == "CloudStorage" or d.endswith(SKIP_BUNDLE_SUFFIXES):
                continue
            try:
                if os.lstat(os.path.join(dirpath, d)).st_dev != dev:
                    continue
            except OSError:
                continue
            keep.append(d)
        dirnames[:] = keep
        yield dirpath, dirnames, filenames


def scan_training(roots: list[Path], managed: list[Path], items: list[Item],
                  blob_dirs: list[str], links: dict[str, list[str]]) -> None:
    managed_s = [str(m.resolve()) for m in managed if m.exists()]
    seen_runs: set[str] = set()
    for root in roots:
        for dirpath, dirnames, filenames in walk_local(root):
            if any(dirpath.startswith(m) for m in managed_s):
                dirnames[:] = []
                continue
            for d in list(dirnames):
                if os.path.islink(os.path.join(dirpath, d)):
                    note_symlink(Path(dirpath, d), blob_dirs, links)
            fset = set(filenames)
            marks = fset & TRAINING_MARKERS
            if marks or any(d.startswith("checkpoint-") for d in dirnames):
                run = Path(dirpath)
                if str(run) not in seen_runs:
                    seen_runs.add(str(run))
                    items.append(Item(f"train:{run}", "training-run", str(run.parent), run.name,
                                      tree_bytes(run), "keep-archive-first",
                                      [f"training markers: {', '.join(sorted(marks)) or 'checkpoint-* dirs'}",
                                       "local training output — cannot be re-downloaded"],
                                      [str(run)]))
                dirnames[:] = []
                continue
            for f in filenames:
                fp = Path(dirpath, f)
                if fp.is_symlink():
                    note_symlink(fp, blob_dirs, links)
                    continue
                if fp.suffix.lower() not in WEIGHT_SUFFIXES:
                    continue
                size = allocated(fp)
                if size < MIN_WEIGHT_BYTES or f.startswith("ggml-vocab-"):
                    continue  # tokenizer/vocab fixtures shipped with llama.cpp, not weights
                items.append(Item(f"file:{fp}", "loose-weights", str(fp.parent), fp.name, size,
                                  "unknown-archive-first",
                                  ["weights file outside any managed store — origin unknown; "
                                   "could be an export or a manual download"],
                                  [str(fp)]))


# ---------------------------------------------------------------- references

def find_refs(items: list[Item], ref_roots: list[Path]) -> None:
    """Grep caller-supplied project roots for model names (cheap 'is it used' signal)."""
    names = {i.id: i.name.split(":")[0] for i in items
             if i.kind in ("ollama-model", "hf-repo", "lmstudio-model") and len(i.name) > 3}
    if not names or not ref_roots:
        return
    hits: dict[str, set[str]] = {k: set() for k in names}
    text_ext = {".py", ".ts", ".js", ".mjs", ".json", ".toml", ".yaml", ".yml", ".md",
                ".sh", ".env", ".swift", ".rs", ".go"}
    for root in ref_roots:
        for dirpath, dirnames, filenames in walk_local(root):
            for f in filenames:
                fp = Path(dirpath, f)
                if fp.suffix.lower() not in text_ext:
                    continue
                try:
                    if fp.stat().st_size > 2_000_000:
                        continue
                    body = fp.read_text(errors="ignore")
                except OSError:
                    continue
                for iid, n in names.items():
                    if n in body:
                        hits[iid].add(str(fp))
    for i in items:
        if i.id in hits:
            h = sorted(hits[i.id])
            i.evidence.append(f"referenced in {len(h)} file(s)" + (f", e.g. {h[0]}" if h else ""))


# ---------------------------------------------------------------- scan command

def cmd_scan(a: argparse.Namespace) -> int:
    roots = [Path(r).expanduser() for r in (a.root or [str(HOME)])]
    items: list[Item] = []
    stores, blocked = ollama_stores([Path(x).expanduser() for x in (a.store or [])])
    for b in blocked:
        items.append(Item(f"ollama:{b}", "ollama-store", str(b), "(unreadable store)", 0,
                          "unknown-archive-first",
                          ["exists but is not readable as this user — rerun with sudo to inventory it"]))
    owners = scan_ollama(stores, a.check_registry, items)
    scan_hf(items)
    scan_lmstudio(items)
    blob_dirs = [str((s / "blobs").resolve()) for s in stores if (s / "blobs").is_dir()]
    links: dict[str, list[str]] = {}
    store_symlinks(stores, blob_dirs, links)
    managed = stores + hf_hub_dirs() + [HOME / ".lmstudio" / "models"]
    scan_training(roots, managed, items, blob_dirs, links)
    for i in items:
        if i.kind != "ollama-model":
            continue
        overlap: dict[str, int] = {}
        for p in i.paths[1:]:
            for s in owners.get(Path(p).name.replace("-", ":", 1), set()) - {i.store}:
                overlap[s] = overlap.get(s, 0) + allocated(Path(p))
        i.shared_with = sorted(s for s, b in overlap.items() if b >= 1 << 20)
        for s in i.shared_with:
            i.evidence.append(f"{human(overlap[s])} of identical blobs also stored in {s} — "
                              "consolidate stores to free the copy")
        linked = [l for p in i.paths[1:] for l in links.get(str(Path(p).resolve()), [])]
        if linked:
            i.evidence.append(f"{len(linked)} symlink(s) point at its blobs, e.g. {linked[0]} "
                              "— removing it breaks them")
    find_refs(items, [Path(r).expanduser() for r in (a.refs or [])])

    items.sort(key=lambda i: (VERDICT_ORDER.index(i.verdict), -i.bytes))
    report = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": os.uname().nodename,
              "roots": [str(r) for r in roots], "registry_checked": a.check_registry,
              "stores": {"ollama": [str(s) for s in stores], "hf": [str(h) for h in hf_hub_dirs()]},
              "items": [asdict(i) for i in items]}
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=2))
    totals: dict[str, int] = {}
    for i in items:
        totals[i.verdict] = totals.get(i.verdict, 0) + i.bytes
    print(f"stores: ollama={len(stores)} hf={len(hf_hub_dirs())}  items={len(items)}")
    for v in VERDICT_ORDER:
        group = [i for i in items if i.verdict == v]
        if not group:
            continue
        print(f"\n== {v}  ({human(totals[v])})")
        for i in group:
            print(f"  {human(i.bytes):>7}  {i.name}  [{i.kind}, {i.in_use}]  {i.store}")
            for e in i.evidence:
                print(f"           - {e}")
    return 0


# ---------------------------------------------------------------- archive command

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_archive(a: argparse.Namespace) -> int:
    dest = Path(a.dest).expanduser()
    if not dest.is_dir():
        print(f"× destination {dest} does not exist or is not a directory", file=sys.stderr)
        return 2
    report = json.loads(Path(a.from_json).read_text())
    by_id = {i["id"]: i for i in report["items"]}
    missing = [x for x in a.item if x not in by_id]
    if missing:
        print("× unknown item id(s): " + "; ".join(missing), file=sys.stderr)
        return 2
    run = dest / f"model-archive-{time.strftime('%Y%m%d-%H%M%S')}"
    sums, manifest = [], []
    for iid in a.item:
        it = by_id[iid]
        src_paths = [Path(p) for p in it["paths"]]
        if (not a.allow_same_disk and src_paths and src_paths[0].exists()
                and os.stat(src_paths[0]).st_dev == os.stat(dest).st_dev):
            print(f"× {it['name']}: destination is on the same disk as the source — "
                  "archiving there frees nothing. Choose another volume.", file=sys.stderr)
            return 2
        for src in src_paths:
            if not src.exists():
                print(f"! missing, skipped: {src}", file=sys.stderr)
                continue
            # Preserve the absolute layout under the run dir so a restore is a plain copy back.
            target = run / str(src).lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, target, symlinks=True, dirs_exist_ok=True)
                files = [p for p in target.rglob("*") if p.is_file() and not p.is_symlink()]
            else:
                shutil.copy2(src, target)
                files = [target]
            for f in files:
                orig = src / f.relative_to(target) if src.is_dir() else src
                got, want = sha256(f), sha256(orig)
                expect = orig.name.removeprefix("sha256-") if orig.name.startswith("sha256-") else want
                if got != want or got != expect:
                    print(f"× hash mismatch: {orig} → {f}", file=sys.stderr)
                    return 1
                sums.append(f"{got}  {f.relative_to(run)}")
        manifest.append({k: it[k] for k in ("id", "name", "kind", "store", "bytes", "verdict", "evidence")})
        print(f"✓ {it['name']}: copied and verified ({human(it['bytes'])})")
    (run / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    (run / "MANIFEST.json").write_text(json.dumps(
        {"archived": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": os.uname().nodename,
         "items": manifest}, indent=2))
    print(f"\narchive: {run}\nverify later: cd '{run}' && shasum -a 256 -c SHA256SUMS")
    print("Nothing was deleted. Remove originals only after you've confirmed the archive.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="inventory models (read-only)")
    s.add_argument("--root", action="append", help="tree to sweep for training runs and loose weights (default: $HOME; repeatable)")
    s.add_argument("--store", action="append", help="extra Ollama models dir to inventory (repeatable; no tree globbing)")
    s.add_argument("--refs", action="append", help="project tree to grep for model-name references (repeatable)")
    s.add_argument("--check-registry", action="store_true", help="compare Ollama manifests with the registry (network)")
    s.add_argument("--json", help="write the full report here")
    s.set_defaults(fn=cmd_scan)
    r = sub.add_parser("archive", help="copy + SHA-256-verify items to DEST; never deletes")
    r.add_argument("--dest", required=True, help="directory on the archive volume (chosen by the user)")
    r.add_argument("--from-json", required=True, help="report written by `scan --json`")
    r.add_argument("--item", action="append", required=True, help="item id from the report (repeatable)")
    r.add_argument("--allow-same-disk", action="store_true",
                   help="permit a destination on the source disk (tests/staging; frees nothing)")
    r.set_defaults(fn=cmd_archive)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
