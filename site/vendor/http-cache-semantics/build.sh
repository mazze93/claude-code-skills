#!/usr/bin/env bash
# build.sh — rebuild the vendored, patched http-cache-semantics tarball.
#
# Pipeline: fetch the upstream tarball from the npm registry → verify it
# against the pinned upstreamIntegrity in provenance.json (the trust anchor)
# → apply guard-stale-reuse.patch → stamp the version → npm pack.
#
# Modes:
#   bash build.sh           check: rebuild and fail if the committed tarball
#                           or any hash in provenance.json differs (reproducible)
#   bash build.sh --write   rebuild and overwrite the tarball + provenance hashes
#                           (use after editing the patch)
#
# Side effects: network fetch from registry.npmjs.org; temp dir under
# $TMPDIR, removed on exit. --write also modifies files beside this script.
set -euo pipefail

readonly HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROV="$HERE/provenance.json"
MODE="check"
[[ "${1:-}" == "--write" ]] && MODE="write"

# ── helpers ──────────────────────────────────────────────────────────────────
prov() { node -e 'process.stdout.write(String(require(process.argv[1])[process.argv[2]]))' "$PROV" "$1"; }

sri512() {  # SRI sha512 of a file, the format npm records in package-lock.json
  node -e 'const c=require("crypto"),f=require("fs");process.stdout.write("sha512-"+c.createHash("sha512").update(f.readFileSync(process.argv[1])).digest("base64"))' "$1"
}

sha256() {
  node -e 'const c=require("crypto"),f=require("fs");process.stdout.write(c.createHash("sha256").update(f.readFileSync(process.argv[1])).digest("hex"))' "$1"
}

fail() { echo "FAIL $*" >&2; exit 1; }

# ── fetch + verify upstream ──────────────────────────────────────────────────
readonly NAME="$(prov package)"
readonly UPSTREAM_VERSION="$(prov upstreamVersion)"
readonly PATCHED_VERSION="$(prov patchedVersion)"
readonly TARBALL="$(prov tarball)"
readonly PATCH="$HERE/$(prov patch)"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

(cd "$WORK" && npm pack --silent "$NAME@$UPSTREAM_VERSION" >/dev/null)
UPSTREAM_TGZ="$WORK/$NAME-$UPSTREAM_VERSION.tgz"
[[ "$(sri512 "$UPSTREAM_TGZ")" == "$(prov upstreamIntegrity)" ]] \
  || fail "upstream $NAME@$UPSTREAM_VERSION does not match pinned upstreamIntegrity"
echo "ok   upstream integrity $(prov upstreamIntegrity | cut -c1-24)…"

[[ "$(sha256 "$PATCH")" == "$(prov patchSha256)" || "$MODE" == "write" ]] \
  || fail "patch sha256 differs from provenance.json (run with --write after reviewing)"

# ── patch + stamp + pack ─────────────────────────────────────────────────────
mkdir "$WORK/src"
tar -xzf "$UPSTREAM_TGZ" -C "$WORK/src"
patch --quiet --forward -p1 -d "$WORK/src/package" < "$PATCH" || fail "patch did not apply cleanly"

node -e '
  const f=process.argv[1], p=require(f);
  p.version=process.argv[2];
  require("fs").writeFileSync(f, JSON.stringify(p, null, 4) + "\n");
' "$WORK/src/package/package.json" "$PATCHED_VERSION"

(cd "$WORK/src/package" && npm pack --silent --pack-destination "$WORK" >/dev/null)
BUILT="$WORK/$NAME-$PATCHED_VERSION.tgz"
[[ -f "$BUILT" ]] || fail "npm pack did not produce $(basename "$BUILT")"

BUILT_SRI="$(sri512 "$BUILT")"
BUILT_INDEX="$(sha256 "$WORK/src/package/index.js")"
PATCH_SHA="$(sha256 "$PATCH")"

# ── write or check ───────────────────────────────────────────────────────────
if [[ "$MODE" == "write" ]]; then
  cp "$BUILT" "$HERE/$TARBALL"
  node -e '
    const f=process.argv[1], p=require(f);
    [p.patchSha256, p.tarballIntegrity, p.indexJsSha256] = process.argv.slice(2);
    require("fs").writeFileSync(f, JSON.stringify(p, null, 2) + "\n");
  ' "$PROV" "$PATCH_SHA" "$BUILT_SRI" "$BUILT_INDEX"
  echo "wrote $TARBALL  $BUILT_SRI"
  echo "      update site/package-lock.json: cd site && npm install"
  exit 0
fi

[[ "$BUILT_SRI" == "$(prov tarballIntegrity)" ]] || fail "rebuilt tarball differs from provenance tarballIntegrity"
[[ "$(sri512 "$HERE/$TARBALL")" == "$BUILT_SRI" ]] || fail "committed $TARBALL differs from a clean rebuild"
[[ "$BUILT_INDEX" == "$(prov indexJsSha256)" ]] || fail "patched index.js sha256 differs from provenance"
echo "ok   $TARBALL reproduces byte-for-byte ($BUILT_SRI)"
