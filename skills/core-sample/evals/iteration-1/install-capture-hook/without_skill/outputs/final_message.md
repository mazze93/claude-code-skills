## Tool results that survive compaction

When Claude Code compacts, it replaces the conversation with a summary, and the raw tool output is lost. This setup uses two hooks so you can get it back:

| Hook | When it runs | What it does |
|---|---|---|
| `PostToolUse` (matcher `*`) | after every tool call | `tool-ledger.py capture` adds the tool name, a short summary of the input and the result to `~/.claude/tool-ledger/<session_id>.jsonl`. Each stored result is cut to 20k chars. |
| `SessionStart` (matcher `compact`) | right after any compaction, auto or `/compact` | `tool-ledger.py restore` puts the most recent results back into context (about 9k chars, under Claude Code's 10k cap on `additionalContext`). It also gives the ledger's path, so Claude can `Read` the full entries. |

Your existing `Stop` hook and `permissions` block are the same as before. The two new events are added next to them.

### Install

```bash
mkdir -p ~/.claude/hooks
cp tool-ledger.py ~/.claude/hooks/tool-ledger.py
chmod +x ~/.claude/hooks/tool-ledger.py
cp ~/.claude/settings.json ~/.claude/settings.json.bak   # keep a copy of the old file
cp settings.json ~/.claude/settings.json
python3 -m json.tool ~/.claude/settings.json >/dev/null && echo "settings valid"
```

The script only uses the Python 3 standard library. Start a new Claude Code session afterwards, because hooks load when a session starts.

### Check it works

1. **The hooks are registered.** Run `/hooks` in Claude Code. You should see `PostToolUse → *`, `SessionStart → compact` and your `Stop` hook.
2. **Capture works.** Ask Claude to run `echo LEDGER_CANARY_42`, then in a terminal run:
   ```bash
   ls -lt ~/.claude/tool-ledger/ | head
   tail -n 1 "$(ls -t ~/.claude/tool-ledger/*.jsonl | head -1)"
   ```
   The last line should be a JSON entry with `"result": "LEDGER_CANARY_42"`.
3. **Restore works without compacting.** Use the session ID from that filename:
   ```bash
   SID=$(basename "$(ls -t ~/.claude/tool-ledger/*.jsonl | head -1)" .jsonl)
   echo "{\"session_id\":\"$SID\",\"source\":\"compact\"}" | python3 ~/.claude/hooks/tool-ledger.py restore
   ```
   You should get a JSON object whose `additionalContext` contains the canary.
4. **Real test.** In the same session, run `/compact`, then ask: *"What was the exact output of the echo command you ran before compaction?"* Claude should answer `LEDGER_CANARY_42` from the restored block, not from memory. For proof, start with `claude --debug` and look for the `SessionStart` hook running with source `compact`.
5. **If nothing happens,** check `~/.claude/tool-ledger/_errors.log`. The script never blocks a tool call; failures are written to that log instead.

### Things to know

- **Plaintext on disk.** The ledger holds raw tool output, which can include secrets that end up in command output (env dumps, tokens in `curl` responses). The folder is created as `0700` and the files as `0600`. Ledgers older than 14 days are deleted the next time a restore runs. To change that, set `TOOL_LEDGER_KEEP_DAYS`. To skip capture for a noisy or sensitive tool, narrow the `PostToolUse` matcher, for example `"Bash|Read|Grep|mcp__.*"`.
- **Newest first.** If the session produced more than about 9k chars of results, only the newest entries are put back. The footer says how many were left out, and those are only in the file.
- **Extra time per call.** The capture hook runs on every tool call, which adds about 30–50 ms of Python startup each time.
- **Settings you can change** (environment variables): `TOOL_LEDGER_DIR`, `TOOL_LEDGER_STORE_CHARS` (20000), `TOOL_LEDGER_BUDGET` (9000), `TOOL_LEDGER_ENTRY_CHARS` (700) and `TOOL_LEDGER_KEEP_DAYS` (14).

### What has been tested

- **Capture:** tested by piping sample payloads into the script. The tool output shapes covered were Bash stdout/stderr, Read file content, MCP content blocks and a 50k-char result. Error cases covered were bad input, a `session_id` containing `../` (it stays inside the ledger folder) and 40 parallel writes (all 40 lines were still valid JSON).
- **Restore:** tested the same way. Covered: the size budget (40 entries came back as 10 shown, 8.4k chars), an unknown session and a `startup` source (both produce no output), a half-written last line (skipped) and deleting old ledgers.
- **Live capture:** a real headless Claude Code run with these hooks wrote a correct entry from a real `tool_response`.
- **Not tested:** an actual `/compact` in a live session. Step 4 above covers that.
