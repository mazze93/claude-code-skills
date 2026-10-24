---
name: disk-audit
description: Audit macOS disk usage end-to-end, explain what is filling the disk, and deliver an opinionated debrief with a tiered, safety-rated cut list. Use when the user reports low disk space, storage mysteries, or wants to find duplicate files.
---

# Disk Audit & Storage Triage (macOS)

You are running a storage triage. The deliverable is a **debrief document** (see
"Phase 5 — The debrief"), not a pile of command output. Diagnose first,
recommend second, delete **nothing** without explicit per-item approval.

## Ground rules

- **Never delete on a hunch.** Photo libraries, message archives, and anything
  under another user account require verified overlap (size match, then hash)
  before you even *propose* removal.
- **Every `du` run as a normal user lies on a multi-user Mac.** Home
  directories are mode 700/750, so other accounts silently undercount (this
  has hidden 200+ GB before). If `sum(visible) < df used`, suspect exactly
  this before anything exotic.
- **You cannot sudo interactively.** When root is needed, hand the user a
  ready-to-paste command prefixed with `!` so it runs in-session and the
  output lands in the conversation. Have root-owned output files written to
  the scratchpad and `chmod 644`'d so you can read them.
- **iCloud placeholders skew everything.** Evicted files have large logical
  size but 0 allocated blocks (`stat -f "%z %b"`). `du` shows them tiny;
  `find`+`stat %z` shows them huge. Never hash or copy evicted files in bulk —
  it forces re-download. Local dedup targets *materialized* files only;
  evicted duplicates waste **iCloud quota**, not SSD, and are cleaned in the
  cloud instead.
- **One unit for reconciliation: bytes.** `df -h` prints GiB, `diskutil`
  prints GB — the same volume reads 800Gi in one and 859 GB in the other, a
  7% "gap" that is pure unit drift. Take the used figure as raw bytes from
  `diskutil info` and convert every `du` total to bytes (`du -sk` × 1024)
  before comparing.
- **APFS clones and hardlinks distort duplicate math.** `du` counts each clone
  in full even though clones share blocks, so two hash-identical clones are a
  "duplicate" that frees nothing when removed. Hardlinks go the other way:
  `du` counts them once, a `find`+`stat %z` manifest counts every link.
  Before promising a dedup reclaim, confirm the copies are independent.
- **Never block the session on a slow scan.** A whole-disk `du` takes minutes.
  Run it in the background from the start and do the fast checks (`df`,
  snapshots, `diskutil`) while it runs.

## Phase 1 — Establish the shape of the problem

Start the slow scans in the background first (expect 2–10 minutes on a
large, multi-account disk):

```sh
du -xsk /Users/* /Applications /Library /private/var /opt /usr/local 2>/dev/null | sort -rn
du -xsh ~/* ~/.[!.]* 2>/dev/null | sort -rh | head -30
du -xh -d 2 ~/Library 2>/dev/null | sort -rh | head -30
```

The second line is deliberately exhaustive: hidden dot-directories
(`~/.ollama`, `~/.cache`, `~/.npm`, `~/.cargo`, …) routinely hold 100+ GB and
a hand-picked folder list misses them. The third goes two levels deep because
`~/Library` is usually the largest single consumer and one level
(`Application Support`) is too coarse to act on.

While those run (seconds):

```sh
df -h / /System/Volumes/Data
diskutil info /System/Volumes/Data | grep -E 'Volume Used Space|Container Free Space'
diskutil apfs list | grep -E 'Name:|Role|Capacity Consumed'
```

Note the headline numbers immediately: total used, free, and the top 3
consumers. Tell the user the headline before drilling further.

## Phase 2 — Close the accounting gap

Sum everything visible (in bytes) and compare against the Data volume's used
bytes. If the gap exceeds ~20 GB, chase it in this order:

1. **Snapshots:** Time Machine snapshots live on the *Data* volume, so list
   that, not `/`:
   `tmutil listlocalsnapshots /System/Volumes/Data` and
   `diskutil apfs listSnapshots /System/Volumes/Data`.
   `com.apple.os.update-*` snapshots on the system volume are normal; dated
   `com.apple.TimeMachine.*` snapshots on the Data volume are reclaimable
   (`tmutil deletelocalsnapshots <date>`).
2. **Purgeable space:** `diskutil info` often omits it on recent macOS;
   `system_profiler SPStorageDataType` reports it but takes ~30 s — background it.
3. **Root-only and other-user directories** (the usual culprit) — have the
   user run:
   ```
   ! sudo du -xh -d 2 /Users/* /System/Volumes/Data/.[!.]* 2>/dev/null | sort -rh | head -40
   ```
   (`.[!.]*` matches every dot-entry except `.` and `..`, including names that
   start with a digit or underscore.)
4. Drill into whatever that surfaces with
   `! sudo du -xh -d 2 <dir> 2>/dev/null | sort -rh | head -25`.

Do not write the debrief while a large gap is unexplained — an audit that
can't account for the disk isn't done.

## Phase 3 — Categorize what you found

Bucket every major consumer; the bucket determines the safety rating later.
Rate each item on two axes: **data risk** (can anything irreplaceable be lost)
and **restore cost** (what it takes to get it back).

- **Regenerable, free to restore** (delete freely): `~/Library/Caches`,
  Xcode `DerivedData`, Trash, and package-manager caches — dry-run first where
  a dry run exists:
  - Homebrew: `brew cleanup --prune=all -n` (then without `-n`)
  - npm: `~/.npm` → `npm cache clean --force`
  - uv / pip: `~/.cache/uv` → `uv cache clean`; `pip cache purge`
  - pnpm: `pnpm store prune`
  - Build output in project trees: `node_modules`, `.venv`, `target/` —
    find with `find <projects-root> -type d \( -name node_modules -o -name .venv -o -name target \) -prune`
    and list per project; the user picks.
- **Regenerable, costly to restore** (inventory first, user picks per item):
  - On-device AI models — Ollama, Hugging Face, Unsloth, LM Studio, MLX,
    llama.cpp. **Hand off to the `model-inventory` skill**: it finds every
    store (including other accounts and `/Users/Shared`), detects
    locally-built or fine-tuned models that *cannot* be re-pulled, and
    archives to a user-chosen drive before anything is removed. Never treat a
    model directory as plain cache.
  - Docker / OrbStack / VM disk images: `docker system df`, OrbStack's own
    UI; large images under `~/Library/Containers` and `~/Library/Group Containers`.
  - Xcode `iOS DeviceSupport` and old simulators
    (`xcrun simctl delete unavailable`); `Archives` only if no build there
    still needs symbolication.
- **Not junk despite the location**: `~/Library/Application Support/MobileSync/Backup`
  (device backups), `~/Library/Messages`, `~/Library/Mail`. Report size; never
  put them on a cut list without the user naming them.
- **Redundant Apple content**: `~/Music/Logic Pro Library.bundle` is installed
  *per user home* (~20–50 GB each) — on multi-account Macs it duplicates;
  Logic can relocate it to a shared path (Logic Pro → Settings → Sound
  Library).
- **Media libraries** (`Photos Library.photoslibrary`): break down
  `originals/` by extension (`find … -type f | sed 's/.*\.//' | tr 'A-Z'
  'a-z' | sort | uniq -c | sort -rn`). Videos (.mov/.mp4) and RAW (.dng)
  dominate size. Remedies live *inside Photos*: Utilities → Duplicates, and
  iCloud "Optimize Mac Storage" — never manipulate the bundle's files
  directly.
- **Sync-client sediment**: File Provider clients (Proton Drive, Google Drive,
  Dropbox) leave dated or numbered copies of their root folder in
  `~/Library/CloudStorage` after a reset. They can hold edits that never
  uploaded — compare against the live root and the web copy before proposing
  removal.
- **Migration sediment**: nested trees like `Desktop - <name>'s MacBook Pro`
  inside old-desktop archives, often duplicated 3–5 deep. Check whether
  they're evicted (blocks=0) before counting them as local waste.
- **Second user accounts**: treat as a potential full mirror of the primary
  account (photos, music library, dev caches, model stores). Ask which account
  is primary and whether the other is still needed.

## Phase 4 — Duplicate detection (cheap → expensive)

1. **Use a tested tool, not a one-liner.** `fclones` (`brew install fclones`)
   or `jdupes` both prefilter by size, then hash. Point them only at
   materialized, user-owned files — never at `.photoslibrary` internals.
   ```sh
   fclones group <dirs> -s 1M > <scratchpad>/dupes.txt
   ```
   Same size ≠ same file (audio sample libraries collide constantly); only a
   hash match is a duplicate.
2. **Prefer cloning to deleting.** `fclones dedupe` replaces duplicates with
   copy-on-write reflinks: every path keeps working, the bytes are stored
   once, and nothing is lost. Offer this as the default Tier 2 remedy;
   deletion is the fallback when the user wants the paths gone too.
   Upstream docs describe reflink dedupe generically and don't name APFS, so
   **prove it on first use**: `fclones dedupe --help` for the input and
   dry-run syntax, then dedupe one known pair and confirm with
   `df` before/after that space actually came back.
3. **Content-addressed stores dedup by filename.** Model blob stores
   (`sha256-<hash>` files in Ollama, Hugging Face `blobs/`) need no hashing:
   `comm -12` over the sorted filenames of two stores is an exact overlap.
4. **Cross-account photo overlap:** dump `stat -f "%z %N"` of each library's
   `originals/` (sudo → scratchpad → chmod 644), join on byte size; treat
   multi-MB exact-size matches as strong overlap, hash-verify a sample
   before concluding.
5. **Cross-cloud** (iCloud/Box/Drive): build per-store manifests of
   (size, hash where cheap) via the relevant MCP tools and report — cloud
   dedup is always report-then-user-decides.

## Phase 5 — The debrief (the deliverable)

Produce it in this exact structure, opinionated and concrete:

### 1. What exists on disk
A table: consumer, size, one-line identity ("362 GB — Photos originals,
video-heavy"). Must sum to within ~5% of the Data volume's used bytes, or say
what remains unexplained and why.

### 2. Why the disk is full
Name the 1–3 *causes* — not a list of folders, a diagnosis. e.g. "Two user
accounts each carrying a full media stack" or "Video originals accumulating
in Photos with no offload". Distinguish local-SSD cost from cloud-quota cost.

### 3. The cut list
Tiered, each item with: size reclaimed, exact command or app procedure, and a
safety rating:

- **Tier 1 — cut now** (regenerable, free to restore; no data risk): caches,
  DerivedData, package-manager caches, Trash. Give ready-to-run commands.
- **Tier 2 — cut after one check** (cheap verification): costly-to-restore
  regenerables (models, images, simulators — each with its inventory step),
  duplicate content (clone-dedup first), sync-client and migration sediment,
  second copies where overlap is provable. State the check.
- **Tier 3 — structural** (big wins, needs a decision + verified backup):
  retiring a redundant account, Photos Optimize Storage, relocating a shared
  Logic library. State the decision required, the verification steps, and
  the order of operations (archive → verify → delete, never delete first).

End with a recommendation of what to do *first* and the total realistic
reclaim for each tier. If asked to execute: Tier 1 directly on approval;
Tier 2/3 only item-by-item, with the verification actually performed.

### 4. Save it and diff against last time
Ask the user where debriefs should live (don't assume a path), then write
the debrief there as `disk-audit-<YYYY-MM-DD>.md` with the raw byte totals per
consumer in a table. On later runs, ask for that location again (or recall it
from memory if the user has saved it), load the newest prior debrief, and add a
**Growth since <date>** section: which consumers grew, by how much. One audit
says what is big; two say what is *growing*, which is usually the real cause.
