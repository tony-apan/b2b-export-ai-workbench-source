---
doc_id: allincms-bulk-operational-findings
title: AllinCMS 实操问题沉淀
description: LAICMS / AllinCMS 操作中发现的可复用问题、失败模式和收尾沉淀规则
layer: ops
status: draft
created: 2026-06-29
updated: 2026-07-30
page_type: reference
sources: []
confidence: medium
---

# Operational Findings

Use this file at the end of each AllinCMS skill turn: browser operation, local simulation, helper-script edits, request analysis, planning, discussion, interface inventory, validation-only checks, or final QA. Record only reusable platform behavior and operational lessons.

## 2026-07-30 — Shared orchestration must resolve the canonical source root and keep authorization layers separate

- Symptom: shared documentation named one maintainer's absolute checkout path, while the portable sub-library contract used `<SUB_LIBRARY_ROOT>`; the same shared flow also described an eight-hour run grant next to an Adapter that rejects mutation contexts at 30 minutes.
- Cause: orchestration routing and runtime Adapter authority were documented in one local workspace before the sub-library became independently packaged. A package-level intent grant was then easy to misread as request-level authorization.
- Rule: resolve the source root with `scripts/resolve_website_content_ops_root.py`, an exact `--root`, or `WEBSITE_CONTENT_OPS_ROOT`; verify package identity and required Adapter files; reject `dist/`; never add a personal-directory fallback.
- Authorization boundary: the run grant may keep the confirmed orchestration package in scope, but it never satisfies the canonical Adapter. Every article, taxonomy, article-image, or media mutation still needs the exact structured `authorizationContext` with a maximum 30-minute lifetime and immediate pre-request revalidation.
- Enforcement: `scripts/test_resolve_website_content_ops_root.py` checks resolution precedence, fail-closed invalid roots, `dist/` rejection, machine output, absence of the old absolute path, and the explicit two-layer authorization wording.

## 2026-07-27 — Article image save needs a post-readback editor health gate

- Context: an authorized virtual A/B/A article draft used two unique media assets at three Markdown occurrence positions.
- Failure: a plain string `caption` returned HTTP 200 and was visible in backend readback, but the AllinCMS Plate editor then rendered a 500 page.
- Stable rule: every image caption must be a non-empty Slate text-node array; every array entry must be an object with a string `text`. Block strings and mixed arrays before any request.
- Completion gate: HTTP 200 and backend readback are only intermediate evidence. After reload, require the Slate editor, exact article-image count, all images decoded, visible Caption sequence matching the saved Slate content, and a Draft/草稿 badge. Return the observed editor-DOM Alt-missing count as a documented product gap, not as proof that backend Alt failed.
- Retry rule: once the save request may have started, any readback or render mismatch is at-most-once and fail-closed. Reload/read back only; never automatically resend the article update.
- Routing: execute `<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/article-image-binding.mjs` through `AI-START-HERE.md`; do not recapture the interface, globally replace Markdown strings, or handwrite Slate image nodes.
- Audit-proof rule: a self-declared `status: verified` is not media proof. Before binding, require `contractVerified`, `mediaRecordPresent`, `anonymousHttpsGet`, and `browserImageDecodes` to all be true. Position audit compares actual Slate node indexes, and URL/decode counters must be derived from verification evidence rather than hard-coded zeroes. Pre-save audit can validate expected Alt only; `missing_required_alt_in_backend_data` belongs exclusively to post-save backend readback. The mapping must also prove the exact source SHA-256 and start from a candidate carrying the already-known media ID and URL; title-only adoption is forbidden. Immediately before Slate construction, reread local asset bytes serially and reject a stale image manifest. Revalidate the backend readback Caption structure itself, because matching visible text does not make a plain string Caption safe. Article-manifest lock files should record PID, acquisition time, and target manifest path so manual stale-lock review has evidence.

## Invariants (stated once; do not restate per finding)

These platform rules are universal across the skill. Finding blocks below should reference an invariant by name rather than re-deriving it each time; new findings must not paste these restatements.

```text
INV-1 Persistence proof: a save/publish request returning HTTP 200 (or a success toast) is NOT
      persistence proof. Require a backend re-read (isDraft:false + non-empty content) AND the
      public detail route rendering the expected DOM before calling anything persisted/launched.
INV-2 Authorization does not carry: every local prepare/apply/build helper is non-authorizing
      scaffolding. Each remote mutation (create site, save, publish, upload, delete, batch) needs
      its own action-time authorization + check_pre_mutation_gate.py; one authorization never
      carries to the next action, the next content type, or the next site.
INV-3 Read-only recovery is not authorization: loading /sites or a module route, a preflight, or a
      read-only scan is control-surface/auth recovery, not authorization and not state proof.
INV-4 Slate bodies via JSON only: content bodies are Slate node arrays; a UI edit-form save does
      not bind the Slate editor and wipes the body, so body-bearing entities (products/posts) must
      be saved via JSON replay. Gate with validate_slate_content_shape.py.
INV-5 next-action drifts per deployment: Server Action next-action ids are build artifacts; re-capture
      them each run and gate a batch with check_next_action_freshness.py before replay.
INV-6 Append-only ledgers: the source gap/docs ledgers are append-only; only resolved-with-evidence
      entries clear a gap; a plain --write-ledger must not swallow an unresolved diff.
INV-7 Never fabricate: specs, certifications, prices, reviews, a physical address, or contact PII are
      user-supplied; if not in the source, flag needs-user-input or hide the block — never invent.
```

## Sedimentation Rule

Before the final response of every AllinCMS skill turn, perform this check:

```text
0. Which closeout path applies: run-evidence closeout or maintenance closeout?
1. What concrete problems, surprises, failures, command drift, unsafe assumptions, or validation gaps appeared in this turn?
2. Are any of them reusable for future LAICMS / AllinCMS site-building work?
3. If yes, update this file and any specific reference affected by the finding.
4. If no, do not add filler; state in the final response that no reusable skill update was needed after checking.
5. If any skill file changed, run skill hygiene and quick validation before claiming the turn is complete.
6. Run `scripts/check_round_closeout.py` against the current run summary before the final response so the sedimentation outcome is explicit.
7. Pass at least one `--round-issue` item to both the maintenance summary builder and the closeout gate. Use it for reusable findings, command drift, validation gaps, or the explicit observation that no reusable update was needed after checking.
```

Update this skill when the turn reveals any of these:

```text
new request URL, method, header, or payload shape
new field name, required field, or field mismatch
new save, publish, enable, bind, upload, delete, or cleanup behavior
new frontend verification failure mode
new browser-control limitation, stale evidence, or login/session issue
new local simulation mismatch with the intended real workflow
new helper-script flag, output, or command example drift
new UI behavior that is safer than JSON, or JSON path that is safer than UI
new authorization boundary or destructive-action risk
new validation command, check, or stop condition
```

Do not record:

```text
temporary business copy
private account names, emails, cookies, tokens, or credentials
raw object IDs unless they are converted to placeholders
site-specific content strategy that is not platform behavior
one-off navigation history with no reusable lesson
```

## Problem Recording Contract

Each AllinCMS skill turn must leave one of two states before final response:

```text
updated = at least one reusable problem or platform behavior was recorded in this skill package
none    = the operator checked the turn and found no reusable skill update needed
```

Use `updated` for local-only changes too, not only live browser mutations. Examples: a simulator uncovered stale summary semantics, a validation command in the docs was wrong, a helper allowed an unsafe stage, or browser evidence needed redaction. Use `none` only after checking actual turn evidence, not as a default.

For a reusable problem, record the smallest neutral lesson that prevents future errors. Keep raw run logs, business copy, account labels, object IDs, and temporary site details out of the skill.

## 2026-07-03 Source Review Objective Coverage Propagation Finding

- Context: `sourceReviewObjectiveCoverage` (from `make_source_review_objective_coverage.py`) was generated and validated at rehearsal/confirmation-brief time, but the confirmed execution chain did not carry it, so a locally review-complete package could be read as a live target completion once confirmation was applied.
- Symptom: after user confirmation, the confirmation record, execution plan, artifact readiness, source execution status, and next-stage handoff exposed `contentGoalCoverage`, `contentQualityReview`, `wikiReview`, and overages, but nothing preserved the pre-browser objective checklist that keeps `complete=false`/`remoteMutationAllowed=false` visible. Downstream readers had no single carried object proving "review done, live objective still open."
- Evidence: `make_source_package_confirmation.py` and `prepare_confirmed_site_execution.py` now accept `--source-review-objective-coverage`; `run_source_file_rehearsal.py` wires the rehearsal's `source-review-objective-coverage.json` into confirmed execution automatically. `content_goal_coverage_utils.py` grew `matching_source_review_objective_coverage`, and `validate_source_package_confirmation.py` grew the base `validate_source_review_objective_coverage`. A full rehearsal now shows the identical coverage object in confirmation, plan, readiness, status, and next-stage handoff; regression tests prove that a plan claiming `complete=true`, a confirmation claiming `remoteMutationAllowed=true`, a review-packet/package binding mismatch, and a plan that drops the coverage while the confirmation keeps it are all rejected.
- Risk: without a carried, drift-checked coverage object, a resumed operator (or a copied artifact) can treat local review readiness as the finished website objective and skip live site creation/selection, schema capture, sample/batch upload, launch, cleanup, and closeout.
- Rule: when coverage is generated, carry it through the confirmed execution chain. Every stage must keep `reviewComplete=true`, `complete=false`, `remoteMutationAllowed=false`, empty `missingForReview`, and the four live blockers in `missingForFinal`, and must bind to the same package/review packet. Treat any drift as a stale-artifact boundary and rebuild from the confirmation record. The coverage is optional end-to-end (older callers and simulators omit it), but once present it may not be dropped or mutated downstream.

## 2026-07-03 Coverage Drift Monitor Silent-Drop Finding

- Context: adversarial re-review of the just-shipped `sourceReviewObjectiveCoverage` propagation, specifically whether "rejected downstream if dropped" actually held on every consumer.
- Symptom: `summarize_source_execution_status.py` — the intended whole-chain drift monitor — did NOT catch the asymmetric case where the confirmation carries coverage but the execution plan and artifact readiness silently drop it. `matching_source_review_objective_coverage` only compared artifacts that already carried coverage; with a single carrier it never flagged a mismatch, and the status even re-echoed the confirmation's coverage, masking the drop. `export` caught it via a bespoke check, but the status dashboard and `prepare_source_next_stage` propagated the masked value.
- Evidence: a probe using the status test fixtures (confirmation carries coverage; plan.json and artifacts.json drop it) returned `source_package: passed`, `currentStage: create_site_handoff`, `sourceReviewObjectiveCoverageIssues: []`. The sibling matchers `matching_created_site_submitted_values` and `matching_content_goal_overages` already had "required when present in source context" logic (`labels_with_data`); the coverage matcher lacked it. Two more latent issues surfaced: downstream validators only required `reviewPacket`/`sourcePackage` be non-empty (never re-bound to the artifact's own package/packet), and cross-artifact equality compared the whole object including the volatile `generatedAt`, which would false-positive on any regeneration.
- Risk: a hand-edited or regenerated artifact could quietly lose the objective coverage while the status report still showed a clean, review-complete coverage — exactly the "local review mistaken for live completion" failure the field was added to prevent.
- Rule: a drift monitor must fail on omission, not only on mutation. When a matcher enforces cross-artifact consistency, give it "required in every present source-context artifact once any carries it" semantics (mirror `matching_created_site_submitted_values`), re-bind carried path references to the hosting artifact's own package/review packet, and exclude generation-stamped fields (`generatedAt`) from equality. Regression-test the drop case, not just the presence and the mutation cases.

## 2026-07-03 PicGo Media Upload And Auto-Run Boundary Finding

- Context: user asked for the skill to "auto-run", auto-convert files to Markdown, and push local body images to an online host via PicGo (127.0.0.1) then replace local links with hosted URLs.
- Symptom: two capability gaps and one expectation mismatch. (1) Extraction produced plain-text content blocks, not Markdown, and there was no image-upload/link-rewrite step anywhere. (2) A plain-text brief did not auto-reach review-ready even with `--auto-draft-refined-source-wiki`: the heuristic extractor mis-classified `## Products / ### Item` structure (real products became posts, product slot held a placeholder "Draft Product" with 58-char copy), producing publication-gate failures (`products_present_without_product_categories`, `short_product_copy`, placeholder/review wording).
- Evidence: `run_source_file_rehearsal.py` on a synthetic multi-section brief returned `reviewReady=false readyForBrowserStage=needs_source_wiki_refinement`; the refinement plan produced 8 `needs_source_backed_rewrite` items. A new helper `upload_media_via_picgo.py` was added: it scans an `allincms_source_wiki` for local image refs (`media[]`, `mediaNeeds`, Markdown `![](path)` in body), POSTs to the PicGo local server, rewrites links to hosted URLs, and writes an `allincms_media_upload_map`. It defaults to `--dry-run` and requires `--confirm-upload` for a real (external, public) upload; it never touches AllinCMS (`allincmsRemoteMutationsPerformed=false`).
- Risk: treating "auto-run" as zero-AI would ship placeholder/miscategorized content to a live site; treating PicGo upload as a local no-op would silently publish unapproved images to a public host; conflating the PicGo external upload with the AllinCMS mutation gates would bypass the real create/save/publish authorization.
- Rule: the deterministic spine (extract -> wiki -> package -> confirm -> confirmed execution -> browser) is single-command, but the AI content-refinement pass is irreducible — meeting publication gates (classification, non-placeholder source-backed copy, copy length, categories, per-article distillation, image placement) is content generation, not extraction. Run PicGo upload as a separate, `--confirm-upload`-gated step after the user approves media and before package confirmation, then feed the rewritten hosted-URL wiki downstream. Never treat the external image upload as an AllinCMS mutation or as authorization for one.

## 2026-07-03 Chrome Fallback Is Control-Plane Only Finding

- Context: the SKILL.md Chrome fallback rule allows switching to Chrome when the in-app browser cannot be controlled, but this can be misread as "Chrome is available, so remote mutation is ready."
- Symptom: a reachable Chrome tab (or a previously opened deep link) can look like a continuation path even when the session is logged out or pointed at the wrong site key.
- Evidence: prior findings already recorded Chrome landing on `workspace.laicms.com/sign-in` and stale deep links surviving a logout; the fallback only restores a controllable surface, not authorization.
- Risk: preparing or running a create/save/publish/upload action on a Chrome fallback surface without re-proving auth and site key can mutate the wrong site or fail mid-action.
- Rule: Chrome fallback resolves browser control-plane problems only. Before any create/save/publish/upload, first prove in Chrome that `/sites` or the exact target module route loads with a valid login state and correct site key, then still run the action-specific authorization and pre-mutation gate.

## 2026-07-03 Source Status CLI Continuation Finding

- Context: estimating remaining time after a source-file rehearsal summary had already been produced and the run was blocked on create-site read-only preflight.
- Symptom: `summarize_source_execution_status.py` was easy to misuse as if it accepted an existing top-level rehearsal summary as a positional input. The helper actually requires explicit source artifacts such as `--package`, `--review-packet`, `--confirmation`, `--execution-plan`, and a required `--output` path.
- Evidence: running `python3 skills/allincms-bulk-content-upload/scripts/summarize_source_execution_status.py /tmp/.../source-file-rehearsal-summary.json` returned an argparse error requiring `--output`. The valid continuation surface for a confirmed source rehearsal is the current rehearsal summary plus the stage-specific apply or next-stage helper, not a positional status refresh.
- Risk: after context compaction, an operator can waste time retrying a status helper with the wrong contract, or hand-derive stage readiness from memory instead of using the indexed continuation artifacts in the rehearsal summary.
- Rule: do not use `summarize_source_execution_status.py` as a generic summary reader. For quick progress reports, inspect the top-level rehearsal summary fields or use a stage-specific helper such as `apply_create_preflight_to_source_rehearsal.py`; use `summarize_source_execution_status.py` only when rebuilding a status file from explicit artifact paths and an explicit `--output`.

## 2026-07-03 Created-Site Evidence Continuation Findings

- Context: real source-file-to-site continuation after `/sites` preflight, gated create-site submit, backend/frontend verification, and created-site evidence apply.
- Symptom: `validate_run_evidence.py` was easy to call with `--json` because many newer helpers support that flag. The validator currently accepts only the evidence path; adding `--json` fails even when the evidence file is valid.
- Evidence: `make_create_preflight_evidence.py` wrote valid preflight evidence, then `validate_run_evidence.py <preflight> --json` failed with `unrecognized arguments: --json`; rerunning without `--json` passed. Later created-site evidence validation also passed without `--json`.
- Risk: command drift after context compaction can make operators suspect the evidence is bad, or skip validation because the command wrapper failed for an unsupported flag.
- Rule: use `validate_run_evidence.py <evidence>` with no `--json` unless the script itself is updated and tested to support that flag. Do not infer validator flags from neighboring helpers.

- Context: read-only `/sites` scanning immediately before the create-site submit.
- Symptom: a browser `evaluate()` scan tried `document.querySelectorAll('.group/card, [class*="group/card"]')`. The slash in the class selector made the selector invalid and the script failed before any click or submit.
- Evidence: the browser returned `SyntaxError: Failed to execute 'querySelectorAll' ... '.group/card, [class*="group/card"]' is not a valid selector.` The retry used text/domain based scanning and the gated submit then created exactly one new site.
- Risk: Tailwind or framework-generated class names can contain characters that require CSS escaping. A failed pre-submit scan can be mistaken for a create failure or can encourage brittle selector escalation.
- Rule: for broad read-only AllinCMS card scans, prefer domain/text/route extraction or properly escaped selectors over raw class selectors copied from rendered class names. If a scan fails before a submit click, explicitly record that no remote mutation occurred before retrying.

- Context: applying post-create evidence into the source-file rehearsal chain.
- Symptom: writing the upgraded `allincms_created_site_browser_evidence` JSON directly to `created-site-evidence.filled-template.json` failed the bundle applier. The applier expects the bundle's fill-template contract, including `kind=allincms_created_site_browser_evidence_fill_template`, gate status, concrete authorization record path, stop condition, forbidden-neighbor proof, and source-context mirrors.
- Evidence: `apply_created_site_evidence_to_source_rehearsal.py` rejected the wrong file with missing fill-template fields and source-context mismatches. Rebuilding the filled template from `created-site-evidence.template.json` and updating only concrete browser-proof fields succeeded, advanced the source chain to `pages_site_info_execution`, and preserved submitted name/description.
- Risk: operators can confuse final run evidence with a fill-template, overwrite the wrong local artifact, lose source-context continuity, or bypass the validator that protects submitted site values and content-count hashes.
- Rule: after a gated create-site submit, fill the prepared `created-site-evidence.template.json`; do not replace it with output from `make_created_site_evidence.py`. Let `apply_created_site_evidence_bundle.py` or `apply_created_site_evidence_to_source_rehearsal.py` write final created-site evidence.

- Context: newly created AllinCMS site from the default create-site flow.
- Symptom: the site was not empty. Dashboard showed a Default active theme, 7 published pages, 3 published products, 3 published posts, and 1 published form. The frontend root rendered nonblank starter commerce content while using the submitted site title.
- Evidence: the new backend dashboard exposed module routes for dashboard, products, posts, media, themes, routes, forms, site-info, tracking, and domains. The public root loaded generic starter commerce copy, images, product detail links, and post links under the new site domain.
- Risk: nonblank frontend, published route counts, or default products/posts can be mistaken for source-package completion. Batch upload or launch QA can then compare source content against starter content or duplicate default records.
- Rule: immediately after site creation, treat default pages/products/posts/forms as starter content to map, overwrite, or explicitly clean up. A new-site run is not content-complete until frontend proof shows source-confirmed content present and starter-template signals absent.

- Context: deriving concrete theme/page targets for page beautification after created-site binding.
- Symptom: the page/site-info handoff correctly used placeholders such as `{themeId}` and `{pageId}` until the real theme pages were inspected. Direct authorization of `save_design` with placeholders would be unsafe.
- Evidence: read-only theme navigation exposed a concrete Default theme ID; opening the Home design page exposed a concrete `/{siteKey}/themes/{themeId}/{pageId}/design` URL, nonzero preview iframe dimensions, and disabled Save/Publish before edits.
- Risk: page design actions can be authorized against placeholder URLs or stale default-page assumptions, making save/publish evidence unbound to a real page.
- Rule: before any theme/page mutation, collect a read-only concrete theme/page target map. Authorization records for `save_design`, `publish_design`, `enable_theme_page`, or `bind_route` must use concrete URLs and target identifiers, not `{themeId}` or `{pageId}` placeholders.

## 2026-07-03 Browser Surface Readiness Gate Finding

- Context: Chrome was available as a fallback browser surface, but the current AllinCMS Chrome tab was on `workspace.laicms.com/sign-in`; the in-app browser had only public frontend tabs and no live backend designer tab to continue page design.
- Symptom: a visible Chrome tab or previously opened designer URL can look like a possible continuation path even when it is unauthenticated. Separately, an in-app designer surface can open but expose a zero-size preview frame, stay on `Render canvas...`, or leave save/publish controls disabled.
- Evidence: `validate_browser_surface_readiness.py` now consumes a redacted browser observation JSON and returns `blocked_login_required`, `blocked_browser_surface`, `ready_for_readonly`, or `ready_for_mutation_preparation` without granting authorization. Regression tests cover Chrome sign-in, in-app zero-width designer, valid designer readiness, and read-only limited-surface reporting.
- Risk: operators can waste time retrying clicks in an unusable browser surface, misdiagnose a browser-control limitation as an AllinCMS save failure, or prepare mutation authorization against a tab that is actually logged out.
- Rule: before design/theme/page mutation preparation, validate the current browser observation. Chrome must prove auth by loading `/sites` or the target module, not a cached page; designer mutations require visible designer UI, nonzero preview frame dimensions, no `Render canvas...` stall, and enabled action controls for the requested action. A readiness pass still does not authorize save, publish, create, or route changes.

- Follow-up: when the current in-app browser tab list shows only public frontend tabs, do not conclude the backend session is unusable until a focused target backend URL has been opened once. In this case, opening the exact Home designer URL restored an authenticated designer with visible Blocks/Layers, a nonzero preview iframe, and disabled Save/Publish controls because no edit had been made. Record that as `ready_for_readonly`, keep the tab for handoff, and require a fresh observation plus action-specific mutation record before editing.

## 2026-07-03 Existing Content Gate Closure Finding

- Context: continuing the source-file-to-site objective after one product and one post had already been partially overwritten on a temporary AllinCMS site.
- Symptom: the skill documented that existing non-probe products/posts needed `save_product`, `publish_product`, `save_post`, and `publish_post`, but the helper scripts still only had probe save/publish, batch, and generic publish surfaces. This left future browser work choosing between unsafe probe-gate reuse and ungated local records.
- Evidence: `make_authorization_record.py` and `check_pre_mutation_gate.py` now recognize the four existing-content actions. The gate requires a concrete `/{siteKey}/products|posts/{contentId}/update` target, matching content type, non-probe target identifier, current edit/list field evidence, fresh timestamps, save proof fields (`requestCapture`, `payloadShape`, `persistedVerified`, `bodyOrMediaAudit`), and publish proof fields (`publishStatus`, `backendVerified`, `frontendVerified`). Regression tests cover accepted product-save/post-publish records and rejection of probe identifiers, list URLs, and missing body/media audit fields.
- Risk: if only the docs mention dedicated actions, resumed operators may still perform real demo content replacement under probe semantics or skip the final gate because the CLI cannot validate the action.
- Rule: when a known mutation-safety gap is recorded as a follow-up, close it in the executable helpers before relying on it for further browser work. For existing product/post replacement, use the dedicated single-row gates; do not treat them as batch upload, JSON replay, deletion, or cleanup authorization.

## 2026-07-03 Existing Product Body Publish Residue Finding

- Context: using the new `save_product` and `publish_product` gates on one existing temporary-site product after replacing only its rich body.
- Symptom: generating preflight and authorization in parallel made the publish gate fail because `authorization.generatedAt` was earlier than `preflight.generatedAt`. After regenerating authorization sequentially, the gate passed. The in-app browser then hit the known 0x0 viewport/editor click issue on the first controlled tab; opening a fresh tab restored a normal viewport. Playwright fill/keyboard replacement appended new Slate body text to old starter body text, while CUA click plus system select-all/backspace plus clipboard paste produced a clean editor body. Saving changed the product to draft, and publishing returned the row to `已发布`. Frontend detail rendered the new body and no old body text, but starter specs, starter category/tag labels, starter brand/navigation, and starter images remained.
- Evidence: the frontend product detail contained the newly saved product body and no old starter body paragraphs, while it still showed starter specification rows, category/tag labels, template brand/navigation, and non-source-backed images.
- Risk: an operator can overclaim launch readiness after a body save/publish succeeds, or can corrupt a rich editor by saving appended old/new body text. Parallel preflight/auth generation can also look like a real authorization failure when it is only timestamp ordering.
- Rule: for existing product save/publish, generate preflight before authorization, then run the gate. If an editor tab reports 0x0 viewport or impossible click coordinates, open a fresh backend edit tab. For Slate body replacement, read the editor text after paste and block saving unless old starter phrases are absent. Treat body, specs, category/tag, media, brand/navigation, and related-product modules as separate launch verification surfaces.

## 2026-07-03 Existing Post Body Publish and Schema Boundary Finding

- Context: replacing the rich body of one existing temporary-site post through the backend editor after its title, slug, and excerpt had already been overwritten.
- Symptom: the post edit page exposed the same Slate-editor risk as products: the body had to be cleared and pasted through a controlled UI sequence, then read back before clicking `更新`. Saving the post changed it from `已发布` to `草稿`; a separate `publish_post` gate and click were required to return the list row to `已发布`. Frontend `/posts/{slug}` then rendered the new body and old starter body text was absent, while starter cover image, starter list neighbors, and starter brand/navigation remained. The run did not capture the network save payload, so the UI success resolved only the single existing post quality blocker, not the posts batch-upload schema gate.
- Evidence: backend save proof showed `保存成功`, `statusAfterSave=草稿`, and a visible publish control. After publish, the backend list row returned to `已发布`; the frontend list linked the target slug and the detail page rendered the new body signals with no visible raw Markdown or old entryway body. Source-input requirements moved `posts.post-body` to resolved but kept `posts.post-body-payload-schema` plus `posts.post-cover-media` blocked.
- Risk: an operator can mistake a manual UI body replacement for schema capture and start JSON replay or batch upload without a real non-empty post body payload template. The same save/publish split can also make a previously public article disappear if the publish step is skipped.
- Rule: for existing post body replacement, use `save_post` and `publish_post` as separate gated actions. Read the editor after paste and block save if starter text remains. Treat UI persistence/frontend rendering as one-row quality proof only; keep posts batch upload locked until a real current-site save request captures the non-empty body payload/block schema and one manifest sample passes backend/frontend verification.

## 2026-07-03 Existing Content Helper Contract Drift Finding

- Context: generating fresh authorization and source-input gap records during an existing post body save/publish run.
- Symptom: `check_pre_mutation_gate.py --action save_post` rejected an otherwise valid authorization record when `targetType` was `post-edit`; the current helper requires `targetType=posts`. Separately, `record_source_input_gap.py` rejected a descriptive `currentEvidence=ui-save-publish-only`; the supported vocabulary requires `ui-only` with the nuance carried in `generationRule` or `operatorNote`.
- Evidence: regenerating the authorization record with `--target-type posts` made the gate pass. Re-recording the gap with `--current-evidence ui-only` and an explicit operator note made ledger validation pass and preserved the batch-schema blocker.
- Risk: after context compaction, operators can waste a mutation window debugging correct intent but invalid helper vocabulary, or can weaken evidence by inventing unsupported enum labels.
- Rule: for existing-content authorization, use the content collection name (`posts` or `products`) as `targetType`, even when the target URL is an edit page. For source-input gap evidence, use the helper's fixed `currentEvidence` enum and put finer-grained distinctions such as "UI save/publish proof but no request payload" into `generationRule` and `operatorNote`.

## 2026-07-03 Declared Content Goal Overrun Finding

- Context: a local multi-file source rehearsal used a brief, tabular product data, article notes, and a structured site plan. The source declared minimum content goals, but extraction and auto-draft produced more items or obligations than the declared counts for some content areas.
- Symptom: `contentGoalCoverage` correctly showed both actual counts and declared goals, but `contentQualityReview.warnings` was empty and the suggested confirmation text said `warning: none`. A user could confirm the package without noticing that the AI expanded scope beyond the declared target.
- Evidence: review-packet generation and validation now emit `exceeds_declared_content_goal:<field>` warnings when actual counts exceed source-declared content goals. These warnings keep `readyShape=true` when no blocking quality issue exists, set `reviewRequired=true`, appear in `suggestedConfirmationText`, and propagate through confirmation/execution artifacts. Regression tests and a neutral multi-file rehearsal prove the run still reaches `waiting_for_user_content_confirmation`, then `needs_create_site_preflight` after confirmation.
- Risk: treating content goals only as minimums can silently add extra pages/posts/media/site-info obligations, increasing browser work, upload scope, and launch QA without user-visible consent.
- Rule: declared content goals are lower bounds for package completeness and review-visible upper-scope signals for confirmation. Under-generation blocks review readiness; over-generation is allowed only as a surfaced non-blocking warning that the user can accept, prune, or send back for regeneration before site creation or upload.

## 2026-07-03 Pages/Site-Info Starter-Template Proof Finding

- Context: read-only continuation after a created demo site had current site-info values, an enabled default theme, published default pages, and bound default routes.
- Symptom: the public frontend root was nonblank and the document title used the new site name, but the page body, navigation, product cards, article links, and images still came from the starter commerce template. A weak pages/site-info evidence file could previously pass with any non-empty `renderAudit` string and therefore overstate default-page reuse as source-content completion.
- Evidence: `validate_pages_site_info_execution_evidence.py` now requires each page `renderAudit` to be an object proving `sourceContentVerified=true`, `starterTemplateAbsent=true`, non-empty redacted source signals, empty starter-template signals, and redacted proof. The pages/site-info evidence template now exposes those fields instead of a free-text proof slot. Regression tests reject string render audits and starter-template residue.
- Risk: site-info persistence, active default theme, published routes, or a nonblank frontend can hide that launch pages were never replaced with the source-confirmed content. This blocks pages/site-info completion and must stop taxonomy/schema/upload work until the page design save/publish/frontend proof shows the intended source content.
- Rule: for pages/site-info execution, frontend proof must verify source-confirmed content presence and starter-template absence. Do not use site title, nonblank DOM, active theme, default route binding, or starter-template product/post links as proof that source pages are complete.

## 2026-07-03 Theme Target-Map Sequencing Finding

- Context: building a concrete theme/page target map from read-only theme page observations after collecting Home, About Us, and Contact Us design URLs.
- Symptom: the theme list rows exposed `设计` as buttons, not links. The concrete `/{siteKey}/themes/{themeId}/{pageId}/design` URL appeared only after opening each row's design button. Separately, running the target-map generator and a dependent `jq` read in parallel caused the read to observe the previous target-map file before the generator finished writing the new one.
- Evidence: opening About Us and Contact Us design buttons produced concrete design URLs and loaded designer surfaces with nonzero preview iframes while Save/Publish were disabled before edits. A parallel command then printed stale blocker output, while an immediate sequential reread showed the new target map had concrete page IDs/design URLs and no blockers for existing pages.
- Follow-up: the target map originally concretized the structured `target` field but left copied `authorizationRecordCommand` strings with `{themeId}` and `{pageId}` placeholders. The helper now recursively replaces placeholders across each action and marks `commandsConcrete`.
- Risk: operators can assume design buttons have hrefs, authorize placeholder `{pageId}` targets, copy stale helper commands, or misread stale validation output as a failed helper result when generation and dependent validation are launched concurrently.
- Rule: collect design URLs by read-only opening each page designer when the theme list does not expose hrefs. Treat disabled Save/Publish plus a nonzero preview iframe as read-only readiness proof. Run target-map generation and any dependent validation/readback sequentially, not in parallel. Before using a target-map action command, verify both `targetConcrete=true` and `commandsConcrete=true`.

## 2026-07-03 Product Core-Field Save Residue Finding

- Context: overwriting one default starter product on a temporary test site with source-like demo product core fields.
- Symptom: saving name, slug, and description changed the backend row and public detail title/description, but the save changed the product from published to draft until a separate publish action was clicked. After publish, the frontend detail still contained starter body paragraphs, starter specs, starter Unsplash images, and starter navigation/brand copy.
- Evidence: the backend list showed the new product title, slug, and description as `草稿` immediately after save; publishing returned the row to `已发布`. The public product detail loaded at the new slug and showed the updated title/description, while the old body/spec/media remained visible.
- Risk: a one-field or core-field save can look successful in the list while the public detail remains mixed with starter content, and save/publish can be accidentally collapsed into one assumed action. Batch upload built only from title/slug/description would produce launch pages with stale body, specs, images, categories, tags, and navigation signals.
- Rule: treat product save and product publish as separate actions. For existing-product overwrites, verify backend list status after save, publish explicitly if public visibility is required, and audit the public detail for title, description, body, specs, cover/gallery, category/tag chips, and starter-template residue. Record field gaps for `products.content`, `products.specs`, and product media/alt when the editor schema was not captured or source assets are missing.

## 2026-07-03 Post List/Detail Split Verification Finding

- Context: overwriting one default starter post with source-like demo article core fields.
- Symptom: saving title, slug, and excerpt changed the backend row to `草稿`; publishing changed the row to `已发布`. The public `/posts` list showed the updated article and linked the new slug. An initial detail navigation returned 404, but a later bounded recheck rendered the new detail route while the old slug returned 404 as expected after the slug change.
- Evidence: frontend list proof contained the new title, excerpt, and link to the new slug. The later redacted recheck showed `/posts/{newSlug}` rendering title and excerpt, and `/posts/{oldSlug}` returning the site's 404 page. The same recheck still showed starter article body text, starter cover image, and starter header/footer copy on the new detail page.
- Risk: verifying only the backend row or the `/posts` list can overstate article upload completion. Conversely, a single immediate 404 after publish or slug change can overstate a permanent route failure if the detail page later renders. Even when detail routing recovers, title/slug/excerpt-only saves can leave starter body and media in the public article.
- Rule: for posts, verify both list rendering and every linked `/posts/{slug}` detail page, with a bounded retry after publish or slug changes before calling the route permanently broken. If the new detail route renders, downgrade route failure to a propagation/recheck note and continue checking body, cover media, categories, tags, site template residue, and old-slug 404. Keep `posts.content` and `posts.coverImage/mediaAlt` blocked until their current-site save schema and frontend proof are captured.

## 2026-07-03 Multi-Run Browser Target Drift Finding

- Context: resuming a source-file-to-site run after browser tabs from other AllinCMS runs were still open in the in-app browser.
- Symptom: current visible frontend tabs belonged to site keys different from the active run evidence. Opening the run-bound backend URL still proved the intended site was logged in and readable, but the visible public tabs alone could cause cross-site verification.
- Evidence: the active run artifacts were bound to one site key and frontend base URL, while `openTabs()` showed other public frontend domains. A direct backend read-only navigation to the run-bound dashboard showed the expected counts and previously edited product/post for the intended site.
- Risk: after context compaction, a resumed agent can treat the browser's currently visible public tabs as the target site and mix frontend proof, screenshots, route checks, or launch QA across multiple sites. This contaminates source-run evidence and can make the skill appear to support upload/launch when it only verified another site.
- Rule: before every resumed browser verification or mutation-preparation round, bind the run to the site key and frontend base URL from current evidence, then compare that binding with `openTabs()`, `tabs.list()`, and the backend route to be inspected. If visible tabs belong to another site, record target drift, open the run-bound backend/frontend URL explicitly, and do not reuse the other site's page state as proof.

## 2026-07-03 Core-Field Overwrite Edit-Field Recheck Finding

- Context: read-only backend edit-page recheck after one product and one post were overwritten only at core fields.
- Symptom: product and post edit pages both exposed a Slate body editor and media controls. Product labels included name, slug, category, tags, description, order, main media, and gallery. Post labels included title, slug, category, tags, excerpt, order, and cover image. The update button was disabled because no edit had been made, but unpublish was visible for already published content.
- Evidence: the product editor still displayed starter body text and starter media after the product title/slug/description were changed. The post editor still displayed starter body text and starter cover image after title/slug/excerpt were changed.
- Risk: backend list rows and public list/detail titles can be correct while the editable body/media fields remain starter content. A batch uploader built from only list-visible fields will produce mixed pages and fail launch quality even if every route returns 200.
- Rule: treat title/name, slug, excerpt/description, body, media, categories/tags, order, status, and content-type-specific fields as separate verification surfaces. For products and posts, a schema capture that does not touch the Slate body editor and media controls is insufficient for launch-ready batch upload unless the user explicitly accepts preserving existing body/media.

## 2026-07-03 Resolved Gap Evidence Helper Finding

- Context: a later frontend recheck superseded an earlier operation-time gap, while the run also discovered new body/media gaps that should remain active.
- Symptom: the append-only source-input gap ledger had no low-friction helper for producing `allincms_resolved_source_input_gaps` evidence. Operators could be tempted to hand-edit the old ledger row, which removes the audit trail and can make future PDF/catalog extraction depend on untraceable state.
- Evidence: `make_source_input_requirements.py` already supports `--resolved-gap-evidence`, but resolved evidence previously had to be hand-written. `make_resolved_source_input_gaps.py` now writes the evidence, validates the optional source ledger, rejects unresolved field labels not present in that ledger, rejects sensitive proof paths, and regression tests prove the requirements report filters only the resolved field.
- Risk: stale blockers can keep source extraction blocked after later proof, while manual ledger edits can hide why the field was originally considered blocked.
- Rule: keep operation gap ledgers append-only. When later proof supersedes a gap, generate resolved evidence with `make_resolved_source_input_gaps.py` and pass it into requirements or source-file rehearsal with `--resolved-gap-evidence`. If the superseding proof exposes a different missing field, append a new gap row for that field instead of rewriting the old one.

## 2026-07-03 Resolved Gap Automation Contract Finding

- Context: adding resolved-gap evidence generation to the source-file-to-site helper chain.
- Symptom: a helper can support `--json` but still print human status before the JSON branch, breaking machine consumers that pipe stdout to `json.tool` or another agent. Separately, the requirements builder could consume a hand-written `allincms_resolved_source_input_gaps` file without applying the same sensitive-string checks as the generator.
- Evidence: `make_resolved_source_input_gaps.py` now emits pure JSON when `--json` is set and is included in `test_source_chain_json_stdout_contract.py`. `make_source_input_requirements.py` now rejects sensitive `fieldLabel`, `proof`, or `note` values in resolved-gap evidence even if the file was hand-written rather than produced by the helper. Regression tests cover both paths.
- Risk: source-chain automation can fail after context compaction because stdout contains non-JSON text, or stale blockers can be filtered with a sensitive or unsafe proof pointer that bypassed the generator.
- Rule: every source-chain helper with `--json` must be added to the JSON stdout contract test in the same sedimentation round. Every consumer of hand-written or external resolved-gap evidence must validate sensitive strings defensively; generator-side validation is not enough.

## 2026-07-03 Source Gap Ledger Classification Finding

- Context: recording browser-discovered product/body/media and post-detail field gaps for later PDF/catalog extraction.
- Symptom: `record_source_input_gap.py` rejected intuitive classification labels such as `required-for-launch`, `source-derived-or-user-provided`, and `blocked-until-public-url-or-upload`; it also rejects evidence pointers whose filename suggests authorization or credential material.
- Evidence: attempts with those labels failed validation; using supported labels such as `source-derived`, `user-confirmed`, `recommended`, and `blocked-until-schema-captured` succeeded. Pointing entries to a neutral redacted verification file succeeded where an authorization-record path was rejected.
- Risk: operators may either skip gap recording after a validation failure or weaken the ledger by storing sensitive/authorization file paths. Invalid labels also make later source-input requirements generation brittle.
- Rule: use the ledger's supported classification vocabulary and encode launch necessity in `generationRule` or `operatorNote` instead of inventing labels. Evidence pointers should target neutral redacted proof files, not authorization records, credential-like filenames, raw headers, cookies, or request captures.

## 2026-07-02 Create Preflight Apply Continuation Finding

- Context: local new-site source run after content confirmation and `/sites` read-only preflight collection.
- Symptom: `apply_create_preflight_to_confirmed_execution.py` originally expected a source-confirmation apply result with `artifacts.confirmation`. Passing the current `source-next-stage-handoff.json` from confirmed execution, which is the artifact surfaced by the latest status, caused a low-level directory read error instead of a clear continuation path.
- Evidence: the helper now accepts both source-confirmation apply results and `allincms_source_next_stage_handoff` inputs. For handoffs it reads `contextPaths.confirmation` and `contextPaths.execution_plan`, then regenerates the confirmed create-site handoff, runbook, and created-site evidence bundle from the supplied preflight. Regression coverage passes the current source next-stage handoff directly.
- Risk: after context compaction or a resumed run, operators may have the current handoff but not remember the older apply-result path. A brittle helper input contract can lead to hand-copying commands or rebuilding confirmed execution from memory.
- Rule: post-confirmation helpers should accept the current continuation surface when it contains the required context paths. If a helper cannot consume an input artifact, fail with an explicit missing-path error rather than a low-level filesystem exception.

## 2026-07-02 Create Authorization Prep Continuation Finding

- Context: preparing action-time create-site authorization after create preflight produced a confirmed handoff/runbook.
- Symptom: `prepare_create_site_authorization.py` exposed top-level `runbook`, `preflight`, and authorization fields but no compact `artifacts` object. A resumed operator had to manually stitch the runbook, preflight, authorization target, and created-site evidence bundle/target before the browser submit and post-submit evidence stages.
- Evidence: `authorization-prep.json` now includes `artifacts.runbook`, `artifacts.preflight`, `artifacts.authorizationRecord`, `artifacts.authorizationRecordTarget`, `artifacts.createdSiteEvidenceBundle`, and `artifacts.createdSiteEvidenceTarget`. Regression tests cover both awaiting-authorization and pre-mutation-gate-passed states.
- Risk: the handoff from local authorization preparation to browser execution can lose the created-site evidence bundle path or use a stale authorization target, making the one-submit create-site stage harder to verify and resume.
- Rule: every post-confirmation local helper that is a handoff boundary should expose a compact `artifacts` continuation index. Top-level fields are useful for humans, but downstream agents should not have to infer sibling paths.

## 2026-07-02 Create Authorization Prep Artifact-Source Finding

- Context: continuing from a confirmed create-site apply result or directly from a create-site browser runbook.
- Symptom: `prepare_create_site_authorization.py` originally tried to read `createdSiteEvidenceBundle` and `createdSiteEvidenceTarget` from the runbook. The runbook only owns the created-site evidence output path; the evidence bundle path is emitted by the confirmed-execution/apply-result `artifacts` index. A direct runbook-only continuation therefore lost the bundle path, and an apply-result continuation could expose an empty bundle even though the upstream summary had prepared one.
- Evidence: the helper now inherits `createdSiteEvidenceBundle` and `createdSiteEvidenceTarget` from the apply-result `artifacts` when available, while direct `--runbook` input falls back to the runbook's `createdSiteEvidenceOutput` as the evidence target and leaves the bundle empty instead of fabricating it. Regression tests cover both continuation modes.
- Risk: browser operators can lose the post-submit evidence bundle and hand-write created-site proof from memory, or assume a bundle exists when only a runbook was provided.
- Rule: preserve upstream continuation artifacts when a helper is invoked from an apply/summary artifact. When invoked from a lower-level runbook, surface only the evidence paths the runbook actually contains and make missing higher-level bundles explicit.

## 2026-07-02 Source Create-Preflight Handoff Finding (superseded by 2026-08-12 API session preflight)

- Historical context only: local file-to-wiki-to-site rehearsal after user content-intent confirmation for a new-site run. The field names below are retired and must not be emitted by active helpers.
- Symptom: `source-next-stage-handoff.json` correctly reported `needsCreateSitePreflight=true` and `browserWorkRequired=false`, but the next action still required a read-only browser visit to `/sites` to collect create-site preflight evidence. Without a separate field, a resumed operator could misread `browserWorkRequired=false` as "no browser work needed" instead of "no mutation/browser evidence stage is executable yet."
- Evidence: `prepare_source_next_stage.py` now emits `readOnlyBrowserPreflightRequired=true` and `readOnlyBrowserPreflightTarget=https://workspace.laicms.com/sites` when a new-site run is blocked on create-site preflight. Regression tests cover both direct next-stage handoff generation and confirmed execution summaries. A local neutral three-file rehearsal reached `reviewReady=true`, then after content confirmation reached `needs_create_site_preflight` with no remote mutation.
- Risk: the file-to-site chain can stall after confirmation or skip the required `/sites` read-only preflight, leading to hand-built create-site runbooks, stale site lists, or attempted create-site authorization without current form evidence.
- Superseded rule: active helpers now use the 2026-08-12 structured API session preflight contract below. Do not reuse the historical browser-named fields or treat this historical section as current execution guidance.

## 2026-08-12 Workspace API Session Preflight Supersession

- Context: a resumed AllinCMS run visibly navigated to `/sites` even though login and site discovery were intended to be API-first.
- Root cause: old handoff fields named `readOnlyBrowserPreflightRequired` / `readOnlyBrowserPreflightTarget` and prose saying “browser visit to /sites” conflated the browser's authenticated session transport with a visible UI workflow.
- Fix: active handoffs now emit `apiSessionPreflightRequired` plus a structured `apiSessionPreflight` contract containing the RSC GET URL template, `in_app_browser_same_origin_cdp_fetch`, `credentials=include`, `visibleNavigationAllowed=false`, `foregroundAllowed=false`, and `loginNavigationGate=api_result_login_required_only`. The ambiguous legacy fields are no longer emitted by active helpers.
- Rule: reuse the in-app browser as a same-origin credential carrier only. Do not navigate to or foreground `/sites` for normal preflight. Open `/sign-in` only after the API response is explicitly classified as `login_required`.

## 2026-07-02 Batch Upload Capability Finding

- Context: answering whether the current skill can perform batch uploads.
- Symptom: the skill has source-file packaging, draft manifest export, schema-verified manifest gates, sample-upload preparation, batch runbook preparation, and batch evidence validation helpers. That can sound like "batch upload is ready now", but a local-ready package or a generic manifest is not live upload permission.
- Evidence: `SKILL.md` and `batch-verification.md` require current-site save-request capture per content type, `validate_manifest.py --require-schema-verified`, one real manifest-sample backend/frontend verification, a batch authorization/pre-mutation gate, complete progress proof, and frontend detail audit before batch completion can be claimed. A local source-file rehearsal that stops at confirmation or create-site preflight proves package/readiness flow only, not remote persistence.
- Rule: answer batch capability in layers. The skill can help batch upload by preparing source-backed manifests and gated runbooks, but direct live batch upload is allowed only after schema capture, sample verification, action-time authorization, batch evidence validation, and final frontend QA for the exact site and content type.

## 2026-07-02 Selected-Site Source Rehearsal Apply Finding

- Context: continuing a confirmed source-file rehearsal that targets an existing selected site.
- Symptom: the rehearsal summary exposed `confirmedExecutionSummary`, `confirmedSourceExecutionStatus`, and `confirmedSourceNextStageHandoff`, but not the lower-level confirmation record, execution plan, or artifact-readiness paths directly. A follow-up helper that required direct `confirmedConfirmation`, `confirmedExecutionPlan`, and `confirmedArtifactReadiness` keys could fail on older summaries or push operators to reopen nested summaries and hand-stitch paths.
- Evidence: `run_source_file_rehearsal.py` now surfaces those three confirmed continuation artifacts directly. `apply_selected_site_to_source_rehearsal.py` also supports older summaries by resolving the same paths from `confirmedExecutionSummary.artifacts`, requires `existing_site_selected` evidence, rejects `created_verified` evidence, and writes a compact apply result with schema-capture, pages/site-info, taxonomy, source status, and next-stage artifacts. Regression coverage proves selected-site apply advances to `pages_site_info_execution` without `createdSiteSubmittedValues`.
- Rule: current source rehearsal summaries should be usable as the continuation index. Existing-site continuation should go through a local apply helper after read-only selected-site evidence, not through manual path reconstruction from nested confirmed-execution artifacts. Keep selected-site binding distinct from new-site creation proof.

## 2026-07-02 Create-Preflight Source Rehearsal Apply Finding

- Context: continuing a confirmed source-file rehearsal for a new-site objective after `/sites` read-only create preflight has been collected.
- Symptom: the lower-level `apply_create_preflight_to_confirmed_execution.py` could consume a source-confirmation apply result or current source next-stage handoff, but operators starting from the top-level `source-file-rehearsal-summary.json` still had to find `confirmedSourceNextStageHandoff` manually before preparing the create-site handoff/runbook/evidence bundle.
- Evidence: `apply_create_preflight_to_source_rehearsal.py` now consumes the top-level rehearsal summary plus `create_preflight_verified` evidence, requires `confirmationPrepared=true`, `readyForBrowserStage=needs_create_site_preflight`, and new-site target mode, then delegates to the lower-level helper and writes a compact non-authorizing result with create-site handoff, runbook, evidence bundle, source status, and next-stage handoff. Regression coverage proves the runbook remains `browserStepsExecutable=false` and rejects existing-site or unconfirmed rehearsals.
- Rule: top-level source rehearsal summaries should be first-class continuation indexes for both new-site and existing-site branches. After `/sites` preflight, new-site continuation should use a local apply helper instead of hand-copying confirmation text, accepted fields, deferrals, or nested handoff paths. Create-site submit still requires separate action-time authorization and a pre-mutation gate.

## 2026-07-02 Source Confirmation Findings

- Context: applying a source-confirmation next-step handoff after user content confirmation.
- Symptom: `prepare_source_confirmation_next_step.py` could generate a correct `localCommand`, but the operator still had to execute or parse that shell string manually to produce confirmed execution artifacts. That left a brittle point between "user confirmed" and "confirmed execution prepared", especially after context compaction or when command quoting includes long confirmation text and repeated deferrals.
- Evidence: `apply_source_confirmation_next_step.py` now consumes `allincms_source_confirmation_next_step_handoff` directly. For `await_user_confirmation_text` handoffs with `localCommandReady=true`, it parses the local command, calls `prepare_confirmed_site_execution.build()` in-process, and writes `allincms_source_confirmation_next_step_apply` with the confirmed execution summary, source execution status, and source next-stage handoff. For `collect_create_preflight` and `run_gated_create_site`, it returns `browser_boundary_not_applied` and preserves the browser boundary without executing remote work. Regression tests cover local apply, browser-boundary refusal, and JSON stdout; a local source-file rehearsal proves the chain reaches `needs_create_site_preflight` with no remote mutation.
- Rule: machine-readable handoffs should not stop at shell strings when the next stage is local-only. Provide an apply helper that executes local preparation in-process and refuses browser boundaries. Reserve shell commands for operator transparency and debugging, not as the only continuation path.

- Context: resuming from `source-confirmation-brief.json` after the user confirms content intent.
- Symptom: adding a machine-readable `executionIntake` to the brief still left one brittle step: the next operator had to inspect the brief, decide whether to prepare confirmed execution, collect read-only create preflight, or use a create-site runbook, and then copy the right command manually. That made the "user confirms, AI continues" path vulnerable to context compaction and command-copy drift.
- Evidence: `prepare_source_confirmation_next_step.py` now consumes a validated `source-confirmation-brief.json` and writes `allincms_source_confirmation_next_step_handoff`. In `await_user_confirmation_text` mode it can insert the supplied user confirmation text into the local `prepare_confirmed_site_execution.py` command without executing it. In `collect_create_preflight` mode it exposes a read-only browser boundary and target evidence file. In `run_gated_create_site` mode it points to the non-executable create-site runbook and created-site evidence bundle while preserving action-time authorization and pre-mutation gate requirements. Regression tests cover all three modes plus JSON stdout, and a local source-file rehearsal proves the handoff can bridge review-ready confirmation to confirmed-execution preparation without remote mutation.
- Rule: do not make resumption depend on parsing Markdown or hand-copying long command templates. After validating a source confirmation brief, generate a next-step handoff from `executionIntake`; execute only local helper commands from that handoff, and treat any browser boundary as non-authorizing until the normal action-specific gate passes.

- Context: source confirmation brief after source-file rehearsal reaches review-ready or confirmed-execution states.
- Symptom: the brief carried human-readable counts, command templates, and next actions, but the next operator still had to infer execution routing from prose or parse long command strings: waiting for user confirmation, collecting `/sites` create preflight, or running an already prepared create-site runbook. That is brittle after context compaction and makes "user confirms, AI continues" depend on Markdown reading instead of a small machine-checkable contract.
- Evidence: `make_source_confirmation_brief.py` now writes an `executionIntake` object with `mode`, booleans for user-confirmation/preflight/create-runbook readiness, package/review-packet paths, confirmation output, confirmed execution output directory, create preflight target, create-site handoff/runbook/evidence bundle paths, create action-gate output, and the next command template when waiting for confirmation. `validate_source_confirmation_brief.py` validates mode/status alignment and binds intake paths back to the source rehearsal summary. Regression coverage and a local two-file rehearsal prove `await_user_confirmation_text` before confirmation and `collect_create_preflight` after confirmation without preflight.
- Rule: confirmation briefs are execution handoffs, not only user summaries. Preserve a compact machine-readable intake block so the next AI can continue from the correct local helper or browser boundary without parsing Markdown or reconstructing command strings from memory. Keep it non-authorizing; remote create/save/upload/publish still requires the normal action-time gate.

- Context: multi-file source intake where structured JSON and CSV/Markdown describe the same product or article.
- Symptom: `extract_source_materials.py` can append products/posts from multiple source files, and `build_source_wiki.py` previously normalized them one by one. When the same product appeared in a JSON site plan and a CSV table, `validate_source_wiki.py` rejected duplicate slugs before the run could reach source-package review or user confirmation.
- Evidence: `build_source_wiki.py` now merges normalized products/posts by slug while preserving deterministic first-seen order. The merge keeps the stronger first non-placeholder name/title/description/excerpt, unions `sourceRefs`, categories, tags, media needs, and product specs, and appends distinct content blocks instead of dropping either source. Regression coverage creates duplicate product and post slugs from two inventory refs and asserts a single merged item with both refs and merged fields. A local three-file rehearsal with duplicated products now reaches `waiting_for_user_content_confirmation` with 3 products, not 6, and valid initial/refined source wiki files.
- Rule: duplicate product/post slugs from source intake are not automatically an upload conflict. First merge same-slug source-wiki entities at the normalization layer and preserve all source refs/fields. Keep manifest duplicate-slug validation strict after source-wiki normalization; if two different real entities still collapse to one slug after merge, fix the source wiki or ask for user confirmation before package approval.

- Context: launch-acceptance filled input validation before applying final source-run acceptance.
- Symptom: `apply_launch_acceptance.py` and final acceptance could reject missing products/posts sample or batch proof, but `prepare_launch_acceptance_inputs_bundle.py --validate-inputs` only required non-empty `sampleEvidence[]` and `batchValidation[]`. A mixed products/posts run could therefore pass the fill-template validation with only one content type represented, then fail later during apply.
- Evidence: `prepare_launch_acceptance_inputs_bundle.py` now derives expected content types from `contentCounts.products` and `contentCounts.posts`, loads each `sampleEvidence[]` and `batchValidation[]` file, reads `contentType`, and requires both `products` and `posts` coverage when both are planned. Regression coverage rejects a mixed products/posts filled inputs file with only products sample/batch proof, rejects two products paths that merely satisfy count, and accepts the inputs after posts paths are added.
- Rule: launch-acceptance input validation should fail at the filled-template boundary when the confirmed source scope includes both products and posts but sample or batch proof lacks either content type. Catching this before apply avoids a late launch acceptance failure and prevents two same-type files from masquerading as complete mixed-content proof.

- Context: launch-acceptance input bundle apply-command scaffolding for mixed products/posts source runs.
- Symptom: the generated `apply-command.txt` listed upload readiness and batch validation arrays but omitted `--sample-evidence <...sampleEvidence[]>`. The normal `prepare_source_next_stage.py --launch-acceptance-inputs-bundle` route already expands sample evidence correctly, but an operator debugging from the bundle's command file could run launch acceptance without the per-content-type sample evidence required by final acceptance.
- Evidence: `prepare_launch_acceptance_inputs_bundle.py` now includes `--sample-evidence <from launch-acceptance-inputs.filled.json:sampleEvidence[]>` in the generated apply-command scaffold, and regression coverage asserts the command preserves the filled inputs' sample evidence array.
- Rule: every launch-acceptance apply path must carry all sample evidence paths, not only upload readiness and batch validation. For mixed products/posts runs, final acceptance must see both content-type samples before it can accept launch completion.

- Context: source next-stage routing at `batch_upload` for mixed products/posts runs.
- Symptom: once both products and posts had manifest sample evidence, the batch-preparation handoff could use the first sample evidence from source status as the primary `--sample-evidence` when the operator passed only `--manifest` and `--base-run-evidence`. That made the command look concrete while relying on sample order instead of an explicit content-type match, increasing the chance of preparing a posts batch from a products sample or the reverse.
- Evidence: `prepare_source_next_stage.py` now emits `<sample-evidence-for-selected-manifest.json>` when multiple source-status samples exist and no explicit sample is supplied. The handoff required inputs and adversarial checks now require the sample evidence to match the selected schema-verified manifest. Regression coverage asserts the placeholder appears for ambiguous mixed-sample preparation and disappears when `--sample-evidence` is supplied explicitly.
- Rule: batch preparation is one manifest and one content type at a time. Existing products/posts samples are continuity context only; the operator must pass the sample evidence that matches the selected manifest before preparing the batch runbook.

- Context: source review packet and confirmation brief before user content-intent confirmation.
- Symptom: the review packet top-level `counts.media` could count only direct `contentPlan.media` entries, while the actual launch scope lived in `contentGoalCoverage.counts.media` after adding product/post/page media needs and missing-image obligations. A file-to-site rehearsal could therefore show `media=0` in the user-facing confirmation brief while the validated coverage and later execution plan correctly required media proof.
- Evidence: `make_source_package_review_packet.py` and `validate_source_package_review_packet.py` now derive top-level review counts for `media`, `siteInfoFields`, and `navigationItems` from `contentGoalCoverage.counts` when present. Regression coverage asserts review packet counts expose media needs and site-info/navigation scope, and a local structured-source rehearsal now reaches `waiting_for_user_content_confirmation` with review and brief counts matching coverage counts.
- Rule: user-facing confirmation counts must use the same extended scope as downstream execution counts. Do not let direct-array counts for media or other auxiliary structures hide source-declared media needs, site-info fields, or navigation items at the confirmation boundary.

- Context: final source-run acceptance after pages/site-info validation began exposing `siteInfoFieldCount`.
- Symptom: final acceptance could prefer the pages/site-info validation count over a later forms/media/settings evidence file that explicitly reported a lower `siteInfoFieldCount`. That let earlier site-info save proof mask a later final-settings shortfall, so a confirmed site-info field scope could be accepted even though the final settings evidence said fewer fields were verified.
- Evidence: `validate_source_run_acceptance.py` now uses forms/media/settings `siteInfoFieldCount` / `siteInfoFields` / `verifiedSiteInfoFieldCount` first when it is explicitly present, and falls back to pages/site-info validation only when the later settings evidence omits the count. Regression coverage accepts the fallback path when the count is absent and blocks when the explicit later count is below the confirmed scope.
- Rule: pages/site-info validation can satisfy final site-info field-count proof only as a fallback. If a later forms/media/settings artifact explicitly reports site-info field coverage, final acceptance must honor that current count and block shortfalls instead of letting older page-stage proof overwrite it.

- Context: confirmed source-package execution handoff after user content confirmation.
- Symptom: confirmation records bound the review packet hash, but not the source-site package hash. If the package file was replaced at the same path after confirmation, downstream execution plan, create-site handoff, or runbook could rely on path/count/coverage checks without an explicit immutable package fingerprint.
- Evidence: `make_source_package_confirmation.py` now writes `sourcePackageSha256`; `validate_source_package_confirmation.py --package --review-packet` rehashes both current files; `build_confirmed_site_execution_plan.py`, `build_confirmed_create_site_handoff.py`, and `build_create_site_runbook.py` preserve package and review-packet hashes. Regression tests reject source package hash mismatch and create-site handoff identity drift.
- Rule: user confirmation must bind to both the exact package and exact review packet. If either file changes, regenerate the review packet/confirmation/execution artifacts before requesting create-site authorization or any browser mutation.

- Context: post-confirmation export, created-site binding, schema-capture preparation, manifest sample, and batch preparation after source-package/review-packet hashes were added to confirmation.
- Symptom: source identity hashes could survive the create-site handoff but disappear from artifact readiness, created-site binding, schema-capture handoff, bound/schema-verified manifests, sample runbooks, or batch summaries. Later upload evidence could then prove a valid schema or frontend page without proving it still belonged to the exact source package and review packet the user confirmed.
- Evidence: `export_confirmed_site_artifacts.py`, `bind_created_site_to_artifacts.py`, `prepare_created_site_schema_capture.py`, `build_schema_capture_handoff.py`, `apply_save_capture_to_manifest.py`, sample/batch runbook and evidence-bundle helpers, `prepare_batch_upload_publish.py`, `apply_batch_upload_publish.py`, and `summarize_source_execution_status.py` now preserve or validate `sourcePackageSha256` and `sourceReviewPacketSha256`. Regression tests cover export, site binding, created-site schema preparation, schema manifest upgrade, manifest sample preparation, and batch preparation/apply.
- Rule: after user confirmation, both source identity hashes must remain attached through export, site binding, schema handoff, schema-verified manifests, sample proof, batch proof, launch acceptance, and final closeout. If either hash is missing from a new confirmed-source artifact or mismatches among artifacts that carry it, stop and rebuild the stale artifact before browser mutation.

- Context: final source-run acceptance for confirmed site-info scope.
- Symptom: source package validation preserved and checked `contentGoals.siteInfoFields`, but the final source-run acceptance structure-count gate checked navigation, taxonomy, forms, and media only. A run could therefore carry confirmed site-info field scope through local artifacts while final acceptance relied on `siteInfoVerified=true` without proving how many SEO/contact/legal/logo fields were actually covered.
- Evidence: `validate_source_run_acceptance.py` now treats `contentCounts.siteInfoFields` or `contentGoalCoverage.counts.siteInfoFields` as an expected final structure count and requires forms/media/settings evidence to expose `siteInfoFieldCount`, `siteInfoFields`, or `verifiedSiteInfoFieldCount` unless `site-info` is explicitly deferred. `validate_forms_media_settings_evidence.py` now requires a positive site-info field count when `siteInfoVerified=true`, and the forms/media/settings evidence bundle template includes `siteInfoFieldCount`.
- Rule: site-info verification must be count-bound at final acceptance. Do not accept a file-to-site launch where the user confirmed site-info fields but the final evidence only says site info was verified without a field count or explicit deferral.

- Context: structured source plans that declare content goals for forms, media, and site-info fields.
- Symptom: source package coverage protected declared pages, products, posts, navigation, and taxonomy counts, but not `forms`, `media`, or `siteInfoFields`. A source file could therefore request form/media/site-info scope while the package still looked review-ready with those structures missing or under-scoped.
- Evidence: `build_source_site_package.py` now preserves `contentGoals.forms`, `contentGoals.media`, and `contentGoals.siteInfoFields`; `validate_source_site_package.py` counts and blocks shortfalls for form plans, media plan plus source-declared media needs, and populated site-info fields; regression tests cover both successful extended-goal coverage and review-ready blocking when those declared goals are unmet.
- Rule: structured source-plan goals for forms, media, and site-info fields are source-scope contracts. They must block a review-ready package when unmet, even though browser schema capture and live proof are still required before any form save, media upload, site-info save, or batch content upload.

- Context: launch acceptance validation after final frontend audit stage-result hardening.
- Symptom: final source-run acceptance reopened the redacted frontend audit report, inputs summary, and expected-status map, but `validate_launch_acceptance.py` still accepted a final frontend audit stage result mainly from `status`, `proof`, and empty blockers. A hand-written completed stage result could therefore pass launch acceptance even if the underlying audit report had DOM issues or wrong detail URL fingerprints.
- Evidence: `validate_launch_acceptance.py` now calls the final audit direct checks: `validate_browser_stage_result`, redacted audit report loading, `summarize_reports`, and `validate_expected_coverage`. Regression tests reject launch acceptance when the final report contains a visible Markdown issue or the product detail URL fingerprint differs from the expected status map. Existing launch fixtures now include the direct audit report, inputs summary, expected statuses, and URL fingerprints.
- Rule: launch acceptance must not trust final frontend audit stage status alone. It must reopen and revalidate the direct audit artifacts before marking `final_frontend_audit_passed`.

- Context: final frontend audit input generation for source packages that plan both products and posts.
- Symptom: `make_final_frontend_audit_inputs.py` accepted only one manifest, so a mixed products/posts launch required manual URL/status stitching or separate audits. That made it easy to prove product detail routes while omitting post detail routes, or vice versa, before final acceptance.
- Evidence: `make_final_frontend_audit_inputs.py` now accepts repeated `--manifest` flags and either one combined completed progress log or one progress log per manifest. Its summary reports `contentType=mixed`, `contentTypes`, `manifestCount`, and `detailRouteCountByContentType`. Regression tests cover single-manifest compatibility, mixed products/posts URL generation, combined progress logs, extra same-type slug rejection, and CLI repeated-manifest output.
- Rule: final launch audit inputs must be built from the whole uploaded content set, not from a single convenient manifest. For mixed launches, generate one final URL/status set containing every planned product/post detail slug plus in-scope static routes before running the redacted frontend audit and final acceptance.

- Context: final frontend audit coverage after batch upload/publish uses redacted route patterns.
- Symptom: final acceptance could compare route patterns such as `/products/{slug}` and detail-route counts while missing that the audited concrete slug was different from the manifest/progress slug expected for the run.
- Evidence: `audit_frontend_rendering.py --redact` now preserves a SHA-256 `urlFingerprint` for each original URL, and `make_final_frontend_audit_stage_result.py` compares the expected concrete URL fingerprints from `expectedStatuses` with the redacted audit report. Regression coverage rejects wrong detail-slug fingerprints while keeping slugs redacted from reusable evidence.
- Rule: final frontend audit proof must bind to the exact generated runtime URL set. Redact concrete slugs in reports, but preserve URL fingerprints and fail the final audit stage when expected detail URL fingerprints are missing or unexpected fingerprints appear.

- Context: source next-stage handoff routing for `taxonomy_execution` when the operator passes a generated taxonomy evidence bundle.
- Symptom: after taxonomy evidence validation was hardened, `prepare_source_next_stage.py` could still derive an `apply_taxonomy_execution.py` command from a bundle that advertised `handoffReadyForBrowserStage=blocked_taxonomy_preflight` or non-empty `handoffPreflightIssues`. The apply helper would later reject it, but the controller handoff still looked like a local helper command was ready.
- Evidence: `prepare_source_next_stage.py` now rejects blocked taxonomy evidence bundles before emitting an apply command. Regression coverage proves a blocked taxonomy bundle raises a clear error instead of producing `localCommand`, while ready bundles still derive the filled evidence path and handoff.
- Rule: next-stage handoffs are control surfaces, not passive command templates. They must not emit a downstream apply command from evidence bundles that already declare their own source handoff is blocked.

- Context: taxonomy execution validation after created-site schema preparation can generate a taxonomy evidence bundle even when product/post taxonomy read-only preflight is still missing.
- Symptom: a handoff with `readyForBrowserStage=blocked_taxonomy_preflight` and non-empty `preflightIssues` still produced a fillable evidence template. A fully populated evidence file could validate if every term mapping looked complete, letting a run appear to satisfy taxonomy before current products/posts category/tag UI or request-shape preflight was proven.
- Evidence: `validate_taxonomy_execution_evidence.py` now rejects taxonomy evidence when the source handoff is not `ready_to_prepare_action_specific_taxonomy_authorization` or has non-empty `preflightIssues`. `prepare_taxonomy_evidence_bundle.py` exposes `handoffReadyForBrowserStage` and `handoffPreflightIssues`, and its next action tells the operator to resolve taxonomy preflight blockers before browser actions. Regression tests cover blocked-handoff rejection at both validator and apply-helper layers.
- Rule: evidence cannot wash a blocked handoff. If taxonomy is blocked on read-only products/posts taxonomy preflight, refresh and merge the missing preflight, rebuild created-site schema capture, and regenerate the taxonomy handoff before filling or applying taxonomy evidence.

- Context: applying pages/site-info evidence after a source package was confirmed and downstream artifacts carried actual accepted-field source labels.
- Symptom: the review packet's `confirmationDecisionMatrix` used `source=suggestedAcceptedFields` / `suggestedAcceptedDeferrals`, while post-confirmation artifacts used `source=acceptedFields` / `acceptedDeferrals`. The shared matcher compared whole rows, so a valid post-confirmation chain could be rejected even when `field`, `decision`, `deferDecision`, `reason`, and `blocksRemoteMutation` were unchanged.
- Evidence: `content_goal_coverage_utils.py` now compares confirmation decision matrices by stable decision semantics and ignores the transitional `source` label. Regression tests accept suggested-to-confirmed source-label transitions for accept and defer rows, while still rejecting real `decision` or `deferDecision` drift. The previously blocked pages/site-info apply path now validates and advances to taxonomy handoff in local rehearsal.
- Rule: treat `source` in `confirmationDecisionMatrix` as provenance, not execution semantics. Post-confirmation matching must preserve field coverage and decision meaning, but should not block solely because review suggestions became accepted-field records after user confirmation.

- Context: source-file manifests with product/post cover, gallery, or source-declared `mediaNeeds` during sample and batch upload gates.
- Symptom: sample evidence could pass with `coverOrMediaVerified=false` plus a note even when the sampled manifest item carried `coverImage`, `media`, `gallery`, or source-package `mediaNeeds`. Batch evidence validation relied on later final-audit/progress checks and did not directly bind all manifest media requirements to each progress row, so a source-backed image requirement could disappear during upload while the run advanced toward settings/launch gates.
- Evidence: `validate_manifest_sample_upload_evidence.py` now requires `coverOrMediaVerified=true` when the sampled manifest item has media fields or `mediaNeeds`. `validate_batch_upload_publish_evidence.py` now checks each progress row against the matching manifest item and rejects missing cover/media proof for media-required rows. `prepare_batch_upload_publish.py` writes `mediaRequired` into batch progress seed rows so browser evidence capture knows which slugs require image proof. Regression tests cover sample rejection, batch rejection, and progress seed marking for both concrete media fields and source-derived `mediaNeeds`.
- Rule: note-only media absence is valid only for manifest items that have no media field, no source-declared `mediaNeeds`, and whose launch scope accepts no image. If source-derived `coverImage`, `media`, `gallery`, or `mediaNeeds` exists in the schema-verified manifest, sample and batch evidence must prove the media rendered, stayed attached, or was explicitly resolved before the run can advance.

- Context: confirmed source-file package continuation into an already selected existing site.
- Symptom: the source-file chain had a strong new-site binding path, but `bind_created_site_to_artifacts.py` accepted only `created_verified` evidence. Existing-site confirmation stopped at read-only refresh and then required manual interpretation before bound products/posts manifests, pages/site-info handoff, taxonomy handoff, and schema-capture preparation could continue.
- Evidence: `bind_created_site_to_artifacts.py` now accepts validated `existing_site_selected` evidence as selected-site binding input, writes `siteBindingMode=existing_site`, keeps manifests `schemaVerified=false`, and adds adversarial checks that existing-site binding is not proof of new-site creation. `build_schema_capture_handoff.py` also accepts the selected-site binding/evidence pair and carries `siteBindingMode` into the schema-capture handoff. Regression tests cover both `created_site` and `existing_site` binding plus existing-site schema-capture preparation.
- Rule: artifact binding is valid for either a newly created site or a freshly selected existing site, but completion semantics differ. Use `created_site` binding for from-scratch site-creation proof; use `existing_site` binding only for continuation on a selected site, then continue through pages/site-info, taxonomy, schema, sample, batch, forms/media/settings, and launch gates. Downstream schema handoffs must validate that `siteBindingMode=existing_site` is paired with `siteCreation.status=existing_site_selected`, not silently demand or fabricate `created_verified`.

- Context: final source-run acceptance after existing-site binding support was added.
- Symptom: final acceptance required an `allincms_created_site_artifact_binding`, but the same binding kind can represent either `siteBindingMode=created_site` or `siteBindingMode=existing_site`. Without an explicit final objective check, an existing-site continuation could be mistaken for completion of a from-scratch "new site" objective.
- Evidence: `validate_source_run_acceptance.py` now detects new-site objectives from `--objective` text or package target mode and rejects `siteBindingMode=existing_site` with `created_site_required`. Regression tests cover a complete-looking run that fails when the objective says the AI must create a new site.
- Rule: final acceptance for a new-site/from-scratch objective must require `siteBindingMode=created_site` and `siteCreationStatus=created_verified`. Existing-site binding remains valid continuation proof only when the objective is explicitly existing-site continuation or selection.

- Context: source-file rehearsal where a prose brief declared required static pages while structured navigation omitted one of those pages.
- Symptom: source extraction and auto-draft produced a `readyShape=true` package with enough product/post copy, but publication validation still blocked on `declaredContentGoals.pages`. The auto-draft helper added static pages from navigation items only, so a page named in prose `Required pages:` but absent from navigation was not created.
- Evidence: `draft_refined_source_wiki.py` now extracts required page labels from source-wiki page text/open questions, filters reserved list/detail/dynamic routes, and creates reviewable static pages until the declared page count is satisfied. Regression tests cover a brief that lists a required page outside navigation. A four-file local rehearsal now reaches `waiting_for_user_content_confirmation`, and with create-site preflight plus content confirmation reaches `create_site_handoff_ready` with non-executable create-site runbook/evidence bundle.
- Rule: declared page scope must not rely only on navigation items. Treat prose page lists such as `Required pages:` or `Pages:` as page-scope evidence, create non-reserved static pages from those labels during auto-draft refinement, and keep reserved list/detail routes as route/module requirements rather than standalone pages.

- Context: final frontend audit stage-result generation after launch acceptance requires explicit final-audit `contentCounts`.
- Symptom: `make_final_frontend_audit_stage_result.py` could preserve coverage, quality, wiki review, and confirmation matrix from source-context artifacts, but did not write `contentCounts`. The stricter launch acceptance gate then correctly required final frontend audit evidence to carry counts, while the normal generator could still omit them.
- Evidence: `make_final_frontend_audit_stage_result.py` now loads source-context artifacts, validates matching `contentCounts`, writes them into the generated final audit stage result, and rejects count drift. Regression tests cover count preservation and final-audit count drift.
- Rule: final frontend audit stage-result generation is part of the `contentCounts` continuity chain. If source-context artifacts carry counts, the generated final audit result must carry matching counts itself; do not rely on launch acceptance to inherit or repair a countless final-audit artifact.

- Context: source-file rehearsal with structured taxonomy count goals.
- Symptom: a structured source plan could declare more post categories than extraction produced; auto-draft left the package blocked on `declaredContentGoals.postCategories`, and the refinement plan misclassified the taxonomy-count issue as a media-policy deferral.
- Evidence: `draft_refined_source_wiki.py` now reads declared taxonomy goals and can add reviewable post/product category draft terms from item categories, post titles, and tags. `make_source_wiki_refinement_plan.py` now classifies declared taxonomy goal gaps as taxonomy work. A four-file local rehearsal with declared page/product/post/navigation/taxonomy counts now reaches `waiting_for_user_content_confirmation`, and regression tests cover post-category goal satisfaction plus taxonomy issue classification.
- Rule: structured taxonomy goals are scope contracts, but they should not force manual source-wiki editing when enough item/topic evidence exists to draft reviewable terms. Auto-draft may fill taxonomy planning terms, while taxonomy remains user-confirmed and blocked until current-site category/tag schema capture and backend mapping proof.

- Context: confirmed source-file rehearsal without fresh create-site preflight.
- Symptom: after user content confirmation, `run_source_file_rehearsal.py` correctly produced confirmed execution artifacts and stopped at `readyForBrowserStage=needs_create_site_preflight`, but the top-level `nextAction` still said to continue with the browser create/select-site stage. That contradicted the confirmed execution helper's own preflight-first instruction.
- Evidence: `run_source_file_rehearsal.py` now reuses the confirmed execution summary `nextAction` when confirmation artifacts exist. Regression tests assert missing-preflight summaries point to `create-site-preflight-brief.json`, while handoff-ready summaries point to `create-site-browser-runbook.json`.
- Rule: wrapper summaries must not flatten confirmed execution boundaries. Missing create-site preflight is read-only evidence collection, not browser creation readiness; only `create_site_handoff_ready` may direct the operator to the create-site runbook.

- Context: created-site schema-capture preparation after binding preserves full `contentCounts`.
- Symptom: created-site binding could carry full `contentCounts`, but `prepare_created_site_schema_capture.py` then copied only `pages/products/posts` into its summary and omitted counts from pages/site-info and taxonomy handoffs/bundles. That weakened the handoff before page/site-info and taxonomy browser work.
- Evidence: `prepare_created_site_schema_capture.py` now validates `pages/products/posts/forms/media/navigationItems/siteInfoFields` from created-site binding and includes `contentCounts` in the shared source-context fields copied into pages/site-info handoff, pages/site-info evidence bundle/template, taxonomy handoff, taxonomy evidence bundle/template, and the preparation summary. Regression tests assert the full count object survives through those artifacts.
- Rule: after created-site binding, schema-capture preparation must preserve the full `contentCounts` object through every post-create handoff and evidence scaffold. A summary or bundle that drops to pages/products/posts is stale and must be regenerated from current binding.

- Context: created-site binding after artifact readiness began carrying full `contentCounts`.
- Symptom: `artifact-readiness.json` preserved `forms`, `media`, `navigationItems`, and `siteInfoFields`, but `bind_created_site_to_artifacts.py` rederived `contentCounts` from `contentGoalCoverage.counts`, which only provides content and navigation/taxonomy counts. The binding and bound manifests therefore collapsed back to `pages/products/posts`.
- Evidence: `bind_created_site_to_artifacts.py` now reads full `contentCounts` from artifact readiness, validates `pages/products/posts/forms/media/navigationItems/siteInfoFields`, compares pages/products/posts/navigationItems against coverage counts, and writes the full object into created-site binding, bound artifact readiness, and bound products/posts manifests. Regression tests assert extended counts survive and missing `navigationItems` blocks binding.
- Rule: created-site binding must preserve the artifact readiness `contentCounts` object. Use `contentGoalCoverage.counts` only as a cross-check for overlapping keys, not as a replacement source for the confirmed site-building scope.

- Context: shared `contentCounts` comparison after artifact readiness began carrying navigation and site-info counts.
- Symptom: the shared `matching_content_counts` helper still validated only `pages`, `products`, and `posts`. A downstream artifact could therefore drop `forms`, `media`, `navigationItems`, or `siteInfoFields` and still pass count matching as long as the three content counts stayed equal.
- Evidence: `content_goal_coverage_utils.py` now treats `pages/products/posts` as the minimum legacy keys, then dynamically requires every extended key that appears anywhere in the compared chain. A new utility regression test rejects a created-site binding that drops `navigationItems` while keeping legacy three-count artifacts valid.
- Rule: if any source-context artifact carries extended `contentCounts` keys, every compared artifact in that chain must carry the same extended keys and values. Do not rely on pages/products/posts-only matching after the confirmed package has declared navigation, forms, media, or site-info scope.

- Context: confirmed artifact export after user package confirmation and before created-site binding/schema preparation.
- Symptom: the execution plan and create-site handoff/runbook could preserve full `contentCounts`, but `artifact-readiness.json` did not carry those counts. Because created-site binding and later schema/sample/batch helpers use artifact readiness as a central source-context input, the confirmed navigation and site-info scope could still disappear after artifact export.
- Evidence: `export_confirmed_site_artifacts.py` now validates and writes `contentCounts` from the confirmed execution plan into artifact readiness, requiring non-negative `pages`, `products`, `posts`, `navigationItems`, and `siteInfoFields`. Regression tests assert exported readiness includes navigation/site-info counts and rejects incomplete count scope.
- Rule: artifact readiness is a source-context continuity boundary, not just a file index. Do not continue to created-site binding, schema capture, or upload planning from artifact readiness that drops `contentCounts`; rebuild it from the confirmed package and execution plan.

- Context: confirmed source-package create-site boundary before the first remote site mutation.
- Symptom: the execution plan preserved full `contentCounts` including navigation and site-info scope, but the create-site handoff recalculated a narrower count set and could drop `navigationItems` and `siteInfoFields` before the browser runbook. That made the first remote mutation boundary weaker than the user-confirmed package even though no content upload had happened yet.
- Evidence: `build_confirmed_create_site_handoff.py` now reuses the confirmed execution-plan count helper, and both create-site handoff and runbook validators require non-negative `pages`, `products`, `posts`, `navigationItems`, and `siteInfoFields`. Regression tests reject handoff/runbook artifacts that omit navigation or site-info counts.
- Rule: the create-site stage is shell creation only, but it must preserve the confirmed site-building scope. Do not request create-site authorization from a handoff or runbook that drops navigation-item or site-info-field counts; rebuild from the confirmed package/execution plan first.

- Context: source-file rehearsal with auto-drafted or manually refined source wiki.
- Symptom: after auto refinement produced a review-ready package, `objectiveAudit.readyShape` still reported the initial source-prepare `contentQuality.readyShape=false` from the pre-refinement package. That made the summary look contradictory: `reviewReady=true` but the objective audit shape appeared not ready.
- Evidence: `run_source_file_rehearsal.py` now computes objective audit `readyShape` from the chosen review packet's `contentQualityReview.readyShape` when a refined/review-ready package is active, while preserving the pre-refinement `sourcePrepare.contentQuality` as historical context. Regression tests assert the refined-wiki confirmation gate reports objective ready shape true. A local four-file product-site rehearsal reached `waiting_for_user_content_confirmation` with `objectiveAudit.readyShape=true` and validation ok.
- Rule: after refinement, treat the chosen review packet and confirmation quality review as the current package-quality source. Keep pre-refinement quality in `sourcePrepare` only as history explaining why refinement was needed.

- Context: confirmed source-package execution before and after create-site preflight.
- Symptom: source execution status can be at `create_site_handoff` before a confirmed create-site handoff exists, but the next-stage handoff did not explicitly distinguish that read-only preflight blocker from a browser mutation boundary.
- Evidence: `prepare_source_next_stage.py` now emits `needsCreateSitePreflight=true`, `browserWorkRequired=false`, local-helper mode, and an explicit preflight blocker when `create_site_handoff` lacks a confirmed handoff. Tests cover the no-preflight boundary and the valid-handoff boundary where status advances to `created_site_binding` and browser work requires created-site evidence.
- Rule: missing create-site handoff is a read-only preflight blocker, not mutation readiness. After a valid handoff/runbook exists, do not treat it as created-site proof; perform one gated browser create submit and then fill created-site evidence before artifact binding.

- Context: source next-stage handoff documentation after create-site preflight boundary clarification.
- Symptom: `source-files-to-site-package.md` still said `currentStage=create_site_handoff` must emit a runbook command, even though the updated state machine distinguishes missing preflight from a valid handoff and normally advances a valid handoff to `created_site_binding`.
- Evidence: source-file workflow docs now describe the three-way boundary: missing preflight means `needsCreateSitePreflight=true` and no browser mutation; valid handoff/runbook advances to `created_site_binding`; browser work at that point is one gated create submit plus created-site evidence. Regression tests cover the same states.
- Rule: keep source workflow docs aligned with next-stage status semantics. Do not document a local command as mandatory for a stage that may be a read-only blocker or may already have advanced to the next browser evidence boundary.

- Context: created-site artifact binding and schema-capture preparation after a confirmed source package has been created or selected.
- Symptom: create-site handoff/runbook carried confirmed `contentCounts`, but created-site binding and schema-capture preparation exposed only broader source context. The next operator could see source coverage while losing the direct pages/products/posts quantity scope that later gates pages/site-info proof, sample requirements, and batch counts.
- Evidence: `bind_created_site_to_artifacts.py` now derives `contentCounts` from `contentGoalCoverage.counts`, validates pages/products/posts as non-negative integers, writes them into created-site binding and bound artifact readiness, and rejects drift. `prepare_created_site_schema_capture.py` now carries the counts into the preparation summary. Regression tests cover preservation and missing-count rejection.
- Rule: after site creation, keep confirmed `contentCounts` attached to created-site binding and schema-capture preparation. Treat them as scope metadata only; they do not authorize upload or replace schema capture, manifest sample proof, batch evidence, or final frontend QA.

- Context: schema-verified manifest, manifest sample, and batch preparation after created-site binding starts carrying `contentCounts`.
- Symptom: `contentCounts` could survive created-site binding, but schema-verified manifests, manifest sample runbooks/templates, and batch runbooks/bundles still copied only the older source-context keys. That could make the final pre-upload operator lose the direct pages/products/posts scope exactly when comparing sample and batch coverage.
- Evidence: `apply_save_capture_to_manifest.py` now preserves `contentCounts`; manifest sample runbooks/evidence bundles and batch runbooks/evidence bundles now copy and validate `contentCounts` when present. `prepare_batch_upload_publish.py` rejects count drift across run evidence, schema-verified manifest, and sample evidence. Regression tests cover schema-manifest/sample propagation, batch bundle propagation, and batch count-drift rejection.
- Rule: after schema capture, keep `contentCounts` attached through schema-verified manifest, sample evidence scaffolding, and batch preparation. Counts remain scope metadata only; they do not authorize browser upload or replace sample, batch progress, or frontend audit proof.

- Context: manifest sample and batch apply stages after counts are present in schema/sample/batch preparation artifacts.
- Symptom: `contentCounts` could be preserved into runbooks and evidence templates but then disappear or drift when `apply_manifest_sample_upload.py` or `apply_batch_upload_publish.py` refreshed source execution status. That made later source-stage dashboards weaker than the already-validated pre-upload artifacts.
- Evidence: `content_goal_coverage_utils.py` now exposes shared `matching_content_counts`; sample apply and batch apply summaries include `contentCounts` and reject mismatches across source-context artifacts, schema-verified manifest, sample evidence, base run evidence, and batch evidence as applicable. Regression tests cover preservation and count-drift rejection in both apply helpers.
- Rule: keep `contentCounts` attached through sample apply and batch apply. Treat counts as scope metadata that guards planned pages/products/posts quantity, not as a substitute for per-slug sample proof, batch progress rows, or frontend render audits.

- Context: manifest sample upload after schema-verified products/posts manifests are prepared.
- Symptom: `prepare_schema_manifest_sample.py` could generate a one-item sample runbook and upload readiness, while `validate_manifest_sample_upload_evidence.py` and `apply_manifest_sample_upload.py` could validate/apply completed proof, but operators still had to hand-write `allincms_manifest_sample_upload_evidence`. This stage is the direct blocker before batch upload, so missing body, media/no-image, frontend detail, or stop-condition proof can incorrectly unlock batch planning.
- Evidence: `prepare_manifest_sample_evidence_bundle.py` now creates a local evidence bundle from a manifest sample runbook, including a fillable sample evidence template, notes, validation command, and apply command. `prepare_schema_manifest_sample.py` writes the bundle next to the sample runbook, and regression tests assert it is exposed and non-executable.
- Risk: a source-file run can have a schema-verified manifest and a valid runbook but still overclaim sample proof, letting batch upload proceed before one real source-generated item proves backend persistence, publish state, frontend detail rendering, body structure, and cover/media policy.
- Rule: after manifest sample browser work, fill the generated sample evidence bundle with redacted backend/frontend proof, validate it, then run `apply_manifest_sample_upload.py`. Do not hand-write sample evidence from memory or prepare batch upload while the filled evidence fails validation.
- Follow-up: schema-manifest/sample preparation, source-file docs, SKILL inventory, and regression tests now expose the manifest sample evidence bundle.

- Context: source next-stage handoff at `sample_upload` after manifest sample evidence bundle support.
- Symptom: the sample evidence bundle exposed `filledEvidencePath`, manifest path, validation command, and apply command, but `prepare_source_next_stage.py` still required the operator to pass `--sample-evidence` directly. Operators could leave the one-stage source handoff, copy the wrong filled path, or forget the manifest path derived from the bundle.
- Evidence: `prepare_source_next_stage.py` now accepts `--sample-evidence-bundle`, reads `filledEvidencePath` and `manifest` from the bundle, and emits `apply_manifest_sample_upload.py` with existing sample evidence preserved. Regression tests cover deriving the filled path from the bundle while retaining prior products/posts sample evidence.
- Rule: at `sample_upload`, prefer passing the generated evidence bundle when the browser proof was captured through `manifest-sample-evidence.filled.json`. Let the next-stage handoff derive the filled evidence path and manifest instead of manually copying paths into `apply_manifest_sample_upload.py`.
- Follow-up: `SKILL.md`, `source-files-to-site-package.md`, `prepare_source_next_stage.py`, and next-stage regression tests now encode sample evidence bundle routing.

- Context: created-site evidence bundle generation before applying real browser create-site proof.
- Symptom: `prepare_created_site_evidence_bundle.py` advertised `filledEvidenceTemplate` and docs told operators to fill `created-site-evidence.filled-template.json`, but the helper only wrote `created-site-evidence.template.json`. The apply command could therefore point at a missing file after a real create-site browser submit.
- Evidence: the helper now writes `created-site-evidence.filled-template.json` as a materialized fill target initialized from the same redacted template, and regression tests assert both template files exist and match at generation time.
- Risk: after a successful create-site mutation, the next `created_site_binding` step can be blocked by local artifact path drift even though browser proof exists, forcing manual evidence reconstruction.
- Rule: every evidence bundle must materialize every path it advertises, especially fill targets referenced by apply commands or source next-stage handoffs. Treat an advertised-but-missing fill file as a helper bug, not as an operator proof gap.

- Context: follow-on evidence/input bundles after the created-site fill-target bug was fixed.
- Symptom: the same advertised-but-missing fill-target pattern also existed in later source execution stages: pages/site-info evidence, taxonomy evidence, manifest sample evidence, batch upload/publish evidence, forms/media/settings evidence, launch acceptance inputs, and probe save-capture evidence. Each bundle generated a template and command files that pointed at a `*.filled.json` path, but the path was not always materialized.
- Evidence: the affected bundle builders now write the declared filled target next to the template, initialized from the same redacted template. Regression tests assert the filled target exists and initially matches the template for each stage.
- Risk: a source-file-to-site run can pass local preparation, complete real browser proof, and then fail during evidence apply because a later-stage fill target was never created. This turns an operator formatting issue into a false workflow blocker and encourages hand-written evidence.
- Rule: new evidence bundles and input bundles must pass a fill-target materialization check: every path referenced by `filledEvidencePath`, `filledInputsPath`, or equivalent apply/validation command input must be written at bundle generation time and tested for existence. The file may still contain placeholders and must not be treated as validated proof until the stage-specific validator passes.

- Context: source next-stage handoff when reusing an existing evidence/input bundle.
- Symptom: after bundle generators began materializing filled targets, `prepare_source_next_stage.py` could still accept an older or hand-written bundle whose `filledEvidencePath` or `filledInputsPath` pointed at a missing file. It would then emit an apply command that fails later, or worse, encourages operators to reconstruct evidence by hand.
- Evidence: the next-stage helper now requires bundle filled target paths to be non-placeholder existing files before deriving apply commands for pages/site-info, taxonomy, manifest sample, batch upload/publish, forms/media/settings, and launch acceptance inputs. Regression tests reject a manifest sample bundle with a missing filled evidence file.
- Risk: cross-session reuse, copied `/tmp` folders, or manually edited bundle JSON can drift from the actual files on disk while still passing stage-string checks.
- Rule: bundle handoff safety is two-phase. Bundle builders must materialize fill targets at generation time, and next-stage helpers must re-check those paths at reuse time before emitting any apply command.

- Context: manifest sample runbook and evidence bundle after source-context propagation was added to schema-verified manifests.
- Symptom: schema-verified manifests and sample apply summaries could preserve `contentGoalCoverage`, `contentQualityReview`, `wikiReview`, and `confirmationDecisionMatrix`, but the sample runbook and sample evidence bundle/template did not expose the same context. A browser operator filling only the sample evidence template could lose the user-reviewed wiki/coverage/deferral boundary at the last gate before batch upload.
- Evidence: `build_manifest_sample_upload_runbook.py` now copies source-context fields from the schema-verified manifest into the runbook and redacted evidence template. `prepare_manifest_sample_evidence_bundle.py` copies the same context into the bundle and validates the four-field contract when present. `prepare_schema_manifest_sample.py` now also derives `contentGoalCoverage` from schema manifests when no separate source artifacts are supplied. Regression tests cover direct runbook/bundle preservation and the schema-manifest/sample main path.
- Rule: sample upload preparation is part of the source-context chain. If a schema-verified manifest carries source context, the sample runbook, evidence bundle, and fill template must carry the same four fields before browser mutation or sample evidence fill.

- Context: taxonomy execution after created-site schema preparation.
- Symptom: `prepare_created_site_schema_capture.py` generated a taxonomy execution handoff, and `apply_taxonomy_execution.py` could validate/apply completed evidence, but the operator still had to hand-write `allincms_taxonomy_execution_evidence` after browser create/map actions. Because taxonomy can gate product/post manifests and homepage category modules, manual evidence assembly can miss a term, omit selector-option proof, or skip a per-term pre-mutation gate.
- Evidence: `prepare_taxonomy_evidence_bundle.py` now creates a local evidence bundle from the taxonomy handoff, including a fillable taxonomy evidence template, notes, validation command, and apply command. `prepare_created_site_schema_capture.py` writes the bundle next to `taxonomy-execution-handoff.json`, and regression tests assert it is exposed and non-executable.
- Risk: a source-file run can correctly plan categories/tags but later overclaim taxonomy readiness, causing products/posts with `categories`, `tags`, or `categoryIds` to pass into upload planning without every source-confirmed term being created or mapped on the current site.
- Rule: after taxonomy browser work, fill the generated taxonomy evidence bundle with redacted backend row or selector-option proof, validate it, then run `apply_taxonomy_execution.py`. Do not hand-write taxonomy evidence from memory or continue to schema/sample/batch upload while the filled evidence fails validation.
- Follow-up: created-site schema preparation, source-file docs, SKILL inventory, and regression tests now expose the taxonomy evidence bundle.

- Context: pages/site-info execution after created-site schema preparation.
- Symptom: `prepare_created_site_schema_capture.py` generated a pages/site-info browser handoff, but the operator still had to hand-write the completed `allincms_pages_site_info_execution_evidence` JSON before validation/apply. Because this stage spans site-info save plus page create/save/publish/enable/route/frontend proof, manual evidence assembly can miss a page path, leave placeholder IDs, or skip one action's pre-mutation proof.
- Evidence: `prepare_pages_site_info_evidence_bundle.py` now creates a local evidence bundle from the pages/site-info handoff, including a fillable evidence template, notes, validation command, and apply command. `prepare_created_site_schema_capture.py` writes the bundle alongside the handoff, and regression tests assert it is exposed and non-executable.
- Risk: a source-file run can create a valid pages/site-info handoff but stall or overclaim completion because the browser proof format is too easy to assemble inconsistently.
- Rule: after pages/site-info browser work, fill the generated evidence bundle with redacted proof, validate it, then run `apply_pages_site_info_execution.py`. Do not hand-write pages/site-info evidence from memory or continue to taxonomy/schema/upload while the filled evidence fails validation.
- Follow-up: created-site schema preparation, source-file docs, SKILL inventory, and regression tests now expose the pages/site-info evidence bundle.

- Context: post-create evidence capture after create-site runbook generation.
- Symptom: the normal source-file path could produce a create-site runbook and a created-site evidence brief, but after the browser submit the operator still had to manually translate observed browser state into a long `make_created_site_evidence.py` command. That left room to omit setup-page proof, module routes, submitted fields, forbidden-neighbor-action proof, or the next `prepare_created_site_schema_capture.py` bridge.
- Evidence: `prepare_created_site_evidence_bundle.py` now builds a local bundle from the create-site runbook and created-site evidence brief. It writes a fillable redacted evidence template, notes, an apply command file, a lower-level `make_created_site_evidence.py` command file, and a `prepare_created_site_schema_capture.py` command file. `prepare_confirmed_site_execution.py` and `run_source_file_rehearsal.py` expose the bundle when fresh create preflight is available. Regression tests validate the bundle and summary paths.
- Risk: a browser-created site can be real, but the evidence capture can be incomplete or inconsistently shaped, blocking or weakening artifact binding, schema-capture preparation, and later upload stages.
- Rule: after a gated create-site submit, fill the created-site evidence bundle from redacted browser proof, then run the apply helper. Do not hand-assemble created-site evidence from memory, and do not continue to probes/schema/upload until `created_verified` evidence validates and is applied through `prepare_created_site_schema_capture.py`.
- Follow-up: confirmed execution, source-file rehearsal, docs, and regression tests now expose the post-create evidence bundle.

- Context: created-site evidence bundle apply after the gated create-site browser submit.
- Symptom: the bundle made post-submit proof fields explicit, but the preferred next step still required manually copying many filled-template values into a long `make_created_site_evidence.py` command and then separately running schema-capture preparation. That made the bridge from browser proof to created-site binding fragile.
- Evidence: `apply_created_site_evidence_bundle.py` now consumes `created-site-evidence.filled-template.json`, validates it against the source bundle context, writes standard `created-site-evidence.json`, and can immediately run `prepare_created_site_schema_capture.py` when package/artifact context is provided. `prepare_created_site_evidence_bundle.py` writes `apply-created-site-evidence-bundle-command.txt`, and regression tests cover evidence writing, chained schema-capture preparation, and source-context drift rejection.
- Rule: after browser create-site proof, fill the bundle template and run the apply helper instead of hand-copying fields into `make_created_site_evidence.py`. Use the lower-level make command only as a diagnostic fallback; schema-capture preparation remains local-only and does not create probes or upload content.
- Follow-up: SKILL inventory and source-file workflow docs now point operators at the apply helper as the preferred bridge.

- Context: source next-stage handoff at `created_site_binding` after filled created-site evidence bundle support.
- Symptom: even after the apply helper existed, `prepare_source_next_stage.py` only emitted a schema-capture command when a completed `created-site-evidence.json` path was supplied. Operators using the normal source execution status still had to leave the one-stage handoff and manually locate the bundle apply command, which reintroduced path drift and hand-copy risk.
- Evidence: `prepare_source_next_stage.py` now accepts `--created-site-evidence-bundle` and `--filled-created-site-evidence-template`. At `currentStage=created_site_binding`, it emits `apply_created_site_evidence_bundle.py --prepare-created-site-schema-capture` with package, artifact readiness, review packet, confirmation, and execution-plan context from the current status. Regression tests cover this hybrid bundle-apply path.
- Rule: at `created_site_binding`, use the next-stage handoff as the controller. Pass either `--created-site-evidence` for an existing validated evidence file, or pass the bundle plus filled template so the handoff emits the apply helper. Do not bypass the handoff by manually copying bundle fields into lower-level commands.
- Follow-up: `SKILL.md`, `source-files-to-site-package.md`, `prepare_source_next_stage.py`, and next-stage regression tests now encode bundle apply routing.

- Context: created-site evidence bundle after source-context propagation was added to create-site handoff and runbook.
- Symptom: `confirmed-create-site-handoff.json` and `create-site-browser-runbook.json` preserved `contentGoalCoverage`, `contentQualityReview`, `wikiReview`, and `confirmationDecisionMatrix`, but the created-site evidence bundle itself did not expose those fields. An operator filling only the bundle template after the browser submit could lose the user-reviewed wiki/coverage/deferral context before `make_created_site_evidence.py` and schema-capture preparation.
- Evidence: `prepare_created_site_evidence_bundle.py` now copies the four source-context fields into both `evidence-bundle.json` and `created-site-evidence.template.json`, and validates that the bundle has complete coverage, quality warnings shape, readable wiki index pointer, and a non-empty confirmation decision matrix. Regression tests cover the direct bundle builder and the source-file rehearsal fast path.
- Rule: every evidence bundle that bridges a confirmed source package into browser proof must carry the same source-context contract as the handoff/runbook. If `contentGoalCoverage`, `contentQualityReview`, `wikiReview`, or `confirmationDecisionMatrix` is missing from a post-confirmation browser evidence bundle, regenerate the bundle before browser mutation or evidence fill.

- Context: created-site evidence bundle after confirmed create-site handoff/runbook began preserving full `contentCounts`.
- Symptom: the create-site handoff and runbook carried `contentCounts`, but the post-submit created-site evidence bundle still preserved only the older source-context fields. This could keep user-reviewed wiki/deferral context but drop the confirmed pages/products/posts/forms/media/navigation/site-info scope before artifact binding and schema-capture preparation.
- Evidence: `prepare_created_site_evidence_bundle.py` now copies `contentCounts` into both `evidence-bundle.json` and `created-site-evidence.template.json`, requires pages/products/posts counts, and validates optional forms/media/navigationItems/siteInfoFields counts when present. Regression tests cover count preservation and missing-count rejection.
- Risk: a new-site browser submit can be correctly authorized and proven, but the immediate evidence scaffold can narrow the source-file objective from a complete site scope to a shell-site proof, making downstream upload planning easier to under-scope.
- Rule: created-site evidence bundles are part of the same `contentCounts` continuity chain as create-site handoffs, runbooks, created-site binding, schema capture, sample, batch, and final acceptance. Counts remain scope metadata only; they do not prove site creation, authorize uploads, or replace browser evidence.

- Context: pages/site-info and taxonomy evidence bundles after created-site artifact binding.
- Symptom: created-site binding and schema-capture preparation preserved `contentGoalCoverage`, `contentQualityReview`, `wikiReview`, and `confirmationDecisionMatrix`, but the generated pages/site-info and taxonomy handoffs/bundles could omit the same source context. An operator filling only those post-create evidence templates could therefore lose the user-reviewed page/site-info/taxonomy scope and accepted/deferral matrix before applying pages or taxonomy proof.
- Evidence: `prepare_created_site_schema_capture.py` now injects the created-site binding source context into the generated pages/site-info and taxonomy handoffs. `prepare_pages_site_info_evidence_bundle.py` and `prepare_taxonomy_evidence_bundle.py` copy that context into both bundle and fill template when present, and validate that all four source-context fields are complete together. Regression tests cover direct bundle preservation and the created-site schema-capture main path.
- Rule: every post-confirmation browser evidence bundle that advances source execution must preserve the same source-context contract as created-site binding. If pages/site-info or taxonomy handoff/bundle/template drops `contentGoalCoverage`, `contentQualityReview`, `wikiReview`, or `confirmationDecisionMatrix`, regenerate it from current created-site binding before browser mutation or evidence fill.

- Context: confirmed execution and source-file rehearsal after create-site runbook support was added.
- Symptom: the standalone next-stage handoff could build `create-site-browser-runbook.json`, but the full `prepare_confirmed_site_execution.py` / `run_source_file_rehearsal.py` path still only exposed the confirmed create-site handoff and then advanced source status to `created_site_binding`. Operators starting from the normal source-file entrypoint could miss the runbook and fall back to manual browser steps.
- Evidence: `prepare_confirmed_site_execution.py` now builds and validates `create-site-browser-runbook.json` whenever fresh create preflight produces a confirmed create-site handoff. `run_source_file_rehearsal.py` exposes `confirmedCreateSiteRunbook`, and regression tests assert the runbook exists, points to the handoff, and keeps `browserStepsExecutable=false`.
- Risk: a correct local source-file rehearsal can still be operationally brittle if the normal summary hides the exact browser checklist for the first remote mutation.
- Rule: when a source-file run reaches `create_site_handoff_ready`, the summary artifacts must expose both the confirmed handoff and the non-executable browser runbook. Use the runbook for action-time authorization/gate/browser execution; do not reconstruct create-site clicks from memory.
- Follow-up: confirmed execution, source-file rehearsal, docs, and regression tests now expose the runbook on the normal path.

- Context: create-site handoff after user confirmation in source-file-to-site runs.
- Symptom: `sourceExecutionStatus.currentStage=create_site_handoff` could expose a valid confirmed handoff, but `prepare_source_next_stage.py` still treated the boundary as abstract browser work. The operator had to jump from handoff text to browser steps manually, increasing the risk of skipping the runbook, omitting source-context review, or bundling content upload/theme/domain actions into the same create-site authorization.
- Evidence: `build_create_site_runbook.py` is now wired into `prepare_source_next_stage.py` for `create_site_handoff`. The next-stage handoff emits a local `build_create_site_runbook.py` command, keeps `browserStepsExecutable=false`, carries content goal/quality/wiki/confirmation context, requires action-time authorization and `check_pre_mutation_gate.py --action create_site`, and stops at created-site evidence. Regression tests cover direct runbook generation and next-stage routing.
- Risk: after a user confirms the generated site package, an agent can overrun the first remote mutation boundary by treating the confirmed handoff as executable browser permission or by inventing click steps from memory.
- Rule: `create_site_handoff` is a local runbook-preparation stage before browser mutation. Build and validate the create-site runbook first; only after current authorization and the create-site gate pass may the browser submit once, then it must stop and capture created-site evidence.
- Follow-up: `SKILL.md`, `source-files-to-site-package.md`, `prepare_source_next_stage.py`, and create-site runbook tests now encode the bridge.

- Context: final frontend audit for source-file-to-site runs.
- Symptom: final source-run acceptance could re-open the redacted frontend audit report and compare upstream source-context artifacts, but the `final_frontend_audit` browser-stage result itself was not required to carry the confirmed source context. A standalone route audit could therefore be moved around without proving which user-reviewed wiki and confirmation matrix it belonged to.
- Evidence: `make_final_frontend_audit_stage_result.py` now accepts repeatable `--source-context-artifact` inputs and writes matching `contentGoalCoverage`, `contentQualityReview`, `wikiReview`, and `confirmationDecisionMatrix` into the stage result. `validate_source_run_acceptance.py` includes final frontend audit in the same source-context matching sets and rejects drift. Regression tests cover carried context and final-audit wiki drift.
- Risk: a launch-facing frontend QA artifact can appear valid because routes return HTTP 200 and no Markdown residue exists, while it is not bound to the user-confirmed source wiki, accepted deferrals, or content plan.
- Rule: for source-file runs, the final frontend audit stage result is part of the source-context contract. Build it from the same package/confirmation/binding context and reject it if it drops or changes the wiki review, quality review, content-goal coverage, or confirmation decision matrix.
- Follow-up: source-file docs, final audit generator, final acceptance validator, and regression tests now enforce this binding.

- Context: source confirmation brief before user content-intent approval.
- Symptom: the brief exposed `suggestedAcceptedFields` and `suggestedAcceptedDeferrals`, but did not present a single per-field decision surface. A user or operator could miss whether every `confirmationFields` item had been explicitly accepted or deferred before moving to execution preparation.
- Evidence: `make_source_confirmation_brief.py` now writes `confirmationDecisionMatrix`, with one row per confirmation field and decision `accept` or `defer`. `validate_source_confirmation_brief.py` rejects missing rows, extra rows, unsupported decisions, uncovered fields, and drift from the review packet. The Markdown brief renders a `Confirmation Decision Matrix` section.
- Risk: content confirmation can look complete while launch-adjacent fields such as contact, legal company name, domain, tracking, media, taxonomy, or forms are not visibly accepted or deferred.
- Rule: before preparing confirmed execution artifacts, use the confirmation decision matrix as the user-facing checklist. Every confirmation field must be either accepted from source/user intent or explicitly deferred with a decision and reason.
- Follow-up: confirmation brief generation, validation, Markdown output, docs, and regression tests now enforce the matrix.

- Context: `run_source_file_rehearsal.py` after the standalone rehearsal-summary validator was added.
- Symptom: the validator existed, but the main source-file rehearsal wrapper still required the operator to remember a separate validation command. That left a gap where freshly generated summaries could be shown for confirmation or carried into browser work without an automatically written validation artifact.
- Evidence: `run_source_file_rehearsal.py` now writes `source-file-rehearsal-validation.json`, fails immediately if the generated summary is invalid, and adds `artifacts.sourceFileRehearsalValidation` plus top-level `sourceFileRehearsalValidation` to the final summary. Regression tests assert the validation artifact exists for refinement, confirmation, and create-site-handoff-ready runs.
- Risk: a file-to-wiki run can depend on human memory for the first operator index validation, especially across long sessions or copied handoffs.
- Rule: the wrapper must self-validate its own summary before returning it. Use manual `validate_source_file_rehearsal.py` only for reused, copied, or older summaries.
- Follow-up: source-file docs and source-file rehearsal tests now encode automatic summary validation.

- Context: local source-file rehearsal before user confirmation or browser continuation.
- Symptom: `run_source_file_rehearsal.py` wrote a rich `source-file-rehearsal-summary.json`, but there was no standalone validator for reusing that summary later. A copied or hand-edited summary could drift from its package, review packet, confirmation brief, objective audit, or confirmed execution artifacts before the operator asked for content confirmation or continued to browser work.
- Evidence: `validate_source_file_rehearsal.py` now reopens and validates the rehearsal summary, package/review packet when review-ready, confirmation brief, objective audit, and confirmed execution artifact pointers. Regression tests reject review-packet drift and objective-audit next-blocker drift, and prove CLI JSON validation output is parseable.
- Risk: an operator can treat a stale or edited rehearsal summary as a valid bridge from user files to confirmation or browser work, causing wrong counts, wrong next stage, or overclaiming remote readiness.
- Rule: after every `run_source_file_rehearsal.py` run, validate `source-file-rehearsal-summary.json` before showing the confirmation brief, reusing the run in a later turn, or continuing to browser site creation/schema/upload stages.
- Follow-up: source-file docs and SKILL script inventory now include the rehearsal-summary validator.

- Context: final source-run acceptance for probe/test cleanup after public frontend audit.
- Symptom: final source-run acceptance accepted cleanup evidence based on `siteKey` and a broad `status` value, but did not directly prove that probe candidates were cleaned or that no candidates remained after scanning relevant surfaces.
- Evidence: `validate_source_run_acceptance.py` now directly validates cleanup evidence. If `cleanedCandidates` is non-empty it reuses `validate_probe_cleanup_evidence.py`; if no candidates were cleaned, it requires `noCandidatesVerified=true`, non-empty `scannedSurfaces`, and backend/frontend verification. Regression tests reject a `completed` cleanup artifact that omits no-candidate scan proof.
- Risk: a file-to-site run can be accepted while `Codex Probe`, `Delete Me`, or other test entries still exist as backend rows or public pages.
- Rule: final acceptance must treat cleanup evidence as direct proof, not a status label. A no-op cleanup is valid only when the operator proves the relevant backend/frontend surfaces were scanned and no candidates remained.
- Follow-up: final acceptance validator and source-run acceptance regression tests now enforce cleanup proof.

- Context: final source-run acceptance for public frontend launch quality.
- Symptom: final source-run acceptance checked the final frontend audit stage result's `status` and `blockers`, but did not reopen the redacted frontend audit report, inputs summary, or expected-status map. A hand-written `completed` result could therefore hide route coverage gaps, HTTP mismatches, raw Markdown residue, DOM/rich-text issues, or image issues.
- Evidence: `validate_source_run_acceptance.py` now validates the final audit artifact as an `allincms_browser_stage_result`, requires `stageId=final_frontend_audit`, resolves the redacted audit report pointer, and re-runs the final frontend report summarizer plus expected-route coverage checks when summary/status artifacts are provided. Regression tests reject a completed final audit result whose underlying report still contains a `literal_bold` DOM/rich-text issue.
- Risk: a source-file-to-site run can be marked accepted while the public frontend still has visitor-visible formatting or route problems.
- Rule: final source-run acceptance must treat final frontend audit stage results as pointers to direct frontend proof. Reopen and re-evaluate the redacted audit report at the final gate instead of trusting the status string alone.
- Follow-up: final acceptance validator and source-run acceptance regression tests now recheck frontend audit report quality.

- Context: final source-run acceptance after forms/media/settings evidence began preserving `wikiReview` in source execution status.
- Symptom: final source-run acceptance still performed only lightweight forms/media/settings checks and compared `wikiReview` across status/package/review/confirmation/launch/binding, but not the forms/media/settings artifact itself. A final acceptance call could therefore bypass the dedicated forms/media/settings validator or accept a forms/settings artifact whose source-wiki proof drifted from the confirmed package.
- Evidence: `validate_source_run_acceptance.py` now re-runs `validate_forms_media_settings_evidence.py` logic directly and includes forms/media/settings evidence in the final `wikiReview` consistency set. Regression tests reject missing media deferral proof and reject forms/media/settings `wikiReview` drift at final acceptance.
- Risk: a file-to-wiki-to-site run can be marked accepted even though launch-adjacent forms, media, domains, tracking, or settings evidence would fail its own validator, or belongs to a different user-reviewed wiki.
- Rule: final source-run acceptance must revalidate forms/media/settings evidence directly and treat it as part of the final source-context contract. Do not rely only on source status or a few flags at the completion gate.
- Follow-up: final acceptance validator and source-run acceptance tests now enforce direct forms/media/settings validation plus `wikiReview` matching.

- Context: source-file-to-site hardening for the post-batch `forms_media_settings` stage.
- Symptom: upstream source package, confirmation, artifact binding, schema/sample, batch, and launch helpers preserved `wikiReview`, but `forms/media/settings` evidence could advance the source status without carrying the same source-wiki proof.
- Evidence: `summarize_source_execution_status.py` now includes forms/media/settings evidence in `wikiReview` consistency checks and blocks a source-file run when valid forms/media/settings evidence omits or drifts from the upstream `wikiReview`. `validate_forms_media_settings_evidence.py` validates `wikiReview` shape when present. Regression tests cover successful propagation, missing `wikiReview`, and drift.
- Risk: a file-to-wiki-to-site run can prove content upload from one source wiki, then use forms/media/settings evidence from another context or no source context before launch acceptance.
- Rule: for source-file runs, forms/media/settings evidence is part of the final launch chain and must preserve the same `wikiReview` as the confirmed source package. Missing or mismatched `wikiReview` blocks before launch acceptance.
- Follow-up: status summary, forms/media/settings evidence validation, and regression tests now enforce the binding.

- Context: request-analysis maintenance after checking whether the current skill can help with batch upload.
- Symptom: `validate_manifest.py --help` previously behaved like a missing manifest path instead of a help entrypoint.
- Evidence: the script now uses `argparse`; `python3 skills/allincms-bulk-content-upload/scripts/validate_manifest.py --help` prints the purpose, `--json`, and `--require-schema-verified`. Regression coverage in `test_validate_manifest_cli.py` includes JSON success, schema-gate failure, and help output.
- Risk: without a discoverable help surface, a future operator or read-only agent can misread the batch validator as broken during upload preparation.
- Rule: use `validate_manifest.py --help` for flag discovery, but do not treat CLI discoverability as upload readiness. Batch upload still requires current-site schema capture, `--require-schema-verified`, one manifest-sample backend/frontend proof, authorization, pre-mutation gate, progress evidence, and final frontend audit.
- Follow-up: helper usability is fixed; live upload proof remains unverified until the exact site/content-type gates pass.

- Context: local source-file rehearsal for file-to-wiki-to-site runs before user content confirmation.
- Symptom: `prepare_source_site_package.py` could detect non-blocking `contentQuality.warnings`, but the review packet and confirmation brief did not expose those warnings. A package could appear `reviewReady=true` while the user-facing confirmation surface hid risks such as missing post categories or short copy.
- Evidence: `contentQualityReview` is now written into `source-package-review-packet.json`, propagated through `confirmationReview`, copied into `source-confirmation-brief.json`, and rendered in `source-confirmation-brief.md`. Validators require the quality review to match the source package and require `reviewRequired == bool(warnings)`. A local rehearsal confirmed `posts_present_without_post_categories` appears in the Markdown brief and suggested confirmation text.
- Risk: users can confirm a source package without seeing content-quality warnings, then later hit taxonomy/homepage/module gaps during browser upload or launch QA.
- Rule: review-ready means structurally confirmable, not risk-free. Non-blocking quality warnings must be visible in both JSON and Markdown confirmation surfaces before asking the user to confirm content intent.
- Follow-up: review-packet, source-rehearsal, confirmation-brief helpers and regression tests now propagate and validate `contentQualityReview`.

- Context: confirmation and execution-plan handoff after the user confirms a source package.
- Symptom: after quality warnings became visible in the review/brief surface, the confirmation record and confirmed execution plan still risked dropping `contentQualityReview`, leaving downstream browser stages without the quality-risk context the user saw.
- Evidence: `confirmation-record.json` now copies `contentQualityReview` from the review packet, `confirmed-site-execution-plan.json` carries the same object, and validators reject confirmation records whose quality review drifts from the review packet. A confirmed local rehearsal proved `posts_present_without_post_categories` is present in review packet, confirmation brief, confirmation record, and execution plan.
- Risk: an operator can correctly show warnings before confirmation, then continue from a later execution artifact that no longer exposes those warnings when creating pages, taxonomy, products, posts, or launch QA handoffs.
- Rule: quality-risk context must survive confirmation. Treat `contentQualityReview` as part of the confirmed content contract, not merely a pre-confirmation display field.
- Follow-up: confirmation helper, confirmation validator, execution-plan builder, and confirmation/execution regression tests now preserve and check `contentQualityReview`.

- Context: source execution status and next-stage handoff after confirmation/execution artifacts are prepared.
- Symptom: even after `contentQualityReview` survived confirmation and execution-plan generation, the source status dashboard and next-stage handoff could omit it. That made the browser-stage entry point look clean while the confirmed package still had non-blocking quality risks.
- Evidence: `allincms_source_execution_status` now carries `contentQualityReview` and `contentQualityReviewIssues`; `allincms_source_next_stage_handoff` copies the same object into browser/helper handoffs and validates `reviewRequired == bool(warnings)`. A confirmed local rehearsal proved `posts_present_without_post_categories` appears in both confirmed source execution status and source next-stage handoff.
- Risk: operators can enter create-site/schema/pages/upload browser stages without the quality-risk context that was shown and confirmed earlier, leading to missed taxonomy, navigation, or launch-QA repairs.
- Rule: the status dashboard and next-stage handoff are browser-stage control surfaces; they must carry confirmed content-quality warnings alongside content goal coverage.
- Follow-up: source status, next-stage handoff, and regression tests now preserve `contentQualityReview` through the browser-stage entry boundary.

- Context: confirmed create-site handoff as the first remote-mutation entry after local package confirmation.
- Symptom: source status and next-stage handoff could preserve `contentQualityReview`, but `confirmed-create-site-handoff.json` itself still only carried content counts and `contentGoalCoverage`. The browser operator could submit the site creation action without seeing the confirmed quality-risk context.
- Evidence: `confirmed-create-site-handoff.json` now copies `contentQualityReview` from the confirmed execution plan and validates it against the review packet and confirmation record. The pre-submit checklist tells the operator to review content-quality warnings before creating the site. A local confirmed create-preflight rehearsal proved `posts_present_without_post_categories` appears in the create-site handoff.
- Risk: the first live mutation can proceed with a clean-looking handoff while the confirmed package still requires post-create taxonomy/page/upload care.
- Rule: every browser-mutation handoff derived from a source package must carry the confirmed `contentQualityReview`, starting with create-site handoff.
- Follow-up: create-site handoff builder, validator, prepare-confirmed-execution tests, and create-site handoff regression tests now preserve quality warnings at the first mutation boundary.

## 2026-07-01 Official Docs Alignment Findings

- Context: applying manifest sample evidence when products and posts samples are verified in separate browser stages.
- Symptom: `apply_manifest_sample_upload.py` already accepted `--existing-sample-evidence`, but the apply summary did not expose the merged sample set and regression coverage did not prove a dual-content package could advance after merging prior sample evidence with the current sample.
- Evidence: the helper now exposes `existingSampleEvidence` and `mergedSampleEvidence` in its summary. Regression coverage proves an existing posts sample plus current products sample advances source status to `batch_upload` and records `contentTypeCoverage.sampleEvidence = [posts, products]`.
- Risk: an operator can have valid sample proof for both content types but fail to see that the apply helper carried both forward, or accidentally diagnose a stuck `sample_upload` stage without checking the merged evidence set.
- Rule: for multi-content sample stages, preserve every successful content-type sample evidence path across apply calls. Pass prior samples with `--existing-sample-evidence`; inspect `mergedSampleEvidence` and source status content-type coverage before batch preparation.
- Follow-up: manifest sample apply summary, sample apply tests, and source-file docs now expose and verify merged sample evidence.

- Context: applying batch upload evidence when a confirmed package contains both products and posts.
- Symptom: `apply_batch_upload_publish.py` refreshed source execution status with only the current content type's batch validation. After products and posts were uploaded in separate browser stages, the later apply call could lose the earlier validation path and keep the source dashboard blocked at `batch_upload`.
- Evidence: the helper now accepts repeatable `--existing-batch-validation`, merges those paths with the current validation, and exposes both `existingBatchValidation` and `mergedBatchValidation` in the apply summary. Regression coverage proves a package requiring products and posts advances only when an existing posts validation and current products validation are merged.
- Risk: operators can rerun a valid batch apply for the second content type and still see an incomplete dashboard, or incorrectly repeat uploads because the previous content type proof was not carried forward.
- Rule: for multi-content batch stages, preserve every successful content-type validation path across apply calls. Pass prior validations with `--existing-batch-validation`; the source dashboard should evaluate the merged set.
- Follow-up: batch apply helper, batch apply tests, and source-file docs now encode merged batch validation.

- Context: source execution dashboard after final source-run acceptance began checking confirmed pages/products/posts counts.
- Symptom: final acceptance could reject partial page/product/post proof, but `summarize_source_execution_status.py` could still advance past `pages_site_info_execution` or `batch_upload` based on boolean validity and content-type presence alone, leaving the count shortfall to be found only at the final gate.
- Evidence: source execution status now derives expected counts from `contentGoalCoverage.counts`, blocks `pages_site_info_execution` when validation `pageCount` is missing or lower than planned pages, and blocks `batch_upload` when posts/products batch validation lacks `manifestItemCount`/`progressCount` or reports fewer items than the confirmed plan. Regression tests cover a two-page plan with `pageCount=1` and a two-product plan with product batch count `1`.
- Risk: an operator can continue schema capture, sample upload, forms/settings, or launch QA after only a subset of planned pages/products/posts has actually been proven, then hit a late final-acceptance failure.
- Rule: stage dashboards must enforce count coverage at the earliest relevant stage. Page count gaps stop at `pages_site_info_execution`; products/posts count gaps stop at `batch_upload`; final source-run acceptance remains the backstop.
- Follow-up: source execution status, source-file docs, and regression tests now enforce early count blocking.

- Context: final source-run acceptance for the user's requested file-to-wiki-to-site workflow.
- Symptom: final acceptance already required matching `contentGoalCoverage`, same `siteKey`, sample evidence, batch validation, forms/media/settings, frontend audit, cleanup, and closeout, but it could still accept artifacts that proved only one item per content type if the confirmed plan later contained more pages, products, or posts.
- Evidence: `validate_source_run_acceptance.py` now compares confirmed `contentGoalCoverage.counts.pages/products/posts` with final proof counts. Pages/site-info validation must expose `pageCount`; posts/products batch validation must expose `manifestItemCount` or `progressCount`. Regression coverage rejects a two-product confirmed plan when the final product batch validation proves only one item.
- Risk: an operator can overclaim that a source-file site is complete after one sample or a partial batch, even though the user-confirmed package promised more single pages, products, or articles.
- Rule: final source-run acceptance must prove quantity coverage as well as stage coverage. Do not mark a source-file-to-site run complete until page and batch validation counts are at least the confirmed source package counts for pages, products, and posts.
- Follow-up: source-file docs, launch acceptance docs, final acceptance validator, and regression tests now enforce the count gate.

- Context: automatic next-stage routing after source execution helpers refresh status.
- Symptom: `prepare_source_next_stage.py` could turn a status into a next-stage handoff, but callers still had to remember to run it separately after confirmation preparation, created-site binding, pages/site-info evidence, taxonomy evidence, schema-manifest preparation, sample proof, batch proof, or launch acceptance.
- Evidence: the key source execution orchestrators and apply helpers now write `artifacts.sourceNextStageHandoff` and a `sourceNextStage` summary after they refresh `allincms_source_execution_status`. Regression tests assert the handoff exists and points to the expected next currentStage.
- Risk: a workflow can correctly refresh status but then stall or jump stages because the operator forgets the extra next-handoff command and hand-copies the next helper manually.
- Rule: after any source execution orchestrator/apply helper, read the summary's `artifacts.sourceNextStageHandoff` first. Use manual `prepare_source_next_stage.py` only when a lower-level diagnostic status lacks the handoff.
- Follow-up: confirmed execution, created-site preparation, pages/site-info apply, taxonomy apply, schema-manifest sample preparation, manifest-sample apply, batch apply, launch apply, docs, and tests now emit or expect the next-stage handoff.

- Context: source execution chain routing after the status dashboard became the authority for file-to-site runs.
- Symptom: `summarize_source_execution_status.py` exposed `currentStage`, blockers, and evidence paths, but operators still had to hand-copy paths into the next helper or browser handoff. This made it easy to miss context such as confirmation, artifact readiness, pages/site-info validation, taxonomy validation, or sample evidence while moving toward site creation/upload.
- Evidence: `prepare_source_next_stage.py` now reads one `allincms_source_execution_status` JSON and writes an `allincms_source_next_stage_handoff` with context paths, required inputs, forbidden actions, and a local helper command only when the next stage is locally preparable/applicable. Browser-only stages are marked `browserWorkRequired=true` without fake local mutation commands.
- Risk: a source-file-to-site run can accidentally jump from status text to a later upload command, omit an upstream evidence path, or treat browser-only work as locally executable.
- Rule: after every source status refresh, run `prepare_source_next_stage.py` and follow its one-stage handoff. If it emits placeholders, gather validated evidence first. If it reports browser work, use the stage-specific authorization/gate/evidence path and refresh status again after the browser stage.
- Follow-up: `SKILL.md`, `source-files-to-site-package.md`, the next-stage helper, and regression tests now encode source-status-to-next-stage routing.

- Context: source-package confirmation gate hardening for the files-to-wiki-to-site workflow.
- Symptom: review packets already surfaced forms/media counts and policy summaries, but confirmation validation could accept a record that omitted explicit decisions for `contentPlan.forms`, `contentPlan.media`, public contact, legal company name, custom domain, or tracking code.
- Evidence: `validate_source_package_confirmation.py` now derives required accepted fields from the package confirmation gate, treats contact/domain/tracking surfaces as required accept-or-defer decisions, rejects fields that are both accepted and deferred, and verifies every review-packet `confirmationFields` item is covered. Regression tests cover missing decision deferrals.
- Risk: an operator can let a user confirm only page/product/post intent, then create a site whose forms, media, public contact, legal identity, domain, or tracking decisions are still implicit and only fail at launch QA.
- Rule: package confirmation must cover every review-packet confirmation field. Content surfaces belong in `acceptedFields`; launch-adjacent or missing-source fields such as public contact, legal company name, custom domain, and tracking code must either be truly accepted from source/user input or explicitly deferred with decision and reason.
- Follow-up: source-file docs, confirmation helper, validator, and regression tests now enforce accept-or-defer coverage before execution-plan generation.

- Context: source-file refinement workflow after readable Markdown wiki export was added.
- Symptom: non-review-ready runs exposed validation issue strings, but there was no deterministic field-level plan telling the next AI pass which `source-wiki.json` field to rewrite, source, confirm, or defer.
- Evidence: `make_source_wiki_refinement_plan.py` now converts source-wiki/package/review issues into `sourceWikiTarget`, classification, and suggested action entries. `prepare_source_site_package.py` and `apply_refined_source_wiki.py` both write `source-wiki-refinement-plan.json`, and tests cover placeholder and review-ready cases.
- Risk: operators can stall after `needs_source_wiki_refinement`, make broad unsourced rewrites, or miss policy fields such as media, contact/form, taxonomy, and navigation while fixing only product/post copy.
- Rule: when `packageStatus != review_ready` or `reviewReady=false`, read `source-wiki-refinement-plan.json` before editing the wiki. Treat every item as a blocker until the source wiki is repaired, explicitly user-confirmed, or deliberately deferred in the appropriate policy field.
- Follow-up: source-file docs, SKILL.md, refinement helper, orchestrators, and regression tests now encode the refinement checklist.

- Context: source-file workflow audit against the user's requirement that files be organized and distilled into a wiki before generating site/page/product/post content.
- Symptom: the source workflow built `source-wiki.json`, but did not produce human-readable wiki pages by default. Operators could show a review packet or JSON package, but the intermediate wiki layer was not easy to inspect, refine, or hand off.
- Evidence: `export_source_wiki_markdown.py` now exports `index.md`, `site.md`, `pages.md`, `products.md`, and `posts.md` plus a manifest outside the skill package. `prepare_source_site_package.py` and `apply_refined_source_wiki.py` both generate those Markdown wiki artifacts, and tests assert they exist and contain page/product/post content.
- Risk: without readable wiki files, an agent can skip the user's requested "梳理提炼成 wiki" stage, overfit directly to JSON payloads, or make user confirmation harder because the user sees only a compact review packet.
- Rule: every source-file run must treat `source-wiki.json` as the machine contract and `wiki/*.md` as the human review layer. Neither is an AllinCMS upload payload; both must stay outside the skill package and feed package/review/refinement only.
- Follow-up: source-file docs, SKILL.md, orchestrators, exporter, and regression tests now cover readable wiki export.

- Context: source-file-to-site orchestration maintenance after adding pages/site-info, taxonomy, and forms/media/settings stages.
- Symptom: `prepare_source_site_package.py` and `prepare_confirmed_site_execution.py` created source execution status with an older argument set, omitting explicit pages/site-info, taxonomy, and forms/media/settings fields.
- Evidence: both orchestrators now pass the complete source-status argument surface, and their regression tests assert that the generated dashboard includes `pages_site_info_handoff`, `pages_site_info_execution`, `taxonomy_execution_handoff`, `taxonomy_execution`, and `forms_media_settings`.
- Risk: an operator can start from user files or from a confirmed review packet, then trust a stale dashboard that does not expose the same stage order as later upload/launch helpers. Missing fields can hide real blockers in the "files -> wiki -> confirmation -> create site -> upload" path.
- Rule: every orchestrator that refreshes `allincms_source_execution_status` must pass the full current stage surface, even when later evidence paths are empty. Treat omitted stage arguments as command drift, not as proof the stage is not required.
- Follow-up: source-file preparation, confirmed execution preparation, source-file docs, and regression tests now cover the complete status surface.

- Context: request-analysis and local maintenance after the user asked whether the current skill can help with batch upload.
- Symptom: the browser execution/rehearsal flow already had `forms_media_settings` after batch upload, and launch acceptance required forms/media/settings evidence, but `summarize_source_execution_status.py` skipped directly from `batch_upload` to `launch_acceptance`.
- Evidence: source execution status now includes `forms_media_settings` between `batch_upload` and `launch_acceptance`; `apply_batch_upload_publish.py` refreshes status to that stage after valid batch proof, and `apply_launch_acceptance.py` passes the same evidence into the dashboard before marking a run complete.
- Risk: an operator can correctly batch-upload records but then overclaim that the website is launch-ready while forms, media, domains, tracking, or settings are still unverified or not explicitly deferred.
- Rule: when answering whether batch upload is supported, separate content-record batch capability from launch readiness. Batch upload is supported only after schema/sample/authorization gates; after batch proof, the next source-stage gate is `forms_media_settings`, not `complete` or direct launch acceptance.
- Follow-up: source status, apply helpers, batch verification docs, launch acceptance docs, and regression tests now enforce the stage.

- Context: local-only skill maintenance after a from-scratch test-site run hit an empty/blank theme path and the operator was told to use `https://www.allincms.com/docs`.
- Symptom: browser-first exploration can create a blank theme and then spend time forcing designer block insertion, while the official tutorial says to first open the frontend, reuse/edit default template content if present, and create a `默认` preset theme only when the frontend is 404/blank or no usable theme/pages exist.
- Evidence: official docs pages checked: `/docs`, `/docs/quickstart/overview`, `/docs/quickstart/create-site`, `/docs/quickstart/site-build-flow`, `/docs/pages/homepage-basics`, `/docs/pages/create-page`, `/docs/content/add-products`, `/docs/content/add-posts`, `/docs/domains/bind-domain`, and `/docs/launch/launch-checklist`.
- Risk: an operator can overfit to UI probing, create duplicate themes/pages/content, or overclaim launch readiness from backend rows while the public frontend remains empty, 404, unbound, or missing required starter content.
- Rule: for new sites, follow the official sequence first: create site, open frontend, fix theme/homepage if 404 or blank, prefer default-template edits, prepare categories/products/posts before homepage modules, create extra pages only when needed, and finish with frontend click-through launch QA. Use JSON/Server Action capture only to verify or accelerate a documented action after the exact current-site request is captured.
- Follow-up: `SKILL.md`, `site-creation.md`, `create-flows.md`, `interface-inventory.md`, and `launch-acceptance.md` now encode official-docs-first operation.

## 2026-07-01 Live Docs Refresh And Module-Boundary Findings

- Context: documentation-only correction after the user said to check `https://www.allincms.com/docs` and fix the skill from the tutorial rather than random exploration.
- Symptom: prior guidance could still overfit to browser discoveries such as adding `Full Product List (Filtered)` to `/products`, then accidentally treat that as satisfying the official homepage product-module step.
- Evidence: refreshed docs pages `/quickstart/create-site`, `/quickstart/site-build-flow`, `/content/product-categories`, `/content/add-products`, `/content/add-posts`, `/pages/homepage-basics`, `/pages/create-page`, `/content/product-module`, `/content/homepage-featured-products`, `/quickstart/site-settings`, and `/launch/launch-checklist` directly state the flow: open the public site after creation, edit default content first, create 2-3 categories, add 2 products per category, add 3 posts, then configure homepage Header/Banner/Category Showcase/Featured Product List or Recommended Products/Featured News/Footer, and finish with visitor-style frontend/mobile/form/domain checks.
- Risk: an operator can confuse product-list page repair with homepage completion, or keep probing UI/API actions while official prerequisite content counts and public click-through checks are still missing.
- Rule: treat official tutorial gates as the primary stage order. `Full Product List (Filtered)` is a `/products` list-page repair, while homepage product completion requires Category Showcase and Featured Product List or Recommended Products with `Detail Page = /products` and frontend product-card click proof.
- Follow-up: `SKILL.md`, `official-docs-alignment.md`, and `site-creation.md` now call out the refreshed docs evidence and the product-list-vs-homepage module boundary.

## 2026-07-01 Maintenance Command Drift Finding

- Context: local skill inspection used a shell loop to print reference-file headings while grepping for official-docs and JSON terms.
- Symptom: `printf "--- %s\n"` failed because the format string began with `--`, producing `printf: --: invalid option`.
- Evidence: terminal output showed repeated `printf: usage: printf [-v var] format [arguments]` before grep matches.
- Risk: noisy maintenance commands can hide real grep output or make a validation pass look broken when the skill files are not the problem.
- Rule: when printing separators that begin with hyphens in shell loops, use `printf '%s\n' "--- $file"` or `printf -- '--- %s\n' "$file"`.
- Follow-up: use safer separator commands in future local maintenance; no helper script change needed.

- Context: local docs refresh command in zsh used `for path in ...` while fetching official docs snippets.
- Symptom: after assigning to the special zsh variable `path`, commands in the loop failed with `command not found: curl`, `command not found: perl`, and `command not found: sed`.
- Evidence: the first docs fetch worked, but the multi-page loop failed immediately after `path` was set; rerunning with `doc_path` and absolute command paths succeeded.
- Risk: a maintenance or verification command can look like the environment lost standard tools, when the shell command actually broke command lookup by overwriting zsh's tied `$path` array.
- Rule: in zsh examples and ad hoc maintenance loops, never use `path` as a loop variable. Use names such as `doc_path`, `file_path`, or `route_path`; when recovering from a suspected path issue, call standard tools by absolute path for the verification command.
- Follow-up: future skill command examples should avoid `path` loop variables.

- Context: AllinCMS maintenance closeout after a documentation/browser-auth sedimentation turn.
- Symptom: `make_round_maintenance_summary.py` rejected a hand-written `--status incomplete` flag, and `check_round_closeout.py` rejected a closeout whose `--note`, `--round-issue`, and `--changed-files` did not exactly match the generated maintenance summary.
- Evidence: the helper printed `unrecognized arguments: --status incomplete`; after removing it, closeout failed with summary/closeout mismatch errors.
- Risk: operators may treat closeout helpers as loose reporting tools and rewrite the note/issues at the final gate, causing the recorded sedimentation proof to diverge from the summary artifact.
- Rule: for maintenance closeout, do not pass `--status`. Reuse the exact `--sedimentation`, `--note`, every `--round-issue`, and every `--changed-files` value from `make_round_maintenance_summary.py` when invoking `check_round_closeout.py`.
- Follow-up: final closeout commands should be copied from the generated summary or scripted to avoid hand drift.

## 2026-07-01 Chrome Auth And Stale Deep-Link Findings

- Context: switching LAICMS operations from the in-app browser to Chrome because designer interactions in the in-app browser were unstable.
- Symptom: opening an old site designer deep link redirected to `/sign-in`, but Chrome still had an authenticated `workspace.laicms.com/{siteKey}/dashboard` tab for another current site.
- Evidence: current Chrome open tabs showed a signed-in dashboard with account/workspace controls; recent history showed the old `/{oldSiteKey}/themes/.../design` URL, then `/sign-in`, then `/`, `/sites`, and a different current site dashboard.
- Risk: an operator may incorrectly conclude that Chrome is globally logged out, ask the user to log in again, or keep forcing a stale site/theme/page deep link that belongs to an old run and causes repeated redirects.
- Rule: diagnose auth state from current open tabs plus recent route history. A single `/sign-in` redirect after an old deep link means "route/session context mismatch" until proven otherwise. Resume from `/sites` or the currently authenticated site dashboard, refresh the site identity, and regenerate run evidence before using any old deep-link artifact.
- Follow-up: `SKILL.md` now includes the Chrome-specific auth diagnostic rule; do not use old `siteKey/themeId/pageId` URLs as current authority after a redirect.

- Context: follow-up Chrome read-only navigation from a visible site dashboard to target backend modules.
- Symptom: the visible dashboard showed site/account navigation and current counts, but direct navigation to `/products`, `/posts`, `/themes`, and `/routes` redirected to `/sign-in`.
- Evidence: each target module snapshot contained the sign-in form even though the earlier dashboard DOM contained the side navigation and site cards.
- Risk: cached React/dashboard state can be mistaken for a valid authenticated session. Acting on that assumption can cause repeated redirects, stale evidence, or lost browser continuity.
- Rule: before any Chrome mutation, validate auth with a fresh `/sites` load or the exact target module URL. If that fresh navigation redirects to `/sign-in`, stop for user login in Chrome; do not create, save, publish, or replay from a cached dashboard state.
- Follow-up: `SKILL.md` now requires target-module or `/sites` auth proof before Chrome mutations.

## 2026-07-01 In-App Browser Controlled-Tab Recovery Finding

- Context: read-only resume of a temporary AllinCMS theme designer tab in the in-app browser after the user asked to continue there and check status.
- Symptom: `user.openTabs()` initially showed the designer tab, but `claimTab()` failed with a stale tab-id style error; a later `user.openTabs()` returned an empty list even though the controlled tab still existed.
- Evidence: `tabs.list()` and `tabs.selected()` still returned one controlled tab at `https://workspace.laicms.com/{siteKey}/themes/{themeId}/{pageId}/design`; binding to that tab id allowed DOM inspection and proved the designer was loaded, logged in, Active/Published, with Save and Publish disabled.
- Risk: an operator may misdiagnose a Browser client bookkeeping issue as the user having exited, the site being logged out, or the LAICMS tab being closed, then unnecessarily reload, switch browsers, or lose the current designer handoff.
- Rule: when in-app `claimTab()` or `openTabs()` disagrees with visible/known state, check `tabs.list()` and `tabs.selected()` before declaring logout or closure. If a controlled tab is listed, bind to that tab id and verify URL/title/DOM state. Treat the failure as browser-control recovery, not platform failure.
- Follow-up: `SKILL.md` now includes this controlled-tab recovery path near the live tab authority rule.

## 2026-07-01 Media Empty-State Upload Boundary Finding

- Context: read-only media library status check on a temporary AllinCMS build site; no upload dialog was opened, no file was selected, and no remote mutation was performed.
- Symptom: an empty media library showed both a top-level `上传` button and an empty-state `上传` call-to-action under `没有找到媒体` / `上传第一张图片开始使用`, with no media images, no forms, and no file input visible before opening the upload dialog.
- Evidence: redacted backend URL pattern `/{siteKey}/media`, visible controls `搜索媒体...`, `最新`, two `上传` buttons, page size `24`, disabled previous/next pagination, and empty media count.
- Risk: an operator or helper can misclassify duplicate upload labels as two different upload workflows, or treat absence of table headers/images as failed preflight and click upload during a read-only pass.
- Rule: for empty media libraries, duplicate upload buttons are one upload authorization boundary until the current version is captured. Read-only media preflight may rely on backend URL plus search/sort/upload/page-size/empty-state controls. Do not click either upload button or select a file without exact upload authorization and an action record.
- Follow-up: `create-flows.md` now records the duplicate-upload-button empty-state rule.

## 2026-07-01 Skill Validator Path Drift Finding

- Context: local validation after updating the AllinCMS skill from live browser findings.
- Symptom: running `python3 skills/allincms-bulk-content-upload/scripts/quick_validate.py` failed because this skill does not bundle a local `quick_validate.py`.
- Evidence: Python returned `can't open file .../skills/allincms-bulk-content-upload/scripts/quick_validate.py: [Errno 2] No such file or directory`, while `SKILL.md` already points to the system skill-creator validator path.
- Risk: an operator can misreport validation failure or skip the actual skill validator by using a stale handoff command.
- Rule: after changing this skill package, run the bundled AllinCMS hygiene audit plus the system validator path from `SKILL.md`: `python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/allincms-bulk-content-upload`.
- Follow-up: no helper script change needed; use the documented validator command as authority when handoff notes disagree.

## 2026-07-01 Media Upload Dialog Probe And Helper Findings

- Context: authorized media-library upload probe on a temporary AllinCMS build site using the in-app browser; the probe stopped before storage upload because file selection was unsupported by the current API surface.
- Symptom: the media upload dialog opened and exposed `input type=file multiple=true`, accepted type text `PNG、JPG、GIF、WebP，最大 5MB`, and a disabled upload button before file selection. The current Playwright locator surface did not expose `setInputFiles`, so no file could be selected and no media row was created.
- Evidence: redacted backend URL pattern `/{siteKey}/media`, dialog text `上传媒体`, file input present while dialog open, upload button disabled before file, dialog cancelled, no file input after cancel, no images/media rows after cancel.
- Risk: an operator can overclaim media upload proof from merely opening the dialog, or leave the dialog in a half-upload state after file selection fails.
- Rule: media upload proof requires file selection, upload request/storage response, backend media row, public URL/dimensions, and cleanup candidate proof. If the browser cannot select files, cancel the dialog, verify no media row was created, and mark the stage as `file_selection` blocked. Use Chrome or another filechooser-capable runtime only after fresh workspace auth is proven.
- Follow-up: `create-flows.md` now records the observed upload dialog fields and blocked-stage handling.

## 2026-07-02 Default Theme Bootstrap And Maintenance Findings

- Context: local skill maintenance for the source-files-to-site goal after a created test site reached the pages/site-info stage while frontend/theme setup still needed a reliable blank-site recovery path.
- Symptom: `create_theme` was supported as a generic mutation, and docs described choosing `默认`, but there was no dedicated runbook/evidence validator that separated default theme creation from theme activation and public route proof.
- Evidence: new helpers prepare and validate a default-theme bootstrap stage. The runbook emits separate `create_theme` and `activate_theme` authorization commands, requires preset `默认`, and keeps browser steps non-executable until action-time authorization and pre-mutation gates pass. The validator rejects blank/0-page themes, missing public path checks, raw header values, and `businessContentComplete=true`.
- Risk: an operator can create a blank or default theme, see a toast or backend row, and continue to pages/products/posts while the public site is still blank, unbound, or only generic template content.
- Rule: when a new site's frontend is 404/blank and themes/pages are missing or unusable, run the default-theme bootstrap stage before source pages/site-info and content upload. Treat passing bootstrap evidence as foundation proof only; business copy, homepage modules, taxonomy, product/post schema capture, sample upload, batch upload, forms/media/settings, and launch acceptance remain separate gates.
- Follow-up: `prepare_default_theme_bootstrap.py`, `validate_default_theme_bootstrap_evidence.py`, action gates, docs, and tests now encode the default-theme bootstrap boundary.

- Context: continuing the source-file-to-site chain after default-theme bootstrap evidence validates.
- Symptom: the runbook and validator could prove the default theme was created/activated, but later helpers still consumed the original created-site evidence whose setup-page observations came from the pre-bootstrap blank/empty theme state.
- Evidence: `apply_default_theme_bootstrap.py` now validates bootstrap evidence, writes `default-theme-bootstrap-validation.json`, emits `created-site-evidence.after-default-theme-bootstrap.json`, and regression coverage verifies the refreshed evidence passes `validate_run_evidence.py` while marking `businessContentComplete=false`.
- Risk: an operator can perform the correct browser bootstrap and still prepare pages/site-info, taxonomy, schema capture, or upload work from stale evidence that says themes/routes were missing or unusable.
- Rule: after default-theme bootstrap validation, apply the bootstrap evidence back into created-site evidence and use the refreshed file as the next `--created-site-evidence` input. Do not continue from the stale pre-bootstrap created-site evidence after a blank-site recovery.
- Follow-up: `apply_default_theme_bootstrap.py`, its regression tests, `SKILL.md`, `site-creation.md`, and `create-flows.md` now encode the apply-back step.

- Context: source next-stage routing after default-theme bootstrap evidence exists.
- Symptom: `prepare_source_next_stage.py` could route missing pages/site-info or taxonomy handoffs back through `prepare_created_site_schema_capture.py`, but did not know how to emit the bootstrap apply command when the operator had already captured default-theme bootstrap evidence.
- Evidence: the next-stage helper now accepts `--default-theme-bootstrap-runbook` and `--default-theme-bootstrap-evidence`. For post-create stages such as `pages_site_info_handoff`, it emits `apply_default_theme_bootstrap.py` before downstream handoff regeneration. Regression coverage checks that the apply command takes precedence over `prepare_created_site_schema_capture.py`.
- Risk: after correct browser bootstrap, an operator can still hand-run the wrong next command and rebuild handoffs from stale blank-theme evidence.
- Rule: when a status is blocked after site creation and default-theme bootstrap evidence exists, regenerate the source next-stage handoff with the bootstrap runbook/evidence. Apply bootstrap first, then rerun downstream preparation with `created-site-evidence.after-default-theme-bootstrap.json`.
- Follow-up: `prepare_source_next_stage.py`, next-stage regression tests, `SKILL.md`, and `source-files-to-site-package.md` now encode this routing.

- Context: reducing the manual gap after default-theme bootstrap apply-back in source-package runs.
- Symptom: `apply_default_theme_bootstrap.py` could write refreshed created-site evidence, but the operator still had to manually run `prepare_created_site_schema_capture.py` with the new evidence and the same source-package context.
- Evidence: `apply_default_theme_bootstrap.py` now accepts `--prepare-created-site-schema-capture` plus artifact-readiness/package/confirmation/execution-plan context. Regression coverage proves it writes the refreshed evidence, downstream created-site schema-capture preparation summary, source execution status, and source next-stage handoff.
- Risk: a correct bootstrap apply can still stall or drift if the next command is hand-copied with the old evidence path or missing package context.
- Rule: for source-package runs, prefer the chained local apply when context paths are available. The helper remains local-only: it applies evidence and regenerates handoffs/status, but does not create probes, save pages, upload content, publish, or mutate AllinCMS.
- Follow-up: `apply_default_theme_bootstrap.py`, its tests, `SKILL.md`, `site-creation.md`, and `source-files-to-site-package.md` now document and verify the chained preparation path.

- Context: local shell maintenance while looking for theme-related tests.
- Symptom: zsh reported `no matches found` for an unmatched glob such as `skills/.../test_*theme*`, even though the intent was only to list possible files.
- Evidence: terminal output showed `zsh:1: no matches found: skills/allincms-bulk-content-upload/scripts/test_*theme*`.
- Risk: a harmless file lookup can interrupt a maintenance run and look like a repository or script problem.
- Rule: in zsh ad hoc commands, use `rg --files | rg 'theme'`, quote globs, or add `2>/dev/null` only after preventing glob expansion with `noglob`/quotes. Prefer `rg --files` for optional file discovery.
- Follow-up: use `rg --files` for optional script/test discovery in this skill.

- Context: Chrome fallback attempt for the same media upload probe after the in-app browser lacked file selection support.
- Symptom: Chrome's browser-control documentation exposed the correct `waitForEvent("filechooser")` plus `chooser.setFiles(...)` capability, but navigating the current Chrome AllinCMS tab from `/{siteKey}/themes` to `/{siteKey}/media` redirected to `/sign-in`.
- Evidence: target navigation result was `https://workspace.laicms.com/sign-in`, sign-in form text was visible, no upload button existed on the page, and no upload/filechooser action was attempted.
- Risk: an operator can assume Chrome solves the upload problem because it has filechooser support, then try to upload from an expired session or cached stale tab.
- Rule: Chrome is the preferred fallback for media-library file selection only after fresh workspace auth is proven by loading `/sites` or the exact target module URL. If the target module redirects to `/sign-in`, stop before upload and ask the user to log into Chrome; keep the prepared authorization/preflight artifacts but regenerate freshness-sensitive gates after login.
- Follow-up: keep Chrome media-upload resumes bound to the exact `{siteKey}/media` URL, not an older theme/dashboard tab.

- Context: generating the media upload pre-mutation gate from read-only scan evidence.
- Symptom: `check_pre_mutation_gate.py` crashed with `TypeError: 'NoneType' object is not iterable` when a media preflight used empty/grid-style controls and omitted `listColumns`. After that, a raw scan conversion carried sidebar account text into `contentInspection.listColumns` until redaction was applied.
- Evidence: the gate now accepts `visibleControls` together with `listColumns` for media empty-state evidence, and `validate_run_evidence.py` correctly rejected unredacted account/contact text before mutation.
- Risk: media uploads can be blocked by helper crashes instead of readable gate failures; raw browser scans can leak account data into reusable evidence if converted before redaction.
- Rule: for media empty-state preflight, helper logic must treat `visibleControls` as acceptable upload-control proof and must never iterate over `None`. Always run `redact_browser_scan.py` before converting scans into existing-site evidence. If a validator rejects contact/account text, fix the scan/redaction path before regenerating authorization.
- Follow-up: `check_pre_mutation_gate.py` now handles media `visibleControls` and avoids the `NoneType` crash.

- Context: recording a media source-input gap after file selection was blocked.
- Symptom: `record_source_input_gap.py` rejected custom enum values such as `needs-browser-upload-capability-or-public-url-policy` and `blocked-until-upload-proof`.
- Evidence: the script only allows fixed `decisionNeeded` and `classification` values; the accepted record used `needs-user-confirmation` and `blocked-until-schema-captured` with the precise upload-capability blocker in `generationRule` and `operatorNote`.
- Risk: operators may invent gap taxonomy values and fail to record the field, losing the source-intake requirement for future PDF/catalog/asset ingestion.
- Rule: keep gap taxonomy within the script's allowed enum values. Put operation-specific blockers such as browser upload capability, public URL policy, or cleanup proof into `generationRule` and `operatorNote`.
- Follow-up: no script change needed; current enum validation is useful, but future taxonomy may add a dedicated upload-proof blocker if repeated.

## 2026-07-01 Public Frontend QA Findings

- Context: read-only public frontend QA for a temporary AllinCMS site after homepage/category image cleanup, contact-form read-only QA, and media upload probing.
- Symptom: raw link discovery from homepage HTML included `/_next/static/...` CSS/JS assets as URLs; a broad `audit_frontend_rendering.py` run hung on chunked reads; split CLI audit reported `missing_h1` on successful pages and `fetch_failed` on two routes that later returned HTTP 200 with H1 in a bounded recheck.
- Evidence: route discovery produced 12 page routes after filtering assets; split audit had two `fetch_failed` artifacts; bounded recheck proved `/about-us` and one product detail were HTTP 200 with H1; bounded sample QA showed all 12 page routes returned 200 and had at least one H1.
- Risk: an operator can waste time fixing non-page asset URLs, overclaim route failures from CLI chunked-read behavior, or ignore a real content blocker because the status/H1 checks are green.
- Rule: filter asset URLs before page audits. Treat CLI `fetch_failed` and `missing_h1` on large AllinCMS pages as provisional until a bounded curl or browser DOM recheck confirms them. Preserve both artifacts in run evidence and explain the discrepancy.
- Follow-up: `batch-verification.md` now documents asset filtering and bounded recheck for CLI audit noise.

- Context: same public frontend QA pass on product and post detail routes, followed by a focused visible-text recheck.
- Symptom: all tested public page routes returned HTTP 200 and had H1s in bounded samples, and raw HTML contained `**` markers. A later recheck showed those markers came from framework/editor CSS class attributes such as `**:data-slate-placeholder...`, not visitor-visible Markdown.
- Evidence: affected route patterns were `/products/{slug}` and `/posts/{slug}`; each route had `htmlDoubleStarCount` diagnostics, but parsed visible text had `visibleTextDoubleStarCount: 0` and no Markdown residue. Backend editor text for the same products/posts also had no raw Markdown markers.
- Risk: an operator can waste time mutating already-correct content or republishing six detail pages because raw HTML/CSS class names look like Markdown markers.
- Rule: literal Markdown markers are blockers only when they appear in parsed visible text or rendered content DOM. Treat raw HTML attribute/class matches as diagnostics, then confirm with visible-text or browser DOM evidence before scheduling a content repair.
- Follow-up: `batch-verification.md` and `audit_frontend_rendering.py` now separate HTML `**` diagnostics from visitor-visible Markdown residue.

- Context: authorized public contact-form test on a temporary AllinCMS site.
- Symptom: the public form accepted neutral test inputs and the submit button became disabled after clicking submit, with no console errors, but no toast/alert appeared and the backend `/forms` list exposed only the form definition row, not a submission count or inbox.
- Evidence: public form fields were `name`, `email`, topic chooser, `message`, and submit. Topic options included generic inquiry choices. After submit, the URL stayed on the contact page, form values remained visible, submit stayed disabled, and no backend submission record was visible in the forms list.
- Risk: an operator can overclaim form success from a disabled button or static page copy such as `after submission`, while delivery, persistence, webhook, or email notification is still unproven.
- Rule: public form submission launch proof requires captured request/response, a non-static success state, backend submission record/count, email/webhook destination proof, or an explicit demo-scope acceptance. Treat frontend-only disabled state as partial proof and keep the form launch gap open.
- Follow-up: `create-flows.md` now documents the public form submission proof boundary and helper coverage gap.

- Context: follow-up public contact-form test with CDP Network capture.
- Symptom: UI-only submit proof was weak, but enabling CDP Network before submitting captured a public Server Action request and response for the same page.
- Evidence: the public submit emitted `POST /contact-us`, resource type `Fetch`, headers including `Accept`, `Content-Type`, `next-action`, and `next-router-state-tree`, `hasPostData: true`, and response `200 text/x-component`. Raw field values, server-action values, router state, cookies, and raw payload were not stored.
- Risk: without network capture, operators may either overclaim from button-disabled UI state or underclaim by missing an available request/response proof path. With network capture, they may still overclaim delivery if no backend/email/webhook destination proof exists.
- Rule: for public forms, use CDP Network capture when available and store only redacted request/response shape. Treat it as request/response proof, not persistent delivery proof.
- Follow-up: `request-capture.md` now documents the public form submission capture pattern.

- Context: read-only backend status scan after public contact-form submission tests on a temporary AllinCMS site.
- Symptom: the dashboard recent-activity stream showed neutral `Form submission received` events linking to `/forms`, while the `/forms` list itself still exposed only the form definition row and no visible submission inbox/count.
- Evidence: the read-only backend scan covered dashboard, products, posts, media, themes, routes, forms, site-info, tracking, and domains without auth redirect or mutation; dashboard had recent form-submission activity, and forms list had one published form row with field count.
- Risk: an operator can either overclaim email/webhook/storage delivery from dashboard activity alone, or underclaim by ignoring a useful backend-side confirmation signal after a public Server Action submit.
- Rule: dashboard activity can supplement public form request/response proof, but it does not complete form launch proof unless submission storage/destination, email/webhook delivery, or an explicit demo-scope acceptance and cleanup policy is also recorded.
- Follow-up: `create-flows.md` now documents dashboard recent-activity as a supplemental form proof source.

- Context: final frontend audit and launch-gap diagnostic pass on a temporary AllinCMS site.
- Symptom: a fresh 12-route frontend audit could prove all current public routes returned expected 200 with no audit issues, while no complete `run-evidence`, module coverage, batch evidence, cleanup evidence, or final frontend stage-result artifact existed for `validate_launch_acceptance.py`.
- Evidence: the evidence index contained final frontend audit, visible-Markdown verification, public form request/response capture, media upload dialog proof, Chrome media auth blocker, and current gap summary, but lacked the formal launch-acceptance artifact chain.
- Risk: an operator may treat a clean public audit plus scattered `/tmp` evidence files as launch completion, bypassing required proof for from-scratch creation, module capture, batch upload/publish, media/forms/settings, cleanup, and sedimentation.
- Rule: use evidence indexes as diagnostics only. Formal launch acceptance requires the documented helper-produced artifacts or an explicit report that the full gate cannot yet be evaluated.
- Follow-up: `launch-acceptance.md` now states that scattered evidence indexes do not replace the launch gate inputs.

- Context: local launch-acceptance validation after a read-only backend scan and public form request capture on a temporary AllinCMS site.
- Symptom: the acceptance validator previously forced the `forms_media_settings` stage into either all booleans true or whole-stage `explicitly_out_of_scope`, which could not represent a realistic mixed state where site-info, forms, and domains are verified while media upload and tracking are explicitly deferred.
- Evidence: current evidence proved site-info inputs, a published form row, public form request/response plus dashboard activity, and domain CNAME target state; media remained upload-storage/public-URL blocked, and tracking had no supplied Google Tag ID.
- Risk: operators may over-defer verified work by marking the entire stage out of scope, or overclaim incomplete media/tracking work just to satisfy an all-true gate.
- Rule: launch acceptance should accept `partially_verified_with_explicit_deferrals` when every false forms/media/settings boolean has a matching deferral entry with module and reason. Keep true proof and deferred sub-items separate.
- Follow-up: `validate_launch_acceptance.py`, its regression tests, and `launch-acceptance.md` now support mixed verified/deferred forms-media-settings evidence.

- Context: read-only cleanup verification after prior probe cleanup on a temporary AllinCMS site.
- Symptom: existing backend and frontend scans contained no `Codex Probe`, `Delete Me`, `Untitled`, `Test API Probe`, or `UI Request Probe` residue, but the launch cleanup gate previously expected cleanup evidence to behave like a deletion run with a candidate list.
- Evidence: a fresh scan covered backend products, posts, and forms lists plus public home, products, posts, about-us, and contact-us routes; no probe/test terms were visible on any scanned surface.
- Risk: an operator may create a new probe purely to satisfy a cleanup gate, or overreport cleanup as incomplete after the site is already clean.
- Rule: accept cleanup absence proof when `cleanedCandidates` is empty only if `noCandidatesVerified: true`, backend/frontend verification are true, and `scannedSurfaces` names the backend and frontend surfaces checked. This closes cleanup without remote mutation and keeps content-upload proof requirements separate.
- Follow-up: `validate_launch_acceptance.py`, its regression tests, and `batch-verification.md` now document cleanup absence evidence.

## 2026-07-01 Current-Site Launch Gate Assembly Findings

- Context: assembling formal launch acceptance for a from-scratch temporary AllinCMS site after browser-visible products, posts, theme routes, forms, and cleanup were already in good shape.
- Symptom: hand-maintained detail slugs produced false 404s for one product and one post, while the public list pages linked the actual current slugs. A browser navigation timeout also fired after the destination page had already loaded and the selected tab showed the correct title.
- Evidence: public list DOM linked current `/products/{slug}` and `/posts/{slug}` detail URLs; stale guessed product/post detail URLs returned 404; after the timeout, the tab URL/title proved the intended post detail was loaded.
- Risk: an operator can mark real published content as broken, waste time repairing correct pages, or discard a loaded tab because the navigation promise timed out.
- Rule: derive final detail audit URLs from current frontend list links, backend rows, or manifest/progress logs, not from memory or earlier copy. When navigation times out, first inspect the current tab URL/title/DOM before treating the route as failed.
- Follow-up: keep `batch-verification.md` and frontend audit helpers oriented around generated URL inputs and browser DOM rechecks.

- Context: merging from-scratch site creation evidence with later product probe request-capture, sample verification, and cleanup evidence.
- Symptom: `validate_run_evidence.py` forced one top-level `authorization` object to satisfy create-site, upload/probe, and cleanup checks at the same time, so valid multi-stage evidence failed after merging.
- Evidence: a `created_verified` base required `authorization.target = https://workspace.laicms.com/sites`, while probe upload proof required the authorization target to belong to `/{siteKey}/products`; merging save proof failed with mutually incompatible authorization errors.
- Risk: formal launch evidence can get stuck even when every remote mutation had its own action-time authorization and validated proof, encouraging operators to hand-edit or discard provenance.
- Rule: multi-stage run evidence must preserve action-specific authorization records. Keep the legacy top-level `authorization` for compatibility, but use `authorizationHistory[]` to validate create-site, probe/save/publish, and cleanup stages independently.
- Follow-up: `validate_run_evidence.py`, `merge_probe_evidence.py`, and regression tests now support staged `authorizationHistory`.

- Context: closing the final launch gate after a current browser pass proved visible modules and public routes, but JSON replay contracts were intentionally not complete.
- Symptom: the launch acceptance gate blocked when only capture-plan gate coverage existed; it passed once current-site `allincms_module_capture_coverage` explicitly stated `uiFirst: true`, `complete: true`, and `jsonReplayReady: false`.

## 2026-07-01 Source Sample Apply Finding

- Context: local skill-maintenance pass on the source-file-to-site chain after pages/site-info and taxonomy stages already had apply helpers.
- Symptom: manifest sample upload had a validator and batch-prep consumer, but no dedicated `evidence -> validation/progress -> source execution status` apply helper.
- Evidence: `validate_manifest_sample_upload_evidence.py` could validate one sample, and `summarize_source_execution_status.py --sample-evidence` could mark `sample_upload` passed, but operators had to hand-wire the status arguments after browser evidence was captured.
- Risk: a standalone sample validation report can be mistaken for a completed source-stage transition, or the source execution dashboard can remain stuck at `sample_upload` even though the sample proof is valid.
- Rule: after a source-generated manifest sample is uploaded and verified, run `apply_manifest_sample_upload.py` to validate the evidence, write one progress-log entry, and refresh `source-execution-status.after-manifest-sample.json`. Follow that refreshed `currentStage`; only `batch_upload` means batch preparation is the next source-stage boundary.
- Follow-up: added `apply_manifest_sample_upload.py`, regression tests, and documented the apply step in `SKILL.md` plus `batch-verification.md`.

## 2026-07-01 Source Batch Apply Finding

- Context: local skill-maintenance pass on the source-file-to-site chain after manifest sample evidence already had an apply helper.
- Symptom: batch upload/publish evidence had a strong validator and source status could consume a validation path, but there was no dedicated `evidence -> validation/progress -> source execution status` apply helper for completed batch runs.
- Evidence: `validate_batch_upload_publish_evidence.py` validated schema gate, sample proof, progress log, backend/frontend URL ownership, body/media checks, and redacted frontend audit reports; `summarize_source_execution_status.py --batch-validation` could advance to `launch_acceptance`; operators still had to hand-wire the validation path after browser evidence.
- Risk: a standalone batch validation report can be mistaken for a completed source-stage transition, or the source execution dashboard can remain stuck at `batch_upload` even though batch proof is valid.
- Rule: after a source-generated batch upload/publish run completes, run `apply_batch_upload_publish.py` to validate the evidence, write a batch progress-log artifact, and refresh `source-execution-status.after-batch-upload.json`. Follow that refreshed `currentStage`; valid batch proof should advance to `forms_media_settings`, not directly to launch acceptance.
- Follow-up: added `apply_batch_upload_publish.py`, regression tests, and documented the apply step in `SKILL.md` plus `batch-verification.md`.
- Evidence: current-site module coverage pointed to the backend launch scan, frontend DOM scan, module scan summary, capture plan, and gate coverage; launch acceptance reported `module_interface_capture_complete` as passed with details `complete UI-first coverage`.
- Risk: operators may confuse capture-plan authorization coverage with actual module coverage, or conversely overclaim JSON replay readiness from UI-first browser verification.
- Rule: for broad feature walkthroughs, record UI-first module coverage separately from JSON replay readiness. UI-first coverage can close module-interface launch acceptance only when it is current-site, complete, redacted, and clearly states `jsonReplayReady: false` until per-action contracts are captured.
- Follow-up: use a current-site module coverage artifact, not another site's coverage or a capture-plan gate report, in final launch acceptance.

## Record Template

Use short, redacted bullets. Prefer placeholders like `{siteKey}`, `{themeId}`, `{pageId}`, `{contentId}`, and `{serverActionId}`.

```text
## YYYY-MM-DD <Neutral Finding Group>

- Context: module/action and whether it was read-only, local-only, or mutating.
- Symptom: what failed, surprised, or differed from expectation.
- Evidence: redacted URL/method/payload shape, backend state, frontend status, or DOM proof.
- Risk: what would go wrong if an agent relied on the old assumption.
- Rule: the reusable operation rule or stop condition to apply next time.
- Follow-up: validator, reference, or helper script that should be updated, if any.
```

Do not keep raw run logs here. Compress the evidence into reusable platform behavior.

## Fast Function Pass Record Contract

When the user asks to quickly run through many AllinCMS pages or functions, keep a per-run ledger outside the skill package, such as `/tmp/allincms-{siteKey}-fast-page-function-run-record-{date}.json`. Use the ledger for operational detail, then copy only reusable platform lessons into this skill.

Each module/action row should include:

```text
module or page
backendUrlPattern
mode: read-only, authorized-mutation, blocked, or frontend-verification
authorizationSource: none, read-only, or exact gated action record
actionPerformed
uiReturn: toast, status text, navigation, dialog state, or visible control result
networkReturn: redacted method, URL pattern, payload keys, and status when captured
backendResult
frontendResult
blockerOrError
evidencePointer
mutationFlag
riskLevel
followUp
operatorNote: neutral platform behavior only
```

Do not store account labels, private site copy, raw IDs, cookies, tokens, or business strategy in the skill. Runtime ledgers may contain concrete temporary URLs or slugs when needed for verification, but keep them in `/tmp` or another run-evidence location and redact before using them as reusable examples.

## 2026-06-29 Per-Turn Skill Sedimentation Discipline

- Every AllinCMS skill turn needs an explicit skill-sedimentation closeout, including hands-on browser work, local rehearsal, helper maintenance, planning, discussion, request analysis, and validation-only checks. The closeout should happen before the final response, not as a later memory cleanup.
- At turn start, classify the expected closeout path as run-evidence or maintenance. During the turn, keep a small running list of reusable problems, command drift, and validation gaps so they are not lost during browser work or context compaction.
- The sedimentation check is not permission to store business strategy. Keep temporary site examples, product copy, customer topics, and run-specific content out of the skill; write only neutral platform behavior and redacted interface facts.
- If the turn changes the skill package, rerun both the local hygiene audit and the Codex skill validator. Report failures directly instead of presenting the skill as ready.
- If there is no reusable platform finding, say so in the final response after checking. Do not add low-value bullets just to prove activity.
- Use `scripts/check_round_closeout.py` as the deterministic final-response gate: `--sedimentation updated` when skill files changed; `--sedimentation none --note "no reusable skill update needed after checking"` only when there are no skill changes and no reusable finding.

## 2026-06-29 Theme Launch Findings

- Theme activation is two-step when route mapping is incomplete. The switch click can send `POST /{siteKey}/themes` with `[siteId, themeId]`, but that only opens the route-mapping dialog. The final `应用主题` action is a separate Server Action with `id`, `siteId`, and `mappings`.
- `应用主题` can mark the theme active even when some mappings have empty `pageId`. Treat active theme status as necessary but not sufficient.
- Published pages can still have disabled page switches in the theme detail list. Verify `published` and `enabled` separately.
- The routes module can show paths as present but unbound after theme activation. Verify route binding separately from route existence.
- Frontend browser runtime can appear as an empty shell while HTTP requests return 404. For public launch checks, verify both HTTP status and DOM content.
- A launch-ready page requires this full chain: page saved, page published, page enabled, route bound, theme active, public HTTP not 404, and public DOM contains expected headings/body/media.
- Editing an existing designer block can be more reliable than Copilot generation. In one verified run, typed Inspector fields for an existing `hero-commerce` block saved and published correctly, while prior Copilot prompt attempts returned success-like UI without changing the canvas.
- Visual canvas selection is not sufficient proof that Inspector editing is ready. The canvas can show a selected block overlay while the Inspector still says `No block selected` or remains at `Loading props...`.
- For `hero-commerce`, the stable editing surface is typed Props fields and the saved `pageDocument.elements.<elementId>.props` payload. Repeated visible labels such as `Label` and `Value` map to different arrays, so build templates from the saved payload rather than visible text order.
- Saving a design can change the page status from `Published` to `Draft`; publish is still a separate Server Action even if the public page previously existed.
- Empty page design replay requires a complete `pageDocument`: explicit `page-root` element with `children` pointing to block ids, and each block must include `children: []`. Missing either produced Server Action validation errors inside a 200 `text/x-component` response.
- Designer action buttons use nested target objects such as `target: {type: "custom", href: "/..."}`. A plain `href` field can leave stale public links even when the visible label changes.
- A published and enabled page can still 404 if no site route row exists. Creating `/solutions` through the routes module auto-bound it to the matching Solutions page route option and made the public page render.
- Root `/` route creation was rejected with `validation.routePath.rootInvalid`; `/home` rendering does not imply root homepage rendering. The verified fix is to use the theme page list's `设为首页` action for the intended homepage. That action can make public `/` render the selected page without creating a `/` route row.

## 2026-06-29 Module Scan Findings

- Read-only module scans are safe and useful through direct page navigation. The dashboard, products, posts, media, themes, theme pages, routes, forms, site-info, tracking, and domains pages loaded as documents and often caused RSC prefetches for sibling modules.
- Sibling `_rsc` fetches during read-only navigation are not action interfaces. Seeing `GET /{siteKey}/products?_rsc={token}` while scanning routes/forms/themes means the app prefetched component data; it does not prove product JSON create/save is available.
- Product and post list pages exposed empty-state create buttons. Treat those buttons as potentially mutating until the current version is probed with explicit authorization.
- Historical state at that time: media upload remained UI-first until multipart/storage request behavior was captured. **Superseded on 2026-07-27 by the canonical direct adapter and the final finding in this file.**
- Site-info, tracking, domains, forms, and route mutations require action-specific capture before JSON replay.
- The authorization helper and pre-mutation gate must include granular theme launch mutations. If either helper lacks actions such as `save_design`, `publish_design`, `enable_theme_page`, or `bind_route`, extend and test it instead of recording these mutations as generic `publish`.
- Empty-state tables can still contain a `tbody tr` for the empty row. Do not use raw table row count alone as proof that posts, products, forms, routes, or other records exist. Check headers, empty-state text, row action controls, and record-specific cells.

## 2026-06-29 Frontend Audit Evidence Findings

- Redacted frontend audit output should preserve route identity as a path such as `/`, `/home`, `/products`, or `/products/{slug}`. Do not mix full public origins for some pages with relative route patterns for others; inconsistent evidence makes batch verification harder to compare.
- For route-level public checks, a useful minimal proof is: path, HTTP status, content type, tag counts, image count, link count, heading counts, and issue list. Redact headings and snippets, not structural counts.
- Frontend route audits need explicit expected status support. Static launch pages should be checked with expected 200, while nonexistent probe detail pages can be checked with expected 404 to prove no accidental public content exists. Run separate commands for different expected statuses.
- Static route audit inputs must be generated from the actual site/navigation and the current content type. A product-focused site may have `/products` public while `/posts` returns 404; that is not automatically a product launch failure. Conversely, a posts run must not use `/products` as proof that `/posts` renders.
- End-to-end run evidence needs to support static launch verification separately from content upload verification. A site can have working static launch pages while product/post detail routes are still unverified or intentionally 404. Record `frontendRendering.expectedStatuses` so the evidence does not overclaim content upload readiness.
- A single mixed launch audit is safer when it uses a URL-to-status JSON map. This avoids losing the relationship between static routes that must be 200 and redacted probe detail routes that should remain 404 before content upload.
- Convert frontend audit JSON into run evidence with a helper instead of hand-copying route patterns and expected statuses. Hand-built evidence is easy to desynchronize from the actual audit report.
- Generate the launch audit URL list and expected-status map from one command when possible. Hand-maintained URL files and status maps can drift, especially when adding or removing static theme pages.
- Existing-site read-only evidence should accept generated `frontendRendering` JSON directly. This keeps frontend audit proof tied to the final run evidence and avoids a temporary merge script.
- A clean mixed launch audit with static pages at expected 200 and content detail probe routes at expected 404 is good phase evidence, not upload completion. Treat it as proof that static launch pages render and no accidental probe details are public; it still says product/post detail upload is unverified.
- CLI boolean flags that use Python `BooleanOptionalAction` require `--no-...` for false values. Passing `--flag=false` fails and should not be used in examples.
- Add focused regression tests when introducing helper scripts that transform launch audit inputs, frontend audit JSON, or run evidence. These helpers define the evidence chain and should fail fast if route redaction, expected statuses, or merge behavior drifts.

## 2026-06-29 Authorization Helper Findings

- Probe creation authorization should be content-type-specific. A generic `create_draft` action is too broad when the next step is known to be a post, product, or form probe.
- The helper should reject placeholder or not-yet-authorized source text. A prepared record template is not permission to mutate the backend; only an action-time user instruction that names the exact action and target should generate a usable record.
- Verified local helper actions now include `create_post_probe`, `create_product_probe`, and `create_form_probe`. Use these before clicking create controls that may immediately create remote drafts.
- Probe authorization text must contain three independent signals: exact backend target URL, content type, and probe/draft/test intent. Without all three, an agent can accidentally convert a generic "create product" instruction into permission to create a schema probe draft.
- Creating a probe and saving a probe are separate authorization boundaries. `save_probe` must name the exact edit URL and include capture/request/persistence intent; simply authorizing probe creation or generic save is not enough to capture a real save request.
- Saving a probe and publishing a probe are also separate authorization boundaries. `publish_probe` must name the exact edit URL, content type, probe/draft intent, publish intent, and frontend verification expectation; a generic `publish` action is too broad for sample probe publication.
- Probe cleanup needs its own authorization and gate. `cleanup_probe` must name the exact target, content type, probe/draft intent, cleanup/delete/unpublish intent, and backend/frontend verification fields; publishing or saving a probe does not grant deletion or unpublish permission.

## 2026-06-29 Manifest Gate Findings

- A draft manifest can pass generic local validation while still being unsafe for upload because no current-site save request has been captured. Treat generic manifest validation as source normalization only.
- Live upload or JSON replay must require `schemaVerified: true`, a current-site `fieldMapping`, and a `payloadTemplate` derived from the exact content-type save request. Use `validate_manifest.py --require-schema-verified` as the upload gate.

## 2026-06-29 Run Status Findings

- A structurally valid run evidence file is not the same as an achieved end-to-end run. Use `summarize_run_status.py` after `validate_run_evidence.py` to produce proven items, missing items, and next actions before the final response.
- When the summary says `complete: false`, preserve that state in the user-facing report. Do not soften missing upload proof into a launch-complete claim.
- Next-action summaries should include executable handoff details for supported probe actions: exact backend target, suggested authorization text, authorization-record command, and pre-mutation gate command. Do not output pretend commands for modules that the local authorization helper and gate do not support yet.
- Create-site preflight is also an incomplete run state that needs executable handoff details. When `siteCreation.status` is `create_preflight_verified`, the summary should include `authorize_create_site` plus the exact `/sites` authorization text, authorization-record command, and create-site pre-mutation gate command.
- Static launch proof must cover the full expected static route set, not just whichever static routes happen to appear in `expectedStatuses`. Detail-route absence must match the current `contentInspection.contentType`; a product detail 404 is not proof that post detail upload remains unverified, and vice versa.
- Completion should be gated by an explicit required proof set, not only by the absence of currently known missing items. A complete site-build/content-upload run needs site source proof, site identity, setup-page inspection, static frontend render proof, persisted request capture, sample backend/frontend verification, and cleanup proof. Surface any absent item as `completionGaps`.
- From-scratch site-build goals need a stricter completion mode than existing-site continuation. Use `summarize_run_status.py --require-created-site` when the objective says to start from creating a site; otherwise `existing_site_selected` can correctly support continuation work but must not satisfy from-zero creation proof.

## 2026-06-30 Probe Stage Handoff Findings

- Probe workflows need staged next actions after the initial create handoff. If upload is in scope and request capture is missing, the status summary should emit `authorize_save_probe`; if request capture is proven but sample backend/frontend verification is missing, emit `authorize_publish_probe`; if the sample is verified but cleanup is pending, emit `authorize_cleanup_probe`.
- The summary should output only the next safe mutation stage. Do not present save, publish, and cleanup as parallel permissions; each stage requires a fresh user authorization record and a matching pre-mutation gate.
- When no exact edit URL has been proven yet, a save handoff may target the content module list URL as a placeholder under the verified `{siteKey}/{contentType}` route. Once `requestCapture.url` or `sampleVerification.backendUrl` exists, prefer that edit URL for publish and cleanup handoff.
- Suggested Chinese authorization text must still pass the local authorization validator. Keep the validator bilingual for supported action verbs instead of forcing operators to translate helper output into English.
- Probe evidence should be merged with `scripts/merge_probe_evidence.py` after each authorized stage. A merged request capture is valid phase progress but can still fail full run validation because `sampleVerification` is intentionally missing; use `summarize_run_status.py` to decide the next authorization instead of treating the merge as completion.
- Status summaries must surface stale run evidence before emitting mutation handoff details. If `generatedAt` is older than the pre-mutation gate window, the next action should start with `refresh_readonly_evidence`; otherwise an operator may prepare a valid-looking authorization record that fails only at the final gate.
- Refreshing existing-site read-only evidence must include a real `/sites` list check and a create-site dialog open/close check when the evidence contains `siteCreation.createSiteFields`. Do not reuse old create-dialog fields merely to satisfy the builder; either re-open the dialog and close it without submitting, or change the evidence model before claiming freshness.
- Browser read-only refreshes should preserve a redacted scan JSON and convert it with `scripts/make_existing_site_evidence_from_scan.py`. Hand-copying the long `make_existing_site_readonly_evidence.py` command is error-prone and can accidentally mix fresh module observations with stale create-dialog fields.
- Scan-to-evidence conversion must require the observed URL for each required backend module. Generating module routes from `siteKey` alone can hide a missed page load or wrong-site scan, so the converter should reject missing or cross-site module URLs.
- Raw browser scans can include account-menu text, emails, site switcher labels, and frontend domain strings inside generic button text. The scan converter must filter these before building run evidence; otherwise a clean read-only refresh can still leak account or site-specific material.
- Do not derive `existingSiteKeysBeforeCreate` from a full-page text regex. Next.js scripts, CSS class names, English body copy, account labels, and object-id fragments can match the loose site-key shape. Extract site keys from scoped site cards, backend hrefs, or previously verified site-list evidence, and reject unusually large existing-site key lists in run-evidence validation.
- Create-dialog scans may report `name` and `description` in `fields` while `创建` and `Close` appear in `buttons`. Treat the dialog evidence as the combined dialog surface, not a fields-only list.

## 2026-06-30 Interface Scan Summary Findings

- Module scan summaries need a middle state between read-only and replay-ready. A captured POST should be labeled `captured_post_requires_review`, not treated as JSON-ready, until payload shape, current id fields, action-specific authorization, and persistence proof are all present.
- `_rsc` GET fetches during navigation should be labeled `read_only_prefetch_only` when no mutation request exists. This prevents agents from confusing Next.js component prefetch with a create/save API.
- Interface scan summaries should preserve redacted `payloadShape` or `payloadKeys` counts for POST requests. Missing payload shape is itself a warning because the request cannot be safely replayed or templated.

## 2026-06-30 Created-Site Evidence Merge Findings

- From-scratch site-build runs should keep post-create proof and static frontend audit proof in one run evidence file when possible. Otherwise later summaries can prove site creation and frontend rendering only through separate artifacts, which makes completion gaps easier to misread.
- `make_created_site_evidence.py` should accept a generated `frontendRendering` evidence block. This lets `summarize_run_status.py --require-created-site` report `site_created_and_verified` and `static_frontend_routes_render` together while still leaving request capture, sample verification, and cleanup as explicit gaps.
- The default frontend origin opening is not equivalent to static route rendering. Merge frontend rendering only after route-level audit evidence exists.
- When validators add a required setup module after an older site-creation proof was recorded, merge only current read-only setup evidence from the same `{siteKey}` into the old `created_verified` evidence. Preserve the original create timestamp and authorization, and keep the summary stale for mutation if the original `generatedAt` is stale.
- Use `scripts/merge_created_site_readonly_refresh.py --validate` for that merge instead of hand-editing run evidence. Treat the output as historical creation plus current read-only setup proof, not as fresh permission to create, save, publish, upload, or delete.

## 2026-06-30 Site Action Gate Findings

- Site launch mutations need the same local gate discipline as content probes. Supporting an action in `make_authorization_record.py` is not enough; `check_pre_mutation_gate.py` must also know the module route, target type, and required proof fields before the browser or JSON replay mutates remote state.
- Theme/page/route operations should use action-specific gates such as `save_design`, `publish_design`, `set_homepage`, `enable_theme_page`, `bind_route`, and `create_route`. Do not pass them through generic publish, save, or cleanup gates.
- The gate intentionally requires proof-field names such as `pageDocument`, `routePath`, `boundPage`, `homepage`, or `frontendVerified`. These fields are a preflight contract for what must be captured and verified after the mutation; they do not replace real backend/frontend checks.

## 2026-06-30 Launch Readiness Evidence Findings

- Theme/page/route launch readiness should be its own run-evidence block. `frontendRendering` proves public route behavior, while `launchReadiness` proves backend state: active theme, published pages, enabled pages, bound routes, HTTP success, and DOM verification.
- Do not treat active theme, page `Published`, a success toast, or HTTP 200 Server Action response as launch-ready proof. All launch readiness booleans must be true, and blocking issues must be empty.
- `launchReadiness` is still not content-upload proof. Completion for content upload continues to require exact content-type request capture, sample backend/frontend verification, and cleanup.
- Generate `launchReadiness` with `scripts/make_launch_readiness_evidence.py` instead of hand-writing the JSON. The helper rejects concrete slug paths, requires redacted route patterns, and forces blockers for partial launch state while preserving the stricter validator rule that launch-ready proof needs all booleans true.
- Merge generated `launchReadiness` into run evidence through `make_existing_site_readonly_evidence.py --launch-readiness-evidence` or `make_created_site_evidence.py --launch-readiness-evidence`. Otherwise the flow still depends on manual JSON copying after the helper runs.
- Context: read-only frontend audit of an existing site after theme/page work.
- Symptom: product-oriented static pages returned 200, but `/posts` returned 404 while the expected-status map required 200.
- Evidence: redacted audit array contained per-URL entries with `/posts` status 404 vs expected 200, plus generated `launchReadiness` had `routesBound: false`, `frontendHttpOk: false`, and blocking issues for `/posts`.
- Risk: an operator could overclaim launch readiness by focusing on passing static pages or assume `/posts` exists because posts are a supported content type.
- Rule: static route expectations must be site-specific and content-type-specific. If an expected static route returns 404, keep launch readiness incomplete; if a content type is not in scope, omit its list route from required static launch proof rather than treating another content type's route as evidence.
- Follow-up: `references/batch-verification.md` now warns that `/posts` must not be assumed and that a 404 expected-200 list route blocks launch readiness.

## 2026-06-30 Frontend Audit JSON Shape Findings

- Context: local evidence conversion after a read-only frontend audit.
- Symptom: `audit_frontend_rendering.py --json` emits a JSON array of per-URL reports, while downstream reasoning can drift toward expecting a top-level object summary.
- Evidence: `make_frontend_rendering_evidence.py` rejects non-array audit JSON with `audit JSON must be an array`; the actual redacted audit report was a list containing `/`, `/products`, `/posts`, and redacted detail-route entries.
- Risk: hand-wrapping the audit result or assuming object keys can break evidence conversion or hide per-route status mismatches.
- Rule: treat frontend audit JSON as a list until converted. Only after running `make_frontend_rendering_evidence.py` should run evidence contain the top-level `frontendRendering` object.
- Follow-up: `references/batch-verification.md` now documents the array shape directly next to the audit command.

## 2026-06-30 Browser-Stage Authorization Placeholder Findings

- Context: preparing a real-site `module_interface_capture` package for a single `products:create` capture stage.
- Symptom: the capture-plan package validated, but the stricter browser-stage package validator rejected the generated package because `authorizationRecordCommand` embedded suggested authorization text instead of retaining the current-user authorization placeholder.
- Evidence: `validate_browser_stage_authorization_package.py` reported `authorizationRecordCommand must retain the current-user authorization placeholder`; after fixing the helper, the command retained `--authorization-source '<paste current user authorization text here>'` and validation passed.
- Risk: suggested authorization wording could be mistaken for live user authorization, causing a remote mutation without action-time approval.
- Rule: browser-stage authorization packages may include suggested wording, but every executable authorization-record command must keep the placeholder until the current user explicitly authorizes that exact action and target in the conversation.
- Follow-up: `prepare_browser_stage_authorization.py` now rewrites generated command templates to keep the placeholder, and regression tests cover module capture, theme launch, content probe, batch upload, and settings actions.

## 2026-06-30 Helper CLI and Shell Drift Findings

- Context: local preparation of all capture-plan authorization packages for a real module scan.
- Symptom: the first batch command failed because `prepare_capture_authorization.py` requires `--preflight` and `--authorization-output`; a second cleanup command failed because zsh treats an empty `*.json` glob as an error.

## 2026-06-30 Posts Route And Designer Findings

- Context: mutating test-site posts flow from draft creation through save, publish, theme page creation, enable, route binding, and frontend verification.
- Symptom: a published post with backend status `已发布` still returned frontend 404 until both `/posts` and `/posts/{post}` had matching theme pages and enabled switches. Creating those pages made the routes bind and changed HTTP 404 to 200.
- Evidence: posts save used `POST /{siteKey}/posts/{postId}/update` with `title, slug, excerpt, order, coverImage, categories, tags, content, siteId, postId, mode`; publish used the same URL with `mode: "publish"`. Static Posts page create used `path: "/posts"`; dynamic Post Detail child used `path: "/posts/{post}"`, `routeMode: "param"`, and `parentPath: "/posts"`. Enable actions used `{id, siteId, themeId, enabled: true}`.
- Risk: an operator can confuse backend publish success with frontend readiness, or reuse product detail route behavior without creating the corresponding posts theme pages.
- Rule: for posts, verify all four layers separately: content published, `/posts` theme page exists and is enabled, `/posts/{post}` dynamic page exists and is enabled, and frontend list/detail DOM contains visible content.
- Follow-up: `references/create-flows.md` now documents posts save payload keys and posts theme-page create/enable behavior.

- Context: frontend verification after posts route binding.
- Symptom: `/posts` and `/posts/{postSlug}` returned HTTP 200, and the detail HTML title contained the post title, but browser-visible body text was empty because both new posts theme pages had `No blocks yet`.
- Evidence: browser DOM for the list/detail pages had empty body text; designer for Posts showed `No blocks yet`, disabled Save, and disabled Publish.
- Risk: HTTP-only checks and title checks can overclaim posts launch readiness while users see a blank page.
- Rule: final frontend verification must include browser-visible DOM text or equivalent rendered HTML body proof, not only HTTP 200, document title, or route binding.
- Follow-up: use `launch-acceptance.md` and frontend QA to require DOM content for each in-scope route.

- Context: attempted Articles block insertion in the theme designer for a Posts list page.
- Symptom: selecting or dragging `Full News List (Filtered)` produced a status message like `Draggable item ... was dropped over droppable target canvas-drop`, but `No blocks yet` remained and Save stayed disabled.
- Evidence: after both click and drag attempts, the designer still showed no blocks and no enabled Save action.
- Risk: a drag/drop accessibility message can look like success while the design document is unchanged.
- Rule: never treat `was dropped over droppable target canvas-drop` as insertion proof. Require the block to appear in canvas or Layers and Save to become enabled before saving or publishing.
- Follow-up: keep posts launch blocked until a reliable Articles block insertion path or validated `pageDocument` save path is captured.

- Context: repeated Articles block insertion attempts in a Posts designer page.
- Symptom: a block can become selected, `aria-pressed`, and `aria-grabbed`, and keyboard or mouse drop can emit a dnd-kit dropped status, while the page design still has no block. A failed sequence can also leave the canvas stuck at `Render canvas...` with Save and Publish disabled.
- Evidence: `Full News List (Filtered)` entered selected/grabbed states and emitted drop announcements, but no canvas or Layers block appeared and Save remained disabled; a later refresh showed only `Render canvas...`.
- Risk: ARIA state, keyboard drag state, or a rendering spinner can be mistaken for a successful insertion or safe save point.
- Rule: treat dnd and ARIA states as interaction telemetry only. Design insertion proof is `No blocks yet` gone after rendering, target block visible in canvas or Layers, and Save enabled. If the canvas remains at `Render canvas...`, record a browser/designer failure and retry from a fresh tab or validated `pageDocument` save path.
- Follow-up: `references/create-flows.md` now states the stricter Articles insertion proof and stop condition.

- Context: fresh Posts designer retry after a previous stuck-canvas run.
- Symptom: the Articles category displayed `Full News List (Filtered)`, but `Search blocks` with `Full News List` or `News` produced an empty list. Clicking the block card, hovering for an Add button, pressing Enter, and submitting a Copilot prompt for an article list page still left `No blocks yet` and Save disabled.
- Evidence: the browser evidence recorded no remote save/publish; the current designer state retained disabled Save/Publish and an empty canvas after every insertion attempt.
- Risk: an operator may assume search filtering or Copilot prompt success is equivalent to insertion, then save/publish an empty posts page or overclaim a 200-but-blank route.
- Rule: for Articles blocks, search results, card selection, hover state, Enter, and Copilot prompts are only candidate interactions. Require visible block insertion and enabled Save before running `save_design`; otherwise stop and use a validated `pageDocument` path.
- Follow-up: `references/create-flows.md` now names this search/Copilot failure mode.

- Context: final frontend audit URL selection for a temporary site with a published Contact Us page.
- Symptom: `/contact` returned a 404, but the actual theme page and frontend links used `/contact-us`, which rendered the contact page and form.
- Evidence: the theme page row route was `/contact-us`; browser verification showed `/contact-us` with visible headings and one form, while `/contact` showed a 404.
- Risk: hand-maintained audit URL lists can mark a real page as missing or hide a broken CTA alias, depending on which path is guessed.
- Rule: build static audit paths from the current theme page list, route table, navigation, and CTA hrefs. Treat an unlinked guessed alias such as `/contact` as a URL-selection error unless the site is expected to support it.
- Follow-up: `references/batch-verification.md` now warns to derive contact paths from live route/link evidence.

## 2026-06-30 Product Specification Findings

- Context: live mutating product specification edit on a temporary AllinCMS test site.
- Symptom: the product specs dialog can work without any site-level spec templates. The dialog-level `保存` applies local page state only; the outer product `更新` still has to be clicked, and that save changes a previously published product back to draft.
- Evidence: the specs dialog showed no available template, `添加字段` created default name/value inputs, outer `更新` posted to `/{siteKey}/products/{productId}/update`, and a separate publish POST to the same URL was required. The frontend product detail then rendered a `Specifications` section with term/definition rows.
- Risk: an operator can close the specs dialog and assume public specs changed, or forget the publish step after the product save moved the item to draft.
- Rule: product specs require three boundaries: dialog save, outer product update, and product publish. Verify backend status and frontend rendered spec terms after publish. Product specs completion does not prove product media completion.
- Follow-up: `references/create-flows.md` now documents manual specs fields and the save/publish chain.

## 2026-07-01 Product Row And Specs Verification Findings

- Context: live mutating product specification replacement across existing published products on a temporary AllinCMS test site.
- Symptom: after choosing a product row menu `更新`, an immediate read can still look like the products list, while the pending navigation later resolves to the intended product edit URL. Refreshing during the split state may reveal the edit page rather than the list.
- Evidence: the row menu was scoped to one product title and the `更新` menu item was clicked once; the first URL/state read still looked like `/{siteKey}/products`, but a later reload showed `/{siteKey}/products/{contentId}/update` with the matching product title, published status, and specification table.
- Risk: an operator can misdiagnose a slow SPA navigation as a failed click and click another row/menu, causing wrong-row edits or confusing evidence.
- Rule: after a row menu update click, wait for the edit URL or `更新产品` heading and product-specific fields. If URL and DOM disagree, refresh once and re-check before retrying the menu action.
- Follow-up: `references/create-flows.md` now documents the delayed row-menu navigation stop condition.

- Context: frontend verification after replacing default product specification rows.
- Symptom: one CLI frontend audit returned a transient `fetch_failed` for a product detail that had just rendered in the browser; an immediate rerun of the same audit passed for all product details.
- Evidence: browser DOM checks showed product detail `h1`, `dt/dd` specification terms, images, and no old template terms; the second redacted CLI audit returned HTTP 200 and no issues for every `/products/{slug}` detail route.
- Risk: a single CLI fetch failure can either hide a real route issue or waste time if treated as definitive while browser proof and rerun evidence pass.
- Rule: for final product specs QA, combine browser DOM term/definition checks with a bounded CLI audit rerun. Treat the first `fetch_failed` as diagnostic unless it repeats or browser verification also fails.
- Follow-up: `references/batch-verification.md` now states the rerun/browser split-evidence rule and product-spec denylist check.

## 2026-06-30 Media Empty-State Findings

- Context: read-only media module and product detail verification.
- Symptom: a product detail page can render a product image element or placeholder while the backend media library is empty and the products list media column remains blank.
- Evidence: the media page showed `没有找到媒体` and upload controls, while the product row media cell was empty. Product detail body/specs rendered, but real media/public asset proof was still absent.
- Risk: a frontend `img` element, placeholder, or product detail block can be mistaken for a real uploaded/bound image.
- Rule: media completion requires a backend media row, a public media URL or uploaded asset proof, product media binding proof, and frontend image load proof. Empty media library blocks launch-quality product image claims.
- Follow-up: keep media as source-input/user-confirmation work until real assets or generated-image approval are available.

## 2026-06-30 Form Builder Findings

- Context: mutating test-site form field editing and frontend contact-page verification.
- Symptom: form field changes persisted only after the field-builder `完成` action, then the outer `更新`, then a separate `发布`.
- Evidence: save/publish posted to `/{siteKey}/forms/{formId}/update` with payload keys `_status, schema, submit, siteId, formId`, and publish added `mode: "publish"`. `schema.fields[]` held field objects for `text`, `email`, and `textarea` with names, labels, and placeholders.
- Risk: leaving the field builder without `完成`, or treating outer save as publish, can leave public forms stale.
- Rule: for form edits, verify builder completion, backend field count/status, and public form controls. Public submission testing remains separate and should wait for destination and cleanup policy.
- Follow-up: `references/create-flows.md` now documents the form field edit sequence and payload shape.

## 2026-06-30 Form Builder And Publish Findings

- Context: live mutating form setup on a user-designated temporary AllinCMS test site.
- Symptom: the form field editor is a drag-to-canvas builder. Clicking or imprecisely dragging a sidebar field can produce a status message that the item was dropped, but leave the canvas empty. The reliable success signal included `dropped over droppable area root`, a non-empty canvas preview, and a changed field count on the parent edit page after clicking `完成`.
- Evidence: a saved form update posted to `/{siteKey}/forms/{formId}/update` with `Accept: text/x-component`, `Content-Type: text/plain;charset=UTF-8`, `next-action: <server-action-id>`, and payload keys `name`, `slug`, `description`, `_status`, `schema.fields`, and `submit`. Publishing reused the same update action with `_status: "published"` and changed the UI to `已发布` / `取消发布`; the forms list then showed field count and status.
- Risk: an operator can think a field exists because a drag event fired or because the form is published, while the field schema was never saved or the public contact page still has no embedded form.
- Rule: for forms, verify all boundaries separately: field drop success, `完成`, `更新`, reload/list persistence, publish status, and public theme-page embed. A published form module is backend proof only; it is not public form proof until a theme/page embed and frontend DOM/submission behavior are verified.
- Follow-up: add granular helper/gate coverage for form field edit, form save, form publish, form embed, and form submission test instead of overloading `create_form`.

## 2026-06-30 Contact Form Theme Embed Findings

- Context: live mutating Contact Us page designer work on a temporary AllinCMS test site after a form module had been published.
- Symptom: published form modules do not automatically appear on public pages; the page designer needs an explicit form block such as `Contact Form (Split)` and a selected form slug. Coordinate and locator clicks against the designer block list can fail in the in-app browser when the block sits inside a scroll area.
- Evidence: filtering `Search blocks` to `Contact Form`, focusing the single result, and pressing `Space` inserted the `Contact Form (Split)` block. The Inspector showed a `Form` combobox; selecting the intended published form set the hidden value to `{formSlug}`. The canvas and public route then rendered a `<form>` with the expected input name/placeholder and submit button.
- Risk: an operator may overclaim embed completion from form-module status, Copilot narration, HTTP 200, or a designer page status. Copilot text can say an insert/update is done, but public form rendering still needs DOM proof.
- Rule: verify form embed with this chain: block inserted, Inspector bound to the intended form slug, page publish request captured, designer status `Published`, public page contains `<form>` plus expected inputs/buttons, and submission is explicitly tested or explicitly omitted. Do not submit a public form unless creating a test inquiry record is in scope.
- Follow-up: add helper/gate actions for `embed_form` and `test_form_submission`; save/publish design gates should allow form-embed proof fields and should document stale preflight regeneration requirements.
- Evidence: `prepare_capture_authorization.py --help` showed the missing required flags; replacing `rm "$outdir"/*.json` with `find "$outdir" -maxdepth 1 -type f -name '*.json' -delete` avoided the empty-glob failure.
- Risk: helper examples or ad hoc loops can fail before generating evidence, or worse, generate packages without the preflight/authorization-output paths needed for safe gating.
- Rule: before scripting helper loops, check the helper's current `--help` output and use glob-safe cleanup commands. Do not assume old parameter names or shell glob behavior.
- Follow-up: this finding is recorded as an operator rule; no helper code change was needed for zsh cleanup.

## 2026-06-30 Source Intake Field Gap Findings

- Context: maintaining the site-build skill while planning future PDF/catalog/brief ingestion for full LAICMS website generation.
- Symptom: source-intake evidence covered products/posts/forms/media/theme pages, but common setup modules such as site-info, routes, domains, tracking, and navigation were easier to leave as chat notes or generic operation gaps.
- Evidence: `record_source_input_gap.py` and `make_source_input_requirements.py` needed explicit content-type support so a run can record fields like notification email, route binding, custom domain, tracking code, menu labels, and CTA destinations without placing source copy or account data in the skill.
- Risk: a later PDF extractor could over-infer fields that require user approval, such as custom domains, operational emails, tracking snippets, legal names, CTA destinations, pricing, inventory, or unsupported certification claims.
- Rule: record every browser-discovered input need as a local `/tmp` source-input gap with source owner, generation rule, schema evidence, and upload blocker. Treat content/spec/copy fields as source-derived only when schema proof exists; treat domains, tracking, notification/contact details, sitemap/CTA decisions, prices, inventory, variants, and unsupported claims as user-confirmed unless the user explicitly accepts the source as authoritative.
- Follow-up: `SKILL.md`, `field-contract.md`, `record_source_input_gap.py`, and `make_source_input_requirements.py` now include the broader source-intake contract.

## 2026-06-30 Capture Package Set Findings

- Context: converting a real module capture plan into a reusable per-action checklist.
- Symptom: hand-written loops for every capture-plan stage duplicated helper CLI details and were easy to break when required flags changed.
- Evidence: a new local helper generated 10 valid package files plus `summary.json` from a real capture plan and read-only preflight; all items remained `jsonReplayReady: false`, with `upload_media` explicitly `gateSupported: false`.
- Risk: operators may treat a complete package list as permission to run multiple mutations, or confuse package validity with replay readiness.
- Rule: use `prepare_all_capture_authorizations.py` to generate the checklist, then choose exactly one stage and prepare a browser-stage authorization package for that one action. A valid package set is preparation only, not authorization, not execution, and not JSON replay proof.
- Follow-up: `SKILL.md` now lists the helper and the recommended command; regression tests cover package-set generation and simulated-target suppression.

## 2026-06-30 Capture Package Set Revalidation Findings

- Context: reusing a previously generated capture authorization package-set summary.
- Symptom: generation-time `valid: true` in `summary.json` was only a snapshot. It did not independently prove that referenced package files still existed, still matched the capture plan, or still matched the summary fields.
- Evidence: a new validator reopens each package path, runs the existing single-package validator, checks module/action coverage against the capture plan, and rejects summary/package drift such as a changed target.
- Risk: an operator could pick a stale or hand-edited package from a valid-looking summary and prepare the wrong mutation action or target.
- Rule: after generating a package set and before reusing an older one, run `validate_all_capture_authorizations.py --plan-json <capture-plan> <summary.json>`. Treat generation-time validity as insufficient once files can drift.
- Follow-up: `prepare_all_capture_authorizations.py` now self-validates after writing the summary; `SKILL.md` documents the explicit revalidation command.

## 2026-06-30 Browser-Stage Capture-Plan Binding Findings

- Context: preparing the next single browser-stage authorization package for `module_interface_capture`.
- Symptom: the browser-stage validator checked packet and preflight alignment, but did not independently verify that `captureStage` still matched the current module capture plan.
- Evidence: adding `--capture-plan` allowed the validator to compare `captureStage.module`, `captureStage.action`, `authorizationAction`, target, and `mustCapture` against the current plan; the real next `products:create` package passed with packet, preflight, and capture plan all supplied.
- Risk: a package copied from an older plan could still look valid for the aggregate browser stage while pointing at the wrong module/action target.
- Rule: validate every `module_interface_capture` browser-stage authorization package with `--packet-json`, `--preflight`, and `--capture-plan` before asking for or acting on user authorization.
- Follow-up: `validate_browser_stage_authorization_package.py`, `SKILL.md`, and regression tests now cover capture-plan binding.

## 2026-06-30 Parallel Verification Agent Boundary

- Context: planning future LAICMS / AllinCMS verification and exploration work.
- Symptom: verification and exploration can be parallelized, but remote site mutations still require exact action-time authorization and controller-owned execution.
- Evidence: repository collaboration rules already require independent read-only adversarial review for sensitive rule/SOP changes; AllinCMS browser work adds remote-state risk because create/save/publish/delete/upload/replay actions mutate shared backend state.
- Risk: a subagent could treat a broad "continue" instruction as permission to click a create button, save a probe, publish content, bind a route, or replay a captured request.
- Rule: use parallel agents for independent read-only checks only: frontend URL audits, backend visible-field inspection, local evidence review, skill hygiene review, or captured-request analysis. Assign exact scope, forbidden actions, and evidence format. Keep all remote mutations single-stage, controller-run, and gated by the usual authorization record plus pre-mutation gate.
- Follow-up: `SKILL.md` and `references/mutation-safety.md` now document the parallel-agent boundary.

## 2026-06-30 Product Detail Dynamic Page Finding

- Context: read-only browser exploration of a product-oriented theme where `/products` rendered but `/products/{product}` was unbound.
- Symptom: the routes table showed `/products/{product}` as type `Product`, bound page `—`, and `未绑定`; opening the row update dialog exposed only path param and note fields, not a bound-page selector.
- Evidence: the active theme had only static pages. The top-level create-page dialog suggested only static routes, while the Products row `创建子页面` dialog exposed a param route editor with allowed `{*}`, `{product}`, `{post}`, `{category}`, and `{tag}` values.
- Risk: an operator could waste time trying to bind the detail route from the route-row update dialog, or publish product content before a product-detail theme page exists, leaving published products with frontend 404 detail URLs.
- Rule: when a content detail route is unbound and no detail page exists, first create a dynamic child theme page as its own `create_theme_page` stage, then separately design/save, publish, enable, bind/verify the route, and only afterward resume product sample verification or batch upload.
- Follow-up: scripts now recognize `create_theme_page` as a gated site action; `create-flows.md`, `interface-inventory.md`, and `mutation-safety.md` document the sequence.

## 2026-06-30 Partial Launch Readiness Evidence Finding

- Context: converting a read-only product-detail blocker into local run evidence.
- Symptom: `make_launch_readiness_evidence.py` can generate a partial `launchReadiness` object with blocking issues, but `validate_run_evidence.py` rejects any embedded `launchReadiness` whose readiness booleans are not all true.
- Evidence: a generated partial object for `/products/{slug}` had `routesBound: false`, `frontendHttpOk: false`, and `frontendDomVerified: false`; standalone JSON was useful diagnostic proof, but embedding it into existing-site run evidence failed validation.
- Risk: an operator may confuse diagnostic blocker evidence with launch-ready proof, or create invalid run evidence by merging partial readiness output.
- Rule: keep partial launch readiness as a sidecar diagnostic artifact or record the blocker through `frontendBlockingIssues`; merge `launchReadiness` into run evidence only after all booleans are true and blockers are empty.
- Follow-up: `SKILL.md` now documents this merge boundary.

## 2026-06-30 Theme Page Create Evidence Gate Finding

- Context: preparing the next product-detail fix after discovering that `/products/{product}` needs a dynamic theme child page.
- Symptom: a valid `create_theme_page` authorization package proves only that one future mutation is scoped and gated; it does not prove the page was created, has a page id, or can support product detail routing.
- Evidence: the prepared package retained the current-user authorization placeholder and emitted a gate command, but downstream launch stages still need concrete request capture, route path, page id, and backend row proof.
- Risk: an operator could proceed to design/publish/enable/bind or product sample verification after a click without proving that the dynamic child page exists.
- Rule: build a `create_theme_page` browser runbook before the action and validate the resulting redacted evidence with `validate_theme_page_create_evidence.py` before relying on the page for any later launch or content-upload stage.
- Follow-up: added `build_theme_page_create_runbook.py`, `validate_theme_page_create_evidence.py`, SKILL entries, and regression tests.

## 2026-06-30 Next Browser Action Handoff Findings

- Context: preparing to move from local evidence into one real browser action without broadening authorization.
- Symptom: the next action proof was spread across a browser-stage package, stage packet, preflight evidence, and capture plan, making it easy to present or execute from an incomplete set.
- Evidence: a new handoff builder validates all referenced pieces together and emits one `allincms_next_browser_action_handoff` with exact target, action, stop condition, required proof, source files, suggested authorization text, and command templates.
- Risk: operators could ask for or act on authorization from a stale package without carrying the current preflight, packet, or capture-plan proof.
- Rule: before asking for action-time authorization for the next real browser action, build a handoff with `make_next_browser_action_handoff.py`. The handoff is preparation only and must still say it is not user authorization.
- Follow-up: `SKILL.md` now documents this handoff step; regression tests cover valid handoff wrapping and rejection of invalid packages.
- Context: local-only maintenance after preparing a real-site next browser action handoff.
- Symptom: the builder validated the handoff at creation time, but there was no standalone validator to re-open the handoff's `sourceFiles` before reuse or after context compaction.
- Evidence: a generated `allincms_next_browser_action_handoff` stores paths to the package, packet, preflight, and capture plan; if any source file or handoff field drifts afterward, generation-time success no longer proves the handoff is safe.
- Risk: an operator could resume from a stale or hand-edited handoff, ask for the wrong action authorization, or run a command that lost the current-user authorization placeholder.
- Rule: run `scripts/validate_next_browser_action_handoff.py <handoff.json>` after generating a handoff and before asking the user for authorization or resuming from that file. Treat a passing handoff as preparation only, not permission to operate the browser.
- Follow-up: the validator now reruns source package validation, checks handoff/package field equality, enforces preparation-only flags, and regression tests cover source reopening plus drift rejection.
- Context: local-only rehearsal hardening after adding the standalone next-browser-action handoff validator.
- Symptom: a validator documented only as a manual command can still be skipped during the long from-scratch rehearsal path.
- Evidence: `run_full_rehearsal.py` already advanced to `module_interface_capture` and wrote the matching packet, but it did not generate the browser-stage authorization package or next-browser-action handoff that a real operator would use before asking for authorization.
- Risk: the full rehearsal could be green while the immediate authorization handoff path remains unexercised until live browser work.
- Rule: the one-command rehearsal must generate a module-capture browser-stage authorization package, wrap it in `allincms_next_browser_action_handoff`, and validate it with `validate_next_browser_action_handoff.py`. A green full rehearsal should prove this local preparation chain, while still not granting permission to mutate LAICMS.
- Follow-up: `run_full_rehearsal.py`, `validate_full_rehearsal.py`, `SKILL.md`, and regression tests now include the next-browser-action handoff artifact and safety check.
- Context: local-only runbook hardening after the next-browser-action handoff became part of full rehearsal output.
- Symptom: the standalone `browser-runbook-summary.json` still focused on the immediate read-only packet and evidence bundle, so an operator reading only the runbook could miss the stricter next-browser-action handoff artifact generated for later authorization review.
- Evidence: `rehearsal-summary.json` contained `artifacts.nextBrowserActionHandoff`, but `browser-runbook-summary.json` did not expose it in `requiredLocalArtifacts` or `operatorHandoff`.
- Risk: future browser execution could fall back to manually reconstructing authorization packages from the long artifact list, bypassing the handoff validator added to prevent stale package/packet/preflight drift.
- Rule: when a full rehearsal generated `next-browser-action-handoff.json`, the browser runbook must surface that path in both `requiredLocalArtifacts.nextBrowserActionHandoff` and `operatorHandoff.nextBrowserActionHandoffPath`.
- Follow-up: `make_browser_runbook_summary.py`, `validate_full_rehearsal.py`, `SKILL.md`, and regression tests now require the runbook to carry the handoff path.
- Context: follow-up local-only hardening for standalone browser runbook reuse.
- Symptom: `validate_full_rehearsal.py` cross-checks the integrated runbook at generation time, but a copied or hand-edited `browser-runbook-summary.json` could drift afterward without being revalidated directly.
- Evidence: the standalone runbook stores `sourceSummary`, `requiredLocalArtifacts.nextBrowserActionHandoff`, and `operatorHandoff.nextBrowserActionHandoffPath`; tampering those handoff paths leaves the original rehearsal summary untouched.
- Risk: an operator could resume from a stale runbook, miss the current next-browser-action handoff, or ask for authorization from a path that no longer matches the source packet/preflight/capture package.
- Rule: before reusing a standalone runbook after copy, transfer, edit, or context compaction, run `validate_browser_runbook_summary.py`. The validator must reopen `sourceSummary`, rerun full rehearsal validation, and compare packet, ledger, evidence bundle, next-browser-action handoff, and browser-stage authorization-package paths.
- Follow-up: `validate_browser_runbook_summary.py`, `SKILL.md`, and regression tests now cover standalone runbook acceptance and handoff-path drift rejection.
- Context: local-only hardening after a real-site `module_interface_capture` package was prepared from an older read-only preflight.
- Symptom: the pre-mutation gate would reject stale read-only evidence, but `validate_browser_stage_authorization_package.py` and the next-browser-action handoff wrapper could still validate a package shape before the operator reached the gate.
- Evidence: a stale real-site preflight older than the 30-minute gate window produced a valid-looking preparation package until package validation added the same freshness check; the stale package now fails with `preflight freshness: preflight: generatedAt is stale`.
- Risk: an operator could ask the user to authorize a browser mutation from an already-expired scan, wasting the authorization round or, worse, relying on stale field/module state.
- Rule: any browser-stage authorization package or next-browser-action handoff that emits executable gate commands must validate the supplied preflight freshness before asking for action-time authorization. If it is stale or lacks `generatedAt`, refresh read-only evidence first.
- Follow-up: `validate_browser_stage_authorization_package.py`, `make_next_browser_action_handoff.py`, `validate_next_browser_action_handoff.py`, and regression tests now enforce this freshness gate.

## 2026-06-30 Browser Scan Redaction Findings

- Raw read-only browser scans can leak account-menu text, emails, language/sidebar controls, site-selector labels, frontend domain strings, and long page/body text even when the final run evidence converter filters setup-page evidence.
- Redaction must happen before storing, reusing, or converting a scan artifact. Filtering only inside `make_existing_site_evidence_from_scan.py` is too late because the raw scan can already become a handoff artifact.
- Preserve only the proof surface needed for evidence: `siteKey`, existing site keys, create-dialog state, backend module URLs under `workspace.laicms.com`, neutral headings, table headers, input placeholders, and control labels.
- Use `scripts/redact_browser_scan.py` before `scripts/make_existing_site_evidence_from_scan.py`. The redactor should fail if protected backend URLs leave `workspace.laicms.com` or site keys do not match the safe key shape.
- Add regression coverage whenever scan redaction changes: confirm emails/front-end domain labels/sidebar-language noise/raw body text are removed, and confirm the redacted scan still converts into valid existing-site read-only evidence.
- Context: real read-only `/sites` refresh followed by scan-to-evidence conversion.
- Symptom: the browser controller produced `sites.existingSiteKeysBeforeCreate` plus nested `createDialog.dialogs[]` and `dialogClosed.dialogCount: 0`, while the converter only accepted `sites.existingSiteKeys` and flat `createDialog.fields/buttons/headings/closedVerified`.
- Evidence: conversion failed with `scan.sites.existingSiteKeys must be an array` even though the redacted scan had scoped site-card proof, closed dialog proof, and same-site module URLs.
- Risk: operators may hand-edit redacted JSON or skip the deterministic converter after a valid browser scan, weakening evidence freshness and redaction guarantees.
- Rule: scan converters must accept both helper-oriented flat scan fields and controller-oriented nested dialog/key aliases, while still requiring scoped site keys, closed-dialog proof, and same-site module URLs.
- Follow-up: `make_existing_site_evidence_from_scan.py`, `redact_browser_scan.py`, and regressions now accept `existingSiteKeysBeforeCreate` and nested dialog scans.
- Context: extracting existing site keys from the `/sites` page during a read-only refresh.
- Symptom: selecting generic `[data-slot=card]` also matched nested card headers, causing incomplete site-key extraction even when the page visibly contained multiple cards.
- Evidence: a narrower debug scan showed three top-level `group/card` containers with scoped default frontend domains, backend buttons, and open-site buttons, including the current `{siteKey}`.
- Risk: a partial existing-site list can make preflight evidence look fresh but incomplete, or hide that the current site already exists before a from-scratch ledger tries to create another site.
- Rule: derive existing site keys from scoped top-level site-card containers or backend/open-site button parent cards, not from full-page text and not from broad card selectors that include headers.
- Follow-up: keep `/sites` key extraction scoped and redacted; do not use full-page regex extraction.

## 2026-06-30 Round Closeout Gate Findings

- A text-only instruction to "沉淀到 skill" is easy to miss during long browser rounds. Add a deterministic closeout check after run-summary generation so the final response cannot silently omit the sedimentation outcome.
- `scripts/check_round_closeout.py` should read the JSON written by `summarize_run_status.py --output`, inspect skill file changes, and require either `--sedimentation updated` with a concrete note or `--sedimentation none` with the exact phrase `no reusable skill update needed`.
- The closeout gate must also receive at least one `--round-issue` observation. This prevents an operator from running the mechanical closeout while omitting the actual problem list or no-change check.
- Treat closeout as a reporting gate, not as proof of launch or upload completion. It verifies that the operator reports `proven`, `missing`, `completionGaps`, `nextActions`, and skill sedimentation status before handing back control.
- Do not document nonexistent CLI flags. `summarize_run_status.py` writes machine-readable JSON with `--output`; reserve `--json` for helpers that actually define it, such as frontend audit and closeout output.
- Context: local-only maintenance after the operator emphasized that every conversation turn must sediment reusable problems into the skill.
- Symptom: `check_round_closeout.py` accepted the command-line `--sedimentation`, `--note`, and `--changed-files` values without checking whether a maintenance summary's own `sedimentation` block matched those values.
- Evidence: a stale or hand-edited `allincms_round_maintenance_summary` could claim a different status, note, or file list while the closeout command still passed from its arguments.
- Risk: a future turn could appear closed out in the terminal while the durable summary artifact records a contradictory no-update/update state.
- Rule: when a summary contains a `sedimentation` block, the closeout gate must require its `status`, `note`, `changedFiles`, and `findingsRecorded` values to match the closeout arguments. Maintenance summaries must always include that block.
- Follow-up: `check_round_closeout.py` and regression tests now reject mismatched internal sedimentation status and changed file lists.
- Context: local-only closeout hardening after the operator required that encountered problems be recorded into the skill every round.
- Symptom: even with a sedimentation status, a closeout command could pass without carrying the actual per-turn issue list that justified `updated` or `none`.
- Evidence: run-evidence closeout examples only supplied `--sedimentation` and `--note`; maintenance summaries had no machine-readable `roundIssues` block.
- Risk: future operators could satisfy the closeout ritual while leaving reusable LAICMS problems in chat history only, or a maintenance summary could disagree with the issue list used at final response time.
- Rule: every closeout must include at least one `--round-issue` item. Maintenance summaries must store `roundIssues.checked`, `roundIssues.items`, `reusableFindingsRecorded`, and `noReusableUpdateNeeded`, and `check_round_closeout.py` must reject summaries whose issue list differs from the closeout arguments.
- Follow-up: `make_round_maintenance_summary.py`, `check_round_closeout.py`, `SKILL.md`, and regression tests now enforce per-round issue observations.
- Context: same local-only closeout hardening round.
- Symptom: new regression functions were added to `test_validate_run_evidence.py`, but the file uses a hand-maintained `main()` invocation list, so tests can be defined but never executed.
- Evidence: the first regression command passed before the new mismatch tests appeared in the tail `main()` list.
- Risk: future helper hardening can look tested while the new checks are dead code.
- Rule: when adding tests to this file, update the bottom `main()` invocation list in the same edit and inspect it before accepting a passing test run.
- Follow-up: the new sedimentation mismatch tests are now included in `main()`.

## 2026-06-30 Site-Creation Simulation Findings

- A local create-site dry run should exercise the same summary states the real browser workflow needs, including the middle state where site creation and static launch are proven but content upload is still missing.
- `scripts/simulate_site_creation_chain.py --include-simulated-static-launch` should add redacted `frontendRendering` and `launchReadiness` blocks for static route patterns only. This lets `summarize_run_status.py --require-created-site` prove `static_frontend_routes_render` and `theme_route_launch_ready` while still keeping request capture, sample verification, and cleanup as completion gaps.
- Keep the warning explicit: simulated static launch evidence proves helper compatibility and state modeling, not that a remote site was created or that real frontend pages rendered.

## 2026-06-30 Probe Lifecycle Simulation Findings

- From-scratch runs need a local rehearsal for the content-probe half, not only the create-site half. Add `scripts/simulate_probe_lifecycle.py` to exercise create probe, save/request capture, publish/sample verification, cleanup, final summary, and closeout as separate staged artifacts.
- A verified `siteCreation.status: created_verified` run must be allowed to proceed into `mutating_probe` and `batch_upload` phases. The validator should keep created-site proof while allowing the current authorization to be probe/save/publish/cleanup rather than forcing the old create-site authorization forever.
- Probe lifecycle gates need stage-aware validation. Before save, request and sample proof are intentionally absent; before publish, sample proof is intentionally absent. The gate should tolerate only the missing proof for the current stage and still reject unrelated validation errors.
- `uploadInScope` should mean request/sample upload evidence is in scope, not merely that a probe draft was created. Otherwise a valid create-probe handoff cannot be represented as phase evidence.
- Simulated probe lifecycle completion proves helper compatibility only. It must not be reported as real content upload completion unless backed by browser request capture, backend persistence, frontend detail verification, and cleanup evidence from the actual site.
- Local probe lifecycle artifacts must set `localOnly: true`, `simulationOnly: true`, `remoteMutationsPerformed: false`, and `completionClaimed: false`. A summary may show zero modeled completion gaps while still keeping `complete: false`; only real browser evidence may claim remote completion.

## 2026-06-30 Full Local E2E Simulation Findings

- Running site-creation and probe-lifecycle dry runs separately can leave a false sense that the whole workflow is rehearsed when only one half was checked. Add `scripts/simulate_full_e2e_chain.py` as the preferred one-command local rehearsal.
- The full simulator should preserve separate subdirectories for `01-site-creation` and `02-probe-lifecycle`, plus a small top-level `full-e2e-summary.json` with `localOnly: true` and `remoteMutationsPerformed: false`.
- Treat `probeSummary.complete: true` inside the full simulator as local helper compatibility only. It is not remote completion and must not trigger `update_goal complete`.

## 2026-06-30 Operation-Round Problem Logging Findings

- Context: local-only skill maintenance round after the operator was instructed to record encountered problems into the skill every round.
- Symptom: the existing closeout language emphasized hands-on browser rounds, which could be misread as excluding local simulation, helper-script validation, request-analysis, or documentation-only rounds.
- Evidence: the closeout gate existed, but `SKILL.md` and this reference used browser/hands-on wording in several mandatory instructions.
- Risk: future operators might run local rehearsals or patch helper scripts without recording reusable problems, causing command drift and validation gaps to stay in conversation history only.
- Rule: every AllinCMS skill turn must explicitly check and record reusable problems or state `no reusable skill update needed after checking`, regardless of whether remote LAICMS was mutated.
- Follow-up: keep `scripts/check_round_closeout.py` as the deterministic final gate, and update examples whenever a helper command or summary field changes.
- Context: local-only skill validation after broadening the closeout rule from browser rounds to all operation rounds.
- Symptom: `scripts/audit_skill_hygiene.py` still required the old literal marker `Every hands-on round must end with a skill sedimentation pass`, so hygiene failed after the docs were correctly generalized.
- Evidence: hygiene audit failed while `quick_validate.py`, Python compilation, and closeout check passed.
- Risk: stale marker checks can block valid skill wording changes or encourage operators to preserve obsolete terminology just to satisfy a script.
- Rule: when the skill changes a mandatory phrase, update the hygiene marker in the same round and record the command drift as an operational finding.
- Follow-up: keep marker checks semantic enough to protect the rule while avoiding obsolete wording locks.

## 2026-06-30 Per-Turn Sedimentation Clarification Findings

- Context: local-only skill maintenance after the operator was instructed that every conversation turn must sediment reusable problems into the skill.
- Symptom: the existing rule had been broadened from hands-on browser rounds to operation rounds, but that still left ambiguity for pure planning, discussion, request-analysis, and validation-only turns.
- Evidence: `SKILL.md` and this reference used `operation round` language, while the requested operating behavior was per skill turn.
- Risk: future operators could treat a non-browser reply as outside the closeout gate and leave reusable command drift, validation gaps, or safer sequencing rules only in chat history.
- Rule: every AllinCMS skill turn must run the sedimentation check before final response. If reusable platform or workflow learning appeared, update this skill package; otherwise explicitly report `no reusable skill update needed after checking`.
- Follow-up: hygiene markers now check for the per-turn wording so future edits cannot silently revert to the narrower rule.

## 2026-06-30 Final Frontend Audit Stage-Result Findings

- Context: local-only helper maintenance for the staged browser execution flow after final audit input generation was already available.
- Symptom: the workflow could generate final audit URL/status files and redacted frontend reports, but lacked a deterministic bridge from that report to the `final_frontend_audit` browser-stage result.
- Evidence: `final_frontend_audit` requires HTTP status report, DOM/rich-text report, image report, and an empty broken-entry list before cleanup can unlock; without a converter, operators had to hand-write `proofRecorded` and blockers.
- Risk: hand-written final audit proof can accidentally mark cleanup ready when one detail page, image, raw Markdown marker, or expected status still fails.
- Rule: convert redacted final frontend audit reports with `scripts/make_final_frontend_audit_stage_result.py` and apply that generated result to the execution ledger. A partial result must keep cleanup locked until the same stage is recovered and completed.
- Follow-up: regression tests now cover completed reports, HTTP mismatch, DOM/rich-text issues, image issues, warning escalation with `--fail-on-warn`, and wrong-stage packet rejection.

## 2026-06-30 Browser Runbook Summary Findings

- Context: local-only continuation after full rehearsal began producing many stage packets, ledgers, partial results, recovery packets, and handoff artifacts.
- Symptom: the validated rehearsal summary listed every artifact, but did not provide a compact operator-facing answer for the next real browser step.
- Evidence: a from-scratch rehearsal can write dozens of valid JSON files while the only safe real next step is still a read-only `/sites` refresh and create-dialog open/close proof. Mutation command templates may be suppressed because targets are still simulated or templated.
- Risk: future operators could pick a later stage artifact from the long list, run a suppressed/template command against LAICMS, or treat a local-only rehearsal as action-time authorization.
- Rule: after `run_full_rehearsal.py` and `validate_full_rehearsal.py`, generate `scripts/make_browser_runbook_summary.py` and follow its `nextRealBrowserStep`, `requiredRealEvidenceBeforeMutation`, and `stopConditions` before touching the browser.
- Follow-up: regression tests now require valid rehearsal summaries to expose the initial real-browser read-only stage and invalid rehearsal summaries to report `blocked` instead of a runnable next step.
- Context: follow-up helper integration for the same local-only rehearsal flow.
- Symptom: leaving the runbook summary as a separate manual command made it easy to validate a full rehearsal but forget the compact next-real-browser instruction before returning to LAICMS.
- Evidence: `run_full_rehearsal.py` already writes the stage ledger and first packet, so the safe next step is known at generation time; manual post-processing only duplicates state and can drift from `rehearsal-summary.json`.
- Risk: an operator could act from the long artifact list, miss `commandsSuppressed`, or skip the read-only `/sites` refresh before a real mutation.
- Rule: `run_full_rehearsal.py` must write `browser-runbook-summary.json` as an integrated artifact, and `validate_full_rehearsal.py` must cross-check its stage id, authorization requirement, suppressed-command status, ledger next stage, and stop conditions.
- Follow-up: keep `make_browser_runbook_summary.py` for external or older summaries, but treat the integrated artifact as the normal one-command rehearsal output.

## 2026-06-30 Theme Launch Authorization Split Findings

- Context: local-only helper maintenance for real-browser staged operation after module interface capture, before theme/page/route launch mutations.
- Symptom: `theme_page_route_launch` was modeled as one aggregate browser stage, while the actual launch workflow contains separate mutations such as save design, publish design, enable page, set homepage, create route, and bind route.
- Evidence: the existing authorization and pre-mutation gate helpers already supported granular site actions, but `prepare_browser_stage_authorization.py` could only prepare create-site and module-capture authorization packages.
- Risk: an operator asking whether JSON submission is faster could accidentally treat the aggregate launch stage as one broad permission and replay or click multiple theme/route mutations without per-action proof.
- Rule: prepare exactly one launch sub-action at a time with `--launch-action` and a real current-site `--launch-target`. If the target is templated or simulated, suppress copyable commands and use the output only as a template.
- Follow-up: regression tests now require `theme_page_route_launch` to reject missing `--launch-action`, suppress templated-target commands, and emit `make_authorization_record.py` plus `check_pre_mutation_gate.py` only for a real action-specific target.

## 2026-06-30 Content Probe Stage Authorization Findings

- Context: local-only helper maintenance for the staged browser plan after static frontend audit, before content request capture and upload.
- Symptom: the browser execution plan exposed `content_probe_create`, `save_request_capture`, `publish_sample_verify`, and `cleanup_probes` as authorization-required stages, but the stage authorization helper did not translate those packets into the existing probe gates.
- Evidence: `make_authorization_record.py` and `check_pre_mutation_gate.py` already supported `create_post_probe`, `create_product_probe`, `create_form_probe`, `save_probe`, `publish_probe`, and `cleanup_probe`; the missing piece was the packet-to-action bridge.
- Risk: a real browser run could reach content upload and either stop with a generic unsupported-stage package or tempt an operator to hand-write broad save/publish/cleanup authorization commands.
- Rule: content probe lifecycle packets must use `--content-type` and prepare exactly one create, save, publish, or cleanup probe action. Do not infer content type from `{contentType}` templates, and do not treat create-probe authorization as permission to save, publish, batch upload, or cleanup.
- Follow-up: regression tests now require missing `--content-type` to fail, templated targets to suppress copyable commands, and real products targets to emit action-specific authorization and pre-mutation gate commands for create/save/publish/cleanup probe stages.

## 2026-06-30 Batch Upload Stage Authorization Findings

- Context: local-only helper maintenance after manifest schema gate and sample verification unlocked the `batch_upload_publish` browser stage.
- Symptom: `make_authorization_record.py` already accepted `batch_upload` and `batch_publish`, but `check_pre_mutation_gate.py` and `prepare_browser_stage_authorization.py` did not provide a matching batch-stage gate or browser-stage authorization package.
- Evidence: the staged runbook could present `batch_upload_publish` as authorization-required while the local pre-mutation gate had no batch action path, leaving operators with either unsupported packages or hand-written commands.
- Risk: a real run could start batch upload without proving the current-site save request, sample frontend verification, schema gate, progress log, and frontend detail audit expectations for every uploaded route.
- Rule: `batch_upload_publish` must require `--content-type`, support only posts/products batches, and emit commands only for a real current-site target. The pre-mutation gate must require schema gate pass, sample verification, progress log, and frontend detail audit fields before batch mutation.
- Follow-up: regression tests now cover accepted batch upload gates, missing sample proof, missing frontend detail audit fields, wrong module targets, templated command suppression, and real-target batch authorization/gate command generation.

## 2026-06-30 Forms/Media/Settings Authorization Split Findings

- Context: local-only helper maintenance after completed batch upload unlocked the `forms_media_settings` browser stage.
- Symptom: `forms_media_settings` is an aggregate stage that can include site settings, theme creation, form creation, domain binding, tracking tags, and media upload, but the browser-stage authorization helper had no action-specific bridge for it.
- Evidence: lower-level authorization and gates already existed for `save_site_settings`, `create_theme`, `create_form`, `add_domain`, and `add_tracking_tag`; `upload_media` existed only as an intentionally ungated capture action because multipart/storage behavior still needs dedicated proof.
- Risk: a real browser operator could ask for one broad settings/media/forms authorization and accidentally combine unrelated mutations, or emit JSON/replay commands for media upload before request storage behavior is understood.
- Historical rule at that time: `forms_media_settings` required `--settings-action`; `upload_media` was command-suppressed and UI-first. **The command-suppression fact remains, but UI-first is superseded on 2026-07-27: actual upload now routes to the canonical adapter.**
- Follow-up: regression tests now require missing `--settings-action` to fail, real settings/form/domain/tracking targets to emit action-specific gates, and media upload to stay ungated with no copyable mutation command.

## 2026-06-30 Final Frontend Audit Input Findings

- Context: local-only helper maintenance for the stage after batch upload and forms/media/settings proof.
- Symptom: frontend audit tooling could check supplied URLs, but the final audit URL list still had to be hand-maintained from manifest slugs or batch progress output.
- Evidence: `audit_frontend_rendering.py` accepts `--urls-file` and status maps, while `validate_manifest.py` already knows the posts/products item slugs and frontend base URL.
- Risk: a real batch upload could miss one uploaded detail route in final QA, especially when batch progress includes many created/updated items or duplicate-slug handling.
- Rule: generate final audit URL/status files from the schema-verified manifest, and require a complete progress log when the run is using batch proof to unlock final audit. Runtime URL files may contain concrete slugs; keep them in temporary run artifacts and only copy redacted audit evidence into durable run evidence.
- Follow-up: `make_final_frontend_audit_inputs.py` now builds expected-200 static/detail audit inputs and can fail when any manifest slug lacks successful save, backend verification, frontend verification, or cover/media proof in the progress log.
- Context: continuation of final-audit input hardening during local-only rehearsal toward a launchable site.
- Symptom: the progress completeness check proved every manifest slug had a progress entry, but did not reject extra progress entries whose slug was not in the manifest. It also allowed `publishStatus: skipped` even though final detail routes are generated with expected status 200.
- Evidence: `make_final_frontend_audit_inputs.py` built final audit URLs only from manifest slugs, so an extra uploaded/progress slug could avoid final HTTP/DOM/image audit entirely. A skipped publish status contradicted the expected 200 detail route generated for the same manifest item.
- Risk: an operator could treat batch upload as final-audit-ready while an unintended extra entry exists, or while a manifest item was saved/verified in backend but not actually published for public detail-page audit.
- Rule: when `--require-progress-complete` is used, the manifest slug set and progress-log slug set must match exactly, and every item expected to have a public detail URL must have `publishStatus: ok`.
- Follow-up: `make_final_frontend_audit_inputs.py` and regression tests now reject extra progress slugs and skipped publish status before generating final audit inputs.
- Context: local-only helper maintenance after final audit input generation and stage-result conversion both existed.
- Symptom: `make_final_frontend_audit_stage_result.py` could mark a clean report as completed without checking whether the report covered every route generated by `make_final_frontend_audit_inputs.py`.
- Evidence: a report with only `/products` and no `/products/{slug}` could still have correct HTTP/DOM/image structure for the routes it contained; without the input summary or expected-status map, the missing detail route is invisible.
- Risk: cleanup could unlock while a static route or uploaded detail route was never audited, leaving broken or unpublished pages on a site that appears launch-ready.
- Rule: final frontend audit stage-result conversion should include the audit inputs summary and expected statuses JSON. The converter must compare report count and redacted route patterns against those expected inputs and keep the stage partial if any expected route is missing.
- Follow-up: `make_final_frontend_audit_stage_result.py`, `SKILL.md`, and regression tests now support `--audit-inputs-summary-json` and `--expected-statuses-json` coverage checks.
- Context: follow-up local rehearsal after adding final-audit coverage checks to the converter.
- Symptom: the full rehearsal still hand-built `final_frontend_audit` stage results with `build_stage_result()`, so the new missing-route coverage gate was covered only by focused helper tests, not by the preferred from-scratch rehearsal.
- Evidence: `run_full_rehearsal.py` used fixed evidence pointers such as `local://final-audit-broken-entry-list-empty.json` and never generated simulated audit reports, inputs summary, or expected-statuses artifacts for `make_final_frontend_audit_stage_result.py`.
- Risk: the documented one-command rehearsal could pass while not exercising the strongest final-QA gate, letting future changes break coverage-aware final audit conversion without failing the main runbook validation.
- Rule: when a helper becomes the canonical bridge for a browser stage, the full rehearsal should exercise that helper and validator should assert the helper-specific artifacts and blockers, not just generic stage-result shape.
- Follow-up: `run_full_rehearsal.py` now generates simulated final audit report/input/status artifacts and builds partial/complete final-audit stage results through the converter; `validate_full_rehearsal.py` and tests assert coverage blockers and evidence pointers.

## 2026-06-30 Capture Plan Gate Coverage Findings

- Context: local-only skill maintenance after module scan planning produced capture stages for products, posts, media, themes, routes, forms, site-info, domains, and tracking.
- Symptom: a new capture-plan `authorizationAction` can be added by `plan_module_capture.py` while `make_authorization_record.py`, `prepare_capture_authorization.py`, or `check_pre_mutation_gate.py` lacks matching coverage.
- Evidence: domain and tracking capture stages needed helper/gate additions after the plan already exposed `add_domain` and `add_tracking_tag`; this mismatch would have been caught earlier by a plan-level coverage validator.
- Risk: an operator could enter a real browser mutation stage with suggested authorization text but no working local gate, or silently treat an unknown action as safe.
- Rule: after generating a module capture plan and before preparing any browser capture authorization, run `scripts/validate_capture_plan_gate_coverage.py` against the full plan. Unknown actions, missing field templates, and missing gates must fail unless the action is explicitly allowlisted as ungated.
- Historical follow-up: `upload_media` was the only ungated allowlist entry and was UI-first. **Superseded on 2026-07-27: exact authorization is still required, while execution now uses the canonical adapter rather than UI selection.**
- Context: local regression test for the new capture-plan coverage validator.
- Symptom: passing an empty allowlist still behaved like the default allowlist because the helper used truthiness when choosing defaults.
- Evidence: the test that removed all ungated exceptions expected `upload_media` to fail, but the validator still passed until the defaulting logic was corrected.
- Risk: tests cannot prove that an ungated action is allowed only by explicit policy, so future unsupported mutation actions could appear safe by accident.
- Rule: use `None` to mean "use default policy"; preserve an empty collection as an intentional "allow nothing" policy in gate and validator helpers.
- Follow-up: keep regression coverage for both default allowlist and empty allowlist paths whenever adding action-policy validators.
- Context: documentation update after a full local rehearsal generated the real capture-plan artifact path.
- Symptom: the new example command initially pointed to `full-e2e/03-module-interface/module-capture-plan.json`, but the rehearsal writes `full-e2e/03-module-interface-plan/module-capture-plan.json`.
- Evidence: `run_full_rehearsal.py` output listed `artifacts.moduleCapturePlan` under `03-module-interface-plan`.
- Risk: operators copying the documented command would hit a missing file and might skip the new coverage gate during browser preparation.
- Rule: whenever adding command examples that target rehearsal artifacts, verify the exact path against a freshly generated `rehearsal-summary.json` or command output before finalizing the skill text.
- Follow-up: rerun the new gate against the real rehearsal artifact path as part of this round's validation.
- Context: local-only rehearsal integration after the capture-plan coverage validator existed only as a standalone command and documentation rule.
- Symptom: a full rehearsal could pass `validate_full_rehearsal.py` even if the module capture plan later drifted to an unsupported `authorizationAction`, unless the operator remembered to run the new coverage script separately.
- Evidence: the validator rechecked full E2E, handoff, launch plan, execution ledger, packets, and coverage ledgers, but did not recompute `validate_plan_gate_coverage()` from the generated module capture plan.
- Risk: the preferred one-command rehearsal would not actually prove browser-capture readiness for action authorization/gate coverage, creating a gap between documented SOP and machine validation.
- Rule: preferred rehearsal artifacts must include `capture-plan-gate-coverage.json`, and `validate_full_rehearsal.py` must recompute coverage from the current module capture plan and compare it with the saved artifact and summary.
- Follow-up: keep tests that corrupt both the saved coverage artifact and the underlying capture plan action; the top-level rehearsal validator must fail in both cases.

## 2026-06-30 Browser Stage Authorization Findings

- Context: local-only continuation from the staged browser ledger after `setup_pages_inspection` unlocks `module_interface_capture`.
- Symptom: `prepare_browser_stage_authorization.py` supported `create_site_submit` only; the next authorization-required stage returned `gateSupported: false`, even though a full module capture plan and per-action authorization helpers already existed.
- Evidence: the browser execution plan exposes `module_interface_capture` as an aggregate stage, while the module capture plan contains concrete stages such as `products:create`, `posts:create`, `media:upload`, `themes:create`, `routes:create`, and so on.
- Risk: an operator could either stop after setup inspection or request overly broad authorization for the aggregate module capture stage, instead of capturing one module/action at a time.
- Rule: browser-stage authorization for `module_interface_capture` must delegate to the capture-plan authorization helper and select exactly one `module:action`. If a coverage file exists, use `nextUncapturedStageKey`; otherwise use the first capture-plan stage.
- Follow-up: simulated targets must still suppress executable commands by default. Use `--allow-command-output` only for local tests, never for real browser mutation preparation.

## 2026-06-30 Recovery Packet Artifact Findings

- Context: local-only full-rehearsal maintenance for the browser execution ledger and partial-stage recovery flow.
- Symptom: a partial stage could be completed from a recovery packet, but only some recovery packets were persisted as explicit artifacts; the rest were easy to inspect only while the script was still running.
- Evidence: the rehearsal summary already tracked `completedFromRecoveryPacket: true`, but regression coverage did not require every non-module partial gate to expose its recovery packet path, safety validation, partial-summary marker, and `artifacts` entry.
- Risk: future operators could claim a completed recovery without an auditable packet proving that the completion used the same blocked stage, missing-proof scope, and recovery-only action boundary.
- Rule: every non-module partial gate that is later recovered must persist `browserStagePacketAfter<Stage>PartialRecoveryPath`, validate `browserStagePacketAfter<Stage>PartialRecoverySafety.ok`, set the partial summary's `recoveryPacketStageId` and `recoveryPacket: true`, and include the recovery packet in the top-level `artifacts` map.
- Follow-up: keep `run_full_rehearsal.py`, `validate_full_rehearsal.py`, `test_validate_run_evidence.py`, and `references/e2e-simulation.md` aligned whenever a new browser stage or partial/complete gate is added.

## 2026-06-30 Final Ledger Exhaustion Findings

- Context: local-only full-rehearsal maintenance after cleanup recovery completed every browser execution stage.
- Symptom: the ledger had all stages completed and no `nextStageId`, but the rehearsal summary did not explicitly prove that another next-stage packet could not be generated.
- Evidence: `build_browser_stage_packet.py` already rejects a fully exhausted ledger with `ledger has no nextStageId; no stage is ready`; the missing piece was a summary and validator assertion for that terminal stop condition.
- Risk: future operators could finish cleanup, see a valid ledger artifact, and still attempt to generate or follow another browser packet as a generic continuation.
- Rule: after cleanup completion, the full rehearsal must record `finalLedgerExhaustion` with all stages completed, empty `nextStageId`, `packetBuildRejected: true`, and a rejection reason containing `no nextStageId`.
- Follow-up: keep this terminal check in `run_full_rehearsal.py`, `validate_full_rehearsal.py`, and `test_validate_run_evidence.py` whenever the stage list changes.

## 2026-06-30 Stage Result Template Drift Findings

- Context: local-only skill maintenance after partial browser-stage handling had been added across module capture, launch, audit, upload, settings, and cleanup gates.
- Symptom: `next-browser-stage-packet.json` still showed `evidenceCaptureTemplate.status: completed|blocked`, even though the validator and ledger application already supported `partial`.
- Evidence: partial stage results were required in full rehearsal, but the operator-facing packet template omitted `partial` as a valid status.
- Risk: a browser operator could force incomplete proof into `completed` or `blocked`, losing the precise partial state that keeps dependent mutation stages locked while preserving captured evidence.
- Rule: every browser-stage packet must present `evidenceCaptureTemplate.status: completed|blocked|partial`, and packet validation should reject stale two-status templates.
- Follow-up: keep packet templates, `validate_browser_stage_packet`, stage-result validation, and E2E documentation aligned whenever a new stage status is introduced.

## 2026-06-30 Source Input Requirements Helper Findings

- Context: local-only skill maintenance after the operator required each run to record which fields future PDFs, catalogs, websites, spreadsheets, or briefs must provide.
- Symptom: the field contract described source-input requirements, but operators still had to hand-write per-run JSON and could omit whether a field was source-derived, user-confirmed, or blocked until schema capture.
- Evidence: product save capture can prove keys such as `name`, `slug`, `description`, `media`, `mediaList`, `specifications`, and `content`, while readiness evidence can still block rich body/media because non-empty body blocks or real media upload proof are missing.
- Risk: PDF/catalog extraction could generate a plausible manifest that invents specs, contacts, images, form destinations, or rich body structure before the current site schema is actually captured.
- Rule: before source extraction and manifest generation, run `make_source_input_requirements.py` for the current site/content types and treat `blockedUntil` as hard blockers unless the user records an explicit omission or acceptance rule in run evidence.
- Follow-up: `SKILL.md` and `field-contract.md` now route source-material ingestion through the helper before manifest generation.
- Context: local-only full-rehearsal hardening after the helper existed as a standalone script.
- Symptom: the full rehearsal still proved only draft manifest validation and schema-gate failure; it did not require the source-input requirements artifact before entering `manifest_schema_gate`.
- Evidence: `run_full_rehearsal.py` now writes `full-e2e/04-manifest-rehearsal/source-input-requirements.json`, includes it in manifest-gate partial and completed stage evidence pointers, and `validate_full_rehearsal.py` rejects rehearsal summaries that omit the artifact or blocked-source summary.
- Risk: future agents could skip the user/PDF/source-field planning step and proceed from source extraction straight to schema gate or batch-upload preparation.
- Rule: every manifest rehearsal and full site-build rehearsal must produce source-input requirements and keep it blocked until current-site schema/media/body proof or explicit omission rules exist.
- Follow-up: `simulate_manifest_rehearsal.py`, `validate_manifest_rehearsal.py`, `simulate_full_e2e_chain.py`, `validate_full_e2e_simulation.py`, `run_full_rehearsal.py`, `validate_full_rehearsal.py`, and regression tests now enforce this artifact.
- Context: real-site continuation planning after a run summary already emitted `nextActionDetails` for `create_product_probe`.
- Symptom: the staged browser queue helper expected a next-browser-action handoff/readiness artifact, so a valid run summary could identify the next action without producing the 10-stage queue needed for goal-level progress reporting.
- Evidence: `make_browser_stage_queue_from_summary.py` bridges `summarize_run_status.py --output` directly into a local queue, preserving the current authorization text and appending the machine-checked `do not save or publish` stop condition. `make_e2e_gap_audit.py` now also accepts `--source-input-requirements` and reports blocked source fields alongside remote-operation gaps.
- Risk: operators could report only the next mutation without showing later schema, posts, batch, source-material, and final-QA blockers; or they could skip the source-field blockers when assessing whether the site is close to launch.
- Rule: when resuming from a real run summary, generate a browser stage queue from `nextActionDetails`, then generate an E2E gap audit with upload readiness and source-input requirements before reporting progress or asking for the next action-time authorization.
- Follow-up: `SKILL.md`, `make_browser_stage_queue_from_summary.py`, `make_e2e_gap_audit.py`, and regression tests now cover this continuation path.

## 2026-06-30 Ledger Update Command Findings

- Context: local-only maintenance of the browser-stage packet used to guide one real browser stage at a time.
- Symptom: `ledgerUpdate.commandTemplate` still recommended rebuilding the ledger with `build_browser_execution_ledger.py --completed-stage-ids` after evidence was recorded.
- Evidence: `apply_browser_stage_result.py` already exists to validate a redacted stage result against the packet and preserve evidence pointers, proofRecorded, partial/blocking issues, and last-applied status.
- Risk: rebuilding from completed stage ids discards audit evidence and cannot represent `partial` or `blocked` outcomes, so a real browser operator could lose the exact proof trail that prevents unsafe dependency jumps.
- Rule: browser-stage packets must tell operators to update the ledger with `apply_browser_stage_result.py --result-json`, not with `--completed-stage-ids`.
- Follow-up: packet validation now rejects command templates that omit `apply_browser_stage_result.py`, omit `--result-json`, or contain `--completed-stage-ids`.

## 2026-06-30 Browser Execution Planning Findings

- Context: local-only skill maintenance for moving from simulated site creation toward real browser operation.
- Symptom: full rehearsal artifacts proved helper compatibility and produced the next single capture handoff, but they did not provide one ordered browser runbook for the whole site-build path.
- Evidence: `run_full_rehearsal.py` wrote full E2E evidence, a handoff, and a launch plan; the missing artifact was a stage list separating read-only refresh, create-site submit, setup inspection, module capture, launch work, content probe, schema gate, batch upload, final audit, and cleanup.
- Risk: future operators could treat one broad user instruction as permission to combine multiple mutations, or could jump from local JSON rehearsal directly to real replay without a fresh request capture and persistence proof.
- Rule: before real browser work that spans site creation, theme/page/route launch, and content upload, generate and validate `browser-execution-plan.json`. Execute at most one `requires_authorization` stage per explicit action-time authorization, and keep verification stages separate from mutation stages.
- Follow-up: `scripts/run_full_rehearsal.py` now writes `browser-execution-plan.json`, and `scripts/validate_full_rehearsal.py` cross-checks it with the top-level summary.
- Context: local-only continuation after adding the staged browser execution plan.
- Symptom: the plan correctly listed all real-browser stages, but it did not record current progress or compute which single stage is actually ready next.
- Evidence: a static plan can list `create_site_submit`, `theme_page_route_launch`, and `batch_upload_publish` together even though each depends on previous proof and separate authorization.
- Risk: an operator could read the whole plan as an actionable checklist and jump to a later mutation before refreshing read-only evidence or completing dependencies.
- Rule: generate `browser-execution-ledger.json` from the plan before real browser work. The ledger must expose only the next ready stage, keep later stages pending until dependencies are completed, and be regenerated after every completed, blocked, or skipped stage.
- Follow-up: `scripts/run_full_rehearsal.py` now writes `browser-execution-ledger.json`, and `scripts/validate_full_rehearsal.py` cross-checks ledger safety, counts, and `nextStageId`.
- Context: local-only continuation after adding the execution ledger.
- Symptom: the ledger identified the one next safe stage, but it still required the operator to manually extract allowed actions, proof requirements, stop condition, and the ledger update command.
- Evidence: `browser-execution-ledger.json` contained entries for all stages; the next actionable unit was only one entry, not the whole ledger.
- Risk: manual extraction from the ledger can omit required proof, forget the stop condition, or accidentally include a pending future stage in the browser instructions.
- Rule: before touching the browser, generate `next-browser-stage-packet.json` from the ledger and use that packet as the immediate operator instruction. The packet must target only `ledger.nextStageId`, include required proof and stop conditions, and provide a ledger update template after evidence is recorded.
- Follow-up: `scripts/run_full_rehearsal.py` now writes `next-browser-stage-packet.json`, and `scripts/validate_full_rehearsal.py` cross-checks that the packet stage matches `ledger.nextStageId`.
- Context: local-only continuation after adding the next-stage packet.
- Symptom: the packet included an evidence-capture template, but there was no deterministic way to validate the filled result and apply it back to the ledger.
- Evidence: a completed browser stage needs required proof coverage, redacted evidence pointers, and a dependency-safe next-stage calculation; hand-editing the ledger can bypass all three.
- Risk: operators could mark a stage complete without recording required proof, leave later stages pending even after dependencies are complete, or accidentally advance to the wrong next mutation stage.
- Rule: after each browser stage, write a redacted `allincms_browser_stage_result`, validate it against the packet, and apply it with `scripts/apply_browser_stage_result.py`. Never hand-edit ledger status for real LAICMS work.
- Follow-up: full rehearsal now writes `simulated-first-stage-result.json` and `browser-execution-ledger-after-first-stage.json` to prove the result-application path locally.
- Context: local-only continuation after result application advanced the ledger from read-only refresh to site creation.
- Symptom: the updated ledger could compute `create_site_submit` as ready, but the original implementation had discarded pending-stage allowed actions, so the next packet would have fallen back to a generic instruction.
- Evidence: pending stages had `nextAllowedActions: []` and no preserved source action list; once unblocked, `create_site_submit` needed the concrete action `submit create-site form with authorized name and description only`.
- Risk: generic next-stage packets can blur authorization boundaries and make `/sites` create submit look like a broad continuation command.
- Rule: ledger entries must preserve `plannedActions` for every pending/ready stage and restore them into `nextAllowedActions` when dependencies complete. Also, `create_site_submit` is a pre-site-key action: its authorization text should include the `/sites` target, not require `{realSiteKey}`.
- Follow-up: full rehearsal now writes `next-browser-stage-packet-after-first-stage.json`, proving the next real packet after read-only refresh is a concrete, authorization-required create-site packet.
- Context: local-only continuation after proving the create-site packet can be generated from the post-refresh ledger.
- Symptom: the simulation still stopped before proving what happens after create-site proof is applied.
- Evidence: from-scratch work requires a mandatory read-only setup inspection after site creation; skipping directly to theme/page/content work would miss module field drift and wrong-site context.
- Risk: a successful create-site submit can be mistaken as permission to launch theme, upload content, or mutate settings immediately.
- Rule: after `create_site_submit` completes, apply the create-site result and generate a fresh packet. The next stage must be `setup_pages_inspection`, read-only, and cover site-info, domains, themes, routes, and forms before any further mutation.
- Follow-up: full rehearsal now writes `simulated-create-site-result.json`, `browser-execution-ledger-after-create-site.json`, and `next-browser-stage-packet-after-create-site.json`.
- Context: local-only continuation after proving create-site-to-setup transition.
- Symptom: the rehearsal still stopped before proving that setup inspection feeds into the interface-capture stage.
- Evidence: setup pages expose controls and columns, but those observations are read-only and do not prove JSON replay or mutation payload shape.
- Risk: an operator could treat visible setup controls as enough to start JSON submission or batch changes without a fresh capture.
- Rule: after `setup_pages_inspection` completes, apply the setup result and generate a fresh packet. The next stage must be `module_interface_capture`, require authorization, and capture exactly one module/action before stopping.
- Follow-up: full rehearsal now writes `simulated-setup-pages-result.json`, `browser-execution-ledger-after-setup-pages.json`, and `next-browser-stage-packet-after-setup-pages.json`.
- Context: local-only continuation after generating the first `module_interface_capture` packet.
- Symptom: stage results only supported `completed` and `blocked`, so a one-module capture could be marked completed and automatically unlock dependent launch/settings stages.
- Evidence: the `module_interface_capture` stop condition says to capture exactly one module/action, while `theme_page_route_launch` and `forms_media_settings` depended on the whole `module_interface_capture` stage.
- Risk: a single captured request could be mistaken for site-wide JSON replay readiness, causing theme/page/route launch, settings/media mutations, or batch upload to proceed before interface coverage is proven.
- Rule: one module/action capture should be applied as `partial` unless the run has an explicit current coverage rule proving the entire interface-capture stage complete. Partial results must preserve proof pointers and blocking issues, keep the stage non-completed, and leave later dependent stages locked.
- Follow-up: `apply_browser_stage_result.py` and ledger validation now support `partial`; full rehearsal writes `simulated-module-capture-partial-result.json` and `browser-execution-ledger-after-module-capture-partial.json`.
- Context: local-only continuation after adding `partial` support for `module_interface_capture`.
- Symptom: partial status prevented unsafe advancement, but it did not say which module/action captures were already done or what exact stage remained next.
- Evidence: the capture plan contained multiple stages (`products:create`, `posts:create`, `media:upload`, `themes:create`, `routes:create`, `routes:bind`, `forms:create`, `site-info:save`), while the browser execution ledger had only one aggregate `module_interface_capture` entry.
- Risk: operators could get a safe stop but no actionable next coverage target, or they could repeat the same capture stage and still not know whether JSON replay is ready.
- Rule: maintain a module/action coverage ledger after each capture. A single captured stage must leave `complete: false`, `jsonReplayReady: false`, and `nextUncapturedStageKey` populated unless every planned capture stage is captured or explicitly not applicable.
- Follow-up: added `scripts/update_module_capture_coverage.py`; full rehearsal now writes `simulated-module-capture-stage-result.json` and `module-capture-coverage-after-one-stage.json`.
- Context: first local rehearsal after adding the module-capture coverage helper.
- Symptom: the helper validated an initial, incomplete coverage object before it had `nextUncapturedStageKey`, so the first update failed.
- Evidence: rehearsal stopped with `incomplete coverage must include nextUncapturedStageKey` before writing the coverage artifact.
- Risk: a helper that requires a field it does not initialize blocks the exact first-capture path it is supposed to make safer.
- Rule: initial coverage generation must populate `nextUncapturedStageKey` from the first pending planned stage. Validators should enforce the field, but builders must provide it.
- Follow-up: `empty_coverage()` now initializes `nextUncapturedStageKey`; the rehearsal verifies the one-capture state with `captured=1`, `pending>0`, and `jsonReplayReady=false`.
- Context: local-only continuation after module/action coverage started recording the next missing capture.
- Symptom: the browser execution ledger still had `nextStageId: ""` after a partial aggregate `module_interface_capture`, so the run was safe but could not proceed to the next missing capture packet.
- Evidence: coverage showed `nextUncapturedStageKey: posts:create`, while the aggregate ledger had `module_interface_capture` marked `partial` and no ready stage.
- Risk: operators would either stop indefinitely, hand-edit the ledger, or incorrectly mark `module_interface_capture` completed to continue.
- Rule: after updating module capture coverage, sync coverage back into the browser ledger. If coverage is incomplete, only `module_interface_capture` should become ready again and its actions must name the next missing `module:action`; dependent launch/settings/upload stages stay pending. Only complete coverage may mark the aggregate stage completed and unlock dependencies.
- Follow-up: `update_module_capture_coverage.py` now supports ledger sync and `--ledger-output`; full rehearsal writes `browser-execution-ledger-after-module-capture-coverage-sync.json`.
- Context: local-only continuation after proving incomplete coverage can continue one capture at a time.
- Symptom: the rehearsal still did not prove the positive transition from fully captured module interfaces to the next browser stage.
- Evidence: `sync_ledger_with_coverage()` had code for complete coverage, but no top-level rehearsal artifact showed `module_interface_capture` becoming completed and `theme_page_route_launch` becoming the next packet.
- Risk: operators could trust the no-unlock guard but still lack evidence that the workflow can proceed once capture coverage is genuinely complete.
- Rule: rehearsal must prove both sides of the gate: incomplete coverage keeps downstream stages locked, and complete coverage marks aggregate `module_interface_capture` completed before exposing `theme_page_route_launch`.
- Follow-up: full rehearsal now writes `module-capture-coverage-complete.json`, `browser-execution-ledger-after-module-capture-complete.json`, and `next-browser-stage-packet-after-module-capture-complete.json`.

## 2026-06-30 Module Scan Summary Compatibility Findings

- Context: local-only interface scan summarization using an already redacted browser scan from a temporary AllinCMS site.
- Symptom: `scripts/summarize_module_scan.py` originally accepted only a request-oriented list, while the redacted browser scan artifact used an object root with a `modules` map. The first real command failed before producing JSON suitability output.
- Evidence: the redacted scan contained `siteKey`, `contentType`, `sites`, and `modules`; each module had URL, headings, table headers, inputs, and buttons but no request list.
- Risk: operators could skip the summary step or hand-convert scan JSON, losing the distinction between DOM-only visible controls and captured mutation requests.
- Rule: module scan summary must accept both list-shaped request scans and object-shaped redacted browser scans. DOM-only module evidence is `read_only_only`; visible create/save/upload buttons are only `visible_control_only`, not JSON-ready.
- Follow-up: `summarize_module_scan.py` now normalizes object scans and keeps JSON replay blocked unless POST payload shape, ids, authorization, and persistence proof are captured.
- Context: redaction gate alignment for module scan summaries.
- Symptom: the summary script rejected a redacted scan because it preserved safe real workspace URLs instead of replacing the site key with `{siteKey}`.
- Evidence: `redact_browser_scan.py` and the evidence converter intentionally preserve `workspace.laicms.com/{safeSiteKey}/...` routes as proof of current module navigation, while still dropping account/menu/body noise.
- Risk: incompatible redaction rules make one helper's valid output unusable by the next helper, encouraging manual edits to evidence artifacts.
- Rule: helper-to-helper redaction contracts must match. Accept safe lowercase site-key-shaped workspace paths or `{siteKey}` placeholders, but continue rejecting cookies, auth headers, `next-action`, `next-router-state-tree`, and unsafe path tokens.
- Follow-up: add regression tests whenever a helper consumes artifacts generated by another helper.
- Context: module-scan summary used to answer whether JSON/Server Action replay would be faster for site modules.
- Symptom: per-module `jsonSuitability` was useful, but there was no top-level machine-readable answer for "is replay ready now?" or "what should be captured next?"
- Evidence: the real redacted DOM-only scan found visible create/save/upload controls for products, posts, media, themes, routes, forms, and site-info, but no POST requests or payload shapes.
- Risk: a human operator might read visible controls as enough to start JSON replay, especially when trying to speed up page/theme/content creation.
- Rule: module summaries should emit `jsonReplayReady: false` until a future action-specific validator proves payload shape, ids, authorization, and persistence. Use `captureNextActions` as the next browser-capture checklist, not as a replay plan.
- Follow-up: if a future helper can prove a specific action is replay-ready, it must set readiness per action with proof links, not globally from POST presence.
- Context: local-only planning after a module scan summary showed visible controls across content, media, theme, route, form, and site settings modules.
- Symptom: `captureNextActions` listed the controls to inspect, but did not separate authorization boundaries or stop conditions for browser execution.
- Evidence: the real scan summary produced visible controls for products/posts create, media upload, themes create, routes create/bind, forms create, and site-info save.
- Risk: operators could batch unrelated captures under one broad permission, or accidentally combine create, save, publish, upload, and route binding in a single browser mutation.
- Rule: convert scan summaries into a staged capture plan before browser mutation. Each stage needs its own target, authorization action, stop condition, and required proof; a plan is not permission.
- Follow-up: use `scripts/plan_module_capture.py` after `scripts/summarize_module_scan.py` when deciding the next browser-capture order.
- Context: regression test for capture-plan route proof.
- Symptom: the first assertion checked whether a phrase was directly in the `mustCapture` list, while the script intentionally stores each proof requirement as a list item.
- Evidence: the script output was correct, but the regression failed because list membership requires exact item equality.
- Risk: overly literal tests can force less structured output or hide useful proof granularity.
- Rule: tests for structured capture plans should check fields semantically, such as any list item containing the required proof concept, while still verifying exact action boundaries.
- Follow-up: keep capture-plan output structured as arrays so future browser operators can consume it programmatically.

## 2026-06-30 Full E2E Module-Plan Simulation Findings

- Context: local-only full E2E rehearsal from create-site simulation through content probe simulation.
- Symptom: the full simulator proved site creation and probe lifecycle, but did not produce the module interface scan summary or staged capture plan needed before real browser module captures.
- Evidence: `simulate_full_e2e_chain.py` originally emitted only `01-site-creation/`, `02-probe-lifecycle/`, and `full-e2e-summary.json`.
- Risk: a run could look fully rehearsed while still missing the operational bridge from read-only module inspection to one-action-at-a-time request capture.
- Rule: full local E2E rehearsal should include module interface planning as its own phase. Emit `03-module-interface-plan/` with redacted module scan, scan summary, and capture plan.
- Follow-up: keep `full-e2e-summary.json.moduleInterface` explicit with `jsonReplayReady: false`, capture stage count, and capture groups.
- Context: simulated module scan redaction in the full simulator.
- Symptom: the default simulated site key `codex-simulated-site` failed the redaction gate because real LAICMS site keys are lowercase alphanumeric and do not contain hyphens.
- Evidence: `summarize_module_scan.py` rejected every simulated workspace path under `/codex-simulated-site/...`.
- Risk: unrealistic placeholder keys either force operators to weaken the redaction gate or make local full simulations fail for reasons that would not happen with real site-key-shaped data.
- Rule: local simulations must use safe site-key-shaped placeholders, such as `simsite01`, unless the test intentionally verifies rejection.
- Follow-up: keep simulated data realistic enough to pass the same validators used for redacted real browser artifacts.
- Context: validating the full local E2E output after adding module interface planning.
- Symptom: individual phase tests passed, but there was no single directory-level validator proving `full-e2e-summary.json`, site evidence, probe evidence, module scan summary, and capture plan agreed with each other.
- Evidence: `validate_run_evidence.py` can validate a single evidence file, while `full-e2e-summary.json` also carries cross-file path, module stage count, and capture group claims.
- Risk: a stale or partially regenerated output directory could look complete even when the top-level summary no longer matches the module capture plan or phase artifacts.
- Rule: run `scripts/validate_full_e2e_simulation.py` after `scripts/simulate_full_e2e_chain.py` before using the rehearsal as handoff evidence.
- Follow-up: validate top-level `localOnly`, `remoteMutationsPerformed`, phase directory paths, site/probe evidence validity, module `jsonReplayReady`, capture stage count, and capture groups.
- Context: path comparison inside the full E2E validator on macOS.
- Symptom: validating `/tmp/allincms-full-e2e-simulation-v2` failed because Python resolved the root as `/private/tmp/...`, while `full-e2e-summary.json` stored `/tmp/...`.
- Evidence: the same physical directory was represented by two equivalent absolute paths.
- Risk: validators that compare raw path strings can reject valid artifacts on systems where `/tmp` is a symlink or alias.
- Rule: compare filesystem paths after `Path(...).resolve()` when validating generated artifact directories.
- Follow-up: keep stored paths human-readable, but normalize before validation.

## 2026-06-30 Capture Authorization Package Findings

- Context: preparing the next browser-capture step from a generated module capture plan.
- Symptom: the capture plan originally emitted action names such as `upload_media_probe` and `save_site_info`, but the authorization helper and gate already support `upload_media` and `save_site_settings`.
- Evidence: `make_authorization_record.py` and `check_pre_mutation_gate.py` did not list the probe/site-info variants generated by `plan_module_capture.py`.
- Risk: a downstream operator could receive a plausible stage name that cannot generate a valid authorization record or pass the local gate.
- Rule: capture-plan `authorizationAction` values must match the local authorization helper and pre-mutation gate exactly. Do not invent friendlier action aliases unless all helpers and tests are updated in the same round.
- Follow-up: keep regression tests that compare capture-plan output against supported helper actions.
- Context: generating a package for the `products/create` capture stage.
- Symptom: a generated command can create a valid local authorization record and pass the pre-mutation gate, but it is still not user authorization.
- Evidence: `prepare_capture_authorization.py` can emit suggested Chinese authorization text, `make_authorization_record.py` command, and `check_pre_mutation_gate.py` command for `create_product_probe`.
- Risk: an agent might treat generated suggested text as permission to mutate LAICMS.
- Rule: authorization packages are preparatory artifacts only. The user must explicitly provide the suggested action-time authorization before the generated record and gate can be used for real browser operation.
- Follow-up: package output must include a warning and keep unsupported gates explicit with `gateSupported: false`.
- Context: generating the next real-browser handoff from the full E2E simulation output.
- Symptom: a simple priority sort picked `posts/create` before `products/create` because both are in `content_probe_capture` and `posts` sorts first alphabetically.
- Evidence: the full simulation was for `contentType: products`, but the first generated handoff targeted `/posts`.
- Risk: the operator could start probing the wrong content model after a products-focused run.
- Rule: default capture handoff must prefer the module matching the current run's `contentType` when no explicit `--module/--action` is supplied. Alphabetical ordering is only a fallback inside the same priority group.
- Follow-up: `make_capture_handoff.py` reads `03-module-interface-plan/module-scan.redacted.json.contentType` before choosing the default stage.
- Context: generating a handoff from local-only full E2E simulation output.
- Symptom: the handoff contained realistic `workspace.laicms.com/simsite01/...` targets and executable command strings, even though the full E2E evidence was explicitly local-only.
- Evidence: `full-e2e-summary.json.localOnly` was true, but `handoff.json.authorizationPackage.authorizationRecordCommand` initially looked ready to run against the simulated target.
- Risk: an operator could mistake a simulation handoff for a real-site authorization/gate package and attempt a remote operation against a placeholder site key.
- Rule: handoffs derived from local-only simulation evidence must set `simulationOnly: true` and suppress command fields by default. They may keep suggested authorization wording for review, but they must not expose runnable remote commands unless explicitly requested for command-shape testing.
- Follow-up: use `--allow-command-output` only for local validation of command shape or after regenerating evidence from a real site. Never treat command output as user authorization.
- Context: reviewing the default simulation-only handoff after command suppression.
- Symptom: even with commands suppressed, `suggestedAuthorizationText` and `target` still contained `https://workspace.laicms.com/simsite01/...`, which could be copied into a real authorization message.
- Evidence: default `handoff.json` had `commandsSuppressed: true`, but the authorization text still named the simulated backend target.
- Risk: simulated target URLs can leak from rehearsal artifacts into real operator authorization text.
- Rule: simulation-only handoffs must template target URLs as `https://workspace.laicms.com/{realSiteKey}/...` in user-facing fields. Keep the original simulated URL only as `simulatedTarget` for audit.
- Follow-up: test both default and `--allow-command-output` modes so safe default handoff output cannot regress.
- Context: hardening the handoff safety policy after templating simulation targets.
- Symptom: the safety behavior was covered by broad regression tests, but no standalone validator existed for handoff artifacts created outside the test runner.
- Evidence: `handoff.json` is a reusable artifact that can be copied into final responses or browser-operation plans.
- Risk: future script changes could reintroduce simulated URLs or command fields without a direct handoff safety check in the operator workflow.
- Rule: run `scripts/validate_capture_handoff.py` on generated handoffs before reporting them or using them as a real-browser preparation artifact.
- Follow-up: the validator must reject default simulation handoffs that expose commands, omit `{realSiteKey}` templates, or put simulated site keys in user-facing authorization text.

## 2026-06-30 Full Rehearsal Orchestration Findings

- Context: local-only skill maintenance round after the workflow already had separate commands for full simulation, directory validation, capture handoff generation, and handoff safety validation.
- Symptom: the safe command sequence was documented, but an operator still had to remember to run four separate commands in the right order.
- Evidence: `simulate_full_e2e_chain.py`, `validate_full_e2e_simulation.py`, `make_capture_handoff.py`, and `validate_capture_handoff.py` each worked independently, but the workflow had no single artifact proving all four gates ran together.
- Risk: a real browser capture could start from a handoff whose full E2E output or handoff safety was never validated in the current round.
- Rule: use `scripts/run_full_rehearsal.py` as the preferred local-only rehearsal before real browser capture. It must write `full-e2e/`, `next-capture-handoff/handoff.json`, and `rehearsal-summary.json`, and it must fail if either full E2E validation or handoff safety validation fails.
- Follow-up: keep the standalone commands available for debugging, but keep SKILL.md's default dry-run path pointed at the one-command rehearsal so the gate chain does not drift.

## 2026-06-30 Launch Proof Plan Findings

- Context: local-only continuation of the from-scratch site-building rehearsal after site creation, module capture planning, and content probe simulation were already wired together.
- Symptom: the rehearsal could prove helper compatibility and choose the next capture stage, but it did not produce a single artifact that said what evidence is still needed before calling a real site launch-ready.
- Evidence: `rehearsal-summary.json` had full E2E validation and handoff safety, but no normalized list of launch proof gates for theme/page/route readiness, static frontend audit, content schema capture, sample upload, batch upload, form/media/settings, final frontend audit, and cleanup.
- Risk: operators could mistake a successful local probe lifecycle or static route audit for a complete launch, especially when the temporary demo content seems visually adequate.
- Rule: full rehearsal should also emit `launch-plan.json`. The plan must stay local-only, use `{realSiteKey}` templates and redacted route patterns, and separate before-upload expected 404 detail routes from after-sample expected 200 detail routes.
- Follow-up: run `scripts/validate_launch_plan.py` before using a launch plan in a browser-operation handoff, and keep business copy, concrete slugs, and simulated site keys out of user-facing plan fields.

## 2026-06-30 Full Rehearsal Summary Validation Findings

- Context: local-only rehearsal now emits full E2E artifacts, capture handoff, launch plan, and a top-level `rehearsal-summary.json`.
- Symptom: the child artifacts had validators, but the top-level summary itself could drift: artifact paths, selected stage fields, launch proof counts, or safety booleans could be stale while child validators still passed when run separately.
- Evidence: `rehearsal-summary.json` duplicates paths and summaries from `full-e2e/`, `handoff.json`, and `launch-plan.json`.
- Risk: an operator could report a stale summary that no longer matches the actual handoff or launch plan, especially after regenerating only one child artifact.
- Rule: validate the top-level rehearsal summary with `scripts/validate_full_rehearsal.py` before reporting a full rehearsal result or using it as a browser-operation handoff.
- Follow-up: keep the validator cross-checking child validator results, path normalization, command-suppression state, selected stage fields, and launch proof counts.
- Context: testing `validate_full_rehearsal.py` immediately after starting `run_full_rehearsal.py`.
- Symptom: the first validation attempt reported `rehearsal-summary.json` missing, while a follow-up file listing showed the file existed and validation then passed.
- Evidence: generation and validation were launched in parallel even though the validator depends on the generator's final artifact.
- Risk: parallelizing dependent rehearsal commands can create false negatives or, worse, make an operator ignore a real missing-artifact failure as "probably a race."
- Rule: run dependent rehearsal commands sequentially: generate full rehearsal first, then validate `rehearsal-summary.json`, then report. Use parallelism only for independent read/check commands.
- Follow-up: keep `run_full_rehearsal.py` as the preferred single generator, and reserve `multi_tool_use.parallel` for checks that do not depend on newly written artifacts.

## 2026-06-30 Manifest Rehearsal Findings

- Context: local-only full rehearsal covered content probe evidence but did not separately exercise the source manifest path that precedes batch upload.
- Symptom: `validate_manifest.py` could already distinguish draft validation from schema-verified upload validation, but the full rehearsal had no artifact proving that distinction was exercised for the selected content type.
- Evidence: `simulate_full_e2e_chain.py` emitted site, probe, and module phases only; a generic draft manifest could pass validation without surfacing the expected upload-blocking schema gate failure in rehearsal output.
- Risk: operators could treat a clean draft manifest as upload-ready, especially after a successful probe lifecycle simulation.
- Rule: full local rehearsal must include `04-manifest-rehearsal/` with `draft-manifest.json` and `manifest-rehearsal-summary.json`. Draft validation should pass, while `--require-schema-verified` should fail until a real save request supplies `payloadTemplate` and verified field mapping.
- Follow-up: keep `validate_full_e2e_simulation.py` and `validate_full_rehearsal.py` checking `manifestDraftValidationPassed: true` and `manifestSchemaGateExpectedFailure: true`.

## 2026-06-30 Maintenance Closeout Summary Findings

- Context: local-only skill maintenance after the operator was told to record encountered problems into the skill every round.
- Symptom: the closeout gate expected a summary from `summarize_run_status.py`, but documentation-only or helper-script rounds may not produce a fresh run-evidence JSON.
- Evidence: reusing an older browser/rehearsal summary would satisfy field-shape checks while tying the final closeout to stale site or content evidence unrelated to the current maintenance round.
- Risk: future operators could either skip closeout on non-browser rounds or accidentally imply that skill maintenance proved LAICMS site creation, launch, upload, publish, cleanup, or frontend persistence.
- Rule: when no current run-evidence JSON exists, generate a maintenance summary with `scripts/make_round_maintenance_summary.py` and pass it through `scripts/check_round_closeout.py`. Treat that summary only as sedimentation reporting proof, never as remote LAICMS operation proof.
- Follow-up: keep regression coverage so maintenance summaries include `valid`, `complete`, `proven`, `missing`, `completionGaps`, and `nextActions`, and so closeout still rejects inconsistent sedimentation claims.

## 2026-06-30 Theme Launch Ledger Gate Findings

- Context: local-only full rehearsal after module/action capture coverage could unlock `theme_page_route_launch`.
- Symptom: the rehearsal proved module capture could expose the launch stage, but did not prove how incomplete launch readiness should behave once the stage starts.
- Evidence: active theme and published page proof can be recorded while enabled-page, bound-route, frontend HTTP, or frontend DOM proof is still missing.
- Risk: an operator could treat a partial launch stage as enough to start static audit, content probes, or uploads, especially when the backend shows an active theme or a success-like publish state.
- Rule: theme/page/route launch needs its own partial/complete gate. A partial result must keep `theme_page_route_launch` partial and leave `nextStageId` empty. Only complete proof for active theme, published pages, enabled pages, bound routes, frontend HTTP ok, and frontend DOM verified may unlock `static_frontend_audit`.
- Follow-up: full rehearsal now writes partial and complete theme-launch stage results plus the corresponding ledgers and next packet, and `validate_full_rehearsal.py` rejects summaries that unlock frontend audit from partial launch proof.
- Context: first regression run after adding the theme launch partial gate.
- Symptom: partial `theme_page_route_launch` still exposed `forms_media_settings` as the next ready stage.
- Evidence: the browser execution plan had `forms_media_settings` depending only on `module_interface_capture`, so once module capture was complete the stage could bypass theme launch, static audit, probe creation, schema gate, and batch upload.
- Risk: settings/media/form mutations could start while the public site launch state is still partial, creating side effects before route/page readiness and content workflow proof are complete.
- Rule: forms/media/settings must not be a parallel escape hatch after interface capture. In the default from-scratch runbook it depends on `batch_upload_publish`, and final frontend audit depends on both batch upload and forms/media/settings.
- Follow-up: keep tests asserting partial theme launch leaves no next stage and complete theme launch exposes only `static_frontend_audit` first.

## 2026-06-30 Static Frontend Audit Gate Findings

- Context: local-only full rehearsal after complete theme/page/route launch could unlock `static_frontend_audit`.
- Symptom: the runbook needed the same partial/complete discipline for frontend audit before allowing content probe creation.
- Evidence: an expected-status map or one redacted route audit can exist while another static route still has blocking DOM, image, HTTP status, or rich-text issues.
- Risk: an operator could start creating content probe drafts before the static site shell is verified, making later frontend failures ambiguous between launch/theme issues and content-upload issues.
- Rule: static frontend audit needs its own gate. Partial static audit proof must keep `static_frontend_audit` partial and leave `nextStageId` empty. Only expected status map, redacted frontend audit, and `frontendRendering` evidence for all expected static routes may unlock `content_probe_create`.
- Follow-up: full rehearsal writes partial and complete static-audit stage results plus ledgers and next packet; `validate_full_rehearsal.py` rejects summaries that unlock content probes from partial static audit proof.

## 2026-06-30 Content Probe Creation Gate Findings

- Context: local-only full rehearsal after complete static frontend audit could unlock `content_probe_create`.
- Symptom: the runbook stopped at the content-probe packet and did not prove partial versus complete probe creation behavior.
- Evidence: authorization text and probe naming proof can exist before a backend draft row or edit URL is captured.
- Risk: an operator could treat authorization plus intended probe name as enough to proceed into save-request capture, accidentally saving content or capturing payloads without a proven draft target.
- Rule: content probe creation needs its own partial/complete gate. Partial proof must keep `content_probe_create` partial and leave `nextStageId` empty. Only content-type-specific authorization, probe/test naming proof, and backend draft proof may unlock `save_request_capture`.
- Follow-up: full rehearsal now writes partial and complete content-probe stage results plus the corresponding ledgers and next packet; `validate_full_rehearsal.py` rejects summaries that unlock save-request capture from partial probe proof.

## 2026-06-30 Save Request Capture Gate Findings

- Context: local-only full rehearsal after complete content-probe creation could unlock `save_request_capture`.
- Symptom: the runbook did not prove that partially captured request data remains blocked before publishing or manifest schema verification.
- Evidence: request URL, method, headers, or payload shape can be captured before field mapping and backend persistence proof are verified.
- Risk: an operator could treat an incomplete payload capture as an upload-ready schema, or proceed to sample publish while the saved probe was not proven to persist.
- Rule: save request capture needs its own partial/complete gate. Partial proof must keep `save_request_capture` partial and leave `nextStageId` empty. Only request URL, method, required headers, payload template, field mapping, and backend persistence proof may unlock downstream publish/sample and manifest-schema stages.
- Follow-up: full rehearsal now writes partial and complete save-request stage results plus corresponding ledgers and next packet; `validate_full_rehearsal.py` rejects summaries that unlock publish or manifest stages from partial save-request proof.

## 2026-06-30 Resume Closeout Gate Findings

- Context: resuming an AllinCMS skill-maintenance round after summary handoff.
- Symptom: the previous round had recorded the save-request capture finding and run validations, but its maintenance summary and `check_round_closeout.py` gate had not been run after the final change.
- Evidence: the resumed handoff explicitly listed the missing `make_round_maintenance_summary.py` and `check_round_closeout.py` commands before any next-stage work.
- Risk: a resumed operator could continue with new browser-stage simulation while the prior sedimentation change was never closed out, weakening the "every turn sediments" contract.
- Rule: after interruption, summary handoff, or context compaction, first verify whether the latest AllinCMS skill change already has a matching closeout result. If not, run the missing closeout before continuing.
- Follow-up: keep `SKILL.md` requiring resumed turns to check closeout status before new browser stages or helper changes.

## 2026-06-30 Publish Sample Verification Gate Findings

- Context: local-only full rehearsal after complete save-request capture exposed `publish_sample_verify` first while `manifest_schema_gate` was also ready.
- Symptom: the first test expected partial sample verification to leave no next stage, but the ledger correctly exposed the already-ready local `manifest_schema_gate`.
- Evidence: after a partial sample result, `publish_sample_verify` stayed partial, `manifest_schema_gate` remained ready, and `batch_upload_publish` stayed pending.
- Risk: operators could confuse "local manifest gate is ready" with "batch upload is allowed", or incorrectly block local manifest validation while waiting for final sample media/body proof.
- Rule: partial sample verification may leave `manifest_schema_gate` as next because it is local verification already unlocked by save-request capture, but it must never unlock batch upload, forms/media/settings, cleanup, or final audit. Completed sample verification still requires backend published status, frontend detail 200, title/name, cover/media, and structured body proof.
- Follow-up: full rehearsal now writes partial and complete publish-sample stage results plus ledgers and next packet; `validate_full_rehearsal.py` rejects summaries that unlock batch upload before both sample verification and manifest schema gate are complete.

## 2026-06-30 Manifest Schema Gate Findings

- Context: local-only full rehearsal after complete sample verification exposed `manifest_schema_gate`.
- Symptom: the prior rehearsal stopped before proving that a draft-valid manifest stays blocked until strict schema verification passes.
- Evidence: generic `validate_manifest.py` can pass while `--require-schema-verified` is still missing or failing.
- Risk: operators could treat a draft-clean manifest as upload-ready and start JSON replay or UI batch work without proof that the current site's captured payload template and field mapping match the manifest.
- Rule: manifest schema gate needs its own partial/complete gate. Partial proof must keep `manifest_schema_gate` partial and leave batch upload locked. Only both generic validation and `--require-schema-verified` validation passing for the current site/content type may unlock `batch_upload_publish`, which still requires fresh mutation authorization.
- Follow-up: full rehearsal now writes partial and complete manifest-gate stage results plus ledgers and next packet; `validate_full_rehearsal.py` rejects summaries that unlock batch upload from generic validation alone.

## 2026-06-30 Batch Upload Publish Gate Findings

- Context: local-only full rehearsal after completed manifest schema gate exposed `batch_upload_publish`.
- Symptom: the runbook previously unlocked forms/media/settings after batch upload but did not prove what happens when batch progress is incomplete.
- Evidence: a progress log and some frontend audits can exist while not every uploaded route, cover/media, status, or duplicate slug is verified.
- Risk: operators could start settings/media/form mutations, final audit, or cleanup while some uploaded entries are still broken, drafts, duplicated, or unverified.
- Rule: batch upload/publish needs its own partial/complete gate. Partial proof must keep `batch_upload_publish` partial and leave forms/media/settings, final audit, and cleanup locked. Only complete proof with schema gate pass, sample verification pass, progress log, duplicate-slug handling if applicable, and frontend detail audit for every uploaded route may unlock `forms_media_settings`.
- Follow-up: full rehearsal now writes partial and complete batch-upload stage results plus ledgers and next packet; `validate_full_rehearsal.py` rejects summaries that unlock forms/media/settings from partial batch evidence.

## 2026-06-30 Forms Media Settings Gate Findings

- Context: local-only full rehearsal after completed batch upload exposed `forms_media_settings`.
- Symptom: the runbook reached forms/media/settings but did not separately prove that incomplete settings/media/form effects keep final audit locked.
- Evidence: a module-specific request capture and backend saved state can exist before the public page, media render, form integration, domain, or tracking effect is verified.
- Risk: operators could start final frontend audit or cleanup while a form, media upload, domain, tracking, or site-info change has not taken effect publicly.
- Rule: forms/media/settings needs its own partial/complete gate. Partial proof must keep `forms_media_settings` partial and leave final audit and cleanup locked. Only complete proof with action-specific request capture, backend persisted proof, and public or integration effect proof where applicable may unlock `final_frontend_audit`, which is verification mode and requires no mutation authorization.
- Follow-up: full rehearsal now writes partial and complete forms-media-settings stage results plus ledgers and next packet; `validate_full_rehearsal.py` rejects summaries that unlock final frontend audit from partial settings/media/form evidence.

## 2026-06-30 Final Frontend Audit Gate Findings

- Context: local-only full rehearsal after completed forms/media/settings exposed `final_frontend_audit`.
- Symptom: the runbook reached final audit but did not separately prove that incomplete frontend QA keeps cleanup locked.
- Evidence: HTTP status, DOM/rich-text, and image reports can exist while the broken-entry list is still non-empty or unresolved.
- Risk: operators could delete or unpublish probes before fixing broken routes, missing images, raw Markdown residue, wrong statuses, stale drafts, or unresolved detail pages.
- Rule: final frontend audit needs its own partial/complete gate. Partial proof must keep `final_frontend_audit` partial and leave cleanup locked. Only complete proof with HTTP status report, DOM/rich-text report, image report, and broken-entry list empty may unlock `cleanup_probes`, which still requires fresh cleanup authorization.
- Follow-up: full rehearsal now writes partial and complete final-frontend-audit stage results plus ledgers and next packet; `validate_full_rehearsal.py` rejects summaries that unlock cleanup from partial frontend audit evidence.

## 2026-06-30 Cleanup Probe Gate Findings

- Context: local-only full rehearsal after completed final frontend audit exposed `cleanup_probes`.
- Symptom: the runbook reached cleanup but did not separately prove that authorization and candidate selection are not cleanup completion.
- Evidence: cleanup authorization and a candidate list can exist before backend absence/unpublished state and frontend non-public proof are verified.
- Risk: operators could claim the site-build/upload run is closed while probes, Untitled drafts, duplicate slugs, or public test URLs still exist.
- Rule: cleanup needs its own partial/complete gate. Partial proof must keep `cleanup_probes` partial and must not claim the run is closed. Only complete proof with cleanup authorization, candidate list, backend cleanup proof, and frontend non-public proof may mark cleanup completed and leave no next stage.
- Follow-up: full rehearsal now writes partial and complete cleanup stage results plus ledgers; `validate_full_rehearsal.py` rejects summaries that treat cleanup authorization or candidate lists as cleanup completion.

## 2026-06-30 Browser Stage Evidence Pointer Findings

- Context: local-only rehearsal validation for staged real-browser packets.
- Symptom: a stage result could require non-empty `redactedEvidencePointers`, but the pointer format itself was not constrained.
- Evidence: free-text values such as `done` or `verified` can satisfy a non-empty string check while pointing to no inspectable artifact, URL, or run-evidence file.
- Risk: an operator could advance the ledger from a browser stage without leaving an auditable proof trail, making later launch, upload, or cleanup claims impossible to verify.
- Rule: stage result evidence pointers must be inspectable references such as `local://...`, `https://...`, `/tmp/...`, `./...`, or `../...`; status words belong in `operatorNote` or `proofRecorded`, not in evidence pointers.
- Follow-up: `validate_browser_stage_result.py` now rejects unauditable evidence pointer text, and the rehearsal/test suite covers the constraint.

## 2026-06-30 Partial Stage Recovery Findings

- Context: local-only rehearsal validation for browser stages that can end as `partial`.
- Symptom: after a non-module stage was applied as `partial`, the ledger correctly exposed no `nextStageId`, but there was no generic same-stage recovery packet to finish the missing proof later.
- Evidence: a partial `theme_page_route_launch` ledger could record blockers and keep dependent stages locked, while the normal next-stage packet builder had no ready stage unless the partial stage was selected explicitly.
- Risk: operators could rebuild from the static plan, mark the stage complete out of band, or skip the missing proof in order to unlock later frontend audit, upload, settings, or cleanup stages.
- Rule: resume a partial stage only by explicitly selecting that same stage with `build_browser_stage_packet.py --stage-id <partial-stage-id>`. The packet must have `recovery: true`, allow only same-stage recovery actions, and completion from that recovery packet is the only path that may unlock dependent stages.
- Follow-up: `build_browser_stage_packet.py`, `apply_browser_stage_result.py`, `run_full_rehearsal.py`, `validate_full_rehearsal.py`, `test_validate_run_evidence.py`, `SKILL.md`, and `e2e-simulation.md` now model and validate same-stage recovery.
- Context: local-only continuation after adding the first theme-launch recovery packet.
- Symptom: later partial/complete gates still simulated completion by applying a completed result against the pre-partial packet and pre-partial ledger.
- Evidence: static audit, content probe, save request, sample publish, manifest gate, batch upload, forms/media/settings, final audit, and cleanup all had partial ledgers, but their completion path did not prove same-stage recovery from those partial ledgers.
- Risk: the rehearsal could pass while teaching an unsafe real-browser pattern: ignore the partial ledger with no ready stage, reuse an older packet, and unlock downstream stages without explicitly recovering the current blocker.
- Rule: every rehearsal stage that first records `partial` must complete from that partial ledger through a `recovery: true` same-stage packet. Summary fields should record `completedFromRecoveryPacket: true`, and the full-rehearsal validator should reject completion summaries that omit it.
- Follow-up: `run_full_rehearsal.py`, `validate_full_rehearsal.py`, and `test_validate_run_evidence.py` now require same-stage recovery completion for all non-module partial/complete gates.

## 2026-06-30 Conversation-Turn Closeout Findings

- Context: local-only skill maintenance after the operator was told that encountered problems must be recorded into the skill on every conversation turn.
- Symptom: the skill required a final sedimentation pass, but it did not force the operator to classify the closeout path at turn start or keep a running list of reusable findings during long browser or helper-script work.
- Evidence: prior recovery work needed a resumed closeout before new work could continue, showing that end-only sedimentation is easy to miss after interruption or compaction.
- Risk: reusable failures, command drift, and validation gaps can remain only in chat history, especially when the turn is discussion-only, status-only, or interrupted after a helper edit.
- Rule: at the start of each AllinCMS skill turn, decide whether the final closeout will use current run evidence or a maintenance summary. Track reusable problems as they occur, then run `check_round_closeout.py` before the final response with either `updated` or an explicit no-update note.
- Follow-up: `SKILL.md` now names this turn-start closeout-path rule, and the hygiene audit checks for that marker.
- Context: local-only skill maintenance after the operator asked that every round visibly sediment encountered problems into the skill.
- Symptom: closeout could pass locally, but the final response requirement did not explicitly say to report the sedimentation status and the main `roundIssues` item back to the user.
- Evidence: `SKILL.md` required `--round-issue` and `check_round_closeout.py`, while the final-response shape was left implicit.
- Risk: future operators could update or check the skill but return a vague status, making it hard for the user to confirm that per-round sedimentation actually happened.
- Rule: every AllinCMS skill final response should report `--sedimentation updated` or `--sedimentation none` plus the main round issue/no-change observation.
- Follow-up: `SKILL.md` now states the final-response reporting requirement, and the hygiene audit checks for the `main roundIssues item` marker.

## 2026-06-30 Stage Result Builder Findings

- Context: local-only continuation of the staged real-browser rehearsal after ledger update commands were changed to `apply_browser_stage_result.py --result-json`.
- Symptom: `e2e-simulation.md` still contained a stale sentence telling operators to regenerate or update the ledger with completed stage ids, and the browser-stage result JSON still had to be hand-written.
- Evidence: the packet validator now rejects `--completed-stage-ids`, but a stale reference sentence and manual result construction could still teach the wrong real-browser habit.
- Risk: an operator could bypass packet/result validation, lose evidence pointers and partial/blocking issues, or accidentally advance later mutation stages from a completed-id list.
- Rule: after each real browser stage, create or store an `allincms_browser_stage_result`, validate it against the packet, and apply it with `apply_browser_stage_result.py --result-json`. Prefer `make_browser_stage_result.py` over hand-written JSON so stage id, completed proof coverage, pointer validation, and blocker requirements stay aligned with the packet.
- Follow-up: `make_browser_stage_result.py`, `SKILL.md`, and `e2e-simulation.md` now document and support the packet-to-result path.
- Context: local-only follow-up after adding `make_browser_stage_result.py`.
- Symptom: the `apply_browser_stage_result.py --stage-id --status ...` convenience path built a result and validated it only without packet context before applying it.
- Evidence: packet-aware validation catches completed results missing packet `requiredProof`, but the inline build path could reach `apply_stage_result` with a weak result object instead of failing immediately at construction.
- Risk: a real operator using the convenience flags could update the ledger with incomplete proof labels or discover the failure later than necessary, weakening the single-stage packet contract.
- Rule: every result path, including inline CLI flags, must validate against the packet before ledger mutation. Completed inline results must name all packet `requiredProof`, and partial/blocked inline results must still provide evidence pointers or blockers as required.
- Follow-up: `apply_browser_stage_result.py` now validates inline-built results against the packet before applying them, and the test suite covers rejection of missing required proof from the CLI path.
- Context: local-only follow-up after the inline apply path was hardened.
- Symptom: `make_browser_stage_result.py` created a result with `build_stage_result()` and then appended `operatorNote` afterward. It also allowed manually supplied `--proof-recorded` to bypass final packet-aware validation in the builder itself.
- Evidence: `validate_browser_stage_result(result, packet)` checks emails, forbidden terms, concrete frontend origins, stage id, and completed `requiredProof` coverage, but that check was not run after `operatorNote` was added.
- Risk: the builder could write a result artifact that a later validator rejects, or worse, store unredacted operator notes in a durable run artifact before the failure is noticed.
- Rule: every stage-result builder must run final packet-aware validation on the exact JSON it writes. Fields added after the initial constructor, including notes, must pass the same redaction and proof coverage checks.
- Follow-up: `make_browser_stage_result.py` now validates the final result against the packet before writing output, and tests cover both missing required proof and unredacted operator-note rejection.
- Context: local-only continuation while checking whether the browser-stage packet still taught the old ledger update path.
- Symptom: `ledgerUpdate.commandTemplate` correctly used `apply_browser_stage_result.py --result-json`, but the same packet still exposed `ledgerUpdate.completedStageIds`, which reads like a list-based ledger update instruction.
- Evidence: `e2e-simulation.md` already forbids `--completed-stage-ids`; the remaining field name conflicted with that rule and appeared in generated packets and test fixtures.
- Risk: a real browser operator could copy the field semantics instead of the result-json command, advancing ledgers without proof pointers, partial blockers, or packet-aware result validation.
- Rule: packet `ledgerUpdate` must require a stage-result artifact with `stageResultRequired: true`; use `expectedCompletedStageIdsAfterApply` only as audit metadata and reject any `completedStageIds` field in packets.
- Follow-up: `build_browser_stage_packet.py`, `e2e-simulation.md`, and regression tests now enforce the result-json apply path and reject the old field name.
- Context: applying a real read-only refresh result from an existing-site scan to a full from-scratch browser execution ledger.
- Symptom: `validate_browser_stage_packet.py --ledger <ledger>` failed because the current validator accepts only the packet JSON path; the correct ledger relationship is already inside the packet/ledger artifacts and the helper's `--help` is the authority.
- Evidence: `validate_browser_stage_packet.py` returned `unrecognized arguments: --ledger ...`; rerunning `validate_browser_stage_packet.py <packet>` passed.
- Risk: operators can lose time or script around nonexistent flags if they infer CLI shapes from neighboring helpers instead of current `--help`.
- Rule: before wiring rehearsal artifacts together, check the exact helper `--help` for `validate_*`, `build_*`, `make_*`, and `apply_*` scripts. Do not invent cross-helper flags such as `--ledger` unless that script exposes them.
- Follow-up: keep command examples in `SKILL.md` and `e2e-simulation.md` tied to real helper output whenever CLI shape changes.
- Context: same read-only refresh bridge from real existing-site evidence into a from-scratch rehearsal ledger.
- Symptom: after the read-only refresh stage completed, the from-scratch ledger correctly advanced to `create_site_submit`, even though the real environment already had a verified site selected for continuation.
- Evidence: updated ledger `nextStageId` was `create_site_submit`; the next packet required authorization and `remoteMutationExpectation: must`.
- Risk: an operator could accidentally create a duplicate site by following the from-scratch rehearsal ledger after a real site already exists and the user's practical goal is to continue configuring that site.
- Rule: when real browser evidence proves an existing target site, treat a from-scratch ledger's `create_site_submit` as a stopping point unless the current user explicitly asks for a new site at action time. For existing-site continuation, branch to the existing-site workflow rather than executing create-site submit.
- Follow-up: report this distinction in the handoff before asking for any create-site authorization.
- Context: local-only helper hardening for the existing-site continuation branch.
- Symptom: the ledger validator already allowed `skipped`, but no helper existed to safely skip `create_site_submit` after a real existing-site refresh.
- Evidence: after applying read-only refresh proof, the ledger's next stage was `create_site_submit`; manually editing it would bypass evidence validation and dependency checks.
- Risk: operators could either create a duplicate site or hand-edit ledger state in a way that unlocks later mutation stages without proving the selected site.
- Rule: use `scripts/branch_existing_site_ledger.py` to branch only after validated `existing_site_selected` evidence and completed `refresh_readonly_site_evidence`. The helper skips only `create_site_submit`, records the evidence pointer, and exposes `setup_pages_inspection` as the next read-only stage.
- Follow-up: `SKILL.md`, `e2e-simulation.md`, and regression tests document and validate the existing-site continuation branch.
- Context: validating the generated next packet after an existing-site continuation branch.
- Symptom: the setup packet's `ledgerUpdate.expectedCompletedStageIdsAfterApply` listed completed stages only and did not include the skipped `create_site_submit` stage.
- Evidence: after branching, `nextStageId` was `setup_pages_inspection`, while the packet expected completed stages `refresh_readonly_site_evidence` and `setup_pages_inspection`.
- Risk: operators might misread the missing create stage as a bug or manually add it as completed, accidentally claiming from-scratch creation proof.
- Rule: in an existing-site branch, `create_site_submit` should remain `skipped`, not `completed`. Completion metadata should not list skipped create-site proof as if a remote create mutation occurred.
- Follow-up: report skipped create-site state separately through `existingSiteContinuation` and the skipped stage entry.
- Context: inspecting generated stage-result JSON after completing a read-only refresh stage.
- Symptom: quick JSON summaries that look for `evidencePointers` can show null because the current stage-result schema stores pointers in `redactedEvidencePointers`.
- Evidence: the result file contained `redactedEvidencePointers` with the run-evidence, redacted scan, and summary paths, while a narrow diagnostic printed `evidencePointers: null`.
- Risk: an operator may think evidence pointers were lost and rerun browser work unnecessarily, or hand-edit proof fields.
- Rule: use the validator and inspect `redactedEvidencePointers` for durable stage-result proof. Treat legacy or ad hoc `evidencePointers` summaries as insufficient.
- Follow-up: prefer `validate_browser_stage_result.py` and direct schema inspection over hand-written key probes.

## 2026-06-30 Setup Pages Inspection Findings

- Context: real browser read-only `setup_pages_inspection` on an existing-site continuation ledger.
- Symptom: the setup pages' generic shell exposed account email, site switcher text, frontend domain, and editable site business description alongside neutral controls.
- Evidence: raw DOM extraction for `site-info`, `domains`, `themes`, `routes`, and `forms` included account/menu text and site copy before redaction, while the redacted evidence preserved only placeholders, control labels, module URLs, table headers, and row counts.
- Risk: writing raw setup scans to disk or skill docs can leak account data or business copy, even when the browser action is read-only.
- Rule: setup-page proof must be redacted before storage. Keep neutral fields such as `name`, `notificationEmail`, `domain`, search placeholders, save/add/create controls, route/form table headers, row counts, and `{realSiteKey}` URL patterns; remove emails, site switcher labels, frontend domains, and textarea business copy.
- Follow-up: `references/e2e-simulation.md` now warns to redact setup-page evidence before writing it.
- Context: applying a completed setup-pages stage result to the existing-site continuation ledger.
- Symptom: after `setup_pages_inspection` completed, the next packet became `module_interface_capture` with `authorizationRequired: true` and `remoteMutationExpectation: may`.
- Evidence: the generated packet allowed exactly one capture-plan stage, request capture, and persistence/no-persistence proof.
- Risk: an operator could continue from setup inspection into module capture as if it were read-only, but content/theme/form create controls may mutate or create drafts.
- Rule: stop after setup inspection and request fresh action-time authorization before module-interface capture. The next capture should cover exactly one module/action and must not chain multiple modules or replay JSON.
- Follow-up: keep module capture as a single-stage authorization boundary in run handoffs.

## 2026-06-30 Stage Result Workspace URL Redaction Findings

- Context: local-only hardening of the staged browser result validator before using packets for real LAICMS browser work.
- Symptom: stage-result evidence pointers allowed generic `https://...` URLs and rejected concrete frontend origins, but did not reject concrete backend URLs such as `https://workspace.laicms.com/{siteKey}/products`.
- Evidence: the result schema calls the field `redactedEvidencePointers`, while a concrete workspace site URL exposes the real site key in a durable run artifact.
- Risk: a real browser run could write site-specific backend URLs into reusable artifacts or handoffs, making later skill sedimentation or sharing more likely to leak run-specific identifiers.
- Rule: stage-result evidence may point to local redacted artifacts or redacted workspace URL templates, but concrete workspace site URLs must use `{realSiteKey}`. `/sites` remains acceptable because it is not site-scoped.
- Follow-up: `validate_browser_stage_result` now rejects concrete `workspace.laicms.com/{siteKey}` URLs, and tests cover both rejected concrete URLs and accepted `{realSiteKey}` templates.

## 2026-06-30 Browser Stage Remote-Mutation Flag Findings

- Context: local-only full rehearsal before applying stage packets to real browser work.
- Symptom: browser-stage results always recorded `remoteMutationsPerformed: false`, which is correct for the local helper artifact but ambiguous after an authorized browser stage has actually created, saved, published, uploaded, mutated settings, or cleaned remote LAICMS state.
- Evidence: `create_site_submit`, `save_request_capture`, `publish_sample_verify`, `batch_upload_publish`, `forms_media_settings`, and `cleanup_probes` are authorization-required stages whose successful completion normally means the browser changed remote state, while the helper itself still performs only local ledger updates.
- Risk: an operator could truthfully validate a local result artifact but leave the audit trail implying no remote state changed, making cleanup, rollback, or final launch proof harder to reason about.
- Rule: keep `localOnly: true` and `remoteMutationsPerformed: false` for the stage-result artifact itself, but record the browser-stage effect separately as `browserStageMutatedRemote: true` only for completed authorization-required stages with packet-required proof. Read-only, verification, partial, and blocked stage results must keep it false.
- Follow-up: `apply_browser_stage_result.py` and `make_browser_stage_result.py` now support and validate `browserStageMutatedRemote`, and tests cover allowed authorized mutation results plus rejected read-only and partial mutation claims.

## 2026-06-30 Remote Mutation Expectation Findings

- Context: follow-up local rehearsal after adding `browserStageMutatedRemote`.
- Symptom: the result schema could record remote mutation truth, but packets did not say whether a completed stage should set it. An operator could still complete `create_site_submit` or `batch_upload_publish` with the flag left false.
- Evidence: `create_site_submit`, `theme_page_route_launch`, `content_probe_create`, `save_request_capture`, `batch_upload_publish`, `forms_media_settings`, and `cleanup_probes` have successful completion semantics that require remote state changes; read-only and verification stages must not change remote state; module capture and sample publish can be action-dependent.
- Risk: real-browser ledgers could pass structural checks while under-reporting remote changes, weakening rollback/cleanup reasoning and final launch audit.
- Rule: stage packets must carry `remoteMutationExpectation` as `must`, `may`, or `must_not`. Completed `must` results must set `browserStageMutatedRemote: true`; `must_not` results must keep it false; `may` results require operator judgment based on observed persistence.
- Follow-up: execution plans, ledgers, packets, result validation, rehearsal artifacts, tests, and `SKILL.md` now carry the expectation and enforce it.

## 2026-06-30 Browser Stage Authorization Package Findings

- Context: local-only rehearsal before starting real browser execution from `/sites`.
- Symptom: browser-stage packets exposed suggested authorization text, but did not provide the concrete local authorization-record and pre-mutation-gate command templates for the ready mutation stage.
- Evidence: `create_site_submit` needs both `make_authorization_record.py --action create_site` and `check_pre_mutation_gate.py --action create_site` before submitting the real create-site form.
- Risk: an operator could copy only the suggested text, skip the local freshness/gate checks, hand-write inconsistent commands, or mistake helper-generated wording for current user authorization.
- Rule: authorization-required browser-stage packets should be paired with an explicit preparation package when the helper and gate support that stage. Unsupported stages must report `gateSupported: false` and must not emit pretend authorization or gate commands.
- Follow-up: `prepare_browser_stage_authorization.py` now supports `create_site_submit`; later stages should be added only after their helper/gate commands are verified.
- Context: follow-up local rehearsal for the forms/media/settings stage.
- Symptom: `upload_media` correctly suppressed commands because no media upload gate exists, but its suggested authorization text still looked like a normal forms/media/settings mutation authorization.
- Evidence: media upload requires unknown multipart/storage behavior plus a backend media row, public URL, and cleanup/rollback proof before replay; a generic `upload_media` text can be misread as permission to reuse an endpoint or batch upload.
- Risk: a real browser operator could convert one UI upload probe into an unsafe JSON replay or batch media upload path without a dedicated gate.
- Historical rule at that time: ungated media packages were UI-first capture packages. **Superseded on 2026-07-27 for execution by the canonical adapter; legacy package fields may remain for compatibility but must not route operators back to UI selection.**
- Follow-up: `prepare_browser_stage_authorization.py`, `SKILL.md`, and regression tests now distinguish UI-first media capture from gated settings/form/domain/tracking actions.

## 2026-06-30 Live Read-Only Module Scan Findings

- Context: read-only in-app browser scan of backend module pages for an existing LAICMS site.
- Symptom: direct navigation proved visible module fields and controls, but captured no action-specific POST requests because no create/save/publish/upload controls were clicked.
- Evidence: products, posts, media, themes, routes, forms, site-info, domains, and tracking exposed neutral headings, columns, inputs, and mutation-looking controls; the observed network surface was page/navigation GET behavior and RSC-style fetches, not submitted mutation payloads.
- Risk: treating this scan as JSON-ready would confuse visible UI controls or `_rsc` prefetches with a reusable Server Action/API contract. It would also miss that raw scan artifacts can leak account-menu text, frontend domains, and relative `/{siteKey}/...` links even when full workspace URLs are redacted.
- Rule: read-only module scans may populate an interface inventory and capture checklist, but JSON replay remains blocked until each exact action has fresh authorization, POST capture, payload/ID mapping, and persistence proof. Redact both absolute and relative site-key paths before storing or summarizing browser scan artifacts.
- Follow-up: `redact_browser_scan.py` now templates non-protected relative site-key paths, drops redacted account placeholders, and accepts already-redacted `{siteKey}` / `{realSiteKey}` placeholders during second-pass cleanup; `summarize_module_scan.py` now accepts compact browser scan network summaries with `tableHeaders` and `network` fields.
- Context: follow-up planning from the same read-only scan.
- Symptom: `domains` displayed `添加域名` and `tracking` displayed `添加 Google Tag ID`, but the action inference did not treat Chinese `添加` as a create/add mutation, so the generated capture plan omitted both modules.
- Evidence: read-only DOM controls showed add-domain and add-tracking-tag controls while `captureNextActions` initially contained products/posts/media/themes/routes/forms/site-info only.
- Risk: a "scan every module" workflow could miss external DNS and tracking mutations, then later claim the interface inventory is complete.
- Rule: treat `添加` / `add` as create-like mutation language during interface scan summarization, and keep domains/tracking as separate capture stages with their own authorization actions rather than folding them into generic site settings.
- Follow-up: `summarize_module_scan.py` now maps `添加` to create-like actions, and `plan_module_capture.py` emits `add_domain` and `add_tracking_tag` stages.

## 2026-06-30 Capture Action Gate Coverage Findings

- Context: local-only continuation after the read-only module scan produced a 10-stage capture plan.
- Symptom: the capture plan emitted `add_domain` and `add_tracking_tag`, but the authorization record helper, pre-mutation gate, and setup evidence builders did not yet support those actions as first-class gated mutations.
- Evidence: `prepare_capture_authorization.py` could build stages for domains/tracking only after the plan update, while `make_authorization_record.py` and `check_pre_mutation_gate.py` initially lacked matching action names. `tracking` also appeared in module routes but not in required `setupPages` evidence.
- Risk: an operator could generate a capture plan that looks complete but cannot pass local mutation gates before real browser work, or could skip tracking setup inspection because the evidence model did not require it.
- Rule: every capture-plan `authorizationAction` must be accepted by the authorization helper and either have a supported pre-mutation gate or explicitly report `gateSupported: false`. Setup modules that can mutate state, including tracking, must have read-only setup evidence before their mutation gate can pass.
- Follow-up: `add_domain` and `add_tracking_tag` are now supported by authorization records, capture authorization packages, and site-action gates; `tracking` is now a required setup evidence page in run evidence builders and validation.
- Context: smoke testing the new domain/tracking authorization packages against a local-only rehearsal capture plan.
- Symptom: direct package generation from a rehearsal plan emitted executable command strings and suggested authorization text containing the simulated site key.
- Evidence: the capture handoff path already suppresses simulated command output, but `prepare_capture_authorization.py` could be called directly on `simsite01` plans and produce copyable commands.
- Risk: rehearsal artifacts could be mistaken for real LAICMS mutation authorization, especially when testing newly supported module actions.
- Rule: direct authorization-package generation must suppress commands for known simulated site keys by default. Use an explicit local-test flag only when testing helper output, never for real browser work.
- Follow-up: `prepare_capture_authorization.py` now redacts simulated targets, suppresses commands by default, and requires `--allow-simulated-target` for local command-output smoke tests.
- Context: capture handoff builds a second safety wrapper around the direct authorization package.
- Symptom: after direct package generation began suppressing simulated targets, the handoff wrapper overwrote the audit-only `simulatedTarget` with an already-redacted target.
- Evidence: handoff validation expects user-facing text to contain `{realSiteKey}` while preserving `simsite01` only in `simulatedTarget` for audit.
- Risk: losing the simulated target makes local-only rehearsal artifacts harder to audit, while exposing it in suggested text is unsafe.
- Rule: nested suppression layers must preserve raw simulated targets only in explicit audit fields and keep user-facing authorization text templated.
- Follow-up: `make_capture_handoff.py` now preserves an existing `authorizationPackage.simulatedTarget` when applying handoff-level command suppression.
- Context: explicit handoff smoke tests sometimes need command output from simulated plans to verify helper wiring.
- Symptom: handoff-level `allow_command_output=True` no longer produced gate-supported packages because the direct package helper suppressed simulated targets before the handoff wrapper could decide.
- Evidence: explicit route-stage handoff expected `gateSupported: true` for local tests, but the package returned suppressed commands.
- Risk: local wiring tests could no longer verify that supported capture actions generate coherent authorization and gate commands, hiding broken helper updates.
- Rule: the handoff wrapper must pass explicit local-test command-output intent down to the direct package helper. Default behavior remains command suppression for simulated targets.
- Follow-up: `make_capture_handoff.py` now forwards `allow_command_output` as `allow_simulated_target` when building the underlying package.

## 2026-06-30 Final Frontend Per-Item Audit Findings

- Context: local-only hardening after the operator was asked to verify frontend pages one by one and keep encountered problems recorded in the skill.
- Symptom: redacted final frontend audit reports collapsed every detail URL to `/posts/{slug}` or `/products/{slug}`. Count checks could catch a missing report, but the durable report lost which redacted item instance had been opened.
- Evidence: `audit_frontend_rendering.py --redact` intentionally removes concrete slugs, and `make_final_frontend_audit_stage_result.py` compared route patterns and counts. Multiple detail pages therefore shared the same redacted route label.
- Risk: an operator could claim "逐个打开验证" while the stored evidence only proved repeated route-pattern coverage, not distinct per-item audit identities. Reintroducing concrete slugs would fix identity but leak run-specific content into reusable artifacts.
- Rule: redacted frontend audit reports must preserve a neutral per-report instance key such as `products-detail-1` while keeping `url` as `/products/{slug}`. Final audit conversion must reject multi-item detail coverage that lacks unique redacted route instances.
- Follow-up: `audit_frontend_rendering.py` now emits `routeInstance`, final audit inputs summarize `detailRouteInstances`, and the stage-result converter/rehearsal validator require matching redacted instances for multi-item detail audits.

## 2026-06-30 Per-Stage Evidence Bundle Findings

- Context: local-only continuation toward a from-scratch real-browser site-build runbook.
- Symptom: the skill had single-stage packets and stage-result validators, but no deterministic place to prepare redacted proof files before running each browser stage.
- Evidence: packet output named required proof and result templates, while operators still had to invent a directory layout for redacted browser scans, network captures, backend proof, frontend audit output, and the final `stage-result.json`.
- Risk: proof could remain only in chat, evidence pointers could become vague, or a later ledger apply could be built from hand-written paths that are not tied to the packet's stage id and mutation expectation.
- Rule: before a real browser stage, create a local stage evidence bundle from the validated packet. The bundle must be local-only, non-mutating, inherit the packet's `stageId`, `authorizationRequired`, and `remoteMutationExpectation`, and start with a partial stage-result template so no unrun stage is accidentally marked complete.
- Follow-up: `prepare_browser_stage_evidence_bundle.py` now writes `evidence-manifest.json`, `stage-result-template.json`, and `notes.md`; `run_full_rehearsal.py` generates the first-stage bundle, and `validate_full_rehearsal.py` cross-checks it against the first packet.
- Context: follow-up local rehearsal after adding the per-stage evidence bundle.
- Symptom: the full rehearsal generated the bundle, but `browser-runbook-summary.json` still listed only the ledger, packet, handoff, and capture coverage as required local artifacts.
- Evidence: `make_browser_runbook_summary.py` did not copy `browserStageEvidenceBundle` or `browserStageEvidenceManifest` into `nextRealBrowserStep` or `requiredLocalArtifacts`, even though `run_full_rehearsal.py` wrote both paths.
- Risk: a real-browser operator could follow the runbook summary, skip the prepared evidence directory, and return to chat-only or ad hoc proof collection.
- Rule: the real-browser runbook summary must point directly to the next stage's evidence bundle and manifest, and the full-rehearsal validator must reject drift in those paths.
- Follow-up: `make_browser_runbook_summary.py` now exposes `evidenceBundle`, `evidenceManifest`, `nextBrowserStageEvidenceBundle`, and `nextBrowserStageEvidenceManifest`; `validate_full_rehearsal.py` and regression tests cross-check those paths.

## 2026-06-30 Evidence Bundle Validator Findings

- Context: local-only hardening before using per-stage evidence bundles for real browser module/interface capture and JSON replay assessment.
- Symptom: the full rehearsal generated and indirectly checked the first evidence bundle, but there was no standalone validator for a bundle directory or manifest used outside the rehearsal.
- Evidence: `prepare_browser_stage_evidence_bundle.py` wrote `evidence-manifest.json`, `stage-result-template.json`, and `notes.md`, while `validate_full_rehearsal.py` only spot-checked selected manifest fields against the first packet.
- Risk: an operator could reuse or hand-edit a bundle whose manifest, packet path, template status, notes proof rules, or mutation expectation drifted, then advance a browser stage from unsafe or non-auditable proof scaffolding.
- Rule: before a real browser stage or ledger apply, validate the evidence bundle itself. The validator must check packet alignment, local-only/non-mutating status, partial template state, required proof notes, redaction, and no concrete site-scoped workspace or frontend origins.
- Follow-up: `validate_browser_stage_evidence_bundle.py` now validates bundles directly; `run_full_rehearsal.py` records `browserStageEvidenceBundleSafety`, `validate_full_rehearsal.py` recomputes it, and regression tests cover valid bundles plus manifest, template, and notes drift.

## 2026-06-30 Packet Command Path Findings

- Context: local-only hardening of staged real-browser packets before using them as the operator's immediate instruction for site creation, request capture, launch work, and cleanup.
- Symptom: `ledgerUpdate.commandTemplate` used a fixed `/tmp/allincms-full-rehearsal/...` example path even when the packet was generated under a different run directory.
- Evidence: the packet carried correct stage id, proof, and result-json workflow, but the copyable command could still point at the wrong ledger, packet, result, or updated-ledger path.
- Risk: a real-browser operator could apply a stage result to a stale rehearsal ledger, validate against a different packet, overwrite another run's ledger, or lose same-stage recovery proof by copying the static example command.
- Rule: packet update commands must either contain explicit current-run paths for the generated ledger, packet, stage-result, and updated-ledger output, or use visible placeholders such as `{ledgerPath}` that cannot be mistaken for executable paths.
- Follow-up: `build_browser_stage_packet.py` now accepts path parameters and emits path-aligned `commandTemplate` values; `run_full_rehearsal.py` passes current artifact paths for normal and recovery packets; `validate_full_rehearsal.py` rejects command-path drift; regression tests cover both placeholder packets and stale default-path packets.

## 2026-06-30 Browser Runbook Operator Handoff Findings

- Context: local-only rehearsal/runbook hardening before continuing real LAICMS browser stages.
- Symptom: the next real-browser stage required packet, ledger, evidence bundle, stage-result template, authorization helper, and ledger apply command artifacts, but the compact runbook summary did not expose them as one operator handoff.
- Evidence: `browser-runbook-summary.json` listed the next step and evidence bundle, while the exact `ledgerUpdate.commandTemplate` and stage-result paths lived in the packet and bundle manifest separately.
- Risk: a future operator could fill proof in the evidence bundle but apply a stale packet command or write the stage result to a path the ledger apply command does not read.
- Rule: every full rehearsal runbook must include an `operatorHandoff` checklist with packet path, ledger path, evidence bundle, evidence manifest, stage-result template, bundle draft result path, ledger-expected stage-result path, ledger apply command, authorization preparation template, required proof, stop condition, and next action mode.
- Follow-up: `make_browser_runbook_summary.py` now emits `operatorHandoff`, and `validate_full_rehearsal.py` cross-checks the handoff against the current packet, ledger, evidence bundle, and command paths.
- Context: same local-only handoff hardening round.
- Symptom: the evidence bundle's local draft result path can differ from the stage-result path embedded in `ledgerUpdate.commandTemplate`.
- Evidence: generated bundle scaffolding writes `next-browser-stage-evidence-bundle/stage-result.json`, while the packet apply command expects the packet-sibling `next-browser-stage-packet-stage-result.json`.
- Risk: treating those paths as interchangeable can make a real browser stage look documented while the ledger apply step reads an older or missing result file.
- Rule: distinguish `bundleStageResultDraftPath` from `ledgerExpectedStageResultPath`; copy or write the final redacted stage result to the ledger-expected path before running `ledgerApplyCommand`.
- Follow-up: the runbook summary now surfaces both paths and the validator rejects drift.

## 2026-06-30 Real Read-Only Refresh Findings

- Context: real browser read-only refresh of a logged-in LAICMS workspace and one temporary site before any create-site mutation.
- Symptom: `redact_browser_scan.py` correctly templated module URLs to `https://workspace.laicms.com/{siteKey}/...`, but `make_existing_site_evidence_from_scan.py` required the concrete `/{siteKeyValue}/module` path and rejected the redacted scan.
- Evidence: redacted scan preserved protected module URLs with `{siteKey}` placeholders; conversion failed on `scan.modules.dashboard.url must be /{realSiteKeyValue}/dashboard`.
- Risk: the safe redaction step could make real read-only evidence unusable, nudging operators to either skip redaction or hand-copy evidence from raw browser scans that contain account/menu/frontend-domain noise.
- Rule: scan-to-evidence conversion must accept protected module URLs with `{siteKey}` or `{realSiteKey}` placeholders and reconstruct the concrete module route from the separately verified `siteKey`.
- Follow-up: `make_existing_site_evidence_from_scan.py` now accepts redacted module URL placeholders while still rejecting wrong domains, missing modules, and wrong module names; regression tests cover placeholder URLs.
- Context: same real read-only refresh, after applying a stage result to the browser execution ledger.
- Symptom: hand-run commands drifted from the actual helper CLIs: `apply_browser_stage_result.py` has no `--json`, and `build_browser_stage_packet.py` takes the ledger JSON as a positional argument rather than `--ledger`.
- Evidence: both commands exited with argparse errors before succeeding with the helper's actual CLI shape.
- Risk: operators can lose time or corrupt handoff instructions by adding flags from nearby helpers instead of using the packet's `ledgerUpdate.commandTemplate` or the helper `--help` output.
- Rule: for stage apply and packet regeneration, copy the generated packet command or check the helper `--help`; do not infer common flags such as `--json` or `--ledger` across scripts.
- Follow-up: keep runbook/packet command templates as the source of truth for stage application, and record CLI drift whenever a command example fails.
- Context: real browser read-only refresh of `/sites` and the current site's setup/content modules before the `create_site_submit` stage.
- Symptom: a broad DOM query that selected any container containing `创建站点` captured the site-list search field instead of the actual create-site dialog fields.
- Evidence: the first scan returned `input placeholder: 搜索站点...` under `sites.createDialog.fields`; a narrowed `[role="dialog"]` scan then returned `input name: name, placeholder: 站点名称` and `textarea name: description, placeholder: 站点简介`, with controls `创建` and `Close`.
- Risk: preflight evidence can look structurally present while proving only the page-level site list, not the modal fields needed before creating a site.
- Rule: create-dialog evidence must be scoped to the actual modal surface and must contain both `name` and `description` fields plus create and close controls. Do not accept broad page containers or body-text matches as dialog proof.
- Follow-up: `site-creation.md` now documents the modal scoping rule for create-dialog field capture.
- Context: preparing the next `create_site_submit` packet after applying the real read-only refresh stage.
- Symptom: the real refresh produced `existing_site_selected` evidence, but the create-site mutation gate requires a distinct `create_preflight_verified` evidence file.
- Evidence: `check_pre_mutation_gate.py --action create_site` checks `preflight.siteCreation.status == create_preflight_verified`, while the validated read-only site evidence records the current working site as `existing_site_selected`.
- Risk: an operator could either try to use existing-site evidence directly and hit a late gate failure, or weaken the gate and accidentally count an existing site as proof for a from-scratch create flow.
- Rule: after a real read-only refresh, derive a separate create preflight with `make_create_preflight_evidence.py` using the fresh site-key list, strong site-key evidence, scoped create-dialog fields, and `dialogClosedVerified: true`. Use that create preflight for `create_site_submit`; keep existing-site evidence for content/module continuation.
- Follow-up: `site-creation.md` now states the conversion requirement before preparing or validating create-site authorization.
- Context: local-only hardening immediately after the first real read-only refresh.
- Symptom: deriving create-site preflight from existing-site evidence required a hand-written command that extracted `existingSiteKeysBeforeCreate` and create-dialog fields, then reconstructed strong site-key evidence.
- Evidence: the manual command worked, but it duplicated builder logic and could drift from future `make_create_preflight_evidence.py` validation rules.
- Risk: future operators could hand-copy stale site-key evidence, omit a field, preserve `siteIdentity` in create preflight, or accidentally use the wrong evidence status for `create_site_submit`.
- Rule: use `make_create_preflight_from_existing_site_evidence.py` to convert fresh `existing_site_selected` evidence into a separate `create_preflight_verified` file before create-site authorization prep.
- Follow-up: helper script, regression tests, `SKILL.md`, and `site-creation.md` now document and validate this conversion path.

## 2026-06-30 Create-Site Authorization Package Findings

- Context: real read-only create-site preflight after the browser stage ledger advanced to `create_site_submit`.
- Symptom: the browser-stage authorization helper can emit a package with suggested text and command templates, but the pre-mutation gate must still fail until an actual user authorization record exists.
- Evidence: `prepare_browser_stage_authorization.py` wrote a `create_site_submit` package with `gateSupported: true`; running `check_pre_mutation_gate.py` immediately after failed because `/tmp/allincms-authorization-create-site-next.json` did not exist.
- Risk: an operator could mistake a generated authorization package for action-time permission and submit the create-site form without a current user instruction naming the target and fields.
- Rule: authorization packages are preparation artifacts only. The mutation gate may pass only after `make_authorization_record.py` validates current user authorization text and writes the authorization JSON.
- Follow-up: keep the failed missing-authorization gate as the expected stop condition before real create-site submit.
- Context: local-only preparation after a run summary emitted `authorize_content_probe` and a `create_product_probe` next action.
- Symptom: the preparation package was initially assembled by hand from `nextActionDetails`, duplicating summary fields and risking stale command paths or accidental removal of the authorization-source placeholder.
- Evidence: `summarize_run_status.py` already emitted the suggested authorization text, authorization-record command template, and pre-mutation gate command; the local gate correctly failed because the authorization JSON did not exist.
- Risk: hand-written packages can be mistaken for user authorization, lose the placeholder that forces action-time authorization, or drift from the summary's preflight path.
- Rule: when `summarize_run_status.py --output` contains `nextActionDetails`, use `scripts/prepare_next_action_authorization.py` to generate the non-authorizing package. Require `preparedOnly: true`, `isUserAuthorization: false`, a retained authorization-source placeholder, and an optional expected missing-authorization gate failure before browser mutation.
- Follow-up: `prepare_next_action_authorization.py`, tests, and `SKILL.md` now cover summary-derived authorization packages.
- Context: resumed maintenance after preparing a real `create_site_submit` browser-stage authorization package from fresh read-only `/sites` evidence.
- Symptom: the package existed as JSON, but there was no deterministic validator proving it still matched the current packet and create preflight, retained the current-user authorization placeholder, and warned that it was not authorization.
- Evidence: the expected missing-authorization gate failure proved the stop condition, but a future operator could still hand-edit the package or reuse it after packet/preflight drift.
- Risk: a package can look official while pointing at stale packet paths, missing `name,description`, dropping the placeholder, or being mistaken for the user's current permission.
- Rule: after `prepare_browser_stage_authorization.py`, run `validate_browser_stage_authorization_package.py` with the current packet and preflight. Passing validation only proves package coherence; user authorization and `check_pre_mutation_gate.py` are still required immediately before mutation.
- Follow-up: validator script, regression tests, `SKILL.md`, `site-creation.md`, and `mutation-safety.md` now require package validation before create-site submit authorization handling.
- Context: live read-only `/sites` refresh applied to a local browser execution ledger after a full from-scratch rehearsal.
- Symptom: the standalone `browser-runbook-summary.json` stored the next step under `nextRealBrowserStep.stageId`, while `rehearsal-summary.json` stored a compact embedded value under `browserRunbookSummary.nextStageId`.
- Evidence: reading the standalone runbook top-level `nextStageId` returned empty even though the runbook correctly reported `nextRealBrowserStep.stageId=refresh_readonly_site_evidence`.
- Risk: operators can falsely think the runbook has no next stage or read the wrong artifact path before browser execution.
- Rule: use `nextRealBrowserStep.stageId` in `browser-runbook-summary.json`; use `browserRunbookSummary.nextStageId` only when reading the embedded compact summary inside `rehearsal-summary.json`.
- Follow-up: `SKILL.md`, `e2e-simulation.md`, and this finding now document the field-path distinction.
- Context: live read-only `/sites` stage was applied and the ledger advanced to the create-site stage.
- Symptom: filtering `stages` for `status == "ready"` returned an empty list while `ledger.nextStageId` correctly said `create_site_submit`.
- Evidence: `build_browser_stage_packet.py` accepted the updated ledger and generated a valid `create_site_submit` packet.
- Risk: a manual status scan can incorrectly report no next stage and either stall the run or rebuild the ledger from stale plan data.
- Rule: after applying a stage result, treat `ledger.nextStageId` as the authority and build the next packet from the ledger. Do not infer readiness by ad hoc stage-status filters.
- Follow-up: `SKILL.md` and `e2e-simulation.md` now state the `nextStageId` rule.
- Context: checking the expected missing-authorization failure before create-site submit in zsh.
- Symptom: a wrapper command used `status=$?`, but `status` is a read-only zsh parameter, causing an extra shell error after the intended gate failure.
- Evidence: rerunning the same check with `cmd_status=$?` produced the clean expected result: missing authorization JSON and exit status 2.
- Risk: expected-failure checks can produce noisy or misleading output, making it harder to distinguish correct stop gates from command bugs.
- Rule: in zsh wrapper snippets, use `cmd_status`, `exit_code`, or another non-reserved variable name; do not assign to `status`.
- Follow-up: record this as command hygiene for future expected-failure gate checks.
- Context: live read-only setup inspection of an existing site after `/sites` refresh and before any module capture.
- Symptom: the first setup scan captured useful module-local fields, but it also included account-menu text, site-switcher labels, and concrete frontend domain text inside repeated header buttons.
- Evidence: a leakage check found email-like text and account/site labels in the raw setup scan; a second redaction pass removed them while preserving six setup modules, field names, placeholders, table headers, and mutation-looking control labels.
- Risk: even read-only setup scans can leak private account or business identifiers into run artifacts or future skill sedimentation if generic header/sidebar controls are stored verbatim.
- Rule: setup-page evidence needs a second redaction pass that keeps module-local controls and field metadata only. Drop account menu text, site-switcher button text, concrete frontend domains, site names, recent-activity text, and business copy.
- Follow-up: `site-creation.md` now documents second-pass setup redaction.
- Context: preparing the next `module_interface_capture` package after real setup inspection.
- Symptom: the authorization package selected exactly one action (`posts:create`) but still contained `{realSiteKey}` and suppressed commands because the capture plan/coverage came from local rehearsal templates.
- Evidence: package output showed `target=https://workspace.laicms.com/{realSiteKey}/posts`, `gateSupported=false`, `commandsSuppressed=true`, and no authorization/gate commands; the missing-authorization gate still failed as expected.
- Risk: an operator could mistake a simulated/rehearsal module-capture package for real-site authorization and click a create button that may immediately create a draft.
- Rule: for a real browser run, module-capture authorization packages that still contain `{realSiteKey}` are template-only. Rebuild the capture plan or authorization package from current real-site evidence and require a concrete backend target before recording action-time authorization.
- Follow-up: `SKILL.md` now states the template-only stop condition for module capture packages.
- Context: live read-only scan of the current real site modules before module-interface capture.
- Symptom: the local rehearsal capture plan produced template targets, so a real-site module scan was needed before preparing a concrete capture authorization package.
- Evidence: the real read-only scan covered products, posts, media, themes, routes, forms, site-info, domains, and tracking; the module summary stayed `jsonReplayReady: false` and emitted only `visible_control_only` capture actions. The concrete capture plan then targeted `https://workspace.laicms.com/{siteKey}/products` for `products:create`, and the package emitted a supported `create_product_probe` gate while missing authorization still failed.
- Risk: using rehearsal capture plans directly can leave targets templated, while using a concrete package without validation can still drift from the selected plan stage or be mistaken for user authorization.
- Rule: before module capture on a real site, build a redacted real-site module scan, summarize it, generate a concrete capture plan, prepare exactly one capture authorization package, validate that package against the plan, and only then ask for fresh action-time authorization.
- Follow-up: `validate_capture_authorization_package.py`, regression tests, `SKILL.md`, and `interface-inventory.md` now add the deterministic capture-package validation gate.
- Context: regression testing the new capture-package validator against simulated capture packages.
- Symptom: command-suppressed simulated packages warned that commands were suppressed but did not explicitly say the package was not user authorization.
- Evidence: `validate_capture_authorization_package.py` rejected the simulated package until the warning text included `not user authorization`.
- Risk: a template/suppressed package can be safer than an executable command but still be misread as permission if the warning omits the authorization boundary.
- Rule: every capture authorization package, including simulated or command-suppressed packages, must explicitly state that it is not user authorization.
- Follow-up: `prepare_capture_authorization.py` now emits the non-authorization warning for simulated packages, and regression tests cover it through the package validator.

## 2026-06-30 Interface Coverage vs JSON Replay Findings

- Context: local-only hardening after considering whether theme/page/module operations should use JSON submission for speed.
- Symptom: complete module capture coverage previously set `jsonReplayReady: true`, even though coverage only proves every planned module/action was captured or marked not applicable.
- Evidence: `update_module_capture_coverage.py` treated `complete and not blocked` as JSON replay readiness, while the interface inventory requires per-action request URL, method, volatile headers, payload shape, IDs, authorization boundary, backend persistence proof, frontend proof when public, and rollback/cleanup plan.
- Risk: an operator could treat a complete interface scan as permission to replay Server Actions or batch-submit JSON, skipping action-specific schema and persistence verification.
- Rule: split interface coverage from replay readiness. `interfaceCoverageComplete: true` may unlock the next browser stage, but `jsonReplayReady` must remain false until exact action replay contracts are validated separately.
- Follow-up: module coverage summaries now expose `interfaceCoverageComplete`, keep `actionReplayContractsVerified: false`, keep `jsonReplayReady: false`, and validators/tests reject the old conflation.

## 2026-06-30 Action Replay Contract Findings

- Context: local-only hardening for JSON/Server Action acceleration after module interface coverage was separated from replay readiness.
- Symptom: the workflow said a future validator must prove exact action replay contracts, but no deterministic contract validator existed yet.
- Evidence: `interfaceCoverageComplete` could now remain separate from `jsonReplayReady`, while operators still had to manually inspect request URL, method, headers, payload shape, IDs, authorization action, backend proof, frontend proof, and cleanup plan for each action.
- Risk: a future browser run could reintroduce subjective judgment or mark `jsonReplayReady` based on partial request capture, raw header values, or backend-only proof for a public action.
- Rule: represent JSON replay readiness as a redacted per-action contract and validate it with `validate_action_replay_contract.py`. Keep contracts local-only, action-specific, and free of cookies, authorization values, raw server action IDs, router state, account emails, and raw payloads.
- Follow-up: `validate_action_replay_contract.py`, SKILL instructions, request-capture guidance, interface inventory guidance, and regression tests now define the action-level replay gate.
- Context: follow-up aggregation of validated replay contracts back into module coverage.
- Symptom: once per-action contracts existed, there was no deterministic way to say a whole coverage file had every captured stage backed by a valid contract.
- Evidence: `update_module_capture_coverage.py` correctly kept `jsonReplayReady: false`, but a future operator would otherwise have to hand-check whether contract files covered every captured `module:action`.
- Risk: missing one contract, using a wrong-stage contract, or accepting a duplicate could make a module look replay-ready while one action still lacks proof.
- Rule: use `apply_action_replay_contracts.py` to aggregate valid contracts into coverage. It must require one matching valid contract for every captured stage before setting `actionReplayContractsVerified: true` and `jsonReplayReady: true`.
- Follow-up: contract aggregation helper and regression tests now reject missing and wrong-stage contracts while preserving the rule that replay readiness is technical evidence only, not user authorization.
- Context: follow-up sync from replay-ready coverage back into the browser execution ledger.
- Symptom: a replay-ready coverage file could set `lastCoverageSync.jsonReplayReady: true`, while the `module_interface_capture` ledger proof still said action replay contracts required validation.
- Evidence: `sync_ledger_with_coverage()` had a single completed-coverage proof string before checking `jsonReplayReady`.
- Risk: runbook operators could see contradictory status: coverage technically replay-ready, but ledger proof implying contracts were still missing.
- Rule: when replay-ready coverage is synced, the ledger entry must say per-action contracts are verified and list next actions as authorization/gate steps, not more contract validation.
- Follow-up: ledger sync now emits replay-ready proof text plus `request fresh action-time authorization` and `run action-specific mutation gate` next actions.

## 2026-06-30 Round-Issue Command Drift Findings

- Context: local-only full rehearsal from site creation through browser execution planning after the closeout gate started requiring `--round-issue`.
- Symptom: `references/e2e-simulation.md` still showed maintenance closeout examples without `--round-issue`, while `SKILL.md` and `check_round_closeout.py` required it.
- Evidence: a grep over skill references found the stale `make_round_maintenance_summary.py` and `check_round_closeout.py` command examples in the E2E simulation reference.
- Risk: an operator following the simulation reference could copy a command that fails the current closeout gate, or worse, omit the actual per-turn issue list when performing maintenance closeout.
- Rule: whenever the closeout gate gains a required flag or summary field, update every command example in the directly linked references in the same turn.
- Follow-up: `e2e-simulation.md` examples now include matching `--round-issue` values for both maintenance summary generation and closeout validation.

## 2026-06-30 Capture Authorization Placeholder Findings

- Context: real read-only module scan generated a 10-stage capture plan and per-action capture authorization packages for products, posts, media, themes, routes, forms, site-info, domains, and tracking.
- Symptom: direct capture-plan packages embedded the helper-generated Chinese `suggestedAuthorizationText` in `authorizationRecordCommand --authorization-source`.
- Evidence: product probe packages showed a copyable `make_authorization_record.py` command whose authorization source was generated wording rather than a current-user placeholder.
- Risk: a preparation artifact could be mistaken for action-time user authorization, allowing an operator to create a probe, add a domain/tracking tag, or trigger another mutation without fresh current-run permission.
- Rule: all capture-plan authorization packages must keep `--authorization-source '<paste current user authorization text here>'` in emitted commands. `suggestedAuthorizationText` is user-facing guidance only and must never be embedded as command authorization source. Reject command packages that already contain `授权 Codex` or the full suggested text.
- Follow-up: `prepare_capture_authorization.py`, `validate_capture_authorization_package.py`, regression tests, `SKILL.md`, and `interface-inventory.md` now enforce the placeholder rule for direct capture packages.

## 2026-06-30 Browser Context Freshness Findings

- Context: continuing a real LAICMS browser run after several tab changes and a context handoff.
- Symptom: chat-provided in-app browser metadata reported the design page, while the live tab list showed the active backend tab on `tracking` and a frontend tab on the site homepage.
- Evidence: reading `openTabs()` before acting revealed the actual browser state differed from the prompt's `Current URL` metadata.
- Risk: an operator could mutate or verify the wrong module if they trust stale prompt metadata after redirects, tab switches, resumes, or context compaction.
- Rule: before every browser action, read the live tab list (`openTabs()` or equivalent) and treat it as the authority for current URL and tab selection. Use chat metadata only as a hint.
- Follow-up: `SKILL.md` now includes a workflow step requiring live tab-state confirmation before acting on LAICMS browser pages.

## 2026-06-30 Scan Table Header Alias Findings

- Context: current real-site read-only backend scan was converted into existing-site run evidence after frontend static route audit.
- Symptom: the browser scan and module summarizer use `tableHeaders`, while `make_existing_site_evidence_from_scan.py` accepted only `tableHeads` for content list columns.
- Evidence: the current scan had product list columns under `tableHeaders`; evidence conversion required a manual normalization step before the helper could build run evidence.
- Risk: operators may hand-edit redacted browser scan JSON, losing provenance or accidentally changing fields, just to satisfy a helper alias mismatch.
- Rule: scan-to-evidence helpers must accept both `tableHeads` and `tableHeaders` as equivalent neutral list-column evidence, while still requiring the selected content type to have a non-empty column list.
- Follow-up: `make_existing_site_evidence_from_scan.py` and regression tests now accept the alias directly.

## 2026-06-30 Full Rehearsal Summary Shape Findings

- Context: local-only full rehearsal from site creation through browser execution planning during goal continuation.
- Symptom: the generated `rehearsal-summary.json` and `browser-runbook-summary.json` validated successfully, but probing them for run-evidence fields such as `valid`, `complete`, and `completionGaps` returned missing values.
- Evidence: `rehearsal-summary.json` has `kind: allincms_full_rehearsal_summary` with safety blocks such as `fullE2EValidation.ok`, `handoffSafety.ok`, `browserExecutionPlanSafety.ok`, and `nextBrowserActionHandoffSafety.ok`; `browser-runbook-summary.json` has `kind: allincms_browser_runbook_summary` and `nextRealBrowserStep.stageId`.
- Risk: operators can falsely report a rehearsal as incomplete because run-evidence fields are absent, or falsely apply run-evidence completion semantics to a local-only orchestration artifact.
- Rule: judge full rehearsal artifacts with `validate_full_rehearsal.py`, `validate_browser_runbook_summary.py`, and their safety/runbook fields. Use `summarize_run_status.py` and `valid/complete/completionGaps` only for run-evidence JSON.
- Follow-up: `SKILL.md`, `e2e-simulation.md`, and this finding now document the summary-shape distinction.

## 2026-06-30 Zsh Backtick Search Pattern Findings

- Context: final verification after documenting full rehearsal summary-shape rules.
- Symptom: an `rg -n "Do not read `rehearsal-summary.json`..." ...` command printed `zsh: command not found: rehearsal-summary.json` before returning matches.
- Evidence: zsh interpreted backticks inside the double-quoted search pattern as command substitution.
- Risk: a harmless verification search can emit noisy shell errors, hide a real failure, or make operators think a referenced artifact is missing.
- Rule: when searching for literal Markdown code spans or any string containing backticks in zsh, wrap the pattern in single quotes or escape the backticks. Prefer `rg -n 'literal `code` text' ...` for documentation checks.
- Follow-up: record this as command hygiene; no helper change is needed.

## 2026-06-30 Fresh Existing-Site Continuation Findings

- Context: live read-only refresh of an existing site before preparing a `products:create` module-interface capture.
- Symptom: a broad DOM summary captured private account-menu text, concrete frontend domains, site labels, and business copy before redaction.
- Evidence: the raw browser result contained useful module fields plus repeated global header/sidebar/site-card text; a minimized redacted scan preserved only site key, module URLs, create-dialog controls, table headers, input placeholders, and neutral buttons.
- Risk: storing raw read-only scans can leak account or business data even when no remote mutation occurred.
- Rule: after browser scans, write only a minimized redacted scan to disk before evidence conversion. Avoid broad `body`/page-text dumps; preserve module-local evidence and structural controls only.
- Follow-up: keep using `redact_browser_scan.py` plus `make_existing_site_evidence_from_scan.py`; do not hand-copy raw browser dumps into durable artifacts.

- Context: live read-only module scan after returning to the products page.
- Symptom: the first redacted scan removed emails and frontend domains but still preserved a business site title in dashboard headings and a deep theme object link under dashboard links.
- Evidence: a post-redaction grep still found the site display title, and dashboard links retained `/themes/{themeId}` before the redactor was tightened.
- Risk: supposedly redacted module scans can leak business copy or raw object identifiers into downstream summaries, capture plans, or handoffs.
- Rule: scan redaction must drop non-module dashboard headings and deep object links. Preserve only module-local headings, first-level backend module links, tab query links, table headers, inputs, and neutral controls.
- Follow-up: `redact_browser_scan.py` now filters non-neutral headings and deep links; regression tests cover site-title and deep object-link removal.

- Context: applying fresh read-only evidence back into the staged browser execution ledger.
- Symptom: a stale `create_site_submit` packet was accidentally used to build a refresh stage result, causing proof validation to demand create-site authorization, site card proof, backend proof, and frontend proof.
- Evidence: `make_browser_stage_result.py` rejected the result with missing create-site proof; using the initial `refresh_readonly_site_evidence` packet succeeded and allowed the existing-site ledger branch.
- Risk: reusing similarly named packet files from a long rehearsal directory can advance or validate the wrong stage.
- Rule: when applying a browser stage result, confirm `packet.stageId` matches the evidence you just captured before writing the result. The filename alone is not enough; inspect or validate the packet stage.
- Follow-up: record this as an operator stop condition; no helper change was required because the validator rejected the mismatch.

- Context: preparing a fresh browser-stage authorization package for `module_interface_capture`.
- Symptom: `prepare_browser_stage_authorization.py` uses positional `packet_json` and selects the next capture stage from the capture plan/coverage; it does not accept `--packet-json`, `--capture-module`, or `--capture-action`.
- Evidence: the first command failed with `unrecognized arguments`; checking `--help` showed the current CLI contract, and the corrected command produced a valid `products:create` handoff.
- Risk: operators can waste freshness windows or drift into hand-written JSON when helper CLI assumptions are stale.
- Rule: before scripting an older helper from memory, run `--help` and copy the current flags. Prefer coverage files for selecting later capture stages; without coverage, the helper selects the first capture-plan stage.
- Follow-up: keep command examples aligned with helper `--help` output when documenting real browser handoffs.

- Context: local inspection of fresh capture authorization package-set and next-browser-action handoff JSON.
- Symptom: an ad hoc reader script expected package-set fields named `packageCount` and `packages`, and a top-level handoff field named `stopCondition`.
- Evidence: the actual package-set summary uses `count` and `items`; the handoff uses `stopAfter`, matching the underlying browser-stage authorization package and validator.
- Risk: operators can misreport a valid package set as empty or think the stop condition is missing, then rebuild artifacts unnecessarily or hand-write unsafe summaries.
- Rule: read helper output by its current `kind` and actual field names. For capture package sets use `count/items`; for next-browser-action handoffs use `stopAfter`.
- Follow-up: `SKILL.md` and `interface-inventory.md` now document these field names.

- Context: resuming from a prepared `products:create` next-browser-action handoff before any action-time user authorization.
- Symptom: `validate_next_browser_action_handoff.py` correctly returned valid while the preflight evidence was still within the 30-minute window, but the output did not summarize how close the source evidence was to staleness or whether it was appropriate to ask the user for authorization now.
- Evidence: the handoff remained preparation-only and valid; a separate read-only products-page check confirmed the product list was still empty and no probe text was visible.
- Risk: an operator may ask for authorization from a structurally valid handoff without noticing that the read-only evidence needs refresh soon, or may fail to distinguish "valid handoff" from "ready to request authorization".
- Rule: run `make_handoff_readiness.py` before asking the user for action-time authorization. Treat `ready_to_request_authorization` as permission to ask, not permission to click; treat `blocked_refresh_readonly_evidence` as a mandatory read-only refresh.
- Follow-up: `make_handoff_readiness.py`, `SKILL.md`, and regression tests now cover fresh and stale handoff readiness.

- Context: generated suggested authorization text for content probe creation.
- Symptom: the helper produced mixed-language content labels such as `products 测试草稿`.
- Evidence: the fresh `products:create` handoff validated structurally but the suggested authorization text read awkwardly before helper wording was fixed.
- Risk: unclear or awkward authorization text can make action-time user approval less precise, especially when posts/products/forms have different payload schemas.
- Rule: suggested authorization text should use human-readable content labels (`文章`, `产品`, `表单`) while command fields keep machine module names (`posts`, `products`, `forms`).
- Follow-up: `prepare_browser_stage_authorization.py` now maps content types to Chinese labels, and regression tests reject `products 测试草稿`-style wording.

## 2026-06-30 Draft Manifest Planning Findings

- Context: local-only preparation of temporary products and posts before any real save request was captured.
- Symptom: products and posts draft manifests passed generic validation, while `--require-schema-verified` failed for both because `schemaVerified`, `fieldMapping`, and `payloadTemplate` were intentionally absent.
- Evidence: `validate_manifest.py` accepted the generic structure and then rejected the stricter upload gate with `capture the live save request for this content type first`.
- Risk: a clean draft manifest can be mistaken for upload readiness, especially when product and article content are prepared together.
- Rule: treat generic manifest validation as local source hygiene only. Keep products and posts schema gates separate and blocked until each content type has its own captured save request, payload template, sample backend/frontend proof, and cleanup proof.
- Follow-up: `batch-verification.md` now states that parallel draft preparation is allowed, but live upload remains content-type-specific and schema-gated.

- Context: local content normalization for rich body fields.
- Symptom: Markdown features such as bold syntax, inline code, links, and pipe tables remain unsafe for direct upload because the frontend may render raw syntax unless the editor block schema supports them.
- Evidence: `validate_manifest.py` rejects raw Markdown/HTML-like strings in `content`; the temporary manifests used structured paragraph/list arrays instead.
- Risk: generated content can look correct in a markdown preview but publish as raw syntax or broken rich text in LAICMS.
- Rule: use plain structured draft arrays or captured editor block JSON for body content. Do not upload Markdown tables, bold markers, links, or HTML-like spans until they have been converted to and verified as the current editor block schema.
- Follow-up: keep the raw-Markdown validator active and verify rich DOM nodes in frontend audit after sample publication.

- Context: local-only multi-manifest planning before request capture.
- Symptom: when products and posts draft manifests are prepared together, separate generic validation commands can make the batch look cleaner than it is because both still fail the upload schema gate.
- Evidence: a readiness report over the draft manifests returns `overallStatus: blocked`, `readyCount: 0`, and one blocked item per manifest with `schema_gate_not_passed`.
- Risk: an operator could proceed to sample upload planning from green generic checks while neither content type has a captured save payload template.
- Rule: use `make_manifest_upload_readiness.py` whenever more than one posts/products manifest is being staged. Report `blocked` as the expected state until each content type has live request capture, `fieldMapping`, and `payloadTemplate`.
- Follow-up: `SKILL.md`, `batch-verification.md`, and regression tests now include the readiness report helper and blocked/ready cases.

- Context: local verification of `make_manifest_upload_readiness.py --fail-on-blocked`.
- Symptom: a zsh one-liner used `status=$?` to capture the helper exit code and failed with `read-only variable: status`.
- Evidence: rerunning the same command with `exit_code=$?` proved the helper returned `1` for blocked manifests as intended.
- Risk: shell wrapper failures can be mistaken for helper failures, especially when verifying expected non-zero exits.
- Rule: in zsh validation snippets, avoid reserved or special parameter names such as `status`; use neutral names like `exit_code` when checking expected non-zero helper exits.
- Follow-up: record this as command hygiene; no helper code change was needed.

## 2026-06-30 Dialog Close Control Findings

- Context: read-only `/sites` refresh while opening the create-site dialog only to inspect fields and close it without submitting.
- Symptom: closing the dialog with a page-level keyboard press failed because the focused input target changed after the dialog opened.
- Evidence: `body.press('Escape')` failed with a focused-target mismatch; clicking the unique visible dialog `Close` control after confirming there was exactly one visible close button dismissed the modal.
- Risk: a read-only refresh can abort before saving evidence, or an operator may incorrectly mark `dialogClosedVerified: true` after a failed keyboard close.
- Rule: for create-site dialog read-only evidence, prefer a dialog-scoped close path: count visible `Close` controls, click only when unique, then verify no visible dialog remains. Use `Escape` only as a fallback and never record close proof until the modal is gone.
- Follow-up: `site-creation.md` documents the safer close order.

## 2026-06-30 Site-Key Extraction Findings

- Context: read-only `/sites` refresh before preparing a product probe-create handoff.
- Symptom: collecting keys from all page links returned navigation paths such as `/dashboard` and `/help-center` as if they were site keys.
- Evidence: a strict site-card scan found the actual site keys only inside visible `{siteKey}.web.allincms.com` card text, while generic links lacked site-card hrefs and included non-site navigation.
- Risk: before-create evidence can be polluted with fake keys, making created-site absence checks and existing-site continuation evidence unreliable.
- Rule: do not derive `existingSiteKeys` from generic page links. Use scoped site-card evidence, explicit `data-site-key`, backend module URLs, or visible frontend domains ending in `.web.allincms.com`; reject ordinary route names such as `dashboard`, `sites`, `users`, or `help-center`.
- Follow-up: keep strict site-key extraction in browser scan practice; strengthen helpers if a future raw scan shape exposes generic links under `sites.existingSiteKeys`.

## 2026-06-30 Regression Harness Findings

- Context: adding route-name rejection tests for browser-scan redaction and scan-to-evidence conversion.
- Symptom: a previously defined redactor regression had not been called from the file's hand-written `main()` list, so it did not run until another new test was added nearby.
- Evidence: after adding the missing call, the test exposed expected-shape drift: redacted module URLs now use `https://workspace.laicms.com/{siteKey}/...`, while the old assertion expected a concrete key.
- Risk: adding a test function without registering it in `main()` creates false confidence; old unrun tests can also preserve obsolete expectations.
- Rule: when adding tests to `test_validate_run_evidence.py`, add the function call to `main()` in the same patch and run the full file. Prefer assertions that match the current redaction contract, including `{siteKey}` placeholders for module URLs.
- Follow-up: redactor and converter tests now cover route-name rejection and the previously uncalled redaction-shape test is registered.

## 2026-06-30 Goal Continuation Authorization Findings

- Context: automatic continuation of a long-running AllinCMS goal while a product probe-create handoff was fresh and ready to request authorization.
- Symptom: the continuation context repeated the broad objective, but the current user message did not explicitly authorize clicking the product `创建` control or creating a probe draft.
- Evidence: `make_handoff_readiness.py` returned `ready_to_request_authorization`, whose next action is to ask the user for exact action-time authorization and not run commands until they provide it.
- Risk: an operator could mistake a system/tool goal reminder for current user authorization and mutate LAICMS state without explicit action-time approval.
- Rule: goal-continuation text, objective reminders, and bare "continue working" signals are never authorization sources. If the current user gives an explicit session-level instruction to proceed with future needed LAICMS operations, it may be used only when the generated authorization record still names the exact action, target URL, content type, expected result, verification plan, and cleanup boundary.
- Follow-up: `mutation-safety.md` lists goal continuation/objective reminders as non-authorization examples; `make_authorization_record.py` now separately handles exact-target current-session continuation text.

## 2026-06-30 Browser Stage Queue Findings

- Context: continuing a staged site/content rehearsal after a fresh `products:create` handoff and draft manifests were prepared.
- Symptom: the next 10 browser stages were first represented as a hand-written `/tmp` JSON queue.
- Evidence: the queue correctly kept only `products_create_probe` ready and locked save, publish, cleanup, posts, schema gate, batch upload, and final audit, but hand-written queues can drift from readiness and manifest reports.
- Risk: future operators might copy an old queue after evidence freshness changes, or accidentally mark batch upload ready before schema gate and sample proof.
- Rule: build staged browser queues from current handoff readiness and upload readiness with a helper. A queue is local planning only: it must never authorize browser mutation or unlock later stages without proof.
- Follow-up: `make_browser_stage_queue.py`, `SKILL.md`, and regression tests now cover fresh and stale readiness queues.

## 2026-06-30 Product Probe Create Findings

- Context: authorized live browser stage for `products:create` on a verified existing site.
- Symptom: clicking the empty-state `创建产品` control did not open a harmless dialog. It sent a Server Action `POST /{siteKey}/products` with payload shape `[{siteId}]`, then navigated to `/{siteKey}/products/{contentId}/update`.
- Evidence: the update page showed status `草稿`, default name pattern `Untitled Product`, numeric timestamp-like slug, `更新` disabled, and `发布` visible. No save or publish action was clicked in the create-only authorization.
- Risk: an operator may say the `Codex Probe - Delete Me` product was created even though the create-only stage leaves the backend draft under its platform default name until a later save.
- Rule: for products, treat create as a mutating draft-creation Server Action. If authorization stops after draft/dialog verification, record the cleanup candidate and stop; renaming to `Codex Probe - Delete Me`, request capture, persistence proof, publish, and cleanup are separate gated stages.
- Follow-up: `create-flows.md` and `SKILL.md` now warn that probe naming may require the save/request-capture stage.

- Context: applying the real product-create result to the generic browser execution ledger.
- Symptom: completing the broad `module_interface_capture` stage advanced the generic ledger to `theme_page_route_launch`, while the product-specific queue still requires product save request capture next.
- Evidence: `apply_browser_stage_result.py` marked `module_interface_capture` completed and reported next stage `theme_page_route_launch`; the product queue keeps `products_save_request_capture` behind stage-1 proof.
- Risk: a broad module-capture ledger can skip the content probe lifecycle when a single capture action is used as proof for an aggregate stage.
- Rule: after a granular product/post create probe, use the content-specific stage queue and probe evidence for the next content step. Do not rely on the generic aggregate ledger alone to decide whether save, publish, cleanup, or batch upload is unlocked.
- Follow-up: keep product/post lifecycle stages explicit in `make_browser_stage_queue.py`; future helper work should reconcile aggregate module capture completion with content-specific next stages.

## 2026-06-30 Save Probe Handoff Findings

- Context: preparing the next stage after an authorized product create probe left a draft edit page open.
- Symptom: the user's broad preference to proceed without repeated confirmations did not pass `save_probe` authorization-record validation because it did not name the exact save/capture action and edit URL.
- Evidence: `make_authorization_record.py --action save_probe ... --authorization-source '后续需要操作的，你直接进行，无需我授权...'` failed with `authorization source must mention the action`.
- Risk: treating broad continuation approval as save authorization can mutate the draft, capture incomplete payload evidence, or publish/batch later without a clear stop condition.
- Rule: save/request-capture remains a separate action boundary. Generate a `save_probe` handoff from create evidence and fresh preflight, but do not save until the current user message or an accepted policy explicitly names the save/capture action, exact edit URL, content type, probe/test intent, and stop condition.
- Follow-up: `prepare_probe_save_handoff.py`, `SKILL.md`, and regression tests now cover the create-to-save handoff.

- Context: interpreting a user's stated preference to proceed without further interruptions during a long AllinCMS run.
- Symptom: the preference is operationally useful for local preparation but unsafe if treated as remote mutation authorization.
- Evidence: the save handoff now exposes `automationPreference.canProceedWithoutAsking` for local/read-only steps and `automationPreference.doesNotAuthorize` for save, publish, cleanup, upload, batch, and replay.
- Risk: without an explicit field in handoff artifacts, future operators may either stop doing useful local work or over-apply the preference to remote mutations.
- Rule: broad automation preference may suppress repeated prompts for local/read-only work, but every LAICMS mutation still needs an action-specific authorization source accepted by `make_authorization_record.py`.
- Follow-up: `mutation-safety.md` and `prepare_probe_save_handoff.py` now encode this boundary.

- Context: preparing a future product save/request-capture browser stage without performing the save.
- Symptom: the handoff held authorization and gate commands, but not the concrete field-edit, network-capture, persistence-check, and evidence-template steps an operator must follow after the gate passes.
- Evidence: the generated save runbook contains `browserStepsAfterGate` for target confirmation, field edits (`名称`, `Slug`, `描述`), one `更新` click, network capture, backend persistence verification, forbidden actions, and a redacted evidence template starting with `savedOnce: false` and `published: false`.
- Risk: after authorization, operators could improvise the save capture, forget to enable network capture first, click publish, or record incomplete field mapping/payload template evidence.
- Rule: before any `save_probe` browser operation, generate `build_probe_save_runbook.py` from the save handoff. Execute its browser steps only after the authorization record exists and the save gate passes.
- Follow-up: `request-capture.md`, `build_probe_save_runbook.py`, and regression tests now cover the save-capture runbook.

- Context: validating a prepared save-probe runbook before browser execution.
- Symptom: a runbook can contain both the intended gated save action and broad automation-preference denials; if both are stored as `forbiddenActions`, the operator sees contradictory instructions.
- Evidence: the product save runbook inherited `saving the probe` from `automationPreference.doesNotAuthorize` even though the runbook's purpose is to save once after the `save_probe` gate passes.
- Risk: future operators may either skip the authorized save or ignore the whole forbidden list and accidentally publish, delete, upload, batch-submit, replay JSON, or click save repeatedly.
- Rule: separate `automationPreferenceDoesNotAuthorize` from `forbiddenActions`. Broad "continue" preferences do not authorize saving, but once action-time authorization and the gate pass, exactly one save is executable while publish/delete/upload/batch/replay/repeated-save actions remain forbidden.
- Follow-up: `validate_probe_save_runbook.py` now checks handoff/preflight/authorization alignment, missing-authorization blocking, unsaved evidence templates, and `ready_after_gate` before browser execution.

- Context: planning the post-save evidence merge before the real save request exists.
- Symptom: `merge_probe_evidence.py` could merge request-capture proof from many CLI strings, but it had no first-class validator for the richer save-runbook evidence template.
- Evidence: the save runbook emits a redacted `allincms_probe_save_capture_evidence` shape with `savedOnce`, `published`, request capture fields, field mapping, payload template, and backend persistence status; a direct string merge path could omit or leak critical fields.
- Risk: after a real save, an operator could merge incomplete evidence, raw `next-action` values, cookies, account emails, or unverified field mappings into run evidence and prematurely unlock publish or batch stages.
- Rule: after one authorized `save_probe` run, validate the redacted capture JSON with `validate_probe_save_capture_evidence.py`, then merge it with `merge_probe_evidence.py --save-capture-evidence`. Do not merge hand-copied request fields until the validator reports `mergeReady: true`.
- Follow-up: `merge_probe_evidence.py`, `request-capture.md`, and regression tests now support the validated JSON evidence path.

- Context: local smoke testing of save-capture evidence validation and merge.
- Symptom: a standalone redacted save-capture JSON validated, but merging it into a different site's run evidence failed because the request URL belonged to another `{siteKey}`.
- Evidence: the standalone validator returned `mergeReady: true`; `merge_probe_evidence.py` then failed with `request url must belong to siteKey mysite03`.
- Risk: operators could trust standalone evidence validation and only discover cross-site drift during merge, after already reporting readiness.
- Rule: validate save-capture evidence with `--base-run-evidence` whenever the evidence will be merged. The validator must bind the capture target, request URL, site key, and content type to the current run evidence before claiming merge readiness.
- Follow-up: `validate_probe_save_capture_evidence.py` now accepts base run evidence and rejects cross-site/content-type captures before merge.

- Context: local smoke testing after merging request-capture-only proof.
- Symptom: the merge succeeded and `summarize_run_status.py` wrote a useful summary with next action `authorize_publish_probe`, but full `validate_run_evidence.py` still failed because `sampleVerification` was intentionally missing. A separate command also failed because `summarize_run_status.py` does not support `--json`.
- Evidence: merged evidence contained `request_capture_persisted_verified`; summary marked `valid: false`, `missing: sample_backend_frontend_verified`, and emitted a publish-probe handoff.
- Risk: operators may mistake expected partial-evidence validation failure or a wrong summarizer flag for a broken request-capture merge.
- Rule: after request-capture-only merge, use `summarize_run_status.py --output <summary.json>` and inspect the output file. Treat missing `sampleVerification` as the expected next-stage gap, not as evidence corruption, if the summary emits `authorize_publish_probe`.
- Follow-up: `request-capture.md` now documents the summarizer command and the lack of `--json`.

## 2026-06-30 Publish Probe Evidence Findings

- Context: planning the next stage after request-capture proof produces `authorize_publish_probe`.
- Symptom: the skill had authorization and gate support for `publish_probe`, but lacked a save-runbook equivalent for the browser publish click and lacked a first-class validator for sample verification evidence.
- Evidence: `summarize_run_status.py` emitted a publish-probe handoff after request capture, while `merge_probe_evidence.py` only accepted sample proof as loose CLI strings.
- Risk: after a real publish, an operator could record frontend proof from the wrong host/path, skip render-audit checks, omit cover/media status, or accidentally treat publish authorization as cleanup/batch permission.
- Rule: build `build_probe_publish_runbook.py` from request-captured run evidence before publishing. After the gated publish, validate `allincms_probe_publish_sample_evidence` with base run evidence, then merge with `merge_probe_evidence.py --publish-sample-evidence`.
- Follow-up: publish runbook, publish sample evidence validator, merge support, and regression tests now cover the publish sample stage.

## 2026-06-30 Cleanup Probe Evidence Findings

- Context: planning the probe cleanup stage after sample backend/frontend verification.
- Symptom: cleanup authorization and gate support existed, but cleanup proof still depended on loose CLI strings and there was no browser runbook that forced the operator to clean only the probe item.
- Evidence: `summarize_run_status.py` emits `authorize_cleanup_probe` after sample verification; `merge_probe_evidence.py` previously accepted `--cleaned-candidates` strings without a structured evidence validator.
- Risk: an operator could clean a real business item, merge a count mismatch, use a cross-site backend URL, or report cleanup without frontend non-public proof.
- Rule: build `build_probe_cleanup_runbook.py` from sample-verified run evidence before cleanup. After the gated cleanup, validate `allincms_probe_cleanup_evidence` with base run evidence, then merge with `merge_probe_evidence.py --cleanup-evidence`.
- Follow-up: cleanup runbook, cleanup evidence validator, merge support, and regression tests now cover the cleanup stage.

## 2026-06-30 Batch Evidence Gate Findings

- Context: local-only helper maintenance for the posts/products batch upload stage.
- Symptom: the batch pre-mutation gate required `progressLog` and `frontendDetailAudit`, but there was no dedicated evidence validator tying the schema-verified manifest, base sample proof, progress entries, and redacted frontend audit together.
- Evidence: existing helpers could generate final audit inputs from a progress log, but no single validator rejected missing manifest slugs, cross-site backend/frontend URLs, missing `bodyVerified`, or frontend detail audit issues before later stages were unlocked.
- Risk: an operator could treat partial progress, HTTP 200 only, or a list-page check as proof that every uploaded product/post detail rendered correctly.
- Rule: after an authorized batch run, validate `allincms_batch_upload_publish_evidence` against the schema-verified manifest, base run evidence, complete progress log, and redacted frontend detail audit before unlocking forms/settings, final QA, or cleanup.
- Follow-up: added `build_batch_upload_publish_runbook.py`, `validate_batch_upload_publish_evidence.py`, and regression tests for complete evidence, missing slug progress, and frontend audit issues.

## 2026-06-30 Session Continuation Authorization Finding

- Context: user changed the operating instruction from per-action authorization prompts to "future needed operations, proceed directly; just give final result".
- Symptom: the previous authorization helper model would treat broad continuation wording as insufficient even when the next command also names an exact action target, causing the workflow to stall on stale authorization policy instead of proceeding with evidence gates.
- Evidence: the authorization validator rejected generic `continue`, but did not distinguish that from a current-session instruction paired with a concrete workspace target and content type.
- Risk: either extreme is unsafe: rejecting the instruction blocks the requested site-building run, while accepting a bare "continue" could authorize unrelated mutations.
- Rule: a current-session continuation instruction may be used as the authorization source only when the generated record still names the exact action, target URL, target type, expected result, verification plan, and cleanup boundary. Bare fuzzy words remain invalid.
- Follow-up: `make_authorization_record.py` now recognizes the explicit session-continuation phrase while preserving exact target checks; regression tests cover acceptance for an exact save target and continued rejection of generic `continue`.

## 2026-06-30 Product Detail Route Binding Finding

- Context: real product probe save and publish on an existing site, followed by frontend sample verification.
- Symptom: the backend product list showed the probe as `已发布`, and public `/products` returned 200, but `/products/{slug}` returned 404.
- Evidence: the routes table showed `/products` bound to the Products page while `/products/{product}` existed as a Product route with binding page `—` and status `未绑定`.
- Risk: batch upload could publish many products that appear correct in the backend and list page but all fail on detail URLs.
- Rule: sample verification for products/posts must include backend route binding proof for the detail route pattern. If `/products/{product}` or `/posts/{post}` is unbound, stop batch upload and perform a separate `bind_route` action with backend and frontend verification.
- Follow-up: `batch-verification.md` now names unbound detail route rows as a blocking sample-verification issue.

## 2026-06-30 Parallel Read-Only Agent Findings

- Context: planning future AllinCMS verification/exploration rounds where the user wants many fields, routes, or module interfaces checked one by one.
- Symptom: the broad instruction to use agents in parallel can speed up read-only checks, but it can also blur the boundary between independent verification and remote mutation.
- Evidence: AllinCMS workflows already separate read-only frontend/backend audits from gated create/save/publish/delete/upload/replay stages; product probe work showed that even a `创建` click may create a remote draft.
- Risk: delegating browser work without a strict scope can let multiple agents operate the same mutable tab, click a create button, or treat a subagent observation as final launch/upload proof.
- Rule: use parallel agents for independent read-only URL/file/evidence checks only. The controller must define allowed and forbidden actions, merge evidence, resolve conflicts, and keep every remote mutation single-stage under the normal authorization and pre-mutation gates.
- Follow-up: `SKILL.md` and `mutation-safety.md` now document split candidates, forbidden delegated actions, and controller reconciliation rules.

## 2026-06-30 Current-Session Authorization Wording Finding

- Context: continuing a long AllinCMS site-build run after the user gave a broad preference to perform later needed operations directly.
- Symptom: `mutation-safety.md` still had an older rule saying broad automation preference never replaces authorization for remote mutations, while `make_authorization_record.py` supports a stricter current-session path when the authorization record binds the exact action and target.
- Evidence: helper tests accept the session-continuation phrase only when paired with a concrete target URL and action record, and still reject bare `continue` / `继续` style wording.
- Risk: operators may either block useful staged execution after the user explicitly delegated the run, or over-accept vague continuation text without binding it to the next mutation.
- Rule: broad current-session preference can be used only through the authorization helper, with exact action, target URL, target type, target identifier, expected result, verification plan, and cleanup boundary. Bare continuation text, goal continuation, and helper-suggested text alone remain invalid.
- Follow-up: `mutation-safety.md` now distinguishes valid current-session paired records from invalid fuzzy continuation.

## 2026-06-30 Dynamic Child Page Create Evidence Finding

- Context: authorized `create_theme_page` browser stage for a Products parent page on an existing AllinCMS site.
- Symptom: the child-page dialog route field was a `param` route-mode selector plus a segment input, not a full route-path input.
- Evidence: filling name `Product Detail`, segment `{product}`, and a description submitted a `POST /{siteKey}/themes/{themeId}` Server Action with payload keys `path`, `routeMode`, `parentPath`, `siteId`, `themeId`, `name`, `description`, and `_status`; the resulting backend row showed `Product Detail /products/{product} Product` and a design URL containing `{pageId}`.
- Risk: filling `/products/{product}` into the segment field, or assuming row status `已发布` means the detail route is live, can create the wrong path or overclaim frontend readiness.
- Rule: for a Products child detail page, set route mode `param` and segment `{product}` so the payload path becomes `/products/{product}`. After creation, validate `allincms_theme_page_create_evidence`, then separately check routes; if `/products/{product}` remains `未绑定`, detail frontend verification and batch upload remain blocked.
- Follow-up: `create-flows.md` now documents the segment-field behavior and the post-create route-binding recheck.

## 2026-06-30 Fast Function Pass and Product Detail Enable Finding

- Context: fast-pass operation across an existing AllinCMS site after the user asked to quickly run through all page functions while recording what was done, returned, and blocked.
- Symptom: a generated fast backend scan used `sitesSnapshot + modules`, but `make_existing_site_evidence_from_scan.py` expected `scan.sites` and rejected it. A shell audit one-liner also failed because zsh treats `status` as a read-only variable. During the gated `enable_theme_page` action, clicking the hidden checkbox input did not toggle the Product Detail page; the visible `role=switch` labeled `启用 Product Detail` was the real control.
- Evidence: the fast pass inspected dashboard, products, posts, media, themes, routes, forms, site-info, domains, and tracking read-only. The authorized Product Detail enable action changed the switch label to `停用 Product Detail`, produced `页面启用状态已更新`, and re-reading routes showed `/products/{product}` bound to `Product Detail` with status `已绑定`.
- Risk: operators can lose time on incompatible scan converters, broken zsh snippets, hidden inputs, or stale probe URLs. They can also overclaim that route binding failed if they test an old slug instead of the current backend list slug.
- Rule: for fast-pass records, write a dedicated run record when the generic scan converter does not match the scan shape. Use `audit_code=$?` instead of `status=$?` in zsh snippets. For theme page enable, target the visible switch by accessible label, then verify the page row and route table. For frontend detail verification, read the actual list slug first; old or guessed probe detail URLs can remain 404 even when the correct detail URL now returns 200.
- Follow-up: `create-flows.md` now records the visible-switch enable behavior, automatic route binding after enable, and actual-list-slug verification rule.

## 2026-06-30 Product Detail Designer Insertion Finding

- Context: authorized `save_design` attempt on a Product Detail dynamic page whose public detail URL returned 200 but had no H1/images because the page canvas was empty.
- Symptom: the designer listed `Product Detail (Gallery)` under Products, but clicking the block list item did not insert it. Dragging the item to the canvas emitted a visible dropped-over-canvas message, and an AI prompt to improve the current page returned no visible change. In all cases, the canvas still said `No blocks yet` and `Save` stayed disabled.
- Evidence: the blocked attempt record shows three attempted paths: block click, drag to `canvas-drop`, and AI prompt. None produced a block, page document, enabled Save button, or save request. No Save or Publish click was performed.
- Risk: operators may mistake drag/drop accessibility status text or product-related text in the block library for a real page design, then overclaim product detail readiness or attempt to publish an empty page.
- Rule: designer block insertion is proven only when the block appears in the canvas or Layers panel and Save becomes enabled. If `No blocks yet` remains visible, stop the save/publish stage and either find the real Add Block trigger or build a validated `pageDocument` save path from a captured working page.
- Follow-up: `create-flows.md` now records this Product Detail insertion failure mode next to the manual block insertion proof requirements.

- Context: authorized `save_design` retry on the same Product Detail dynamic page after the failed click/drag/prompt insertion attempts.
- Symptom: selecting `Product Detail (Gallery)` still was not enough by itself; the real insertion happened only after the explicit `Add Block` button appeared and was clicked.
- Evidence: after `Add Block`, `No blocks yet` disappeared, Save became enabled, the Inspector showed `Product Detail (Gallery)`, and saving left Save disabled, Publish enabled, and the design status `Draft` without clicking Publish.
- Risk: an operator can waste time on drag/drop or overclaim readiness from block-library text, or accidentally publish immediately after a save changed a previously published design back to draft.
- Rule: for designer block insertion, require the explicit `Add Block` action plus post-insertion state proof. Treat save and publish as separate mutations: save may leave the page in Draft and must be followed by a separate `publish_design` stage with frontend verification.
- Follow-up: `create-flows.md` and `interface-inventory.md` now document the true Product Detail block insertion path.

## 2026-06-30 Fast Page Function Run Record Findings

- Context: user requested a fast practical pass across all AllinCMS site pages while preserving a record of what was done, what returned, what failed, and what should improve next.
- Symptom: ad hoc browser notes are too easy to lose across compaction, especially when read-only scans, gated mutations, and frontend audits are interleaved.
- Evidence: the temporary site run already produced separate files for read-only setup scans, dynamic page creation, page enabling, design save, routes rereads, and frontend audits; without a shared row format, later agents must re-open many artifacts before knowing the current module state.
- Risk: future operators may rerun mutating actions unnecessarily, skip unverified pages, or confuse read-only visibility with usable feature coverage.
- Rule: maintain a fast-pass module ledger with one row per page/module/action: module, backend URL, mode, action attempted, returned UI/API state, evidence pointer, mutation flag, current status, blocker, and next step. Use it for progress reporting; keep raw IDs and business copy in `/tmp` evidence, not in the skill package.
- Follow-up: use `interface-inventory.md` for durable module/action contract fields and `operational-findings.md` only for reusable platform lessons; store per-run ledgers as temporary redacted JSON or Markdown evidence.

## 2026-06-30 Cross-Content Preflight and Settings Page Findings

- Context: fast practical pass after products-specific evidence existed and the operator moved to posts, forms, media, site-info, tracking, and domains.
- Symptom: the pre-mutation gate correctly rejected `create_post_probe` when the preflight `contentInspection.contentType` was still `products`. After creating a posts-specific preflight, the first authorization record was rejected because it was older than the new preflight.
- Evidence: gate errors were `preflight.contentInspection.contentType must be posts` and `authorization: generatedAt must be at or after preflight.generatedAt`.
- Risk: reusing same-site evidence across content types can make a valid-looking gate target the wrong module; generating authorization before refreshing preflight can leave stale permission.
- Rule: regenerate content-type-specific read-only evidence before each posts/products/forms probe action, then regenerate the action authorization after that preflight. Do not reuse products preflight for posts or forms.
- Follow-up: apply this to future fast-pass probes and manifest schema work.

- Context: media, tracking, and settings-style pages during the same fast pass.
- Symptom: `make_existing_site_evidence_from_scan.py` requires non-empty table headers for the selected content type, but media and tracking pages are setup/grid pages with no table headers in the read-only scan.
- Evidence: attempts to build media/tracking preflight failed with `scan.modules.<module>.tableHeads or tableHeaders must not be empty`.
- Risk: operators might bypass local gates to upload media or add tracking tags, or incorrectly report these pages as unverified because they are not table-based.
- Historical rule at that time: module-specific proof was required and media/tracking actions stayed blocked or UI-first. **For media only, superseded on 2026-07-27 by exact-page runtime verification plus the canonical adapter; tracking remains governed separately.**
- Follow-up: `make_existing_site_evidence_from_scan.py` now accepts control/input proof for media, site-info, tracking, and domains; `create-flows.md` and `interface-inventory.md` document those field surfaces.

- Context: authorized media upload attempt with a generated non-private test image.
- Symptom: the in-app browser opened the upload dialog and revealed a hidden `input type=file`, but real file selection failed with `File uploads are not supported by Codex In-app Browser`. A Chrome fallback was checked, but no workspace Chrome tab/session was available in current open tabs, and the user accepted simulated clicking instead.
- Evidence: media page showed two `上传` buttons; dialog `上传媒体` showed `Choose File`, accepted PNG/JPG/GIF/WebP up to 5MB, and kept final `上传` disabled before file selection. No request, backend media row, or public URL was produced.
- Risk: an operator can accidentally report upload success after only opening the dialog, or use browser tooling limits as an excuse to skip media verification while still marking product images fixed.
- Rule: distinguish simulated upload-flow proof from real upload proof. Real media completion requires file selection, upload submit, request/storage capture, backend row, public URL, and cleanup plan. If browser upload is unsupported, record blocked/simulated evidence and keep product image verification incomplete.
- Follow-up: `create-flows.md`, `interface-inventory.md`, and `SKILL.md` now document browser file-upload limitations and the media-specific gate.

- Context: authorized form create behavior verification.
- Symptom: `创建表单` behaved like posts/products create: it directly created a draft and navigated to update instead of opening a harmless dialog.
- Evidence: update page showed `更新表单`, `Untitled Form`, timestamp-like slug, `草稿`, `更新` disabled, `发布` visible, and field-editor/preview controls with `0 个字段`.
- Risk: clicking form create for inspection creates cleanup debt and can be mistaken for a configured usable form.
- Rule: form create is a mutating create-only stage. Field editing, saving, publishing, public embedding/submission tests, and cleanup are separate stages.
- Follow-up: `create-flows.md` and `interface-inventory.md` now record form create behavior.

- Context: authorized same-value site-info save.
- Symptom: site-info uses simple fields plus an image picker; saving current values returned a success toast, while image upload was a separate untouched control.
- Evidence: fields were `name`, description textarea, and `notificationEmail`; save returned `站点信息已更新`.
- Risk: site-info save can be conflated with favicon/image upload or domain/tracking changes.
- Rule: keep site-info field save, image/file upload, tracking add, and domain add as separate actions and gates. Redact private values such as email and business description in reusable records.
- Follow-up: `create-flows.md` and `interface-inventory.md` now document the setting surfaces and separation.

## 2026-06-30 Fast QA Evidence Classification Findings

- Context: fast practical pass across backend modules and public frontend routes on an existing temporary site.
- Symptom: a frontend audit helper reported `fetch_failed` for the root route while a direct HTTP header check returned 200 for the same public origin. The same pass also mixed read-only page scans, simulated media upload dialog proof, and earlier gated mutations in nearby artifacts.
- Evidence: backend fast-pass records separately showed products/posts/forms/media/themes/routes/settings current state; frontend audit showed static routes and product detail status, but the root route needed independent HTTP confirmation. Media evidence explicitly had `remoteMutationsPerformed: false`.
- Risk: an operator could mark a usable route as failed because of one transient audit fetch error, or overclaim a simulated click/dialog path as real upload/persistence proof.
- Rule: when a fast QA audit emits a tool-level fetch error for one route, recheck that exact URL with a minimal independent HTTP or browser load before classifying launch failure. In fast-pass ledgers, every row must classify evidence as `read-only`, `authorized-mutation`, `simulated-click`, or `frontend-verification`; simulated-click rows must never satisfy upload, publish, media, or persistence gates.
- Follow-up: keep per-run fast-pass ledgers in `/tmp` with evidence pointers, and copy only this evidence-classification rule into the skill.

## 2026-06-30 Manifest Schema Depth Findings

- Context: local manifest readiness review after a real product save request was captured.
- Symptom: the generic manifest schema gate can be satisfied by setting `schemaVerified: true`, copying `fieldMapping`, and adding a `payloadTemplate`, even when the captured save request only proved `content` as an empty array and media upload remained simulated.
- Evidence: the save capture proved product update fields and backend persistence, but its `contentBlockShape` stated that the probe captured an empty content array. The media upload evidence stated `remoteMutationsPerformed: false`, with no backend media row or public URL.
- Risk: an operator could create a schema-verified manifest that passes local validation but still cannot safely upload rich product bodies or image/media fields.
- Rule: treat schema verification as depth-sensitive. `payloadTemplate` proves field names and request shape, not every nested value shape. Before batch upload, separately prove non-empty body block schema when body content is required, and prove real media/public URL behavior when cover or gallery media is required. Otherwise mark the manifest readiness blocked or record an explicit no-body/no-image acceptance rule for that batch.
- Follow-up: `batch-verification.md` now warns that payload templates are necessary but not sufficient for body/media batch readiness.

## 2026-06-30 Rich Editor Focus Findings

- Context: gated `save_probe` attempt to capture non-empty product body schema from an existing product probe.
- Symptom: the product edit page exposed a unique `div[contenteditable="true"][role="textbox"]`, but the in-app browser failed to click it with a coordinate translation error. No editor text changed, the `更新` button stayed disabled, and no save request was captured.
- Evidence: blocked attempt evidence showed editor text still at the placeholder, update disabled, and publish/unpublish state unchanged after the failed click.
- Risk: a passed save gate can be mistaken for browser edit success, or an operator may try to click save without proving the rich editor accepted content.
- Rule: for rich body schema capture, require a focus/type proof before save: unique editor locator, text changed, save/update enabled, then save request captured. If focus or typing fails, record blocked evidence and keep body schema readiness blocked.
- Follow-up: `request-capture.md` now adds a rich-editor focus proof checklist before save.

## 2026-06-30 Source Input Requirement Findings

- Context: user clarified that operation records should capture which fields need user/source material so future PDF, catalog, datasheet, or brief uploads can generate targeted AllinCMS fields.
- Symptom: backend field mapping and request capture alone do not say what source material is required, what can be inferred, and what must be confirmed by the user before generating products, posts, forms, media, or page copy.
- Evidence: the current temporary site has product fields partially captured, posts/forms UI-mapped only, media upload simulated only, and theme pages partially configured. A separate run record was needed to list required inputs such as product names, slugs, descriptions, body content, specs, images, contact details, and form fields.
- Risk: an operator may upload placeholder content, invent specs/contact details, or build a manifest from a PDF without knowing which fields are blocked by missing schema or missing user data.
- Rule: during site-building and content-upload runs, maintain a source-input requirements record before manifest generation. For each content type, classify fields as required/recommended/optional, map them to backend keys, name the source hint, state generation rules, mark current evidence strength, and list user decisions needed. Use this record to drive PDF/material extraction and keep missing inputs blocked instead of guessing.
- Follow-up: `field-contract.md` now includes a source-input requirements section.

- Context: operation-time recording while quickly exercising backend modules and preparing future PDF/catalog intake.
- Symptom: a generated source-input requirements file is a useful phase summary, but it does not capture every field gap at the moment it is discovered during browser operation.
- Evidence: fields can be discovered across separate pages and stages: site description from site creation, product specs from edit pages, media proof from upload dialogs, form fields from form editors, route/CTA decisions from theme pages, and contact fields from site-info/forms.
- Risk: waiting until the end of a long browser run can lose which field came from which module, whether it was UI-only or request-captured, and what exact user/source decision is needed before PDF/material extraction.
- Rule: keep an operation-time source-input gap ledger outside the skill package. Append one row per discovered field gap with content type, target, classification, source hint, generation rule, evidence strength, decision needed, and redacted evidence pointer. Use the ledger as run evidence for later manifest generation; do not store raw source copy or private values in the skill.
- Follow-up: `record_source_input_gap.py`, `SKILL.md`, and `field-contract.md` now define the append-only gap ledger flow.

## 2026-06-30 Resume-State Queue Drift Findings

- Context: read-only resume of an existing AllinCMS browser session after local queue and gap-audit artifacts were generated earlier in the day.
- Symptom: the local browser-stage queue still marked `create_product_probe` as the ready next action, but the live browser tab was already on a concrete product probe edit URL and the page showed a published probe state.
- Evidence: the claimed tab URL matched `/{siteKey}/products/{contentId}/update`; the backend page showed update controls, published status, a disabled update button, placeholder-only product body, and an unpublish control. A separate frontend audit showed the matching product detail route returned 200 with no images.
- Risk: an operator could trust stale local artifacts and create a duplicate probe, skip cleanup debt, or report the wrong next action.
- Rule: after resume, live browser state overrides stale local queue artifacts. If the claimed tab proves a queued mutation stage already happened, mark the queue stale, do not execute that stage, and rebuild the next action from fresh read-only evidence. Keep current-state proof in `/tmp` and record source-input gaps discovered during the read-only refresh.
- Follow-up: `SKILL.md` now requires comparing live tab state with any reused queue, summary, handoff, or gap audit before executing the next mutation stage.

- Context: local helper maintenance after the same resume-state check found an already-public probe but no complete requestCapture/sampleVerification chain in the current run evidence.
- Symptom: the standard cleanup runbook correctly requires merged sample proof, but that left no safe preparation path for legacy or resumed public probes discovered through fresh read-only browser state.
- Evidence: current read-only backend proof showed a concrete probe edit URL with published state and unpublish control; frontend audit showed the matching detail URL returned 200. Older queue artifacts still pointed at probe creation.
- Risk: operators may either create duplicate probes to fit the normal lifecycle, or skip cleanup preparation because the existing public probe lacks the exact lifecycle artifacts expected by the standard runbook.
- Rule: support a separate non-authorizing existing-probe cleanup handoff. It may be built only from current backend read-only evidence, frontend public-detail audit, a concrete edit URL, and current preflight. It must retain the authorization-source placeholder, forbid creating another probe or saving fields, and still require action-time cleanup authorization plus the normal `cleanup_probe` gate before browser mutation.
- Follow-up: `prepare_existing_probe_cleanup_handoff.py` now prepares this narrow recovery handoff while preserving the stricter standard cleanup runbook for lifecycle-complete probes.

- Context: local helper maintenance for the alternate next action after a resume found an existing probe edit page with placeholder-only body content.
- Symptom: the standard `prepare_probe_save_handoff.py` requires create-probe evidence, which is correct for a fresh lifecycle but not enough for a resumed session where the live edit page already exists and the current blocker is non-empty body schema capture.
- Evidence: read-only backend state showed a concrete product edit URL, one contenteditable body editor in placeholder-only state, update disabled before editing, and product fields visible. The source-input gap ledger already marked product body as blocked until schema capture.
- Risk: operators may recreate a probe to satisfy the create-to-save handoff, or attempt to save from chat instructions without a current preflight and action-time save/capture authorization.
- Rule: support a separate non-authorizing existing-probe save handoff. It may be built only from current backend read-only evidence, a concrete edit URL, and current preflight. It must retain the authorization-source placeholder, forbid publishing, upload, cleanup, and duplicate probe creation, and require the normal `save_probe` gate before saving once.
- Follow-up: `prepare_existing_probe_save_handoff.py` now prepares this narrow recovery handoff for non-empty editor/body schema capture from an already-open probe.

- Context: adapting the save-capture runbook after adding the existing-probe save handoff.
- Symptom: the original save runbook assumed the create-to-save path: rename the draft, set slug/description, and verify draft status. That does not fit a resumed existing probe whose name/slug already exist and whose immediate purpose is body/editor schema capture.
- Evidence: the generated existing-probe save handoff points at a concrete edit URL and says the body editor is placeholder-only; the runbook now emits one required field change for the body editor and keeps the item name/slug untouched.
- Risk: a resumed save-capture run could unnecessarily rewrite title/slug, depend on draft status even when the probe is already published, or widen the mutation beyond the body schema capture.
- Rule: `build_probe_save_runbook.py` must adapt to handoff kind. For `allincms_existing_probe_save_handoff`, it should require a unique body editor, type one non-business body sample, save once, capture request/payload shape, and forbid publish/upload/cleanup/duplicate probe creation. Do not rename existing probes in this path.
- Follow-up: `build_probe_save_runbook.py` now records `sourceHandoffKind` and `existingProbeResume`, and regression tests verify the existing-probe runbook uses the body editor only.

- Context: validating the existing-probe save runbook before browser execution.
- Symptom: the runbook validator originally validated only the create-to-save handoff kind, so the new existing-probe runbook could be well-formed but still rejected or left unclassified before browser execution.
- Evidence: current local validation of the existing-probe save runbook now reports `valid: true`, `status: blocked_missing_authorization`, `runbookValid: true`, `handoffValid: true`, `preflightExists: true`, and `authorization_record_missing`.
- Risk: without a validator state that distinguishes format problems from missing action-time authorization, an operator might either touch the browser too early or waste time rebuilding valid artifacts.
- Rule: pre-browser validators must support every handoff kind accepted by the runbook builder and classify missing authorization as a blocker, not a format error. Browser steps remain non-executable until the authorization record exists and `save_probe` gate passes.
- Follow-up: `validate_probe_save_runbook.py` now reuses the runbook builder's supported-handoff validation and regression tests cover existing-probe runbooks blocked on missing authorization.

- Context: local helper maintenance for the save-probe evidence bundle before another browser save attempt.
- Symptom: the first evidence-bundle helper generated a validation command that passed the save handoff JSON as `--base-run-evidence`, and the command pointed directly at the unfilled evidence template.
- Evidence: save-capture evidence validation binds against `siteIdentity.siteKey` and `contentInspection.contentType`, which exist in run/preflight evidence, not in the save handoff. The unfilled template also contains placeholders such as `passed|required_before_save`, `to_fill_after_capture`, and `{capturedContentBlocks}`.
- Risk: an operator could run a generated command that fails for the wrong reason, or worse, fill only booleans/status codes and accidentally treat placeholder payload/content shapes as captured evidence.
- Rule: save-capture evidence bundles must keep the template and filled evidence file separate. The validation command must target `save-capture-evidence.filled.json`, bind `--base-run-evidence` only to a real preflight/run-evidence path when available, and validators must reject unfilled capture placeholders.
- Follow-up: `prepare_probe_save_evidence_bundle.py`, `validate_probe_save_capture_evidence.py`, `SKILL.md`, and regression tests now enforce this split.

- Context: refining field-gap recording for future user-supplied PDFs, catalogs, websites, spreadsheets, and briefs.
- Symptom: recording only a field name and source hint is not enough to generate upload-ready content later; the operator also needs to know who supplies the value, how it is generated, what schema proof exists, and what blocks upload.
- Evidence: AllinCMS product/page/form runs can surface fields long before their request schema is captured: body editor, specs, media/gallery, forms, contact destinations, route paths, CTA target objects, prices, SKU, variants, and certifications.
- Risk: later PDF extraction could infer unsupported fields, invent missing values, or include blocked rich body/media/spec data in a live payload because the original browser-stage gap record was too thin.
- Rule: each source-input gap row is a field intake contract. Record provider (`source-derived`/`user-confirmed`), source signal, generation rule, schema proof strength, decision needed, and upload blocker. Unknowns should be explicit blockers or confirmation requests, not implicit omissions.
- Follow-up: `SKILL.md` and `field-contract.md` now state this four-part field intake requirement.

## 2026-06-30 Launch Acceptance Findings

- Context: goal continuation after a local full rehearsal passed from site creation through cleanup simulation.
- Symptom: local rehearsal produced many green safety artifacts, but the top-level completion concept still risked being narrower than the user's "from site creation to launchable website" goal.
- Evidence: the rehearsal covered 14 stages and final ledger exhaustion, while source-input requirements still had blocked fields and the single-run status summary focused on site identity, static rendering, request capture, sample verification, and cleanup. A read-only subagent also flagged that beautification, media/forms/settings, batch upload, and final launch QA needed one explicit acceptance layer.
- Risk: another operator could report completion after a sample/probe lifecycle or static launch proof while real batch content, theme beautification, media/form behavior, settings, final route audit, or cleanup remained incomplete.
- Rule: use a separate from-scratch launch acceptance checklist before claiming a website is complete. Require created-site proof, setup inspection, module capture, theme/page/route launch readiness, static audit, content save/sample proof, manifest schema gate, batch upload proof, in-scope media/forms/settings proof or explicit deferral, final frontend audit, cleanup, and sedimentation/read-only exception handling.
- Follow-up: `references/launch-acceptance.md`, `SKILL.md`, and `summarize_rehearsal_stage_coverage.py` now make local rehearsal coverage distinct from live launch completion.

- Context: converting a full local rehearsal into a concise operator record.
- Symptom: `rehearsal-summary.json` is too large for fast human review, and some important stage details live behind artifact paths such as `browserExecutionPlanPath` and `browserRunbookSummaryPath`.
- Evidence: the compact stage summary script initially found no full stage list until it reopened the plan artifact. After correction, it reports 14 stages, 9 authorization-required stages, source-input blocker count, final ledger exhaustion, and per-stage remote mutation expectations.
- Risk: operators may confuse summary-embedded fragments with complete evidence, or miss which stages require authorization and which are verification-only.
- Rule: after full rehearsal, generate a stage coverage summary. Treat it as status compression only; it does not prove live LAICMS mutations or public launch quality.
- Follow-up: `summarize_rehearsal_stage_coverage.py` now reads linked artifacts and outputs a compact 14-stage coverage record.

- Context: read-only validation and subagent review of the skill.
- Symptom: the skill's normal sedimentation rule could conflict with an explicit user instruction forbidding file edits.
- Evidence: a read-only subagent found reusable issues but correctly did not edit files; the previous rule had no explicit exception path.
- Risk: another Codex could violate a read-only instruction to satisfy skill closeout, or skip reporting reusable findings entirely.
- Rule: when the user explicitly forbids edits, report reusable findings as read-only deferred sedimentation in the final answer and record them later when edits are allowed before continuing mutable work.
- Follow-up: `SKILL.md` and `references/launch-acceptance.md` now document the read-only sedimentation exception.

## 2026-06-30 Source Intake Contract Hardening

- Context: local-only skill maintenance after the operator asked whether every field has explanations and whether potential problems are captured for future PDF/catalog/source uploads.
- Symptom: source-input requirements explained fields, but operation-time gap rows could still be appended with blank source hints, blank generation rules, or blank evidence pointers. The generated requirements also buried the risk and blocker inside free-text classification instead of exposing explicit fields.
- Evidence: `record_source_input_gap.py` validation allowed empty `sourceHint`, `generationRule`, and `evidencePointer`; `make_source_input_requirements.py` emitted classification and decision fields but no explicit `sourceOwner`, `potentialIssue`, or `uploadBlocker`.
- Risk: a later PDF/catalog extractor could treat an incomplete gap row as usable, invent specs/media/contact values, or send a field before schema/user confirmation is actually resolved.
- Rule: each field gap must be a complete source-intake contract. Require non-empty source hint, generation rule, and redacted evidence pointer; require an operator note when claiming UI/request/sample proof; and expose source owner, potential issue, and upload blocker in generated requirements.
- Follow-up: `record_source_input_gap.py`, `make_source_input_requirements.py`, `field-contract.md`, and regression tests now enforce this hardening.

## 2026-06-30 Launch Acceptance Gate Hardening

- Context: local-only skill maintenance while continuing the from-scratch site-building simulation toward a launchable website.
- Symptom: `launch-acceptance.md` defined the correct completion checklist, but there was no executable gate tying that checklist to real run evidence, module coverage, schema-gated upload readiness, batch proof, forms/media/settings proof or deferral, final frontend audit, cleanup evidence, and round closeout.
- Evidence: existing run summaries and local rehearsal validators can prove phase progress, static rendering, or stage sequencing, but they do not require batch upload, forms/media/settings, final frontend QA, or cleanup to be present before a launch-complete claim.
- Risk: an operator could report "能上线" after local rehearsal, a static audit, or one sample probe while real batch content, settings/form/media decisions, final route audit, or cleanup are still missing.
- Rule: before claiming from-scratch launch completion, run `validate_launch_acceptance.py` with `--require-created-site` and all real evidence artifacts. Stage coverage or rehearsal artifacts alone must fail; cleanup may be provided as separate evidence because cleanup has its own authorization boundary.
- Follow-up: `validate_launch_acceptance.py`, `SKILL.md`, `launch-acceptance.md`, and regression tests now enforce the executable launch acceptance gate.

## 2026-06-30 Read-Only Resume Evidence Findings

- Context: read-only browser refresh of an existing temporary AllinCMS site after prior local launch/rehearsal maintenance.
- Symptom: the live browser already had an existing product probe edit page open. The probe showed a public/unpublish-capable state, and frontend detail audit returned 200 with no images. The edit-page body editor was no longer `placeholder_only`, so the existing-probe save handoff's old precondition did not fit the current page.
- Evidence: backend read-only scan covered dashboard, products, posts, media, themes, routes, forms, site-info, tracking, and domains; run evidence validated as existing-site phase proof. Source-input requirements stayed blocked because no current save request, media proof, form schema, or theme/page payload schema was captured. A cleanup handoff could be prepared from current backend/frontend proof, while save handoff should not be forced against a non-placeholder body state.
- Risk: an operator could trust stale queues and create another probe, attempt a save-capture run with the wrong precondition, or leave a public probe/detail route in place while claiming launch progress.
- Rule: on resume, live browser state overrides stale queue stage assumptions. If an existing probe is already public, prepare cleanup first from current read-only backend state and frontend 200 proof. Only prepare existing-probe save capture when its validator preconditions match the page; otherwise refresh the handoff model or choose a new authorized stage.
- Follow-up: current run artifacts live under `/tmp/allincms-mysite03-*2026-06-30*`; no remote mutation was performed in this read-only refresh.

- Context: operation-time source-input gap recording during the same read-only refresh.
- Symptom: two local `record_source_input_gap.py` commands were run in parallel against the same ledger path. The resulting ledger remained intact in this run, but concurrent append/write to one JSON file is a race-prone pattern.
- Evidence: final ledger contained four entries and validated structurally by inspection, but both commands opened and rewrote the same `/tmp/...source-input-gap-ledger...json` file concurrently.
- Risk: future runs could lose a gap row or corrupt the ledger if two parallel writers target the same JSON file.
- Rule: source-input gap ledger appends must be serialized per output file. Parallel agents may discover fields independently, but the controller should merge their findings by running `record_source_input_gap.py` one row at a time or by writing per-agent ledgers and merging later.
- Follow-up: update helper or docs if this pattern recurs; for now, treat it as an operator rule in this findings file.

- Context: local preparation after the read-only refresh produced an existing public product probe cleanup handoff.
- Symptom: the standard cleanup runbook only accepts a full probe lifecycle run evidence with `sampleVerification`; it cannot directly consume the safer recovery handoff produced when a resumed browser session finds an already-public probe without the full lifecycle chain.
- Evidence: `build_probe_cleanup_runbook.py` requires `sampleVerification.backendUrl` or `requestCapture.url`, while the current recovery path had a valid `allincms_existing_probe_cleanup_handoff` from backend read-only state plus frontend 200 audit. Running the normal `cleanup_probe` gate without an authorization file failed as expected.
- Risk: operators may either recreate/publish a duplicate probe just to fit the standard lifecycle, or skip the runbook/evidence-template step before cleanup.
- Rule: when cleanup starts from an existing public probe handoff, build an existing-probe cleanup runbook that stays `browserStepsExecutable: false`, preserves the authorization placeholder, names forbidden neighboring actions, and proves the pre-mutation gate is still blocked until a current action-time cleanup authorization record exists.
- Follow-up: `build_existing_probe_cleanup_runbook.py`, `SKILL.md`, and regression tests now cover this recovery preparation path.

## 2026-06-30 Frontend Audit Timeout and Launch Blocker Findings

- Context: read-only frontend audit of an existing temporary site after theme/page/content probe work.
- Symptom: several frontend routes returned structural warnings or fetch failures: some 200 pages lacked an H1 and had zero images, `/posts` returned 404 when expected 200 in that audit, and several static routes hit `fetch_failed` under the audit timeout. The public product probe detail still returned 200 with no image.
- Evidence: the redacted audit report used per-route entries and issue codes such as `missing_h1`, `fetch_failed`, and `http_status`; no remote mutation was performed during this audit.
- Risk: an operator could treat any HTTP 200 or partial static route pass as launch completion while public pages are structurally incomplete, chunked reads fail, or probe detail content remains public.
- Rule: a frontend audit with `fetch_failed`, expected-status mismatch, missing required structure, no required images, or a public probe route is launch-blocking diagnostic evidence. Do not merge it as launch-ready proof; rerun with bounded `--timeout` and `--max-bytes`, then verify browser/backend/frontend state before claiming completion.
- Follow-up: `batch-verification.md` now documents `audit_frontend_rendering.py --timeout --max-bytes` and treats fetch failures as blockers.

- Context: local helper usage around the same frontend audit.
- Symptom: wrapper examples can fail in zsh if they assign to `status`, because `status` is a read-only special parameter.
- Evidence: zsh rejected status assignment during command result handling.
- Risk: audit or validation wrapper snippets can fail before preserving evidence, causing operators to rerun ad hoc or lose the actual failure state.
- Rule: do not use `status=$?` in zsh examples. Use `exit_code`, `cmd_status`, or shell `if command; then ... fi` forms.
- Follow-up: `batch-verification.md` now records the shell-variable rule.

## 2026-06-30 Source Requirements Gap-Ledger Merge Finding

- Context: local-only skill maintenance for future user-provided PDF/catalog/website/spreadsheet ingestion.
- Symptom: `make_source_input_requirements.py` generated a static field requirement record, while the operation-time gap ledger captured browser-discovered fields separately. Without an explicit merge, a later source extractor could miss fields discovered during the actual backend run.
- Evidence: source-gap rows can capture form destinations, route/CTA targets, product specs, media/gallery, rich body, prices, SKU, variants, certifications, and contact decisions before those fields are covered by static reusable sections.
- Risk: PDF/catalog extraction may generate only the static common fields and omit current-browser gaps, or include blocked fields without recognizing their schema/user-confirmation blocker.
- Rule: pass operation-time ledgers into `make_source_input_requirements.py --gap-ledger`. Treat the output `operationGaps` block as part of the extraction contract, and keep `operationGaps.blockedFields` out of live payloads until schema capture, user confirmation, or explicit omission/acceptance resolves them.
- Follow-up: `make_source_input_requirements.py`, `SKILL.md`, `field-contract.md`, and regression tests now cover gap-ledger merge behavior.

- Context: rerunning the from-scratch local full rehearsal after adding `--gap-ledger` support.
- Symptom: the standalone requirements helper could merge gap ledgers, but the full site-build rehearsal still produced `operationGaps.entryCount: 0`.
- Evidence: `/tmp/.../04-manifest-rehearsal/source-input-requirements.json` showed `operationGaps.sourceLedgers: []` even though the workflow goal requires operation records to drive future PDF/catalog field generation.
- Risk: a green full rehearsal could miss the exact source-intake behavior needed for future user uploads, leaving the feature tested only in a helper-level path.
- Rule: manifest rehearsal and full rehearsal must generate a neutral local `source-input-gap-ledger.json`, pass it into source-input requirements, and validate positive `operationGaps.entryCount`. The simulated ledger must stay local-only and contain no business copy, raw IDs, cookies, or real account data.
- Follow-up: `simulate_manifest_rehearsal.py`, `validate_manifest_rehearsal.py`, `validate_full_e2e_simulation.py`, `validate_full_rehearsal.py`, `SKILL.md`, `e2e-simulation.md`, and regression tests now enforce gap-ledger coverage inside the full rehearsal chain.

## 2026-06-30 Source Gap Ledger Validation Finding

- Context: skill maintenance after the operator clarified that browser operation should record which fields later user PDFs, catalogs, websites, spreadsheets, or briefs must provide.
- Symptom: single-row gap appends were validated, but an older, hand-merged, or per-agent merged ledger could still drift after creation: duplicate rows, stale summary counts, missing proof notes, or sensitive strings could enter before source extraction.
- Evidence: `make_source_input_requirements.py --gap-ledger` treats `operationGaps` as part of the extraction contract, so a bad ledger can directly influence which fields are generated, blocked, or sent to upload planning.
- Risk: later source processing could omit a discovered field, ask the wrong user question, invent unsupported values, or include blocked specs/media/form/CTA fields because ledger quality was assumed from the original append command.
- Rule: validate any reused or merged source-input gap ledger before generating source-input requirements. Use `record_source_input_gap.py --validate-only --output <ledger> --site-key <siteKey>`; the requirements builder should also reject invalid ledgers defensively.
- Follow-up: `record_source_input_gap.py`, `make_source_input_requirements.py`, `SKILL.md`, `field-contract.md`, and regression tests now enforce ledger-level validation.

## 2026-06-30 Read-Only Refresh Resume Findings

- Context: read-only browser refresh while continuing a from-scratch rehearsal objective against an already-created temporary site.
- Symptom: a claimed existing in-app browser user tab could navigate and read DOM, but reported `innerWidth: 0` and `innerHeight: 0`; clicking the visible `创建站点` button failed because its geometry was outside the usable viewport. A fresh controlled in-app tab to the same `/sites` URL had a normal viewport and completed the open/close dialog check.
- Evidence: the controlled tab verified `/sites`, opened and closed the create-site dialog, and scanned dashboard, products, posts, media, themes, routes, forms, site-info, tracking, and domains read-only under the same `{siteKey}`. No save, publish, delete, upload, or submit action was performed.
- Risk: an operator could misdiagnose viewport/click failure as LAICMS UI failure, retry brittle clicks, or accidentally submit a form while trying to recover.
- Rule: if a claimed user tab has a `0x0` viewport or impossible click geometry, switch to a fresh controlled tab for read-only evidence. Keep the original as a browser-control limitation and do not force clicks.

## 2026-06-30 Articles Block Save And Publish Boundary Findings

- Context: live Posts designer work on a temporary AllinCMS test site.
- Symptom: `Full News List (Filtered)` insertion only became trustworthy after a drag caused `No blocks yet` to disappear, the canvas selected the block, Inspector showed the block props, and Save became enabled. Saving persisted the design as Draft, disabled Save, and left Publish as a separate enabled action.
- Evidence: browser-visible designer state changed from empty canvas to a selected `Full News List (Filtered)` block; after `save_design`, the designer showed `Draft`, `Saved current changes`, disabled Save, and still exposed Publish.
- Risk: an operator can overclaim public posts readiness from a saved draft, or continue blind clicking when the top toolbar cannot be clicked by the browser surface.
- Rule: split Articles work into insertion proof, `save_design` proof, `publish_design` proof, and frontend DOM proof. If the browser reports impossible top-toolbar click geometry or a `0x0` viewport during publish, stop and recover with a fresh browser session or a freshly captured publish request contract; do not mark `/posts` launch-ready from saved-draft proof.
- Follow-up: `references/create-flows.md` now documents successful Articles drag insertion, saved-draft proof, and the separate publish boundary.

- Context: same Posts designer publish attempt through the in-app browser.
- Symptom: the top toolbar `Publish` button was uniquely present and enabled, but role clicks, coordinate clicks, CDP mouse events, and forced CSS locator clicks all failed with impossible hit-test geometry such as y=0 or "No element found at point"; keyboard Space reported success at the tool layer but left the designer in Draft.
- Evidence: post-attempt backend state still showed Draft and frontend `/posts` had zero visible body text.
- Risk: a tool-level click success or a unique enabled locator can be mistaken for a successful publish action.
- Rule: after any designer publish attempt, always re-read designer status and public frontend DOM. If status remains Draft or the frontend remains blank, treat the publish as not executed and switch to a fresh browser surface or captured publish Server Action contract before retrying.
- Follow-up: keep frontend launch acceptance blocked until `publish_design` and frontend DOM proof are both current.
- Follow-up: `SKILL.md` now documents this fallback.

- Context: applying a read-only refresh result to a local from-scratch browser execution ledger.
- Symptom: after the existing-site refresh stage completed, the static rehearsal ledger advanced to `create_site_submit` even though a real temporary site already exists.
- Evidence: the updated ledger reported `nextStageId: create_site_submit`, while current read-only evidence proved the existing site modules and fresh `/sites` dialog state.
- Risk: blindly following the local from-scratch ledger can create duplicate temporary sites or drift away from the user's current site-building work.
- Rule: after an existing-site refresh, stop before `create_site_submit` unless the user gives exact action-time create-site authorization. For continuation on the current site, branch or regenerate an existing-site execution ledger instead of treating the from-scratch static next stage as mandatory.
- Follow-up: `SKILL.md` now records the branch/stop rule; a future helper should make this branch explicit if it recurs.

## 2026-06-30 Existing-Site Continuation Planning Findings

- Context: branching a from-scratch browser execution ledger into existing-site continuation after current read-only evidence proved the temporary site already exists.
- Symptom: the branch helper correctly skipped `create_site_submit` and moved the next stage to `setup_pages_inspection`, then the setup stage could be completed from the same fresh read-only scan. The next packet became `module_interface_capture`, which is authorization-required and selected `products:create` / `create_product_probe` as the first concrete capture action.
- Evidence: the existing-site continuation ledger recorded `existingSiteContinuation.enabled: true`, `skippedStageId: create_site_submit`, and `nextStageId: setup_pages_inspection`; after applying setup proof, the next packet required `fresh authorization`, `captured request or explicit UI-only finding`, and `persistence or no-persistence proof`.
- Risk: without this branch, an operator either blocks unnecessarily at create-site or creates a duplicate site; without the next packet, an operator may treat aggregate module capture as permission to run many actions.
- Rule: for an already-created temporary site, branch the ledger with `branch_existing_site_ledger.py`, apply only read-only setup proof that is already fresh, then stop at the single selected module/action capture package. Do not execute module capture without action-time authorization and a pre-mutation gate.
- Follow-up: keep `branch_existing_site_ledger.py`, browser-stage packets, and module capture package validation in the existing-site continuation path.

- Context: building a completion gap audit from a validated `module_interface_capture` authorization package.
- Symptom: `prepare_browser_stage_authorization.py` produced a valid browser-stage authorization package for `create_product_probe`, but `make_browser_stage_queue.py` expects an `allincms_next_browser_action_handoff_readiness` artifact. There is no dedicated helper that converts a validated browser-stage authorization package into queue readiness.
- Evidence: a local readiness object had to be built from the validated package, fresh run summary, and preflight evidence before `make_browser_stage_queue.py` could generate the 10-stage queue and `make_e2e_gap_audit.py` could report `products_create_probe` as the only ready stage.
- Risk: future operators may hand-roll this bridge inconsistently, lose the authorization placeholder, or skip queue/gap-audit generation after package validation.
- Rule: treat a validated browser-stage authorization package as preparation only. If a queue/gap audit is needed, build or add a deterministic package-to-readiness helper instead of manually copying package fields.
- Follow-up: `make_browser_stage_authorization_readiness.py` now converts a validated browser-stage authorization package into queue-ready readiness and reruns package/preflight freshness checks before queue generation.

- Context: implementing the package-to-readiness bridge against an existing real-site authorization package.
- Symptom: valid browser-stage authorization packages do not always include a `remoteMutationsPerformed` field, because they are preparation artifacts and their validator relies on warning, placeholder, gate, target, and preflight checks.
- Evidence: the real `create_product_probe` package validated, but the first readiness helper draft blocked it because `remoteMutationsPerformed` was absent rather than `false`.
- Risk: an overly strict readiness bridge can block valid prepared packages and push operators back to hand-written readiness JSON.
- Rule: readiness output itself must set `remoteMutationsPerformed: false`, but the package input should be rejected only if it explicitly claims `remoteMutationsPerformed: true`; absence is acceptable after `validate_browser_stage_authorization_package.py` passes.
- Follow-up: regression tests cover fresh package readiness, stale preflight blocking, and real package-to-queue generation.

## 2026-06-30 Local Full Rehearsal Validator Findings

- Context: rerunning the full local-only from-scratch rehearsal with a custom simulated site key.
- Symptom: `run_full_rehearsal.py` accepted `--simulated-created-site-key simleddemo1`, but `validate_capture_handoff.py` only recognized fixed simulation keys and rejected the handoff because it did not see the custom simulated target preserved for audit.
- Evidence: the module capture plan contained `https://workspace.laicms.com/simleddemo1/products`, while the handoff safety check expected a preserved simulated target and templated `{realSiteKey}` authorization text. After updating the validator, the full rehearsal, standalone rehearsal validator, and browser runbook validator all passed.
- Risk: operators may either avoid realistic simulation names or weaken handoff validation; either path can hide whether a local-only target is safely templated before real browser work.
- Rule: validators must allow any concrete `workspace.laicms.com/{simulatedSiteKey}/...` target to remain in `simulatedTarget` for audit, while still requiring user-facing target and authorization text to use `{realSiteKey}` and suppress command output for local-only handoffs.
- Follow-up: `validate_capture_handoff.py` and regression tests now cover custom simulated targets.

- Context: running Python compile checks in the managed workspace sandbox.
- Symptom: `python3 -m py_compile ...` tried to write bytecode into `~/Library/Caches/com.apple.python/...` and failed with `PermissionError` even though the source compiled under a writable cache prefix.
- Evidence: rerunning with `PYTHONPYCACHEPREFIX=/tmp/allincms-pycache` completed successfully.
- Risk: a sandbox bytecode-cache write failure can be mistaken for a code syntax failure or cause operators to skip compilation.
- Rule: in restricted sandboxes, run py_compile with `PYTHONPYCACHEPREFIX=/tmp/allincms-pycache` or another writable temporary cache.
- Follow-up: `SKILL.md` now documents the sandbox-safe compile command.

## 2026-06-30 Test-Site Session Policy and Demo Product Findings

- Context: mutating browser work on a user-designated temporary AllinCMS test site after the user instructed the operator to create, save, publish, and clean around the launch goal without repeated precise prompts.
- Symptom: the normal `create_product_probe` pre-mutation gate rejected a legitimate demo product creation because `authorization.targetIdentifier` did not include `Codex Probe - Delete Me`.
- Evidence: the local record named the current site, products URL, demo product target, expected result, verification plan, and cleanup boundary, but the gate remained probe-only. The UI create action sent `POST /{siteKey}/products` and navigated to `/{siteKey}/products/{productId}/update`; the later save and publish actions posted to that edit URL with `mode: "update"` and `mode: "publish"`.
- Risk: an operator can either block useful test-site buildout because the helper only supports probe names, or weaken probe safety too broadly and accidentally create/delete real content.

## 2026-07-01 Live Product Probe Save Findings

- Context: real in-app browser product probe lifecycle on a temporary AllinCMS build site, from products list through create draft, save request capture, and backend list persistence verification.
- Symptom: after saving the probe with slug `codex-probe-delete-me-product`, the publish runbook helper still predicted the frontend detail URL as `/products/codex-probe-product-delete-me`.
- Evidence: the captured save request posted to `/{siteKey}/products/{contentId}/update` with payload keys `name`, `slug`, `description`, `order`, `media`, `mediaList`, `content`, `categories`, `tags`, `specifications`, `siteId`, `productId`, and `mode`; the backend list then showed `Codex Probe - Delete Me`, slug `codex-probe-delete-me-product`, and status `草稿`.
- Risk: a later publish/sample verification can audit the wrong frontend URL, incorrectly report a 404, or merge sample evidence that does not match the slug actually saved during request capture.
- Rule: publish/sample runbooks must derive or accept the saved slug from current request/backend evidence when possible. Until that helper is expanded, keep its default probe slug aligned with the save runbook and actual probe input: products use `codex-probe-delete-me-product`, posts use `codex-probe-delete-me-post`.
- Follow-up: `build_probe_publish_runbook.py` and its regression tests now use the same default probe slug order as the save stage.

- Context: local summary rerun after request-capture evidence merge.
- Symptom: ad hoc zsh commands using `status=$?` failed with `read-only variable: status`, preventing the intended summary and validation command from running.
- Evidence: the shell returned `zsh:1: read-only variable: status`; rerunning with `rc=$?` worked and produced the expected phase summary.
- Risk: a command-wrapper failure can be mistaken for AllinCMS evidence failure or hide the real validator output.
- Rule: avoid `status` as a shell variable in zsh command snippets. Use `rc`, `exit_code`, or another non-reserved name when preserving command exit codes.
- Follow-up: use `rc=$?` in future validation snippets.

- Context: cleanup stage in the same live product probe lifecycle.
- Symptom: clicking `取消发布` on a published product probe returned the backend row to `草稿`, but the public detail URL still rendered the probe with HTTP 200 and visible title/body.
- Evidence: backend list showed the probe as `草稿`; a refreshed frontend detail check and frontend audit still returned `/products/{slug}` status 200 with the probe content. Deleting the probe from the row-scoped menu then removed it from the backend list, and the frontend URL returned a 404 page with no probe title/body.
- Risk: operators can overclaim cleanup completion from backend draft status alone, leaving public probe/test content visible.
- Rule: for product probe cleanup, unpublish is not sufficient unless frontend non-public proof also passes. If the frontend still renders after unpublish, continue within the cleanup authorization to delete the exact probe row after confirmation text names `Codex Probe - Delete Me`, then verify backend absence and frontend 404/no-probe DOM.
- Follow-up: future cleanup evidence should record failed unpublish-only attempts as partial, not completed cleanup proof.

- Context: launch acceptance diagnostic after merging the same live product probe save, publish-sample, and cleanup evidence.
- Symptom: specialized evidence validators accepted the save/sample/cleanup artifacts, but the top-level launch acceptance gate initially rejected the merged run evidence because `merge_probe_evidence.py` stores `requestCapture.payloadShape` as a redacted JSON string, `sampleVerification.renderAudit` as a string, and published status as Chinese `已发布`.
- Evidence: `validate_probe_save_capture_evidence.py`, `validate_probe_publish_sample_evidence.py`, and `validate_probe_cleanup_evidence.py` all passed. The launch gate then blocked with `payloadShape must be a non-empty object`, `status must be published`, and `renderAudit missing` until its acceptance adapter was updated.
- Risk: operators can misread a launch diagnostic as proof that the browser probe failed, when the underlying phase evidence is valid and only the aggregate gate is too narrow for its own merge helper output.
- Rule: top-level launch acceptance must accept the redacted shapes produced by first-party merge helpers when the specialized validators pass: non-empty `payloadShape` object or parseable/non-empty redacted shape string, `status` `published` or `已发布`, and non-empty string or object `renderAudit`.
- Follow-up: `validate_launch_acceptance.py` and regression tests now accept merged probe evidence shapes while still requiring non-empty proof.
- Rule: distinguish `probe` content from legitimate `demo/test-site launch content`. A current-session test-site policy may remove repeated user prompts only when each mutation still has an exact action record, unique UI target, backend/frontend verification, and cleanup or keep boundary. Keep probe cleanup naming strict, but record helper gate coverage gaps when demo content creation is in scope.
- Follow-up: `SKILL.md`, `mutation-safety.md`, and `create-flows.md` now describe current-session test-site policy plus exact action records.

- Context: saving a real demo product through the product edit UI.
- Symptom: clicking the visible product body placeholder and typing did not insert into the rich body editor; the `contenteditable` text stayed as the placeholder while the typed body text was appended to the description textarea.
- Evidence: the saved product request payload contained `content: []`, `media: null`, and a non-empty `description`; the frontend detail rendered the name and description but no image or rich body block.
- Risk: an operator may think body/schema capture succeeded while the payload proves only description save. Batch upload would then omit product body blocks or mis-map rich text into the wrong field.
- Rule: after typing into rich editors, inspect both the visible editor text and the captured payload. Do not claim non-empty product body schema until `content` contains real blocks and the frontend detail renders body content. If body remains empty, explicitly classify the product as description-only and keep body/media schema gates blocked.
- Follow-up: `create-flows.md` now records the editor focus failure mode next to product create/save behavior.

- Context: cleanup of old public probe residue before continuing demo launch work.
- Symptom: a previously published `Codex Probe - Delete Me ...` product still existed in the product list and frontend detail route after later work had moved on.
- Evidence: scoped deletion used the unique probe slug row menu, a confirmation dialog that named the probe title, backend list empty-state proof, and frontend old detail route rendering a 404 with no probe text.
- Risk: stale public probes can make frontend verification look like real content exists, pollute launch QA, or be mistaken for batch output.
- Rule: on resume, explicitly search backend lists for `Codex Probe`, `Untitled`, and prior test slugs. Clean only unique test/probe rows, then verify both backend absence and frontend non-public state before creating new demo or batch content.
- Follow-up: keep cleanup evidence in run artifacts; do not store concrete object ids or private account details in the skill.

## 2026-06-30 Product Body Save and Browser Verification Findings

- Context: mutating product edit work on a user-designated temporary test site, scoped to an existing demo product.
- Symptom: after the product rich body was correctly filled, the visible `更新` button became enabled but appeared at impossible coordinates in the in-app browser (`y < 0`) until a normal desktop viewport override was applied. Locator and coordinate clicks failed before the viewport fix, even though the page state was valid.
- Evidence: the rich editor text was present in `div[contenteditable="true"][role="textbox"]`; after setting a normal viewport, the `更新` button returned to a visible coordinate, the save POST succeeded, and the backend showed `保存成功`.
- Risk: an operator can misdiagnose browser geometry failure as LAICMS save failure, refresh the page, and lose unsaved editor content.
- Rule: when a sticky action bar has impossible click geometry, first preserve current editor state, then reset or set a normal viewport and re-check button rectangles before clicking. Do not refresh an unsaved edit page just to recover clickability.
- Follow-up: keep viewport overrides temporary and reset before final browser handoff when no longer needed.

- Context: saving and publishing a non-probe demo product body.
- Symptom: the product save helper/gate coverage is still probe-oriented; legitimate demo product `save` and `publish` actions needed exact local action records under the current-session test-site policy, but no `save_product` / `publish_product` helper action existed.
- Evidence: save and publish both posted to `/{siteKey}/products/{contentId}/update`; save used `mode: "update"` and changed the product to draft, while publish used `mode: "publish"` and returned to the list with published status. Public HTML then contained the Slate body text and list markup.
- Risk: using `save_probe` for demo content weakens probe naming boundaries, while blocking all non-probe saves prevents practical temporary-site buildout.
- Rule: keep probe gates strict, but add or use separate demo/content save-publish records for test-site launch content. Do not mark batch upload safe until the helper coverage or run evidence distinguishes normal content save/publish from probe save/publish.
- Follow-up: future helper coverage should add content-type-specific non-probe actions such as `save_product`, `publish_product`, `save_post`, and `publish_post`. Status update: this follow-up is now closed by the 2026-07-03 Existing Content Gate Closure Finding below; use those dedicated actions for single-row product/post save and publish.

- Context: frontend verification after product publish.
- Symptom: browser tab navigation to the public product detail timed out, but direct public HTML fetch returned HTTP 200 and contained the expected body. The timeout was a browser-control/navigation wait issue, not proof of frontend failure.
- Evidence: the downloaded HTML contained the product title, `Key features`, `Applications`, Slate data attributes, and `<ul>` markup; it also had zero `<img>` tags and an image-off placeholder.
- Risk: relying on a single browser navigation timeout can hide successful public rendering or cause unnecessary retries. Conversely, HTTP 200 alone could miss missing media.
- Rule: for public verification, combine browser DOM when available with bounded HTTP/HTML checks. Treat successful body rendering and missing media separately: body proof can pass while media remains a launch blocker.
- Follow-up: product final QA should still require real media proof or an explicit no-image acceptance rule.

## 2026-07-01 Posts Publish And Post Detail Block Findings

- Context: authorized `publish_design` continuation on a temporary test site's static Posts theme page after `save_design` had already persisted an Articles list block.
- Symptom: a previously claimed in-app tab exposed a `0x0` viewport and impossible top-toolbar click geometry, but opening a fresh visible in-app tab to the same backend URL restored a normal viewport and made the designer toolbar clickable.
- Evidence: the fresh tab showed the Posts designer as `Draft`, `Save` disabled, and `Publish` enabled; after one toolbar click the designer showed `Published`, `Publish` disabled, and the theme page list re-read showed the Posts row as `已发布`.
- Risk: repeated clicks in a stale `0x0` browser surface can look like LAICMS failure and can leave a saved page in Draft indefinitely.
- Rule: when a logged-in in-app tab has `innerWidth/innerHeight` of zero or toolbar hit tests land at y=0, open a fresh visible in-app tab to the exact backend URL before retrying. Keep the first tab failure as browser-control evidence, then re-read backend state and frontend DOM after the action.
- Follow-up: `create-flows.md` now records the fresh-visible-tab recovery path for designer publish.

- Context: frontend verification immediately after the static Posts page was published.
- Symptom: `/posts` changed from an empty 200 page to a visible list page, but the rendered structure still had no H1 or images.
- Evidence: public `/posts` rendered list text, one article title, excerpt, and three links to `/posts/{post}`, while the audit still reported `h1: 0` and `img: 0`.
- Risk: operators may treat "non-empty list route" as launch-ready proof even though the page still has SEO and media gaps.
- Rule: split Posts verification into public render proof and launch-quality proof. A non-empty Articles list unlocks detail-page follow-up, but launch acceptance still needs H1/heading policy, image/media handling or an explicit no-image acceptance, and final route audit.
- Follow-up: `batch-verification.md` now distinguishes non-empty Posts list proof from launch acceptance.

- Context: authorized `save_design` attempt on the dynamic Post Detail theme page for `/posts/{post}`.
- Symptom: the designer page was `Published` but still showed `No blocks yet`, with both `Save` and `Publish` disabled. Clicking, selecting, and three drag/drop paths for `Post Detail (Article)` only emitted status text such as `Draggable item library-block-post-detail-article was dropped over droppable target canvas-drop`; `No blocks yet` remained and Save stayed disabled.
- Evidence: the public `/posts/{post}` route returned HTTP 200 and the correct HTML title, but browser DOM body was empty with zero headings, paragraphs, images, and links. The backend designer remained empty after each insertion attempt.
- Risk: a successful drag/drop announcement can be mistaken for block insertion, leading to saving or publishing an empty detail page, or to unsafe synthesis of a `pageDocument` without a captured block schema.
- Rule: for `Post Detail (Article)`, treat click, selection, and drag/drop announcements as interaction telemetry only. Do not run `save_design` unless `No blocks yet` disappears, the block appears in canvas or Layers, and Save becomes enabled. If UI insertion fails repeatedly and no captured `pageDocument` contract exists for that block, stop and keep the detail route blocked instead of inventing a payload.
- Follow-up: `create-flows.md` now names the Post Detail (Article) failure mode explicitly.

- Context: local preparation for a `publish_design` continuation on an existing temporary site.
- Symptom: `make_existing_site_readonly_evidence.py` and the scan converter still require create-site dialog fields such as `name`, `description`, and `Close` even when the current mutation is a publish-only theme-page continuation and the operator has not opened the create-site dialog in the current browser stage.
- Evidence: the helper rejected honest publish-only evidence with errors requiring `--dialog-closed-verified`, cleanup candidates, and observed create-site fields including `name`.
- Risk: operators may be tempted to fabricate create-dialog proof just to pass the pre-mutation gate, or they may interrupt an in-progress designer stage to open `/sites` only for an unrelated helper requirement.
- Rule: do not fake create-site preflight data. For existing-site continuation, prove the selected site with current site keys, strong site-key evidence, selected dashboard evidence, backend module routes, setup-page evidence, and target content inspection. Create-site dialog fields are optional context for existing-site evidence and must not be fabricated.
- Follow-up: `make_existing_site_readonly_evidence.py`, `make_existing_site_evidence_from_scan.py`, and `validate_run_evidence.py` now allow `existing_site_selected` evidence without create-dialog fields while keeping create-site preflight dialog requirements separate.

## 2026-07-02 Existing-Site Continuation Preflight Finding

- Context: source-file or browser continuation where the target site already exists and the next step is content/schema/theme work, not creating a new site.
- Symptom: existing-site read-only evidence generation and validation reused create-site preflight requirements, forcing `createSiteFields` with name/description/submit/close even when the operator had only refreshed the selected site's dashboard/modules.
- Evidence: existing-site evidence now carries `siteCreation.siteKeyEvidence` and `siteCreation.selectedSiteEvidence`. `createSiteFields` and `dialogClosedVerified` are optional for `existing_site_selected`, but still required for `create_preflight_verified` and created-site paths. The scan converter accepts module scans without `sites.createDialog` for existing-site continuation. Regression tests cover scan conversion without create dialog, validator acceptance, content-type preflight merge, and schema-capture handoff.
- Risk: fake create-dialog data can unlock the wrong mental model and blur the boundary between selecting an existing site and authorizing a new-site mutation.
- Rule: treat existing-site continuation and create-site mutation preflight as separate evidence types. Existing-site evidence proves the selected site and current module state; create-site preflight proves the `/sites` create dialog and must be derived separately before any new-site submit.

- Context: recovery after direct UI insertion failed for a dynamic Post Detail theme page.
- Symptom: a focused Copilot prompt to insert the exact `Post Detail (Article)` block succeeded where click and drag/drop attempts had failed, but the change appeared as a staged `Draft` with `Save` disabled and `Publish` enabled.
- Evidence: `No blocks yet` disappeared, the canvas rendered the current post preview, the Inspector showed `Post Detail (Article)`, and publishing the top toolbar button changed the designer to `Published`; public `/posts/{slug}` then rendered visible title, excerpt, and body DOM.
- Risk: operators can dismiss Copilot entirely because prior list-page prompts failed, or they can overtrust Copilot narration without checking canvas state. They can also wait for Save to enable even though this insertion path already staged a Draft requiring only publish.
- Rule: Copilot is an acceptable recovery path only when it produces concrete designer state: block visible in canvas or Layers, matching Inspector heading, Draft/Publish state, and later frontend DOM proof. Treat narration alone as non-proof. If Save remains disabled but the page status becomes Draft and Publish is enabled, proceed through `publish_design` rather than trying to save an already staged change.
- Follow-up: `references/create-flows.md` now documents this recovery path and the separate publish boundary.

- Context: publishing a designer page after Copilot inserted a block.
- Symptom: the designer DOM contained two `Publish` buttons, so `getByRole('button', {name: 'Publish'})` was not unique and the first publish attempt skipped the click.
- Evidence: a targeted toolbar coordinate click against the visible enabled top button changed the page from `Draft` to `Published`, disabled Publish, and frontend detail DOM changed from empty to non-empty.
- Risk: role-locator ambiguity can silently leave a page in Draft if the automation chooses not to click or clicks the wrong Publish control.
- Rule: when a designer has multiple same-name action buttons, identify the intended top toolbar control by visible rectangle and post-action state, not by global role name alone. Always verify designer status and public frontend DOM after the click.
- Follow-up: `references/create-flows.md` now warns about duplicate Publish buttons.

- Context: final route audit after posts/detail publish.
- Symptom: the CLI frontend auditor reported `fetch_failed` for a static route, but a live browser check of the same route rendered normal visible DOM with H1 and image content.
- Evidence: the audit report flagged the route with `fetch_failed`; browser verification then showed body text, H1, and image count for the same public URL.
- Risk: a transient fetch/read timeout can be mistaken for a broken public page, or a browser-only check can hide audit-tool instability that should be rerun before release.
- Rule: treat `fetch_failed` as a launch blocker until resolved by rerun or browser proof. If browser proof passes, record a split result and keep final acceptance pending a clean audit or explicit acceptance of the audit-tool limitation.
- Follow-up: `references/batch-verification.md` now documents browser recheck for CLI `fetch_failed` routes.

## 2026-07-01 Posts List H1 And Designer Geometry Findings

- Context: read-only inspection plus one scoped `save_design` preparation for improving a temporary site's static Posts list page.
- Symptom: selecting the `Full News List (Filtered)` block exposed Inspector props for action label, image display, detail page, page size, toolbar, sort, and columns, but no title, heading, H1, or intro text field.
- Evidence: the public `/posts` page rendered article list text and links, while browser DOM showed zero H1 and zero images. The selected list block's props did not include a heading field, and `Save`/`Publish` remained disabled.
- Risk: operators may keep editing list-block props expecting a page H1 to appear, or may claim a list page is launch-ready because content is non-empty.
- Rule: treat Posts list H1/intro as a separate page-design concern unless the current block's Inspector exposes a real heading prop. If the list block has no heading prop, add a separate hero/heading block through a proven insertion path, or record an explicit no-H1 acceptance for temporary demos.
- Follow-up: `create-flows.md` and `batch-verification.md` now distinguish list block configuration from page heading proof.

- Context: attempting to browse block categories and submit a designer prompt in the in-app browser after selecting a Posts list block.
- Symptom: elements in the designer moved to negative coordinates or reported impossible hit targets; Playwright text clicks for `Heroes` resolved to y=0, coordinate clicks reported no element, and the Copilot textarea became a huge offscreen rectangle. Keyboard submission left the prompt text visible but did not modify the canvas or enable Save.
- Evidence: after the prompt attempt, `Save` and `Publish` were still disabled, the body still showed the original `Full News List (Filtered)` state, and no frontend H1 appeared on `/posts`.
- Risk: browser geometry or prompt submission artifacts can be mistaken for a saved designer change, especially when the prompt text remains visible in the designer UI.
- Rule: do not save or publish after designer prompt attempts unless there is concrete changed-canvas proof: a new block in canvas or Layers, matching Inspector heading, Save enabled or Draft/Publish state changed, and later public DOM proof. If controls shift to negative coordinates, recover the viewport/fresh tab before further clicks.
- Follow-up: keep prompt text and drag/drop status as telemetry only; they are not pageDocument proof.

- Context: generating pre-mutation evidence for Posts design work.
- Symptom: local frontend route-pattern validation accepts public audit patterns such as `/posts/{slug}`, while the designer Inspector's Detail Page prop displays `/posts/{post}`.
- Evidence: a preflight using `/posts/{post}` in `frontend_route_patterns` failed validation, while the same current-site evidence passed after switching the public audit pattern to `/posts/{slug}` and retaining `/posts/{post}` only as designer-prop evidence.
- Risk: operators may either weaken validators or lose useful designer-route evidence by forcing all route strings into one vocabulary.
- Rule: distinguish internal designer route parameters from public frontend audit patterns. Use `/posts/{post}` or `/products/{product}` when recording designer props, but normalize public audit and launch-check route patterns to `/posts/{slug}` and `/products/{slug}` where the helper requires them.
- Follow-up: future helpers should support an explicit `internalRoutePattern` versus `publicRoutePattern` pair.

## 2026-07-01 Content Media URL Binding Findings

- Context: temporary test-site launch QA after product and post detail pages rendered body text but still had zero images.
- Symptom: the media library page was empty, while existing product/post edit pages exposed image controls with a picker that had `媒体库`, `上传`, and `URL` tabs. The URL tab accepted a public image URL, rendered a preview, and enabled `确认`.
- Evidence: product `主图/视频` and post `封面图` both accepted the same public image URL. Confirming the picker inserted an edit-page preview and enabled `更新`; saving posted to the existing product/post update URL with HTTP 200. Each save changed the item from published to draft, requiring a separate `发布` POST before public pages updated. After publish, `/products/{slug}`, `/posts`, and `/posts/{slug}` all rendered one public image with non-zero natural dimensions.
- Risk: operators may over-block media work because the media library is empty or file upload is unavailable, or may overclaim from the edit-page preview without saving/publishing and checking the public frontend. They may also try to force this through the existing `upload_media` gate even though that gate is media-library/file-upload oriented and requires `uploadFile` plus `mediaId`.
- Rule: treat edit-page URL media binding as a content save/publish workflow. It can provide valid media proof when the public URL preview, content save request, backend status, republish step, and frontend list/detail `<img>` DOM are all verified. Keep media-library upload proof separate from content URL binding proof.
- Follow-up: `create-flows.md` and `batch-verification.md` now document URL media binding. Future helper coverage should add a dedicated content media URL action, or content-specific non-probe `save_product`, `publish_product`, `save_post`, and `publish_post` gates that can include media URL fields.

## 2026-07-01 Product Probe Cleanup And Batch Evidence Findings

- Context: authorized product probe cleanup on a temporary test site.
- Symptom: the first delete confirmation click returned a stale React read where the dialog and probe row still appeared, but the next visible DOM read and a backend reload proved the probe row was gone. The frontend probe detail URL then rendered a public 404 with no probe title or body.
- Evidence: the delete alert dialog explicitly named `Codex Probe - Delete Me`; after reload the products list contained only non-probe product rows, and `/products/{probe-slug}` showed a 404 page.
- Risk: reading immediately after a destructive click can produce stale dialog/list state and trigger unnecessary repeat deletion attempts. A global row-menu locator can also target the wrong product when multiple rows expose `打开菜单`.
- Rule: scope delete actions to the row containing the probe title, require the confirmation dialog to name that probe, then verify cleanup by backend reload plus frontend non-public route. If the first post-click read still shows the old row, re-read/reload before clicking delete again.
- Follow-up: keep cleanup evidence as structured JSON; include `status: completed` for launch acceptance even though `validate_probe_cleanup_evidence.py` validates the core proof without that field.

- Context: merging structured cleanup proof into run evidence.
- Symptom: `merge_probe_evidence.py --cleanup-evidence` initially failed when the cleanup candidate `reason` contained commas because the merge path converted structured candidates into a comma-delimited string and parsed it back.
- Evidence: the cleanup validator passed, but merge failed with `cleanup candidate 1 must use contentType|titlePattern|backendUrl|reason`; after changing the structured JSON path to preserve the `cleanedCandidates` array directly, the same evidence merged and validation passed.
- Risk: evidence that is valid as JSON can fail or be corrupted when serialized through ad hoc delimiter formats. Operators may work around it by weakening reasons instead of fixing the helper.
- Rule: structured evidence inputs must stay structured through helper pipelines. Delimited CLI strings are legacy/manual input only and should not be used internally for JSON evidence.
- Follow-up: `merge_probe_evidence.py` now uses `cleanedCandidates` directly for `--cleanup-evidence`, with a regression test for comma-containing reasons.

- Context: preparing a real `batch_upload` gate after a schema-verified product manifest and sample proof existed.
- Symptom: `validate_run_evidence.py` and `check_pre_mutation_gate.py` rejected structured request/sample proof because `headers`, `payloadShape`, `contentBlockShape`, `idFields`, and `renderAudit` were objects or arrays, while the upload-scope validators expected strings.
- Evidence: the same run evidence passed before upload scope, but setting `mode: batch_upload` exposed type errors such as `requestCapture.payloadShape must be present`; after accepting non-empty string/object/list evidence values, the batch gate passed.
- Risk: helpers can block valid rich evidence or encourage flattening payload schemas into lossy strings. This weakens later field mapping and batch upload checks.
- Rule: request capture and sample verification fields may be structured evidence. Validators should require non-empty evidence values, not force every proof field into a string.
- Follow-up: upload-scope validators now accept non-empty strings, objects, and arrays for those evidence fields while preserving URL/method-specific checks.

- Context: real product batch proof after product save schema capture.
- Symptom: a batch evidence file initially failed because its manifest still listed the earlier demo product slug, while the browser-created batch item used a new slug. After aligning the schema-verified manifest to the actual batch item, validation required `saveStatus: ok` and `publishStatus: ok` in the progress row. A later public `/products` check also showed a static marketing page that did not list the CMS product titles, even though product detail URLs rendered.
- Evidence: backend list showed the batch product as `已发布`; frontend detail rendered H1, description, body text, and a non-zero image; the redacted frontend audit was clean; `validate_batch_upload_publish_evidence.py` passed after manifest/progress alignment. Public `/products` had the static products-page H1 and links but no batch/demo product names.
- Risk: batch proof can be overclaimed if the manifest, progress log, backend URL, and frontend audit are not bound to the same slug. Conversely, a static `/products` page that omits CMS product cards can make operators think publish failed when detail routes are valid, or can hide a missing CMS list block requirement.
- Rule: before claiming batch upload/publish, validate the manifest used for the batch stage, require one progress row per manifest slug, include `saveStatus` and `publishStatus`, and run a redacted frontend detail audit for the same slug. Verify product list-page behavior separately: if `/products` is a static marketing page rather than a CMS list block, report detail publish success separately from list visibility.
- Follow-up: `batch-verification.md` now emphasizes manifest/progress slug alignment and explicit save/publish status fields.

## 2026-07-01 Official Docs First Correction

- Context: user requested correction against `https://www.allincms.com/docs` instead of continuing broad UI exploration.
- Symptom: the skill already mentioned official docs, but the actionable checklist was split across site creation, create flows, batch verification, interface inventory, and launch acceptance. This made it too easy to focus on request capture or JSON acceleration before finishing the tutorial's categories -> products -> posts -> homepage modules sequence.
- Evidence: official docs pages checked live on 2026-07-01 state the primary path as create site, open frontend, edit default content when present, fix 404/blank theme first, create or edit 2-3 product categories, at least 2 products per main category, 3 posts, then homepage modules and launch click-through QA.
- Risk: operators may treat captured Server Actions as the main route, create duplicate blank themes/pages/content, or claim backend publish success without public visitor checks.
- Rule: load `official-docs-alignment.md` for from-scratch builds, broad walkthroughs, homepage/module work, launch QA, and JSON-vs-UI decisions. JSON replay is allowed only for the exact current docs-required action after capture and backend/frontend proof.
- Follow-up: `SKILL.md`, `site-creation.md`, `create-flows.md`, `interface-inventory.md`, `batch-verification.md`, and `launch-acceptance.md` now point to the official-docs route map.

- Context: live docs refresh for the same correction request, focusing on tutorial stop gates instead of UI probing.
- Symptom: the previous docs-first wording still allowed an operator to continue exploring after a normal frontend rendered, or to treat theme/page creation as a general setup task rather than a recovery path for 404/blank sites.
- Evidence: the refreshed docs say to open the public site immediately after creation; stop creating themes when a normal template page appears; create a preset `默认` theme only when the public site is 404/blank or theme/pages are missing; edit existing default pages/products/posts before creating duplicates; create new pages through route -> page -> bind -> enable -> public URL; and perform visitor-style launch checks including mobile, forms/contact, images, and domain/HTTPS when in scope.
- Risk: an agent can still "实操所有功能" by creating unnecessary themes, pages, products, or routes, polluting the temporary site and hiding the user's real goal of a launchable website.
- Rule: treat official tutorial stop gates as hard stage boundaries. Do not advance from site creation to content, from content to homepage, or from page rows to launch claims until the tutorial's public frontend proof for that stage is true or an explicit demo-scope deferral is recorded.
- Follow-up: `official-docs-alignment.md`, `site-creation.md`, and `create-flows.md` now include refreshed stop gates and page-to-action routing.

## 2026-07-01 Posts Completion And Category Setup Findings

- Context: continuing a temporary business-demo site against the official docs checklist.
- Symptom: after clicking the posts list `创建` button, the immediate URL read still returned `/posts`, but the DOM had already switched into an `更新文章` draft edit view with `Untitled Post`, title/slug/excerpt fields, the rich text editor, `更新`, and `发布`.
- Evidence: the third article was filled, saved, published, and backend `/posts` then listed 3 published articles. Public `/posts` rendered `3 stories` and linked all three titles; the new detail slug rendered H1 and body text without 404.
- Risk: URL-only checks can trigger duplicate draft creation if the operator retries `创建` while the edit view is already open.
- Rule: after post create clicks, verify DOM state as well as URL. If the edit view fields are present, continue editing the created draft; do not click create again.
- Follow-up: `create-flows.md` now records the post-create URL lag condition.

- Context: creating official-docs-required product categories on the temporary site.
- Symptom: the product category page initially had no categories and an empty-state `创建分类` button. After one root category existed, the empty-state button disappeared and creation moved to icon-only `+` controls. Creating two root categories succeeded, but repeated attempts to create the third root category returned `Given transaction number ... does not match any in-progress transactions`.
- Evidence: backend category tree showed two new root categories; the intended third root category did not appear after retry, and the create dialog remained open with the transaction error.
- Risk: blind repeated submissions can create duplicates or keep failing against stale transaction state. Icon-only `+` controls can also create child categories if the row-level button is clicked instead of the toolbar button.
- Rule: distinguish toolbar-root `+` from row-child `+`, create categories one at a time, reload and verify after transaction mismatch, and stop with explicit blocker evidence when retry fails. The official docs lower bound is 2-3 main categories; 2 categories can satisfy the lower bound, but any planned third category remains blocked until the transaction issue is resolved.
- Follow-up: `create-flows.md` now documents category create UI and transaction mismatch handling.

- Context: verifying product category acceptance on the public frontend.
- Symptom: public `/products` rendered a static marketing page with no newly created backend category names, no product category links, and no `/products?category=...` links.
- Evidence: browser DOM showed static product-family text and no product-category anchors after the backend categories were created.
- Risk: operators may count backend category rows as full tutorial completion even though the official docs require copying real category links from the frontend and using categories in homepage/product modules.
- Rule: backend category rows are setup progress only. The category frontend acceptance item remains incomplete until a CMS product/category module renders clickable category filters, or a demo-scope deferral is explicitly recorded.
- Follow-up: `official-docs-alignment.md` and `batch-verification.md` now separate backend category existence from frontend category-filter proof.

## 2026-07-01 Blank Theme Activation And In-App Browser Stability Findings

- Context: resuming a from-scratch temporary site in the in-app browser after Chrome auth was unavailable.
- Symptom: the site dashboard was accessible in the in-app browser, but the public root `/` returned 404. The theme list showed a blank theme with one page, theme status draft/stopped, and a `配置路由映射` warning. The theme page list showed Home as published but not initially enabled or set as homepage.
- Evidence: enabling the Home switch and clicking set-home changed the Home row to checked/enabled and disabled the set-home button. Enabling the theme from the theme list opened the route-mapping dialog; clicking `应用主题` produced a `主题已应用` toast and changed the theme switch to checked/disabled. Public `/home` then returned 200 and `/home` route became bound to Home, while public `/` still returned 404 and `/home` rendered only an empty `main`.
- Risk: operators can overclaim "site fixed" from theme-enabled and route-bound state even though the root URL is still 404 and the bound page has no visible content. Conversely, they may keep creating content while the official first gate, a usable frontend homepage, remains incomplete.
- Rule: for blank-theme recovery, verify three layers separately: theme active, at least one enabled/bound page such as `/home`, and the public root `/` or accepted homepage URL rendering non-empty visible DOM. A 200 `/home` with empty `main` is only partial launch-readiness evidence, not homepage completion.
- Follow-up: future runbooks should distinguish `home_route_bound_partial` from `root_homepage_ready`.

- Context: attempting to locate the real Home design link after a guessed design URL returned backend 404.
- Symptom: reading a broad `document.querySelectorAll('a,button')` snapshot on the theme detail page caused the in-app browser target to close, leaving no open in-app tabs.
- Evidence: the browser command failed with `target closed while handling command`; a follow-up `openTabs()` call succeeded but returned an empty tab list.
- Risk: broad DOM extraction on LAICMS theme/designer pages can destabilize the in-app browser just like drag/drop interactions. Operators may lose the current tab and partial browser state.
- Rule: avoid broad DOM extraction on theme/designer pages in the in-app browser. Prefer `domSnapshot()` excerpts, scoped locators from visible rows, or direct links already present in the snapshot. After target closure, recover from `/sites` or the known backend URL and record the last proven state before continuing.
- Follow-up: use Chrome when possible for theme/designer operations; if forced to use the in-app browser, keep reads and clicks scoped and verify after every step.

## 2026-07-01 Default Theme Recovery And Root Homepage Findings

- Context: continuing a temporary from-scratch site in the in-app browser after a blank theme left Home published/enabled but empty.
- Symptom: the Home theme-page row exposed an enabled `设为首页` action. Clicking it produced `首页已更新` and disabled the row button, but public `/` still rendered 404 while `/home` remained HTTP 200 with an empty `main`.
- Evidence: backend theme-page proof showed Home `/home` enabled and published; public `/home` had no body text, no H1, no links, and no images; public `/` showed the platform 404 page after the `首页已更新` toast.
- Risk: operators can overclaim root homepage repair from a toast or disabled button, or keep adding content while the official first gate still lacks a usable public homepage.
- Rule: `set_homepage` needs public root proof, not only backend row proof. If a blank theme has no blocks, treat `/home` 200 with empty DOM and `/` 404 as a failed launch gate.
- Follow-up: `create-flows.md` now states that `设为首页` is expected root-home behavior but must be verified by non-empty public `/` DOM.

- Context: recovering the same site through the official tutorial path instead of forcing designer block insertion on a blank page.
- Symptom: the `创建主题` dialog exposed both `空白` and `默认` presets. Creating a `默认` preset theme produced 7 published/enabled pages, while the existing blank theme had only one empty Home page.
- Evidence: the generated default theme contained Home, Products, Product detail, Posts, Post detail, About Us, and Contact Us. After enabling the default theme, the theme list showed it as `启用`, routes for `/home`, `/products`, `/products/{product}`, `/posts`, `/posts/{post}`, `/about-us`, and `/contact-us` were bound, and public `/`, `/home`, `/products`, `/posts`, `/about-us`, and `/contact-us` rendered non-empty DOM.
- Risk: blank-theme recovery wastes time on brittle block insertion and can leave the site unusable, while default-theme recovery may look complete even though the public content is still generic template copy.
- Rule: for 404/blank new sites without a validated pageDocument path, create or switch to a `默认` preset theme before editing blocks. Treat this as a structural recovery only; the site is not business-ready until template brand/copy/assets are replaced and public pages are reverified.
- Follow-up: `create-flows.md` now documents default-theme page generation and the required post-activation checks.

- Context: activating the default recovery theme from the theme list.
- Symptom: `主题已应用` appeared without a route-mapping dialog, and an immediate snapshot still looked partly stale. After a refresh, the old blank theme became `草稿` and the new default theme became `启用`.
- Evidence: refreshed theme-list state, route-list bindings, and public frontend route checks agreed after reload; transient Statsig network timeout/queue warnings appeared in the browser tool output but did not correspond to LAICMS mutation failure.
- Risk: immediate post-click snapshots and browser telemetry noise can cause false negatives or false positives.
- Rule: after theme activation, refresh the backend theme list and route list before judging final state. Treat third-party telemetry warnings as browser noise unless LAICMS state or public frontend proof contradicts the mutation.
- Follow-up: `mutation-safety.md` now records the missing dedicated helper action for whole-theme activation and requires refreshed backend plus frontend proof.

## 2026-07-01 Product Replacement Editor And Detail Retry Findings

- Context: replacing generated default product content on a temporary launch site after cleaning a public probe product.
- Symptom: deleting the unique `Codex Probe - Delete Me` product required row-scoped menu targeting; a generic row locator matched multiple ancestor rows. After confirmation, backend products dropped from 4 to 3 and public `/products` plus the probe detail route no longer exposed the probe.
- Evidence: table-row text showed the probe as the fourth row; DOM node targeting opened that row menu; the confirmation dialog named `Codex Probe - Delete Me`; backend reload listed only three non-probe products; `/products` had no probe text and the old probe detail URL rendered 404.
- Risk: global row/menu locators can delete the wrong product or fail strict uniqueness checks; immediate public list checks can keep stale probe residue if not reloaded.
- Rule: for product cleanup, enumerate table row text first, open the menu belonging to the exact row, require a confirmation dialog naming the probe, then verify backend absence and frontend non-public state.
- Follow-up: keep cleanup proof redacted; do not store raw product IDs in the skill.

- Context: editing a default generated product into business-specific product content and publishing it.
- Symptom: after save, the product moved from `已发布` to `草稿` and required a separate `发布` click. Immediately after publish, `/products/{newSlug}` returned 404, while `/products` already displayed the new product title and linked to the new slug. A short retry of the same detail URL then rendered the expected H1 and body.
- Evidence: backend list showed the edited product as `已发布`; public `/products` linked to the new `/products/{slug}`; the first detail check was 404; a later detail check rendered the edited product H1 with the edited body.
- Risk: immediate detail-route 404 can be misdiagnosed as publish failure even though route/index propagation is still catching up; conversely, list visibility alone can be overclaimed as detail proof.
- Rule: after a product slug change, verify backend publish and list link first, then retry the detail URL with a bounded delay. Product verification passes only when detail DOM renders the new title/body.
- Follow-up: `create-flows.md` and `batch-verification.md` now include the bounded retry rule.

- Context: replacing the rich body of a second default generated product.
- Symptom: `locator.fill()` on the Slate contenteditable appended the new business body to existing default text instead of replacing it. A second attempt using focus, select-all, backspace, and typing still left default text mixed into the editor. The operator closed the unsaved edit tab and confirmed the backend row was unchanged.
- Evidence: editor `innerText` still contained old default-template phrases after replacement attempts, while the update button was enabled. No save was clicked; backend product list still showed the original default product.
- Risk: a clean title/slug/description replacement can hide polluted rich body content if the operator saves without separately reading the editor text. Keyboard shortcuts may not select all Slate nodes in this designer/editor runtime.
- Rule: before saving product body replacements, inspect the rich editor text and assert old default phrases are gone. If the editor appends or leaves old paragraphs, abandon the unsaved page and use a captured request/schema path or a proven clear method; never save mixed default/business body text.
- Follow-up: `create-flows.md` now warns about default-body replacement pollution.

- Context: continuing the same temporary product replacement run on the generated default theme.
- Symptom: a guessed backend edit route using the public slug returned a backend 404, while the row action menu exposed the real `/{siteKey}/products/{contentId}/update` URL. On the third product, `locator.fill()` and keyboard select-all appended or prepended replacement text to the old Slate body. CUA clear removed old content, but CUA direct typing left the editor placeholder text in the body; CUA clear plus clipboard paste produced clean editor text and enabled a safe save.
- Evidence: the operator blocked saves whenever editor `innerText` still contained old template phrases, probe/test strings, or `编写产品详情...`; after the clipboard-paste path, backend `/products` showed the edited product as `已发布` and public `/products/{slug}` rendered the new H1/body.
- Risk: agents can corrupt live product bodies by saving mixed old/new copy or by assuming a public slug doubles as a backend content id. Placeholder residue can also become real published body text if not checked.
- Rule: obtain product edit URLs from backend row menus, not public slugs. For Slate body replacement, prefer CUA node focus + system select-all/backspace + clipboard paste, then assert no old phrases/test text/placeholders before clicking `更新`. Treat save-to-draft and separate publish as expected.
- Follow-up: `create-flows.md` now documents row-menu edit URLs and the clipboard-paste clear method; `mutation-safety.md` now records the missing dedicated helper actions for updating existing non-probe products/posts.

## 2026-07-01 Existing Content Update Gate Coverage Finding

- Context: updating existing generated products into legitimate temporary launch content.
- Symptom: the authorization helper can create a `publish` record, but the pre-mutation gate has no dedicated `save_product`, `publish_product`, `save_post`, or `publish_post` action for existing non-probe content. Probe save/publish gates are too narrow because they require `Codex Probe - Delete Me`, while generic batch actions are too broad for one row.
- Evidence: exact per-product authorization records were generated for the existing edit URLs, but no matching pre-mutation gate action could validate them. The run stayed safe by scoping to one row, reading the editor before save, saving once, publishing once, and verifying backend plus frontend detail pages.
- Risk: operators may either misuse probe gates for real demo content or skip action records entirely because the exact helper action is missing.
- Rule: until helper coverage is extended, pair the current-session test-site policy with an exact local record for each existing-content update, keep the mutation single-item scoped, and verify backend status plus public detail DOM immediately. Do not use this workaround for batch replay, production content, deletion, or external-data uploads.
- Follow-up: add dedicated helper/gate actions for existing content update/publish before relying on deterministic gates for full batch replacement. Status update: this follow-up is now closed by the 2026-07-03 Existing Content Gate Closure Finding; the dedicated actions exist, while batch replacement still requires schema/sample/batch gates separately.

## 2026-07-01 Post Replacement And Verification Findings

- Context: replacing generated/default posts with business-specific demo posts and verifying them on a temporary launch site.
- Symptom: post editing behaved like product editing in two important ways: save could move an already public item back to draft, and immediate frontend detail checks could fail while the list page already linked the updated slug.
- Evidence: backend `/posts` listed three published post rows after separate save and publish operations. Public `/posts` rendered the three updated article cards, and browser checks of each `/posts/{slug}` detail page rendered title, excerpt, and body text. Some immediate or CLI checks reported 404/fetch failure for recently updated post detail routes, but bounded browser retry rendered the expected detail DOM.
- Risk: operators can overclaim from `/posts` list links alone, or falsely mark detail routes broken from the first immediate 404/fetch failure after publish. They can also leave updated posts in draft if they treat `更新` as enough.
- Rule: for existing post replacement, use row-derived backend edit URLs, treat save and publish as separate operations, verify backend `已发布`, then verify both `/posts` list links and each `/posts/{slug}` detail DOM with bounded retry. Browser-visible detail DOM can prove current rendering when the CLI auditor times out, but rerun or record the CLI warning before final launch acceptance.
- Follow-up: `create-flows.md` and `batch-verification.md` now document post update save-to-draft behavior, row-menu edit URL requirements, and bounded detail retry.

## 2026-07-01 Frontend Status And Template Residue Findings

- Context: read-only status check after products and posts had been replaced on a default recovery theme.
- Symptom: controlled in-app browser tabs from the previous run could time out while attaching, but opening a fresh controlled in-app tab to the same backend route proved the session was still authenticated and the content list was available. Public route audit produced a valid JSON report but exited non-zero due to warnings/fetch failures; browser route checks showed the pages themselves rendered.
- Evidence: a fresh backend products tab loaded without sign-in and showed the updated product rows without probe or untitled rows. Public browser checks showed `/`, `/posts`, post details, `/about-us`, and `/contact-us` rendered, while the homepage, header, footer, About, Contact, category chips, and recommended-product blocks still contained generic default-theme brand/copy.
- Risk: an operator may misdiagnose an in-app browser attach timeout as LAICMS logout, or treat route HTTP 200/content detail success as launch-ready while generic template residue remains visible to visitors.
- Rule: after browser-control attach failures, recover through a fresh controlled tab and fresh target-module load before declaring auth/page failure. For launch QA, check default-theme residue separately from content-detail verification; a site can be structurally live and content-partially updated while still not launch-ready.
- Follow-up: `batch-verification.md` now names CLI-vs-browser route split handling and default-theme residue as launch blockers.

## 2026-07-01 Designer Rewrite And Contact Form Findings

- Context: mutating static pages on a temporary default-preset theme through the in-app browser designer.
- Symptom: the designer Copilot/`Improve the current page` path updated only some blocks. It changed header/navigation and some copy, but left other public sections with default-template category chips, product labels, FAQ/contact text, team blurbs, or address blocks. The designer could show `inspect-block Done` or `update-block Done`, and a page could publish successfully, while lower-page default copy still remained.
- Evidence: a public homepage rendered updated header/hero copy but still showed default product category chips until specific campaign/category/story Props were edited directly. A company page rendered an updated H1 and intro, while stats/team blocks still kept generic retail metrics/team copy until block-specific nested fields were edited. A contact page rendered updated inquiry copy, but still exposed a stale location block and an unresolved embedded form message until those blocks were hidden and republished.
- Risk: operators can overclaim page completion from successful generation or publish states. They can also corrupt the wrong Prop field because generic input names such as `description` are duplicated across block panels.
- Rule: treat designer generation as a partial draft. After every generated rewrite, run public DOM residue checks and then use Layers plus block-level Props for remaining default blocks. Fill only unique or block-scoped fields; when `[name="description"]` or other generic selectors are ambiguous, stop and scope tighter instead of filling globally.
- Follow-up: `create-flows.md` and `batch-verification.md` now document partial designer generation, duplicate Prop names, public residue checks, and unresolved form handling.

- Context: public contact page QA after the designer generated domain-specific inquiry copy.
- Symptom: the visible copy was mostly correct, but the page still showed an old location section and `Form "..." could not be resolved`.
- Evidence: hiding `Location Map (Interactive)` and `Contact Form (Split)`, then saving and publishing, removed the stale address/local-pickup text and unresolved form message from `/contact-us`.
- Risk: a good-looking contact headline can hide a broken form embed or fake/default contact details below the fold.
- Rule: contact-page launch QA must include form binding state and contact detail provenance. If the form lifecycle has not been captured or user-confirmed, hide unresolved form blocks and record a source-input/schema gap. Do not present unresolved or placeholder contact mechanisms as production-ready.
- Follow-up: gap ledger entries now cover contact details and form binding requirements; future helper coverage should capture form create/save/embed and notification settings before claiming contact readiness.

## 2026-07-01 Taxonomy, Global Contact, And Gap-Ledger Findings

- Context: mutating product/post taxonomy and static theme blocks on a temporary site after content bodies and page copy already rendered correctly.
- Symptom: public product/post chips still exposed default category labels even after list pages, detail titles, excerpts, and body copy had been replaced. The page designer did not own those chips; they came from the backend category associations.
- Evidence: backend category tabs showed default product and post category names; selecting a tree category opened an edit panel with `name`, `slug`, `description`, and cover fields. After changing category fields, a backend refresh preserved the new values and frontend list/detail chips changed.
- Risk: operators can keep editing page headers or product body copy while the visible residue actually belongs to taxonomy. They may also assume a category edit is unsaved because no text Save button is visible, or overclaim success from the in-memory tree before refreshing.
- Rule: treat taxonomy as a separate content layer from page copy. When frontend chips are wrong, inspect backend categories/tags and content associations directly. For tree category edits, verify persistence with a backend refresh plus frontend list/detail chip proof; do not rely on the immediate tree text alone.
- Follow-up: batch QA must include taxonomy-chip residue checks separately from static page residue.

- Context: cleaning contact residue after the contact page body had already been fixed.
- Symptom: public home pages still exposed old address, phone, email, or brand text even though the `/contact-us` page no longer showed those values. Selecting `Contact Dialog Form (Modal)` proved the dialog shell had only title/description/form reference fields, while the stale address lived in a separate `Contact Form (Split)` page block; another brand residue lived in a news/editorial block.
- Evidence: public DOM context around the stale address identified a contact block with email/phone/address/hours fields. Layer-scoped Inspector fields for `Contact Form (Split)` exposed `emailValue`, `phoneValue`, `addressValue`, and related labels; `Featured News List (Editorial)` exposed a separate `supportingCopy` field with old brand text.
- Risk: a QA pass that checks only `/contact-us` or only a global modal can miss cross-page contact/CTA residue. Conversely, editing the modal shell does not necessarily change a page-level contact block or embedded form copy.
- Rule: final QA must scan all public pages for contact details and CTA residue across header, footer, page contact blocks, global dialogs/modals, floating buttons, and editorial/recommended blocks. Identify the exact layer before editing; do not assume all contact text belongs to one form or modal.
- Follow-up: launch QA should include stale contact terms and brand terms in the public DOM residue scan.

- Context: local action-record and gap-ledger maintenance during taxonomy/contact cleanup.
- Symptom: shell commands that passed URLs containing `?tab=...` without quotes failed under zsh globbing, and `record_source_input_gap.py --current-evidence` rejected free-form prose because the argument is an enum.
- Evidence: the shell printed `no matches found` for an unquoted taxonomy URL, and the gap-ledger helper listed allowed `--current-evidence` choices such as `ui-only`, `blocked`, and `request-captured`.
- Risk: operators can mistake command-line quoting or enum misuse for helper failure and skip records before a mutation.
- Rule: quote URLs with query strings in shell commands. For source-input gaps, put one of the supported enum values in `--current-evidence` and move detailed proof text to `--operator-note`.
- Follow-up: command examples that include query strings or gap-ledger evidence should follow this pattern.

- Context: using existing mutation helpers for taxonomy category replacement.
- Symptom: the authorization helper and pre-mutation gate have no dedicated action for creating, updating, or renaming existing categories/tags. `save_site_settings` can record a broad site-scoped change, but it does not model taxonomy-specific fields, row/tree selection, or frontend chip verification.
- Evidence: supported action lists include site/theme/route/form/probe/batch/media actions but no `create_category`, `update_category`, `rename_category`, `create_tag`, `update_tag`, or `rename_tag` actions.
- Risk: operators may misuse generic site settings records for taxonomy mutations or skip deterministic gates entirely.
- Rule: until dedicated taxonomy actions exist, use an exact local action record naming the content type, taxonomy tab URL, old and new category/tag identifiers, fields changed, expected backend refresh proof, and frontend chip proof. Keep taxonomy mutations small and verify immediately.
- Follow-up: add helper/gate support for taxonomy create/update/rename actions before relying on deterministic taxonomy batch operations.

## 2026-07-01 Designer Hide Controls And Telemetry Findings

- Context: mutating an existing homepage design on a temporary site by hiding unconfirmed FAQ, newsletter, and floating-social modules.
- Symptom: the designer initially showed the `Blocks` tab, where per-instance `Hide ...` controls were not available. After switching to `Layers`, each target module had a unique hide button. Clicking hide changed the layer control from `Hide ...` to `Show ...`, set the page status to `Editing`, and enabled both Save and Publish. Save then disabled Save and changed status to `Draft`; Publish later returned status to `Published` and disabled Publish.
- Evidence: public `/` and `/home` browser DOM no longer contained the hidden default FAQ/newsletter/floating WhatsApp text after publish. CLI audit for `/` still produced a `fetch_failed` artifact while the live browser DOM rendered; this was treated as a tool/network split requiring explicit recording, not as page failure.
- Risk: operators can search in the wrong designer tab, miss the hide controls, or overreact to browser telemetry/CLI fetch noise and misdiagnose a successful save/publish. They can also forget that hiding a block is a mutation requiring save, publish, and public DOM verification.
- Rule: use Layers for existing-block hide/show operations. Verify the `Hide` to `Show` state change, Save/Draft/Publish/Published state machine, and public DOM removal. Treat Statsig or `ab.chatgpt.com` timeout warnings as browser-control noise unless LAICMS state or public DOM contradicts the expected mutation.
- Follow-up: `create-flows.md`, `interface-inventory.md`, and `mutation-safety.md` now document hide/show operation state and telemetry-noise handling.

- Context: hiding a Products page `Recommended Articles (Grid)` module to remove generic recommendation copy from a temporary launch page.
- Symptom: the `button[aria-label="Hide Recommended Articles (Grid)"]` locator was unique, but the Playwright click timed out in the designer. Switching to a visible DOM snapshot exposed the same control as a concrete node id, and clicking that node changed the control to `Show Recommended Articles (Grid)`.
- Evidence: after the DOM-node click, the designer status became `Editing`, Save/Publish were enabled, Save moved the page to `Draft`, Publish returned it to `Published`, and a rerun public `/products` audit returned 200 with no issues. Text proof showed product titles still present while `Buying guides, material notes`, `material notes`, and `Recommended articles` were gone.
- Risk: operators may retry a failing locator until the browser destabilizes, or edit recommendation copy field-by-field when the safer launch fix is to hide an unneeded generic recommendation block.
- Rule: if a unique designer hide locator times out, use one fresh visible DOM snapshot and click the exact node id, then verify `Show ...` before save/publish. For optional generic recommendation blocks, hiding the whole block can be safer than editing copy when the page already has the required product/list content.
- Follow-up: `create-flows.md` now documents DOM-node fallback for designer hide controls.

- Context: recording source-input gaps during the same homepage QA pass.
- Symptom: using `blocked` or `blocked-until-confirmed` as a source-input `classification` is invalid; `blocked` belongs to `currentEvidence`, while confirmation blockers need the supported classification enum plus an explicit decision. The helper also rejects `ui-only` proof without an `operatorNote`.
- Evidence: `record_source_input_gap.py` rejected a row with `operatorNote is required when currentEvidence claims UI/request/sample proof`; previous enum checks showed the allowed classification values are only `required`, `recommended`, `optional`, `user-confirmed`, `source-derived`, `blocked-until-schema-captured`, and `not-in-scope`.
- Risk: source-intake ledgers can fail during browser work, or future PDF/catalog extraction can misread a confirmation blocker as a schema blocker.
- Rule: for user-confirmation blockers, use `classification: required,user-confirmed`, `decisionNeeded: needs-user-confirmation`, a supported `currentEvidence` value, and an `operatorNote` when evidence is UI/request/sample based. Do not use `blocked` or `blocked-until-confirmed` as classifications.
- Follow-up: `field-contract.md` now includes the classification反例 and current-evidence split.

- Context: opening a contact page designer from the theme page list during launch cleanup.
- Symptom: a handoff note had an outdated page id for Contact; opening that URL displayed `Page context: About Us` and route `/about-us`. Broad locators containing `Contact Us` matched multiple rows and footer/navigation controls, not just the theme-list row.
- Evidence: the correct Contact designer was only confirmed after reading the theme page list and checking the opened designer showed `Page context: Contact Us`, page id placeholder `{pageId}`, and route `/contact-us`. The stale action record was not used for mutation.
- Risk: an operator can save/publish the wrong page because theme page order changed or a stale page id survived in local notes.
- Rule: before theme-page mutations, verify the target by current designer context and route chip, not by old IDs or broad row text. If the target is wrong, regenerate the action record for the actual page id and discard the stale one.
- Follow-up: `create-flows.md` now warns against stale page ids and broad theme-list locators.

- Context: removing unconfirmed public contact and social placeholders from Home and Contact pages.
- Symptom: Footer social entries could be changed from external `Custom` URLs to `None`, removing public `href`s while leaving plain text labels. Contact-page placeholder links, email, phone, and address lived in a `Contact Info (Grid)` block, not in the global footer or dialog.
- Evidence: public browser checks after publish showed `/`, `/home`, and `/contact-us` had no `instagram.com`, `x.com`, `linkedin.com`, `youtube.com`, placeholder email, phone, or address links; Home still displayed plain Footer labels after link targets were set to `None`.
- Risk: operators may keep fake contact details live, edit the wrong global component, or assume social label text means an external link still exists.
- Rule: for launch cleanup without confirmed contact channels, either set link targets to `None` or hide the owning page block, then verify public anchors rather than visible text alone. Record the missing real channels as user-confirmed source-input gaps.
- Follow-up: `create-flows.md` and `interface-inventory.md` now document `None` link targets and owner-block verification.

- Context: final frontend route audit after static cleanup and content detail verification.
- Symptom: a 12-route CLI audit and later smaller product/post detail audits could hang on Python `http.client` chunked response reads. Interrupting a product or post group produced `fetch_failed` for the last detail route, while browser checks of the same routes showed 200-level rendered DOM, one H1, images, links, and no denylist residue.
- Evidence: the interrupt stack stopped in `_read_next_chunk_size`; browser checks for the affected product/post detail URLs rendered the expected titles, images, and clean denylist state. Static pages and several detail URLs passed CLI before the hang.
- Risk: a hung audit process can stall the run or falsely mark a good public route as broken. Conversely, ignoring all CLI failures without browser proof can hide real route issues.
- Rule: for broad AllinCMS frontend audits, split URL groups, cap bytes, and use browser DOM proof for any route with CLI `fetch_failed` or interrupted chunked reads. Stop the hung process; record the split result explicitly.
- Follow-up: `batch-verification.md` now documents chunked-read hangs and the split-audit fallback.

## 2026-07-01 Mobile Viewport Verification Finding

- Context: read-only public frontend QA in the in-app browser after desktop route checks passed.
- Symptom: the browser viewport capability accepted a 390px mobile-size request, but page-side `window.innerWidth` and `document.documentElement.clientWidth` still reported the desktop width. A second pass using tab-level CDP device metrics produced the intended 390px page width.
- Evidence: the first mobile pass showed `viewport.w` and `clientWidth` as desktop-sized values; the CDP pass showed `window.innerWidth`, `visualViewport.width`, `clientWidth`, and `scrollWidth` at the intended mobile width with mobile navigation controls visible.
- Risk: operators can falsely mark mobile QA complete from a successful tool call while the actual page was never rendered at a mobile breakpoint.
- Rule: mobile launch QA must record page-observed viewport values, not only the requested viewport. If the page still reads as desktop width, rerun with a stronger emulation path such as CDP `Emulation.setDeviceMetricsOverride`, clear the override afterward, and only then evaluate overflow, menu, H1, image, and denylist results.
- Follow-up: `launch-acceptance.md` now requires effective viewport proof for mobile QA.

## 2026-07-01 Source Gap Supersession Finding

- Context: regenerating source-input requirements after a long temporary-site build where later browser QA had fixed some earlier blockers.
- Symptom: the append-only gap ledger still marked product specifications, taxonomy, media, newsletter, social, and contact placeholders as active blockers even after later public QA showed some were fixed, hidden, or explicitly deferred for demo scope.
- Evidence: the first regenerated requirements report kept old operation gaps in `operationGaps.blockedFields`; adding resolved-gap evidence filtered superseded rows into `resolvedEntries` while leaving the remaining unresolved form-binding gap active.
- Risk: future PDF/catalog extraction can be blocked by stale browser findings, or an operator may edit old ledger rows and lose the audit trail.
- Rule: keep gap ledgers append-only. When later browser proof supersedes an old operation gap, create `allincms_resolved_source_input_gaps` evidence with `fieldLabel`, `proof`, and `note`, then pass it to `make_source_input_requirements.py --resolved-gap-evidence`. Do not use resolved evidence to bypass fields that still lack schema capture or user confirmation.
- Follow-up: `make_source_input_requirements.py`, its regression tests, and `field-contract.md` now support resolved operation gaps.

## 2026-07-01 Published Form Versus Public Embed Finding

- Context: read-only resume of a temporary AllinCMS site after the operator was asked to open the in-app browser and check current state.
- Symptom: earlier demo-scope evidence said forms were deferred, but a fresh `/forms` read showed a published form row with a slug and field count. The public contact page still rendered with `formCount: 0` and no unresolved-form message because the theme page did not embed the form.
- Evidence: backend `/forms` columns showed name, slug, description, fields, status, and updated time with a published form row; public `/contact-us` returned a normal page with no `<form>`, no expected form field labels, and no unresolved form error.
- Risk: operators can overclaim contact readiness from a published backend form, or keep using stale deferral evidence after another stage creates or publishes a form. They can also miss that a hidden or unbound designer `Contact Form (Split)` block produces a clean public page with no form instead of an obvious error.
- Rule: before claiming form/contact launch readiness, re-check both surfaces in the same round: backend `/forms` row state and public contact-page DOM. A published form proves only backend form availability; launch proof still requires designer binding/embedding, page save/publish when needed, public `<form>` DOM proof, and an explicit submission-test or omission policy.
- Follow-up: keep the forms gap active until embed and submission behavior are proven or explicitly out of scope for the current site.

- Context: mutating a Contact page designer on a temporary site to embed an already published form.
- Symptom: changing `Contact Form (Split)` from hidden to visible enabled Save/Publish, but the preview iframe initially rendered `Form "{oldFormSlug}" could not be resolved`; selecting the layer showed Inspector `Form` as `Select a form` rather than the current published form.
- Evidence: after choosing the current published form in the Inspector combobox, the preview iframe rendered labels such as Name, Email, Topic, Message and a submit button, the unresolved-form text disappeared, Save changed the page to Draft, Publish returned it to Published, and public `/contact-us` contained one `<form>` with expected inputs.
- Risk: operators may think showing a hidden form block is enough, or rely on a route-level HTTP/render audit that does not inspect form controls. That can ship either a hidden empty contact page or a visible unresolved-form error.
- Rule: contact form embed proof requires the full chain: show or insert the block, select the current published form in Inspector, verify preview iframe fields/no unresolved error, save, publish, and verify public DOM `formCount > 0` plus expected inputs and submit text. Treat submission testing as a separate policy gate.
- Follow-up: `create-flows.md` now documents stale form-slug repair and separates route audit from form DOM proof.

- Context: mutating the same Contact page after the form embed worked, to remove unconfirmed placeholder contact channels.
- Symptom: the `Contact Form (Split)` Inspector owned both the form selector and contact-detail fields. Even with a valid form embed, the public page still showed placeholder email, phone, address, and hours until `emailValue`, `phoneValue`, `addressValue`, and `hoursValue` were edited or removed.
- Evidence: after replacing those values with non-contact routing copy and publishing, public `/contact-us` still had one form with expected fields, no unresolved form error, no fake contact strings, and no external social `href`s. Plain social labels could still remain without external links.
- Risk: an operator can mark contact readiness complete after the form appears while fake phone/address/email details remain visible. Conversely, anchor-only checks can miss plain placeholder labels, and visible-text checks can overstate risk when the link target has already been removed.
- Rule: contact QA must treat form embed, contact-detail values, and social/footer links as separate checks. Without user-confirmed contact channels, route visitors to the form or hide the owner block; then verify denylist text and external anchors separately while recording any remaining plain labels as a policy decision.
- Follow-up: `create-flows.md` now documents `Contact Form (Split)` contact-detail fields and the text-versus-anchor verification split.

- Context: mutating the global `Footer (Columns)` block to remove remaining unlinked social labels.
- Symptom: `socialLinks.*.label` fields can visibly remain after link targets are set to `None`. A Playwright `fill("")` attempt against the label inputs reverted to the old value and left Save disabled, while a real focus plus select-all/backspace cleared the inputs and enabled Save.
- Evidence: after keyboard clearing, the designer fields for `socialLinks.0.label` and `socialLinks.1.label` were empty; Save moved the page to Draft, Publish returned it to Published, and public `/contact-us`, `/products`, and `/` had no social label text, no external social anchors, and retained footer product/company/resource links.
- Risk: an operator may assume `fill("")` worked, skip reading the field back, or remove/hide the whole footer when only the social label inputs need cleanup.
- Rule: when deleting designer input values, especially social labels, verify field values and Save enablement immediately after the input action. If programmatic fill reverts, use visible keyboard select-all/backspace, then save, publish, and verify both public text and anchors.
- Follow-up: `create-flows.md` now documents the footer social-label cleanup path and post-publish public verification.

## 2026-07-01 Designer URL Image Picker And Homepage Image QA Findings

- Context: mutating an existing homepage `Category Showcase (Grid)` block on a temporary site to remove default-template category images.
- Symptom: the block copy and links were already domain-correct, but the first category images still exposed old template alt labels. The `替换图片` control opened a picker with `媒体库`, `上传`, and `URL` tabs; the media library was empty, while the `URL` tab accepted one public image URL and enabled `确认` only after the preview loaded. The `URL` tab appeared as a tab role, not a plain button in the first locator attempt.
- Evidence: confirming one URL changed only the intended image preview and enabled Save/Publish. Saving changed the design state to Draft with Save disabled and Publish enabled. Publishing returned the design to Published with Save/Publish disabled. Public desktop and mobile DOM then showed the first module images with non-zero dimensions and no old template alt labels.
- Risk: operators can overclaim launch quality from correct text alone, waste time on media-library upload when URL-bound designer media is sufficient for a temporary site, or replace multiple repeated images before proving the picker/save/publish chain on one item.
- Rule: for designer module image cleanup, probe one image through the URL tab first, require preview dimensions and Confirm enablement, then replace repeated images. After save and publish, verify public DOM image alts/dimensions plus surrounding text/links on desktop and effective mobile viewport. Keep media-library upload proof separate.
- Follow-up: `create-flows.md` now documents Theme Designer image replacement, and `batch-verification.md` now requires homepage/static module image QA.

- Context: local mutation-record maintenance for a design image cleanup action.
- Symptom: `make_authorization_record.py --fields-or-files` accepts one string argument, not repeated positional values, and the helper rejects an authorization source that does not mention the exact action such as `save_design`.
- Evidence: passing several field strings after one `--fields-or-files` produced `unrecognized arguments`, and the next attempt failed with `authorization source must mention the action` until the source explicitly named `save_design`.
- Risk: operators may mistake helper argument drift for an authorization failure, or create vague records that do not bind the current mutation.
- Rule: pass multiple changed fields as one comma-separated `--fields-or-files` value unless the helper grows true multi-value support. The authorization source must explicitly name the exact action and target, even under a current-session test-site policy.
- Follow-up: keep helper examples action-explicit and comma-separated for multi-field records.

## 2026-07-01 Frontend Stale-Tab Residue Finding

- Context: read-only contact/form QA after prior global footer cleanup and homepage image publish on a temporary site.
- Symptom: an already-open public contact tab initially still showed plain `Instagram` and `X` footer labels even though earlier publish evidence said those labels had been removed. The same route, after a reload, no longer contained those labels or social anchors.
- Evidence: the first DOM read found visible footer anchors with no external `href`; after reloading `/contact-us`, the body text and anchor scan had no `Instagram`, no `X`, and no social external anchors while the embedded contact form still rendered.
- Risk: operators can misdiagnose stale hydrated frontend state as a regression and perform unnecessary designer edits, or they can dismiss real residue without proving a fresh route state.
- Rule: when public QA finds residue in a route that was already open before a recent designer publish, reload that route once or open a fresh tab before declaring the residue active. Record both before/after signals when they differ, and keep visible-text checks separate from external-anchor checks.
- Follow-up: `batch-verification.md` now requires reload/fresh-tab confirmation for recently changed global-block residue.

## 2026-07-01 Module Capture Plan Versus Completion Finding

- Context: local module-interface planning from a fresh redacted backend module scan on a temporary AllinCMS site.
- Symptom: `summarize_module_scan.py` and `plan_module_capture.py` generated a valid 10-stage capture plan, and `validate_capture_plan_gate_coverage.py` passed, but launch acceptance still correctly blocked `module_interface_capture_complete`.
- Historical evidence: the plan covered products create, posts create, media upload, themes create, routes create/bind, forms create, site-info save, tracking create, and domains create; every stage had an authorization action, while `upload_media` was then the explicit UI-first ungated allowlist. No action request/payload/persistence capture was performed in that read-only turn. **The media routing conclusion is superseded by the 2026-07-27 canonical-adapter finding.**
- Risk: operators may confuse capture-plan gate coverage with completed module coverage, then unlock downstream launch or JSON replay stages without real action capture.
- Rule: capture-plan gate coverage is only a readiness checklist. `module_interface_capture_complete` requires a real module capture coverage artifact with every planned stage captured or explicitly not applicable, and `jsonReplayReady` remains false until action replay contracts are validated.
- Follow-up: `interface-inventory.md` now distinguishes capture-plan gate coverage from module capture completion.

## 2026-07-01 Source Files To Site Package Finding

- Context: this section was a ~1600-line running build-log of the source-file → wiki → package → confirmation → execution pipeline (roughly 250 skill-maintenance/hardening entries). Per this file's own Recording Contract (do not record helper-iteration detail), that construction log has been compressed here to its reusable lessons; the full history is in git and the stable, authoritative pipeline spec is `references/source-files-to-site-package.md`.
- Reusable lessons (the rest was per-commit construction detail):
  1. There must be an explicit local `allincms_source_site_package` artifact — a user-confirmed content contract — between raw extraction and any remote create/upload; never jump from a PDF/catalog straight to `/sites` or schema-gated upload. Confirmation is NOT remote-mutation authorization (Invariant INV-2).
  2. A coverage/objective artifact introduced at the user-confirmation boundary (e.g. `sourceReviewObjectiveCoverage`, `contentGoalCoverage`, `contentGoalOverages`) must be preserved through EVERY downstream artifact (confirmation record, execution plan, artifact readiness, created-site handoff/runbook/evidence-bundle, taxonomy, schema/sample/batch, launch inputs, status, next-stage handoff). Dropping it after confirmation is scope drift — stop and rebuild from the review packet.
  3. `reviewComplete=true` (local) does NOT mean the files-to-live-site objective is complete; carry the live-blocker list (remote_site_creation / schema_capture / sample_batch / final_launch not started) and say so in handoffs.
  4. The source gap ledger is append-only; only resolved-with-evidence entries clear a gap; `--write-ledger` must not swallow an unresolved diff (Invariant INV-6).
  5. Publication-ready floors + placeholder/PII rejection are enforced by `validate_source_site_package.py`; the refinement brief advertises the exact `policyStatusOptions` / `policyRequiredFields` / `contentFloors` (see `make_source_wiki_refinement_brief.py`), so a hand-editing operator sets each policy right the first time. Taxonomy-first, categories as ID arrays; `coverImage` carried as a hosted `{url, alt}` only (see the coverImage carry finding below and `build_source_site_package.py`).
  6. Every prepare/apply/build helper in this chain is local-only, non-authorizing scaffolding (INV-2); the next-stage handoff routes to the correct read-only browser preflight and must not emit a browser `localCommand` when a preflight is blocked. The whole local chain is E2E-regression-tested by `test_source_pipeline_e2e.py`.


- Context: browser fallback planning for AllinCMS operations.
- Symptom: the user may switch from Codex in-app browser to Chrome because the in-app browser has higher failure risk, but Chrome can also show cached dashboards, stale deep links, or a sign-in redirect for only one route.
- Evidence: the active `SKILL.md` operating rule already states to use the in-app browser first, fall back to Chrome for zero-size viewports, claim failures, route load failures, or login drift, and prove Chrome auth through `/sites` or the exact target module before mutation.
- Risk: treating Chrome availability as mutation readiness can create/save/publish on the wrong site, operate from a stale route, or proceed while authentication is not actually valid for the target module.
- Rule: Chrome fallback is a control-surface recovery, not authorization or state proof. Before any AllinCMS remote mutation in Chrome, load `/sites` or the exact target module in the same Chrome context, bind the current `siteKey` and URL, and then run the normal action-specific gate.

- Context: carrying source cover images through the package/manifest layer into product/post uploads.
- Symptom: even after images were uploaded to a public host and `coverImage` (a hosted URL) was written into `source-wiki.json` products/posts, `build_source_site_package.py` dropped `coverImage` when normalizing products/posts. The `contentPlan` items and `manifests.*.items` kept only name/slug/description/content/specs/categories/tags/mediaNeeds/sourceRefs, so a later upload could never set a real product/post cover; the image survived only as a `mediaNeeds` hint.
- Evidence: `build_source_site_package.py` now carries `coverImage` via `hosted_cover_image()`, which normalizes a bare hosted URL string or a `{url, alt}` object into the manifest `{url, alt}` contract (alt defaults to product name / post title) and rejects local file paths and non-http strings. Because `draft_manifest()` reuses the normalized product/post list, the cover flows into both `contentPlan` and `manifests.*.items`, and `export_confirmed_site_artifacts.py` preserves it in the exported draft manifest. `validate_manifest.py` already required `coverImage/media` to be an object with a public `url`, and `validate_manifest_sample_upload_evidence.py` already requires `coverOrMediaVerified` when an item carries `coverImage`, so the downstream media-proof plumbing was ready and only the intake step was missing. Regression in `test_source_site_package.py` proves string and object covers normalize, local paths are dropped, and the carried object satisfies the manifest contract.
- Risk: uploading a manifest whose items lost `coverImage` yields cover-less products/posts on the live frontend, and only surfaces at the sample/batch frontend-media check. Conversely, carrying a raw local path into the manifest would fail `validate_manifest` or point uploads at a non-public path.
- Rule: only a public http(s) cover URL may be carried into the package/manifest; upload local source images to a public host first, then keep `coverImage` as `{url, alt}` so `validate_manifest` and sample media proof (`coverOrMediaVerified`) apply. Do not treat `mediaNeeds` hints as delivered covers.

- Context: driving live AllinCMS backend from an assistant while the user is logged in.
- Symptom: the user was logged into `workspace.laicms.com` in their normal Chrome window (dashboard visible, sites listed), but every automation-controlled tab redirected to `/sign-in`. Both browser bridges landed in a non-logged-in context: the Claude-in-Chrome extension saw only its own isolated MCP tab group tab (still on `/sign-in`), and the Chrome DevTools (`Control_Chrome`) bridge saw a different set of tabs (a published-site frontend plus a freshly opened `/sign-in`), never the user's logged-in dashboard tab. Navigating either bridge to `/dashboard` or `/sites` re-redirected to `/sign-in`; `document.cookie` on the sign-in page showed zero readable cookies (Clerk session cookies are httpOnly, so this is inconclusive, but the persistent redirect is decisive).
- Evidence: `list_connected_browsers` returned one browser; `tabs_context_mcp` only ever exposed the single isolated sign-in tab; `Control_Chrome list_tabs`/`get_current_tab` exposed unrelated frontend tabs. A red on-page marker banner injected into the controlled tab did not match the window the user was logging into, confirming the user was authenticating in a different Chrome profile/window than either automation bridge controlled.
- Risk: repeatedly asking the user to "log in" does not help when the automation bridge is bound to a different Chrome profile than the one holding the session; time is lost and the operator may wrongly assume login succeeded and attempt mutation in the wrong context.
- Rule: before live browser work, prove the automation-controlled tab itself reaches a logged-in backend route (e.g., `/dashboard` or `/sites` without a `/sign-in` redirect) via the same bridge that will perform actions. If the controlled tab redirects to sign-in while the user's own window is logged in, treat it as a Chrome profile/bridge mismatch: the user must log in inside the exact profile the bridge drives (or the extension must be attached to the logged-in profile). Keep a reliable local fallback (a copy-paste build kit) ready so a browser-profile block does not stall the deliverable.

- Context: navigating the AllinCMS backend (Clerk-authenticated Next.js) between routes during a live JSON-batch build.
- Symptom: using the browser bridge's `navigate` (hard reload) to move between backend routes intermittently dropped the Clerk session and bounced the tab to `/sign-in`, wiping an authenticated context that click-based navigation kept alive.
- Evidence: after a working login, `navigate`-driven route changes re-triggered the sign-in redirect, while JS-clicking in-app SPA links (soft navigation) preserved the in-memory Clerk session across the same routes. The user asked "why does it log out after I log in — what did you do?"; the cause was the assistant's own `navigate`/hard-reload calls, not a user action.
- Risk: an operator who hard-navigates mid-run can lose an authenticated session it spent time establishing, then wrongly conclude the account or login failed and restart, or attempt mutation in a re-authenticating context.
- Rule: once logged into the AllinCMS backend, move between routes with click-based SPA soft navigation, not `navigate`/hard reload. Reserve hard navigation for the initial route load, and re-prove the logged-in route (no `/sign-in` redirect) after any hard reload before mutating.

- Context: entering text into AllinCMS backend form fields and the Slate rich-text editor via the browser bridge.
- Symptom: keystroke `type` dropped or duplicated characters (e.g. "everyday" became "eeryday", hyphens in part numbers were stripped), and `execCommand('insertText')` into the Slate editor rendered visible text but did not update Slate's internal save-state, so the saved product/post body came back empty.
- Evidence: switching field entry to `form_input` (which sets the DOM value and dispatches the React input/change events) produced reliable, complete field values; body content only persisted when submitted directly as Slate node arrays through the Server Action replay, never through typed/execCommand editor text.
- Risk: trusting typed field values or editor-typed body text yields corrupted specs/slugs and silently empty article/product bodies that only surface on the live frontend or in a backend content re-read.
- Rule: set backend form fields with `form_input`, not keystroke `type`. Never author Slate body content by typing or `execCommand` into the editor — submit it as a Slate node array via JSON (see `server-action-save-api.md`). Re-read the saved entity's `content` to confirm the body persisted, not just the field.

- Context: the user pushed to stop hand-clicking the UI and instead replay the backend save API for a full product/post/category batch ("why batch-upload by clicking instead of calling the skill's JSON path?").
- Symptom: the UI edit form for a product does not bind the Slate editor state, so saving through the form persists name/specs/media but wipes the rich-text body; UI-only operation is both slower and lossy for body content.
- Evidence: a full JSON batch (2 categories + 6 products + 3 posts, created and published) via captured Server Actions was faster and, unlike UI save, preserved bodies; backend re-read confirmed `isDraft:false` with non-empty `content`. Publishing required the product-update action ID with `mode:'publish'` and all fields — injecting `isDraft:false` into an `update` body did nothing.
- Risk: defaulting to UI clicking for content batches loses body content silently and does not scale; assuming `isDraft:false` in an update body publishes leaves items as drafts.
- Rule: for content batches, capture the backend Server Actions once (per deployment) and replay them as JSON — do not hand-click the edit form for body-bearing entities. Treat the UI form as unsafe for Slate bodies. Publish via the update action with `mode:'publish'` and full fields; verify by re-reading `isDraft` and `content`. Contract shape, action table, publish semantics, `next-action` per-deployment drift, and the 503 / MongoDB transaction-conflict serial-retry rule are recorded in `server-action-save-api.md`.

- Context: editing theme (page-builder) block text/images on a live AllinCMS site during content replacement.
- Symptom: theme text/image edits were done one block at a time through the visual designer because the theme design-save Server Action was not captured *this turn* — but this is a capture-method problem, not an impossibility. The theme design-save (`POST /{siteKey}/themes/{themeId}/{pageId}/design`, body `[{...,intent:'save',pageDocument:{root,elements:{blockId:{type,props}}}}]`) is a real Server Action and was captured on a prior run (2026-06-29) via CDP Network; a late-injected `window.fetch` interceptor (used this turn) cannot catch it because Next captured `fetch` at bundle init, and the default Jotai store is empty (scoped store).
- Evidence: a repeatable half-auto method worked as the fallback (JS-click `[aria-label="Page context"]` to switch page via SPA soft-nav → Layers panel select block → React native value-setter to batch-fill inputs by `name` → top-bar Save + Publish; images via the media modal's URL tab), and produced professional per-page results across the whole site, but each block was a separate round trip. Separately, `request-capture.md` documents the captured `pageDocument` shape for a whole page — enough to build a JSON whole-page replay once the design-save action is captured by CDP.
- Risk: writing "theme cannot be JSON" anywhere in the skill is an overclaim that contradicts the 2026-06-29 CDP capture and would stop a later operator from JSON-ifying the last UI layer; conversely, assuming a late `window.fetch` patch will catch theme saves wastes a turn. Leaving theme edits UI-only also makes broad sweeps slow and misses below-fold/secondary generic content.
- Rule: theme design-save IS JSON-replayable — capture it via **CDP Network** (or a pre-bundle-init fetch hook / the scoped Jotai doc atom), then edit `pageDocument` block props and replay the whole page, exactly like content. A late-injected `window.fetch` interceptor is the wrong tool for theme (it works for content pages only). Until the design-save action is captured, use the React-setter + Save/Publish half-auto method (`server-action-save-api.md` §7). When replacing placeholder content, sweep every page (home below-fold, About, Contact, News/list intros, collection/related blocks, global Header/Footer/Contact-Dialog), not just the hero.

- Context: replacing a default theme's placeholder content on a brand-new site where some blocks assert social proof or a physical location.
- Symptom: the default template shipped a Social Proof (Quotes) block with fabricated reviews, named customers, and a "4.9 average" rating, and a Contact Location Map block with a fabricated street address, coordinates, and transit directions. Rewriting these into on-topic copy would still be fabricating testimonials/geography the new business does not have; leaving them shows another brand's fake data.
- Evidence: on a from-PDF site build, these two blocks had no truthful source in the brief. They were hidden via the Layers panel `Hide <block>` control (not filled with invented reviews/address) and recorded as "needs real data" deferrals; the fake contact values (email/phone/office/timezone) in the Contact Info and Contact Form blocks were neutralized to honest, form-directed placeholders ("Enquiries via this form", "Available on request", "Made to order, shipped worldwide") rather than invented real ones, and flagged as user-supplied PII.
- Risk: fabricating reviews, ratings, a physical address, or contact details on a live site is dishonest, can mislead customers, and (for contact PII) crosses the never-fabricate-contact-details rule. Filling placeholder blocks just to look complete manufactures false claims.
- Rule: never fabricate social proof (reviews, ratings, named customers), a physical location/map, or contact details (email, phone, address) to fill a default block. If there is no truthful source, hide the block and record it as a real-data deferral, or neutralize misleading foreign placeholders to honest form-directed copy. Only the user supplies real testimonials, address, and contact PII. Replacing content means replacing with what is true, not with a plausible invention.

- Context: an adversarial review of the skill (2026-07-03) converged on the pipeline being JSON-capable but under-gated at two silent-failure points identified in the ground truth.
- Symptom: two ground-truth failure modes have no automated gate — (1) an AI content pass can write a `content` field as a markdown string instead of a Slate node array, which passes casual review but produces an empty body on save; (2) a stale `next-action` ID (from a prior deployment) is reused for a batch and fails silently. Both are currently only prose warnings in `server-action-save-api.md`.
- Evidence: `validate_manifest.py` gates schema-verified manifests but does not assert `content` is `[{type,children,id}]` Slate shape; there is no `check_next_action_freshness`-style gate before batch. The review recommended both as the highest-value hardening for a stable end-to-end pipeline.
- Risk: without these gates the two most likely silent failures in a from-source build (markdown-in-body, stale action ID) surface only on the live frontend or in a backend re-read, after the batch has run.
- Rule: next build — add (a) a Slate-shape validator for every `content` field entering a manifest (reject markdown/HTML strings; require node arrays), and (b) a `next-action` freshness gate that refuses a batch unless the action IDs were captured against the current deployment. Each new script needs its own `test_*.py` (the `audit_test_entrypoints.py` discipline). Until built, treat the prose rules in `server-action-save-api.md` §3/§5 as the manual checklist.
- Context: 2026-07-04 exhaustive attempt to capture the theme design-save `next-action` id with the available Claude-in-Chrome MCP tools, to close full theme-JSON replay.
- Symptom: full theme-JSON replay needs the design-save `next-action` id plus the `pageDocument` body. The body is constructible from page state and validated by `validate_theme_page_document.py`, but the `next-action` id could not be obtained with the current bridge.
- Evidence: four JS-reachable capture paths were each tried and each blocked — (1) late-injected `window.fetch` interceptor: does not fire for the design-save (Next captured `fetch` at bundle init); (2) `read_network_requests`: confirms `POST /{siteKey}/themes/{themeId}/{pageId}/design` fires (200/503) but returns only url/method/status — no request headers, no postData; (3) the server-action reference `$$id` on the fiber: the Save button's `memoizedProps`/parent fibers expose no `react.server.reference` object — the action is held in a hook closure, which JS cannot read; (4) the scoped Jotai doc atom: `__JOTAI_DEFAULT_STORE__` is empty (the designer uses a Provider-scoped store that was not locatable). The 2026-06-29 capture that got the payload used a fuller CDP session that returns postData, which this MCP bridge does not expose.
- Risk: without recording this, a later operator re-runs the same four dead-ends. Treating theme-JSON as a skill defect (rather than an external-tooling ceiling) mis-frames the skill's maturity.
- Rule: full theme-JSON replay is blocked by tool capability, not by skill logic — it needs a CDP session (or a pre-bundle-init `fetch` hook the user installs) that exposes request `postData`/headers. Everything else is ready: endpoint confirmed live, body constructible, `validate_theme_page_document.py` gates the replay body. Until such a capture channel exists, the React-setter half-auto method (`server-action-save-api.md` §7.5) is the proven path (it edited the entire Example site). Do not re-attempt the four exhausted JS paths above; go straight to a CDP/postData channel when one is available.

- Update (2026-07-04): both gates are now BUILT and registered — `scripts/validate_slate_content_shape.py` (Slate node-array shape for `content`, run after the AI content pass and before sample/batch) and `scripts/check_next_action_freshness.py` (refuse a batch when the contract's `deploymentId` != the current live deployment, run right before the batch). Also added `scripts/validate_theme_page_document.py`, the local validator for a theme design-save `pageDocument` replay body — the local half of theme-JSON: once a live CDP capture supplies the current design-save `next-action` id, the whole-page replay is gate-validated (placeholder + local-image-path rejection under `--require-publication-ready`). The remaining live piece for full theme-JSON is capturing the design-save action via CDP (not a late `window.fetch` patch); see `server-action-save-api.md` §7.6.

- Context: 2026-07-04 audit proposed extracting a shared `_common.py` to remove the copy-defined helpers (`load_json` in 117 scripts, `write_json` in 96, `now_iso` in 93, `skill_root` in 49, `ensure_output_*` in ~50).
- Symptom: a full AST/body-hash analysis showed the "duplication" is not clean copies: `load_json` has **47 distinct implementations** across 117 files (SystemExit vs ValueError, different messages, str vs Path signatures, optional labels), `write_json` 11 variants, `ensure_output_outside_skill` 6 variants, `ensure_output_dir_outside_skill` 2. Only `skill_root` (1 variant) and `now_iso` (1 dominant of 2) are uniform.
- Evidence: blanket-unifying 47 `load_json` variants into one would change the error/return behaviour of ~90 scripts, roughly half of which have no direct test, for a maintainability-only gain invisible to how the skill executes (the operator reads SKILL.md/references, not the helper copies).
- Risk: a forced dedup trades real regression risk (untested error paths) for LOC reduction that does not make the skill run more efficiently; a partial migration also leaves the tree inconsistent.
- Rule: created `scripts/_common.py` as the go-forward canonical module (new scripts import `load_json/write_json/now_iso/skill_root/ensure_output_outside_skill` from it, so the duplication stops growing) with `test__common.py`. Do NOT retroactively force-migrate the 47-variant `load_json` etc.; leave the working divergent copies. Only 1-variant helpers (`skill_root`) are safe to consolidate if ever needed.

## 2026-07-27 Unlimited Strict-Serial AllinCMS Media Retry Finding

- Context: the canonical AllinCMS media adapter replaced the earlier ten-file controller cap and UI-first upload guidance.
- Symptom: treating “more than ten files” as a rate-limit condition unnecessarily split batches, while immediate retry after a timeout could duplicate a remote record whose first request actually succeeded. Generic browser-stage helpers also caused later agents to mistake “no generated media command” for “must use the file picker.”
- Evidence: the canonical controller accepts a 12-file local fixture with maximum concurrent uploads equal to one; its 29 adapter tests pass. Error-path tests prove the order `delay -> read-only reconciliation -> reuse existing or retry current image only after not_found_stop`.
- Risk: a worker pool, `Promise.all`, multiple tabs, immediate resend, or automatic PicGo/UI fallback can create duplicate records, break source-hash-to-URL mapping, or make another AI rediscover a contract that is already captured.
- Rule: file quantity is not the rate limiter. Accept any input count but keep every AllinCMS upload strictly serial. Default to three attempts per image with 2-second and 5-second delays. After an upload error, delay before read-only reconciliation; if the remote record is verified, index and reuse it without retransmission; retry only the current image after exact `not_found_stop`; stop the batch on ambiguous reconciliation or exhausted attempts. Metadata writes and deletes remain at-most-once on ambiguous outcomes.
- Routing: the canonical entry is `<SUB_LIBRARY_ROOT>/ADAPTERS/cms/allincms/AI-START-HERE.md`. The exact logged-in `/{siteKey}/media` page must be open and retained. UI file selection is approved fallback only; PicGo/R2/GitHub/COS/OSS are external-host alternatives only when explicitly selected.
