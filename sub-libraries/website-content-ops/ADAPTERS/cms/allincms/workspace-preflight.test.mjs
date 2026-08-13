import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ALLINCMS_SIGN_IN_URL,
  buildAllinCmsCreateSiteActionRequest,
  buildAllinCmsLoginHandoff,
  buildAllinCmsSitesRscRequest,
  discoverAllinCmsCreateSiteClientContract,
  inspectAllinCmsWorkspaceSession,
  listAllinCmsSites,
  parseAllinCmsWorkspaceRsc,
  runAllinCmsWorkspacePreflight,
  selectExactAllinCmsSite,
  validateAllinCmsCreateSiteInput,
} from './workspace-preflight.mjs';

const user = {
  id: 'user-synthetic-001',
  name: 'Synthetic Operator',
  email: 'operator@example.invalid',
  role: 'site-admin',
  tenant: 'tenant-synthetic-001',
};

function site(index) {
  return {
    id: `site-synthetic-${index}`,
    name: `Synthetic Site ${index}`,
    description: `Synthetic description ${index}`,
    slug: `synthetic-${index}`,
    domains: [],
    displayDomain: `synthetic-${index}.example.invalid`,
    active: true,
    themeCount: index,
    createdAt: '2026-08-11T00:00:00.000Z',
  };
}

function rsc({ sites = [], page = 1, totalPages = 1, totalDocs = sites.length, canCreate = true, currentUser = user } = {}) {
  return [
    '1:["$","layout",null,{"children":"$L2"}]',
    `2:${JSON.stringify({ user: currentUser })}`,
    `3:${JSON.stringify({ data: sites, pagination: { page, limit: 2, totalDocs, totalPages, hasNextPage: page < totalPages, hasPrevPage: page > 1 }, canCreate })}`,
  ].join('\n');
}

function response(text, overrides = {}) {
  return {
    status: 200,
    url: 'https://workspace.laicms.com/sites?_rsc=test',
    headers: { 'content-type': 'text/x-component' },
    text,
    ...overrides,
  };
}

test('parses user.id, tenant and site-list fields from synthetic RSC', () => {
  const parsed = parseAllinCmsWorkspaceRsc(rsc({ sites: [site(1)] }));
  assert.equal(parsed.status, 'authenticated');
  assert.equal(parsed.userId, user.id);
  assert.equal(parsed.tenantId, user.tenant);
  assert.equal(parsed.sites[0].displayDomain, 'synthetic-1.example.invalid');
  assert.equal(parsed.canCreate, true);
});

test('fails closed when the RSC user contract is missing', () => {
  const parsed = parseAllinCmsWorkspaceRsc(`3:${JSON.stringify({ data: [], pagination: { page: 1, limit: 12, totalDocs: 0, totalPages: 1 }, canCreate: true })}`);
  assert.equal(parsed.status, 'contract_drift');
  assert.deepEqual(parsed.missing, ['user']);
});

test('does not accept HTTP 200 login HTML as authentication', () => {
  const inspected = inspectAllinCmsWorkspaceSession(response('<form action="/sign-in"><input type="password"></form>', {
    headers: { 'content-type': 'text/html' },
  }));
  assert.equal(inspected.status, 'login_required');
});

test('detects a final /sign-in URL even when the status is 200', () => {
  const inspected = inspectAllinCmsWorkspaceSession(response('redirected', {
    url: 'https://workspace.laicms.com/sign-in',
  }));
  assert.equal(inspected.status, 'login_required');
});

test('detects 401 and 403 as login required', () => {
  assert.equal(inspectAllinCmsWorkspaceSession(response('', { status: 401 })).status, 'login_required');
  assert.equal(inspectAllinCmsWorkspaceSession(response('', { status: 403 })).status, 'login_required');
});

test('builds a read-only credentialed sites RSC request', () => {
  const request = buildAllinCmsSitesRscRequest({ page: 2, search: 'RF Test' });
  assert.equal(request.method, 'GET');
  assert.equal(request.mutation, false);
  assert.equal(request.credentials, 'include');
  assert.match(request.url, /page=2/);
  assert.match(request.url, /search=RF\+Test/);
  assert.equal(request.headers.Accept, 'text/x-component');
  assert.equal(request.browserTransport, 'existing_same_origin_session');
  assert.equal(request.requiresVisibleNavigation, false);
  assert.equal(request.foreground, false);
});

test('lists every page and verifies totalDocs', async () => {
  const seen = [];
  const result = await listAllinCmsSites({
    fetchPage: async (request) => {
      const page = new URL(request.url).searchParams.get('page') || '1';
      seen.push(Number(page));
      return Number(page) === 1
        ? response(rsc({ sites: [site(1), site(2)], page: 1, totalPages: 2, totalDocs: 3 }))
        : response(rsc({ sites: [site(3)], page: 2, totalPages: 2, totalDocs: 3 }));
    },
  });
  assert.deepEqual(seen, [1, 2]);
  assert.equal(result.status, 'multiple_sites');
  assert.equal(result.sites.length, 3);
  assert.equal(result.complete, true);
});

test('returns pagination_incomplete when maxPages blocks a declared page', async () => {
  const result = await listAllinCmsSites({
    maxPages: 1,
    fetchPage: async () => response(rsc({ sites: [site(1)], page: 1, totalPages: 2, totalDocs: 2 })),
  });
  assert.equal(result.status, 'pagination_incomplete');
  assert.equal(result.fetchedPages, 1);
});

test('returns pagination_incomplete when unique site count differs from totalDocs', async () => {
  const result = await listAllinCmsSites({
    fetchPage: async () => response(rsc({ sites: [site(1)], totalDocs: 2 })),
  });
  assert.equal(result.status, 'pagination_incomplete');
});

test('classifies zero, single and multiple site lists', () => {
  assert.equal(selectExactAllinCmsSite([]).status, 'zero_sites');
  assert.equal(selectExactAllinCmsSite([site(1)]).status, 'single_site');
  assert.equal(selectExactAllinCmsSite([site(1), site(2)]).status, 'multiple_sites');
});

test('selects only exact site id, slug or displayDomain', () => {
  const sites = [site(1), site(2)];
  assert.equal(selectExactAllinCmsSite(sites, 'synthetic-2').site.id, 'site-synthetic-2');
  assert.equal(selectExactAllinCmsSite(sites, 'synthetic-1.example.invalid').status, 'target_selected');
  assert.equal(selectExactAllinCmsSite(sites, 'synthetic').status, 'target_not_visible');
});

test('builds the user-facing login handoff without claiming a browser opened', () => {
  const handoff = buildAllinCmsLoginHandoff();
  assert.equal(handoff.openUrl, ALLINCMS_SIGN_IN_URL);
  assert.equal(handoff.browserOpened, false);
  assert.equal(handoff.recheckRequired, true);
  assert.match(handoff.userMessage, /重新通过接口检查/);
});


test('does not open or foreground browser UI when API preflight is authenticated', async () => {
  const opened = [];
  const result = await runAllinCmsWorkspacePreflight({
    fetchPage: async () => response(rsc({ sites: [site(1)] })),
    openLoginPage: async (...args) => opened.push(args),
  });
  assert.equal(result.status, 'single_site');
  assert.deepEqual(opened, []);
});

test('does not open login UI for non-auth errors or contract drift', async () => {
  for (const apiResponse of [
    response('server error', { status: 500 }),
    response('not the workspace contract'),
  ]) {
    const opened = [];
    const result = await runAllinCmsWorkspacePreflight({
      fetchPage: async () => apiResponse,
      openLoginPage: async (...args) => opened.push(args),
    });
    assert.notEqual(result.status, 'login_required');
    assert.deepEqual(opened, []);
  }
});

test('does not open login UI when site pagination is incomplete', async () => {
  const opened = [];
  const result = await runAllinCmsWorkspacePreflight({
    maxPages: 1,
    fetchPage: async () => response(rsc({ sites: [site(1)], page: 1, totalPages: 2, totalDocs: 2 })),
    openLoginPage: async (...args) => opened.push(args),
  });
  assert.equal(result.status, 'pagination_incomplete');
  assert.deepEqual(opened, []);
});

test('opens the in-app login handoff through the injected host callback', async () => {
  const opened = [];
  const result = await runAllinCmsWorkspacePreflight({
    fetchPage: async () => response('', { status: 401 }),
    openLoginPage: async (...args) => opened.push(args),
  });
  assert.equal(result.status, 'login_required');
  assert.equal(result.handoff.browserOpened, true);
  assert.equal(opened[0][0], ALLINCMS_SIGN_IN_URL);
  assert.deepEqual(opened[0][1], { foreground: true, keepVisible: true });
});

test('requires the host browser action when no login opener is available', async () => {
  const result = await runAllinCmsWorkspacePreflight({
    fetchPage: async () => response('<form action="/sign-in"><input type="password"></form>', { headers: { 'content-type': 'text/html' } }),
  });
  assert.equal(result.hostActionRequired, 'open_login_in_in_app_browser');
  assert.equal(result.handoff.browserOpened, false);
});

test('discovers the current createSiteAction and field constraints from client code', () => {
  const syntheticActionId = 'a'.repeat(42);
  const script = `let action=(0,x.createServerReference)("${syntheticActionId}",x.callServer,void 0,x.findSourceMapURL,"createSiteAction"),schema=z.object({name:z.string().min(2,"min").max(50,"max"),description:z.string().max(200,"max").optional()});`;
  const contract = discoverAllinCmsCreateSiteClientContract(script);
  assert.equal(contract.status, 'observed');
  assert.equal(contract.actionId, syntheticActionId);
  assert.equal(contract.fields.name.minLength, 2);
  assert.equal(contract.fields.description.required, false);
});

test('fails closed when create-site action discovery is incomplete', () => {
  const contract = discoverAllinCmsCreateSiteClientContract('const unrelated = true;');
  assert.equal(contract.status, 'contract_drift');
  assert.deepEqual(contract.missing, ['action_reference', 'name_rules', 'description_rules']);
});

test('validates only name and optional description create-site fields', () => {
  assert.deepEqual(validateAllinCmsCreateSiteInput({ name: 'AB' }), { name: 'AB' });
  assert.throws(() => validateAllinCmsCreateSiteInput({ name: 'A' }), /between 2 and 50/);
  assert.throws(() => validateAllinCmsCreateSiteInput({ name: 'AB', slug: 'not-client-owned' }), /Unsupported/);
  assert.throws(() => validateAllinCmsCreateSiteInput({ name: 'AB', description: 'x'.repeat(201) }), /up to 200/);
});

test('builds the observed Next.js create-site Server Action request without user or tenant fields', () => {
  const request = buildAllinCmsCreateSiteActionRequest({
    actionId: 'b'.repeat(42),
    routerStateTree: '["",{"children":["sites",{}]}]',
    deploymentId: 'synthetic-deployment',
    input: { name: 'Synthetic B2B Site', description: 'Synthetic only.' },
  });
  assert.equal(request.method, 'POST');
  assert.equal(request.mutation, true);
  assert.equal(request.headers['Next-Action'], 'b'.repeat(42));
  assert.deepEqual(JSON.parse(request.body), [{ name: 'Synthetic B2B Site', description: 'Synthetic only.' }]);
  assert.equal(JSON.parse(request.body)[0].userId, undefined);
  assert.equal(JSON.parse(request.body)[0].tenant, undefined);
});
