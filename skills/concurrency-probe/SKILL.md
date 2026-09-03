---
name: concurrency-probe
description: Verify a concurrency-adjacent claim (thread-safe, handles concurrent requests, session isolation, no race conditions, lock-protected) by actually running simultaneous execution, not sequential tests or code review. Use before declaring any fix "verified" or "done" that touches locking, shared state, FFI/native extensions, background threads, async concurrency, or "two X at once" behavior — especially in threading-heavy native code (Swift/C/Rust/Cython extensions with semaphores, locks, or callbacks). Also use when asked to stress-test, race-test, or check thread-safety.
---

# concurrency-probe

Sequential tests cannot verify a concurrency claim. Calling `a()` then `b()` and checking both worked proves nothing about what happens when `a()` and `b()` run *at the same time* — and that interleaving is exactly where concurrency bugs live. A full green test suite built entirely from sequential calls is not evidence for "handles concurrent requests," no matter how many of them pass.

This was learned the expensive way: a session-isolation fix for a native FFI extension (Swift/Cython) was declared "verified" on the strength of 6/6 regression tests and a full green suite — all sequential. A `/touchstone` pass asked for real simultaneous probes instead, and the very first one found a process-level indefinite hang (confirmed via `kill -9`, not a timeout) that no amount of additional sequential testing would ever have surfaced. The bug was in the *interleaving* of two calls, not in either call alone.

## When to use

- Before declaring done: any fix or feature described as thread-safe, handles concurrent requests, session-isolated, race-free, or lock-protected.
- Any codebase with locks, mutexes, semaphores, shared/global mutable state, background threads, or an FFI boundary to a language with its own concurrency model (Swift `Task`/`DispatchSemaphore`, Rust `Mutex`, C callbacks into a scripting language).
- When `/touchstone`'s boundary taxonomy flags "Concurrency and time" as a live, high-ranked boundary — this skill is the concrete probe technique for that category.
- When asked directly to stress-test, race-test, or check thread-safety.

## The core technique

**1. Actually run things at the same time — don't approximate it with sequencing.**

Sync APIs: real OS threads, started with as close to zero stagger as possible (max contention finds races fastest; a small stagger like 50ms is only for isolating "did the second call see the first as already-started" from genuine simultaneity).

```python
import threading

results, errors = {}, {}

def worker(name, fn):
    try:
        results[name] = fn()
    except Exception as e:
        errors[name] = e

t1 = threading.Thread(target=worker, args=("A", call_a), daemon=True)
t2 = threading.Thread(target=worker, args=("B", call_b), daemon=True)
t1.start(); t2.start()
t1.join(timeout=20)
t2.join(timeout=20)
```

Async APIs: `asyncio.gather` — but **always wrap it in `asyncio.wait_for` with a hard timeout**. `gather` alone has no timeout and will hang your whole probe (and your session) exactly as hard as the bug does.

```python
try:
    await asyncio.wait_for(asyncio.gather(worker("A", call_a), worker("B", call_b)), timeout=20)
except asyncio.TimeoutError:
    assert False, "hung instead of completing or raising"
```

**2. Never let a probe hang your own session.** This is the part that's easy to skip and expensive to skip:
- `daemon=True` on every probe thread, so a genuinely hung thread doesn't block process exit.
- A real timeout on every join/wait — and check it explicitly. `thread.join(timeout=20)` **returns** after 20s whether or not the thread finished; it does not raise. The only way to know if it actually hung is `thread.is_alive()` after the join returns.
- If a probe does hang despite the above (e.g. a bare `asyncio.gather` with no wrapper, or a blocking call with no thread), be ready to `kill -9` the runaway process yourself rather than waiting indefinitely — check `ps`/`lsof` first if anything about the hang is ambiguous, but a probe process you started yourself with no unique state is safe to kill once confirmed stuck.

**3. Distinguish three outcomes, not two.** "Pass/fail" is too coarse — a concurrency probe can land in three different places, and only one of them is actually fine:
- **Held cleanly**: both calls succeeded correctly, or the second was rejected with a real, documented error (e.g. a `ConcurrentRequestsError`) — this is what "thread-safe" should mean.
- **Hung**: the worst outcome, and the one sequential tests can never catch. If a join/wait needs its timeout to return, that's a hang, not a pass.
- **Silently corrupted**: no error, no hang, but wrong data — e.g. two callbacks sharing one dispatch slot so call B's result lands in call A's consumer. This is easy to miss if the probe doesn't check *which* result went *where*, not just that something came back.

**4. Run it more than once, at zero stagger.** A single trial passing is weak evidence — many races are timing-dependent and won't reproduce every run. 5 trials at zero stagger is a reasonable default; increase if the mechanism (locks, dict keyed by a shared id, callback registries) looks fragile.

**5. If a probe finds a real bug and you fix it, re-run the exact probe that failed before calling it fixed** (same discipline as `/touchstone`'s bounded-recursion step) — not a new, easier probe, and not just "the tests pass now."

## Worked shape (from the case that produced this skill)

- Claim: "sessions are independently isolated, including under concurrent use."
- Sequential proof: 6/6 regression tests, full suite green — all calls made one after another.
- Probe 1 (two different sessions, real threads, simultaneous): held.
- Probe 2 (two calls on the *same* session, simultaneous, non-streaming): held — clean `ConcurrentRequestsError`.
- Probe 3 (two calls on the *same* session, simultaneous, *streaming*): did not hold — indefinite hang, confirmed via `kill -9`.
- Root cause once found: two compounding bugs — no guard against a second concurrent call reaching the underlying model, and a shared dict keyed only by session id where the second (doomed) call's cleanup silently deleted the first (active) call's live registration.
- Fix verified by re-running probe 3 (and its async equivalent, `asyncio.gather` + `wait_for`) across 5 zero-stagger trials each, clean every time, before declaring it done.
