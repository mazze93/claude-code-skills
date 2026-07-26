---
name: cloudflare
description: "Cloudflare development: Workers, Wrangler CLI, Pages, Durable Objects, storage (KV/D1/R2/Queues), AI (Workers AI, Vectorize, Agents SDK), Sandbox SDK, Email Service, Turnstile setup, security (WAF, DDoS), networking, and IaC. Use for any Cloudflare build, deploy, or code-review task. Retrieval-first over pre-trained knowledge."
references:
  - workers
  - pages
  - d1
  - durable-objects
  - workers-ai
---

# Cloudflare Platform Skill

Consolidated skill for building on the Cloudflare platform. Use decision trees below to find the right product, then load detailed references.

Your knowledge of Cloudflare APIs, types, limits, and pricing may be outdated. **Prefer retrieval over pre-training** — the references in this skill are starting points, not source of truth.

## Retrieval Sources

Fetch the **latest** information before citing specific numbers, API signatures, or configuration options. Do not rely on baked-in knowledge or these reference files alone.

| Source | How to retrieve | Use for |
|--------|----------------|---------|
| Cloudflare docs | `cloudflare-docs` search tool or `https://developers.cloudflare.com/` | Limits, pricing, API reference, compatibility dates/flags |
| Workers types | `npm pack @cloudflare/workers-types` or check `node_modules` | Type signatures, binding shapes, handler types |
| Wrangler config schema | `node_modules/wrangler/config-schema.json` | Config fields, binding shapes, allowed values |
| Product changelogs | `https://developers.cloudflare.com/changelog/` | Recent changes to limits, features, deprecations |

When a reference file and the docs disagree, **trust the docs**. This is especially important for: numeric limits, pricing tiers, type signatures, and configuration options.

## Deep Guides

Several reference directories carry a `guide.md` — a full standalone treatment consolidated from what used to be separate skills (2026-07-25). Load these when the task is substantially about that product, not just touching it:

| Task | Load |
|---|---|
| Building agents, durable execution, streaming chat, voice, MCP, human-in-the-loop | `references/agents-sdk/guide.md` + the topic files beside it |
| Writing or reviewing Worker code against production best practices | `references/workers/guide.md`, `references/workers/rules.md`, `references/workers/review.md` |
| Any `wrangler` command — deploy, dev, secrets, bindings, resource management | `references/wrangler/guide.md` |
| Durable Objects: RPC, SQLite storage, alarms, WebSockets, testing | `references/durable-objects/guide.md` + `rules.md`, `testing.md`, `workers.md` |
| Sandboxed code execution, code interpreters, preview URLs | `references/sandbox/guide.md` + `api-quick-ref.md`, `examples.md` |
| Sending/receiving transactional email, deliverability, SPF/DKIM/DMARC | `references/email-workers/guide.md` + `sending.md`, `deliverability.md`, `rest-api.md`, `routing.md`, `cli-and-mcp.md` |
| Adding Turnstile to a project end-to-end (scan → create widget → embed → siteverify → validate) | `references/turnstile/spin.md`; per-framework snippets (`astro.md`, `nextjs-app.md`, `sveltekit.md`, `hugo.md`, `vanilla-html.md`) and `scripts/` beside it |

For Zero Trust / SASE work (Access, Gateway, WARP, Tunnel, DLP, CASB), use the separate `cloudflare-one` skill.

## Quick Decision Trees

### "I need feature flags"

```
Need feature flags?
└─ Feature toggles, targeting rules, percentage rollouts → flagship/
   ├─ Evaluate in Workers → Flagship binding (env.FLAGS)
   ├─ Evaluate in Node.js / browser → OpenFeature SDK (@cloudflare/flagship)
   └─ Manage flags via API → Flagship REST API
```

### "I need to run code"

```
Need to run code?
├─ Serverless functions at the edge → workers/
├─ Full-stack web app with Git deploys → pages/
├─ Stateful coordination/real-time → durable-objects/
├─ Long-running multi-step jobs → workflows/
├─ Run containers → containers/
├─ Multi-tenant (customers deploy code) → workers-for-platforms/
├─ Scheduled tasks (cron) → cron-triggers/
├─ Lightweight edge logic (modify HTTP) → snippets/
├─ Process Worker execution events (logs/observability) → tail-workers/
└─ Optimize latency to backend infrastructure → smart-placement/
```

### "I need to store data"

```
Need storage?
├─ Key-value (config, sessions, cache) → kv/
├─ Relational SQL → d1/ (SQLite) or hyperdrive/ (existing Postgres/MySQL)
├─ Object/file storage (S3-compatible) → r2/
├─ Versioned file trees (repos, build outputs, checkpoints) → artifacts/
├─ Message queue (async processing) → queues/
├─ Vector embeddings (AI/semantic search) → vectorize/
├─ Strongly-consistent per-entity state → durable-objects/ (DO storage)
├─ Secrets management → secrets-store/
├─ Streaming ETL to R2 → pipelines/
├─ Managed Apache Iceberg catalog on R2 → r2-data-catalog/
├─ Serverless SQL analytics over Iceberg tables → r2-sql/
└─ Persistent cache (long-term retention) → cache-reserve/
```

### "I need AI/ML"

```
Need AI?
├─ Run inference (LLMs, embeddings, images) → workers-ai/
├─ Vector database for RAG/search → vectorize/
├─ Build stateful AI agents → agents-sdk/
├─ Gateway for any AI provider (caching, routing) → ai-gateway/
└─ AI-powered search widget → ai-search/
```

### "I need networking/connectivity"

```
Need networking?
├─ Expose local service to internet → tunnel/
├─ TCP/UDP proxy (non-HTTP) → spectrum/
├─ WebRTC TURN server → turn/
├─ Private network connectivity → network-interconnect/
├─ Optimize routing → argo-smart-routing/
├─ Optimize latency to backend (not user) → smart-placement/
└─ Real-time video/audio → realtimekit/ or realtime-sfu/
```

### "I need security"

```
Need security?
├─ Web Application Firewall → waf/
├─ DDoS protection → ddos/
├─ Bot detection/management → bot-management/
├─ API protection → api-shield/
├─ CAPTCHA alternative → turnstile/
└─ Credential leak detection → waf/ (managed ruleset)
```

### "I need media/content"

```
Need media?
├─ Image optimization/transformation → images/
├─ Video streaming/encoding → stream/
├─ Browser automation/screenshots → browser-rendering/
└─ Third-party script management → zaraz/
```

### "I need analytics/metrics data"

```
Need analytics?
├─ Query across all Cloudflare products (HTTP, Workers, DNS, etc.) → graphql-api/
├─ Custom high-cardinality metrics from Workers → analytics-engine/
├─ Client-side (RUM) performance data → web-analytics/
├─ Workers Logs and real-time debugging → observability/
├─ SQL over Iceberg data lake (logs, events) → r2-sql/ (+ pipelines/, r2-data-catalog/)
└─ Raw logs (Logpush to external tools) → Cloudflare docs
```

### "I need infrastructure-as-code"

```
Need IaC? → pulumi/ (Pulumi), terraform/ (Terraform), or api/ (REST API)
```

## Product Index

### Feature Flags
| Product | Reference |
|---------|-----------|
| Flagship | `references/flagship/` |

### Compute & Runtime
| Product | Reference |
|---------|-----------|
| Workers | `references/workers/` |
| Pages | `references/pages/` |
| Pages Functions | `references/pages-functions/` |
| Durable Objects | `references/durable-objects/` |
| Workflows | `references/workflows/` |
| Containers | `references/containers/` |
| Workers for Platforms | `references/workers-for-platforms/` |
| Cron Triggers | `references/cron-triggers/` |
| Tail Workers | `references/tail-workers/` |
| Snippets | `references/snippets/` |
| Smart Placement | `references/smart-placement/` |

### Storage & Data
| Product | Reference |
|---------|-----------|
| KV | `references/kv/` |
| D1 | `references/d1/` |
| R2 | `references/r2/` |
| Artifacts | `references/artifacts/` |
| Queues | `references/queues/` |
| Hyperdrive | `references/hyperdrive/` |
| DO Storage | `references/do-storage/` |
| Secrets Store | `references/secrets-store/` |
| Pipelines | `references/pipelines/` |
| R2 Data Catalog | `references/r2-data-catalog/` |
| R2 SQL | `references/r2-sql/` |

### AI & Machine Learning
| Product | Reference |
|---------|-----------|
| Workers AI | `references/workers-ai/` |
| Vectorize | `references/vectorize/` |
| Agents SDK | `references/agents-sdk/` |
| AI Gateway | `references/ai-gateway/` |
| AI Search | `references/ai-search/` |

### Networking & Connectivity
| Product | Reference |
|---------|-----------|
| Tunnel | `references/tunnel/` |
| Spectrum | `references/spectrum/` |
| TURN | `references/turn/` |
| Network Interconnect | `references/network-interconnect/` |
| Argo Smart Routing | `references/argo-smart-routing/` |
| Workers VPC | `references/workers-vpc/` |

### Security
| Product | Reference |
|---------|-----------|
| WAF | `references/waf/` |
| DDoS Protection | `references/ddos/` |
| Bot Management | `references/bot-management/` |
| API Shield | `references/api-shield/` |
| Turnstile | `references/turnstile/` |

### Media & Content
| Product | Reference |
|---------|-----------|
| Images | `references/images/` |
| Stream | `references/stream/` |
| Browser Rendering | `references/browser-rendering/` |
| Zaraz | `references/zaraz/` |

### Real-Time Communication
| Product | Reference |
|---------|-----------|
| RealtimeKit | `references/realtimekit/` |
| Realtime SFU | `references/realtime-sfu/` |

### Developer Tools
| Product | Reference |
|---------|-----------|
| Wrangler | `references/wrangler/` |
| Miniflare | `references/miniflare/` |
| C3 | `references/c3/` |
| Observability | `references/observability/` |
| GraphQL Analytics API | `references/graphql-api/` |
| Analytics Engine | `references/analytics-engine/` |
| Web Analytics | `references/web-analytics/` |
| Sandbox | `references/sandbox/` |
| Workerd | `references/workerd/` |
| Workers Playground | `references/workers-playground/` |

### Infrastructure as Code
| Product | Reference |
|---------|-----------|
| Pulumi | `references/pulumi/` |
| Terraform | `references/terraform/` |
| API | `references/api/` |

### Other Services
| Product | Reference |
|---------|-----------|
| Email Routing | `references/email-routing/` |
| Email Workers | `references/email-workers/` |
| Static Assets | `references/static-assets/` |
| Bindings | `references/bindings/` |
| Cache Reserve | `references/cache-reserve/` |
