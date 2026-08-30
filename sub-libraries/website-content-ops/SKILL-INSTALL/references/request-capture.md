---
doc_id: allincms-bulk-request-capture
title: AllinCMS 保存请求捕获
description: LAICMS / AllinCMS 探针内容、保存请求捕获、持久化证明和回放安全规则
layer: ops
status: draft
created: 2026-06-29
updated: 2026-07-05
page_type: reference
sources: []
confidence: medium
---

# Request Capture

Use this reference before creating a probe item, saving through the UI, or replaying any request.

## Authorization Gate

Ask for explicit authorization before any action that creates, edits, publishes, unpublishes, deletes, or batch uploads remote content.

For request capture, sample upload, replay, or batch upload, the authorization must name the operation and target the current backend site path:

```json
{
  "authorization": {
    "userAuthorized": true,
    "authorizedAction": "create probe and save sample content",
    "target": "https://workspace.laicms.com/{siteKey}/posts",
    "authorizationSource": "current user instruction",
    "verificationPlan": "capture save request, verify backend persistence, then verify frontend render"
  }
}
```

Do not reuse site creation, cleanup, deletion, or generic continuation authorization as permission to create a probe, save, upload, replay, batch publish, or publish content.

Allowed probe names must include:

```text
Codex Probe - Delete Me
```

Never use real business titles for request capture.

For the first create-probe click in a content module, validate the gate before touching the browser:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action create_product_probe \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-create-product-probe.json
```

Passing this gate only authorizes opening/creating the probe draft for that exact module. Saving the probe, publishing it, replaying its request, or cleaning it up each need their own authorization and evidence.

Before saving the probe to capture the real request, generate a separate `save_probe` authorization and run the save gate:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action save_probe \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-save-product-probe.json
```

The save authorization must name the exact backend edit URL, content type, probe title, and capture/request/persistence intent. A prior `create_product_probe` authorization is not permission to save.

After a create-probe stage has produced a draft edit URL, build a local save runbook before touching the browser again:

```bash
python3 skills/allincms-bulk-content-upload/scripts/prepare_probe_save_handoff.py \
  --create-evidence ~/allincms-projects/allincms-create-probe-evidence.json \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --edit-url https://workspace.laicms.com/{siteKey}/products/{productId}/update \
  --authorization-output ~/allincms-projects/allincms-authorization-save-product-probe.json \
  --output ~/allincms-projects/allincms-save-probe-handoff.json
python3 skills/allincms-bulk-content-upload/scripts/build_probe_save_runbook.py \
  ~/allincms-projects/allincms-save-probe-handoff.json \
  --output ~/allincms-projects/allincms-save-probe-runbook.json
python3 skills/allincms-bulk-content-upload/scripts/validate_probe_save_runbook.py \
  ~/allincms-projects/allincms-save-probe-runbook.json \
  --expect-missing-authorization \
  --output ~/allincms-projects/allincms-save-probe-runbook-validation.json
```

The runbook is still local preparation. Its `browserStepsAfterGate` must not be executed until the `save_probe` authorization record exists and `check_pre_mutation_gate.py --action save_probe` passes. Treat the runbook as the operator checklist for field edits, network capture, persistence verification, and forbidden actions after the gate passes.

The save runbook separates two concepts:

```text
automationPreferenceDoesNotAuthorize = broad "continue" preferences that still do not authorize saving
forbiddenActions = actions still forbidden even after the save gate, such as publish, delete, upload, batch, replay, or repeated saves
```

Do not put `saving the probe` in `forbiddenActions`; the save is the exact gated action. Before browser execution after authorization, rerun:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_probe_save_runbook.py \
  ~/allincms-projects/allincms-save-probe-runbook.json \
  --fail-on-blocked
```

Only `status: ready_after_gate` makes the runbook executable.

For rich body editors, prove the editable surface before saving. A visible `contenteditable` node or placeholder is not enough:

```text
1. Confirm the editor locator is unique.
2. Focus or type into the editor with the current browser surface.
3. Verify the editor text changed.
4. Verify the `更新` / save button becomes enabled.
5. Only then click save and capture the request.
```

If the browser cannot click or focus the editor, stop and record a blocked attempt. Do not click save through another path, do not claim request capture, and do not treat a passed pre-mutation gate as proof that content was edited or persisted.

If publish is needed for frontend detail verification, generate a separate `publish_probe` authorization and run the publish gate:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action publish_probe \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-publish-product-probe.json
```

The publish authorization must name the exact backend edit URL, content type, probe title, publish intent, and frontend verification expectation. A `save_probe` authorization is not permission to publish.

After request capture is merged and `summarize_run_status.py` emits `authorize_publish_probe`, build a publish runbook before touching the browser:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_probe_publish_runbook.py \
  --run-evidence ~/allincms-projects/allincms-run-evidence-after-request-capture.json \
  --authorization-output ~/allincms-projects/allincms-publish-probe-authorization.json \
  --output ~/allincms-projects/allincms-publish-probe-runbook.json
```

The runbook is local preparation only. It must retain the authorization placeholder and `browserStepsExecutable: false` until the `publish_probe` authorization record exists and the publish gate passes. The only gated mutation is one `发布` click for that probe; cleanup, upload, batch, replay, or repeated publish clicks remain forbidden.

After the publish-probe browser run, validate and merge sample proof:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_probe_publish_sample_evidence.py \
  ~/allincms-projects/allincms-publish-sample-evidence.json \
  --base-run-evidence ~/allincms-projects/allincms-run-evidence-after-request-capture.json \
  --merge-args-output ~/allincms-projects/allincms-publish-sample-merge-args.json \
  --output ~/allincms-projects/allincms-publish-sample-validation.json
python3 skills/allincms-bulk-content-upload/scripts/merge_probe_evidence.py \
  --base ~/allincms-projects/allincms-run-evidence-after-request-capture.json \
  --publish-sample-evidence ~/allincms-projects/allincms-publish-sample-evidence.json \
  --output ~/allincms-projects/allincms-run-evidence-after-publish-sample.json
python3 skills/allincms-bulk-content-upload/scripts/summarize_run_status.py \
  ~/allincms-projects/allincms-run-evidence-after-publish-sample.json \
  --output ~/allincms-projects/allincms-run-summary-after-publish-sample.json
```

The publish sample evidence must prove `publishedOnce`, `publishRequestCaptured`, backend status, frontend HTTP/detail render, title/name, body, cover/media state or an explicit absence note, and no raw Markdown residue. It must be bound to the same base run evidence before merge.

## Capture One Real Save

Use browser network inspection while saving a probe item through the UI. Record:

```text
request URL
method
required headers
payload format
content block structure
coverImage or media structure
siteId
postId, productId, pageId, or mediaId
mode
status behavior
whether publish is a separate action
```

For run evidence, summarize these fields explicitly:

```text
headers: redacted required header names and volatile server-action notes
payloadShape: redacted top-level shape
contentBlockShape: editor block/mark/table shape summary
idFields: siteId plus postId/productId/formId/etc. field names, redacted values
mode: create/update/publish behavior as captured
publishBehavior: save-only, publish-separate, or save-and-publish if proven
persistedVerified: true only after backend or frontend proof
```

After a save-probe browser run, write redacted capture evidence as `allincms_probe_save_capture_evidence` and validate it before merging:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_probe_save_capture_evidence.py \
  ~/allincms-projects/allincms-save-capture-evidence.json \
  --base-run-evidence ~/allincms-projects/allincms-run-evidence.json \
  --merge-args-output ~/allincms-projects/allincms-save-capture-merge-args.json \
  --output ~/allincms-projects/allincms-save-capture-validation.json
python3 skills/allincms-bulk-content-upload/scripts/merge_probe_evidence.py \
  --base ~/allincms-projects/allincms-run-evidence.json \
  --save-capture-evidence ~/allincms-projects/allincms-save-capture-evidence.json \
  --output ~/allincms-projects/allincms-run-evidence-after-request-capture.json
python3 skills/allincms-bulk-content-upload/scripts/summarize_run_status.py \
  ~/allincms-projects/allincms-run-evidence-after-request-capture.json \
  --output ~/allincms-projects/allincms-run-summary-after-request-capture.json
```

The evidence must use header names only. Never store raw cookies, authorization header values, raw `next-action` values, `next-router-state-tree` blobs, account emails, or raw IDs. The validator requires `savedOnce: true`, `published: false`, `preMutationGate: passed`, `backendPersisted: true`, `stopConditionMet: true`, a concrete edit `target`, a current-site POST `requestCapture.url`, verified `fieldMapping`, and a redacted `payloadTemplate`. Use `--base-run-evidence` so the capture is bound to the same `siteKey` and `contentType` before merge, not only during merge.

After request-capture-only merge, full `validate_run_evidence.py` may still fail with missing `sampleVerification`; that is expected phase evidence until a separate publish/sample verification authorization runs. Use `summarize_run_status.py --output` to confirm the next action is `authorize_publish_probe`. The summarizer has no `--json` flag; read the output file instead of passing one.

The captured save URL must belong to the verified backend site key:

```text
https://workspace.laicms.com/{siteKey}/...
```

Do not treat a request URL as valid merely because it mentions the site key somewhere in a query string, router state, or payload text.

Do not paste raw authorization headers, cookies, server action IDs, router state blobs, account emails, or raw payloads into evidence.

## Public Form Submission Capture

Public form submissions can also use Next.js Server Action requests, but they are not the same as backend post/product/form-definition saves. Treat them as integration proof for the public site, not as a reusable content payload template.

When the browser tab exposes the `cdp` capability, a public form test can capture redacted Network events:

```text
Network.enable
cursor from readEvents()
fill neutral test data
click submit
read Network.requestWillBeSent and Network.responseReceived after the cursor
record URL, method, resource type, header names, hasPostData, postData length, response status, and mime type
```

Do not store form field values, raw `postData`, cookies, server-action header values, or `next-router-state-tree`. Header names and payload length are enough for proof that a submit request was sent. A verified public contact-form submit used:

```text
POST /contact-us
type: Fetch
request headers: Accept, Content-Type, Referer, User-Agent, next-action, next-router-state-tree, sec-ch-*
hasPostData: true
response: 200 text/x-component
```

This proves request/response, not destination delivery. Public form launch readiness still needs a non-static success state, backend submission record/count, email/webhook destination proof, or an explicit demo-scope acceptance that request/response proof is sufficient.

## JSON Acceleration Gate

> The single authoritative "may I use JSON at all" gate is `official-docs-alignment.md` §JSON Acceleration Gate (the action must belong to the official-docs step currently being executed, plus the generic captured/known-IDs/verifiable/rollback checks). This section is not a second copy of that gate — it adds the **capture-first prerequisites** that are this file's job (a real UI request captured for the exact action, fresh volatile headers, a redacted per-action contract). When the two lists overlap, treat official-docs-alignment as canonical.

JSON or Server Action submission can be faster for repetitive work such as creating theme pages, creating routes, saving design changes, or uploading multiple posts/products. Treat it as an acceleration path, not as the source of truth.

Before replaying, in addition to the official-docs-alignment gate, these capture-first facts must be true:

```text
current site key and internal siteId were confirmed in the live backend
the exact content type was confirmed: theme, page, route, form, post, product, or media
one real UI request was captured for that exact action in the current site/version
required volatile headers were captured fresh and redacted in evidence
payload IDs such as siteId, themeId, pageId, postId, or productId came from the current backend
the user authorized replay for this exact action and target
one replayed sample was verified in backend state and public frontend state when public
```

Do not replay JSON if the only evidence is a similar request from another site, another content type, or an older browser session.

After those facts are captured, encode them as a redacted per-action contract and validate it:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_action_replay_contract.py \
  ~/allincms-projects/allincms-action-replay-contract.json
```

The contract must use header names only, not values. It must never store raw cookies, authorization headers, raw `next-action` IDs, router state blobs, account emails, raw payloads, or object IDs as values. A passing contract makes only that exact action replay-ready locally; it is not user authorization and it is not proof that adjacent actions or batch upload are safe.

For theme/page work, capture these actions separately when they are in scope:

```text
create theme
create page under a theme
save page design blocks
publish page
activate or publish theme, if exposed
create or bind route
```

The page creation payload is not evidence for page design save, route binding, publish, or theme activation. Each operation may use a different endpoint, action header, payload body, and persistence rule.

For theme page design save, one verified 2026-06-29 run showed a Next.js Server Action POST to the exact design URL:

```text
POST /{siteKey}/themes/{themeId}/{pageId}/design
Accept: text/x-component
Content-Type: text/plain;charset=UTF-8
next-action: <captured server action id>
next-router-state-tree: <captured router state>
```

The redacted payload shape was an array with one object:

```json
[
  {
    "siteId": "<internal site id, not siteKey>",
    "themeId": "<theme id>",
    "pageId": "<page id>",
    "intent": "save",
    "pageDocument": {
      "root": "page-root",
      "elements": {
        "<block instance id>": {
          "type": "<designer block type>",
          "props": {}
        }
      }
    }
  }
]
```

Do not synthesize `pageDocument` from desired copy alone. First insert a block through the designer, save once, and use the captured block type, element IDs, and prop schema as the template for that page/theme version.

For editing an existing `hero-commerce` block, one verified 2026-06-29 run showed that the designer saves the block as:

```json
{
  "pageDocument": {
    "root": "page-root",
    "elements": {
      "hero-commerce-1": {
        "type": "hero-commerce",
        "children": [],
        "props": {
          "eyebrow": "...",
          "title": "...",
          "description": "...",
          "secondaryNote": "...",
          "media": {
            "type": "image",
            "value": {
              "name": "...",
              "type": "image",
              "source": "url",
              "url": "https://..."
            }
          },
          "fit": "cover",
          "mediaCaption": "...",
          "mediaKicker": "...",
          "mediaMeta": "...",
          "productName": "...",
          "productDescription": "...",
          "productPriceLabel": "...",
          "serviceItems": [
            {"label": "...", "value": "..."}
          ],
          "campaignPills": [
            {"label": "...", "value": "..."}
          ],
          "actions": [
            {
              "label": "...",
              "target": {"type": "custom", "href": "/..."},
              "variant": "..."
            }
          ]
        }
      }
    }
  }
}
```

Use the live Inspector field names and the saved payload to build a template. Do not treat the visible text order as the schema; repeated labels such as `Label` and `Value` occur under different arrays.

When constructing a `pageDocument` for an empty page, include the explicit root element. Server Actions can return HTTP 200 while embedding validation errors in the component response:

```json
{
  "root": "page-root",
  "elements": {
    "page-root": {
      "type": "page-root",
      "props": {},
      "children": ["hero-commerce-1"]
    },
    "hero-commerce-1": {
      "type": "hero-commerce",
      "props": {},
      "children": []
    }
  }
}
```

Known failed shapes:

```text
missing block children -> serverError: Element "<id>" children must be an array of element ids.
missing page-root element -> serverError: Document root "page-root" is missing from elements.
action target as plain href -> visible link may keep a stale target; use target: {type, href}
```

For theme page publish, one verified 2026-06-29 run showed the same design URL and headers, with a smaller payload:

```json
[
  {
    "siteId": "<internal site id, not siteKey>",
    "themeId": "<theme id>",
    "pageId": "<page id>",
    "intent": "publish",
    "pageDocument": "$undefined",
    "globals": "$undefined",
    "themeConfig": "$undefined"
  }
]
```

The designer status changed to `Published`, but `Public 404` remained while the theme was still inactive or routing was incomplete. Treat publish as necessary but not sufficient for frontend availability; verify active theme and route/home binding separately.

For setting a theme page as homepage, one verified 2026-06-29 run showed a Next.js Server Action POST to the theme detail URL:

```text
POST /{siteKey}/themes/{themeId}
```

Payload shape:

```json
[
  {
    "id": "<page id>",
    "siteId": "<internal site id>",
    "themeId": "<theme id>"
  }
]
```

The backend showed a homepage-updated toast, but the theme can still remain inactive. Homepage binding alone is not proof that the frontend root or page URL renders.

In a later verified 2026-06-29 run, clicking `将 Home 设为首页` on the theme page list sent this same payload shape and changed the public root `/` from 404 to the Home page. The route table still did not contain a `/` row, and trying to create `/` through routes returned `validation.routePath.rootInvalid`. Treat theme-page homepage binding as the root-home mechanism for that version, separate from the routes module.

For enabling a theme page, one verified 2026-06-29 run showed the same theme detail URL with the homepage payload plus an enabled flag:

```json
[
  {
    "id": "<page id>",
    "siteId": "<internal site id>",
    "themeId": "<theme id>",
    "enabled": true
  }
]
```

One attempt returned a visible write-conflict message. When this happens, do not assume success from HTTP 200; wait, refresh or re-read the row, then retry only if the backend state is still unchanged. JSON replay should serialize page mutations instead of firing homepage, enable, publish, and route updates concurrently.

For starting theme activation from the theme list, one verified 2026-06-29 run showed:

```text
POST /{siteKey}/themes
payload: ["<internal site id>", "<theme id>"]
```

This did not immediately activate the theme. It opened a route-mapping confirmation dialog when site routes were not fully bound. The dialog listed route rows such as `/home`, `/about-us`, `/products`, `/posts/{post}`, each with current page, target page, and binding status, plus `取消` and `应用主题`.

Do not claim theme activation until the final `应用主题` action is captured or the theme list confirms the theme is active. If the dialog appears, route mapping must be reviewed before applying the theme.

For applying theme activation from the route-mapping dialog, one verified 2026-06-29 run showed a separate Next.js Server Action:

```text
POST /{siteKey}/themes
Accept: text/x-component
Content-Type: text/plain;charset=UTF-8
next-action: <captured server action id>
next-router-state-tree: <captured router state>
```

The redacted payload shape was:

```json
[
  {
    "id": "<theme id>",
    "siteId": "<internal site id>",
    "mappings": [
      {
        "routePath": "/home",
        "pageId": "<page id or empty string>"
      }
    ]
  }
]
```

The route list in the dialog can include unbound routes with empty `pageId`. If applied that way, the backend may mark the theme active while those public routes remain unavailable. Capture and review every mapping row before applying. Do not infer the mappings from page slugs; use the dialog or route module state.

After applying, verify three separate surfaces:

```text
theme list: row shows active/enabled
theme detail: intended pages are enabled, not just published
routes page: intended paths are bound, not just present
frontend: HTTP status and rendered DOM contain the expected content
```

One verified run produced an active theme row while the theme detail page still showed page enabled switches as false and the route module showed several paths as unbound. Public URLs then returned 404 or an empty runtime shell. Treat that as failed launch verification, even if the backend action returned HTTP 200 and displayed a success toast.

For theme page creation, one verified 2026-06-29 run showed a Next.js Server Action POST to the theme detail URL:

```text
POST /{siteKey}/themes/{themeId}
Accept: text/x-component
Content-Type: text/plain;charset=UTF-8
next-action: <captured server action id>
next-router-state-tree: <captured router state>
```

The redacted payload shape was an array with one object:

```json
[
  {
    "path": "/about-us",
    "query": "",
    "routeMode": "$undefined",
    "parentPath": "$undefined",
    "siteId": "<internal site id, not siteKey>",
    "themeId": "<theme id>",
    "name": "About Us",
    "description": "Page purpose summary",
    "_status": "draft"
  }
]
```

Do not reuse the `next-action`, `next-router-state-tree`, `siteId`, or `themeId` across sites without capturing them fresh. `siteId` is an internal ID and differs from `siteKey`.

For route creation, one verified 2026-06-29 run showed a Next.js Server Action POST to:

```text
POST /{siteKey}/routes
Accept: text/x-component
Content-Type: text/plain;charset=UTF-8
next-action: <captured server action id>
next-router-state-tree: <captured router state>
```

The redacted payload shape was:

```json
[
  {
    "siteId": "<internal site id>",
    "path": "/solutions",
    "query": "",
    "routeMode": "$undefined",
    "parentPath": "$undefined",
    "note": "Default route"
  }
]
```

If the path matches an existing theme page route option, creating the route can auto-bind it to the page. Verify the route table row shows the page name and `已绑定`, then verify the public frontend route. A root path `/` was rejected by the same Server Action with `validation.routePath.rootInvalid`, while HTTP status was still 200.

In the in-app browser runtime, Playwright page evaluation is read-only and may not expose `fetch` for replaying authenticated Server Action POSTs. Capturing the payload is still useful for building a template, but replay must use an approved mechanism that preserves the current browser auth context without reading cookies, or fall back to UI submission.

Next.js server actions may require headers like:

```js
{
  "Accept": "text/x-component",
  "Content-Type": "text/plain;charset=UTF-8",
  "next-action": "<server-action-id>",
  "next-router-state-tree": "<encoded-router-state-tree>"
}
```

Do not assume these headers are stable across deployments. Capture them fresh for the current content type.

## Persistence Proof

HTTP 200 is not enough. After saving:

1. Reopen the backend edit page and confirm the changed fields are present.
2. Open the backend list page and confirm status, title/name, slug, and cover state.
3. Open the frontend detail URL and confirm the rendered content.
4. If publish is separate, prove both draft save and publish action separately.

## Payload Template

Build a template from the captured request, not from memory. The hypotheses below are pre-capture
placeholders; the **authoritative per-type field contract is `server-action-save-api.md` §3** —
products use `name` + `specifications` + `media` (NOT `title`/`specs`), posts use `title` +
`excerpt` + `coverImage`. When a hypothesis below disagrees with §3, §3 wins (replaying the old
`title`/`specs` assumption breaks product fields).

Post hypothesis:

```js
{
  title,
  slug,
  excerpt,
  order,
  coverImage: {
    source: "url",
    type: "image",
    url,
    name,
    alt
  },
  categories: [],
  tags: [],
  content,
  siteId,
  postId,
  mode: "update"
}
```

Product hypothesis (field names per `server-action-save-api.md` §3 — products use `name` / `media` / `specifications`, NOT `title` / `coverImage` / `specs`):

```js
{
  name,
  slug,
  description,
  order,
  media: {
    source: "url",
    type: "image",
    url,
    name,
    alt
  },
  categories: [],
  tags: [],
  specifications: [],
  content,
  siteId,
  productId,
  mode: "update"
}
```

These examples are not authority. Replace them with the captured schema for the current site and type.

## Replay Safety

When replaying requests:

- Use the exact content type template.
- Include only public image URLs.
- Track each item: input slug, backend ID, save response, publish response, backend verification, frontend verification, cleanup status.
- Stop the batch after the first failure until the cause is understood.
