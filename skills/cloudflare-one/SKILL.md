---
name: cloudflare-one
description: "Cloudflare One Zero Trust / SASE: Access, Gateway, WARP, Tunnel, WAN, DLP, CASB, device posture, identity — design, configure, troubleshoot, review, and migrate from Zscaler/Palo Alto/legacy VPN. Retrieval-first: use current Cloudflare docs over embedded knowledge."
references:
  - assessment
  - guardrails
  - validation
  - migrations
---

# Cloudflare One

Before citing limits, settings, API fields, category IDs, or exact UI paths, retrieve current information from the [Cloudflare One docs](https://developers.cloudflare.com/cloudflare-one/), the Cloudflare docs MCP server, or the Cloudflare API schema.

## Workflow

1. Classify the ask: architecture, configuration, troubleshooting, migration, or review.
2. Gather context: account ID, users/sites/apps, identity provider, SCIM/group sync, device management, traffic path, compliance constraints, and rollout blast radius. → `references/assessment.md`
3. Retrieve only the current docs needed for the products involved: Access, Gateway, WARP/device client, Tunnel/Mesh, Cloudflare WAN, DLP, CASB, device posture, or identity.
4. If account access is available, inspect existing resources before proposing or making changes: Access apps/policies/groups/IdPs, Gateway rules/lists/categories, device profiles/posture checks, tunnels/routes, DNS/resolver settings, and locations/sites.
5. Check the domain guardrails before proposing anything. → `references/guardrails.md`
6. Propose the change set with prerequisites, validation, and rollback. For risky changes, stage disabled or scoped to a pilot group/site unless the user explicitly asks otherwise. → `references/validation.md`

## References

| Load when | Reference |
|---|---|
| Scoping a deployment — what to ask before configuring anything | `references/assessment.md` |
| Any config/troubleshooting work — per-domain gotchas and non-obvious semantics (identity, device client & split tunnels, private networking, Gateway/TLS/DLP, CASB & risk, infrastructure access, logs & DEX, WAN) | `references/guardrails.md` |
| Before enabling broadly — per-product test cases | `references/validation.md` |
| Migrating from Zscaler ZIA/ZPA, Palo Alto, legacy VPN, SWG, or another SASE stack — assessment, policy mapping, rollout, parity/gap analysis | `references/migrations.md` |

## Output Defaults

- Designs: current assumptions, target architecture, product responsibilities, rollout phases, validation, and open decisions.
- Configuration work: prerequisites, exact resources to inspect/create/change, test cases, and rollback.
- Troubleshooting: traffic path, likely failure point, evidence to collect, and next test.

## API Safety

- Use fully qualified MCP tool names when MCP tools are available.
- Never guess category IDs, application IDs, wirefilter fields, or API request bodies. Retrieve the current schema/docs and existing account objects.
- Do not enable broad production policies without explicit approval.
