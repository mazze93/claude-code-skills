# Per-repo CLAUDE.md Templates

Use `engram-stub-repo ~/Code/{project}` to create a stub for any project.
The function (installed by setup-script.sh) writes a generic template.
After the brain-dump session, enrich stubs using the domain additions below.

Full project list: `~/Code/WORKSPACE.md`
Workspace root:   `~/Code` (alias for `~/🚀 PROJECTS`)

---

## Generic template (written by engram-stub-repo)

```markdown
# {name} — Claude Context

Global context: ~/.claude/CLAUDE.md
Workspace map: ~/Code/WORKSPACE.md → {name}

## Stack
[from WORKSPACE.md]

## Compliance & Posture
[from WORKSPACE.md domain — see domain additions below]

## Current Status
[TO FILL]

## Active Work
[TO FILL]

## Open Questions
[TO FILL]

## Key Conventions
[TO FILL]
```

---

## Domain additions

Copy the relevant block into a stub after brain-dump. These encode posture,
hard stops, and known constraints the generic template cannot infer.

---

### tools/ domain

```markdown
## Posture
STANDARD unless otherwise noted. Security tooling (stele, aegis-*) → HIGH.

## Key Conventions
[TO FILL]
```

---

### cognitive/ domain

```markdown
## Posture
RESEARCH — document tradeoffs over implementations. Flag decisions that
foreclose future options. Async/sync boundaries always explicit.
```

**cognitive/ContextSynapse — add this block:**
```markdown
## PERMANENT HARD STOP
Operational context inference is OUT OF SCOPE. Permanently. No exceptions.
Do not suggest, implement, or revisit under any framing. If a proposed
change would infer operational context: stop and flag it.

## Open Questions (standing)
- Affect vector: sync vs async — UNRESOLVED
- Lighthouse pinning strategy — UNRESOLVED
```

**cognitive/praxis-aegis — add this block:**
```markdown
## Posture
HIGH — policy engine. Zod schemas for all I/O. No silent failures.
```

---

### blog/ domain

```markdown
## Stack
Astro 6 · React 19 · MDX · Tailwind 4 · Cloudflare Pages
Own repo: mazze-leczzare-blog.git (not tracked in container)

## Posture
HIGH — design fidelity = code quality. No CLS. Performant islands only.
WCAG 2.1 AA non-negotiable. No PII. Minimal cookies.

## Design System
Cipher Gothic (display) · Inter Variable + Playfair Display (body)
Teal #5CCFCF · Coral #F07178 · obsidian background
All colors via CSS variables — never hardcode hex in components.
```

---

### secure-pride/ domain

```markdown
## Posture
MAX — GDPR · CCPA · SOGI data protection · WCAG 2.1 AA mandatory.
Escalate on any unclear compliance boundary before proceeding.

## Hard Constraints
- Crypto: libsodium only
- No localStorage — ever
- SQL: parameterized queries only
- Audit logs: mask all SOGI identifiers before writing
- WCAG 2.1 AA on all UI surfaces

## Sensitive
Lives in private repo(s). Never commit into the public workspace container.
Never log certs or identifiers unmasked.
```

---

### creative/ and publishing/ domains

```markdown
## Posture
CREATIVE — creative fidelity leads. Code (if any) serves narrative.
No PII. MIT or original work only. Copyright-clean assets.
```

---

### templates/ domain

```markdown
## Posture
MAX — scaffolds must embody best practices. Security defaults on.
Document every assumption. SBOM where applicable.
```

---

## Known-project enrichments

For projects with specific known context beyond their domain defaults:

**tools/meridian**
```markdown
## Notes
Local-first CRDT calendar. No cloud. Automerge-Swift for sync.
Extracted 2026-05-30 → mazze93/meridian (public submodule).
CLAUDE.md lives inside the submodule — edit there, not in workspace container.
```

**tools/stele**
```markdown
## Notes
Directive compiler (Anchor). Anthropic API. React 19 · TS · Vite.
```

**cognitive/daedalus**
```markdown
## Notes
ProtonVPN / iTerm2 / Safari atomic environment switcher. zsh · YAML.
Workspace contract enforcement lives here — touches all domains.
```

**blog — PR #124**
```markdown
## Active PR
#124 — constellation-decay homepage. Check status before starting new work.
```

**unfiled/smart-form-filler**
```markdown
## Priority blocker
Encryption backlog must be resolved before public release. Do not ship without it.
```
