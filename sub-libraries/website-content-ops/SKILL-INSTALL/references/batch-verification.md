---
doc_id: allincms-bulk-batch-verification
title: AllinCMS 批量上传验证
description: LAICMS / AllinCMS 样本上传、批量发布、前台渲染检查和清理验收流程
layer: ops
status: draft
created: 2026-06-29
updated: 2026-07-03
page_type: reference
sources: []
confidence: medium
---

# Batch Verification

Use this reference for sample upload, batch upload, publish, cleanup, and final QA.

For first-launch content targets and official tutorial order, read `official-docs-alignment.md` before running final QA. Batch proof is content persistence proof; launch proof still requires the official visitor-style checks for categories, products, posts, homepage modules, contact/form, images, mobile, and domain when in scope.

## Manifest Shape

The local manifest should be a JSON object with an `items` array:

```json
{
  "siteKey": "example",
  "contentType": "products",
  "frontendBaseUrl": "https://example.web.allincms.com",
  "items": [
    {
      "name": "Example Product",
      "slug": "example-product",
      "description": "Short product description",
      "coverImage": {
        "url": "https://cdn.example.com/example.jpg",
        "alt": "Example Product"
      },
      "content": []
    }
  ]
}
```

Run:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_manifest.py manifest.json
```

The default script checks generic draft safety rules. It does not prove the payload matches the live backend schema.

Before any live upload, replay, or batch operation, require a captured schema:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_manifest.py \
  --require-schema-verified manifest.json
```

This stricter gate requires `schemaVerified: true`, a current-site `fieldMapping`, and a `payloadTemplate` derived from the real save request for the exact content type. Use `schemaVerified: false` for local draft manifests before product/post probe request capture; never upload from that state.

When a draft manifest came from source-package export, upgrade it with validated save-capture evidence instead of toggling fields by hand:

```bash
python3 skills/allincms-bulk-content-upload/scripts/apply_save_capture_to_manifest.py \
  --manifest ~/allincms-projects/allincms-products-draft-manifest.json \
  --save-capture-evidence ~/allincms-projects/allincms-products-save-capture-evidence.json \
  --base-run-evidence ~/allincms-projects/allincms-products-run-evidence-after-save-capture.json \
  --output ~/allincms-projects/allincms-products-schema-verified-manifest.json
```

Run `validate_manifest.py --require-schema-verified` on the output. The helper binds one content type to one current-site capture; products and posts must be processed separately.

`payloadTemplate` is necessary but not always sufficient. Check the captured request for the actual depth of proof:

```text
If the save capture only proves `content` is an empty array, it does not prove the block schema for non-empty body content.
If media upload or media selection was only simulated, it does not prove `media`, `mediaList`, cover image, or public URL behavior.
If sample verification still says body/media is false, do not batch upload even if the manifest passes the generic schema flag check.
```

For products or posts with body content, require either a captured non-empty editor block shape or an explicit no-body acceptance rule for that batch. For products or posts with images, require real media/public URL proof or an explicit no-image acceptance rule before final QA.

URL-bound content media can satisfy media proof only after the full content lifecycle is verified. A product main media or post cover chosen through an edit-page media picker `URL` tab is not the same as media-library upload proof, but it can be valid for launch QA when all of these are true:

```text
the picker preview loads the public URL
the edit page shows the selected image
the content save request is captured on the product/post update URL
the save result is not left in draft
the item is published or republished if the save changed status to draft
the public list/detail pages render an <img> with non-zero natural dimensions
the image source is public and not a local path
```

If the backend list lacks a media column, as posts may, do not require backend-list image proof. Use edit-page preview, save/publish request evidence, backend published status, and public frontend list/detail DOM image proof instead.

Homepage and static page module images need a separate public QA check. A page can have correct category/product copy while still showing default template image alts such as generic lifestyle labels. For launch-facing modules such as Category Showcase, Hero, Featured Products, News, Material Story, and Contact blocks, inspect both the images and their surrounding public DOM:

```text
old/template alt labels are absent
every in-scope image has complete=true and non-zero naturalWidth/naturalHeight
surrounding card text still matches the intended block item
card links still point to the intended public route
desktop has no broken images or raw Markdown residue
mobile effective viewport is proven and has no horizontal overflow
```

Replacing designer module images through the `URL` tab counts as URL-bound designer media proof only after the picker preview, design save, design publish, public desktop DOM, and public mobile DOM are all verified. If the images are public but still generic stock/demo assets, record an asset-quality gap instead of calling the site production launch-complete.

For local rehearsal, generate a neutral draft manifest and confirm the expected gate behavior:

```bash
python3 skills/allincms-bulk-content-upload/scripts/simulate_manifest_rehearsal.py \
  --site-key simsite01 \
  --content-type products \
  --output-dir ~/allincms-projects/allincms-manifest-rehearsal
python3 skills/allincms-bulk-content-upload/scripts/validate_manifest_rehearsal.py \
  ~/allincms-projects/allincms-manifest-rehearsal/manifest-rehearsal-summary.json
```

This rehearsal must pass generic draft validation and fail `--require-schema-verified` with `schemaVerified` and `payloadTemplate` errors. A generic draft manifest is source normalization proof only, not upload permission.

Do not treat Markdown strings as publish-ready rich text. If source content contains `**bold**`, backticks, Markdown links, lists, or pipe tables, convert them to the editor's real block/mark schema before upload and verify the frontend DOM contains the expected `strong`, `code`, `a`, `ul/ol`, or `table` nodes.

Literal Markdown markers in visitor-visible text or rendered DOM are a launch blocker even when the route returns HTTP 200, has an H1, and renders images. If product or post detail visible text contains raw `**`, backticks, pipe-table syntax, or other Markdown source text, repair the saved rich-text body or replay the content with the current editor block schema, publish again, and rerun detail QA. Do not classify raw HTML/CSS alone as Markdown residue: Tailwind/Slate class names such as `**:data-slate-placeholder...` may appear in HTML attributes while no visitor-visible Markdown exists. In that case, record `htmlDoubleStarCount` as diagnostics and confirm `visibleTextDoubleStarCount` plus DOM residue before blocking launch.

Products and posts draft manifests may be prepared in parallel while content is being planned, but their schema gates must remain separate. Passing generic validation for both only proves local content hygiene. Each content type still needs its own live save request capture, `fieldMapping`, `payloadTemplate`, sample backend/frontend verification, and cleanup proof before upload or batch publishing.

For source-package manifests, use a manifest sample stage after the schema gate and before batch upload. The sample must be one concrete slug from the schema-verified manifest:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_manifest_sample_upload_runbook.py \
  --manifest ~/allincms-projects/allincms-products-schema-verified-manifest.json \
  --target https://workspace.laicms.com/example/products \
  --sample-slug example-product \
  --authorization-output ~/allincms-projects/allincms-authorization-products-sample.json \
  --output ~/allincms-projects/allincms-products-sample-runbook.json
python3 skills/allincms-bulk-content-upload/scripts/validate_manifest_sample_upload_evidence.py \
  ~/allincms-projects/allincms-products-sample-evidence.json \
  --manifest ~/allincms-projects/allincms-products-schema-verified-manifest.json \
  --output ~/allincms-projects/allincms-products-sample-validation.json
```

This is separate from the older `Codex Probe - Delete Me` sample path. Probe sample proof can validate schema and route behavior, but a source-generated manifest also needs one manifest item to prove the manifest's actual title/body/media mapping before batch upload.

The sample item is **written the same way the batch is — a JSON replay of one manifest entry** through the captured Server Action (`server-action-save-api.md`), not a hand-clicked UI edit. The sample gate is about verifying persistence (backend `isDraft:false` + non-empty `content`, then the public detail route), not about the write being manual. If the one-item JSON replay + verification passes, the batch is the same replay repeated serially with retry; if it fails, fix the payload/capture before the batch, never fall back to clicking every entry through the UI.

For source-package runs, apply the validated sample evidence back into the source execution dashboard before preparing batch upload:

```bash
python3 skills/allincms-bulk-content-upload/scripts/apply_manifest_sample_upload.py \
  --manifest ~/allincms-projects/allincms-products-schema-verified-manifest.json \
  --sample-evidence ~/allincms-projects/allincms-products-sample-evidence.json \
  --package ~/allincms-projects/allincms-run/source-site-package.json \
  --confirmation ~/allincms-projects/allincms-run/execution/confirmation-record.json \
  --execution-plan ~/allincms-projects/allincms-run/execution/confirmed-site-execution-plan.json \
  --artifact-readiness ~/allincms-projects/allincms-run/execution/confirmed-artifacts/artifact-readiness.json \
  --created-site-binding ~/allincms-projects/allincms-run/created-site-schema-capture/created-site-artifact-binding.json \
  --pages-site-info-handoff ~/allincms-projects/allincms-run/created-site-schema-capture/pages-site-info/pages-site-info-browser-handoff.json \
  --pages-site-info-validation ~/allincms-projects/allincms-run/pages-site-info-applied/pages-site-info-execution-validation.json \
  --schema-capture-handoff ~/allincms-projects/allincms-run/created-site-schema-capture/schema-capture-handoff.json \
  --upload-readiness ~/allincms-projects/allincms-run/schema-capture/products-schema-manifest-sample/products-upload-readiness.json \
  --output-dir ~/allincms-projects/allincms-run/manifest-sample-applied
```

The apply helper writes a sample validation report, one progress-log seed entry, and `source-execution-status.after-manifest-sample.json`. A standalone `validate_manifest_sample_upload_evidence.py` pass proves the sample file shape; it does not by itself update the source-package execution boundary. Follow the refreshed `currentStage`; only `batch_upload` means batch preparation is the next source-stage boundary.

When multiple draft manifests exist, build a deterministic readiness report before upload planning:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_manifest_upload_readiness.py \
  ~/allincms-projects/allincms-products-draft-manifest.json \
  ~/allincms-projects/allincms-posts-draft-manifest.json \
  --output ~/allincms-projects/allincms-upload-readiness-report.json
```

If any manifest item contains `categories`, `tags`, or `categoryIds`, include the validated taxonomy execution report:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_manifest_upload_readiness.py \
  ~/allincms-projects/allincms-products-schema-verified-manifest.json \
  ~/allincms-projects/allincms-posts-schema-verified-manifest.json \
  --taxonomy-validation ~/allincms-projects/allincms-taxonomy-execution-validation.json \
  --output ~/allincms-projects/allincms-upload-readiness-report.json
```

Use the report's `overallStatus`, `readyCount`, `blockedCount`, and per-manifest `taxonomyGate` in the handoff. `overallStatus: blocked` is the correct result until every manifest has `schemaVerified: true`, a current-site `fieldMapping`, a captured `payloadTemplate`, and `taxonomyGate.ok=true` when taxonomy fields are present. Add `--fail-on-blocked` in automation that must stop before any live upload:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_manifest_upload_readiness.py \
  ~/allincms-projects/allincms-products-draft-manifest.json \
  ~/allincms-projects/allincms-posts-draft-manifest.json \
  --output ~/allincms-projects/allincms-upload-readiness-report.json \
  --fail-on-blocked
```

For repeatable frontend checks, run:

```bash
python3 skills/allincms-bulk-content-upload/scripts/audit_frontend_rendering.py \
  --json --redact \
  --timeout 8 --max-bytes 2000000 \
  https://example.web.allincms.com/posts/example-slug
```

Use `--urls-file urls.txt --json` for a batch report.

Use `--timeout` and `--max-bytes` for broad launch audits. Some deployed frontend routes can keep chunked reads open longer than the socket timeout, so the auditor wraps the whole fetch in an operation alarm and can stop after a bounded byte count. A `fetch_failed` issue is a launch blocker until rerun or browser verification proves the route renders.

If the CLI audit reports `fetch_failed` for a route that recently rendered in the browser, verify the same URL in a live browser before calling the page broken. Record the split result explicitly: browser-visible DOM can prove route rendering, while the CLI failure remains an audit-tool reliability or network-fetch issue that should be rerun before final launch acceptance.

If an immediate rerun of the same CLI audit succeeds with expected status and no issues, keep the first `fetch_failed` artifact as diagnostic noise rather than final route proof. Still preserve a browser DOM check for the affected route when the first failed artifact was part of a launch blocker review.

For broad audits on AllinCMS frontend routes, a single large `audit_frontend_rendering.py` run may hang on a chunked response while reading the next chunk size, even when `--timeout` and `--max-bytes` are set. If the same URL renders in the browser, split the audit into smaller route groups, lower `--max-bytes`, and preserve browser DOM proof for any route whose CLI check ends in `fetch_failed` or has to be interrupted. Do not leave the hung process running, and do not treat an interrupted chunked read as public route failure by itself.

When discovering public routes from HTML, filter out asset URLs such as `/_next/static/...`, CSS, JS, images, fonts, and hash-only links before building a page audit URL file. Asset URLs can appear in raw `href` extraction and should not be counted as launch pages or route failures.

If `audit_frontend_rendering.py` reports `missing_h1` or `fetch_failed` on large AllinCMS pages, confirm with a second bounded method before recording a launch blocker. A bounded `curl` sample or browser DOM sample that returns HTTP 200 and finds `<h1>` can downgrade the CLI finding to tool noise. Keep the CLI artifact and the recheck artifact together so the final summary explains the discrepancy.

`audit_frontend_rendering.py --json` writes a JSON array of per-URL report objects, not a top-level summary object. Helpers that consume the report, such as `make_frontend_rendering_evidence.py`, expect that array shape. Do not hand-wrap the report in another object before conversion.

Use `--redact` whenever the report is copied into run evidence or a skill reference. Redacted reports keep route patterns such as `/posts/{slug}` and issue codes, but remove concrete slugs, page headings, and text snippets.

For posts routes, do not accept HTTP 200, route binding, or an HTML title as launch proof. `/posts` and `/posts/{post}` need browser-visible DOM content from a list/detail Articles block. A rendered body that is blank, an empty theme page, `No blocks yet`, or a designer stuck at `Render canvas...` is a blocker even when the status code is 200.

A non-empty `/posts` list route is phase progress, not launch acceptance. In one verified run, publishing the static Posts design changed `/posts` from an empty 200 page to a visible list with one article title, excerpt, and links, but the route still had no H1 or images. Treat that as list-render proof only. Final QA still needs heading policy, media/no-image acceptance, and a separate `/posts/{post}` detail DOM check.

When the Posts list block is `Full News List (Filtered)`, verify H1 independently from list rendering. The block may render post titles, excerpts, and links while exposing no heading prop in the designer. A clean list render with `h1: []` remains a structural warning or blocker under launch QA unless the run has an explicit no-H1 acceptance rule or a separate heading block is added and published.

Use normalized public route patterns in frontend audit artifacts:

```text
/posts/{slug}
/products/{slug}
```

Designer props may show internal parameter names such as `/posts/{post}` or `/products/{product}`. Keep those as backend/designer field evidence, but do not put them into helpers that validate public audit route patterns unless the helper explicitly supports internal route parameters.

For `/posts/{post}` detail pages, visible article title, excerpt, and body text after `Post Detail (Article)` publish are valid detail-render proof. Still keep media proof separate: a detail page with zero images may be acceptable only with an explicit no-image/no-cover decision or later media upload and binding proof.

For post updates that change slug or publish state, verify in this order: backend row is `已发布`, `/posts` lists and links the updated slug, and `/posts/{slug}` renders the detail DOM. If the first immediate detail request returns 404 or a fetch timeout while the browser list already links the slug, retry within a short bounded window before declaring the detail route broken. Do not accept the list link as detail proof.

For product detail pages, verify body, specifications, and media separately. A product can render title/body/specification terms while still lacking real media because the media library is empty or no product media is bound. Treat `Specifications` term/definition DOM as specs proof only; it is not image proof.

When replacing default product specifications, verify every product detail route against a denylist of old template values after publish. Clean backend rows are not enough: the public `dt/dd` terms and definitions must show product-domain specs and must not include unrelated default material, closure, tray, bag, capacity, or care terms.

After batch upload and before final frontend audit, generate the audit URL/status inputs from the schema-verified manifest and the batch progress log. Do not hand-maintain final detail URLs:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_final_frontend_audit_inputs.py \
  --manifest ~/allincms-projects/allincms-schema-verified-manifest.json \
  --progress-log ~/allincms-projects/allincms-batch-progress.json \
  --require-schema-verified \
  --require-progress-complete \
  --static-paths /,/products,/about-us,/contact-us \
  --urls-output ~/allincms-projects/allincms-final-audit-urls.txt \
  --statuses-output ~/allincms-projects/allincms-final-expected-statuses.json \
  --summary-output ~/allincms-projects/allincms-final-audit-inputs-summary.json

python3 skills/allincms-bulk-content-upload/scripts/audit_frontend_rendering.py \
  --json --redact \
  --timeout 8 --max-bytes 2000000 \
  --urls-file ~/allincms-projects/allincms-final-audit-urls.txt \
  --expect-statuses-file ~/allincms-projects/allincms-final-expected-statuses.json \
  > ~/allincms-projects/allincms-final-audit-report.json
```

For mixed products/posts launches, pass every schema-verified manifest to the same final-audit input generator. Use one combined completed progress log, or repeat `--progress-log` in the same order as the manifests:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_final_frontend_audit_inputs.py \
  --manifest ~/allincms-projects/allincms-products-schema-verified-manifest.json \
  --manifest ~/allincms-projects/allincms-posts-schema-verified-manifest.json \
  --progress-log ~/allincms-projects/allincms-combined-batch-progress.json \
  --require-schema-verified \
  --require-progress-complete \
  --static-paths /,/products,/posts,/about-us,/contact-us \
  --urls-output ~/allincms-projects/allincms-final-audit-urls.txt \
  --statuses-output ~/allincms-projects/allincms-final-expected-statuses.json \
  --summary-output ~/allincms-projects/allincms-final-audit-inputs-summary.json
```

Do not run separate final audits and claim the whole site is accepted from only one content type. A products manifest proves product detail coverage only; a posts manifest proves post detail coverage only. The final URL/status files must include every planned uploaded products/posts slug plus the in-scope static routes before launch acceptance.

The generated URL/status files are runtime artifacts and may contain concrete slugs; keep them in `~/allincms-projects` or the current run evidence folder, not in the skill. Only copy the redacted audit report or the generated evidence block into durable run evidence.

Redacted final audit reports must still bind back to the concrete runtime URLs. Use `audit_frontend_rendering.py --redact`, which preserves `urlFingerprint` while replacing detail URLs with `/products/{slug}` or `/posts/{slug}`. Final audit stage generation must compare the expected concrete URL fingerprints from `expectedStatuses` against the redacted report fingerprints. Route pattern coverage and instance counts are not enough for final acceptance because the wrong product/post slug can otherwise satisfy the same route pattern.

Static route expectations must come from the actual site navigation, route table, and content type in scope. Do not include `/posts` as required launch proof on a product-only site unless the route is visible and intended to render. If `/posts` is expected 200 but returns 404, record a blocking issue and keep launch readiness incomplete even if `/`, `/products`, `/about-us`, `/contact-us`, or other static pages pass.

For product categories, separate backend category existence from frontend category-filter proof. A static marketing `/products` page may render product-family copy but no CMS category names, links, or `?category=` filters. In that case, backend categories can count toward content setup progress, but the official-docs category acceptance item "front `/products` can click category filters and copy real category links" remains incomplete until a CMS product/category module renders those links or an explicit demo-scope deferral is recorded.

Do not hand-write contact or CTA audit paths from memory. Derive them from the current theme page list, route table, or visible frontend links. In one temporary-site run, `/contact-us` was the actual published contact route and rendered a form, while `/contact` returned a 404. Treat the wrong alias as a URL-selection error, not proof that the contact page is missing. If a CTA points to the wrong alias, fix the CTA or create an intentional redirect/route; otherwise audit the actual route.

For staged browser execution, convert the final audit report into a stage result before applying the ledger:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_final_frontend_audit_stage_result.py \
  --packet-json ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet-after-forms-media-settings-complete.json \
  --audit-report-json ~/allincms-projects/allincms-final-audit-report.json \
  --evidence-pointers ~/allincms-projects/allincms-final-audit-report.json,~/allincms-projects/allincms-final-audit-inputs-summary.json \
  --output ~/allincms-projects/allincms-final-frontend-audit-stage-result.json
```

The helper records `completed` only when the report contains the required HTTP status, DOM/rich-text, image, and empty broken-entry proof. Any status mismatch, raw Markdown residue, DOM/rich-text issue, or image issue produces a `partial` result and must keep cleanup locked.

Use `--fail-on-warn` when duplicate H1s, missing H1s, missing alt text, or other structural warnings should block a release:

```bash
python3 skills/allincms-bulk-content-upload/scripts/audit_frontend_rendering.py \
  --urls-file urls.txt \
  --fail-on-warn
```

Use `--expect-status` for route-state checks where all supplied URLs share the same expected status. For example, before product or post probes exist, detail routes should usually remain 404:

```bash
python3 skills/allincms-bulk-content-upload/scripts/audit_frontend_rendering.py \
  --json --redact --expect-status 404 \
  https://example.web.allincms.com/products/codex-probe-delete-me \
  https://example.web.allincms.com/posts/codex-probe-delete-me
```

For a mixed launch audit where static pages should return 200 and content detail probe routes should return 404, use a status map:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_launch_audit_inputs.py \
  --frontend-base-url https://example.web.allincms.com \
  --static-paths /,/home,/products,/solutions,/about-us,/contact-us \
  --detail-probe-paths /products/codex-probe-delete-me,/posts/codex-probe-delete-me \
  --urls-output ~/allincms-projects/allincms-launch-audit-urls.txt \
  --statuses-output ~/allincms-projects/allincms-launch-expected-statuses.json

python3 skills/allincms-bulk-content-upload/scripts/audit_frontend_rendering.py \
  --json --redact \
  --timeout 8 --max-bytes 2000000 \
  --urls-file ~/allincms-projects/allincms-launch-audit-urls.txt \
  --expect-statuses-file ~/allincms-projects/allincms-launch-expected-statuses.json
```

The status map keys must match the original URL strings from the URL file or command arguments.

To reuse the audit output inside run evidence, write the redacted JSON report to a file and convert it:

```bash
python3 skills/allincms-bulk-content-upload/scripts/audit_frontend_rendering.py \
  --json --redact \
  --timeout 8 --max-bytes 2000000 \
  --urls-file ~/allincms-projects/allincms-launch-audit-urls.txt \
  --expect-statuses-file ~/allincms-projects/allincms-launch-expected-statuses.json \
  > ~/allincms-projects/allincms-launch-audit-report.json

python3 skills/allincms-bulk-content-upload/scripts/make_frontend_rendering_evidence.py \
  ~/allincms-projects/allincms-launch-audit-report.json \
  --output ~/allincms-projects/allincms-frontend-rendering-evidence.json
```

The generated JSON contains a top-level `frontendRendering` object that can be copied or merged into run evidence before `validate_run_evidence.py`.

For existing-site read-only launch evidence, pass that generated file directly to the evidence generator:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_existing_site_readonly_evidence.py \
  --site-key example \
  --existing-site-keys example \
  --frontend-rendering-evidence ~/allincms-projects/allincms-frontend-rendering-evidence.json \
  ...other required read-only evidence fields... \
  --output ~/allincms-projects/allincms-readonly-launch-evidence.json
```

Use `--no-repo-check-passed --repo-check-note "..."` for partial read-only evidence when the wider workspace has unrelated dirty files or repo checks were intentionally not run. Do not write `--repo-check-passed=false`.

In zsh examples and wrapper commands, do not assign to a shell variable named `status`; zsh exposes `status` as a read-only special parameter. Use `exit_code`, `cmd_status`, or direct `if command; then ... fi` checks.

## Sample Upload Gate

Upload one item first. For posts, verify:

```text
/posts/{slug} returns 200
title is correct
excerpt is visible where expected
cover image loads
body content renders
status is published only if publish was requested
```

For products, verify:

```text
/products/{slug} returns 200
name or title is correct
description is visible
cover image loads
body content renders
specs or parameters render if required
status is published only if publish was requested
```

If the frontend route differs, update the route template before continuing.

If the backend exposes a `routes` page, verify detail route bindings there before assuming route names. On verified sites, the default route rows can exist while still showing `未绑定`. A product can be `已发布` in the backend and `/products` can return 200 while `/products/{slug}` returns 404 if `/products/{product}` is unbound. Treat the detail route binding as a blocking sample-verification issue and bind/verify it before batch upload. On the verified `mysite01` route shape, the detail patterns were `/posts/{post}` and `/products/{product}`.

Run evidence for a sample upload must record:

```text
backendUrl
frontendUrl
status
titleOrNameVerified
coverOrMediaVerified
bodyVerified
renderAudit result or command summary
```

For read-only frontend checks, run evidence may include:

```json
{
  "frontendRendering": {
    "checked": true,
    "routePatterns": ["/", "/home", "/products", "/products/{slug}"],
    "expectedStatuses": {
      "/": 200,
      "/home": 200,
      "/products": 200,
      "/products/{slug}": 404
    },
    "markdownResidueChecked": true,
    "structuredRichTextChecked": true,
    "blockingIssues": [
      {
        "routePattern": "/posts/{slug}",
        "code": "literal_bold",
        "evidence": "redacted raw Markdown marker"
      }
    ]
  }
}
```

Do not record concrete slugs, page titles, product names, article names, or raw Markdown snippets in this evidence block.

Use `expectedStatuses` to distinguish a release-ready static page from a deliberately absent detail page. A static product landing page returning 200 does not prove `/products/{slug}` is wired; a redacted probe detail route returning expected 404 proves only that no accidental detail content is public yet.

When static launch pages return expected 200 and probe detail routes return expected 404 with no blocking issues, record the result as `read_only_simulation` or phase evidence. Do not claim content upload completion from that audit. Content upload completion still requires an authorized probe or sample item, a captured save request for the exact content type, backend persistence proof, and a real frontend detail route returning expected 200 after publish.

For rich text, inspect DOM nodes, not just visible text:

```text
bold -> <strong> or <b>, no literal ** markers
inline code -> <code>, no literal backticks
links -> <a href="...">
tables -> <table> with rows/cells, not pipe-delimited text
lists -> <ul>/<ol>/<li>, not a flattened bullet string unless that is the intended design
headings -> one primary <h1> unless the active theme intentionally duplicates the title
```

Scope Markdown residue checks to parsed visible text and rendered DOM. Raw source HTML may include framework CSS variants, serialized attributes, or editor class names that contain marker-looking strings; those are diagnostics unless the marker appears in visitor-visible text or a rendered content node.

Treat these as blocking by default after batch upload:

```text
literal_bold
literal_inline_code
literal_markdown_link
literal_markdown_image
literal_pipe_table
jsx_style_object
html_tag_text
http_status
image_missing_src
```

Treat these as warnings that usually need review:

```text
multiple_h1
duplicate_h1_text
missing_h1
image_missing_alt
content_type
```

## Batch Upload Log

Track each item with at least:

```json
{
  "slug": "",
  "contentType": "products",
  "operation": "create|update",
  "backendId": "",
  "saveStatus": "pending|ok|failed",
  "publishStatus": "skipped|pending|ok|failed",
  "backendVerified": false,
  "frontendUrl": "",
  "frontendVerified": false,
  "coverVerified": false,
  "errors": []
}
```

Before browser execution, generate a batch runbook from the schema-verified manifest and the run evidence that already contains persisted request capture plus either merged sample verification or a validated manifest sample evidence file:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_batch_upload_publish_runbook.py \
  --run-evidence ~/allincms-projects/allincms-run-evidence-after-save-capture.json \
  --manifest ~/allincms-projects/allincms-schema-verified-manifest.json \
  --sample-evidence ~/allincms-projects/allincms-products-sample-evidence.json \
  --target https://workspace.laicms.com/example/products \
  --target-identifier "products manifest batch" \
  --authorization-output ~/allincms-projects/allincms-authorization-batch-upload.json \
  --output ~/allincms-projects/allincms-batch-upload-runbook.json
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action batch_upload \
  --preflight ~/allincms-projects/allincms-run-evidence-after-save-capture.json \
  --authorization ~/allincms-projects/allincms-authorization-batch-upload.json \
  --sample-evidence ~/allincms-projects/allincms-products-sample-evidence.json
```

The runbook remains preparation only until the `batch_upload` authorization record exists and the pre-mutation gate passes.

After the batch browser run, validate the evidence before treating the batch as complete:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_batch_upload_publish_evidence.py \
  ~/allincms-projects/allincms-batch-upload-evidence.json \
  --manifest ~/allincms-projects/allincms-schema-verified-manifest.json \
  --base-run-evidence ~/allincms-projects/allincms-run-evidence-after-publish-sample.json \
  --frontend-audit-report ~/allincms-projects/allincms-final-audit-report.json \
  --output ~/allincms-projects/allincms-batch-upload-validation.json
```

The validator requires the manifest schema gate, base sample verification, complete progress log, matching backend/frontend URL prefixes, `bodyVerified: true` for every item, and an empty redacted frontend detail audit issue list. A backend progress log without a DOM/rich-text audit does not unlock final QA or cleanup.

For source-package runs, apply the batch evidence back into the source execution dashboard after validation:

```bash
python3 skills/allincms-bulk-content-upload/scripts/apply_batch_upload_publish.py \
  --batch-evidence ~/allincms-projects/allincms-batch-upload-evidence.json \
  --manifest ~/allincms-projects/allincms-schema-verified-manifest.json \
  --base-run-evidence ~/allincms-projects/allincms-run-evidence-after-publish-sample.json \
  --frontend-audit-report ~/allincms-projects/allincms-final-audit-report.json \
  --package ~/allincms-projects/allincms-run/source-site-package.json \
  --confirmation ~/allincms-projects/allincms-run/execution/confirmation-record.json \
  --execution-plan ~/allincms-projects/allincms-run/execution/confirmed-site-execution-plan.json \
  --artifact-readiness ~/allincms-projects/allincms-run/execution/confirmed-artifacts/artifact-readiness.json \
  --created-site-binding ~/allincms-projects/allincms-run/created-site-schema-capture/created-site-artifact-binding.json \
  --pages-site-info-handoff ~/allincms-projects/allincms-run/created-site-schema-capture/pages-site-info/pages-site-info-browser-handoff.json \
  --pages-site-info-validation ~/allincms-projects/allincms-run/pages-site-info-applied/pages-site-info-execution-validation.json \
  --schema-capture-handoff ~/allincms-projects/allincms-run/created-site-schema-capture/schema-capture-handoff.json \
  --upload-readiness ~/allincms-projects/allincms-run/upload-readiness.json \
  --sample-evidence ~/allincms-projects/allincms-products-sample-evidence.json \
  --output-dir ~/allincms-projects/allincms-run/batch-applied
```

The apply helper writes a batch validation report, a batch progress log artifact, and `source-execution-status.after-batch-upload.json`. A standalone `validate_batch_upload_publish_evidence.py` pass proves the batch evidence shape; it does not by itself update the source-package execution boundary. Follow the refreshed `currentStage`; only `forms_media_settings` means batch proof has been accepted and the next gate is site-info/forms/media/domains/tracking proof or explicit deferral. Do not jump from batch proof directly to launch acceptance.

Keep the batch manifest, progress log, backend verification, and frontend audit bound to the same slug set. If the manifest still names an earlier demo item while the browser created a different batch item, the batch evidence must fail until the manifest is corrected or the actual manifest item is uploaded. Each progress row must include explicit `saveStatus: ok` and `publishStatus: ok` when the item should be public.

Product detail publication and product list visibility are separate checks. A site may have a static `/products` marketing page that returns 200 with images and links but does not render CMS product cards. In that case, product detail URLs can still prove content upload/publish, while list-page launch acceptance must either add/verify a CMS products list block or explicitly accept the static list page behavior.

When a product slug changes during save/publish, treat frontend verification as a two-step check. The list route may update first while the new detail URL briefly returns 404. If the backend row is published and `/products` links to the new slug, retry the detail URL after a short bounded delay. Do not mark the product broken from the first immediate 404, but also do not mark it verified until the detail URL renders the expected H1/body/media state.

If the CLI frontend auditor reports `fetch_failed` for a route that is browser-visible, use a live browser DOM check as the tie-breaker for current route rendering and keep the CLI result as an audit-tool reliability warning to rerun before final launch. Record both signals. This is especially important for `/posts` and `/posts/{slug}` after recent publish operations.

Default-theme template residue is a launch blocker even when all target content details render. Check static pages, header, footer, CTAs, category labels, recommended-product blocks, contact details, copyright, and social links for generic template brand/copy. If residue remains, report the site as structurally working but not launch-ready.

For designer-generated page rewrites, verify residue at the public page level after publishing, not just in the designer chat history or generated action log. A generated page can show `update-block Done` and publish successfully while product category chips, FAQ copy, contact address blocks, team blurbs, or lower-page sections still contain default-template text.

Taxonomy-chip residue is separate from page-copy residue. If product or post cards/details still show wrong category or tag chips after titles, excerpts, bodies, and static page headings are correct, inspect the backend category/tag tabs and content associations instead of repeatedly editing the page designer. Final QA should include old category/tag names in the public DOM residue scan, then verify replacements on both list pages and detail pages.

For contact pages, final QA must explicitly check both visible contact placeholders and functional form state. A page with good B2B copy but unresolved embedded form text is not launch-ready. If real form setup is out of scope, hide the form block and verify the public page has no unresolved form message; keep a gap ledger entry for the required form fields, notification email, consent text, and binding behavior.

Contact residue can live outside the public contact page. Scan every launch route for old email, phone, address, hours, brand, and CTA text across header, footer, page-level contact blocks, global contact dialogs/modals, floating buttons, newsletter blocks, and editorial/recommended sections. Select the exact designer layer that owns the residue before editing; a global modal shell may not own the page-level address block that appears near it.

When verifying recently changed global blocks such as footer, header, navigation, contact dialog, or social links, reload the public route before treating visible residue as current state. A previously open frontend tab can retain an old global block instance after a designer publish. If the first read shows old labels or links, capture the stale signal, reload the same route once, and re-check visible text plus anchors. Treat residue as active only when it survives the reload or appears in a freshly opened tab; otherwise record it as stale-tab evidence, not a new launch blocker.

Product specifications need their own placeholder check. A product title, description, body, category chip, and image can all be domain-correct while the detail page still shows default template spec rows such as unrelated material, zipper, tray, bag, or care fields. Treat non-domain spec terms as launch blockers until the current product spec edit/save schema is captured or an explicit no-spec acceptance rule is recorded.

Do not flatten captured schema proof just to satisfy a helper. `requestCapture.headers`, `payloadShape`, `contentBlockShape`, `idFields`, and `sampleVerification.renderAudit` may be structured arrays or objects in run evidence. Upload-scope gates should require non-empty evidence values while still checking URL, method, site key, and frontend route ownership.

## Cleanup Search Terms

After probing or failed attempts, search and clean:

```text
Codex Probe
Test API Probe
UI Request Probe
Untitled Post
Untitled Product
Delete Me
random numeric slugs
```

Cleanup changes remote state. Before deleting or unpublishing anything, record the candidate title/name, content type, status, backend URL, and the reason it is safe to remove. Ask for explicit cleanup authorization unless the user's current instruction already authorizes deleting those exact entries.

For probe cleanup, prefer the dedicated `cleanup_probe` action and gate:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action cleanup_probe \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-cleanup-product-probe.json
```

Do not use a previous create, save, publish, upload, or generic cleanup authorization as permission to delete or unpublish a probe.

Confirm cleaned frontend URLs return 404 or no longer render the probe item.

After sample verification is merged and `summarize_run_status.py` emits `authorize_cleanup_probe`, build a cleanup runbook before touching the browser:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_probe_cleanup_runbook.py \
  --run-evidence ~/allincms-projects/allincms-run-evidence-after-publish-sample.json \
  --authorization-output ~/allincms-projects/allincms-cleanup-probe-authorization.json \
  --output ~/allincms-projects/allincms-cleanup-probe-runbook.json
```

The runbook is local preparation only. It must retain the authorization placeholder and `browserStepsExecutable: false` until the `cleanup_probe` authorization record exists and the cleanup gate passes. The only gated mutation is deleting or unpublishing the Codex Probe item; cleaning real business content, upload, batch, replay, or a second cleanup action remain forbidden.

After the cleanup browser run, validate and merge cleanup proof:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_probe_cleanup_evidence.py \
  ~/allincms-projects/allincms-cleanup-evidence.json \
  --base-run-evidence ~/allincms-projects/allincms-run-evidence-after-publish-sample.json \
  --merge-args-output ~/allincms-projects/allincms-cleanup-merge-args.json \
  --output ~/allincms-projects/allincms-cleanup-validation.json
python3 skills/allincms-bulk-content-upload/scripts/merge_probe_evidence.py \
  --base ~/allincms-projects/allincms-run-evidence-after-publish-sample.json \
  --cleanup-evidence ~/allincms-projects/allincms-cleanup-evidence.json \
  --output ~/allincms-projects/allincms-run-evidence-after-cleanup.json
python3 skills/allincms-bulk-content-upload/scripts/summarize_run_status.py \
  ~/allincms-projects/allincms-run-evidence-after-cleanup.json \
  --output ~/allincms-projects/allincms-run-summary-after-cleanup.json
```

Cleanup evidence normally includes a non-empty `cleanedCandidates` list whose `titlePattern` includes `Codex Probe - Delete Me`, `cleanedCount` matching the list length, backend proof that the probe is absent/unpublished, frontend proof that the detail route no longer renders probe content, and the same base `siteKey/contentType` as the run evidence.

If a fresh cleanup scan finds no probe/test candidates, do not create a new probe just to delete it. Record absence proof instead: `status: "verified"`, `cleanedCount: 0`, `cleanedCandidates: []`, `noCandidatesVerified: true`, `backendVerified: true`, `frontendVerified: true`, and a non-empty `scannedSurfaces` list covering the relevant backend lists and public routes. This proves cleanup has no current work; it does not replace request capture, sample verification, manifest schema, or batch upload proof.

When cleanup proof is supplied as JSON, preserve `cleanedCandidates` as an array through merge helpers. Delimited strings such as `contentType|titlePattern|backendUrl|reason` are only for manual CLI input; do not convert structured cleanup evidence through comma-separated strings because normal `reason` text may contain commas.

## Final Report

Report:

- Site and content type.
- Backend and frontend route templates verified.
- Field mapping summary.
- Request capture summary without secrets.
- Sample upload result.
- Batch counts: created, updated, published, skipped, failed.
- Failed slugs and exact failure stage.
- Cleanup result.
- Frontend list page left open for the user.
