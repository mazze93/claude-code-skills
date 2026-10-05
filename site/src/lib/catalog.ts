/**
 * Typed view over the generated catalogue.
 *
 * Deliberately contains no node:fs and no node:child_process. The Cloudflare
 * prerenderer runs in workerd, where neither exists — an earlier version of
 * this file shelled out to git for the "new" badge and died at build with
 * `paths[0] must be of type string`. The data is produced by
 * scripts/build_marketplace.py, lives in src/data/catalog.json, and is checked
 * for drift by the same --check gate as marketplace.json and INDEX.md.
 *
 * The render path is pure data. That is the whole point.
 */
import data from '../data/catalog.json';

/** A skill as emitted by build_marketplace.py — date-independent, so --check is stable. */
interface CatalogSkill {
  name: string;
  plugin: string;
  description: string;
  summary: string;
  added: string | null;
}

/** A skill as rendered: `isNew` is derived here, at build time, not committed. */
export interface Skill extends CatalogSkill {
  isNew: boolean;
}

export interface Plugin {
  name: string;
  description: string;
  tier: string;
  price: number;
  tierLabel: string;
  checkout: string | null;
  skills: Skill[];
}

export interface Catalog {
  marketplaceName: string;
  currency: string;
  licence: string;
  plugins: Plugin[];
  recent: Skill[];
  totals: { plugins: number; skills: number };
}

/** Days a skill keeps its "new" badge after its SKILL.md first appears in git. */
const NEW_DAYS = 30;
const DAY_MS = 86_400_000;

/**
 * Pure: `added` (ISO 8601 or null) → whether the skill is still new at `now`.
 * Lives here rather than in the generator because a committed boolean that
 * depends on today's date drifts on its own and fails the --check gate.
 */
export function isNewSince(added: string | null, now: number): boolean {
  if (!added) return false;
  const t = Date.parse(added);
  if (Number.isNaN(t)) return false;
  return now - t <= NEW_DAYS * DAY_MS;
}

function withBadge(s: CatalogSkill, now: number): Skill {
  return { ...s, isNew: isNewSince(s.added, now) };
}

export function loadCatalog(now: number = Date.now()): Catalog {
  const raw = data as unknown as Omit<Catalog, 'plugins' | 'recent'> & {
    plugins: (Omit<Plugin, 'skills'> & { skills: CatalogSkill[] })[];
    recent: CatalogSkill[];
  };
  return {
    ...raw,
    plugins: raw.plugins.map((p) => ({ ...p, skills: p.skills.map((s) => withBadge(s, now)) })),
    recent: raw.recent.map((s) => withBadge(s, now)),
  };
}
