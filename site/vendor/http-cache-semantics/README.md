# Vendored `http-cache-semantics` — stale-reuse guard patch

`site/` installs a **locally patched** build of
[`http-cache-semantics`](https://github.com/kornelski/http-cache-semantics)
in place of the registry release, for every consumer in the tree
(today: `astro`, via `^4.2.0`).

| | |
|---|---|
| Upstream | `http-cache-semantics@4.3.0`, commit `b1d4bd6`, sha512 pinned in `provenance.json` |
| Installed | `4.3.0-mazze93.1` — `http-cache-semantics-4.3.0-mazze93.1.tgz` (this directory) |
| Change | `guard-stale-reuse.patch`: 61 lines added to `index.js`, nothing removed |
| License | BSD-2-Clause (`LICENSE`), Kornel Lesiński. **Not** covered by the repo's MIT license |

## What the patch fixes

`maxAge()` returns `0` both for responses that are simply expired and for
responses the cache is **forbidden** to reuse without revalidation.
`evaluateRequest()`'s `max-stale` branch then serves any zero-lifetime entry,
so a request with `Cache-Control: max-stale` got a cached response back even
when that response was marked `no-store`, `no-cache` / `Pragma: no-cache`,
shared `private`, shared + `Authorization`, shared `Set-Cookie` (without
`public`/`immutable`), or shared `proxy-revalidate`. Verified on stock 4.3.0:
the regression gate fails 21 of its 44 cases there; the rest are controls
that must pass on both builds.

`useStaleWhileRevalidate()` and `_useStaleIfError()` also ignored
`must-revalidate`, so `revalidatedPolicy()` returned the old stale policy and
body on a 5xx from the origin.

The patch adds two helpers built only from fields `toObject()` already
serializes, so stored policies keep working and the serialization version is
unchanged:

- `_prohibitsReuseWithoutRevalidation()`: the prohibitions behind the
  zero-lifetime collapse in `maxAge()`, plus any `*` in `Vary`.
- `_forbidsStaleReuse()`: the above, or `must-revalidate`.

`max-stale`, stale-while-revalidate and stale-if-error check them first.
Under `must-revalidate` alone, a **fresh** entry can still be used on an
origin error; a stale one cannot.

**Behaviour kept on purpose:** `public, max-age=0`, an expired `Expires` and a
heuristic zero still allow client-requested stale reuse (upstream README
allows it). Private caches, the shared-cookie `public`/`immutable` opt-ins and
`ignoreCargoCult` behave exactly as before. `maxAge()`, `storable()` and
`timeToLive()` are not touched. `storable()` and `timeToLive()` are the only
methods astro's remote-image cache calls, so the patch changes nothing on that
path.

## Gates

| Command (from `site/`) | Proves |
|---|---|
| `npm run test:vendor` | The **installed** package, resolved from astro, is this build (version + `index.js` sha256) and behaves as patched, including after `toObject`/`fromObject`. The committed tarball's sha512 matches provenance and the lockfile |
| `bash vendor/http-cache-semantics/build.sh` | Fetches upstream, checks it against the pinned sha512, re-applies the patch, and rebuilds the tarball **byte for byte** |

Both run in CI (`store` job). `npm run check` includes `test:vendor`.

## Wiring (why it looks like this)

```jsonc
"dependencies": { "http-cache-semantics": "file:vendor/http-cache-semantics/http-cache-semantics-4.3.0-mazze93.1.tgz" },
"overrides":    { "http-cache-semantics": "$http-cache-semantics" }
```

A `file:` path written directly in `overrides` resolves against the
*dependent* package (`node_modules/astro/vendor/...`, ENOENT). The direct
dependency plus `$ref` override is npm's documented workaround.

**npm does not protect this tarball.** The lockfile records its sha512, but
npm doesn't verify `integrity` for `file:` dependencies. I checked npm 10.9.4
and 11.19.1: `npm ci` installs a tarball with a byte appended and doesn't
complain. The in-repo gates do that job instead (`test:vendor` checks the
hash offline; `build.sh` rebuilds from scratch).

## Changing the patch

1. Edit `index.js` in a checkout of upstream at `upstreamCommit`, run its
   mocha suite (128 passing at 4.3.0), then `git diff > guard-stale-reuse.patch`.
2. `bash build.sh --write` rewrites the tarball and the hashes in `provenance.json`.
3. Bump `patchedVersion`/`tarball` (`-mazze93.N`) and the two paths in
   `site/package.json`, then `npm install` (npm ≥ 11, matching the lockfile).
   If you keep the version unchanged, npm reuses the old lock entry and its
   stale sha512. Delete `node_modules/http-cache-semantics` from both the
   lockfile and disk first; `test:vendor` fails if you skip this.
4. `npm run check`.

## Replace when

Drop this directory, the dependency and the override as soon as **a
published `http-cache-semantics` release makes `max-stale`,
stale-while-revalidate and stale-if-error respect these prohibitions**. To
confirm: point `test/installed.test.mjs` at the new release, drop the identity
block, and every behaviour case should pass. Until then, scanners that match
by version will see `4.3.0-mazze93.1`, a prerelease of 4.3.0. If an
advisory names 4.3.0, check whether this patch covers it; don't assume it does.
