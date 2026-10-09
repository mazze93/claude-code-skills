---
name: core-sample
disable-model-invocation: true
description: Capture a Claude session as an analysis-ready ledger — every tool call with its outcome (including failures the tool never flagged), a typed failure log, prompts, findings, sources, deliverables and open items — then build SQLite + CSV and a navigable Excel workbook with charts. Use whenever the user asks to record, log, audit, export or "make a spreadsheet of" a session or conversation, wants tool use or failures treated as data, asks what went wrong or what caught it, wants to compare sessions, or wants hooks so tool results survive compaction. Also use near the end of a long build session when a post-mortem, field note or essay needs evidence.
hooks:
  PostToolUse:
    - matcher: "*"
      hooks:
        - type: command
          command: python3 "$HOME/.claude/core-sample/toolkit/hooks/ledger_hook.py"
  PostToolUseFailure:
    - matcher: "*"
      hooks:
        - type: command
          command: python3 "$HOME/.claude/core-sample/toolkit/hooks/ledger_hook.py"
  PreCompact:
    - hooks:
        - type: command
          command: python3 "$HOME/.claude/core-sample/toolkit/hooks/ledger_hook.py"
  SessionEnd:
    - hooks:
        - type: command
          command: python3 "$HOME/.claude/core-sample/toolkit/hooks/ledger_hook.py"
          timeout: 10
---

# core-sample

A core sample is a cylinder drilled out of the ground: every layer in order,
nothing smoothed over. This skill drills one out of a working session. The
output is a **ledger** (SQLite + CSV) you can query across sessions, and a
**workbook** a person can read: index, KPI tiles, charts that each answer one
question, and cross-linked tables.

The governing idea: **a claim about the session is only as good as the record
it points at.** Tool calls and their failures are first-class rows. Where the
record has a gap (a call whose result was never kept), the gap is a row too,
never filled in from memory.

**Evidence identity:** transcript and hook records are reconciled using Claude's
`tool_use_id`, with contradictions rejecting the build. Unkeyed export/manual
mentions live in `source_mentions` (SQLite + CSV); uniquely matching mentions
corroborate one execution, and ambiguous overlaps are excluded from distinct
execution counts rather than being assigned an invented identity. The count
of ambiguous mentions is preserved in the session notes. If exchange numbering
cannot be established from the available record, annotate it explicitly.

## What you produce

```
<session-folder>/
  session.json  exchanges.json  failures.json  findings.json
  sources.json  deliverables.json  open_items.json  calls_manual.json   ← you write these
  raw/transcript.jsonl  raw/hook-ledger.jsonl  raw/export/*.txt         ← captured sources
  ledger/core-sample.sqlite  ledger/csv/*.csv  ledger/<id>_session-record_vX.Y.Z.xlsx
```

The toolkit lives in `scripts/` beside this file (`scripts/core_sample`, a
stdlib + openpyxl Python package). Run it from `scripts/`:
`python3 -m core_sample <init|capture|build|query> …`. If this skill's
`scripts/` isn't on disk (some surfaces sync only SKILL.md), look for
`$HOME/.claude/core-sample/toolkit/` next; if neither exists, say so and ask
the person for the toolkit zip rather than rewriting it from this page.

## Explicit capture lifecycle — required

**No background/global capture.** This skill is user-invoked only
(`disable-model-invocation: true`), so Claude cannot select it automatically.
In the `rigor` plugin, invoke `/rigor:core-sample start` at the beginning and
`/rigor:core-sample compile` when ready to close the capture.
The four hooks above are skill-local:
Claude Code registers them only when you invoke core-sample, for the rest of
that Claude session. Their handler is **fail-closed**; even once registered it
writes no tool payloads until explicitly armed for that exact `session_id`.

Install the reviewed toolkit once on the machine running Claude Code, **not**
in a cloud container you cannot access:

```bash
mkdir -p "$HOME/.claude/core-sample/toolkit"
cp -R <repo>/skills/core-sample/scripts/core_sample "$HOME/.claude/core-sample/toolkit/"
mkdir -p "$HOME/.claude/core-sample/toolkit/hooks"
cp <repo>/skills/core-sample/scripts/hooks/ledger_hook.py "$HOME/.claude/core-sample/toolkit/hooks/"
```

Do **not** register these hooks in global `~/.claude/settings.json` or the
plugin-wide `hooks.json`. Remove any earlier always-on core-sample hook entries,
without modifying unrelated hooks.

1. **Begin at the start of the session:** invoke **core-sample** with **start**.
   The skill must use Claude Code's **Bash tool** to execute **exactly** this command:

   ```bash
   python3 "$HOME/.claude/core-sample/toolkit/hooks/ledger_hook.py" arm
   ```

   A successful `PostToolUse` event for this exact command is the authorization
   to start recording. The command prints an arm-request marker; it does not
   create a global state file. The event supplies the authoritative session ID.
   A direct terminal invocation outside Claude Code **does not arm anything**.
   Check for `CaptureStarted` in
   `$HOME/.claude/core-sample/ledger/<session_id>.jsonl`; do not assert capture
   is enabled merely because the Bash command printed success.

2. **Capture continues** only within the armed session. Separate Claude sessions
   require their own explicit arm. Hook payloads are redacted and limited to
   20,000 characters per string; they are not a byte-complete transcript.

3. **Compile at the end:** invoke **core-sample** with **compile**. **Before**
   running any export, analysis or build, execute this exact command via Bash:

   ```bash
   python3 "$HOME/.claude/core-sample/toolkit/hooks/ledger_hook.py" disarm
   ```

   The successful matching hook event records `CaptureStopped` and disables
   storage for this session. Compilation calls and subsequent tool results
   remain out of the capture. Confirm the stop event before building.

4. With capture stopped, copy the session's private hook ledger into the
   selected session folder via `core_sample capture --hook-ledger ...`, add
   available transcript/export evidence, annotate and `core_sample build`.
   The `session.json` session ID must match the captured hook filename.
   Never delete raw evidence after building. **If compilation fails, capture
   stays off** until another explicit arm request.

5. **SessionEnd** independently disables capture; it never silently arms a
   subsequent session. Skill-local hooks remain *registered* until the Claude
   session ends (Claude Code cannot remove an individual registered hook
   mid-session); after disarm their processes are inert and store no payload.
   This distinction is important: **capture off**, not "hook unregistered."

Raw transcript archives are **OFF by default**. `PreCompact`/ `SessionEnd`
events still enter the hook ledger while armed. Set
`CORE_SAMPLE_ARCHIVE_RAW=1` deliberately in the Claude Code environment to
enable transcript snapshot copies into `$CORE_SAMPLE_HOME/archive/`. These
copies are **UNREDACTED**, confidential and excluded from public repositories,
irrespective of ledger redaction. Prefer a private encrypted location with a
retention policy. Hook failure logs and derived records also require review.

Official Claude Code hooks reference:
https://code.claude.com/docs/en/hooks

## Step 1 — Find out what record exists (do this first, it decides everything)

Tool **results** survive in only some places. Check, in this order:

| Source | Has results? | Where |
|---|---|---|
| Hook ledger | ✅ live, per call | `$CORE_SAMPLE_HOME/ledger/<session_id>.jsonl` (default `~/.claude/core-sample`) |
| Transcript | ✅ for what it still holds | `~/.claude/projects/<cwd-slug>/<session_id>.jsonl`; archived copies in `$CORE_SAMPLE_HOME/archive/` |
| Conversation export | ❌ calls only | `read_conversation` (claude.ai) — page by page |

Compaction matters: in at least one environment, the transcript file kept
only post-compaction entries, so every earlier result was gone. If the session
was compacted and there's no hook ledger or archive, the pre-compaction calls
can only be recovered from the export, and they enter the ledger as
`unrecorded`. Say that plainly in `session.json` notes; it shows up on the
index and in the "how much can anyone check?" chart. Don't guess outcomes.

Reading the export: each `read_conversation` page is capped by size, not turn
count, so a large turn comes back alone and is saved to a tool-results file.
Copy saved pages into `raw/export/`. Pages that come back inline can't be
saved by a tool. Transcribe their calls into `calls_manual.json` (tool,
description, abridged input) and say in the notes that you did.

## Where the session folder lives

In a git repository the person owns, committed as you go: never a scratchpad,
`/tmp` or another temporary directory. The ledger is evidence. A record that
dies with the container is the failure this skill exists to prevent, and the
person has had to ask for this more than once. Put the derived record (annotations,
CSV, SQLite, workbook) in the repo the work belongs to, outside any deployed
folder. Keep `raw/` (transcripts, export pages) out of public repos: it holds
everything the session touched, memory contents included. Add a `.gitignore` for `raw/` and
deliver it to the person privately. Commit after each build, and run
`git check-ignore -v` on the outputs first: repos often ignore generic folder names (`out/`, `logs/`), and an
ignored record commits nothing without any error. Before a public commit, grep the built CSVs for private topics. Your
own scan commands become recorded tool calls, so list any such words, one per line, in `raw/redact_terms.txt`
(private by construction, since `raw/` is never committed). Don't put them in `session.json`: that file is committed.

## Step 2 — Scaffold and capture

```bash
cd <skill>/scripts
python3 -m core_sample init  <session-folder> --title "<what the person calls this work>"
python3 -m core_sample capture <session-folder> --transcript <path.jsonl> [--hook-ledger <path>] [--export <pages…>]
```

Then set `session.json`: `transcript_first_exchange` (the exchange the
transcript file starts in; mid-exchange after compaction) and
`transcript_exchange_offset` (the exchange number of the transcript's first
prompt). Exchanges from the export map as `turn // 2 + 1`; override with
`export_turn_map` if turns don't alternate.

## Step 3 — Write the annotations

Read `references/annotations.md` for every file's shape. What matters most:

**Exchanges** — one per prompt that started work (the person's, or a hook
like a stop-hook that made you act). The prompt is verbatim. The response is
your one-paragraph summary, marked as yours. Transcript prompts overwrite your
text at build time, because they're verbatim.

**Failures** — the heart of it. Log everything that went wrong at any layer,
not only tool errors: `environment`, `tool-use`, `artifact`, `claim`,
`perception`, `process`, `record`. For each, say what caught it (`detection`),
who (`detected_by`), where it happened and where it was caught (the build
computes the lag), whether it reached the person (`caught`), and `severity`
1–3. Tie it to a call when you can:

- `{"exchange": "E04", "seq": 18}` or `{"exchange": "E12", "tool": "Bash", "contains": "git push"}`
- `link_basis` must be honest: `observed` (the call's own result) > `log` >
  `description-chain` (the next call says "retry"/"see why") > `reply` >
  `summary` (the post-compaction summary only, which is the weakest basis).

An `unrecorded` call that a failure points at becomes `attested_fail`, with
the basis as its source. That is the only way a call without a result gets an
outcome.

Why the rigour: a session summary is a reconstruction. In the session that
produced this skill, a "correction" told the person a commit hash had been
shown to them earlier. It hadn't. The hash came from the compaction summary,
was presented as memory, and was copied into two spreadsheets. **Any claim
about what you said, saw or did earlier needs a source in the record. Grep the
transcript or export before writing it.**

**Findings / sources / deliverables / open items** — straightforward; keep
provenance on each, and keep "not read" sources as rows so nothing looks more
checked than it was.

## Step 4 — Build

```bash
python3 -m core_sample build <session-folder> --version X.Y.Z [--db <shared.sqlite>]
```

The build validates every coded value against `core_sample/taxonomy.py` and
fails loudly on anything unknown (an unmatched call reference, a layer that
doesn't exist). Fix the annotation; don't loosen the vocabulary to make the
build pass. Point `--db` at one shared database (e.g.
`$CORE_SAMPLE_HOME/core-sample.sqlite`) so sessions accumulate.

Output scanning: Bash and remote-shell results are scanned for error
signatures (`fatal:`, tracebacks, `returned error: 403`, …), because a pipe
like `| tail` makes a failed command report success. Those calls become
`error_unflagged`. If the scan misfires on a call, record the correction as a
failure note rather than editing the parsed data.

## Step 5 — Verify before you deliver

1. Recalculate (the xlsx skill's `recalc.py`) and require zero formula errors.
2. Read back the six KPI tiles and the Chart Data blocks with
   `load_workbook(data_only=True)`, and check them against a direct count from
   the ledger. A clean recalc proves formulas evaluate, not that they're right:
   a SUM that also caught its own total row once doubled a KPI.
3. Read every generated takeaway on the Charts tab against its chart.
   Takeaways are generated from data. If you add one by hand, it must be true
   of this session alone.
4. Render to PDF (`soffice --headless --convert-to pdf`) and look at the index
   and charts pages once.
5. Run `python3 -m unittest discover -s tests` after changing the toolkit.

Deliver the recalculated workbook (it carries cached values, so previews show
numbers), the CSV folder and the SQLite file, named by taxonomy with a
semantic version. Lead the hand-over with what the data says, not what you
built: the share of calls with no recorded result, the failures that reached
the person, and what caught them.

## Analysis across sessions

```bash
python3 -m core_sample query <db> "SELECT * FROM v_tool_reliability ORDER BY failed DESC LIMIT 10"
```

Useful views: `v_outcome_coverage` (how much of the record is checkable, per
source), `v_failures_by_layer_detection` (what catches what, and what
escapes), `v_tool_reliability` (calls, failures, unflagged failures per tool).
See `references/analysis.md` for questions worth asking, with their SQL.

## Verification of the lifecycle

Run one short session: invoke **core-sample start**, execute successful and
failing Bash calls, compact, then invoke **core-sample compile**. Check:

- No ledger file appeared **before** `CaptureStarted`.
- Events for the correct session appear strictly between `CaptureStarted`
  and `CaptureStopped`; post-stop calls are not appended.
- A second, unarmed session has no recorded tool events.
- No raw archive is created without deliberate `CORE_SAMPLE_ARCHIVE_RAW=1`.
- `tool_use_id` links hook and transcript evidence without duplicates; a
  contradictory result **fails validation** rather than being overwritten.
- Verify real Claude Code hook stdin once before asserting end-to-end coverage.

## Data classification

The ledger is **confidential-local**: tool inputs and outputs can hold
anything the session touched. The hook writes files mode 0600 and folders
0700. It redacts bearer tokens, `ghp_`/`sk-` keys and `key=value` secrets
(the redaction is not exhaustive), truncates long fields, never sends data
anywhere, and always exits 0 so it can't block a session. `session_id` is
sanitised before it becomes a file name, and values under secret-named keys
(`api_key`, `password`, `token`, …) are masked as well as `key=value` text. Before publishing a
workbook or putting it in a repo, scan the Tool Calls tab's input and
error columns for anything private. The same goes for verbatim prompts on the
Exchanges tab.
