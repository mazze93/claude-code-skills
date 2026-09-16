// @ts-check
import { defineConfig } from 'astro/config';
import cloudflare from '@astrojs/cloudflare';

// static-by-default. The catalogue is read at build time from skill-map.json, so
// every route can be prerendered; a route that later needs on-demand rendering
// opts out with `export const prerender = false`. Not 'hybrid' — removed in
// Astro 5 and merged into 'static'.
export default defineConfig({
  site: 'https://store.mazzeleczzare.com',
  output: 'static',
  adapter: cloudflare(),
  // No UI framework: the one island was the astrolabe, and it is now a static
  // Astro component. The site ships zero JavaScript.
  integrations: [],
  build: { inlineStylesheets: 'always' },
});
