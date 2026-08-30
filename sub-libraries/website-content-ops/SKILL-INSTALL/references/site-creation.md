---
doc_id: allincms-bulk-site-creation
title: AllinCMS 建站起步核验
description: LAICMS / AllinCMS 从站点创建入口到首次站点配置的浏览器核验流程
layer: ops
status: draft
created: 2026-06-29
updated: 2026-07-01
page_type: reference
sources: []
confidence: medium
---

# Site Creation

Use this reference when the run begins before a site exists, or when simulating the full LAICMS / AllinCMS workflow from site creation through content upload.

## Official Tutorial Alignment

Official docs source pages checked on 2026-07-01:

```text
https://www.allincms.com/docs
https://www.allincms.com/docs/quickstart/overview
https://www.allincms.com/docs/quickstart/create-site
https://www.allincms.com/docs/quickstart/site-build-flow
https://www.allincms.com/docs/quickstart/site-settings
https://www.allincms.com/docs/pages/homepage-basics
https://www.allincms.com/docs/pages/create-page
https://www.allincms.com/docs/content/product-module
https://www.allincms.com/docs/content/homepage-featured-products
https://www.allincms.com/docs/content/product-categories
https://www.allincms.com/docs/content/add-products
https://www.allincms.com/docs/content/add-posts
https://www.allincms.com/docs/domains/bind-domain
https://www.allincms.com/docs/launch/launch-checklist
```

Treat these docs as the primary operating path for from-scratch builds. Browser probing is for verifying the current backend state, capturing real requests, and handling version drift; it must not replace the official sequence with ad hoc blank-theme experimentation.

For the condensed step-by-step checklist, read `official-docs-alignment.md`. Keep this file focused on site creation and first setup gates.

If the user explicitly asks to follow the official docs, refresh the relevant docs pages before relying on this file. The local reference records the last checked route, but the live docs page is the authority when the user points to it.

Default first-build order from the refreshed official docs:

```text
1. Create site.
2. Open the frontend once from the site card or default subdomain.
3. If the frontend shows a normal template, reuse/edit the generated theme/pages/content instead of creating another theme.
4. If the frontend is 404 or blank, inspect themes/pages/homepage and create a 默认 preset theme only when no usable theme/pages exist.
5. Prepare or edit product categories first.
6. Prepare or edit products.
7. Prepare or edit posts/articles.
8. Edit homepage modules after real categories/products/posts exist.
9. Create extra pages only when default pages are missing or the site needs new routes such as OEM, Cases, Services, or Solutions.
10. Configure site-info, domains, tracking, forms, and launch QA.
```

Do not start by creating a blank theme unless the user explicitly requests a blank build or a captured design/pageDocument workflow is already available. Official docs distinguish `空白` from `默认`: `默认` gives new operators starter pages/modules, while `空白` leaves the site without a launchable page structure and is easy to get stuck on.

The first launch target is intentionally narrow. Do not continue random backend exploration when these official minimums are not yet met:

```text
2-3 main product categories
at least 2 products per main category
3 basic posts/articles
homepage Header, Banner/Carousel, Category Showcase, Featured Product List or Recommended Products, Featured News List, Footer
Home, Products, Posts/News, About Us, and Contact Us routes open without unexpected 404s
```

Official site-creation stop gate:

```text
1. Create the site.
2. Return to the site list and open the public site.
3. If a normal template renders, stop theme creation and edit existing content.
4. Only if the site is 404 or blank, enter the site dashboard and inspect theme/page/homepage/route state.
5. If a theme exists with pages, use its Pages/Design controls.
6. If no theme exists or pages are empty, create a preset 默认 theme, enable it, and open the public site again.
7. If /home opens but / is 404, inspect homepage selection instead of creating a root route blindly.
```

## Safety Gate

Creating a site changes remote workspace state. Opening the create dialog and reading fields is read-only; pressing the final `创建` button is not read-only.

Before submitting creation, confirm the exact destination and data:

```text
workspace: https://workspace.laicms.com
action: create a new site
authorization target: https://workspace.laicms.com/sites
generatedAt: helper-generated ISO timestamp for both preflight and authorization
fields: name, description
existing site keys before create; use [] only when the site list is verified empty
siteKeyEvidence: one strong neutral source per existing key, such as backend URL/root route, href, or safe attribute
expected result: new site card, backend route, default frontend domain
```

Do not submit the create-site form unless the user explicitly authorizes that action in the current run. The authorization must name site creation and the `/sites` target; cleanup, upload, publish, or generic continuation authorization is not enough.

Do not use a visible site-card count as a substitute for `existingSiteKeysBeforeCreate`. The before-create evidence must contain reliable site keys, or `[]` only when the list was verified empty. If the `/sites` UI shows existing cards but their site keys cannot be extracted from visible routes, safe attributes, or verified backend URLs such as `https://workspace.laicms.com/{siteKey}`, stop before create submit and refresh the evidence path; otherwise a newly created key cannot be proven absent from the before-create set.

Before pressing the final `创建` button, all three local checks must pass in sequence:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_run_evidence.py ~/allincms-projects/allincms-create-site-preflight.json
python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py --validate-only ~/allincms-projects/allincms-authorization-create-site.json
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action create_site \
  --preflight ~/allincms-projects/allincms-create-site-preflight.json \
  --authorization ~/allincms-projects/allincms-authorization-create-site.json
```

The final gate rejects existing-site evidence, stale or malformed preflight evidence, generic authorization, wrong target URLs, and authorization records that omit `name` or `description`.

When the next browser packet is `create_site_submit`, first prepare and validate the non-authorizing browser-stage package:

```bash
python3 skills/allincms-bulk-content-upload/scripts/prepare_browser_stage_authorization.py \
  ~/allincms-projects/allincms-next-browser-stage-packet.json \
  --preflight ~/allincms-projects/allincms-create-site-preflight.json \
  --authorization-output ~/allincms-projects/allincms-authorization-create-site.json \
  --output ~/allincms-projects/allincms-create-site-authorization-package.json
python3 skills/allincms-bulk-content-upload/scripts/validate_browser_stage_authorization_package.py \
  ~/allincms-projects/allincms-create-site-authorization-package.json \
  --packet-json ~/allincms-projects/allincms-next-browser-stage-packet.json \
  --preflight ~/allincms-projects/allincms-create-site-preflight.json
```

This package validation proves only that the suggested text, command templates, `/sites` target, `name,description` fields, placeholder authorization source, and create-site gate are aligned. It is not user permission. Record fresh user authorization after this validation and rerun the pre-mutation gate immediately before submitting the form.

When site creation follows a confirmed source package, add one more local binding step before asking for action-time authorization:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_confirmed_create_site_handoff.py \
  --package ~/allincms-projects/run/source-site-package.json \
  --review-packet ~/allincms-projects/run/source-package-review-packet.json \
  --confirmation ~/allincms-projects/run/confirmation-record.json \
  --execution-plan ~/allincms-projects/run/confirmed-site-execution-plan.json \
  --preflight ~/allincms-projects/run/create-site-preflight.json \
  --authorization-output ~/allincms-projects/run/authorization-create-site.json \
  --output ~/allincms-projects/run/create-site-handoff.json
```

This handoff checks that the confirmed package, review packet, confirmation, `new_site` execution plan, and fresh `/sites` preflight all agree. It uses the confirmed `siteProposal.siteName` and `siteProposal.siteDescription` as the only create-site form data, keeps the authorization placeholder, and explicitly forbids content upload, publish, theme, route, domain, media, or tracking work in the same action. Passing this handoff still means "ready to ask for create-site authorization", not "authorized to submit".

The handoff command also writes `created-site-evidence-brief.json`. After the final create-site submit has passed its authorization and pre-mutation gate, use that brief to collect post-submit proof before binding artifacts or planning schema capture. Required proof includes the newly observed site key, absence from `existingSiteKeysBeforeCreate`, site-card link, backend dashboard URL, public frontend URL, required module routes, setup-page evidence, and one read-only content-type list/edit inspection. The brief is post-submit evidence guidance only; it does not authorize probes, saves, publishes, uploads, theme/routes/forms/settings edits, domain binding, or tracking changes.

Preflight and authorization JSON are short-lived. The helpers generate `generatedAt`; the final gate rejects missing, future, authorization-before-preflight, or older-than-30-minute records by default. If the gate fails for age, reopen `/sites`, refresh the create-site dialog evidence, regenerate authorization from the current user instruction, and rerun the gate.

For local-only rehearsal before a real submit, prefer `scripts/simulate_site_creation_chain.py`. It now writes preflight, authorization, created-site evidence, run summary, and round closeout artifacts in one directory. Treat those artifacts as proof that the local chain is coherent, not proof that any remote site exists.

Use `siteCreation.status: "create_preflight_verified"` only after the site list and create-site dialog have been inspected, `existingSiteKeysBeforeCreate` has been recorded as an array, and the form has not been submitted. An empty array is valid only when the site list was verified empty. This status is a pre-submit checkpoint, not proof that a site was created.

If confirmed source-package execution reports `needs_create_site_preflight`, open its `create-site-preflight-brief.json` first. The brief defines the read-only browser tasks and command templates for `make_create_preflight_evidence.py`; it does not authorize submitting the form. Use it to collect fresh `/sites` list evidence, scoped create-dialog fields, and dialog-close proof, then rerun confirmed execution with `--create-preflight`.

The next-stage handoff may still name `currentStage=create_site_handoff` while the confirmed create-site handoff is missing. In that case it must report `needsCreateSitePreflight=true` and `browserWorkRequired=false`; this is a read-only preflight blocker, not a browser submit step. Once the confirmed create-site handoff and create-site browser runbook exist, source execution advances to `created_site_binding`; then the required browser work is exactly one gated create-site submit followed by created-site evidence capture.

Preflight evidence must record the observed `创建站点` entry control, dialog title, `name` field, `description` field, submit/create control, close control, and `dialogClosedVerified: true` after no visible dialog remains.

When capturing create-dialog fields from the browser, scope to the actual modal surface, such as `[role="dialog"]`, `[aria-modal="true"]`, or the framework's dialog-content node. Do not select a broad page container merely because it contains the text `创建站点`; the site list page itself also contains that text and can make the search textbox look like a create-dialog field. Accept the dialog evidence only when the same scoped modal contains both `name` and `description` form fields plus `创建` and `Close` controls.

If the real browser refresh was first converted into `existing_site_selected` evidence with `make_existing_site_evidence_from_scan.py`, do not use that file directly as the create-site mutation preflight. The create-site gate intentionally requires `siteCreation.status: "create_preflight_verified"`. Build a separate create preflight with `make_create_preflight_evidence.py` from the freshly observed site keys, strong site-key evidence, and scoped create-dialog fields before preparing or validating `create_site_submit` authorization.

When the existing-site evidence was generated from the same fresh `/sites` refresh and already contains the scoped create-dialog fields, prefer the helper:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_create_preflight_from_existing_site_evidence.py \
  ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --output ~/allincms-projects/allincms-create-site-preflight.json
python3 skills/allincms-bulk-content-upload/scripts/validate_run_evidence.py \
  ~/allincms-projects/allincms-create-site-preflight.json
```

This helper is a conversion tool only. It does not create a site and does not create user authorization.

## Browser-Verified Entry Flow

Observed on 2026-06-29 in the in-app browser:

```text
Workspace dashboard:
https://workspace.laicms.com/dashboard

Site list:
https://workspace.laicms.com/sites
```

The dashboard exposes a `站点` side-nav link and a `管理站点` action. The site list exposes:

```text
搜索站点...
创建站点
site cards
进入后台
打开站点
```

The create-site dialog opened from `创建站点` contains:

```text
title: 创建站点
description: 填写信息以创建新站点。
field: 名称, placeholder 站点名称
field: 描述, placeholder 站点简介
submit: 创建
close: Close
```

After reading fields, close the dialog and verify it is no longer visible before continuing. Prefer the dialog-scoped `Close` control: count visible close controls, click only when exactly one is visible, then verify no visible `[role="dialog"]` remains. Use `Esc` only as a fallback; page-level keyboard presses can fail after focus changes inside the modal. Do not assume any close action worked until the modal is gone. Record `dialogClosedVerified: true` only after no visible `[role="dialog"]` remains.

## After Site Creation

After the site is created, record these values before any upload:

```json
{
  "siteName": "",
  "siteDescription": "",
  "siteKey": "",
  "backendDashboardUrl": "https://workspace.laicms.com/{siteKey}/dashboard",
  "frontendBaseUrl": "https://{siteKey}.web.allincms.com",
  "preflightGeneratedAt": "YYYY-MM-DDTHH:MM:SS+00:00",
  "generatedAt": "YYYY-MM-DDTHH:MM:SS+00:00",
  "createdBy": "redacted"
}
```

Open the new site's backend dashboard and verify visible module routes. On the verified site, these groups existed:

```text
Content: products, posts, media
Design: themes, routes, forms
Settings: site-info, tracking, domains
```

Do not assume every new site has existing posts/products or the same default theme pages. Count dashboard records and inspect list pages.

For source-package-driven new sites, bind the created site identity into exported runtime artifacts before schema capture or upload planning:

```bash
python3 skills/allincms-bulk-content-upload/scripts/bind_created_site_to_artifacts.py \
  --artifact-readiness ~/allincms-projects/run/confirmed-artifacts/artifact-readiness.json \
  --created-site-evidence ~/allincms-projects/run/created-site-evidence.json \
  --output-dir ~/allincms-projects/run/created-site-bound-artifacts \
  --output ~/allincms-projects/run/created-site-artifact-binding.json
```

This prevents placeholder `{siteKey-after-creation}` or stale frontend base URLs from entering later upload runbooks. The bound manifests are still draft-only: `schemaVerified` must remain false until products/posts save-request capture and sample verification pass.

Before creating content probes from those bound manifests, build the schema-capture handoff:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_schema_capture_handoff.py \
  --created-site-binding ~/allincms-projects/run/created-site-artifact-binding.json \
  --created-site-evidence ~/allincms-projects/run/created-site-evidence.json \
  --output-dir ~/allincms-projects/run/schema-capture \
  --output ~/allincms-projects/run/schema-capture-handoff.json
```

This handoff keeps the new-site flow honest: products and posts each need their own list/edit preflight before create-probe authorization. It does not create drafts, save probes, publish samples, or make the manifests upload-ready.

If a content type is blocked by missing read-only preflight, inspect that list/edit page without saving, generate same-site `existing_site_selected` evidence, merge it, then rebuild the handoff:

```bash
python3 skills/allincms-bulk-content-upload/scripts/merge_content_type_preflight.py \
  --created-evidence ~/allincms-projects/run/created-site-evidence.json \
  --refresh-evidence ~/allincms-projects/run/posts-readonly-evidence.json \
  --content-type posts \
  --output ~/allincms-projects/run/created-site-evidence.posts-preflight.json
```

The merge output preserves the original created-site proof but switches top-level `contentInspection` to the target content type so the normal create-probe pre-mutation gate can use it.
For this existing-site refresh, do not fabricate create-site dialog fields. Current site-key evidence, selected dashboard evidence, module routes, setup-page observations, and content list/edit fields are enough for `existing_site_selected`; a separate `create_preflight_verified` file is still required before any new-site submit.

Immediately after creation, open the frontend before creating themes or uploading content:

```text
normal template page = theme/template import likely succeeded; continue by editing existing content
404 or blank page = stop content upload; inspect themes, pages, enabled state, homepage selection, route binding, and active theme
```

If themes already exist and show page counts, prefer using `页面` or `设计` on that theme. If themes exist but page count is `0`, or the theme/page list is empty, create a `默认` preset theme. A blank theme that shows `0 页` is phase evidence only; it is not a launchable site foundation until real pages, blocks, homepage, route binding, active theme state, and frontend DOM proof exist.

When the frontend is 404/blank and read-only setup evidence shows no usable theme/pages, prepare the default-theme bootstrap runbook before touching products/posts:

```bash
python3 skills/allincms-bulk-content-upload/scripts/prepare_default_theme_bootstrap.py \
  --preflight ~/allincms-projects/allincms-run/created-site-evidence.json \
  --output ~/allincms-projects/allincms-run/default-theme-bootstrap-runbook.json
```

The runbook is preparation only. It splits the browser work into two mutations: `create_theme` with preset `默认`, then `activate_theme` after route mapping is reviewed. Each action still needs its own authorization record and `check_pre_mutation_gate.py` pass.

After the browser stage, validate redacted evidence:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_default_theme_bootstrap_evidence.py \
  ~/allincms-projects/allincms-run/default-theme-bootstrap-evidence.json \
  --runbook ~/allincms-projects/allincms-run/default-theme-bootstrap-runbook.json \
  --output ~/allincms-projects/allincms-run/default-theme-bootstrap-validation.json
```

After validation, apply the bootstrap result to created-site evidence before rebuilding pages/site-info, taxonomy, or schema-capture handoffs:

```bash
python3 skills/allincms-bulk-content-upload/scripts/apply_default_theme_bootstrap.py \
  --created-site-evidence ~/allincms-projects/allincms-run/created-site-evidence.json \
  --runbook ~/allincms-projects/allincms-run/default-theme-bootstrap-runbook.json \
  --bootstrap-evidence ~/allincms-projects/allincms-run/default-theme-bootstrap-evidence.json \
  --output-dir ~/allincms-projects/allincms-run/default-theme-bootstrap-applied \
  --fail-on-invalid
```

Use `~/allincms-projects/allincms-run/default-theme-bootstrap-applied/created-site-evidence.after-default-theme-bootstrap.json` as the next created-site evidence input. Do not keep using stale pre-bootstrap evidence after the public site was blank: later helpers need updated themes/routes/frontend foundation proof, while still treating business content as incomplete.

For source-package runs, prefer the chained local path when artifact readiness and confirmation context are available:

```bash
python3 skills/allincms-bulk-content-upload/scripts/apply_default_theme_bootstrap.py \
  --created-site-evidence ~/allincms-projects/allincms-run/created-site-evidence.json \
  --runbook ~/allincms-projects/allincms-run/default-theme-bootstrap-runbook.json \
  --bootstrap-evidence ~/allincms-projects/allincms-run/default-theme-bootstrap-evidence.json \
  --output-dir ~/allincms-projects/allincms-run/default-theme-bootstrap-applied \
  --prepare-created-site-schema-capture \
  --artifact-readiness ~/allincms-projects/allincms-run/execution/confirmed-artifacts/artifact-readiness.json \
  --package ~/allincms-projects/allincms-run/source-site-package.json \
  --confirmation ~/allincms-projects/allincms-run/execution/confirmation-record.json \
  --execution-plan ~/allincms-projects/allincms-run/execution/confirmed-site-execution-plan.json \
  --fail-on-invalid
```

This still performs local evidence application and local preparation only. It writes the refreshed created-site evidence, created-site artifact binding, pages/site-info handoff, taxonomy handoff, schema-capture handoff, source execution status, and source next-stage handoff. It does not create probes, save pages, upload content, publish, or mutate the remote site.

Valid evidence requires preset `默认`, a concrete theme id, starter page count, enabled theme proof, route binding/review proof, and non-empty public frontend DOM for `/`, `/home`, `/products`, `/posts`, `/about-us`, and `/contact-us`. Keep `businessContentComplete=false`: default template content fixes the blank-site foundation but still needs source-confirmed copy, products, posts, forms/media/settings, and launch QA.

When recording evidence, require `preflightGeneratedAt`, fresh `generatedAt`, `existingSiteKeysBeforeCreate`, `createdSiteKey`, backend dashboard URL, frontend base URL, and module routes. The before-create list may be empty only when `/sites` was verified empty. The created site key must be absent from the before-create list, and every created-site URL must use the same lowercase/digit/hyphen site key. Do not verify a newly created site with an older site's dashboard or frontend domain.

For a created site, do not mark creation complete until all three checks are true:

```text
siteCardVerified: the site list shows the new site card and an enter/open control
backendVerified: the new backend dashboard opens under /{createdSiteKey}/dashboard
frontendVerified: the default frontend origin opens at https://{createdSiteKey}.web.allincms.com
```

Record short neutral evidence for each check. If only the create form was submitted but the new card, backend, or frontend was not verified, keep the status below completed and stop before upload.

Opening the default frontend origin only proves the new public runtime is reachable. A newly created site may show little or no visible page content until theme pages, routes, or content have been configured. Do not treat `frontendVerified: true` as proof that the homepage, product list, or post list is ready; verify those routes separately before upload or publish work.

When static frontend routes have been audited after site creation, merge the generated `frontendRendering` block into the created-site evidence with `make_created_site_evidence.py --frontend-rendering-evidence`. Keep one evidence file for the created site whenever possible, so `summarize_run_status.py --require-created-site` can distinguish these states:

```text
created site verified
static frontend routes render
content upload still missing request capture/sample/cleanup proof
```

For the first post-create check, record module routes for dashboard, products, posts, media, themes, routes, forms, site-info, tracking, and domains. Missing modules must be treated as a setup variance to inspect before content upload.

## First-Site Setup Checks

Before uploading content, inspect these pages without saving:

```text
/{siteKey}/site-info
/{siteKey}/domains
/{siteKey}/themes
/{siteKey}/routes
/{siteKey}/forms
```

Observed setup fields and controls on 2026-06-29:

```text
site-info:
  name input, placeholder 站点名称
  description textarea, placeholder 站点简介
  site icon upload control
  notificationEmail input
  保存 button

domains:
  CNAME target copy control
  domain input
  添加域名 button

themes:
  search themes
  创建主题
  页面
  设计
  预览

routes:
  search routes
  状态
  视图
  创建
  columns: 路径, 绑定页面, 绑定状态, 备注, 更新时间
  添加子路由

forms:
  search forms
  状态
  视图
  创建
  columns: 名称, Slug, 描述, 字段, 状态, 更新时间
```

Official-docs first-build setup decisions to record as source-input gaps or user-confirmed fields:

```text
site-info: favicon/logo, notification email, site name/description
domains: intended public domain, CNAME target copied as plain domain, DNS platform, SSL wait/check status
tracking: real Google Tag ID if analytics is in scope; never invent a fake tag
forms: notification destination and whether a public test submission is allowed
navigation: Home, Products, News/Blog, About Us, Contact Us, plus any OEM/Cases/Services/Solutions pages
homepage: Header, Banner/Carousel, Category Showcase, Featured Product List, Featured News List, Footer
```

## Stop Conditions

Stop before upload if:

```text
site creation was not explicitly authorized
create-site submission result was not verified
siteKey or frontend base URL is unknown
site dashboard does not expose expected content modules
site-info or domain setup is required but not decided by user
routes do not show post/product/page bindings needed for frontend verification
```

## Evidence Hygiene

Record only neutral UI labels, route shapes, counts, and redacted identifiers. Do not store account emails, business copy, customer names, source-site topics, or content titles in this skill.

When inspecting dashboards or list pages, do not copy account menu text, recent-activity rows, content titles, content IDs, or row text into skill docs or run evidence. Record only module routes, aggregate counts, control labels, placeholders, and table headers needed to prove platform behavior.

For setup-page scans, do a second redaction pass before storing the artifact as evidence. Top-level navigation and site-switcher buttons can include account labels, email addresses, concrete frontend domains, and site names even when the target page itself is neutral. Keep only module-local controls such as `保存`, `添加域名`, `创建主题`, `状态`, `视图`, table headers, field names, placeholders, and redacted `https://workspace.laicms.com/{realSiteKey}/...` URLs.
