# Changelog

## [Unreleased]

### Added
- `skills/model-inventory/` (workspace plugin) — inventories on-device models (Ollama across every account's store, Hugging Face/MLX, LM Studio, training runs, loose weights), assigns an evidence-backed verdict (`keep-archive-first`, `unknown-archive-first`, `orphan`, `re-downloadable`, `cloud-stub`), and archives user-picked items to a user-chosen drive with per-file SHA-256 verification. Never deletes; refuses a same-disk destination. `scripts/model_inventory.py` is stdlib-only; 26 tests on synthetic stores and a mock registry, covering every Greptile finding on #13 (nested variant dependencies, vanished sources, links leaving the archive and their space accounting, v2-only installs, linked orphans, LM Studio provenance, blobs-only stores, small weights, `--offline`); seven mutation-checked.
- Journal → ENGRAM **promote** flow: `session-journal` close-out appends `[promote]` pointer lines to ENGRAM's inbox; `engram` Consolidate routes them with a `src:` pointer and checks pointer liveness (`[DEAD-SRC]` / `[UNVERIFIED-SRC]`, report-only, never blocks); `stratum-project-init` notes ENGRAM as a third, citing view. Pointers, never copies.
- `plugins/rigor/evals/` — `claude plugin eval` suite for the `rigor` plugin (7 cases, with-plugin vs baseline). Final run: +8.3 pts over baseline on Opus 5.5 (6/7), +4.2 on Sonnet 5.5 (5/7). README records results, what the suite does not establish (mutation test, timeout blind spot), the Sonnet 5.5 `reasoning_extraction` safeguard on `decision-telemetry`, and harness bugs found.
- `skills/decision-telemetry/tree-of-knowledge.html` — the canonical implementation `SKILL.md` already referenced but the repo never contained; path in `SKILL.md` corrected.
- `LICENSE` — MIT, covering this repo's own work.
- `NOTICE` — index of vendored third-party content and its terms.
- `skills/cloudflare/`, `skills/cloudflare-one/`, `skills/web-perf/` — vendored from [`cloudflare/skills`](https://github.com/cloudflare/skills) (Apache-2.0, retrieved 2026-07-23). Each carries its own `LICENSE` and `NOTICE` with an Apache-2.0 §4b statement of changes; they are **not** covered by the repo's MIT license.

### Security
- `site/`: `http-cache-semantics` now installs from a locally patched build, `site/vendor/http-cache-semantics/` (`4.3.0-mazze93.1`, BSD-2-Clause). On stock 4.3.0, `Cache-Control: max-stale` reused stored responses marked `no-store`, `no-cache`, shared `private`, shared `Set-Cookie` or shared `proxy-revalidate`, and stale-while-revalidate / stale-if-error ignored `must-revalidate`. No published release fixes this (latest is 4.3.0, 2026-10-04). Upstream's mocha suite still passes 128/128 on the patched code. The new installed-package gate, `npm run test:vendor`, passes 46/46 on the patched build and fails 23 of 46 on stock 4.3.0. The vendored tarball rebuilds byte for byte from the pinned upstream sha512 plus the patch. Both checks run in CI. npm does not verify lockfile `integrity` for `file:` dependencies (npm 10 and 11 both install a tampered tarball), so the gate pins the tarball hash itself. Observed reach is limited: astro, the only consumer, calls `storable()`/`timeToLive()`, which the patch leaves alone. Drop the vendored build once a published release fixes these paths; see that directory's README.
- `site/`: `overrides.sharp ^0.35.5` clears GHSA-wq5f-xc86-pv6w (librsvg); `npm update` can't, because miniflare pins sharp exactly. `allowScripts` aligned to the lockfile (`f380a38`). **Correction to that commit message:** it says the stale pins would have *blocked* the workerd/esbuild install scripts. npm 11.19.1 does not — it warns ("not yet covered by allowScripts") and runs them anyway (verified: native bins in place under the stale pins). The alignment silences the warning and holds up if npm starts enforcing; nothing was broken before it.

### Changed
- `touchstone`: new "Probe-harness gotchas" section, distilled from a 2026-10-29 pass on context-synapse's jj collector (#50). Covers: assert the precondition before reading a result (3 of 4 probe runs there were silently invalid); measure state, not flag docs, for "read-only" claims (`jj --ignore-working-copy` still writes a reconcile op when op heads diverge); treat the author's own check as proof, not probe; degenerate-but-routine inputs that hand-written fixtures never produce (empty jj changes recorded as commits); stub recorders in disposable copies; check whether real data is already affected. Workflow, taxonomy and anti-patterns are unchanged. Not re-run against `plugins/rigor/evals/`.
- `disk-audit`: reconcile in bytes; scan every home dot-directory; background slow scans; snapshot check on the Data volume; `.[!.]*` root glob; data-risk vs restore-cost rating; package-manager, build-output, VM-image and sync-client buckets; models handed to `model-inventory`; `fclones` with reflink dedup (proven on first use); dated debrief diffed against the previous run.
- `site/src/data/catalog.json` no longer stores `isNew`; `site/src/lib/catalog.ts` derives it from `added` at build time. A committed date-relative boolean made `build_marketplace.py --check` fail on an untouched tree once any skill turned 30 days old (main went red 2026-10-03).
- `.gitignore`: `plugins/*/evals/results/` (eval run output is local only).
- Consolidated the Cloudflare skill set 10 → 2. `agents-sdk`, `cloudflare-email-service`, `durable-objects`, `sandbox-sdk`, `turnstile-spin`, `wrangler`, `workers-best-practices` folded into `cloudflare/references/` (each former `SKILL.md` preserved as `<product>/guide.md`, Turnstile as `turnstile/spin.md` with its `scripts/` and `tests/`); `cloudflare-one-migrations` folded into `cloudflare-one/references/migrations.md`. `cloudflare-one/SKILL.md` split 22KB → 3KB router + `references/{assessment,guardrails,validation,migrations}.md`.
- Skill listing cost: ~2,525 → ~1,671 est. resident tokens per session, back under the ~1% context budget where entries start being truncated.

- `hooks/post-tool-use.sh` v1 — PostToolUse(Edit|Write) antipattern scanner: innerHTML assignment with non-literal RHS, Linux `/home/` paths, SQL string interpolation; project-aware validation reminders (npm run check / swift build)
- `hooks/on-prompt.sh` v3 — portability fix: MEMORY_DIR path derived from `$HOME` via sed instead of hardcoded slug
- `hooks/on-session-end.sh` v4 — canonical copy of `~/.claude/scripts/on-session-end.sh`; already portable
- `bootstrap/bootstrap.sh` — orchestrator; idempotent, portable (`$HOME` throughout), dry-run safe; calls install-hooks/install-skills/install-settings
- `bootstrap/lib/install-hooks.sh` — symlinks on-prompt/on-session-end/post-tool-use into `~/.claude/scripts/`; creates `mem-map.conf` if missing
- `bootstrap/lib/install-skills.sh` — symlinks each `skills/*/` dir into `~/.claude/skills/`; symlinks `cc-statusline.sh` into `~/.config/iterm2/`
- `bootstrap/lib/install-settings.sh` — surgically adds PostToolUse antipattern hook to `settings.json` via jq; backs up settings before writing; preserves all existing config

### Context
Implemented from `/insights` session analysis (2026-05-26). All scripts are idempotent (check before act), transferrable (`$HOME` throughout, no hardcoded paths), and elegant (each sub-script self-contained; main entry orchestrates only).

## [1.0.0] — 2026-05-22

### Added
- Initial repo: `skills/git-forensics/` — adversarial git forensics skill
- `config/cc-statusline.sh` — Claude Code statusLine command (iTerm2 integration)
