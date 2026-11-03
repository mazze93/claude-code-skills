---
name: muster-triage
description: >-
  Classify stale or unmerged jj/git bookmarks by content (stable patch-id), not
  ahead-count or tip-tree diffs, then touchstone the class before any archive or
  delete. Use when ws muster reports stale unmerged tips, when consolidating
  branches into main, when a tip looks stranded but might already be on trunk,
  when retiring bookmarks to archive/* tags, or when the user says triage
  bookmarks, de-puzzle muster, retire to archives, or ask whether a branch is
  safe to abandon. Complements corroborate (what is this change) and touchstone
  (is this class claim true). Never auto-abandon; per-bookmark OK required.
---

# muster-triage

Stale bookmarks lie in two directions: they look stranded when the patch already
landed under another SHA, and they look mergeable when trunk has moved past an
alternate path. This skill is the standard triage for that puzzle.

**Oracle:** `git patch-id --stable` (via `scripts/ops/jj_triage.py`).  
**Not an oracle:** `git cherry` (false `+ UNIQUE` on PR-merged twins), raw
`ahead=N`, tip-vs-trunk blob diffs alone.

## When to use

- `ws muster` / `jj_muster` shows `stale unmerged`
- Consolidating feature branches into `main` without stranding work
- User asks to retire / archive / abandon bookmarks
- A tip shares a subject with trunk but SHAs differ

## Workflow (do not skip)

### 1. Run the automated classifier

```bash
# fleet (default de-puzzle surface)
scripts/ws triage
# or one bookmark
python3 scripts/ops/jj_triage.py --repo PATH --bookmark NAME
# JSON for agents
python3 scripts/ops/jj_triage.py --fleet --json
```

`ws muster` embeds the same one-line class on stale hits by default
(`MUSTER_TRIAGE=1`). Prefer the class string over the old bare description.

### 2. Read the class

| Class | Meaning | Default next step |
|---|---|---|
| `on_trunk_by_content` | Every non-merge commit's patch-id is on trunk | Retire → `archive/<name>` tag, then delete bookmark |
| `likely_superseded` | Unique patches, but trunk rewrote most paths — **or** subject twin with patch-id drift and **no** tip-vs-twin residual paths | Retire → archive tag; **do not merge** |
| `unique` | Real content not on trunk — including subject twin **with residual paths** (tip-only files / diverged blobs) | Salvage `residual_paths`, then decide — **human OK** |
| `empty` | Merge-only or already contained | Retire or delete |

Subject-prefix match alone is **not** retire-safe. After a drifted twin is found, triage diffs tip paths against twin and trunk blobs; leftovers become `residual_paths`.

Classify an archive tag with `--tip archive/… --bookmark <former-name>` (`--tip` wins as the rev; `--bookmark` is the label). Annotated tags are peeled to commits.

### 3. Touchstone the class claim

Load `/touchstone`. The claim to assay is exactly the classifier's
`touchstone_claim` field, e.g.:

> Bookmark X is correctly classed `on_trunk_by_content` relative to origin/main;
> retiring it will not strand unique work.

Probe at least:

1. **Verifier blind spot** — spot-check one “matched” commit: does trunk twin
   actually share the patch-id? (`git show A \| git patch-id --stable` vs twin)
2. **Composition / divergence** — if local tip ≠ `origin/<bookmark>`, classify
   **both** tips (tag both if retiring)
3. For `likely_superseded` / `unique`: would merging the tip *regress* a path
   trunk already advanced? (one concrete path)

If touchstone **does not hold**, stop. Do not archive. Escalate to the human.

### 4. Report, then wait

Print a table: bookmark · class · tip · suggested archive tag · action.  
**Abandon / delete only with explicit OK per bookmark.** Golden Road: no
auto-answer on destructive ops.

### 5. Retire (only after OK)

Blog convention — annotated tags, then delete:

```bash
git tag -a "archive/<bookmark>" <tip> -m "Archive of <bookmark> before deletion on YYYY-MM-DD. <class reason>"
git push origin refs/tags/archive/<bookmark>
jj bookmark delete <bookmark>          # jj repos
jj git push --deleted                  # or: git push origin --delete <bookmark>
```

Divergent local vs remote tips → two tags (e.g. `archive/<name>` +
`archive/<name>.jj-local`).

Re-run `scripts/ws muster` — expect exit 0 if that was the last hit.

## Anti-patterns

- Leading with `ahead=N` or tip-tree file mismatches as proof of stranded work
- Trusting `git cherry` over patch-id
- Merging `likely_superseded` tips “to be safe”
- Deleting without an `archive/*` tag when the tip is not already an ancestor
- Bulk-abandon without per-bookmark OK
- Skipping touchstone because the classifier “looked sure”

## Complements

| Skill | Role |
|---|---|
| **corroborate** | What is an unfamiliar *working-tree* change |
| **touchstone** | Is the triage *class claim* true |
| **muster-triage** | Is this *bookmark tip* stranded, superseded, or already landed |

## Automation home

- Classifier: `~/Projects/scripts/ops/jj_triage.py`
- Muster embed: `~/Projects/scripts/ops/jj_muster.sh` (`MUSTER_TRIAGE=1`)
- CLI: `scripts/ws triage` [args…]
- Salvage: `jj_triage.py --repo DIR --tip REF --salvage-to DIR` (writes blobs; does not open a trunk PR)

## Perimeter (known)

- Unrelated same-blob coincidence on trunk can clear a residual.
- Short subjects (`<24` chars) skip twin matching.
- Multi-commit bookmarks are classified per ahead-commit.
- Merge commits are skipped on the patch-id path.
- Submodules/gitlinks are skipped.
- `--salvage-to` exports files only — landing on trunk is a separate human/PR step (see Aletheia Class-Closure recovery).
- Wrong twin after a title collision is mitigated by requiring shared changed paths; not eliminated.