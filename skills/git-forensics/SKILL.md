---
name: git-forensics
description: Use when git repos show "fatal: unable to read <hash>", when investigating unauthorized git index modifications, when detecting staged file replacements across repos, or when correlating cross-repo git damage from a potential intrusion. Distinct from normal git debugging — this skill is for adversarial git manipulation scenarios.
---

# Git Forensics — Index Corruption and Staged Replacement Detection

## Overview

Git index corruption from adversarial sources leaves specific artifacts. The index file can be
replaced or modified without touching committed history — making it invisible to `git log` while
still poisoning what would be committed next. This skill covers reading those artifacts without
destroying them, identifying attack patterns, and safe repair after forensics are complete.

**Core principle:** The index is evidence. Read it before repairing it.

## When to Use

- `git status` or `git diff` fails with `fatal: unable to read <hash>`
- Committed history looks clean but working state is wrong
- Suspicion of unauthorized process access to `~/Code/` or equivalent
- Multiple repos showing the same failure pattern simultaneously
- Staged content doesn't match what you expect to have staged

## Quick Reference

```bash
# 1. Detect corruption across multiple repos
for repo in /path/to/repo1 /path/to/repo2; do
  result=$(cd "$repo" && git status --short 2>&1 | head -1)
  echo "$(basename $repo): $result"
done

# 2. Read raw index WITHOUT failing on missing blobs
#    (outputs: mode hash stage filename — hash may be unreadable, entry is still visible)
cd /affected/repo && git ls-files --stage 2>/dev/null

# 3. Compare staged index vs HEAD tree to detect replacements
cd /affected/repo
git ls-files --stage 2>/dev/null | awk '{print $2, $4}' | sort > /tmp/staged.txt
git ls-tree -r HEAD 2>/dev/null | awk '{print $3, $4}' | sort > /tmp/head.txt
diff /tmp/staged.txt /tmp/head.txt
# Lines with < are staged but not in HEAD (additions/replacements)
# Lines with > are in HEAD but not staged (deletions)

# 4. Read a blob's content from any repo that has it
#    (blobs are content-addressed — same content = same hash across all repos)
cd /repo/that/might/have/it && git cat-file -t "$BLOB_HASH" 2>/dev/null && git cat-file -p "$BLOB_HASH"

# 5. Check if a .DS_Store contaminated .git/refs
git fsck --no-dangling 2>&1 | grep -i "badRefName\|DS_Store"
find .git/refs -name ".DS_Store"  # remove these — they break ref parsing

# 6. Repair index after forensics are complete
git read-tree HEAD  # rebuilds index from HEAD tree; does NOT touch working tree files
```

## Attack Pattern: Staged Repository Replacement

The highest-severity pattern: an adversarial process replaces the entire `.git/index` with a
different project's file tree. From git's perspective, every file in the repo appears deleted
and every file from the injected project appears added.

**Detection:**
```bash
git ls-files --stage 2>/dev/null | head -20
# If filenames don't match this repo's structure → replacement attack
```

**Confirmation:** Compare staged filenames against known project files. If staged content is
from a completely different project, the index was replaced wholesale.

**Why it works:** The `.git/index` is a plain binary file. Any process with filesystem write
access can replace it. The replacement doesn't appear in `git log`. It only fires when
`git status` or `git diff` is run — or when an unsuspecting `git commit` is executed.

## Cross-Repo Correlation

When multiple repos share the **same missing blob hash**, the writes were coordinated:
```
praxis-aegis:  fatal: unable to read b6651396...  ← same
context-synapse: fatal: unable to read b6651396...  ← same
secure-pride:  fatal: unable to read b6651396...  ← same
```

A shared hash means a single blob object was being written simultaneously into multiple repos'
object stores when the process was killed. The write never completed; the index entries pointing
to it remain as evidence of the intended operation.

Different hashes across repos indicate different write stages — the process was further along in
some repos than others, revealing write ordering and priority.

## CLAUDE.md Semantic Attack Vector

If the staged index contains a CLAUDE.md blob, read it:
```bash
# Get the staged CLAUDE.md hash
CLAUDE_BLOB=$(git ls-files --stage 2>/dev/null | grep "CLAUDE.md" | awk '{print $2}')
# Try to read it (may exist in a sibling repo's object store)
cd /sibling/repo && git cat-file -p "$CLAUDE_BLOB" 2>/dev/null
# Compare hash to HEAD
git ls-tree HEAD CLAUDE.md
```

A staged CLAUDE.md from a different project would cause future AI sessions in the repo to
operate under the wrong project context — a semantic attack on AI governance rather than
a code attack. Check: does the staged CLAUDE.md match HEAD? Does it match another project's
CLAUDE.md? Does the content differ from what you expect?

## Evidence Preservation

Before repairing any index:
1. Record the missing blob hash(es) — they are the evidence
2. Run `git ls-files --stage 2>/dev/null > /tmp/forensic-index-$(basename $PWD).txt` for each repo
3. Run `git fsck --no-dangling 2>&1 >> /tmp/forensic-index-$(basename $PWD).txt`
4. Note shared hashes across repos and the correspondence between hash and filename

After preservation, repair with `git read-tree HEAD`. The missing objects remain missing
(they were never written) — repair only replaces the corrupted index pointers.

## What `git read-tree HEAD` Does and Does NOT Do

- **Does**: Rebuilds `.git/index` from HEAD's committed tree. Working tree files untouched.
- **Does NOT**: Modify any committed objects, blob content, or working tree files.
- **Does NOT**: Delete the missing objects (they were never written; they stay missing in fsck).
- Safe to run on a repo with missing blob objects — it bypasses the corrupted index entirely.

## Common Mistakes

| Mistake | Consequence |
|---------|-------------|
| Running `git reset HEAD` before reading index | May fail with same missing-blob error; also loses index state |
| Removing `.DS_Store` from `.git/refs/` without checking fsck first | Fix the symptom; may miss deeper corruption |
| Assuming clean `git log` means clean repo | Index and working tree are separate from commit history |
| Repairing index before recording staged content | Loses the only artifact showing what was staged |
| Checking only the affected repo | Cross-repo correlation requires checking all repos in the workspace |

## Origin: Validated Against 2026-05-20 Incident

This skill was written after hands-on forensics of a coordinated 7-repo git index
replacement by the OpenAI Codex VS Code extension. The `git ls-files --stage` approach,
cross-repo blob correlation, and CLAUDE.md semantic attack pattern were all identified
during that investigation. The RED phase is documented in:
`~/.claude/projects/-Users-daedalus/memory/incident-20260520.md`
