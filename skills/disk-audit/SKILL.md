---
name: disk-audit
description: Audit macOS disk usage end-to-end, explain what is filling the disk, and deliver an opinionated debrief with a tiered, safety-rated cut list. Use when the user reports low disk space, storage mysteries, or wants to find duplicate files.
---

# Disk Audit & Storage Triage (macOS)

You are running a storage triage. The deliverable is a **debrief document** (see
"Debrief format" at the end), not a pile of command output. Diagnose first,
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

## Phase 1 — Establish the shape of the problem

```sh
df -h / /System/Volumes/Data
du -sh ~/Documents ~/Downloads ~/Desktop ~/Library ~/Pictures ~/Movies ~/Music 2>/dev/null
du -sh /Users/* /Applications /private/var/vm 2>/dev/null | sort -rh | head
du -sh ~/Library/* 2>/dev/null | sort -rh | head
```

Note the headline numbers immediately: total used, free, and the top 3
consumers. Tell the user the headline before drilling further.

## Phase 2 — Close the accounting gap

Sum everything visible and compare against `df` used. If the gap exceeds
~20 GB, chase it in this order:

1. **Snapshots:** `tmutil listlocalsnapshots /` and
   `diskutil apfs listSnapshots <dataVolume>`. `com.apple.os.update-*`
   snapshots on the system volume are normal; dated
   `com.apple.TimeMachine.*` snapshots on the Data volume are reclaimable
   (`tmutil deletelocalsnapshots <date>`).
2. **Purgeable space:** `diskutil info <dataVolume>` and
   `system_profiler SPStorageDataType`.
3. **Root-only and other-user directories** (the usual culprit) — have the
   user run:
   ```
   ! sudo du -xsh /System/Volumes/Data/.[A-Z,a-z]* /Users/* 2>/dev/null | sort -rh | head
   ```
4. Drill into whatever that surfaces with
   `! sudo du -xh -d 2 <dir> 2>/dev/null | sort -rh | head -25`.

Do not write the debrief while a large gap is unexplained — an audit that
can't account for the disk isn't done.

## Phase 3 — Categorize what you found

Bucket every major consumer; the bucket determines the safety rating later.

- **Regenerable junk** (delete freely): `~/Library/Caches`, `~/.npm`,
  `~/.cache`, Xcode `DerivedData`, old simulators
  (`xcrun simctl delete unavailable`), Ollama/HuggingFace model caches,
  Docker images, Trash.
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
- **Migration sediment**: nested trees like `Desktop - <name>'s MacBook Pro`
  inside old-desktop archives, often duplicated 3–5 deep. Check whether
  they're evicted (blocks=0) before counting them as local waste.
- **Second user accounts**: treat as a potential full mirror of the primary
  account (photos, music library, dev caches). Ask which account is primary
  and whether the other is still needed.

## Phase 4 — Duplicate detection (cheap → expensive)

1. Size-match candidates first:
   ```sh
   find <dirs> -type f -size +1M -exec stat -f "%z %N" {} + \
     | sort -n | awk '{sz=$1;$1="";if(sz==prev){if(!p)print pl;print sz $0;p=1}else p=0;prev=sz;pl=sz $0}'
   ```
   Same size ≠ same file (audio sample libraries collide constantly) —
   size match only nominates candidates.
2. Hash-confirm candidates with `md5 -q` / `shasum`, or install `jdupes`
   (`brew install jdupes`) for bulk verified dedup. Point it only at
   materialized, user-owned files. Never at `.photoslibrary` internals.
3. Cross-account photo overlap: dump `stat -f "%z %N"` of each library's
   `originals/` (sudo → scratchpad → chmod 644), join on byte size; treat
   multi-MB exact-size matches as strong overlap, hash-verify a sample
   before concluding.
4. Cross-cloud (iCloud/Box/Drive): build per-store manifests of
   (size, hash where cheap) via the relevant MCP tools and report — cloud
   dedup is always report-then-user-decides.

## Phase 5 — The debrief (the deliverable)

Produce it in this exact structure, opinionated and concrete:

### 1. What exists on disk
A table: consumer, size, one-line identity ("362 GB — Photos originals,
video-heavy"). Must sum to within ~5% of `df` used, or say what remains
unexplained and why.

### 2. Why the disk is full
Name the 1–3 *causes* — not a list of folders, a diagnosis. e.g. "Two user
accounts each carrying a full media stack" or "Video originals accumulating
in Photos with no offload". Distinguish local-SSD cost from cloud-quota cost.

### 3. The cut list
Tiered, each item with: size reclaimed, exact command or app procedure, and a
safety rating:

- **Tier 1 — cut now** (regenerable; no data risk): caches, DerivedData,
  simulators, model caches, Trash. Give ready-to-run commands.
- **Tier 2 — cut after one check** (cheap verification): duplicate app
  content, migration sediment, second copies where overlap is provable.
  State the check.
- **Tier 3 — structural** (big wins, needs a decision + verified backup):
  retiring a redundant account, Photos Optimize Storage, relocating a shared
  Logic library. State the decision required, the verification steps, and
  the order of operations (archive → verify → delete, never delete first).

End with a recommendation of what to do *first* and the total realistic
reclaim for each tier. If asked to execute: Tier 1 directly on approval;
Tier 2/3 only item-by-item, with the verification actually performed.
