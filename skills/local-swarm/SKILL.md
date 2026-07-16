---
name: local-swarm
description: Fan out parallel review/analysis/summarization passes to on-device Ollama (claude-local) instead of cloud subagents, with the cloud session acting as orchestrator and verifier. Use when the user asks to "use local inference", "leverage claude-local / on-device Ollama", "run parallel agents locally", or when cloud session limits make spawning cloud subagents wasteful — especially for review passes, bulk classification, per-file summaries, and second-opinion scans.
---

# local-swarm

Cloud Claude orchestrates and judges; the user's Mac does the parallel grunt
work. Born 2026-07-16, when two of three cloud review agents died mid-flight
on a session limit — burned budget, unrecoverable partial results — while the
Ollama lane sat idle.

## Division of labor (non-negotiable)

- **Local model (gemma4/gpt-oss via Ollama): candidate generator only.**
  It surfaces suspects, summaries, checklists. It never gets a verdict.
- **Cloud session: scoping, verification, and probes.** Every local finding
  is verified against the actual code/data before it's reported. A local
  "all clean" is weak evidence — accept it only when your own independent
  check agrees.
- **Deterministic probes beat model reviews.** In the founding session, two
  real bugs were found by concrete probes (run the binary, observe the
  numbers) after both local correctness passes returned nothing. Budget the
  probes first; the swarm is the supplement.

## Two transports

1. **`claude-local -p "<prompt>"`** — full Claude Code harness on Ollama.
   Use when the task benefits from tool use (reading files itself).
   Slower per call (harness startup); one task per invocation.
2. **Ollama API directly** (`POST http://localhost:11434/api/generate`,
   `{"model":…,"prompt":…,"stream":false,"options":{"num_predict":N}}`) —
   same engine, no harness overhead. Use for pure text-in/text-out passes
   (summaries, classification, checklist scans). Parallelize with
   backgrounded Bash jobs writing to separate output files.

## Prompt discipline for small models

- **Scope small.** One file, one section, one question per call. A 688-line
  diff in one prompt produced silent empty output — twice.
- Crisp output contract in the prompt: "Output ONLY the list", a max item
  count, and a fixed line format. Small models fall apart on open-ended asks.
- Low temperature (≈0.2) for review/classification.

## Failure modes (all observed live — check for every one)

1. **Silent empty output, exit 0.** Oversized prompt → the model returns
   nothing, the CLI exits clean. ALWAYS validate the output file is
   non-empty and matches the requested format before using it; retry once
   with a smaller scope, then report the lane as failed — don't fabricate.
2. **Vacuous "all clean".** An 8B model asked for rule violations tends to
   return clean-across-the-board. Treat as advisory; never let it close a
   review on its own.
3. **Cloud-agent session death.** If cloud subagents are used at all, keep
   the count minimal and design for partial loss: each agent's output must
   be independently useful, and the orchestrator must be able to finish the
   job inline when an agent dies. Never make the verdict depend on all
   agents returning.
4. **World moves mid-review.** The PR under review can merge while the swarm
   runs. Check the target's state before acting on results; deliver late
   findings as a follow-up PR (cherry-pick onto the squashed main — the
   original branch will conflict).
5. **Harness noise in output.** `claude-local` prepends warnings (connector
   notices) to stdout — strip known noise lines before parsing.

## Orchestration pattern

```sh
# 1. Prepare N small, scoped prompt scripts writing to separate files
# 2. Launch in parallel as background jobs (Ollama queues requests itself)
# 3. Continue doing the highest-value work inline (probes!) while they run
# 4. On completion: validate non-empty + format, verify every candidate
#    against the code, fold confirmed findings into the report
```

Pair with `/touchstone` for the verification half: the swarm generates
candidates, touchstone probes decide.

## When NOT to use

- Judgment-heavy single tasks (architecture review, subtle correctness) —
  the local model wastes time you'll spend re-doing the work.
- When the artifact fits in one cloud pass anyway — orchestration overhead
  exceeds the savings.
- Anything requiring the local output to be trusted unverified.
