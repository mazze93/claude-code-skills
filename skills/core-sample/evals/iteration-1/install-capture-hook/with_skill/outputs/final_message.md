# Capture hook: tool results that survive compaction

One Python hook, registered on four events, writes every tool call and its result to a local ledger as it happens. It also copies the transcript right before compaction and at session end, so the pre-compaction record still exists after `/compact`.

| Event | What the hook does |
|---|---|
| `PostToolUse` (all tools) | Appends the call (input and result) to `~/.claude/core-sample/ledger/<session_id>.jsonl` |
| `PostToolUseFailure` (all tools) | Same, for calls that failed |
| `PreCompact` | Logs the event and copies the transcript to `~/.claude/core-sample/archive/<session_id>/transcript-PreCompact-<utc>.jsonl` |
| `SessionEnd` | Same, with `transcript-SessionEnd-<utc>.jsonl` |

Your `Stop` hook (`~/.claude/stop-hook-git-check.sh`) and the `Bash(git status:*)` permission are unchanged. The new events were appended, and nothing existing was replaced.

## Files

- `settings.json`: your settings with the four hook events added
- `hooks/ledger_hook.py`: the capture script

## Install (on your Mac, not a cloud session)

```bash
# 1. Put the script where settings.json points
mkdir -p ~/.claude/core-sample/toolkit/hooks
cp hooks/ledger_hook.py ~/.claude/core-sample/toolkit/hooks/ledger_hook.py
chmod 700 ~/.claude/core-sample

# 2. Back up your live settings, then install the new one
cp ~/.claude/settings.json ~/.claude/settings.json.bak-$(date +%Y%m%d)
diff ~/.claude/settings.json.bak-$(date +%Y%m%d) settings.json   # only additions should show
cp settings.json ~/.claude/settings.json
python3 -m json.tool ~/.claude/settings.json > /dev/null && echo "valid JSON"
```

I built this from the copy you gave me. If your live `~/.claude/settings.json` has changed since then, the diff in step 2 will show lines being removed. In that case, paste the four new blocks (`PostToolUse`, `PostToolUseFailure`, `PreCompact`, `SessionEnd`) into the live file by hand instead of overwriting it.

Optional: to turn ledgers into the SQLite/xlsx record later, also copy the core-sample skill's `scripts/` folder to `~/.claude/core-sample/toolkit/`. Then copy this `ledger_hook.py` over the one that comes with it, because this version has the fixes listed below.

## How to check it works

**1. Smoke-test the script alone.** This writes to a temporary folder and leaves your real ledger untouched:

```bash
T=$(mktemp -d)
echo '{"session_id":"smoke","hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"echo hi","api_key":"shouldvanish"},"tool_response":{"stdout":"token=shouldvanish"}}' \
  | CORE_SAMPLE_HOME=$T python3 ~/.claude/core-sample/toolkit/hooks/ledger_hook.py; echo "exit=$?"
cat $T/ledger/smoke.jsonl      # one line; both "shouldvanish" values replaced by [REDACTED]
ls -la $T $T/ledger            # folder drwx------, file -rw-------
rm -rf $T
```

The expected exit code is `exit=0`. The hook always exits 0, including on bad input. Its own errors go to `hook-errors.log` instead of blocking Claude.

**2. Confirm Claude Code loaded it.** Start `claude` and run `/hooks`. You should see `Stop`, `PostToolUse`, `PostToolUseFailure`, `PreCompact` and `SessionEnd`.

**3. Run one short real session. This is the check that matters.** Ask Claude to:
- run `echo ok` (a call that succeeds)
- run `ls /definitely-not-here` (a call that fails)
- read any small file

Then run `/compact` and exit. Afterwards:

```bash
ls -la ~/.claude/core-sample/ledger/ ~/.claude/core-sample/archive/*/
cat ~/.claude/core-sample/hook-errors.log 2>/dev/null || echo "no hook errors"

# Which events fired, and which fields each one carried
python3 - <<'EOF'
import json, glob, os
f = max(glob.glob(os.path.expanduser("~/.claude/core-sample/ledger/*.jsonl")), key=os.path.getmtime)
for line in open(f):
    r = json.loads(line); p = r["payload"]
    print(r["event"], p.get("tool_name", "-"), sorted(p))
EOF
```

Each item below has to be true:
- There are `PostToolUse` lines that carry `tool_name`, `tool_input` and `tool_response`.
- The failed `ls` appears either as `PostToolUseFailure` with an `error` field, or as `PostToolUse` with the failure text inside `tool_response`. Note which one it was.
- There is a `PreCompact` line, and the archive folder holds a `transcript-PreCompact-*.jsonl`. After you exit there is also a `SessionEnd` line and a `transcript-SessionEnd-*.jsonl`.
- `hook-errors.log` is empty or doesn't exist.

If a field has a different name (for example, there is no `tool_response`), send me one ledger line. The parser reads fields defensively, but a renamed field would show up as `?` tools or empty outcomes, and those should not be trusted.

## What isn't confirmed yet

I tested the script on this machine with sample payloads I wrote myself. Those payloads covered successes, failures, a `git push` 403 hidden behind `| tail`, secrets, a 50 KB output, non-JSON input, and a `session_id` that tries to escape the folder. The core-sample parser read the resulting ledger correctly: it flagged the hidden 403 as an unflagged failure. It has not run inside Claude Code.

The Claude Code hooks docs confirm these parts:
- the event names, including `PostToolUseFailure`
- that `"*"` matches every tool
- the common input fields `session_id`, `transcript_path` and `hook_event_name`
- that `SessionEnd` hooks share a 1.5 s budget, which a per-hook `timeout` raises. That's why `PreCompact` and `SessionEnd` have `"timeout": 10`, so a large transcript copy isn't cut off.

The copy of the docs I could fetch ended before the per-event input sections. So the names `tool_response` and `error`, and whether a non-zero Bash exit fires `PostToolUseFailure` or `PostToolUse`, are still unverified. Step 3 is what settles them.

## Changes to the script vs the skill's copy

Testing with sample payloads found three problems, and this version fixes them:
- **Path escape.** A `session_id` such as `../../x` was used directly as a file name, so the hook could write outside `~/.claude/core-sample`. It is now sanitised.
- **Secrets in structured inputs.** Values under keys like `api_key`, `password` and `token` (as in `{"api_key": "…"}`) were kept in clear text, because only `key=value` text inside strings was redacted. They are now masked.
- **Folder permissions.** `~/.claude/core-sample` and `archive/` were created 0755, although the skill says folders are 0700. They are now forced to 0700.

The ledger format is unchanged.

## Data handling

The ledger is confidential and stays local: it holds whatever your tools read or printed. Files are 0600 and folders 0700. Long fields are cut at 20,000 characters. Nothing is sent anywhere. Redaction catches bearer tokens, `ghp_` and `sk-` keys, `key=value` secrets, private-key blocks and secret-named fields, but it can't catch everything. Read through a ledger before you share it or commit it anywhere.
