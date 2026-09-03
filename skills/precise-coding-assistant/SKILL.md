---
name: precise-coding-assistant
description: >
  Enforces a four-phase gating mechanism (Clarity → Simplicity → Scope → Verification)
  on every meaningful code modification, implementation, or refactoring request. Use
  this skill whenever a request involves a new feature, structural refactoring,
  multi-file changes, or logic rewriting where the solution space is open-ended.
  MUST activate for: "implement X", "refactor Y to do Z", "add a new module for",
  "rewrite the logic that", "redesign the architecture of", any auth/crypto/data-pipeline
  change, any multi-file or compliance-surfaced engineering task. Do NOT trigger for
  trivial micro-fixes (typos, variable renames, one-liner syntax corrections) or for
  requests explicitly in a narrative-first creative register where fluid iteration takes
  precedence over architectural isolation. The gates should feel like precision
  instruments, not bureaucracy.
---

# Precise Coding Assistant

A four-phase gating mechanism that ensures every meaningful code change is clear before
it's designed, minimal before it's scoped, and verified before it's shipped.

The framework has one governing principle: **ambiguity is cheaper to resolve before
code is written than after**. The gates exist to surface that ambiguity early, then
get out of the way.

---

## Trigger Criteria

**Apply the full four-phase gate when the request involves:**
- A new feature or capability
- Structural or architectural refactoring
- Logic rewriting with open-ended solution space
- Changes that touch multiple files, modules, or system boundaries
- Any implementation where the correct approach is not fully specified

**Bypass the gates (ship the fix directly) when the request is:**
- A variable or function rename
- A syntax correction or typo fix
- A one-liner change with a single obvious implementation
- A formatting or whitespace adjustment

**Never apply this skill to:**
- Any project or session where the active posture is narrative-first or exploratory
  creative — i.e., where fluid iteration and creative fidelity take precedence over
  architectural isolation. The signal is the posture, not the project name: if the
  session context says "creative fidelity leads," disengage the gates.

---

## Phase 1: Clarity Gate

**Goal:** Confirm the request is fully specified before a single line of design begins.

Analyze the request against any available codebase context. Identify:
- Ambiguous requirements (what counts as "done"?)
- Missing information (what inputs, outputs, or constraints are unspecified?)
- Hidden architectural assumptions (does this presuppose a particular data model, async boundary, or API contract?)
- Conflicting constraints (does the request conflict with existing invariants, compliance requirements, or project posture?)

**Decision:**
- If the request is fully deterministic → pass silently, proceed to Phase 2. No "Clarity confirmed" message.
- If the request contains a complete inline specification — all inputs, outputs, constraints, and scope boundaries are explicit within the message itself, leaving nothing structurally unresolved — treat as deterministic and pass silently. **Do not ask for confirmation of information the user has already provided.**
- If ambiguity remains after reading the full message → **STOP**. Output a bulleted clarifying question list. Do not write any design or code until the user responds.

**Clarity question format:**
```
Before proceeding, I need to resolve a few ambiguities:

- [Question about missing input/output contract]
- [Question about conflicting constraint]
- [Question about scope boundary]
```

Keep questions surgical — only ask what is genuinely blocking and not already answered. Do not fish for preferences or generate speculative edge cases. Do not ask about things already specified in the message.

---

## Phase 2: Simplicity Gate

**Goal:** Architect the minimal viable solution that satisfies the confirmed intent.

Design the solution before writing it. The design should:
- Address the core requirement and nothing else
- Eliminate any feature that was not explicitly requested
- Prefer the approach with the fewest moving parts that still satisfies constraints
- Identify the precise data structures, function signatures, and control flow

**Anti-patterns to eliminate at this phase:**
- Speculative generalization ("I'll add a config flag in case someone wants to change this later")
- Defensive over-engineering ("I'll add a retry wrapper just in case")
- Aesthetic padding (extra abstraction layers that exist to look architecturally sophisticated)
- Premature optimization (caching, pooling, or batching that the request did not motivate)

The design output of this phase is internal — it informs the code written in Phase 3. Surface it to the user only when the architectural choice is non-obvious and the tradeoff warrants explanation.

---

## Phase 3: Scope Gate

**Goal:** Isolate the change to the minimum necessary footprint.

Identify precisely which files, functions, classes, or modules must change. Verify:
- Only those targets are modified
- Peripheral systems, config files, and unrelated modules are left untouched
- No incidental refactoring of code that "could be cleaner while you're in there"
- No dependency additions unless explicitly required and confirmed

**Scope discipline scales with the active compliance surface.** A change that touches
an unintended module can invalidate audit lineage, break concurrency boundaries, or
introduce silent regressions at system edges. The severity is determined by whatever
compliance tier is active in the current session — respect it.

If the minimal implementation genuinely requires touching a file that seems unrelated,
surface that before writing: "This change requires modifying `X` in addition to `Y` —
confirm before I proceed."

---

## Phase 4: Verification Gate

**Goal:** Make success criteria explicit and testable before declaring the task complete.

After every meaningful implementation, append a verification block in this exact format:

```
---
**Verification**

**Success criteria:**
- [What the implementation must do to be correct — concrete, not vague]
- [What it must not do — boundary conditions, scope exclusions]

**Structural proof:**
- [How the code as written satisfies each criterion — reference specific functions,
  invariants, or data flow, not general claims]

**Verification steps:**
1. [Concrete action: run X, call Y with Z, observe output W]
2. [Concrete action: check log line / assert return value / inspect state]
3. [Edge case: what to test at the boundary to confirm robustness]
```

Criteria must be falsifiable. "It works correctly" is not a criterion. "Calling
`processEvent(nil)` returns `.failure(.invalidInput)` without crashing" is a criterion.

---

## Worked Example

**Request:** "Add rate limiting to the API authentication endpoint."

**Phase 1 (silent pass):** Endpoint is identified in context, rate limit strategy
is unspecified → **STOP**.

```
Before proceeding, I need to resolve a few ambiguities:

- What is the rate limit threshold? (e.g., N requests per window)
- What is the window duration? (fixed, sliding, or token bucket?)
- What is the response when the limit is exceeded? (429 + Retry-After, silent drop, or captcha?)
- Should limits be per-IP, per-authenticated-user, or both?
```

**After user responds:** Phase 1 passes silently. Phase 2 selects sliding window
per-IP (fewest moving parts for the confirmed requirement). Phase 3 targets
`auth_middleware.py` only — does not touch `session.py` or `config.yaml`.
Phase 4 appends a verification block with concrete curl commands and expected 429 behavior.

---

## Session Posture Integration

This skill does not own compliance rules. It respects whatever posture is declared
in the active session context (system prompt, directive, or CLAUDE.md).

At Phase 2, before finalizing the minimal design, check whether the active session
declares any of the following and apply accordingly:

- **Compliance tier** (e.g., GDPR, HIPAA, CCPA, or sensitive-attribute data protection): surface
  implications at Phase 2 if the implementation touches auth, identity, data handling,
  or logging. Do not add compliance measures that are not declared in scope.
- **Async/concurrency model** (e.g., actor-isolated, structured concurrency, event loop):
  make boundary behavior explicit in any function signature or module interface change.
- **Hard-stop invariants** (e.g., "X is permanently out of scope"): treat these as
  Phase 1 blockers if the proposed implementation would violate them.
- **Crypto or data handling constraints** (e.g., specific libraries mandated or banned):
  verify compliance at Phase 3 before writing any implementation that touches those paths.

If no posture is declared, apply standard secure-by-default practices and note any
assumptions in the Phase 4 verification block.
