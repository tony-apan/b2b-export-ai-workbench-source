import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSiteCreatePayload, buildSiteCreateRequest, createSite, _internal } from './site-operations.mjs';
import { createAllinCmsMutationAuthorizationContext } from './mutation-authorization.mjs';

test('buildSiteCreatePayload validates name and optional description', () => {
  assert.deepEqual(buildSiteCreatePayload({ name: 'FluxPedal Motors', description: 'Cargo e-bike motors' }), {
    name: 'FluxPedal Motors',
    description: 'Cargo e-bike motors',
  });
  assert.throws(() => buildSiteCreatePayload({ name: 'A' }), /name must be a string between 2 and 50/);
});

test('buildSiteCreateRequest produces a POST /sites request with action name', () => {
  const req = buildSiteCreateRequest({
    actionId: 'a'.repeat(42),
    routerStateTree: '[]',
    deploymentId: 'd'.repeat(40),
    input: { name: 'Example Site' },
  });
  assert.equal(req.method, 'POST');
  assert.equal(req.url, 'https://workspace.laicms.com/sites');
  assert.equal(req.actionName, 'createSiteAction');
});

test('createSite sends through the action client and returns readback when provided', async () => {
  const sent = [];
  const request = async (details) => {
    sent.push(details);
    return { status: 200, ok: true, contentType: 'text/x-component', headers: { 'content-type': 'text/x-component' } };
  };
  const runtime = {
    actions: {
      siteCreate: {
        actionId: 'a'.repeat(42),
        routerTree: '[]',
        deploymentId: 'd'.repeat(40),
      },
    },
    deploymentId: 'd'.repeat(40),
    routerTree: '[]',
  };
  const authorizationContext = createAllinCmsMutationAuthorizationContext({
    siteKey: 'workspace',
    operation: 'allincms.site.create',
    target: { name: 'FluxPedal Motors' },
    approvalActor: 'Test Reviewer',
    approvedAt: new Date().toISOString(),
  });
  const result = await createSite({
    runtime,
    request,
    authorizationContext,
    input: { name: 'FluxPedal Motors' },
    readback: async () => ({ id: 'site-1', slug: 'fluxpedal' }),
  });
  assert.equal(result.status, 'site_mutation_succeeded');
  assert.equal(sent.length, 1);
  assert.equal(sent[0].actionName, 'siteCreate');
  assert.equal(sent[0].route, '/sites');
  assert.deepEqual(result.readback, { id: 'site-1', slug: 'fluxpedal' });
});

test('createSite validates before/after unique site ID delta when callbacks are provided', async () => {
  const runtime = {
    actions: { siteCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } },
    deploymentId: 'd'.repeat(40),
    routerTree: '[]',
  };
  const request = async () => ({ status: 200, ok: true, contentType: 'text/x-component', headers: { 'content-type': 'text/x-component' } });
  const authorizationContext = createAllinCmsMutationAuthorizationContext({
    siteKey: 'workspace',
    operation: 'allincms.site.create',
    target: { name: 'FluxPedal Motors' },
    approvalActor: 'Test Reviewer',
  });
  const result = await createSite({
    runtime,
    request,
    authorizationContext,
    input: { name: 'FluxPedal Motors' },
    beforeSiteIds: ['old-1'],
    readback: async () => ({ sites: [{ id: 'old-1' }, { id: 'new-1', slug: 'fluxpedal', domain: 'fluxpedal.web.example' }] }),
    getAfterSiteIds: (actual) => actual.sites.map((site) => site.id),
    getCreatedSiteId: (actual) => actual.sites.find((site) => site.id === 'new-1').id,
    getCreatedSiteKey: (actual) => actual.sites.find((site) => site.id === 'new-1').slug,
    getCreatedSiteDomain: (actual) => actual.sites.find((site) => site.id === 'new-1').domain,
  });
  assert.equal(result.status, 'site_mutation_succeeded');
  assert.equal(result.siteDeltaEvidence.verdict, 'pass');
});

test('internal constants are stable', () => {
  assert.equal(_internal.SITE_BOOTSTRAP_SITE_KEY, 'workspace');
});
