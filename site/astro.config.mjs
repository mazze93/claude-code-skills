// @ts-check
import { defineConfig } from 'astro/config';
import cloudflare from '@astrojs/cloudflare';
import react from '@astrojs/react';

// static-by-default. The catalogue is read at build time from skill-map.json, so
// every route can be prerendered; a route that later needs on-demand rendering
// opts out with `export const prerender = false`. Not 'hybrid' — removed in
// Astro 5 and merged into 'static'.
export default defineConfig({
  site: 'https://store.mazzeleczzare.com',
  output: 'static',
  adapter: cloudflare(),
  integrations: [react()],
  build: { inlineStylesheets: 'always' },
});
