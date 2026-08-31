---
doc_id: allincms-canonical-adapter-routing
title: Canonical Website Content Operations Adapter Routing
description: Resolve the portable Website Content Operations source root and preserve the authorization boundary between this orchestration Skill and the canonical AllinCMS Adapter.
layer: ops
status: "Working"
created: 2026-07-30
updated: 2026-08-12
last_updated: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
sources: ["self"]
related: ["../README.md"]
owner: "AI"
type: "doc"
---
# Canonical Adapter Routing

This shared Skill is an orchestration and SOP package with a digest-verified bundled runtime generated from canonical committed bytes. It does not own an independently editable AllinCMS implementation. For article, taxonomy, media, and article-image operations, the current source of truth is:

```text
<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/AI-START-HERE.md
```

## Source-driven create/update route

For user-provided files or URLs and any request to create or update a site, article, product, taxonomy, media, or theme page, the portable canonical sequence is:

```text
<SUB_LIBRARY_ROOT>/PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md
→ host format-capability routing
→ <SUB_LIBRARY_ROOT>/TEMPLATES/source-extraction.md
→ <SUB_LIBRARY_ROOT>/SCHEMAS/source-extraction.schema.json
→ <SUB_LIBRARY_ROOT>/scripts/validate-source-extraction.mjs
→ <SUB_LIBRARY_ROOT>/TEMPLATES/content-operation-plan.md
→ <SUB_LIBRARY_ROOT>/SCHEMAS/content-operation-plan.schema.json
→ <SUB_LIBRARY_ROOT>/scripts/validate-content-operation-plan.mjs
→ <SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/AI-START-HERE.md
```

The shared Skill may locate and invoke a full source checkout or the generated bundled copies of these files, but maintainers must not hand-edit the bundle or independently fork its parsers, rules, Schemas, validators, or implementations. Source extraction stays in private runtime and remains claim-candidate input. It must not persist current Action IDs, router trees, deployment/build IDs, Cookie, Authorization, or tokens. Historical product flows remain exploration material until the canonical current-deployment capability snapshot proves the exact product lifecycle.

## New-site two-plan boundary

A new site cannot be represented by an invented future `site_key`. The canonical model is:

1. Plan A `site_bootstrap`: account target, current `user.id`, null `site_key/site_id`, exactly one `site:create`, `non_public_resource`;
2. read back the real site identity and bind it to Plan A digest in private runtime;
3. Plan B `site_operation`: real site target, fresh capability/current-state discovery, then content operations.

The two plans cannot share a digest or authorization. A valid authorization approves the complete ordered operations of one plan once; the Adapter revalidates that same authorization before each request without prompting again. Any drift or expiry stops execution. The current canonical Adapter still blocks remote create-site unless its current-deployment capability is upgraded from local request-builder evidence to `live_verified_current_deployment`.

## Resolve `<SUB_LIBRARY_ROOT>`

Run from the shared Skill root:

```bash
python3 scripts/resolve_website_content_ops_root.py --start "$PWD" --json
```

Resolution order is deterministic:

1. an exact full-source `--root` supplied by the caller;
2. full-source `WEBSITE_CONTENT_OPS_ROOT`;
3. upward discovery of `sub-libraries/website-content-ops` or a standalone `website-content-ops` package;
4. the installed digest-verified bundled runtime under `vendor/website-content-ops-runtime`.

The resolver accepts a full source root only when its manifest, runtime contract, Controller dependency closure, AllinCMS entry/contracts and required source files validate and the path is not below `dist/`. It accepts the bundled runtime only when `BUNDLE-MANIFEST.json`, the exact immutable file set, every byte size and SHA-256, package identity and recorded source commit validate. Runtime-created `node_modules/` is excluded from the immutable file-set comparison, while any symlink inside the immutable bundle is rejected.


An invalid explicit path or environment value fails closed. It does not silently fall back to another checkout or the bundle. Do not add a machine-specific home-directory fallback to this Skill. The bundled snapshot is sufficient only after its manifest, full file set, per-file SHA-256 values, runtime contract, Controller imports, locked dependency descriptors, Registry/index checks and local test closure validate. It excludes committed `node_modules`, source cards, customer data, credentials, unredacted private evidence and binary fixtures. `runtimeBundleValidated` is not executable readiness: bundled operations additionally require `runtimeDependenciesInstalled` and `controllerExecutable`, produced only after `install.sh` completes `npm ci`, local tests and native `sharp` loading. Bundle integrity does not upgrade current-deployment capabilities.

## API-first login handoff

Invoke the resolved canonical `workspace-preflight.mjs`; do not reproduce its request parser or status classifier here.

- `authenticated` (including exact zero/single/multiple-site selection outcomes): continue read-only without visible navigation, foregrounding, screenshots, or UI clicks.
- Only `login_required` may open and foreground the canonical `/sign-in` URL in the host in-app browser. An open tab, visible page, or screenshot is not authentication evidence.
- `http_error`, `contract_drift`, and `pagination_incomplete` are separate BLOCK results. They must not be relabelled as logged-out and must not trigger the login page.
- After the user completes login, discard the old response and run a fresh API preflight to read `user.id` and every declared site-list page. Never reuse a previous user/site selection.
- The browser is a same-origin credentialed transport or explicit login handoff, not the default content-operation UI. Prefer the in-app browser; do not switch to Chrome merely because a same-origin context is needed.

The thin Skill chooses only the host callback for the in-app login page. Status classification, pagination completeness, user/site parsing, and create-site discovery remain canonical Adapter responsibilities.

## Authority

```text
current <SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms implementation,
machine contract, tests, and current-deployment evidence
  > this shared Skill's orchestration and SOP
  > neutral or historical request templates
```

When they differ, stop using the stale shared text and update it. Never patch a frozen `dist/` copy. Do not hand-edit `vendor/`; rebuild it from an exact canonical commit with the allowlisted bundle builder.

## Authorization layering

The shared Skill's run-scoped authorization expresses approval for one confirmed build package and may remain valid for its orchestration window. It is not a CMS request credential and **never satisfies the canonical Adapter's mutation authorization input**.

For one real AllinCMS plan, the controller creates the canonical structured authorization only after the user approves the exact target, ordered operations, publication effects, and plan digest. The plan-level authorization may cover that whole immutable serial chain for no more than 30 minutes. The Adapter revalidates the same context immediately before every request; this is a machine check, not a requirement to interrupt the user before every API call.

If the run grant or Adapter context is absent, mismatched, drifted, or expired, the operation stops. Target or plan changes require a new confirmation; Plan A and Plan B always differ in target identity and therefore require separate authorization. Neither layer proves the actor's external identity.
