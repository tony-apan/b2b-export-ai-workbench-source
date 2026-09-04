import test from 'node:test';
import assert from 'node:assert/strict';
import { runInNewContext } from 'node:vm';
import {
  ALLINCMS_ARTICLE_FORMAT_SUPPORT,
  ARTICLE_FIELDS,
  createCanonicalAllinCmsSlateExamples,
  extractPublishableArticleMarkdown,
  markdownToAllinCmsSlate,
  publishableArticleMarkdownToAllinCmsSlate,
  buildArticlePayload,
  buildCategoryPayload,
  buildTagPayload,
  createAllinCmsActionClient,
  createPostCategory,
  createPostDraft,
  createPostTag,
  deletePost,
  deletePostCategory,
  deletePostTag,
  publishPost,
  runArticleBatchSerial,
  runActionWithRecovery,
  savePostDraft,
  unpublishPost,
  updatePostCategory,
  updatePostTag,
  assertNoDuplicateSlug,
  assertSameSite,
} from './article-operations.mjs';
import {
  createAllinCmsMutationAuthorizationContext,
  deriveAllinCmsMutationBinding,
} from './mutation-authorization.mjs';
import { prepareStableCreatePayload } from './content-mutation-primitives.mjs';

test('article operations entrypoint exposes the verified format matrix and Markdown converter', () => {
  assert.equal(ALLINCMS_ARTICLE_FORMAT_SUPPORT.verified.length, 12);
  assert.deepEqual(ALLINCMS_ARTICLE_FORMAT_SUPPORT.unsupportedCurrentShape.map((item) => item.key), ['code-block']);
  assert.equal(createCanonicalAllinCmsSlateExamples().table.type, 'table');
  assert.equal(markdownToAllinCmsSlate('### Heading')[0].type, 'h3');
  const bounded = '<!-- PUBLISHABLE_BODY_START -->\nSafe body\n<!-- PUBLISHABLE_BODY_END -->';
  assert.equal(extractPublishableArticleMarkdown(bounded), 'Safe body');
  assert.equal(publishableArticleMarkdownToAllinCmsSlate(bounded)[0].type, 'p');
});

const runtime = {
  routerTree: 'TREE-current', deploymentId: 'd'.repeat(40),
  actions: {
    postCreate: { actionId: 'create-action' }, postUpdate: { actionId: 'update-action' }, postDelete: { actionId: 'delete-action' },
    categoryCreate: { actionId: 'category-create-action' }, categoryUpdate: { actionId: 'category-update-action' }, categoryDelete: { actionId: 'category-delete-action' },
    tagCreate: { actionId: 'tag-create-action' }, tagUpdate: { actionId: 'tag-update-action' }, tagDelete: { actionId: 'tag-delete-action' },
  },
};
const ids = { siteId: 'site-1', postId: 'post-1', categoryId: 'category-1', tagId: 'tag-1' };
const base = {
  title: '接口文章', slug: 'api-article', excerpt: '摘要', order: 2,
  coverImage: { name: 'cover.webp', alt: '封面', type: 'image', source: 'oss', path: 'site/cover.webp', size: 42, mimeType: 'image/webp' },
  categories: ['category-1'], tags: ['tag-1'], content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
};
function clientFor({ response = { status: 200, contentType: 'text/x-component' }, onSend } = {}) {
  const calls = [];
  return { calls, async send(details) { calls.push(details); if (onSend) await onSend(details); return typeof response === 'function' ? response(details, calls) : response; } };
}
function articleRecord(payload, status = 'draft') { return { ...structuredClone(payload), status }; }

function mutationAuth({ siteKey = 'demo-site', operation, target, approvedAt, expiresAt }) {
  const approved = approvedAt || new Date(Date.now() - 1_000).toISOString();
  return createAllinCmsMutationAuthorizationContext({
    siteKey,
    operation,
    target,
    approvalActor: 'Tony test fixture',
    approvedAt: approved,
    expiresAt: expiresAt || new Date(Date.parse(approved) + 20 * 60 * 1000).toISOString(),
  });
}
function articleAuth(mode, { siteId = ids.siteId, postId = ids.postId, ...times } = {}) {
  return mutationAuth({ operation: `allincms.article.${mode}`, target: { site_id: siteId, post_id: postId }, ...times });
}
function createDraftAuth(payload = { siteId: ids.siteId }) {
  const binding = deriveAllinCmsMutationBinding({ siteKey: 'demo-site', route: '/demo-site/posts', actionName: 'postCreate', payload });
  return mutationAuth(binding);
}
function taxonomyAuth(type, action, { siteId = ids.siteId, id, slug } = {}) {
  return mutationAuth({
    operation: `allincms.taxonomy.${type}.${action}`,
    target: action === 'create' ? { site_id: siteId, slug } : { site_id: siteId, id },
  });
}

for (const mode of ['update', 'publish', 'unpublish']) {
  test(`buildArticlePayload keeps complete field contract for ${mode}`, () => {
    const payload = buildArticlePayload({ defaults: base, overrides: {}, ...ids, mode });
    assert.deepEqual(Object.keys(payload).sort(), [...ARTICLE_FIELDS].sort());
    assert.equal(payload.mode, mode); assert.equal(payload.coverImage.path, 'site/cover.webp');
  });
}
test('article payload normalizes IDs and rejects duplicates', () => {
  const payload = buildArticlePayload({ defaults: base, overrides: { categories: [' category-1 '] }, ...ids });
  assert.deepEqual(payload.categories, ['category-1']);
  assert.throws(() => buildArticlePayload({ defaults: base, overrides: { tags: ['tag-1', ' tag-1 '] }, ...ids }), /duplicate IDs/);
});
test('article payload blocks invalid Slate, order, and incomplete canonical cover fields before request', () => {
  assert.throws(() => buildArticlePayload({ defaults: base, overrides: { order: '2' }, ...ids }), /integer/);
  assert.throws(() => buildArticlePayload({ defaults: base, overrides: { content: '<p>bad<\/p>' }, ...ids }), /Slate/);
  for (const field of ['name', 'alt', 'type', 'source', 'path', 'size', 'mimeType']) {
    const incompleteCover = { ...base.coverImage };
    delete incompleteCover[field];
    assert.throws(
      () => buildArticlePayload({ defaults: base, overrides: { coverImage: incompleteCover }, ...ids }),
      new RegExp(`missing canonical persisted fields: .*${field}`),
    );
  }
  assert.throws(
    () => buildArticlePayload({ defaults: base, overrides: { coverImage: { ...base.coverImage, alt: null } }, ...ids }),
    /coverImage\.alt must be a string/,
  );
  assert.throws(
    () => buildArticlePayload({ defaults: base, overrides: { coverImage: { ...base.coverImage, size: '42' } }, ...ids }),
    /coverImage\.size must be a non-negative integer/,
  );
});
test('action client uses dynamic runtime headers and one-argument body', async () => {
  let received;
  const client = createAllinCmsActionClient({ siteKey: 'demo-site', runtime, authorizationContext: articleAuth('update'), request: async (details) => { received = details; return { status: 200, contentType: 'text/x-component' }; } });
  await client.send({ route: '/demo-site/posts/post-1/update', actionName: 'postUpdate', payload: { mode: 'update', siteId: ids.siteId, postId: ids.postId } });
  assert.equal(received.headers['next-action'], 'update-action'); assert.equal(received.headers['x-deployment-id'], 'd'.repeat(40)); assert.equal(received.headers['next-router-state-tree'], 'TREE-current'); assert.deepEqual(JSON.parse(received.body), [{ mode: 'update', siteId: ids.siteId, postId: ids.postId }]);
});
test('runtime with an action map refuses an uncaptured action instead of falling back', async () => {
  const client = createAllinCmsActionClient({ siteKey: 'demo-site', runtime, authorizationContext: articleAuth('update'), request: async () => ({ status: 200, contentType: 'text/x-component' }) });
  await assert.rejects(() => client.send({ route: '/demo-site/posts', actionName: 'uncapturedAction', payload: {} }), /Missing runtime action/);
});
test('site key is restricted to one safe route segment', () => {
  assert.throws(() => createAllinCmsActionClient({ siteKey: 'demo/site', runtime, authorizationContext: articleAuth('update'), request: async () => ({ status: 200 }) }), /safe route segment/);
});
test('all mutation paths require exact, fresh structured authorization with injected client', async () => {
  for (const authorizationContext of [
    undefined,
    true,
    articleAuth('update', { approvedAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(), expiresAt: new Date(Date.now() - 1_000).toISOString() }),
    articleAuth('update', { siteId: 'other-site-id' }),
    articleAuth('publish'),
  ]) {
    const client = clientFor();
    await assert.rejects(() => savePostDraft({
      client,
      siteKey: 'demo-site',
      authorizationContext,
      ...ids,
      defaults: base,
      readback: async () => articleRecord({ ...base, ...ids, mode: 'update' }),
    }), /authorizationContext|expired|target|operation/);
    assert.equal(client.calls.length, 0);
  }
  const requestCalls = [];
  const directClient = createAllinCmsActionClient({
    siteKey: 'demo-site',
    runtime,
    authorizationConfirmed: true,
    request: async (details) => { requestCalls.push(details); return { status: 200, contentType: 'text/x-component' }; },
  });
  await assert.rejects(() => directClient.send({
    route: '/demo-site/posts/post-1/update',
    actionName: 'postUpdate',
    payload: { mode: 'update', siteId: ids.siteId, postId: ids.postId },
  }), /structured authorizationContext/);
  assert.equal(requestCalls.length, 0);
});
test('root and child category payloads keep parent distinction', () => {
  const root = buildCategoryPayload({ siteId: ids.siteId, name: '根', slug: 'root', cover: null, order: 0 });
  const child = buildCategoryPayload({ siteId: ids.siteId, name: '子', slug: 'child', parent: ids.categoryId, cover: null, order: 1 });
  assert.equal(Object.hasOwn(root, 'parent'), false); assert.equal(child.parent, ids.categoryId); assert.equal(root.contentType, 'posts');
});
test('taxonomy payloads omit empty or whitespace descriptions (observed 2026-08-27: server rejects create with empty-string description)', () => {
  const tag = buildTagPayload({ siteId: ids.siteId, name: '标签', slug: 'tag', description: '' });
  assert.equal(Object.hasOwn(tag, 'description'), false, 'empty description must be omitted from tag payload');
  const category = buildCategoryPayload({ siteId: ids.siteId, name: '分类', slug: 'category', description: '   ' });
  assert.equal(Object.hasOwn(category, 'description'), false, 'whitespace-only description must be omitted from category payload');
  const withDescription = buildTagPayload({ siteId: ids.siteId, name: '标签', slug: 'tag', description: 'phase stability' });
  assert.equal(withDescription.description, 'phase stability');
  const undefinedDescription = buildTagPayload({ siteId: ids.siteId, name: '标签', slug: 'tag' });
  assert.equal(Object.hasOwn(undefinedDescription, 'description'), false);
});
test('taxonomy slug duplicate is scoped to same site', () => {
  assert.throws(() => assertNoDuplicateSlug([{ siteId: ids.siteId, slug: 'same' }], 'same', ids.siteId, 'tag'), /already exists/);
  assert.doesNotThrow(() => assertNoDuplicateSlug([{ siteId: 'other-site', slug: 'same' }], 'same', ids.siteId, 'tag'));
  assert.throws(() => assertSameSite({ siteId: 'other-site' }, ids.siteId, 'tag'), /different site/);
  assert.throws(() => assertSameSite({ id: ids.tagId }, ids.siteId, 'tag'), /siteId is required/);
  assert.throws(() => assertSameSite(null, ids.siteId, 'tag'), /readback record is required/);
});
test('taxonomy creation requires a current snapshot and posts content type', () => {
  assert.throws(() => createPostCategory({ client: clientFor(), siteKey: 'demo-site', authorizationContext: taxonomyAuth('category', 'create', { slug: 'category' }), siteId: ids.siteId, name: '分类', slug: 'category', readback: async () => null }), /snapshot is required/);
  assert.throws(() => createPostTag({ client: clientFor(), siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'create', { slug: 'tag' }), siteId: ids.siteId, name: '标签', slug: 'tag', readback: async () => null }), /snapshot is required/);
  assert.throws(() => buildCategoryPayload({ siteId: ids.siteId, name: '分类', slug: 'category', contentType: 'pages' }), /contentType must be posts/);
  assert.throws(() => buildTagPayload({ siteId: ids.siteId, name: '标签', slug: 'tag', contentType: 'pages' }), /contentType must be posts/);
});
test('savePostDraft sends full update and verifies draft readback', async () => {
  let record = null; const client = clientFor({ onSend: async ({ payload }) => { record = articleRecord(payload, 'draft'); } });
  const result = await savePostDraft({ client, siteKey: 'demo-site', authorizationContext: articleAuth('update'), ...ids, defaults: base, readback: async () => record });
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(client.calls[0].route, '/demo-site/posts/post-1/update'); assert.equal(client.calls[0].payload.mode, 'update'); assert.equal(client.calls[0].payload.coverImage.path, 'site/cover.webp');
});
test('publishPost refuses 200 when readback is not published', async () => {
  let current = articleRecord({ ...base, ...ids, mode: 'update' }, 'draft'); const client = clientFor({ onSend: async ({ payload }) => { current = articleRecord(payload, 'draft'); } });
  const result = await publishPost({ client, siteKey: 'demo-site', authorizationContext: articleAuth('publish'), ...ids, defaults: base, readback: async () => current });
  assert.equal(result.status, 'stopped_manual_intervention'); assert.match(result.mismatches.join('; '), /published/);
});
test('publishPost succeeds only after backend status becomes published', async () => {
  let current = articleRecord({ ...base, ...ids, mode: 'update' }, 'draft'); const client = clientFor({ onSend: async ({ payload }) => { current = articleRecord(payload, 'published'); } });
  const result = await publishPost({ client, siteKey: 'demo-site', authorizationContext: articleAuth('publish'), ...ids, defaults: base, readback: async () => current });
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(result.readback.status, 'published');
});
test('article mutation blocks missing or conflicting publish state', async () => {
  const missing = await savePostDraft({ client: clientFor({ onSend: async () => {} }), siteKey: 'demo-site', authorizationContext: articleAuth('update'), ...ids, defaults: base, readback: async () => ({ ...base, ...ids, mode: 'update' }) });
  assert.equal(missing.status, 'stopped_manual_intervention');
  assert.match(missing.mismatches.join('; '), /missing/);
  const conflicting = await publishPost({ client: clientFor(), siteKey: 'demo-site', authorizationContext: articleAuth('publish'), ...ids, defaults: base, readback: async () => ({ ...base, ...ids, status: 'published', _status: 'draft' }) });
  assert.match(conflicting.mismatches.join('; '), /conflicting/);
});
test('readback comparison ignores object key order but preserves values', async () => {
  const result = await publishPost({ client: clientFor(), siteKey: 'demo-site', authorizationContext: articleAuth('publish'), ...ids, defaults: base, readback: async () => ({ ...base, ...ids, coverImage: { mimeType: 'image/webp', path: 'site/cover.webp', source: 'oss', type: 'image', name: 'cover.webp', alt: '封面', size: 42 }, status: 'published' }) });
  assert.equal(result.status, 'mutation_succeeded');
});
test('readback comparison ignores browser realm prototypes when JSON values match', async () => {
  const foreignRecord = runInNewContext(`({
    title: '接口文章', slug: 'api-article', excerpt: '摘要', order: 2,
    coverImage: { name: 'cover.webp', alt: '封面', type: 'image', source: 'oss', path: 'site/cover.webp', size: 42, mimeType: 'image/webp' },
    categories: ['category-1'], tags: ['tag-1'],
    content: [{ type: 'p', children: [{ text: '正文' }], id: 'node-1' }],
    siteId: 'site-1', postId: 'post-1', mode: 'publish', status: 'published'
  })`);
  assert.notEqual(Object.getPrototypeOf(foreignRecord), Object.prototype);
  assert.notEqual(Object.getPrototypeOf(foreignRecord.coverImage), Object.prototype);
  const result = await publishPost({
    client: clientFor(), siteKey: 'demo-site', authorizationContext: articleAuth('publish'),
    ...ids, defaults: base, readback: async () => foreignRecord,
  });
  assert.equal(result.status, 'mutation_succeeded');
});
test('unpublishPost requires and verifies draft readback', async () => {
  let current = articleRecord({ ...base, ...ids, mode: 'publish' }, 'published'); const client = clientFor({ onSend: async ({ payload }) => { current = articleRecord(payload, 'draft'); } });
  const result = await unpublishPost({ client, siteKey: 'demo-site', authorizationContext: articleAuth('unpublish'), ...ids, defaults: base, readback: async () => current });
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(result.readback.status, 'draft');
});
test('503 reconciles to success without resend, including injected-client transport errors', async () => {
  let current = null; const client = clientFor({ response: { status: 503, contentType: 'text/plain' }, onSend: async ({ payload }) => { current = articleRecord(payload, 'draft'); } });
  const result = await savePostDraft({ client, siteKey: 'demo-site', authorizationContext: articleAuth('update'), ...ids, defaults: base, readback: async () => current });
  assert.equal(result.status, 'reconciled_success'); assert.equal(client.calls.length, 1);
  let injectedReadback = null;
  const injected = {
    async send({ payload }) {
      injectedReadback = articleRecord(payload, 'draft');
      throw new Error('connection lost after send');
    },
  };
  const injectedResult = await savePostDraft({
    client: injected, siteKey: 'demo-site', authorizationContext: articleAuth('update'),
    ...ids, defaults: base, readback: async () => injectedReadback,
  });
  assert.equal(injectedResult.status, 'reconciled_success');
  assert.equal(injectedResult.requestStarted, true);
  assert.equal(injectedResult.automaticRetryAllowed, false);
});
test('503 plus exact absence does not retry an existing article without explicit absence proof', async () => {
  let current = null; let sends = 0; const client = clientFor({ response: () => ({ status: 503, contentType: 'text/plain' }), onSend: async ({ payload }) => { sends += 1; if (sends === 2) current = articleRecord(payload, 'draft'); } });
  const result = await savePostDraft({ client, siteKey: 'demo-site', authorizationContext: articleAuth('update'), ...ids, defaults: base, readback: async () => current });
  assert.equal(result.status, 'stopped_manual_intervention'); assert.equal(sends, 1);
});
test('503 plus exact absence permits one controlled retry only with explicit absence proof', async () => {
  let current = null; let sends = 0; const client = clientFor({ response: () => ({ status: 503, contentType: 'text/plain' }), onSend: async ({ payload }) => { sends += 1; if (sends === 2) current = articleRecord(payload, 'draft'); } });
  const result = await runActionWithRecovery({ client, route: '/x', actionName: 'categoryCreate', payload: {}, expected: {}, operation: 'taxonomy:category:create', readback: async () => current, retryOnExactAbsence: true, confirmExactAbsence: async () => true });
  assert.equal(result.status, 'reconciled_success'); assert.equal(sends, 2);
});
test('readback mismatch stops instead of blind retry', async () => {
  const client = clientFor({ response: { status: 503, contentType: 'text/plain' } });
  const result = await savePostDraft({ client, siteKey: 'demo-site', authorizationContext: articleAuth('update'), ...ids, defaults: base, readback: async () => articleRecord({ ...base, ...ids, content: [] }, 'draft') });
  assert.equal(result.status, 'stopped_manual_intervention'); assert.equal(client.calls.length, 1);
});
test('deletePost treats exact absence as success and uses list route', async () => {
  const client = clientFor(); const result = await deletePost({ client, siteKey: 'demo-site', authorizationContext: articleAuth('delete'), siteId: ids.siteId, postId: ids.postId, readback: async () => null });
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(client.calls[0].route, '/demo-site/posts?tab=list'); assert.deepEqual(client.calls[0].payload, { id: ids.postId, siteId: ids.siteId });
});
const createExtractors = {
  getCreatedPostId: (actual) => actual?.record?.id,
  getCreatedPostSiteId: (actual) => actual?.record?.siteId,
  getAfterPostIds: (actual) => actual?.afterPostIds,
};
// P0-3.3a.3: the canonical expected comparison is owned by createPostDraft
// itself — the bottom layer extracts the record (host {record, afterPostIds}
// wrapper or bare record) and compares every contract field plus siteId. These
// direct bottom-layer tests pass no matcher at all; `match` is only ever an
// extra AND-ed constraint.
// 2026-09-04 stable create payload B1: the authorization context is minted
// over the exact prepared snapshot (the same object whose canonical
// payloadText the bottom layer sends), mirroring the canonical driver handoff.
function createDraftBase(overrides = {}) {
  // Mirrors the canonical driver: one payload object (contract fields plus
  // siteId) is passed as both `payload` and `expected`, by reference.
  const payload = { ...base, siteId: ids.siteId };
  const prepared = prepareStableCreatePayload('article', payload, ids.siteId);
  return {
    siteKey: 'demo-site',
    authorizationContext: createDraftAuth(prepared.snapshot),
    siteId: ids.siteId,
    payload,
    expected: payload,
    beforePostIds: ['post-1', 'post-2'],
    ...createExtractors,
    editorReopen: async (postId) => ({ status: 200, authenticated: true, healthy: true, postId }),
    ...overrides,
  };
}
test('createPostDraft proves the sole before/after delta, same site, and editor reopen evidence', async () => {
  let created = null;
  const client = clientFor({ onSend: async ({ payload }) => { created = { ...payload, id: 'post-new-1' }; } });
  const reopened = [];
  const result = await createPostDraft(createDraftBase({
    client,
    readback: async () => ({ record: created, afterPostIds: ['post-2', 'post-1', 'post-new-1'] }),
    editorReopen: async (postId) => { reopened.push(postId); return { status: 200, authenticated: true, healthy: true, postId }; },
  }));
  assert.equal(result.status, 'mutation_succeeded');
  assert.equal(result.createdPostId, 'post-new-1');
  assert.equal(result.editorReopen.postId, 'post-new-1');
  assert.deepEqual(reopened, ['post-new-1']);
  assert.equal(result.automaticRetryAllowed, false);
  assert.equal(client.calls.length, 1);
  assert.equal(client.calls[0].route, '/demo-site/posts');
  assert.equal(client.calls[0].actionName, 'postCreate');
  // 2026-09-04 stable create payload: the wire payload is the prepared frozen
  // snapshot (cover alt is normalized away), not the raw spread of `base`.
  const prepared = prepareStableCreatePayload('article', { ...base, siteId: ids.siteId }, ids.siteId);
  assert.deepEqual(client.calls[0].payload, prepared.snapshot);
});
test('createPostDraft sends postCreate through the runtime action client under the exact payload digest', async () => {
  let received = null;
  const created = { ...base, siteId: ids.siteId, id: 'post-new-9' };
  const result = await createPostDraft(createDraftBase({
    runtime,
    request: async (details) => { received = details; return { status: 200, contentType: 'text/x-component' }; },
    beforePostIds: ['post-1'],
    readback: async () => ({ record: created, afterPostIds: ['post-1', 'post-new-9'] }),
  }));
  assert.equal(result.status, 'mutation_succeeded');
  assert.equal(received.url, 'https://workspace.laicms.com/demo-site/posts');
  assert.equal(received.headers['next-action'], 'create-action');
  assert.equal(received.headers['x-deployment-id'], 'd'.repeat(40));
  // B2: the native wire body is exactly [payloadText] and the inner bytes are
  // the canonical serialization of the sent frozen snapshot.
  const prepared = prepareStableCreatePayload('article', { ...base, siteId: ids.siteId }, ids.siteId);
  assert.equal(received.body, `[${prepared.payloadText}]`);
  assert.deepEqual(JSON.parse(received.body), [prepared.snapshot]);
});
test('createPostDraft refuses a payload that drifts from the authorization digest before any request', async () => {
  const client = clientFor();
  await assert.rejects(() => createPostDraft(createDraftBase({
    client,
    authorizationContext: createDraftAuth({ ...base, siteId: ids.siteId, title: '另一篇文章' }),
    readback: async () => null,
  })), /target_digest|payload/);
  assert.equal(client.calls.length, 0);
});
test('createPostDraft blocks duplicate snapshots, multi-delta results, cross-site records, and field drift', async () => {
  await assert.rejects(() => createPostDraft(createDraftBase({
    client: clientFor(),
    beforePostIds: ['post-1', ' post-1 '],
    readback: async () => null,
  })), /duplicate IDs/);
  const cases = [
    {
      label: 'two new IDs after create',
      record: { ...base, siteId: ids.siteId, id: 'post-new-1' },
      afterPostIds: ['post-1', 'post-2', 'post-new-1', 'post-new-2'],
      pattern: /exactly one new article ID after create, found 2/,
    },
    {
      label: 'created record belongs to another site',
      record: { ...base, siteId: 'other-site', id: 'post-new-1' },
      afterPostIds: ['post-1', 'post-2', 'post-new-1'],
      pattern: /different site/,
    },
    {
      label: 'created ID is not the sole snapshot difference',
      record: { ...base, siteId: ids.siteId, id: 'post-9' },
      afterPostIds: ['post-1', 'post-2', 'post-new-1'],
      pattern: /sole before\/after snapshot difference/,
    },
    {
      label: 'created record drifted from the expected fields',
      record: { ...base, siteId: ids.siteId, id: 'post-new-1', title: '丢失标题' },
      afterPostIds: ['post-1', 'post-2', 'post-new-1'],
      pattern: /did not match the canonical expected readback/,
    },
  ];
  for (const testCase of cases) {
    const client = clientFor();
    const result = await createPostDraft(createDraftBase({
      client,
      readback: async () => ({ record: testCase.record, afterPostIds: testCase.afterPostIds }),
    }));
    assert.equal(result.status, 'stopped_manual_intervention', testCase.label);
    assert.equal(result.createdPostId, null, testCase.label);
    assert.equal(result.automaticRetryAllowed, false, testCase.label);
    assert.equal(client.calls.length, 1, testCase.label);
    assert.match(result.mismatches.join('; '), testCase.pattern, testCase.label);
  }
});
test('createPostDraft fails closed before any request when required inputs are missing', async () => {
  for (const drop of ['readback', 'getCreatedPostId', 'getCreatedPostSiteId', 'getAfterPostIds', 'editorReopen']) {
    const client = clientFor();
    const options = createDraftBase({ client, readback: async () => null });
    delete options[drop];
    await assert.rejects(() => createPostDraft(options), /callback is required/, drop);
    assert.equal(client.calls.length, 0, drop);
  }
  for (const [label, mutate, pattern] of [
    ['payload not an object', (options) => { options.payload = ['not-an-object']; }, /payload must be an object/],
    ['payload siteId conflict', (options) => { options.payload.siteId = 'other-site'; }, /must match siteId/],
    ['expected missing (P0-3.3a.1)', (options) => { delete options.expected; }, /expected must be a non-array object/],
    ['expected explicit undefined (P0-3.3a.1)', (options) => { options.expected = undefined; }, /expected must be a non-array object/],
    ['expected equal but separate object (P0-3.3a.1)', (options) => { options.expected = { ...options.payload }; }, /same object reference/],
    ['expectedMatch supplied (P0-3.3a.3)', (options) => { options.expectedMatch = () => true; }, /expectedMatch has been removed/],
    ['match not a function (P0-3.3a.2)', (options) => { options.match = 'permissive-string'; }, /match must be a function/],
    ['before snapshot missing', (options) => { delete options.beforePostIds; }, /beforePostIds snapshot is required/],
    ['retry budget non-zero', (options) => { options.maxControlledRetries = 1; }, /maxControlledRetries must be 0/],
  ]) {
    const client = clientFor();
    const options = createDraftBase({ client, readback: async () => null });
    mutate(options);
    await assert.rejects(() => createPostDraft(options), pattern, label);
    assert.equal(client.calls.length, 0, label);
  }
});
test('createPostDraft refuses a non-object or array expected before any request', async () => {
  // P0-3.3a: a junk expected value (array, string, number, explicit null) would
  // silently degrade readback verification, so it is refused before the request.
  for (const [label, expected] of [['array', ['title']], ['string', 'title'], ['number', 3], ['null', null]]) {
    const client = clientFor();
    await assert.rejects(
      () => createPostDraft(createDraftBase({ client, expected, readback: async () => null })),
      /expected must be a non-array object/,
      label,
    );
    assert.equal(client.calls.length, 0, label);
  }
});
test('createPostDraft sends zero requests without expected or with an equal-but-separate expected object (P0-3.3a.1)', async () => {
  // Fail-closed: canonical create never runs without a bound expected readback,
  // and the expected readback must be the exact payload object reference (the
  // canonical driver passes one frozen object as both). Both refusals happen
  // before any client, provider, or request.
  for (const [label, mutate, pattern] of [
    ['no expected', (options) => { options.expected = undefined; }, /expected must be a non-array object/],
    ['null expected', (options) => { options.expected = null; }, /expected must be a non-array object/],
    ['equal but separate expected object', (options) => { options.expected = { ...options.payload }; }, /same object reference/],
  ]) {
    const client = clientFor();
    const options = createDraftBase({
      client,
      readback: async () => ({ record: { ...base, siteId: ids.siteId, id: 'post-new-1' }, afterPostIds: ['post-1', 'post-2', 'post-new-1'] }),
    });
    mutate(options);
    await assert.rejects(() => createPostDraft(options), pattern, label);
    assert.equal(client.calls.length, 0, label);
  }
});
test('createPostDraft rejects a drifted record even when a permissive custom match returns true (P0-3.3a.3, driver-style wrapper readback)', async () => {
  // The bottom layer owns the canonical expected comparison: even a match that
  // always returns true cannot wave a field-drifted created record through,
  // and no expectedMatch predicate exists that a caller could forge.
  const client = clientFor();
  const result = await createPostDraft(createDraftBase({
    client,
    match: () => true,
    readback: async () => ({
      record: { ...base, siteId: ids.siteId, id: 'post-new-1', title: '丢失标题' },
      afterPostIds: ['post-1', 'post-2', 'post-new-1'],
    }),
  }));
  assert.equal(result.status, 'stopped_manual_intervention');
  assert.equal(result.createdPostId, null);
  assert.equal(result.automaticRetryAllowed, false);
  assert.equal(client.calls.length, 1);
  assert.match(result.mismatches.join('; '), /did not match the canonical expected readback/);
  assert.match(result.mismatches.join('; '), /title drifted from the frozen expected payload/);
});
test('createPostDraft refuses every forged expectedMatch callback before any request (P0-3.3a.3)', async () => {
  // The public expectedMatch parameter is deleted: the canonical comparison
  // is bottom-layer logic, so supplying a permissive (or any) predicate is a
  // hard pre-request refusal — the historical `() => true` forgery bypass
  // cannot even reach the request.
  for (const [label, expectedMatch] of [
    ['always-true predicate', () => true],
    ['always-false predicate', () => false],
    ['throwing predicate', () => { throw new Error('boom'); }],
    ['non-function junk', 'permissive-string'],
  ]) {
    const client = clientFor();
    await assert.rejects(
      () => createPostDraft(createDraftBase({
        client,
        expectedMatch,
        readback: async () => ({ record: { ...base, siteId: ids.siteId, id: 'post-new-1' }, afterPostIds: ['post-1', 'post-2', 'post-new-1'] }),
      })),
      /expectedMatch has been removed/,
      label,
    );
    assert.equal(client.calls.length, 0, label);
  }
});
test('createPostDraft compares a bare raw record readback by default and cannot be bypassed there (P0-3.3a.3)', async () => {
  // Raw-record readback is natively supported (no wrapper, no extractor, no
  // matcher option), and the same irreplaceable comparison runs on it: a
  // drifted raw record plus a permissive match still stops.
  const rawGetters = {
    getCreatedPostId: (actual) => actual?.id,
    getCreatedPostSiteId: (actual) => actual?.siteId,
    getAfterPostIds: () => ['post-1', 'post-2', 'post-new-1'],
  };
  let created = null;
  const client = clientFor({ onSend: async ({ payload }) => { created = { ...payload, id: 'post-new-1' }; } });
  const pass = await createPostDraft(createDraftBase({
    client,
    ...rawGetters,
    readback: async () => created,
  }));
  assert.equal(pass.status, 'mutation_succeeded');
  assert.equal(pass.createdPostId, 'post-new-1');

  const driftClient = clientFor();
  const drift = await createPostDraft(createDraftBase({
    client: driftClient,
    ...rawGetters,
    match: () => true,
    readback: async () => ({ ...base, siteId: ids.siteId, id: 'post-new-1', slug: 'drifted-slug' }),
  }));
  assert.equal(drift.status, 'stopped_manual_intervention');
  assert.equal(driftClient.calls.length, 1);
  assert.match(drift.mismatches.join('; '), /slug drifted from the frozen expected payload/);

  // A raw record missing one contract field is never defaulted into a pass.
  const missingClient = clientFor();
  const incomplete = { ...base, siteId: ids.siteId, id: 'post-new-1' };
  delete incomplete.excerpt;
  const missing = await createPostDraft(createDraftBase({
    client: missingClient,
    ...rawGetters,
    readback: async () => incomplete,
  }));
  assert.equal(missing.status, 'stopped_manual_intervention');
  assert.match(missing.mismatches.join('; '), /excerpt is missing from the created article record/);
});
test('createPostDraft fails closed on an empty or non-object wrapper record and on readback errors (P0-3.3a.3)', async () => {
  for (const [label, record, pattern] of [
    ['wrapper record null', null, /readback record must be a non-array object/],
    // 2026-09-04 stable create payload B2: an undefined-valued readback key is
    // refused by the stable capture itself (JSON data never carries undefined);
    // an explicit undefined record therefore fails closed even earlier.
    ['wrapper record undefined', undefined, /could not be captured as stable plain data/],
    ['wrapper record string', 'not-a-record', /readback record must be a non-array object/],
    ['wrapper record array', ['not-a-record'], /readback record must be a non-array object/],
  ]) {
    const client = clientFor();
    const result = await createPostDraft(createDraftBase({
      client,
      readback: async () => ({ record, afterPostIds: ['post-1', 'post-2', 'post-new-1'] }),
    }));
    assert.equal(result.status, 'stopped_manual_intervention', label);
    assert.equal(result.createdPostId, null, label);
    assert.equal(client.calls.length, 1, label);
    assert.match(result.mismatches.join('; '), pattern, label);
  }
  const throwingClient = clientFor();
  const failed = await createPostDraft(createDraftBase({
    client: throwingClient,
    readback: async () => { throw new Error('readback transport exploded'); },
  }));
  assert.equal(failed.status, 'stopped_manual_intervention');
  assert.equal(failed.readbackError, 'readback transport exploded');
  assert.equal(failed.automaticRetryAllowed, false);
  assert.equal(throwingClient.calls.length, 1);
});
test('createPostDraft passes with the same-reference expected and the bottom-owned canonical comparison', async () => {
  // Legitimate positive path: expected is the exact payload object and the
  // bottom layer compares every contract field of the extracted record itself.
  const options = createDraftBase({});
  assert.equal(options.expected, options.payload, 'the fixture must bind expected to the exact payload reference');
  let created = null;
  const client = clientFor({ onSend: async ({ payload }) => { created = { ...payload, id: 'post-new-1' }; } });
  const result = await createPostDraft({ ...options, client, readback: async () => ({ record: created, afterPostIds: ['post-1', 'post-2', 'post-new-1'] }) });
  assert.equal(result.status, 'mutation_succeeded');
  assert.equal(result.createdPostId, 'post-new-1');
  assert.equal(client.calls.length, 1);
});
test('createPostDraft stops without resend when the reopened editor is not healthy', async () => {
  for (const [label, reopen, pattern] of [
    ['HTTP 404 editor', async (postId) => ({ status: 404, authenticated: false, healthy: false, postId }), /HTTP 200/],
    ['wrong post editor', async () => ({ status: 200, authenticated: true, healthy: true, postId: 'other-post' }), /does not match the created article/],
    ['unauthenticated editor', async (postId) => ({ status: 200, authenticated: false, healthy: true, postId }), /not authenticated/],
  ]) {
    let created = null;
    const client = clientFor({ onSend: async ({ payload }) => { created = { ...payload, id: 'post-new-1' }; } });
    let reopens = 0;
    const result = await createPostDraft(createDraftBase({
      client,
      readback: async () => ({ record: created, afterPostIds: ['post-1', 'post-2', 'post-new-1'] }),
      editorReopen: async (postId) => { reopens += 1; return reopen(postId); },
    }));
    assert.equal(result.status, 'stopped_manual_intervention', label);
    assert.equal(result.automaticRetryAllowed, false, label);
    assert.equal(result.createdPostId, 'post-new-1', label);
    assert.equal(reopens, 1, label);
    assert.equal(client.calls.length, 1, label);
    assert.match(result.mismatches.join('; '), pattern, label);
  }
});
test('createPostDraft never blindly resends after a transport exception', async () => {
  let sends = 0;
  const lost = { async send() { sends += 1; throw new Error('connection lost after send'); } };
  const unknown = await createPostDraft(createDraftBase({
    client: lost,
    readback: async () => null,
  }));
  assert.equal(unknown.status, 'stopped_manual_intervention');
  assert.equal(unknown.requestStarted, true);
  assert.equal(unknown.automaticRetryAllowed, false);
  assert.equal(sends, 1);
  let record = null;
  let recoveringSends = 0;
  const recovering = {
    async send({ payload }) { recoveringSends += 1; record = { ...payload, id: 'post-new-1' }; throw new Error('connection lost after send'); },
  };
  const recovered = await createPostDraft(createDraftBase({
    client: recovering,
    readback: async () => ({ record, afterPostIds: ['post-1', 'post-new-1'] }),
  }));
  assert.equal(recovered.status, 'reconciled_success');
  assert.equal(recovered.createdPostId, 'post-new-1');
  assert.equal(recovered.automaticRetryAllowed, false);
  assert.equal(recoveringSends, 1);
});
test('category create verifies every supplied field, exact ID, and site ownership', async () => {
  let current = null; const client = clientFor({ onSend: async ({ payload }) => { current = { ...payload, id: ids.categoryId }; } });
  const cover = { name: 'category-cover.webp', type: 'image', source: 'oss', path: 'site/category-cover.webp' };
  const options = { client, siteKey: 'demo-site', authorizationContext: taxonomyAuth('category', 'create', { slug: 'child' }), siteId: ids.siteId, name: '子分类', slug: 'child', description: '完整说明', cover, parent: 'parent-1', order: 7, existing: [], readback: async () => current };
  const result = await createPostCategory(options);
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(result.readback.id, ids.categoryId); assert.equal(client.calls[0].route, '/demo-site/posts?tab=categories'); assert.deepEqual(client.calls[0].payload, { siteId: ids.siteId, contentType: 'posts', name: '子分类', slug: 'child', order: 7, description: '完整说明', cover, parent: 'parent-1' });
  current = { ...current, description: '丢失后的说明' };
  const mismatch = await createPostCategory({ ...options, client: clientFor() });
  assert.equal(mismatch.status, 'stopped_manual_intervention'); assert.ok(mismatch.mismatches.includes('description'));
  current = { ...client.calls[0].payload };
  const missingId = await createPostCategory({ ...options, client: clientFor() });
  assert.equal(missingId.status, 'stopped_manual_intervention'); assert.match(missingId.mismatches.join('; '), /created category.id is required/);
});
test('taxonomy create accepts route-scoped readback that omits contentType', async () => {
  let category = null;
  const categoryClient = clientFor({ onSend: async ({ payload }) => {
    const { contentType, ...routeScopedRecord } = payload;
    category = { ...routeScopedRecord, id: ids.categoryId };
  } });
  const categoryResult = await createPostCategory({
    client: categoryClient, siteKey: 'demo-site',
    authorizationContext: taxonomyAuth('category', 'create', { slug: 'route-scoped-category' }),
    siteId: ids.siteId, name: '路由限定分类', slug: 'route-scoped-category',
    existing: [], readback: async () => category,
  });
  assert.equal(categoryResult.status, 'mutation_succeeded');
  assert.equal(Object.hasOwn(categoryResult.readback, 'contentType'), false);

  let tag = null;
  const tagClient = clientFor({ onSend: async ({ payload }) => {
    const { contentType, ...routeScopedRecord } = payload;
    tag = { ...routeScopedRecord, id: ids.tagId };
  } });
  const tagResult = await createPostTag({
    client: tagClient, siteKey: 'demo-site',
    authorizationContext: taxonomyAuth('tag', 'create', { slug: 'route-scoped-tag' }),
    siteId: ids.siteId, name: '路由限定标签', slug: 'route-scoped-tag',
    existing: [], readback: async () => tag,
  });
  assert.equal(tagResult.status, 'mutation_succeeded');
  assert.equal(Object.hasOwn(tagResult.readback, 'contentType'), false);
});

test('taxonomy create rejects an explicit conflicting contentType', async () => {
  const client = clientFor({ onSend: async () => {} });
  const result = await createPostCategory({
    client, siteKey: 'demo-site',
    authorizationContext: taxonomyAuth('category', 'create', { slug: 'wrong-scope' }),
    siteId: ids.siteId, name: '错误范围', slug: 'wrong-scope',
    existing: [],
    readback: async () => ({
      id: ids.categoryId, siteId: ids.siteId, name: '错误范围', slug: 'wrong-scope',
      cover: null, order: 0, contentType: 'products',
    }),
  });
  assert.equal(result.status, 'stopped_manual_intervention');
  assert.deepEqual(result.mismatches, ['contentType']);
  assert.equal(client.calls.length, 1);
});

test('tag create verifies all fields and blocks duplicate slug before request', async () => {
  const duplicateClient = clientFor(); assert.throws(() => createPostTag({ client: duplicateClient, siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'create', { slug: 'same' }), siteId: ids.siteId, name: '重复', slug: 'same', existing: [{ siteId: ids.siteId, slug: 'same' }], readback: async () => null }), /already exists/); assert.equal(duplicateClient.calls.length, 0);
  const unscopedClient = clientFor(); assert.throws(() => createPostTag({ client: unscopedClient, siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'create', { slug: 'same' }), siteId: ids.siteId, name: '重复', slug: 'same', existing: [{ slug: 'same' }], readback: async () => null }), /tag\[0\]\.siteId is required/); assert.equal(unscopedClient.calls.length, 0);
  const foreignClient = clientFor(); assert.throws(() => createPostTag({ client: foreignClient, siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'create', { slug: 'same' }), siteId: ids.siteId, name: '重复', slug: 'same', existing: [{ siteId: 'other-site', slug: 'other' }, { slug: 'same' }], readback: async () => null }), /tag\[1\]\.siteId is required/); assert.equal(foreignClient.calls.length, 0);
  let current = null; const client = clientFor({ onSend: async ({ payload }) => { current = { ...payload, id: ids.tagId }; } });
  const result = await createPostTag({ client, siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'create', { slug: 'full-tag' }), siteId: ids.siteId, name: '完整标签', slug: 'full-tag', description: '标签说明', existing: [], readback: async () => current });
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(result.readback.id, ids.tagId); assert.equal(result.readback.description, '标签说明');
});
test('category update and delete use distinct payloads', async () => {
  let current = null; const updateClient = clientFor({ onSend: async ({ payload }) => { current = { ...payload }; } });
  const updated = await updatePostCategory({ client: updateClient, siteKey: 'demo-site', authorizationContext: taxonomyAuth('category', 'update', { id: ids.categoryId }), id: ids.categoryId, siteId: ids.siteId, name: '新名', slug: 'new-name', readback: async () => current });
  assert.equal(updated.status, 'mutation_succeeded'); assert.equal(updateClient.calls[0].payload.id, ids.categoryId);
  const deleteClient = clientFor(); const deleted = await deletePostCategory({ client: deleteClient, siteKey: 'demo-site', authorizationContext: taxonomyAuth('category', 'delete', { id: ids.categoryId }), id: ids.categoryId, siteId: ids.siteId, readback: async () => null });
  assert.equal(deleted.status, 'mutation_succeeded'); assert.deepEqual(deleteClient.calls[0].payload, { id: ids.categoryId, siteId: ids.siteId, contentType: 'posts' });
});
test('tag update and delete use current-site IDs', async () => {
  let current = null; const updateClient = clientFor({ onSend: async ({ payload }) => { current = { ...payload }; } });
  const updated = await updatePostTag({ client: updateClient, siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'update', { id: ids.tagId }), id: ids.tagId, siteId: ids.siteId, name: '标签', slug: 'tag', readback: async () => current });
  assert.equal(updated.status, 'mutation_succeeded'); assert.equal(updateClient.calls[0].route, '/demo-site/posts?tab=tags');
  const deleteClient = clientFor(); const deleted = await deletePostTag({ client: deleteClient, siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'delete', { id: ids.tagId }), id: ids.tagId, siteId: ids.siteId, readback: async () => null });
  assert.equal(deleted.status, 'mutation_succeeded'); assert.equal(deleteClient.calls[0].payload.id, ids.tagId);
});
test('taxonomy mutations enforce the controlled retry budget', async () => {
  await assert.rejects(() => updatePostTag({ client: clientFor(), siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'update', { id: ids.tagId }), id: ids.tagId, siteId: ids.siteId, name: '标签', slug: 'tag', maxControlledRetries: 2, readback: async () => null }), /maxControlledRetries must be 0 or 1/);
  const client = clientFor({ response: { status: 503, contentType: 'text/plain' } });
  const result = await updatePostTag({ client, siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'update', { id: ids.tagId }), id: ids.tagId, siteId: ids.siteId, name: '标签', slug: 'tag', maxControlledRetries: 0, readback: async () => null });
  assert.equal(result.status, 'stopped_manual_intervention');
  assert.equal(client.calls.length, 1);
});
test('serial batch skips completed items and stops on first ambiguous result', async () => {
  const executed = []; const result = await runArticleBatchSerial({ items: [{ key: 'a' }, { key: 'b' }, { key: 'c' }], completedKeys: ['a'], execute: async (item) => { executed.push(item.key); return item.key === 'b' ? { status: 'stopped_manual_intervention' } : { status: 'mutation_succeeded' }; } });
  assert.deepEqual(executed, ['b']); assert.equal(result.status, 'stopped'); assert.deepEqual(result.skipped, ['a']); assert.equal(result.stopped.key, 'b');
});
test('serial batch handles 50 items without parallelism', async () => {
  const active = { value: 0, max: 0 }; const result = await runArticleBatchSerial({ items: Array.from({ length: 50 }, (_, i) => ({ key: `item-${i}` })), execute: async () => { active.value += 1; active.max = Math.max(active.max, active.value); await new Promise((resolve) => setTimeout(resolve, 0)); active.value -= 1; return { status: 'mutation_succeeded' }; } });
  assert.equal(result.status, 'completed'); assert.equal(result.completed.length, 50); assert.equal(active.max, 1);
});
test('serial batch refuses over-limit runs before execution', async () => {
  await assert.rejects(() => runArticleBatchSerial({ items: Array.from({ length: 51 }, (_, i) => ({ key: String(i) })), execute: async () => ({ status: 'mutation_succeeded' }) }), /safety limit/);
});
test('generic recovery reports manual intervention when readback is unavailable', async () => {
  const client = clientFor({ response: { status: 503, contentType: 'text/plain' } }); const result = await runActionWithRecovery({ client, route: '/x', actionName: 'postUpdate', payload: {}, expected: {}, readback: async () => { throw new Error('RSC unavailable'); }, operation: 'test' });
  assert.equal(result.status, 'stopped_manual_intervention'); assert.equal(result.automaticRetryAllowed, false);
});
test('recovery converts compare exceptions into manual intervention', async () => {
  const client = clientFor({ response: { status: 200, contentType: 'text/x-component' } });
  const result = await runActionWithRecovery({ client, route: '/x', actionName: 'postUpdate', payload: {}, expected: {}, readback: async () => ({ ok: true }), compare: () => { throw new Error('readback shape changed'); }, operation: 'test' });
  assert.equal(result.status, 'stopped_manual_intervention');
  assert.equal(result.error, 'readback shape changed');
  assert.equal(result.automaticRetryAllowed, false);
});

// Article body format profile and deterministic Markdown conversion regression tests.
function collectIds(value, ids = []) {
  if (Array.isArray(value)) {
    for (const item of value) collectIds(item, ids);
  } else if (value && typeof value === 'object') {
    if (typeof value.id === 'string') ids.push(value.id);
    for (const child of Object.values(value)) collectIds(child, ids);
  }
  return ids;
}

test('format matrix preserves 12 verified, one blocked current shape, and zero untested candidates', () => {
  assert.equal(ALLINCMS_ARTICLE_FORMAT_SUPPORT.verified.length, 12);
  assert.deepEqual(ALLINCMS_ARTICLE_FORMAT_SUPPORT.unsupportedCurrentShape.map((item) => item.key), ['code-block']);
  assert.deepEqual(ALLINCMS_ARTICLE_FORMAT_SUPPORT.notTested, []);
  assert.match(ALLINCMS_ARTICLE_FORMAT_SUPPORT.unsupportedCurrentShape[0].policy, /Do not publish/);
});

test('canonical examples cover every verified candidate and use unique Slate IDs', () => {
  const examples = createCanonicalAllinCmsSlateExamples({ idPrefix: 'test-format' });
  assert.deepEqual(Object.keys(examples), ALLINCMS_ARTICLE_FORMAT_SUPPORT.verified);
  const ids = collectIds(examples);
  assert.equal(ids.length, new Set(ids).size);
  assert.equal(examples.bold.children[0].bold, true);
  assert.equal(examples.underline.children[0].underline, true);
  assert.equal(examples['inline-code'].children[0].code, true);
  assert.equal(examples['bulleted-list'].listStyleType, 'disc');
  assert.equal(examples['numbered-list'].listStyleType, 'decimal');
  assert.equal(examples.table.children[0].children[0].type, 'th');
  assert.equal(examples.table.children[1].children[0].type, 'td');
});

test('canonical examples are fresh clones and do not share caller mutations', () => {
  const first = createCanonicalAllinCmsSlateExamples();
  const second = createCanonicalAllinCmsSlateExamples();
  first.bold.children[0].text = 'changed';
  assert.equal(second.bold.children[0].text, 'Bold text');
});

test('Markdown converter emits verified block and inline shapes deterministically', () => {
  const source = [
    '## Section',
    '### Subsection',
    '**Bold** *Italic* <u>Underline</u> ~~Strike~~ `inline` [Reference](https://example.com/docs)',
    '- Bullet one',
    '1. Number one',
    '> Evidence needs readback.',
    '---',
    '| Field | Value |',
    '| --- | --- |',
    '| Format | Verified |',
  ].join('\n');
  const first = markdownToAllinCmsSlate(source, { idPrefix: 'article' });
  const second = markdownToAllinCmsSlate(source, { idPrefix: 'article' });
  assert.deepEqual(first, second);
  assert.deepEqual(first.map((node) => node.type), ['h2', 'h3', 'p', 'p', 'p', 'blockquote', 'hr', 'table']);
  const inline = first[2].children;
  assert.equal(inline.find((leaf) => leaf.bold)?.text, 'Bold');
  assert.equal(inline.find((leaf) => leaf.italic)?.text, 'Italic');
  assert.equal(inline.find((leaf) => leaf.underline)?.text, 'Underline');
  assert.equal(inline.find((leaf) => leaf.strikethrough)?.text, 'Strike');
  assert.equal(inline.find((leaf) => leaf.code)?.text, 'inline');
  assert.equal(inline.find((child) => child.type === 'a')?.url, 'https://example.com/docs');
  assert.equal(first[3].listStyleType, 'disc');
  assert.equal(first[4].listStyleType, 'decimal');
  assert.equal(first[7].children[0].children[0].type, 'th');
  assert.equal(first[7].children[1].children[0].type, 'td');
});

test('Markdown converter joins ordinary paragraph lines with a single space', () => {
  const nodes = markdownToAllinCmsSlate('First line\nsecond line', { idPrefix: 'paragraph' });
  assert.equal(nodes.length, 1);
  assert.deepEqual(nodes[0].children, [{ text: 'First line second line' }]);
});

test('Markdown converter blocks fenced and indented code blocks before payload construction', () => {
  assert.throws(() => markdownToAllinCmsSlate('```js\nalert(1)\n```'), /code blocks are unsupported-current-shape/);
  assert.throws(() => markdownToAllinCmsSlate('    const blocked = true;'), /code blocks are unsupported-current-shape/);
  assert.throws(() => markdownToAllinCmsSlate('     const stillBlocked = true;'), /code blocks are unsupported-current-shape/);
  assert.throws(() => markdownToAllinCmsSlate('\tconst tabBlocked = true;'), /code blocks are unsupported-current-shape/);
});

test('Markdown converter blocks body H1, raw HTML, Markdown images, unsafe links, and unsupported tables', () => {
  assert.throws(() => markdownToAllinCmsSlate('# Duplicate article title'), /H1 is not allowed/);
  assert.throws(() => markdownToAllinCmsSlate('<div>raw HTML</div>'), /Raw HTML is unsupported/);
  assert.throws(() => markdownToAllinCmsSlate('<!-- hidden raw HTML -->'), /Raw HTML is unsupported/);
  assert.throws(() => markdownToAllinCmsSlate('![Alt](https://example.com/image.webp)'), /article-image-binding\.mjs/);
  assert.throws(() => markdownToAllinCmsSlate('![Alt][hero]\n\n[hero]: https://example.com/image.webp'), /article-image-binding\.mjs/);
  assert.throws(() => markdownToAllinCmsSlate('[Reference][source]\n\n[source]: https://example.com/'), /Reference-style Markdown links are unsupported/);
  assert.throws(() => markdownToAllinCmsSlate('[Unsafe](javascript:alert(1))'), /http\(s\)/);
  assert.throws(() => markdownToAllinCmsSlate('### Supported\n\n#### Unsupported'), /H4-H6 are unsupported/);
  assert.throws(() => markdownToAllinCmsSlate('Setext title\n---'), /Setext headings are unsupported/);
  assert.throws(() => markdownToAllinCmsSlate('| A | B |\n| --- | --- |\n| only one |'), /same number of cells/);
  assert.throws(() => markdownToAllinCmsSlate('| A | B |\n| --- | --- |'), /at least one body row/);
  assert.throws(() => markdownToAllinCmsSlate('| A | B |\n| :--- | ---: |\n| 1 | 2 |'), /alignment markers are unsupported/);
});

test('Markdown converter rejects unsafe ID prefixes', () => {
  assert.throws(() => markdownToAllinCmsSlate('Paragraph', { idPrefix: '../bad' }), /safe identifier prefix/);
  assert.throws(() => createCanonicalAllinCmsSlateExamples({ idPrefix: '' }), /safe identifier prefix/);
});
