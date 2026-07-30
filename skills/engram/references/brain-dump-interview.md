# Brain-dump Interview

Five-section structured interview. Run in order. Write each file before starting
the next section. Do not batch or skip. Use the Write tool for file output.

---

## Section 1 → identity.md

Ask these as a natural conversation, not a form. Probe where answers are vague.

1. Beyond M5 Pro + iTerm2, what does your daily environment look like? (monitors, editors, any secondary tools in the loop)
2. What's your work rhythm? When are you sharpest? What kills momentum mid-session?
3. What specific ADHD friction shows up most often in your dev workflow? (context switching, starting vs finishing, something else?)
4. What tools do you reach for without thinking? (editors, CLIs, libraries, anything you'd reinstall first on a new machine)
5. What are your strongest technical areas? What do you actively lean on Claude for vs. what do you prefer to reason through yourself?
6. Any preferences Claude keeps having to relearn — things you've had to correct repeatedly?

**Write** `~/.claude/memory/identity.md` from answers.
Include as established facts: M5 Pro · Apple Silicon · /opt/homebrew · iTerm2 · zsh · git remote m3.local

---

## Section 2 → projects.md

**Step 0 — read the workspace map first.**
Before asking any questions, read `~/Code/WORKSPACE.md`. This is the authoritative project registry.
It contains: all projects, their domains (tools/ cognitive/ creative/ publishing/ blog/ secure-pride/),
their stacks, and their statuses. Do not ask the user to re-supply information already in WORKSPACE.md.

From WORKSPACE.md, identify every project with status **active** or any open work noted.
As of the last-reconciled date (2026-05-26) the confirmed active set includes:
- tools/meridian, tools/stele, tools/claude-code-skills
- cognitive/daedalus, cognitive/ContextSynapse, cognitive/praxis-aegis, cognitive/AI
- blog (Astro 6 · Cloudflare — PR #124 open)
- secure-pride/secure-pride-site, secure-pride/aegis-icons
- unfiled: adaptive-response, smart-form-filler + others (see Unfiled table)

Ask the user: "Are there additional active projects not yet in WORKSPACE.md, or projects
whose status has changed since 2026-05-26?" Update your list accordingly.

**Five questions per active project** (complete one before moving to next):
1. Current status — actively building, maintenance mode, paused, or near-complete?
2. What were you last working on? Any open branches, PRs, or half-finished changes?
3. What decisions are unresolved right now? What's the one thing you're most uncertain about?
4. Any recurring pain points or gotchas Claude should know to avoid repeating?
5. What's the next meaningful step?

**Known hard stops and posture overrides** (pre-populate, do not ask):
- cognitive/ContextSynapse: operational context inference PERMANENTLY OUT OF SCOPE. No exceptions.
- secure-pride/*: MAX posture — GDPR · CCPA · SOGI · libsodium only · no localStorage · parameterized queries · masked audit logs
- blog (mazzeleczzare): design fidelity = code quality · no CLS · WCAG 2.1 AA · Astro 6 (not 5)
- thesis-pipeline: IRB-adjacent · spatial masking required · Barrett constructionist framework · cite all validity assumptions
- smart-form-filler: encryption backlog is priority 1 before public release

**Do not ask about** projects with status seed, reference, or paused unless the user raises them.

**Write** `~/.claude/memory/projects.md` from answers.
Use format: domain/name · stack (from WORKSPACE.md) · status · last-worked-on · open questions · next step · hard stops if any.

---

## Section 3 → patterns.md

Ask these — they're about cross-project conventions Claude should always apply:

1. Code style: tabs or spaces, width? Trailing commas? Semicolons in JS/TS?
2. How do you name things? (variables camelCase/snake_case, file naming, branch naming, commit message format)
3. Error handling philosophy: fail fast, defensive, explicit return types, something else?
4. Testing approach — is it consistent across projects, or project-specific?
5. What things has Claude gotten wrong repeatedly that you've had to correct? (This is the most important question in this section — honest answers here save significant friction.)
6. Any cross-project constants that should always be true regardless of project posture?

**Write** `~/.claude/memory/patterns.md` from answers.
Keep entries scannable: short lines, not paragraphs.

---

## Section 4 → decisions.md

Ask:

1. Any architectural decisions made in the last few months that Claude should know about?
2. Any "we tried X, it failed, we're doing Y now" decisions across any project?
3. Technology choices that are locked in and shouldn't be questioned (beyond what's already known from the directive)?
4. Anything you're currently wrestling with that hasn't resolved yet?

**Pre-populate** with ENGRAM decisions (already locked) and known hard-stops:
- `context-synapse: operational context inference permanently out of scope`

Add project-specific decisions from answers.

Format: `YYYY-MM-DD · [project or global] · decision · rationale`

**Write** `~/.claude/memory/decisions.md`.

---

## Section 5 → CLAUDE.md synthesis

After all four files are written, synthesize `~/.claude/CLAUDE.md`.

Requirements:
- References all four memory files with a one-line summary of what's in each
- Machine config as inline facts (not a reference link — Claude should see it immediately)
- A "how to work with me" paragraph in plain language: work style, ADHD considerations, what helps, what hurts
- Active projects list with one-line status each (pulled from projects.md)
- ENGRAM system note: inbox location, how to consolidate, how to capture
- Target length: under 80 lines — this is read at every session start, not an encyclopedia

**Write** `~/.claude/CLAUDE.md`. This replaces the stub written by the setup script.

**Post-transfer variant:** If this is a post-M3-transfer session, compare interview answers against existing file content. Prepend `[STALE]` to any entries that are no longer accurate. Add new context at the bottom of each section. Do not delete anything — the user triages manually.
