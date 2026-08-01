#!/usr/bin/env node
/* ═══════════════════════════════════════════════════════════════
   COMPONENT FACTORY — portable reference implementation
   Assembles pages from modular components driven by ONE token file.

   Configure via manifest.json:
     { "tokensCss": "project/colors_and_type.css",
       "outRoot":   "project",
       "pages":     [ ... ] }
   Both paths are relative to the repo root (this file's parent dir).

   Components may not contain raw hex or @font-face. The build fails
   if they do — that guard is what makes palette drift structurally
   impossible rather than merely discouraged.

   Usage:
     node factory/build.mjs                  # all groups
     node factory/build.mjs --group colors   # one group
     node factory/build.mjs --only colors-status
     node factory/build.mjs --check          # verify, write nothing
   ═══════════════════════════════════════════════════════════════ */

import { readFileSync, writeFileSync, readdirSync, mkdirSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const manifest = JSON.parse(readFileSync(join(HERE, "manifest.json"), "utf8"));
const TOKENS_CSS = join(ROOT, manifest.tokensCss ?? "tokens.css");
const OUT_ROOT = join(ROOT, manifest.outRoot ?? ".");

// ─── ARGS ────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const flag = (n) => {
  const i = argv.indexOf(n);
  return i === -1 ? null : argv[i + 1];
};
const GROUP = flag("--group");
const ONLY = flag("--only");
const CHECK = argv.includes("--check");

// ─── TOKENS ──────────────────────────────────────────────────
// Parse `--sp-name: #hex;` out of the source of truth. This is the
// only place hex enters the pipeline.
function loadTokens() {
  const css = readFileSync(TOKENS_CSS, "utf8");
  const tokens = new Map();
  const re = /(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;/g;
  let m;
  while ((m = re.exec(css)) !== null) tokens.set(m[1], m[2].toLowerCase());
  if (tokens.size === 0) throw new Error(`No tokens parsed from ${TOKENS_CSS}`);
  return tokens;
}

const TOKENS = loadTokens();

function hexOf(name) {
  const key = name.startsWith("--") ? name : `--${name}`;
  const hex = TOKENS.get(key);
  if (!hex) throw new Error(`Unknown token: ${key}`);
  return hex;
}

function rgbOf(name) {
  const h = hexOf(name).replace("#", "");
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const n = parseInt(full.slice(0, 6), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// ─── TEMPLATE ENGINE ─────────────────────────────────────────
// {{#each rows}}…{{/each}}   repeat over manifest data
// {{field}}                  plain text field
// {{var:field}}              -> var(--sp-x)      (styling)
// {{hex:field}}              -> #rrggbb          (visible labels)
// {{alpha:field:0.06}}       -> rgba(r,g,b,0.06) (derived tints)
function render(tpl, ctx) {
  // Loops first, so inner substitutions see the item context.
  tpl = tpl.replace(
    /\{\{#each\s+([\w.]+)\}\}([\s\S]*?)\{\{\/each\}\}/g,
    (_, key, body) => {
      const list = ctx[key];
      if (!Array.isArray(list)) throw new Error(`{{#each ${key}}} is not an array`);
      return list.map((item) => render(body, { ...ctx, ...item })).join("");
    }
  );

  tpl = tpl.replace(/\{\{alpha:([\w.]+):([\d.]+)\}\}/g, (_, f, a) => {
    const [r, g, b] = rgbOf(ctx[f] ?? f);
    return `rgba(${r},${g},${b},${a})`;
  });
  tpl = tpl.replace(/\{\{var:([\w.]+)\}\}/g, (_, f) => {
    const name = ctx[f] ?? f;
    hexOf(name); // validate it exists
    return `var(${name.startsWith("--") ? name : `--${name}`})`;
  });
  tpl = tpl.replace(/\{\{hex:([\w.]+)\}\}/g, (_, f) => hexOf(ctx[f] ?? f));
  tpl = tpl.replace(/\{\{([\w.]+)\}\}/g, (_, f) => {
    if (!(f in ctx)) throw new Error(`Unbound template field: {{${f}}}`);
    return String(ctx[f]);
  });
  return tpl;
}

// ─── HEX GUARD ───────────────────────────────────────────────
// Components are the thing that must never carry literal colour.
const HEX_RE = /#[0-9a-fA-F]{3}\b|#[0-9a-fA-F]{6}\b/;
function guard(name, src) {
  const problems = [];
  src.split("\n").forEach((line, i) => {
    if (HEX_RE.test(line)) problems.push(`  ${name}:${i + 1}  raw hex: ${line.trim().slice(0, 70)}`);
    if (line.includes("@font-face")) problems.push(`  ${name}:${i + 1}  inline @font-face`);
    if (line.includes("fonts.googleapis.com")) problems.push(`  ${name}:${i + 1}  CDN font import`);
  });
  return problems;
}

// ─── BUILD ───────────────────────────────────────────────────
const partials = {};
for (const f of readdirSync(join(HERE, "partials"))) {
  partials[f.replace(/\.html$/, "")] = readFileSync(join(HERE, "partials", f), "utf8");
}
const components = {};
const violations = [];
for (const f of readdirSync(join(HERE, "components"))) {
  const src = readFileSync(join(HERE, "components", f), "utf8");
  const name = f.replace(/\.html$/, "");
  components[name] = src;
  violations.push(...guard(`components/${f}`, src));
}

if (violations.length) {
  console.error("✗ hex guard failed — components must reference tokens, not literals:\n");
  console.error(violations.join("\n"));
  process.exit(1);
}

let pages = manifest.pages;
if (GROUP) pages = pages.filter((p) => p.group === GROUP);
if (ONLY) pages = pages.filter((p) => p.out.includes(ONLY));

if (pages.length === 0) {
  console.error(`✗ no pages matched (--group ${GROUP} --only ${ONLY})`);
  process.exit(1);
}

let wrote = 0, drift = 0;
for (const page of pages) {
  const outPath = join(OUT_ROOT, page.out);
  // CSS url() resolves relative to the stylesheet, not the page — so linking
  // the token file by relative hop keeps its font paths correct untouched.
  const cssPath = relative(dirname(outPath), TOKENS_CSS);

  const body = (page.components || [])
    .map((c) => {
      if (!components[c]) throw new Error(`${page.out}: unknown component "${c}"`);
      return render(components[c], { ...(page.data || {}) });
    })
    .join("\n");

  const html = render(partials["page-shell"], {
    ...(page.data || {}),
    cssPath,
    title: page.title,
    head: render(partials.head, { cssPath, title: page.title }),
    styles: page.styles || "",
    body,
  });

  let existing = null;
  try { existing = readFileSync(outPath, "utf8"); } catch {}

  if (CHECK) {
    if (existing !== html) { console.error(`  drift: ${page.out}`); drift++; }
    continue;
  }

  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, html);
  wrote++;
  console.log(`  ✓ ${page.out}`);
}

if (CHECK) {
  if (drift) { console.error(`\n✗ ${drift} page(s) differ from source`); process.exit(1); }
  console.log(`✓ ${pages.length} page(s) up to date`);
} else {
  console.log(`\n✓ built ${wrote} page(s) from ${TOKENS.size} tokens · 0 CDN imports`);
}
