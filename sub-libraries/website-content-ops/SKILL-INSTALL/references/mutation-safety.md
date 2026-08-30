---
doc_id: allincms-bulk-mutation-safety
title: AllinCMS 远程变更授权
description: LAICMS / AllinCMS 建站、创建草稿、保存、发布、上传和清理删除前的动作级授权与记录规则
layer: ops
status: draft
created: 2026-06-29
updated: 2026-07-05
page_type: reference
sources: []
confidence: medium
---

# Mutation Safety

Use this reference before any LAICMS / AllinCMS action that can change remote state.

## Remote Mutations

Treat these as mutations:

```text
submit create-site form
click a content-type 创建 button that creates an Untitled draft
save/update an edit page
publish or unpublish
delete or archive
upload media or choose a local file for upload
create route, theme, form, category, tag, spec, or subroute
change site-info, tracking, domain, or theme settings
replay captured save requests
batch upload or batch publish
cleanup accidental drafts/probes
save or publish theme page design
set a theme page as homepage
enable a theme page
bind or rebind a route
```

Opening list pages, reading existing edit pages, and opening non-submitted dialogs are normally read-only. This is not guaranteed; if prior evidence shows the click creates a draft, treat the click itself as a mutation.

## Parallel Agent Boundary

Verification and exploration may be delegated to parallel agents only when the assigned task is read-only and independently scoped. Good examples are: checking a set of public frontend URLs, reading backend list/edit fields without submitting forms, reviewing local evidence JSON, or auditing skill documentation. Use parallelism for breadth and independent confirmation; keep decisions, sequencing, evidence merge, and all mutation gates in the main controller.

Default split candidates:

```text
frontend route audit: split URL groups by static pages, list pages, and detail pages
backend read-only audit: split modules such as products, posts, routes, themes, forms, domains
local evidence audit: split run-evidence, manifest, capture-plan, and skill-reference checks
adversarial review: assign one agent to look for overclaims and another to check missing proof
```

Do not delegate:

```text
clicking create/save/publish/delete/upload controls
JSON or Server Action replay
same edit page, same dialog, or same mutable browser tab
actions that may create drafts as a side effect
credential/session recovery
final decision that a stage is complete or launch-ready
```

Parallel agents must receive explicit constraints:

```text
allowed: navigate/read/screenshot/inspect local evidence
forbidden: create/save/publish/unpublish/delete/upload/replay requests/change settings
scope: exact URLs, files, or route patterns
output: concise findings with evidence, blockers, and whether any action looked mutating
```

Do not split one remote mutation across agents. The controller must perform any create, save, publish, route binding, theme setting, upload, cleanup, or JSON/Server Action replay itself after the action-specific authorization record and pre-mutation gate pass. If a delegated read-only check discovers that a click is likely mutating, it must stop and report the boundary instead of probing further.

Before using a subagent result as proof, the controller must reconcile it:

```text
1. Confirm the agent stayed within read-only scope.
2. Check that evidence includes URL/file path, observed status or fields, timestamp/run pointer, and blocker list.
3. Resolve conflicts between agents by rechecking the smallest disputed target in the main session.
4. Convert accepted findings into redacted run evidence, maintenance summary, or operational finding before final reporting.
5. Do not use subagent text alone as authorization, persistence proof, or launch completion proof.
```

## Authorization Record

Before mutating, record a short action plan:

```json
{
  "generatedAt": "YYYY-MM-DDTHH:MM:SS+00:00",
  "workspace": "https://workspace.laicms.com",
  "siteKey": "",
  "action": "",
  "targetType": "",
  "targetIdentifier": "",
  "fieldsOrFiles": [],
  "expectedResult": "",
  "verification": "",
  "cleanupPlan": ""
}
```

Proceed only if the user explicitly authorizes that action in the current run, if the user's latest instruction already names that exact action and target, or if a current-session test-site policy has been paired with an exact action record for this mutation.

A **run-scoped authorization** (`scripts/run_authorization.py`, granted once at content-review time and bound to one `siteKey` + the confirmed package hash) satisfies the per-action authorization requirement for an ALLOWLISTED content-build action only — `check_pre_mutation_gate.py --run-authorization --target ...` derives the per-action record and passes without re-prompting, while every other gate check still runs and each action is still recorded. It never covers a carve-out (new-site create, delete/cleanup/unpublish, outward-facing settings, any other site, or any non-allowlisted/unknown action): those raise "carve-out" and still require an explicit fresh `--authorization`. A gate failure still stops regardless. The grant also **expires** (`expiresAt`, default 8h TTL via `--ttl-hours`): past its TTL it stops auto-covering and the user must re-grant, so a stale grant from an earlier session can't silently keep authorizing — the grant is scoped to one build session, not indefinite.

For final mutation gates, `generatedAt` must be present and recent. Do not reuse an old authorization record, even if its action and target look correct; regenerate it from the current user instruction immediately before the mutation.
Generate fresh read-only/preflight evidence first, then generate the action authorization record. Do not create them in parallel for the same gate: the gate requires `authorization.generatedAt` to be at or after `preflight.generatedAt`, and parallel commands can race into a false failure even when both files are fresh.

Run `summarize_run_status.py` before asking for or acting on mutation authorization. If it reports `evidenceFreshness.freshForMutation: false` or emits `refresh_readonly_evidence`, re-open the relevant backend list/setup pages and regenerate read-only evidence first. The summary warning mirrors the final gate freshness window; it prevents preparing an authorization record against stale preflight evidence.

Use the authorization helper before any mutation:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_authorization_record.py \
  --action create_site \
  --target https://workspace.laicms.com/sites \
  --target-type site \
  --target-identifier pending-new-site \
  --fields-or-files name,description \
  --expected-result "new site card, backend dashboard, and default frontend open" \
  --verification-plan "verify site card, backend dashboard, frontend base URL, and module routes" \
  --cleanup-plan "no automatic deletion; stop before content upload" \
  --authorization-source "current user explicitly authorizes creating a site at https://workspace.laicms.com/sites with name and description" \
  --output ~/allincms-projects/allincms-authorization-create-site.json
```

The authorization helper supports granular theme launch actions such as `create_theme_page`, `save_design`, `publish_design`, `set_homepage`, `enable_theme_page`, and `bind_route`. It also supports content-type-specific probe creation actions such as `create_post_probe`, `create_product_probe`, and `create_form_probe`, plus `save_probe`, `publish_probe`, and `cleanup_probe` for the separate save/capture, sample publish, and cleanup steps. For existing non-probe launch/demo content, use `save_product`, `publish_product`, `save_post`, or `publish_post`. Use those exact actions instead of overloading generic `publish`, `create_draft`, `save`, or `delete_or_cleanup` when creating a theme page, editing page design, setting homepage, enabling a theme page, changing route bindings, creating a probe for a specific module, saving a probe to capture a request, publishing a probe for frontend verification, cleaning a probe, or updating one existing product/post.

The pre-mutation gate also supports site setup and launch actions: `save_site_settings`, `create_theme`, `activate_theme`, `create_theme_page`, `save_design`, `publish_design`, `set_homepage`, `enable_theme_page`, `bind_route`, `create_route`, and `create_form`. Run the gate before using either UI or JSON replay for these actions. The gate verifies same-site routing, target module, target type, recent timestamps, and action-specific proof fields; it does not prove the payload is correct by itself.

Browser-control telemetry or analytics warnings are not mutation proof. In-app browser output may include Statsig queue warnings or `ab.chatgpt.com` timeout errors while the LAICMS action itself succeeds, and the reverse is also possible. For save/publish decisions, rely on action-specific UI state, backend refresh, captured request/response when available, and public frontend DOM proof, not browser telemetry noise.

Whole-theme activation is `activate_theme`; do not use `enable_theme_page` for it. `enable_theme_page` covers one page row, while `activate_theme` changes which theme serves public routes. For default-theme bootstrap, use `prepare_default_theme_bootstrap.py`, then run `create_theme` and `activate_theme` separately with fresh authorization records and gates. Verify refreshed theme-list state, route mappings, and public route DOM. Do not treat a `主题已应用` toast alone as proof that the public site switched themes.

Current helper coverage is incomplete for the later form lifecycle. `create_form` covers the initial draft creation, but field editing, saving form settings/schema, publishing a form, embedding a form into a theme page, and testing a public submission are separate mutation stages. Until dedicated actions such as `edit_form_fields`, `save_form`, `publish_form`, `embed_form`, and `test_form_submission` exist, record the helper gap in the run evidence, scope the UI action to one concrete test-site form, capture the real request, and verify persistence immediately. Do not reuse `create_form` as if it authorized or gated later save/publish/embed actions.

The suggested authorization text emitted by local helpers may be Chinese or English. The authorization record validator must accept either language when the text still names the exact action, target URL, content type, and probe/draft intent. Do not weaken the requirement to make Chinese text pass; add explicit action terms such as 创建, 保存, 发布, 清理, 删除, or 取消发布.

The authorization source must name the exact action and target, or must combine a current-session test-site policy with an exact action record that names them. Do not treat these bare phrases alone as authorization:

```text
continue
go ahead
proceed
ok
逐个验证
继续
后续需要操作的，你直接进行
无需我授权
只需要最终结果
goal continuation
active thread goal
objective reminder
```

System or tool-provided continuation context is not action-time user authorization, even when it repeats the user's long-running objective. Treat it as a planning/continuation signal only. Before any remote mutation, require either the current user message itself to name the exact LAICMS action, target URL, content type, probe/test intent when applicable, and stop condition, or a current-session test-site policy plus an exact generated record that binds those fields.

If the user states a broad automation preference such as "do the later operations directly" or "do not ask me again", use it to reduce interruptions for local preparation, read-only verification, helper generation, and non-mutating gate checks. For remote mutations, that preference is usable only as a current-session authorization source when the generated authorization record still binds the exact action, target URL, target type, target identifier, expected result, verification plan, and cleanup/stop boundary. Bare continuation text remains invalid, and helper-suggested wording is still only a preparation artifact until the current user message or accepted current-session policy is paired with the exact action and target in the record.

For temporary/test-site buildouts, prefer the term `current-session test-site policy`: it authorizes the operating mode, not every possible action. Each create, save, publish, upload, settings, route, theme, form, or cleanup mutation still needs a local record with exact scope and a post-action report. If the current helper gate is narrower than the legitimate action, such as a probe-only content create gate rejecting a demo product title, record that as a gate coverage gap and proceed only when the UI target is unique, the affected content is test/demo scoped, and backend plus frontend verification will immediately follow.

Updating existing non-probe products or posts as legitimate demo/launch content requires the dedicated existing-content actions:

```text
save_product    fields: requestCapture, payloadShape, persistedVerified, bodyOrMediaAudit
publish_product fields: publishStatus, backendVerified, frontendVerified
save_post       fields: requestCapture, payloadShape, persistedVerified, bodyOrMediaAudit
publish_post    fields: publishStatus, backendVerified, frontendVerified
```

The target must be the concrete backend edit URL ending in `/update`, not the list URL or public slug. The target identifier must name the exact existing title or slug and must not contain `Codex Probe - Delete Me`. Save and publish stay separate because existing content saves can move a public item back to draft. `bodyOrMediaAudit` is required on save to prevent title/description-only updates from hiding starter body, specs, images, or placeholder residue. These actions authorize one existing row only; they do not authorize batch upload, JSON replay across multiple entries, deletion, or production-site rollback.

Current helper coverage is incomplete for taxonomy category/tag creation, update, and rename actions. The helper and final gate do not yet model `create_category`, `update_category`, `rename_category`, `create_tag`, `update_tag`, or `rename_tag` for product or post taxonomy tabs. Until those actions exist, use an exact local action record naming the module, taxonomy tab URL, old and new category/tag identifiers, fields changed (`name`, `slug`, `description`, cover if touched), expected backend refresh proof, frontend list/detail chip proof, and abort condition. Keep changes small and verify immediately; do not treat a broad site-settings record as permission for taxonomy batch operations.

Examples:

```text
valid only when paired in the record with exact action/target:
后续需要操作的，你直接进行，无需我授权，我只需要最终你给我结果；current stage target https://workspace.laicms.com/{siteKey}/themes/{themeId} create_theme_page /products/{product}
现在是测试，随便搞；current stage target https://workspace.laicms.com/{siteKey}/products create demo product {demoProductTitle}

still invalid:
继续
go ahead
后续需要操作的，你直接进行
```

Browser-stage authorization packages are preparation artifacts, not authorization records. After generating one with `prepare_browser_stage_authorization.py`, validate it before asking the user to authorize or before running any generated command:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_browser_stage_authorization_package.py \
  ~/allincms-projects/allincms-browser-stage-authorization-package.json \
  --packet-json ~/allincms-projects/allincms-next-browser-stage-packet.json \
  --preflight ~/allincms-projects/allincms-preflight-or-site-evidence.json
```

The validator must keep the warning that the package is not user authorization and must keep `<paste current user authorization text here>` inside `authorizationRecordCommand`. If either is missing, stop and regenerate or fix the package; do not replace the placeholder with old chat text or helper-generated suggested wording.

For probe creation actions, the source must also name both the content type and probe/draft intent. These are different permissions:

```text
create product probe draft at https://workspace.laicms.com/{siteKey}/products
create post probe draft at https://workspace.laicms.com/{siteKey}/posts
create form probe draft at https://workspace.laicms.com/{siteKey}/forms
```

Do not accept "create probe" without the content type, and do not accept "create product" as permission for `create_product_probe` unless the user also says probe, draft, test, or an equivalent Chinese term such as 探针 / 探测 / 测试 / 草稿.

Before clicking a content-type create button for a probe, run the final local gate with the current read-only site evidence and the fresh authorization record:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action create_product_probe \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-create-product-probe.json
```

The gate must verify the same site key, module route, content type, target URL, `Codex Probe - Delete Me` target identifier, non-empty probe fields, and recent timestamps. Use `create_post_probe` or `create_form_probe` for those modules; do not use a generic `create_draft`.

Before saving a probe, run the save gate:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action save_probe \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-save-product-probe.json
```

This gate must verify the target edit URL belongs under the same `{siteKey}/{contentType}` route, the target identifier includes `Codex Probe - Delete Me`, and `fieldsOrFiles` includes `requestCapture`, `payloadShape`, and `persistedVerified`.

Before publishing a probe, run the publish gate:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action publish_probe \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-publish-product-probe.json
```

This gate must verify the target edit URL belongs under the same `{siteKey}/{contentType}` route, the edit field evidence includes a publish control, the target identifier includes `Codex Probe - Delete Me`, and `fieldsOrFiles` includes `publishStatus` and `frontendVerified`.

Before mutating theme, route, form, or site settings state, run the site-action gate with a fresh authorization record:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action save_design \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-save-design.json
```

Examples of required `fieldsOrFiles`:

```text
save_design: requestCapture,pageDocument,persistedVerified
publish_design: publishStatus,frontendVerified
create_theme_page: requestCapture,pageId,routePath,backendVerified
set_homepage: homepage,frontendVerified
enable_theme_page: enabled,frontendVerified
bind_route: routePath,boundPage,frontendVerified
create_route: routePath,backendVerified,frontendVerified
create_theme: requestCapture,themeId,backendVerified
activate_theme: themeId,routeMappingReviewed,themeEnabled,frontendVerified
create_form: requestCapture,formId,backendVerified
form save/publish/embed: helper coverage gap until granular actions exist; require exact local action record plus immediate backend/frontend proof on test sites
save_site_settings: fieldMapping,persistedVerified
```

## Probe Naming

New probe content must use an obvious cleanup prefix:

```text
Codex Probe - Delete Me
```

If the platform creates an automatic draft before fields can be edited, immediately rename it to the probe name before saving any meaningful payload, or stop and ask before continuing.

## Accidental Draft Handling

If exploration creates an unintended draft:

1. Stop creating more records.
2. Record only neutral evidence:

   ```text
   content type
   title/name pattern, for example Untitled Post <timestamp>
   status, for example 草稿
   backend list page where it appears
   ```

3. Do not delete, publish, unpublish, or edit it without explicit cleanup authorization.
4. If cleanup is authorized, verify the entry disappears from the backend list and its frontend URL does not render published content.

When reporting cleanup as completed, record:

```text
cleanedCount
cleanedCandidates as objects with contentType, redacted titlePattern, backendUrl, and reason
backendVerified: true only after the cleaned entry is absent from the backend list/search
frontendVerified: true only after the cleaned frontend URL returns 404 or no longer renders the probe
backendEvidence: short neutral proof, no raw IDs or business copy
frontendEvidence: short neutral proof, no raw IDs or business copy
```

Do not use plain strings for completed cleanup candidates. Each candidate backend URL must belong to the verified site key.

Cleanup completion must have action-specific authorization:

```json
{
  "authorization": {
    "userAuthorized": true,
    "authorizedAction": "cleanup/delete/unpublish LAICMS probe drafts",
    "target": "https://workspace.laicms.com/{siteKey}/posts",
    "authorizationSource": "current user instruction",
    "verificationPlan": "verify backend list and frontend URLs after cleanup"
  }
}
```

Do not reuse site creation, upload, publish, or generic continuation authorization as permission to delete, unpublish, or clean records.

Before cleaning a probe, run the cleanup gate:

```bash
python3 skills/allincms-bulk-content-upload/scripts/check_pre_mutation_gate.py \
  --action cleanup_probe \
  --preflight ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --authorization ~/allincms-projects/allincms-authorization-cleanup-product-probe.json
```

This gate must verify the target edit/list URL belongs under the same `{siteKey}/{contentType}` route, the target identifier includes `Codex Probe - Delete Me`, and `fieldsOrFiles` includes `cleanedCandidates`, `backendVerified`, and `frontendVerified`.

Do not mark cleanup completed if the item was only found, queued, deferred, or left for the user.

## Cleanup Authorization Phrase

Ask for concrete authorization, not a vague "continue":

```text
请确认是否允许我删除/清理这些 LAICMS 草稿：
- posts: Untitled Post <timestamp>, status 草稿
- products: Untitled Product <timestamp>, status 草稿
- forms: Untitled Form <timestamp>, status 草稿
```

## Final Mutation Report

After any mutation, report:

```text
action attempted
target site/content type
created/updated/deleted/published count
backend verification
frontend verification, if applicable
remaining cleanup candidates
```
