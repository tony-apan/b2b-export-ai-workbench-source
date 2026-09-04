import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, writeFileSync, readFileSync, rmSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { runAllinCmsContentPlan } from './content-run-controller.mjs';
import { createAllinCmsPlanHandlerSet, allinCmsOperationAuthorization } from './content-plan-host-driver.mjs';
import { computeAllinCmsMutationTargetDigest, deriveAllinCmsMutationBinding } from './mutation-authorization.mjs';
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
  const AUTH_AT = new Date(Date.now() - 60000).toISOString();
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
    capability_snapshot: { captured_at: new Date(Date.now() - 60000).toISOString(), expires_at: new Date(Date.now() + 28 * 60000).toISOString(), deployment_fingerprint: H('dep'), capabilities: [
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
    authorization_scope: { status: 'approved', actor: 'Test Human', identity_status: 'not_verified', target_scope: 'site', target_key: 'synthetic-site', operation_ids: ['OP-001', 'OP-002'], approved_at: AUTH_AT, archived_at: AUTH_AT, expires_at: new Date(Date.now() + 28 * 60000).toISOString(), plan_sha256: null },
    reconciliation_policy: { ambiguous_write: 'read-only-reconcile-before-any-retry', automatic_retry_after_request_started: false, identity_rule: 'exact-id-or-site-scoped-natural-key' },
    verification_plan: { backend_readback: true, editor_reopen: true, frontend: true, evidence_targets: [runtimePath('70_evidence/run.json')] },
    writeback_targets: [{ kind: 'evidence', path: runtimePath('70_evidence/run.json'), visibility: 'private-runtime' }],
  };
  return reseal(plan);
}

test('host driver wires controller: noop + product publish completes with valid evidence', async () => {
  const tmp = mkdtempSync(join(tmpdir(), 'acrun-'));
  mkdirSync(join(tmp, '70_evidence'), { recursive: true });
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

function makeArticleCreateRunPlan() {
  const plan = makePlan();
  const identity = { id: null, natural_key: { site_key: 'synthetic-site', slug: 'new-guide' }, match_strategy: 'exact_natural_key' };
  const claimEvidence = { source_id: 'SRC-001', source_digest: H('b'), extraction_id: 'SX-001', unit_id: 'UNIT-1', locator: 'x', extraction_digest: H('u') };
  plan.claim_ledger.push(
    { claim_id: 'CLAIM-ART-TITLE', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value: 'Synthetic New Guide', notes: '' },
    { claim_id: 'CLAIM-ART-SLUG', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value: 'new-guide', notes: '' },
    { claim_id: 'CLAIM-ART-EXCERPT', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value: '', notes: '' },
    { claim_id: 'CLAIM-ART-ORDER', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value: 0, notes: '' },
    { claim_id: 'CLAIM-ART-COVER', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value: null, notes: '' },
    { claim_id: 'CLAIM-ART-CATEGORIES', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value: [], notes: '' },
    { claim_id: 'CLAIM-ART-TAGS', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value: [], notes: '' },
    { claim_id: 'CLAIM-ART-CONTENT', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value: [], notes: '' },
  );
  plan.capability_snapshot.capabilities = [{ capability_id: 'allincms.article.create', entity_type: 'article', action: 'create', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('70_evidence/basis.json')] }];
  plan.desired_state = [{
    entity_ref: 'article:new-guide', entity_type: 'article', intent: 'create', identity,
    fields: {
      title: { value: 'Synthetic New Guide', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-TITLE'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
      slug: { value: 'new-guide', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-SLUG'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
      excerpt: { value: '', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-EXCERPT'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
      order: { value: 0, fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-ORDER'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
      coverImage: { value: null, fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-COVER'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
      categories: { value: [], fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-CATEGORIES'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
      tags: { value: [], fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-TAGS'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
      content: { value: [], fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-CONTENT'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
    },
  }];
  plan.diff = [{ operation_id: 'OP-AC-001', entity_ref: 'article:new-guide', resolved_intent: 'create', changed_fields: ['title', 'slug'] }];
  plan.operations = [{ operation_id: 'OP-AC-001', entity_ref: 'article:new-guide', entity_type: 'article', intent: 'create', identity: structuredClone(identity), field_refs: ['title', 'slug'], capability_ref: 'allincms.article.create', expected_current_fingerprint: null, dependencies: [], mutation: true, publication_effect: 'private_draft', readback_requirements: ['article.create.before_after_unique_id_delta', 'article.create.backend_field_readback', 'article.create.editor_reopen_health'] }];
  plan.authorization_scope.operation_ids = ['OP-AC-001'];
  return reseal(plan);
}

test('controller+driver article create passes the execute-result runtime ID to the host readback provider', async () => {
  const tmp = mkdtempSync(join(tmpdir(), 'acrun-create-'));
  mkdirSync(join(tmp, '70_evidence'), { recursive: true });
  const plan = makeArticleCreateRunPlan();
  const SITE_KEY = plan.site_selector.site_key;
  const SITE_ID = plan.site_selector.site_id;
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const toTmp = (path) => join(tmp, path.replace('customer-runtime/10_clients/fluxpedal-synthetic/30_tasks/synthetic-task/', ''));
  let postIds = ['existing-1'];
  const requested = [];
  const request = async (details) => { requested.push(details); postIds = [...postIds, 'created-1']; return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const createdRecord = () => ({ title: 'Synthetic New Guide', slug: 'new-guide', excerpt: '', order: 0, coverImage: null, categories: [], tags: [], content: [], siteId: SITE_ID, id: 'created-1' });
  const readbackProviderArgs = [];
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: SITE_KEY, siteId: SITE_ID, runtime, request,
    readbackProvider: async ({ plan: readbackPlan, operation, runtime_entity_id, runtime_entity_id_source }) => {
      readbackProviderArgs.push({ runtime_entity_id, runtime_entity_id_source });
      const entityId = runtime_entity_id; // bind evidence to the identity the controller actually passed in
      const checks = operation.readback_requirements.map((checkId, idx) => {
        const ts = new Date().toISOString();
        const kind = checkId === 'article.create.editor_reopen_health' ? 'editor_reopen' : 'backend_readback';
        const subjectObj = {
          operation_id: operation.operation_id, entity_ref: operation.entity_ref, entity_type: operation.entity_type,
          intent: operation.intent, identity: operation.identity, field_refs: operation.field_refs,
          publication_effect: operation.publication_effect, capability_ref: operation.capability_ref,
          expected_current_fingerprint: operation.expected_current_fingerprint, dependencies: operation.dependencies,
          desired_entity: readbackPlan.desired_state.find((d) => d.entity_ref === operation.entity_ref),
        };
        const subjectDigest = digest(subjectObj);
        const obs = kind === 'editor_reopen'
          ? { backend_authoritative: null, exact_match: true, duplicate_count: 0, current_fingerprint: null, http_status: 200, content_type: 'application/json', resource_url: null, anonymous: null, decoded: null, editor_healthy: true, media_applicable: null }
          : { backend_authoritative: true, exact_match: true, duplicate_count: 0, current_fingerprint: null, http_status: 200, content_type: 'application/json', resource_url: null, anonymous: null, decoded: null, editor_healthy: null, media_applicable: null };
        const envelope = { schema_version: '1.0', check_id: checkId, evidence_kind: kind, captured_at: ts, site_key: SITE_KEY, site_id: SITE_ID, entity_ref: operation.entity_ref, entity_id: entityId, subject_digest: subjectDigest, method: 'host-readback', observed_result: JSON.stringify({ ok: true }), observations: obs };
        const ref = runtimePath(`70_evidence/ac-check-${operation.operation_id}-${idx}.json`);
        writeFileSync(toTmp(ref), JSON.stringify(envelope));
        return { check_id: checkId, evidence_kind: kind, passed: true, artifact_ref: ref, artifact_digest: `sha256:${createHash('sha256').update(JSON.stringify(envelope)).digest('hex')}`, artifact_media_type: 'application/json', observed_at: ts, site_key: SITE_KEY, site_id: SITE_ID, entity_ref: operation.entity_ref, entity_id: entityId, subject_digest: subjectDigest, method: 'host-readback', observed_result: JSON.stringify({ ok: true }), observations: obs };
      });
      return { ok: true, authoritative: true, requirements: operation.readback_requirements, evidence_ref: runtimePath('70_evidence/ac-check-OP-AC-001-0.json'), checks };
    },
    articleBeforePostIdsProvider: async () => [...postIds],
    articleCreateReadbackProvider: async () => ({ record: createdRecord(), afterPostIds: [...postIds] }),
    articleEditorReopenProvider: async ({ createdPostId }) => ({ status: 200, authenticated: true, healthy: true, postId: createdPostId }),
    writeEvidenceArtifact: async ({ path, bytes }) => { mkdirSync(dirname(toTmp(path)), { recursive: true }); writeFileSync(toTmp(path), bytes); },
  });
  const evidencePath = runtimePath('70_evidence/run.json');
  const preflight = async () => ({
    login_status: 'authenticated', user_id: 'uid-1', site_key: SITE_KEY, site_id: SITE_ID,
    deployment_fingerprint: H('dep'), capability_ids: ['allincms.article.create'],
  });
  const readEvidenceArtifact = async (arg) => readFileSync(toTmp(typeof arg === 'string' ? arg : arg?.path));
  const writeEvidence = async ({ path, evidence }) => {
    mkdirSync(dirname(toTmp(path)), { recursive: true });
    writeFileSync(toTmp(path), JSON.stringify(evidence));
    return { ok: true, evidence_ref: path };
  };
  const result = await runAllinCmsContentPlan({ plan, handlers, preflight, writeEvidence, readEvidenceArtifact, evidencePath, runId: 'ACRUN-driver-create-test-001' });
  assert.equal(result.ok, true, JSON.stringify(result.problems ?? result).slice(0, 400));
  assert.equal(readbackProviderArgs.length, 1);
  assert.notEqual(readbackProviderArgs[0].runtime_entity_id, null, 'host readback provider received a stale null runtime_entity_id');
  assert.equal(readbackProviderArgs[0].runtime_entity_id, 'created-1');
  assert.equal(readbackProviderArgs[0].runtime_entity_id_source, 'execute_result');
  const row = result.evidence.operations[0];
  assert.equal(row.status, 'readback_passed');
  assert.equal(row.runtime_entity_id, 'created-1');
  assert.equal(row.runtime_entity_id_source, 'execute_result');
  assert.ok(row.readback.checks.every((check) => check.entity_id === 'created-1'));
  assert.equal(requested.length, 1);
  assert.match(requested[0].url, /synthetic-site\/posts$/);
  rmSync(tmp, { recursive: true, force: true });
});

function makeArticleCreatePlanFixture() {
  const identity = { id: null, natural_key: { site_key: 'synthetic-site', slug: 'new-guide' }, match_strategy: 'exact_natural_key' };
  const fields = {
    title: { value: 'Synthetic New Guide' },
    slug: { value: 'new-guide' },
    excerpt: { value: 'Fixture excerpt.' },
    order: { value: 3 },
    coverImage: { value: null },
    categories: { value: [] },
    tags: { value: [] },
    content: { value: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }] },
  };
  return {
    plan_id: 'COP-host-driver-article-create',
    authorization_scope: {
      status: 'approved', actor: 'Test Human',
      approved_at: new Date(Date.now() - 60000).toISOString(),
      expires_at: new Date(Date.now() + 28 * 60000).toISOString(),
    },
    desired_state: [{ entity_ref: 'article:new-guide', entity_type: 'article', intent: 'create', identity, fields }],
    operations: [{ operation_id: 'OP-AC-001', entity_ref: 'article:new-guide', entity_type: 'article', intent: 'create', identity: structuredClone(identity) }],
  };
}

test('allinCmsOperationAuthorization maps article intents onto postCreate/postUpdate bindings', () => {
  const plan = makeArticleCreatePlanFixture();
  const siteKey = 'synthetic-site';
  const siteId = 'sid-1';
  const desiredPayload = {
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
  };
  const created = allinCmsOperationAuthorization({ plan, operation: plan.operations[0], siteKey, siteId, approvalActor: 'Test Human' });
  assert.equal(created.operation, 'allincms.article.create-draft');
  assert.equal(created.site_key, siteKey);
  const expectedPayloadDigest = computeAllinCmsMutationTargetDigest({ ...desiredPayload, siteId });
  assert.equal(created.target_digest, computeAllinCmsMutationTargetDigest({ site_id: siteId, payload_digest: expectedPayloadDigest }));
  assert.notEqual(created.target_digest, computeAllinCmsMutationTargetDigest({ site_id: siteId, payload_digest: computeAllinCmsMutationTargetDigest(desiredPayload) }));
  const updateOperation = { entity_type: 'article', intent: 'update', entity_ref: 'article:new-guide', identity: { id: 'post-77' } };
  const updated = allinCmsOperationAuthorization({ plan, operation: updateOperation, siteKey, siteId, approvalActor: 'Test Human' });
  assert.equal(updated.operation, 'allincms.article.update');
  assert.equal(updated.target_digest, computeAllinCmsMutationTargetDigest({ site_id: siteId, post_id: 'post-77' }));
  const publishOperation = { entity_type: 'article', intent: 'publish', entity_ref: 'article:new-guide', identity: { id: 'post-77' } };
  const published = allinCmsOperationAuthorization({ plan, operation: publishOperation, siteKey, siteId, approvalActor: 'Test Human' });
  assert.equal(published.operation, 'allincms.article.publish');
  assert.equal(published.target_digest, updated.target_digest);
  const publishedWithRuntimeId = allinCmsOperationAuthorization({ plan, operation: publishOperation, siteKey, siteId, approvalActor: 'Test Human', runtimeEntityId: 'post-88' });
  assert.equal(publishedWithRuntimeId.operation, 'allincms.article.publish');
  assert.equal(publishedWithRuntimeId.target_digest, computeAllinCmsMutationTargetDigest({ site_id: siteId, post_id: 'post-88' }));
  assert.notEqual(publishedWithRuntimeId.target_digest, updated.target_digest);
  assert.throws(() => allinCmsOperationAuthorization({
    plan, operation: { entity_type: 'article', intent: 'create', entity_ref: 'article:missing', identity: { id: null } }, siteKey, siteId,
  }), /matches no desired_state entity/);
});

test('allinCmsOperationAuthorization freezes the approved plan authorization window exactly and never mints a fresh one', () => {
  const plan = makeArticleCreatePlanFixture();
  const siteKey = 'synthetic-site';
  const siteId = 'sid-1';
  // The frozen plan window deliberately already ended: a driver that renewed
  // the window from now() would produce a future expires_at instead.
  const approvedAt = new Date(Date.now() - 10 * 60000).toISOString();
  const expiresAt = new Date(Date.now() - 5 * 60000).toISOString();
  plan.authorization_scope.approved_at = approvedAt;
  plan.authorization_scope.expires_at = expiresAt;
  const created = allinCmsOperationAuthorization({ plan, operation: plan.operations[0], siteKey, siteId, approvalActor: 'Test Human' });
  assert.equal(created.approved_at, approvedAt, 'approved_at must be exactly the plan-frozen timestamp');
  assert.equal(created.expires_at, expiresAt, 'expires_at must be exactly the plan-frozen timestamp');
  assert.ok(Date.parse(created.expires_at) < Date.now(), 'a renewed window would have moved expires_at into the future');
  const missingApprovedAt = structuredClone(plan);
  delete missingApprovedAt.authorization_scope.approved_at;
  assert.throws(() => allinCmsOperationAuthorization({ plan: missingApprovedAt, operation: missingApprovedAt.operations[0], siteKey, siteId, approvalActor: 'Test Human' }), /approved_at/);
  const blankExpiresAt = structuredClone(plan);
  blankExpiresAt.authorization_scope.expires_at = '   ';
  assert.throws(() => allinCmsOperationAuthorization({ plan: blankExpiresAt, operation: blankExpiresAt.operations[0], siteKey, siteId, approvalActor: 'Test Human' }), /expires_at/);
});

test('article:create handler fails closed without real before-snapshot, readback, and editor-reopen providers', async () => {
  const plan = makeArticleCreatePlanFixture();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const requested = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const readbackProvider = async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] });
  const context = { plan, operation: plan.operations[0] };
  const step = (extra) => createAllinCmsPlanHandlerSet({ siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request, readbackProvider, ...extra })['article:create'];
  await assert.rejects(() => step({}).execute(context), /articleBeforePostIdsProvider/);
  await assert.rejects(() => step({ articleBeforePostIdsProvider: async () => ['existing-1'] }).execute(context), /articleCreateReadbackProvider/);
  await assert.rejects(() => step({
    articleBeforePostIdsProvider: async () => ['existing-1'],
    articleCreateReadbackProvider: async () => ({ record: null, afterPostIds: [] }),
  }).execute(context), /articleEditorReopenProvider/);
  await assert.rejects(() => step({
    articleBeforePostIdsProvider: async () => 'not-an-array',
    articleCreateReadbackProvider: async () => ({ record: null, afterPostIds: [] }),
    articleEditorReopenProvider: async () => null,
  }).execute(context), /must return an array of IDs/);
  await assert.rejects(() => step({
    articleBeforePostIdsProvider: async () => ['existing-1', 'existing-1'],
    articleCreateReadbackProvider: async () => ({ record: null, afterPostIds: [] }),
    articleEditorReopenProvider: async () => null,
  }).execute(context), /articleBeforePostIdsProvider returned duplicate IDs/);
  assert.equal(requested.length, 0);
});

test('article:create handler runs createPostDraft through the providers and reports the created post', async () => {
  const plan = makeArticleCreatePlanFixture();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const events = [];
  const requested = [];
  let postIds = ['existing-1'];
  const request = async (details) => {
    events.push(`request:${details.actionName}`);
    requested.push(details);
    postIds = [...postIds, 'created-1'];
    return { status: 200, ok: true, contentType: 'text/x-component' };
  };
  const createdRecord = () => ({
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1', id: 'created-1',
  });
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site',
    siteId: 'sid-1',
    runtime,
    request,
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    articleBeforePostIdsProvider: async () => { events.push('before-snapshot'); return [...postIds]; },
    articleCreateReadbackProvider: async () => { events.push('create-readback'); return { record: createdRecord(), afterPostIds: [...postIds] }; },
    articleEditorReopenProvider: async ({ createdPostId }) => { events.push(`editor-reopen:${createdPostId}`); return { status: 200, authenticated: true, healthy: true, postId: createdPostId }; },
  });
  const result = await handlers['article:create'].execute({ plan, operation: plan.operations[0] });
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'created-1' });
  assert.deepEqual(events, ['before-snapshot', 'request:postCreate', 'create-readback', 'editor-reopen:created-1']);
  assert.equal(requested.length, 1);
  assert.equal(requested[0].url, 'https://workspace.laicms.com/synthetic-site/posts');
  assert.deepEqual(requested[0].payload, {
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1',
  });
});

test('article:create provider delay crossing the frozen plan expiry sends zero host requests and fails with expired', async () => {
  const plan = makeArticleCreatePlanFixture();
  // Short real window: approved 1s ago, expires 250ms from now. The
  // before-snapshot provider below deliberately takes 600ms, so the request
  // is attempted strictly after the frozen window has ended.
  plan.authorization_scope.approved_at = new Date(Date.now() - 1000).toISOString();
  plan.authorization_scope.expires_at = new Date(Date.now() + 250).toISOString();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const events = [];
  const requested = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request,
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    articleBeforePostIdsProvider: async () => { events.push('before-snapshot'); await new Promise((resolve) => setTimeout(resolve, 600)); return ['existing-1']; },
    articleCreateReadbackProvider: async () => { events.push('create-readback'); throw new Error('create readback must not run after an expired-window refusal'); },
    articleEditorReopenProvider: async () => { events.push('editor-reopen'); throw new Error('editor reopen must not run after an expired-window refusal'); },
  });
  await assert.rejects(
    () => handlers['article:create'].execute({ plan, operation: plan.operations[0] }),
    (error) => { assert.match(error.message, /expired/); return true; },
  );
  assert.deepEqual(events, ['before-snapshot'], 'the before-snapshot provider must have executed before the expired-window refusal');
  assert.equal(requested.length, 0, 'no host request may be sent once the frozen plan window has expired');
});

test('driver readback forwards the controller runtime identity to the host readback provider', async () => {
  const plan = makeArticleCreatePlanFixture();
  const seen = [];
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime: { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: {} }, request: async () => ({}),
    readbackProvider: async (args) => {
      seen.push(args);
      return { ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] };
    },
  });
  await handlers['article:create'].readback({ plan, operation: plan.operations[0], observed: {}, priorReadbacks: new Map(), runtime_entity_id: 'created-1', runtime_entity_id_source: 'execute_result' });
  await handlers['article:publish'].readback({ plan, operation: plan.operations[0], observed: {}, priorReadbacks: new Map(), runtime_entity_id: 'created-1', runtime_entity_id_source: 'authoritative_readback' });
  assert.deepEqual(seen.map((args) => [args.runtime_entity_id, args.runtime_entity_id_source, args.siteKey, args.siteId]), [
    ['created-1', 'execute_result', 'synthetic-site', 'sid-1'],
    ['created-1', 'authoritative_readback', 'synthetic-site', 'sid-1'],
  ]);
});

test('article:publish prefers the readback-verified runtime ID for the mutation, authorization and readback', async () => {
  const plan = makeArticleCreatePlanFixture();
  const operation = { operation_id: 'OP-AC-PUB-001', entity_ref: 'article:new-guide', entity_type: 'article', intent: 'publish', identity: structuredClone(plan.operations[0].identity) };
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postUpdate: { actionId: 'p'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const requested = [];
  const mutationReadbackIds = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const publishedRecord = {
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1', postId: 'created-1', status: 'published',
  };
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request,
    backendReadback: async ({ runtime_entity_id }) => { mutationReadbackIds.push(runtime_entity_id); return publishedRecord; },
    readbackProvider: async () => { throw new Error('readbackProvider must not be used when backendReadback is provided'); },
  });
  const result = await handlers['article:publish'].execute({ plan, operation, runtime_entity_id: 'created-1', runtime_entity_id_source: 'authoritative_readback' });
  assert.deepEqual(result, { request_started: true, status: 'completed' });
  assert.equal(requested.length, 1);
  assert.match(requested[0].url, /synthetic-site\/posts\/created-1\/update$/);
  assert.deepEqual(requested[0].payload.postId, 'created-1');
  assert.deepEqual(mutationReadbackIds, ['created-1']);
});

function makeProductCreatePlanFixture() {
  const identity = { id: null, natural_key: { site_key: 'synthetic-site', slug: 'fp-qc60' }, match_strategy: 'exact_natural_key' };
  // 2026-09-04 stable create payload B1: the create write path takes FLAT
  // URL/OSS media only ({type,value} editor wrappers are readback-only). The
  // fixture keeps alt:null to prove the write normalization drops it while a
  // flat and a {type,value}-wrapped readback both still compare equal.
  const productMedia = { name: 'fp-qc60.webp', alt: null, type: 'image', source: 'url', url: 'https://assets.example.invalid/s/fp-qc60.webp' };
  const fields = {
    name: { value: 'FP-QC60' },
    slug: { value: 'fp-qc60' },
    description: { value: 'Fixture description non-empty.' },
    order: { value: 3 },
    media: { value: productMedia },
    mediaList: { value: [] },
    content: { value: [{ type: 'p', children: [{ text: '产品正文' }] }] },
    categories: { value: ['cat-1'] },
    tags: { value: ['tag-1'] },
    specifications: { value: [{ key: 'Rated power', value: '500W' }] },
  };
  return {
    plan_id: 'COP-host-driver-product-create',
    authorization_scope: {
      status: 'approved', actor: 'Test Human',
      approved_at: new Date(Date.now() - 60000).toISOString(),
      expires_at: new Date(Date.now() + 28 * 60000).toISOString(),
    },
    desired_state: [{ entity_ref: 'product:fp-qc60', entity_type: 'product', intent: 'create', identity, fields }],
    operations: [{ operation_id: 'OP-PC-001', entity_ref: 'product:fp-qc60', entity_type: 'product', intent: 'create', identity: structuredClone(identity) }],
  };
}

function productCreateDriverHarness({ recordOverrides = {}, afterProductIds, requestBehavior, authorizationProvider: customAuthorizationProvider, beforeProviderHook } = {}) {
  const plan = makeProductCreatePlanFixture();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { productCreate: { actionId: 'b'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const events = [];
  const requested = [];
  let productIds = ['prd-existing-1'];
  const request = async (details) => {
    events.push(`request:${details.actionName}`);
    requested.push(details);
    if (requestBehavior) return requestBehavior(details);
    productIds = [...productIds, 'prd-new-1'];
    return { status: 200, ok: true, contentType: 'text/x-component' };
  };
  const createdRecord = () => ({
    name: 'FP-QC60', slug: 'fp-qc60', description: 'Fixture description non-empty.', order: 3,
    media: { type: 'image', value: { name: 'fp-qc60.webp', alt: null, type: 'image', source: 'url', url: 'https://assets.example.invalid/s/fp-qc60.webp' } },
    mediaList: [], content: [{ type: 'p', children: [{ text: '产品正文' }] }],
    categories: [{ id: 'cat-1' }], tags: [{ id: 'tag-1' }], specifications: [{ key: 'Rated power', value: '500W' }],
    siteId: 'sid-1', id: 'prd-new-1', ...recordOverrides,
  });
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site',
    siteId: 'sid-1',
    runtime,
    request,
    ...(customAuthorizationProvider ? { authorizationProvider: customAuthorizationProvider } : {}),
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    productBeforeProductIdsProvider: async () => { events.push('before-snapshot'); if (beforeProviderHook) await beforeProviderHook(plan); return [...productIds]; },
    productCreateReadbackProvider: async () => { events.push('create-readback'); return { record: createdRecord(), afterProductIds: afterProductIds ?? [...productIds] }; },
  });
  return { plan, handlers, events, requested, context: { plan, operation: plan.operations[0] } };
}

test('product:create handler fails closed without real providers and does not require an upload dialog', async () => {
  const plan = makeProductCreatePlanFixture();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { productCreate: { actionId: 'b'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const requested = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const readbackProvider = async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] });
  const context = { plan, operation: plan.operations[0] };
  const step = (extra) => createAllinCmsPlanHandlerSet({ siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request, readbackProvider, ...extra })['product:create'];
  await assert.rejects(() => step({}).execute(context), /productBeforeProductIdsProvider/);
  await assert.rejects(() => step({ productBeforeProductIdsProvider: async () => ['prd-existing-1'] }).execute(context), /productCreateReadbackProvider/);
  await assert.rejects(() => step({
    productBeforeProductIdsProvider: async () => ['prd-existing-1', 'prd-existing-1'],
    productCreateReadbackProvider: async () => ({ record: null, afterProductIds: [] }),
  }).execute(context), /duplicate IDs/);
  assert.equal(requested.length, 0);
});

test('product:create handler runs createProductDraft over a real sole-delta snapshot', async () => {
  const h = productCreateDriverHarness();
  const result = await h.handlers['product:create'].execute(h.context);
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'prd-new-1' });
  assert.deepEqual(h.events, ['before-snapshot', 'request:productCreate', 'create-readback']);
  assert.equal(h.requested.length, 1);
  assert.equal(h.requested[0].url, 'https://workspace.laicms.com/synthetic-site/products');
  // 2026-09-04 stable create payload: the wire payload is the prepared frozen
  // snapshot — flat URL media with alt normalized away (no size/mimeType on a
  // new-site URL upload), never the {type,value} editor wrapper.
  assert.deepEqual(h.requested[0].payload, {
    name: 'FP-QC60', slug: 'fp-qc60', description: 'Fixture description non-empty.', order: 3,
    media: { name: 'fp-qc60.webp', type: 'image', source: 'url', url: 'https://assets.example.invalid/s/fp-qc60.webp' },
    mediaList: [], content: [{ type: 'p', children: [{ text: '产品正文' }] }],
    categories: ['cat-1'], tags: ['tag-1'], specifications: [{ key: 'Rated power', value: '500W' }],
    siteId: 'sid-1',
  });
});

test('product:create handler stops on multi-delta or cross-site readback evidence', async () => {
  const multiDelta = productCreateDriverHarness({ afterProductIds: ['prd-existing-1', 'prd-new-1', 'prd-new-2'] });
  await assert.rejects(() => multiDelta.handlers['product:create'].execute(multiDelta.context), /expected exactly one new product ID after create, found 2/);
  assert.equal(multiDelta.requested.length, 1);
  const crossSite = productCreateDriverHarness({ recordOverrides: { siteId: 'other-site' } });
  await assert.rejects(() => crossSite.handlers['product:create'].execute(crossSite.context), /different site/);
  assert.equal(crossSite.requested.length, 1);
});

test('product:create provider delay crossing the frozen plan expiry sends zero host requests and fails with expired', async () => {
  const plan = makeProductCreatePlanFixture();
  // Short real window plus a 600ms before-snapshot provider delay: the request
  // is attempted strictly after the frozen window has ended.
  plan.authorization_scope.approved_at = new Date(Date.now() - 1000).toISOString();
  plan.authorization_scope.expires_at = new Date(Date.now() + 250).toISOString();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { productCreate: { actionId: 'b'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const events = [];
  const requested = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request,
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    productBeforeProductIdsProvider: async () => { events.push('before-snapshot'); await new Promise((resolve) => setTimeout(resolve, 600)); return ['prd-existing-1']; },
    productCreateReadbackProvider: async () => { events.push('create-readback'); throw new Error('create readback must not run after an expired-window refusal'); },
  });
  await assert.rejects(
    () => handlers['product:create'].execute({ plan, operation: plan.operations[0] }),
    (error) => { assert.match(error.message, /expired/); return true; },
  );
  assert.deepEqual(events, ['before-snapshot'], 'the before-snapshot provider must have executed before the expired-window refusal');
  assert.equal(requested.length, 0, 'no host request may be sent once the frozen plan window has expired');
});

// P0 window re-mint bypass: a custom authorizationProvider that re-mints a
// fresh now-based window would sail through the request layer's expiry check
// (the fresh window is not expired), so the driver itself must refuse it
// before any request is attempted.
function remintingAuthorizationProvider(events) {
  return (args) => {
    events.push('authorization-provider');
    const frozen = allinCmsOperationAuthorization(args);
    const now = Date.now();
    return { ...frozen, approved_at: new Date(now - 1000).toISOString(), expires_at: new Date(now + 29 * 60000).toISOString() };
  };
}

function assertWindowDriftRejection(promise, requested) {
  return assert.rejects(
    promise,
    (error) => {
      assert.equal(error.code, 'AUTHORIZATION_WINDOW_DRIFT');
      assert.match(error.message, /AUTHORIZATION_WINDOW_DRIFT/);
      return true;
    },
  ).then(() => {
    assert.equal(requested.length, 0, 'a re-minted authorization window must be refused before any host request');
  });
}

test('article:create custom provider re-minting a fresh window after crossing plan expiry is refused before any request', async () => {
  const plan = makeArticleCreatePlanFixture();
  // Short real window: approved 1s ago, expires 250ms from now. The
  // before-snapshot provider delays 600ms, so the re-minted context is
  // produced strictly after the frozen plan window has ended.
  plan.authorization_scope.approved_at = new Date(Date.now() - 1000).toISOString();
  plan.authorization_scope.expires_at = new Date(Date.now() + 250).toISOString();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const events = [];
  const requested = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request,
    authorizationProvider: remintingAuthorizationProvider(events),
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    articleBeforePostIdsProvider: async () => { events.push('before-snapshot'); await new Promise((resolve) => setTimeout(resolve, 600)); return ['existing-1']; },
    articleCreateReadbackProvider: async () => { events.push('create-readback'); throw new Error('create readback must not run after a window-drift refusal'); },
    articleEditorReopenProvider: async () => { events.push('editor-reopen'); throw new Error('editor reopen must not run after a window-drift refusal'); },
  });
  await assertWindowDriftRejection(
    () => handlers['article:create'].execute({ plan, operation: plan.operations[0] }),
    requested,
  );
  assert.deepEqual(events, ['before-snapshot', 'authorization-provider'], 'providers must have executed before the window-drift refusal');
});

test('product:create custom provider re-minting a fresh window after crossing plan expiry is refused before any request', async () => {
  const plan = makeProductCreatePlanFixture();
  plan.authorization_scope.approved_at = new Date(Date.now() - 1000).toISOString();
  plan.authorization_scope.expires_at = new Date(Date.now() + 250).toISOString();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { productCreate: { actionId: 'b'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const events = [];
  const requested = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request,
    authorizationProvider: remintingAuthorizationProvider(events),
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    productBeforeProductIdsProvider: async () => { events.push('before-snapshot'); await new Promise((resolve) => setTimeout(resolve, 600)); return ['prd-existing-1']; },
    productCreateReadbackProvider: async () => { events.push('create-readback'); throw new Error('create readback must not run after a window-drift refusal'); },
  });
  await assertWindowDriftRejection(
    () => handlers['product:create'].execute({ plan, operation: plan.operations[0] }),
    requested,
  );
  assert.deepEqual(events, ['before-snapshot', 'authorization-provider'], 'providers must have executed before the window-drift refusal');
});

test('driver refuses authorization contexts with missing, empty, or plan-missing window strings', async () => {
  const plan = makeArticleCreatePlanFixture();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const requested = [];
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const readbackProvider = async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] });
  const providers = {
    articleBeforePostIdsProvider: async () => ['existing-1'],
    articleCreateReadbackProvider: async () => ({ record: null, afterPostIds: [] }),
    articleEditorReopenProvider: async () => null,
  };
  const step = (authorizationProvider) => createAllinCmsPlanHandlerSet({ siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request, readbackProvider, authorizationProvider, ...providers })['article:create'];
  const validArgs = { plan, operation: plan.operations[0], siteKey: 'synthetic-site', siteId: 'sid-1', approvalActor: 'Test Human' };
  const frozen = () => allinCmsOperationAuthorization(validArgs);
  await assertWindowDriftRejection(() => step(() => ({ ...frozen(), approved_at: undefined })).execute({ plan, operation: plan.operations[0] }), requested);
  await assertWindowDriftRejection(() => step(() => ({ ...frozen(), expires_at: '' })).execute({ plan, operation: plan.operations[0] }), requested);
  await assertWindowDriftRejection(() => step(() => ({ ...frozen(), approved_at: '   ' })).execute({ plan, operation: plan.operations[0] }), requested);
  const planWithoutApprovedAt = structuredClone(plan);
  delete planWithoutApprovedAt.authorization_scope.approved_at;
  // The provider returns a fully valid context, but the executing plan froze no
  // approved_at, so the strings cannot match and the driver must refuse.
  await assertWindowDriftRejection(
    () => step(() => frozen()).execute({ plan: planWithoutApprovedAt, operation: planWithoutApprovedAt.operations[0] }),
    requested,
  );
  assert.equal(requested.length, 0);
});

test('custom authorizationProvider whose window strings exactly equal plan.authorization_scope is not blocked', async () => {
  const plan = makeArticleCreatePlanFixture();
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const requested = [];
  let providerCalls = 0;
  const request = async (details) => { requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const createdRecord = () => ({
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1', id: 'created-1',
  });
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request,
    authorizationProvider: (args) => {
      providerCalls += 1;
      const context = allinCmsOperationAuthorization(args);
      assert.equal(context.approved_at, plan.authorization_scope.approved_at);
      assert.equal(context.expires_at, plan.authorization_scope.expires_at);
      return context;
    },
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    articleBeforePostIdsProvider: async () => ['existing-1'],
    articleCreateReadbackProvider: async () => ({ record: createdRecord(), afterPostIds: ['existing-1', 'created-1'] }),
    articleEditorReopenProvider: async ({ createdPostId }) => ({ status: 200, authenticated: true, healthy: true, postId: createdPostId }),
  });
  const result = await handlers['article:create'].execute({ plan, operation: plan.operations[0] });
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'created-1' });
  assert.ok(providerCalls >= 1, 'the injected custom provider must actually have been used');
  assert.equal(requested.length, 1, 'a window-identical custom provider must not be blocked');
  assert.match(requested[0].url, /synthetic-site\/posts$/);
});

// P0 authorization-context TOCTOU: the driver projects whatever the provider
// returns into a driver-owned frozen plain-data snapshot, checks the plan
// window on that snapshot, and hands only the snapshot to the operation. A
// mutable plain object flipped to a fresh window by a microtask, or an
// accessor/Proxy object serving a fresh window to later reads, can then only
// ever re-present the plan-frozen window, which the request layer refuses.
function articleCreateAuthorizationHarness({ authorizationProvider, articleCreateReadbackProvider = null, shortWindow = false } = {}) {
  const plan = makeArticleCreatePlanFixture();
  if (shortWindow) {
    // Short real window: approved 1s ago, expires 250ms from now. The
    // before-snapshot provider delays 600ms, so the authorization provider
    // returns strictly after the frozen plan window has ended.
    plan.authorization_scope.approved_at = new Date(Date.now() - 1000).toISOString();
    plan.authorization_scope.expires_at = new Date(Date.now() + 250).toISOString();
  }
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const events = [];
  const requested = [];
  const request = async (details) => { events.push('request'); requested.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const createdRecord = () => ({
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1', id: 'created-1',
  });
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request,
    authorizationProvider: (args) => { events.push('authorization-provider'); return authorizationProvider(args); },
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    articleBeforePostIdsProvider: async () => { events.push('before-snapshot'); if (shortWindow) await new Promise((resolve) => setTimeout(resolve, 600)); return ['existing-1']; },
    ...(articleCreateReadbackProvider
      ? { articleCreateReadbackProvider: async (args) => { events.push('create-readback'); return articleCreateReadbackProvider(args); } }
      : { articleCreateReadbackProvider: async () => { events.push('create-readback'); return { record: createdRecord(), afterPostIds: ['existing-1', 'created-1'] }; } }),
    articleEditorReopenProvider: async ({ createdPostId }) => { events.push('editor-reopen'); return { status: 200, authenticated: true, healthy: true, postId: createdPostId }; },
  });
  return { plan, handlers, events, requested };
}

test('ambiguous article:create failure carries a locked requestStarted that prototype pollution cannot flip to not-started (2026-09-04 pollution fix)', async () => {
  // Force the "not confirmed" branch (drifted readback =>
  // stopped_manual_intervention with requestStarted=true), then arm an
  // Object.prototype.requestStarted accessor that answers false. The thrown
  // error must carry its own locked non-writable true (read via the own
  // descriptor by the controller), and the pollution getter must never be
  // consulted while the driver materializes the error.
  let pollutionReads = 0;
  Object.defineProperty(Object.prototype, 'requestStarted', {
    get() { pollutionReads += 1; return false; },
    set() {},
    configurable: true,
  });
  try {
    const harness = articleCreateAuthorizationHarness({
      authorizationProvider: (args) => allinCmsOperationAuthorization(args),
      articleCreateReadbackProvider: async () => ({
        record: { title: 'DRIFTED', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3, coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }], siteId: 'sid-1', id: 'created-1' },
        afterPostIds: ['existing-1', 'created-1'],
      }),
    });
    await assert.rejects(
      () => harness.handlers['article:create'].execute({ plan: harness.plan, operation: harness.plan.operations[0] }),
      (error) => {
        const descriptor = Object.getOwnPropertyDescriptor(error, 'requestStarted');
        assert.equal(descriptor?.value, true, 'the own locked requestStarted must be true');
        assert.equal(descriptor?.writable, false, 'the own requestStarted must be non-writable');
        assert.equal(descriptor?.configurable, false, 'the own requestStarted must be non-configurable');
        assert.match(error.message, /article create not confirmed/);
        return true;
      },
    );
    assert.equal(pollutionReads, 0, 'the polluted prototype accessor must never be read while materializing the error');
  } finally {
    delete Object.prototype.requestStarted;
  }
  assert.equal(({}).requestStarted, undefined, 'the prototype pollution must be cleaned up');
});

test('plain authorization object flipped to a fresh window by queueMicrotask still sends zero requests after plan expiry', async () => {
  // The provider returns the plan-frozen window, then a queued microtask
  // mutates the same reference to a fresh window after the driver check, so
  // pre-fix the request layer validated the fresh window and sent the request.
  const harness = articleCreateAuthorizationHarness({
    shortWindow: true,
    authorizationProvider: (args) => {
      const frozen = allinCmsOperationAuthorization(args);
      const mutable = { ...frozen };
      queueMicrotask(() => {
        const now = Date.now();
        mutable.approved_at = new Date(now - 1000).toISOString();
        mutable.expires_at = new Date(now + 29 * 60000).toISOString();
        harness.events.push('mutated-to-fresh-window');
      });
      return mutable;
    },
  });
  await assert.rejects(
    () => harness.handlers['article:create'].execute({ plan: harness.plan, operation: harness.plan.operations[0] }),
    (error) => { assert.match(error.message, /expired/); return true; },
  );
  // The attack really fired (mutation happened before the refusal) but the
  // request layer only ever saw the frozen plan window on the snapshot.
  assert.deepEqual(harness.events, ['before-snapshot', 'authorization-provider', 'mutated-to-fresh-window']);
  assert.equal(harness.requested.length, 0, 'a microtask-mutated authorization window must not produce any host request');
});

test('authorization object serving a fresh window through getters is refused as non-stable data before any request', async () => {
  // Access-timing attack: the getters serve the plan strings to the driver's
  // window reads and fresh past-approved / future-expiry strings to the
  // request layer's later reads.
  let approvedReads = 0;
  let expiresReads = 0;
  const harness = articleCreateAuthorizationHarness({
    shortWindow: true,
    authorizationProvider: (args) => {
      const frozen = allinCmsOperationAuthorization(args);
      return {
        ...frozen,
        get approved_at() { approvedReads += 1; return approvedReads <= 1 ? frozen.approved_at : new Date(Date.now() - 1000).toISOString(); },
        get expires_at() { expiresReads += 1; return expiresReads <= 1 ? frozen.expires_at : new Date(Date.now() + 29 * 60000).toISOString(); },
      };
    },
  });
  await assert.rejects(
    () => harness.handlers['article:create'].execute({ plan: harness.plan, operation: harness.plan.operations[0] }),
    (error) => {
      assert.equal(error.code, 'AUTHORIZATION_CONTEXT_NOT_STABLE_DATA');
      assert.match(error.message, /accessor property/);
      return true;
    },
  );
  // Detection is descriptor-level: the driver never even read the getter
  // values, and no request or evidence provider ran.
  assert.equal(approvedReads, 0);
  assert.equal(expiresReads, 0);
  assert.deepEqual(harness.events, ['before-snapshot', 'authorization-provider']);
  assert.equal(harness.requested.length, 0, 'an accessor-based fresh-window authorization context must be refused before any request');
});

test('Proxy authorization object is snapshot-neutralized or fail-closed, never a post-check mutation channel', async () => {
  // Proxy variant of the access-timing attack: the get and
  // getOwnPropertyDescriptor traps serve the plan-frozen window on the first
  // read per field and a fresh window afterwards. The driver reads each own
  // data property exactly once during projection, so the frozen snapshot
  // carries the plan window and the request layer refuses it after expiry.
  const reads = { approved_at: 0, expires_at: 0 };
  const proxyAttack = articleCreateAuthorizationHarness({
    shortWindow: true,
    authorizationProvider: (args) => {
      const frozen = allinCmsOperationAuthorization(args);
      const windowFor = (field) => {
        reads[field] += 1;
        return reads[field] <= 1 ? frozen[field] : new Date(Date.now() + 29 * 60000).toISOString();
      };
      return new Proxy({ ...frozen }, {
        get: (object, key, receiver) => (key === 'approved_at' || key === 'expires_at' ? windowFor(key) : Reflect.get(object, key, receiver)),
        getOwnPropertyDescriptor: (object, key) => ({
          ...(Object.getOwnPropertyDescriptor(object, key) ?? { writable: true, enumerable: true, configurable: true }),
          value: key === 'approved_at' || key === 'expires_at' ? windowFor(key) : object[key],
        }),
      });
    },
  });
  await assert.rejects(
    () => proxyAttack.handlers['article:create'].execute({ plan: proxyAttack.plan, operation: proxyAttack.plan.operations[0] }),
    (error) => { assert.match(error.message, /expired/); return true; },
  );
  assert.deepEqual(reads, { approved_at: 1, expires_at: 1 }, 'each window field must be read exactly once during projection');
  assert.equal(proxyAttack.requested.length, 0, 'a proxy-served fresh window must not produce any host request');

  // A Proxy whose descriptor trap throws cannot be copied reliably and must
  // fail closed before any request.
  const throwingProxy = articleCreateAuthorizationHarness({
    shortWindow: true,
    authorizationProvider: (args) => new Proxy({ ...allinCmsOperationAuthorization(args) }, {
      getOwnPropertyDescriptor: () => { throw new Error('descriptor trap boom'); },
    }),
  });
  await assert.rejects(
    () => throwingProxy.handlers['article:create'].execute({ plan: throwingProxy.plan, operation: throwingProxy.plan.operations[0] }),
    (error) => {
      assert.equal(error.code, 'AUTHORIZATION_CONTEXT_NOT_STABLE_DATA');
      assert.match(error.message, /descriptor threw/);
      return true;
    },
  );
  assert.deepEqual(throwingProxy.events, ['before-snapshot', 'authorization-provider']);
  assert.equal(throwingProxy.requested.length, 0, 'an uncopyable proxy authorization context must fail closed before any request');
});

test('legitimate non-frozen plain authorization object passes, and later changes to the provider object never reach the operation', async () => {
  // The provider returns a plain (non-frozen) object with the exact plan
  // window; a queued microtask then corrupts the ORIGINAL object's window and
  // digest fields before the request layer validates. The operation only ever
  // receives the frozen snapshot, so the request still succeeds -- if the
  // driver had passed the provider's reference, validation would have failed.
  const harness = articleCreateAuthorizationHarness({
    authorizationProvider: (args) => {
      const frozen = allinCmsOperationAuthorization(args);
      const original = { ...frozen };
      queueMicrotask(() => {
        original.approved_at = '1999-01-01T00:00:00.000Z';
        original.expires_at = '1999-01-01T00:00:00.000Z';
        original.target_digest = '0'.repeat(64);
        original.operation = 'allincms.article.delete';
        harness.events.push('corrupted-provider-original');
      });
      return original;
    },
  });
  const result = await harness.handlers['article:create'].execute({ plan: harness.plan, operation: harness.plan.operations[0] });
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'created-1' });
  // The corruption fired before the request layer read the context, proving
  // the validated object was the frozen snapshot, not the provider reference.
  assert.ok(harness.events.indexOf('corrupted-provider-original') < harness.events.indexOf('request'), 'the provider object must be corrupted before the request-layer validation read');
  assert.equal(harness.requested.length, 1, 'a legitimate plain authorization object must not be blocked');
  assert.match(harness.requested[0].url, /synthetic-site\/posts$/);
});

// ---- P0-3.3a expected full-field binding for article/product create ----

function articleCreateBindingHarness({ recordOverrides = {}, mutateFixture = null, authorizationWrapper = null, beforeProviderHook = null } = {}) {
  const plan = makeArticleCreatePlanFixture();
  if (mutateFixture) mutateFixture(plan);
  const runtime = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };
  const events = [];
  const requested = [];
  let postIds = ['existing-1'];
  const request = async (details) => { requested.push(details); postIds = [...postIds, 'created-1']; return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const createdRecord = () => ({
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1', id: 'created-1', ...recordOverrides,
  });
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site', siteId: 'sid-1', runtime, request,
    authorizationProvider: authorizationWrapper || ((args) => allinCmsOperationAuthorization(args)),
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    articleBeforePostIdsProvider: async () => { events.push('before-snapshot'); if (beforeProviderHook) await beforeProviderHook(plan); return [...postIds]; },
    articleCreateReadbackProvider: async () => { events.push('create-readback'); return { record: createdRecord(), afterPostIds: [...postIds] }; },
    articleEditorReopenProvider: async ({ createdPostId }) => { events.push('editor-reopen'); return { status: 200, authenticated: true, healthy: true, postId: createdPostId }; },
  });
  return { plan, handlers, events, requested, context: { plan, operation: plan.operations[0] } };
}

const ARTICLE_CREATE_DRIFTS = {
  title: 'DRIFTED TITLE',
  slug: 'drifted-slug',
  excerpt: 'Drifted excerpt.',
  order: 99,
  coverImage: { name: 'drifted.webp', alt: null, type: 'image', source: 'url', url: 'https://assets.example.invalid/s/drifted.webp' },
  categories: ['cat-drift'],
  tags: ['tag-drift'],
  content: [{ type: 'p', children: [{ text: '被替换的正文' }], id: 'node-drift' }],
};

test('article:create rejects a created record drifted on any of the 8 contract fields with exactly one request and zero retries', async () => {
  for (const [field, drift] of Object.entries(ARTICLE_CREATE_DRIFTS)) {
    const h = articleCreateBindingHarness({ recordOverrides: { [field]: drift } });
    await assert.rejects(
      () => h.handlers['article:create'].execute(h.context),
      (error) => {
        assert.match(error.message, /frozen expected payload/, field);
        assert.match(error.message, new RegExp(`${field} drifted from the frozen expected payload`), field);
        return true;
      },
      field,
    );
    assert.equal(h.requested.length, 1, `${field}: exactly one request, zero retries`);
    assert.deepEqual(h.events, ['before-snapshot', 'create-readback'], `${field}: editor reopen must not run for a drifted record`);
  }
});

test('product:create rejects a created record drifted on any of the 10 contract fields with exactly one request and zero retries', async () => {
  const drifts = {
    name: 'DRIFTED FP-QC60',
    slug: 'drifted-slug',
    description: 'Drifted description.',
    order: 99,
    media: null,
    mediaList: [{ type: 'image', value: 'extra-item' }],
    content: [{ type: 'p', children: [{ text: 'drift' }] }],
    categories: [{ id: 'cat-9' }],
    tags: ['tag-9'],
    specifications: [{ key: 'Rated power', value: '750W' }],
  };
  for (const [field, drift] of Object.entries(drifts)) {
    const h = productCreateDriverHarness({ recordOverrides: { [field]: drift } });
    await assert.rejects(
      () => h.handlers['product:create'].execute(h.context),
      (error) => {
        assert.match(error.message, /frozen expected payload/, field);
        assert.match(error.message, new RegExp(`${field} drifted from the frozen expected payload`), field);
        return true;
      },
      field,
    );
    assert.equal(h.requested.length, 1, `${field}: exactly one request, zero retries`);
    assert.deepEqual(h.events, ['before-snapshot', 'request:productCreate', 'create-readback'], field);
  }
  // A media wrapper whose type conflicts with the frozen wrapper fails even
  // when the unwrapped inner values are identical.
  const conflict = productCreateDriverHarness({
    recordOverrides: { media: { type: 'video', value: { name: 'fp-qc60.webp', alt: null, type: 'image', source: 'url', url: 'https://assets.example.invalid/s/fp-qc60.webp' } } },
  });
  await assert.rejects(() => conflict.handlers['product:create'].execute(conflict.context), /media wrapper type "video" conflicts/);
  assert.equal(conflict.requested.length, 1);
});

test('article:create passes a correct {record, afterPostIds} wrapper: {id} taxonomy, key-order-insensitive objects, backend-only fields ignored', async () => {
  const h = articleCreateBindingHarness({
    mutateFixture: (plan) => {
      plan.desired_state[0].fields.coverImage.value = { name: 'cover.webp', alt: '封面', type: 'image', source: 'url', url: 'https://assets.example.invalid/s/cover.webp' };
      plan.desired_state[0].fields.categories.value = ['cat-1', 'cat-2'];
      plan.desired_state[0].fields.tags.value = ['tag-1'];
    },
    recordOverrides: {
      coverImage: { url: 'https://assets.example.invalid/s/cover.webp', source: 'url', type: 'image', alt: '封面', name: 'cover.webp' },
      categories: [{ id: 'cat-2' }, { id: 'cat-1', name: 'Cat 1' }],
      tags: [{ id: 'tag-1' }],
      content: [{ children: [{ text: '正文' }], id: 'node-1', type: 'p' }],
      createdAt: '2026-09-04T00:00:00.000Z', updatedAt: '2026-09-04T00:00:00.000Z', status: 'draft', _status: 'draft',
    },
  });
  const result = await h.handlers['article:create'].execute(h.context);
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'created-1' });
  assert.equal(h.requested.length, 1);
  assert.equal(h.requested[0].payload.coverImage.name, 'cover.webp');
  assert.deepEqual(h.requested[0].payload.categories, ['cat-1', 'cat-2']);
  assert.deepEqual(h.events, ['before-snapshot', 'create-readback', 'editor-reopen']);
});

test('product:create passes a wrapper-correct record: canonical media vs {type,value} wrapper, {id} taxonomy, backend-only fields ignored', async () => {
  const h = productCreateDriverHarness({
    recordOverrides: {
      media: { name: 'fp-qc60.webp', alt: null, type: 'image', source: 'url', url: 'https://assets.example.invalid/s/fp-qc60.webp' },
      categories: [{ id: 'cat-1' }], tags: [{ id: 'tag-1' }],
      createdAt: '2026-09-04T00:00:00.000Z', updatedAt: '2026-09-04T00:00:00.000Z', status: 'draft',
    },
  });
  const result = await h.handlers['product:create'].execute(h.context);
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'prd-new-1' });
  assert.equal(h.requested.length, 1);
  assert.deepEqual(h.requested[0].payload.categories, ['cat-1']);
  assert.deepEqual(h.events, ['before-snapshot', 'request:productCreate', 'create-readback']);
});

test('article:create blocks a desired state missing any of the 8 contract fields before the before-provider and any request', async () => {
  for (const field of Object.keys(ARTICLE_CREATE_DRIFTS)) {
    const h = articleCreateBindingHarness({ mutateFixture: (plan) => { delete plan.desired_state[0].fields[field]; } });
    await assert.rejects(
      () => h.handlers['article:create'].execute(h.context),
      (error) => { assert.match(error.message, /missing the contract field|wrapper/, field); return true; },
      field,
    );
    assert.deepEqual(h.events, [], `${field}: must block before the before-snapshot provider runs`);
    assert.equal(h.requested.length, 0, field);
  }
});

test('product:create blocks a desired state missing any of the 10 contract fields before the before-provider and any request', async () => {
  const reference = productCreateDriverHarness();
  const contractFields = Object.keys(reference.plan.desired_state[0].fields);
  assert.equal(contractFields.length, 10, 'the product create fixture must carry exactly the 10 contract fields');
  for (const field of contractFields) {
    const h = productCreateDriverHarness();
    delete h.plan.desired_state[0].fields[field];
    await assert.rejects(
      () => h.handlers['product:create'].execute(h.context),
      (error) => { assert.match(error.message, /missing the contract field|wrapper/, field); return true; },
      field,
    );
    assert.deepEqual(h.events, [], `${field}: must block before the before-snapshot provider runs`);
    assert.equal(h.requested.length, 0, field);
  }
});

test('article:create blocks wrapperless or value-less desired field wrappers before any provider or request', async () => {
  const cases = [
    ['wrapper without value', (fields) => { fields.title = {}; }, /missing its own value/],
    ['bare non-object wrapper', (fields) => { fields.title = 'bare-title'; }, /must be a field wrapper object/],
    ['undefined wrapper value', (fields) => { fields.title = { value: undefined }; }, /undefined|missing its own value/],
  ];
  for (const [label, mutate, pattern] of cases) {
    const h = articleCreateBindingHarness({ mutateFixture: (plan) => mutate(plan.desired_state[0].fields) });
    await assert.rejects(() => h.handlers['article:create'].execute(h.context), pattern, label);
    assert.deepEqual(h.events, [], label);
    assert.equal(h.requested.length, 0, label);
  }
});

test('article:create blocks entity_ref ambiguity and entity_type mismatch before any provider or request', async () => {
  const zero = articleCreateBindingHarness({ mutateFixture: (plan) => { plan.operations[0].entity_ref = 'article:ghost'; } });
  await assert.rejects(() => zero.handlers['article:create'].execute(zero.context), /matches no desired_state entity/);
  assert.deepEqual(zero.events, []);
  assert.equal(zero.requested.length, 0);
  const two = articleCreateBindingHarness({ mutateFixture: (plan) => { plan.desired_state.push(structuredClone(plan.desired_state[0])); } });
  await assert.rejects(() => two.handlers['article:create'].execute(two.context), /matches 2 desired_state entities/);
  assert.deepEqual(two.events, []);
  assert.equal(two.requested.length, 0);
  const typeMismatch = articleCreateBindingHarness({ mutateFixture: (plan) => { plan.desired_state[0].entity_type = 'product'; } });
  await assert.rejects(() => typeMismatch.handlers['article:create'].execute(typeMismatch.context), /entity_type .* mismatch|resolved a desired_state entity of entity_type/);
  assert.deepEqual(typeMismatch.events, []);
  assert.equal(typeMismatch.requested.length, 0);
});

test('product:create blocks entity_ref ambiguity before any provider or request', async () => {
  const zero = productCreateDriverHarness();
  zero.context.operation.entity_ref = 'product:ghost';
  await assert.rejects(() => zero.handlers['product:create'].execute(zero.context), /matches no desired_state entity/);
  assert.deepEqual(zero.events, []);
  assert.equal(zero.requested.length, 0);
  const two = productCreateDriverHarness();
  two.plan.desired_state.push(structuredClone(two.plan.desired_state[0]));
  await assert.rejects(() => two.handlers['product:create'].execute(two.context), /matches 2 desired_state entities/);
  assert.deepEqual(two.events, []);
  assert.equal(two.requested.length, 0);
});

test('article:create providers mutating the live plan after the freeze cannot move the request body, the authorization digest, or the expected record', async () => {
  const frozenPayload = {
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1',
  };
  const captured = {};
  const h = articleCreateBindingHarness({
    authorizationWrapper: (args) => {
      captured.createPayload = args.createPayload;
      const context = allinCmsOperationAuthorization(args);
      captured.targetDigest = context.target_digest;
      return context;
    },
    beforeProviderHook: async (plan) => {
      // Async provider mutates the live plan AFTER the driver froze the payload.
      plan.desired_state[0].fields.title.value = 'MUTATED TITLE';
      plan.desired_state[0].fields.slug.value = 'mutated-slug';
      plan.desired_state[0].fields.order.value = 99;
    },
  });
  const result = await h.handlers['article:create'].execute(h.context);
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'created-1' });
  assert.equal(h.requested.length, 1, 'the frozen digest must still authorize the frozen body after the plan mutated');
  assert.equal(h.requested[0].payload.title, 'Synthetic New Guide');
  assert.equal(h.requested[0].payload.slug, 'new-guide');
  assert.equal(h.requested[0].payload.order, 3);
  assert.ok(Object.isFrozen(captured.createPayload), 'the authorization payload input must be the frozen object');
  assert.deepEqual({ ...captured.createPayload }, frozenPayload);
  const frozenBinding = deriveAllinCmsMutationBinding({ siteKey: 'synthetic-site', route: '/__driver__', actionName: 'postCreate', payload: frozenPayload });
  const mutatedBinding = deriveAllinCmsMutationBinding({ siteKey: 'synthetic-site', route: '/__driver__', actionName: 'postCreate', payload: { ...frozenPayload, title: 'MUTATED TITLE' } });
  assert.equal(captured.targetDigest, computeAllinCmsMutationTargetDigest(frozenBinding.target));
  assert.notEqual(captured.targetDigest, computeAllinCmsMutationTargetDigest(mutatedBinding.target));
  // Expected stayed frozen as well: a record carrying the mutated title is rejected.
  const mutated = articleCreateBindingHarness({
    beforeProviderHook: async (plan) => { plan.desired_state[0].fields.title.value = 'MUTATED TITLE'; },
    recordOverrides: { title: 'MUTATED TITLE' },
  });
  await assert.rejects(() => mutated.handlers['article:create'].execute(mutated.context), /frozen expected payload/);
  assert.equal(mutated.requested.length, 1);
});

test('product:create providers mutating the live plan after the freeze cannot move the request body or the authorization digest input', async () => {
  let capturedCreatePayload = null;
  const h = productCreateDriverHarness({
    authorizationProvider: (args) => { capturedCreatePayload = args.createPayload; return allinCmsOperationAuthorization(args); },
    beforeProviderHook: async (plan) => {
      plan.desired_state[0].fields.name.value = 'MUTATED NAME';
      plan.desired_state[0].fields.order.value = 99;
    },
  });
  const result = await h.handlers['product:create'].execute(h.context);
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'prd-new-1' });
  assert.equal(h.requested.length, 1, 'the frozen digest must still authorize the frozen body after the plan mutated');
  assert.equal(h.requested[0].payload.name, 'FP-QC60');
  assert.equal(h.requested[0].payload.order, 3);
  assert.ok(Object.isFrozen(capturedCreatePayload), 'the authorization payload input must be the frozen object');
  assert.equal(capturedCreatePayload.name, 'FP-QC60');
});

test('article:create rejects a created record missing any of the 8 contract fields', async () => {
  const reference = articleCreateBindingHarness();
  const baseRecord = {
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: [], tags: [], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1', id: 'created-1',
  };
  for (const field of Object.keys(ARTICLE_CREATE_DRIFTS)) {
    const record = structuredClone(baseRecord);
    delete record[field];
    const handlers = createAllinCmsPlanHandlerSet({
      siteKey: 'synthetic-site', siteId: 'sid-1',
      runtime: { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } },
      request: async () => ({ status: 200, ok: true, contentType: 'text/x-component' }),
      readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
      articleBeforePostIdsProvider: async () => ['existing-1'],
      articleCreateReadbackProvider: async () => ({ record, afterPostIds: ['existing-1', 'created-1'] }),
      articleEditorReopenProvider: async ({ createdPostId }) => ({ status: 200, authenticated: true, healthy: true, postId: createdPostId }),
    });
    await assert.rejects(
      () => handlers['article:create'].execute({ plan: reference.plan, operation: reference.plan.operations[0] }),
      (error) => { assert.match(error.message, new RegExp(`${field} is missing from the created article record`), field); return true; },
      field,
    );
  }
});

test('product:create rejects a created record missing any of the 10 contract fields', async () => {
  const reference = productCreateDriverHarness();
  const baseRecord = {
    name: 'FP-QC60', slug: 'fp-qc60', description: 'Fixture description non-empty.', order: 3,
    media: { type: 'image', value: { name: 'fp-qc60.webp', alt: null, type: 'image', source: 'url', url: 'https://assets.example.invalid/s/fp-qc60.webp' } },
    mediaList: [], content: [{ type: 'p', children: [{ text: '产品正文' }] }],
    categories: [{ id: 'cat-1' }], tags: [{ id: 'tag-1' }], specifications: [{ key: 'Rated power', value: '500W' }],
    siteId: 'sid-1', id: 'prd-new-1',
  };
  for (const field of Object.keys(baseRecord).filter((key) => !['siteId', 'id'].includes(key))) {
    const record = structuredClone(baseRecord);
    delete record[field];
    const handlers = createAllinCmsPlanHandlerSet({
      siteKey: 'synthetic-site', siteId: 'sid-1',
      runtime: { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { productCreate: { actionId: 'b'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } },
      request: async () => ({ status: 200, ok: true, contentType: 'text/x-component' }),
      readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
      productBeforeProductIdsProvider: async () => ['prd-existing-1'],
      productCreateReadbackProvider: async () => ({ record, afterProductIds: ['prd-existing-1', 'prd-new-1'] }),
    });
    await assert.rejects(
      () => handlers['product:create'].execute({ plan: reference.plan, operation: reference.plan.operations[0] }),
      (error) => { assert.match(error.message, new RegExp(`${field} is missing from the created product record`), field); return true; },
      field,
    );
  }
});
