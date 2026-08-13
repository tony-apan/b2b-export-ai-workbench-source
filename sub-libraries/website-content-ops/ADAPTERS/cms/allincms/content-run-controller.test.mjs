import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { calculatePlanDigest } from '../../../scripts/validate-content-operation-plan.mjs';
import { expectedRuntimeScope } from '../../../scripts/runtime-scope.mjs';
import { runAllinCmsContentPlan, validateAllinCmsLiveRunEvidence } from './content-run-controller.mjs';

const H = (char) => `sha256:${char.repeat(64)}`;
const NOW = '2026-08-12T00:10:00Z';
const TASK_ROOT = 'customer-runtime/10_clients/synthetic-client/30_tasks/synthetic-task';
const runtimePath = (suffix) => `${TASK_ROOT}/${suffix}`;
const EVIDENCE_PATH = runtimePath('40_evidence/live-run.json');
const direct = () => ({ mode: 'direct', notes: '' });
const normalized = () => ({ mode: 'normalized', notes: 'Normalized source wording into the target field format.' });
const claimEvidence = (locator, char) => [{ source_id: 'SRC-001', source_digest: H('b'), extraction_id: 'SX-SRC-001', unit_id: `UNIT-${char}`, locator, extraction_digest: H(char) }];

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function digest(value) { return `sha256:${createHash('sha256').update(stable(value)).digest('hex')}`; }
function bytesDigest(value) { return `sha256:${createHash('sha256').update(value).digest('hex')}`; }
function operationSubject(operation, plan) {
  return {
    operation_id: operation.operation_id, entity_ref: operation.entity_ref, entity_type: operation.entity_type,
    intent: operation.intent, identity: operation.identity, field_refs: operation.field_refs,
    publication_effect: operation.publication_effect, capability_ref: operation.capability_ref,
    expected_current_fingerprint: operation.expected_current_fingerprint, dependencies: operation.dependencies,
    desired_entity: plan.desired_state.find((entity) => entity.entity_ref === operation.entity_ref),
  };
}
function verificationArtifactEnvelope(check) {
  return {
    schema_version: '1.0', check_id: check.check_id, evidence_kind: check.evidence_kind,
    captured_at: check.observed_at, site_key: check.site_key, site_id: check.site_id,
    entity_ref: check.entity_ref, entity_id: check.entity_id, subject_digest: check.subject_digest,
    method: check.method, observed_result: check.observed_result, observations: check.observations,
  };
}
function artifactBytesForCheck(check) { return Buffer.from(JSON.stringify(verificationArtifactEnvelope(check))); }
function resealCheckArtifact(check) { check.artifact_digest = bytesDigest(artifactBytesForCheck(check)); return check; }


function reseal(plan) {
  plan.plan_digest = calculatePlanDigest(plan);
  if (plan.authorization_scope.status === 'approved') plan.authorization_scope.plan_sha256 = plan.plan_digest;
  return plan;
}

function makePlan() {
  return reseal({
    schema_version: '1.1', plan_id: 'COP-controller-001', plan_digest: H('0'),
    client_id: 'synthetic-client', company_id: 'synthetic-company', task_id: 'synthetic-task',
    runtime_scope: expectedRuntimeScope({ client_id: 'synthetic-client', company_id: 'synthetic-company', task_id: 'synthetic-task' }),
    execution_mode: 'audit', plan_phase: 'site_operation',
    cms_adapter: { id: 'allincms', version: 'runtime-discovered', observed_at: '2026-08-12T00:00:00Z', deployment_fingerprint: H('a') },
    site_selector: { target_scope: 'site', site_key: 'site-fixture', site_id: 'site-id-fixture', account_user_id: 'user-fixture', selection_source: 'user-confirmed', bootstrap_readback_ref: null, bootstrap_plan_digest: null, cross_site_fallback: false },
    source_snapshot: { captured_at: '2026-08-12T00:00:00Z', sources: [{
      source_id: 'SRC-001', kind: 'brief', location: runtimePath('10_sources/brief.md'), digest: H('b'), authority: 'primary', owner: 'synthetic-owner', rights_status: 'owned', method_use_clearance: 'approved', publication_clearance: 'approved', source_date: '2026-08-01T00:00:00Z', review_after: null, source_scope: 'synthetic-client/synthetic-company/synthetic-task',
      extractions: [{ extraction_id: 'SX-SRC-001', artifact_ref: runtimePath('20_work/source-extraction.json'), source_digest: H('b'), captured_at: '2026-08-12T00:00:00Z', status: 'complete', units: [
        { unit_id: 'UNIT-e', locator: 'brief.md#category-name', extraction_digest: H('e') },
        { unit_id: 'UNIT-f', locator: 'brief.md#article-title', extraction_digest: H('f') },
        { unit_id: 'UNIT-1', locator: 'brief.md#buyer-needs', extraction_digest: H('1') },
      ] }],
    }] },
    claim_ledger: [
      { claim_id: 'CLAIM-CATEGORY-NAME', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: claimEvidence('brief.md#category-name', 'e'), value: 'Guides', notes: '' },
      { claim_id: 'CLAIM-ARTICLE-TITLE', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: claimEvidence('brief.md#article-title', 'f'), value: 'Buyer Guide', notes: '' },
      { claim_id: 'CLAIM-ARTICLE-SUMMARY', status: 'inferred', source_refs: ['SRC-001'], evidence_refs: claimEvidence('brief.md#buyer-needs', '1'), value: 'A guide for qualified buyers.', notes: 'Editorial synthesis.' },
    ],
    capability_snapshot: { captured_at: '2026-08-12T00:01:00Z', expires_at: '2026-08-12T00:31:00Z', deployment_fingerprint: H('a'), capabilities: [
      { capability_id: 'CAP-category-create', entity_type: 'category', action: 'create', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] },
      { capability_id: 'CAP-article-update', entity_type: 'article', action: 'update', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] },
      { capability_id: 'CAP-article-publish', entity_type: 'article', action: 'publish', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] },
    ] },
    desired_state: [
      { entity_ref: 'category:guides', entity_type: 'category', intent: 'upsert', identity: { id: null, natural_key: { site_key: 'site-fixture', slug: 'guides' }, match_strategy: 'exact_natural_key' }, fields: {
        name: { value: 'Guides', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-CATEGORY-NAME'], derivation: direct(), clear_existing: false },
      } },
      { entity_ref: 'article:buyer-guide', entity_type: 'article', intent: 'update', identity: { id: 'article-id-fixture', natural_key: { site_key: 'site-fixture', slug: 'buyer-guide' }, match_strategy: 'exact_id' }, fields: {
        title: { value: 'Buyer Guide', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ARTICLE-TITLE'], derivation: direct(), clear_existing: false },
        summary: { value: 'Buyer-ready guide.', fact_status: 'inferred', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ARTICLE-SUMMARY'], derivation: normalized(), clear_existing: false },
      } },
    ],
    current_state_fingerprint: H('c'),
    diff: [
      { operation_id: 'OP-001', entity_ref: 'category:guides', resolved_intent: 'create', changed_fields: ['name'] },
      { operation_id: 'OP-002', entity_ref: 'article:buyer-guide', resolved_intent: 'update', changed_fields: ['title', 'summary'] },
      { operation_id: 'OP-003', entity_ref: 'article:buyer-guide', resolved_intent: 'publish', changed_fields: [] },
    ],
    operations: [
      { operation_id: 'OP-001', entity_ref: 'category:guides', entity_type: 'category', intent: 'create', identity: { id: null, natural_key: { site_key: 'site-fixture', slug: 'guides' }, match_strategy: 'exact_natural_key' }, field_refs: ['name'], capability_ref: 'CAP-category-create', expected_current_fingerprint: null, dependencies: [], mutation: true, publication_effect: 'private_draft', readback_requirements: ['taxonomy.precise_id', 'taxonomy.exact_slug_and_submitted_fields', 'scope.exact_site_binding', 'taxonomy.same_site_duplicate_slug_excluded'] },
      { operation_id: 'OP-002', entity_ref: 'article:buyer-guide', entity_type: 'article', intent: 'update', identity: { id: 'article-id-fixture', natural_key: { site_key: 'site-fixture', slug: 'buyer-guide' }, match_strategy: 'exact_id' }, field_refs: ['title', 'summary'], capability_ref: 'CAP-article-update', expected_current_fingerprint: H('9'), dependencies: ['OP-001'], mutation: true, publication_effect: 'private_draft', readback_requirements: ['concurrency.expected_current_fingerprint', 'article.complete_backend_field_readback', 'article.editor_reopen_health', 'article.taxonomy_media_binding_readback'] },
      { operation_id: 'OP-003', entity_ref: 'article:buyer-guide', entity_type: 'article', intent: 'publish', identity: { id: 'article-id-fixture', natural_key: { site_key: 'site-fixture', slug: 'buyer-guide' }, match_strategy: 'exact_id' }, field_refs: [], capability_ref: 'CAP-article-publish', expected_current_fingerprint: null, dependencies: ['OP-002'], mutation: true, publication_effect: 'publish_transition', readback_requirements: ['article.backend_published_state', 'article.editor_reopen_health', 'article.public_url', 'article.anonymous_frontend_detail', 'article.visible_content_and_media'] },
    ],
    authorization_scope: { status: 'approved', actor: 'Human Reviewer Fixture', identity_status: 'not_verified', target_scope: 'site', target_key: 'site-fixture', operation_ids: ['OP-001', 'OP-002', 'OP-003'], approved_at: '2026-08-12T00:05:00Z', expires_at: '2026-08-12T00:25:00Z', plan_sha256: null },
    reconciliation_policy: { ambiguous_write: 'read-only-reconcile-before-any-retry', automatic_retry_after_request_started: false, identity_rule: 'exact-id-or-site-scoped-natural-key' },
    verification_plan: { backend_readback: true, editor_reopen: true, frontend: true, evidence_targets: [EVIDENCE_PATH, runtimePath('40_evidence/frontend.json')] },
    writeback_targets: [{ kind: 'task', path: runtimePath('TASK.json'), visibility: 'private-runtime' }],
  });
}

function keepOperations(plan, count) {
  plan.operations = plan.operations.slice(0, count);
  plan.diff = plan.diff.slice(0, count);
  plan.authorization_scope.operation_ids = plan.operations.map((operation) => operation.operation_id);
  return reseal(plan);
}

function makeUpdatePlan() {
  const plan = keepOperations(makePlan(), 2);
  plan.operations = [structuredClone(plan.operations[1])];
  plan.operations[0].operation_id = 'OP-UPDATE-001';
  plan.operations[0].intent = 'update';
  plan.operations[0].expected_current_fingerprint = H('9');
  plan.operations[0].capability_ref = 'CAP-article-update';
  plan.capability_snapshot.capabilities = [{ capability_id: 'CAP-article-update', entity_type: 'article', action: 'update', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] }];
  plan.operations[0].dependencies = [];
  plan.diff = [{ operation_id: 'OP-UPDATE-001', entity_ref: 'article:buyer-guide', resolved_intent: 'update', changed_fields: ['title', 'summary'] }];
  plan.authorization_scope.operation_ids = ['OP-UPDATE-001'];
  return reseal(plan);
}

function makePublishPlan() {
  const plan = makePlan();
  plan.operations = [structuredClone(plan.operations[2])];
  plan.operations[0].operation_id = 'OP-PUBLISH-001';
  plan.operations[0].dependencies = [];
  plan.diff = [{ operation_id: 'OP-PUBLISH-001', entity_ref: 'article:buyer-guide', resolved_intent: 'publish', changed_fields: [] }];
  plan.capability_snapshot.capabilities = [plan.capability_snapshot.capabilities[2]];
  plan.authorization_scope.operation_ids = ['OP-PUBLISH-001'];
  return reseal(plan);
}

function makeMediaCreatePlan() {
  const plan = keepOperations(makePlan(), 1);
  plan.desired_state[0] = {
    ...plan.desired_state[0], entity_ref: 'media:fixture', entity_type: 'media', intent: 'create',
    identity: { id: null, natural_key: { site_key: 'site-fixture', slug: 'media-fixture' }, match_strategy: 'exact_natural_key' },
  };
  plan.desired_state = [plan.desired_state[0]];
  plan.capability_snapshot.capabilities = [{ capability_id: 'CAP-media-create', entity_type: 'media', action: 'create', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] }];
  plan.diff = [{ operation_id: 'OP-MEDIA-001', entity_ref: 'media:fixture', resolved_intent: 'create', changed_fields: ['name'] }];
  plan.operations = [{ operation_id: 'OP-MEDIA-001', entity_ref: 'media:fixture', entity_type: 'media', intent: 'create', identity: structuredClone(plan.desired_state[0].identity), field_refs: ['name'], capability_ref: 'CAP-media-create', expected_current_fingerprint: null, dependencies: [], mutation: true, publication_effect: 'private_draft', readback_requirements: ['media.precise_backend_id', 'media.persisted_url', 'media.anonymous_https_get', 'media.image_decode', 'media.metadata_readback'] }];
  plan.authorization_scope.operation_ids = ['OP-MEDIA-001'];
  return reseal(plan);
}

function mediaPreflight() {
  return observed({ capability_ids: [...observed().capability_ids, 'CAP-media-create'] });
}

function makeReadOnlyPlan(intent = 'noop') {
  const plan = makePlan();
  plan.desired_state[0].intent = intent;
  plan.capability_snapshot.capabilities = [{ capability_id: `CAP-category-${intent}`, entity_type: 'category', action: intent === 'noop' ? 'readback' : 'discover', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] }];
  plan.diff = [{ operation_id: 'OP-READ-001', entity_ref: 'category:guides', resolved_intent: intent, changed_fields: [] }];
  plan.operations = [{ operation_id: 'OP-READ-001', entity_ref: 'category:guides', entity_type: 'category', intent, identity: structuredClone(plan.desired_state[0].identity), field_refs: [], capability_ref: `CAP-category-${intent}`, expected_current_fingerprint: null, dependencies: [], mutation: false, publication_effect: 'none', readback_requirements: intent === 'noop' ? ['read_only.authoritative_noop_readback', 'scope.exact_site_binding'] : ['read_only.authoritative_exploration_readback', 'scope.exact_site_binding'] }];
  plan.authorization_scope.operation_ids = ['OP-READ-001'];
  return reseal(plan);
}

function observed(overrides = {}) {
  return { login_status: 'authenticated', deployment_fingerprint: H('a'), capability_ids: ['CAP-category-create', 'CAP-article-publish', 'CAP-category-noop', 'CAP-category-explore', 'CAP-article-update'], site_key: 'site-fixture', site_id: 'site-id-fixture', account_user_id: 'user-fixture', current_fingerprint: null, ...overrides };
}

const checkKinds = {
  'read_only.authoritative_noop_readback': 'backend_readback',
  'read_only.authoritative_exploration_readback': 'backend_readback',
  'taxonomy.precise_id': 'backend_readback',
  'taxonomy.exact_slug_and_submitted_fields': 'backend_readback',
  'scope.exact_site_binding': 'backend_readback',
  'taxonomy.same_site_duplicate_slug_excluded': 'duplicate_exclusion',
  'concurrency.expected_current_fingerprint': 'concurrency_match',
  'backend.exact_persisted_fields': 'backend_readback',
  'media.precise_backend_id': 'backend_readback',
  'media.persisted_url': 'backend_readback',
  'media.anonymous_https_get': 'anonymous_resource',
  'media.image_decode': 'image_fetch_decode',
  'media.metadata_readback': 'backend_readback',
  'article.complete_backend_field_readback': 'backend_readback',
  'article.editor_reopen_health': 'editor_reopen',
  'article.taxonomy_media_binding_readback': 'backend_readback',
  'article.backend_published_state': 'backend_readback',
  'article.public_url': 'anonymous_resource',
  'article.anonymous_frontend_detail': 'anonymous_frontend',
  'article.visible_content_and_media': 'anonymous_frontend',
};

function verificationCheck(operation, checkId, plan) {
  const evidenceKind = checkKinds[checkId];
  const articleUrl = 'https://site-fixture.web.allincms.com/posts/buyer-guide';
  const mediaUrl = 'https://cdn.example.invalid/media-fixture.png';
  const observations = {
    backend_authoritative: null, exact_match: null, duplicate_count: null,
    current_fingerprint: null, http_status: null, content_type: null, resource_url: null,
    anonymous: null, decoded: null, editor_healthy: null, media_applicable: null,
  };
  if (evidenceKind === 'backend_readback') Object.assign(observations, { backend_authoritative: true, exact_match: true });
  if (evidenceKind === 'concurrency_match') Object.assign(observations, { backend_authoritative: true, exact_match: true, current_fingerprint: operation.expected_current_fingerprint });
  if (evidenceKind === 'duplicate_exclusion') Object.assign(observations, { backend_authoritative: true, duplicate_count: 0 });
  if (evidenceKind === 'editor_reopen') Object.assign(observations, { editor_healthy: true, exact_match: true });
  if (evidenceKind === 'anonymous_resource') Object.assign(observations, { anonymous: true, http_status: 200, resource_url: checkId.startsWith('media.') ? mediaUrl : articleUrl });
  if (evidenceKind === 'anonymous_frontend') Object.assign(observations, { anonymous: true, http_status: 200, exact_match: true, resource_url: articleUrl });
  if (evidenceKind === 'image_fetch_decode') Object.assign(observations, { anonymous: true, http_status: 200, content_type: 'image/png', decoded: true, resource_url: mediaUrl });
  if (checkId === 'media.persisted_url') observations.resource_url = mediaUrl;
  if (checkId === 'article.visible_content_and_media') Object.assign(observations, { media_applicable: true, decoded: true });
  const check = {
    check_id: checkId, evidence_kind: evidenceKind, passed: true,
    artifact_ref: runtimePath(`40_evidence/${operation.operation_id.toLowerCase()}-${checkId.replaceAll('.', '-')}.json`),
    artifact_digest: H('0'), artifact_media_type: 'application/json', observed_at: NOW,
    site_key: 'site-fixture', site_id: 'site-id-fixture', entity_ref: operation.entity_ref,
    entity_id: operation.identity.id ?? `${operation.operation_id}-entity-id`,
    subject_digest: digest(operationSubject(operation, plan)), method: 'synthetic authoritative fixture',
    observed_result: `passed ${checkId}`, observations,
  };
  check.artifact_digest = bytesDigest(artifactBytesForCheck(check));
  return check;
}
function successfulReadback(operation, plan, overrides = {}) {
  return {
    ok: true, authoritative: true, requirements: [...operation.readback_requirements],
    evidence_ref: runtimePath(`40_evidence/${operation.operation_id.toLowerCase()}-readback.json`),
    checks: operation.readback_requirements.map((checkId) => verificationCheck(operation, checkId, plan)),
    entity: { id: operation.operation_id }, ...overrides,
  };
}

function makeHandler(operation, plan, events, overrides = {}) {
  const ref = runtimePath(`40_evidence/${operation.operation_id.toLowerCase()}-readback.json`);
  return {
    async execute() { events.push(`execute:${operation.operation_id}`); return { request_started: true, status: 'completed' }; },
    async readCurrent() { return { fingerprint: operation.expected_current_fingerprint }; },
    async readback() { events.push(`readback:${operation.operation_id}`); return successfulReadback(operation, plan, { evidence_ref: ref }); },
    async reconcile() { events.push(`reconcile:${operation.operation_id}`); return { verdict: 'applied', authoritative: true, evidence_ref: runtimePath(`40_evidence/${operation.operation_id.toLowerCase()}-reconcile.json`) }; },
    ...overrides,
  };
}

function harness(plan, options = {}) {
  const events = [];
  const writes = [];
  const handlers = {};
  for (const operation of plan.operations) handlers[`${operation.entity_type}:${operation.intent}`] = makeHandler(operation, plan, events);
  Object.assign(handlers, options.handlers ?? {});
  let preflightCount = 0;
  let writeCount = 0;
  const params = {
    plan,
    handlers,
    evidencePath: options.evidencePath ?? EVIDENCE_PATH,
    clock: options.clock ?? (() => Date.parse(NOW)),
    runId: 'ACRUN-controller-test',
    readEvidenceArtifact: options.readEvidenceArtifact ?? (async ({ check }) => artifactBytesForCheck(check)),
    preflight: options.preflight ?? (async ({ operation }) => { preflightCount += 1; events.push(`preflight:${operation.operation_id}`); return observed({ current_fingerprint: operation.intent === 'update' ? operation.expected_current_fingerprint : null }); }),
    writeEvidence: options.writeEvidence ?? (async ({ path, evidence }) => { writeCount += 1; events.push(`persist:${evidence.operations.length}:${evidence.status}`); writes.push(structuredClone(evidence)); return { ok: true, evidence_ref: path }; }),
  };
  return { params, handlers, events, writes, counts: () => ({ preflight: preflightCount, write: writeCount }) };
}

async function run(plan = makePlan(), options = {}) {
  const h = harness(plan, options);
  return { h, result: await runAllinCmsContentPlan(h.params) };
}



function mutateReadback(plan, operation, mutate) {
  const readback = successfulReadback(operation, plan);
  mutate(readback);
  return readback;
}

async function expectReadbackBlocked(plan, readback, { readEvidenceArtifact, preflight, pattern } = {}) {
  const operation = plan.operations[0];
  const handler = makeHandler(operation, plan, [], { async readback() { return readback; } });
  const { result } = await run(plan, { handlers: { [`${operation.entity_type}:${operation.intent}`]: handler }, readEvidenceArtifact, preflight });
  assert.equal(result.code, 'AUTHORITATIVE_READBACK_FAILED');
  if (pattern) assert.match(result.problems.join('\n'), pattern);
  return result;
}

function makeSingleRoutePlan({ entityType, intent }) {
  const plan = keepOperations(makePlan(), 1);
  const entityRef = `${entityType}:blocked-fixture`;
  const update = intent === 'update';
  const identity = update
    ? { id: `${entityType}-id-fixture`, natural_key: { site_key: 'site-fixture', slug: 'blocked-fixture' }, match_strategy: 'exact_id' }
    : { id: null, natural_key: { site_key: 'site-fixture', slug: 'blocked-fixture' }, match_strategy: 'exact_natural_key' };
  plan.desired_state[0] = {
    ...plan.desired_state[0], entity_ref: entityRef, entity_type: entityType, intent,
    identity,
  };
  plan.desired_state = [plan.desired_state[0]];
  plan.capability_snapshot.capabilities = [{ capability_id: `CAP-${entityType}-${intent}`, entity_type: entityType, action: intent, maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] }];
  plan.diff = [{ operation_id: 'OP-BLOCK-001', entity_ref: entityRef, resolved_intent: intent, changed_fields: ['name'] }];
  plan.operations = [{ operation_id: 'OP-BLOCK-001', entity_ref: entityRef, entity_type: entityType, intent, identity: structuredClone(plan.desired_state[0].identity), field_refs: ['name'], capability_ref: `CAP-${entityType}-${intent}`, expected_current_fingerprint: update ? H('9') : null, dependencies: [], mutation: true, publication_effect: 'private_draft', readback_requirements: ['self-asserted-live'] }];
  plan.authorization_scope.operation_ids = ['OP-BLOCK-001'];
  return reseal(plan);
}

function assertNoExecute(events) { assert.equal(events.some((event) => event.startsWith('execute:')), false, events.join('\n')); }

test('strict serial success persists preflight, executes, and authoritatively reads back each operation', async () => {
  const { h, result } = await run();
  assert.equal(result.ok, true);
  assert.deepEqual(h.events.filter((event) => !event.startsWith('persist:')), [
    'preflight:OP-001', 'execute:OP-001', 'readback:OP-001',
    'preflight:OP-002', 'execute:OP-002', 'readback:OP-002',
    'preflight:OP-003', 'execute:OP-003', 'readback:OP-003',
  ]);
  assert.equal(result.evidence.status, 'completed');
  assert.ok(result.evidence.operations.every((row) => row.status === 'readback_passed'));
  assert.equal(validateAllinCmsLiveRunEvidence(result.evidence).ok, true);
});

test('pending plan is blocked before preflight or handler execution', async () => {
  const plan = makePlan(); plan.authorization_scope = { status: 'pending', actor: null, identity_status: 'not_verified', target_scope: 'site', target_key: 'site-fixture', operation_ids: plan.operations.map((op) => op.operation_id), approved_at: null, expires_at: null, plan_sha256: null }; reseal(plan);
  const { h, result } = await run(plan);
  assert.equal(result.code, 'PLAN_NOT_EXECUTION_READY'); assertNoExecute(h.events); assert.equal(h.counts().preflight, 0);
});

test('expired authorization is blocked before mutation', async () => {
  const plan = makePlan(); plan.authorization_scope.expires_at = '2026-08-12T00:09:00Z'; reseal(plan);
  const { h, result } = await run(plan);
  assert.equal(result.code, 'PLAN_NOT_EXECUTION_READY'); assertNoExecute(h.events);
});

for (const [name, override, pattern] of [
  ['wrong site key', { site_key: 'other-site' }, /site_target_mismatch/],
  ['wrong site id', { site_id: 'other-id' }, /site_id_mismatch/],
  ['deployment fingerprint drift', { deployment_fingerprint: H('d') }, /deployment_fingerprint_mismatch/],
  ['missing capability', { capability_ids: [] }, /capability_not_current/],
]) {
  test(`${name} records a blocked preflight row and performs no mutation`, async () => {
    const plan = keepOperations(makePlan(), 1);
    const h = harness(plan, { preflight: async ({ operation }) => { h.events.push(`preflight:${operation.operation_id}`); return observed(override); } });
    const result = await runAllinCmsContentPlan(h.params);
    assert.equal(result.code, 'PREFLIGHT_BLOCK'); assert.equal(result.evidence.operations[0].status, 'blocked'); assert.match(result.evidence.operations[0].failure_message, pattern); assertNoExecute(h.events);
  });
}

test('expired capability snapshot is blocked before mutation', async () => {
  const plan = makePlan(); plan.capability_snapshot.expires_at = '2026-08-12T00:09:00Z'; reseal(plan);
  const { h, result } = await run(plan);
  assert.equal(result.code, 'PLAN_NOT_EXECUTION_READY'); assertNoExecute(h.events);
});

test('authorization is revalidated after preflight and evidence persistence immediately before execute', async () => {
  const plan = keepOperations(makePlan(), 1); let now = Date.parse(NOW); let executeCount = 0;
  const handler = makeHandler(plan.operations[0], plan, [], { async execute() { executeCount += 1; return { request_started: true, status: 'completed' }; } });
  const h = harness(plan, {
    handlers: { 'category:create': handler }, clock: () => now,
    writeEvidence: (() => { let writes = 0; return async ({ path }) => { writes += 1; if (writes === 2) now = Date.parse('2026-08-12T00:25:00Z'); return { ok: true, evidence_ref: path }; }; })(),
  });
  const result = await runAllinCmsContentPlan(h.params);
  assert.equal(result.code, 'AUTHORIZATION_EXPIRED_BEFORE_REQUEST'); assert.equal(result.status, 'blocked'); assert.equal(executeCount, 0);
});

test('missing handler blocks before execute and records the operation', async () => {
  const plan = keepOperations(makePlan(), 1); const { h, result } = await run(plan, { handlers: { 'category:create': undefined } });
  assert.equal(result.code, 'HANDLER_BLOCK'); assert.equal(result.evidence.operations[0].status, 'blocked'); assertNoExecute(h.events);
});

for (const [name, handler] of [
  ['top-level Action ID', { action_id: 'dynamic', execute() {}, readback() {} }],
  ['nested Action ID', { execute() {}, readback() {}, metadata: { server_action_id: 'dynamic' } }],
  ['prefixed Action ID', { execute() {}, readback() {}, metadata: { current_action_id: 'dynamic' } }],
  ['aliased credential token', { execute() {}, readback() {}, metadata: { api_token: 'dynamic' } }],
]) {
  test(`${name} in a handler is blocked before execute`, async () => {
    const plan = keepOperations(makePlan(), 1); const { h, result } = await run(plan, { handlers: { 'category:create': handler } });
    assert.equal(result.code, 'HANDLER_BLOCK'); assert.match(result.problems.join('\n'), /must not expose dynamic Action IDs/); assertNoExecute(h.events);
  });
}

test('failure in the first operation prevents the second operation from executing', async () => {
  const plan = keepOperations(makePlan(), 2); const events = [];
  const handler = makeHandler(plan.operations[0], plan, events, { async execute() { events.push('execute:OP-001'); return { request_started: false, status: 'failed' }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } });
  assert.equal(result.code, 'REQUEST_NOT_STARTED'); assert.equal(events.includes('execute:OP-002'), false); assert.equal(result.evidence.operations.length, 1);
});

test('request not started fails without reconcile or retry', async () => {
  const plan = keepOperations(makePlan(), 1); let executeCount = 0; let reconcileCount = 0;
  const handler = makeHandler(plan.operations[0], plan, [], { async execute() { executeCount += 1; return { request_started: false, status: 'failed' }; }, async reconcile() { reconcileCount += 1; throw new Error('must not run'); } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } });
  assert.equal(result.code, 'REQUEST_NOT_STARTED'); assert.equal(executeCount, 1); assert.equal(reconcileCount, 0);
});

test('request may have started without reconcile becomes ambiguous', async () => {
  const plan = keepOperations(makePlan(), 1); const handler = { async execute() { throw new Error('network lost'); }, async readback() {} };
  const { result } = await run(plan, { handlers: { 'category:create': handler } });
  assert.equal(result.status, 'ambiguous'); assert.equal(result.code, 'RECONCILIATION_HANDLER_MISSING');
});

test('unknown reconciliation remains ambiguous and does not retry', async () => {
  const plan = keepOperations(makePlan(), 1); let executeCount = 0;
  const handler = makeHandler(plan.operations[0], plan, [], { async execute() { executeCount += 1; return { request_started: true, status: 'unknown' }; }, async reconcile() { return { verdict: 'unknown', authoritative: true, evidence_ref: runtimePath('40_evidence/reconcile.json') }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } });
  assert.equal(result.code, 'AMBIGUOUS_WRITE'); assert.equal(executeCount, 1);
});

test('authoritative reconciliation confirming not-applied fails without retry', async () => {
  const plan = keepOperations(makePlan(), 1); let executeCount = 0;
  const handler = makeHandler(plan.operations[0], plan, [], { async execute() { executeCount += 1; return { request_started: true, status: 'unknown' }; }, async reconcile() { return { verdict: 'not_applied', authoritative: true, evidence_ref: runtimePath('40_evidence/reconcile.json') }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } });
  assert.equal(result.code, 'WRITE_CONFIRMED_NOT_APPLIED'); assert.equal(executeCount, 1);
});

test('authoritative reconciliation confirming applied proceeds to authoritative readback', async () => {
  const plan = keepOperations(makePlan(), 1); let readbackCount = 0;
  const handler = makeHandler(plan.operations[0], plan, [], { async execute() { return { request_started: true, status: 'unknown' }; }, async readback() { readbackCount += 1; return successfulReadback(plan.operations[0], plan, { evidence_ref: runtimePath('40_evidence/readback.json') }); } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } });
  assert.equal(result.ok, true); assert.equal(readbackCount, 1); assert.equal(result.evidence.operations[0].reconciliation.verdict, 'applied');
});

test('non-authoritative readback fails', async () => {
  const plan = keepOperations(makePlan(), 1); const handler = makeHandler(plan.operations[0], plan, [], { async readback() { return { ok: true, authoritative: false, requirements: [...plan.operations[0].readback_requirements], evidence_ref: runtimePath('40_evidence/readback.json') }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } }); assert.equal(result.code, 'AUTHORITATIVE_READBACK_FAILED');
});

test('readback missing a required assertion fails', async () => {
  const plan = keepOperations(makePlan(), 1); const handler = makeHandler(plan.operations[0], plan, [], { async readback() { return { ok: true, authoritative: true, requirements: ['category-id'], evidence_ref: runtimePath('40_evidence/readback.json') }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } }); assert.equal(result.code, 'AUTHORITATIVE_READBACK_FAILED'); assert.match(result.problems.join('\n'), /readback_requirements_must_exactly_match_plan/);
});

test('duplicate or blank readback assertions fail before evidence persistence can mask the error', async () => {
  const plan = keepOperations(makePlan(), 1); const handler = makeHandler(plan.operations[0], plan, [], { async readback() { return { ok: true, authoritative: true, requirements: ['category-id', 'slug', 'site-key', 'site-key'], evidence_ref: runtimePath('40_evidence/readback.json') }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } }); assert.equal(result.code, 'AUTHORITATIVE_READBACK_FAILED'); assert.match(result.problems.join('\n'), /readback_requirements_invalid/);
});

test('cross-client readback evidence is rejected', async () => {
  const plan = keepOperations(makePlan(), 1); const handler = makeHandler(plan.operations[0], plan, [], { async readback() { return { ok: true, authoritative: true, requirements: [...plan.operations[0].readback_requirements], evidence_ref: 'customer-runtime/10_clients/other/30_tasks/synthetic-task/40_evidence/readback.json' }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } }); assert.equal(result.code, 'AUTHORITATIVE_READBACK_FAILED');
});

test('cross-client reconciliation remains AMBIGUOUS_WRITE instead of being masked by evidence schema failure', async () => {
  const plan = keepOperations(makePlan(), 1); const handler = makeHandler(plan.operations[0], plan, [], { async execute() { return { request_started: true, status: 'unknown' }; }, async reconcile() { return { verdict: 'applied', authoritative: true, evidence_ref: 'customer-runtime/10_clients/other/30_tasks/synthetic-task/40_evidence/reconcile.json' }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } }); assert.equal(result.status, 'ambiguous'); assert.equal(result.code, 'AMBIGUOUS_WRITE');
});

test('evidence path must be declared and inside the same task root', async () => {
  const plan = keepOperations(makePlan(), 1); const { h, result } = await run(plan, { evidencePath: 'customer-runtime/10_clients/other/30_tasks/synthetic-task/40_evidence/live-run.json' });
  assert.equal(result.code, 'EVIDENCE_PATH_OUT_OF_SCOPE'); assertNoExecute(h.events);
});

test('initial evidence write must be confirmed before any mutation', async () => {
  const plan = keepOperations(makePlan(), 1); const { h, result } = await run(plan, { writeEvidence: async () => ({ ok: false }) });
  assert.equal(result.code, 'EVIDENCE_WRITE_FAILED'); assertNoExecute(h.events);
});

test('evidence write failure after first readback prevents the second request', async () => {
  const plan = keepOperations(makePlan(), 2); let writes = 0; const events = [];
  const h = harness(plan, { writeEvidence: async ({ path }) => { writes += 1; if (writes === 3) throw new Error('disk full'); return { ok: true, evidence_ref: path }; } });
  h.handlers['category:create'] = makeHandler(plan.operations[0], plan, events);
  h.handlers['article:update'] = makeHandler(plan.operations[1], plan, events);
  const result = await runAllinCmsContentPlan(h.params);
  assert.equal(result.code, 'EVIDENCE_WRITE_FAILED'); assert.deepEqual(events, ['execute:OP-001', 'readback:OP-001']);
});

test('update fingerprint mismatch blocks before execute', async () => {
  const plan = makeUpdatePlan(); let executeCount = 0; const handler = makeHandler(plan.operations[0], plan, [], { async readCurrent() { return { fingerprint: H('8') }; }, async execute() { executeCount += 1; return { request_started: true, status: 'completed' }; } });
  const { result } = await run(plan, { handlers: { 'article:update': handler } }); assert.equal(result.code, 'CURRENT_FINGERPRINT_BLOCK'); assert.equal(executeCount, 0);
});

test('handler cannot mutate the frozen plan snapshot', async () => {
  const plan = keepOperations(makePlan(), 1); const handler = makeHandler(plan.operations[0], plan, [], { async execute({ plan: snapshot }) { assert.throws(() => { snapshot.authorization_scope.target_key = 'other'; }, TypeError); return { request_started: true, status: 'completed' }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } }); assert.equal(result.ok, true); assert.equal(result.evidence.target.key, 'site-fixture');
});

test('caller mutation after controller entry cannot alter the cloned plan snapshot', async () => {
  const plan = keepOperations(makePlan(), 1); let release; const gate = new Promise((resolve) => { release = resolve; }); let entered;
  const enteredPromise = new Promise((resolve) => { entered = resolve; });
  const h = harness(plan, { preflight: async () => { entered(); await gate; return observed(); } });
  const pending = runAllinCmsContentPlan(h.params); await enteredPromise; plan.authorization_scope.target_key = 'other-site'; release();
  const result = await pending; assert.equal(result.ok, true); assert.equal(result.evidence.target.key, 'site-fixture');
});

test('dependency readback map is isolated from downstream handler mutation', async () => {
  const plan = keepOperations(makePlan(), 2); let observedId;
  const first = makeHandler(plan.operations[0], plan, [], { async readback() { return successfulReadback(plan.operations[0], plan, { evidence_ref: runtimePath('40_evidence/first.json'), entity: { id: 'original' } }); } });
  const second = makeHandler(plan.operations[1], plan, [], { async execute({ priorReadbacks }) { const prior = priorReadbacks.get('OP-001'); assert.throws(() => { prior.entity.id = 'mutated'; }, TypeError); observedId = prior.entity.id; return { request_started: true, status: 'completed' }; } });
  const { result } = await run(plan, { handlers: { 'category:create': first, 'article:update': second } }); assert.equal(result.ok, true); assert.equal(observedId, 'original');
});

test('credential-like errors are redacted from returned and persisted evidence', async () => {
  const syntheticSecrets = ['zxBearer', 'zxToken', 'zxCookie', 'zxDeployment', 'zxAction', 'zxPassword'].map((prefix) => `${prefix}${['Secret', '909'].join('')}`);
  const [bearer, token, cookie, deployment, action, password] = syntheticSecrets;
  const message = [`Authorization: Bearer ${bearer}`, `token=${token} cookie=${cookie} deployment_id=${deployment} action_id=${action} password=${password}`].join('\n');
  const plan = keepOperations(makePlan(), 1); const handler = makeHandler(plan.operations[0], plan, [], { async execute() { const error = new Error(message); error.requestStarted = false; throw error; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } }); const serialized = JSON.stringify(result);
  for (const secret of syntheticSecrets) assert.equal(serialized.includes(secret), false, secret);
  assert.match(serialized, /REDACTED/);
});

test('dynamic runtime identifiers returned by handlers are blocked and never persisted', async () => {
  const plan = keepOperations(makePlan(), 1); const handler = makeHandler(plan.operations[0], plan, [], { async execute() { return { request_started: true, status: 'completed', metadata: { action_id: 'dynamic-secret' } }; } });
  const { result } = await run(plan, { handlers: { 'category:create': handler } }); assert.equal(result.status, 'blocked'); assert.equal(result.code, 'HANDLER_OUTPUT_CONTRACT_VIOLATION_APPLIED'); assert.equal(result.evidence.operations[0].readback.passed, true); assert.equal(JSON.stringify(result.evidence).includes('dynamic-secret'), false);
});

test('blocked operation remains schema-valid and preserves the blocking code if terminal evidence persistence also fails', async () => {
  const plan = keepOperations(makePlan(), 1); let writes = 0; const h = harness(plan, { preflight: async () => observed({ site_key: 'wrong' }), writeEvidence: async ({ path }) => { writes += 1; if (writes > 1) throw new Error('disk full'); return { ok: true, evidence_ref: path }; } });
  const result = await runAllinCmsContentPlan(h.params); assert.equal(result.status, 'blocked'); assert.equal(result.code, 'EVIDENCE_WRITE_FAILED'); assert.equal(result.original_code, 'PREFLIGHT_BLOCK');
});

test('successful noop and explore use separate authoritative read-only profiles without weakening mutation verification', async () => {
  for (const intent of ['noop', 'explore']) {
    const plan = makeReadOnlyPlan(intent);
    let executeCount = 0;
    let reconcileCount = 0;
    const handler = makeHandler(plan.operations[0], plan, [], {
      async execute() { executeCount += 1; return { request_started: true, status: 'completed' }; },
      async reconcile() { reconcileCount += 1; return { verdict: 'applied', authoritative: true, evidence_ref: runtimePath('40_evidence/reconcile.json') }; },
    });
    const { result } = await run(plan, { handlers: { [`category:${intent}`]: handler } });
    assert.equal(result.ok, true, intent);
    assert.equal(result.code, 'ALLINCMS_CONTENT_RUN_COMPLETED', intent);
    assert.equal(executeCount, intent === 'noop' ? 0 : 1, intent);
    assert.equal(reconcileCount, 0, intent);
    const row = result.evidence.operations[0];
    assert.equal(row.status, 'readback_passed', intent);
    assert.equal(row.transport.request_started, intent === 'explore', intent);
    assert.equal(row.transport.status, intent === 'explore' ? 'completed' : 'not_started', intent);
    assert.equal(validateAllinCmsLiveRunEvidence(result.evidence).ok, true, intent);
  }
});

test('standalone evidence validation rejects noop transport claims and any read-only write reconciliation', async () => {
  for (const intent of ['noop', 'explore']) {
    const plan = makeReadOnlyPlan(intent);
    const { result } = await run(plan);
    assert.equal(result.ok, true, intent);
    const tampered = structuredClone(result.evidence);
    if (intent === 'noop') {
      tampered.operations[0].transport = { request_started: true, status: 'completed' };
      assert.match(validateAllinCmsLiveRunEvidence(tampered).problems.join('\n'), /noop evidence must not claim a remote request/);
    }
    const reconciled = structuredClone(result.evidence);
    reconciled.operations[0].reconciliation = { performed: true, verdict: 'applied', authoritative: true, evidence_ref: runtimePath('40_evidence/reconcile.json') };
    assert.match(validateAllinCmsLiveRunEvidence(reconciled).problems.join('\n'), /read-only evidence must not claim write reconciliation/);
  }
});

test('read-only operations fail closed when their plan requirements drift from the canonical intent profile', async () => {
  for (const intent of ['noop', 'explore']) {
    const plan = makeReadOnlyPlan(intent);
    plan.operations[0].readback_requirements = ['scope.exact_site_binding'];
    reseal(plan);
    const { h, result } = await run(plan);
    assert.equal(result.code, 'CAPABILITY_ROUTE_BLOCK', intent);
    assert.match(result.problems.join('\n'), /authoritative read-only profile/, intent);
    assert.equal(h.counts().preflight, 0, intent);
    assertNoExecute(h.events);
  }
});

test('noop readback failure and explore transport failure never enter write reconciliation', async () => {
  for (const intent of ['noop', 'explore']) {
    const plan = makeReadOnlyPlan(intent);
    let executeCount = 0;
    let reconcileCount = 0;
    const handler = makeHandler(plan.operations[0], plan, [], {
      async execute() { executeCount += 1; return { request_started: true, status: 'unknown' }; },
      async readback() {
        if (intent === 'noop') throw new Error('authoritative noop readback unavailable');
        return successfulReadback(plan.operations[0], plan);
      },
      async reconcile() { reconcileCount += 1; return { verdict: 'applied', authoritative: true, evidence_ref: runtimePath('40_evidence/reconcile.json') }; },
    });
    const { result } = await run(plan, { handlers: { [`category:${intent}`]: handler } });
    assert.equal(result.code, intent === 'noop' ? 'AUTHORITATIVE_READBACK_FAILED' : 'READ_OPERATION_FAILED', intent);
    assert.equal(result.status, 'failed', intent);
    assert.equal(executeCount, intent === 'noop' ? 0 : 1, intent);
    assert.equal(reconcileCount, 0, intent);
    assert.equal(result.evidence.operations[0].intent, intent);
    assert.equal(validateAllinCmsLiveRunEvidence(result.evidence).ok, true, intent);
  }
});


test('blocked capability routes cannot be revived by a self-reported live capability snapshot', async () => {
  for (const [entityType, intent] of [['article', 'create'], ['product', 'create'], ['media', 'update']]) {
    const plan = makeSingleRoutePlan({ entityType, intent });
    let executeCount = 0;
    const handler = makeHandler(plan.operations[0], plan, [], { async execute() { executeCount += 1; return { request_started: true, status: 'completed' }; } });
    const { result } = await run(plan, { handlers: { [`${entityType}:${intent}`]: handler } });
    assert.equal(result.code, 'CAPABILITY_ROUTE_BLOCK', `${entityType}:${intent}`);
    assert.equal(executeCount, 0, `${entityType}:${intent}`);
  }
});

test('approved plans cannot add self-defined verification requirements beyond the canonical route profile', async () => {
  const plan = keepOperations(makePlan(), 1);
  plan.operations[0].readback_requirements.push('backend.exact_persisted_fields');
  reseal(plan);
  const h = harness(plan);
  const result = await runAllinCmsContentPlan(h.params);
  assert.equal(result.ok, false);
  assert.equal(result.code, 'CAPABILITY_ROUTE_BLOCK');
  assert.match(result.problems.join('\n'), /must exactly match authoritative profile/);
  assert.equal(h.counts().preflight, 0);
  assertNoExecute(h.events);
});

test('readback strings without structured checks fail closed', async () => {
  const plan = keepOperations(makePlan(), 1);
  await expectReadbackBlocked(plan, { ok: true, authoritative: true, requirements: [...plan.operations[0].readback_requirements], evidence_ref: runtimePath('40_evidence/readback.json') }, { pattern: /structured_verification_checks_required/ });
});

test('structured backend, site, entity and subject bindings fail closed when tampered', async () => {
  for (const [label, mutate, pattern] of [
    ['backend authority', (readback) => { readback.checks[0].observations.backend_authoritative = false; }, /backend_readback_not_authoritative_exact/],
    ['site key', (readback) => { readback.checks[0].site_key = 'other-site'; }, /verification_site_mismatch/],
    ['site id', (readback) => { readback.checks[0].site_id = 'other-site-id'; }, /verification_site_id_mismatch/],
    ['entity ref', (readback) => { readback.checks[0].entity_ref = 'category:other'; }, /verification_entity_mismatch/],
    ['entity id drift', (readback) => { readback.checks[1].entity_id = 'other-id'; resealCheckArtifact(readback.checks[1]); }, /verification_entity_id_drift/],
    ['operation subject', (readback) => { readback.checks[0].subject_digest = H('8'); }, /verification_subject_digest_mismatch/],
  ]) {
    const plan = keepOperations(makePlan(), 1);
    const readback = mutateReadback(plan, plan.operations[0], mutate);
    await expectReadbackBlocked(plan, readback, { pattern });
  }
});

test('cross-client and digest-mismatched primary verification artifacts fail closed', async () => {
  {
    const plan = keepOperations(makePlan(), 1);
    const readback = mutateReadback(plan, plan.operations[0], (value) => { value.checks[0].artifact_ref = 'customer-runtime/10_clients/other/30_tasks/synthetic-task/40_evidence/check.json'; });
    await expectReadbackBlocked(plan, readback, { pattern: /another client|does not match expected task root|must remain inside/ });
  }
  {
    const plan = keepOperations(makePlan(), 1);
    const readback = successfulReadback(plan.operations[0], plan);
    await expectReadbackBlocked(plan, readback, { readEvidenceArtifact: async () => Buffer.from('{"forged":true}'), pattern: /verification_artifact_digest_mismatch/ });
  }
});

test('anonymous frontend HTTP 200 is insufficient without anonymous exact page identity', async () => {
  const plan = makePublishPlan();
  for (const mutate of [
    (readback) => { readback.checks.find((check) => check.check_id === 'article.anonymous_frontend_detail').observations.anonymous = false; },
    (readback) => { readback.checks.find((check) => check.check_id === 'article.anonymous_frontend_detail').observations.exact_match = false; },
  ]) {
    const readback = mutateReadback(plan, plan.operations[0], mutate);
    await expectReadbackBlocked(plan, readback, { pattern: /anonymous_frontend_not_proven/ });
  }
});

test('editor HTTP success is insufficient without editor health and exact persisted content', async () => {
  const plan = makeUpdatePlan();
  for (const mutate of [
    (check) => { check.observations.editor_healthy = false; },
    (check) => { check.observations.exact_match = false; },
  ]) {
    const readback = successfulReadback(plan.operations[0], plan);
    mutate(readback.checks.find((check) => check.check_id === 'article.editor_reopen_health'));
    await expectReadbackBlocked(plan, readback, { pattern: /editor_reopen_not_healthy/ });
  }
});

test('image MIME and HTTP 200 are insufficient without decode', async () => {
  const plan = makeMediaCreatePlan();
  const readback = successfulReadback(plan.operations[0], plan);
  readback.checks.find((check) => check.check_id === 'media.image_decode').observations.decoded = false;
  await expectReadbackBlocked(plan, readback, {
    preflight: async () => mediaPreflight(),
    pattern: /image_decode_not_proven/,
  });
});

test('current fingerprint evidence must match the approved expected-current fingerprint', async () => {
  const plan = makeUpdatePlan();
  const readback = successfulReadback(plan.operations[0], plan);
  readback.checks.find((check) => check.check_id === 'concurrency.expected_current_fingerprint').observations.current_fingerprint = H('8');
  await expectReadbackBlocked(plan, readback, { pattern: /expected_current_fingerprint_not_proven/ });
});

test('primary verification artifact must be JSON and its parsed envelope must match the structured check', async () => {
  {
    const plan = keepOperations(makePlan(), 1);
    const readback = successfulReadback(plan.operations[0], plan);
    readback.checks[0].artifact_media_type = 'image/png';
    await expectReadbackBlocked(plan, readback, { pattern: /verification_primary_artifact_must_be_json/ });
  }
  {
    const plan = keepOperations(makePlan(), 1);
    const readback = successfulReadback(plan.operations[0], plan);
    const target = readback.checks[0];
    const forgedArtifact = Buffer.from(JSON.stringify({ ...verificationArtifactEnvelope(target), observed_result: 'forged but digest-valid' }));
    target.artifact_digest = bytesDigest(forgedArtifact);
    await expectReadbackBlocked(plan, readback, {
      readEvidenceArtifact: async ({ check }) => check.check_id === target.check_id ? forgedArtifact : artifactBytesForCheck(check),
      pattern: /verification_artifact_envelope_mismatch/,
    });
  }
});

test('verification observations must be captured inside the exact operation window', async () => {
  for (const observedAt of ['2026-08-12T00:09:59Z', '2026-08-12T00:10:01Z']) {
    const plan = keepOperations(makePlan(), 1);
    const readback = successfulReadback(plan.operations[0], plan);
    readback.checks[0].observed_at = observedAt;
    await expectReadbackBlocked(plan, readback, { pattern: /verification_observed_at_outside_operation/ });
  }
});

test('media and article verification URL groups must bind to one exact HTTPS resource', async () => {
  {
    const plan = makeMediaCreatePlan();
    const readback = successfulReadback(plan.operations[0], plan);
    const target = readback.checks.find((check) => check.check_id === 'media.image_decode');
    target.observations.resource_url = 'https://cdn.example.invalid/other.png';
    resealCheckArtifact(target);
    await expectReadbackBlocked(plan, readback, { preflight: async () => mediaPreflight(), pattern: /verification_resource_url_drift:media.persisted_url/ });
  }
  {
    const plan = makePublishPlan();
    const readback = successfulReadback(plan.operations[0], plan);
    const target = readback.checks.find((check) => check.check_id === 'article.visible_content_and_media');
    target.observations.resource_url = 'https://site-fixture.web.allincms.com/posts/other';
    resealCheckArtifact(target);
    await expectReadbackBlocked(plan, readback, { pattern: /verification_resource_url_drift:article.public_url/ });
  }
});

test('exact-ID article operations reject evidence for any other backend entity ID', async () => {
  const plan = makeUpdatePlan();
  const readback = successfulReadback(plan.operations[0], plan);
  const target = readback.checks[0];
  target.entity_id = 'other-article-id';
  resealCheckArtifact(target);
  await expectReadbackBlocked(plan, readback, { pattern: /verification_entity_id_mismatch/ });
});

test('article frontend verification requires actual decode when required media is applicable', async () => {
  const plan = makePublishPlan();
  const readback = successfulReadback(plan.operations[0], plan);
  const target = readback.checks.find((check) => check.check_id === 'article.visible_content_and_media');
  target.observations.decoded = false;
  await expectReadbackBlocked(plan, readback, { pattern: /article_required_media_decode_not_proven/ });
});

test('artifact byte reader is a mandatory controller dependency', async () => {
  const plan = keepOperations(makePlan(), 1);
  const h = harness(plan);
  const result = await runAllinCmsContentPlan({ ...h.params, readEvidenceArtifact: undefined });
  assert.equal(result.ok, false);
  assert.equal(result.code, 'CONTROLLER_DEPENDENCY_MISSING');
  assert.match(result.problems.join('\n'), /readEvidenceArtifact/);
  assert.equal(h.counts().preflight, 0);
  assertNoExecute(h.events);
});

test('readback requirements and check IDs cannot add self-defined passing assertions', async () => {
  {
    const plan = keepOperations(makePlan(), 1);
    const readback = successfulReadback(plan.operations[0], plan);
    readback.requirements.push('backend.exact_persisted_fields');
    readback.checks.push(verificationCheck(plan.operations[0], 'backend.exact_persisted_fields', plan));
    await expectReadbackBlocked(plan, readback, { pattern: /readback_requirements_must_exactly_match_plan/ });
  }
  {
    const plan = keepOperations(makePlan(), 1);
    const readback = successfulReadback(plan.operations[0], plan);
    readback.checks.push(verificationCheck(plan.operations[0], 'backend.exact_persisted_fields', plan));
    await expectReadbackBlocked(plan, readback, { pattern: /verification_checks_must_exactly_match_plan/ });
  }
});

test('completed evidence validator rejects missing, out-of-scope and unbound checks', async () => {
  const { result } = await run();
  assert.equal(result.ok, true);
  for (const mutate of [
    (evidence) => { evidence.operations[0].readback.checks = []; },
    (evidence) => { evidence.operations[0].readback.checks[0].artifact_ref = 'customer-runtime/10_clients/other/30_tasks/synthetic-task/40_evidence/check.json'; },
    (evidence) => { evidence.operations[0].readback.checks[0].subject_digest = H('8'); },
    (evidence) => {
      const row = evidence.operations[0];
      row.readback.requirements.push('backend.exact_persisted_fields');
      row.readback.checks.push(verificationCheck(makePlan().operations[0], 'backend.exact_persisted_fields', makePlan()));
    },
    (evidence) => { evidence.operations[0].readback.checks[0].evidence_kind = 'editor_reopen'; },
  ]) {
    const evidence = structuredClone(result.evidence); mutate(evidence);
    assert.equal(validateAllinCmsLiveRunEvidence(evidence).ok, false);
  }
});

test('standalone evidence validator rejects resource URL drift but does not claim artifact-byte verification', async () => {
  const { result } = await run(makePublishPlan());
  assert.equal(result.ok, true);
  const evidence = structuredClone(result.evidence);
  evidence.operations[0].readback.checks.find((check) => check.check_id === 'article.visible_content_and_media').observations.resource_url = 'https://site-fixture.web.allincms.com/posts/other';
  const validation = validateAllinCmsLiveRunEvidence(evidence);
  assert.equal(validation.ok, false);
  assert.match(validation.problems.join('\n'), /verification resource URLs drift/);
});

test('completed status is emitted only after every authoritative readback passes', async () => {
  const plan = keepOperations(makePlan(), 2); const second = makeHandler(plan.operations[1], plan, [], { async readback() { return { ok: false, authoritative: true, requirements: [], evidence_ref: runtimePath('40_evidence/second.json') }; } });
  const { result } = await run(plan, { handlers: { 'article:update': second } }); assert.equal(result.ok, false); assert.equal(result.evidence.status, 'failed'); assert.notEqual(result.evidence.status, 'completed');
});
