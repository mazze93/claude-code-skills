// Regression gate for the vendored http-cache-semantics patch.
//
// Runs against the package *as installed* in site/node_modules (resolved the
// way astro resolves it), not against the tarball or patch in this directory.
// A lockfile regeneration, a dropped override, or an upstream bump that
// silently replaces the patched build fails here before the site builds.
//
// Run: cd site && npm run test:vendor
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

// ── resolve the installed package from astro's point of view ─────────────────
const siteRequire = createRequire(new URL('../../../package.json', import.meta.url));
const astroRequire = createRequire(siteRequire.resolve('astro/package.json'));
const installedEntry = astroRequire.resolve('http-cache-semantics');
const CachePolicy = astroRequire('http-cache-semantics');
const installedPkg = astroRequire('http-cache-semantics/package.json');
const provenance = JSON.parse(readFileSync(new URL('../provenance.json', import.meta.url), 'utf8'));

// ── fixtures ─────────────────────────────────────────────────────────────────
const NOW = Date.parse('2026-10-20T12:00:00Z');
const HTTP_DATE = new Date(NOW).toUTCString();

function req(extra = {}) {
    return { method: 'GET', url: '/img.png', headers: { host: 'example.com', ...extra } };
}

/** Policy with a deterministic clock; `elapsed` is seconds since the response. */
function policy(resHeaders, { status = 200, elapsed = 0, request = req(), ...opts } = {}) {
    const realNow = CachePolicy.prototype.now;
    CachePolicy.prototype.now = () => NOW;
    try {
        const p = new CachePolicy(request, { status, headers: { date: HTTP_DATE, ...resHeaders } }, opts);
        p.now = () => NOW + elapsed * 1000;
        return p;
    } finally {
        CachePolicy.prototype.now = realNow;
    }
}

/** Serialization round trip, keeping the deterministic clock. */
function roundTrip(p) {
    const restored = CachePolicy.fromObject(JSON.parse(JSON.stringify(p.toObject())));
    restored.now = p.now;
    return restored;
}

const BARE = req({ 'cache-control': 'max-stale' });
const BOUNDED = req({ 'cache-control': 'max-stale=3600' });

// ── 1. the installed bytes are the patched build ─────────────────────────────
describe('installed package identity', () => {
    test('version is the patched build', () => {
        assert.equal(installedPkg.version, provenance.patchedVersion);
    });

    test('index.js hash matches provenance', () => {
        const digest = createHash('sha256').update(readFileSync(installedEntry)).digest('hex');
        assert.equal(digest, provenance.indexJsSha256);
    });

    // npm does NOT verify lockfile integrity for file: dependencies (checked with
    // npm 10.9 and 11.19: a tarball with a byte appended installs cleanly), so
    // the committed tarball is pinned here instead.
    test('committed tarball matches provenance and lockfile', () => {
        const tgz = readFileSync(new URL(`../${provenance.tarball}`, import.meta.url));
        const sri = 'sha512-' + createHash('sha512').update(tgz).digest('base64');
        assert.equal(sri, provenance.tarballIntegrity);
        const lock = JSON.parse(readFileSync(new URL('../../../package-lock.json', import.meta.url), 'utf8'));
        assert.equal(lock.packages['node_modules/http-cache-semantics'].integrity, sri);
    });

    test('patch helpers are present', () => {
        assert.equal(typeof CachePolicy.prototype._prohibitsReuseWithoutRevalidation, 'function');
        assert.equal(typeof CachePolicy.prototype._forbidsStaleReuse, 'function');
    });
});

// ── 2. max-stale never overrides a prohibition ───────────────────────────────
describe('max-stale cannot reuse prohibited responses', () => {
    const prohibited = {
        'no-store': [{ 'cache-control': 'no-store, max-age=600' }],
        'no-cache': [{ 'cache-control': 'no-cache, max-age=600' }],
        'Pragma: no-cache': [{ pragma: 'no-cache' }],
        'shared Set-Cookie': [{ 'cache-control': 'max-age=600', 'set-cookie': 'sid=1' }],
        'shared proxy-revalidate': [{ 'cache-control': 'max-age=1, proxy-revalidate' }],
        'shared private': [{ 'cache-control': 'private, max-age=600' }],
        'Vary: *': [{ 'cache-control': 'max-age=1', vary: '*' }],
        'Vary: accept, *': [{ 'cache-control': 'max-age=1', vary: 'accept, *' }],
        'must-revalidate': [{ 'cache-control': 'max-age=1, must-revalidate' }],
        'shared Authorization': [{ 'cache-control': 'max-age=600' }, { request: req({ authorization: 'Bearer x' }) }],
    };

    for (const [name, [headers, opts = {}]] of Object.entries(prohibited)) {
        for (const [label, r] of [['bare', BARE], ['bounded', BOUNDED]]) {
            test(`${name} (${label} max-stale)`, () => {
                const p = policy(headers, { elapsed: 10, ...opts });
                const ask = opts.request ? { ...r, headers: { ...r.headers, ...opts.request.headers } } : r;
                assert.equal(p.satisfiesWithoutRevalidation(ask), false);
                assert.equal(p.evaluateRequest(ask).response, undefined);
                assert.equal(roundTrip(p).satisfiesWithoutRevalidation(ask), false, 'after toObject/fromObject');
            });
        }
    }
});

// ── 3. legitimate stale reuse is preserved ───────────────────────────────────
describe('ordinary zero-lifetime and expired entries stay reusable', () => {
    const allowed = {
        'public, max-age=0': [{ 'cache-control': 'public, max-age=0' }],
        'expired Expires': [{ expires: new Date(NOW - 60_000).toUTCString() }],
        'heuristic zero': [{ 'last-modified': HTTP_DATE }],
        'shared Set-Cookie + public': [{ 'cache-control': 'public, max-age=1', 'set-cookie': 'sid=1' }],
        'shared Set-Cookie + immutable': [{ 'cache-control': 'immutable, max-age=1', 'set-cookie': 'sid=1' }],
        'private cache, Set-Cookie': [{ 'cache-control': 'max-age=1', 'set-cookie': 'sid=1' }, { shared: false }],
        'private cache, proxy-revalidate': [{ 'cache-control': 'max-age=1, proxy-revalidate' }, { shared: false }],
        'private cache, private': [{ 'cache-control': 'private, max-age=1' }, { shared: false }],
        'ignoreCargoCult strips no-cache': [
            { 'cache-control': 'max-age=1, no-cache, pre-check=0, post-check=0' },
            { ignoreCargoCult: true },
        ],
    };

    for (const [name, [headers, opts = {}]] of Object.entries(allowed)) {
        test(name, () => {
            const p = policy(headers, { elapsed: 10, ...opts });
            assert.equal(p.stale(), true, 'fixture must be stale to exercise max-stale');
            assert.equal(p.satisfiesWithoutRevalidation(BARE), true, 'bare max-stale');
            assert.equal(p.satisfiesWithoutRevalidation(BOUNDED), true, 'bounded max-stale');
            assert.equal(roundTrip(p).satisfiesWithoutRevalidation(BARE), true, 'after toObject/fromObject');
        });
    }

    test('bounded max-stale is still bounded', () => {
        const p = policy({ 'cache-control': 'public, max-age=0' }, { elapsed: 7200 });
        assert.equal(p.satisfiesWithoutRevalidation(BOUNDED), false);
        assert.equal(p.satisfiesWithoutRevalidation(BARE), true);
    });

    test('fresh responses are untouched', () => {
        assert.equal(policy({ 'cache-control': 'max-age=600' }).satisfiesWithoutRevalidation(req()), true);
    });
});

// ── 4. stale-while-revalidate / stale-if-error helpers ───────────────────────
describe('direct stale helpers honour prohibitions', () => {
    const SWR_SIE = 'stale-while-revalidate=600, stale-if-error=600';

    test('must-revalidate: stale entry is not served by SWR or SIE', () => {
        const p = policy({ 'cache-control': `max-age=1, must-revalidate, ${SWR_SIE}` }, { elapsed: 10 });
        assert.equal(p.useStaleWhileRevalidate(), false);
        assert.equal(p._useStaleIfError(), false);
        const { policy: next, modified } = p.revalidatedPolicy(req(), { status: 500, headers: {} });
        assert.notEqual(next, p, 'origin error must not resurrect the stale entry');
        assert.equal(modified, true);
    });

    test('must-revalidate: fresh entry may still be served on origin error', () => {
        const p = policy({ 'cache-control': `max-age=600, must-revalidate, ${SWR_SIE}` }, { elapsed: 10 });
        assert.equal(p._useStaleIfError(), true);
        assert.equal(p.revalidatedPolicy(req(), { status: 500, headers: {} }).policy, p);
    });

    test('must-revalidate without SWR: useStaleWhileRevalidate stays false (as upstream)', () => {
        assert.equal(policy({ 'cache-control': 'max-age=600, must-revalidate' }).useStaleWhileRevalidate(), false);
    });

    for (const [name, headers] of Object.entries({
        'no-cache': { 'cache-control': `no-cache, max-age=600, ${SWR_SIE}` },
        'shared proxy-revalidate': { 'cache-control': `max-age=1, proxy-revalidate, ${SWR_SIE}` },
        'Vary: *': { 'cache-control': `max-age=1, ${SWR_SIE}`, vary: '*' },
        'shared Set-Cookie': { 'cache-control': `max-age=1, ${SWR_SIE}`, 'set-cookie': 'sid=1' },
    })) {
        test(`${name}: SWR and SIE disabled`, () => {
            const p = policy(headers, { elapsed: 10 });
            assert.equal(p.useStaleWhileRevalidate(), false);
            assert.equal(p._useStaleIfError(), false);
            assert.notEqual(p.revalidatedPolicy(req(), { status: 503, headers: {} }).policy, p);
            assert.equal(roundTrip(p).useStaleWhileRevalidate(), false, 'after toObject/fromObject');
        });
    }

    test('ordinary SWR and SIE still work', () => {
        const p = policy({ 'cache-control': `max-age=1, ${SWR_SIE}` }, { elapsed: 10 });
        assert.equal(p.useStaleWhileRevalidate(), true);
        assert.equal(p._useStaleIfError(), true);
        const hit = p.evaluateRequest(req());
        assert.ok(hit.response, 'served stale while revalidating');
        assert.equal(hit.revalidation.synchronous, false);
        assert.equal(p.revalidatedPolicy(req(), { status: 503, headers: {} }).policy, p);
    });
});

// ── 5. what astro actually calls is unchanged ────────────────────────────────
describe('astro remote-image path (storable + timeToLive)', () => {
    test('timeToLive is not altered by the patch', () => {
        const p = policy({ 'cache-control': 'max-age=600, stale-while-revalidate=60' });
        assert.equal(p.storable(), true);
        assert.equal(p.timeToLive(), 660_000);
        assert.equal(policy({ 'cache-control': 'no-store' }).storable(), false);
    });
});
