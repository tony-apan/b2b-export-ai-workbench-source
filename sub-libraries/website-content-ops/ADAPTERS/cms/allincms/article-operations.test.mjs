import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ARTICLE_FIELDS,
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
test('article payload blocks invalid Slate and non-integer order before request', () => {
  assert.throws(() => buildArticlePayload({ defaults: base, overrides: { order: '2' }, ...ids }), /integer/);
  assert.throws(() => buildArticlePayload({ defaults: base, overrides: { content: '<p>bad</p>' }, ...ids }), /Slate/);
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
test('taxonomy slug duplicate is scoped to same site', () => {
  assert.throws(() => assertNoDuplicateSlug([{ siteId: ids.siteId, slug: 'same' }], 'same', ids.siteId, 'tag'), /already exists/);
  assert.doesNotThrow(() => assertNoDuplicateSlug([{ siteId: 'other-site', slug: 'same' }], 'same', ids.siteId, 'tag'));
  assert.throws(() => assertSameSite({ siteId: 'other-site' }, ids.siteId, 'tag'), /different site/);
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
test('unpublishPost requires and verifies draft readback', async () => {
  let current = articleRecord({ ...base, ...ids, mode: 'publish' }, 'published'); const client = clientFor({ onSend: async ({ payload }) => { current = articleRecord(payload, 'draft'); } });
  const result = await unpublishPost({ client, siteKey: 'demo-site', authorizationContext: articleAuth('unpublish'), ...ids, defaults: base, readback: async () => current });
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(result.readback.status, 'draft');
});
test('503 reconciles to success without resend when record is present', async () => {
  let current = null; const client = clientFor({ response: { status: 503, contentType: 'text/plain' }, onSend: async ({ payload }) => { current = articleRecord(payload, 'draft'); } });
  const result = await savePostDraft({ client, siteKey: 'demo-site', authorizationContext: articleAuth('update'), ...ids, defaults: base, readback: async () => current });
  assert.equal(result.status, 'reconciled_success'); assert.equal(client.calls.length, 1);
});
test('503 plus exact absence does not retry an existing article without explicit absence proof', async () => {
  let current = null; let sends = 0; const client = clientFor({ response: () => ({ status: 503, contentType: 'text/plain' }), onSend: async ({ payload }) => { sends += 1; if (sends === 2) current = articleRecord(payload, 'draft'); } });
  const result = await savePostDraft({ client, siteKey: 'demo-site', authorizationContext: articleAuth('update'), ...ids, defaults: base, readback: async () => current });
  assert.equal(result.status, 'stopped_manual_intervention'); assert.equal(sends, 1);
});
test('503 plus exact absence permits one controlled retry only with explicit absence proof', async () => {
  let current = null; let sends = 0; const client = clientFor({ response: () => ({ status: 503, contentType: 'text/plain' }), onSend: async ({ payload }) => { sends += 1; if (sends === 2) current = articleRecord(payload, 'draft'); } });
  const result = await runActionWithRecovery({ client, route: '/x', actionName: 'postCreate', payload: {}, expected: {}, operation: 'post:create', readback: async () => current, retryOnExactAbsence: true, confirmExactAbsence: async () => true });
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
test('createPostDraft requires a live create contract and exact created ID', async () => {
  let current = null; const client = clientFor({ onSend: async ({ payload }) => { current = { id: ids.postId, siteId: payload.siteId, title: 'Untitled Post' }; } });
  await assert.rejects(() => createPostDraft({ client, siteKey: 'demo-site', authorizationContext: createDraftAuth({ siteId: ids.siteId }), siteId: ids.siteId, payload: { siteId: ids.siteId }, readback: async () => current, match: (record) => record?.id === ids.postId, getCreatedPostId: (record) => record?.id }), /Live post-create contract/);
  const result = await createPostDraft({ client, siteKey: 'demo-site', authorizationContext: createDraftAuth({ siteId: ids.siteId }), createContractConfirmed: true, siteId: ids.siteId, payload: { siteId: ids.siteId }, beforePostIds: [], readback: async () => current, match: (record) => record?.id === ids.postId, getCreatedPostId: (record) => record?.id });
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(result.createdPostId, ids.postId); assert.equal(client.calls[0].route, '/demo-site/posts');
});
test('createPostDraft requires a before snapshot and rejects an existing ID as newly created', async () => {
  let current = null; const client = clientFor({ onSend: async ({ payload }) => { current = { id: ids.postId, siteId: payload.siteId }; } });
  await assert.rejects(() => createPostDraft({ client, siteKey: 'demo-site', authorizationContext: createDraftAuth({ siteId: ids.siteId }), createContractConfirmed: true, siteId: ids.siteId, payload: { siteId: ids.siteId }, readback: async () => current, match: () => true, getCreatedPostId: (record) => record?.id }), /beforePostIds snapshot/);
  const result = await createPostDraft({ client, siteKey: 'demo-site', authorizationContext: createDraftAuth({ siteId: ids.siteId }), createContractConfirmed: true, siteId: ids.siteId, payload: { siteId: ids.siteId }, beforePostIds: [ids.postId], readback: async () => current, match: () => true, getCreatedPostId: (record) => record?.id });
  assert.equal(result.status, 'stopped_manual_intervention');
  assert.match(result.mismatches.join('; '), /already existed/);
});
test('createPostDraft stops when readback has no exact created ID', async () => {
  let current = null; const client = clientFor({ onSend: async ({ payload }) => { current = { siteId: payload.siteId, title: 'Untitled Post' }; } });
  const result = await createPostDraft({ client, siteKey: 'demo-site', authorizationContext: createDraftAuth({ siteId: ids.siteId }), createContractConfirmed: true, siteId: ids.siteId, payload: { siteId: ids.siteId }, beforePostIds: [], readback: async () => current, match: () => true, getCreatedPostId: (record) => record?.id });
  assert.equal(result.status, 'stopped_manual_intervention');
  assert.match(result.mismatches.join('; '), /created post ID is missing/);
  assert.equal(result.createdPostId, null);
});
test('category create is taxonomy-first and confirms by slug', async () => {
  let current = null; const client = clientFor({ onSend: async ({ payload }) => { current = { ...payload, id: ids.categoryId }; } });
  const result = await createPostCategory({ client, siteKey: 'demo-site', authorizationContext: taxonomyAuth('category', 'create', { slug: 'root' }), siteId: ids.siteId, name: '根', slug: 'root', existing: [], readback: async () => current });
  assert.equal(result.status, 'mutation_succeeded'); assert.equal(client.calls[0].route, '/demo-site/posts?tab=categories'); assert.equal(client.calls[0].payload.contentType, 'posts');
});
test('tag create blocks duplicate slug before request', async () => {
  const client = clientFor(); assert.throws(() => createPostTag({ client, siteKey: 'demo-site', authorizationContext: taxonomyAuth('tag', 'create', { slug: 'same' }), siteId: ids.siteId, name: '重复', slug: 'same', existing: [{ siteId: ids.siteId, slug: 'same' }], readback: async () => null }), /already exists/); assert.equal(client.calls.length, 0);
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
