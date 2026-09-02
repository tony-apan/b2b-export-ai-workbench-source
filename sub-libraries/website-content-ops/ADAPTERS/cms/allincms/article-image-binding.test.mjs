import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { isAbsolute, join } from 'node:path';
import { tmpdir } from 'node:os';
import {
  _internal as bindingInternal,
  auditArticleImageBinding,
  bindAndSaveAllinCmsArticleDraftDirect,
  buildAllinCmsSlateContent,
  createArticleImageBindingManifest,
  readAllinCmsArticleDraftFromPage,
  replaceMarkdownImageOccurrences,
  saveAllinCmsArticleDraftDirect,
  tokenizeMarkdownImages,
  verifyArticleImageReadback,
  verifyArticleMediaMappings,
  verifyFreshArticleImageOccurrences,
  writeArticleImageBindingManifest,
} from './article-image-binding.mjs';
import { createAllinCmsArticleImageAuthorizationContext } from './mutation-authorization.mjs';

function articleImageAuth({
  siteKey = 'virtualsite',
  postId = '222222222222222222222222',
  approvedAt,
  expiresAt,
} = {}) {
  const approved = approvedAt || new Date(Date.now() - 1_000).toISOString();
  return createAllinCmsArticleImageAuthorizationContext({
    siteKey,
    postId,
    approvalActor: 'Tony test fixture',
    approvedAt: approved,
    expiresAt: expiresAt || new Date(Date.parse(approved) + 20 * 60 * 1000).toISOString(),
  });
}

async function fixture(files = { 'a.png': 'asset-a', 'b.png': 'asset-b', 'c.png': 'asset-c' }) {
  const dir = await mkdtemp(join(tmpdir(), 'allincms-article-images-'));
  for (const [name, value] of Object.entries(files)) {
    const target = join(dir, name);
    await mkdir(join(target, '..'), { recursive: true });
    await writeFile(target, value);
  }
  return dir;
}

async function manifestFor(markdown, files, metadata = {}) {
  const dir = await fixture(files);
  return {
    dir,
    markdown,
    manifest: await createArticleImageBindingManifest({
      sourceMarkdown: markdown,
      articleId: 'virtual-article',
      baseDir: dir,
      occurrenceMetadata: metadata,
      now: () => '2026-07-27T00:00:00.000Z',
    }),
  };
}

function mappingsFor(manifest) {
  return Object.fromEntries(manifest.assets.map((asset, index) => [asset.assetId, {
    status: 'verified',
    sourceSha256: asset.assetId,
    expectedTitle: `asset-${index + 1}`,
    mediaId: String(index + 1).padStart(24, '0'),
    url: `https://assets.laicms.com/virtualsite/image-${index + 1}.webp`,
    mimeType: 'image/webp',
    verification: { contractVerified: true, mediaRecordPresent: true, anonymousHttpsGet: true, browserImageDecodes: true },
  }]));
}
function candidatesFor(manifest) {
  return Object.fromEntries(manifest.assets.map((asset, index) => [asset.assetId, {
    sourceSha256: asset.assetId,
    expectedTitle: `asset-${index + 1}`,
    mediaId: String(index + 1).padStart(24, '0'),
    url: `https://assets.laicms.com/virtualsite/image-${index + 1}.webp`,
  }]));
}

function successfulImageSaveFixture() {
  const defaults = {
    title: 'T', slug: 't', excerpt: '', order: 0, coverImage: null,
    categories: [], tags: [], content: [{ type: 'p', id: 'old', children: [{ text: 'old' }] }],
  };
  const contract = {
    actionId: 'a'.repeat(40), actionIdLength: 40, actionIdSha256: 'hash',
    deploymentId: 'd'.repeat(40), deploymentFingerprint: 'd'.repeat(40), routerTree: '[]',
    draft: { siteId: '1'.repeat(24), defaults },
  };
  let sentPayload = null;
  let sendCount = 0;
  return {
    tab: {
      url: async () => 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update',
      playwright: {}, capabilities: {}, reload: async () => {},
    },
    internal: {
      cdp: { send: async () => ({}), readEvents: async () => ({ cursor: 1, events: [] }) },
      contract,
      cursor: { cursor: 1 },
      sendReplay: async ({ payload }) => {
        sendCount += 1;
        sentPayload = structuredClone(payload);
        return { status: 200, contentType: 'text/x-component' };
      },
      readCaptured: async () => ({ events: [
        { method: 'Network.requestWillBeSent', params: { requestId: 'r', request: { method: 'POST', url: 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update', postData: 'x' } } },
        { method: 'Network.responseReceived', params: { requestId: 'r', response: { status: 200, mimeType: 'text/x-component' } } },
      ] }),
      reloadPage: async () => {},
      readback: async () => ({ defaults: sentPayload }),
      verifyEditorPage: async () => ({ ok: true, error500: false, heading: '' }),
    },
    get sendCount() { return sendCount; },
    get sentPayload() { return sentPayload; },
  };
}

test('tokenizes three distinct image occurrences in source order', () => {
  const source = 'P1\n![A](a.png)\nP2\n![B](b.png)\nP3\n![C](c.png)\nP4';
  const result = tokenizeMarkdownImages(source);
  assert.deepEqual(result.occurrences.map((item) => item.destination), ['a.png', 'b.png', 'c.png']);
  assert.deepEqual(result.occurrences.map((item) => item.lineIndex), [1, 3, 5]);
});

test('one asset can produce multiple distinct occurrences', async () => {
  const { manifest } = await manifestFor('P1\n![A](a.png)\nP2\n![A again](a.png)\nP3', { 'a.png': 'same-bytes' });
  assert.equal(manifest.assets.length, 1);
  assert.equal(manifest.occurrences.length, 2);
  assert.equal(new Set(manifest.occurrences.map((item) => item.occurrenceId)).size, 2);
  assert.equal(new Set(manifest.occurrences.map((item) => item.assetId)).size, 1);
});

test('same filename with different content produces different asset IDs', async () => {
  const dir = await fixture({ 'one/a.png': 'one', 'two/a.png': 'two' });
  const markdown = '![one](one/a.png)\n![two](two/a.png)';
  const manifest = await createArticleImageBindingManifest({ sourceMarkdown: markdown, articleId: 'x', baseDir: dir });
  assert.equal(manifest.assets.length, 2);
  assert.notEqual(manifest.occurrences[0].assetId, manifest.occurrences[1].assetId);
});

test('same content from different paths reuses one asset ID', async () => {
  const { manifest } = await manifestFor('![one](a.png)\n![two](b.png)', { 'a.png': 'same', 'b.png': 'same' });
  assert.equal(manifest.assets.length, 1);
  assert.equal(manifest.occurrences[0].assetId, manifest.occurrences[1].assetId);
});

test('modified article invalidates the source hash', async () => {
  const { manifest, markdown } = await manifestFor('Before\n![A](a.png)\nAfter', { 'a.png': 'a' });
  assert.throws(() => replaceMarkdownImageOccurrences({
    sourceMarkdown: `${markdown}\nchanged`,
    manifest,
    mappings: mappingsFor(manifest),
  }), /Stale article image manifest/);
});

test('changed before/after anchor blocks binding even when source hash is forged', async () => {
  const { manifest, markdown } = await manifestFor('Before\n![A](a.png)\nAfter', { 'a.png': 'a' });
  manifest.occurrences[0].beforeAnchorSha256 = 'sha256:bad';
  assert.throws(() => replaceMarkdownImageOccurrences({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) }), /anchor mismatch/);
});

test('deleted remote media record stops verification', async () => {
  const { manifest } = await manifestFor('![A](a.png)', { 'a.png': 'a' });
  const tab = { url: async () => 'https://workspace.laicms.com/virtualsite/media' };
  await assert.rejects(() => verifyArticleMediaMappings({
    tab,
    expectedSiteKey: 'virtualsite',
    manifest,
    candidates: candidatesFor(manifest),
    reconcile: async () => ({ status: 'not_found_stop' }),
  }), /not_found_stop/);
});

test('URL with non-image content stops verification', async () => {
  const { manifest } = await manifestFor('![A](a.png)', { 'a.png': 'a' });
  const tab = { url: async () => 'https://workspace.laicms.com/virtualsite/media' };
  await assert.rejects(() => verifyArticleMediaMappings({
    tab,
    expectedSiteKey: 'virtualsite',
    manifest,
    candidates: candidatesFor(manifest),
    reconcile: async () => ({ status: 'reconciled_existing', media: { mediaId: '000000000000000000000001', url: 'https://assets.laicms.com/virtualsite/image-1.webp', mimeType: 'image/webp' }, image: { ok: true } }),
    verifyUrl: async () => { throw new Error('Content-Type is not an image'); },
  }), /Content-Type is not an image/);
});

test('image MIME without browser decode stops verification', async () => {
  const { manifest } = await manifestFor('![A](a.png)', { 'a.png': 'a' });
  const tab = { url: async () => 'https://workspace.laicms.com/virtualsite/media' };
  await assert.rejects(() => verifyArticleMediaMappings({
    tab,
    expectedSiteKey: 'virtualsite',
    manifest,
    candidates: candidatesFor(manifest),
    reconcile: async () => ({ status: 'reconciled_existing', media: { mediaId: '000000000000000000000001', url: 'https://assets.laicms.com/virtualsite/image-1.webp', mimeType: 'image/webp' }, image: { ok: false } }),
    verifyUrl: async () => ({ ok: true }),
  }), /Browser image decode failed/);
});

test('decorative image may have an empty alt', async () => {
  const dir = await fixture({ 'a.png': 'a' });
  const probe = await createArticleImageBindingManifest({
    sourceMarkdown: '![](a.png)',
    articleId: 'decorative',
    baseDir: dir,
    occurrenceMetadata: { '1': { role: 'decorative' } },
  });
  assert.equal(probe.occurrences[0].alt, '');
});

test('content image with empty alt is blocked', async () => {
  const dir = await fixture({ 'a.png': 'a' });
  await assert.rejects(() => createArticleImageBindingManifest({
    sourceMarkdown: '![](a.png)',
    articleId: 'content',
    baseDir: dir,
  }), /requires non-empty alt/);
});

test('A/B/A produces three image nodes but two assets', async () => {
  const markdown = 'P1\n![A](a.png "A caption")\nP2\n![B](b.png "B caption")\nP3\n![A again](a.png "A again caption")\nP4';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
  const result = await buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) });
  assert.equal(manifest.assets.length, 2);
  assert.deepEqual(result.content.filter((node) => node.type === 'img').map((node) => node.url), [
    'https://assets.laicms.com/virtualsite/image-1.webp',
    'https://assets.laicms.com/virtualsite/image-2.webp',
    'https://assets.laicms.com/virtualsite/image-1.webp',
  ]);
  assert.deepEqual(result.content.filter((node) => node.type === 'img').map((node) => node.caption), [
    [{ text: 'A caption' }],
    [{ text: 'B caption' }],
    [{ text: 'A again caption' }],
  ]);
});

test('swapped occurrence order is blocked', async () => {
  const markdown = '![A](a.png)\n![B](b.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
  manifest.occurrences.reverse();
  assert.throws(() => replaceMarkdownImageOccurrences({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) }), /order or position mismatch/);
});

test('missing occurrence is blocked', async () => {
  const markdown = '![A](a.png)\n![B](b.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
  manifest.occurrences.pop();
  assert.throws(() => replaceMarkdownImageOccurrences({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) }), /Occurrence count mismatch/);
});

test('Slate image node always contains the required empty text child', async () => {
  const markdown = '![A](a.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a' });
  const result = await buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) });
  assert.deepEqual(result.content[0].children, [{ text: '' }]);
  assert.equal(result.content.at(-1).type, 'p');
});

test('save failure after request is ambiguous and never auto-retried', async () => {
  const contract = {
    actionId: 'a'.repeat(40), actionIdLength: 40, actionIdSha256: 'hash', deploymentId: 'd'.repeat(40), deploymentFingerprint: 'd'.repeat(40), routerTree: '[]',
    draft: { siteId: '1'.repeat(24), defaults: { title: 'T', slug: 't', excerpt: '', order: 0, coverImage: null, categories: [], tags: [], content: [{ type: 'p', id: 'p', children: [{ text: '' }] }] } },
  };
  const tab = { url: async () => 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update', playwright: {}, capabilities: {} };
  await assert.rejects(async () => {
    try {
      await saveAllinCmsArticleDraftDirect({
        tab, expectedSiteKey: 'virtualsite', expectedPostId: '222222222222222222222222', authorizationContext: articleImageAuth(),
        overrides: {},
        _internal: {
          cdp: { send: async () => ({}), readEvents: async () => ({ cursor: 1, events: [] }) },
          contract,
          sendReplay: async () => { throw new Error('network uncertain'); },
        },
      });
    } catch (error) {
      assert.equal(error.result.status, 'article_save_ambiguous');
      assert.equal(error.result.automaticRetryAllowed, false);
      throw error;
    }
  }, /network uncertain/);
});

test('manifest write is atomic and leaves no lock', async () => {
  const dir = await fixture({});
  const path = join(dir, 'manifest.json');
  const result = await writeArticleImageBindingManifest({ manifestPath: path, manifest: { ok: true } });
  assert.equal(result.status, 'manifest_written_atomically');
  assert.deepEqual(JSON.parse(await readFile(path, 'utf8')), { ok: true });
  await assert.rejects(() => readFile(`${path}.lock`, 'utf8'), /ENOENT/);
});

test('existing manifest lock blocks a second writer', async () => {
  const dir = await fixture({});
  const path = join(dir, 'manifest.json');
  await writeFile(`${path}.lock`, 'held');
  await assert.rejects(() => writeArticleImageBindingManifest({ manifestPath: path, manifest: {} }), /is locked/);
});

test('implementation contains no Promise.all or worker-pool upload path', async () => {
  const source = await readFile(new URL('./article-image-binding.mjs', import.meta.url), 'utf8');
  assert.equal(/Promise\.all\s*\(/.test(source), false);
  assert.equal(/new\s+Worker\s*\(/.test(source), false);
});

test('ambiguous remote reconciliation stops the whole verification run', async () => {
  const { manifest } = await manifestFor('![A](a.png)\n![B](b.png)', { 'a.png': 'a', 'b.png': 'b' });
  const tab = { url: async () => 'https://workspace.laicms.com/virtualsite/media' };
  let calls = 0;
  await assert.rejects(() => verifyArticleMediaMappings({
    tab,
    expectedSiteKey: 'virtualsite',
    manifest,
    candidates: candidatesFor(manifest),
    reconcile: async () => { calls += 1; return { status: 'verification_failed' }; },
  }), /verification_failed/);
  assert.equal(calls, 1);
});

test('HTML images and reference-style images are blocked', () => {
  assert.throws(() => tokenizeMarkdownImages('<img src="a.png">'), /HTML <img>/);
  assert.throws(() => tokenizeMarkdownImages('![A][ref]\n[ref]: a.png'), /Reference-style/);
});

test('image-looking examples inside code are not occurrences', () => {
  const source = '`![inline](a.png)`\n```md\n![fenced](b.png)\n```\n![real](c.png)';
  assert.deepEqual(tokenizeMarkdownImages(source).occurrences.map((item) => item.destination), ['c.png']);
});

test('Slate conversion blocks image mixed with prose on one line', async () => {
  const markdown = 'Before ![A](a.png) after';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a' });
  await assert.rejects(() => buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) }), /image-only line/);
});

test('paragraph and A/B/A image positions survive conversion', async () => {
  const markdown = 'P1\n![A](a.png)\nP2\n![B](b.png)\nP3\n![A2](a.png)\nP4';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
  const result = await buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) });
  assert.deepEqual(result.content.map((node) => node.type), ['p', 'img', 'p', 'img', 'p', 'img', 'p']);
  assert.deepEqual(Object.values(result.audit), Array(Object.keys(result.audit).length).fill(0));
});

test('direct draft save forces mode update and verifies readback', async () => {
  const defaults = { title: 'T', slug: 't', excerpt: '', order: 0, coverImage: null, categories: [], tags: [], content: [{ type: 'p', id: 'p', children: [{ text: 'old' }] }] };
  const nextContent = [{ type: 'p', id: 'n', children: [{ text: 'new' }] }];
  const contract = { actionId: 'a'.repeat(40), actionIdLength: 40, actionIdSha256: 'hash', deploymentId: 'd'.repeat(40), deploymentFingerprint: 'd'.repeat(40), routerTree: '[]', draft: { siteId: '1'.repeat(24), defaults } };
  let sentPayload;
  const tab = { url: async () => 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update', playwright: {}, capabilities: {}, reload: async () => {} };
  await assert.rejects(() => saveAllinCmsArticleDraftDirect({
    tab, expectedSiteKey: 'virtualsite', expectedPostId: '222222222222222222222222', authorizationConfirmed: true,
    overrides: { content: nextContent },
    _internal: {
      cdp: { send: async () => ({}), readEvents: async () => ({ cursor: 1, events: [] }) },
      contract,
      sendReplay: async () => { sentPayload = 'request-started'; },
    },
  }), /structured authorizationContext/);
  assert.equal(sentPayload, undefined);
  await assert.rejects(() => saveAllinCmsArticleDraftDirect({
    tab, expectedSiteKey: 'virtualsite', expectedPostId: '222222222222222222222222', authorizationContext: articleImageAuth(),
    overrides: { coverImage: { name: 'cover.webp', alt: 'Cover alt', type: 'image', source: 'oss', path: 'x/cover.webp', size: 42 } },
    _internal: {
      cdp: { send: async () => ({}) },
      contract,
      sendReplay: async () => { sentPayload = 'request-started'; },
    },
  }), /missing canonical persisted fields: mimeType/);
  assert.equal(sentPayload, undefined);
  const result = await saveAllinCmsArticleDraftDirect({
    tab, expectedSiteKey: 'virtualsite', expectedPostId: '222222222222222222222222', authorizationContext: articleImageAuth(),
    overrides: { content: nextContent },
    _internal: {
      cdp: { send: async () => ({}), readEvents: async () => ({ cursor: 1, events: [] }) },
      contract,
      cursor: { cursor: 1 },
      sendReplay: async ({ payload }) => { sentPayload = payload; return { status: 200, contentType: 'text/x-component' }; },
      readCaptured: async () => ({ events: [
        { method: 'Network.requestWillBeSent', params: { requestId: 'r', request: { method: 'POST', url: 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update', postData: 'x' } } },
        { method: 'Network.responseReceived', params: { requestId: 'r', response: { status: 200, mimeType: 'text/x-component' } } },
      ] }),
      reloadPage: async () => {},
      readback: async () => ({ defaults: { ...defaults, content: nextContent } }),
      verifyEditorPage: async () => ({ ok: true, error500: false, heading: '' }),
    },
  });
  assert.equal(sentPayload.mode, 'update');
  assert.equal(result.published, false);
  assert.equal(result.status, 'draft_saved_and_readback_verified');
});

test('draft readback accepts the canonical persisted cover image subset', () => {
  const fullCover = {
    id: 'media-1', mediaId: 'media-1', title: 'Extended title', caption: 'Extended caption',
    url: 'https://assets.laicms.com/x/cover.webp',
    name: 'cover.webp', alt: 'Cover alt', type: 'image', source: 'oss',
    path: 'x/cover.webp', size: 42, mimeType: 'image/webp',
  };
  const persistedCover = {
    name: 'cover.webp', alt: 'Cover alt', type: 'image', source: 'oss',
    path: 'x/cover.webp', size: 42, mimeType: 'image/webp',
  };
  const payload = { title: 'T', slug: 't', excerpt: '', order: 0, coverImage: fullCover, categories: [], tags: [], content: [] };
  const readback = { ...payload, coverImage: persistedCover };
  assert.deepEqual(bindingInternal.compareReadback(payload, readback), []);
});

test('draft readback still rejects missing or changed canonical cover fields', () => {
  const cover = {
    name: 'cover.webp', alt: 'Cover alt', type: 'image', source: 'oss',
    path: 'x/cover.webp', size: 42, mimeType: 'image/webp',
  };
  const payload = { title: 'T', slug: 't', excerpt: '', order: 0, coverImage: cover, categories: [], tags: [], content: [] };
  const missingMimeType = { ...payload, coverImage: { ...cover } };
  delete missingMimeType.coverImage.mimeType;
  assert.deepEqual(bindingInternal.compareReadback(payload, missingMimeType), ['coverImage']);
  assert.throws(
    () => bindingInternal.normalizedDraftPayload(
      { ...payload, coverImage: missingMimeType.coverImage },
      {},
      '1'.repeat(24),
      '2'.repeat(24),
    ),
    /missing canonical persisted fields: mimeType/,
  );
  const changedPath = { ...payload, coverImage: { ...cover, path: 'x/other.webp' } };
  assert.deepEqual(bindingInternal.compareReadback(payload, changedPath), ['coverImage']);
});

test('readback verifier detects lost alt/caption', () => {
  const expected = [{ type: 'img', url: 'https://assets.laicms.com/x/a.webp', alt: 'A', caption: [{ text: 'Cap' }], children: [{ text: '' }], id: 'a' }];
  const actual = [{ type: 'img', url: 'https://assets.laicms.com/x/a.webp', children: [{ text: '' }], id: 'a' }];
  const manifest = { occurrences: [{ role: 'inline-detail' }] };
  const result = verifyArticleImageReadback({ expectedContent: expected, actualContent: actual, manifest });
  assert.equal(result.ok, false);
  assert.equal(result.missingAltCount, 1);
  assert.equal(result.missing_required_alt_in_backend_data, 1);
  assert.match(result.errors.join(' '), /alt/);
});

test('plain-string image caption is blocked before the save request', async () => {
  const content = [{ type: 'img', url: 'https://assets.laicms.com/x/a.webp', alt: 'A', caption: 'Cap', children: [{ text: '' }], id: 'a' }];
  const defaults = { title: 'T', slug: 't', excerpt: '', order: 0, coverImage: null, categories: [], tags: [], content: [] };
  const contract = { actionId: 'a'.repeat(40), actionIdLength: 40, actionIdSha256: 'hash', deploymentId: 'd'.repeat(40), deploymentFingerprint: 'd'.repeat(40), routerTree: '[]', draft: { siteId: '1'.repeat(24), defaults } };
  let requestStarted = false;
  const tab = { url: async () => 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update', playwright: {}, capabilities: { get: async () => ({ send: async () => ({}), readEvents: async () => ({ cursor: 1, events: [] }) }) } };
  await assert.rejects(() => saveAllinCmsArticleDraftDirect({
    tab, expectedSiteKey: 'virtualsite', expectedPostId: '222222222222222222222222', authorizationContext: articleImageAuth(),
    overrides: { content },
    _internal: {
      cdp: { send: async () => ({}), readEvents: async () => ({ cursor: 1, events: [] }) },
      contract,
      sendReplay: async () => { requestStarted = true; },
    },
  }), /caption must be a Slate text-node array/);
  assert.equal(requestStarted, false);

  const mixedCaptionContent = [{
    type: 'img',
    url: 'https://assets.laicms.com/x/a.webp',
    alt: 'A',
    caption: [{ text: 'Cap' }, 'hidden string bypass'],
    children: [{ text: '' }],
    id: 'a',
  }];
  await assert.rejects(() => saveAllinCmsArticleDraftDirect({
    tab, expectedSiteKey: 'virtualsite', expectedPostId: '222222222222222222222222', authorizationContext: articleImageAuth(),
    overrides: { content: mixedCaptionContent },
    _internal: {
      cdp: { send: async () => ({}), readEvents: async () => ({ cursor: 1, events: [] }) },
      contract,
      sendReplay: async () => { requestStarted = true; },
    },
  }), /caption must be a Slate text-node array/);
  assert.equal(requestStarted, false);
});

test('editor 500 after verified readback is not reported as success', async () => {
  const content = [{ type: 'p', id: 'p', children: [{ text: 'safe' }] }];
  const defaults = { title: 'T', slug: 't', excerpt: '', order: 0, coverImage: null, categories: [], tags: [], content };
  const contract = { actionId: 'a'.repeat(40), actionIdLength: 40, actionIdSha256: 'hash', deploymentId: 'd'.repeat(40), deploymentFingerprint: 'd'.repeat(40), routerTree: '[]', draft: { siteId: '1'.repeat(24), defaults } };
  const tab = { url: async () => 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update', playwright: {}, capabilities: {} };
  await assert.rejects(() => saveAllinCmsArticleDraftDirect({
    tab, expectedSiteKey: 'virtualsite', expectedPostId: '222222222222222222222222', authorizationContext: articleImageAuth(),
    overrides: { content },
    _internal: {
      cdp: { send: async () => ({}), readEvents: async () => ({ cursor: 1, events: [] }) },
      contract,
      cursor: { cursor: 1 },
      sendReplay: async () => ({ status: 200, contentType: 'text/x-component' }),
      readCaptured: async () => ({ events: [
        { method: 'Network.requestWillBeSent', params: { requestId: 'r', request: { method: 'POST', url: 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update', postData: 'x' } } },
        { method: 'Network.responseReceived', params: { requestId: 'r', response: { status: 200, mimeType: 'text/x-component' } } },
      ] }),
      reloadPage: async () => {},
      readback: async () => ({ defaults }),
      verifyEditorPage: async () => ({ ok: false, error500: true, heading: '500' }),
    },
  }), (error) => {
    assert.equal(error.result.status, 'article_editor_render_failed');
    assert.equal(error.result.readbackVerified, true);
    assert.equal(error.result.automaticRetryAllowed, false);
    return true;
  });
});

test('editor health gate requires the Slate editor, exact image count, decode, captions, and draft badge', async () => {
  const expectedContent = [
    { type: 'p', id: 'p1', children: [{ text: 'P1' }] },
    { type: 'img', id: 'a', url: 'https://assets.laicms.com/x/a.webp', alt: 'A', caption: [{ text: 'Cap A' }], children: [{ text: '' }] },
    { type: 'img', id: 'b', url: 'https://assets.laicms.com/x/b.webp', alt: 'B', caption: [{ text: 'Cap B' }], children: [{ text: '' }] },
  ];
  const healthy = await bindingInternal.verifyArticleEditorPage({
    expectedContent,
    tab: { playwright: { evaluate: async () => ({
      heading: '', bodyText: 'Update article', editorPresent: true,
      articleImageCount: 2, decodedArticleImageCount: 2, editorDomAltMissing: 2,
      visibleCaptions: ['Cap A', 'Cap B'], statusBadges: ['草稿'],
    }) } },
  });
  assert.equal(healthy.ok, true);
  assert.equal(healthy.editorDomAltMissing, 2);

  const broken = await bindingInternal.verifyArticleEditorPage({
    expectedContent,
    tab: { playwright: { evaluate: async () => ({
      heading: '', bodyText: 'Update article', editorPresent: true,
      articleImageCount: 2, decodedArticleImageCount: 1, editorDomAltMissing: 2,
      visibleCaptions: ['Cap A'], statusBadges: [],
    }) } },
  });
  assert.equal(broken.ok, false);
  assert.match(broken.errors.join('; '), /decode mismatch/);
  assert.match(broken.errors.join('; '), /captions/);
  assert.match(broken.errors.join('; '), /draft status/);
});

test('RSC draft reader parses defaultValues and site ID from separate scripts', async () => {
  const defaults = { title: 'T', slug: 't', excerpt: '', order: 0, coverImage: null, content: [], categories: [], tags: [] };
  const tab = {
    url: async () => 'https://workspace.laicms.com/virtualsite/posts/222222222222222222222222/update',
    playwright: {
      evaluate: async () => ({
        scripts: [
          `x\\"defaultValues\\":${JSON.stringify(defaults)}x`,
          'x\\"site\\":{\\"id\\":\\"111111111111111111111111\\",\\"name\\":\\"Virtual\\",\\"slug\\":\\"virtualsite\\"}x',
        ],
        scriptSources: ['https://workspace.laicms.com/a.js?dpl=' + 'd'.repeat(40)],
        statusBadges: ['Draft'],
      }),
    },
  };
  const result = await readAllinCmsArticleDraftFromPage({ tab, expectedSiteKey: 'virtualsite', expectedPostId: '222222222222222222222222' });
  assert.equal(result.siteId, '111111111111111111111111');
  assert.deepEqual(result.defaults, defaults);
});


test('verified status without the complete media proof is blocked', async () => {
  const markdown = '![A](a.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a' });
  const mappings = mappingsFor(manifest);
  const mapping = mappings[manifest.assets[0].assetId];
  mapping.verification = { contractVerified: true };
  await assert.rejects(
    () => buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings }),
    /Incomplete media verification/,
  );
});

test('audit detects image position drift even when image count and URL order match', async () => {
  const markdown = 'P1\n![A](a.png)\nP2\n![B](b.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
  const mappings = mappingsFor(manifest);
  const content = (await buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings })).content;
  const moved = [content[1], content[0], ...content.slice(2)];
  const audit = auditArticleImageBinding({ sourceMarkdown: markdown, manifest, mappings, content: moved });
  assert.equal(audit.image_order_mismatches, 0);
  assert.ok(audit.image_position_mismatches > 0);
  assert.equal(audit.broken_public_urls, 0);
  assert.equal(audit.image_decode_failures, 0);
  assert.equal(audit.missing_required_alt_in_expected_content, 0);
});

test('audit reports wrong image order', async () => {
  const markdown = '![A](a.png)\n![B](b.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
  const mappings = mappingsFor(manifest);
  const content = (await buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings })).content;
  const swapped = [content[1], content[0], ...content.slice(2)];
  const audit = auditArticleImageBinding({ sourceMarkdown: markdown, manifest, mappings, content: swapped });
  assert.ok(audit.image_order_mismatches > 0);
});

test('media mapping must prove it belongs to the exact source asset SHA-256', async () => {
  const markdown = '![A](a.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a' });
  const mappings = mappingsFor(manifest);
  mappings[manifest.assets[0].assetId].sourceSha256 = 'sha256:' + 'f'.repeat(64);
  await assert.rejects(
    () => buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings }),
    /source SHA-256 mismatch/,
  );
});

test('changed local image bytes invalidate the manifest before Slate binding', async () => {
  const markdown = '![A](a.png)';
  const { manifest, dir } = await manifestFor(markdown, { 'a.png': 'original-bytes' });
  await writeFile(join(dir, 'a.png'), 'changed-after-manifest');
  await assert.rejects(
    () => buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) }),
    /Stale source image (asset|occurrence)/,
  );
});

test('readback verifier rejects a backend string caption even when text matches', async () => {
  const markdown = '![A](a.png "Caption")';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a' });
  const built = await buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) });
  const actual = structuredClone(built.content);
  actual.find((node) => node.type === 'img').caption = 'Caption';
  const result = verifyArticleImageReadback({ expectedContent: built.content, actualContent: actual, manifest });
  assert.equal(result.ok, false);
  assert.match(result.errors.join('; '), /actual Slate content invalid/);
});

test('manifest schema 2 keeps occurrence-scoped source identity for equal bytes at different paths', async () => {
  const { manifest } = await manifestFor('![one](a.png)\n![two](b.png)', { 'a.png': 'same', 'b.png': 'same' });
  assert.equal(manifest.schemaVersion, 2);
  assert.equal(manifest.assets.length, 1);
  assert.equal(manifest.assets[0].sourceFiles.length, 2);
  assert.notEqual(manifest.occurrences[0].sourceFile, manifest.occurrences[1].sourceFile);
  for (const occurrence of manifest.occurrences) {
    assert.equal(isAbsolute(occurrence.sourceFile), true);
    assert.equal(occurrence.sourceSha256, occurrence.assetId);
    assert.match(occurrence.sourceMd5, /^md5:[0-9a-f]{32}$/);
  }
});

test('equal-byte paths are rechecked separately and changing only the second path blocks binding', async () => {
  const markdown = '![one](a.png)\n![two](b.png)';
  const { manifest, dir } = await manifestFor(markdown, { 'a.png': 'same', 'b.png': 'same' });
  await writeFile(join(dir, 'b.png'), 'changed-second-path');
  await assert.rejects(
    () => buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings: mappingsFor(manifest) }),
    (error) => {
      assert.match(error.message, /Stale source image occurrence/);
      assert.match(error.message, /b\.png/);
      return true;
    },
  );
});

test('same remote asset may be reused while every equal-byte occurrence is read and verified serially', async () => {
  const markdown = '![one](a.png)\n![two](b.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'same', 'b.png': 'same' });
  const reads = [];
  const progress = [];
  await verifyFreshArticleImageOccurrences({
    manifest,
    readAsset: async (path) => { reads.push(path); return readFile(path); },
    onProgress: async (event) => { progress.push(`${event.stage}:${event.current}/${event.total}`); },
  });
  assert.deepEqual(reads, manifest.occurrences.map((item) => item.sourceFile));
  assert.deepEqual(progress, ['occurrence_source_verified:1/2', 'occurrence_source_verified:2/2']);
});

test('build returns an exact binding proof and occurrence-by-occurrence progress', async () => {
  const markdown = 'P1\n![A](a.png)\nP2\n![B](b.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
  const progress = [];
  const built = await buildAllinCmsSlateContent({
    sourceMarkdown: markdown,
    manifest,
    mappings: mappingsFor(manifest),
    onProgress: async (event) => { progress.push(`${event.stage}:${event.current}`); },
  });
  assert.equal(built.bindingProof.kind, 'allincms-article-image-binding-proof');
  assert.equal(built.bindingProof.version, 1);
  assert.deepEqual(built.bindingProof.occurrenceIds, manifest.occurrences.map((item) => item.occurrenceId));
  assert.deepEqual(built.bindingProof.urls, built.content.filter((node) => node.type === 'img').map((node) => node.url));
  assert.match(built.bindingProof.contentSha256, /^sha256:[0-9a-f]{64}$/);
  assert.match(built.bindingProof.proofSha256, /^sha256:[0-9a-f]{64}$/);
  assert.deepEqual(progress, [
    'occurrence_source_verified:1',
    'occurrence_source_verified:2',
    'occurrence_bound:1',
    'occurrence_bound:2',
  ]);
});

test('handwritten valid Slate image content without binding proof is blocked before the save request', async () => {
  const fixtureSave = successfulImageSaveFixture();
  const content = [{
    type: 'img', id: 'handwritten', url: 'https://assets.laicms.com/x/a.webp',
    alt: 'A', children: [{ text: '' }],
  }];
  await assert.rejects(() => saveAllinCmsArticleDraftDirect({
    tab: fixtureSave.tab,
    expectedSiteKey: 'virtualsite',
    expectedPostId: '222222222222222222222222',
    authorizationContext: articleImageAuth(),
    overrides: { content },
    _internal: fixtureSave.internal,
  }), /build-generated bindingProof/);
  assert.equal(fixtureSave.sendCount, 0);
});

test('direct image save with a valid proof still requires the article operation guard', async () => {
  const markdown = '![A](a.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a' });
  const mappings = mappingsFor(manifest);
  const built = await buildAllinCmsSlateContent({ sourceMarkdown: markdown, manifest, mappings });
  const fixtureSave = successfulImageSaveFixture();
  await assert.rejects(() => saveAllinCmsArticleDraftDirect({
    tab: fixtureSave.tab,
    expectedSiteKey: 'virtualsite',
    expectedPostId: '222222222222222222222222',
    authorizationContext: articleImageAuth(),
    overrides: { content: built.content },
    bindingProof: built.bindingProof,
    sourceMarkdown: markdown,
    manifest,
    mappings,
    _internal: fixtureSave.internal,
  }), /must use bindAndSaveAllinCmsArticleDraftDirect/);
  assert.equal(fixtureSave.sendCount, 0);
});

test('different source assets cannot be forced onto one media record or URL', async () => {
  for (const duplicateField of ['mediaId', 'url']) {
    const markdown = '![A](a.png)\n![B](b.png)';
    const { manifest } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
    const mappings = mappingsFor(manifest);
    const [first, second] = manifest.assets;
    mappings[second.assetId][duplicateField] = mappings[first.assetId][duplicateField];
    await assert.rejects(() => buildAllinCmsSlateContent({
      sourceMarkdown: markdown,
      manifest,
      mappings,
    }), duplicateField === 'mediaId'
      ? /Different source assets cannot share one mediaId/
      : /Different source assets cannot share one media URL/);
  }
});

test('schema 1 or incomplete occurrence source identity must be rebuilt', async () => {
  const markdown = '![A](a.png)';
  const { manifest } = await manifestFor(markdown, { 'a.png': 'a' });
  const cases = [
    { name: 'schema 1', mutate: (copy) => { copy.schemaVersion = 1; }, pattern: /rebuild with schema 2/ },
    { name: 'missing occurrence MD5', mutate: (copy) => { delete copy.occurrences[0].sourceMd5; }, pattern: /source hashes are incomplete/ },
    { name: 'missing sourceFiles path', mutate: (copy) => { copy.assets[0].sourceFiles = []; }, pattern: /sourceFiles does not include occurrence sourceFile/ },
  ];
  for (const item of cases) {
    const copy = structuredClone(manifest);
    item.mutate(copy);
    await assert.rejects(() => verifyFreshArticleImageOccurrences({ manifest: copy }), item.pattern, item.name);
  }
});

test('unsafe routes and relative manifest or operation lock paths stop before lock acquisition', async () => {
  const markdown = '![A](a.png)';
  const { manifest, dir } = await manifestFor(markdown, { 'a.png': 'a' });
  const base = {
    tab: successfulImageSaveFixture().tab,
    expectedSiteKey: 'virtualsite',
    expectedPostId: '222222222222222222222222',
    sourceMarkdown: markdown,
    manifest,
    mappings: mappingsFor(manifest),
    manifestPath: join(dir, 'binding.json'),
    authorizationContext: articleImageAuth(),
  };
  for (const scenario of [
    { patch: { manifestPath: 'binding.json' }, pattern: /manifestPath must be absolute/ },
    { patch: { expectedSiteKey: '../other-site' }, pattern: /expectedSiteKey must be one safe route segment|siteKey must be a single safe route segment/ },
    { patch: { expectedPostId: 'post/other' }, pattern: /expectedPostId must be one safe route segment|authorizationContext.target_digest does not match/ },
    { patch: { operationLockPath: 'article.operation.lock' }, pattern: /operationLockPath must be absolute/ },
  ]) {
    let lockAttempted = false;
    await assert.rejects(() => bindAndSaveAllinCmsArticleDraftDirect({
      ...base,
      ...scenario.patch,
      _internal: {
        openOperationLock: async () => {
          lockAttempted = true;
          throw new Error('lock should not be attempted');
        },
      },
    }), scenario.pattern);
    assert.equal(lockAttempted, false);
  }
});

test('changing source bytes after build blocks the one final save before any request', async () => {
  const markdown = '![A](a.png)';
  const { manifest, dir } = await manifestFor(markdown, { 'a.png': 'original' });
  const manifestPath = join(dir, 'binding.json');
  const fixtureSave = successfulImageSaveFixture();
  await assert.rejects(() => bindAndSaveAllinCmsArticleDraftDirect({
    tab: fixtureSave.tab,
    expectedSiteKey: 'virtualsite',
    expectedPostId: '222222222222222222222222',
    sourceMarkdown: markdown,
    manifest,
    mappings: mappingsFor(manifest),
    manifestPath,
    authorizationContext: articleImageAuth(),
    _internal: {
      saveInternal: fixtureSave.internal,
      afterBuild: async () => { await writeFile(join(dir, 'a.png'), 'changed-after-build'); },
    },
  }), /Stale source image occurrence/);
  assert.equal(fixtureSave.sendCount, 0);
});

test('content or proof tampering after build is blocked before any request', async () => {
  for (const tamper of ['content', 'proof-url']) {
    const markdown = '![A](a.png)';
    const { manifest, dir } = await manifestFor(markdown, { 'a.png': `asset-${tamper}` });
    const fixtureSave = successfulImageSaveFixture();
    await assert.rejects(() => bindAndSaveAllinCmsArticleDraftDirect({
      tab: fixtureSave.tab,
      expectedSiteKey: 'virtualsite',
      expectedPostId: '222222222222222222222222',
      sourceMarkdown: markdown,
      manifest,
      mappings: mappingsFor(manifest),
      manifestPath: join(dir, 'binding.json'),
      authorizationContext: articleImageAuth(),
      _internal: {
        saveInternal: fixtureSave.internal,
        afterBuild: async ({ built }) => {
          if (tamper === 'content') built.content[0].alt = 'tampered';
          else built.bindingProof.urls[0] = 'https://assets.laicms.com/tampered.webp';
        },
      },
    }), /bindingProof/);
    assert.equal(fixtureSave.sendCount, 0);
  }
});

test('valid image operation binds one by one, saves the complete draft once, verifies, and writes manifest', async () => {
  const markdown = 'P1\n![A](a.png "Cap A")\nP2\n![B](b.png "Cap B")';
  const { manifest, dir } = await manifestFor(markdown, { 'a.png': 'a', 'b.png': 'b' });
  const fixtureSave = successfulImageSaveFixture();
  const manifestPath = join(dir, 'binding.json');
  const progress = [];
  let activeProgress = 0;
  let maxActiveProgress = 0;
  const result = await bindAndSaveAllinCmsArticleDraftDirect({
    tab: fixtureSave.tab,
    expectedSiteKey: 'virtualsite',
    expectedPostId: '222222222222222222222222',
    sourceMarkdown: markdown,
    manifest,
    mappings: mappingsFor(manifest),
    manifestPath,
    authorizationContext: articleImageAuth(),
    onProgress: async (event) => {
      activeProgress += 1;
      maxActiveProgress = Math.max(maxActiveProgress, activeProgress);
      await new Promise((resolve) => setTimeout(resolve, 1));
      progress.push(`${event.stage}:${event.current}/${event.total}`);
      activeProgress -= 1;
    },
    _internal: { saveInternal: fixtureSave.internal },
  });
  assert.equal(result.status, 'article_images_bound_draft_saved_and_manifest_written');
  assert.equal(fixtureSave.sendCount, 1);
  assert.equal(fixtureSave.sentPayload.content.filter((node) => node.type === 'img').length, 2);
  assert.equal(maxActiveProgress, 1);
  assert.deepEqual(progress, [
    'occurrence_source_verified:1/2',
    'occurrence_source_verified:2/2',
    'occurrence_bound:1/2',
    'occurrence_bound:2/2',
    'occurrence_source_reverified_before_save:1/2',
    'occurrence_source_reverified_before_save:2/2',
  ]);
  const written = JSON.parse(await readFile(manifestPath, 'utf8'));
  assert.equal(written.runtime.backendReadback.editorVerified, true);
  assert.equal(written.runtime.backendReadback.bindingProofSha256, result.build.bindingProof.proofSha256);
  await assert.rejects(() => readFile(result.lockPath, 'utf8'), /ENOENT/);
});

test('article operation lock blocks a second writer before build or request', async () => {
  const markdown = '![A](a.png)';
  const { manifest, dir } = await manifestFor(markdown, { 'a.png': 'a' });
  const manifestPath = join(dir, 'binding.json');
  let firstEnteredSave;
  let releaseFirst;
  const entered = new Promise((resolve) => { firstEnteredSave = resolve; });
  const hold = new Promise((resolve) => { releaseFirst = resolve; });
  const base = {
    tab: successfulImageSaveFixture().tab,
    expectedSiteKey: 'virtualsite',
    expectedPostId: '222222222222222222222222',
    sourceMarkdown: markdown,
    manifest,
    mappings: mappingsFor(manifest),
    manifestPath,
    authorizationContext: articleImageAuth(),
  };
  const first = bindAndSaveAllinCmsArticleDraftDirect({
    ...base,
    _internal: {
      saveDraft: async () => {
        firstEnteredSave();
        await hold;
        return { status: 'stub_saved', savedAt: '2026-07-27T00:00:00.000Z', editorPage: { ok: true }, contract: {} };
      },
      writeManifest: async () => ({ status: 'stub_manifest_written' }),
    },
  });
  await entered;
  let secondSaveCalled = false;
  await assert.rejects(() => bindAndSaveAllinCmsArticleDraftDirect({
    ...base,
    _internal: {
      saveDraft: async () => { secondSaveCalled = true; },
      writeManifest: async () => ({ status: 'never' }),
    },
  }), /already locked/);
  assert.equal(secondSaveCalled, false);
  releaseFirst();
  await first;
});

test('manifest write failure after verified save is ambiguous and never permits resend', async () => {
  const markdown = '![A](a.png)';
  const { manifest, dir } = await manifestFor(markdown, { 'a.png': 'a' });
  const fixtureSave = successfulImageSaveFixture();
  await assert.rejects(() => bindAndSaveAllinCmsArticleDraftDirect({
    tab: fixtureSave.tab,
    expectedSiteKey: 'virtualsite',
    expectedPostId: '222222222222222222222222',
    sourceMarkdown: markdown,
    manifest,
    mappings: mappingsFor(manifest),
    manifestPath: join(dir, 'binding.json'),
    authorizationContext: articleImageAuth(),
    _internal: {
      saveInternal: fixtureSave.internal,
      writeManifest: async () => { throw new Error('disk full'); },
    },
  }), (error) => {
    assert.equal(error.result.status, 'article_manifest_write_failed_after_save');
    assert.equal(error.result.requestMayHaveSucceeded, true);
    assert.equal(error.result.automaticRetryAllowed, false);
    return true;
  });
  assert.equal(fixtureSave.sendCount, 1);
});
