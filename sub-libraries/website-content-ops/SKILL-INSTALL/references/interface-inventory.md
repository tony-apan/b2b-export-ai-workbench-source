---
doc_id: allincms-bulk-interface-inventory
title: AllinCMS 模块接口矩阵
description: LAICMS / AllinCMS 各后台模块接口检测、JSON 化判断和验证要求
layer: ops
status: "Working"
created: 2026-06-29
updated: 2026-07-05
page_type: reference
sources: ["self"]
confidence: medium
last_updated: 2026-08-31
visibility: "public"
redaction_status: "safe-to-publish"
related: ["../README.md"]
owner: "AI"
type: "doc"
---

# Interface Inventory

Use this reference when deciding whether a LAICMS / AllinCMS operation should be done through JSON/Server Action replay or through the UI.

## Rule

JSON is better for speed only after the exact operation is captured and verified. Build one interface row per module and per action:

```text
module
action: list, create, save, publish, enable, upload, delete, bind, verify
backend URL
method
request type: page load, API JSON, multipart upload, Next.js Server Action, unknown
required volatile headers, redacted
payload shape, redacted
id fields: siteId, themeId, pageId, postId, productId, routeId, formId, mediaId
side effect
JSON suitability: yes, conditional, no, unknown
verification: backend state plus frontend render when public
```

Do not merge actions. A `create page` request is not a `save design` request; a `save draft` request is not a `publish` request.

Do not use JSON replay to bypass the official build order. For from-scratch sites, first determine whether the default template already created usable themes/pages/categories/products/posts. Read `official-docs-alignment.md` when the run spans more than one module. JSON/Server Action acceleration is appropriate only after the current operation has a documented purpose in the tutorial flow and the exact action has been captured and verified. For example, a captured `create blank theme` request must not be reused when the docs-required action is `create default theme`, and a captured `create page` request must not stand in for route binding, page enablement, design save, or frontend verification.

Read-only navigation commonly triggers sibling route prefetches such as `GET /{siteKey}/products?_rsc={token}` while the current page is `/{siteKey}/routes`, `/{siteKey}/forms`, or another module. Treat these as page/component fetches only. They prove the route can be read, not that products, posts, forms, or themes have a JSON save/create API ready for replay. A mutation row requires a captured action-specific `POST`, its payload shape, and backend/frontend persistence verification.

After collecting a redacted module scan JSON, summarize it before storing evidence:

```bash
python3 skills/allincms-bulk-content-upload/scripts/summarize_module_scan.py \
  ~/allincms-projects/allincms-module-scan.json \
  --output ~/allincms-projects/allincms-module-scan-summary.json
```

The scan file can be either a request-oriented list of module records or a redacted browser-scan object with a `modules` map. If the scan object contains only DOM evidence (`url`, headings, table headers, inputs, buttons) and no network request list, the summary must stay at `read_only_only` with `visible_control_only` inferred actions. That means the operator has proved module visibility and possible controls, not JSON/Server Action replay readiness.

The scan summary intentionally distinguishes three states:

```text
read_only_only = only document/list evidence was captured
read_only_prefetch_only = document plus RSC GET prefetches were captured; no mutation API is proven
captured_post_requires_review = a POST-like request exists, but payload shape, IDs, authorization, and persistence proof still need action-level review before replay
```

Do not interpret `captured_post_requires_review` as "JSON ready." It means the operation is a candidate for JSON acceleration after the exact action row is reviewed and sample persistence is verified.

Safe redacted scans may preserve a real lowercase site key in `workspace.laicms.com/{siteKeyLike}/...` URLs. The summary helper accepts safe site-key-shaped paths and `{siteKey}` placeholders, but still rejects volatile headers, cookies, authorization values, `next-action`, `next-router-state-tree`, and unsafe path tokens.

The summary also emits top-level readiness fields:

```text
jsonReplayReady = false unless a future validator proves the full action-specific replay contract
blockedReplayActions = visible or captured actions that must not be replayed yet
captureNextActions = visible controls that need fresh request capture before replay analysis
```

For read-only DOM scans, use `captureNextActions` as the browser-capture checklist. It is not an upload or replay plan.

After module capture coverage is complete, keep two states separate:

```text
interfaceCoverageComplete = every planned module/action capture stage was captured or marked not applicable
jsonReplayReady = an exact action replay contract is verified for replay
```

Complete interface coverage may unlock the next browser stage in the runbook, but it must not be used as permission to JSON replay or batch-submit. `jsonReplayReady` stays false until each concrete action has a current request URL, method, volatile header names, payload shape, required IDs, authorization boundary, backend persistence proof, frontend proof when public, and rollback/cleanup plan.

Capture-plan gate coverage is preparation evidence, not module interface completion. A file such as `allincms_capture_plan_gate_coverage` proves that planned actions have authorization-action mappings and that unsupported actions are explicitly allowlisted or rejected. It does not prove any action was captured, persisted, or replay-ready. Keep `module_interface_capture_complete` blocked until a real `allincms_module_capture_coverage` file is complete with every planned stage captured or marked not applicable, plus replay-ready contracts or explicit UI-first completion.

Once a single action has all of that proof, validate a redacted action replay contract:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_action_replay_contract.py \
  ~/allincms-projects/allincms-action-replay-contract.json
```

This validator is intentionally action-level. A valid `save_design` contract does not validate `publish_design`; a valid `create_route` contract does not validate route binding; a valid product `save_probe` contract does not validate posts or batch upload.

If all captured stages in a module coverage file have matching valid contracts, aggregate them locally:

```bash
python3 skills/allincms-bulk-content-upload/scripts/apply_action_replay_contracts.py \
  --coverage ~/allincms-projects/allincms-module-capture-coverage.json \
  --contract ~/allincms-projects/allincms-action-a-contract.json \
  --contract ~/allincms-projects/allincms-action-b-contract.json \
  --output ~/allincms-projects/allincms-module-capture-coverage-replay-ready.json
```

The aggregator rejects missing, duplicate, invalid, or wrong-stage contracts. A replay-ready coverage file is still a technical-readiness artifact only; user authorization and mutation gates remain separate.

To turn that checklist into staged browser work, generate a capture plan:

```bash
python3 skills/allincms-bulk-content-upload/scripts/plan_module_capture.py \
  ~/allincms-projects/allincms-module-scan-summary.json \
  --site-key safe-site-key \
  --output ~/allincms-projects/allincms-module-capture-plan.json
```

The plan groups actions by authorization boundary, target URL, stop condition, and required proof. It is a sequencing aid only. Execute at most one stage per explicit user authorization; after each stage, re-run the relevant evidence and closeout checks before continuing.

For one selected stage, prepare an authorization package:

```bash
python3 skills/allincms-bulk-content-upload/scripts/prepare_capture_authorization.py \
  ~/allincms-projects/allincms-module-capture-plan.json \
  --module products \
  --action create \
  --preflight ~/allincms-projects/allincms-created-site-evidence.json \
  --authorization-output ~/allincms-projects/allincms-auth-products-create.json \
  --output ~/allincms-projects/allincms-auth-products-create-package.json
```

The package contains suggested user-facing authorization text plus local commands to generate an authorization record and run the pre-mutation gate when supported. The suggested text is not itself authorization unless the user explicitly sends it as the current instruction. Do not run the generated mutation gate against stale evidence, and do not use the package to combine multiple stages.

Capture authorization packages must keep the authorization source as a visible placeholder:

```text
<paste current user authorization text here>
```

The generated command must not embed `suggestedAuthorizationText` or helper-generated wording such as `授权 Codex` as the `--authorization-source`. Suggested wording is only a draft for the user to approve or rewrite in the current conversation.

Validate the package before using it:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_capture_authorization_package.py \
  ~/allincms-projects/allincms-auth-products-create-package.json \
  --plan-json ~/allincms-projects/allincms-module-capture-plan.json
```

Passing validation means the package aligns with one capture-plan stage, retains the current-user authorization placeholder, and any emitted commands target a concrete backend URL. It still does not create an authorization record and does not permit a browser mutation. If the package is command-suppressed, templated, simulated, or already contains suggested authorization text in a command, rebuild it from current real-site evidence before asking for action-time authorization.

For package-set summaries generated by `prepare_all_capture_authorizations.py`, read the actual JSON shape:

```text
count
items[].module
items[].action
items[].authorizationAction
items[].target
items[].gateSupported
items[].package
```

Do not expect `packageCount` or `packages`. Those names are not part of the current helper output.

## Current Verified Matrix

| Module | Action | Captured behavior | JSON suitability | Must verify |
|---|---|---|---|---|
| dashboard/module pages | read page/list | Page navigation loads a document and often prefetches sibling modules through RSC `GET /{siteKey}/{module}?_rsc=...`. | Yes for read-only scanning, not enough for mutation. | Visible module route, headings, columns, counts, and no unintended drafts. |
| themes | read list | Theme list shows search, `创建主题`, status, route configuration, page/design/preview controls. | Yes for read-only scanning. | Theme status, page count, and controls. |
| themes | create theme | Prior verified UI opened a dialog with name, preset, description; final submit creates a draft theme. | Conditional yes after fresh create-theme request capture. | New theme row appears with expected status and controls. |
| themes | start activation | Theme list switch sent Server Action `POST /{siteKey}/themes` with `[siteId, themeId]`, then opened route-mapping confirmation when routes were not fully bound. | Conditional; not sufficient by itself. | Route mapping dialog or final active theme state. |
| themes | apply activation | Route-mapping dialog `应用主题` sent Server Action `POST /{siteKey}/themes` with `id` as theme id, `siteId`, and `mappings: [{routePath, pageId}]`. Backend changed the theme row to active/enabled after success. | Conditional yes after fresh capture; this is a separate action from the switch click. | Theme list active/enabled state, route binding state, page enabled state, and frontend HTTP plus DOM render. |
| themes/pages | create page | Next.js Server Action `POST /{siteKey}/themes/{themeId}` with `siteId`, `themeId`, `path`, `name`, `description`, `_status`. | Conditional yes after fresh capture. | Page row appears under the same theme and design URL opens. |
| themes/pages | create dynamic child page | Products-page child creation can expose a param route editor with `{product}` as an allowed route value. This is the required precursor when `/products/{product}` exists but is unbound and no product-detail page exists. | Conditional yes after fresh capture; separate from route binding. | Child page row appears under the theme with route `/products/{product}` or equivalent page route; page id and backend row are recorded before design/publish/enable. |
| themes/pages | read page list | Theme detail page exposes columns such as name, route, query, home, enabled, description, status, created time. | Yes for read-only scanning. | Columns and page rows match current theme. |
| themes/pages | set homepage | Next.js Server Action `POST /{siteKey}/themes/{themeId}` with `id` as page id plus `siteId` and `themeId`. In one verified run, setting Home as homepage changed public `/` from 404 to the Home page without adding a `/` route row. | Conditional yes after fresh capture. | Frontend root `/` renders intended page, `/home` still renders, theme active, and page enabled/published. |
| themes/pages | enabled toggle | Next.js Server Action `POST /{siteKey}/themes/{themeId}` with page id, siteId, themeId, and `enabled: true`. One attempt showed a write-conflict message despite HTTP 200, so row state must be re-read before retry. | Conditional yes after fresh capture; serialize mutations. | Backend enabled checkbox/row state and frontend route resolution. |
| themes/pages/design | insert block | UI path: open block category, select a concrete block, then click `Add Block`. Drag/drop or AI `insert-block Done` alone was not enough. | Do not replay until the resulting save payload is captured. | Canvas/Layers shows the block and Save becomes enabled. |
| themes/pages/design | insert product detail block | Verified Product Detail path: open Blocks > Products, select `Product Detail (Gallery)`, then click explicit `Add Block`; only after that did `No blocks yet` disappear and Save enable. | UI-first until a saved `pageDocument` for the exact block is captured and verified. | Block visible in canvas/Inspector, Save enabled before save, Save disabled after save, status Draft, Publish remains separate. |
| themes/pages/design | edit existing block props | Selecting a canvas block may show the overlay but still leave Inspector on `No block selected` or `Loading props...`; selecting through Layers or the block overlay can eventually expose typed Props fields. Existing `hero-commerce` props include eyebrow, title, description, secondaryNote, serviceItems, campaignPills, actions, media fields, and product card fields. | UI-first until the current block props schema is captured. JSON can be used only after a saved payload confirms element id, type, and props shape. | Canvas preview updates, Save enables, save request includes changed props, and frontend renders changed text after publish. |
| themes/pages/design | hide existing block | Per-instance hide controls are exposed from `Layers`, not from the insert-oriented `Blocks` tab. Clicking `Hide <module>` changes the control to `Show <module>` and enables Save/Publish. | Conditional after fresh save/publish capture; UI-first when no payload contract exists for hidden state. | Layer button remains `Show <module>`, Save disables after save, Publish disables after publish, and public DOM no longer renders the hidden module content. |
| themes/pages/design | remove placeholder external links | Some Footer/contact link arrays expose segmented target controls such as `None`, `Custom`, `Internal`, and `Action`. Choosing `None` for an unconfirmed social entry can remove the public `href` while leaving the label text visible. | UI-first until the saved payload confirms target object shape. | Public DOM has no external placeholder link; if the label remains as plain text, decide whether that is acceptable or hide/delete the block. |
| themes/pages/design | save design | Next.js Server Action `POST /{siteKey}/themes/{themeId}/{pageId}/design` with `siteId`, `themeId`, `pageId`, `intent: "save"`, and `pageDocument`. A real save changed designer status from Published to Draft and left Publish enabled. | Conditional yes after a block schema template exists for this theme version. | Save button becomes disabled, designer can be reopened with changed props, and publish remains a separate step. |
| themes/pages/design | publish design | Next.js Server Action `POST /{siteKey}/themes/{themeId}/{pageId}/design` with `intent: "publish"` and undefined document/config fields. Publishing changed designer status to `Published` but did not clear `Public 404` while the theme remained inactive or routing incomplete. | Conditional yes after fresh capture. | Designer status, active theme, route/home binding, and frontend route render. |
| routes | read list | Route page exposes path, bound page, binding status, note, updated time, plus `创建` and child-route controls. | Yes for read-only scanning. | Route rows and binding status match frontend paths. |
| routes | create/bind route | Prior verified UI opens a create-route dialog; final submit creates route. Binding and child-route actions need separate capture. | Conditional yes after fresh request capture. | Route row appears and public frontend path resolves. |
| routes | create static route from page route option | `POST /{siteKey}/routes` Server Action with `siteId`, `path`, `query`, `routeMode`, `parentPath`, and `note`. When `path` matched an existing page route option, the new row auto-bound to that page. Root `/` was rejected with `validation.routePath.rootInvalid` in the component response despite HTTP 200; use theme-page `set homepage` for root mapping. | Conditional yes after fresh capture; parse component response for validation errors. | Backend row shows intended path, page name, and `已绑定`; public frontend route renders expected DOM. |
| forms | read list | Form page exposes columns name, slug, description, fields, status, updated time, and `创建`. Empty state also shows `创建表单`. | Yes for read-only scanning. | Form columns and status. |
| forms | create form | Empty-state `创建表单` immediately created an `Untitled Form` draft and navigated to `/{siteKey}/forms/{formId}/update`; update page exposed form settings, preview, and field editor entry. | Conditional yes after fresh capture; create is separate from save/publish/field editing. | Draft edit URL, status 草稿, default fields, and cleanup candidate. |
| forms | save/publish/edit fields | Not captured beyond create-only draft. | Unknown until action-specific capture. | Field list, persisted form schema, published form rendering, and submission behavior if in scope. |
| posts | read list | Post page exposes columns title, slug, excerpt, order, status, categories, tags, created time. Empty state shows `创建文章`. | Yes for read-only scanning. | List columns and counts. |
| posts | create draft | Prior verified behavior: clicking create can immediately create an Untitled draft. | Conditional only with explicit probe authorization. | New draft renamed/probed, save request captured, cleanup done. |
| products | read list | Product page exposes media, name, slug, description, order, status, categories, tags, created time, plus tabs for categories/tags/specs. | Yes for read-only scanning. | List columns and counts. |
| products | create draft | Prior verified behavior: clicking create can immediately create an Untitled draft. | Conditional only with explicit probe authorization. | Draft appears, product schema captured, cleanup done. |
| media | read list | Media page exposes search, sort, upload controls, empty state, pagination. | Yes for read-only scanning. | Media count and visible assets. |
| media | upload | Canonical direct adapter requires the exact logged-in `/{siteKey}/media` page, a user-approved local file list, and a private absolute image index. The controller accepts any file count but sends one request at a time; errors trigger delay and read-only reconciliation before a bounded current-image retry. | Direct-adapter-first. Do not recapture or hand-roll a loop. UI file selection is approved fallback only after contract drift/runtime failure; simulated dialog proof is not upload proof. | Exact media record exists, returned public URL loads and decodes, source hash maps to the URL/media ID, metadata is verified when authorized, and maximum upload concurrency is one. |
| site-info | read form | Site info page exposes site name, description, favicon/image picker, notification email, and save. | Yes for read-only scanning. | Current values and save button state. |
| site-info | save | Same-value save returned `站点信息已更新`; fields remained present. Image picker was not touched. | Conditional after capture; low-risk for same-value save, still gated. | Reopen page and frontend metadata/icon as applicable; image upload remains separate. |
| domains | read setup | Domains page exposes CNAME target, domain input, add-domain action, and empty state. | Yes for read-only scanning. | CNAME target and domain rows/status. |
| domains | add domain | External DNS-dependent mutation; not captured. | Usually prefer UI/manual unless domain ownership and DNS are ready. | User-owned domain, CNAME/DNS status, SSL, frontend route. |
| tracking | read setup | Tracking page exposes Google Tag ID input and add action. | Yes for read-only scanning. | Current tag list. |
| tracking | add tag | Not captured. Do not add fake tag IDs. | Conditional after capture and user supplies intended tag ID. | Published frontend includes expected tag config. |

## 2026-06-29 Module Scan Findings

On a temporary site, browser verification showed this important split:

```text
backend dashboard: active theme and published page counts can be true
theme detail: pages can show published while their enabled switches are still false
routes page: routes can still show unbound after theme activation
frontend: root or page URLs can return HTTP 404 or an empty runtime shell
```

Therefore, a launch-ready workflow must not stop at `Published` or active theme status. Verify in this order:

```text
theme active
page row published
page enabled switch true
route bound to the intended page
frontend HTTP status is not 404
frontend DOM contains expected headings/body/media
```

If any step fails, treat the previous JSON action as only partially successful.

When all six launch checks pass, write them into run evidence as `launchReadiness` with `themeActive`, `pagesPublished`, `pagesEnabled`, `routesBound`, `frontendHttpOk`, and `frontendDomVerified` all true. Use `scripts/make_launch_readiness_evidence.py` so route patterns stay redacted and partial states require blockers. Keep `frontendRendering` for route-level HTTP/DOM audit details. Do not use `launchReadiness` as a substitute for product/post request capture or sample upload proof.

## Module Scan Checklist

For each backend module, inspect these without mutating first:

```text
visible columns and controls
network requests on page load
whether create/upload buttons open a dialog or create immediately
whether save/publish/enable/delete are separate actions
whether frontend verification route exists
```

Suggested scan order:

```text
themes
themes/{themeId} pages
themes/{themeId}/{pageId}/design
routes
forms
posts
products
media
site-info
domains
tracking
```

## JSON Suitability Guidance

> The authoritative "may I use JSON at all" gate is `official-docs-alignment.md` §JSON Acceleration Gate (docs-step membership + captured/known-IDs/verifiable/rollback). The "use JSON when" list below is the same generic suitability read; the value this section adds is the **Prefer-UI triggers** and the scan-summary stop conditions that the other two gate copies do not carry. Treat official-docs-alignment as canonical for the core criteria.

Use JSON/Server Action replay when (generic read; see official-docs-alignment gate for the authoritative version):

```text
the payload is structured and deterministic
IDs are known from current backend state
there is a safe sample item or temporary site
the operation can be verified after replay
failed replay can be stopped before batch damage
```

Prefer UI when:

```text
the action requires local file upload
the action depends on complex drag/drop state not represented in the captured payload
the only available auth context is the live browser and replay cannot be done safely
the operation is destructive or hard to undo
the request uses volatile hidden state that changes on every render
```

Stop before JSON replay when the scan summary lacks any of these:

```text
action name separated from neighboring actions
redacted payloadShape or payloadKeys
current backend id fields
required volatile header names, redacted
backend persistence proof after the action
frontend render proof for public actions
cleanup or rollback plan for probe content
```
