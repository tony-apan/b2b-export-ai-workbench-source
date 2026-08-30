import test from 'node:test';
import assert from 'node:assert/strict';
import { buildProductPayload, createProductDraft, _internal } from './product-operations.mjs';
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

test('createProductDraft verifies exactly one before/after product ID delta', async () => {
  const runtime = {
    actions: {
      productCreate: { actionId: 'a'.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) },
    },
    deploymentId: 'd'.repeat(40),
    routerTree: '[]',
  };
  const request = async () => ({ status: 200, ok: true, contentType: 'text/x-component', headers: { 'content-type': 'text/x-component' } });
  const binding = deriveAllinCmsMutationBinding({
    siteKey: 'oajc2ezib4',
    route: '/oajc2ezib4/products',
    actionName: 'productCreate',
    payload: { siteId: 'site-1' },
  });
  const authorizationContext = createAllinCmsMutationAuthorizationContext({
    siteKey: binding.siteKey,
    operation: binding.operation,
    target: binding.target,
    approvalActor: 'Test Reviewer',
  });
  const result = await createProductDraft({
    siteKey: 'oajc2ezib4',
    runtime,
    request,
    authorizationContext,
    siteId: 'site-1',
    beforeProductIds: ['old-1'],
    readback: async () => ({ id: 'new-1', siteId: 'site-1' }),
    getCreatedProductId: (actual) => actual.id,
    getCreatedProductSiteId: (actual) => actual.siteId,
    getAfterProductIds: () => ['old-1', 'new-1'],
  });
  assert.equal(result.createdProductId, 'new-1');
  assert.equal(result.status, 'mutation_succeeded');
});
