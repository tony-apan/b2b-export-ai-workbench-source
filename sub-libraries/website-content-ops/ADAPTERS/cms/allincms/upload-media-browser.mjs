/**
 * AllinCMS media adapter for a signed-in Codex Browser tab.
 *
 * Preferred verified path (2026-07-27): one local PNG/JPG/WebP is normalized in
 * Node and uploaded by direct Next Server Action replay in the page's same-origin
 * session. This path performs zero UI clicks and opens no file chooser. The older
 * semantic UI path remains available for 1-5 files. Neither path reads or exports
 * cookies, Clerk tokens, Authorization headers, or complete action values.
 *
 * Direct media-record delete is verified with strict identity matching and zero UI
 * clicks. Delete completion is intentionally limited to the AllinCMS media card and
 * RSC media record disappearing. Direct batch replay, automatic retries, overwrite,
 * and content binding remain outside
 * the verified contract.
 */
import { constants as fsConstants } from 'node:fs';
import { lstat, mkdir, open, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import { basename, dirname, extname, isAbsolute } from 'node:path';
import { createHash, randomUUID } from 'node:crypto';

const WORKSPACE_ORIGIN = 'https://workspace.laicms.com';
const ASSET_ORIGIN = 'https://assets.laicms.com';
const MAX_BYTES = 5 * 1024 * 1024;
const VERIFIED_MAX_FILES = 5;
const ALLOWED_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp']);

const MEDIA_UPLOAD_OPERATION = 'allincms.media.upload';
const MEDIA_UPLOAD_AUTHORIZATION_VERSION = 1;
const MEDIA_UPLOAD_AUTHORIZATION_TTL_MS = 30 * 60 * 1000;
const MEDIA_UPLOAD_ENTRYPOINTS = new Set(['direct', 'serial', 'batch', 'single']);
const AI_OR_SYSTEM_ACTOR = /\b(ai|assistant|agent|bot|codex|claude|system|unknown)\b/i;

function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  throw new Error('Authorization context contains a non-canonical JSON value');
}

function uploadAuthorizationFileRecord(item) {
  const filename = typeof item?.filename === 'string' ? item.filename.trim() : '';
  const bytes = item?.bytes;
  const digest = typeof item?.sha256 === 'string' ? item.sha256.trim() : '';
  if (!filename || basename(filename) !== filename) {
    throw new Error('Authorization file records require a portable basename-only filename');
  }
  if (!Number.isInteger(bytes) || bytes < 1) {
    throw new Error(`Authorization file record ${filename} requires a positive integer byte count`);
  }
  if (!/^[a-f0-9]{64}$/.test(digest)) {
    throw new Error(`Authorization file record ${filename} requires a lowercase SHA-256 digest`);
  }
  return { filename, bytes, sha256: digest };
}

export function computeAllinCmsMediaUploadFileListDigest(files) {
  if (!Array.isArray(files) || files.length < 1) {
    throw new Error('Authorization file list must contain at least one file');
  }
  const records = files.map(uploadAuthorizationFileRecord);
  return sha256(Buffer.from(canonicalJson(records), 'utf8'));
}

function validateAuthorizationContextShape(authorizationContext, { expectedSiteKey, entrypoint, now = Date.now() }) {
  if (!authorizationContext || typeof authorizationContext !== 'object' || Array.isArray(authorizationContext)) {
    throw new Error('Explicit media upload authorizationContext is required before any AllinCMS request');
  }
  const requiredKeys = [
    'authorization_context_version',
    'site_key',
    'operation',
    'entrypoint',
    'file_list_digest_algorithm',
    'file_list_digest',
    'approval_actor',
    'approval_actor_type',
    'approval_identity_status',
    'approved_at',
    'expires_at',
  ];
  const keys = Object.keys(authorizationContext).sort();
  const expectedKeys = [...requiredKeys].sort();
  if (JSON.stringify(keys) !== JSON.stringify(expectedKeys)) {
    throw new Error(`authorizationContext must contain exactly: ${requiredKeys.join(', ')}`);
  }
  if (authorizationContext.authorization_context_version !== MEDIA_UPLOAD_AUTHORIZATION_VERSION) {
    throw new Error(`authorizationContext.authorization_context_version must be ${MEDIA_UPLOAD_AUTHORIZATION_VERSION}`);
  }
  if (authorizationContext.site_key !== expectedSiteKey || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(expectedSiteKey || '')) {
    throw new Error('authorizationContext.site_key must exactly match the requested AllinCMS site');
  }
  if (authorizationContext.operation !== MEDIA_UPLOAD_OPERATION) {
    throw new Error(`authorizationContext.operation must be ${MEDIA_UPLOAD_OPERATION}`);
  }
  if (!MEDIA_UPLOAD_ENTRYPOINTS.has(entrypoint) || authorizationContext.entrypoint !== entrypoint) {
    throw new Error(`authorizationContext.entrypoint must exactly match ${entrypoint}`);
  }
  if (authorizationContext.file_list_digest_algorithm !== 'sha256-canonical-json-v1') {
    throw new Error('authorizationContext.file_list_digest_algorithm must be sha256-canonical-json-v1');
  }
  if (!/^[a-f0-9]{64}$/.test(authorizationContext.file_list_digest || '')) {
    throw new Error('authorizationContext.file_list_digest must be 64 lowercase hexadecimal characters');
  }
  const actor = typeof authorizationContext.approval_actor === 'string'
    ? authorizationContext.approval_actor.trim()
    : '';
  if (!actor || AI_OR_SYSTEM_ACTOR.test(actor)) {
    throw new Error('authorizationContext.approval_actor must be a named non-AI approval actor');
  }
  if (authorizationContext.approval_actor_type !== 'human-asserted') {
    throw new Error('authorizationContext.approval_actor_type must be human-asserted');
  }
  if (authorizationContext.approval_identity_status !== 'not_verified') {
    throw new Error('authorizationContext.approval_identity_status must remain not_verified');
  }
  const approvedAt = Date.parse(authorizationContext.approved_at);
  const expiresAt = Date.parse(authorizationContext.expires_at);
  if (!Number.isFinite(approvedAt) || new Date(approvedAt).toISOString() !== authorizationContext.approved_at) {
    throw new Error('authorizationContext.approved_at must be a canonical ISO-8601 UTC timestamp');
  }
  if (!Number.isFinite(expiresAt) || new Date(expiresAt).toISOString() !== authorizationContext.expires_at) {
    throw new Error('authorizationContext.expires_at must be a canonical ISO-8601 UTC timestamp');
  }
  if (approvedAt > now) {
    throw new Error('authorizationContext.approved_at must not be in the future');
  }
  if (expiresAt <= approvedAt || expiresAt - approvedAt > MEDIA_UPLOAD_AUTHORIZATION_TTL_MS) {
    throw new Error('authorizationContext.expires_at must be after approved_at and no more than 30 minutes later');
  }
  if (now >= expiresAt) throw new Error('authorizationContext has expired; obtain fresh explicit approval');
  return authorizationContext;
}

function validateMediaUploadAuthorization({ authorizationContext, expectedSiteKey, entrypoint, files, now }) {
  validateAuthorizationContextShape(authorizationContext, { expectedSiteKey, entrypoint, now });
  const actualDigest = computeAllinCmsMediaUploadFileListDigest(files);
  if (authorizationContext.file_list_digest !== actualDigest) {
    throw new Error('authorizationContext.file_list_digest does not match the exact ordered upload file list');
  }
  return authorizationContext;
}

function delegatedMediaUploadAuthorization(authorizationContext, entrypoint, files) {
  return {
    ...authorizationContext,
    entrypoint,
    file_list_digest: computeAllinCmsMediaUploadFileListDigest(files),
  };
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function md5(value) {
  return createHash('md5').update(value).digest('hex');
}

function stripExtension(filename) {
  const extension = extname(filename);
  return extension ? filename.slice(0, -extension.length) : filename;
}

async function uniqueRole(playwright, role, names) {
  for (const name of names) {
    const locator = playwright.getByRole(role, { name, exact: true });
    const count = await locator.count();
    if (count === 1) return locator;
    if (count > 1) throw new Error(`Ambiguous ${role} ${JSON.stringify(name)}: ${count} matches`);
  }
  throw new Error(`Missing ${role}; tried ${names.map(JSON.stringify).join(', ')}`);
}

async function waitForPath(tab, predicate, description, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const current = new URL(await tab.url());
    if (predicate(current)) return current;
    await tab.playwright.waitForTimeout(100);
  }
  throw new Error(`Timed out waiting for ${description}; current URL is ${await tab.url()}`);
}

async function countMediaCardsByTitle(tab, title) {
  return tab.playwright.evaluate((expectedTitle) => [...document.querySelectorAll('p')]
    .filter((element) => element.textContent?.trim() === expectedTitle)
    .filter((element) => element.closest('div[data-slot="card"]')?.querySelector('img'))
    .length, title);
}

async function waitForMediaCard(tab, title, timeoutMs = 20_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const card = await tab.playwright.evaluate((expectedTitle) => {
      const matches = [...document.querySelectorAll('p')]
        .filter((element) => element.textContent?.trim() === expectedTitle)
        .map((element) => element.closest('div[data-slot="card"]'))
        .filter(Boolean);
      if (matches.length !== 1) return null;
      const image = matches[0].querySelector('img');
      return image
        ? { title: expectedTitle, url: image.currentSrc || image.src, text: matches[0].innerText }
        : null;
    }, title);
    if (card) return card;
    await tab.playwright.waitForTimeout(250);
  }
  throw new Error(`Timed out waiting for one unambiguous uploaded media card: ${title}`);
}

async function readMediaRecordFromRsc(tab, assetUrl) {
  return tab.playwright.evaluate((expectedUrl) => {
    for (const script of [...document.scripts]) {
      const raw = script.textContent || '';
      if (!raw.includes(expectedUrl)) continue;
      const normalized = raw.replaceAll('\\"', '"');
      const urlIndex = normalized.indexOf(`"url":"${expectedUrl}"`);
      if (urlIndex < 0) continue;

      // Media records are flat JSON objects in the observed RSC payload. Anchor
      // the object on its own `name` field instead of scanning an arbitrary
      // prefix, which can mix adjacent records during a multi-file response.
      const start = normalized.lastIndexOf('{"name":"', urlIndex);
      const end = normalized.indexOf('}', urlIndex);
      if (start < 0 || end < 0) continue;

      try {
        const record = JSON.parse(normalized.slice(start, end + 1));
        if (record.url !== expectedUrl) continue;
        return {
          mediaId: record.id || null,
          name: record.name || null,
          alt: record.alt || null,
          caption: record.caption || null,
          title: record.title || null,
          type: record.type || null,
          source: record.source || null,
          path: record.path || null,
          mimeType: record.mimeType || null,
          size: Number.isFinite(record.size) ? record.size : null,
          url: record.url,
          createdAt: record.createdAt || null,
          updatedAt: record.updatedAt || null,
        };
      } catch {
        // Keep looking in later RSC scripts; never guess a record from fragments.
      }
    }
    return null;
  }, assetUrl);
}

async function verifyImageInBrowser(tab, url) {
  return tab.playwright.evaluate((expectedUrl) => {
    const image = [...document.querySelectorAll('img')]
      .find((item) => item.src === expectedUrl || item.currentSrc === expectedUrl);
    return {
      ok: Boolean(image?.complete && image?.naturalWidth > 0 && image?.naturalHeight > 0),
      width: image?.naturalWidth || 0,
      height: image?.naturalHeight || 0,
      src: image?.currentSrc || image?.src || expectedUrl,
    };
  }, url);
}

function hasRecognizedImageSignature(buffer) {
  if (buffer.length >= 4 && buffer[0] === 0xff && buffer[1] === 0xd8) return true;
  if (buffer.length >= 8 && buffer.subarray(1, 4).toString('ascii') === 'PNG') return true;
  if (buffer.length >= 6 && ['GIF87a', 'GIF89a'].includes(buffer.subarray(0, 6).toString('ascii'))) return true;
  return buffer.length >= 12
    && buffer.subarray(0, 4).toString('ascii') === 'RIFF'
    && buffer.subarray(8, 12).toString('ascii') === 'WEBP';
}

export async function verifyAllinCmsMediaUrl({
  url,
  expectedSiteKey,
  expectedMimeType,
  timeoutMs = 20_000,
}) {
  const requested = new URL(url);
  if (requested.protocol !== 'https:' || requested.origin !== ASSET_ORIGIN) {
    throw new Error(`Unexpected AllinCMS asset origin: ${requested.origin}`);
  }
  if (!requested.pathname.startsWith(`/${expectedSiteKey}/`)) {
    throw new Error('Asset URL does not belong to the confirmed site key');
  }

  const response = await fetch(requested, {
    redirect: 'follow',
    credentials: 'omit',
    signal: typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
      ? AbortSignal.timeout(timeoutMs)
      : undefined,
  });
  if (!response.ok) throw new Error(`Anonymous asset GET failed: HTTP ${response.status}`);
  const finalUrl = new URL(response.url);
  if (finalUrl.origin !== ASSET_ORIGIN || !finalUrl.pathname.startsWith(`/${expectedSiteKey}/`)) {
    throw new Error('Anonymous asset GET redirected outside the confirmed site asset path');
  }
  const contentType = (response.headers.get('content-type') || '')
    .split(';')[0]
    .trim()
    .toLowerCase();
  if (!contentType.startsWith('image/')) {
    throw new Error(`Anonymous asset Content-Type is not an image: ${contentType || '(missing)'}`);
  }
  if (expectedMimeType && contentType !== expectedMimeType.toLowerCase()) {
    throw new Error(`Expected ${expectedMimeType}, received ${contentType}`);
  }
  const body = Buffer.from(await response.arrayBuffer());
  if (!hasRecognizedImageSignature(body)) {
    throw new Error('Anonymous asset body has no recognized PNG, JPG, GIF, or WebP signature');
  }
  return {
    ok: true,
    anonymousHttpsGet: true,
    httpStatus: response.status,
    contentType,
    bytes: body.length,
    contentSha256: sha256(body),
    contentMd5: md5(body),
    finalUrl: finalUrl.href,
    etagPresent: Boolean(response.headers.get('etag')),
  };
}

function summarizeUploadNetwork(events, expectedSiteKey) {
  const requests = new Map();
  const responses = new Map();
  for (const event of events) {
    if (event.method === 'Network.requestWillBeSent') {
      requests.set(event.params.requestId, event.params);
    } else if (event.method === 'Network.responseReceived') {
      responses.set(event.params.requestId, event.params.response);
    }
  }

  const actions = [...requests.values()].filter((params) => {
    try {
      const url = new URL(params.request.url);
      return params.request.method === 'POST'
        && url.origin === WORKSPACE_ORIGIN
        && url.pathname === `/${expectedSiteKey}/media`;
    } catch {
      return false;
    }
  });

  const assets = [...requests.values()].filter((params) => {
    try {
      const url = new URL(params.request.url);
      return params.request.method === 'GET'
        && params.type === 'Image'
        && url.origin === ASSET_ORIGIN;
    } catch {
      return false;
    }
  });

  const summarizeAction = (action) => {
    const response = responses.get(action.requestId);
    const headers = action.request.headers || {};
    const nextAction = headers['next-action'] || headers['Next-Action'] || '';
    const deploymentId = headers['x-deployment-id'] || headers['X-Deployment-Id'] || '';
    const contentType = headers['content-type'] || headers['Content-Type'] || '';
    return {
      method: action.request.method,
      routePattern: '/{site_key}/media',
      requestMimeType: contentType.split(';')[0] || null,
      responseStatus: response?.status ?? null,
      responseMimeType: response?.mimeType ?? null,
      nextActionPresent: Boolean(nextAction),
      nextActionLength: nextAction.length || null,
      nextActionSha256: nextAction ? sha256(nextAction) : null,
      nextRouterStateTreePresent: Boolean(
        headers['next-router-state-tree'] || headers['Next-Router-State-Tree'],
      ),
      deploymentFingerprint: deploymentId || null,
    };
  };

  return {
    actionCount: actions.length,
    action: actions.length === 1 ? summarizeAction(actions[0]) : null,
    actions: actions.map(summarizeAction),
    assets: assets.map((asset) => {
      const response = responses.get(asset.requestId);
      return {
        url: asset.request.url,
        responseStatus: response?.status ?? null,
        responseMimeType: response?.mimeType ?? null,
      };
    }),
  };
}

function sameFileSnapshot(left, right) {
  return left.dev === right.dev
    && left.ino === right.ino
    && left.size === right.size
    && left.mtimeMs === right.mtimeMs
    && left.ctimeMs === right.ctimeMs;
}

function assertPreparedFileSnapshot(item) {
  if (!Buffer.isBuffer(item?.sourceBuffer)) {
    throw new Error(`Missing immutable source-byte snapshot for ${item?.filename || 'media file'}`);
  }
  if (item.sourceBuffer.length !== item.bytes
      || sha256(item.sourceBuffer) !== item.sha256
      || md5(item.sourceBuffer) !== item.md5) {
    throw new Error(`Approved source-byte snapshot changed for ${item.filename}; obtain fresh explicit approval`);
  }
  return item;
}

function authorizationNow(_internal = {}) {
  const now = typeof _internal.now === 'function' ? _internal.now() : Date.now();
  if (!Number.isFinite(now)) throw new Error('Internal authorization clock must return finite epoch milliseconds');
  return now;
}

function mimeTypeForExtension(extension) {
  if (extension === '.jpg' || extension === '.jpeg') return 'image/jpeg';
  if (extension === '.png') return 'image/png';
  if (extension === '.gif') return 'image/gif';
  if (extension === '.webp') return 'image/webp';
  throw new Error(`Unsupported image extension ${extension}`);
}

function browserFilePayload(item) {
  assertPreparedFileSnapshot(item);
  return {
    name: item.filename,
    mimeType: mimeTypeForExtension(item.extension),
    buffer: Buffer.from(item.sourceBuffer),
  };
}

function assertBrowserFilePayload(item, payload) {
  assertPreparedFileSnapshot(item);
  if (payload?.name !== item.filename
      || payload?.mimeType !== mimeTypeForExtension(item.extension)
      || !Buffer.isBuffer(payload?.buffer)
      || payload.buffer.length !== item.bytes
      || sha256(payload.buffer) !== item.sha256) {
    throw new Error(`Browser file payload changed for ${item.filename}; stop before confirmation`);
  }
  return payload;
}

function assertNormalizedFileSnapshot(item) {
  if (!Buffer.isBuffer(item?.buffer)
      || item.buffer.length !== item.bytes
      || sha256(item.buffer) !== item.sha256
      || md5(item.buffer) !== item.md5) {
    throw new Error(`Normalized upload-byte snapshot changed for ${item?.filename || 'media file'}; stop before request`);
  }
  return item;
}

async function prepareLocalFiles(localFiles, maxFiles, _internal = {}) {
  if (!Array.isArray(localFiles)) throw new Error('localFiles must be an array');
  if (!Number.isInteger(maxFiles) || maxFiles < 1 || maxFiles > VERIFIED_MAX_FILES) {
    throw new Error(`maxFiles must be an integer from 1 to ${VERIFIED_MAX_FILES}`);
  }
  if (localFiles.length < 1 || localFiles.length > maxFiles) {
    throw new Error(`Select between 1 and ${maxFiles} files; received ${localFiles.length}`);
  }
  if (new Set(localFiles).size !== localFiles.length) {
    throw new Error('localFiles contains duplicate paths');
  }

  const lstatNow = _internal.lstat || lstat;
  const prepared = [];
  for (const localFile of localFiles) {
    if (!isAbsolute(localFile)) throw new Error(`localFile must be an absolute path: ${localFile}`);
    const pathState = await lstatNow(localFile);
    if (pathState.isSymbolicLink()) {
      throw new Error(`Refusing symbolic-link media input; select an immutable regular file: ${localFile}`);
    }
    if (!pathState.isFile()) throw new Error(`Not a file: ${localFile}`);
    if (pathState.size > MAX_BYTES) throw new Error(`File exceeds AllinCMS 5 MB limit: ${localFile}`);
    const extension = extname(localFile).toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(extension)) {
      throw new Error(`Unsupported image extension ${extension}: ${localFile}`);
    }

    let handle;
    let before;
    let after;
    let contents;
    try {
      handle = await open(localFile, fsConstants.O_RDONLY | (fsConstants.O_NOFOLLOW || 0));
      before = await handle.stat();
      if (!before.isFile()) throw new Error(`Not a regular file: ${localFile}`);
      if (before.size > MAX_BYTES) throw new Error(`File exceeds AllinCMS 5 MB limit: ${localFile}`);
      contents = await handle.readFile();
      after = await handle.stat();
    } catch (error) {
      if (error?.code === 'ELOOP') {
        throw new Error(`Refusing symbolic-link or retargeted media input: ${localFile}`);
      }
      throw error;
    } finally {
      await handle?.close();
    }
    if (!sameFileSnapshot(before, after) || contents.length !== after.size) {
      throw new Error(`Media file changed while its approval snapshot was being read: ${localFile}`);
    }
    if (contents.length < 1) throw new Error(`Media file is empty: ${localFile}`);

    const filename = basename(localFile);
    const title = stripExtension(filename);
    const sourceBuffer = Buffer.from(contents);
    prepared.push({
      localFile,
      filename,
      title,
      extension,
      bytes: sourceBuffer.length,
      sha256: sha256(sourceBuffer),
      md5: md5(sourceBuffer),
      sourceBuffer,
    });
  }

  const titles = prepared.map((item) => item.title);
  if (new Set(titles).size !== titles.length) {
    throw new Error('Every file in a batch must have a unique filename stem');
  }
  return prepared;
}

export async function createAllinCmsMediaUploadAuthorizationContext({
  localFiles,
  expectedSiteKey,
  entrypoint,
  approvalActor,
  approvedAt = new Date().toISOString(),
  expiresAt,
}) {
  if (!Array.isArray(localFiles) || localFiles.length < 1) {
    throw new Error('localFiles must contain at least one item for authorization');
  }
  const paths = localFiles.map((item) => (typeof item === 'string' ? item : item?.localFile));
  const prepared = [];
  for (const localFile of paths) prepared.push((await prepareLocalFiles([localFile], 1))[0]);
  const approvedAtMs = Date.parse(approvedAt);
  const resolvedExpiresAt = expiresAt
    ?? (Number.isFinite(approvedAtMs)
      ? new Date(approvedAtMs + MEDIA_UPLOAD_AUTHORIZATION_TTL_MS).toISOString()
      : '');
  const context = {
    authorization_context_version: MEDIA_UPLOAD_AUTHORIZATION_VERSION,
    site_key: expectedSiteKey,
    operation: MEDIA_UPLOAD_OPERATION,
    entrypoint,
    file_list_digest_algorithm: 'sha256-canonical-json-v1',
    file_list_digest: computeAllinCmsMediaUploadFileListDigest(prepared),
    approval_actor: approvalActor,
    approval_actor_type: 'human-asserted',
    approval_identity_status: 'not_verified',
    approved_at: approvedAt,
    expires_at: resolvedExpiresAt,
  };
  validateMediaUploadAuthorization({
    authorizationContext: context,
    expectedSiteKey,
    entrypoint,
    files: prepared,
  });
  return context;
}

const DIRECT_TARGET_BYTES = 1024 * 1024;
const DIRECT_MAX_BYTES = 2 * 1024 * 1024;

async function waitForExistingImageDecode(tab, url, timeoutMs = 20_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const state = await verifyImageInBrowser(tab, url);
    if (state.ok) return state;
    await tab.playwright.waitForTimeout(250);
  }
  return verifyImageInBrowser(tab, url);
}

async function normalizeForDirectUpload(input) {
  assertPreparedFileSnapshot(input);
  const original = Buffer.from(input.sourceBuffer);
  const outputFilename = `${input.title}.webp`;

  if (input.extension === '.gif') {
    throw new Error('Direct upload has not verified animated GIF normalization; use PNG, JPG, or WebP');
  }
  if (input.extension === '.webp' && original.length <= DIRECT_TARGET_BYTES) {
    return {
      buffer: original,
      filename: outputFilename,
      mimeType: 'image/webp',
      bytes: original.length,
      sha256: sha256(original),
      md5: md5(original),
      normalized: false,
    };
  }

  let sharp;
  try {
    sharp = (await import('sharp')).default;
  } catch (error) {
    throw new Error(`Direct upload needs the sharp package to normalize ${input.extension} to WebP: ${error.message}`);
  }

  const metadata = await sharp(original, { animated: false }).metadata();
  const originalWidth = metadata.width || null;
  const attempts = [
    { quality: 82, width: null },
    { quality: 76, width: originalWidth ? Math.min(originalWidth, 2400) : 2400 },
    { quality: 70, width: originalWidth ? Math.min(originalWidth, 2000) : 2000 },
    { quality: 64, width: originalWidth ? Math.min(originalWidth, 1600) : 1600 },
    { quality: 58, width: originalWidth ? Math.min(originalWidth, 1280) : 1280 },
  ];

  let output = null;
  for (const attempt of attempts) {
    let pipeline = sharp(original, { animated: false }).rotate();
    if (attempt.width) {
      pipeline = pipeline.resize({ width: attempt.width, withoutEnlargement: true });
    }
    output = await pipeline.webp({ quality: attempt.quality, effort: 4 }).toBuffer();
    if (output.length <= DIRECT_TARGET_BYTES) break;
  }
  if (!output || output.length > DIRECT_MAX_BYTES) {
    throw new Error(`Normalized WebP still exceeds the verified 2 MB direct-upload ceiling: ${output?.length || 0} bytes`);
  }

  return {
    buffer: output,
    filename: outputFilename,
    mimeType: 'image/webp',
    bytes: output.length,
    sha256: sha256(output),
    md5: md5(output),
    normalized: true,
  };
}

async function discoverDirectMediaActionContract({
  tab,
  cdp,
  expectedSiteKey,
  actionExportName,
  actionLabel,
}) {
  const pageState = await tab.playwright.evaluate(() => {
    const scriptSources = [...document.scripts].map((script) => script.src).filter(Boolean);
    let siteId = null;
    for (const script of [...document.scripts]) {
      const normalized = (script.textContent || '').replaceAll('\\"', '"');
      const match = normalized.match(/"site":\{"id":"([0-9a-f]{24})","name":"[^"]+","slug":"([^"]+)"/);
      if (match) {
        siteId = match[1];
        return { scriptSources, siteId, siteKey: match[2] };
      }
    }
    return { scriptSources, siteId, siteKey: null };
  });
  if (!pageState.siteId || pageState.siteKey !== expectedSiteKey) {
    throw new Error('Could not derive the current site ID from the confirmed media page RSC state');
  }

  const deploymentIds = [...new Set(pageState.scriptSources
    .map((source) => source.match(/[?&]dpl=([0-9a-f]{40})/)?.[1])
    .filter(Boolean))];
  if (deploymentIds.length !== 1) {
    throw new Error(`Expected one deployment fingerprint; observed ${deploymentIds.length}`);
  }

  const chunkTexts = [];
  for (const source of pageState.scriptSources) {
    const response = await fetch(source, { credentials: 'omit' });
    if (!response.ok) throw new Error(`Could not read AllinCMS client chunk: HTTP ${response.status}`);
    chunkTexts.push(await response.text());
  }
  if (!actionExportName || !/^[A-Za-z0-9_]+$/.test(actionExportName)) {
    throw new Error('A safe actionExportName is required');
  }
  const actionIds = [...new Set(chunkTexts.flatMap((text) => {
    const matches = [];
    const pattern = new RegExp(
      `createServerReference\\)\\("([0-9a-f]{32,64})"[\\s\\S]{0,240}"${actionExportName}"\\)`,
      'g',
    );
    for (const match of text.matchAll(pattern)) matches.push(match[1]);
    return matches;
  }))];
  if (actionIds.length !== 1) {
    throw new Error(`Expected one ${actionLabel || actionExportName} Server Action reference; observed ${actionIds.length}`);
  }

  const routerResult = await cdp.send('Runtime.evaluate', {
    expression: 'JSON.stringify(history.state?.__PRIVATE_NEXTJS_INTERNALS_TREE?.tree || null)',
    returnByValue: true,
  });
  const routerTree = routerResult?.result?.value;
  if (!routerTree || routerTree === 'null') {
    throw new Error('Current Next.js router state tree is unavailable');
  }

  return {
    actionId: actionIds[0],
    actionIdLength: actionIds[0].length,
    actionIdSha256: sha256(actionIds[0]),
    deploymentId: deploymentIds[0],
    siteId: pageState.siteId,
    routerTree,
  };
}

function runtimeValue(result) {
  if (result?.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description
      || result.exceptionDetails.text
      || 'CDP Runtime.evaluate failed');
  }
  return result?.result?.value;
}

async function inspectUploadedMedia({ tab, expectedSiteKey, expectedTitle, timeoutMs }) {
  const errors = [];
  let card = null;
  let media = null;
  let image = { ok: false, width: 0, height: 0, src: null };
  let anonymous = { ok: false, anonymousHttpsGet: false };

  try {
    card = await waitForMediaCard(tab, expectedTitle, timeoutMs);
  } catch (error) {
    errors.push(`backend reload: ${error.message}`);
  }
  if (card?.url) {
    media = await readMediaRecordFromRsc(tab, card.url);
    if (!media) errors.push('RSC media record is missing');
    if (!media?.mediaId) errors.push('media ID is missing');
    if (media && media.url !== card.url) errors.push('RSC media URL does not match the media card URL');
    image = await waitForExistingImageDecode(tab, card.url, timeoutMs);
    if (!image.ok) errors.push('media-card image did not decode in the browser');
    try {
      anonymous = await verifyAllinCmsMediaUrl({
        url: card.url,
        expectedSiteKey,
        expectedMimeType: media?.mimeType || 'image/webp',
        timeoutMs,
      });
    } catch (error) {
      errors.push(`anonymous asset verification: ${error.message}`);
    }
  }
  return { card, media, image, anonymous, errors };
}

function createAmbiguousUploadResult({
  input,
  normalized,
  expectedSiteKey,
  phase,
  error,
  replay = null,
  network = null,
  contract = null,
}) {
  return {
    status: 'upload_result_ambiguous',
    requestMayHaveSucceeded: true,
    automaticRetryAllowed: false,
    reconciliationRequired: true,
    retryPolicy: 'do_not_retry_automatically_after_direct_request',
    phase,
    interaction: {
      mode: 'direct_next_server_action_replay',
      uiClicks: 0,
      fileChooserEvents: 0,
    },
    input: input ? {
      filename: input.filename,
      title: input.title,
      bytes: input.bytes,
      sha256: input.sha256,
      md5: input.md5,
      normalizedFilename: normalized?.filename || null,
      normalizedBytes: normalized?.bytes || null,
      normalizedSha256: normalized?.sha256 || null,
      normalizedMd5: normalized?.md5 || null,
    } : null,
    site: { siteKey: expectedSiteKey },
    replay,
    network,
    contract: contract ? {
      actionIdStored: false,
      actionIdLength: contract.actionIdLength,
      actionIdSha256: contract.actionIdSha256,
      deploymentFingerprint: contract.deploymentId,
    } : null,
    verification: { contractVerified: false },
    errors: [error instanceof Error ? error.message : String(error)],
  };
}

function throwUploadResult(result, message = 'Direct AllinCMS media upload is ambiguous; reconcile before any retry') {
  const error = new Error(message);
  error.result = result;
  throw error;
}

export async function uploadAllinCmsMediaDirect({
  tab,
  localFile,
  expectedSiteKey,
  timeoutMs = 30_000,
  authorizationContext,
  beforeRequest,
  _internal = {},
}) {
  validateAuthorizationContextShape(authorizationContext, {
    expectedSiteKey,
    entrypoint: 'direct',
    now: authorizationNow(_internal),
  });
  if (!tab?.playwright || !tab?.capabilities) {
    throw new Error('A claimed Browser tab with Playwright and CDP capabilities is required');
  }

  const prepareInput = _internal.prepareInput || (async (file) => (await prepareLocalFiles([file], 1))[0]);
  const normalizeInput = _internal.normalizeInput || normalizeForDirectUpload;
  const countExisting = _internal.countExisting || countMediaCardsByTitle;
  const getCdp = _internal.getCdp || ((currentTab) => currentTab.capabilities.get('cdp'));
  const discoverContract = _internal.discoverContract || discoverDirectMediaActionContract;
  const summarizeNetwork = _internal.summarizeNetwork || summarizeUploadNetwork;
  const inspectResult = _internal.inspectResult || inspectUploadedMedia;

  const input = _internal.preparedInput || await prepareInput(localFile);
  assertPreparedFileSnapshot(input);
  validateMediaUploadAuthorization({
    authorizationContext,
    expectedSiteKey,
    entrypoint: 'direct',
    files: [input],
    now: authorizationNow(_internal),
  });
  const currentUrl = new URL(await tab.url());
  if (currentUrl.origin !== WORKSPACE_ORIGIN
      || currentUrl.pathname !== `/${expectedSiteKey}/media`) {
    throw new Error(`Open the confirmed media page first; current URL is ${currentUrl.href}`);
  }
  if (await countExisting(tab, input.title)) {
    throw new Error(`A media card already uses title ${JSON.stringify(input.title)}; rename or reuse it explicitly`);
  }

  const normalized = await normalizeInput(input);
  const cdp = await getCdp(tab);
  await cdp.send('Network.enable', {});
  const contract = await discoverContract({
    tab,
    cdp,
    expectedSiteKey,
    actionExportName: 'uploadMedia',
    actionLabel: 'uploadMedia',
  });
  const cursor = _internal.readCursor
    ? await _internal.readCursor({ cdp })
    : await cdp.readEvents({
      methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
      limit: 1,
      timeoutMs: 1,
    });

  const expression = `(async()=>{
    const bytes=Uint8Array.from(atob(${JSON.stringify(normalized.buffer.toString('base64'))}),c=>c.charCodeAt(0));
    const file=new File([bytes],${JSON.stringify(normalized.filename)},{type:'image/webp'});
    const form=new FormData();
    form.append('_1_files',file);
    form.append('0',JSON.stringify([${JSON.stringify(contract.siteId)},'$K1']));
    const response=await window.fetch(location.pathname,{
      method:'POST',
      credentials:'include',
      headers:{
        Accept:'text/x-component',
        'next-action':${JSON.stringify(contract.actionId)},
        'next-router-state-tree':${JSON.stringify(contract.routerTree)},
        'x-deployment-id':${JSON.stringify(contract.deploymentId)}
      },
      body:form
    });
    const text=await response.text();
    return {
      status:response.status,
      ok:response.ok,
      contentType:response.headers.get('content-type'),
      responseBytes:text.length
    };
  })()`;

  if (beforeRequest) {
    await beforeRequest({
      input: {
        filename: input.filename,
        title: input.title,
        bytes: input.bytes,
        sha256: input.sha256,
        md5: input.md5,
      },
      normalized: {
        filename: normalized.filename,
        bytes: normalized.bytes,
        sha256: normalized.sha256,
        md5: normalized.md5,
      },
      site: { siteKey: expectedSiteKey },
    });
  }

  // The callback above may take arbitrary time. Bind the actual mutation edge to
  // the same approved source snapshot, normalized bytes, site, entrypoint and
  // current wall clock immediately before Runtime.evaluate/sendReplay.
  assertPreparedFileSnapshot(input);
  assertNormalizedFileSnapshot(normalized);
  validateMediaUploadAuthorization({
    authorizationContext,
    expectedSiteKey,
    entrypoint: 'direct',
    files: [input],
    now: authorizationNow(_internal),
  });

  let replay = null;
  let replayError = null;
  let network = null;
  try {
    try {
      replay = _internal.sendReplay
        ? await _internal.sendReplay({ cdp, expression, timeoutMs })
        : runtimeValue(await cdp.send('Runtime.evaluate', {
          expression,
          awaitPromise: true,
          returnByValue: true,
        }, { timeoutMs }));
    } catch (error) {
      replayError = error.message;
    }

    const captured = _internal.readCaptured
      ? await _internal.readCaptured({ cdp, cursor })
      : await cdp.readEvents({
        afterSequence: cursor.cursor,
        methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
        limit: 1000,
        timeoutMs: 1_500,
      });
    network = summarizeNetwork(captured.events || captured, expectedSiteKey);

    if (_internal.reloadPage) {
      await _internal.reloadPage({ tab, timeoutMs });
    } else {
      await tab.reload();
      try {
        await tab.playwright.waitForLoadState('domcontentloaded', { timeoutMs: 15_000 });
      } catch {
        // The refreshed media record below is authoritative.
      }
    }

    const inspected = await inspectResult({
      tab,
      expectedSiteKey,
      expectedTitle: input.title,
      timeoutMs,
    });
    const errors = [...(inspected.errors || [])];
    if (replayError) errors.unshift(`direct replay: ${replayError}`);
    if (replay?.status !== 200) errors.push(`direct replay returned HTTP ${replay?.status ?? 'unknown'}`);
    if (!String(replay?.contentType || '').startsWith('text/x-component')) {
      errors.push(`direct replay returned unexpected Content-Type ${replay?.contentType || '(missing)'}`);
    }
    if (network.actionCount !== 1) {
      errors.push(`expected one direct Server Action request; observed ${network.actionCount}`);
    }
    if (network.action?.responseStatus !== 200) {
      errors.push(`captured Server Action response was ${network.action?.responseStatus ?? 'missing'}`);
    }

    const result = {
      status: errors.length === 0 ? 'uploaded_and_verified' : 'upload_result_ambiguous',
      requestMayHaveSucceeded: true,
      automaticRetryAllowed: false,
      reconciliationRequired: errors.length > 0,
      retryPolicy: 'do_not_retry_automatically_after_direct_request',
      interaction: {
        mode: 'direct_next_server_action_replay',
        uiClicks: 0,
        fileChooserEvents: 0,
      },
      input: {
        filename: input.filename,
        title: input.title,
        bytes: input.bytes,
        sha256: input.sha256,
        md5: input.md5,
        normalizedFilename: normalized.filename,
        normalizedBytes: normalized.bytes,
        normalizedSha256: normalized.sha256,
        normalizedMd5: normalized.md5,
      },
      site: { siteKey: expectedSiteKey },
      media: inspected.media,
      image: inspected.image,
      anonymous: inspected.anonymous,
      replay,
      network,
      contract: {
        actionIdStored: false,
        actionIdLength: contract.actionIdLength,
        actionIdSha256: contract.actionIdSha256,
        deploymentFingerprint: contract.deploymentId,
      },
      verification: {
        oneDirectInterfaceRequest: network.actionCount === 1,
        serverAction200: replay?.status === 200 && network.action?.responseStatus === 200,
        mediaRecordPresent: Boolean(inspected.media),
        mediaIdPresent: Boolean(inspected.media?.mediaId),
        backendReloadPersists: Boolean(inspected.card),
        anonymousHttpsGet: inspected.anonymous?.ok === true,
        browserImageDecodes: inspected.image?.ok === true,
        contractVerified: errors.length === 0,
      },
      errors,
    };

    if (errors.length) throwUploadResult(result);
    return result;
  } catch (error) {
    if (error?.result?.status === 'upload_result_ambiguous') throw error;
    throwUploadResult(createAmbiguousUploadResult({
      input,
      normalized,
      expectedSiteKey,
      phase: network ? 'post_request_reload_or_verification' : 'post_request_capture',
      error,
      replay,
      network,
      contract,
    }));
  }
}

const IMAGE_INDEX_SCHEMA_VERSION = 1;

function isoNow() {
  return new Date().toISOString();
}

function createEmptyImageIndex(expectedSiteKey) {
  return {
    schemaVersion: IMAGE_INDEX_SCHEMA_VERSION,
    kind: 'allincms-local-image-index',
    siteKey: expectedSiteKey,
    updatedAt: isoNow(),
    records: {},
  };
}

export async function readAllinCmsImageIndex({ imageIndexPath, expectedSiteKey }) {
  if (!isAbsolute(imageIndexPath || '')) {
    throw new Error('imageIndexPath must be an absolute path in the private runtime workspace');
  }
  try {
    const parsed = JSON.parse(await readFile(imageIndexPath, 'utf8'));
    if (parsed.schemaVersion !== IMAGE_INDEX_SCHEMA_VERSION || parsed.kind !== 'allincms-local-image-index') {
      throw new Error('Unsupported AllinCMS image-index schema');
    }
    if (parsed.siteKey !== expectedSiteKey) {
      throw new Error('Image index belongs to a different AllinCMS site key');
    }
    if (!parsed.records || typeof parsed.records !== 'object' || Array.isArray(parsed.records)) {
      throw new Error('Image index records must be an object keyed by source SHA-256');
    }
    return parsed;
  } catch (error) {
    if (error?.code === 'ENOENT') return createEmptyImageIndex(expectedSiteKey);
    throw error;
  }
}

async function writeAllinCmsImageIndexAtomic({ imageIndexPath, index }) {
  await mkdir(dirname(imageIndexPath), { recursive: true });
  const temporaryPath = `${imageIndexPath}.${process.pid}.${randomUUID()}.tmp`;
  const payload = `${JSON.stringify({ ...index, updatedAt: isoNow() }, null, 2)}\n`;
  try {
    await writeFile(temporaryPath, payload, { encoding: 'utf8', mode: 0o600 });
    await rename(temporaryPath, imageIndexPath);
  } catch (error) {
    try {
      await unlink(temporaryPath);
    } catch {
      // Best-effort cleanup only; preserve the original write error.
    }
    throw error;
  }
}

async function acquireAllinCmsImageIndexLock(imageIndexPath) {
  const lockPath = `${imageIndexPath}.lock`;
  await mkdir(dirname(imageIndexPath), { recursive: true });
  let handle;
  try {
    handle = await open(lockPath, 'wx', 0o600);
  } catch (error) {
    if (error?.code === 'EEXIST') {
      const locked = new Error(`AllinCMS image index is already locked: ${lockPath}`);
      locked.code = 'ALLINCMS_IMAGE_INDEX_LOCKED';
      locked.lockPath = lockPath;
      throw locked;
    }
    throw error;
  }
  await handle.writeFile(`${JSON.stringify({ pid: process.pid, acquiredAt: isoNow() })}\n`, 'utf8');
  return async () => {
    try {
      await handle.close();
    } finally {
      try {
        await unlink(lockPath);
      } catch (error) {
        if (error?.code !== 'ENOENT') throw error;
      }
    }
  };
}

function appendIndexHistory(existing, stage, detail = null) {
  const history = Array.isArray(existing?.history) ? existing.history.slice(-19) : [];
  history.push({ at: isoNow(), stage, detail });
  return history;
}

async function persistIndexRecord({ imageIndexPath, index, sourceSha256, patch, stage }) {
  const existing = index.records[sourceSha256] || null;
  index.records[sourceSha256] = {
    ...(existing || {}),
    ...patch,
    source_sha256: sourceSha256,
    updated_at: isoNow(),
    history: appendIndexHistory(existing, stage, patch.status || null),
  };
  await writeAllinCmsImageIndexAtomic({ imageIndexPath, index });
  return index.records[sourceSha256];
}

function serialInputDescriptor(value) {
  if (typeof value === 'string') return { localFile: value };
  if (!value || typeof value !== 'object' || typeof value.localFile !== 'string') {
    throw new Error('Each serial upload item must be an absolute file path or { localFile, title?, description?, alt?, caption?, notes?, metadata? }');
  }
  let metadata;
  if (value.metadata !== undefined && value.metadata !== null) {
    if (typeof value.metadata !== 'object' || Array.isArray(value.metadata)) {
      throw new Error('media metadata must be a JSON-serializable object');
    }
    try {
      metadata = JSON.parse(JSON.stringify(value.metadata));
    } catch (error) {
      throw new Error(`media metadata must be JSON-serializable: ${error.message}`);
    }
  }
  return {
    localFile: value.localFile,
    title: value.title ?? undefined,
    description: value.description ?? undefined,
    alt: value.alt ?? undefined,
    caption: value.caption ?? undefined,
    notes: value.notes ?? undefined,
    metadata,
  };
}

function localMetadataPatch(descriptor, existingRecord = null) {
  return {
    requested_title: descriptor.title ?? existingRecord?.requested_title ?? null,
    description: descriptor.description ?? existingRecord?.description ?? null,
    alt: descriptor.alt ?? existingRecord?.alt ?? null,
    caption: descriptor.caption ?? existingRecord?.caption ?? null,
    notes: descriptor.notes ?? existingRecord?.notes ?? null,
    ai_metadata: descriptor.metadata ?? existingRecord?.ai_metadata ?? null,
  };
}

function hasNewLocalMetadata(descriptor) {
  return ['title', 'description', 'alt', 'caption', 'notes', 'metadata']
    .some((key) => descriptor[key] !== undefined);
}

function verifiedIndexRecord(record) {
  return Boolean(
    record
    && ['verified', 'reconciled_existing'].includes(record.status)
    && record.media_id
    && record.url,
  );
}

function mappingPatch({ prepared, descriptor, result, status, existingRecord = null }) {
  return {
    status,
    source_file_name: prepared.filename,
    source_file_path: prepared.localFile,
    source_md5: prepared.md5,
    title: result.media?.title || result.media?.name || prepared.title,
    ...localMetadataPatch(descriptor, existingRecord),
    allincms_metadata_observed: {
      title: result.media?.title || result.media?.name || prepared.title,
      alt: result.media?.alt ?? null,
      caption: result.media?.caption ?? null,
      sync_status: 'upload_defaults_observed_no_post_upload_metadata_update',
    },
    normalized_upload_sha256: result.input?.normalizedSha256 || existingRecord?.normalized_upload_sha256 || null,
    normalized_upload_md5: result.input?.normalizedMd5 || existingRecord?.normalized_upload_md5 || null,
    media_id: result.media?.mediaId || null,
    url: result.media?.url || result.anonymous?.finalUrl || null,
    mime_type: result.media?.mimeType || result.anonymous?.contentType || null,
    remote_sha256: result.anonymous?.contentSha256 || null,
    remote_md5: result.anonymous?.contentMd5 || null,
    verified_at: isoNow(),
  };
}

export async function reconcileAllinCmsMediaDirect({
  tab,
  expectedSiteKey,
  expectedTitle,
  controlledReload = true,
  timeoutMs = 30_000,
  _internal = {},
}) {
  const base = {
    requestSent: false,
    automaticRetryAllowed: false,
    interaction: { mode: 'read_only_reconciliation', uiClicks: 0, fileChooserEvents: 0 },
    site: { siteKey: expectedSiteKey },
    expectedTitle,
  };
  try {
    if (!tab?.playwright) throw new Error('A claimed Browser tab is required');
    const currentUrl = new URL(await tab.url());
    if (currentUrl.origin !== WORKSPACE_ORIGIN
        || currentUrl.pathname !== `/${expectedSiteKey}/media`) {
      throw new Error(`Open the confirmed media page first; current URL is ${currentUrl.href}`);
    }

    if (controlledReload) {
      if (_internal.reloadPage) {
        await _internal.reloadPage({ tab, timeoutMs });
      } else {
        await tab.reload();
        try {
          await tab.playwright.waitForLoadState('domcontentloaded', { timeoutMs: 15_000 });
        } catch {
          // Continue to authoritative record inspection.
        }
      }
    }

    const count = _internal.countExisting
      ? await _internal.countExisting(tab, expectedTitle)
      : await countMediaCardsByTitle(tab, expectedTitle);
    if (count === 0) {
      return { ...base, status: 'not_found_stop', reconciliationRequired: true, matches: 0 };
    }
    if (count !== 1) {
      return {
        ...base,
        status: 'ambiguous_multiple_matches',
        reconciliationRequired: true,
        matches: count,
      };
    }

    const inspected = _internal.inspectResult
      ? await _internal.inspectResult({ tab, expectedSiteKey, expectedTitle, timeoutMs })
      : await inspectUploadedMedia({ tab, expectedSiteKey, expectedTitle, timeoutMs });
    const errors = [...(inspected.errors || [])];
    if (!inspected.media?.mediaId) errors.push('media ID is missing');
    if (!inspected.media?.url) errors.push('media URL is missing');
    if (errors.length) {
      return {
        ...base,
        status: 'verification_failed',
        reconciliationRequired: true,
        matches: 1,
        media: inspected.media || null,
        image: inspected.image || null,
        anonymous: inspected.anonymous || null,
        errors,
      };
    }
    return {
      ...base,
      status: 'reconciled_existing',
      reconciliationRequired: false,
      matches: 1,
      media: inspected.media,
      image: inspected.image,
      anonymous: inspected.anonymous,
      verification: {
        mediaRecordPresent: true,
        mediaIdPresent: true,
        anonymousHttpsGet: inspected.anonymous?.ok === true,
        browserImageDecodes: inspected.image?.ok === true,
        contractVerified: true,
      },
      errors: [],
    };
  } catch (error) {
    return {
      ...base,
      status: 'verification_failed',
      reconciliationRequired: true,
      errors: [error.message],
    };
  }
}

export async function checkAllinCmsMediaRuntime({
  tab,
  expectedSiteKey,
  localFiles = [],
  _internal = {},
}) {
  const errors = [];
  const warnings = [];
  let currentUrl = null;
  let sharpAvailable = false;
  let sharpError = null;

  try {
    currentUrl = new URL(await tab?.url());
  } catch (error) {
    errors.push(`browser tab URL unavailable: ${error.message}`);
  }
  if (!tab?.playwright || !tab?.capabilities) {
    errors.push('claimed Browser tab with Playwright and CDP capabilities is required');
  }
  if (currentUrl && (currentUrl.origin !== WORKSPACE_ORIGIN
      || currentUrl.pathname !== `/${expectedSiteKey}/media`)) {
    errors.push(`open the exact signed-in media page first: ${WORKSPACE_ORIGIN}/${expectedSiteKey}/media`);
  }

  try {
    const loader = _internal.loadSharp || (() => import('sharp'));
    await loader();
    sharpAvailable = true;
  } catch (error) {
    sharpError = error.message;
    warnings.push('sharp is unavailable; only WebP files at or below 1 MB can use the direct path');
  }

  const files = [];
  for (const value of localFiles) {
    const descriptor = serialInputDescriptor(value);
    try {
      const prepared = (await prepareLocalFiles([descriptor.localFile], 1))[0];
      const directWithoutSharp = prepared.extension === '.webp' && prepared.bytes <= DIRECT_TARGET_BYTES;
      const blockedGif = prepared.extension === '.gif';
      const ready = !blockedGif && (directWithoutSharp || sharpAvailable);
      files.push({
        localFile: prepared.localFile,
        extension: prepared.extension,
        bytes: prepared.bytes,
        sourceSha256: prepared.sha256,
        directWithoutSharp,
        ready,
        reason: ready
          ? null
          : blockedGif
            ? 'animated GIF normalization is not verified'
            : `sharp is required to normalize ${prepared.extension} or oversized WebP`,
      });
      if (!ready) errors.push(`${prepared.filename}: ${files.at(-1).reason}`);
    } catch (error) {
      files.push({ localFile: descriptor.localFile, ready: false, reason: error.message });
      errors.push(error.message);
    }
  }

  return {
    status: errors.length ? 'blocked' : 'ready',
    exactMediaPageReady: Boolean(currentUrl
      && currentUrl.origin === WORKSPACE_ORIGIN
      && currentUrl.pathname === `/${expectedSiteKey}/media`),
    signedInState: currentUrl?.origin === WORKSPACE_ORIGIN ? 'inferred_from_exact_media_page' : 'not_confirmed',
    cdpAvailable: Boolean(tab?.capabilities),
    sharp: { available: sharpAvailable, error: sharpError },
    files,
    errors,
    warnings,
  };
}

export async function uploadAllinCmsMediaSerial({
  tab,
  localFiles,
  expectedSiteKey,
  imageIndexPath,
  authorizationContext,
  progressMode = 'visible',
  onProgress,
  syncRemoteMetadata = false,
  metadataAuthorizationConfirmed = false,
  timeoutMs = 30_000,
  maxAttemptsPerImage = 3,
  retryDelaysMs = [2_000, 5_000],
  _internal = {},
}) {
  validateAuthorizationContextShape(authorizationContext, {
    expectedSiteKey,
    entrypoint: 'serial',
    now: authorizationNow(_internal),
  });
  if (!Array.isArray(localFiles) || localFiles.length < 1) {
    throw new Error('localFiles must contain at least one item');
  }
  if (!Number.isInteger(maxAttemptsPerImage) || maxAttemptsPerImage < 1) {
    throw new Error('maxAttemptsPerImage must be a positive integer');
  }
  if (!Array.isArray(retryDelaysMs) || retryDelaysMs.length < 1
      || retryDelaysMs.some((value) => !Number.isFinite(value) || value < 0)) {
    throw new Error('retryDelaysMs must contain one or more non-negative finite numbers');
  }
  if (!['visible', 'quiet'].includes(progressMode)) {
    throw new Error('progressMode must be visible or quiet');
  }
  if (!isAbsolute(imageIndexPath || '')) {
    throw new Error('imageIndexPath must be an absolute path in the private runtime workspace');
  }

  const descriptors = localFiles.map(serialInputDescriptor);
  const authorizationFiles = [];
  for (const descriptor of descriptors) {
    authorizationFiles.push((await prepareLocalFiles([descriptor.localFile], 1))[0]);
  }
  validateMediaUploadAuthorization({
    authorizationContext,
    expectedSiteKey,
    entrypoint: 'serial',
    files: authorizationFiles,
    now: authorizationNow(_internal),
  });
  const hasRemoteMetadataCandidates = descriptors.some(
    (descriptor) => descriptor.title !== undefined
      || descriptor.alt !== undefined
      || descriptor.caption !== undefined,
  );
  if (syncRemoteMetadata !== false && syncRemoteMetadata !== true) {
    throw new Error('syncRemoteMetadata must be a boolean');
  }
  if (syncRemoteMetadata && hasRemoteMetadataCandidates && metadataAuthorizationConfirmed !== true) {
    throw new Error('metadataAuthorizationConfirmed=true is required to write AllinCMS title/alt/caption');
  }
  if (syncRemoteMetadata) {
    for (const descriptor of descriptors) {
      if (descriptor.title !== undefined) {
        normalizeAllinCmsMediaText(descriptor.title, 'title', 100, { required: true });
      }
      if (descriptor.alt !== undefined) normalizeAllinCmsMediaText(descriptor.alt, 'alt', 200);
      if (descriptor.caption !== undefined) normalizeAllinCmsMediaText(descriptor.caption, 'caption', 500);
    }
  }
  const uploadOne = _internal.uploadOne || uploadAllinCmsMediaDirect;
  const reconcileOne = _internal.reconcileOne || reconcileAllinCmsMediaDirect;
  const updateMetadataOne = _internal.updateMetadataOne || updateAllinCmsMediaMetadataDirect;
  const acquireLock = _internal.acquireLock || acquireAllinCmsImageIndexLock;
  const readIndex = _internal.readIndex || readAllinCmsImageIndex;
  const persistRecord = _internal.persistRecord || persistIndexRecord;
  const delay = _internal.delay || ((milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)));
  const releaseLock = await acquireLock(imageIndexPath);
  const items = [];
  const progressWarnings = [];
  const cleanup = { imageIndexLockReleased: null, error: null };
  let index;

  const emitProgress = async (event) => {
    if (progressMode !== 'visible' || !onProgress) return;
    try {
      await onProgress(event);
    } catch (error) {
      progressWarnings.push(`progress callback: ${error.message}`);
    }
  };

  try {
    index = await readIndex({ imageIndexPath, expectedSiteKey });
    for (let offset = 0; offset < descriptors.length; offset += 1) {
      const descriptor = descriptors[offset];
      const position = offset + 1;
      const prepared = authorizationFiles[offset];
      let existing = index.records[prepared.sha256] || null;

      await emitProgress({ stage: 'checking', position, total: descriptors.length, filename: prepared.filename });
      if (verifiedIndexRecord(existing)) {
        if (hasNewLocalMetadata(descriptor)) {
          existing = await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: 'local_metadata_updated',
            patch: {
              status: existing.status,
              ...localMetadataPatch(descriptor, existing),
            },
          });
        }
        let metadataResult = null;
        const shouldSyncExistingRemoteMetadata = syncRemoteMetadata
          && (descriptor.title !== undefined
            || descriptor.alt !== undefined
            || descriptor.caption !== undefined);
        if (shouldSyncExistingRemoteMetadata) {
          await emitProgress({ stage: 'metadata_updating', position, total: descriptors.length, filename: prepared.filename });
          try {
            metadataResult = await updateMetadataOne({
              tab,
              expectedSiteKey,
              mediaId: existing.media_id,
              expectedUrl: existing.url,
              expectedCurrentTitle: existing.title,
              title: descriptor.title ?? existing.title,
              alt: descriptor.alt ?? existing.allincms_metadata_observed?.alt ?? existing.alt ?? '',
              caption: descriptor.caption ?? existing.allincms_metadata_observed?.caption ?? existing.caption ?? '',
              authorizationConfirmed: true,
              timeoutMs,
            });
            existing = await persistRecord({
              imageIndexPath,
              index,
              sourceSha256: prepared.sha256,
              stage: 'metadata_verified',
              patch: {
                status: existing.status,
                title: metadataResult.observedAfter?.title || descriptor.title || existing.title,
                metadata_sync_status: 'metadata_verified',
                metadata_verified_at: isoNow(),
                allincms_metadata_observed: {
                  title: metadataResult.observedAfter?.title || descriptor.title || existing.title,
                  alt: metadataResult.observedAfter?.alt ?? '',
                  caption: metadataResult.observedAfter?.caption ?? '',
                  sync_status: 'metadata_verified',
                },
              },
            });
          } catch (error) {
            const requestMayHaveSucceeded = error?.result?.requestMayHaveSucceeded === true;
            existing = await persistRecord({
              imageIndexPath,
              index,
              sourceSha256: prepared.sha256,
              stage: requestMayHaveSucceeded ? 'metadata_update_ambiguous' : 'metadata_update_failed_before_request',
              patch: {
                status: existing.status,
                metadata_sync_status: requestMayHaveSucceeded
                  ? 'metadata_update_ambiguous'
                  : 'metadata_update_failed_before_request',
                metadata_last_error: error.message,
                metadata_automatic_retry_allowed: false,
              },
            });
            const stopped = {
              status: requestMayHaveSucceeded
                ? 'stopped_metadata_ambiguous'
                : 'stopped_metadata_before_request',
              uploadVerified: true,
              automaticRetryAllowed: false,
              reuploadAllowed: false,
              sourceSha256: prepared.sha256,
              mapping: existing,
              metadataResult: error.result || null,
              error: error.message,
            };
            items.push(stopped);
            await emitProgress({ stage: 'stopped', position, total: descriptors.length, filename: prepared.filename, result: stopped });
            return {
              status: stopped.status,
              automaticRetryAllowed: false,
              completed: items.length - 1,
              uploaded: 0,
              requested: descriptors.length,
              imageIndexPath,
              items,
              progressWarnings,
              cleanup,
            };
          }
        }
        const reused = {
          status: metadataResult ? 'reused_mapping_metadata_verified' : 'reused_verified_mapping',
          sourceSha256: prepared.sha256,
          mapping: existing,
          metadataResult,
        };
        items.push(reused);
        await emitProgress({
          stage: metadataResult ? 'metadata_verified' : 'reused',
          position,
          total: descriptors.length,
          filename: prepared.filename,
          result: reused,
        });
        continue;
      }

      if (existing && ['prepared', 'prepared_title_collision', 'request_started', 'upload_result_ambiguous'].includes(existing.status)) {
        const reconciliation = await reconcileOne({
          tab,
          expectedSiteKey,
          expectedTitle: existing.title || prepared.title,
          controlledReload: true,
          timeoutMs,
        });
        const requestWasNotStarted = ['prepared', 'prepared_title_collision'].includes(existing.status);
        if (requestWasNotStarted && reconciliation.status !== 'not_found_stop') {
          const titleCollision = reconciliation.status === 'reconciled_existing'
            || reconciliation.status === 'ambiguous_multiple_matches';
          const stopped = {
            status: titleCollision ? 'stopped_preexisting_title_collision' : 'stopped_reconciliation_failed_before_request',
            automaticRetryAllowed: false,
            requestSent: false,
            sourceSha256: prepared.sha256,
            reconciliation,
          };
          items.push(stopped);
          await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: titleCollision ? 'prepared_title_collision' : 'prepared',
            patch: {
              ...existing,
              status: titleCollision ? 'prepared_title_collision' : 'prepared',
              last_reconciliation: reconciliation,
            },
          });
          return {
            status: stopped.status,
            automaticRetryAllowed: false,
            completed: items.length - 1,
            requested: descriptors.length,
            items,
            progressWarnings,
            cleanup,
          };
        }
        if (!requestWasNotStarted && reconciliation.status === 'reconciled_existing') {
          const mapping = await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: 'reconciled_existing',
            patch: mappingPatch({
              prepared,
              descriptor,
              result: reconciliation,
              status: 'reconciled_existing',
              existingRecord: existing,
            }),
          });
          const reconciled = { status: 'reconciled_existing', sourceSha256: prepared.sha256, mapping };
          items.push(reconciled);
          await emitProgress({ stage: 'reconciled', position, total: descriptors.length, filename: prepared.filename, result: reconciled });
          continue;
        }
        if (!requestWasNotStarted) {
          const stopped = {
            status: 'stopped_ambiguous',
            automaticRetryAllowed: false,
            sourceSha256: prepared.sha256,
            reconciliation,
          };
          items.push(stopped);
          await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: 'upload_result_ambiguous',
            patch: { ...existing, status: 'upload_result_ambiguous', last_reconciliation: reconciliation },
          });
          return {
            status: 'stopped_ambiguous',
            automaticRetryAllowed: false,
            completed: items.length - 1,
            requested: descriptors.length,
            items,
            progressWarnings,
            cleanup,
          };
        }
      }

      await persistRecord({
        imageIndexPath,
        index,
        sourceSha256: prepared.sha256,
        stage: 'prepared',
        patch: {
          status: 'prepared',
          source_file_name: prepared.filename,
          source_file_path: prepared.localFile,
          source_md5: prepared.md5,
          title: prepared.title,
          ...localMetadataPatch(descriptor),
        },
      });
      await emitProgress({ stage: 'prepared', position, total: descriptors.length, filename: prepared.filename });

      let uploadResult = null;
      let uploadResolution = null;
      let uploadAttempts = 0;
      let lastUploadError = null;

      while (uploadAttempts < maxAttemptsPerImage) {
        uploadAttempts += 1;
        let requestStartedThisAttempt = false;
        try {
          uploadResult = await uploadOne({
            tab,
            localFile: prepared.localFile,
            expectedSiteKey,
            timeoutMs,
            authorizationContext: delegatedMediaUploadAuthorization(
              authorizationContext,
              'direct',
              [prepared],
            ),
            _internal: {
              preparedInput: prepared,
              ...(typeof _internal.now === 'function' ? { now: _internal.now } : {}),
            },
            beforeRequest: async (requestState) => {
              try {
                await persistRecord({
                  imageIndexPath,
                  index,
                  sourceSha256: prepared.sha256,
                  stage: 'request_started',
                  patch: {
                    status: 'request_started',
                    upload_attempt: uploadAttempts,
                    normalized_upload_sha256: requestState.normalized.sha256,
                    normalized_upload_md5: requestState.normalized.md5,
                  },
                });
              } catch (error) {
                error.code = error.code || 'ALLINCMS_INDEX_BEFORE_REQUEST_FAILED';
                throw error;
              }
              requestStartedThisAttempt = true;
              await emitProgress({
                stage: 'uploading',
                position,
                total: descriptors.length,
                filename: prepared.filename,
                attempt: uploadAttempts,
                maxAttempts: maxAttemptsPerImage,
              });
            },
          });
          uploadResolution = 'uploaded';
          break;
        } catch (error) {
          lastUploadError = error;
          existing = index.records[prepared.sha256] || null;

          if (error?.code === 'ALLINCMS_INDEX_BEFORE_REQUEST_FAILED') {
            const stopped = {
              status: 'stopped_index_write_failed',
              automaticRetryAllowed: false,
              requestSent: false,
              sourceSha256: prepared.sha256,
              attempts: uploadAttempts,
              error: error.message,
            };
            items.push(stopped);
            await emitProgress({ stage: 'stopped', position, total: descriptors.length, filename: prepared.filename, result: stopped });
            return {
              status: stopped.status,
              automaticRetryAllowed: false,
              completed: items.length - 1,
              requested: descriptors.length,
              imageIndexPath,
              items,
              progressWarnings,
              cleanup,
            };
          }

          const requestMayHaveSucceeded = error?.result?.requestMayHaveSucceeded === true
            || requestStartedThisAttempt
            || existing?.status === 'request_started';
          await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: requestMayHaveSucceeded ? 'upload_error_pending_reconciliation' : 'upload_error_before_request',
            patch: {
              status: requestMayHaveSucceeded ? 'upload_error_pending_reconciliation' : 'upload_error_before_request',
              upload_attempt: uploadAttempts,
              last_error: error.message,
              request_may_have_succeeded: requestMayHaveSucceeded,
              automatic_retry_allowed: false,
            },
          });

          const retryDelayMs = retryDelaysMs[Math.min(uploadAttempts - 1, retryDelaysMs.length - 1)];
          await emitProgress({
            stage: 'upload_error_waiting',
            position,
            total: descriptors.length,
            filename: prepared.filename,
            attempt: uploadAttempts,
            maxAttempts: maxAttemptsPerImage,
            delayMs: retryDelayMs,
            error: error.message,
          });
          if (retryDelayMs > 0) await delay(retryDelayMs);

          let reconciliation;
          try {
            reconciliation = await reconcileOne({
              tab,
              expectedSiteKey,
              expectedTitle: prepared.title,
              controlledReload: true,
              timeoutMs,
            });
          } catch (reconciliationError) {
            reconciliation = {
              status: 'reconciliation_error',
              requestSent: false,
              automaticRetryAllowed: false,
              error: reconciliationError.message,
            };
          }

          await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: 'upload_error_reconciled',
            patch: {
              status: reconciliation.status === 'reconciled_existing'
                ? 'reconciled_existing'
                : reconciliation.status === 'not_found_stop'
                  ? 'upload_absence_confirmed'
                  : 'upload_result_ambiguous',
              upload_attempt: uploadAttempts,
              last_reconciliation: reconciliation,
              automatic_retry_allowed: reconciliation.status === 'not_found_stop'
                && uploadAttempts < maxAttemptsPerImage,
            },
          });

          if (reconciliation.status === 'reconciled_existing') {
            uploadResult = reconciliation;
            uploadResolution = 'reconciled';
            break;
          }

          if (reconciliation.status !== 'not_found_stop') {
            const stopped = {
              status: 'stopped_ambiguous',
              automaticRetryAllowed: false,
              sourceSha256: prepared.sha256,
              attempts: uploadAttempts,
              uploadResult: error.result || null,
              reconciliation,
            };
            items.push(stopped);
            await emitProgress({ stage: 'stopped', position, total: descriptors.length, filename: prepared.filename, result: stopped });
            return {
              status: stopped.status,
              automaticRetryAllowed: false,
              completed: items.length - 1,
              requested: descriptors.length,
              imageIndexPath,
              items,
              progressWarnings,
              cleanup,
            };
          }

          if (uploadAttempts >= maxAttemptsPerImage) {
            const stopped = {
              status: 'stopped_retry_exhausted',
              automaticRetryAllowed: false,
              exactAbsenceConfirmed: true,
              sourceSha256: prepared.sha256,
              attempts: uploadAttempts,
              lastError: error.message,
              reconciliation,
            };
            items.push(stopped);
            await emitProgress({ stage: 'stopped', position, total: descriptors.length, filename: prepared.filename, result: stopped });
            return {
              status: stopped.status,
              automaticRetryAllowed: false,
              completed: items.length - 1,
              requested: descriptors.length,
              imageIndexPath,
              items,
              progressWarnings,
              cleanup,
            };
          }

          await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: 'upload_retry_scheduled',
            patch: {
              status: 'upload_retry_scheduled',
              previous_upload_attempt: uploadAttempts,
              next_upload_attempt: uploadAttempts + 1,
              last_error: error.message,
              exact_remote_absence_confirmed: true,
              automatic_retry_allowed: true,
            },
          });
          await emitProgress({
            stage: 'retrying_upload',
            position,
            total: descriptors.length,
            filename: prepared.filename,
            attempt: uploadAttempts + 1,
            maxAttempts: maxAttemptsPerImage,
          });
        }
      }

      if (!uploadResult || !uploadResolution) {
        const stopped = {
          status: 'stopped_retry_exhausted',
          automaticRetryAllowed: false,
          sourceSha256: prepared.sha256,
          attempts: uploadAttempts,
          lastError: lastUploadError?.message || 'Upload attempts ended without a verified result',
        };
        items.push(stopped);
        return {
          status: stopped.status,
          automaticRetryAllowed: false,
          completed: items.length - 1,
          requested: descriptors.length,
          imageIndexPath,
          items,
          progressWarnings,
          cleanup,
        };
      }

      let mapping;
      try {
        mapping = await persistRecord({
          imageIndexPath,
          index,
          sourceSha256: prepared.sha256,
          stage: uploadResolution === 'reconciled' ? 'reconciled_existing' : 'verified',
          patch: mappingPatch({
            prepared,
            descriptor,
            result: uploadResult,
            status: uploadResolution === 'reconciled' ? 'reconciled_existing' : 'verified',
            existingRecord: index.records[prepared.sha256] || existing,
          }),
        });
      } catch (error) {
        const stopped = {
          status: 'stopped_index_write_failed',
          automaticRetryAllowed: false,
          reconciliationRequired: true,
          sourceSha256: prepared.sha256,
          attempts: uploadAttempts,
          uploadResult,
          error: error.message,
        };
        items.push(stopped);
        await emitProgress({ stage: 'stopped', position, total: descriptors.length, filename: prepared.filename, result: stopped });
        return {
          status: stopped.status,
          automaticRetryAllowed: false,
          completed: items.length - 1,
          requested: descriptors.length,
          imageIndexPath,
          items,
          progressWarnings,
          cleanup,
        };
      }

      let metadataResult = null;
      const shouldSyncRemoteMetadata = syncRemoteMetadata
        && (descriptor.title !== undefined
          || descriptor.alt !== undefined
          || descriptor.caption !== undefined);
      if (shouldSyncRemoteMetadata) {
        await emitProgress({ stage: 'metadata_updating', position, total: descriptors.length, filename: prepared.filename });
        try {
          metadataResult = await updateMetadataOne({
            tab,
            expectedSiteKey,
            mediaId: mapping.media_id,
            expectedUrl: mapping.url,
            expectedCurrentTitle: mapping.title,
            title: descriptor.title ?? mapping.title,
            alt: descriptor.alt ?? mapping.allincms_metadata_observed?.alt ?? '',
            caption: descriptor.caption ?? mapping.allincms_metadata_observed?.caption ?? '',
            authorizationConfirmed: true,
            timeoutMs,
          });
          mapping = await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: 'metadata_verified',
            patch: {
              status: uploadResolution === 'reconciled' ? 'reconciled_existing' : 'verified',
              title: metadataResult.observedAfter?.title || descriptor.title || mapping.title,
              metadata_sync_status: 'metadata_verified',
              metadata_verified_at: isoNow(),
              allincms_metadata_observed: {
                title: metadataResult.observedAfter?.title || mapping.title,
                alt: metadataResult.observedAfter?.alt ?? '',
                caption: metadataResult.observedAfter?.caption ?? '',
                sync_status: 'metadata_verified',
              },
            },
          });
        } catch (error) {
          const requestMayHaveSucceeded = error?.result?.requestMayHaveSucceeded === true;
          mapping = await persistRecord({
            imageIndexPath,
            index,
            sourceSha256: prepared.sha256,
            stage: requestMayHaveSucceeded ? 'metadata_update_ambiguous' : 'metadata_update_failed_before_request',
            patch: {
              status: uploadResolution === 'reconciled' ? 'reconciled_existing' : 'verified',
              metadata_sync_status: requestMayHaveSucceeded
                ? 'metadata_update_ambiguous'
                : 'metadata_update_failed_before_request',
              metadata_last_error: error.message,
              metadata_automatic_retry_allowed: false,
            },
          });
          const stopped = {
            status: requestMayHaveSucceeded
              ? 'stopped_metadata_ambiguous'
              : 'stopped_metadata_before_request',
            uploadVerified: true,
            automaticRetryAllowed: false,
            reuploadAllowed: false,
            sourceSha256: prepared.sha256,
            attempts: uploadAttempts,
            mapping,
            metadataResult: error.result || null,
            error: error.message,
          };
          items.push(stopped);
          await emitProgress({ stage: 'stopped', position, total: descriptors.length, filename: prepared.filename, result: stopped });
          return {
            status: stopped.status,
            automaticRetryAllowed: false,
            completed: items.length - 1,
            uploaded: items.length,
            requested: descriptors.length,
            imageIndexPath,
            items,
            progressWarnings,
            cleanup,
          };
        }
      }

      const completed = {
        status: uploadResolution === 'reconciled'
          ? metadataResult
            ? 'reconciled_metadata_verified_and_indexed'
            : 'reconciled_and_indexed'
          : metadataResult
            ? 'uploaded_metadata_verified_and_indexed'
            : 'uploaded_and_indexed',
        sourceSha256: prepared.sha256,
        attempts: uploadAttempts,
        mapping,
        metadataResult,
      };
      items.push(completed);
      await emitProgress({
        stage: metadataResult
          ? 'metadata_verified'
          : uploadResolution === 'reconciled'
            ? 'reconciled'
            : 'verified',
        position,
        total: descriptors.length,
        filename: prepared.filename,
        result: completed,
      });
    }
    return {
      status: 'completed',
      requested: descriptors.length,
      completed: items.length,
      automaticRetryAllowed: false,
      imageIndexPath,
      items,
      progressWarnings,
      cleanup,
    };
  } catch (error) {
    return {
      status: 'stopped_index_or_runtime_error',
      automaticRetryAllowed: false,
      completed: items.length,
      requested: descriptors.length,
      imageIndexPath,
      items,
      error: error.message,
      code: error.code || null,
      progressWarnings,
      cleanup,
    };
  } finally {
    try {
      await releaseLock();
      cleanup.imageIndexLockReleased = true;
    } catch (error) {
      cleanup.imageIndexLockReleased = false;
      cleanup.error = error.message;
      progressWarnings.push(`image index lock cleanup failed: ${error.message}; inspect the private runtime lock before the next run`);
    }
  }
}

export async function deleteAllinCmsMediaDirect({
  tab,
  expectedSiteKey,
  mediaId,
  expectedTitle,
  expectedUrl,
  authorizationConfirmed = false,
  timeoutMs = 30_000,
}) {
  if (authorizationConfirmed !== true) {
    throw new Error('Explicit current-user authorization is required for this exact media-record delete');
  }
  if (!tab?.playwright || !tab?.capabilities) {
    throw new Error('A claimed Browser tab with Playwright and CDP capabilities is required');
  }
  if (!/^[0-9a-f]{24}$/i.test(String(mediaId || ''))) {
    throw new Error('A 24-character AllinCMS mediaId is required');
  }
  if (!expectedTitle || typeof expectedTitle !== 'string') {
    throw new Error('expectedTitle is required for fail-closed deletion');
  }
  const expectedAsset = new URL(expectedUrl);
  if (expectedAsset.protocol !== 'https:' || expectedAsset.origin !== ASSET_ORIGIN) {
    throw new Error(`Unexpected AllinCMS asset origin: ${expectedAsset.origin}`);
  }
  if (!expectedAsset.pathname.startsWith(`/${expectedSiteKey}/`)) {
    throw new Error('expectedUrl does not belong to the confirmed site key');
  }

  const currentUrl = new URL(await tab.url());
  if (currentUrl.origin !== WORKSPACE_ORIGIN
      || currentUrl.pathname !== `/${expectedSiteKey}/media`) {
    throw new Error(`Open the confirmed media page first; current URL is ${currentUrl.href}`);
  }

  const existingCount = await countMediaCardsByTitle(tab, expectedTitle);
  if (existingCount !== 1) {
    throw new Error(`Expected one media card titled ${JSON.stringify(expectedTitle)}; observed ${existingCount}`);
  }
  const card = await waitForMediaCard(tab, expectedTitle, timeoutMs);
  if (card.url !== expectedAsset.href) {
    throw new Error('The unique media card URL does not match expectedUrl');
  }
  const record = await readMediaRecordFromRsc(tab, card.url);
  if (!record) throw new Error('The exact RSC media record is missing');
  if (record.mediaId !== mediaId) throw new Error('The exact RSC media ID does not match mediaId');
  if (record.url !== expectedAsset.href) throw new Error('The exact RSC media URL does not match expectedUrl');
  if (record.title !== expectedTitle && record.name !== expectedTitle) {
    throw new Error('The exact RSC media title/name does not match expectedTitle');
  }

  const cdp = await tab.capabilities.get('cdp');
  await cdp.send('Network.enable', {});
  const contract = await discoverDirectMediaActionContract({
    tab,
    cdp,
    expectedSiteKey,
    actionExportName: 'deleteMediaAction',
    actionLabel: 'deleteMediaAction',
  });
  const cursor = await cdp.readEvents({
    methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
    limit: 1,
    timeoutMs: 1,
  });

  const expression = `(async()=>{
    const response=await window.fetch(location.pathname,{
      method:'POST',
      credentials:'include',
      headers:{
        Accept:'text/x-component',
        'Content-Type':'text/plain;charset=UTF-8',
        'next-action':${JSON.stringify(contract.actionId)},
        'next-router-state-tree':${JSON.stringify(contract.routerTree)},
        'x-deployment-id':${JSON.stringify(contract.deploymentId)}
      },
      body:JSON.stringify([{id:${JSON.stringify(mediaId)},siteId:${JSON.stringify(contract.siteId)}}])
    });
    const text=await response.text();
    return {
      status:response.status,
      ok:response.ok,
      contentType:response.headers.get('content-type'),
      responseBytes:text.length
    };
  })()`;

  let replay = null;
  let replayError = null;
  try {
    replay = runtimeValue(await cdp.send('Runtime.evaluate', {
      expression,
      awaitPromise: true,
      returnByValue: true,
    }, { timeoutMs }));
  } catch (error) {
    replayError = error.message;
  }

  const captured = await cdp.readEvents({
    afterSequence: cursor.cursor,
    methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
    limit: 1000,
    timeoutMs: 1_500,
  });
  const network = summarizeUploadNetwork(captured.events || captured, expectedSiteKey);

  await tab.reload();
  try {
    await tab.playwright.waitForLoadState('domcontentloaded', { timeoutMs: 15_000 });
  } catch {
    // The refreshed media state below is authoritative.
  }

  const errors = [];
  const warnings = [];
  if (replayError) errors.push(`direct replay: ${replayError}`);
  if (replay?.status !== 200) errors.push(`direct replay returned HTTP ${replay?.status ?? 'unknown'}`);
  if (!String(replay?.contentType || '').startsWith('text/x-component')) {
    errors.push(`direct replay returned unexpected Content-Type ${replay?.contentType || '(missing)'}`);
  }
  if (network.actionCount !== 1) {
    errors.push(`expected one direct Server Action request; observed ${network.actionCount}`);
  }
  if (network.action?.responseStatus !== 200) {
    errors.push(`captured Server Action response was ${network.action?.responseStatus ?? 'missing'}`);
  }

  const remainingCardCount = await countMediaCardsByTitle(tab, expectedTitle);
  if (remainingCardCount !== 0) {
    errors.push(`media card still exists after delete; observed ${remainingCardCount}`);
  }
  const remainingRecord = await readMediaRecordFromRsc(tab, expectedAsset.href);
  if (remainingRecord) errors.push('RSC media record still exists after delete');

  const coreVerified = errors.length === 0;
  const result = {
    status: coreVerified
      ? 'media_record_deleted_and_verified'
      : 'direct_delete_verification_failed',
    retryPolicy: 'do_not_retry_automatically_after_delete_request',
    interaction: {
      mode: 'direct_next_server_action_replay',
      uiClicks: 0,
      dialogOpens: 0,
    },
    target: {
      mediaId,
      title: expectedTitle,
      url: expectedAsset.href,
    },
    site: { siteKey: expectedSiteKey },
    replay,
    network,
    contract: {
      actionIdStored: false,
      actionIdLength: contract.actionIdLength,
      actionIdSha256: contract.actionIdSha256,
      deploymentFingerprint: contract.deploymentId,
    },
    verification: {
      oneDirectInterfaceRequest: network.actionCount === 1,
      serverAction200: replay?.status === 200 && network.action?.responseStatus === 200,
      mediaCardRemoved: remainingCardCount === 0,
      mediaRecordRemoved: !remainingRecord,
      completionScope: 'allincms_media_record',
      contractVerified: coreVerified,
    },
    warnings,
    errors,
  };

  if (!coreVerified) {
    const error = new Error('Direct AllinCMS media delete was not fully verified; do not retry automatically');
    error.result = result;
    throw error;
  }
  return result;
}


function normalizeAllinCmsMediaText(value, field, maxLength, { required = false } = {}) {
  if (value === null || value === undefined) {
    if (required) throw new Error(`${field} is required`);
    return '';
  }
  if (typeof value !== 'string') throw new Error(`${field} must be a string`);
  const normalized = value.trim();
  if (required && !normalized) throw new Error(`${field} is required`);
  if ([...normalized].length > maxLength) {
    throw new Error(`${field} exceeds the AllinCMS ${maxLength}-character limit`);
  }
  return normalized;
}

export async function updateAllinCmsMediaMetadataDirect({
  tab,
  expectedSiteKey,
  mediaId,
  expectedUrl,
  expectedCurrentTitle,
  title,
  alt = '',
  caption = '',
  authorizationConfirmed = false,
  timeoutMs = 30_000,
  _internal = {},
}) {
  if (authorizationConfirmed !== true) {
    throw new Error('Explicit current-user authorization is required for this exact media metadata update');
  }
  if (!tab?.playwright || !tab?.capabilities) {
    throw new Error('A claimed Browser tab with Playwright and CDP capabilities is required');
  }
  if (!/^[0-9a-f]{24}$/i.test(String(mediaId || ''))) {
    throw new Error('A 24-character AllinCMS mediaId is required');
  }
  const currentTitle = normalizeAllinCmsMediaText(
    expectedCurrentTitle,
    'expectedCurrentTitle',
    100,
    { required: true },
  );
  const desired = {
    title: normalizeAllinCmsMediaText(title, 'title', 100, { required: true }),
    alt: normalizeAllinCmsMediaText(alt, 'alt', 200),
    caption: normalizeAllinCmsMediaText(caption, 'caption', 500),
  };
  const expectedAsset = new URL(expectedUrl);
  if (expectedAsset.protocol !== 'https:' || expectedAsset.origin !== ASSET_ORIGIN) {
    throw new Error(`Unexpected AllinCMS asset origin: ${expectedAsset.origin}`);
  }
  if (!expectedAsset.pathname.startsWith(`/${expectedSiteKey}/`)) {
    throw new Error('expectedUrl does not belong to the confirmed site key');
  }

  const currentUrl = new URL(await tab.url());
  if (currentUrl.origin !== WORKSPACE_ORIGIN
      || currentUrl.pathname !== `/${expectedSiteKey}/media`) {
    throw new Error(`Open the confirmed media page first; current URL is ${currentUrl.href}`);
  }

  const countCards = _internal.countCards || countMediaCardsByTitle;
  const waitCard = _internal.waitCard || waitForMediaCard;
  const readRecord = _internal.readRecord || readMediaRecordFromRsc;
  const getCdp = _internal.getCdp || ((currentTab) => currentTab.capabilities.get('cdp'));
  const discoverContract = _internal.discoverContract || discoverDirectMediaActionContract;
  const summarizeNetwork = _internal.summarizeNetwork || summarizeUploadNetwork;

  const existingCount = await countCards(tab, currentTitle);
  if (existingCount !== 1) {
    throw new Error(`Expected one media card titled ${JSON.stringify(currentTitle)}; observed ${existingCount}`);
  }
  const card = await waitCard(tab, currentTitle, timeoutMs);
  if (card.url !== expectedAsset.href) {
    throw new Error('The unique media card URL does not match expectedUrl');
  }
  const before = await readRecord(tab, expectedAsset.href);
  if (!before) throw new Error('The exact RSC media record is missing');
  if (before.mediaId !== mediaId) throw new Error('The exact RSC media ID does not match mediaId');
  if (before.url !== expectedAsset.href) throw new Error('The exact RSC media URL does not match expectedUrl');
  if (before.title !== currentTitle && before.name !== currentTitle) {
    throw new Error('The exact RSC media title/name does not match expectedCurrentTitle');
  }
  if (desired.title !== currentTitle) {
    const desiredTitleCount = await countCards(tab, desired.title);
    if (desiredTitleCount !== 0) {
      throw new Error(`Refusing metadata rename because ${desiredTitleCount} media card(s) already use the requested title`);
    }
  }

  const cdp = await getCdp(tab);
  await cdp.send('Network.enable', {});
  const contract = await discoverContract({
    tab,
    cdp,
    expectedSiteKey,
    actionExportName: 'updateMediaAction',
    actionLabel: 'updateMediaAction',
  });
  const cursor = _internal.readCursor
    ? await _internal.readCursor({ cdp })
    : await cdp.readEvents({
      methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
      limit: 1,
      timeoutMs: 1,
    });

  const expression = `(async()=>{
    const response=await window.fetch(location.pathname,{
      method:'POST',
      credentials:'include',
      headers:{
        Accept:'text/x-component',
        'Content-Type':'text/plain;charset=UTF-8',
        'next-action':${JSON.stringify(contract.actionId)},
        'next-router-state-tree':${JSON.stringify(contract.routerTree)},
        'x-deployment-id':${JSON.stringify(contract.deploymentId)}
      },
      body:JSON.stringify([{
        id:${JSON.stringify(mediaId)},
        siteId:${JSON.stringify(contract.siteId)},
        title:${JSON.stringify(desired.title)},
        alt:${JSON.stringify(desired.alt)},
        caption:${JSON.stringify(desired.caption)}
      }])
    });
    const text=await response.text();
    return {
      status:response.status,
      ok:response.ok,
      contentType:response.headers.get('content-type'),
      responseBytes:text.length
    };
  })()`;

  let replay = null;
  let replayError = null;
  try {
    replay = _internal.sendReplay
      ? await _internal.sendReplay({ cdp, expression, timeoutMs })
      : runtimeValue(await cdp.send('Runtime.evaluate', {
        expression,
        awaitPromise: true,
        returnByValue: true,
      }, { timeoutMs }));
  } catch (error) {
    replayError = error.message;
  }

  let network = null;
  let capturedError = null;
  try {
    const captured = _internal.readCaptured
      ? await _internal.readCaptured({ cdp, cursor })
      : await cdp.readEvents({
        afterSequence: cursor.cursor,
        methods: ['Network.requestWillBeSent', 'Network.responseReceived'],
        limit: 1000,
        timeoutMs: 1_500,
      });
    network = summarizeNetwork(captured.events || captured, expectedSiteKey);
  } catch (error) {
    capturedError = error.message;
  }

  const verificationDelaysMs = _internal.verificationDelaysMs || [0, 750, 2_000];
  if (!Array.isArray(verificationDelaysMs) || verificationDelaysMs.length < 1
      || verificationDelaysMs.some((value) => !Number.isInteger(value) || value < 0)) {
    throw new Error('verificationDelaysMs must be a non-empty array of non-negative integers');
  }
  const sleep = _internal.sleep || ((delayMs) => new Promise((resolve) => setTimeout(resolve, delayMs)));
  const reloadPage = _internal.reloadPage || (async ({ tab: currentTab }) => {
    await currentTab.reload();
    try {
      await currentTab.playwright.waitForLoadState({ state: 'domcontentloaded', timeoutMs: 15_000 });
    } catch {
      // The refreshed RSC media record below is authoritative.
    }
  });
  const observations = [];
  let reloadError = null;
  let after = null;
  let titleCardCount = null;
  let previousTitleCardCount = null;

  for (let attempt = 0; attempt < verificationDelaysMs.length; attempt += 1) {
    if (verificationDelaysMs[attempt] > 0) await sleep(verificationDelaysMs[attempt]);
    try {
      await reloadPage({ tab, timeoutMs });
      const observed = await readRecord(tab, expectedAsset.href);
      const observedTitleCardCount = await countCards(tab, desired.title);
      const observedPreviousTitleCardCount = desired.title === currentTitle
        ? null
        : await countCards(tab, currentTitle);
      observations.push({
        attempt: attempt + 1,
        delayMs: verificationDelaysMs[attempt],
        record: observed ? {
          title: observed.title || observed.name || null,
          alt: observed.alt ?? null,
          caption: observed.caption ?? null,
          mediaId: observed.mediaId,
          url: observed.url,
        } : null,
        titleCardCount: observedTitleCardCount,
        previousTitleCardCount: observedPreviousTitleCardCount,
      });
      after = observed;
      titleCardCount = observedTitleCardCount;
      previousTitleCardCount = observedPreviousTitleCardCount;
      reloadError = null;
      const metadataMatches = Boolean(observed)
        && observed.mediaId === mediaId
        && observed.url === expectedAsset.href
        && (observed.title === desired.title || observed.name === desired.title)
        && (observed.alt ?? '') === desired.alt
        && (observed.caption ?? '') === desired.caption
        && observedTitleCardCount === 1
        && (observedPreviousTitleCardCount === null || observedPreviousTitleCardCount === 0);
      if (metadataMatches) break;
    } catch (error) {
      reloadError = error.message;
      observations.push({
        attempt: attempt + 1,
        delayMs: verificationDelaysMs[attempt],
        error: error.message,
      });
    }
  }
  const errors = [];
  if (replayError) errors.push(`direct replay: ${replayError}`);
  if (capturedError) errors.push(`network capture: ${capturedError}`);
  if (reloadError) errors.push(`reload: ${reloadError}`);
  if (replay?.status !== 200) errors.push(`direct replay returned HTTP ${replay?.status ?? 'unknown'}`);
  if (!String(replay?.contentType || '').startsWith('text/x-component')) {
    errors.push(`direct replay returned unexpected Content-Type ${replay?.contentType || '(missing)'}`);
  }
  if (network?.actionCount !== 1) {
    errors.push(`expected one direct Server Action request; observed ${network?.actionCount ?? 'unknown'}`);
  }
  if (network?.action?.responseStatus !== 200) {
    errors.push(`captured Server Action response was ${network?.action?.responseStatus ?? 'missing'}`);
  }
  if (!after) errors.push('RSC media record is missing after metadata update');
  if (after?.mediaId !== mediaId) errors.push('media ID changed or no longer matches after metadata update');
  if (after?.url !== expectedAsset.href) errors.push('media URL changed or no longer matches after metadata update');
  if (after?.title !== desired.title && after?.name !== desired.title) {
    errors.push('RSC title/name does not match the requested title after metadata update');
  }
  if ((after?.alt ?? '') !== desired.alt) errors.push('RSC alt does not match the requested alt');
  if ((after?.caption ?? '') !== desired.caption) errors.push('RSC caption does not match the requested caption');
  if (titleCardCount !== 1) errors.push(`expected one updated media card; observed ${titleCardCount ?? 'unknown'}`);
  if (previousTitleCardCount !== null && previousTitleCardCount !== 0) {
    errors.push(`the previous media title still appears on ${previousTitleCardCount} card(s)`);
  }

  const verified = errors.length === 0;
  const result = {
    status: verified ? 'metadata_updated_and_verified' : 'metadata_update_ambiguous',
    requestMayHaveSucceeded: true,
    automaticRetryAllowed: false,
    retryPolicy: 'do_not_retry_automatically_after_metadata_request',
    interaction: {
      mode: 'direct_next_server_action_replay',
      uiClicks: 0,
      dialogOpens: 0,
      uploadRequests: 0,
    },
    target: {
      mediaId,
      url: expectedAsset.href,
      previousTitle: currentTitle,
    },
    requestedMetadata: desired,
    observedBefore: {
      title: before.title || before.name || null,
      alt: before.alt ?? null,
      caption: before.caption ?? null,
    },
    observedAfter: after ? {
      title: after.title || after.name || null,
      alt: after.alt ?? null,
      caption: after.caption ?? null,
      mediaId: after.mediaId,
      url: after.url,
    } : null,
    site: { siteKey: expectedSiteKey },
    replay,
    network,
    contract: {
      actionIdStored: false,
      actionIdLength: contract.actionIdLength,
      actionIdSha256: contract.actionIdSha256,
      deploymentFingerprint: contract.deploymentId,
    },
    verification: {
      oneDirectInterfaceRequest: network?.actionCount === 1,
      serverAction200: replay?.status === 200 && network?.action?.responseStatus === 200,
      readOnlyVerificationAttempts: observations.length,
      readOnlyVerificationObservations: observations,
      metadataMatchesAfterReload: Boolean(after)
        && (after.title === desired.title || after.name === desired.title)
        && (after.alt ?? '') === desired.alt
        && (after.caption ?? '') === desired.caption,
      mediaIdentityUnchanged: after?.mediaId === mediaId && after?.url === expectedAsset.href,
      oneUpdatedCard: titleCardCount === 1,
      contractVerified: verified,
    },
    errors,
  };

  if (!verified) {
    const error = new Error('Direct AllinCMS media metadata update was not fully verified; do not retry automatically');
    error.result = result;
    throw error;
  }
  return result;
}

export async function openAllinCmsMedia({
  tab,
  siteDisplayName,
  expectedSiteKey,
  timeoutMs = 20_000,
}) {
  if (!tab?.playwright) throw new Error('A claimed Browser tab is required');
  if (!siteDisplayName || !expectedSiteKey) {
    throw new Error('siteDisplayName and expectedSiteKey are required');
  }

  const currentUrl = new URL(await tab.url());
  if (currentUrl.origin !== WORKSPACE_ORIGIN) {
    throw new Error(`Unexpected origin: ${currentUrl.origin}`);
  }

  if (currentUrl.pathname === '/sites') {
    const siteName = tab.playwright.getByText(siteDisplayName, { exact: true });
    if (await siteName.count() !== 1) {
      throw new Error(`Expected one site named ${siteDisplayName}`);
    }
    const card = siteName.locator('xpath=ancestor::div[@data-slot="card"]');
    const cardText = await card.innerText();
    if (!cardText.includes(expectedSiteKey)) {
      throw new Error(`Site card does not contain expected site key ${expectedSiteKey}`);
    }
    const enter = await uniqueRole(card, 'button', ['进入后台', 'Enter admin']);
    await enter.click();
    await waitForPath(
      tab,
      (url) => url.origin === WORKSPACE_ORIGIN && url.pathname.startsWith(`/${expectedSiteKey}`),
      `site ${expectedSiteKey} admin`,
      timeoutMs,
    );
  }

  const afterEntry = new URL(await tab.url());
  if (!afterEntry.pathname.startsWith(`/${expectedSiteKey}`)) {
    throw new Error(`Wrong site selected; current path is ${afterEntry.pathname}`);
  }
  if (afterEntry.pathname !== `/${expectedSiteKey}/media`) {
    const media = await uniqueRole(tab.playwright, 'link', ['媒体', 'Media']);
    const href = await media.getAttribute('href');
    if (href !== `/${expectedSiteKey}/media`) {
      throw new Error(`Unexpected media link: ${href}`);
    }
    await media.click();
    await waitForPath(
      tab,
      (url) => url.origin === WORKSPACE_ORIGIN && url.pathname === `/${expectedSiteKey}/media`,
      `media page for ${expectedSiteKey}`,
      timeoutMs,
    );
  }

  return { siteKey: expectedSiteKey, url: await tab.url() };
}

export async function uploadAllinCmsMediaBatch({
  tab,
  localFiles,
  expectedSiteKey,
  authorizationContext,
  maxFiles = VERIFIED_MAX_FILES,
  timeoutMs = 30_000,
  _internal = {},
}) {
  validateAuthorizationContextShape(authorizationContext, {
    expectedSiteKey,
    entrypoint: 'batch',
    now: authorizationNow(_internal),
  });
  if (!tab?.playwright || !tab?.capabilities) {
    throw new Error('A claimed Browser tab with Playwright and CDP capabilities is required');
  }
  const prepared = _internal.preparedFiles || await prepareLocalFiles(localFiles, maxFiles, _internal);
  if (!Array.isArray(prepared) || prepared.length < 1 || prepared.length > maxFiles) {
    throw new Error(`Prepared media snapshot count must be between 1 and ${maxFiles}`);
  }
  prepared.forEach(assertPreparedFileSnapshot);
  validateMediaUploadAuthorization({
    authorizationContext,
    expectedSiteKey,
    entrypoint: 'batch',
    files: prepared,
    now: authorizationNow(_internal),
  });

  const currentUrl = new URL(await tab.url());
  if (currentUrl.origin !== WORKSPACE_ORIGIN
      || currentUrl.pathname !== `/${expectedSiteKey}/media`) {
    throw new Error(`Open the confirmed media page first; current URL is ${currentUrl.href}`);
  }

  // Existing same-title cards make post-upload attribution ambiguous. Stop before
  // mutation and let the caller rename or explicitly design a separate reuse flow.
  for (const item of prepared) {
    const existing = await countMediaCardsByTitle(tab, item.title);
    if (existing > 0) {
      throw new Error(`A media card already uses title ${JSON.stringify(item.title)}; rename or reuse it explicitly`);
    }
  }

  const cdp = await tab.capabilities.get('cdp');
  await cdp.send('Network.enable', {});
  const marker = await cdp.readEvents({ limit: 1 });
  const cursor = marker.cursor;

  prepared.forEach(assertPreparedFileSnapshot);
  validateMediaUploadAuthorization({
    authorizationContext,
    expectedSiteKey,
    entrypoint: 'batch',
    files: prepared,
    now: authorizationNow(_internal),
  });
  const browserPayloads = prepared.map(browserFilePayload);

  const upload = await uniqueRole(tab.playwright, 'button', ['上传', 'Upload']);
  await upload.click();
  const choose = await uniqueRole(tab.playwright, 'button', ['Choose File', '选择文件']);
  const chooserPromise = tab.playwright.waitForEvent('filechooser', { timeout: timeoutMs });
  await choose.click();
  const chooser = await chooserPromise;
  await chooser.setFiles(browserPayloads);

  const count = prepared.length;
  const confirm = await uniqueRole(tab.playwright, 'button', [
    `上传 (${count})`,
    `Upload (${count})`,
  ]);
  if (_internal.beforeConfirm) {
    await _internal.beforeConfirm({
      files: prepared.map(({ filename, bytes, sha256: digest }) => ({ filename, bytes, sha256: digest })),
      site: { siteKey: expectedSiteKey },
    });
  }

  // The chooser owns byte payload copies, not source paths. Rebind the complete
  // authorization and every copied payload immediately before the confirm click.
  prepared.forEach(assertPreparedFileSnapshot);
  browserPayloads.forEach((payload, index) => assertBrowserFilePayload(prepared[index], payload));
  validateMediaUploadAuthorization({
    authorizationContext,
    expectedSiteKey,
    entrypoint: 'batch',
    files: prepared,
    now: authorizationNow(_internal),
  });
  await confirm.click();

  // After this point a mutation may have happened. Do not automatically retry.
  const initialCards = new Map();
  const initialFailures = [];
  for (const item of prepared) {
    try {
      initialCards.set(item.title, await waitForMediaCard(tab, item.title, timeoutMs));
    } catch (error) {
      initialFailures.push({ title: item.title, stage: 'initial_card', error: error.message });
    }
  }

  const captured = await cdp.readEvents({
    afterSequence: cursor,
    limit: 2000,
    timeoutMs: 1000,
    methods: [
      'Network.requestWillBeSent',
      'Network.responseReceived',
      'Network.loadingFinished',
      'Network.loadingFailed',
    ],
  });
  const network = summarizeUploadNetwork(captured.events || captured, expectedSiteKey);
  const globalFailures = [...initialFailures];
  if (network.actionCount !== 1) {
    globalFailures.push({
      stage: 'network_contract',
      error: `Expected one media Server Action; observed ${network.actionCount}`,
    });
  } else if (network.action?.responseStatus !== 200) {
    globalFailures.push({
      stage: 'network_contract',
      error: `Media Server Action status was ${network.action?.responseStatus ?? 'missing'}, not 200`,
    });
  }

  await tab.reload();
  try {
    await tab.playwright.waitForLoadState('domcontentloaded', { timeout: 15_000 });
  } catch {
    // Refreshed media cards below are the authoritative persistence check.
  }

  const items = [];
  for (const input of prepared) {
    const errors = [];
    let card = null;
    let record = null;
    let image = { ok: false, width: 0, height: 0, src: null };
    let anonymous = { ok: false, anonymousHttpsGet: false };
    try {
      card = await waitForMediaCard(tab, input.title, timeoutMs);
    } catch (error) {
      errors.push(`backend reload: ${error.message}`);
    }
    if (card?.url) {
      record = await readMediaRecordFromRsc(tab, card.url);
      if (!record) {
        errors.push('RSC media record missing or could not be matched to its exact URL');
      } else {
        if (!record.mediaId) errors.push('media ID missing');
        if (record.url !== card.url) errors.push('RSC URL does not match the media card URL');
        if (record.title !== input.title && record.name !== input.title) {
          errors.push('RSC media record title/name does not match the input filename stem');
        }
      }
      image = await verifyImageInBrowser(tab, card.url);
      if (!image.ok) errors.push('media-card image did not decode in the browser');
      try {
        anonymous = await verifyAllinCmsMediaUrl({
          url: card.url,
          expectedSiteKey,
          expectedMimeType: record?.mimeType || undefined,
          timeoutMs,
        });
      } catch (error) {
        errors.push(`anonymous asset verification: ${error.message}`);
      }
    }

    const asset = card?.url
      ? network.assets.find((candidate) => candidate.url === card.url) || null
      : null;
    items.push({
      status: errors.length === 0 ? 'verified' : 'verification_failed',
      input: {
        filename: input.filename,
        bytes: input.bytes,
        extension: input.extension,
        sha256: input.sha256,
      },
      media: record,
      image,
      anonymous,
      verification: {
        mediaCardAppearedBeforeReload: initialCards.has(input.title),
        backendReloadPersists: Boolean(card),
        mediaRecordPresent: Boolean(record),
        mediaIdPresent: Boolean(record?.mediaId),
        recordMatchesExpectedUrl: Boolean(record && card && record.url === card.url),
        recordMatchesExpectedTitle: Boolean(
          record && (record.title === input.title || record.name === input.title),
        ),
        publicAssetRequest200: asset?.responseStatus === 200,
        anonymousHttpsGet: anonymous.ok === true,
        anonymousContentTypeMatches: Boolean(
          anonymous.ok && (!record?.mimeType || anonymous.contentType === record.mimeType),
        ),
        browserImageDecodes: image.ok,
      },
      errors,
    });
  }

  const verifiedCount = items.filter((item) => item.status === 'verified').length;
  const contractVerified = globalFailures.length === 0 && verifiedCount === prepared.length;
  return {
    status: contractVerified
      ? 'uploaded_and_verified'
      : verifiedCount > 0
        ? 'uploaded_with_partial_verification'
        : 'upload_verification_failed',
    retryPolicy: 'do_not_retry_automatically_after_confirm_click',
    site: { siteKey: expectedSiteKey },
    batch: {
      requested: prepared.length,
      verified: verifiedCount,
      failed: prepared.length - verifiedCount,
      oneServerActionObserved: network.actionCount === 1,
    },
    items,
    network,
    globalFailures,
    verification: {
      serverActionCountIsOne: network.actionCount === 1,
      serverAction200: network.actionCount === 1 && network.action?.responseStatus === 200,
      allMediaRecordsPresent: items.every((item) => item.verification.mediaRecordPresent),
      allMediaIdsPresent: items.every((item) => item.verification.mediaIdPresent),
      allBackendReloadPersist: items.every((item) => item.verification.backendReloadPersists),
      allAnonymousHttpsGet: items.every((item) => item.verification.anonymousHttpsGet),
      allAnonymousContentTypesMatch: items.every(
        (item) => item.verification.anonymousContentTypeMatches,
      ),
      allBrowserImagesDecode: items.every((item) => item.verification.browserImageDecodes),
      contractVerified,
    },
  };
}

export async function uploadAllinCmsMedia({
  tab,
  localFile,
  expectedSiteKey,
  authorizationContext,
  timeoutMs = 20_000,
  _internal = {},
}) {
  validateAuthorizationContextShape(authorizationContext, {
    expectedSiteKey,
    entrypoint: 'single',
    now: authorizationNow(_internal),
  });
  const prepared = await prepareLocalFiles([localFile], 1);
  validateMediaUploadAuthorization({
    authorizationContext,
    expectedSiteKey,
    entrypoint: 'single',
    files: prepared,
    now: authorizationNow(_internal),
  });
  const result = await uploadAllinCmsMediaBatch({
    tab,
    localFiles: [localFile],
    expectedSiteKey,
    authorizationContext: delegatedMediaUploadAuthorization(
      authorizationContext,
      'batch',
      prepared,
    ),
    maxFiles: 1,
    timeoutMs,
    _internal: { ..._internal, preparedFiles: prepared },
  });
  if (result.status !== 'uploaded_and_verified') {
    const error = new Error('Single-media upload was not fully verified; do not retry automatically');
    error.result = result;
    throw error;
  }

  const item = result.items[0];
  return {
    status: result.status,
    input: item.input,
    site: result.site,
    media: item.media,
    image: item.image,
    anonymous: item.anonymous,
    network: result.network,
    verification: {
      serverAction200: result.verification.serverAction200,
      mediaRecordPresent: item.verification.mediaRecordPresent,
      publicAssetRequest200: item.verification.publicAssetRequest200,
      anonymousHttpsGet: item.verification.anonymousHttpsGet,
      anonymousContentTypeMatches: item.verification.anonymousContentTypeMatches,
      backendReloadPersists: item.verification.backendReloadPersists,
      browserImageDecodes: item.verification.browserImageDecodes,
    },
  };
}

// ---------------------------------------------------------------------------
// 2026-08-27 deployment wire contract guard + verified dialog driver.
// Observed on dpl 83eddf696484d494d59ae961cb4ded1d61d14b56:
//   the media upload dialog builds `new FormData(); i.append("files", new File(...))`
//   and calls `uploadMedia(siteId, formData)` through the app dispatcher.
// The historical in-page template (`_1_files` + `0` slots) is STALE for this
// deployment and silently produced full-flight responses without a record.
// `assertAllinCmsUploadWireShape` blocks direct entrypoints before a request
// when the discovered chunk text is not the current `files` contract, and
// `uploadAllinCmsUploadViaDialog` drives the app's own dialog (the only
// empirically reliable mutation path on the current deployment) with an
// explicit `uiFallbackApproved` gate.
// ---------------------------------------------------------------------------

export function assertAllinCmsUploadWireShape(scriptTexts, { siteKey, actionLabel = 'uploadMedia' } = {}) {
  if (!Array.isArray(scriptTexts)) throw new Error('scriptTexts must be an array of client chunk texts');
  const joined = scriptTexts.filter((s) => typeof s === 'string').join('\n');
  const hasFilesAppend = /append\(\s*["']files["']/.test(joined);
  const hasActionReference = joined.indexOf(actionLabel) > -1;
  if (!hasActionReference || !hasFilesAppend) {
    throw new Error(`UPLOAD_WIRE_CONTRACT_DRIFT ${siteKey ?? ''}: expected ${actionLabel} reference and FormData field "files" in current client chunks; observed actionReference=${hasActionReference} filesAppend=${hasFilesAppend}. Re-capture the wire contract or use uploadAllinCmsUploadViaDialog with explicit approval.`);
  }
  return { status: 'observed', actionLabel, wireShape: 'files+siteId-formdata' };
}

export async function uploadAllinCmsUploadViaDialog({
  runInTab,
  expectedSiteKey,
  mediaPagePath,
  file,
  uiFallbackApproved = false,
  waitMs = 4000,
  pollTries = 6,
  pollDelayMs = 3000,
  onProgress = () => {},
}) {
  if (uiFallbackApproved !== true) {
    throw new Error('UI fallback upload requires explicit uiFallbackApproved: true for this batch and image');
  }
  if (typeof runInTab !== 'function') throw new Error('runInTab callback is required');
  if (!file || typeof file !== 'object') throw new Error('file entry is required');
  const base64 = Buffer.isBuffer(file.bytes) ? file.bytes.toString('base64') : file.base64;
  if (!base64) throw new Error('file.bytes (Buffer) or file.base64 is required');
  const filename = file.filename || file.name;
  const mimeType = file.mimeType || 'image/webp';
  const path = mediaPagePath || `/${expectedSiteKey}/media`;

  const openAndInject = `(function(){
    var d=document.querySelector('[role=dialog]');
    try{
      var btns=[].slice.call(document.querySelectorAll('button')).filter(function(b){return b.textContent.trim().indexOf(String.fromCharCode(19978,20256))>-1;});
      if(btns.length){btns[0].click();}
    }catch(e){}
    return 'opened';
  })()`;
  await runInTab(openAndInject);
  onProgress({ stage: 'dialog-open', filename });
  await sleep(waitMs);

  const inject = `(function(){
    try{
      var d=document.querySelector('[role=dialog]');
      var inp=d?d.querySelector('input[type=file]'):null;
      if(!inp) return 'NO_INPUT';
      var bytes=Uint8Array.from(atob(${JSON.stringify(base64)}),function(c){return c.charCodeAt(0)});
      var f=new File([bytes],${JSON.stringify(filename)},{type:${JSON.stringify(mimeType)}});
      var dt=new DataTransfer();dt.items.add(f);
      inp.files=dt.files;
      inp.dispatchEvent(new Event('change',{bubbles:true}));
      inp.dispatchEvent(new Event('input',{bubbles:true}));
      return 'INJECTED';
    }catch(e){return 'ERR:'+e.message}
  })()`;
  const injected = await runInTab(inject);
  if (injected !== 'INJECTED') throw new Error(`dialog input injection failed: ${injected}`);
  onProgress({ stage: 'file-injected', filename });
  await sleep(500);
  const submit = `(function(){
    var d=document.querySelector('[role=dialog]');
    if(!d) return 'NO_DIALOG';
    var bs=[].slice.call(d.querySelectorAll('button')).filter(function(b){return /${'\\u4e0a\\u4f20'}/.test(b.textContent);});
    if(!bs.length) return 'NO_SUBMIT';
    bs[bs.length-1].click();
    return 'SUBMITTED';
  })()`;
  const submitted = await runInTab(submit);
  if (submitted !== 'SUBMITTED') throw new Error(`dialog submit failed: ${submitted}`);
  onProgress({ stage: 'submitted', filename });

  const lookFor = filename.replace(/\.[^.]+$/, '');
  for (let attempt = 1; attempt <= pollTries; attempt++) {
    await sleep(pollDelayMs);
    const record = await readMediaRecordInDialog(runInTab, expectedSiteKey, lookFor);
    if (record) {
      return { status: 'uploaded_for_dialog_driver', mediaId: record.id, url: record.url, title: record.title, filename: record.filename, mimeType: record.mimeType, bytes: record.bytes, attempts: attempt };
    }
    onProgress({ stage: 'readback-poll', attempt, filename });
  }
  return { status: 'stopped_ambiguous__no_record_in_media_library', attempts: pollTries, filename };
}

async function readMediaRecordInDialog(runInTab, siteKey, stem) {
  const js = `(function(){
    try{
      var n=Date.now().toString(36)+Math.random().toString(36).slice(2,9);
      var x=new XMLHttpRequest();
      x.open('GET','https://workspace.laicms.com/${siteKey}/media?_rsc='+n,false);
      x.setRequestHeader('Accept','text/x-component');x.setRequestHeader('RSC','1');x.withCredentials=true;x.send(null);
      var t=x.responseText;
      var i=t.indexOf(${JSON.stringify(stem)});
      if(i<0) return 'NM';
      var s=t.lastIndexOf('{"id"',i-400);if(s<0)s=Math.max(0,i-500);
      var d=0,fi=-1;
      for(var k=s;k<t.length;k++){var c=t[k];if(c==='{')d++;if(c==='}'){d--;if(d===0){fi=k+1;break;}}}
      var chunk=t.slice(s,fi);
      var id=(chunk.match(/"id":"([0-9a-f]{24})"/)||[])[1]||null;
      var url=(chunk.match(/"url":"(https:\\/\\/assets\\.laicms\\.com\\/[^"]+)"/)||[])[1]||null;
      var title=(chunk.match(/"title":"([^"]+)"/)||[])[1]||null;
      var fn=(chunk.match(/"filename":"([^"]+)"/)||[])[1]||null;
      var mt=(chunk.match(/"mimeType":"([^"]+)"/)||[])[1]||null;
      var sz=(chunk.match(/"filesize":(\\d+)/)||[])[1]||null;
      return id&&url?JSON.stringify({id:id,url:url,title:title,filename:fn,mimeType:mt,bytes:sz?Number(sz):null}):'NM';
    }catch(e){return 'ERR:'+e.message}
  })()`;
  const out = await runInTab(js);
  if (!out || out === 'NM' || out.startsWith('ERR:')) return null;
  try { return JSON.parse(out); } catch { return null; }
}

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
