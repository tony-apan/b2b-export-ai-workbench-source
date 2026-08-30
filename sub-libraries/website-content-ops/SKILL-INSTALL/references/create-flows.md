---
doc_id: allincms-bulk-create-flows
title: AllinCMS 创建流程核验
description: LAICMS / AllinCMS 各模块创建入口的副作用、字段预览和授权边界
layer: ops
status: draft
created: 2026-06-29
updated: 2026-07-30
page_type: reference
sources: []
confidence: medium
---

# Create Flows

Use this reference before clicking any `创建`, `创建主题`, `上传`, or similar action in the backend.

## Rule

Treat create/upload actions as potentially state-changing even if the UI looks like it might only open a form. Verify by reading the list page first, then require either exact user authorization or a current-session test-site policy paired with an exact local action record before clicking any button known or suspected to create a record.

When resuming a browser run, current browser state wins over old handoff URLs. If Chrome redirects a stored `/{siteKey}/themes/{themeId}/{pageId}/design` link to `/sign-in` but another `workspace.laicms.com/{currentSiteKey}/dashboard` tab appears authenticated, treat the stored design link as stale or wrong-context until a fresh `/sites` or target-module load proves auth. Cached dashboards can still show counts and side navigation while `/products`, `/posts`, `/themes`, or `/routes` redirect to `/sign-in`. Do not click create/save/publish from a stale deep link or cached dashboard; require a fresh authenticated module URL first.

Follow official-docs create order before adding records:

```text
default content exists -> edit/replace it first
default content missing or insufficient -> create only what is missing
frontend 404/blank -> fix theme/homepage/routes before product/post/page expansion
extra static page -> create route, create page, bind route, enable page, then design and verify frontend
homepage modules -> add/edit after categories, products, and posts exist
```

Do not create duplicate default pages, duplicate themes, or large batches of products/posts just because a create button is visible. The first launch goal is a small complete site: 2-3 product categories, at least 2 products per main category, 3 basic posts, clickable homepage modules, verified navigation, real or deferred contact/form fields, and desktop/mobile launch checks when public quality is claimed.

For broad build runs, load `official-docs-alignment.md` before clicking create controls. It decides whether the next action should be edit-existing, create-missing, or defer. This file only records the observed side effects and field surfaces of create/update controls.

## Browser-Verified Findings

Observed on 2026-06-29 on one logged-in site. These observations are platform-behavior evidence for orientation only; re-check every site/version.

### Posts

> **Primary path is JSON, not UI editing (SKILL.md JSON-first split rule).** For posts and products, the operational path is: probe once to confirm the type and capture one real save (`next-action`), then create/update/publish every entry via JSON replay of the captured Server Action (`server-action-save-api.md`). The `content` body MUST be a Slate node array submitted via JSON — a UI form save does not bind the Slate editor and wipes the body. The UI-editing and Slate-clearing techniques documented below (`fill()` residue, `Ctrl+A`+Backspace, clipboard paste) are the **fallback for inspection/probing or when JSON replay is unavailable**, not the way to author a batch. Keep the payload-key evidence below (it is the JSON contract).

List page:

```text
https://workspace.laicms.com/{siteKey}/posts
```

Visible create control:

```text
创建
```

Click behavior observed:

```text
Clicking 创建 immediately navigated to /{siteKey}/posts/{postId}/update.
The update page heading was 更新文章.
The backend list then showed an Untitled Post <timestamp> draft.
```

Observed update-page fields after the click:

```text
正文 editor
标题, input name title, placeholder 文章标题
Slug, placeholder post-slug
分类
标签, placeholder 选择标签
摘要, placeholder 简短摘要...
排序
封面图
历史
更新
发布
```

Conclusion:

```text
Do not click posts 创建 for inspection unless draft creation is authorized.
Use an existing draft/test item for field mapping when possible.
```

On a verified empty posts list, clicking the empty-state `创建文章` button created a draft immediately and navigated to `/{siteKey}/posts/{postId}/update`. The update page showed `更新文章`, `草稿`, default title `Untitled Post`, disabled `更新`, and visible `发布`. Treat this as a create-only mutation. Saving, renaming, publishing, and cleanup require later action-specific gates.

On a non-empty posts list, the top `创建` button can also create a draft and switch the React view to `更新文章` even when a direct URL read still returns the list URL for a short period. Do not conclude the click failed from the URL alone. Verify by reading the current DOM for `更新文章`, draft status, `Untitled Post`, title/slug/excerpt fields, and the rich-text editor. If those are present, continue on the edit view instead of clicking create again and risking a duplicate draft.

For a verified post save/publish run, the editor surface was `div[contenteditable="true"][role="textbox"]`. Saving posted to:

```text
/{siteKey}/posts/{postId}/update
```

with payload keys:

```text
title, slug, excerpt, order, coverImage, categories, tags, content, siteId, postId, mode
```

Post payload shape differs from products. Posts used `title`, `excerpt`, and `coverImage`; products in the same platform version used `name`, `description`, `media`, `mediaList`, and `specifications`. Publishing the saved post reused the same URL and payload with `mode: "publish"`. The backend list then showed the post as published. Do not treat that as frontend proof until the active theme has a `/posts` list page and `/posts/{post}` detail page with actual article blocks.

When replacing an existing published post, do not guess the backend edit URL from the public slug. Use the backend list row menu or another verified backend link to reach `/{siteKey}/posts/{contentId}/update`. Saving a published post can move it back to `草稿`, so treat `更新` and `发布` as two separate operations and verify the backend list returns to `已发布` before frontend checks.

Slate post body replacement has the same residue risk as products. Use the exact `div[contenteditable="true"][role="textbox"]`, clear or paste through a proven method, then read the editor `innerText` before saving. Block the save if old template phrases, probe/test text, placeholder text, or unintended Markdown/source residue remains.

After a post slug or body update is published, the public `/posts` list can show the new link before `/posts/{slug}` reliably renders. Use a bounded retry for the detail route. Verification passes only after the detail DOM shows the expected article title, excerpt/body, and media state; list visibility alone is not enough.

### Products

> Same as Posts above: **JSON replay is the primary authoring path; the UI-Slate editing/clearing below is fallback.** Product `content` is a Slate node array via JSON; a UI form save wipes it. See the JSON-first callout under `### Posts` and `server-action-save-api.md`.

List page:

```text
https://workspace.laicms.com/{siteKey}/products
```

Visible create control:

```text
创建
```

Click behavior observed:

```text
Clicking 创建 immediately created an Untitled Product <timestamp> draft on the list.
The action did not behave like a harmless modal preview.
In a later verified run, clicking the empty-state 创建产品 button sent a Next.js Server Action POST to /{siteKey}/products with payload shape [{siteId}], then navigated to /{siteKey}/products/{productId}/update.
The update page showed 草稿 status, default name Untitled Product, numeric timestamp-like slug, 更新 disabled, and 发布 visible.
```

Conclusion:

```text
Do not click products 创建 for inspection unless draft creation is authorized.
Prefer an existing draft/test product for field mapping.
If the authorization stops after create/draft verification, do not rename, save, or publish the product. Record the cleanup candidate and require a separate save/capture authorization before setting the probe title.
```

For legitimate demo-site product content, do not force the `Codex Probe - Delete Me` naming rule. Probe gates may still be probe-only; if the helper rejects a demo content target because the identifier lacks the probe prefix, record that as gate coverage drift, keep the UI action scoped to the exact product row or edit URL, and verify the created/saved/published product in both backend and frontend before doing any batch work. Probe content still must use the cleanup prefix.

When typing product body content, verify the editor text actually changes. In one verified run, clicking the visible body placeholder and typing left the contenteditable text as `编写产品详情...` while appending the intended body text to the description textarea. Do not assume focus moved to the rich editor; inspect contenteditable text and save payload `content` before claiming non-empty body schema.

When replacing existing default-template product body text, `locator.fill()` or keyboard `Control/Command+A` may append new rich text instead of fully clearing old Slate paragraphs. Do not click `更新` if the editor still contains default-template phrases after replacement. Close or abandon the unsaved edit page, reopen from the list, and use a captured request/schema path or a proven editor-clear method before saving. Title, slug, and description changes can appear clean while the body remains polluted, so inspect the editor text separately.

Do not guess product update URLs from the public slug. A backend path such as `/{siteKey}/products/{slug}/update` can return the platform 404 even when the public `/products/{slug}` detail route exists. Open the row-scoped action menu from the backend list and use the real `/{siteKey}/products/{contentId}/update` link before editing.

Slate product editor clearing can vary by row and current editor state. In one browser run, `locator.fill()` cleanly replaced one product body but appended on another; `ControlOrMeta+A` plus Backspace also inserted text before old content. A safer UI fallback was: click the visible `contenteditable` node through DOM/CUA, send system `ControlOrMeta+A`, Backspace, write the intended body to the browser clipboard, paste with `ControlOrMeta+V`, then read `innerText` and block save if default phrases, probe/test text, or placeholder text such as `编写产品详情...` remain. CUA direct typing after clearing may leave placeholder residue; prefer clipboard paste for final body input.

For a verified non-empty product body save, the rich editor surface was `div[contenteditable="true"][role="textbox"]`. Filling that exact editor produced a save POST to:

```text
/{siteKey}/products/{contentId}/update
```

with payload keys:

```text
name, slug, description, order, media, mediaList, content, categories, tags, specifications, siteId, productId, mode
```

The `content` value was an array of Slate paragraph nodes. Plain paragraphs used `type: "p"` plus `children: [{text}]`; bullet-like rows were still paragraph nodes with `indent: 1` and `listStyleType: "disc"`. After saving, the backend product status changed from published to draft and the publish button became visible. A separate publish POST with `mode: "publish"` was required before the public product detail rendered the new body.

After publishing a product with a changed slug, the public list page can show the new slug and card before the detail route stops returning 404. Use a bounded retry: verify `/products` lists the new link, wait briefly, then retry `/products/{slug}` before calling the detail route broken. Still require the detail DOM to render the new H1/body before marking the product verified.

Do not treat a product body save as launch-complete if `media` remains `null`, `mediaList` is empty, or `specifications` is empty. In the verified run, the frontend detail rendered the Slate body and list markup, but still showed an image-off placeholder because no real media was uploaded or selected.

After clicking product `创建`, the route may remain on the list briefly while the create button is disabled, then navigate to `/{siteKey}/products/{productId}/update`. Do not assume no draft was created just because the immediate read still shows the list. Wait for URL or backend list state before retrying the create click.

Product row action menus are repeated for every row. Scope menu clicks to the row text, for example the exact product/probe title, before choosing `更新`, `复制`, or `删除`. For destructive cleanup, require the confirmation dialog to name the target title, then reload the backend list and verify the frontend detail route is 404 or non-public.

After choosing a row menu `更新` action, the React view and URL can lag behind the click. In one verified run, an immediate read still looked like the products list, while a later reload landed on the intended `/{siteKey}/products/{contentId}/update` edit page with the row's product fields. Do not retry the same row menu immediately and risk duplicate or wrong-row actions. Wait for either the edit URL or the `更新产品` heading plus product-specific fields; if the evidence is split, refresh once and re-check before deciding the click failed.

For browser-side request capture, do not assume the CDP tab capability exposes an event-emitter API such as `.on`. If the current browser runtime does not support request listeners, do not fall back to UI-only editing: inject a `window.fetch` interceptor into the content edit page and capture the save that way. A late-injected `window.fetch` patch DOES catch content-page saves (products/posts/categories) even after bundle init — this is the proven content-capture path (see `server-action-save-api.md` §1/§5 and `request-capture.md`); it only fails for theme design-save, which needs CDP. Use previously-captured schema plus UI/backend/frontend verification only as a last resort when neither CDP listeners nor a `window.fetch` interceptor can be installed, and record that capture limitation explicitly.

### Product Categories

List page:

```text
https://workspace.laicms.com/{siteKey}/products?tab=categories
```

When the category tree is empty, the page can show a visible `创建分类` empty-state button. After the first root category exists, the empty-state button disappears and category creation moves to icon-only `+` controls in the category tree toolbar and row controls. Treat the toolbar `+` as "create root category" and row-level `+` as "create child category"; use screenshots or element geometry to avoid confusing them.

When a category already exists, selecting its text can open an edit panel with fields such as `name`, `slug`, `description`, and cover media. Some category tree edits may persist without a visible text Save button. Treat the immediate tree label change as provisional until a backend page refresh preserves the new taxonomy and public list/detail chips render the new label. Do not click unlabeled icon buttons around a category row unless their meaning is proven; they may be add, reorder, delete, or other row controls.

The create-category dialog observed in one run exposed only:

```text
名称, input name name, placeholder 例如：技术新闻
Slug, placeholder 例如：tech-news
创建
Close
```

Description and cover fields were not exposed in the create dialog; check the selected category edit panel after creation before claiming description or cover support.

Creating multiple product categories back-to-back can return a visible error such as:

```text
Given transaction number N does not match any in-progress transactions. The active transaction number is M
```

In that state, do not keep resubmitting the same open dialog. Reload the category page, verify which categories actually exist, and either retry one category with a fresh dialog or stop with the current category count if the official-docs lower bound is already met. Record the blocked category and error as run evidence.

### Routes

List page:

```text
https://workspace.laicms.com/{siteKey}/routes
```

Clicking `创建` opened a dialog:

```text
title: 创建路由
field: 路径, placeholder /pricing
route suggestions: /contact-us, /about-us, /posts, /products, /home
field: 备注, placeholder 该路径的可选内部备注。
buttons: 取消, 创建, Close
```

Final `创建` submit creates a route and requires explicit authorization.

When the path input has suggestions, select the intended suggestion before clicking the dialog `创建` button. In one verified run, leaving `/contact-us` selected while `/solutions` was typed did not submit. Selecting `/solutions` first then clicking the dialog-scoped `创建` submitted the Server Action and created a bound `/solutions` row.

Root `/` is not a normal route in the verified version. The UI did not submit, and a direct Server Action returned `validation.routePath.rootInvalid` with HTTP 200. The expected root-home mechanism is the theme page list's `设为首页` action, which posts the page id, siteId, and themeId to `/{siteKey}/themes/{themeId}`. Verify the public root after the action; a success toast such as `首页已更新` and a disabled `设为首页` button can still leave `/` rendering 404 when the active theme's route mapping or page document is incomplete. Do not claim root homepage readiness until `/` renders a non-empty public DOM.

### Themes

> **Scope warning — "theme" is two different things; don't let the payloads below imply the whole theme domain is one JSON path.** (a) **Theme-page structural ops** (create theme, create page, enable/activate, bind route) are separate Server Actions, each captured per-action — the payloads in this section are those. (b) **Theme page design-save** (the block copy/props/images you edit in the designer) is a *different* Server Action (`POST .../design`, whole-page `pageDocument`); it is JSON-replayable but must be captured via **CDP Network**, not a late `window.fetch` patch, and until captured you use the designer half-auto method. See the SKILL.md JSON-first split rule and `server-action-save-api.md` §7. Capturing a `创建页面` request never proves how design-save/publish/activate/route-bind behave — capture each separately.

List page:

```text
https://workspace.laicms.com/{siteKey}/themes
```

Clicking `创建主题` opened a dialog:

```text
title: 创建主题
field: 名称, input name name, placeholder 商务风格
field: 预设, options 空白 and 默认
field: 描述, placeholder 主题方向摘要...
buttons: 取消, 创建主题, Close
```

Final `创建主题` submit creates a theme and requires explicit authorization.

Official-docs rule: when a new site has no usable theme/pages or the frontend is 404/blank, create a theme with preset `默认`, not `空白`, unless the user explicitly wants a blank theme or the operator has a validated design/pageDocument path. If a theme already exists and has pages, do not create another theme; open its `页面` or `设计` controls and edit existing pages.

On a newly created site that has no themes, creating a blank theme produced a draft theme with `0 页` plus `页面`, `设计`, and `预览` controls. The default frontend origin may still render little or no visible content until pages are added and routes are bound. Treat blank theme creation as an advanced or experimental path, not the tutorial path and not a finished homepage.

On a verified recovery run, creating a `默认` preset theme produced a draft theme with 7 generated pages: Home `/home`, Products `/products`, Product detail `/products/{product}`, Posts `/posts`, Post detail `/posts/{post}`, About Us `/about-us`, and Contact Us `/contact-us`. After enabling that default theme, the route table showed all corresponding routes bound and public `/`, `/home`, `/products`, `/posts`, `/about-us`, and `/contact-us` rendered non-empty DOM. The generated copy and brand assets were still generic template content; this fixes the 404/blank-home gate but does not complete business-specific site content.

Use `prepare_default_theme_bootstrap.py` for this recovery path instead of improvising from the theme list. The runbook keeps `create_theme` and `activate_theme` separate, requires preset `默认`, and emits a redacted evidence template. After execution, `validate_default_theme_bootstrap_evidence.py` must pass, then `apply_default_theme_bootstrap.py` must write refreshed created-site evidence before the default theme is used as the foundation for source pages, taxonomy, schema capture, sample upload, or batch upload. A passing bootstrap validation is still not launch acceptance; it only proves starter pages/routes/frontend DOM exist.

When switching themes, a `主题已应用` toast may appear without a route-mapping dialog. Refresh the theme list before judging final state: the old theme can remain visible as `草稿` with a route-mapping warning, while the new theme becomes `启用`. Then verify routes and public pages separately.

JSON acceleration is reasonable for repeated theme/page setup after capture, but each operation must be captured separately. A captured `创建页面` request can speed up adding pages to the same theme, yet it does not prove how to save design blocks, publish the page, activate the theme, or bind frontend routes.

For theme/page setup, verify the chain in this order:

```text
theme exists and current themeId is known
page rows exist under the theme
designer contains blocks, not only an empty canvas
Save enables and persists design changes
Publish enables and changes public state
route or frontend URL renders the page, not Public 404
theme is enabled/active if the platform requires activation
```

If the designer shows `No blocks yet` or `Public 404`, do not treat a page row status such as `已发布` as proof that the public page is usable.

For default-template sites, prefer editing these existing pages/modules before new creation:

```text
Home / homepage
Products
Posts / News / Blog
About Us
Contact Us
Header / navigation
Footer
Banner or Carousel
Category Showcase
Featured Product List
Featured News List
```

Create extra static pages only for missing business needs such as `OEM`, `Cases`, `Services`, or `Solutions`.

Official page-create order:

```text
1. Inspect default pages first; edit existing Home, Products, Posts, About Us, and Contact Us pages instead of duplicating them.
2. Create a route such as /oem only when the page is genuinely new.
3. Create a matching theme page such as OEM.
4. Bind the page to the route.
5. Enable the page.
6. Open the frontend route and verify: non-404, non-empty DOM or accepted placeholder, intended content.
7. Add menu/button links only after the route works.
```

Official docs may show a route input example as `oem` while the public URL is `/oem`; record whichever form the current UI accepts, but verify the normalized public path with a leading slash.

If a newly created route shows `未绑定`, that can be normal before the page exists; it becomes a blocker only if the page is supposed to be public and still unbound after page bind/enable.

Product/post detail routes may require a dynamic child theme page, not just a route row. In one 2026-06-30 read-only check, `/products/{product}` existed in the routes table as type `Product` but showed binding page `—` and `未绑定`; the route row update dialog only exposed path param and note fields, with no bound-page selector. The active theme page list had only static pages. Opening the Products page's `创建子页面` dialog showed a param route editor with allowed values `{*}`, `{product}`, `{post}`, `{category}`, and `{tag}`. Treat creation of that dynamic child page as a separate `create_theme_page` mutation before design, publish, enable, route bind, or frontend detail verification. Do not try to fix a product detail 404 by editing the route row note/path alone.

In the verified Products child-page dialog, the route editor was not a full-path text box. It used a route-mode control set to `param` plus a segment input. For a product detail page, set the segment input to `{product}`; the submitted Server Action payload then includes:

```json
{
  "path": "/products/{product}",
  "routeMode": "param",
  "parentPath": "/products",
  "siteId": "<redacted>",
  "themeId": "<redacted>",
  "name": "Product Detail",
  "description": "...",
  "_status": "draft"
}
```

The row may appear as `已发布` immediately and its design URL provides the new page id, but route binding can still remain unchanged. After creating the dynamic child page, re-open `/{siteKey}/routes`; if `/products/{product}` still shows binding page `—` and `未绑定`, keep frontend detail routes blocked. First check whether the Product Detail page is enabled in the theme page list. In one verified 2026-06-30 run, clicking the visible `role=switch` control labeled `启用 Product Detail` changed the page switch to enabled and automatically changed the routes table from `— / 未绑定` to `Product Detail / 已绑定`. Hidden checkbox inputs did not toggle the page; target the visible switch, then re-read both the page row and routes table before considering any separate `bind_route` stage.

For frontend detail verification, use the actual slug shown in the backend content list after save. Do not reuse an older probe URL or guessed slug. In the verified run, `/products/{old-probe-slug}` still returned 404 after route binding, while `/products/{actual-list-slug}` returned 200. A successful HTTP 200 can still show design/content warnings such as missing H1 or missing images, so detail launch proof still needs DOM/rich-text/media checks before batch upload.

AI-assisted designer generation is a convenience path, not a reliable batch path. In one 2026-06-29 run, submitting the designer prompt called `/api/copilotkit` and returned a visible `insert-block Done` message, but the canvas still showed `No blocks yet`, `Save` stayed disabled, and the public status stayed `Public 404`. The same run also showed a `检测到新版本` refresh prompt. If this happens, record it as a designer-state failure, refresh or reopen the designer, and verify manual block insertion before trying to capture save/publish JSON.

In another 2026-06-29 run, filling the designer prompt and clicking a quick action did not modify the canvas, while manually editing typed Inspector props on an existing block did enable Save and produced a valid design payload. Prefer Inspector fields or block insertion when Copilot does not produce a changed canvas plus enabled Save.

Designer Copilot or `Improve the current page` can be useful as a draft accelerator, but it may update only a subset of blocks and leave other visible default-template sections unchanged. Treat `inspect-block Done`, `update-block Done`, or an enabled `Publish` button as progress signals only. After generation, inspect the canvas or public DOM for residual default copy, then use Layers plus block-level Props for the remaining sections.

When editing generated page Props, repeated field names such as `description`, `sectionLabel`, or `headline` can exist in hidden or previously selected block panels. Do not fill a global selector such as `[name="description"]` unless its count is exactly one. Prefer selecting one block in Layers, reading the current input list, and filling block-specific nested names such as `slides.1.title`, `stats.0.value`, or `members.2.bio`. If a generic name remains ambiguous, stop and scope tighter instead of filling globally.

For hiding existing designer modules, switch to the `Layers` tab first. The `Blocks` tab lists insertable blocks and may not expose per-instance hide controls. In Layers, a visible module normally exposes a `Hide <module>` button; after clicking it the button changes to `Show <module>`, `Save` and `Publish` become enabled, and the page can move through the usual save/publish state machine. If a unique Playwright locator such as `button[aria-label="Hide ..."]` still times out in the designer, take a fresh visible DOM snapshot and click the exact `node_id` for that hide control once, then verify the `Show ...` state before saving. Save can change a published page to `Draft`; publish is still a separate action and must be verified by `Published` status plus public DOM proof. Browser telemetry warnings such as Statsig or `ab.chatgpt.com` timeouts are not LAICMS save/publish proof either way; use designer status, button state, backend refresh, and frontend DOM checks.

When opening a page designer from a theme page list, do not infer the page id from row order or a prior handoff. The list can be sorted differently from earlier notes, and broad text locators such as `Contact Us` may match navigation, footer links, multiple rows, or disabled controls. Verify the destination by checking the designer `Page context`, displayed page id, and route chip such as `/contact-us` before mutating. If the wrong page opens, stop and regenerate the action record for the actual target page id instead of reusing the stale record.

If a public Contact page renders an unresolved form reference such as `Form "..." could not be resolved`, treat it as a launch blocker. Until the real form create/save/embed behavior and notification settings are captured, hide the unresolved form block or remove the reference, publish, and verify the public page no longer exposes the error. Record the form binding as a source-input/schema gap instead of presenting the page as having a working form.

For unconfirmed public contact channels, hiding can be safer than replacing with invented values. If a contact/social block contains placeholder social URLs, email, phone, address, or office copy and the user has not provided authoritative values, hide that block or switch link targets to `None`, then publish and verify the public route no longer contains external placeholder links or fake contact details. Keep the missing fields in the source-input gap ledger for later PDF/catalog/brief intake.

Manual block insertion must be proven by all of these signals:

```text
the block appears in the canvas or Layers panel
Save becomes enabled
the design save request is captured
after save/reopen, the block persists
after publish, the public frontend route renders the block
```

A drag/drop accessibility message such as `library-block-... was dropped over droppable target canvas-drop` is not enough if the canvas still says `No blocks yet`. In one Product Detail design run, clicking `Product Detail (Gallery)`, dragging it to `canvas-drop`, and prompting `Improve the current page` all left `No blocks yet` visible and `Save` disabled. Treat that as a failed insertion path; do not click Save, do not publish, and do not claim the product detail design exists. Find the real Add Block control or use a captured/validated `pageDocument` save path before retrying.

In a later verified Product Detail designer run, the reliable insertion path was:

```text
open Blocks
open Products block group
focus or select Product Detail (Gallery)
wait for the side preview/action surface
click the explicit Add Block button
verify No blocks yet disappears
verify Save becomes enabled
click Save only under a save_design authorization/gate
verify Save becomes disabled after save
verify page status changes to Draft
leave Publish for a separate publish_design authorization/gate
```

Do not infer insertion from the block library item alone. The `Add Block` button is the action that inserted the block in the verified flow; click, drag, and prompt-only attempts were insufficient.

Canvas selection caveat: a block can be visually active in the iframe while the Inspector still says `No block selected` or `Loading props...`. Do not start editing or capturing until the right Inspector heading and actual typed fields are visible.

Posts routes require the same theme-page chain as product detail routes. Creating a published post and seeing `/posts` plus `/posts/{post}` rows in routes is not enough when the routes table shows `— / 未绑定`. Create a static Posts theme page for `/posts` and a dynamic Post Detail child page under Posts with segment `{post}`. The captured static Posts page create payload used:

```json
{
  "path": "/posts",
  "query": "",
  "routeMode": "$undefined",
  "parentPath": "$undefined",
  "siteId": "<redacted>",
  "themeId": "<redacted>",
  "name": "Posts",
  "description": "...",
  "_status": "draft"
}
```

The captured dynamic Post Detail child payload used:

```json
{
  "path": "/posts/{post}",
  "query": "",
  "routeMode": "param",
  "parentPath": "/posts",
  "siteId": "<redacted>",
  "themeId": "<redacted>",
  "name": "Post Detail",
  "description": "...",
  "_status": "draft"
}
```

Both rows can show `已发布` immediately after creation while routes remain unbound. Enable the visible switches labeled `启用 Posts` and `启用 Post Detail`; each enable action posts to `/{siteKey}/themes/{themeId}` with:

```json
{
  "id": "<pageId>",
  "siteId": "<redacted>",
  "themeId": "<redacted>",
  "enabled": true
}
```

After enable, re-open routes and verify `/posts` and `/posts/{post}` are bound before checking frontend detail URLs.

A 200 frontend status for posts can still be a blank rendered page. In one verified run, `/posts` and `/posts/{postSlug}` returned 200 and the HTML title contained the post title, but the browser DOM body was empty because the newly created Posts and Post Detail theme pages had `No blocks yet`. The Articles library exposed `Full News List (Filtered)` and `Post Detail (Article)` blocks, but clicking or dragging `Full News List (Filtered)` produced only a status message such as `Draggable item ... was dropped over droppable target canvas-drop`; `No blocks yet` remained and Save stayed disabled. Treat that as failed insertion, not a saved design. Find a reliable explicit insertion path or capture a valid `pageDocument` before claiming posts launch readiness.

For Articles blocks, do not accept selection or dnd state as insertion proof. In a later Posts designer run, `Full News List (Filtered)` could become active, `aria-pressed`, and `aria-grabbed`; keyboard Enter grab/drop and mouse drop still left the page without a block, with Save disabled. If the designer then shows `Render canvas...` for an extended period, leave the designer, record the stuck state, and retry from a fresh tab or a validated `pageDocument` path. A successful article insertion still needs all of:

```text
No blocks yet disappears after the canvas finishes rendering
the target article block appears in the canvas or Layers
Save becomes enabled
save_design captures a real request and disables Save after persistence
publish_design is run separately before frontend verification
```

Do not Save or Publish when only `selected`, `grabbed`, `dropped`, or `Render canvas...` is proven.

Designer search and Copilot are not guaranteed insertion paths for Articles blocks. In one fresh Posts designer run, filtering `Search blocks` with `Full News List` or `News` returned an empty list even though the Articles category showed `Full News List (Filtered)` when browsed manually. Clicking the block card, hovering for an Add button, pressing Enter, and submitting a Copilot prompt to create an article list page all left `No blocks yet` visible and Save disabled. Treat these as failed insertion attempts. Do not save an empty Posts page just to produce a request; either find the same kind of explicit `Add Block` button proven for another block family, use a keyboard activation path that visibly inserts the block, or move to a validated `pageDocument` save contract.

If an Articles block drag finally succeeds, the proof must be stronger than the dnd status line. In one verified Posts run, dragging `Full News List (Filtered)` from the Articles library to the canvas made `No blocks yet` disappear, selected the block, exposed the Inspector heading `Full News List (Filtered)`, and eventually enabled Save after the block finished rendering. Save then changed the designer status from `Editing` to `Draft`, disabled Save, and left Publish enabled. Treat that as saved design proof only; a separate `publish_design` action is still required before `/posts` can be considered public-render verified. If the publish button cannot be clicked because the browser reports a `0x0` viewport or impossible top-toolbar click geometry, stop after saved-draft proof and use a fresh browser session or a freshly captured publish request contract instead of repeated blind clicks.

When recovering a saved Posts page stuck in Draft, first re-read the designer state. A valid pre-publish state is `Draft`, Save disabled, and Publish enabled. If an old controlled in-app tab reports a `0x0` viewport or toolbar hit tests land at y=0, open a fresh visible in-app tab to the same design URL and retry there; do not keep forcing the stale tab. After publish, verify all three surfaces: designer status `Published`, theme page list row `已发布`, and public `/posts` DOM non-empty with article links. A non-empty `/posts` list can still lack H1 or images and should not be called launch-ready by itself.

When selecting a `Full News List (Filtered)` block, do not assume the block can provide the page H1. In one verified inspection, its Inspector props exposed:

```text
Anchor ID
Post Action Label
Post Image Display
Detail Page
Page Size
Show Toolbar
Sort
Columns
```

There was no title, heading, H1, intro, or subtitle field. If `/posts` needs an H1, add a separate page heading/hero block through a proven insertion path, or record a scoped no-H1 acceptance for a temporary demo. Do not keep tweaking list-block props as if they prove page-heading support.

The designer can enter a bad geometry state where left-panel categories, toolbar controls, or Copilot input areas report negative or zero coordinates. If clicking a visible category such as `Heroes` resolves to y=0, reports no element, or shows a huge/offscreen textarea, stop escalating coordinate clicks. Use a fresh visible tab or viewport recovery first. Copilot prompt text that remains visible in the designer is not proof of insertion; save or publish only after the canvas/Layers changes and Save or Draft/Publish state changes.

For Posts routes, record both route vocabularies when needed:

```text
designer detail prop: /posts/{post}
public audit pattern: /posts/{slug}
```

Use the public `{slug}` pattern in launch-audit helpers that validate route patterns, while retaining the designer `{post}` value as UI field evidence.

For `Post Detail (Article)` on `/posts/{post}`, clicking the block card or dragging it to `canvas-drop` can emit a status message such as `Draggable item library-block-post-detail-article was dropped over droppable target canvas-drop` while the page still shows `No blocks yet` and Save remains disabled. Treat that as failed insertion. Do not save or publish the detail page, and do not synthesize a `pageDocument` from the block name alone. Continue only after the block appears in the canvas or Layers and Save becomes enabled, or after a current-site save request captures a valid `pageDocument` schema for that exact block.

Copilot can sometimes insert `Post Detail (Article)` when direct click/drag fails, but its narration is still not proof. In one verified recovery, a focused prompt to insert the exact Articles block changed the designer from `Published` empty canvas to `Draft`, made `No blocks yet` disappear, exposed Inspector heading `Post Detail (Article)`, and rendered the current post preview in the canvas. Save was already disabled because the designer staged the change directly; Publish was enabled and still required a separate `publish_design` gate. Treat this as a valid insertion only after the canvas, Inspector, Draft/Publish state, and later frontend detail DOM all agree.

Designer pages can expose more than one `Publish` button in the DOM, especially when Copilot or preview surfaces are present. If role-based `Publish` targeting is not unique, do not click a random match. Identify the top toolbar button by visible rectangle, click only that control after the `publish_design` gate passes, then re-read designer status and frontend DOM.

Product specifications can be edited even when the site has no reusable specification templates. In one verified product edit page, clicking product `规格 -> 编辑` opened a dialog with disabled template selection, the message `该站点尚未定义任何规格`, and an `添加字段` button. Adding fields created default `颜色 / 黑色` name-value inputs; replacing them with product-specific rows and clicking dialog `保存` only changed local page state and enabled the outer `更新` button. Clicking outer `更新` posted to:

```text
/{siteKey}/products/{productId}/update
```

with Next.js Server Action headers, changed the product from published to draft, and required a separate publish action to make the frontend detail update. After publish, the product detail route rendered a `Specifications` section with term/definition rows. Treat product specs as a separate save/publish proof from product body and product media.

### Forms

List page:

```text
https://workspace.laicms.com/{siteKey}/forms
```

Visible controls included:

```text
搜索表单...
状态
视图
创建
columns: 名称, Slug, 描述, 字段, 状态, 更新时间
```

For form field editing, the reliable UI flow was: open the form update page, open the field builder, drag a field into the Canvas (`data-builder-container`), configure the right-side Properties panel, click `完成`, then click the outer `更新`, then use a separate `发布` action. Saving form fields posted to:

```text
/{siteKey}/forms/{formId}/update
```

with payload keys:

```text
_status, schema, submit, siteId, formId
```

The `schema.fields[]` array held field objects such as `type: "text"`, `type: "email"`, and `type: "textarea"` with `name`, `label`, and `placeholder` values. Publishing reused the same update URL with `mode: "publish"`. Saving a published form can still require a separate publish step before the public embed updates. A public form embed can update after form publish without republishing the Contact page when the page references the form by slug or initial form data.

In a verified run, clicking the empty-state `创建表单` button did not open a harmless dialog. It immediately created an `Untitled Form` draft and navigated to `/{siteKey}/forms/{formId}/update`. The update page showed `更新表单`, `草稿`, a timestamp-like slug, disabled `更新`, visible `发布`, and fields for `名称`, `Slug`, `描述`, `提交按钮文案`, `成功提示`, `表单预览`, and `编辑字段`; it also showed `0 个字段` before field setup. Treat form create as a mutating action. Field editing, saving, publishing, embedding, public submission tests, and cleanup are separate stages.

The form field editor is a canvas builder, not a normal inline field list. To add a field, drag a field button such as `Text inputs` into the `Canvas`. A successful drop shows status text containing `dropped over droppable area root`, the preview count changes from `0 个字段` to `1 个字段`, and the Properties panel exposes inputs such as `name`, `label`, and `placeholder`. A failed drop may still report `Draggable item sidebar-text was dropped.` without `over droppable area root`; treat that as no field added and do not click `完成` as if the schema changed.

Field edits are only local page state until both boundaries are crossed:

```text
1. Click 完成 in the field editor.
2. Click 更新 on the form edit page.
3. Reload the edit page or list page to prove persistence.
```

If the page is refreshed before `完成` plus `更新`, newly added fields can disappear. Do not publish until a reload still shows the intended field count and preview.

In one verified save/publish run, form save and publish used the same update Server Action:

```text
POST /{siteKey}/forms/{formId}/update
Accept: text/x-component
Content-Type: text/plain;charset=UTF-8
next-action: <server-action-id>
payload: [{
  name,
  slug,
  description,
  _status: "draft" | "published",
  schema: { fields: [...] },
  submit: { label, successMessage }
}]
```

Publishing changed `_status` from `draft` to `published`, returned HTTP 200 `text/x-component`, changed the badge to `已发布`, and changed the action button to `取消发布`. Still verify the list row shows the form name, slug, field count, and `已发布`.

Published forms are not automatically embedded in public theme pages. A frontend contact page can render without any `<form>` and without the published field label or submit label. Treat form module publish as backend proof only; public form launch requires a separate theme/page designer binding or embed capture and frontend DOM/submission verification.

Public form submission testing is a separate lifecycle stage from backend form definition and embed proof. In one verified test-site run, the public contact page exposed fields `name`, `email`, a topic chooser, `message`, and a submit button. Submitting neutral test data left the URL unchanged, produced no console error and no visible alert/toast, and disabled the submit button; the backend `/forms` list still showed only the form definition row with no visible submission count or submission log. Treat that as a partial submit attempt, not hard success.

To mark public form submission launch-ready, require at least one strong proof source:

```text
captured request URL/method/payload and success response
visible post-submit success state that is not static page copy
backend submission record/count/log
email/webhook/destination proof agreed by the user
or an explicit demo-scope acceptance that frontend-only submit state is enough
```

Do not count generic page text such as `after submission` or a disabled submit button as persistence proof. Record test submissions as cleanup candidates if the platform exposes a submission inbox later.

If CDP Network capture is available, capture public submit request/response before relying on UI state. Redacted proof should include method, URL, resource type, header names, `hasPostData`, postData length, response status, and response mime type. Keep raw field values, cookies, server-action IDs, router state, and raw payload out of evidence. A captured `POST /contact-us` with `200 text/x-component` proves that the public form submitted to a Server Action; it still does not prove the message was stored, emailed, or delivered.

The backend dashboard recent-activity stream can expose a neutral event such as `Form submission received` linking back to `/forms` after a public form submit. Treat that as stronger backend-side activity proof than a disabled public submit button, but weaker than a submission inbox row, destination policy, email/webhook delivery proof, or cleanup handle. Record the dashboard activity in run evidence only as a redacted event type, route, and timestamp bucket; do not store submitted field values or account details.

To embed a published form into a theme page, open the page designer for the target page such as:

```text
/{siteKey}/themes/{themeId}/{pageId}/design
```

In the designer Blocks panel, the `Forms` category can expose blocks such as:

```text
Contact Info (Grid)
Location Map (Interactive)
Social Floating Button
Contact Dialog Form (Modal)
Contact Form (Split)
Newsletter (Inline)
```

For a public contact page, `Contact Form (Split)` is the verified page-level block that renders the selected system-managed form. After insertion, select the block and verify the Inspector `Props` panel shows a `Form` combobox. Choose the published form, then verify the hidden/control value uses the selected form slug such as `{formSlug}`; the canvas should render the form field labels and submit label before publishing.

If a `Contact Form (Split)` block was previously hidden, showing it can reveal a stale form reference from an older slug. The preview iframe may then render an error such as `Form "{oldFormSlug}" could not be resolved`. Do not save/publish that state as fixed. Select the `Contact Form (Split)` layer, open the Inspector `Form` combobox, choose the currently published form, and verify the combobox text changes from `Select a form` or the stale value to the intended form name before saving.

`Contact Form (Split)` can also own visible contact-detail fields in the same Inspector panel, not only the form selector. Verified field names include `emailLabel`, `emailValue`, `phoneLabel`, `phoneValue`, `addressLabel`, `addressValue`, `hoursLabel`, and `hoursValue`. If the user has not provided real public contact channels, do not invent an email, phone, office address, or business hours. Either hide the owning block or replace the values with non-contact routing copy that points visitors to the embedded form, then save, publish, and verify the old contact strings are absent from the public page.

The in-app browser can mis-map coordinates inside the designer's left block-list scroll area. If coordinate or locator clicks report no element at a visible point, filter `Search blocks` to the exact block name, then use keyboard focus (`Tab`) and `Space` to activate the single visible result. Treat successful insertion as proven only when all of these are true:

```text
canvas contains the new Contact Form block
Inspector heading shows Contact Form (Split)
Inspector Form control shows the intended form name/slug
the frontend iframe renders fields from the selected form
the page status becomes Draft or Publish becomes enabled
```

Copilot may help insert or update the block, but its narration is not proof. In one verified contact-page run, Copilot reported `insert-block`, `inspect-block`, and `update-block` as done, but the operator still verified the actual canvas, Inspector `Form` control, and frontend DOM before publishing.

Publishing a designer page after the form block was inserted used:

```text
POST /{siteKey}/themes/{themeId}/{pageId}/design
Accept: text/x-component
Content-Type: text/plain;charset=UTF-8
next-action: <server-action-id>
payload: [{
  siteId,
  themeId,
  pageId,
  intent: "publish",
  pageDocument: "$undefined",
  globals: "$undefined",
  themeConfig: "$undefined"
}]
```

This publish action published the already-staged page document and changed the top status from `Draft` to `Published`. Do not assume `pageDocument: "$undefined"` can create or modify a block by itself; it only proved publish for the current staged designer state.

Frontend form embed verification needs DOM proof, not just public HTTP 200:

```text
public page contains at least one <form>
expected input name/placeholder appears
expected submit button appears
business page content still renders
submission is either tested with an explicit test-record policy or explicitly omitted
```

Generic frontend render audits can prove HTTP status, headings, links, and Markdown residue, but they may not inspect form controls. Keep browser DOM proof for `formCount`, input names/placeholders, labels, submit button text, and unresolved-form text separately from a route-level audit artifact.

For contact cleanup QA, check both visible text and anchors. A footer may still display plain social labels after external `href`s are removed; decide whether plain labels are acceptable for the current scope. Production contact readiness requires no fake email/phone/address/hours, no placeholder external social links, and a recorded policy for any remaining unlinked labels.

If remaining footer social labels must be removed, inspect the selected `Footer (Columns)` block for fields such as `socialLinks.0.label` and `socialLinks.1.label`. A programmatic empty `fill("")` can revert to the old value and leave Save disabled. Use the visible input focus path instead: click the field, send system select-all, Backspace, then read the input value and page text before saving. Save should move the page to Draft, and Publish should return it to Published with Save/Publish disabled. Verify public routes for both absent social label text and absent external social anchors.

Do not submit a public form during verification unless creating a test inquiry record is in scope and its cleanup or destination policy is clear.

### Theme Designer Image Replacement

Existing page blocks such as `Category Showcase (Grid)` can expose repeated image controls in the Inspector. Each item may show:

```text
Media
Image
Video
Media Display
移除图片
替换图片
```

Treat `替换图片` as a design mutation once a replacement is confirmed. The picker can open a dialog with tabs:

```text
媒体库
上传
URL
```

An empty media library is not a blocker when the current task only needs a public image URL. The `URL` tab may expose one input with placeholder `https://example.com/image.jpg`. After a public image URL is entered, the dialog should show an image preview, the preview image must have non-zero natural dimensions, and `确认` should become enabled. Confirming updates the in-designer preview and enables `Save` / `Publish`.

For existing homepage category-image cleanup, use a one-image probe before replacing many repeated controls:

```text
1. Open one item image picker.
2. Choose URL.
3. Enter the candidate public image URL.
4. Verify preview loads and Confirm enables.
5. Confirm and verify only the intended item image changed.
6. Continue remaining images only if Save/Publish state is correct.
```

Saving the design should disable `Save` and move the page to `Draft`. Publishing should return the page to `Published` and disable `Publish`. Verify the public route after publish for image count, non-zero image dimensions, old template alt labels, broken images, and surrounding block text/links. Do not claim media-library upload proof from this path; this proves URL-bound designer media only.

### Media

List page:

```text
https://workspace.laicms.com/{siteKey}/media
```

Visible controls included:

```text
搜索媒体...
最新
上传
pagination/page-size controls
```

Do not click `上传` or interact with file inputs without explicit upload authorization.

On an empty media library, the page can show two visible `上传` buttons: one top-level action button and one empty-state call-to-action under `没有找到媒体` / `上传第一张图片开始使用`. Treat both as the same upload authorization boundary until the current version is captured. Do not infer two separate upload flows from the duplicate labels, and do not click either button during read-only status checks.

Media list pages may not expose table headers when empty or grid-based. Do not require a non-empty table header list as the only read-only preflight proof for media. Use visible controls (`搜索媒体`, sort, `上传`, page-size) and the exact backend URL as read-only page proof. For actual AllinCMS media upload, do **not** rediscover the multipart request or default to UI selection. Open and retain the exact logged-in `/{siteKey}/media` page, then use the canonical adapter documented at `<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/AI-START-HERE.md`.

The generic browser-stage authorization helper may still reject media preflight because `tableHeaders` is empty or may not emit a media command. That is a helper-coverage gap, not a reason to click the upload dialog or invent a new request loop. Keep the action authorization bound to the exact site and batch, then hand execution to `uploadAllinCmsMediaSerial()` with a private absolute image index. Input count is unbounded, but requests remain strictly serial. On an upload error, wait, perform read-only reconciliation, reuse the verified remote record when present, and retry only the current image when reconciliation precisely returns `not_found_stop` and attempts remain.

UI file selection is an explicitly approved fallback only after the canonical adapter reports contract drift or cannot run in the available browser runtime. The in-app browser may open the upload dialog and reveal `input type=file` but reject real file selection with `File uploads are not supported by Codex In-app Browser`. When that fallback is attempted and file selection is unavailable, record only dialog evidence and no remote mutation. Use Chrome fallback only with a valid logged-in workspace session, exact-site verification, explicit fallback approval, and a runtime that supports `filechooser.setFiles`; otherwise stop without claiming upload success.

In one read-only/authorized upload-dialog probe, the media upload dialog showed:

```text
上传媒体
拖入文件或点击选择
PNG、JPG、GIF、WebP，最大 5MB
取消
上传 [disabled before file selection]
input type=file multiple=true
```

Opening this dialog does not prove storage upload. If the current browser API cannot set files on the input, cancel the dialog, verify no file inputs remain and the media list is still empty/unchanged, then record the stage as `file_selection` blocked. The next proof must come from a browser/runtime that supports file chooser selection or from a separate public-URL media binding path.

Content edit pages can expose media binding without using the media library upload page. In one verified run, both product `主图/视频` and post `封面图` controls opened a picker with `媒体库`, `上传`, and `URL` tabs. The `URL` tab exposed one input with placeholder `https://example.com/image.jpg`; after a public image URL was entered, the dialog showed an image preview and enabled `确认`. Confirming inserted a preview into the edit page and enabled `更新`.

Treat this as a content save action, not as a media-library upload. Product save still posted to:

```text
/{siteKey}/products/{productId}/update
```

Post save still posted to:

```text
/{siteKey}/posts/{postId}/update
```

Saving URL-bound media changed the already published product/post back to draft in the verified run, so a separate `发布` click was required before the public detail/list pages rendered the image. Do not claim frontend media proof from the edit-page preview alone; verify backend status and public frontend `<img>` after publish.

Current helper coverage caveat: `upload_media` gates are media-library/file-upload oriented and require media content-type evidence such as `uploadFile` and `mediaId`. They do not fully model product/post edit-page URL media binding. Until a dedicated action such as `bind_content_media_url` or content-specific `save_product` / `save_post` exists, record the gate gap, keep the action scoped to the exact edit URL and field, capture the content save/publish requests, and verify frontend list/detail images.

### Site Info

List/setup page:

```text
https://workspace.laicms.com/{siteKey}/site-info
```

Verified read-only fields:

```text
name input, placeholder 站点名称
description textarea, placeholder 站点简介
notificationEmail input, type email
点击选择图片
保存
```

A same-value `save_site_settings` run returned `站点信息已更新` and kept the fields present. Do not click image picker or upload files as part of site-info save; media/file upload is a separate authorization.

### Tracking

List/setup page:

```text
https://workspace.laicms.com/{siteKey}/tracking
```

Verified read-only fields:

```text
googleTagId input, placeholder G-XXXXXXXXXX
添加 Google Tag ID
empty state: 暂无 Google Tag ID
```

Do not add a fake tag. `add_tracking_tag` requires a user-supplied real tag id and verification that the published frontend includes the expected tag configuration.

### Domains

List/setup page:

```text
https://workspace.laicms.com/{siteKey}/domains
```

Verified read-only fields:

```text
domain input, placeholder domains.domainPlaceholder
CNAME target based on {siteKey}.web.allincms.com
复制 CNAME 目标
添加域名
empty state: 暂无域名配置
```

Do not add a placeholder domain. `add_domain` requires a user-owned domain, DNS follow-up plan, backend status proof, and SSL/frontend verification.

## Cleanup

If an accidental draft was created during probing, search for:

```text
Untitled Post
Untitled Product
Untitled Form
Codex Probe
Delete Me
```

Cleanup is itself a remote mutation. Delete or unpublish only after explicit authorization.
