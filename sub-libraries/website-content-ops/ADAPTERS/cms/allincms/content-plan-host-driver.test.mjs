import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, writeFileSync, readFileSync, rmSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { runAllinCmsContentPlan } from './content-run-controller.mjs';
import { createAllinCmsPlanHandlerSet } from './content-plan-host-driver.mjs';
import { calculatePlanDigest } from '../../../scripts/validate-content-operation-plan.mjs';
import { expectedRuntimeScope } from '../../../scripts/runtime-scope.mjs';

const H = (x) => `sha256:${createHash('sha256').update(String(x)).digest('hex')}`;
const runtimePath = (p) => `customer-runtime/10_clients/fluxpedal-synthetic/30_tasks/synthetic-task/${p}`;
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${stable(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
function digest(value) { return `sha256:${createHash('sha256').update(stable(value)).digest('hex')}`; }
function reseal(plan) {
  plan.plan_digest = calculatePlanDigest(plan);
  if (plan.authorization_scope.status === 'approved') plan.authorization_scope.plan_sha256 = plan.plan_digest;
  return plan;
}
function makePlan() {
  const plan = {
    schema_version: '1.1', plan_id: 'COP-host-driver-001', plan_digest: H('0'),
    client_id: 'fluxpedal-synthetic', company_id: 'fluxpedal-motors-synthetic', task_id: 'synthetic-task',
    runtime_scope: expectedRuntimeScope({ client_id: 'fluxpedal-synthetic', company_id: 'fluxpedal-motors-synthetic', task_id: 'synthetic-task' }),
    execution_mode: 'audit', plan_phase: 'site_operation',
    cms_adapter: { id: 'allincms', version: 'test', observed_at: new Date().toISOString(), deployment_fingerprint: H('dep') },
    site_selector: { target_scope: 'site', site_key: 'synthetic-site', site_id: 'sid-1', account_user_id: 'uid-1', selection_source: 'user-confirmed', bootstrap_readback_ref: null, bootstrap_plan_digest: null, cross_site_fallback: false },
    source_snapshot: { captured_at: new Date().toISOString(), sources: [{
      source_id: 'SRC-001', kind: 'brief', location: runtimePath('10_sources/brief.md'), digest: H('b'), authority: 'primary', owner: 'synthetic-owner', rights_status: 'owned', method_use_clearance: 'approved', publication_clearance: 'approved', source_date: '2026-08-27T00:00:00Z', review_after: null, source_scope: 'fluxpedal-synthetic/fluxpedal-motors-synthetic/synthetic-task',
      extractions: [{ extraction_id: 'SX-001', artifact_ref: runtimePath('20_work/sx.json'), source_digest: H('b'), captured_at: new Date().toISOString(), status: 'complete', units: [{ unit_id: 'UNIT-1', locator: 'x', extraction_digest: H('u') }] }], publication_clearance: 'approved' }] },
    claim_ledger: ['Qualification Guides', 'FP-QC60', 'fp-qc60', 'Fixture description non-empty.'].map((v, i) => ({ claim_id: `CLAIM-${i + 1}`, status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [{ source_id: 'SRC-001', source_digest: H('b'), extraction_id: 'SX-001', unit_id: 'UNIT-1', locator: 'x', extraction_digest: H('u') }], value: v, notes: '' })),
    capability_snapshot: { captured_at: new Date(Date.now() - 60000).toISOString(), expires_at: new Date(Date.now() + 29 * 60000).toISOString(), deployment_fingerprint: H('dep'), capabilities: [
      { capability_id: 'CAP-category-readback', entity_type: 'category', action: 'readback', maturity: 'local_tested', evidence_refs: [runtimePath('70_evidence/read.json')] },
      { capability_id: 'allincms.product.publish', entity_type: 'product', action: 'publish', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('70_evidence/basis.json')] }] },
    desired_state: [
      { entity_ref: 'category:existing', entity_type: 'category', intent: 'noop', identity: { id: 'cat-1', natural_key: {}, match_strategy: 'exact_id' }, fields: { name: { value: 'Qualification Guides', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-1'], derivation: { mode: 'direct', notes: '' }, clear_existing: false } } },
      { entity_ref: 'product:fp-qc60', entity_type: 'product', intent: 'update', identity: { id: 'prd-1', natural_key: {}, match_strategy: 'exact_id' }, fields: {
        name: { value: 'FP-QC60', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-2'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        slug: { value: 'fp-qc60', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-3'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        description: { value: 'Fixture description non-empty.', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-4'], derivation: { mode: 'direct', notes: '' }, clear_existing: false } } }],
    current_state_fingerprint: H('c'),
    diff: [
      { operation_id: 'OP-001', entity_ref: 'category:existing', resolved_intent: 'noop', changed_fields: [] },
      { operation_id: 'OP-002', entity_ref: 'product:fp-qc60', resolved_intent: 'publish', changed_fields: [] }],
    operations: [
      { operation_id: 'OP-001', entity_ref: 'category:existing', entity_type: 'category', intent: 'noop', identity: { id: 'cat-1', natural_key: {}, match_strategy: 'exact_id' }, field_refs: [], capability_ref: 'CAP-category-readback', expected_current_fingerprint: null, dependencies: [], mutation: false, publication_effect: 'none', readback_requirements: ['read_only.authoritative_noop_readback', 'scope.exact_site_binding'] },
      { operation_id: 'OP-002', entity_ref: 'product:fp-qc60', entity_type: 'product', intent: 'publish', identity: { id: 'prd-1', natural_key: {}, match_strategy: 'exact_id' }, field_refs: [], capability_ref: 'allincms.product.publish', expected_current_fingerprint: null, dependencies: ['OP-001'], mutation: true, publication_effect: 'publish_transition', readback_requirements: ['product.backend_published_state', 'product.editor_reopen_health', 'product.public_url', 'product.anonymous_frontend_detail', 'product.visible_content_and_media'] }],
    authorization_scope: { status: 'approved', actor: 'Test Human', identity_status: 'not_verified', target_scope: 'site', target_key: 'synthetic-site', operation_ids: ['OP-001', 'OP-002'], approved_at: AUTH_AT, archived_at: AUTH_AT, expires_at: new Date(Date.now() + 29 * 60000).toISOString(), plan_sha256: null },
    reconciliation_policy: { ambiguous_write: 'read-only-reconcile-before-any-retry', automatic_retry_after_request_started: false, identity_rule: 'exact-id-or-site-scoped-natural-key' },
    verification_plan: { backend_readback: true, editor_reopen: true, frontend: true, evidence_targets: [runtimePath('70_evidence/run.json')] },
    writeback_targets: [{ kind: 'evidence', path: runtimePath('70_evidence/run.json'), visibility: 'private-runtime' }],
  };
  return reseal(plan);
}

test('host driver wires controller: noop + product publish completes with valid evidence', async () => {
  const tmp = mkdtempSync(join(tmpdir(), 'acrun-'));
  mkdirSync(join(tmp, '70_evidence'), { recursive: true });
  const AUTH_AT = new Date(Date.now() - 60000).toISOString();
  const plan = reseal(makePlan());
  const SITE_KEY = plan.site_selector.site_key;
  const SITE_ID = plan.site_selector.site_id;
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { productUpdate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const requested = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const toTmp = (path) => join(tmp, path.replace('customer-runtime/10_clients/fluxpedal-synthetic/30_tasks/synthetic-task/', ''));
  const backendReadback = async ({ operation }) => (operation.intent === 'publish'
    ? { id: operation.identity.id, siteId: SITE_ID, name: 'FP-QC60', slug: 'fp-qc60', description: 'Fixture description non-empty.', _status: 'published', order: 0, media: { type: 'image', value: null }, categories: [], tags: [] }
    : { id: operation.identity.id, siteId: SITE_ID, name: 'done', status: 'updated' });
  const readbackProvider = async ({ plan, operation }) => {
    const checks = operation.readback_requirements.map((checkId, idx) => {
      const ts = new Date().toISOString();
      const kind = checkId.endsWith('editor_reopen_health') ? 'editor_reopen'
        : checkId === 'product.public_url' ? 'anonymous_resource'
        : (checkId === 'product.anonymous_frontend_detail' || checkId === 'product.visible_content_and_media') ? 'anonymous_frontend'
        : 'backend_readback';
      const subjectObj = {
        operation_id: operation.operation_id, entity_ref: operation.entity_ref, entity_type: operation.entity_type,
        intent: operation.intent, identity: operation.identity, field_refs: operation.field_refs,
        publication_effect: operation.publication_effect, capability_ref: operation.capability_ref,
        expected_current_fingerprint: operation.expected_current_fingerprint, dependencies: operation.dependencies,
        desired_entity: plan.desired_state.find((d) => d.entity_ref === operation.entity_ref),
      };
      const subjectDigest = digest(subjectObj);
      const obs = { backend_authoritative: true, exact_match: true, duplicate_count: 0, current_fingerprint: null, http_status: 200, content_type: 'application/json', resource_url: 'https://synthetic-site.web.allincms.com/products/fp-qc60', anonymous: true, decoded: true, editor_healthy: true, media_applicable: operation.intent === 'publish' };
      const envelope = { schema_version: '1.0', check_id: checkId, evidence_kind: kind, captured_at: ts, site_key: SITE_KEY, site_id: SITE_ID, entity_ref: operation.entity_ref, entity_id: operation.identity.id, subject_digest: subjectDigest, method: 'host-readback', observed_result: JSON.stringify({ ok: true }), observations: obs };
      const ref = runtimePath(`70_evidence/check-${operation.operation_id}-${idx}.json`);
      writeFileSync(toTmp(ref), JSON.stringify(envelope));
      return { check_id: checkId, evidence_kind: kind, passed: true, artifact_ref: ref, artifact_digest: `sha256:${createHash('sha256').update(JSON.stringify(envelope)).digest('hex')}`, artifact_media_type: 'application/json', observed_at: ts, site_key: SITE_KEY, site_id: SITE_ID, entity_ref: operation.entity_ref, entity_id: operation.identity.id, subject_digest: subjectDigest, method: 'host-readback', observed_result: JSON.stringify({ ok: true }), observations: obs };
    });
    return { ok: true, authoritative: true, requirements: operation.readback_requirements, evidence_ref: runtimePath(`70_evidence/check-${operation.operation_id}-0.json`), checks };
  };
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: SITE_KEY, siteId: SITE_ID, runtime, request, readbackProvider, backendReadback,
    writeEvidenceArtifact: async ({ path, bytes }) => { mkdirSync(dirname(toTmp(path)), { recursive: true }); writeFileSync(toTmp(path), bytes); },
  });
  const evidencePath = runtimePath('70_evidence/run.json');
  const preflight = async () => ({
    login_status: 'authenticated', user_id: 'uid-1', site_key: SITE_KEY, site_id: SITE_ID,
    deployment_fingerprint: H('dep'), capability_ids: ['CAP-category-readback', 'allincms.product.publish'],
  });
  const readEvidenceArtifact = async (arg) => readFileSync(toTmp(typeof arg === 'string' ? arg : arg?.path));
  const writeEvidence = async ({ path, evidence }) => {
    mkdirSync(dirname(toTmp(path)), { recursive: true });
    writeFileSync(toTmp(path), JSON.stringify(evidence));
    return { ok: true, evidence_ref: path };
  };
  const result = await runAllinCmsContentPlan({ plan, handlers, preflight, writeEvidence, readEvidenceArtifact, evidencePath, runId: 'ACRUN-driver-test-001' });
  assert.equal(result.ok, true, JSON.stringify(result).slice(0, 300));
  assert.equal(result.status, 'completed');
  assert.equal(result.code, 'ALLINCMS_CONTENT_RUN_COMPLETED');
  assert.equal(result.evidence.operations.length, 2);
  assert.equal(result.evidence.operations[1].status, 'readback_passed');
  assert.equal(requested.length, 1);
  assert.match(requested[0].url, /synthetic-site\/products\/prd-1\/update/);
  rmSync(tmp, { recursive: true, force: true });
});
