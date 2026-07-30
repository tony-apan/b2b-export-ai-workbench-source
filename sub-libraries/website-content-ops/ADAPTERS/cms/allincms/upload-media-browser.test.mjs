import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { basename, join } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import {
  checkAllinCmsMediaRuntime,
  computeAllinCmsMediaUploadFileListDigest,
  createAllinCmsMediaUploadAuthorizationContext,
  readAllinCmsImageIndex,
  reconcileAllinCmsMediaDirect,
  uploadAllinCmsMedia,
  uploadAllinCmsMediaBatch,
  uploadAllinCmsMediaDirect,
  uploadAllinCmsMediaSerial,
  updateAllinCmsMediaMetadataDirect,
} from './upload-media-browser.mjs';

const SITE_KEY = 'virtualsite1';
const MEDIA_PAGE = `https://workspace.laicms.com/${SITE_KEY}/media`;
const DIRECT_SOURCE_BUFFER = Buffer.from('virtual-file');
const DIRECT_NORMALIZED_BUFFER = Buffer.from('virtual-webp');
const digest = (algorithm, value) => createHash(algorithm).update(value).digest('hex');

function authorizationContext(entrypoint, files, overrides = {}) {
  const approvedAt = new Date(Date.now() - 1_000).toISOString();
  return {
    authorization_context_version: 1,
    site_key: SITE_KEY,
    operation: 'allincms.media.upload',
    entrypoint,
    file_list_digest_algorithm: 'sha256-canonical-json-v1',
    file_list_digest: computeAllinCmsMediaUploadFileListDigest(files),
    approval_actor: 'Test Reviewer',
    approval_actor_type: 'human-asserted',
    approval_identity_status: 'not_verified',
    approved_at: approvedAt,
    expires_at: new Date(Date.parse(approvedAt) + 20 * 60 * 1000).toISOString(),
    ...overrides,
  };
}

function directAuthorizationContext(overrides = {}) {
  return authorizationContext('direct', [{
    filename: 'virtual.webp',
    bytes: DIRECT_SOURCE_BUFFER.length,
    sha256: digest('sha256', DIRECT_SOURCE_BUFFER),
  }], overrides);
}

async function authorizedDirect(options) {
  return uploadAllinCmsMediaDirect({
    ...options,
    authorizationContext: options.authorizationContext ?? directAuthorizationContext(),
  });
}

async function authorizedSerial(options) {
  const context = options.authorizationContext
    ?? await createAllinCmsMediaUploadAuthorizationContext({
      localFiles: options.localFiles,
      expectedSiteKey: options.expectedSiteKey,
      entrypoint: 'serial',
      approvalActor: 'Test Reviewer',
    });
  return uploadAllinCmsMediaSerial({ ...options, authorizationContext: context });
}

function mockTab() {
  return {
    url: async () => MEDIA_PAGE,
    reload: async () => {},
    playwright: {
      waitForLoadState: async () => {},
      waitForTimeout: async () => {},
    },
    capabilities: {
      get: async () => ({ send: async () => ({}) }),
    },
  };
}

function mutationEdgeBatchTab({ expectedCount, onSetFiles, onConfirm }) {
  const chooser = { setFiles: async (files) => onSetFiles?.(files) };
  return {
    url: async () => MEDIA_PAGE,
    reload: async () => {},
    playwright: {
      evaluate: async () => 0,
      waitForTimeout: async () => {},
      waitForEvent: async (event) => {
        assert.equal(event, 'filechooser');
        return chooser;
      },
      getByRole: (_role, { name }) => ({
        count: async () => ['Upload', 'Choose File', `Upload (${expectedCount})`].includes(name) ? 1 : 0,
        click: async () => {
          if (name === `Upload (${expectedCount})`) await onConfirm?.();
        },
      }),
    },
    capabilities: {
      get: async () => ({
        send: async () => ({}),
        readEvents: async () => ({ cursor: 1, events: [] }),
      }),
    },
  };
}

function directInternals(overrides = {}) {
  return {
    prepareInput: async () => ({
      localFile: 'fixtures/virtual.webp',
      filename: 'virtual.webp',
      title: 'virtual',
      extension: '.webp',
      bytes: DIRECT_SOURCE_BUFFER.length,
      sha256: digest('sha256', DIRECT_SOURCE_BUFFER),
      md5: digest('md5', DIRECT_SOURCE_BUFFER),
      sourceBuffer: Buffer.from(DIRECT_SOURCE_BUFFER),
    }),
    normalizeInput: async () => ({
      buffer: Buffer.from(DIRECT_NORMALIZED_BUFFER),
      filename: 'virtual.webp',
      mimeType: 'image/webp',
      bytes: DIRECT_NORMALIZED_BUFFER.length,
      sha256: digest('sha256', DIRECT_NORMALIZED_BUFFER),
      md5: digest('md5', DIRECT_NORMALIZED_BUFFER),
      normalized: false,
    }),
    countExisting: async () => 0,
    getCdp: async () => ({ send: async () => ({}) }),
    discoverContract: async () => ({
      actionId: 'f'.repeat(40),
      actionIdLength: 40,
      actionIdSha256: 'e'.repeat(64),
      deploymentId: '1'.repeat(40),
      siteId: '2'.repeat(24),
      routerTree: '{}',
    }),
    readCursor: async () => ({ cursor: 1 }),
    sendReplay: async () => ({ status: 200, contentType: 'text/x-component', ok: true }),
    readCaptured: async () => ({ events: [] }),
    summarizeNetwork: () => ({ actionCount: 1, action: { responseStatus: 200 }, actions: [], assets: [] }),
    reloadPage: async () => {},
    inspectResult: async () => ({
      card: { url: `https://assets.laicms.com/${SITE_KEY}/virtual.webp` },
      media: {
        mediaId: '3'.repeat(24),
        title: 'virtual',
        url: `https://assets.laicms.com/${SITE_KEY}/virtual.webp`,
        mimeType: 'image/webp',
      },
      image: { ok: true, width: 10, height: 10 },
      anonymous: {
        ok: true,
        finalUrl: `https://assets.laicms.com/${SITE_KEY}/virtual.webp`,
        contentSha256: '4'.repeat(64),
        contentMd5: '5'.repeat(32),
        contentType: 'image/webp',
      },
      errors: [],
    }),
    ...overrides,
  };
}

function metadataInternals(overrides = {}) {
  const url = `https://assets.laicms.com/${SITE_KEY}/virtual.webp`;
  let reads = 0;
  let cardChecks = 0;
  return {
    countCards: async (_tab, title) => {
      cardChecks += 1;
      if (cardChecks === 1) return title === 'virtual' ? 1 : 0;
      if (cardChecks === 2) return 0;
      return title === 'rear-hub-motor-side-view' ? 1 : 0;
    },
    waitCard: async () => ({ title: 'virtual', url }),
    readRecord: async () => {
      reads += 1;
      if (reads === 1) {
        return {
          mediaId: '3'.repeat(24),
          title: 'virtual',
          name: 'virtual',
          alt: 'virtual',
          caption: null,
          url,
        };
      }
      return {
        mediaId: '3'.repeat(24),
        title: 'rear-hub-motor-side-view',
        name: 'rear-hub-motor-side-view',
        alt: 'Rear e-bike hub motor showing the axle and cable lead',
        caption: 'Rear hub motor side view for an electric bicycle application.',
        url,
      };
    },
    getCdp: async () => ({ send: async () => ({}) }),
    discoverContract: async () => ({
      actionId: 'f'.repeat(40),
      actionIdLength: 40,
      actionIdSha256: 'e'.repeat(64),
      deploymentId: '1'.repeat(40),
      siteId: '2'.repeat(24),
      routerTree: '{}',
    }),
    readCursor: async () => ({ cursor: 1 }),
    sendReplay: async () => ({ status: 200, contentType: 'text/x-component', ok: true }),
    readCaptured: async () => ({ events: [] }),
    summarizeNetwork: () => ({ actionCount: 1, action: { responseStatus: 200 }, actions: [], assets: [] }),
    reloadPage: async () => {},
    ...overrides,
  };
}

async function withTempWorkspace(fn) {
  const dir = await mkdtemp(join(tmpdir(), 'allincms-media-test-'));
  try {
    return await fn(dir);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

async function makeImage(dir, name, contents = 'same-image-content') {
  const path = join(dir, name);
  await writeFile(path, contents);
  return path;
}

function uploadedResult(title) {
  const url = `https://assets.laicms.com/${SITE_KEY}/${title}.webp`;
  return {
    status: 'uploaded_and_verified',
    input: {
      normalizedSha256: '6'.repeat(64),
      normalizedMd5: '7'.repeat(32),
    },
    media: { mediaId: '8'.repeat(24), title, url, mimeType: 'image/webp' },
    anonymous: {
      ok: true,
      finalUrl: url,
      contentSha256: '9'.repeat(64),
      contentMd5: '0'.repeat(32),
      contentType: 'image/webp',
    },
  };
}

test('direct metadata update verifies title, alt, caption, and preserves media identity', async () => {
  const result = await updateAllinCmsMediaMetadataDirect({
    tab: mockTab(),
    expectedSiteKey: SITE_KEY,
    mediaId: '3'.repeat(24),
    expectedUrl: `https://assets.laicms.com/${SITE_KEY}/virtual.webp`,
    expectedCurrentTitle: 'virtual',
    title: 'rear-hub-motor-side-view',
    alt: 'Rear e-bike hub motor showing the axle and cable lead',
    caption: 'Rear hub motor side view for an electric bicycle application.',
    authorizationConfirmed: true,
    _internal: metadataInternals(),
  });
  assert.equal(result.status, 'metadata_updated_and_verified');
  assert.equal(result.verification.metadataMatchesAfterReload, true);
  assert.equal(result.verification.mediaIdentityUnchanged, true);
  assert.equal(result.interaction.uploadRequests, 0);
  assert.equal(result.interaction.uiClicks, 0);
});

test('metadata update tolerates delayed RSC persistence with read-only reloads and one write request', async () => {
  const url = `https://assets.laicms.com/${SITE_KEY}/virtual.webp`;
  let reads = 0;
  let reloads = 0;
  let writeRequests = 0;
  const result = await updateAllinCmsMediaMetadataDirect({
    tab: mockTab(),
    expectedSiteKey: SITE_KEY,
    mediaId: '3'.repeat(24),
    expectedUrl: url,
    expectedCurrentTitle: 'virtual',
    title: 'virtual',
    alt: 'Rear e-bike hub motor showing the axle and cable lead',
    caption: 'Rear hub motor side view for an electric bicycle application.',
    authorizationConfirmed: true,
    _internal: metadataInternals({
      readRecord: async () => {
        reads += 1;
        if (reads === 1) {
          return { mediaId: '3'.repeat(24), title: 'virtual', name: 'virtual', alt: 'virtual', caption: null, url };
        }
        if (reads === 2) {
          return {
            mediaId: '3'.repeat(24), title: 'virtual', name: 'virtual',
            alt: 'Rear e-bike hub motor showing the axle and cable lead', caption: null, url,
          };
        }
        return {
          mediaId: '3'.repeat(24), title: 'virtual', name: 'virtual',
          alt: 'Rear e-bike hub motor showing the axle and cable lead',
          caption: 'Rear hub motor side view for an electric bicycle application.', url,
        };
      },
      countCards: async (_tab, title) => title === 'virtual' ? 1 : 0,
      reloadPage: async () => { reloads += 1; },
      sleep: async () => {},
      verificationDelaysMs: [0, 750, 2_000],
      sendReplay: async () => {
        writeRequests += 1;
        return { status: 200, contentType: 'text/x-component', ok: true };
      },
    }),
  });
  assert.equal(result.status, 'metadata_updated_and_verified');
  assert.equal(result.verification.readOnlyVerificationAttempts, 2);
  assert.equal(reloads, 2);
  assert.equal(writeRequests, 1);
  assert.equal(result.observedAfter.caption, 'Rear hub motor side view for an electric bicycle application.');
});

test('metadata update ambiguity forbids automatic retry and never reuploads', async () => {
  await assert.rejects(
    updateAllinCmsMediaMetadataDirect({
      tab: mockTab(),
      expectedSiteKey: SITE_KEY,
      mediaId: '3'.repeat(24),
      expectedUrl: `https://assets.laicms.com/${SITE_KEY}/virtual.webp`,
      expectedCurrentTitle: 'virtual',
      title: 'rear-hub-motor-side-view',
      alt: 'Rear e-bike hub motor showing the axle and cable lead',
      caption: 'Rear hub motor side view for an electric bicycle application.',
      authorizationConfirmed: true,
      _internal: metadataInternals({ readCaptured: async () => { throw new Error('events unavailable'); } }),
    }),
    (error) => {
      assert.equal(error.result.status, 'metadata_update_ambiguous');
      assert.equal(error.result.automaticRetryAllowed, false);
      assert.equal(error.result.interaction.uploadRequests, 0);
      return true;
    },
  );
});

test('metadata rename stops before request when the desired title already exists', async () => {
  let contractDiscovered = false;
  await assert.rejects(
    updateAllinCmsMediaMetadataDirect({
      tab: mockTab(),
      expectedSiteKey: SITE_KEY,
      mediaId: '3'.repeat(24),
      expectedUrl: `https://assets.laicms.com/${SITE_KEY}/virtual.webp`,
      expectedCurrentTitle: 'virtual',
      title: 'rear-hub-motor-side-view',
      authorizationConfirmed: true,
      _internal: metadataInternals({
        countCards: async (_tab, title) => title === 'virtual' ? 1 : 1,
        discoverContract: async () => { contractDiscovered = true; },
      }),
    }),
    /already use the requested title/,
  );
  assert.equal(contractDiscovered, false);
});

test('metadata field limits fail before any remote request', async () => {
  let contractDiscovered = false;
  await assert.rejects(
    updateAllinCmsMediaMetadataDirect({
      tab: mockTab(),
      expectedSiteKey: SITE_KEY,
      mediaId: '3'.repeat(24),
      expectedUrl: `https://assets.laicms.com/${SITE_KEY}/virtual.webp`,
      expectedCurrentTitle: 'virtual',
      title: 'x'.repeat(101),
      authorizationConfirmed: true,
      _internal: metadataInternals({ discoverContract: async () => { contractDiscovered = true; } }),
    }),
    /100-character limit/,
  );
  assert.equal(contractDiscovered, false);
});


test('direct upload rejects missing authorization before preparation or replay', async () => {
  let prepared = 0;
  let replayed = 0;
  await assert.rejects(
    uploadAllinCmsMediaDirect({
      tab: mockTab(),
      localFile: 'fixtures/virtual.webp',
      expectedSiteKey: SITE_KEY,
      _internal: directInternals({
        prepareInput: async () => { prepared += 1; },
        sendReplay: async () => { replayed += 1; },
      }),
    }),
    /authorizationContext is required before any AllinCMS request/,
  );
  assert.equal(prepared, 0);
  assert.equal(replayed, 0);
});

test('direct upload rejects a mismatched file-list digest before browser access', async () => {
  let urlReads = 0;
  let replayed = 0;
  const tab = { ...mockTab(), url: async () => { urlReads += 1; return MEDIA_PAGE; } };
  await assert.rejects(
    uploadAllinCmsMediaDirect({
      tab,
      localFile: 'fixtures/virtual.webp',
      expectedSiteKey: SITE_KEY,
      authorizationContext: directAuthorizationContext({ file_list_digest: '0'.repeat(64) }),
      _internal: directInternals({ sendReplay: async () => { replayed += 1; } }),
    }),
    /does not match the exact ordered upload file list/,
  );
  assert.equal(urlReads, 0);
  assert.equal(replayed, 0);
});

test('serial upload rejects missing authorization before lock, reconcile, or upload', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'serial-auth.webp', 'serial-auth');
  let locks = 0;
  let uploads = 0;
  let reconciles = 0;
  await assert.rejects(
    uploadAllinCmsMediaSerial({
      tab: mockTab(),
      localFiles: [image],
      expectedSiteKey: SITE_KEY,
      imageIndexPath: join(dir, 'image-index.json'),
      _internal: {
        acquireLock: async () => { locks += 1; return async () => {}; },
        uploadOne: async () => { uploads += 1; },
        reconcileOne: async () => { reconciles += 1; },
      },
    }),
    /authorizationContext is required before any AllinCMS request/,
  );
  assert.equal(locks, 0);
  assert.equal(uploads, 0);
  assert.equal(reconciles, 0);
}));

test('UI batch and single upload reject missing authorization before file reads or browser requests', async () => {
  let urlReads = 0;
  const tab = { ...mockTab(), url: async () => { urlReads += 1; return MEDIA_PAGE; } };
  await assert.rejects(
    uploadAllinCmsMediaBatch({
      tab,
      localFiles: ['/definitely/not/read.webp'],
      expectedSiteKey: SITE_KEY,
    }),
    /authorizationContext is required before any AllinCMS request/,
  );
  await assert.rejects(
    uploadAllinCmsMedia({
      tab,
      localFile: '/definitely/not/read.webp',
      expectedSiteKey: SITE_KEY,
    }),
    /authorizationContext is required before any AllinCMS request/,
  );
  assert.equal(urlReads, 0);
});

test('UI batch rejects site, operation, entrypoint, actor, time, and digest mismatches before browser access', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'batch-auth.webp', 'batch-auth');
  const prepared = [{ filename: 'batch-auth.webp', bytes: 10, sha256: createHash('sha256').update('batch-auth').digest('hex') }];
  let urlReads = 0;
  const tab = { ...mockTab(), url: async () => { urlReads += 1; return MEDIA_PAGE; } };
  const attacks = [
    authorizationContext('batch', prepared, { site_key: 'wrong-site' }),
    authorizationContext('batch', prepared, { operation: 'allincms.media.delete' }),
    authorizationContext('direct', prepared),
    authorizationContext('batch', prepared, { approval_actor: 'Codex Agent' }),
    authorizationContext('batch', prepared, { expires_at: new Date(Date.now() - 1_000).toISOString() }),
    authorizationContext('batch', prepared, { file_list_digest: '0'.repeat(64) }),
  ];
  for (const context of attacks) {
    await assert.rejects(uploadAllinCmsMediaBatch({
      tab,
      localFiles: [image],
      expectedSiteKey: SITE_KEY,
      authorizationContext: context,
    }));
  }
  assert.equal(urlReads, 0);
}));

test('direct upload rejects same-path byte replacement made after approval and before preparation', async () => withTempWorkspace(async (dir) => {
  const localFile = await makeImage(dir, 'virtual.webp', 'approved-before-call');
  const context = await createAllinCmsMediaUploadAuthorizationContext({
    localFiles: [localFile],
    expectedSiteKey: SITE_KEY,
    entrypoint: 'direct',
    approvalActor: 'Test Reviewer',
  });
  await writeFile(localFile, 'replaced-before-call');
  let browserReads = 0;
  let replayed = false;
  const tab = { ...mockTab(), url: async () => { browserReads += 1; return MEDIA_PAGE; } };
  await assert.rejects(uploadAllinCmsMediaDirect({
    tab,
    localFile,
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
    _internal: directInternals({
      prepareInput: undefined,
      normalizeInput: undefined,
      sendReplay: async () => { replayed = true; },
    }),
  }), /does not match the exact ordered upload file list/);
  assert.equal(browserReads, 0);
  assert.equal(replayed, false);
}));

test('direct upload sends the first approved byte snapshot after the source path is replaced', async () => withTempWorkspace(async (dir) => {
  const localFile = await makeImage(dir, 'virtual.webp', 'approved-direct-bytes');
  const approvedBytes = await readFile(localFile);
  const context = await createAllinCmsMediaUploadAuthorizationContext({
    localFiles: [localFile],
    expectedSiteKey: SITE_KEY,
    entrypoint: 'direct',
    approvalActor: 'Test Reviewer',
  });
  let replayed = false;
  const result = await uploadAllinCmsMediaDirect({
    tab: mockTab(),
    localFile,
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
    beforeRequest: async () => writeFile(localFile, 'attacker-replacement-bytes'),
    _internal: directInternals({
      prepareInput: undefined,
      normalizeInput: undefined,
      sendReplay: async ({ expression }) => {
        replayed = true;
        assert.match(expression, new RegExp(approvedBytes.toString('base64')));
        assert.doesNotMatch(expression, new RegExp(Buffer.from('attacker-replacement-bytes').toString('base64')));
        return { status: 200, contentType: 'text/x-component', ok: true };
      },
    }),
  });
  assert.equal(replayed, true);
  assert.equal(result.input.sha256, digest('sha256', approvedBytes));
  assert.equal(result.status, 'uploaded_and_verified');
}));

test('serial passes each mutation edge the approved immutable byte snapshot', async () => withTempWorkspace(async (dir) => {
  const localFile = await makeImage(dir, 'serial-edge.webp', 'approved-serial-bytes');
  const approvedBytes = await readFile(localFile);
  let observedSnapshot = null;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [localFile],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: join(dir, 'image-index.json'),
    _internal: {
      uploadOne: async ({ localFile: path, beforeRequest, _internal }) => {
        await writeFile(path, 'attacker-serial-replacement');
        observedSnapshot = Buffer.from(_internal.preparedInput.sourceBuffer);
        await beforeRequest({ normalized: { sha256: digest('sha256', observedSnapshot), md5: digest('md5', observedSnapshot) } });
        return uploadedResult('serial-edge');
      },
    },
  });
  assert.deepEqual(observedSnapshot, approvedBytes);
  assert.equal(result.status, 'completed');
}));

test('batch uses copied byte payloads when a source path changes after setFiles', async () => withTempWorkspace(async (dir) => {
  const one = await makeImage(dir, 'one.webp', 'approved-one');
  const two = await makeImage(dir, 'two.webp', 'approved-two');
  const approved = [await readFile(one), await readFile(two)];
  const context = await createAllinCmsMediaUploadAuthorizationContext({
    localFiles: [one, two],
    expectedSiteKey: SITE_KEY,
    entrypoint: 'batch',
    approvalActor: 'Test Reviewer',
  });
  let chooserPayloads;
  let confirmed = false;
  const tab = mutationEdgeBatchTab({
    expectedCount: 2,
    onSetFiles: async (files) => { chooserPayloads = files; },
    onConfirm: async () => { confirmed = true; throw new Error('CONFIRM_SENTINEL'); },
  });
  await assert.rejects(uploadAllinCmsMediaBatch({
    tab,
    localFiles: [one, two],
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
    _internal: {
      beforeConfirm: async () => writeFile(two, 'attacker-batch-replacement'),
    },
  }), /CONFIRM_SENTINEL/);
  assert.equal(confirmed, true);
  assert.deepEqual(chooserPayloads.map((item) => item.buffer), approved);
  assert.deepEqual(chooserPayloads.map((item) => item.name), ['one.webp', 'two.webp']);
}));

test('batch rejects chooser-payload byte tampering before confirmation', async () => withTempWorkspace(async (dir) => {
  const localFile = await makeImage(dir, 'tamper.webp', 'approved-payload');
  const context = await createAllinCmsMediaUploadAuthorizationContext({
    localFiles: [localFile],
    expectedSiteKey: SITE_KEY,
    entrypoint: 'batch',
    approvalActor: 'Test Reviewer',
  });
  let confirmed = false;
  const tab = mutationEdgeBatchTab({
    expectedCount: 1,
    onSetFiles: async ([file]) => { file.buffer[0] ^= 0xff; },
    onConfirm: async () => { confirmed = true; },
  });
  await assert.rejects(uploadAllinCmsMediaBatch({
    tab,
    localFiles: [localFile],
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
  }), /Browser file payload changed/);
  assert.equal(confirmed, false);
}));

test('single delegates the approved byte snapshot instead of rereading the source path', async () => withTempWorkspace(async (dir) => {
  const localFile = await makeImage(dir, 'single.webp', 'approved-single');
  const approvedBytes = await readFile(localFile);
  const context = await createAllinCmsMediaUploadAuthorizationContext({
    localFiles: [localFile],
    expectedSiteKey: SITE_KEY,
    entrypoint: 'single',
    approvalActor: 'Test Reviewer',
  });
  let chooserPayload;
  const tab = mutationEdgeBatchTab({
    expectedCount: 1,
    onSetFiles: async ([file]) => { chooserPayload = file; },
    onConfirm: async () => { throw new Error('SINGLE_CONFIRM_SENTINEL'); },
  });
  await assert.rejects(uploadAllinCmsMedia({
    tab,
    localFile,
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
    _internal: { beforeConfirm: async () => writeFile(localFile, 'attacker-single-replacement') },
  }), /SINGLE_CONFIRM_SENTINEL/);
  assert.deepEqual(chooserPayload.buffer, approvedBytes);
}));

test('batch rejects symbolic-link inputs even if the link target digest was approved', async () => withTempWorkspace(async (dir) => {
  const first = await makeImage(dir, 'first.webp', 'first-target');
  const second = await makeImage(dir, 'second.webp', 'second-target');
  const link = join(dir, 'linked.webp');
  await symlink(first, link);
  const record = {
    filename: 'linked.webp',
    bytes: Buffer.byteLength('first-target'),
    sha256: digest('sha256', Buffer.from('first-target')),
  };
  const context = authorizationContext('batch', [record]);
  let browserReads = 0;
  const tab = { ...mockTab(), url: async () => { browserReads += 1; return MEDIA_PAGE; } };
  await assert.rejects(uploadAllinCmsMediaBatch({
    tab,
    localFiles: [link],
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
  }), /symbolic-link/);
  await rm(link);
  await symlink(second, link);
  await assert.rejects(uploadAllinCmsMediaBatch({
    tab,
    localFiles: [link],
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
  }), /symbolic-link/);
  assert.equal(browserReads, 0);
}));

test('authorization accepts 29:59.999 and rejects 30:00.000 plus 30:00.001', async () => {
  const approvedAt = Date.parse('2026-07-29T00:00:00.000Z');
  const expiresAt = approvedAt + 30 * 60 * 1000;
  const context = directAuthorizationContext({
    approved_at: new Date(approvedAt).toISOString(),
    expires_at: new Date(expiresAt).toISOString(),
  });
  let replayed = 0;
  const result = await uploadAllinCmsMediaDirect({
    tab: mockTab(),
    localFile: 'fixtures/virtual.webp',
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
    _internal: directInternals({ now: () => expiresAt - 1, sendReplay: async () => {
      replayed += 1;
      return { status: 200, contentType: 'text/x-component', ok: true };
    } }),
  });
  assert.equal(result.status, 'uploaded_and_verified');
  assert.equal(replayed, 1);

  for (const now of [expiresAt, expiresAt + 1]) {
    await assert.rejects(uploadAllinCmsMediaDirect({
      tab: mockTab(),
      localFile: 'fixtures/virtual.webp',
      expectedSiteKey: SITE_KEY,
      authorizationContext: context,
      _internal: directInternals({ now: () => now, sendReplay: async () => { replayed += 1; } }),
    }), /has expired/);
  }
  assert.equal(replayed, 1);
});

test('authorization rejects any future approved_at timestamp', async () => {
  const now = Date.parse('2026-07-29T00:00:00.000Z');
  const approvedAt = now + 1;
  const context = directAuthorizationContext({
    approved_at: new Date(approvedAt).toISOString(),
    expires_at: new Date(approvedAt + 30 * 60 * 1000).toISOString(),
  });
  let replayed = false;
  await assert.rejects(uploadAllinCmsMediaDirect({
    tab: mockTab(),
    localFile: 'fixtures/virtual.webp',
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
    _internal: directInternals({ now: () => now, sendReplay: async () => { replayed = true; } }),
  }), /must not be in the future/);
  assert.equal(replayed, false);
});

test('direct callback delay that crosses expiry fails before sendReplay', async () => {
  const approvedAt = Date.parse('2026-07-29T00:00:00.000Z');
  const expiresAt = approvedAt + 30 * 60 * 1000;
  let now = expiresAt - 1;
  let replayed = false;
  const context = directAuthorizationContext({
    approved_at: new Date(approvedAt).toISOString(),
    expires_at: new Date(expiresAt).toISOString(),
  });
  await assert.rejects(uploadAllinCmsMediaDirect({
    tab: mockTab(),
    localFile: 'fixtures/virtual.webp',
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
    beforeRequest: async () => { now = expiresAt; },
    _internal: directInternals({ now: () => now, sendReplay: async () => { replayed = true; } }),
  }), /has expired/);
  assert.equal(replayed, false);
});

test('batch callback delay that crosses expiry fails before confirmation click', async () => withTempWorkspace(async (dir) => {
  const localFile = await makeImage(dir, 'expiry.webp', 'expiry-bytes');
  const approvedAt = Date.parse('2026-07-29T00:00:00.000Z');
  const expiresAt = approvedAt + 30 * 60 * 1000;
  let now = expiresAt - 1;
  let confirmed = false;
  const prepared = [{
    filename: 'expiry.webp',
    bytes: Buffer.byteLength('expiry-bytes'),
    sha256: digest('sha256', Buffer.from('expiry-bytes')),
  }];
  const context = authorizationContext('batch', prepared, {
    approved_at: new Date(approvedAt).toISOString(),
    expires_at: new Date(expiresAt).toISOString(),
  });
  const tab = mutationEdgeBatchTab({
    expectedCount: 1,
    onConfirm: async () => { confirmed = true; },
  });
  await assert.rejects(uploadAllinCmsMediaBatch({
    tab,
    localFiles: [localFile],
    expectedSiteKey: SITE_KEY,
    authorizationContext: context,
    _internal: { now: () => now, beforeConfirm: async () => { now = expiresAt; } },
  }), /has expired/);
  assert.equal(confirmed, false);
}));

test('direct upload returns verified result with local and normalized MD5', async () => {
  const result = await authorizedDirect({
    tab: mockTab(),
    localFile: 'fixtures/virtual.webp',
    expectedSiteKey: SITE_KEY,
    _internal: directInternals(),
  });
  assert.equal(result.status, 'uploaded_and_verified');
  assert.equal(result.input.md5, digest('md5', DIRECT_SOURCE_BUFFER));
  assert.equal(result.input.normalizedMd5, digest('md5', DIRECT_NORMALIZED_BUFFER));
});

test('reload failure after request becomes ambiguous and forbids retry', async () => {
  await assert.rejects(
    authorizedDirect({
      tab: mockTab(),
      localFile: 'fixtures/virtual.webp',
      expectedSiteKey: SITE_KEY,
      _internal: directInternals({ reloadPage: async () => { throw new Error('reload failed'); } }),
    }),
    (error) => {
      assert.equal(error.result.status, 'upload_result_ambiguous');
      assert.equal(error.result.requestMayHaveSucceeded, true);
      assert.equal(error.result.automaticRetryAllowed, false);
      assert.equal(error.result.reconciliationRequired, true);
      return true;
    },
  );
});

test('CDP event read failure after request becomes ambiguous and forbids retry', async () => {
  await assert.rejects(
    authorizedDirect({
      tab: mockTab(),
      localFile: 'fixtures/virtual.webp',
      expectedSiteKey: SITE_KEY,
      _internal: directInternals({ readCaptured: async () => { throw new Error('CDP events unavailable'); } }),
    }),
    (error) => {
      assert.equal(error.result.status, 'upload_result_ambiguous');
      assert.equal(error.result.automaticRetryAllowed, false);
      assert.match(error.result.errors[0], /CDP events unavailable/);
      return true;
    },
  );
});

test('read-only reconciliation succeeds after one controlled reload', async () => {
  let reloads = 0;
  const result = await reconcileAllinCmsMediaDirect({
    tab: mockTab(),
    expectedSiteKey: SITE_KEY,
    expectedTitle: 'virtual',
    _internal: {
      reloadPage: async () => { reloads += 1; },
      countExisting: async () => 1,
      inspectResult: directInternals().inspectResult,
    },
  });
  assert.equal(result.status, 'reconciled_existing');
  assert.equal(result.requestSent, false);
  assert.equal(reloads, 1);
});

test('serial upload completes remote metadata verification before starting the next image', async () => withTempWorkspace(async (dir) => {
  const one = await makeImage(dir, 'one.webp', 'one');
  const two = await makeImage(dir, 'two.webp', 'two');
  const indexPath = join(dir, 'image-index.json');
  const events = [];
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [
      {
        localFile: one,
        title: 'front-hub-motor-product-view',
        alt: 'First motor image',
        caption: 'First caption.',
      },
      { localFile: two, alt: 'Second motor image', caption: 'Second caption.' },
    ],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    syncRemoteMetadata: true,
    metadataAuthorizationConfirmed: true,
    _internal: {
      uploadOne: async ({ localFile, beforeRequest }) => {
        const title = localFile.endsWith('one.webp') ? 'one' : 'two';
        events.push(`upload:${title}`);
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        return uploadedResult(title);
      },
      updateMetadataOne: async ({ expectedCurrentTitle, title, alt, caption }) => {
        events.push(`metadata:${expectedCurrentTitle}->${title}`);
        return {
          status: 'metadata_updated_and_verified',
          observedAfter: { title, alt, caption },
        };
      },
    },
  });
  assert.equal(result.status, 'completed');
  assert.deepEqual(events, [
    'upload:one',
    'metadata:one->front-hub-motor-product-view',
    'upload:two',
    'metadata:two->two',
  ]);
  assert.equal(result.items[0].status, 'uploaded_metadata_verified_and_indexed');
  assert.equal(result.items[0].mapping.title, 'front-hub-motor-product-view');
  assert.equal(result.items[1].status, 'uploaded_metadata_verified_and_indexed');
}));

test('serial upload stops after metadata ambiguity and never starts the next image', async () => withTempWorkspace(async (dir) => {
  const one = await makeImage(dir, 'one.webp', 'one');
  const two = await makeImage(dir, 'two.webp', 'two');
  const indexPath = join(dir, 'image-index.json');
  let uploads = 0;
  let metadataWrites = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [
      { localFile: one, alt: 'First motor image', caption: 'First caption.' },
      { localFile: two, alt: 'Second motor image', caption: 'Second caption.' },
    ],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    syncRemoteMetadata: true,
    metadataAuthorizationConfirmed: true,
    _internal: {
      uploadOne: async ({ beforeRequest }) => {
        uploads += 1;
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        return uploadedResult('one');
      },
      updateMetadataOne: async () => {
        metadataWrites += 1;
        const error = new Error('metadata verification delayed beyond bounded reads');
        error.result = { status: 'metadata_update_ambiguous', requestMayHaveSucceeded: true };
        throw error;
      },
    },
  });
  assert.equal(result.status, 'stopped_metadata_ambiguous');
  assert.equal(uploads, 1);
  assert.equal(metadataWrites, 1);
  assert.equal(result.items[0].uploadVerified, true);
  assert.equal(result.items[0].reuploadAllowed, false);
}));

test('serial metadata sync requires explicit authorization before any upload', async () => withTempWorkspace(async (dir) => {
  const one = await makeImage(dir, 'one.webp', 'one');
  let uploads = 0;
  await assert.rejects(
    authorizedSerial({
      tab: mockTab(),
      localFiles: [{ localFile: one, alt: 'First motor image' }],
      expectedSiteKey: SITE_KEY,
      imageIndexPath: join(dir, 'image-index.json'),
      syncRemoteMetadata: true,
      _internal: { uploadOne: async () => { uploads += 1; } },
    }),
    /metadataAuthorizationConfirmed=true/,
  );
  assert.equal(uploads, 0);
}));

test('serial upload writes verified mapping and stops before next item when index write fails', async () => withTempWorkspace(async (dir) => {
  const one = await makeImage(dir, 'one.webp', 'one');
  const two = await makeImage(dir, 'two.webp', 'two');
  const indexPath = join(dir, 'image-index.json');
  let uploads = 0;
  let writes = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [one, two],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    _internal: {
      uploadOne: async ({ localFile, beforeRequest }) => {
        uploads += 1;
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        return uploadedResult(localFile.endsWith('one.webp') ? 'one' : 'two');
      },
      persistRecord: async ({ index, sourceSha256, patch }) => {
        writes += 1;
        index.records[sourceSha256] = { ...(index.records[sourceSha256] || {}), ...patch, source_sha256: sourceSha256 };
        if (writes === 3) throw new Error('disk full');
        return index.records[sourceSha256];
      },
    },
  });
  assert.equal(result.status, 'stopped_index_write_failed');
  assert.equal(uploads, 1);
}));

test('serial upload reconciles an ambiguous request instead of re-uploading', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'reconcile.webp');
  const indexPath = join(dir, 'image-index.json');
  let uploads = 0;
  let reconciles = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [image],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    _internal: {
      uploadOne: async ({ beforeRequest }) => {
        uploads += 1;
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        const error = new Error('RSC media ID delayed');
        error.result = { status: 'upload_result_ambiguous', requestMayHaveSucceeded: true };
        throw error;
      },
      delay: async () => {},
      reconcileOne: async () => {
        reconciles += 1;
        return { ...uploadedResult('reconcile'), status: 'reconciled_existing' };
      },
    },
  });
  assert.equal(result.status, 'completed');
  assert.equal(uploads, 1);
  assert.equal(reconciles, 1);
  const index = await readAllinCmsImageIndex({ imageIndexPath: indexPath, expectedSiteKey: SITE_KEY });
  assert.equal(Object.values(index.records)[0].status, 'reconciled_existing');
}));

test('restart recovers request_started item from index and continues without duplicate upload', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'resume.webp');
  const indexPath = join(dir, 'image-index.json');
  const crypto = await import('node:crypto');
  const sourceSha = createHash('sha256').update(await readFile(image)).digest('hex');
  await writeFile(indexPath, `${JSON.stringify({
    schemaVersion: 1,
    kind: 'allincms-local-image-index',
    siteKey: SITE_KEY,
    updatedAt: new Date().toISOString(),
    records: {
      [sourceSha]: {
        source_sha256: sourceSha,
        source_md5: 'x',
        normalized_upload_sha256: 'a'.repeat(64),
        normalized_upload_md5: 'b'.repeat(32),
        status: 'request_started',
        title: 'resume',
        history: [],
      },
    },
  }, null, 2)}\n`);
  let uploads = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [image],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    _internal: {
      uploadOne: async () => { uploads += 1; return uploadedResult('resume'); },
      reconcileOne: async () => {
        const reconciled = { ...uploadedResult('resume'), status: 'reconciled_existing' };
        delete reconciled.input;
        return reconciled;
      },
    },
  });
  assert.equal(result.status, 'completed');
  assert.equal(uploads, 0);
  assert.equal(result.items[0].status, 'reconciled_existing');
  assert.equal(result.items[0].mapping.normalized_upload_sha256, 'a'.repeat(64));
  assert.equal(result.items[0].mapping.normalized_upload_md5, 'b'.repeat(32));
}));

test('prepared state never adopts a pre-existing title match as its own upload', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'collision.webp', 'collision-source');
  const indexPath = join(dir, 'image-index.json');
  const sourceSha = createHash('sha256').update(await readFile(image)).digest('hex');
  await writeFile(indexPath, `${JSON.stringify({
    schemaVersion: 1,
    kind: 'allincms-local-image-index',
    siteKey: SITE_KEY,
    updatedAt: new Date().toISOString(),
    records: {
      [sourceSha]: {
        source_sha256: sourceSha,
        source_md5: 'x',
        status: 'prepared',
        title: 'collision',
        history: [],
      },
    },
  }, null, 2)}\n`);
  let uploads = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [image],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    _internal: {
      uploadOne: async () => { uploads += 1; return uploadedResult('collision'); },
      reconcileOne: async () => ({ ...uploadedResult('collision'), status: 'reconciled_existing' }),
    },
  });
  assert.equal(result.status, 'stopped_preexisting_title_collision');
  assert.equal(result.items[0].requestSent, false);
  assert.equal(uploads, 0);
  const index = await readAllinCmsImageIndex({ imageIndexPath: indexPath, expectedSiteKey: SITE_KEY });
  assert.equal(index.records[sourceSha].status, 'prepared_title_collision');
  assert.equal(index.records[sourceSha].media_id, undefined);
}));

test('same source SHA-256 under a new filename reuses verified mapping', async () => withTempWorkspace(async (dir) => {
  const original = await makeImage(dir, 'first.webp', 'identical');
  const renamed = await makeImage(dir, 'renamed.webp', 'identical');
  const indexPath = join(dir, 'image-index.json');
  let uploads = 0;
  const uploadOne = async ({ localFile, beforeRequest }) => {
    uploads += 1;
    await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
    return uploadedResult(localFile.endsWith('first.webp') ? 'first' : 'renamed');
  };
  const first = await authorizedSerial({
    tab: mockTab(), localFiles: [original], expectedSiteKey: SITE_KEY, imageIndexPath: indexPath,
    _internal: { uploadOne },
  });
  const second = await authorizedSerial({
    tab: mockTab(), localFiles: [renamed], expectedSiteKey: SITE_KEY, imageIndexPath: indexPath,
    _internal: { uploadOne },
  });
  assert.equal(first.status, 'completed');
  assert.equal(second.items[0].status, 'reused_verified_mapping');
  assert.equal(uploads, 1);
}));

test('verified mapping can receive richer AI metadata without re-uploading', async () => withTempWorkspace(async (dir) => {
  const original = await makeImage(dir, 'motor-side-view.webp', 'same-motor-image');
  const renamed = await makeImage(dir, 'motor-side-view-renamed.webp', 'same-motor-image');
  const indexPath = join(dir, 'image-index.json');
  let uploads = 0;
  let metadataWrites = 0;
  const uploadOne = async ({ beforeRequest }) => {
    uploads += 1;
    await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
    return uploadedResult('motor-side-view');
  };

  await authorizedSerial({
    tab: mockTab(),
    localFiles: [{
      localFile: original,
      description: 'Rear hub motor side view on a white background.',
      alt: 'Rear e-bike hub motor side view',
      caption: 'Compact rear hub motor for an e-bike application.',
      metadata: {
        asset_type: 'product_side_view',
        visible_features: ['motor shell', 'axle', 'cable lead'],
        confidence: 0.92,
        human_review_required: false,
      },
    }],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    _internal: { uploadOne },
  });

  const reused = await authorizedSerial({
    tab: mockTab(),
    localFiles: [{
      localFile: renamed,
      title: 'rear-hub-motor-side-view',
      caption: 'Updated caption from product-page context.',
      metadata: {
        asset_type: 'product_side_view',
        page_context: 'product_detail',
        confidence: 0.97,
        human_review_required: false,
      },
    }],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    syncRemoteMetadata: true,
    metadataAuthorizationConfirmed: true,
    _internal: {
      uploadOne,
      updateMetadataOne: async ({ title, alt, caption }) => {
        metadataWrites += 1;
        return {
          status: 'metadata_updated_and_verified',
          observedAfter: { title, alt, caption },
        };
      },
    },
  });

  assert.equal(reused.items[0].status, 'reused_mapping_metadata_verified');
  assert.equal(uploads, 1);
  assert.equal(metadataWrites, 1);
  const index = await readAllinCmsImageIndex({ imageIndexPath: indexPath, expectedSiteKey: SITE_KEY });
  const record = Object.values(index.records)[0];
  assert.equal(record.status, 'verified');
  assert.equal(record.title, 'rear-hub-motor-side-view');
  assert.equal(record.description, 'Rear hub motor side view on a white background.');
  assert.equal(record.alt, 'Rear e-bike hub motor side view');
  assert.equal(record.caption, 'Updated caption from product-page context.');
  assert.equal(record.ai_metadata.page_context, 'product_detail');
  assert.equal(record.ai_metadata.confidence, 0.97);
  assert.equal(record.history.at(-1).stage, 'metadata_verified');
}));

test('serial upload rejects non-object AI metadata before remote upload', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'invalid-metadata.webp');
  const indexPath = join(dir, 'image-index.json');
  await assert.rejects(
    authorizedSerial({
      tab: mockTab(),
      localFiles: [{ localFile: image, metadata: ['not', 'an', 'object'] }],
      expectedSiteKey: SITE_KEY,
      imageIndexPath: indexPath,
    }),
    /metadata must be a JSON-serializable object/,
  );
}));

test('second writer is blocked by the per-index lock', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'locked.webp');
  const indexPath = join(dir, 'image-index.json');
  await writeFile(`${indexPath}.lock`, 'held');
  await assert.rejects(
    authorizedSerial({
      tab: mockTab(), localFiles: [image], expectedSiteKey: SITE_KEY, imageIndexPath: indexPath,
    }),
    (error) => error.code === 'ALLINCMS_IMAGE_INDEX_LOCKED',
  );
}));

test('lock cleanup failure is reported without erasing the completed upload result', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'cleanup-warning.webp');
  const indexPath = join(dir, 'image-index.json');
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [image],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    _internal: {
      acquireLock: async () => async () => { throw new Error('lock unlink denied'); },
      uploadOne: async ({ beforeRequest }) => {
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        return uploadedResult('cleanup-warning');
      },
    },
  });
  assert.equal(result.status, 'completed');
  assert.equal(result.items[0].status, 'uploaded_and_indexed');
  assert.equal(result.cleanup.imageIndexLockReleased, false);
  assert.equal(result.cleanup.error, 'lock unlink denied');
  assert.match(result.progressWarnings[0], /lock cleanup failed/);
}));


test('serial controller accepts more than ten files and never overlaps uploads', async () => withTempWorkspace(async (dir) => {
  const files = [];
  for (let index = 0; index < 12; index += 1) {
    files.push(await makeImage(dir, `bulk-${index + 1}.webp`, `unique-${index + 1}`));
  }
  const indexPath = join(dir, 'image-index.json');
  let active = 0;
  let maxActive = 0;
  const started = [];
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: files,
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    _internal: {
      uploadOne: async ({ localFile, beforeRequest }) => {
        active += 1;
        maxActive = Math.max(maxActive, active);
        const title = basename(localFile, '.webp');
        started.push(title);
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        await Promise.resolve();
        active -= 1;
        return uploadedResult(title);
      },
    },
  });
  assert.equal(result.status, 'completed');
  assert.equal(result.requested, 12);
  assert.equal(result.completed, 12);
  assert.equal(maxActive, 1);
  assert.deepEqual(started, files.map((file) => basename(file, '.webp')));
}));

test('upload error waits and reconciles an existing remote record before any resend', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'late-success.webp', 'late-success');
  const indexPath = join(dir, 'image-index.json');
  const events = [];
  let uploads = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [image],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    retryDelaysMs: [17],
    _internal: {
      delay: async (milliseconds) => { events.push(`delay:${milliseconds}`); },
      uploadOne: async ({ beforeRequest }) => {
        uploads += 1;
        events.push(`upload:${uploads}`);
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        const error = new Error('response timed out after remote acceptance');
        error.result = { status: 'upload_result_ambiguous', requestMayHaveSucceeded: true };
        throw error;
      },
      reconcileOne: async () => {
        events.push('reconcile');
        return { ...uploadedResult('late-success'), status: 'reconciled_existing' };
      },
    },
  });
  assert.equal(result.status, 'completed');
  assert.equal(uploads, 1);
  assert.deepEqual(events, ['upload:1', 'delay:17', 'reconcile']);
  assert.equal(result.items[0].status, 'reconciled_and_indexed');
  assert.equal(result.items[0].attempts, 1);
}));

test('exact remote absence permits retry of only the current image before the next image starts', async () => withTempWorkspace(async (dir) => {
  const one = await makeImage(dir, 'retry-one.webp', 'retry-one');
  const two = await makeImage(dir, 'retry-two.webp', 'retry-two');
  const indexPath = join(dir, 'image-index.json');
  const events = [];
  let firstAttempts = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [one, two],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    maxAttemptsPerImage: 3,
    retryDelaysMs: [5, 9],
    _internal: {
      delay: async (milliseconds) => { events.push(`delay:${milliseconds}`); },
      uploadOne: async ({ localFile, beforeRequest }) => {
        const title = basename(localFile, '.webp');
        events.push(`upload:${title}`);
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        if (title === 'retry-one' && firstAttempts++ === 0) {
          const error = new Error('temporary upload failure');
          error.result = { status: 'upload_result_ambiguous', requestMayHaveSucceeded: true };
          throw error;
        }
        return uploadedResult(title);
      },
      reconcileOne: async () => {
        events.push('reconcile:retry-one');
        return { status: 'not_found_stop', matches: 0, requestSent: false };
      },
    },
  });
  assert.equal(result.status, 'completed');
  assert.deepEqual(events, [
    'upload:retry-one',
    'delay:5',
    'reconcile:retry-one',
    'upload:retry-one',
    'upload:retry-two',
  ]);
  assert.equal(result.items[0].attempts, 2);
  assert.equal(result.items[1].attempts, 1);
}));

test('retry exhaustion stops the batch after delayed exact-absence checks', async () => withTempWorkspace(async (dir) => {
  const one = await makeImage(dir, 'always-fails.webp', 'always-fails');
  const two = await makeImage(dir, 'must-not-start.webp', 'must-not-start');
  const indexPath = join(dir, 'image-index.json');
  let uploads = 0;
  let reconciles = 0;
  const delays = [];
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [one, two],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    maxAttemptsPerImage: 3,
    retryDelaysMs: [2, 5],
    _internal: {
      delay: async (milliseconds) => { delays.push(milliseconds); },
      uploadOne: async ({ beforeRequest }) => {
        uploads += 1;
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        const error = new Error('temporary failure');
        error.result = { status: 'upload_result_ambiguous', requestMayHaveSucceeded: true };
        throw error;
      },
      reconcileOne: async () => {
        reconciles += 1;
        return { status: 'not_found_stop', matches: 0, requestSent: false };
      },
    },
  });
  assert.equal(result.status, 'stopped_retry_exhausted');
  assert.equal(uploads, 3);
  assert.equal(reconciles, 3);
  assert.deepEqual(delays, [2, 5, 5]);
  assert.equal(result.items[0].attempts, 3);
  assert.equal(result.completed, 0);
}));

test('uncertain reconciliation stops without a blind retry', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'uncertain.webp', 'uncertain');
  const indexPath = join(dir, 'image-index.json');
  let uploads = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [image],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    retryDelaysMs: [0],
    _internal: {
      uploadOne: async ({ beforeRequest }) => {
        uploads += 1;
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        const error = new Error('unknown response');
        error.result = { status: 'upload_result_ambiguous', requestMayHaveSucceeded: true };
        throw error;
      },
      reconcileOne: async () => ({ status: 'ambiguous_multiple_matches', matches: 2, requestSent: false }),
    },
  });
  assert.equal(result.status, 'stopped_ambiguous');
  assert.equal(uploads, 1);
  assert.equal(result.items[0].attempts, 1);
}));

test('metadata write runs once after upload retry succeeds', async () => withTempWorkspace(async (dir) => {
  const image = await makeImage(dir, 'metadata-after-retry.webp', 'metadata-after-retry');
  const indexPath = join(dir, 'image-index.json');
  let uploads = 0;
  let metadataWrites = 0;
  const result = await authorizedSerial({
    tab: mockTab(),
    localFiles: [{ localFile: image, alt: 'E-bike hub motor product image' }],
    expectedSiteKey: SITE_KEY,
    imageIndexPath: indexPath,
    syncRemoteMetadata: true,
    metadataAuthorizationConfirmed: true,
    retryDelaysMs: [0],
    _internal: {
      uploadOne: async ({ beforeRequest }) => {
        uploads += 1;
        await beforeRequest({ normalized: { sha256: 'a'.repeat(64), md5: 'b'.repeat(32) } });
        if (uploads === 1) {
          const error = new Error('first request failed');
          error.result = { status: 'upload_result_ambiguous', requestMayHaveSucceeded: true };
          throw error;
        }
        return uploadedResult('metadata-after-retry');
      },
      reconcileOne: async () => ({ status: 'not_found_stop', matches: 0, requestSent: false }),
      updateMetadataOne: async ({ title, alt, caption }) => {
        metadataWrites += 1;
        return { status: 'metadata_updated_and_verified', observedAfter: { title, alt, caption } };
      },
    },
  });
  assert.equal(result.status, 'completed');
  assert.equal(uploads, 2);
  assert.equal(metadataWrites, 1);
  assert.equal(result.items[0].status, 'uploaded_metadata_verified_and_indexed');
}));

test('serial upload source contains no concurrent batch primitive', async () => {
  const source = await readFile(new URL('./upload-media-browser.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /Promise\.all(?:Settled)?\s*\(/);
});

test('runtime preflight allows small WebP but blocks PNG when sharp is missing', async () => withTempWorkspace(async (dir) => {
  const webp = await makeImage(dir, 'small.webp', 'webp');
  const png = await makeImage(dir, 'needs-sharp.png', 'png');
  const result = await checkAllinCmsMediaRuntime({
    tab: mockTab(),
    expectedSiteKey: SITE_KEY,
    localFiles: [webp, png],
    _internal: { loadSharp: async () => { throw new Error('not installed'); } },
  });
  assert.equal(result.status, 'blocked');
  assert.equal(result.files[0].ready, true);
  assert.equal(result.files[1].ready, false);
  assert.equal(result.sharp.available, false);
}));
