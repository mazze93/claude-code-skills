"""Input provenance manifest for a core-sample build.

Hashes are integrity checks, not signatures or independent proof that the
underlying events occurred. Anchor the manifest in a signed Git commit or a
trusted external transparency log for stronger provenance claims.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ANNOTATIONS = (
    "session.json", "exchanges.json", "calls_manual.json", "failures.json",
    "findings.json", "sources.json", "deliverables.json", "open_items.json",
)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(folder: Path) -> dict:
    """Hash every present original input, rejecting symlinks and escape paths."""
    folder = Path(folder).resolve()
    candidates = [folder / name for name in ANNOTATIONS]
    raw = folder / "raw"
    if raw.exists():
        candidates += [p for p in raw.rglob("*") if p.is_file() or p.is_symlink()]
    evidence = {}
    for path in sorted(set(candidates)):
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_symlink() or not path.is_file() or folder not in path.resolve().parents:
            raise ValueError(f"unsafe evidence path: {path}")
        rel = path.relative_to(folder).as_posix()
        evidence[rel] = {"sha256": _digest(path), "bytes": path.stat().st_size}
    return evidence


def toolkit_fingerprint() -> str:
    """Fingerprint the code that interprets input, not merely its data."""
    root = Path(__file__).resolve().parent.parent
    h = hashlib.sha256()
    for path in sorted((root / "core_sample").rglob("*.py")):
        h.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        h.update(bytes.fromhex(_digest(path)))
    hook = root / "hooks" / "ledger_hook.py"
    if hook.is_file():
        h.update(b"hooks/ledger_hook.py\0")
        h.update(bytes.fromhex(_digest(hook)))
    return h.hexdigest()


def write_manifest(folder: Path, destination: Path, version: str, source: dict) -> dict:
    current = fingerprint(folder)
    if source != current:
        raise ValueError("input evidence changed during build; outputs are not reproducible")
    session = json.loads((Path(folder) / "session.json").read_text(encoding="utf-8"))
    result = {
        "format": "core-sample-provenance-v1",
        "session_id": session["session_id"],
        "version": version,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "toolkit_sha256": toolkit_fingerprint(),
        "inputs": source,
        "limitations": "SHA-256 detects changes relative to this manifest; it is not signed or externally anchored.",
    }
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def verify_manifest(folder: Path, manifest_path: Path) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("format") != "core-sample-provenance-v1":
        raise ValueError("unrecognized provenance manifest format")
    actual = fingerprint(folder)
    expected = manifest["inputs"]
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        added = sorted(set(actual) - set(expected))
        changed = sorted(k for k in set(actual) & set(expected) if actual[k] != expected[k])
        raise ValueError(f"evidence integrity mismatch: missing={missing}, added={added}, changed={changed}")
    if toolkit_fingerprint() != manifest["toolkit_sha256"]:
        raise ValueError("toolkit code digest changed since compilation")
    return manifest
