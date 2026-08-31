---
title: "References authority index"
type: "doc"
status: "Working"
owner: "AI"
last_updated: "2026-08-31"
description: AllinCMS 建站工具包文档（README.md）
created: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
canonical_entry: "README.md"
sources: ["self"]
related: ["../README.md"]
---

# References authority index

This directory contains mixed-age supporting material. It is **not** a second CMS execution contract.

## Active portable route

- `canonical-adapter-routing.md` — resolves a preferred full canonical checkout or the verified bundled runtime and explains authority/authorization layering.

## Supplemental, non-authoritative guidance

These may help with content quality or private workspace organization, but they do not define current CMS payloads, routes, fields, Action IDs, capability maturity, or mutation authorization:

- `content-format-standard.md`
- `site-content-and-aesthetics-spec.md`
- `source-material-norms.md`
- `workspace-layout.md`
- `allincms-full-site-runbook.md` — routes to the host operational toolset runbook (runtime `00_shared/interface-kit/RUNBOOK-ANYONE.md`) for full-site build steps the canonical adapter does not yet register (theme pages, taxonomy execution, audit gates, platform-boundary fallbacks).

## Historical host-side references

All other files record earlier exploration, generic helpers, simulations, or old workflow shapes. Use them only to interpret legacy artifacts or identify questions for fresh read-only discovery. They must never authorize a mutation or override:

```text
<SUB_LIBRARY_ROOT>/PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md
<SUB_LIBRARY_ROOT>/SCHEMAS/*.schema.json
<SUB_LIBRARY_ROOT>/scripts/validate-*.mjs
<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/AI-START-HERE.md
```

If neither a full `<SUB_LIBRARY_ROOT>` nor the bundled runtime can be resolved and validated, stop with `CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED`; do not revive a historical flow. The bundle is generated canonical bytes, not a second CMS execution contract.
