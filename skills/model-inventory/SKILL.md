---
name: model-inventory
description: Inventory on-device AI models (Ollama, Hugging Face, LM Studio, MLX, Unsloth and loose .gguf/.safetensors), judge what deleting each would lose — re-downloadable, locally built, fine-tuned, orphaned — and archive to a user-chosen drive with SHA-256 verification before anything is removed. Use when models are eating disk space, before deleting any model, when the user asks "which models do I use", "did I train anything", "is it safe to delete", or when disk-audit hands off its model bucket.
---

# Model Inventory

Local models look like cache and are not. A pulled model costs a long
download to get back; a model you built or fine-tuned cannot be got back at
all. This skill finds every model on the machine, says which is which **with
evidence**, and moves the irreplaceable ones to external storage before anyone
deletes anything. It never deletes.

The scanner is `scripts/model_inventory.py` (stdlib Python, no installs).

## Ground rules

- **Never assume a drive or a path.** The archive destination is always the
  user's choice, asked fresh each time (see Phase 3). Don't reuse one from
  memory without asking.
- **Absence of evidence is not evidence of re-downloadability.** A model is
  `re-downloadable` only when its layer digests match the registry
  (`--check-registry`) or it sits in a hub cache. Everything else is
  `unknown-archive-first` until the user says where it came from.
- **Deletion is the user's act, item by item.** Hand them the exact command
  (`ollama rm <name>`, `hf cache delete`) after the archive is verified. Don't
  run it unprompted.
- **Other accounts' stores need root.** The scan reports them as
  `(unreadable store)`. Give the user a `! sudo …` command to rerun it with
  output written to a records location they choose, then `chmod 644`.
- Reports are records: write them somewhere durable (the user's inbox or
  records folder), never the session scratchpad.

## Phase 1 — Scan (read-only)

```sh
python3 -I <skill>/scripts/model_inventory.py scan --check-registry \
  --refs <project-root> [--refs <another-root>] --json <records-dir>/model-scan.json
```

- `--check-registry` makes one read-only GET per Ollama model to its registry
  and compares layer digests. Without it every Ollama model stays
  `unknown-archive-first`. Skip it only if the user wants zero network.
- `--refs` greps the user's project trees for each model's name — a cheap
  "is anything wired to this" signal. Ask which roots matter; don't guess.
- `--root` (default `$HOME`) is where it sweeps for training runs and loose
  weights. It stays on one filesystem and skips `Library`, `CloudStorage`,
  media libraries, `node_modules`, and the managed stores (inventoried
  separately). File Provider folders (SSH, S3, Drive) can hang `stat()` for
  as long as you let them; never point `--root` into one.
- `--store DIR` adds an Ollama models dir outside the default locations.
  Stores are never found by globbing a tree, for the same hang reason.
- Typical runtime: ~10 s for ~100 GB of models with `--refs` over two
  project trees. If it runs for minutes at 0% CPU, it is stuck on a mount —
  `sample <pid>` shows `lstat`; kill it and narrow `--root`.

What it finds:

| Source | How |
|---|---|
| Ollama | `$OLLAMA_MODELS`, `~/.ollama/models`, every `/Users/*/.ollama/models` (incl. `/Users/Shared`), `--store` — manifests parsed, blobs sized, unreferenced blobs flagged, manifest-list runner variants tied to their parent, `manifests-v2`-only entries surfaced |
| Hugging Face (incl. MLX, Unsloth bases) | `$HF_HUB_CACHE`, `$HF_HOME/hub`, `~/.cache/huggingface/hub` |
| LM Studio | `~/.lmstudio/models`, `~/.cache/lm-studio/models` |
| Training runs | any dir with `adapter_config.json`, `adapter_model.*`, `trainer_state.json`, `training_args.bin`, or `checkpoint-*` |
| Loose weights | `.gguf` / `.safetensors` / large `.bin`/`.pt` outside the managed stores |
| Links | symlinks into a store's blobs (e.g. Unsloth Studio's `.studio_links`) — deleting the model breaks them |
| In use | `loaded now` from Ollama's `/api/ps`; references from `--refs` |

## Phase 2 — Judge

Verdicts, most precious first:

| Verdict | Meaning | Action |
|---|---|---|
| `keep-archive-first` | Adapter layer, training run, or an Ollama model/tag the registry doesn't have at all (`ollama create` output, or a since-removed model) | Archive before any removal. Ask the user what it is. |
| `unknown-archive-first` | Can't prove it's reproducible: no registry check, loose file, unreadable store — or the tag **moved upstream** (registry serves a different build now) | Ask provenance. For a moved tag: the current build re-pulls, this exact one doesn't — usually fine to replace, but the user decides |
| `orphan` | Blobs no manifest references | Check the link evidence; usually safe after `ollama` is restarted and the blobs are still unreferenced |
| `re-downloadable` | Digest-verified registry match, or a hub cache entry | Delete freely if unused; cost is the download |
| `cloud-stub` | Manifest with no local layers (`:cloud` tags) | Nothing to reclaim |

Runner variants (`llamacpp:<64-hex>` and similar, often hidden from
`ollama list`) are part of their parent's pull — listed in its manifest list —
and take the parent's verdict. Never present one as the user's own work.

Also report **cross-store duplicates** (`… of identical blobs also stored in`, only
when ≥ 1 MiB overlaps) — the same
bytes in several stores (e.g. `~/.ollama` and `/Users/Shared/.ollama`).
Consolidating to one store with `OLLAMA_MODELS` frees the copies without
losing anything.

`last used` is deliberately not reported: Ollama keeps no usage log, and
access times on APFS are not reliable enough to decide a deletion on. Say
so if asked; ask the user which models they actually run.

Present one table: name, size, verdict, the evidence line that decided it,
in-use signal. Lead with what can't be got back.

## Phase 3 — Archive (only what the user picks)

1. **Ask for the drive.** List what's mounted, then ask with AskUserQuestion
   (one option per volume, plus "Other"):
   ```sh
   df -h | awk 'NR==1 || ($NF ~ /^\/Volumes\// && $NF != "/Volumes/Recovery")'
   diskutil list external physical
   ```
   Match the mount point column (`$NF`) anchored at `^/Volumes/`: a bare
   `/Volumes/` pattern also matches `/System/Volumes/*` (VM, Preboot, Data)
   and the Recovery volume, none of which are archive targets. If nothing
   external is mounted, say so and stop — don't fall back to an internal
   path. Check free space covers the selection.
2. **Ask for the folder** on that volume (offer a sensible default such as
   `<volume>/model-archive`, but let them change it).
3. Copy and verify:
   ```sh
   python3 -I <skill>/scripts/model_inventory.py archive --dest <chosen-dir> \
     --from-json <records-dir>/model-scan.json --item '<id>' [--item '<id>' …]
   ```
   It refuses a destination on the same disk as the source (that frees
   nothing), copies each item under `model-archive-<timestamp>/` keeping its
   absolute layout, checks every file's SHA-256 against the original — and
   for Ollama blobs, against the hash in the blob's own name — then writes
   `SHA256SUMS` and `MANIFEST.json`. Any mismatch aborts with exit 1.
4. Re-verify from the drive, independently of the script:
   ```sh
   cd '<archive-run-dir>' && shasum -a 256 -c SHA256SUMS
   ```
5. Only now hand the user the removal command per item. For Ollama, restore
   is `OLLAMA_MODELS=<archive-run-dir>/<original store path>` or copying
   `manifests/` and `blobs/` back.

## Phase 4 — Record

State what was archived where, the verify result, what the user chose to
delete, and what was left alone and why. If the user keeps a decision ledger,
log the keep/delete decisions there with the evidence line for each.

## Limits

- Registry check covers Ollama registries that speak the Docker v2 manifest
  API; other hosts report `error:` and stay `unknown-archive-first`.
- Training detection is by marker files. A fine-tune exported straight to a
  single `.gguf` with no run directory shows up as `loose-weights`
  (`unknown-archive-first`), not as training — ask.
- The scan reads as the current user; other accounts need the sudo rerun.
