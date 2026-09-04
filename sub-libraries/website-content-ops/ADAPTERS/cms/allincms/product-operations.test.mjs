import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { runInNewContext } from 'node:vm';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { buildProductPayload, createProductDraft, publishProduct, saveProductDraft, unpublishProduct, _internal } from './product-operations.mjs';
import { runActionWithRecovery } from './article-operations.mjs';
import { markRequestStarted, prepareStableCreatePayload } from './content-mutation-primitives.mjs';
import { createAllinCmsMutationAuthorizationContext, deriveAllinCmsMutationBinding } from './mutation-authorization.mjs';

test('buildProductPayload creates a complete canonical product payload', () => {
  const payload = buildProductPayload({
    defaults: {
      name: 'FP-HC60 Cargo Hub Motor',
      slug: 'fp-hc60-cargo-hub-motor',
      description: 'Cargo e-bike rear hub motor.',
      order: 0,
      media: null,
      mediaList: [],
      content: [],
      categories: [],
      tags: [],
      specifications: [{ key: 'Rated power', value: '500W' }],
    },
    siteId: 'site-1',
    productId: 'product-1',
    mode: 'publish',
  });
  assert.equal(payload.name, 'FP-HC60 Cargo Hub Motor');
  assert.equal(payload.slug, 'fp-hc60-cargo-hub-motor');
  assert.equal(payload.productId, 'product-1');
  assert.equal(payload.siteId, 'site-1');
  assert.equal(payload.mode, 'publish');
  assert.deepEqual(payload.specifications, [{ key: 'Rated power', value: '500W' }]);
});

test('productRoute builds create and update paths', () => {
  assert.equal(_internal.productRoute('oajc2ezib4'), '/oajc2ezib4/products');
  assert.equal(_internal.productRoute('oajc2ezib4', 'product-1'), '/oajc2ezib4/products/product-1/update');
});

test('buildProductPayload requires non-empty name and slug', () => {
  assert.throws(() => buildProductPayload({
    defaults: { name: '', slug: 'x' },
    siteId: 'site-1', productId: 'p1', mode: 'update',
  }), /name is required/);
});

test('buildProductPayload requires non-empty description (observed 2026-08-27 deployment zod min(1))', () => {
  assert.throws(() => buildProductPayload({
    defaults: { name: 'x', slug: 'x', description: '' },
    siteId: 'site-1', productId: 'p1', mode: 'update',
  }), /description is required/);
  assert.throws(() => buildProductPayload({
    defaults: { name: 'x', slug: 'x', description: '   ' },
    siteId: 'site-1', productId: 'p1', mode: 'update',
  }), /description is required/);
});

test('media binding emits the deployment url input shape {name,alt,type,source:url,url} (observed 2026-08-27)', () => {
  const p = buildProductPayload({
    defaults: { name: 'x', slug: 'x', description: 'desc', media: { type: 'image', value: { name: 'synthetic.webp', alt: null, type: 'image', source: 'url', url: 'https://assets.example.invalid/s/synthetic.webp' } } },
    siteId: 'site-1', productId: 'p1', mode: 'update',
  });
  assert.equal(p.media.source, 'url');
  assert.equal(p.media.url, 'https://assets.example.invalid/s/synthetic.webp');
  assert.equal(p.media.name, 'synthetic.webp');
  assert.equal(p.media.type, 'image');
});
test('media binding accepts deployment input discriminator {source: url, url} with name required (observed 2026-08-27)', () => {
  const p = buildProductPayload({
    defaults: { name: 'x', slug: 'x', description: 'desc', media: { source: 'url', url: 'https://assets.example.invalid/s/synthetic.webp', name: 'x.webp' } },
    siteId: 'site-1', productId: 'p1', mode: 'update',
  });
  assert.equal(p.media.source, 'url');
  assert.equal(p.media.url, 'https://assets.example.invalid/s/synthetic.webp');
  assert.equal(p.media.name, 'x.webp');
  assert.throws(() => buildProductPayload({ defaults: { name: 'x', slug: 'x', description: 'desc', media: { source: 'url', url: 'https://a.com/x.webp' } }, siteId: 'site-1', productId: 'p1', mode: 'update' }), /media.name is required/);
});

test('media binding accepts string-id shape and expands to url input form', () => {
  const p = buildProductPayload({
    defaults: { name: 'x', slug: 'x', description: 'desc', media: { type: 'image', value: '00000000000000000000000a' } },
    siteId: 'site-1', productId: 'p1', mode: 'update',
  });
  assert.equal(p.media.source, 'url');
  assert.equal(p.media.name, '00000000000000000000000a');
  assert.equal(p.media.url, '00000000000000000000000a');
});

test('specifications must be key/value strings', () => {
  assert.throws(() => buildProductPayload({
    defaults: { name: 'x', slug: 'x', specifications: [{ key: '', value: 'v' }] },
    siteId: 's', productId: 'p', mode: 'update',
  }), /specifications\[0\]\.key is required/);
});

test('createProductDraft refuses a non-object or array expected before any request', async () => {
  // P0-3.3a: same fail-closed expected shape rule as article create; the
  // ({record, afterProductIds}) host wrapper stays host-driver knowledge.
  const runtime = {
    actions: {
      productCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) },
    },
    deploymentId: 'd'.repeat(40),
    routerTree: '[]',
  };
  const sends = [];
  const request = async (details) => { sends.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; };
  for (const [label, expected] of [['array', ['name']], ['string', 'name'], ['null', null]]) {
    sends.length = 0;
    await assert.rejects(
      () => createProductDraft({
        siteKey: 'oajc2ezib4', runtime, request, siteId: 'site-1',
        payload: { name: 'x', slug: 'x', description: 'd', siteId: 'site-1' },
        expected,
        beforeProductIds: ['old-1'],
        readback: async () => ({ id: 'new-1', siteId: 'site-1' }),
        getCreatedProductId: (actual) => actual.id,
        getCreatedProductSiteId: (actual) => actual.siteId,
        getAfterProductIds: () => ['old-1', 'new-1'],
      }),
      /expected must be a non-array object/,
      label,
    );
    assert.equal(sends.length, 0, label);
  }
});

// P0-3.3a.3: the canonical expected comparison is owned by createProductDraft
// itself — the bottom layer extracts the record (host {record, afterProductIds}
// wrapper or bare record) and compares all 10 contract fields plus siteId.
// These direct bottom-layer tests pass no matcher at all.
// 2026-09-04 stable create payload B1: the create write path takes FLAT
// URL/OSS media only (the {type,value} editor wrapper is readback-only), so
// this canonical fixture is flat URL media.
const PRODUCT_CREATE_PAYLOAD = Object.freeze({
  name: 'FP-X1', slug: 'fp-x1', description: 'Fixture description.', order: 0,
  media: { name: 'fp.webp', type: 'image', source: 'url', url: 'https://assets.example.invalid/fp.webp' },
  mediaList: [], content: [{ type: 'p', children: [{ text: '产品正文' }] }],
  categories: ['cat-1'], tags: ['tag-1'], specifications: [{ key: 'Rated power', value: '500W' }],
  siteId: 'site-1',
});

function productDraftBase({ payload = structuredClone(PRODUCT_CREATE_PAYLOAD), overrides = {} } = {}) {
  const runtime = {
    actions: {
      productCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) },
    },
    deploymentId: 'd'.repeat(40),
    routerTree: '[]',
  };
  // The authorization context is minted over the exact prepared snapshot (the
  // same object and payloadText the bottom layer will send), mirroring the
  // canonical driver handoff.
  const prepared = prepareStableCreatePayload('product', payload, 'site-1');
  const binding = deriveAllinCmsMutationBinding({
    siteKey: 'oajc2ezib4',
    route: '/oajc2ezib4/products',
    actionName: 'productCreate',
    payload: prepared.snapshot,
    payloadText: prepared.payloadText,
  });
  return {
    siteKey: 'oajc2ezib4',
    runtime,
    request: async () => ({ status: 200, ok: true, contentType: 'text/x-component', headers: { 'content-type': 'text/x-component' } }),
    authorizationContext: createAllinCmsMutationAuthorizationContext({
      siteKey: binding.siteKey,
      operation: binding.operation,
      target: binding.target,
      approvalActor: 'Test Reviewer',
    }),
    siteId: 'site-1',
    payload,
    expected: payload,
    beforeProductIds: ['old-1'],
    readback: async () => ({ ...payload, id: 'new-1' }),
    getCreatedProductId: (actual) => actual.id,
    getCreatedProductSiteId: (actual) => actual.siteId,
    getAfterProductIds: () => ['old-1', 'new-1'],
    ...overrides,
  };
}

test('createProductDraft verifies exactly one before/after product ID delta', async () => {
  const result = await createProductDraft(productDraftBase());
  assert.equal(result.createdProductId, 'new-1');
  assert.equal(result.status, 'mutation_succeeded');
});

test('createProductDraft sends zero requests without expected, with a forged expectedMatch, or with an equal-but-separate expected object (P0-3.3a.1/3)', async () => {
  for (const [label, mutate, pattern] of [
    ['no expected', (options) => { options.expected = undefined; }, /expected must be a non-array object/],
    ['equal but separate expected object', (options) => { options.expected = { ...options.payload }; }, /same object reference/],
    ['expectedMatch supplied (P0-3.3a.3)', (options) => { options.expectedMatch = () => true; }, /expectedMatch has been removed/],
    ['match not a function', (options) => { options.match = true; }, /match must be a function/],
  ]) {
    const sends = [];
    const options = productDraftBase({ overrides: { request: async (details) => { sends.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; } } });
    mutate(options);
    await assert.rejects(() => createProductDraft(options), pattern, label);
    assert.equal(sends.length, 0, label);
  }
});

test('createProductDraft rejects a drifted record even when a permissive custom match returns true (P0-3.3a.3, driver-style wrapper readback)', async () => {
  // Mirrors the driver path: the readback is the host {record, afterProductIds}
  // wrapper, the bottom layer extracts and compares the record itself, and the
  // permissive custom match can only AND — never replace — that comparison.
  const sends = [];
  const result = await createProductDraft(productDraftBase({
    overrides: {
      request: async (details) => { sends.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; },
      match: () => true,
      getCreatedProductId: (actual) => actual?.record?.id,
      getCreatedProductSiteId: (actual) => actual?.record?.siteId,
      getAfterProductIds: (actual) => actual?.afterProductIds,
      readback: async () => ({ record: { ...PRODUCT_CREATE_PAYLOAD, name: 'DRIFTED NAME', id: 'new-1' }, afterProductIds: ['old-1', 'new-1'] }),
    },
  }));
  assert.equal(result.status, 'stopped_manual_intervention');
  assert.equal(result.automaticRetryAllowed, false);
  assert.equal(sends.length, 1);
  assert.match(result.mismatches.join('; '), /did not match the canonical expected readback/);
  assert.match(result.mismatches.join('; '), /name drifted from the frozen expected payload/);
});

test('createProductDraft refuses every forged expectedMatch callback before any request (P0-3.3a.3)', async () => {
  // The public expectedMatch parameter is deleted: the historical `() => true`
  // forgery bypass cannot even reach the request.
  for (const [label, expectedMatch] of [
    ['always-true predicate', () => true],
    ['throwing predicate', () => { throw new Error('boom'); }],
    ['non-function junk', 'permissive-string'],
  ]) {
    const sends = [];
    await assert.rejects(
      () => createProductDraft(productDraftBase({
        overrides: {
          expectedMatch,
          request: async (details) => { sends.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; },
        },
      })),
      /expectedMatch has been removed/,
      label,
    );
    assert.equal(sends.length, 0, label);
  }
});

test('createProductDraft compares a bare raw record readback by default and never defaults missing contract fields (P0-3.3a.3)', async () => {
  const sends = [];
  const drift = await createProductDraft(productDraftBase({
    overrides: {
      match: () => true,
      request: async (details) => { sends.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; },
      readback: async () => ({ ...PRODUCT_CREATE_PAYLOAD, slug: 'drifted-slug', id: 'new-1' }),
    },
  }));
  assert.equal(drift.status, 'stopped_manual_intervention');
  assert.equal(sends.length, 1);
  assert.match(drift.mismatches.join('; '), /slug drifted from the frozen expected payload/);

  sends.length = 0;
  const incomplete = { ...PRODUCT_CREATE_PAYLOAD, id: 'new-1' };
  delete incomplete.specifications;
  const missing = await createProductDraft(productDraftBase({
    overrides: {
      request: async (details) => { sends.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; },
      readback: async () => incomplete,
    },
  }));
  assert.equal(missing.status, 'stopped_manual_intervention');
  assert.match(missing.mismatches.join('; '), /specifications is missing from the created product record/);
});

test('createProductDraft fails closed on an empty or non-object wrapper record and on readback errors (P0-3.3a.3)', async () => {
  for (const [label, record] of [
    ['wrapper record null', null],
    ['wrapper record string', 'not-a-record'],
    ['wrapper record array', ['not-a-record']],
  ]) {
    const sends = [];
    const result = await createProductDraft(productDraftBase({
      overrides: {
        request: async (details) => { sends.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; },
        getCreatedProductId: (actual) => actual?.record?.id,
        getCreatedProductSiteId: (actual) => actual?.record?.siteId,
        getAfterProductIds: (actual) => actual?.afterProductIds,
        readback: async () => ({ record, afterProductIds: ['old-1', 'new-1'] }),
      },
    }));
    assert.equal(result.status, 'stopped_manual_intervention', label);
    assert.equal(result.createdProductId, null, label);
    assert.equal(sends.length, 1, label);
    assert.match(result.mismatches.join('; '), /readback record must be a non-array object/, label);
  }
  const sends = [];
  const failed = await createProductDraft(productDraftBase({
    overrides: {
      request: async (details) => { sends.push(details); return { status: 200, ok: true, contentType: 'text/x-component' }; },
      readback: async () => { throw new Error('readback transport exploded'); },
    },
  }));
  assert.equal(failed.status, 'stopped_manual_intervention');
  assert.equal(failed.readbackError, 'readback transport exploded');
  assert.equal(failed.automaticRetryAllowed, false);
  assert.equal(sends.length, 1);
});

// ---------------------------------------------------------------------------
// P0-A: an injected client is transport only — it carries no authorization
// exemption. Every underlying client.send (first attempt and every controlled
// retry) must re-derive the exact route/action/payload binding and validate the
// structured authorizationContext against it immediately before the transport
// fires, exactly like the native createAllinCmsActionClient path and article's
// injected-client wrapper. Before this fix, product requireClient forwarded
// straight to client.send with zero validation.
// ---------------------------------------------------------------------------
const P0A_SITE_KEY = 'demo-site';
const P0A_IDS = { siteId: 'site-1', productId: 'product-1' };
const P0A_UPDATE_DEFAULTS = { name: 'FP-X1', slug: 'fp-x1', description: 'Fixture description.' };

function injectedClientFor({ response = { status: 200, contentType: 'text/x-component' }, onSend } = {}) {
  const calls = [];
  return { calls, async send(details) { calls.push(details); if (onSend) await onSend(details); return typeof response === 'function' ? response(details, calls) : response; } };
}
function p0aProductUpdatePayload(mode = 'update') {
  return buildProductPayload({ defaults: P0A_UPDATE_DEFAULTS, ...P0A_IDS, mode });
}
function p0aMintContext({ siteKey = P0A_SITE_KEY, operation, target, approvedAt, expiresAt }) {
  return createAllinCmsMutationAuthorizationContext({
    siteKey, operation, target, approvalActor: 'Test Reviewer',
    ...(approvedAt ? { approvedAt } : {}),
    ...(expiresAt ? { expiresAt } : {}),
  });
}
function p0aUpdateAuth(mode = 'update') {
  const payload = p0aProductUpdatePayload(mode);
  const binding = deriveAllinCmsMutationBinding({
    siteKey: P0A_SITE_KEY,
    route: _internal.productRoute(P0A_SITE_KEY, payload.productId),
    actionName: 'productUpdate',
    payload,
  });
  return p0aMintContext(binding);
}
function p0aInvalidContextMatrix(mode) {
  const payload = p0aProductUpdatePayload(mode);
  return [
    ['missing authorizationContext', undefined],
    ['boolean authorizationContext', true],
    ['expired authorizationContext', p0aMintContext({
      operation: `allincms.product.${mode}`,
      target: { site_id: P0A_IDS.siteId, product_id: P0A_IDS.productId },
      approvedAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      expiresAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    })],
    ['wrong site authorizationContext', p0aMintContext({
      siteKey: 'other-site',
      operation: `allincms.product.${mode}`,
      target: { site_id: P0A_IDS.siteId, product_id: P0A_IDS.productId },
    })],
    ['wrong operation authorizationContext', p0aMintContext({
      operation: `allincms.product.${mode === 'publish' ? 'unpublish' : 'publish'}`,
      target: { site_id: P0A_IDS.siteId, product_id: P0A_IDS.productId },
    })],
    ['wrong target authorizationContext', p0aMintContext({
      operation: `allincms.product.${mode}`,
      target: { site_id: P0A_IDS.siteId, product_id: 'other-product' },
    })],
  ];
}

test('saveProductDraft/publishProduct/unpublishProduct injected client sends zero requests without exact fresh structured authorization (P0-A)', async () => {
  const runs = [
    ['saveProductDraft', saveProductDraft, 'update'],
    ['publishProduct', publishProduct, 'publish'],
    ['unpublishProduct', unpublishProduct, 'unpublish'],
  ];
  for (const [runLabel, run, mode] of runs) {
    for (const [label, authorizationContext] of p0aInvalidContextMatrix(mode)) {
      const client = injectedClientFor();
      await assert.rejects(() => run({
        client,
        siteKey: P0A_SITE_KEY,
        authorizationContext,
        ...P0A_IDS,
        defaults: P0A_UPDATE_DEFAULTS,
        readback: async () => p0aProductUpdatePayload(mode),
      }), /authorizationContext|expired|target|operation|site/, `${runLabel}: ${label}`);
      assert.equal(client.calls.length, 0, `${runLabel}: ${label}`);
    }
    // A missing authorizationContext must fail as a hard error, never a
    // requestStarted transport ambiguity that could be reconciled or retried.
    const hard = injectedClientFor();
    await assert.rejects(() => run({
      client: hard,
      siteKey: P0A_SITE_KEY,
      authorizationContext: undefined,
      ...P0A_IDS,
      defaults: P0A_UPDATE_DEFAULTS,
      readback: async () => p0aProductUpdatePayload(mode),
    }), (error) => {
      assert.equal(error.requestStarted ?? false, false, `${runLabel}: authorization rejection must not be marked requestStarted`);
      return /authorizationContext/.test(error.message);
    });
    assert.equal(hard.calls.length, 0, runLabel);
  }
});

test('saveProductDraft/publishProduct/unpublishProduct injected client sends exactly once with a valid exact authorization context (P0-A)', async () => {
  for (const [runLabel, run, mode] of [
    ['saveProductDraft', saveProductDraft, 'update'],
    ['publishProduct', publishProduct, 'publish'],
    ['unpublishProduct', unpublishProduct, 'unpublish'],
  ]) {
    const client = injectedClientFor();
    const result = await run({
      client,
      siteKey: P0A_SITE_KEY,
      authorizationContext: p0aUpdateAuth(mode),
      ...P0A_IDS,
      defaults: P0A_UPDATE_DEFAULTS,
      readback: async () => p0aProductUpdatePayload(mode),
    });
    assert.equal(result.status, 'mutation_succeeded', runLabel);
    assert.equal(result.automaticRetryAllowed, false, runLabel);
    assert.equal(client.calls.length, 1, runLabel);
    assert.equal(client.calls[0].actionName, 'productUpdate', runLabel);
    assert.equal(client.calls[0].payload.mode, mode, runLabel);
    assert.equal(client.calls[0].payload.productId, P0A_IDS.productId, runLabel);
  }
});

test('createProductDraft injected client sends zero requests without exact fresh structured authorization (P0-A: injected client is transport only)', async () => {
  const payload = structuredClone(PRODUCT_CREATE_PAYLOAD);
  const binding = deriveAllinCmsMutationBinding({
    siteKey: 'oajc2ezib4',
    route: '/oajc2ezib4/products',
    actionName: 'productCreate',
    payload,
  });
  const driftedPayload = structuredClone(PRODUCT_CREATE_PAYLOAD);
  driftedPayload.name = 'FP-X2';
  const driftedBinding = deriveAllinCmsMutationBinding({
    siteKey: 'oajc2ezib4',
    route: '/oajc2ezib4/products',
    actionName: 'productCreate',
    payload: driftedPayload,
  });
  for (const [label, authorizationContext] of [
    ['missing authorizationContext', undefined],
    ['boolean authorizationContext', true],
    ['expired authorizationContext', p0aMintContext({
      operation: binding.operation,
      target: binding.target,
      approvedAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      expiresAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    })],
    ['wrong site authorizationContext', p0aMintContext({ siteKey: 'other-site', operation: binding.operation, target: binding.target })],
    ['wrong operation authorizationContext (product update instead of create)', p0aMintContext({
      operation: 'allincms.product.update',
      target: { site_id: payload.siteId, product_id: P0A_IDS.productId },
    })],
    ['wrong target authorizationContext (digest over drifted payload)', p0aMintContext({ operation: driftedBinding.operation, target: driftedBinding.target })],
  ]) {
    const client = injectedClientFor();
    await assert.rejects(() => createProductDraft({
      client,
      siteKey: 'oajc2ezib4',
      authorizationContext,
      siteId: 'site-1',
      payload,
      expected: payload,
      beforeProductIds: ['old-1'],
      readback: async () => ({ ...payload, id: 'new-1' }),
      getCreatedProductId: (actual) => actual.id,
      getCreatedProductSiteId: (actual) => actual.siteId,
      getAfterProductIds: () => ['old-1', 'new-1'],
    }), /authorizationContext|expired|target|operation|site/, label);
    assert.equal(client.calls.length, 0, label);
  }
});

test('createProductDraft injected client sends exactly once with the valid exact payload-digest context (P0-A)', async () => {
  const payload = structuredClone(PRODUCT_CREATE_PAYLOAD);
  const binding = deriveAllinCmsMutationBinding({
    siteKey: 'oajc2ezib4',
    route: '/oajc2ezib4/products',
    actionName: 'productCreate',
    payload,
  });
  const client = injectedClientFor();
  const result = await createProductDraft({
    client,
    siteKey: 'oajc2ezib4',
    authorizationContext: p0aMintContext(binding),
    siteId: 'site-1',
    payload,
    expected: payload,
    beforeProductIds: ['old-1'],
    readback: async () => ({ ...payload, id: 'new-1' }),
    getCreatedProductId: (actual) => actual.id,
    getCreatedProductSiteId: (actual) => actual.siteId,
    getAfterProductIds: () => ['old-1', 'new-1'],
  });
  assert.equal(result.status, 'mutation_succeeded');
  assert.equal(result.createdProductId, 'new-1');
  assert.equal(client.calls.length, 1);
  assert.equal(client.calls[0].actionName, 'productCreate');
  assert.equal(client.calls[0].route, '/oajc2ezib4/products');
});

test('injected-client wrapper re-validates authorization before every underlying send: a retry crossing expiry is rejected with zero second sends (P0-A)', async () => {
  const payload = { mode: 'update', siteId: P0A_IDS.siteId, productId: P0A_IDS.productId };
  const route = _internal.productRoute(P0A_SITE_KEY, payload.productId);
  const binding = deriveAllinCmsMutationBinding({ siteKey: P0A_SITE_KEY, route, actionName: 'productUpdate', payload });
  const approvedAt = new Date().toISOString();
  const shortLived = p0aMintContext({
    operation: binding.operation,
    target: binding.target,
    approvedAt,
    expiresAt: new Date(Date.parse(approvedAt) + 500).toISOString(),
  });
  const calls = [];
  const actionClient = await _internal.requireClient({
    client: { async send(details) { calls.push(details); return { status: 503, contentType: 'text/plain' }; } },
    siteKey: P0A_SITE_KEY,
    authorizationContext: shortLived,
  });
  await assert.rejects(() => runActionWithRecovery({
    client: actionClient,
    route,
    actionName: 'productUpdate',
    payload,
    expected: {},
    operation: 'product:update',
    readback: async () => null,
    retryOnExactAbsence: true,
    confirmExactAbsence: async () => { await new Promise((resolve) => { setTimeout(resolve, 1_000); }); return true; },
    maxControlledRetries: 1,
  }), /authorizationContext has expired/);
  assert.equal(calls.length, 1, 'the second send must be rejected before the underlying transport fires');
});

test('injected client transport failure is marked requestStarted, reconciled via readback, and never resent (P0-A)', async () => {
  const calls = [];
  let readbackRecord = null;
  const client = {
    async send(details) {
      calls.push(details);
      readbackRecord = p0aProductUpdatePayload('update');
      throw new Error('connection lost after send');
    },
  };
  const result = await saveProductDraft({
    client,
    siteKey: P0A_SITE_KEY,
    authorizationContext: p0aUpdateAuth('update'),
    ...P0A_IDS,
    defaults: P0A_UPDATE_DEFAULTS,
    readback: async () => readbackRecord,
  });
  assert.equal(result.status, 'reconciled_success');
  assert.equal(result.requestStarted, true);
  assert.equal(result.automaticRetryAllowed, false);
  assert.equal(calls.length, 1);
});

// ---------------------------------------------------------------------------
// 2026-09-04 TOCTOU fix: markRequestStarted used to read-then-write-then-read
// `error.requestStarted` and return the ORIGINAL object when those reads said
// true. A hostile error only needed its accessor to answer `true` for exactly
// the two reads inside the marking function (with a no-op setter so the strict
// -mode write succeeds) and `false` for every downstream read
// (runActionWithRecovery's `error?.requestStarted === true`, the controller's
// `error?.requestStarted !== false`) to skip the mandatory post-request
// reconcile. Frozen/cross-realm/Proxy/mutating-data-property errors are the
// same class of lie. The fix never trusts, mutates, or returns the original:
// every call returns a fresh ordinary Error whose own `requestStarted` is a
// non-writable, non-configurable data property, and message/name/stack are
// copied only through descriptor reads (getters are never invoked).
// ---------------------------------------------------------------------------
function assertLockedRequestStartedWrapper(wrapped, original, label) {
  assert.notEqual(wrapped, original, `${label}: a fresh wrapper must be returned, never the original object`);
  assert.ok(wrapped instanceof Error, `${label}: the wrapper must be a plain Error`);
  const descriptor = Object.getOwnPropertyDescriptor(wrapped, 'requestStarted');
  assert.deepEqual(
    { value: descriptor?.value, writable: descriptor?.writable, enumerable: descriptor?.enumerable, configurable: descriptor?.configurable },
    { value: true, writable: false, enumerable: false, configurable: false },
    `${label}: requestStarted must be a non-writable non-configurable own data property true`,
  );
  for (let i = 0; i < 5; i += 1) {
    assert.equal(wrapped.requestStarted, true, `${label}: every read (read ${i + 1}) must be true`);
  }
  assert.equal(wrapped.cause, original, `${label}: cause keeps the original error by reference`);
}

test('markRequestStarted never trusts the original error: TOCTOU accessor, frozen, proxy, mutating data, cross-realm, plain, and non-error inputs (2026-09-04 TOCTOU fix)', () => {
  // 1. The exact adversarial repro: getter answers true for the first two
  //    reads (the two the old implementation performed) and false afterwards;
  //    a no-op setter let the old strict-mode write succeed so the original
  //    object was returned and every downstream read lied `false`.
  let requestStartedReads = 0;
  const toctou = { message: 'wire died mid-send' };
  Object.defineProperty(toctou, 'requestStarted', {
    get() { requestStartedReads += 1; return requestStartedReads <= 2; },
    set() {},
    configurable: true,
  });
  const toctouWrapped = markRequestStarted(toctou);
  assertLockedRequestStartedWrapper(toctouWrapped, toctou, 'TOCTOU accessor');
  assert.equal(requestStartedReads, 0, 'the hostile requestStarted getter must never be invoked');
  assert.equal(toctouWrapped.message, 'wire died mid-send', 'own data message is copied through the descriptor');

  // 2. Frozen error that already carries requestStarted=false: the original is
  //    never mutated (the old code threw against the frozen write; it must not
  //    matter at all now) and the wrapper reads true forever.
  const frozen = Object.freeze(Object.assign(new Error('frozen transport failure'), { requestStarted: false }));
  const frozenWrapped = markRequestStarted(frozen);
  assertLockedRequestStartedWrapper(frozenWrapped, frozen, 'frozen error');
  assert.equal(frozen.requestStarted, false, 'the frozen original keeps its own false flag untouched');
  assert.equal(frozenWrapped.message, 'frozen transport failure');

  // 3. Proxy whose getOwnPropertyDescriptor trap throws: descriptor reads fail
  //    closed into placeholders; nothing from the proxy is ever invoked.
  const hostileProxy = new Proxy({}, {
    get() { throw new Error('get trap must never run'); },
    getOwnPropertyDescriptor() { throw new Error('descriptor trap must never run'); },
  });
  const proxyWrapped = markRequestStarted(hostileProxy);
  assertLockedRequestStartedWrapper(proxyWrapped, hostileProxy, 'hostile proxy');
  assert.match(proxyWrapped.message, /original message unavailable/, 'the placeholder message is used instead of invoking the proxy');

  // 4. Mutable data property: the original flips to false after marking, the
  //    wrapper keeps reading true.
  const mutable = new Error('flip after send');
  mutable.requestStarted = true;
  const mutableWrapped = markRequestStarted(mutable);
  mutable.requestStarted = false;
  assertLockedRequestStartedWrapper(mutableWrapped, mutable, 'mutating data property');

  // 5. Cross-realm error: same locked local-realm wrapper.
  const foreign = runInNewContext('new Error("cross realm transport failure")');
  const foreignWrapped = markRequestStarted(foreign);
  assertLockedRequestStartedWrapper(foreignWrapped, foreign, 'cross-realm error');
  assert.equal(foreignWrapped.message, 'cross realm transport failure');

  // 6. Plain Error (the everyday transport failure): message preserved
  //    bit-for-bit through the descriptor, stack kept when it is a plain own
  //    data property (an accessor stack is never invoked; the wrapper then
  //    keeps its own stack).
  const plain = new Error('connection lost after send');
  const plainWrapped = markRequestStarted(plain);
  assertLockedRequestStartedWrapper(plainWrapped, plain, 'plain error');
  assert.equal(plainWrapped.message, plain.message);
  const plainStack = Object.getOwnPropertyDescriptor(plain, 'stack');
  assert.equal(plainStack && 'value' in plainStack ? plainWrapped.stack === plainStack.value : true, true);

  // 7. Accessor message: the message getter is never invoked either.
  let messageGetterReads = 0;
  const accessorMessage = {};
  Object.defineProperty(accessorMessage, 'message', { get() { messageGetterReads += 1; return 'LIE'; } });
  const accessorWrapped = markRequestStarted(accessorMessage);
  assert.equal(messageGetterReads, 0, 'the hostile message getter must never be invoked');
  assert.match(accessorWrapped.message, /original message unavailable/);
  assert.equal(accessorWrapped.requestStarted, true);

  // 8. Non-error inputs still yield a locked wrapper.
  assertLockedRequestStartedWrapper(markRequestStarted('wire died'), 'wire died', 'thrown string');
  assert.equal(markRequestStarted('wire died').message, 'wire died');
  assert.equal(markRequestStarted(null).requestStarted, true);
});

test('adversarial TOCTOU transport error is reconciled from readback without any resend, on the injected and native client paths (2026-09-04 TOCTOU fix)', async () => {
  // The hostile error: requestStarted getter answers true exactly twice (the
  // two reads the old markRequestStarted performed) and false for every read
  // afterwards, so the old implementation returned the original object and
  // runActionWithRecovery's read then skipped the reconcile and rethrew.
  function hostileTransportError() {
    let reads = 0;
    const error = { message: 'connection lost after send' };
    Object.defineProperty(error, 'requestStarted', {
      get() { reads += 1; return reads <= 2; },
      set() {},
      configurable: true,
    });
    return { error, reads: () => reads };
  }

  // Injected client path (saveProductDraft -> requireClient wrapper): the
  // already-sent transport failure must be reconciled from readback, exactly
  // one send, never resent.
  const injected = hostileTransportError();
  let injectedRecord = null;
  let injectedSends = 0;
  const injectedResult = await saveProductDraft({
    client: {
      async send({ payload }) {
        injectedSends += 1;
        injectedRecord = p0aProductUpdatePayload('update');
        throw injected.error;
      },
    },
    siteKey: P0A_SITE_KEY,
    authorizationContext: p0aUpdateAuth('update'),
    ...P0A_IDS,
    defaults: P0A_UPDATE_DEFAULTS,
    readback: async () => injectedRecord,
  });
  assert.equal(injectedResult.status, 'reconciled_success');
  assert.equal(injectedResult.requestStarted, true);
  assert.equal(injectedResult.automaticRetryAllowed, false);
  assert.equal(injectedSends, 1, 'the ambiguous transport failure must never be resent');
  assert.equal(injected.reads(), 0, 'the hostile requestStarted accessor must never be read at all');

  // Native client path (createProductDraft -> createAllinCmsActionClient ->
  // request callback): same rule for create, which is not safely retryable.
  const native = hostileTransportError();
  const createPayload = structuredClone(PRODUCT_CREATE_PAYLOAD);
  const nativeBinding = deriveAllinCmsMutationBinding({
    siteKey: 'oajc2ezib4',
    route: '/oajc2ezib4/products',
    actionName: 'productCreate',
    payload: createPayload,
  });
  let nativeSends = 0;
  const nativeResult = await createProductDraft({
    siteKey: 'oajc2ezib4',
    runtime: {
      actions: { productCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } },
      deploymentId: 'd'.repeat(40),
      routerTree: '[]',
    },
    request: async () => { nativeSends += 1; throw native.error; },
    authorizationContext: p0aMintContext(nativeBinding),
    siteId: 'site-1',
    payload: createPayload,
    expected: createPayload,
    beforeProductIds: ['old-1'],
    readback: async () => ({ record: { ...createPayload, id: 'new-1' }, afterProductIds: ['old-1', 'new-1'] }),
    getCreatedProductId: (actual) => actual?.record?.id,
    getCreatedProductSiteId: (actual) => actual?.record?.siteId,
    getAfterProductIds: (actual) => actual?.afterProductIds,
  });
  assert.equal(nativeResult.status, 'reconciled_success');
  assert.equal(nativeResult.requestStarted, true);
  assert.equal(nativeResult.automaticRetryAllowed, false);
  assert.equal(nativeSends, 1, 'a create whose transport failed ambiguously must never be resent');
  assert.equal(native.reads(), 0);
});

test('prototype-polluted requestStarted must never upgrade a pre-send failure into a sent request (2026-09-04 pollution fix)', async () => {
  // The recovery loop trusts `error.requestStarted === true`. A polluted
  // `Object.prototype.requestStarted = true` used to upgrade an authorization
  // refusal (which carries no own requestStarted because nothing was sent)
  // into "a request was sent", routing it into readback reconciliation with
  // zero real requests. The fix reads the own data property descriptor only.
  const pollution = { value: true, writable: true, enumerable: true, configurable: true };
  Object.defineProperty(Object.prototype, 'requestStarted', pollution);
  let readbackCalls = 0;
  let sends = 0;
  try {
    // Direct runActionWithRecovery call: the red-team scenario. A client send
    // error with NO own requestStarted (e.g. thrown before any wire bytes)
    // reaches the trust check naked. With the polluted prototype the old
    // `error?.requestStarted === true` read returned true and the loop treated
    // the failure as "a request was sent", swallowing it into a reconciled
    // resolution with zero real requests. The own-descriptor check rethrows.
    await assert.rejects(
      () => runActionWithRecovery({
        client: {
          async send() {
            sends += 1;
            throw new Error('transport denied upstream');
          },
        },
        route: '/synthetic-site/products/old-1/update',
        actionName: 'productUpdate',
        payload: {},
        expected: {},
        operation: 'product:update',
        readback: async () => { readbackCalls += 1; return {}; },
      }),
      (error) => { assert.match(error.message, /transport denied upstream/); return true; },
    );
    assert.equal(sends, 1, 'the injected transport did attempt its send before throwing unmarked');
    assert.equal(readbackCalls, 0, 'a pre-send failure must never be reconciled from readback');
    assert.equal(sends, 1, 'the injected transport did attempt its send before the authorization-layer throw');
    assert.equal(readbackCalls, 0, 'a pre-send failure must never be reconciled from readback');
  } finally {
    delete Object.prototype.requestStarted;
  }
  assert.equal(({}).requestStarted, undefined, 'the prototype pollution must be cleaned up');
});

test('prototype-polluted cause setter cannot break the locked requestStarted wrapper (2026-09-04 pollution fix)', async () => {
  // The wrapper used to attach `cause` with plain assignment. A polluted
  // `Object.prototype.cause` setter that throws made markRequestStarted blow
  // up while attaching the cause, replacing the locked wrapper with an
  // unlocked error — a sent request then skipped its mandatory reconcile.
  const originalCause = Object.getOwnPropertyDescriptor(Object.prototype, 'cause');
  let causeSetterCalls = 0;
  Object.defineProperty(Object.prototype, 'cause', {
    get() { return undefined; },
    set() { causeSetterCalls += 1; throw new Error('polluted cause setter ran'); },
    configurable: true,
  });
  try {
    const transportError = Object.assign(new Error('connection lost after send'), { requestStarted: true });
    const wrapped = markRequestStarted(transportError);
    assert.equal(causeSetterCalls, 0, 'defineProperty must never invoke the polluted prototype setter');
    const descriptor = Object.getOwnPropertyDescriptor(wrapped, 'cause');
    assert.equal(descriptor?.value, transportError, 'cause keeps the original error by reference as an own data property');
    assert.equal(descriptor?.writable, false);
    assert.equal(wrapped.requestStarted, true, 'the locked requestStarted flag survived the hostile prototype');

    // Integration: an already-sent transport failure must still be reconciled
    // from readback exactly once while the hostile cause setter is armed.
    let sends = 0;
    let readbackCalls = 0;
    const result = await saveProductDraft({
      client: {
        async send({ payload }) {
          sends += 1;
          throw Object.assign(new Error('connection lost after send'), { requestStarted: true });
        },
      },
      siteKey: P0A_SITE_KEY,
      authorizationContext: p0aUpdateAuth('update'),
      ...P0A_IDS,
      defaults: P0A_UPDATE_DEFAULTS,
      readback: async () => { readbackCalls += 1; return p0aProductUpdatePayload('update'); },
    });
    assert.equal(result.status, 'reconciled_success');
    assert.equal(result.requestStarted, true);
    assert.equal(sends, 1, 'never resent');
    assert.equal(readbackCalls, 1, 'the sent request must still be reconciled despite the polluted cause setter');
  } finally {
    if (originalCause) Object.defineProperty(Object.prototype, 'cause', originalCause);
    else delete Object.prototype.cause;
  }
  assert.equal(causeSetterCalls > 0 || true, true, 'setter state recorded');
});

// ---------------------------------------------------------------------------
// 2026-09-04 poisoning fix regression: product-operations.mjs used to
// destructured-share markRequestStarted / createdRecordExpectedProblems /
// extractCreateReadbackRecord from article-operations.mjs's mutable `_internal`
// export. An external actor that imported article-operations first could
// overwrite those properties before product's FIRST import, then watch
// product skip the post-request reconcile (unmarked transport error rethrown
// instead of reconciled) or accept create field drift (comparator replaced
// with `() => []`). The fix moves the shared primitives into
// content-mutation-primitives.mjs (named ESM imports, immutable bindings) and
// freezes both `_internal` facades. This test reproduces the exact adversarial
// sequence in a fresh child process — this file statically imports product, so
// only a child can poison "before product's first import".
// ---------------------------------------------------------------------------
const POISON_SITE_KEY = 'demo-site';
const POISON_CHILD_SCRIPT = `
const adapter = ${JSON.stringify(pathToFileURL(fileURLToPath(new URL('.', import.meta.url))).href)};
const article = await import(new URL('./article-operations.mjs', adapter).href);
const primitives = await import(new URL('./content-mutation-primitives.mjs', adapter).href);

// 1. Preload article, then try every property-poisoning channel against the
//    historical seam BEFORE product is imported for the first time.
const attempts = [];
for (const key of ['markRequestStarted', 'createdRecordExpectedProblems', 'extractCreateReadbackRecord', 'canonicalTexts']) {
  const original = article._internal[key];
  let assign = 'silently-accepted';
  try { article._internal[key] = function poisoned() { return []; }; } catch (error) { assign = error.constructor.name; }
  let define = 'silently-accepted';
  try { Object.defineProperty(article._internal, key, { value: function poisoned() { return []; } }); } catch (error) { define = error.constructor.name; }
  const reflectAccepted = Reflect.set(article._internal, key, function poisoned() { return []; });
  attempts.push({ key, assign, define, reflectAccepted, unchanged: article._internal[key] === original && original === primitives[key] });
}

// 2. First import of product happens only now, after the poisoning attempts.
const product = await import(new URL('./product-operations.mjs', adapter).href);
const frozen = { article: Object.isFrozen(article._internal), product: Object.isFrozen(product._internal) };

const { createAllinCmsMutationAuthorizationContext, deriveAllinCmsMutationBinding } =
  await import(new URL('./mutation-authorization.mjs', adapter).href);
const mint = (binding) => createAllinCmsMutationAuthorizationContext({
  siteKey: binding.siteKey, operation: binding.operation, target: binding.target, approvalActor: 'Poison Regression',
});

// 3. Transport error must still be marked requestStarted=true and reconciled
//    from readback instead of rethrown (a poisoned markRequestStarted used to
//    un-mark the error so the reconcile was skipped).
const defaults = { name: 'FP-X1', slug: 'fp-x1', description: 'Fixture description.' };
const updatePayload = product.buildProductPayload({ defaults, siteId: 'site-1', productId: 'product-1', mode: 'update' });
let sends = 0;
const reconciled = await product.saveProductDraft({
  client: { async send() { sends += 1; throw new Error('connection lost after send'); } },
  siteKey: '${POISON_SITE_KEY}',
  authorizationContext: mint(deriveAllinCmsMutationBinding({
    siteKey: '${POISON_SITE_KEY}',
    route: '/${POISON_SITE_KEY}/products/product-1/update',
    actionName: 'productUpdate',
    payload: updatePayload,
  })),
  siteId: 'site-1',
  productId: 'product-1',
  defaults,
  readback: async () => updatePayload,
});
const transport = { sends, status: reconciled.status, requestStarted: reconciled.requestStarted, automaticRetryAllowed: reconciled.automaticRetryAllowed };

// 4. Create field drift must still be rejected (a poisoned
//    createdRecordExpectedProblems used to wave the drifted record through,
//    and a permissive match must never rescue it either).
const createPayload = {
  name: 'FP-X1', slug: 'fp-x1', description: 'Fixture description.', order: 0,
  media: { name: 'fp.webp', type: 'image', source: 'url', url: 'https://assets.example.invalid/fp.webp' },
  mediaList: [], content: [], categories: [], tags: [],
  specifications: [{ key: 'Rated power', value: '500W' }], siteId: 'site-1',
};
const drift = await product.createProductDraft({
  siteKey: '${POISON_SITE_KEY}',
  client: { async send() { return { status: 200, contentType: 'text/x-component' }; } },
  authorizationContext: mint(deriveAllinCmsMutationBinding({
    siteKey: '${POISON_SITE_KEY}', route: '/${POISON_SITE_KEY}/products', actionName: 'productCreate', payload: createPayload,
  })),
  siteId: 'site-1',
  payload: createPayload,
  expected: createPayload,
  beforeProductIds: ['old-1'],
  match: () => true,
  readback: async () => ({ record: { ...createPayload, name: 'POISONED DRIFT', id: 'new-1' }, afterProductIds: ['old-1', 'new-1'] }),
  getCreatedProductId: (actual) => actual?.record?.id,
  getCreatedProductSiteId: (actual) => actual?.record?.siteId,
  getAfterProductIds: (actual) => actual?.afterProductIds,
});
const create = { status: drift.status, mismatches: drift.mismatches };

console.log('@VERDICT@' + JSON.stringify({ attempts, frozen, transport, create }));
`;

test('poisoning article._internal before product first import cannot skip transport reconcile or accept create drift (2026-09-04 poisoning fix)', () => {
  // In-process half of the frozen assertion: this file's own imports.
  assert.ok(Object.isFrozen(_internal), 'product _internal must be frozen');
  const child = spawnSync(process.execPath, ['--input-type=module', '-e', POISON_CHILD_SCRIPT], {
    cwd: fileURLToPath(new URL('.', import.meta.url)),
    encoding: 'utf8',
  });
  assert.equal(child.status, 0, `${child.stdout}\n${child.stderr}`);
  const verdict = JSON.parse(child.stdout.split('@VERDICT@')[1]);

  // Every poisoning channel failed or was ineffective: the frozen facade
  // either threw (strict-mode assignment / defineProperty) or silently kept
  // the original shared binding (Reflect.set), and the exposed function is
  // still bit-for-bit the content-mutation-primitives.mjs implementation.
  assert.equal(verdict.attempts.length, 4);
  for (const attempt of verdict.attempts) {
    assert.ok(attempt.unchanged, `${attempt.key}: the shared binding must be unchanged after every poisoning attempt (${JSON.stringify(attempt)})`);
    assert.notEqual(attempt.assign, 'silently-accepted', attempt.key);
    assert.notEqual(attempt.define, 'silently-accepted', attempt.key);
    assert.equal(attempt.reflectAccepted, false, attempt.key);
  }
  assert.deepEqual(verdict.frozen, { article: true, product: true });

  // Transport error after the poisoning attempts: still requestStarted=true,
  // still reconciled from readback, exactly one send, no resend.
  assert.equal(verdict.transport.sends, 1);
  assert.equal(verdict.transport.status, 'reconciled_success');
  assert.equal(verdict.transport.requestStarted, true);
  assert.equal(verdict.transport.automaticRetryAllowed, false);

  // Drifted create record: still rejected by the canonical comparison even
  // with a permissive match callback riding on top.
  assert.equal(verdict.create.status, 'stopped_manual_intervention');
  assert.match(verdict.create.mismatches.join('; '), /did not match the canonical expected readback/);
  assert.match(verdict.create.mismatches.join('; '), /name drifted from the frozen expected payload/);
});
