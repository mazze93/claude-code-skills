---
name: component-factory
description: Convert a hand-maintained design system into generated output driven by one token file, with a build-failing guard that makes palette/type drift structurally impossible. Use when a design system has stale values scattered across pages, duplicated @font-face or CDN font imports, or a "source of truth" that nothing actually imports — and when delegating mechanical design migration to a cheaper agent needs a deterministic gate rather than trust.
---

# component-factory

A design system drifts because its token file has **no consumers**. Docs
transcribe it, prototypes mirror it, preview pages duplicate it — and every
copy is a place the next palette change won't reach.

Fixing the stale values corrects today and leaves the machine running. This
skill replaces the machine.

> Born 2026-07-31 migrating Secure Pride to its kintsugi V2 palette. The V2
> migration had landed in exactly one file. Three other surfaces were still
> coherently V1 — and 20 pages each carried their own `@font-face` block and
> their own Google Fonts CDN import.

## The diagnostic (run this first)

Before building anything, prove the drift is structural rather than incidental:

```zsh
# 1. Who actually consumes the token file?
grep -rl "tokens.css\|colors_and_type.css" . --exclude-dir=.git

# 2. How many surfaces duplicate the font setup?
grep -rl "@font-face" . --exclude-dir=.git | wc -l
grep -rl "fonts.googleapis.com\|fonts.gstatic" . --exclude-dir=.git | wc -l

# 3. Where do stale values survive?
grep -rl "<old-hex-1>\|<old-hex-2>" . --exclude-dir=.git | wc -l
```

**If (1) returns only the token file itself, stop hex-mapping and build the
factory.** That result is the whole justification — capture it, it is what
makes the diff defensible later.

Two traps this diagnostic misses on its own:

- **Colors hide in `rgba()` decimals.** `rgba(6,214,224,.4)` is `#06d6e0` and no
  hex sweep will find it. Grep the decimal triples too.
- **A "wrong" font or value may be old-system fidelity, not a typo.** Check
  whether the rest of the old system agrees with it before calling it a bug;
  if it does, you are making a migration decision with visual consequences,
  not a cleanup.

## Structure

```
factory/
  build.mjs          # zero-dep assembler
  manifest.json      # page -> {out, group, title, components[], styles, data}
  partials/
    head.html        # THE single <head>: links the token file, no CDN
    page-shell.html  # document wrapper
  components/        # fragments — NO literal colour, ever
```

Output is written into the served directory, so no deploy config changes.

## The invariant

**Components may not contain raw hex, `@font-face`, or CDN imports. The build
exits non-zero if they do.**

This is the entire point. It converts "please use tokens" from a convention
into a constraint — and it is what makes the work delegable (see Handoff).

```js
const HEX_RE = /#[0-9a-fA-F]{3}\b|#[0-9a-fA-F]{6}\b/;
// per line: raw hex | @font-face | fonts.googleapis.com  -> collect, exit 1
```

**Raw-hex detection alone is not enough.** `{{hex:}}` emits a literal colour —
correct for text that *displays* a value, wrong for styling, where it renders
opaque exactly where a tint was intended. There is no raw hex to find, so the
first rule sees nothing. Add a placement rule:

```js
const HEX_IN_STYLE = /style\s*=\s*"[^"]*\{\{hex:/;
// -> "{{hex:}} inside style= — use {{var:}} or {{alpha:token:N}}"
```

Found the hard way: a delegated agent styled every badge with `{{hex:}}`,
passed the guard clean, and would have shipped solid blocks in place of
translucent pills. **Guard rules are cheap; add one every time a class of
wrongness gets through.**

**Test the guard by violating it.** An untested guard is not a guard:

```zsh
printf '<div style="color:#ff2d95">x</div>\n' > factory/components/_guardtest.html
node factory/build.mjs            # expect: exit 1, exact file:line
rm factory/components/_guardtest.html
node factory/build.mjs --check    # expect: exit 0
```

## Token resolution

Parse the token file; it is the only place literal colour enters the pipeline.

```js
const re = /(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;/g;
```

Four substitutions cover essentially every real page:

| Form | Emits | For |
|---|---|---|
| `{{var:token}}` | `var(--sp-x)` | styling — the default |
| `{{hex:token}}` | `#rrggbb` | swatch labels that *display* the value |
| `{{alpha:token:0.06}}` | `rgba(r,g,b,0.06)` | derived tints and glows |
| `{{field}}` | text | names, captions, copy |

`{{hex:}}` matters more than it looks: a design system's own swatch pages print
hex as content. Deriving it from the token is what keeps the label honest when
the token moves.

Fail loudly on an unknown token or unbound field. A silently empty `var()` is
the drift you are trying to kill.

**Expand loops with depth-aware matching, not a regex.** The obvious
`/\{\{#each (\w+)\}\}([\s\S]*?)\{\{\/each\}\}/` closes the *outer* loop on the
*inner* `{{/each}}`, so any `sections → items` shape silently mangles. Scan for
the balanced close instead. Real design systems nest constantly (rows of
badges, groups of swatches) and the failure is quiet, not loud.

Let the alpha argument accept a data field as well as a literal
(`{{alpha:token:glow}}`) — otherwise one component splits into near-duplicate
variants just to vary an intensity.

## Burst delivery

Never convert every page in one commit. Order by blast radius, smallest first:

1. the simplest group — proves the pipeline end to end
2. mid-size component pages
3. large/composite pages
4. product prototypes last

Each burst is independently committable and verifiable:

```zsh
node factory/build.mjs                    # everything
node factory/build.mjs --group colors     # one group
node factory/build.mjs --only page-name
node factory/build.mjs --check            # verify, write nothing (CI + idempotency)
```

`--check` is what CI runs, and what proves the generator is idempotent against
its own committed output.

## Verification

Deterministic checks are necessary but not sufficient — they prove the files
were written, not that the page *renders* right.

1. `--check` exits 0 (idempotent)
2. Guard demonstrated failing and recovering (above)
3. **Render check via Chrome DevTools MCP** — the one that matters:
   - `list_network_requests` → **zero requests to the font CDN**
   - `evaluate_script` → computed colours equal the displayed labels
     (`getComputedStyle(el).color` vs the swatch text)
   - confirm the font stack resolved to the *new* family
4. Repo sweep: remaining old-hex files and remaining CDN imports, **counted and
   reported honestly** — "3 of 20 pages converted" beats "migrated ✅"

## Handoff to a cheaper agent

The remaining bursts are mechanical, which makes them the local-inference lane
(see `local-swarm`). But `local-swarm`'s standing rule is *local generates
candidates, never verdicts* — because a weaker model's "looks fine" is weak
evidence.

**The factory changes that calculus for this specific work.** Correctness here
is decided by `build.mjs`, not by the model's judgment: raw hex fails the
build, `--check` catches non-idempotent output, and the render check is
mechanical. A local agent cannot approve drift into the repo, because approval
is not the mechanism.

So delegate the bursts, and keep these cloud-side:

- authoring the **first** component of a new shape (the pattern, not the copies)
- any change to `build.mjs` or the guard itself — never let the delegated agent
  weaken the gate to make its own work pass
- semantic remaps (`status.protected: cyan → emerald` is a *meaning* change a
  mechanical map gets wrong)
- the brand mark, and anything whose "correct" value is a design decision
- the final honest count

Hand over with: the invariant, the burst list, the exact commands, and an
explicit "if the build fails, fix the component — never the guard."

### What the first real handoff taught (2026-07-31)

One page delegated to `gpt-oss:20b`. It ran, read the files, and produced a
component — and every part of the verification earned its place:

- **Verify against `git status`, not the agent's report.** It stated it had
  updated the manifest. It had not, and it never ran the build. The prose was
  confident and the diff was one untracked file.
- **A clean exit code is not evidence.** An earlier attempt exited **0 having
  done nothing at all** because the configured model was not installed. Check
  that output is non-empty and that files actually changed.
- **Author the first component of each new shape yourself.** This skill already
  said so; the delegation ignored that and handed over a novel shape, which is
  how both engine and guard defects surfaced. The rule is right — follow it.
  Delegate the *copies*, once the shape is proven.
- **Treat what slips through as a guard bug, not an agent bug.** The model's
  `{{hex:}}`-for-styling mistake was reasonable given the brief. The fix was a
  new rule in the build, not a sterner instruction — instructions are advisory,
  the build is not.

Net: the lane works and the delegation was still worth running, because it
found two real defects in the factory. Budget the first handoff as a test of
the harness rather than as work you are getting for free.

## Stele interface

Stele compiles project config into egregores carrying compliance posture, hard
stops, **and design language**. The factory is the enforcement arm of that last
clause: Stele can *declare* the token contract, but a declaration nothing
checks is the same failure mode as a token file nothing imports.

What the factory gives a governing harness:

- **A machine-checkable design invariant.** `build.mjs --check` is a binary
  integrity signal — no model judgment, reproducible off a clean checkout.
- **A natural hard stop.** "Components may not carry literal colour" is
  expressible as a hard stop, and violations already surface as `file:line`.
- **A tamper surface worth watching.** The highest-value thing to detect is not
  drift in a component — the build catches that — but **edits to the guard**.
  A diff weakening `HEX_RE`, or a component added to an ignore list, is the
  move that would let drift back in silently. Treat `build.mjs` as governed.

Wire `--check` into CI and into the harness's integrity pass. Design drift then
degrades the same way other integrity failures do, instead of being noticed
months later by a human who happens to look at two swatches side by side.

## Reference implementation

`reference/build.mjs` in this skill is a working, dependency-free assembler:
token parsing, the four substitutions, `{{#each}}`, the guard, and
`--group`/`--only`/`--check`. Copy it and write a manifest; it is ~150 lines
and intentionally boring.

Worked example: `mazze93/secure-pride-design`, `factory/` (PR #2).
