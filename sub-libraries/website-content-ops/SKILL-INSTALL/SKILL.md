---
title: "AllinCMS Bulk Content Upload Skill"
status: "Working"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-09-01"
type: "skill"
sources: ["self"]
related: ["README.md"]
visibility: "public"
redaction_status: "safe-to-publish"
name: allincms-bulk-content-upload
description: Source-driven AllinCMS / LAICMS website content operations for creating or updating sites, articles, products, taxonomy, media, and theme pages from user-provided PDFs, DOCX files, spreadsheets, websites, images, briefs, or existing CMS records. Use when an AI must resolve a verified Website Content Operations runtime, extract traceable claims, discover the current logged-in CMS and field/capability contracts, build an exact create/update/noop plan, execute approved API or Server Action mutations strictly serially, and verify backend/editor/frontend persistence. The Skill resolves a complete canonical source checkout (mother library sub-libraries/website-content-ops) as its primary runtime and is distributed from SKILL-INSTALL/ inside that library; the digest-verified runtime snapshot is retired pending the dist pipeline. It must not invent client facts or reuse sample payloads as current contracts.
---

# AllinCMS Bulk Content Upload

## 1. Authority and dependency

This Skill is a **portable discovery and host-orchestration layer** distributed from `SKILL-INSTALL/` inside the mother library (2026-08-30 merge; the former standalone repository is archived). Its primary runtime is the sibling canonical source checkout of Website Content Operations; the generated, digest-verified runtime snapshot is retired pending the dist pipeline (id-0073) and must never be treated as a second editable implementation.

Resolve `<SUB_LIBRARY_ROOT>` before planning or touching AllinCMS:

```bash
python3 scripts/resolve_website_content_ops_root.py --start "$PWD" --json
```

If none is supplied, resolution stops with `CANONICAL_WEBSITE_CONTENT_OPS_ROOT_REQUIRED` (the bundled-snapshot tier is retired pending the dist pipeline; do not fabricate or resurrect it).

For a bundled runtime, `runtimeBundleValidated: true` proves the committed file snapshot only. Before any CMS operation, require `runtimeDependenciesInstalled: true` and `controllerExecutable: true`. If either is false, run this repository's `install.sh`; it installs locked Node dependencies and self-tests the Adapter before creating Skill links. Do not treat a copied-but-not-installed Skill as executable, and do not switch to UI or historical helpers to bypass dependency setup.

Canonical precedence is:

```text
validated full canonical source checkout, when supplied
  > digest-verified bundled runtime snapshot
  > this Skill's host routing
  > supplemental or historical files under references/ and scripts/
```

Read only what the current step needs:

1. `<SUB_LIBRARY_ROOT>/PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md`;
2. `<SUB_LIBRARY_ROOT>/TEMPLATES/source-extraction.md` and `scripts/validate-source-extraction.mjs`;
3. `<SUB_LIBRARY_ROOT>/TEMPLATES/content-operation-plan.md` and `scripts/validate-content-operation-plan.mjs`;
4. `<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/AI-START-HERE.md` only when the target CMS is AllinCMS.

## 2. User material is the run input

User-provided sources override examples. Route PDF, DOCX, spreadsheet, website, image, brief/chat, and existing-CMS inputs through the host's real format capability; do not duplicate parsers here.

For every source, create private-runtime Source Extraction evidence that preserves:

- stable `source_id`, original bytes or snapshot SHA-256, ownership and publication clearance;
- extractor capability, implementation, version and mode;
- page/sheet/cell/paragraph/DOM/JSON-path/image-region locator;
- extracted-value digest, confidence and warnings.

Extraction units are claim candidates, not automatic facts. Every desired-state field marked `confirmed` or `inferred` must bind valid `source_refs` / `claim_refs` and an explicit derivation. `missing`, `conflicting`, `expired`, or `blocked` claims may remain as gaps but cannot silently enter a mutation. Customer source text and live evidence belong only in the bound `customer-runtime/` scope; never write them into this Skill or the canonical public source tree.

## 3. Dynamic values versus frozen invariants

Discover these per client, site and deployment; never copy them from a fixture:

- company/brand/site/domain/language/timezone/market/contact/CTA;
- article/product/taxonomy/media/page content, slugs, SEO fields, specifications and relationships;
- `user_id`, `site_id`, `site_key`, record/media/component IDs and current fingerprints;
- CMS fields, enums, routes, Server Action IDs, router trees, deployment/build IDs and request parameters.

Keep these invariants fixed unless the canonical contract is versioned and requalified:

- Schema versions and fact-state meanings;
- Plan A / Plan B target semantics;
- exact authorization binding and maximum TTL;
- strict serial mutation, idempotency and no-blind-retry rules;
- publication-effect and evidence boundaries;
- frozen release test plan/counts used to qualify a candidate.

A customer value must be dynamic. A safety or qualification invariant must not become caller-configurable merely to look “generic.”

## 4. Desired state, identity and diff

Build platform-neutral desired state first, then discover the live CMS capability and current state. Do not author the final request payload directly from source text.

Resolve every proposed `upsert` before execution into exactly one of `create`, `update`, or `noop`:

- `create`: prove no conflicting site-scoped identity exists;
- `update`: require exact record ID or a site-scoped unique natural key plus `expected_current_fingerprint`;
- `noop`: prove desired and current canonical state are equivalent.

Unmentioned fields remain unchanged. Clearing a value must be explicit. Name/title-only matching is not enough for updates. Operation identity, desired-state identity and diff identity must match exactly.

## 5. New sites require two plans

```text
Plan A: site_bootstrap, account scope
→ current authenticated account user id
→ site_key/site_id remain null
→ exactly one site:create with non_public_resource effect
→ read back the real site id/key/account owner and stop

Plan B: site_operation, site scope
→ reference the exact Plan A digest and private readback evidence
→ bind the real site identity
→ rediscover capability and current state
→ create/update taxonomy, media, articles, products or theme pages
```

Never invent a future site key and never combine site creation and content population in one plan. Plan A and Plan B have different target identities, digests and authorizations.

## 6. Login, capability and execution

Start read-only. Use the canonical Adapter's workspace preflight to check the current session, `user.id`, complete visible site list and exact target. Reuse the in-app browser only as the authenticated same-origin session transport: an authenticated preflight runs as a background credentialed API fetch and must not navigate to `/sites`, foreground a page, or click UI. If no same-origin transport exists, create only a background transport tab. Only if the API itself reports `login_required` may the host open and foreground the canonical sign-in page, guide the user to log in, and then repeat the API preflight. `authenticated` continues without visible navigation; `http_error`, `contract_drift`, or `pagination_incomplete` stop with their exact blocker and must not open the login page. Never infer login from an open tab, visible DOM, screenshot, or guessed site; after login, discard the old response and re-fetch `user.id` plus every declared site-list page through the API.

Capability maturity is one of `live_verified_current_deployment`, `local_tested`, `exploration_only`, or `unsupported`. Every remote mutation requires an unexpired `live_verified_current_deployment` capability for the exact operation and deployment. Registry v2 (2026-08-27 reconciliation): site.create and product create/update/publish are registered canonically under the `fresh_live_verified_current_deployment` gate (single-deployment evidence, no cross-deployment claim); article.create and media metadata update remain `blocked`; media.create runs through a runtime wire-contract guard plus the verified dialog path and its writes are request-scoped (outside `deriveAllinCmsMutationBinding`), not structured-authorization. This Skill does not upgrade any maturity itself.

API / Server Action is preferred. UI is only for login, read-only contract discovery, explicitly approved fallback, or visual verification. UI is never a silent fallback.

Execute one immutable approved plan strictly serially. The user authorizes the complete ordered chain once; immediately before every request, the controller revalidates the same authorization, target, operation order, publication effects, source/plan digests, capability expiry and expected-current fingerprint. This machine revalidation is **not** a requirement to interrupt the user before every API call. The canonical Adapter requires its exact structured context and may return `ADAPTER_AUTHORIZATION_CONTEXT_REQUIRED`; a shared run grant **never satisfies the canonical Adapter**. The Adapter authorization may cover one unchanged serial plan for **no more than 30 minutes**.

Any drift, expiry, ambiguity, target change, source-byte change or request-may-have-started failure stops automatic mutation. Reconcile read-only; never blindly resend. Delete, cleanup, unpublish and public publish remain explicit destructive/publication actions under the canonical plan.

## 7. Verification and writeback

For every attempted operation, record request-start state and perform the canonical applicable gates:

```text
API response
→ exact backend/RSC readback
→ editor reopen and health check when editable content changed
→ anonymous frontend and desktop/mobile render when public output changed
→ image fetch/decode/hash checks when media is involved
```

HTTP 200, toast, local test PASS, or a generated plan alone does not prove persistence, publication, SEO, ranking, inquiry or conversion. When public output includes interactive elements (dialog, menu, CTA), extend the chain with a real-browser click proof (see 7.5). Write current state, evidence pointers, ambiguity, BLOCKs and handoff only to the bound private `customer-runtime/` task.

## 7.5 Delivery gate and silent-failure contracts (2026-09 deployment evidence)

The 13-item machine audit is the floor, not delivery. The delivery gate and the complete check/item taxonomy live in canonical `TOOLS/interface-kit/templates/site-acceptance-v2.md` — always read it for the authoritative BOUNDARY-vs-FAIL classification before escalating or waiving anything.

Rules that fail silently on this platform — assert them by verification, never infer them from config shape:

- Global `contact-dialog-form-modal` must carry `anchorId` equal to the header CTA anchor. With `anchorId: null` the public renderer silently drops the whole dialog subtree (CTA click only changes the URL hash, zero console errors). Canonical spec: `MODULES.md` globals table, ISS-094; builder default already carries it.
- Static top-level pages inherit template-default meta descriptions unless a page-level description is explicitly written — and re-read after the final publish, because publish can reset it. Static pages carry the canonical write recipe; direct meta overrides on dynamic detail pages are platform BOUNDARY — see ISS-073/093 and acceptance-v2 for the verified behavior.
- Classification discipline (details in acceptance-v2): platform-render limits such as hardcoded `lang`, missing canonical/og/JSON-LD and img-attrs are BOUNDARY — check, register with evidence, do not block delivery, do not force-edit unknown themeConfig fields. Sitemap URL-set mismatches (e.g. `/` + `/home` dual-listing) and broken/missing contact links (plain-text email without a working link) are acceptance-v2 FAIL-class items even when the root cause sits platform-side — escalate through the platform ticket workflow, never silently downgrade them to BOUNDARY.
- Interactive elements require a real-browser click proof in the verify chain (dialog open → fill → Escape close, mobile menu, CTA navigation). A `form-render` PASS with correct-looking config does not prove the click works — the reference deployment dialog shipped dead while every config field was byte-identical to the known-good capture.
- Product records require substantive body content, not only `description`, image and specifications: `content: []` creates a hollow product detail page that passes count/HTTP gates. Verify `read_product.content` is non-empty and a real product fact phrase plus H2 render inside the public `<article>` (ISS-097). Product/article internal links must use page modules with real targets; inline Slate link nodes flatten to text. Dynamic `product-related-grid` is same-category and empties when that category has only one item — use a static cross-category module in that case (ISS-099).
- Heavy workspace pages (`/forms`, theme editor) may hang in embedded browsers; the RSC/API channel (`read_page_document`, `save_home`, list pages) is the equivalent, preferred route.

## 8. References and legacy boundary

- `references/canonical-adapter-routing.md`: active portable resolver/authority explanation.
- `references/README.md`: classifies supplemental versus historical material.
- Other `references/*.md` and non-resolver `scripts/*`: host helpers or historical evidence only. They do not define current fields, payloads, Action IDs, routes, capability maturity, authorization, or execution order, and they never override canonical validation.

Do not copy canonical Schemas, validators, adapters or field contracts into this Skill. Fix the canonical source once, then keep this router thin.

## 8.5 Destructive-operation whitelist gate

Deleting sites, products, posts, taxonomy, media, unpublishing or deleting themes, running `delete-demo-content.py`, or any `--force`/`--confirm` bulk write always requires one-by-one explicit user approval listing exact targets and counts. The canonical `authorizationContext` (30-minute TTL) layers on top of this rule and never replaces it.

## 9. Stop conditions

Stop without remote mutation when any of these is true:

- canonical root, source scope, authenticated user or exact target cannot be proven;
- source facts conflict, lack required evidence, or are not cleared for the planned public effect;
- live fields/capability/current state are stale, missing or weaker than required;
- create/update/noop identity or expected-current fingerprint is unresolved;
- authorization is absent, mismatched, drifted or expired;
- a previous request may have started and read-only reconciliation is not conclusive;
- the requested operation is `exploration_only`, `unsupported`, or otherwise BLOCKed by the canonical Adapter.

Report the exact blocker and the next read-only evidence needed. Do not claim Stable, Published, production-ready, SEO PASS, ranking, inquiries or conversion from local structural evidence.
