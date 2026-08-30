---
doc_id: allincms-bulk-e2e-simulation
title: AllinCMS 端到端模拟实操
description: LAICMS / AllinCMS 从建站入口到内容上传、发布、前台核验和清理的端到端模拟检查清单
layer: ops
status: draft
created: 2026-06-29
updated: 2026-07-03
page_type: reference
sources: []
confidence: medium
---

# E2E Simulation

Use this reference when the user asks to simulate the whole workflow from site creation through content upload while improving this skill.

This is an orchestration checklist. Load the referenced files for details instead of duplicating their procedures.

## Authority Order

```text
1. mutation-safety.md for authorization and cleanup boundaries
2. site-creation.md for site list, create-site dialog, and first-site setup pages
3. create-flows.md before clicking create/upload controls
4. field-mapping.md and field-contract.md for content model inspection
5. request-capture.md before saving or replaying requests
6. server-action-save-api.md before any JSON/Server-Action content batch
7. batch-verification.md for sample upload, publish, cleanup, and final QA
8. live-verification-*.md only as orientation, never as cross-site schema authority
```

> **Simulation is not the default execution mode — it is how you probe once, then hand off to JSON.** Per the SKILL.md JSON-first split rule: for content (categories/products/posts), a UI probe exists only to confirm the content type and capture one real save (its `next-action`); after that, batch via JSON replay (`server-action-save-api.md`), do not walk every entry through the UI. The full designer/UI lifecycle is required only for the genuinely-UI-only layers (site create, default-theme bootstrap, media upload) and, until its design-save action is CDP-captured, theme editing. Content `content` bodies never persist through a UI form save (the form does not bind Slate) — they must go through JSON.

## Read-Only Simulation Path

These steps should be possible without remote mutation:

```text
open workspace dashboard
open /sites
open create-site dialog and record fields, then close it and verify no visible dialog remains
open an existing site's dashboard
inspect site-info, domains, themes, routes, forms without saving
inspect posts/products/media list pages without clicking create
open existing content edit pages without saving
inspect route bindings and frontend list/detail pages
run local manifest and skill hygiene validators
```

If any step unexpectedly creates or changes remote data, stop and switch to `mutation-safety.md`.

## Mutation Path

These steps require explicit action-time authorization:

```text
submit create-site form
click posts/products 创建 when the platform creates Untitled drafts
save a probe item
publish/unpublish a probe item
upload media
create route/theme/form/category/tag/spec
delete or clean accidental drafts/probes
batch upload or batch publish
```

Use this authorization record before each mutation:

```json
{
  "action": "",
  "siteKey": "",
  "targetType": "",
  "targetIdentifier": "",
  "data": [],
  "expectedResult": "",
  "verificationPlan": "",
  "cleanupPlan": ""
}
```

## Evidence Checklist

Record these neutral facts as the run progresses:

```text
workspace URL
site list URL
create-site fields
siteKey
frontend base URL
dashboard module routes
site-info fields
domain/CNAME controls
theme controls
route columns and route patterns
form columns
content type inspected
list columns
edit fields
save request captured or not captured
sample backend verification
sample frontend verification
cleanup candidates
cleanup completion
```

Do not record business copy, account email, real content titles, raw content IDs, customer names, or source-site topics in the skill.

## Run Evidence JSON

Before claiming completion, write a local run evidence JSON and validate it:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_run_evidence.py run-evidence.json
python3 skills/allincms-bulk-content-upload/scripts/summarize_run_status.py run-evidence.json
```

The evidence file is a run artifact, not skill documentation. Store it in a temporary run directory or the user's chosen project log; do not copy raw browser evidence into this skill unless it is neutral, redacted platform behavior.

If the turn is documentation-only, helper-script maintenance, planning, discussion, request analysis, or validation-only and no current run evidence exists, do not reuse an old browser or rehearsal summary for closeout. Generate a maintenance summary instead:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_round_maintenance_summary.py \
  --output ~/allincms-projects/allincms-maintenance-summary.json \
  --sedimentation updated \
  --note "Recorded reusable maintenance finding in operational-findings.md." \
  --changed-files "skills/allincms-bulk-content-upload/SKILL.md,skills/allincms-bulk-content-upload/references/operational-findings.md" \
  --round-issue "Maintenance closeout exposed a reusable command or documentation finding."
python3 skills/allincms-bulk-content-upload/scripts/check_round_closeout.py \
  --summary ~/allincms-projects/allincms-maintenance-summary.json \
  --sedimentation updated \
  --note "Recorded reusable maintenance finding in operational-findings.md." \
  --changed-files "skills/allincms-bulk-content-upload/SKILL.md,skills/allincms-bulk-content-upload/references/operational-findings.md" \
  --round-issue "Maintenance closeout exposed a reusable command or documentation finding."
```

This maintenance summary satisfies the per-turn sedimentation reporting gate only. It is not launch, upload, publish, cleanup, request-capture, or frontend persistence evidence.

The validator rejects account emails, contact emails, and business-domain residue. Redact site copy and account identifiers before writing evidence.

When present, `generatedAt` and `preflightGeneratedAt` must be ISO 8601 timestamps with timezone. `generatedAt` records when the evidence artifact was generated; it does not replace action-specific authorization. Created-site evidence must keep `preflightGeneratedAt` from the pre-submit evidence and write a fresh `generatedAt` after post-create verification.

The validator checks structural safety, not proof freshness. If a run evidence file says a page was "previously verified", "not re-opened", or otherwise uses old observations, treat it as a partial/local check only. Do not use it to claim the full end-to-end simulation is complete.

Use the status summary for every closeout. Report `proven`, `missing`, `completionGaps`, and `nextActions` in plain language. If `complete` is false or `completionGaps` is non-empty, do not mark the goal or run as complete even when validation passed.

If the user's objective says to start from creating a site, run the summary with `--require-created-site`. This makes `site_created_and_verified` mandatory and prevents an `existing_site_selected` run from being counted as a from-scratch build:

```bash
python3 skills/allincms-bulk-content-upload/scripts/summarize_run_status.py \
  --require-created-site run-evidence.json
```

When `summarize_run_status.py` emits `nextActionDetails`, use it as the handoff for the next authorized mutation: it should include the exact backend target, suggested user authorization text, the `make_authorization_record.py` command, and the `check_pre_mutation_gate.py` command. This applies to create-site preflight (`authorize_create_site`), content probe creation (`authorize_content_probe`), and the later probe stages (`authorize_save_probe`, `authorize_publish_probe`, `authorize_cleanup_probe`). Do not invent a browser mutation flow for a module unless the local authorization helper and pre-mutation gate already support that exact action. For unsupported modules, first extend and test the helper/gate, then update this skill.

Use the next action as a single-stage handoff, not as permission to run the whole chain. If probe creation is done but request capture is missing, the next action should be `authorize_save_probe`. If request capture is proven but backend/frontend sample verification is missing, the next action should be `authorize_publish_probe`. If the sample is verified and cleanup is pending, the next action should be `authorize_cleanup_probe`.

For broader real-browser work, generate a staged execution plan after the full local rehearsal:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_browser_execution_plan.py \
  ~/allincms-projects/allincms-full-rehearsal/full-e2e \
  --handoff-json ~/allincms-projects/allincms-full-rehearsal/next-capture-handoff/handoff.json \
  --launch-plan-json ~/allincms-projects/allincms-full-rehearsal/launch-plan.json \
  --output ~/allincms-projects/allincms-full-rehearsal/browser-execution-plan.json
python3 skills/allincms-bulk-content-upload/scripts/validate_browser_execution_plan.py \
  ~/allincms-projects/allincms-full-rehearsal/browser-execution-plan.json
```

The execution plan is a local-only runbook, not authorization. Use it to keep site creation, setup inspection, module request capture, theme/page/route launch, content probe, schema gate, batch upload, forms/media/settings, final audit, and cleanup as separate stages. A `requires_authorization` stage needs a fresh action-time user authorization and matching gate before any browser or JSON mutation.

After generating the execution plan, build a ledger before touching the browser:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_browser_execution_ledger.py \
  ~/allincms-projects/allincms-full-rehearsal/browser-execution-plan.json \
  --output ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.json
python3 skills/allincms-bulk-content-upload/scripts/validate_browser_execution_ledger.py \
  ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.json
```

The ledger is the stage-by-stage progress file. It should expose only the next safe `ready` stage while dependencies remain incomplete. After a real browser stage completes, record a redacted stage result outside the skill or in the user's chosen run directory, validate it against the packet, and apply it with `scripts/apply_browser_stage_result.py --result-json`. Do not rebuild the ledger from completed stage ids, and do not mark a later mutation stage ready just because the static plan lists it.

For the actual next browser step, build a single-stage packet from the ledger:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_browser_stage_packet.py \
  ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.json \
  --output ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet.json
python3 skills/allincms-bulk-content-upload/scripts/validate_browser_stage_packet.py \
  ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet.json
```

Use the packet, not the whole execution plan, as the browser operator's immediate instruction. It contains the one ready `stageId`, target template, allowed actions, required proof, stop condition, evidence-capture template, and ledger-update command. If the packet says `authorizationRequired: true`, treat its authorization text as a template only; wait for explicit action-time user approval before touching the browser.

After applying a stage result, use `ledger.nextStageId` as the authoritative next-step pointer and build a new packet from that ledger. Do not decide there is no ready stage by filtering `stages[].status == "ready"`; the ledger-level pointer is the packet-builder contract.

After the stage finishes, validate and apply a redacted stage result instead of hand-editing the ledger:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_browser_stage_result.py \
  --packet-json ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet.json \
  --status completed \
  --evidence-pointers ~/allincms-projects/allincms-stage-proof/redacted-proof.json \
  --output ~/allincms-projects/allincms-stage-result.json
python3 skills/allincms-bulk-content-upload/scripts/validate_browser_stage_result.py \
  ~/allincms-projects/allincms-stage-result.json \
  --packet-json ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet.json
python3 skills/allincms-bulk-content-upload/scripts/apply_browser_stage_result.py \
  --ledger ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.json \
  --packet ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet.json \
  --result-json ~/allincms-projects/allincms-stage-result.json \
  --output ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.updated.json
```

The stage result artifact is always local evidence: keep `localOnly: true` and `remoteMutationsPerformed: false` because the helper is not itself mutating LAICMS. Use the packet's `remoteMutationExpectation` to decide the browser-stage effect:

```text
must     -> completed result must set browserStageMutatedRemote: true
may      -> set true only when the authorized browser action actually changed remote state
must_not -> result must keep browserStageMutatedRemote: false
```

This is separate from authorization. The flag records what already happened during that one browser stage; it does not grant permission to mutate another stage.

If you use `apply_browser_stage_result.py` without `--result-json`, the inline `--stage-id/--status` result is still validated against the packet before the ledger is updated. For a completed result, `--proof-recorded` must include every packet `requiredProof`; otherwise the command must fail. Prefer `make_browser_stage_result.py` when possible because it defaults completed proof labels from the packet and keeps the result artifact inspectable.

`make_browser_stage_result.py` must also run final packet-aware validation after applying `--operator-note`. Operator notes are part of the stored result and must not contain emails, account data, raw IDs, concrete frontend origins, or other unredacted material.

For completed stages, the result must include every `requiredProof` from the packet plus redacted evidence pointers. For blocked stages, record blocking issues and do not mark the stage completed. For partial stages, record the proof that was captured plus the explicit remaining coverage/blocker; the ledger must keep the current stage blocked/partial and must not unlock dependent stages. The updated ledger computes the next ready stage; generate a fresh packet before continuing.

The packet's `evidenceCaptureTemplate.status` must list all valid stage-result statuses:

```text
completed|blocked|partial
```

Do not use older templates that list only `completed|blocked`. A partial result is the normal safe outcome for one-module capture, incomplete launch proof, partial audit proof, incomplete sample verification, partial batch verification, or incomplete cleanup proof.

The packet's `ledgerUpdate.commandTemplate` must use `scripts/apply_browser_stage_result.py` with `--result-json`, and `ledgerUpdate.stageResultRequired` must be `true`. Do not use `build_browser_execution_ledger.py --completed-stage-ids` as the browser-stage update path; that rebuilds status from a list and drops the redacted evidence pointers, partial/blocking issues, proofRecorded, and last-applied result data needed for audit. Packet metadata may expose `expectedCompletedStageIdsAfterApply` for audit, but must not expose a `completedStageIds` field because that name suggests the old list-based update path.

If a partial stage has no ready successor, do not hand-edit the ledger or regenerate from the static plan. Resume only by explicitly selecting the same partial stage:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_browser_stage_packet.py \
  ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.partial.json \
  --stage-id theme_page_route_launch \
  --output ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet.recovery.json
```

The recovery packet must say `recovery: true`, target the same `stageId`, and allow only the missing proof listed in the partial stage's blockers. Apply the later completed/partial/blocked result against that recovery packet. Only a completed recovery result may unlock the next dependent stage.

Persist every recovery packet as an artifact, not only as an in-memory object. A full rehearsal summary should include:

```text
browserStagePacketAfter<Stage>PartialRecoveryPath
browserStagePacketAfter<Stage>PartialRecoverySafety
<stage>PartialSimulation.recoveryPacketStageId
<stage>PartialSimulation.recoveryPacket: true
artifacts.browserStagePacketAfter<Stage>PartialRecovery
```

This applies to non-module partial gates after theme/page launch, static frontend audit, content probe creation, save-request capture, sample publish/verify, manifest schema gate, batch upload, forms/media/settings, final frontend audit, and cleanup. Without a persisted recovery packet, the completion result cannot be independently checked against the exact same-stage recovery instructions.

Evidence pointers must be inspectable references, not plain status text. Acceptable examples include `local://redacted-readonly-scan.json`, `~/allincms-projects/allincms-run/redacted-stage-result.json`, `./run-evidence/stage.json`, or a redacted `https://workspace.laicms.com/{realSiteKey}/...` URL. Reject placeholders such as `done`, `ok`, `verified`, or `see browser`; those are notes, not evidence locations.

When a stage-result evidence pointer uses a workspace backend URL, redact the site segment as `{realSiteKey}`. Store `https://workspace.laicms.com/{realSiteKey}/products` or a local redacted scan path, not `https://workspace.laicms.com/abc123/products`. `/sites` is allowed because it is not tied to a single site key.

For `module_interface_capture`, also update the module/action coverage ledger:

```bash
python3 skills/allincms-bulk-content-upload/scripts/update_module_capture_coverage.py \
  --plan ~/allincms-projects/allincms-full-rehearsal/full-e2e/03-module-interface-plan/module-capture-plan.json \
  --result-json ~/allincms-projects/allincms-module-capture-stage-result.json \
  --existing-coverage ~/allincms-projects/allincms-module-capture-coverage.json \
  --output ~/allincms-projects/allincms-module-capture-coverage.json
```

The first capture can be useful proof, but it should leave `complete: false`, `jsonReplayReady: false`, and `nextUncapturedStageKey` populated unless every planned capture stage is already captured or explicitly marked not applicable.

When coverage remains incomplete, sync the coverage back to the browser execution ledger so only the next missing module/action capture is ready:

```bash
python3 skills/allincms-bulk-content-upload/scripts/update_module_capture_coverage.py \
  --plan ~/allincms-projects/allincms-full-rehearsal/full-e2e/03-module-interface-plan/module-capture-plan.json \
  --result-json ~/allincms-projects/allincms-module-capture-stage-result.json \
  --existing-coverage ~/allincms-projects/allincms-module-capture-coverage.json \
  --sync-ledger ~/allincms-projects/allincms-browser-execution-ledger.json \
  --ledger-output ~/allincms-projects/allincms-browser-execution-ledger.after-coverage-sync.json \
  --output ~/allincms-projects/allincms-module-capture-coverage-and-ledger.json
```

The command outputs a wrapper with `coverage` and `ledger` when `--sync-ledger` is used; `--ledger-output` also writes the synced ledger as a standalone file. Use that synced ledger to build the next packet. The synced ledger should expose `module_interface_capture` again with an action such as `capture next module/action coverage stage: posts:create`. It must not expose theme/page launch, settings/media mutation, or batch upload until coverage is complete.

When every planned capture stage is captured or explicitly marked not applicable, sync coverage again. Only then may the aggregate `module_interface_capture` stage become completed and unlock the next browser packet:

```text
module capture coverage complete
-> sync coverage to ledger
-> module_interface_capture status becomes completed
-> next packet becomes theme_page_route_launch
```

This unlock proves the local state model only. Real LAICMS launch work still requires a fresh action-time authorization and the theme/page/route gates.

After the `theme_page_route_launch` packet is generated, treat launch as its own partial/complete gate:

```text
partial theme launch proof
-> active theme or published pages alone
-> apply stage result as partial
-> theme_page_route_launch remains partial
-> nextStageId remains empty
-> static_frontend_audit, content probe, upload, and forms/media/settings stay locked

complete theme launch proof
-> active theme
-> pages published
-> pages enabled
-> routes bound
-> frontend HTTP ok
-> frontend DOM verified
-> apply stage result as completed
-> next packet becomes static_frontend_audit
```

The static frontend audit packet is verification mode and does not require mutation authorization. This does not grant permission to create content probes, upload content, or change forms/media/settings. Forms/media/settings mutation should remain behind the later batch/upload chain unless a future plan deliberately splits it with its own dependency proof and authorization gate.

Static frontend audit also has a partial/complete gate:

```text
partial static audit proof
-> expected status map or redacted audit exists
-> at least one route still lacks frontendRendering proof or has blocking issues
-> apply stage result as partial
-> static_frontend_audit remains partial
-> nextStageId remains empty
-> content_probe_create, save_request_capture, and upload stay locked

complete static audit proof
-> expected status map
-> redacted frontend audit
-> frontendRendering evidence
-> all expected static routes pass
-> apply stage result as completed
-> next packet becomes content_probe_create
```

The content-probe packet is a mutation stage and must wait for fresh action-time authorization. A clean static audit is not permission to create drafts.

Content probe creation has its own partial/complete gate:

```text
partial content-probe proof
-> action-time authorization exists
-> probe/test naming is visible
-> backend draft row or edit URL is still missing
-> apply stage result as partial
-> content_probe_create remains partial
-> nextStageId remains empty
-> save_request_capture, publish, and upload stay locked

complete content-probe proof
-> action-time authorization
-> probe/test naming proof
-> backend draft proof, such as redacted list row or edit URL
-> apply stage result as completed
-> next packet becomes save_request_capture
```

The save-request packet is another mutation stage. Do not treat successful probe creation as permission to save content, capture a payload, publish, or upload a batch.

Save request capture also has a partial/complete gate:

```text
partial save-request proof
-> request URL/method/headers or payload shape exists
-> fieldMapping or backend persistence proof is still missing
-> apply stage result as partial
-> save_request_capture remains partial
-> nextStageId remains empty
-> publish_sample_verify, manifest_schema_gate, and upload stay locked

complete save-request proof
-> request URL
-> method
-> required headers
-> payloadTemplate
-> fieldMapping
-> backend persistence proof
-> apply stage result as completed
-> next packet becomes publish_sample_verify
-> manifest_schema_gate may also be ready, but it is not the next packet while publish_sample_verify appears first
```

Do not use a partially captured payload as a schema-verified upload template. The manifest schema gate may only pass after the current site and content type have a completed save-request capture.

Sample publish/verify also has a partial/complete gate:

```text
partial sample proof
-> backend published status or frontend detail 200 exists
-> title/name, cover/media, or structured body proof is still missing
-> apply stage result as partial
-> publish_sample_verify remains partial
-> batch_upload_publish, forms/media/settings, cleanup, and final audit stay locked
-> manifest_schema_gate may remain the next packet if it was already ready after save-request capture

complete sample proof
-> backend published status
-> frontend detail 200
-> title/name proof
-> cover/media proof
-> structured body proof
-> apply stage result as completed
-> next packet becomes manifest_schema_gate
-> batch_upload_publish stays pending until manifest schema gate passes
```

Do not treat a frontend 200 or backend published status alone as sample verification. Rich text, media, and displayed title/name must be checked before batch upload.

Manifest schema gate also has a partial/complete gate:

```text
partial manifest proof
-> validate_manifest.py pass
-> validate_manifest.py --require-schema-verified is missing or failed
-> apply stage result as partial
-> manifest_schema_gate remains partial
-> nextStageId remains empty
-> batch_upload_publish, forms/media/settings, and final audit stay locked

complete manifest proof
-> validate_manifest.py pass
-> validate_manifest.py --require-schema-verified pass for current site/content type
-> apply stage result as completed
-> next packet becomes batch_upload_publish
-> batch_upload_publish requires fresh mutation authorization
```

Do not upload from a manifest that only passes generic draft validation. Batch upload requires schema-verified validation from the same captured payload template and field mapping.

Batch upload/publish also has a partial/complete gate:

```text
partial batch proof
-> schema gate pass
-> sample verification pass
-> progress log exists, or only some frontend detail routes are verified
-> apply stage result as partial
-> batch_upload_publish remains partial
-> nextStageId remains empty
-> forms_media_settings, final_frontend_audit, and cleanup stay locked

complete batch proof
-> schema gate pass
-> sample verification pass
-> progress log
-> duplicate-slug handling, if any duplicates occurred
-> frontend detail audit for every uploaded route
-> apply stage result as completed
-> next packet becomes forms_media_settings
-> forms_media_settings requires fresh mutation authorization
```

Do not start forms/media/settings or cleanup from a partially uploaded batch. Treat every broken detail route, missing cover/media, stale draft, duplicate slug, or unverified status as a batch-stage blocker.

Forms/media/settings also has a partial/complete gate:

```text
partial forms/media/settings proof
-> action-specific request capture
-> backend persisted proof
-> public or integration effect proof is missing where applicable
-> apply stage result as partial
-> forms_media_settings remains partial
-> nextStageId remains empty
-> final_frontend_audit and cleanup stay locked

complete forms/media/settings proof
-> action-specific request capture
-> backend persisted proof
-> public or integration effect proof where applicable
-> apply stage result as completed
-> next packet becomes final_frontend_audit
-> final_frontend_audit is verification mode and does not require mutation authorization
```

Do not treat settings save success as launch readiness. Domain, tracking, form, and media changes may require public route, DNS, integration, or rendered media proof before final audit can begin.

Final frontend audit also has a partial/complete gate:

```text
partial final frontend audit proof
-> HTTP status report
-> DOM/rich-text report
-> image report exists
-> broken-entry list is not empty, missing, or unresolved
-> apply stage result as partial
-> final_frontend_audit remains partial
-> nextStageId remains empty
-> cleanup_probes stays locked

complete final frontend audit proof
-> HTTP status report
-> DOM/rich-text report
-> image report
-> broken-entry list empty
-> apply stage result as completed
-> next packet becomes cleanup_probes
-> cleanup_probes requires fresh cleanup authorization
```

Do not start cleanup from a partial final audit. Broken links, missing images, raw Markdown residue, wrong route status, stale drafts, or unresolved detail pages must be fixed or explicitly resolved before deleting or unpublishing probes.

Cleanup also has a partial/complete gate:

```text
partial cleanup proof
-> cleanup authorization
-> candidate list
-> backend cleanup proof or frontend non-public proof is missing
-> apply stage result as partial
-> cleanup_probes remains partial
-> nextStageId remains empty
-> do not claim the run is closed

complete cleanup proof
-> cleanup authorization
-> candidate list
-> backend cleanup proof
-> frontend non-public proof
-> apply stage result as completed
-> nextStageId remains empty
-> all ledger stages are completed
-> building another next-stage packet is rejected because no stage is ready
```

Do not treat a candidate search, authorization record, or cleanup intent as cleanup completion. Backend absence/unpublished state and frontend 404/non-public proof are both required before the simulated chain can close.

After cleanup completion, record a final ledger exhaustion check in the rehearsal summary:

```text
finalLedgerExhaustion.allStagesCompleted: true
finalLedgerExhaustion.nextStageId: ""
finalLedgerExhaustion.packetBuildRejected: true
finalLedgerExhaustion.rejectionReason contains "no nextStageId"
```

This is the stop proof for the browser runbook. Do not generate another browser-stage packet or continue operating the real backend after all stages are complete unless a new objective, new plan, and new authorization are created.

The ledger must preserve each stage's planned actions even while the stage is pending. When a dependency becomes complete, the newly ready stage should recover its concrete allowed actions, not a generic "continue" placeholder. The `create_site_submit` stage is special because it targets `https://workspace.laicms.com/sites` before a real site key exists; its authorization packet should contain the `/sites` target instead of requiring `{realSiteKey}`.

If a real read-only refresh proves that the operator should continue on an existing site instead of creating another site, branch the ledger before any mutation:

```bash
python3 skills/allincms-bulk-content-upload/scripts/branch_existing_site_ledger.py \
  --ledger ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.after-refresh_readonly_site_evidence.json \
  --existing-site-evidence ~/allincms-projects/allincms-existing-site-readonly-evidence.json \
  --output ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.existing-site-continuation.json
python3 skills/allincms-bulk-content-upload/scripts/build_browser_stage_packet.py \
  ~/allincms-projects/allincms-full-rehearsal/browser-execution-ledger.existing-site-continuation.json \
  --output ~/allincms-projects/allincms-full-rehearsal/next-browser-stage-packet-existing-site-setup.json
```

This branch is local bookkeeping only. It skips `create_site_submit`, unlocks read-only `setup_pages_inspection`, and must not be reported as from-scratch site creation proof.

After a create-site result is applied, generate the next packet from the updated ledger and verify it is `setup_pages_inspection`. That stage must remain read-only: inspect `site-info`, `domains`, `themes`, `routes`, and `forms`; record fields, columns, and controls; then stop. Do not proceed from successful site creation directly to theme launch or content upload.

When collecting setup-page proof from the browser, redact before writing evidence to disk. The layout shell can expose account email, site switcher text, frontend domain, and editable site business copy in generic button/input/body text. Preserve only neutral fields, placeholders, control labels, table headers, row counts, and redacted backend URL patterns such as `https://workspace.laicms.com/{realSiteKey}/routes`.

After setup inspection is applied, generate the next packet and verify it is `module_interface_capture`. This is the first post-setup stage that requires action-time authorization. It should capture exactly one module/action interface, classify whether a real mutation request exists, update module capture coverage, sync coverage back to the ledger, and stop before any replay or second module capture. Apply the browser-stage result as `partial` unless the run has a current, explicit coverage rule proving the entire interface-capture stage is complete; one captured module/action is not enough to unlock theme/page launch, forms/media/settings mutation, or batch upload.

When claiming the full end-to-end simulation is complete, set:

```json
{
  "completionClaimed": true
}
```

With `completionClaimed: true`, evidence must be current. The validator rejects stale markers such as `previously verified`, `not re-opened`, `prior run`, or equivalent wording.

Minimum create-site preflight shape:

```json
{
  "generatedAt": "YYYY-MM-DDTHH:MM:SS+00:00",
  "mode": "read_only_simulation",
  "workspaceUrl": "https://workspace.laicms.com",
  "siteListUrl": "https://workspace.laicms.com/sites",
  "siteCreation": {
    "status": "create_preflight_verified",
    "existingSiteKeysBeforeCreate": ["old-site-a", "old-site-b"],
    "createSiteFields": ["name", "description"],
    "dialogClosedVerified": true
  },
  "cleanup": {
    "status": "not_needed",
    "candidates": []
  },
  "localChecks": {
    "skillHygienePassed": true,
    "quickValidatePassed": true,
    "repoCheckPassed": true
  }
}
```

Generate this shape after reading the site list and before submitting the form:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_create_preflight_evidence.py \
  --existing-site-keys old-site-a,old-site-b \
  --site-key-evidence "old-site-a from backend url route https://workspace.laicms.com/old-site-a/dashboard;old-site-b from backend url route https://workspace.laicms.com/old-site-b/dashboard" \
  --observed-create-fields "button: 创建站点;dialog title: 创建站点;input name: name, placeholder: 站点名称;textarea name: description, placeholder: 站点简介;submit button: 创建;close button: Close" \
  --dialog-closed-verified \
  --output ~/allincms-projects/allincms-create-site-preflight.json
python3 skills/allincms-bulk-content-upload/scripts/validate_run_evidence.py \
  ~/allincms-projects/allincms-create-site-preflight.json
```

If `/sites` is verified empty, set `existingSiteKeysBeforeCreate` to `[]` by using `--no-existing-sites --empty-site-list-evidence "verified empty /sites list"`. Do not omit the field.

After selecting or creating a site, add `siteIdentity`, `setupPages`, and `contentInspection`. These are required before claiming completion, before upload, or when `siteCreation.status` is `created_verified` or `existing_site_selected`.

For partial or phase evidence, `repoCheckPassed` may be false only when the evidence does not claim completion and `repoCheckNote` explains the unrelated failure. Do not use such evidence to claim the full simulation is complete.

When frontend audit output already exists, prefer merging it through the evidence generator instead of hand-copying route patterns:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_frontend_rendering_evidence.py \
  ~/allincms-projects/allincms-launch-audit-report.json \
  --output ~/allincms-projects/allincms-frontend-rendering-evidence.json

python3 skills/allincms-bulk-content-upload/scripts/make_existing_site_readonly_evidence.py \
  --frontend-rendering-evidence ~/allincms-projects/allincms-frontend-rendering-evidence.json \
  --launch-readiness-evidence ~/allincms-projects/allincms-launch-readiness-evidence.json \
  ...other required fields... \
  --output ~/allincms-projects/allincms-existing-site-readonly-evidence.json
```

When a browser refresh has produced a raw module scan JSON, redact it before storing, reusing, or converting it to run evidence:

```bash
python3 skills/allincms-bulk-content-upload/scripts/redact_browser_scan.py \
  ~/allincms-projects/allincms-browser-raw-scan.json \
  --output ~/allincms-projects/allincms-browser-readonly-scan.redacted.json

python3 skills/allincms-bulk-content-upload/scripts/make_existing_site_evidence_from_scan.py \
  ~/allincms-projects/allincms-browser-readonly-scan.redacted.json \
  --edit-fields "target content list/edit controls observed read-only" \
  --frontend-rendering-evidence ~/allincms-projects/allincms-frontend-rendering-evidence.json \
  --launch-readiness-evidence ~/allincms-projects/allincms-launch-readiness-evidence.json \
  --output ~/allincms-projects/allincms-existing-site-readonly-evidence.json
```

The redacted scan file must record `sites.existingSiteKeys` and the required backend module observations. `sites.createDialog` is optional for existing-site continuation; include it only when the browser actually opened and closed the create-site dialog in the current read-only pass. When present, `sites.createDialog.closedVerified: true` and name/description/submit/close controls are required. Each required module observation must include the actual observed backend URL, such as `https://workspace.laicms.com/{siteKey}/products`; the converter rejects missing URLs and wrong-site URLs. Do not use the converter to launder guessed routes or old create-dialog fields into fresh evidence. For create-site submit authorization, build a separate `create_preflight_verified` file; existing-site evidence is not a create-site mutation preflight.

Before storing scan-derived evidence, filter account-menu text, emails, site-selector labels, frontend domain strings, and raw body/content text from the scan. Keep neutral headings, table headers, input placeholders, route shapes, backend module URLs, and control labels only.

For BooleanOptionalAction flags, use `--no-repo-check-passed` rather than `--repo-check-passed=false`.

Static launch evidence and content upload evidence are separate phases. A valid read-only evidence file can prove that a created site, active theme, static routes, and public pages are currently rendering, while still proving that product/post upload is incomplete because `/products/{slug}` and `/posts/{slug}` remain expected 404. Keep `completionClaimed: false` until the exact content type has an authorized probe/sample, request capture, backend persistence check, frontend detail 200, and cleanup outcome.

When the run includes theme/page/route launch work, record `launchReadiness` separately from `frontendRendering`. `frontendRendering` proves public route HTTP/DOM audit results; `launchReadiness` proves the backend chain behind those routes is also ready:

Prefer generating this block instead of hand-writing JSON:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_launch_readiness_evidence.py \
  --checked-paths "/,/home,/products,/solutions,/about-us,/contact-us" \
  --evidence "theme active, page rows published/enabled, routes bound, frontend DOM audited" \
  --output ~/allincms-projects/allincms-launch-readiness-evidence.json
```

```json
{
  "launchReadiness": {
    "checked": true,
    "themeActive": true,
    "pagesPublished": true,
    "pagesEnabled": true,
    "routesBound": true,
    "frontendHttpOk": true,
    "frontendDomVerified": true,
    "checkedPaths": ["/", "/home", "/products", "/solutions", "/about-us", "/contact-us"],
    "evidence": "theme row active, page rows published/enabled, routes bound, frontend DOM audited",
    "blockingIssues": []
  }
}
```

Do not set any launch readiness boolean to true from a toast, HTTP 200 Server Action response, or active theme row alone. If any step is false, keep `completionClaimed: false` and record the blocker in `blockingIssues`. The generator allows partial evidence only when a blocker is present, but `validate_run_evidence.py` still rejects partial `launchReadiness` as launch-ready proof.

When both frontend route audit and backend launch readiness evidence exist, merge both generated files into the final run-evidence builder with `--frontend-rendering-evidence` and `--launch-readiness-evidence`. Do not paste these blocks by hand unless a helper is missing and the copied JSON is immediately validated.

`siteCreation.status: "create_preflight_verified"` means the `/sites` page and create-site dialog were inspected and the pre-create site-key list was recorded, but the form was not submitted. Do not include `createdSiteKey` in preflight evidence; upgrade to `created_verified` only after submit plus site-card, backend, and frontend verification.

## Upgrade After Create Submit

Before a real browser submit, run the full local-only simulator to exercise site creation, static launch, module interface planning, content probe lifecycle, final summary, and closeout without touching LAICMS:

```bash
python3 skills/allincms-bulk-content-upload/scripts/run_full_rehearsal.py \
  --existing-site-keys old-site-a,old-site-b \
  --site-key-evidence "old-site-a from backend url route https://workspace.laicms.com/old-site-a/dashboard;old-site-b from backend url route https://workspace.laicms.com/old-site-b/dashboard" \
  --output-dir ~/allincms-projects/allincms-full-rehearsal
```

The rehearsal creates `full-e2e/01-site-creation/`, `full-e2e/02-probe-lifecycle/`, `full-e2e/03-module-interface-plan/`, `full-e2e/04-manifest-rehearsal/`, `full-e2e/full-e2e-summary.json`, `next-capture-handoff/handoff.json`, `launch-plan.json`, staged browser ledgers through static audit and content-probe creation, and `rehearsal-summary.json`. The module interface directory contains a simulated redacted module scan, module scan summary, and staged capture plan so the rehearsal covers the handoff from read-only inspection to one-action-at-a-time browser capture. The manifest rehearsal directory contains a neutral draft manifest, a simulated `source-input-gap-ledger.json`, generated source-input requirements with non-empty `operationGaps`, and a summary proving generic draft validation passes while the stricter upload schema gate fails as expected until a real save request provides `payloadTemplate`. The launch plan lists the proof gates needed before a site can be called launch-ready: real site creation proof, setup-page inspection, theme/route readiness, frontend static audit, module request capture, content schema capture, sample upload, batch upload, form/media/settings proof, final frontend audit, and cleanup. The rehearsal validates directory-level coherence across all four phases, then validates the generated handoff and launch plan. The handoff selects the next single stage, preferring the current `contentType` probe when no module/action is specified. For local-only simulation output, the handoff suppresses command fields by default and templates the target as `https://workspace.laicms.com/{realSiteKey}/...`; the simulated URL is kept only in `simulatedTarget` for audit. Use it as a rehearsal artifact, not as a real-site command or authorization source. This is the preferred local rehearsal before a real browser run because it catches interface drift across site creation, module planning, manifest schema gating, source gap-ledger merge, handoff, launch proof planning, static audit gating, and content probe phases.

Use `make_capture_handoff.py --allow-command-output` only for local command-shape testing or after the evidence is regenerated from a real site and still passes the relevant gates. A generated handoff is never user authorization. Always run `validate_capture_handoff.py` before copying any handoff into a final response or browser-operation plan.

Use `run_full_rehearsal.py --allow-command-output` only for command-shape testing. The rehearsal summary still records `localOnly: true` and `remoteMutationsPerformed: false`; do not treat command output as permission to operate a real site.

Runbook field paths differ by artifact:

```text
browser-runbook-summary.json: nextRealBrowserStep.stageId
rehearsal-summary.json: browserRunbookSummary.nextStageId
```

The standalone runbook file is the full execution checklist. The embedded `browserRunbookSummary` object in the rehearsal summary is only a compact display summary.

Do not expect either full rehearsal artifact to expose run-evidence fields such as `valid`, `complete`, or `completionGaps`. `rehearsal-summary.json` is an orchestration summary; judge it by `validate_full_rehearsal.py` plus the `*Safety.ok` and `fullE2EValidation.ok` blocks. `browser-runbook-summary.json` is the next-step handoff; judge it by `validate_browser_runbook_summary.py` and `nextRealBrowserStep.stageId`. Use `summarize_run_status.py` only for run-evidence JSON generated from real or simulated site evidence.

Use `build_launch_plan.py` on an existing full E2E directory when only the launch proof plan needs to be regenerated:

```bash
python3 skills/allincms-bulk-content-upload/scripts/build_launch_plan.py \
  ~/allincms-projects/allincms-full-rehearsal/full-e2e \
  --handoff-json ~/allincms-projects/allincms-full-rehearsal/next-capture-handoff/handoff.json \
  --output ~/allincms-projects/allincms-full-rehearsal/launch-plan.json
python3 skills/allincms-bulk-content-upload/scripts/validate_launch_plan.py \
  ~/allincms-projects/allincms-full-rehearsal/launch-plan.json
```

The launch plan uses redacted route patterns such as `/products/{slug}` and template origins such as `https://{realSiteKey}.web.allincms.com`. Do not replace those with real slugs or business copy inside the skill.

After generating or editing a full rehearsal artifact, validate the top-level summary. This re-runs the directory validator, handoff validator, launch-plan validator, and cross-checks summary paths, selected stage, and launch proof counts:

```bash
python3 skills/allincms-bulk-content-upload/scripts/validate_full_rehearsal.py \
  ~/allincms-projects/allincms-full-rehearsal/rehearsal-summary.json
```

To rehearse only the manifest normalization and schema gate:

```bash
python3 skills/allincms-bulk-content-upload/scripts/simulate_manifest_rehearsal.py \
  --site-key simsite01 \
  --content-type products \
  --output-dir ~/allincms-projects/allincms-manifest-rehearsal
python3 skills/allincms-bulk-content-upload/scripts/validate_manifest_rehearsal.py \
  ~/allincms-projects/allincms-manifest-rehearsal/manifest-rehearsal-summary.json
```

The expected result is draft validation passing and `--require-schema-verified` failing. If the schema gate passes before request capture, treat that as a validator bug.

Keep simulated site keys in the same safe shape as real LAICMS site keys: lowercase alphanumeric, 6-16 characters. Do not use hyphenated placeholders such as `codex-simulated-site`; they should fail the scan redaction gate just like unsafe real paths.

To rehearse only the create-site half, run:

```bash
python3 skills/allincms-bulk-content-upload/scripts/simulate_site_creation_chain.py \
  --existing-site-keys old-site-a,old-site-b \
  --site-key-evidence "old-site-a from backend url route https://workspace.laicms.com/old-site-a/dashboard;old-site-b from backend url route https://workspace.laicms.com/old-site-b/dashboard" \
  --include-simulated-static-launch \
  --output-dir ~/allincms-projects/allincms-site-creation-simulation
```

The simulator writes five artifacts: `create-site-preflight.json`, `create-site-authorization.json`, `created-site-evidence.json`, `run-summary.json`, and `round-closeout.json`. With `--include-simulated-static-launch`, it also embeds simulated static `frontendRendering` and `launchReadiness` blocks. The summary must show `site_created_and_verified` and static launch proof as simulated proof while still surfacing upload gaps such as `request_capture_persisted_verified`, `sample_backend_frontend_verified`, and `cleanup_completed`.

Use `--no-existing-sites` only when the live `/sites` list has just been verified empty. This simulator is a dry run; it does not authorize or prove a real create-site submit.

After the created-site dry run, rehearse the content upload chain locally:

```bash
python3 skills/allincms-bulk-content-upload/scripts/simulate_probe_lifecycle.py \
  --base ~/allincms-projects/allincms-site-creation-simulation/created-site-evidence.json \
  --require-created-site \
  --output-dir ~/allincms-projects/allincms-probe-lifecycle-simulation
```

This second simulator writes staged authorization and evidence files for probe creation, request capture, sample frontend/backend verification, and cleanup. Its final `run-summary.json` can become `complete: true` only because the proof is simulated; keep that distinction explicit before any real browser operation.

After the user authorizes and the create-site form is submitted, upgrade the same run evidence instead of starting from memory:

```text
1. Keep the exact `existingSiteKeysBeforeCreate` from preflight, including `[]` for a verified empty workspace.
2. Require the preflight to include `dialogClosedVerified: true`; if not, repeat the read-only preflight before submitting.
3. Set `mode` to `site_creation`.
4. Set `siteCreation.status` to `created_verified`.
5. Set `siteCreation.createdSiteKey` to the newly observed site key.
6. Prove `createdSiteKey` is not in `existingSiteKeysBeforeCreate`.
7. Set `siteCardVerified`, `backendVerified`, and `frontendVerified` only after opening those surfaces.
8. Add `siteIdentity` for the new site, including only module routes that were opened or observed on the new site's backend navigation.
9. Add `setupPages` after inspecting site-info, domains, themes, routes, and forms.
10. Add `contentInspection` only after inspecting the chosen content type list/edit pages.
```

Do not carry over `siteIdentity`, setup pages, or content fields from an old site into a newly created site's evidence.

Do not generate module routes from a guessed standard list. Record the routes from the newly opened backend dashboard/sidebar. The required baseline modules are dashboard, products, posts, media, themes, routes, forms, site-info, tracking, and domains; if any are missing, stop and treat the site as a setup variance.

Created-site evidence must bind to the new site key. `siteCardEvidence` must mention `createdSiteKey`; `backendEvidence` must mention `https://workspace.laicms.com/{createdSiteKey}/dashboard`; `frontendEvidence` must mention `https://{createdSiteKey}.web.allincms.com`. Generic evidence such as "dashboard opened" is not enough.

Record submitted create-site field keys as `submittedFieldKeys`, at minimum `name` and `description`. Do not store the raw site name or description in the skill; if value proof is needed, keep a redacted run artifact outside the skill.

Do not let the evidence generator invent authorization. Pass an explicit `--authorization-source` that describes the current user instruction authorizing the create-site submit. Generic "continue" or old authorization from another action is not acceptable.

`siteCreation.status: "created_verified"` is invalid under `mode: "read_only_simulation"` because submitting the form changes remote state. Use `mode: "site_creation"` for this phase. This does not authorize content upload; upload still requires a separate probe/upload authorization and request capture.

After those checks are observed on the new site, generate and validate the created-site evidence:

```bash
python3 skills/allincms-bulk-content-upload/scripts/make_created_site_evidence.py \
  --preflight ~/allincms-projects/allincms-create-site-preflight.json \
  --created-site-key new-site-key \
  --content-type products \
  --list-columns "媒体,名称,Slug,描述,排序,状态,分类,标签,创建时间" \
  --edit-fields "name input,slug input,description textarea,body editor" \
  --site-card-evidence "site list shows new-site-key card and enter-backend control" \
  --backend-evidence "dashboard opens at https://workspace.laicms.com/new-site-key/dashboard" \
  --frontend-evidence "frontend opens at https://new-site-key.web.allincms.com" \
  --site-info-evidence "site-info inspected for name, description, icon, notificationEmail, save" \
  --domains-evidence "domains inspected for CNAME, domain input, add domain" \
  --themes-evidence "themes inspected for search, create theme, page/design/preview controls" \
  --routes-evidence "routes inspected for columns and create controls" \
  --forms-evidence "forms inspected for name, slug, description, fields, status, update time" \
  --tracking-evidence "tracking inspected for Google Tag ID input and add action" \
  --module-routes "/new-site-key/dashboard,/new-site-key/products,/new-site-key/posts,/new-site-key/media,/new-site-key/themes,/new-site-key/routes,/new-site-key/forms,/new-site-key/site-info,/new-site-key/tracking,/new-site-key/domains" \
  --submitted-fields "name,description" \
  --authorization-source "current user instruction explicitly authorized creating new-site-key at https://workspace.laicms.com/sites" \
  --output ~/allincms-projects/allincms-created-site-evidence.json
python3 skills/allincms-bulk-content-upload/scripts/validate_run_evidence.py \
  ~/allincms-projects/allincms-created-site-evidence.json
```

If `mode` is `batch_upload` or `uploadInScope` is true, the evidence must include request capture and sample verification. `mode: "mutating_probe"` may be a staged state before save or before publish; use the pre-mutation gate for the next stage and do not claim completion until request capture, sample verification, and cleanup are all present:

```json
{
  "authorization": {
    "userAuthorized": true,
    "authorizedAction": "create probe and save sample content",
    "target": "https://workspace.laicms.com/{siteKey}/posts",
    "authorizationSource": "current user instruction",
    "verificationPlan": "capture save request, verify backend persistence, then verify frontend render"
  },
  "requestCapture": {
    "url": "",
    "method": "",
    "headers": "",
    "payloadShape": "",
    "contentBlockShape": "",
    "idFields": "",
    "mode": "",
    "publishBehavior": "",
    "persistedVerified": true
  },
  "sampleVerification": {
    "backendVerified": true,
    "frontendVerified": true,
    "backendUrl": "",
    "frontendUrl": "",
    "status": "",
    "titleOrNameVerified": true,
    "coverOrMediaVerified": true,
    "bodyVerified": true,
    "renderAudit": ""
  }
}
```

After each separately authorized probe stage, prefer merging the observed proof through `merge_probe_evidence.py` instead of hand-editing the run evidence. A request-capture merge is allowed to remain partial and should drive the next summary action to `authorize_publish_probe`; it is not full completion proof.

```bash
python3 skills/allincms-bulk-content-upload/scripts/merge_probe_evidence.py \
  --base ~/allincms-projects/allincms-current-run-evidence.json \
  --request-capture \
  --url "https://workspace.laicms.com/{siteKey}/products/{redacted-id}/update" \
  --method POST \
  --headers "Accept, Content-Type, next-action" \
  --payloadShape "redacted server action payload" \
  --contentBlockShape "structured rich text blocks" \
  --idFields "siteId, productId" \
  --mode update \
  --publishBehavior "publish separate" \
  --output ~/allincms-projects/allincms-current-run-evidence.json
```

For cleanup, pass redacted candidates as `contentType|titlePattern|backendUrl|reason` and validate the merged evidence before claiming cleanup is complete.

For upload evidence, authorization must be action-specific. It must explicitly authorize probe, save, update, upload, batch, sample, or publish work, and the target must belong to the verified backend site key. Do not reuse site creation, cleanup, deletion, or generic continuation authorization as upload permission.

For upload evidence, URL ownership is strict:

```text
requestCapture.url and sampleVerification.backendUrl must parse to workspace.laicms.com and start with /{siteKey}/.
sampleVerification.frontendUrl must parse to https://{siteKey}.web.allincms.com/...
Do not accept a URL merely because the site key or frontend host appears in the query string or text.
```

If `siteCreation.status` is `created_verified` or cleanup status is `completed`, the same authorization object is required even when `mode` is not `mutating_probe` or `batch_upload`.

For a completed site creation, authorization must be action-specific:

```json
{
  "authorization": {
    "userAuthorized": true,
    "authorizedAction": "create site",
    "target": "https://workspace.laicms.com/sites",
    "authorizationSource": "current user instruction",
    "verificationPlan": "verify site card, backend dashboard, and default frontend"
  }
}
```

Do not reuse cleanup, upload, publish, or generic "continue" authorization as proof that site creation was authorized.

When `siteCreation.status` is `created_verified`, `siteCreation.createdSiteKey` must match `siteIdentity.siteKey`, and `siteCreation.existingSiteKeysBeforeCreate` must show that the created key did not already exist before submitting the form. An empty array is valid only when `/sites` was verified empty before submit. The backend dashboard URL, frontend base URL, and module routes must all belong to that same site key; do not use an older existing site as proof for the new site.

When `siteCreation.status` is `created_verified`, record proof that the created site is visible and reachable:

```json
{
  "siteCreation": {
    "status": "created_verified",
    "existingSiteKeysBeforeCreate": ["old-site-a", "old-site-b"],
    "createdSiteKey": "example-site",
    "siteCardVerified": true,
    "backendVerified": true,
    "frontendVerified": true,
    "siteCardEvidence": "site list shows example-site card and enter-backend control",
    "backendEvidence": "new dashboard opens at https://workspace.laicms.com/example-site/dashboard",
    "frontendEvidence": "default frontend opens at https://example-site.web.allincms.com"
  }
}
```

Do not use an existing site's dashboard, frontend, or module routes as proof that a newly submitted create-site form succeeded.

The evidence validator also requires site keys to use lowercase letters, digits, or hyphens; create-site fields to include `name` and `description`; `existingSiteKeysBeforeCreate` to be present as an array; `createdSiteKey` to be absent from `existingSiteKeysBeforeCreate`; created-site evidence strings to mention the same `createdSiteKey`, backend dashboard URL, and frontend origin; and module routes to include dashboard, products, posts, media, themes, routes, forms, site-info, tracking, and domains for the same site key.

Each setup page evidence array (`siteInfo`, `domains`, `themes`, `routes`, `forms`) must be non-empty. `contentInspection.contentType` must be one of `posts`, `products`, `media`, `themes`, `routes`, or `forms`.

When `cleanup.status` is `completed`, the evidence must prove what changed:

```json
{
  "authorization": {
    "userAuthorized": true,
    "authorizedAction": "cleanup/delete/unpublish LAICMS probe drafts",
    "target": "https://workspace.laicms.com/{siteKey}/posts",
    "authorizationSource": "current user instruction",
    "verificationPlan": "verify backend list and frontend URLs after cleanup"
  },
  "cleanup": {
    "status": "completed",
    "cleanedCount": 1,
    "cleanedCandidates": [
      {
        "contentType": "posts",
        "titlePattern": "Codex Probe - Delete Me <redacted>",
        "backendUrl": "https://workspace.laicms.com/{siteKey}/posts",
        "reason": "user-authorized probe cleanup"
      }
    ],
    "backendVerified": true,
    "frontendVerified": true,
    "backendEvidence": "backend list no longer shows the cleaned probe title pattern",
    "frontendEvidence": "frontend probe URL returns 404 or no longer renders the probe"
  }
}
```

`cleanedCount` must match the length of `cleanedCandidates`. The cleanup authorization target must belong to the verified backend site key. Do not set cleanup to `completed` for a candidate that was only searched, deferred, or left pending authorization.

## Known Verified Status

As of 2026-06-29, the following are verified on one logged-in site and should be rechecked elsewhere:

```text
/sites exists and exposes 创建站点.
Create-site dialog has 名称 and 描述 fields.
Existing site backend exposes products, posts, media, themes, routes, forms, site-info, tracking, domains.
site-info exposes name, description, site icon, notification email, save.
domains exposes CNAME copy, domain input, add domain.
routes exposes route columns and create-route dialog.
themes exposes create-theme dialog.
media exposes upload controls.
posts/products 创建 can create Untitled drafts and is not read-only.
read-only run evidence can pass validate_run_evidence.py when it includes create-site fields, site identity, setup pages, content list columns, edit fields, cleanup status, and local check results.
```

## Completion Definition

Do not call the simulation complete unless all of these have current evidence:

```text
site creation was either completed and verified, or explicitly simulated without submission
site identity and frontend base URL are known
first-site setup pages were inspected
target content type was mapped from current backend
one real save request was captured for that exact content type, if upload is in scope
one sample item was saved and verified backend/frontend, if upload is in scope
probe/draft cleanup was completed or explicitly left pending with user acceptance
skill files were updated with only neutral platform evidence
audit_skill_hygiene.py passed
validate_run_evidence.py passed
quick_validate.py passed
repo check passed
```
