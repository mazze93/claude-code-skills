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

export interface Skill {
  name: string;
  plugin: string;
  description: string;
  summary: string;
  added: string | null;
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

export function loadCatalog(): Catalog {
  return data as unknown as Catalog;
}
