---
name: corroborate
description: Establish what an uncommitted or unfamiliar change actually IS before committing, discarding, pushing, or merging it — by making the artifact testify rather than reading the diff and inferring. Use when handling work you did not author: a dirty working tree, staged changes of unknown provenance, a stale-looking file, an unexplained deletion, an untracked directory, someone else's WIP, or any sweep that ends in "commit what's finished." Also trigger before discarding anything, before committing a whole dirty tree, when a diff looks like a revert, when a deletion has no explanation, or when the user says "clean this up," "commit what's done," "sync the fleet," or "is this safe to commit." Complements touchstone: touchstone challenges a claim of correctness; corroborate establishes what a change is in the first place.
---

# corroborate

To corroborate is to confirm a story with independent evidence. Not to find the
story plausible — to make something *other than the story* say the same thing.

## What this skill is for

You are about to commit, discard, push, or merge a change you did not author.
The diff shows you *shape*: lines added, lines removed, files touched. Shape is
not meaning. A deletion looks the same whether it was deliberate or accidental.
A file full of additions looks the same whether it is new work or an old copy
written back over new work. An untracked directory looks the same whether it is
a rename in progress or scratch.

Acting on shape is how finished work gets discarded and how reverts get
committed. This skill is the discipline of asking the artifact itself.

**The governing move: every artifact has an authority that is not the diff.**
Find it and consult it before you act.

## The core question

Not *"what does this change look like?"* but:

> **What would this be, and how would I tell that apart from what it resembles?**

Every technique below is a way of answering the second half.

## Techniques, by what you need to know

| Question | Authority to consult | Command |
|---|---|---|
| Is this a move, or a delete plus new files? | The bytes | hash both sides; identical ⇒ rename |
| Is this content new, or a copy of something older? | Git history | `git log -S "<exact string>" -- <path>` |
| Does this data belong in this project? | The project's own validator | run it — projects that have one are telling you to use it |
| Is this finished? | Its test suite | run it; "it looks done" is not a result |
| Was this deletion deliberate? | Why the file arrived | `git log -1 -- <path>` — a file added on purpose and deleted without explanation is an accident until proven otherwise |
| Is this working tree stale? | Timestamps against history | compare file mtime to the commits it lacks |
| Would committing this revert someone? | The diff's *direction* | in `git diff`, `-` is committed and `+` is your tree; a `+` that restores older text is a revert wearing the costume of an edit |
| Is it safe to discard? | Whether git already has it | if the content exists in any commit, discarding loses nothing recoverable |

## The decision rule

Two questions, in order:

1. **Does this content exist anywhere else?** In a commit, on a remote, in a
   backup. If yes, discarding is cheap and reversible. If no, it exists in one
   place and nothing may be done casually.
2. **Does committing it move the repository forward or backward?** Forward
   ⇒ commit. Backward ⇒ discard, and say what it would have reverted.

A change can be large, plausible, and entirely a revert. Size is not direction.

## Anti-patterns

- **`git add -A` on a tree you did not author.** It commits the reverts along
  with the work, and the two are indistinguishable afterwards.
- **Treating untracked as new.** Untracked means git has not been told about
  it — often it is half of a rename whose other half is a pending deletion.
- **Inferring intent from the commit message of the change you are making.**
  You are writing that message. It is not evidence.
- **Asking a model to judge the diff instead of running the thing.** Use a
  local model to *summarise* a large diff; do not let a summary stand in for a
  validator or a test suite that exists and could just be run.
- **Reporting "clean" after a sweep without saying what was left and why.** A
  clean tree that was achieved by discarding someone's work is worse than a
  dirty one.

## Worked examples

Each of these looked like something it was not.

**A rename hiding as a deletion.** Two docs deleted; an untracked directory
containing two files with the same names. Plausible as either a move or a
delete-plus-rewrite. Hashed both sides against `HEAD` — byte-identical, so a
true rename. Committed with `git add -A` of both paths, and git recorded `R`.
Had they differed, it would have been a move *plus* an edit and needed reading.

**New work that was a revert.** Two `SKILL.md` files, one `+149/-16` — every
appearance of substantial new content. `git log -S` on the exact added strings
returned a commit named *"vendor skill set as installed (pre-consolidation)"*.
The working tree was an older vendored copy written back over a consolidation.
Committing it would have destroyed the consolidation; the `+149` was the
give-away only once its provenance was checked. Confirmed twice: the history
search, and the fact that the *installed* skills matched `HEAD`, not the tree.

**Data whose validity was checkable.** An untracked `*-trace.jsonl` in a
project whose CI validates every trace. Rather than guess whether it was real
or scratch, ran the project's own `validate-trace.py`: *"trace loads clean;
every guard passed; projection is total."* That made it committable and proved
CI would accept it.

**Finished work that looked abandoned.** Staged changes two weeks old, no
branch, no PR. Ran the suite: 32 passing, including 4 new tests, with a written
decision entry. Not abandoned — *stranded*, by a stale `.git/index.lock` dated
the day after the work. Committed with the cause recorded, so the timestamps
make sense to whoever reads the log next.

## When a sweep is finished

Report three lists, not one:

1. **Resolved** — with what made each safe.
2. **Left, with reasons** — mid-edit, needs a decision, out of scope. Naming
   the reason is what distinguishes leaving something from missing it.
3. **What you discarded and what it would have done** — never silent.

## Perimeter

This establishes what a change *is*, not whether it is *correct* — for that,
touchstone. It cannot help where the artifact has no authority to consult: no
tests, no validator, no history, content that exists nowhere else. In that case
the honest answer is that it cannot be corroborated, and it belongs on the
"needs a human" list rather than being committed on a hunch.

It also assumes git history is trustworthy. Against a rewritten or force-pushed
history, `git log -S` proves less than it appears to.
