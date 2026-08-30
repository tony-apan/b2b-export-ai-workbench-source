---
doc_id: allincms-bulk-launch-acceptance
title: AllinCMS 上线验收契约
description: 从创建站点到可上线网站的完整验收门槛、证据和阻塞条件
layer: ops
status: draft
created: 2026-06-30
updated: 2026-07-02
page_type: reference
sources: []
confidence: medium
---

# Launch Acceptance

Use this reference before claiming an AllinCMS / LAICMS site-build run is complete, especially when the user asked to "从创建网站开始", "一遍推完", "能上线的网站", "最终 QA", or "实操所有功能".

## Completion Definition

A complete from-scratch launch is proven only when all of these are true in current, redacted run evidence:

```text
1. site_created_and_verified
2. setup_pages_read_only_inspected
3. module_interface_capture_complete
4. theme_route_launch_ready
5. static_frontend_routes_render
6. content_type_save_request_captured_and_persisted
7. sample_backend_frontend_verified
8. manifest_schema_gate_passed
9. batch_upload_publish_verified
10. forms_media_settings_verified_or_explicitly_out_of_scope
11. final_frontend_audit_passed
12. probe_cleanup_completed
13. skill_sedimentation_completed_or_readonly_exception_recorded
```

Do not use a green local rehearsal, a published sample probe, or a passing static route audit as proof that the website is launch-complete. Those are phase evidence only.

Official tutorial alignment for first launch:

```text
Backend saved is not enough; open the public frontend and click as a real visitor.
Default template content should be edited/replaced before creating duplicates.
Frontend 404 or blank blocks content expansion until theme/homepage/route state is fixed.
Product/category/news homepage modules should be checked only after real categories/products/posts exist.
Extra pages are complete only after route, page binding, enabled state, frontend route, and menu/button links are verified.
```

Load `official-docs-alignment.md` for the current official-docs checklist. This launch contract is the proof gate; the docs-alignment reference is the operating route map.

Before claiming completion, run the executable gate:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_launch_acceptance.py \
  --require-created-site \
  --run-evidence ~/allincms-projects/allincms-run-evidence.json \
  --module-coverage ~/allincms-projects/allincms-module-coverage.json \
  --upload-readiness ~/allincms-projects/allincms-upload-readiness-report.json \
  --batch-evidence ~/allincms-projects/allincms-batch-upload-evidence.json \
  --batch-validation ~/allincms-projects/allincms-batch-upload-validation.json \
  --forms-media-settings ~/allincms-projects/allincms-forms-media-settings.json \
  --final-frontend-audit ~/allincms-projects/allincms-final-frontend-audit-stage-result.json \
  --cleanup-evidence ~/allincms-projects/allincms-probe-cleanup-evidence.json \
  --round-closeout ~/allincms-projects/allincms-round-closeout.json
```

If only stage coverage, launch plan, browser execution plan, or rehearsal artifacts exist, this gate should fail. Use the failure report as the next live-evidence checklist instead of softening the launch claim.

The `--round-closeout` artifact for launch acceptance must be a run closeout, not an `allincms_round_maintenance_summary`. Maintenance closeout proves only skill sedimentation for a local turn. Launch acceptance requires `valid=true`, `complete=true`, no `completionGaps`, non-local run proof, accepted sedimentation status, and proof that mentions launch, frontend, and cleanup.

For source-file driven runs, apply the launch gate result back into the local source execution dashboard:

```bash
python3 skills/allincms-bulk-content-upload/scripts/apply_launch_acceptance.py \
  --require-created-site \
  --run-evidence ~/allincms-projects/allincms-run-evidence.json \
  --module-coverage ~/allincms-projects/allincms-module-coverage.json \
  --upload-readiness ~/allincms-projects/allincms-upload-readiness-report.json \
  --batch-evidence ~/allincms-projects/allincms-batch-upload-evidence.json \
  --batch-validation ~/allincms-projects/allincms-batch-upload-validation.json \
  --forms-media-settings ~/allincms-projects/allincms-forms-media-settings.json \
  --final-frontend-audit ~/allincms-projects/allincms-final-frontend-audit-stage-result.json \
  --cleanup-evidence ~/allincms-projects/allincms-probe-cleanup-evidence.json \
  --round-closeout ~/allincms-projects/allincms-round-closeout.json \
  --package ~/allincms-projects/allincms-run/source-site-package.json \
  --confirmation ~/allincms-projects/allincms-run/execution/confirmation-record.json \
  --execution-plan ~/allincms-projects/allincms-run/execution/confirmed-site-execution-plan.json \
  --artifact-readiness ~/allincms-projects/allincms-run/execution/confirmed-artifacts/artifact-readiness.json \
  --created-site-binding ~/allincms-projects/allincms-run/created-site-schema-capture/created-site-artifact-binding.json \
  --pages-site-info-handoff ~/allincms-projects/allincms-run/created-site-schema-capture/pages-site-info/pages-site-info-browser-handoff.json \
  --pages-site-info-validation ~/allincms-projects/allincms-run/pages-site-info-applied/pages-site-info-execution-validation.json \
  --schema-capture-handoff ~/allincms-projects/allincms-run/created-site-schema-capture/schema-capture-handoff.json \
  --sample-evidence ~/allincms-projects/allincms-products-sample-evidence.json \
  --output-dir ~/allincms-projects/allincms-run/launch-acceptance-applied
```

The apply helper is local-only. It writes `launch-acceptance-validation.json`, `source-execution-status.after-launch-acceptance.json`, and a summary. If the launch gate is invalid, the source execution dashboard must stay blocked at `launch_acceptance`; do not mark the source-file-to-site run complete from a failed validation report.

The source execution dashboard may pass `launch_acceptance` only when the launch validation has both `valid=true` and `complete=true`. A partially green validation, such as `valid=true` with `complete=false` or `complete=true` with `valid=false`, must remain blocked at `launch_acceptance` and keep the full source-file-to-live-site objective incomplete.

For source execution status, `forms_media_settings` is a separate stage between `batch_upload` and `launch_acceptance`. Batch evidence can prove content upload/publish, but it must not mark the website launch-ready until forms/media/settings evidence exists and passes, or each missing sub-area has an explicit deferral.

For source-file driven final acceptance, counts are part of the contract. The final source-run acceptance must compare `contentGoalCoverage.counts.pages/products/posts` from the confirmed source package with the final proof artifacts: pages/site-info validation must expose `pageCount`, and each posts/products batch validation must expose `manifestItemCount` or `progressCount`. A run with one verified sample or one partially validated batch must remain incomplete when the confirmed plan contains more pages, products, or posts.

Structure counts are also part of the final proof. When the confirmed package includes navigation, taxonomy terms, forms, or media, final acceptance must require explicit proof counts instead of inferring them from nearby content:

```text
navigationItems -> final frontend audit navigationItemCount
productCategories/postCategories/productTags/postTags -> taxonomy execution validation taxonomyMappingCount
contentCounts.forms -> forms/media/settings evidence formCount, unless forms are explicitly deferred
contentCounts.media -> forms/media/settings evidence mediaCount/uploadedMediaCount/verifiedMediaCount, unless media is explicitly deferred
```

Do not treat page count as navigation proof, product/post category labels as backend taxonomy proof, or a media policy note as public media proof. These structures must either expose matching counts in final evidence or carry explicit accepted deferrals.

Use the generated evidence scaffolds to produce these fields instead of hand-patching final inputs: forms/media/settings bundles should expose `formCount`, `mediaCount`, and `verifiedCounts`; final frontend audit stage results should copy `navigationItemCount` from final audit inputs when available.

Scattered browser evidence or an evidence index is diagnostic only. A current final frontend audit, form request capture, media dialog probe, and launch-gap summary can prove useful phase facts, but they do not replace the required run-evidence chain, module coverage, batch evidence, forms/media/settings evidence, final frontend stage result, cleanup evidence, and round closeout. Before running `validate_launch_acceptance.py`, either assemble the required artifacts through the documented helpers or explicitly report that formal launch acceptance cannot yet be evaluated.

## Stage Evidence

| Stage | Required evidence | Blocks launch if missing |
|---|---|---|
| Site creation | Created site key, site card, backend dashboard, frontend origin, module routes | Existing-site evidence when the goal was from-scratch |
| Setup inspection | `site-info`, `domains`, `themes`, `routes`, `forms`, `tracking` read-only proof | Unknown settings/forms/routes before mutation |
| Module interface capture | Per-action capture coverage or explicit UI-first block for products, posts, media, routes, forms, settings | One captured action treated as all modules captured |
| Theme/page/route beautification | Saved design, published page, enabled page, active theme, bound route, HTTP/DOM proof | Page row exists but design blank, disabled, unbound, or frontend 404 |
| Static frontend audit | Expected static routes, status map, DOM/rich-text/image findings | Static routes inferred from another site or route type |
| Save request capture | Current-site payload template, field mapping, non-empty body schema when required, backend persistence | HTTP 200 without persistence, empty body schema, or post/product schema reuse |
| Sample verification | Backend published state and public detail URL with title/name, body, cover/media proof | Sample published but body/media/list/detail proof missing |
| Manifest schema gate | Generic validation and `--require-schema-verified` pass for each manifest/content type | Draft manifest validation only |
| Batch upload/publish | Progress log for every slug, backend/frontend verification, duplicate-slug handling, frontend detail audit | Partial progress log or some details unverified |
| Source-run final counts | Confirmed `contentGoalCoverage.counts` matched by page and batch validation counts | Sample-only proof or fewer uploaded/published records than the confirmed content plan |
| Forms/media/settings | Action-specific request/backend proof and public/integration effect when relevant | Group stage marked complete from one settings request |
| Final frontend audit | URL/status inputs from manifest + progress log, complete audit report, no blocking issues | Hand-maintained URL list or missing route/media/body check |
| Cleanup | Authorized probe cleanup, backend absence/unpublished proof, frontend non-public proof | Cleanup candidate listed but not verified |

Launch acceptance must reopen the final frontend audit's direct evidence. A `final_frontend_audit` stage result is not enough by itself; it must point to the redacted audit report JSON, audit-inputs summary, and expected-status map. The launch gate must re-run the same report/coverage checks used by final audit stage generation: HTTP status, DOM/rich-text issues, image issues, route counts, route instances, and URL fingerprints for concrete detail routes. A hand-written `status=completed` stage result must remain blocked when the underlying report, expected statuses, or URL fingerprints are missing or inconsistent.

## Beautification Gate

Treat `theme_page_route_launch` as incomplete until the full chain is proven:

```text
theme active
page design saved with non-empty blocks
page published
page enabled
route bound to the intended page
frontend HTTP status matches expected status
frontend DOM contains the intended heading/body/media/CTA structure
mobile and desktop visual sanity checked when a public launch claim is made
```

Creating a theme, creating a page row, or seeing `已发布` is not enough. Product/post detail routes may require a dynamic child theme page such as `/products/{product}` plus route binding and a rendered detail page.

## Forms, Media, And Settings Gate

Do not mark `forms_media_settings` complete because one sub-action was captured. The run must either prove each in-scope sub-action or record an explicit out-of-scope decision:

```text
site-info public metadata saved and verified
forms created/edited and submission behavior or destination policy verified
media upload or public URL behavior verified
domains/DNS state recorded or explicitly deferred
tracking tag state verified or explicitly deferred
favicon/logo/nav/footer/contact details verified or explicitly deferred
```

Mixed evidence is valid when each missing boolean has a matching explicit deferral. For example, a temporary demo site may prove `siteInfoVerified`, `formsVerified`, and `domainsRecorded`, while deferring `media` because upload storage/public URL proof requires a file-selection-capable browser session, and deferring `tracking` because no Google Tag ID was supplied. Do not force the whole stage to `explicitly_out_of_scope` when part of the stage was actually verified; use a partial status such as `partially_verified_with_explicit_deferrals`, keep verified booleans true, and include `deferrals[]` with module names and reasons for each false sub-item.

AllinCMS media upload is canonical-adapter-first. Acceptance requires the adapter's exact-site runtime proof, verified media record, public URL and image decode proof, and private source-hash mapping; simulated clicks or opened dialogs never satisfy media proof. UI selection is an explicitly approved fallback only after adapter contract drift or runtime failure.

## Final QA Checklist

A final launch QA pass must inspect:

```text
homepage
main list pages such as /products or /posts, only when in scope
all static marketing pages in navigation
all uploaded detail URLs from the manifest/progress log
navigation/menu links
CTA links and form entry points
title/name, description/excerpt, body/rich text, cover/media, specs/attributes where expected
raw Markdown residue, broken links, unexpected 404/500, missing images, missing alt/H1 warnings if release-blocking
desktop and mobile layout when visual launch quality is in scope
```

Generate final audit inputs from the schema-verified manifest and complete batch progress log. Do not hand-maintain final detail URL lists.

For a first complete business site, include the official launch checklist fields:

```text
content: no template default copy, no Untitled Product, no Untitled Post, no test/测试 records, true contact details

Enforce the no-template-residue rule with `check_template_residue.py` instead of eyeballing it: capture the old default-template fingerprints as a blacklist before conversion, capture the visible text of every live route after publish, and require zero residue hits. A converted-from-template site otherwise ships old brand / product / category chips / contact info scattered across footer, nav, modals, newsletter, and lower-page sections while the AI reports only "minor residue".
minimum content: 2-3 main product categories, at least 2 representative products per main category, 3 basic posts/articles
navigation: Home, Products, News/Blog, About Us, Contact Us, dropdowns, buttons, footer links, new page links, no unexpected 404s
products/posts: product Detail Page points to /products, post/article detail points to /posts, detail pages open, body not empty, cover/media policy satisfied
forms/contact: footer email/phone are real, mailto/tel links if used, notification email set, test submission done or explicitly omitted
domains: AllinCMS domain row, DNS CNAME, HTTPS access, DNS/SSL wait and status recorded or explicitly deferred
images: logo/favicon, banner, product images, post covers, compression/size policy, no severe crop/blur
mobile: menu, main pages, product detail, post detail, and contact/form entry checked on mobile viewport when public launch quality is claimed
```

When using browser viewport tooling for mobile QA, prove that the viewport actually changed inside the page. Record `window.innerWidth`, `document.documentElement.clientWidth`, and `scrollWidth` for each checked route. If the viewport tool reports success but the page still reads as a desktop width, do not count the pass as mobile proof. Re-run with a tab-level device-emulation mechanism such as CDP `Emulation.setDeviceMetricsOverride`, then clear the override after the check. Mobile evidence should include effective viewport, H1 count, broken image count, horizontal overflow status, mobile navigation button presence, and denylist results.

Any omitted checklist item must be represented as an explicit out-of-scope or user-accepted deferral in the final evidence, not silently skipped.

## Read-Only Sedimentation Exception

The skill normally requires a sedimentation pass every turn. If the user explicitly forbids file edits, do not mutate the skill package. Instead:

```text
1. Complete the read-only review or validation.
2. Report reusable findings in the final answer.
3. State that sedimentation was read-only deferred because edits were forbidden.
4. On the next turn where edits are allowed, record those findings before continuing mutation work.
```

This exception does not apply when edits are allowed. In normal operation, reusable findings must be written into the skill package and closeout must be run before final response.

## Local Rehearsal Interpretation

`run_full_rehearsal.py` and `summarize_rehearsal_stage_coverage.py` prove helper coverage and stage sequencing. They do not prove:

```text
real LAICMS site creation
real theme/page design persistence
real media upload
real content upload/publish
real form submission/integration behavior
real frontend launch quality
real cleanup
```

Use the stage coverage summary to identify which browser evidence must be collected next. Use launch acceptance only after real run evidence, not after local simulation alone.

## New-Site Acceptance Boundary

For a from-scratch or new-site objective, final acceptance must prove that the site was created in this run. `existing_site_selected` evidence and `siteBindingMode=existing_site` are valid only for selected-site continuation. They may support content upload and launch checks on that selected site, but they must not satisfy a "create a new site" completion claim. Run `validate_source_run_acceptance.py` with the current objective text and require it to pass; it rejects existing-site binding for new-site objectives.
