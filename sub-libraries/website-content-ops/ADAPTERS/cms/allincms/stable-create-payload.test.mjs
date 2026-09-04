import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { runInNewContext } from 'node:vm';
import {
  ARTICLE_CREATE_CONTRACT_FIELDS,
  PRODUCT_CREATE_CONTRACT_FIELDS,
  canonicalStableCreateText,
  captureStableReadback,
  prepareStableCreatePayload,
} from './content-mutation-primitives.mjs';
import { createAllinCmsActionClient, createPostDraft, runActionWithRecovery } from './article-operations.mjs';
import { createProductDraft } from './product-operations.mjs';
import {
  createAllinCmsMutationAuthorizationContext,
  deriveAllinCmsMutationBinding,
} from './mutation-authorization.mjs';
import { allinCmsOperationAuthorization, createAllinCmsPlanHandlerSet } from './content-plan-host-driver.mjs';

// ---------------------------------------------------------------------------
// 2026-09-04 stable create payload B1+B2 adversarial matrix.
//
// B1: article/product canonical create flows from caller input through ONE
// stable JSON snapshot and ONE immutable payloadText. prepareStableCreatePayload
// is the single machine truth shared by the bottom create functions and the
// host driver; re-preparing a branded frozen snapshot returns the identical
// object and text.
//
// B2: runActionWithRecovery / the action client chain carry the same
// payloadText, the native wire body is exactly `[payloadText]`, retries reuse
// the same string, the authorization create digest hashes the exact UTF-8
// payloadText bytes, and readbacks are captured as stable data before the
// canonical comparison and every ID getter read them.
//
// The formal runtime profile stays frozen (runtime-test-plan.json
// formalProfile); this suite is dev-suite only.
// ---------------------------------------------------------------------------

const SITE_KEY = 'demo-site';
const SITE_ID = 'site-1';
const URL_MEDIA = Object.freeze({
  name: 'synthetic.webp', alt: null, type: 'image', source: 'url',
  url: 'https://assets.example.invalid/synthetic.webp',
});
const OSS_MEDIA = Object.freeze({
  name: 'cover.webp', alt: '封面', type: 'image', source: 'oss',
  path: 'site/cover.webp', size: 42, mimeType: 'image/webp',
});
const ARTICLE_PAYLOAD = Object.freeze({
  title: 'Stable Guide', slug: 'stable-guide', excerpt: 'Fixture excerpt.', order: 2,
  coverImage: null, categories: ['cat-1'], tags: ['tag-1'],
  content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
  siteId: SITE_ID,
});
const PRODUCT_PAYLOAD = Object.freeze({
  name: 'FP-X1', slug: 'fp-x1', description: 'Fixture description.', order: 0,
  media: URL_MEDIA, mediaList: [],
  content: [{ type: 'p', children: [{ text: '产品正文' }] }],
  categories: ['cat-1'], tags: ['tag-1'], specifications: [{ key: 'Rated power', value: '500W' }],
  siteId: SITE_ID,
});

function sha256Hex(value) {
  return createHash('sha256').update(value).digest('hex');
}

function createRuntime(actionName, actionIdSeed = 'a') {
  return {
    routerTree: '[]', deploymentId: 'd'.repeat(40),
    actions: { [actionName]: { actionId: actionIdSeed.repeat(42), routerTree: '[]', deploymentId: 'd'.repeat(40) } },
  };
}

function createRoute(kind, siteKey = SITE_KEY) {
  return kind === 'article' ? `/${siteKey}/posts` : `/${siteKey}/products`;
}

function createActionName(kind) {
  return kind === 'article' ? 'postCreate' : 'productCreate';
}

function mintCreateAuth(kind, payload, siteKey = SITE_KEY) {
  const prepared = prepareStableCreatePayload(kind, payload, payload.siteId ?? SITE_ID);
  const binding = deriveAllinCmsMutationBinding({
    siteKey,
    route: createRoute(kind, siteKey),
    actionName: createActionName(kind),
    payload: prepared.snapshot,
    payloadText: prepared.payloadText,
  });
  return createAllinCmsMutationAuthorizationContext({
    siteKey: binding.siteKey, operation: binding.operation, target: binding.target,
    approvalActor: 'Stable Payload Fixture',
  });
}

// Counting host transport: every refusal below must keep sends at exactly 0
// (nothing reached the wire), and single-send paths must stay at 1.
function countingTransport() {
  const sent = [];
  const request = async (details) => {
    sent.push(details);
    return { status: 200, ok: true, contentType: 'text/x-component' };
  };
  return { sent, request };
}

// A valid-fixture authorization context for zero-send refusal paths: the
// refusal throws inside prepareStableCreatePayload before any send, so the
// context is never validated against the broken payload. Minting the context
// from the broken payload would itself throw inside this helper.
const VALID_ARTICLE_AUTH = mintCreateAuth('article', structuredClone(ARTICLE_PAYLOAD));
const VALID_PRODUCT_AUTH = mintCreateAuth('product', structuredClone(PRODUCT_PAYLOAD));

function articleDraftOptions({ payload, auth = VALID_ARTICLE_AUTH, overrides = {} } = {}) {
  const { sent, request } = countingTransport();
  return {
    options: {
      siteKey: SITE_KEY,
      runtime: createRuntime('postCreate'),
      request,
      authorizationContext: auth,
      siteId: SITE_ID,
      payload,
      expected: payload,
      beforePostIds: ['post-1'],
      readback: async () => ({
        record: { ...prepareStableCreatePayload('article', structuredClone(ARTICLE_PAYLOAD), SITE_ID).snapshot, id: 'post-new-1' },
        afterPostIds: ['post-1', 'post-new-1'],
      }),
      getCreatedPostId: (actual) => actual?.record?.id,
      getCreatedPostSiteId: (actual) => actual?.record?.siteId,
      getAfterPostIds: (actual) => actual?.afterPostIds,
      editorReopen: async (postId) => ({ status: 200, authenticated: true, healthy: true, postId }),
      maxControlledRetries: 0,
      ...overrides,
    },
    sent,
  };
}

function productDraftOptions({ payload, auth = VALID_PRODUCT_AUTH, overrides = {} } = {}) {
  const { sent, request } = countingTransport();
  return {
    options: {
      siteKey: SITE_KEY,
      runtime: createRuntime('productCreate', 'b'),
      request,
      authorizationContext: auth,
      siteId: SITE_ID,
      payload,
      expected: payload,
      beforeProductIds: ['prd-1'],
      readback: async () => ({
        record: { ...prepareStableCreatePayload('product', structuredClone(PRODUCT_PAYLOAD), SITE_ID).snapshot, id: 'prd-new-1' },
        afterProductIds: ['prd-1', 'prd-new-1'],
      }),
      getCreatedProductId: (actual) => actual?.record?.id,
      getCreatedProductSiteId: (actual) => actual?.record?.siteId,
      getAfterProductIds: (actual) => actual?.afterProductIds,
      maxControlledRetries: 0,
      ...overrides,
    },
    sent,
  };
}

function draftRunnerFor(kind) {
  return kind === 'article' ? createPostDraft : createProductDraft;
}

function draftOptionsFor(kind, args) {
  return kind === 'article' ? articleDraftOptions(args) : productDraftOptions(args);
}

// ---------------------------------------------------------------------------
// B1 unit matrix: snapshot shape, branding, idempotent re-prepare.
// ---------------------------------------------------------------------------

test('prepareStableCreatePayload produces a deep-frozen branded snapshot with canonical payloadText and returns the identical object on re-prepare', () => {
  for (const [kind, fixture, contractFields] of [
    ['article', ARTICLE_PAYLOAD, ARTICLE_CREATE_CONTRACT_FIELDS],
    ['product', PRODUCT_PAYLOAD, PRODUCT_CREATE_CONTRACT_FIELDS],
  ]) {
    const payload = structuredClone(fixture);
    const { snapshot, payloadText } = prepareStableCreatePayload(kind, payload, SITE_ID);
    assert.deepEqual(Object.keys(snapshot).sort(), [...contractFields, 'siteId'].sort(), kind);
    assert.ok(Object.isFrozen(snapshot), kind);
    assert.ok(Object.isFrozen(snapshot.content), `${kind}: nested values are frozen too`);
    assert.ok(Object.isFrozen(kind === 'article' ? snapshot.coverImage ?? snapshot : snapshot.media), kind);
    assert.equal(payloadText, canonicalStableCreateText(snapshot), `${kind}: payloadText is the canonical serialization of the snapshot`);
    // Re-prepare of the branded frozen snapshot: same object, same text — the
    // bottom layer can never rebuild a second, differently-semantic payload.
    const again = prepareStableCreatePayload(kind, snapshot, SITE_ID);
    assert.equal(again.snapshot, snapshot, `${kind}: idempotent re-prepare returns the same object`);
    assert.equal(again.payloadText, payloadText, `${kind}: idempotent re-prepare returns the same text`);
    // Cross-kind re-prepare of a branded snapshot is refused.
    assert.throws(() => prepareStableCreatePayload(kind === 'article' ? 'product' : 'article', snapshot, SITE_ID), /already a prepared frozen/, kind);
    // A different siteId on the branded path is refused.
    assert.throws(() => prepareStableCreatePayload(kind, snapshot, 'other-site'), /siteId/, kind);
    // Input key order never matters: the canonical text is order-insensitive.
    const reordered = {};
    for (const key of Object.keys(payload).reverse()) reordered[key] = structuredClone(payload[key]);
    assert.equal(prepareStableCreatePayload(kind, reordered, SITE_ID).payloadText, payloadText, `${kind}: reordered input serializes identically`);
    // A plain clone re-prepares to the same semantics (equal text) but is a
    // fresh object — the brand is identity-bound, not value-bound.
    const cloned = prepareStableCreatePayload(kind, structuredClone(payload), SITE_ID);
    assert.equal(cloned.payloadText, payloadText, kind);
    assert.notEqual(cloned.snapshot, snapshot, kind);
  }
});

test('prepareStableCreatePayload refuses missing contract fields (8 article / 10 product) before any request', async () => {
  for (const [kind, fixture, contractFields] of [
    ['article', ARTICLE_PAYLOAD, ARTICLE_CREATE_CONTRACT_FIELDS],
    ['product', PRODUCT_PAYLOAD, PRODUCT_CREATE_CONTRACT_FIELDS],
  ]) {
    const runner = draftRunnerFor(kind);
    for (const field of contractFields) {
      const payload = structuredClone(fixture);
      delete payload[field];
      assert.throws(() => prepareStableCreatePayload(kind, payload, SITE_ID), new RegExp(`missing the contract field.*${field}`), `${kind}:${field}`);
      const { options, sent } = draftOptionsFor(kind, { payload });
      await assert.rejects(() => runner(options), /missing the contract field/, `${kind}:${field}`);
      assert.equal(sent.length, 0, `${kind}:${field}: zero requests`);
    }
  }
});

test('prepareStableCreatePayload refuses wrong article field types before any request', () => {
  const cases = [
    ['title', ['', '   ', 42, null, true], /title must be a non-empty string/],
    ['slug', ['', 42, null], /slug must be a non-empty string/],
    ['excerpt', [7, null, [], {}], /excerpt must be a string/],
    ['order', [1.5, '2', true, null], /order must be an integer/],
    ['categories', ['cat-1', [1], [''], ['cat-1', ' cat-1'], [null], 42], /categories/],
    ['tags', [['tag-1', 'tag-1 '], 'tag-1'], /tags/],
    ['content', ['x', ['x'], [42], [{}], [{ type: '', children: [] }], [{ type: 'p', children: 'x' }], [{ type: 'p', children: [], id: '' }], [{ type: 'p', children: [], id: 5 }]], /content/],
  ];
  for (const [field, badValues, pattern] of cases) {
    for (const badValue of badValues) {
      const payload = structuredClone(ARTICLE_PAYLOAD);
      payload[field] = badValue;
      assert.throws(() => prepareStableCreatePayload('article', payload, SITE_ID), pattern, `${field}: ${String(badValue)}`);
    }
  }
  // Duplicate Slate node ids anywhere in the tree are refused.
  const duplicateIds = structuredClone(ARTICLE_PAYLOAD);
  duplicateIds.content[0].children.push({ text: 'second', id: 'node-1' });
  assert.throws(() => prepareStableCreatePayload('article', duplicateIds, SITE_ID), /duplicates the Slate node id node-1/);
});

test('prepareStableCreatePayload refuses wrong article coverImage, product media/mediaList, and specification shapes before any request', () => {
  const badMediaValues = [
    [5, /must be a flat URL or OSS media object/],
    ['x', /must be a flat URL or OSS media object/],
    [[], /must be a flat URL or OSS media object/],
    [{ type: 'image', value: { ...URL_MEDIA } }, /refused on the create write path/],
    [{ ...URL_MEDIA, name: '' }, /\.name must be a non-empty string/],
    [{ ...URL_MEDIA, type: 'video' }, /\.type must be exactly 'image'/],
    [{ ...URL_MEDIA, size: 42 }, /must not carry the OSS-only field size/],
    [{ ...URL_MEDIA, path: 'site/x.webp' }, /must not carry the OSS-only field path/],
    [{ ...URL_MEDIA, mimeType: 'image/webp' }, /must not carry the OSS-only field mimeType/],
    [{ ...URL_MEDIA, url: 'ftp://assets.example.invalid/synthetic.webp' }, /absolute http:\/\/ or https:\/\//],
    [{ ...URL_MEDIA, url: '/relative/path.webp' }, /absolute http:\/\/ or https:\/\//],
    [{ ...URL_MEDIA, extra: 1 }, /unknown media field extra/],
    [{ ...URL_MEDIA, alt: 7 }, /alt must be a string or null/],
    [{ ...OSS_MEDIA, url: 'https://assets.example.invalid/x.webp' }, /must not carry the URL-only field url/],
    [{ ...OSS_MEDIA, path: '' }, /\.path must be a non-empty string/],
    [{ ...OSS_MEDIA, size: -1 }, /size must be a non-negative integer/],
    [{ ...OSS_MEDIA, size: 1.5 }, /size must be a non-negative integer/],
    [{ ...OSS_MEDIA, mimeType: '' }, /mimeType must be a non-empty string/],
  ];
  for (const [badValue, pattern] of badMediaValues) {
    const articlePayload = structuredClone(ARTICLE_PAYLOAD);
    articlePayload.coverImage = structuredClone(badValue);
    assert.throws(() => prepareStableCreatePayload('article', articlePayload, SITE_ID), pattern, `article cover: ${JSON.stringify(badValue)}`);
    const productPayload = structuredClone(PRODUCT_PAYLOAD);
    productPayload.media = structuredClone(badValue);
    assert.throws(() => prepareStableCreatePayload('product', productPayload, SITE_ID), /media/, `product media: ${JSON.stringify(badValue)}`);
  }
  // Product media is non-null flat URL/OSS only; the legacy string-id wrapper
  // and null are both write-refused.
  for (const [badValue, pattern] of [
    [null, /media must be a non-null flat URL or OSS media object/],
    [{ type: 'image', value: '00000000000000000000000a' }, /refused on the create write path/],
  ]) {
    const productPayload = structuredClone(PRODUCT_PAYLOAD);
    productPayload.media = badValue;
    assert.throws(() => prepareStableCreatePayload('product', productPayload, SITE_ID), pattern, JSON.stringify(badValue));
  }
  // mediaList is a dense array of the same flat union.
  for (const [badValue, pattern] of [
    ['x', /mediaList must be a dense array/],
    [[null], /mediaList\[0\] must be a non-null flat URL or OSS media object/],
    [[{ type: 'image', value: { ...URL_MEDIA } }], /refused on the create write path/],
    [[{ ...URL_MEDIA, size: 3 }], /must not carry the OSS-only field size/],
  ]) {
    const productPayload = structuredClone(PRODUCT_PAYLOAD);
    productPayload.mediaList = structuredClone(badValue);
    assert.throws(() => prepareStableCreatePayload('product', productPayload, SITE_ID), pattern, JSON.stringify(badValue));
  }
  // specification rows own exactly {key, value}, both non-empty strings, value <= 200.
  for (const [badValue, pattern] of [
    ['x', /specifications must be a dense array/],
    [[null], /specifications\[0\] must be an object/],
    [[{ key: 'k' }], /specifications\[0\] must own exactly the fields key and value/],
    [[{ value: 'v' }], /specifications\[0\] must own exactly the fields key and value/],
    [[{ key: 'k', value: 'v', unit: 'W' }], /specifications\[0\] must own exactly the fields key and value/],
    [[{ key: '', value: 'v' }], /specifications\[0\]\.key must be a non-empty string/],
    [[{ key: 'k', value: '' }], /specifications\[0\]\.value must be a non-empty string/],
    [[{ key: 'k', value: 42 }], /specifications\[0\]\.value must be a non-empty string/],
    [[{ key: 'k', value: 'x'.repeat(201) }], /at most 200 characters/],
  ]) {
    const productPayload = structuredClone(PRODUCT_PAYLOAD);
    productPayload.specifications = structuredClone(badValue);
    assert.throws(() => prepareStableCreatePayload('product', productPayload, SITE_ID), pattern, JSON.stringify(badValue));
  }
  // Wrong product name/slug/description/order types mirror the article rules.
  for (const [field, badValue] of [['name', ''], ['slug', 42], ['description', '   '], ['order', 0.5]]) {
    const productPayload = structuredClone(PRODUCT_PAYLOAD);
    productPayload[field] = badValue;
    assert.throws(() => prepareStableCreatePayload('product', productPayload, SITE_ID), new RegExp(`${field}`), field);
  }
});

test('bottom-layer create keeps the whole field/type matrix a zero-send refusal (representative sample)', async () => {
  const articleCases = [
    ['title', ''], ['excerpt', 42], ['order', 1.5], ['categories', 'cat-1'],
    ['content', 'not-an-array'], ['coverImage', 5],
  ];
  for (const [field, badValue] of articleCases) {
    const payload = structuredClone(ARTICLE_PAYLOAD);
    payload[field] = badValue;
    const { options, sent } = articleDraftOptions({ payload });
    await assert.rejects(() => createPostDraft(options), /must be/, `${field}: ${String(badValue)}`);
    assert.equal(sent.length, 0, field);
  }
  const productCases = [
    ['media', null], ['media', { type: 'image', value: { ...URL_MEDIA } }],
    ['mediaList', [null]], ['specifications', [{ key: 'k' }]],
  ];
  for (const [field, badValue] of productCases) {
    const payload = structuredClone(PRODUCT_PAYLOAD);
    payload[field] = badValue;
    const { options, sent } = productDraftOptions({ payload });
    await assert.rejects(() => createProductDraft(options), /must be|refused|exactly the fields/, `${field}`);
    assert.equal(sent.length, 0, field);
  }
});

test('prepareStableCreatePayload refuses extra fields, siteId conflicts, and junk payload shapes before any request', async () => {
  for (const [kind, fixture] of [['article', ARTICLE_PAYLOAD], ['product', PRODUCT_PAYLOAD]]) {
    const runner = draftRunnerFor(kind);
    for (const extra of kind === 'article' ? ['mode', 'postId', 'extraField'] : ['productId', 'mode', 'extraField']) {
      const payload = structuredClone(fixture);
      payload[extra] = 'x';
      assert.throws(() => prepareStableCreatePayload(kind, payload, SITE_ID), /unknown extra field/, `${kind}:${extra}`);
      const { options, sent } = draftOptionsFor(kind, { payload });
      await assert.rejects(() => runner(options), /unknown extra field/, `${kind}:${extra}`);
      assert.equal(sent.length, 0, `${kind}:${extra}: zero requests`);
    }
    const conflicting = structuredClone(fixture);
    conflicting.siteId = 'other-site';
    assert.throws(() => prepareStableCreatePayload(kind, conflicting, SITE_ID), /siteId/, kind);
    for (const junk of [null, 'x', 42, true, ['array']]) {
      assert.throws(() => prepareStableCreatePayload(kind, junk, SITE_ID), /must be a non-array object/, `${kind}: ${String(junk)}`);
    }
  }
  class ExoticPayload {}
  assert.throws(() => prepareStableCreatePayload('article', new ExoticPayload(), SITE_ID), /plain object/);
  assert.throws(() => prepareStableCreatePayload('post', structuredClone(ARTICLE_PAYLOAD), SITE_ID), /kind must be 'article' or 'product'/);
  assert.throws(() => prepareStableCreatePayload('article', structuredClone(ARTICLE_PAYLOAD), ''), /siteId must be a non-empty string/);
  assert.throws(() => prepareStableCreatePayload('article', structuredClone(ARTICLE_PAYLOAD), 42), /siteId must be a non-empty string/);
});

// ---------------------------------------------------------------------------
// B1 exotic-value matrix: everything JSON cannot represent is refused
// wherever it hides in the payload graph.
// ---------------------------------------------------------------------------

function exoticValues() {
  const cyclic = { name: 'cycle' };
  cyclic.self = cyclic;
  const symbolKeyed = { ok: true };
  symbolKeyed[Symbol('hidden')] = 'value';
  const nonEnumerable = { ok: true };
  Object.defineProperty(nonEnumerable, 'secret', { value: 'x', enumerable: false, writable: true, configurable: true });
  const accessor = { ok: true };
  Object.defineProperty(accessor, 'late', { get() { return 'lie'; }, enumerable: true, configurable: true });
  const sparse = ['a', 'b'];
  delete sparse[0];
  const extraKeyArray = ['a'];
  extraKeyArray.surprise = 0;
  return [
    ['undefined', undefined],
    ['function', () => {}],
    ['symbol value', Symbol('sym')],
    ['bigint', 10n],
    ['NaN', NaN],
    ['Infinity', Infinity],
    ['negative zero', -0],
    ['Date', new Date('2026-09-04T00:00:00.000Z')],
    ['Map', new Map([['a', 1]])],
    ['Set', new Set(['a'])],
    ['Error', new Error('boom')],
    ['RegExp', /pattern/],
    ['typed array', new Uint8Array([1, 2, 3])],
    ['class instance', new (class Media {})()],
    ['cycle', cyclic],
    ['symbol key', symbolKeyed],
    ['non-enumerable own property', nonEnumerable],
    ['accessor property', accessor],
    ['sparse array', sparse],
    ['array with extra own key', extraKeyArray],
  ];
}

test('every exotic value is refused wherever it appears in the article/product payload graph', () => {
  for (const [label, exotic] of exoticValues()) {
    // Nested inside article content children.
    const articleContent = structuredClone(ARTICLE_PAYLOAD);
    articleContent.content[0].children.push(exotic);
    assert.throws(() => prepareStableCreatePayload('article', articleContent, SITE_ID), /not stable plain data/, `content:${label}`);
    // Inside a product specification row.
    const productSpec = structuredClone(PRODUCT_PAYLOAD);
    productSpec.specifications[0].nested = exotic;
    assert.throws(() => prepareStableCreatePayload('product', productSpec, SITE_ID), /not stable plain data/, `spec:${label}`);
    // Inside coverImage / media as an extra nested value.
    const articleCover = structuredClone(ARTICLE_PAYLOAD);
    articleCover.coverImage = { ...URL_MEDIA, nested: exotic };
    assert.throws(() => prepareStableCreatePayload('article', articleCover, SITE_ID), /not stable plain data|unknown media field/, `cover:${label}`);
    // Directly in a taxonomy slot.
    const taxonomy = structuredClone(ARTICLE_PAYLOAD);
    taxonomy.categories = ['cat-1', exotic];
    assert.throws(() => prepareStableCreatePayload('article', taxonomy, SITE_ID), /not stable plain data/, `taxonomy:${label}`);
  }
  // Proxy traps that throw fail closed during the synchronous copy.
  const throwingOwnKeys = new Proxy({}, { ownKeys() { throw new Error('ownKeys trap'); } });
  const throwingDescriptor = new Proxy({}, {
    ownKeys: () => ['title'],
    getOwnPropertyDescriptor() { throw new Error('descriptor trap'); },
  });
  for (const [label, proxyValue] of [['ownKeys trap', throwingOwnKeys], ['descriptor trap', throwingDescriptor]]) {
    const payload = structuredClone(ARTICLE_PAYLOAD);
    payload.content = [proxyValue];
    assert.throws(() => prepareStableCreatePayload('article', payload, SITE_ID), /not stable plain data/, label);
  }
  // Accessor payloads are refused without the getter ever running.
  let getterReads = 0;
  const accessorPayload = structuredClone(ARTICLE_PAYLOAD);
  Object.defineProperty(accessorPayload, 'title', {
    get() { getterReads += 1; return 'Stable Guide'; },
    enumerable: true, configurable: true,
  });
  assert.throws(() => prepareStableCreatePayload('article', accessorPayload, SITE_ID), /accessor property/);
  assert.equal(getterReads, 0, 'the hostile title getter must never be invoked');
  // Cross-realm objects are refused like same-realm exotics.
  const foreign = runInNewContext('({ text: "foreign" })');
  const foreignPayload = structuredClone(ARTICLE_PAYLOAD);
  foreignPayload.content[0].children.push(foreign);
  assert.throws(() => prepareStableCreatePayload('article', foreignPayload, SITE_ID), /not stable plain data/, 'cross-realm');
});

test('bottom-layer create refuses unstable payloads with zero sends (exotic sample through createPostDraft)', async () => {
  for (const [label, exotic] of [['Date', new Date()], ['accessor payload', null], ['Map', new Map()]]) {
    const payload = structuredClone(ARTICLE_PAYLOAD);
    if (label === 'accessor payload') {
      Object.defineProperty(payload, 'title', { get() { return 'Stable Guide'; }, enumerable: true, configurable: true });
    } else {
      payload.content[0].children.push(exotic);
    }
    const { options, sent } = articleDraftOptions({ payload });
    await assert.rejects(() => createPostDraft(options), /not stable plain data/, label);
    assert.equal(sent.length, 0, label);
  }
});

test('captureStableReadback copies plain data once, isolates later source mutation, and refuses unstable shapes', () => {
  const source = { record: { id: 'x', nested: { deep: [1, 'two', null, true] } }, afterIds: ['a'] };
  const captured = captureStableReadback(source, 'readback');
  assert.deepEqual(captured, source);
  source.record.id = 'MUTATED';
  source.afterIds.push('b');
  assert.equal(captured.record.id, 'x', 'later mutation of the source never reaches the capture');
  assert.deepEqual(captured.afterIds, ['a']);
  for (const [label, exotic] of exoticValues()) {
    assert.throws(() => captureStableReadback({ record: exotic }, 'readback'), /not stable plain data/, label);
  }
});

// ---------------------------------------------------------------------------
// B1/B2 integration: the wire body, the digest, and the expected comparison
// are all the same prepared bytes.
// ---------------------------------------------------------------------------

test('createPostDraft native wire body is exactly [payloadText], the digest hashes those UTF-8 bytes, and tampered payloadText is refused', async () => {
  // Pass the branded snapshot itself as the payload/expected so the bottom
  // layer's idempotent re-prepare hands back the exact same object.
  const prepared = prepareStableCreatePayload('article', structuredClone(ARTICLE_PAYLOAD), SITE_ID);
  const payload = prepared.snapshot;
  const { options, sent } = articleDraftOptions({ payload, auth: mintCreateAuth('article', payload) });
  const result = await createPostDraft(options);
  assert.equal(result.status, 'mutation_succeeded');
  assert.equal(sent.length, 1);
  const received = sent[0];
  assert.equal(received.body, `[${prepared.payloadText}]`, 'the wire body is exactly the bracketed payloadText');
  assert.equal(received.body.slice(1, -1), prepared.payloadText, 'the inner bytes are the immutable payloadText');
  assert.equal(received.payloadText, prepared.payloadText);
  assert.deepEqual(JSON.parse(received.body), [prepared.snapshot]);
  // The authorization create digest is the SHA-256 of the exact UTF-8
  // payloadText, and deriveAllinCmsMutationBinding verifies payloadText equals
  // the canonical serialization of the snapshot before hashing it.
  const binding = deriveAllinCmsMutationBinding({
    siteKey: SITE_KEY, route: createRoute('article'), actionName: 'postCreate',
    payload: prepared.snapshot, payloadText: prepared.payloadText,
  });
  assert.equal(binding.target.payload_digest, sha256Hex(Buffer.from(prepared.payloadText, 'utf8')));
  assert.equal(
    binding.target.payload_digest,
    deriveAllinCmsMutationBinding({
      siteKey: SITE_KEY, route: createRoute('article'), actionName: 'postCreate', payload: prepared.snapshot,
    }).target.payload_digest,
    'the payloadText digest and the canonicalJson digest are byte-identical for a prepared snapshot',
  );
  assert.throws(() => deriveAllinCmsMutationBinding({
    siteKey: SITE_KEY, route: createRoute('article'), actionName: 'postCreate',
    payload: prepared.snapshot, payloadText: `${prepared.payloadText} `,
  }), /must equal the canonical JSON serialization/);
  assert.throws(() => deriveAllinCmsMutationBinding({
    siteKey: SITE_KEY, route: createRoute('article'), actionName: 'postCreate',
    payload: prepared.snapshot, payloadText: Buffer.from('not-a-string'),
  }), /must be an immutable string/);
  // The same bytes protect the injected-client channel: the wrapper
  // re-validates the digest from the carried payloadText before transport.
  const injected = [];
  const injectedResult = await createPostDraft({
    ...options,
    runtime: undefined,
    request: undefined,
    client: {
      async send(details) {
        injected.push(details);
        return { status: 200, contentType: 'text/x-component' };
      },
    },
  });
  assert.equal(injectedResult.status, 'mutation_succeeded', JSON.stringify(injectedResult.mismatches));
  assert.equal(injected.length, 1);
  assert.equal(injected[0].payloadText, prepared.payloadText, 'the injected client receives the same payloadText');
  assert.strictEqual(injected[0].payload, prepared.snapshot, 'the injected client receives the exact frozen snapshot object');
});

test('createProductDraft native wire body and digest bind the same payloadText bytes for flat URL media', async () => {
  const payload = structuredClone(PRODUCT_PAYLOAD);
  const prepared = prepareStableCreatePayload('product', payload, SITE_ID);
  assert.ok(!('size' in prepared.snapshot.media) && !('mimeType' in prepared.snapshot.media), 'a new-site URL media carries no size/mimeType');
  assert.ok(!('alt' in prepared.snapshot.media), 'a string/null alt is normalized to missing');
  const { options, sent } = productDraftOptions({ payload, auth: mintCreateAuth('product', payload) });
  const result = await createProductDraft(options);
  assert.equal(result.status, 'mutation_succeeded');
  assert.equal(result.createdProductId, 'prd-new-1');
  assert.equal(sent.length, 1);
  assert.equal(sent[0].body, `[${prepared.payloadText}]`);
  const binding = deriveAllinCmsMutationBinding({
    siteKey: SITE_KEY, route: createRoute('product'), actionName: 'productCreate',
    payload: prepared.snapshot, payloadText: prepared.payloadText,
  });
  assert.equal(binding.target.payload_digest, sha256Hex(Buffer.from(prepared.payloadText, 'utf8')));
});

test('runActionWithRecovery reuses the identical payloadText string on every controlled retry', async () => {
  const payload = { siteId: SITE_ID, slug: 'cat-x' };
  const payloadText = canonicalStableCreateText(payload);
  const bodies = [];
  const texts = [];
  // Native client + counting host request: the wire body is built by the
  // production client, so retry identity is proven on the real bytes.
  const client = createAllinCmsActionClient({
    siteKey: SITE_KEY,
    runtime: createRuntime('categoryCreate', 'c'),
    authorizationContext: createAllinCmsMutationAuthorizationContext({
      siteKey: SITE_KEY,
      operation: 'allincms.taxonomy.category.create',
      target: { site_id: SITE_ID, slug: 'cat-x' },
      approvalActor: 'Stable Payload Fixture',
    }),
    request: async (details) => {
      bodies.push(details.body);
      texts.push(details.payloadText);
      return { status: 503, contentType: 'text/plain' };
    },
  });
  const result = await runActionWithRecovery({
    client,
    route: '/demo-site/posts?tab=categories',
    actionName: 'categoryCreate',
    payload,
    payloadText,
    expected: {},
    operation: 'taxonomy:category:create',
    readback: async () => (bodies.length >= 2 ? { applied: true } : null),
    retryOnExactAbsence: true,
    confirmExactAbsence: async () => true,
    maxControlledRetries: 1,
  });
  assert.equal(result.status, 'reconciled_success');
  assert.equal(bodies.length, 2, 'one controlled retry happened');
  assert.strictEqual(bodies[0], bodies[1], 'both attempts carried the identical body string');
  assert.strictEqual(bodies[0], `[${payloadText}]`);
  assert.strictEqual(texts[0], payloadText);
  assert.strictEqual(texts[1], payloadText);
  // A non-string payloadText is refused before any send.
  const rejectClient = { async send() { throw new Error('must not send'); } };
  await assert.rejects(() => runActionWithRecovery({
    client: rejectClient,
    route: '/demo-site/posts?tab=categories',
    actionName: 'categoryCreate',
    payload,
    payloadText: 42,
    expected: {},
    operation: 'x',
    readback: async () => null,
  }), /payloadText must be an immutable string/);
});

test('mutating the caller payload after prepare cannot move the wire body, the digest, or the expected comparison', async () => {
  const payload = structuredClone(ARTICLE_PAYLOAD);
  const prepared = prepareStableCreatePayload('article', payload, SITE_ID);
  const { sent, request } = countingTransport();
  const result = await createPostDraft({
    siteKey: SITE_KEY,
    runtime: createRuntime('postCreate'),
    request: async (details) => {
      sent.push(details);
      // Hostile mid-flight mutation of the caller's original object.
      payload.title = 'MUTATED MID-FLIGHT';
      payload.content.push({ type: 'p', children: [{ text: 'injected' }] });
      payload.categories.push('cat-sneaky');
      return { status: 200, ok: true, contentType: 'text/x-component' };
    },
    authorizationContext: mintCreateAuth('article', payload),
    siteId: SITE_ID,
    payload,
    expected: payload,
    beforePostIds: ['post-1'],
    readback: async () => ({
      record: { ...prepared.snapshot, id: 'post-new-1' },
      afterPostIds: ['post-1', 'post-new-1'],
    }),
    getCreatedPostId: (actual) => actual?.record?.id,
    getCreatedPostSiteId: (actual) => actual?.record?.siteId,
    getAfterPostIds: (actual) => actual?.afterPostIds,
    editorReopen: async (postId) => ({ status: 200, authenticated: true, healthy: true, postId }),
    maxControlledRetries: 0,
  });
  void request;
  assert.equal(result.status, 'mutation_succeeded');
  assert.equal(sent.length, 1);
  assert.equal(sent[0].body, `[${prepared.payloadText}]`, 'the wire bytes still bind the prepared snapshot');
  assert.equal(JSON.parse(sent[0].body)[0].title, 'Stable Guide');
  assert.deepEqual(result.readback.record, { ...prepared.snapshot, id: 'post-new-1' });
});

test('readback getters and proxies cannot split the canonical comparison from ID extraction (comparison A / ID B)', async () => {
  const payload = structuredClone(ARTICLE_PAYLOAD);
  const prepared = prepareStableCreatePayload('article', payload, SITE_ID);
  const cleanRecord = { ...prepared.snapshot, id: 'post-new-1' };
  const evilRecord = { ...prepared.snapshot, id: 'EVIL-9', title: 'EVIL TITLE' };
  const base = {
    siteKey: SITE_KEY,
    runtime: createRuntime('postCreate'),
    request: async () => ({ status: 200, ok: true, contentType: 'text/x-component' }),
    authorizationContext: mintCreateAuth('article', payload),
    siteId: SITE_ID,
    payload,
    expected: payload,
    beforePostIds: ['post-1'],
    getCreatedPostId: (actual) => actual?.record?.id,
    getCreatedPostSiteId: (actual) => actual?.record?.siteId,
    getAfterPostIds: (actual) => actual?.afterPostIds,
    editorReopen: async (postId) => ({ status: 200, authenticated: true, healthy: true, postId }),
    maxControlledRetries: 0,
  };

  // 1. Accessor `record`: serves the clean record for the first reads and the
  //    evil record afterwards. The stable capture never invokes the getter;
  //    the readback fails closed as unstable data.
  let recordReads = 0;
  const accessorWrapper = { afterPostIds: ['post-1', 'post-new-1'] };
  Object.defineProperty(accessorWrapper, 'record', {
    enumerable: true, configurable: true,
    get() { recordReads += 1; return recordReads <= 2 ? cleanRecord : evilRecord; },
  });
  const accessorResult = await createPostDraft({ ...base, readback: async () => accessorWrapper });
  assert.equal(accessorResult.status, 'stopped_manual_intervention');
  assert.equal(accessorResult.createdPostId, null);
  assert.equal(recordReads, 0, 'the hostile record getter must never be invoked');
  assert.match(accessorResult.mismatches.join('; '), /could not be captured as stable plain data/);
  assert.match(accessorResult.mismatches.join('; '), /accessor property/);

  // 2. Proxy whose get trap alternates between the clean and the evil record.
  //    The capture reads descriptors only, so the trap never serves a consumer
  //    read (the promise machinery's `then` probe is not a consumer read) and
  //    every consumer sees the same captured copy.
  const consumerTrapReads = [];
  const proxyWrapper = new Proxy({ record: cleanRecord, afterPostIds: ['post-1', 'post-new-1'] }, {
    get(target, key) {
      if (key !== 'then') consumerTrapReads.push(String(key));
      return target[key];
    },
  });
  const proxyResult = await createPostDraft({ ...base, readback: async () => proxyWrapper });
  assert.equal(proxyResult.status, 'mutation_succeeded');
  assert.equal(proxyResult.createdPostId, 'post-new-1');
  assert.deepEqual(consumerTrapReads, [], 'the hostile get trap must never serve a consumer read');

  // 3. A data-property wrapper flipped by a microtask queued during readback
  //    runs before the synchronous capture, so the comparison and the ID
  //    getters still consume ONE coherent state — here the flipped one — and
  //    the drift is reported instead of silently passing.
  const flippingWrapper = { record: cleanRecord, afterPostIds: ['post-1', 'post-new-1'] };
  const flipResult = await createPostDraft({
    ...base,
    readback: async () => {
      queueMicrotask(() => { flippingWrapper.record = evilRecord; });
      return flippingWrapper;
    },
  });
  assert.equal(flipResult.status, 'stopped_manual_intervention');
  assert.match(flipResult.mismatches.join('; '), /title drifted from the frozen expected payload/);
});

test('media readback accepts flat and {type,value} wrapper forms, normalizes alt, and rejects single-sided wrapper type conflicts', async () => {
  const productPayload = structuredClone(PRODUCT_PAYLOAD);
  const productPrepared = prepareStableCreatePayload('product', structuredClone(PRODUCT_PAYLOAD), SITE_ID);
  const urlCore = { name: 'synthetic.webp', alt: null, type: 'image', source: 'url', url: 'https://assets.example.invalid/synthetic.webp' };
  const productBase = {
    siteKey: SITE_KEY,
    runtime: createRuntime('productCreate', 'b'),
    request: async () => ({ status: 200, ok: true, contentType: 'text/x-component' }),
    authorizationContext: mintCreateAuth('product', productPayload),
    siteId: SITE_ID,
    payload: productPayload,
    expected: productPayload,
    beforeProductIds: ['prd-1'],
    getCreatedProductId: (actual) => actual?.record?.id,
    getCreatedProductSiteId: (actual) => actual?.record?.siteId,
    getAfterProductIds: (actual) => actual?.afterProductIds,
    maxControlledRetries: 0,
  };
  const runWithRecordMedia = async (media) => createProductDraft({
    ...productBase,
    readback: async () => ({
      record: { ...productPrepared.snapshot, id: 'prd-new-1', media },
      afterProductIds: ['prd-1', 'prd-new-1'],
    }),
  });
  for (const [label, mediaForm] of [
    ['flat with alt null', structuredClone(urlCore)],
    ['flat without alt', { name: urlCore.name, type: 'image', source: 'url', url: urlCore.url }],
    ['flat with string alt', { ...urlCore, alt: '描述' }],
    ['wrapper with matching outer type', { type: 'image', value: structuredClone(urlCore) }],
  ]) {
    const result = await runWithRecordMedia(mediaForm);
    assert.equal(result.status, 'mutation_succeeded', label);
    assert.equal(result.createdProductId, 'prd-new-1', label);
  }
  // mediaList entries may also arrive wrapped.
  const listPayload = { ...structuredClone(PRODUCT_PAYLOAD), mediaList: [structuredClone(URL_MEDIA)] };
  const listPrepared = prepareStableCreatePayload('product', listPayload, SITE_ID);
  const listResult = await createProductDraft({
    ...productBase,
    payload: listPayload,
    expected: listPayload,
    authorizationContext: mintCreateAuth('product', listPayload),
    readback: async () => ({
      record: { ...listPrepared.snapshot, id: 'prd-new-1', mediaList: [{ type: 'image', value: structuredClone(urlCore) }] },
      afterProductIds: ['prd-1', 'prd-new-1'],
    }),
  });
  assert.equal(listResult.status, 'mutation_succeeded', 'wrapped mediaList entries compare equal');

  // Single-sided conflicts: outer wrapper type vs inner media type.
  for (const [label, mediaForm, pattern] of [
    ['outer video wrapping inner image', { type: 'video', value: structuredClone(urlCore) }, /media wrapper type "video" conflicts/],
    ['outer image wrapping inner video', { type: 'image', value: { ...structuredClone(urlCore), type: 'video' } }, /media wrapper type "image" conflicts/],
  ]) {
    const result = await runWithRecordMedia(mediaForm);
    assert.equal(result.status, 'stopped_manual_intervention', label);
    assert.match(result.mismatches.join('; '), pattern, label);
  }

  // Article cover: URL (new-site, no size/mimeType) and OSS both pass; a
  // numeric alt drifts fail-closed; a null-cover expectation accepts a
  // wrapper-wrapped null record.
  const articleUrlCover = structuredClone(ARTICLE_PAYLOAD);
  articleUrlCover.coverImage = structuredClone(URL_MEDIA);
  const coverPrepared = prepareStableCreatePayload('article', articleUrlCover, SITE_ID);
  assert.ok(!('alt' in coverPrepared.snapshot.coverImage), 'write normalization drops the null alt');
  assert.ok(!('size' in coverPrepared.snapshot.coverImage) && !('mimeType' in coverPrepared.snapshot.coverImage), 'URL cover carries no OSS fields');
  const articleBase = {
    siteKey: SITE_KEY,
    runtime: createRuntime('postCreate'),
    request: async () => ({ status: 200, ok: true, contentType: 'text/x-component' }),
    siteId: SITE_ID,
    beforePostIds: ['post-1'],
    getCreatedPostId: (actual) => actual?.record?.id,
    getCreatedPostSiteId: (actual) => actual?.record?.siteId,
    getAfterPostIds: (actual) => actual?.afterPostIds,
    editorReopen: async (postId) => ({ status: 200, authenticated: true, healthy: true, postId }),
    maxControlledRetries: 0,
  };
  const runWithCover = async (inputPayload, prepared, cover) => createPostDraft({
    ...articleBase,
    authorizationContext: mintCreateAuth('article', inputPayload),
    payload: inputPayload,
    expected: inputPayload,
    readback: async () => ({
      record: { ...prepared.snapshot, id: 'post-new-1', coverImage: cover },
      afterPostIds: ['post-1', 'post-new-1'],
    }),
  });
  assert.equal((await runWithCover(articleUrlCover, coverPrepared, structuredClone(URL_MEDIA))).status, 'mutation_succeeded', 'flat url cover');
  assert.equal((await runWithCover(articleUrlCover, coverPrepared, { type: 'image', value: structuredClone(URL_MEDIA) })).status, 'mutation_succeeded', 'wrapped url cover');
  const ossPayload = structuredClone(ARTICLE_PAYLOAD);
  ossPayload.coverImage = structuredClone(OSS_MEDIA);
  const ossPrepared = prepareStableCreatePayload('article', ossPayload, SITE_ID);
  assert.ok(!('alt' in ossPrepared.snapshot.coverImage), 'OSS alt is normalized away too');
  assert.equal(ossPrepared.snapshot.coverImage.size, 42);
  assert.equal((await runWithCover(ossPayload, ossPrepared, structuredClone(OSS_MEDIA))).status, 'mutation_succeeded', 'oss cover round-trips');
  const numericAlt = await runWithCover(articleUrlCover, coverPrepared, { ...URL_MEDIA, alt: 7 });
  assert.equal(numericAlt.status, 'stopped_manual_intervention');
  assert.match(numericAlt.mismatches.join('; '), /coverImage drifted/);
  const nullPayload = structuredClone(ARTICLE_PAYLOAD);
  const nullPrepared = prepareStableCreatePayload('article', nullPayload, SITE_ID);
  assert.equal((await runWithCover(nullPayload, nullPrepared, { type: 'image', value: null })).status, 'mutation_succeeded', 'a wrapper-wrapped null cover equals a null expected cover');
});

// ---------------------------------------------------------------------------
// Driver-level B1: the host driver prepares before any await/provider/auth
// and hands the bottom layer the exact same branded snapshot.
// ---------------------------------------------------------------------------

const DRIVER_CONTRACT_FIELDS = {
  article: ['title', 'slug', 'excerpt', 'order', 'coverImage', 'categories', 'tags', 'content'],
  product: ['name', 'slug', 'description', 'order', 'media', 'mediaList', 'content', 'categories', 'tags', 'specifications'],
};

function driverCreatePlan(kind, fieldValueOverrides = {}) {
  const fields = {};
  for (const field of DRIVER_CONTRACT_FIELDS[kind]) {
    fields[field] = {
      value: field === 'coverImage' ? null
        : field === 'media' ? structuredClone(URL_MEDIA)
        : field === 'order' ? 1
        : field === 'excerpt' ? ''
        : field === 'content' ? [{ type: 'p', children: [{ text: '正文' }] }]
        : field === 'categories' || field === 'tags' || field === 'mediaList' ? []
        : field === 'specifications' ? [{ key: 'k', value: 'v' }]
        : kind === 'article' ? `Driver ${field}` : `Driver ${field}`,
    };
  }
  for (const [field, value] of Object.entries(fieldValueOverrides)) fields[field] = { value };
  const entityRef = `${kind}:driver`;
  return {
    authorization_scope: {
      status: 'approved', actor: 'Test Human',
      approved_at: new Date(Date.now() - 60_000).toISOString(),
      expires_at: new Date(Date.now() + 28 * 60_000).toISOString(),
    },
    desired_state: [{ entity_ref: entityRef, entity_type: kind, intent: 'create', identity: { id: null, natural_key: {}, match_strategy: 'exact_natural_key' }, fields }],
    operations: [{ operation_id: 'OP-1', entity_ref: entityRef, entity_type: kind, intent: 'create', identity: { id: null, natural_key: {}, match_strategy: 'exact_natural_key' } }],
  };
}

function driverDesiredPayload(kind, plan) {
  const payload = {};
  for (const field of DRIVER_CONTRACT_FIELDS[kind]) payload[field] = plan.desired_state[0].fields[field].value;
  return payload;
}

function driverHandlers(kind, plan, { authorizationProvider, beforeProviderHook, readbackRecord = null } = {}) {
  const requested = [];
  const events = [];
  const newEntityId = kind === 'article' ? 'post-new-1' : 'prd-new-1';
  // A caller-supplied readbackRecord pins the readback to the values the plan
  // carried BEFORE an async provider mutated it (the prepared snapshot).
  const fixedRecord = readbackRecord
    ? { ...readbackRecord, id: newEntityId }
    : null;
  const handlers = createAllinCmsPlanHandlerSet({
    siteKey: SITE_KEY, siteId: SITE_ID,
    runtime: createRuntime(createActionName(kind), kind === 'article' ? 'a' : 'b'),
    request: async (details) => {
      events.push(`request:${details.actionName}`);
      requested.push(details);
      return { status: 200, ok: true, contentType: 'text/x-component' };
    },
    ...(authorizationProvider ? { authorizationProvider } : {}),
    readbackProvider: async () => ({ ok: true, authoritative: true, requirements: [], evidence_ref: 'unused', checks: [] }),
    ...(kind === 'article'
      ? {
        articleBeforePostIdsProvider: async (args) => {
          events.push('before-snapshot');
          if (beforeProviderHook) await beforeProviderHook(args.plan, events);
          return ['post-1'];
        },
        articleCreateReadbackProvider: async () => {
          events.push('create-readback');
          const base = fixedRecord ?? { ...prepareStableCreatePayload('article', driverDesiredPayload('article', plan), SITE_ID).snapshot, id: newEntityId };
          return { record: base, afterPostIds: ['post-1', newEntityId] };
        },
        articleEditorReopenProvider: async ({ createdPostId }) => ({ status: 200, authenticated: true, healthy: true, postId: createdPostId }),
      }
      : {
        productBeforeProductIdsProvider: async (args) => {
          events.push('before-snapshot');
          if (beforeProviderHook) await beforeProviderHook(args.plan, events);
          return ['prd-1'];
        },
        productCreateReadbackProvider: async () => {
          events.push('create-readback');
          const base = fixedRecord ?? { ...prepareStableCreatePayload('product', driverDesiredPayload('product', plan), SITE_ID).snapshot, id: newEntityId };
          return { record: base, afterProductIds: ['prd-1', newEntityId] };
        },
      }),
  });
  return { handlers, events, requested, newEntityId };
}

test('driver prepares the branded snapshot before any await/provider/auth and hands the bottom layer the identical object and payloadText', async () => {
  for (const kind of ['article', 'product']) {
    const plan = driverCreatePlan(kind);
    const captured = {};
    const { handlers, events, requested, newEntityId } = driverHandlers(kind, plan, {
      authorizationProvider: (args) => {
        captured.createPayload = args.createPayload;
        captured.createPayloadText = args.createPayloadText;
        // The provider runs after the before-snapshot provider await: the
        // authorization input was already the branded frozen snapshot.
        assert.ok(events.includes('before-snapshot'), `${kind}: auth ran after the provider await`);
        assert.ok(Object.isFrozen(args.createPayload), `${kind}: the authorization input is frozen`);
        assert.equal(
          prepareStableCreatePayload(kind, args.createPayload, SITE_ID).snapshot,
          args.createPayload,
          `${kind}: re-preparing the authorization input returns the identical branded object`,
        );
        return allinCmsOperationAuthorization(args);
      },
    });
    const result = await handlers[`${kind}:create`].execute({ plan, operation: plan.operations[0] });
    assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: newEntityId }, kind);
    assert.equal(requested.length, 1, kind);
    // No {...payload, siteId} second construction: the request payload IS the
    // authorization input object, and the wire body embeds the same text.
    assert.strictEqual(requested[0].payload, captured.createPayload, `${kind}: the wire payload is the authorization snapshot object`);
    assert.strictEqual(requested[0].body.slice(1, -1), captured.createPayloadText, `${kind}: the wire inner bytes are the authorization payloadText`);
  }
});

test('driver blocks unstable desired-state values before any provider or request', async () => {
  const cases = [
    ['product media wrapper', 'product', { media: { type: 'image', value: structuredClone(URL_MEDIA) } }, /refused on the create write path/],
    ['product media null', 'product', { media: null }, /must be a non-null flat URL or OSS media object/],
    ['product spec extra key', 'product', { specifications: [{ key: 'k', value: 'v', unit: 'W' }] }, /exactly the fields key and value/],
    ['article cover wrapper', 'article', { coverImage: { type: 'image', value: structuredClone(URL_MEDIA) } }, /refused on the create write path/],
    ['article taxonomy duplicate', 'article', { tags: ['tag-1', ' tag-1'] }, /duplicate IDs/],
    ['article content Date node', 'article', { content: [{ type: 'p', children: [new Date()] }] }, /not stable plain data/],
  ];
  for (const [label, kind, overrides, pattern] of cases) {
    const plan = driverCreatePlan(kind, overrides);
    const { handlers, events, requested } = driverHandlers(kind, plan);
    await assert.rejects(
      () => handlers[`${kind}:create`].execute({ plan, operation: plan.operations[0] }),
      pattern,
      label,
    );
    assert.deepEqual(events, [], `${label}: blocked before any provider`);
    assert.equal(requested.length, 0, label);
  }
});

test('driver plan mutated by an async provider after the prepare cannot move the request body or the comparison', async () => {
  const kind = 'article';
  const plan = driverCreatePlan(kind);
  const preMutationSnapshot = prepareStableCreatePayload('article', driverDesiredPayload(kind, plan), SITE_ID).snapshot;
  const { handlers, requested, newEntityId } = driverHandlers(kind, plan, {
    readbackRecord: preMutationSnapshot,
    beforeProviderHook: async (livePlan) => {
      // Async provider mutates the live plan AFTER the driver prepared the
      // outgoing snapshot.
      livePlan.desired_state[0].fields.title.value = 'MUTATED TITLE';
      livePlan.desired_state[0].fields.order.value = 99;
    },
  });
  const result = await handlers[`${kind}:create`].execute({ plan, operation: plan.operations[0] });
  assert.deepEqual(result, { request_started: true, status: 'completed', entity_id: newEntityId });
  assert.equal(requested.length, 1);
  assert.equal(JSON.parse(requested[0].body)[0].title, 'Driver title', 'the prepared title survived the plan mutation');
  assert.equal(JSON.parse(requested[0].body)[0].order, 1, 'the prepared order survived the plan mutation');
});

test('payloadText digests are byte-identical across both canonical serializers for every prepared snapshot', () => {
  for (const [kind, fixture] of [['article', ARTICLE_PAYLOAD], ['product', PRODUCT_PAYLOAD]]) {
    const prepared = prepareStableCreatePayload(kind, structuredClone(fixture), SITE_ID);
    const withText = deriveAllinCmsMutationBinding({
      siteKey: SITE_KEY, route: createRoute(kind), actionName: createActionName(kind),
      payload: prepared.snapshot, payloadText: prepared.payloadText,
    });
    const withoutText = deriveAllinCmsMutationBinding({
      siteKey: SITE_KEY, route: createRoute(kind), actionName: createActionName(kind),
      payload: prepared.snapshot,
    });
    assert.equal(withText.target.payload_digest, withoutText.target.payload_digest, kind);
    assert.equal(withText.target.payload_digest, sha256Hex(Buffer.from(prepared.payloadText, 'utf8')), kind);
  }
});
