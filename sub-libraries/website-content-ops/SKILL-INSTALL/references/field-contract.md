---
doc_id: allincms-bulk-field-contract
title: AllinCMS 字段契约
description: LAICMS / AllinCMS 批量上传 manifest 和 payload 常见字段含义、风险和核验方法
layer: ops
status: draft
created: 2026-06-29
updated: 2026-06-29
page_type: reference
sources: []
confidence: medium
---

# Field Contract

Use this reference before building or accepting a manifest schema. These are platform-operation field definitions, not business-content rules. The live save request remains the source of truth.

## Field Acceptance Gate

Do not treat the tables below as a reusable payload schema. A field may be sent to LAICMS / AllinCMS only after the current run records all of these:

```text
observedInUi: visible list column, edit input, editor node, selector, or media/spec control
capturedInRequest: key, nesting, type, id/source shape, and create/update mode from one real save
writeDecision: send, omit, preserve existing value, or user-deferred
riskReviewed: what breaks if this key is wrong, empty, stale, or in the wrong content type
verification: backend field/list proof plus frontend render proof when public
```

If a field is visible in the UI but absent from the captured request, stop before batch upload and decide whether it is hidden, optional, derived, or controlled by a separate endpoint. If a field appears in the request but not the UI, treat it as internal and preserve it unless the user explicitly authorizes changing it after verification.

## Source Input Requirements

Before generating a manifest from user-provided PDFs, catalogs, datasheets, websites, spreadsheets, or briefs, create a source-input requirements record for the current site and content types. Keep this as run evidence, not as business copy inside the skill.

While operating the browser, also keep a source-input gap ledger with `scripts/record_source_input_gap.py`. This ledger is append-only run evidence for what must be extracted from later user materials. Record a row when you discover any field that needs source material, user confirmation, schema capture, media proof, or an explicit omission/acceptance decision.

Each operation-time gap row should contain:

```text
contentType: global, products, posts, forms, media, themes/pages, routes, site-info, domains, tracking, or navigation
field: user-facing field or logical field name
target: backend field/path or current unknown target
classification: required/recommended/optional plus user-confirmed/source-derived/blocked-until-schema-captured
sourceHint: where a PDF/catalog/brief/spreadsheet should supply it; required, not optional
generationRule: how to turn source material into the target field; required, not optional
currentEvidence: ui-only/request-captured/sample-verified/simulated-only/blocked/not-captured
decisionNeeded: user-must-provide/can-infer-from-source/needs-schema-capture/needs-user-confirmation/omit/preserve-existing/defer
evidencePointer: redacted local evidence path, not a raw cookie/request dump; required, not optional
```

Treat each row as a field intake contract for future source-material processing. A complete row answers:

```text
provider: source-derived, user-confirmed, or both
extraction: what PDF/catalog/website/spreadsheet signal supplies the value
generation: how to normalize it into the backend target
schema proof: UI-only, request-captured, sample-verified, or blocked
upload blocker: what must happen before this value can be included in a live payload
```

If any of these is unknown, mark `decisionNeeded` as `needs-user-confirmation`, `needs-schema-capture`, or `defer`. Do not leave a discovered field undocumented just because the current browser stage cannot fill it. Do not append a gap row with blank `sourceHint`, blank `generationRule`, or blank `evidencePointer`; a later PDF/catalog extractor cannot use a row that lacks those anchors. If `currentEvidence` claims `ui-only`, `request-captured`, or `sample-verified`, add an `operatorNote` explaining what was actually observed.

This is especially important for product specs, body/rich text, media/gallery, contact details, form destinations, route/CTA targets, prices, SKU, variants, and certifications.

Do not put raw PDF text, product copy, personal data, real email values, cookies, auth headers, raw server-action IDs, raw content IDs, or account labels in the ledger. The ledger explains what to ask for or extract; it is not the extracted content itself.

Use this source ownership split while operating:

| Field family | Usually source-derived from PDF/catalog/website/brief | Requires user confirmation before live mutation |
|---|---|---|
| Product content | product names, short descriptions, body sections, applications, specs, certifications explicitly present in source, image alt text | final product selection, duplicate slugs, pricing, inventory, variants, unsupported claims, omit-spec/no-image acceptance |
| Post content | title, excerpt, article outline/body, FAQ, cover alt text | editorial angle, category/tag policy, claims not directly supported by source |
| Theme/page content | homepage copy, solution copy, FAQ blocks, product category sections, draft menu labels | final sitemap/order, CTA destinations, external links, legal/trademark naming, route visibility |
| Forms | draft field labels from inquiry use case | form purpose, required fields, notification destination, privacy/legal copy |
| Media | alt text, product-image matching when source has public image URLs | upload permission, generated-image approval, private/local file usage, gallery inclusion |
| Site-info | description/positioning from approved source | site name for real sites, public contact channels, notification email |
| Routes/domains/tracking | route suggestions from sitemap/source website | route creation/binding, custom domain ownership, DNS proof, tracking provider/code |

If a field sits in the confirmation column, do not treat a PDF/catalog value as sufficient authorization. Record it as `user-confirmed` or `needs-user-confirmation`, then defer the live mutation or ask the user for an explicit acceptance rule.

Use `scripts/make_source_input_requirements.py` to generate this record deterministically from the selected content types plus any current manifest, save-capture evidence, media evidence, and readiness evidence. The script output is a planning/evidence artifact only; it does not validate that live upload is safe and does not authorize browser or JSON mutations.

If an operation-time gap ledger exists, pass it into the requirements builder:

```bash
python3 skills/allincms-bulk-content-upload/scripts/record_source_input_gap.py \
  --validate-only \
  --output ~/allincms-projects/allincms-source-input-gap-ledger.json \
  --site-key current-site-key

python3 skills/allincms-bulk-content-upload/scripts/make_source_input_requirements.py \
  --site-key current-site-key \
  --content-types products,posts,forms,media,themes/pages,site-info,routes,domains,tracking,navigation \
  --gap-ledger ~/allincms-projects/allincms-source-input-gap-ledger.json \
  --output ~/allincms-projects/allincms-source-input-requirements.json
```

The requirements builder also validates supplied ledgers, but run `--validate-only` explicitly when a ledger was hand-merged, produced by parallel read-only agents, or reused after context compaction. The resulting `operationGaps` block is part of the source-intake contract. Use it before extracting user PDFs, catalogs, websites, spreadsheets, or briefs. Static field requirements explain the common model fields; operation gaps explain fields discovered during the current browser run, including fields not yet covered by a reusable static section. If `operationGaps.blockedFields` is non-empty, keep those fields out of live upload until schema capture, user confirmation, or an explicit omission/no-body/no-image acceptance rule resolves them.

Gap ledgers can become stale within the same long browser run. For example, a form gap recorded while only one field was visible must not override later save/publish evidence proving three fields and a current `schema.fields[]` payload. When new request capture or frontend proof supersedes an older gap row, regenerate the requirements record and call out the stale row in run evidence. Do not copy stale `operatorNote` text into a manifest-generation contract without checking the newest evidence pointers.

Because gap ledgers are append-only run evidence, do not edit old rows just to mark them fixed. Instead, create a small resolved-gap evidence file and pass it to the requirements builder:

```json
{
  "kind": "allincms_resolved_source_input_gaps",
  "siteKey": "current-site-key",
  "resolvedGaps": [
    {
      "fieldLabel": "products.specifications",
      "proof": "~/allincms-projects/redacted-product-spec-final-audit.json",
      "note": "Later browser/frontend verification proved the old specification blocker was resolved."
    }
  ]
}
```

Then run:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_source_input_requirements.py \
  --site-key current-site-key \
  --content-types products,posts,forms,media,themes/pages,site-info,routes,domains,tracking,navigation \
  --gap-ledger ~/allincms-projects/allincms-source-input-gap-ledger.json \
  --resolved-gap-evidence ~/allincms-projects/allincms-resolved-source-input-gaps.json \
  --output ~/allincms-projects/allincms-source-input-requirements.json
```

The resolved evidence filters superseded operation gaps out of `operationGaps.blockedFields` and `blockedUntil` while preserving them under `resolvedEntries` for audit. Use this for fields that were later browser-verified, explicitly hidden for demo scope, or deferred with clear public cleanup proof. Do not use it to bypass source fields that still need a user decision or schema capture.

The record should classify each field as:

```text
required
recommended
optional
user-confirmed
source-derived
blocked-until-schema-captured
not-in-scope
```

Do not put `blocked` or `blocked-until-confirmed` in `classification`. `blocked` is a `currentEvidence` value, and user-confirmation blockers should be represented with `classification: required,user-confirmed`, `decisionNeeded: needs-user-confirmation`, and a specific `operatorNote` when UI evidence exists.

For each target field, record:

```text
target content type and backend route
backend key or unknown schema marker
source hint: where to extract it from the PDF/catalog/brief
generation rule: slug, summary, rich body, specs, media, tags, etc.
current evidence: UI-only, request-captured, sample-verified, simulated-only, or blocked
decision needed: user must provide, can infer, omit, preserve existing, or defer
source owner: source material, user confirmation, or both
potential issue: what can go wrong if this field is guessed or schema proof is stale
upload blocker: what must be resolved before the field can enter a live payload
```

Use this requirements record to drive PDF/material extraction. Do not invent missing product specs, prices, certifications, contact details, media, or form destinations. If a source lacks a required field, keep the manifest draft blocked or ask the user for that field before live upload. If a site accepts no-body or no-image content, record that as an explicit user/site acceptance rule in the run evidence before relaxing body/media checks.

## Site-Level Fields

| Field | Meaning | Expected shape | Risks | Verify |
|---|---|---|---|---|
| `siteKey` | Workspace/site path segment used in backend and default frontend subdomain. | non-empty string | Wrong site receives content; frontend URL is built incorrectly. | Compare backend URL and visible site switcher/domain. |
| `siteId` | Internal site identifier from save request. | captured string/id | May differ from `siteKey`; guessing can write to wrong site or fail silently. | Capture from real request. |
| `frontendBaseUrl` | Public frontend origin used for post-publish verification. | `https://...` | Draft/private domain or wrong custom domain gives false QA. | Open list/detail frontend pages. |
| `contentType` | Target model: `posts`, `products`, or media/theme-specific type. | enum confirmed from backend route | Mixing post/product schemas corrupts payload. | Confirm list/edit URL and page heading. |

## Shared Content Fields

| Field | Meaning | Expected shape | Risks | Verify |
|---|---|---|---|---|
| `title` / `name` | Human-visible title/name. Products may use `name`; posts usually use `title`. | non-empty string | Wrong key may save blank title/name. | Inspect input `name`, placeholder, and save payload. |
| `slug` | URL-safe path segment. | lowercase kebab-case string | Duplicate, non-ASCII, uppercase, or changed slug can break routes/links. | Check backend list and frontend detail URL. |
| `excerpt` / `description` | Summary shown in list cards or detail hero. Posts often use `excerpt`; products often use `description`. | string, length appropriate to site | Wrong key, too long, or raw Markdown can show ugly snippets. | Check backend list and frontend cards. |
| `content` | Rich body content. | captured editor block schema, not raw Markdown unless proven supported | Raw Markdown/HTML/MDX may render literally; tables/links/bold can break. | DOM audit for `strong`, `a`, `code`, `table`, lists, and no raw syntax. |
| `order` | Sort order in backend/frontend lists. | integer or numeric string as captured | Duplicate or wrong type can reorder content unexpectedly. | Check list ordering after save. |
| `status` | Draft/published state. | captured enum/action | Save and publish may be separate; HTTP 200 may only save draft. | Backend list status and frontend URL. |
| `categories` | Assigned category objects/ids. | array in captured shape | Names vs IDs can mismatch; old categories can remain if not cleared. | Backend category chips/list and frontend filters. |
| `tags` | Assigned tag objects/ids. | array in captured shape | Existing tags may need creation first; names vs IDs can mismatch. | Backend tag chips/list and frontend tags if rendered. |

## Media Fields

| Field | Meaning | Expected shape | Risks | Verify |
|---|---|---|---|---|
| `coverImage` | Main post/product cover when the model uses image object. | captured object, often `{source,type,url,name,alt}` | Local paths, missing `source/type`, or bad alt break cards. | Backend preview, frontend hero/card image, image DOM. |
| `media` | Product main media when the model uses media object/array. | captured object/array | Product may separate main media and gallery; using `coverImage` may do nothing. | Inspect labels like main media/gallery and save payload. |
| `gallery` | Additional product images/videos. | array in captured shape | Missing public URLs or wrong media type breaks carousel/gallery. | Frontend image/video count and load state. |
| `alt` | Accessibility/SEO text for image. | string | Empty alt may be intentional for decorative images; otherwise weak QA. | DOM image audit. |

## Product-Specific Fields

| Field | Meaning | Expected shape | Risks | Verify |
|---|---|---|---|---|
| `specs` | Product specification groups/rows. | array/table-like block in captured schema | Markdown tables are not enough; frontend may require real table/spec nodes. | Product detail DOM has table/spec section. |
| `price` | Product price. | number/string/currency object as captured | Missing currency, decimal, or display rules can mislead users. | Backend field and frontend price display. |
| `sku` | Stock keeping unit. | string | Duplicate SKU or hidden required field can block save. | Backend payload/field and detail page if visible. |
| `variants` | Product variations. | array in captured shape | Wrong option schema can create unusable product variants. | Backend variant editor and frontend selector. |
| `attributes` | Arbitrary product attributes. | object/array as captured | Can overlap with specs; wrong schema may be ignored. | Captured request and rendered attributes. |
| `inventory` | Stock/availability. | number/object as captured | Wrong defaults may show unavailable or oversell. | Frontend availability and backend inventory field. |
| `categoryIds` | Product category IDs when categories are id-based. | array of IDs | Names may not resolve; stale IDs can assign wrong category. | Compare category management page and payload. |

## Request Fields

| Field | Meaning | Expected shape | Risks | Verify |
|---|---|---|---|---|
| `postId` / `productId` / `pageId` | Existing item identifier for update. | captured id string | Create vs update confusion can duplicate or overwrite content. | URL, save request, and backend list after save. |
| `mode` | Operation mode, often create/update. | captured enum/string | Wrong mode can create duplicate or fail. | Capture from UI save request. |
| action headers | Next/server-action headers or API auth context. | captured headers excluding secrets | Server action IDs/router tree can change after deploy. | Capture fresh for each site/type/version. |

## Theme/Page Fields

These fields are common in theme/page operations, but must still be captured for the current site.

| Field | Meaning | Expected shape | Risks | Verify |
|---|---|---|---|---|
| `themeId` | Theme identifier used by theme page, designer, and route operations. | captured id string | Wrong theme receives pages or design changes; inactive theme can hide valid pages. | Theme URL, theme list row, and design URL. |
| `pageId` | Page identifier under a theme. | captured id string | Updating or publishing the wrong page; duplicate pages with same path. | Page list row, design URL, and public URL. |
| `path` | Public or theme page path such as `/home`. | leading-slash path string | Duplicate paths, route conflicts, or public 404. | Theme page list and frontend exact URL. |
| `routeMode` / `parentPath` | Route hierarchy or mode fields from Server Action payloads. | captured value, sometimes `$undefined` | Guessing can create routes in the wrong tree or silently no-op. | Capture current create/save request. |
| `designBlocks` / `blocks` | Page designer block tree. | captured structured block schema | Empty canvas can still show a published row; wrong schema can disable save or render blank page. | Designer preview plus frontend DOM. |
| theme enabled state | Whether a theme is active for public rendering. | captured UI status/action | Draft/inactive theme can make finished pages unreachable. | Theme list status and public frontend route. |

## Manifest-Only Fields

| Field | Meaning | Expected shape | Risks | Verify |
|---|---|---|---|---|
| `schemaVerified` | Local gate indicating whether this manifest is backed by a current-site captured save request. | boolean | If false or absent, the manifest may be useful for drafting but must not be uploaded or replayed. | `validate_manifest.py --require-schema-verified` before live upload. |
| `payloadTemplate` | Local redacted template from the captured save request. | object | Invented templates can omit hidden IDs or use the wrong content type schema. | Compare to current browser-captured request and sample persistence. |
| `operation` | Intended local operation: create/update. | `create` or `update` | Not necessarily a backend field; do not send unless captured. | Use in local log; compare with payload template. |
| `frontendUrl` | Expected final URL. | generated public URL | Wrong route template hides publish failures. | Open exact URL after save/publish. |
| `sourceRef` | Local/source pointer for traceability. | string path/URL/id | Can leak business/private source if copied into public payload. | Keep in local manifest/log only unless backend has private notes. |

## Field-Level Stop Conditions

Stop before batch upload if any of these are true:

```text
title/name key is not confirmed for this content type
slug route pattern is not confirmed
content is a raw Markdown string and rich text is expected
cover/media field shape is not captured
categories/tags require IDs but only names are available
products have visible specs/variants/price/SKU fields but payload omits them without user decision
publish status is not proven separately from save
frontend route uses a different token than /posts/{slug} or /products/{slug}
```
