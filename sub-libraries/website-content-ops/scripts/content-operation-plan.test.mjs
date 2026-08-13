import test from 'node:test';
import assert from 'node:assert/strict';
import { calculatePlanDigest, validateContentOperationPlan, validateContentOperationPlanSchema } from './validate-content-operation-plan.mjs';
import { expectedRuntimeScope } from './runtime-scope.mjs';

const H = (char) => `sha256:${char.repeat(64)}`;
const VALIDATION_NOW = new Date('2026-08-12T00:10:00Z');
const TASK_ROOT = 'customer-runtime/10_clients/synthetic-client/30_tasks/synthetic-task';
const runtimePath = (suffix) => `${TASK_ROOT}/${suffix}`;
const direct = () => ({ mode: 'direct', notes: '' });
const normalized = () => ({ mode: 'normalized', notes: 'Normalized source wording into the target field format.' });
const evidence = (locator, char = 'e', unitId = null) => [{ source_id: 'SRC-001', source_digest: H('b'), extraction_id: 'SX-SRC-001', unit_id: unitId ?? `UNIT-${char}`, locator, extraction_digest: H(char) }];

function seal(plan) {
  plan.plan_digest = calculatePlanDigest(plan);
  if (plan.authorization_scope.status === 'approved') plan.authorization_scope.plan_sha256 = plan.plan_digest;
  return plan;
}

function makePlan({ approved = false, publicationClearance = 'approved' } = {}) {
  return seal({
    schema_version: '1.1', plan_id: 'COP-synthetic-001', plan_digest: H('0'),
    client_id: 'synthetic-client', company_id: 'synthetic-company', task_id: 'synthetic-task', runtime_scope: expectedRuntimeScope({ client_id: 'synthetic-client', company_id: 'synthetic-company', task_id: 'synthetic-task' }), execution_mode: 'audit', plan_phase: 'site_operation',
    cms_adapter: { id: 'allincms', version: 'runtime-discovered', observed_at: '2026-08-12T00:00:00Z', deployment_fingerprint: H('a') },
    site_selector: { target_scope: 'site', site_key: 'site-fixture', site_id: 'site-id-fixture', account_user_id: 'user-fixture', selection_source: 'user-confirmed', bootstrap_readback_ref: null, bootstrap_plan_digest: null, cross_site_fallback: false },
    source_snapshot: { captured_at: '2026-08-12T00:00:00Z', sources: [
      { source_id: 'SRC-001', kind: 'brief', location: runtimePath('10_sources/brief.md'), digest: H('b'), authority: 'primary', owner: 'synthetic-owner', rights_status: 'owned', method_use_clearance: 'approved', publication_clearance: publicationClearance, source_date: '2026-08-01T00:00:00Z', review_after: null, source_scope: 'synthetic-client/synthetic-company/synthetic-task', extractions: [{ extraction_id: 'SX-SRC-001', artifact_ref: runtimePath('20_work/source-extraction.json'), source_digest: H('b'), captured_at: '2026-08-12T00:00:00Z', status: 'complete', units: [{ unit_id: 'UNIT-e', locator: 'brief.md#category-name', extraction_digest: H('e') }, { unit_id: 'UNIT-f', locator: 'brief.md#article-title', extraction_digest: H('f') }, { unit_id: 'UNIT-1', locator: 'brief.md#buyer-needs', extraction_digest: H('1') }] }] }
    ] },
    claim_ledger: [
      { claim_id: 'CLAIM-CATEGORY-NAME', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: evidence('brief.md#category-name', 'e'), value: 'Guides', notes: '' },
      { claim_id: 'CLAIM-ARTICLE-TITLE', status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: evidence('brief.md#article-title', 'f'), value: 'Buyer Guide', notes: '' },
      { claim_id: 'CLAIM-ARTICLE-SUMMARY', status: 'inferred', source_refs: ['SRC-001'], evidence_refs: evidence('brief.md#buyer-needs', '1'), value: 'A guide for qualified buyers.', notes: 'Editorial synthesis from the supplied brief.' },
      { claim_id: 'CLAIM-MISSING', status: 'missing', source_refs: [], evidence_refs: [], value: null, notes: 'Not present in supplied sources.' }
    ],
    capability_snapshot: { captured_at: '2026-08-12T00:01:00Z', expires_at: '2026-08-12T00:31:00Z', deployment_fingerprint: H('a'), capabilities: [
      { capability_id: 'CAP-category-create', entity_type: 'category', action: 'create', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] },
      { capability_id: 'CAP-article-create', entity_type: 'article', action: 'create', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] },
      { capability_id: 'CAP-article-publish', entity_type: 'article', action: 'publish', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/capability.json')] }
    ] },
    desired_state: [
      { entity_ref: 'category:guides', entity_type: 'category', intent: 'upsert', identity: { id: null, natural_key: { site_key: 'site-fixture', slug: 'guides' }, match_strategy: 'exact_natural_key' }, fields: {
        name: { value: 'Guides', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-CATEGORY-NAME'], derivation: direct(), clear_existing: false }
      } },
      { entity_ref: 'article:buyer-guide', entity_type: 'article', intent: 'upsert', identity: { id: null, natural_key: { site_key: 'site-fixture', slug: 'buyer-guide' }, match_strategy: 'exact_natural_key' }, fields: {
        title: { value: 'Buyer Guide', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ARTICLE-TITLE'], derivation: direct(), clear_existing: false },
        summary: { value: 'Buyer-ready guide.', fact_status: 'inferred', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ARTICLE-SUMMARY'], derivation: normalized(), clear_existing: false },
        unsupported_claim: { value: null, fact_status: 'missing', source_refs: [], claim_refs: ['CLAIM-MISSING'], derivation: direct(), clear_existing: false }
      } }
    ],
    current_state_fingerprint: H('c'),
    diff: [
      { operation_id: 'OP-001', entity_ref: 'category:guides', resolved_intent: 'create', changed_fields: ['name'] },
      { operation_id: 'OP-002', entity_ref: 'article:buyer-guide', resolved_intent: 'create', changed_fields: ['title','summary'] },
      { operation_id: 'OP-003', entity_ref: 'article:buyer-guide', resolved_intent: 'publish', changed_fields: [] }
    ],
    operations: [
      { operation_id: 'OP-001', entity_ref: 'category:guides', entity_type: 'category', intent: 'create', identity: { id: null, natural_key: { site_key: 'site-fixture', slug: 'guides' }, match_strategy: 'exact_natural_key' }, field_refs: ['name'], capability_ref: 'CAP-category-create', expected_current_fingerprint: null, dependencies: [], mutation: true, publication_effect: 'private_draft', readback_requirements: ['category-id', 'slug', 'site-key'] },
      { operation_id: 'OP-002', entity_ref: 'article:buyer-guide', entity_type: 'article', intent: 'create', identity: { id: null, natural_key: { site_key: 'site-fixture', slug: 'buyer-guide' }, match_strategy: 'exact_natural_key' }, field_refs: ['title','summary'], capability_ref: 'CAP-article-create', expected_current_fingerprint: null, dependencies: ['OP-001'], mutation: true, publication_effect: 'private_draft', readback_requirements: ['article-id', 'slug', 'taxonomy'] },
      { operation_id: 'OP-003', entity_ref: 'article:buyer-guide', entity_type: 'article', intent: 'publish', identity: { id: null, natural_key: { site_key: 'site-fixture', slug: 'buyer-guide' }, match_strategy: 'exact_natural_key' }, field_refs: [], capability_ref: 'CAP-article-publish', expected_current_fingerprint: null, dependencies: ['OP-002'], mutation: true, publication_effect: 'publish_transition', readback_requirements: ['published-status', 'public-url'] }
    ],
    authorization_scope: { status: approved ? 'approved' : 'pending', actor: approved ? 'Human Reviewer Fixture' : null, identity_status: 'not_verified', target_scope: 'site', target_key: 'site-fixture', operation_ids: ['OP-001','OP-002','OP-003'], approved_at: approved ? '2026-08-12T00:05:00Z' : null, expires_at: approved ? '2026-08-12T00:25:00Z' : null, plan_sha256: null },
    reconciliation_policy: { ambiguous_write: 'read-only-reconcile-before-any-retry', automatic_retry_after_request_started: false, identity_rule: 'exact-id-or-site-scoped-natural-key' },
    verification_plan: { backend_readback: true, editor_reopen: true, frontend: true, evidence_targets: [runtimePath('40_evidence/readback.json'), runtimePath('40_evidence/frontend.json')] },
    writeback_targets: [{ kind: 'task', path: runtimePath('TASK.json'), visibility: 'private-runtime' }]
  });
}

function makeBootstrapPlan({ approved = false } = {}) {
  const plan = makePlan({ approved });
  plan.plan_id = 'COP-synthetic-bootstrap-001';
  plan.plan_phase = 'site_bootstrap';
  plan.site_selector = {
    target_scope: 'account', site_key: null, site_id: null, account_user_id: 'user-fixture',
    selection_source: 'planned-create', bootstrap_readback_ref: null, bootstrap_plan_digest: null,
    cross_site_fallback: false,
  };
  plan.source_snapshot.sources[0].extractions[0].units.push({ unit_id: 'UNIT-2', locator: 'brief.md#site-description', extraction_digest: H('2') });
  plan.claim_ledger.push({
    claim_id: 'CLAIM-SITE-DESCRIPTION', status: 'confirmed', source_refs: ['SRC-001'],
    evidence_refs: evidence('brief.md#site-description', '2'), value: 'Source-backed site description.', notes: '',
  });
  plan.capability_snapshot.capabilities = [
    { capability_id: 'CAP-site-create', entity_type: 'site', action: 'create', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('40_evidence/site-create-capability.json')] },
  ];
  plan.desired_state = [{
    entity_ref: 'site:guides-site', entity_type: 'site', intent: 'create',
    identity: { id: null, natural_key: { site_key_candidate: 'guides-site' }, match_strategy: 'exact_natural_key' },
    fields: {
      name: { value: 'Guides', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-CATEGORY-NAME'], derivation: direct(), clear_existing: false },
      description: { value: 'Source-backed site description.', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-SITE-DESCRIPTION'], derivation: direct(), clear_existing: false },
    },
  }];
  plan.diff = [{ operation_id: 'OP-SITE-001', entity_ref: 'site:guides-site', resolved_intent: 'create', changed_fields: ['name','description'] }];
  plan.operations = [{
    operation_id: 'OP-SITE-001', entity_ref: 'site:guides-site', entity_type: 'site', intent: 'create',
    identity: { id: null, natural_key: { site_key_candidate: 'guides-site' }, match_strategy: 'exact_natural_key' },
    field_refs: ['name','description'], capability_ref: 'CAP-site-create', expected_current_fingerprint: null,
    dependencies: [], mutation: true, publication_effect: 'non_public_resource',
    readback_requirements: ['site-id','site-key','account-owner'],
  }];
  plan.authorization_scope = {
    status: approved ? 'approved' : 'pending', actor: approved ? 'Human Reviewer Fixture' : null,
    identity_status: 'not_verified', target_scope: 'account', target_key: 'user-fixture',
    operation_ids: ['OP-SITE-001'], approved_at: approved ? '2026-08-12T00:05:00Z' : null,
    expires_at: approved ? '2026-08-12T00:25:00Z' : null, plan_sha256: null,
  };
  plan.verification_plan = { backend_readback: true, editor_reopen: false, frontend: false, evidence_targets: [runtimePath('40_evidence/site-bootstrap-readback.json')] };
  return seal(plan);
}

function validate(plan, now = VALIDATION_NOW) { return validateContentOperationPlan(plan, { now }); }
function expectBlock(mutator, pattern, options = {}) {
  const plan = makePlan(options); mutator(plan); seal(plan);
  const result = validate(plan);
  assert.equal(result.ok, false, 'adversarial fixture unexpectedly passed');
  assert.match(result.problems.join('\n'), pattern);
}

test('operation-plan JSON Schema definition uses only supported constructs', () => assert.deepEqual(validateContentOperationPlanSchema(), []));
test('pending plan passes structurally but cannot execute', () => {
  const result = validate(makePlan()); assert.equal(result.ok, true, result.problems.join('\n')); assert.equal(result.executionReady, false);
});
test('digest-bound approved plan is execution ready', () => {
  const result = validate(makePlan({ approved: true })); assert.equal(result.ok, true, result.problems.join('\n')); assert.equal(result.executionReady, true);
});
test('site bootstrap Plan A passes without inventing a future site key', () => {
  const result = validate(makeBootstrapPlan()); assert.equal(result.ok, true, result.problems.join('\n')); assert.equal(result.executionReady, false);
});
test('approved site bootstrap binds authorization to the exact account target', () => {
  const result = validate(makeBootstrapPlan({ approved: true })); assert.equal(result.executionReady, true, result.problems.join('\n'));
});
test('site bootstrap rejects an invented future site key', () => {
  const plan = makeBootstrapPlan(); plan.site_selector.site_key = 'future-site-key'; plan.desired_state[0].identity.natural_key.site_key = 'future-site-key'; plan.operations[0].identity.natural_key.site_key = 'future-site-key'; seal(plan);
  const result = validate(plan); assert.equal(result.ok, false); assert.match(result.problems.join('\n'), /must keep future site_key.*null|must not contain a future site_key/);
});
test('site bootstrap cannot mix site creation with content population', () => {
  const plan = makeBootstrapPlan(); const articlePlan = makePlan();
  plan.desired_state.push(articlePlan.desired_state[1]);
  plan.diff.push({ operation_id: 'OP-ARTICLE-002', entity_ref: 'article:buyer-guide', resolved_intent: 'create', changed_fields: ['title','summary'] });
  plan.operations.push({ ...articlePlan.operations[1], operation_id: 'OP-ARTICLE-002', dependencies: ['OP-SITE-001'] });
  plan.authorization_scope.operation_ids.push('OP-ARTICLE-002'); seal(plan);
  const result = validate(plan); assert.equal(result.ok, false); assert.match(result.problems.join('\n'), /exactly one desired site create|exactly one site create operation/);
});
test('Plan B selected from bootstrap readback requires Plan A digest and private evidence', () => expectBlock((p) => {
  p.site_selector.selection_source = 'bootstrap-readback';
}, /requires private readback evidence|requires the Plan A bootstrap digest/));
test('Plan B may bind the exact site returned by Plan A readback', () => {
  const plan = makePlan(); plan.site_selector.selection_source = 'bootstrap-readback';
  plan.site_selector.bootstrap_readback_ref = runtimePath('40_evidence/site-bootstrap-readback.json');
  plan.site_selector.bootstrap_plan_digest = H('9'); seal(plan);
  const result = validate(plan); assert.equal(result.ok, true, result.problems.join('\n'));
});

test('confirmed facts require an existing source', () => expectBlock((p) => { p.desired_state[1].fields.title.source_refs = ['SRC-missing']; }, /missing source/));
test('confirmed claims require precise source evidence locators', () => expectBlock((p) => { p.claim_ledger[1].evidence_refs = []; }, /evidence_refs must not be empty/));
test('claim evidence source must be declared by the claim', () => expectBlock((p) => { p.claim_ledger[1].evidence_refs[0].source_id = 'SRC-missing'; }, /references a missing source|must also appear/));
test('mutation fields require claim refs', () => expectBlock((p) => { p.desired_state[1].fields.title.claim_refs = []; }, /claim_refs must not be empty|has no claim evidence/));
test('claim refs must resolve', () => expectBlock((p) => { p.desired_state[1].fields.title.claim_refs = ['CLAIM-MISSING-ID']; }, /references missing claim/));
test('confirmed fields cannot rely on inferred claims', () => expectBlock((p) => { p.desired_state[1].fields.title.claim_refs = ['CLAIM-ARTICLE-SUMMARY']; }, /confirmed fact cannot rely on claim/));
test('claim and field source refs must overlap', () => expectBlock((p) => {
  p.source_snapshot.sources.push({ source_id: 'SRC-002', kind: 'brief', location: runtimePath('10_sources/other.md'), digest: H('d'), authority: 'primary', publication_clearance: 'approved' });
  p.desired_state[1].fields.title.source_refs = ['SRC-002'];
}, /must share at least one source_ref/));
test('direct derivation must preserve the referenced claim value', () => expectBlock((p) => { p.desired_state[1].fields.title.value = 'Invented Title'; }, /direct value must equal/));
test('normalized and composed derivation require notes', () => expectBlock((p) => { p.desired_state[1].fields.summary.derivation.notes = ''; }, /derivation.notes is required/));
test('blocked fact states cannot enter mutation', () => expectBlock((p) => { p.operations[1].field_refs.push('unsupported_claim'); p.diff[1].changed_fields.push('unsupported_claim'); }, /includes blocked fact|uses blocked claim/));
test('unconsumed blocked claims may remain as an explicit gap ledger', () => {
  const result = validate(makePlan()); assert.equal(result.ok, true, result.problems.join('\n'));
});
test('publish blocks pending source clearance', () => expectBlock(() => {}, /public mutation is blocked.*publication_clearance=pending/, { publicationClearance: 'pending' }));
test('private draft may use pending-clearance sources', () => {
  const plan = makePlan({ publicationClearance: 'pending' });
  plan.operations.pop(); plan.diff.pop(); plan.authorization_scope.operation_ids.pop(); seal(plan);
  const result = validate(plan); assert.equal(result.ok, true, result.problems.join('\n'));
});
test('public-immediate create also requires source clearance', () => expectBlock((p) => {
  p.operations[1].publication_effect = 'public_immediate'; p.operations.pop(); p.diff.pop(); p.authorization_scope.operation_ids.pop();
}, /public mutation is blocked.*publication_clearance=pending/, { publicationClearance: 'pending' }));
test('update requires expected-current fingerprint', () => expectBlock((p) => { p.operations[1].intent = 'update'; p.diff[1].resolved_intent = 'update'; }, /expected_current_fingerprint is required/));
test('operation identity must match desired-state identity', () => expectBlock((p) => { p.operations[1].identity.natural_key.slug = 'different-slug'; }, /identity must exactly match/));
test('name-only natural key cannot identify an update', () => expectBlock((p) => { p.operations[1].identity = { id: null, natural_key: { site_key: 'site-fixture', title: 'Buyer Guide' }, match_strategy: 'exact_natural_key' }; }, /name\/title-only matching is forbidden/));
test('unresolved upsert cannot be executed', () => expectBlock((p) => { p.operations[1].intent = 'upsert'; p.diff[1].resolved_intent = 'create'; }, /must be resolved before execution|not in the allowed enum/));
test('strict serial chain is mandatory', () => expectBlock((p) => { p.operations[2].dependencies = []; }, /strict serial chain/));
test('remote mutation requires current-deployment live verification', () => expectBlock((p) => { p.capability_snapshot.capabilities[1].maturity = 'local_tested'; }, /remote mutation requires live_verified_current_deployment/));
test('exploration-only product mutation is blocked', () => expectBlock((p) => {
  p.capability_snapshot.capabilities[1] = { capability_id: 'CAP-product-create', entity_type: 'product', action: 'create', maturity: 'exploration_only', evidence_refs: [runtimePath('40_evidence/exploration.json')] };
  p.desired_state[1].entity_type = 'product'; p.operations[1].entity_type = 'product'; p.operations[1].capability_ref = 'CAP-product-create';
}, /remote mutation requires live_verified_current_deployment/));
test('capability evidence is mandatory', () => expectBlock((p) => { p.capability_snapshot.capabilities[1].evidence_refs = []; }, /evidence_refs must not be empty/));
test('expired capability snapshot blocks execution', () => expectBlock((p) => { p.capability_snapshot.expires_at = '2026-08-12T00:09:59Z'; }, /capability snapshot is expired/));
test('dynamic Action IDs and credentials cannot be persisted', () => expectBlock((p) => { p.cms_adapter.action_id = 'abc'; p.source_snapshot.sources[0].location = 'Cookie: secret'; }, /is forbidden|contains a cookie header/));
test('schema rejects undeclared properties', () => expectBlock((p) => { p.site_selector.unknown = true; }, /schema: .*unknown is not allowed/));
test('operations and diff rows must be one-to-one', () => expectBlock((p) => { p.diff.pop(); }, /same number of rows|no matching diff row/));
test('mutations require explicit readback requirements', () => expectBlock((p) => { p.operations[1].readback_requirements = []; }, /readback_requirements must not be empty/));
test('authorization must bind exact ordered operations', () => expectBlock((p) => { p.authorization_scope.operation_ids = ['OP-001']; }, /must exactly match ordered operations/));
test('authorization longer than 30 minutes is blocked', () => {
  const p = makePlan({ approved: true }); p.authorization_scope.expires_at = '2026-08-12T00:36:00Z'; seal(p);
  const result = validate(p); assert.equal(result.ok, false); assert.match(result.problems.join('\n'), /no more than 30 minutes/);
});
test('expired authorization is blocked at validation time', () => {
  const p = makePlan({ approved: true }); const result = validate(p, new Date('2026-08-12T00:25:00Z'));
  assert.equal(result.ok, false); assert.match(result.problems.join('\n'), /authorization is expired/);
});
test('digest drift invalidates approval', () => {
  const p = makePlan({ approved: true }); p.desired_state[1].fields.title.value = 'Changed after approval';
  const result = validate(p); assert.equal(result.ok, false); assert.match(result.problems.join('\n'), /plan_digest mismatch|plan_sha256/);
});

test('claim evidence must bind an exact extraction unit', () => expectBlock((p) => { p.claim_ledger[1].evidence_refs[0].unit_id = 'UNIT-missing'; }, /unit_id must reference/));
test('claim evidence digest must match the extraction unit', () => expectBlock((p) => { p.claim_ledger[1].evidence_refs[0].extraction_digest = H('9'); }, /extraction_digest must equal/));
test('source digest drift breaks extraction binding', () => expectBlock((p) => { p.source_snapshot.sources[0].extractions[0].source_digest = H('9'); }, /source_digest must equal source.digest/));
test('pending source method-use clearance blocks planning', () => expectBlock((p) => { p.source_snapshot.sources[0].method_use_clearance = 'pending'; }, /method_use_clearance=pending/));
test('review-due source blocks planning', () => expectBlock((p) => { p.source_snapshot.sources[0].review_after = '2026-08-12T00:09:59Z'; }, /review_after is due or expired/));

test('runtime scope explicitly binds the canonical client and task roots', () => {
  const result = validate(makePlan());
  assert.equal(result.ok, true, result.problems.join('\n'));
  assert.equal(makePlan().runtime_scope.task_root, TASK_ROOT);
});
test('source scope cannot point to another company or task', () => expectBlock((p) => {
  p.source_snapshot.sources[0].source_scope = 'synthetic-client/other-company/other-task';
}, /source_scope must exactly match/));
test('source location cannot point to another client task', () => expectBlock((p) => {
  p.source_snapshot.sources[0].location = 'customer-runtime/10_clients/other-client/30_tasks/other-task/brief.md';
}, /must remain inside/));
test('extraction artifact cannot point to another task', () => expectBlock((p) => {
  p.source_snapshot.sources[0].extractions[0].artifact_ref = 'customer-runtime/10_clients/synthetic-client/30_tasks/other-task/source-extraction.json';
}, /artifact_ref must remain inside/));
test('capability evidence cannot point to another client', () => expectBlock((p) => {
  p.capability_snapshot.capabilities[0].evidence_refs[0] = 'customer-runtime/10_clients/other-client/30_tasks/synthetic-task/capability.json';
}, /evidence_refs\[0\] must remain inside/));
test('verification evidence cannot point to another task', () => expectBlock((p) => {
  p.verification_plan.evidence_targets[0] = 'customer-runtime/10_clients/synthetic-client/30_tasks/other-task/readback.json';
}, /evidence_targets\[0\] must remain inside/));
test('writeback cannot target tracked mother-library content', () => expectBlock((p) => {
  p.writeback_targets[0].path = 'wiki/40_business/TASK.json';
}, /writeback_targets\[0\]\.path must remain inside/));
test('parent path traversal is blocked', () => expectBlock((p) => {
  p.writeback_targets[0].path = `${TASK_ROOT}/40_evidence/../TASK.json`;
}, /parent path segments|normalized/));
test('absolute and URL evidence references are blocked', () => {
  for (const bad of ['/tmp/readback.json', 'https://example.invalid/readback.json']) {
    const plan = makePlan(); plan.verification_plan.evidence_targets[0] = bad; seal(plan);
    const result = validate(plan);
    assert.equal(result.ok, false);
    assert.match(result.problems.join('\n'), /absolute path or URL|must remain inside/);
  }
});
test('runtime scope digest cannot be copied from another company', () => expectBlock((p) => {
  p.company_id = 'other-company';
}, /runtime_scope\.scope_digest must equal|source_scope must exactly match/));
test('bootstrap readback evidence passes only in the same task scope', () => {
  const plan = makePlan();
  plan.site_selector.selection_source = 'bootstrap-readback';
  plan.site_selector.bootstrap_readback_ref = runtimePath('40_evidence/site-bootstrap-readback.json');
  plan.site_selector.bootstrap_plan_digest = H('9');
  seal(plan);
  const result = validate(plan);
  assert.equal(result.ok, true, result.problems.join('\n'));
});
test('bootstrap readback evidence is blocked across tasks', () => expectBlock((p) => {
  p.site_selector.selection_source = 'bootstrap-readback';
  p.site_selector.bootstrap_readback_ref = 'customer-runtime/10_clients/synthetic-client/30_tasks/other-task/site-bootstrap-readback.json';
  p.site_selector.bootstrap_plan_digest = H('9');
}, /bootstrap_readback_ref must remain inside/));
