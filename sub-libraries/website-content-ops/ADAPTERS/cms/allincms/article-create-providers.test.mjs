import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, writeFileSync, readFileSync, rmSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import {
  createArticleCreateProviders,
  ALLINCMS_ARTICLE_PROVIDERS_DEFAULT_ORIGIN,
} from './article-create-providers.mjs';
import { createAllinCmsPlanHandlerSet } from './content-plan-host-driver.mjs';
import { runAllinCmsHostPlanTemplate } from './host-run-template.mjs';
import { calculatePlanDigest } from '../../../scripts/validate-content-operation-plan.mjs';
import { expectedRuntimeScope } from '../../../scripts/runtime-scope.mjs';

// ---------------------------------------------------------------------------
// Synthetic RSC flight fixtures.
//
// Modeled on the real workspace flight shape that allincms_api.py read_lists
// / read_post parse (Next.js App Router segmented stream): ordinary
// `<key>:<json>` rows, `o<len>,<id>:` length-prefixed reference rows,
// special-value rows (I[...] / D{...} / T...) that carry no business JSON,
// and one props row whose third element owns the business dict.
// ---------------------------------------------------------------------------

const SPECIAL_ROWS = [
  '0:["$","html",null,{"lang":"en"}]',
  'o1000,20:I["696","default",{"ids":[]}]',
  '1:D{"nextDist":1}',
  '5:T7b7b5f,{"skipped":"text-row"}',
];

function flightList({ rows, pagination, categoryOptions = [], tagOptions = [] }) {
  const props = { data: rows, pagination, categoryOptions, tagOptions };
  return [
    ...SPECIAL_ROWS,
    // the real shape: props sit inside the third element of a component row
    `22:["$","$L2b",null,${JSON.stringify(props)}]`,
    '99:{"unrelated":"record row that parses but owns no needles"}',
  ].join('\n');
}

function flightListMinimalShape({ rows, pagination }) {
  // the Python fallback shape: no categoryOptions/tagOptions keys at all
  return [...SPECIAL_ROWS, `30:["$","$L2c",null,${JSON.stringify({ data: rows, pagination })}]`].join('\n');
}

function flightEditor(defaultValues, postId) {
  return [...SPECIAL_ROWS, `31:["$","$L3c",null,${JSON.stringify({ defaultValues, postId })}]`].join('\n');
}

const SIGN_IN_FLIGHT = [...SPECIAL_ROWS, '40:["$","$L4d",null,{"signInRequired":true}]'].join('\n');

function htmlEditorPage(postId) {
  const flight = JSON.stringify({ postId, editor: 'post-update' });
  return `<!DOCTYPE html><html><body><script>self.__next_f.push([1,"${flight.replace(/"/g, '\\"')}"])</script></body></html>`;
}

// ---------------------------------------------------------------------------
// Fake HTTP harness (fetch-compatible injection; no real network is touched).
// ---------------------------------------------------------------------------

function httpResponse(status, body, headers = {}) {
  return {
    status,
    headers: { get: (name) => Object.hasOwn(headers, name.toLowerCase()) ? headers[name.toLowerCase()] : null },
    text: async () => body,
  };
}

function createFetchRouter(respond) {
  const calls = [];
  const fetchFn = async (url, opts) => {
    const record = { url: String(url), opts };
    calls.push(record);
    return respond(new URL(String(url)), opts, record);
  };
  return { fetchFn, calls };
}

const ORIGIN = 'https://workspace.example.test';
const TOKEN = 'synthetic.payload-token.value';

function makeProviders(fetchFn, overrides = {}) {
  return createArticleCreateProviders({
    siteKey: 'synthetic-site',
    siteId: 'sid-1',
    authCookie: TOKEN,
    origin: ORIGIN,
    fetchFn,
    ...overrides,
  });
}

const PAGINATION_SINGLE = { page: 1, limit: 10, totalPages: 1, totalDocs: 2, hasPrevPage: false, hasNextPage: false };

// ---------------------------------------------------------------------------
// Factory validation
// ---------------------------------------------------------------------------

test('article-create-providers factory rejects missing credentials and malformed inputs', async () => {
  const fetchFn = async () => httpResponse(200, flightList({ rows: [], pagination: PAGINATION_SINGLE }));
  assert.throws(() => createArticleCreateProviders({ siteKey: 'synthetic-site', siteId: 'sid-1' }), /authCookie/);
  assert.throws(() => createArticleCreateProviders({ siteKey: 'synthetic-site', siteId: 'sid-1', authCookie: '  ' }), /authCookie/);
  assert.throws(() => createArticleCreateProviders({ siteKey: 'synthetic-site', siteId: 'sid-1', authCookie: 'tok; other=1' }), /single payload-token value/);
  assert.throws(() => createArticleCreateProviders({ siteId: 'sid-1', authCookie: 'tok', fetchFn }), /siteKey/);
  assert.throws(() => createArticleCreateProviders({ siteKey: 'a/b', siteId: 'sid-1', authCookie: 'tok', fetchFn }), /siteKey/);
  assert.throws(() => createArticleCreateProviders({ siteKey: 'synthetic-site', authCookie: 'tok', fetchFn }), /siteId/);
  assert.throws(() => createArticleCreateProviders({ siteKey: 'synthetic-site', siteId: 'sid-1', authCookie: 'tok', fetchFn, origin: 'workspace.example.test' }), /origin/);
  assert.throws(() => createArticleCreateProviders({ siteKey: 'synthetic-site', siteId: 'sid-1', authCookie: 'tok', fetchFn, origin: 'https://workspace.example.test/posts' }), /origin/);
  assert.throws(() => createArticleCreateProviders({ siteKey: 'synthetic-site', siteId: 'sid-1', authCookie: 'tok', fetchFn: 'nope' }), /fetchFn/);
  assert.throws(() => createArticleCreateProviders({ siteKey: 'synthetic-site', siteId: 'sid-1', authCookie: 'tok', fetchFn, maxListPages: 0 }), /maxListPages/);
  // Default origin is the WORKSPACE domain (the editor routes live there),
  // not the per-site public domain.
  assert.equal(ALLINCMS_ARTICLE_PROVIDERS_DEFAULT_ORIGIN, 'https://workspace.laicms.com');
});

// ---------------------------------------------------------------------------
// beforePostIds: list flight parsing, headers, pagination
// ---------------------------------------------------------------------------

test('beforePostIds parses the posts list flight and sends workspace RSC headers', async () => {
  const { fetchFn, calls } = createFetchRouter(async (url) => httpResponse(200, flightList({
    rows: [{ id: 'existing-1', title: 'Old Guide' }, { id: 'existing-2', title: 'Older Guide' }],
    pagination: PAGINATION_SINGLE,
    categoryOptions: [{ label: 'Guides', value: 'cat-1' }],
    tagOptions: [],
  })));
  const providers = makeProviders(fetchFn);
  const ids = await providers.beforePostIds();
  assert.deepEqual(ids, ['existing-1', 'existing-2']);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${ORIGIN}/synthetic-site/posts?_rsc=1`);
  assert.equal(calls[0].opts.method, 'GET');
  assert.equal(calls[0].opts.redirect, 'manual');
  assert.equal(calls[0].opts.headers.RSC, '1');
  assert.equal(calls[0].opts.headers.Cookie, `payload-token=${TOKEN}`);
  assert.equal(calls[0].opts.headers.Accept, 'text/x-component');
  assert.equal(calls[0].opts.headers.Origin, ORIGIN);
});

test('beforePostIds accepts the minimal data+pagination flight shape', async () => {
  const { fetchFn } = createFetchRouter(async () => httpResponse(200, flightListMinimalShape({
    rows: [{ id: 'existing-1' }],
    pagination: PAGINATION_SINGLE,
  })));
  const providers = makeProviders(fetchFn);
  assert.deepEqual(await providers.beforePostIds(), ['existing-1']);
});

test('beforePostIds follows totalPages pagination and hasNextPage pagination', async () => {
  // totalPages style: page 2 exists.
  {
    const pages = {
      1: flightList({ rows: [{ id: 'a' }, { id: 'b' }], pagination: { page: 1, totalPages: 2, totalDocs: 3, hasNextPage: true } }),
      2: flightList({ rows: [{ id: 'c' }], pagination: { page: 2, totalPages: 2, totalDocs: 3, hasNextPage: false } }),
    };
    const { fetchFn, calls } = createFetchRouter(async (url) => httpResponse(200, pages[url.searchParams.get('page') ?? '1']));
    const providers = makeProviders(fetchFn);
    assert.deepEqual(await providers.beforePostIds(), ['a', 'b', 'c']);
    assert.deepEqual(calls.map((call) => call.url), [
      `${ORIGIN}/synthetic-site/posts?_rsc=1`,
      `${ORIGIN}/synthetic-site/posts?_rsc=1&page=2`,
    ]);
  }
  // hasNextPage style without totalPages.
  {
    const pages = {
      1: flightList({ rows: [{ id: 'a' }], pagination: { page: 1, hasNextPage: true } }),
      2: flightList({ rows: [{ id: 'b' }], pagination: { page: 2, hasNextPage: false } }),
    };
    const { fetchFn, calls } = createFetchRouter(async (url) => httpResponse(200, pages[url.searchParams.get('page') ?? '1']));
    const providers = makeProviders(fetchFn);
    assert.deepEqual(await providers.beforePostIds(), ['a', 'b']);
    assert.equal(calls.length, 2);
  }
  // A pagination cap keeps the loop bounded, and hitting it while more pages
  // remain fails closed instead of returning a truncated snapshot.
  {
    const { fetchFn, calls } = createFetchRouter(async (url) => httpResponse(200, flightList({
      rows: [{ id: `id-${url.searchParams.get('page') ?? '1'}` }],
      pagination: { page: Number(url.searchParams.get('page') ?? '1'), hasNextPage: true },
    })));
    const providers = makeProviders(fetchFn, { maxListPages: 3 });
    await assert.rejects(() => providers.beforePostIds(), /exceeded the maxListPages cap \(3\)/);
    assert.equal(calls.length, 3);
  }
});

test('beforePostIds fails closed on structure drift instead of returning an empty snapshot', async () => {
  // No list props box at all (e.g. a sign-in flight reached with HTTP 200).
  {
    const { fetchFn } = createFetchRouter(async () => httpResponse(200, SIGN_IN_FLIGHT));
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /did not contain a list props box with a data array/);
  }
  // Zero parsable rows (plain HTML error page).
  {
    const { fetchFn } = createFetchRouter(async () => httpResponse(200, '<html>not a flight stream</html>'));
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /no parsable RSC rows/);
  }
  // A data row without a non-empty string id.
  {
    const { fetchFn } = createFetchRouter(async () => httpResponse(200, flightList({
      rows: [{ id: 'existing-1' }, { title: 'missing id' }],
      pagination: PAGINATION_SINGLE,
    })));
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /row 1 has no non-empty string id/);
  }
  // Duplicate IDs inside one page.
  {
    const { fetchFn } = createFetchRouter(async () => httpResponse(200, flightList({
      rows: [{ id: 'existing-1' }, { id: 'existing-1' }],
      pagination: PAGINATION_SINGLE,
    })));
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /duplicate post id "existing-1"/);
  }
  // Page parameter not honored: page 2 replays the exact first-page rows.
  {
    const page1 = flightList({ rows: [{ id: 'a' }], pagination: { page: 1, totalPages: 2, hasNextPage: true } });
    const { fetchFn } = createFetchRouter(async () => httpResponse(200, page1));
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /pagination parameter appears unsupported/);
  }
});

test('providers refuse sign-in redirects, unexpected redirects and non-200 responses', async () => {
  // 302 to the sign-in route: the canonical unauthenticated outcome.
  {
    const { fetchFn } = createFetchRouter(async () => httpResponse(302, '', { location: '/sign-in?next=%2Fsynthetic-site%2Fposts' }));
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /redirected to sign-in \(302 .*payload-token/);
  }
  // Any other unexpected redirect is refused too (never silently followed).
  {
    const { fetchFn } = createFetchRouter(async () => httpResponse(302, '', { location: '/somewhere-else' }));
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /was redirected \(302 .*must land on 200/);
  }
  // Plain HTTP failure.
  {
    const { fetchFn } = createFetchRouter(async () => httpResponse(500, 'Internal Server Error'));
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /returned HTTP 500, expected 200/);
  }
  // Transport-level failure (offline, DNS, TLS).
  {
    const { fetchFn } = createFetchRouter(async () => { throw new Error('ECONNREFUSED synthetic'); });
    const providers = makeProviders(fetchFn);
    await assert.rejects(() => providers.beforePostIds(), /failed at the transport layer \(ECONNREFUSED synthetic\)/);
  }
});

test('RSC reads follow 307 router-state redirects to the canonical location like allincms_api.get_page', async () => {
  const finalFlight = flightList({ rows: [{ id: 'existing-1' }], pagination: PAGINATION_SINGLE });
  // Our own ?_rsc=1 already satisfies the router-state redirect: no extra hop.
  {
    const { fetchFn, calls } = createFetchRouter(async (url) => {
      if (!url.searchParams.has('_rsc')) {
        return httpResponse(307, '', { location: `${url.pathname}?_rsc=8f2a1b` });
      }
      return httpResponse(200, finalFlight);
    });
    const providers = makeProviders(fetchFn);
    assert.deepEqual(await providers.beforePostIds(), ['existing-1']);
    assert.deepEqual(calls.map((call) => call.url), [`${ORIGIN}/synthetic-site/posts?_rsc=1`]);
  }
  // A redirect away from a provider URL (e.g. trailing-slash normalization)
  // is followed once with the same headers and the final 200 is parsed.
  {
    const { fetchFn, calls } = createFetchRouter(async (url) => {
      if (calls.length === 1) return httpResponse(307, '', { location: url.pathname });
      return httpResponse(200, htmlEditorPage('created-1'));
    });
    const providers = makeProviders(fetchFn);
    const evidence = await providers.editorReopen({ createdPostId: 'created-1' });
    assert.deepEqual(evidence, { status: 200, authenticated: true, healthy: true, postId: 'created-1' });
    assert.deepEqual(calls.map((call) => call.url), [
      `${ORIGIN}/synthetic-site/posts/created-1/update`,
      `${ORIGIN}/synthetic-site/posts/created-1/update`,
    ]);
  }
});

// ---------------------------------------------------------------------------
// createReadback
// ---------------------------------------------------------------------------

const CREATED_DEFAULT_VALUES = {
  title: 'Synthetic New Guide',
  slug: 'new-guide',
  excerpt: 'Fixture excerpt.',
  order: 3,
  coverImage: null,
  categories: [{ id: 'cat-1', name: 'Qualification Guides' }],
  tags: [],
  content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
};

function createReadbackHarness({ beforeRows, afterRows, defaultValues = CREATED_DEFAULT_VALUES, defaultValuesStatus = 200 } = {}) {
  const state = { beforeRows, afterRows, created: false };
  const { fetchFn, calls } = createFetchRouter(async (url) => {
    if (url.pathname === '/synthetic-site/posts') {
      const rows = state.created ? (state.afterRows ?? []) : (state.beforeRows ?? []);
      return httpResponse(200, flightList({ rows, pagination: { page: 1, totalPages: 1, totalDocs: rows.length, hasNextPage: false } }));
    }
    if (url.pathname === '/synthetic-site/posts/created-1/update') {
      if (defaultValuesStatus !== 200) return httpResponse(defaultValuesStatus, 'missing');
      return httpResponse(200, flightEditor(defaultValues, 'created-1'));
    }
    return httpResponse(404, 'no route');
  });
  return { providers: makeProviders(fetchFn), calls, state };
}

test('createReadback derives the sole before/after delta and builds the full record', async () => {
  const harness = createReadbackHarness({
    beforeRows: [{ id: 'existing-1' }],
    afterRows: [{ id: 'existing-1' }, { id: 'created-1' }],
  });
  const before = await harness.providers.beforePostIds();
  assert.deepEqual(before, ['existing-1']);
  harness.state.created = true;
  const { record, afterPostIds } = await harness.providers.createReadback({});
  assert.deepEqual(afterPostIds, ['existing-1', 'created-1']);
  // Full-field record: the parsed editor defaultValues plus the created id and
  // the bound siteId (the editor props historically omit siteId).
  assert.deepEqual(record, {
    ...CREATED_DEFAULT_VALUES,
    categories: [{ id: 'cat-1', name: 'Qualification Guides' }],
    id: 'created-1',
    siteId: 'sid-1',
  });
  // The editor read is an RSC read of the update page.
  assert.deepEqual(harness.calls.map((call) => call.url), [
    `${ORIGIN}/synthetic-site/posts?_rsc=1`,
    `${ORIGIN}/synthetic-site/posts?_rsc=1`,
    `${ORIGIN}/synthetic-site/posts/created-1/update?_rsc=1`,
  ]);
});

test('createReadback accepts an explicit createdPostId and cross-checks it against the delta', async () => {
  // Explicit id agreeing with the delta is accepted even without any memo use.
  const agree = createReadbackHarness({
    beforeRows: [{ id: 'existing-1' }],
    afterRows: [{ id: 'existing-1' }, { id: 'created-1' }],
  });
  await agree.providers.beforePostIds();
  agree.state.created = true;
  const { record } = await agree.providers.createReadback({ createdPostId: 'created-1' });
  assert.equal(record.id, 'created-1');

  // Explicit id disagreeing with the sole delta fails closed as drift.
  const disagree = createReadbackHarness({
    beforeRows: [{ id: 'existing-1' }],
    afterRows: [{ id: 'existing-1' }, { id: 'created-1' }],
  });
  await disagree.providers.beforePostIds();
  disagree.state.created = true;
  await assert.rejects(() => disagree.providers.createReadback({ createdPostId: 'created-9' }), /created-9.*drifted from the sole before\/after snapshot delta.*created-1|drifted from the sole before\/after snapshot delta.*created-9/);

  // Without a memo and without args.createdPostId there is no delta basis.
  const noMemo = createReadbackHarness({
    beforeRows: [{ id: 'existing-1' }],
    afterRows: [{ id: 'existing-1' }, { id: 'created-1' }],
  });
  noMemo.state.created = true;
  await assert.rejects(() => noMemo.providers.createReadback({}), /args\.createdPostId or a before snapshot/);
});

test('createReadback fails closed on ambiguous deltas and editor payload drift', async () => {
  // Two new IDs: guessing is forbidden.
  {
    const harness = createReadbackHarness({
      beforeRows: [{ id: 'existing-1' }],
      afterRows: [{ id: 'existing-1' }, { id: 'created-1' }, { id: 'created-2' }],
    });
    await harness.providers.beforePostIds();
    harness.state.created = true;
    await assert.rejects(() => harness.providers.createReadback({}), /expected exactly one new post id .* found 2/);
  }
  // Zero new IDs: the create never landed in the list.
  {
    const harness = createReadbackHarness({
      beforeRows: [{ id: 'existing-1' }],
      afterRows: [{ id: 'existing-1' }],
    });
    await harness.providers.beforePostIds();
    harness.state.created = true;
    await assert.rejects(() => harness.providers.createReadback({}), /found 0/);
  }
  // defaultValues missing a contract field is structure drift, never a defaulted record.
  {
    const drifted = { ...CREATED_DEFAULT_VALUES };
    delete drifted.order;
    const harness = createReadbackHarness({
      beforeRows: [{ id: 'existing-1' }],
      afterRows: [{ id: 'existing-1' }, { id: 'created-1' }],
      defaultValues: drifted,
    });
    await harness.providers.beforePostIds();
    harness.state.created = true;
    await assert.rejects(() => harness.providers.createReadback({}), /missing article create contract fields: order/);
  }
  // The editor page answering non-200 fails closed.
  {
    const harness = createReadbackHarness({
      beforeRows: [{ id: 'existing-1' }],
      afterRows: [{ id: 'existing-1' }, { id: 'created-1' }],
      defaultValuesStatus: 404,
    });
    await harness.providers.beforePostIds();
    harness.state.created = true;
    await assert.rejects(() => harness.providers.createReadback({}), /returned HTTP 404/);
  }
});

test('createReadback refuses a cross-site editor record and honors a matching RSC siteId', async () => {
  // Conflicting siteId inside the editor props: cross-site record, fail closed.
  {
    const harness = createReadbackHarness({
      beforeRows: [{ id: 'existing-1' }],
      afterRows: [{ id: 'existing-1' }, { id: 'created-1' }],
      defaultValues: { ...CREATED_DEFAULT_VALUES, siteId: 'sid-other' },
    });
    await harness.providers.beforePostIds();
    harness.state.created = true;
    await assert.rejects(() => harness.providers.createReadback({}), /reports siteId "sid-other".*"sid-1"/);
  }
  // Matching siteId passes through as the authoritative value.
  {
    const harness = createReadbackHarness({
      beforeRows: [{ id: 'existing-1' }],
      afterRows: [{ id: 'existing-1' }, { id: 'created-1' }],
      defaultValues: { ...CREATED_DEFAULT_VALUES, siteId: 'sid-1' },
    });
    await harness.providers.beforePostIds();
    harness.state.created = true;
    const { record } = await harness.providers.createReadback({});
    assert.equal(record.siteId, 'sid-1');
  }
});

// ---------------------------------------------------------------------------
// editorReopen
// ---------------------------------------------------------------------------

test('editorReopen asserts HTTP 200, no sign-in redirect, and the post edit context', async () => {
  const ok = createFetchRouter(async () => httpResponse(200, htmlEditorPage('created-1')));
  const providers = makeProviders(ok.fetchFn);
  assert.deepEqual(await providers.editorReopen({ createdPostId: 'created-1' }), {
    status: 200, authenticated: true, healthy: true, postId: 'created-1',
  });
  assert.equal(ok.calls[0].url, `${ORIGIN}/synthetic-site/posts/created-1/update`);
  assert.equal(ok.calls[0].opts.headers.RSC, undefined, 'editor reopen is a plain browser-like HTML GET');
  assert.equal(ok.calls[0].opts.headers.Cookie, `payload-token=${TOKEN}`);

  // 302 to sign-in is rejected as unauthenticated.
  const signIn = createFetchRouter(async () => httpResponse(302, '', { location: '/sign-in' }));
  await assert.rejects(() => makeProviders(signIn.fetchFn).editorReopen({ createdPostId: 'created-1' }), /redirected to sign-in/);

  // Non-200 is rejected.
  const missing = createFetchRouter(async () => httpResponse(404, 'gone'));
  await assert.rejects(() => makeProviders(missing.fetchFn).editorReopen({ createdPostId: 'created-1' }), /HTTP 404/);

  // A 200 document without the created post id carries no edit context (an
  // authenticated soft-redirect to sign-in looks exactly like this).
  const noContext = createFetchRouter(async () => httpResponse(200, '<html><body>workspace home</body></html>'));
  await assert.rejects(() => makeProviders(noContext.fetchFn).editorReopen({ createdPostId: 'created-1' }), /does not contain the created post id "created-1"/);

  // The created post id is mandatory.
  const bare = createFetchRouter(async () => httpResponse(200, htmlEditorPage('created-1')));
  await assert.rejects(() => makeProviders(bare.fetchFn).editorReopen({}), /editorReopen args\.createdPostId is required/);
  await assert.rejects(() => makeProviders(bare.fetchFn).editorReopen(), /editorReopen args\.createdPostId is required/);
});

// ---------------------------------------------------------------------------
// Driver integration: real providers + fake mutation transport
// ---------------------------------------------------------------------------

function makeDriverPlanFixture() {
  const identity = { id: null, natural_key: { site_key: 'synthetic-site', slug: 'new-guide' }, match_strategy: 'exact_natural_key' };
  const fields = {
    title: { value: 'Synthetic New Guide' },
    slug: { value: 'new-guide' },
    excerpt: { value: 'Fixture excerpt.' },
    order: { value: 3 },
    coverImage: { value: null },
    categories: { value: ['cat-1'] },
    tags: { value: [] },
    content: { value: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }] },
  };
  return {
    plan_id: 'COP-article-create-providers',
    authorization_scope: {
      status: 'approved', actor: 'Test Human',
      approved_at: new Date(Date.now() - 60000).toISOString(),
      expires_at: new Date(Date.now() + 28 * 60000).toISOString(),
    },
    desired_state: [{ entity_ref: 'article:new-guide', entity_type: 'article', intent: 'create', identity, fields }],
    operations: [{ operation_id: 'OP-AC-001', entity_ref: 'article:new-guide', entity_type: 'article', intent: 'create', identity: structuredClone(identity) }],
  };
}

const DRIVER_RUNTIME = { routerTree: '[]', deploymentId: 'd'.repeat(40), actions: { postCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } } };

function createDriverHarness({ defaultValues = CREATED_DEFAULT_VALUES } = {}) {
  const plan = makeDriverPlanFixture();
  const events = [];
  const state = { created: false };
  const requested = [];
  const request = async (details) => {
    events.push(`request:${details.actionName}`);
    requested.push(details);
    state.created = true;
    return { status: 200, ok: true, contentType: 'text/x-component' };
  };
  const { fetchFn, calls } = createFetchRouter(async (url) => {
    events.push(`fetch:${url.pathname}${url.search}`);
    if (url.pathname === '/synthetic-site/posts') {
      const rows = state.created ? [{ id: 'existing-1' }, { id: 'created-1' }] : [{ id: 'existing-1' }];
      return httpResponse(200, flightList({ rows, pagination: { page: 1, totalPages: 1, totalDocs: rows.length, hasNextPage: false } }));
    }
    if (url.pathname === '/synthetic-site/posts/created-1/update') {
      if (url.searchParams.has('_rsc')) return httpResponse(200, flightEditor(defaultValues, 'created-1'));
      return httpResponse(200, htmlEditorPage('created-1'));
    }
    return httpResponse(404, 'no route');
  });
  const providers = makeProviders(fetchFn);
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: 'synthetic-site',
    siteId: 'sid-1',
    runtime: DRIVER_RUNTIME,
    request,
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    articleBeforePostIdsProvider: providers.beforePostIds,
    articleCreateReadbackProvider: providers.createReadback,
    articleEditorReopenProvider: providers.editorReopen,
  });
  return { plan, handlers, events, requested, fetchCalls: calls, providers };
}

test('driver article:create completes end-to-end with the real providers over a fake transport', async () => {
  const harness = createDriverHarness();
  const result = await harness.handlers['article:create'].execute({ plan: harness.plan, operation: harness.plan.operations[0] });
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: 'created-1' });
  // Provider order: before snapshot -> mutation POST -> after list + editor RSC
  // readback -> editor HTML reopen.
  assert.deepEqual(harness.events, [
    'fetch:/synthetic-site/posts?_rsc=1',
    'request:postCreate',
    'fetch:/synthetic-site/posts?_rsc=1',
    'fetch:/synthetic-site/posts/created-1/update?_rsc=1',
    'fetch:/synthetic-site/posts/created-1/update',
  ]);
  assert.equal(harness.requested.length, 1);
  assert.equal(harness.requested[0].actionName, 'postCreate');
  // The outgoing create payload carries the desired 8 contract fields + siteId
  // (categories as plain IDs; the readback record answers with {id,name} rows).
  assert.deepEqual(harness.requested[0].payload, {
    title: 'Synthetic New Guide', slug: 'new-guide', excerpt: 'Fixture excerpt.', order: 3,
    coverImage: null, categories: ['cat-1'], tags: [],
    content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'sid-1',
  });
});

test('driver article:create fails closed when the authoritative record drifted', async () => {
  const harness = createDriverHarness({ defaultValues: { ...CREATED_DEFAULT_VALUES, title: 'Drifted Title' } });
  await assert.rejects(
    () => harness.handlers['article:create'].execute({ plan: harness.plan, operation: harness.plan.operations[0] }),
    (error) => {
      assert.match(error.message, /article create not confirmed/);
      assert.match(error.message, /title drifted/);
      // The request WAS sent: the failure must stay requestStarted, never a silent not-started.
      assert.equal(Object.getOwnPropertyDescriptor(error, 'requestStarted').value, true);
      return true;
    },
  );
});

// ---------------------------------------------------------------------------
// host-run-template default assembly
// ---------------------------------------------------------------------------

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

function makeTemplatePlan() {
  const AUTH_AT = new Date(Date.now() - 60000).toISOString();
  const identity = { id: null, natural_key: { site_key: 'synthetic-site', slug: 'new-guide' }, match_strategy: 'exact_natural_key' };
  const claimEvidence = { source_id: 'SRC-001', source_digest: H('b'), extraction_id: 'SX-001', unit_id: 'UNIT-1', locator: 'x', extraction_digest: H('u') };
  const plan = {
    schema_version: '1.1', plan_id: 'COP-template-providers-001', plan_digest: H('0'),
    client_id: 'fluxpedal-synthetic', company_id: 'fluxpedal-motors-synthetic', task_id: 'synthetic-task',
    runtime_scope: expectedRuntimeScope({ client_id: 'fluxpedal-synthetic', company_id: 'fluxpedal-motors-synthetic', task_id: 'synthetic-task' }),
    execution_mode: 'audit', plan_phase: 'site_operation',
    cms_adapter: { id: 'allincms', version: 'test', observed_at: new Date().toISOString(), deployment_fingerprint: H('dep') },
    site_selector: { target_scope: 'site', site_key: 'synthetic-site', site_id: 'sid-1', account_user_id: 'uid-1', selection_source: 'user-confirmed', bootstrap_readback_ref: null, bootstrap_plan_digest: null, cross_site_fallback: false },
    source_snapshot: { captured_at: new Date().toISOString(), sources: [{
      source_id: 'SRC-001', kind: 'brief', location: runtimePath('10_sources/brief.md'), digest: H('b'), authority: 'primary', owner: 'synthetic-owner', rights_status: 'owned', method_use_clearance: 'approved', publication_clearance: 'approved', source_date: '2026-08-27T00:00:00Z', review_after: null, source_scope: 'fluxpedal-synthetic/fluxpedal-motors-synthetic/synthetic-task',
      extractions: [{ extraction_id: 'SX-001', artifact_ref: runtimePath('20_work/sx.json'), source_digest: H('b'), captured_at: new Date().toISOString(), status: 'complete', units: [{ unit_id: 'UNIT-1', locator: 'x', extraction_digest: H('u') }] }], publication_clearance: 'approved' }] },
    claim_ledger: ['Synthetic New Guide', 'new-guide', '', 0, null, [], [], []].map((value, i) => ({ claim_id: `CLAIM-ART-${i + 1}`, status: 'confirmed', source_refs: ['SRC-001'], evidence_refs: [claimEvidence], value, notes: '' })),
    capability_snapshot: { captured_at: new Date(Date.now() - 60000).toISOString(), expires_at: new Date(Date.now() + 28 * 60000).toISOString(), deployment_fingerprint: H('dep'), capabilities: [
      { capability_id: 'allincms.article.create', entity_type: 'article', action: 'create', maturity: 'live_verified_current_deployment', evidence_refs: [runtimePath('70_evidence/basis.json')] }] },
    desired_state: [{
      entity_ref: 'article:new-guide', entity_type: 'article', intent: 'create', identity,
      fields: {
        title: { value: 'Synthetic New Guide', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-1'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        slug: { value: 'new-guide', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-2'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        excerpt: { value: '', fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-3'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        order: { value: 0, fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-4'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        coverImage: { value: null, fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-5'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        categories: { value: [], fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-6'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        tags: { value: [], fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-7'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
        content: { value: [], fact_status: 'confirmed', source_refs: ['SRC-001'], claim_refs: ['CLAIM-ART-8'], derivation: { mode: 'direct', notes: '' }, clear_existing: false },
      },
    }],
    current_state_fingerprint: H('c'),
    diff: [{ operation_id: 'OP-AC-001', entity_ref: 'article:new-guide', resolved_intent: 'create', changed_fields: ['title', 'slug'] }],
    operations: [{ operation_id: 'OP-AC-001', entity_ref: 'article:new-guide', entity_type: 'article', intent: 'create', identity: structuredClone(identity), field_refs: ['title', 'slug'], capability_ref: 'allincms.article.create', expected_current_fingerprint: null, dependencies: [], mutation: true, publication_effect: 'private_draft', readback_requirements: ['article.create.before_after_unique_id_delta', 'article.create.backend_field_readback', 'article.create.editor_reopen_health'] }],
    authorization_scope: { status: 'approved', actor: 'Test Human', identity_status: 'not_verified', target_scope: 'site', target_key: 'synthetic-site', operation_ids: ['OP-AC-001'], approved_at: AUTH_AT, archived_at: AUTH_AT, expires_at: new Date(Date.now() + 28 * 60000).toISOString(), plan_sha256: null },
    reconciliation_policy: { ambiguous_write: 'read-only-reconcile-before-any-retry', automatic_retry_after_request_started: false, identity_rule: 'exact-id-or-site-scoped-natural-key' },
    verification_plan: { backend_readback: true, editor_reopen: true, frontend: true, evidence_targets: [runtimePath('70_evidence/run.json')] },
    writeback_targets: [{ kind: 'evidence', path: runtimePath('70_evidence/run.json'), visibility: 'private-runtime' }],
  };
  return reseal(plan);
}

const TEMPLATE_DEFAULT_VALUES = {
  title: 'Synthetic New Guide', slug: 'new-guide', excerpt: '', order: 0,
  coverImage: null, categories: [], tags: [], content: [],
};

function createTemplateHarness() {
  const plan = makeTemplatePlan();
  const tmp = mkdtempSync(join(tmpdir(), 'acrun-providers-'));
  mkdirSync(join(tmp, '70_evidence'), { recursive: true });
  const toTmp = (path) => join(tmp, path.replace('customer-runtime/10_clients/fluxpedal-synthetic/30_tasks/synthetic-task/', ''));
  const state = { created: false };
  const fetchEvents = [];
  const request = async () => { state.created = true; return { status: 200, ok: true, contentType: 'text/x-component' }; };
  const { fetchFn, calls } = createFetchRouter(async (url) => {
    fetchEvents.push(`${url.pathname}${url.search}`);
    if (url.pathname === '/synthetic-site/posts') {
      const rows = state.created ? [{ id: 'existing-1' }, { id: 'created-1' }] : [{ id: 'existing-1' }];
      return httpResponse(200, flightList({ rows, pagination: { page: 1, totalPages: 1, totalDocs: rows.length, hasNextPage: false } }));
    }
    if (url.pathname === '/synthetic-site/posts/created-1/update') {
      if (url.searchParams.has('_rsc')) return httpResponse(200, flightEditor(TEMPLATE_DEFAULT_VALUES, 'created-1'));
      return httpResponse(200, htmlEditorPage('created-1'));
    }
    return httpResponse(404, 'no route');
  });
  const readbackProvider = async ({ plan: readbackPlan, operation }) => {
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
      const envelope = { schema_version: '1.0', check_id: checkId, evidence_kind: kind, captured_at: ts, site_key: 'synthetic-site', site_id: 'sid-1', entity_ref: operation.entity_ref, entity_id: 'created-1', subject_digest: subjectDigest, method: 'host-readback', observed_result: JSON.stringify({ ok: true }), observations: obs };
      const ref = runtimePath(`70_evidence/tpl-check-${operation.operation_id}-${idx}.json`);
      writeFileSync(toTmp(ref), JSON.stringify(envelope));
      return { check_id: checkId, evidence_kind: kind, passed: true, artifact_ref: ref, artifact_digest: `sha256:${createHash('sha256').update(JSON.stringify(envelope)).digest('hex')}`, artifact_media_type: 'application/json', observed_at: ts, site_key: 'synthetic-site', site_id: 'sid-1', entity_ref: operation.entity_ref, entity_id: 'created-1', subject_digest: subjectDigest, method: 'host-readback', observed_result: JSON.stringify({ ok: true }), observations: obs };
    });
    return { ok: true, authoritative: true, requirements: operation.readback_requirements, evidence_ref: runtimePath('70_evidence/tpl-check-OP-AC-001-0.json'), checks };
  };
  const hooks = {
    readbackProvider,
    fingerprintProvider: async () => ({ fingerprint: H('fp') }),
    backendReadback: async () => ({}),
    preflight: async () => ({
      login_status: 'authenticated', user_id: 'uid-1', site_key: 'synthetic-site', site_id: 'sid-1',
      deployment_fingerprint: H('dep'), capability_ids: ['allincms.article.create'],
    }),
    writeEvidence: async ({ path, evidence }) => {
      mkdirSync(dirname(toTmp(path)), { recursive: true });
      writeFileSync(toTmp(path), JSON.stringify(evidence));
      return { ok: true, evidence_ref: path };
    },
    readEvidenceArtifact: async (arg) => readFileSync(toTmp(typeof arg === 'string' ? arg : arg?.path)),
  };
  return { plan, tmp, hooks, request, fetchFn, calls, fetchEvents, cleanup: () => rmSync(tmp, { recursive: true, force: true }) };
}

test('template assembles the default article:create providers from authCookie and completes the full controller run', async () => {
  const harness = createTemplateHarness();
  try {
    // No article:* provider hooks are supplied: the template must wire the
    // real pure-HTTP providers from authCookie + providerOrigin + fetchFn.
    const result = await runAllinCmsHostPlanTemplate({
      plan: harness.plan,
      runtime: DRIVER_RUNTIME,
      hooks: harness.hooks,
      transport: { request: harness.request },
      evidencePath: runtimePath('70_evidence/run.json'),
      authCookie: TOKEN,
      providerOrigin: ORIGIN,
      fetchFn: harness.fetchFn,
    });
    assert.equal(result.ok, true, JSON.stringify(result.problems ?? result).slice(0, 400));
    assert.equal(result.status, 'completed');
    assert.equal(result.evidence.operations[0].status, 'readback_passed');
    assert.deepEqual(harness.fetchEvents, [
      '/synthetic-site/posts?_rsc=1',
      '/synthetic-site/posts?_rsc=1',
      '/synthetic-site/posts/created-1/update?_rsc=1',
      '/synthetic-site/posts/created-1/update',
    ]);
  } finally {
    harness.cleanup();
  }
});

test('template without article hooks and without authCookie keeps the driver fail-closed refusal', async () => {
  const harness = createTemplateHarness();
  try {
    const result = await runAllinCmsHostPlanTemplate({
      plan: harness.plan,
      runtime: DRIVER_RUNTIME,
      hooks: harness.hooks,
      transport: { request: harness.request },
      evidencePath: runtimePath('70_evidence/run.json'),
    });
    assert.equal(result.ok, false, 'a run without providers must not report success');
    // Without article hooks and without an authCookie nothing is wired: the
    // driver refuses inside execute and the controller stops fail-closed for
    // manual intervention (the transport error message itself is not copied
    // into the evidence envelope, so assert the failure code).
    assert.equal(result.status, 'ambiguous');
    assert.equal(result.evidence.operations[0].failure_code, 'RECONCILIATION_HANDLER_MISSING');
    assert.equal(result.evidence.operations[0].transport.status, 'unknown');
    assert.equal(harness.calls.length, 0, 'no provider HTTP read may happen when nothing was wired');
  } finally {
    harness.cleanup();
  }
});

test('template cannot assemble defaults without a complete site binding and explicit hooks fully override them', async () => {
  // site_selector without site_id: assembling defaults fails closed before any work.
  {
    const harness = createTemplateHarness();
    const broken = structuredClone(harness.plan);
    broken.site_selector.site_id = null;
    await assert.rejects(
      () => runAllinCmsHostPlanTemplate({
        plan: broken, runtime: DRIVER_RUNTIME, hooks: harness.hooks, transport: { request: harness.request },
        evidencePath: runtimePath('70_evidence/run.json'), authCookie: TOKEN, providerOrigin: ORIGIN, fetchFn: harness.fetchFn,
      }),
      /cannot assemble the default article:create providers.*site_id/,
    );
    assert.equal(harness.calls.length, 0);
    harness.cleanup();
  }
  // All three explicit hooks win over authCookie-backed defaults: the fetch
  // router is never contacted and the run still completes.
  {
    const harness = createTemplateHarness();
    try {
      const events = [];
      const hooks = {
        ...harness.hooks,
        articleBeforePostIdsProvider: async () => { events.push('before'); return ['existing-1']; },
        articleCreateReadbackProvider: async () => { events.push('readback'); return { record: { ...TEMPLATE_DEFAULT_VALUES, id: 'created-1', siteId: 'sid-1' }, afterPostIds: ['existing-1', 'created-1'] }; },
        articleEditorReopenProvider: async ({ createdPostId }) => { events.push(`reopen:${createdPostId}`); return { status: 200, authenticated: true, healthy: true, postId: createdPostId }; },
      };
      const result = await runAllinCmsHostPlanTemplate({
        plan: harness.plan, runtime: DRIVER_RUNTIME, hooks, transport: { request: harness.request },
        evidencePath: runtimePath('70_evidence/run.json'), authCookie: TOKEN, providerOrigin: ORIGIN, fetchFn: harness.fetchFn,
      });
      assert.equal(result.ok, true, JSON.stringify(result.problems ?? result).slice(0, 400));
      assert.deepEqual(events, ['before', 'readback', 'reopen:created-1']);
      assert.equal(harness.calls.length, 0, 'explicit hooks must fully replace the assembled defaults (zero provider fetches)');
    } finally {
      harness.cleanup();
    }
  }
});
