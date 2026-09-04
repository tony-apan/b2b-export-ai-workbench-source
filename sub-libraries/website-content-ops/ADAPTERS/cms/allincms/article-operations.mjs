/**
 * AllinCMS article and taxonomy lifecycle adapter.
 *
 * This module is deliberately contract-driven. It never stores or invents
 * next-action, deployment, router-tree, site, post, category, or tag IDs.
 * The caller must discover those values from the currently signed-in page and
 * pass them in as runtime data. The shared bulk-upload skill is orchestration;
 * this module is the current site-aware execution contract.
 */
import { randomUUID } from 'node:crypto';
import { deriveAllinCmsMutationBinding, validateAllinCmsMutationAuthorizationContext } from './mutation-authorization.mjs';
// 2026-09-04 poisoning fix: article and product share markRequestStarted, the
// canonical create record comparator/normalization, and the create contract
// field constants ONLY through named ESM imports of this dependency-free
// module. ESM export bindings are immutable, so no importer can overwrite the
// shared implementation the way it could with the historical mutable
// `_internal` object channel (see the frozen `_internal` facade below).
import {
  ARTICLE_CREATE_CONTRACT_FIELDS,
  canonicalTexts,
  captureStableReadback,
  createdRecordExpectedProblems,
  extractCreateReadbackRecord,
  markRequestStarted,
  prepareStableCreatePayload,
} from './content-mutation-primitives.mjs';

export {
  ALLINCMS_ARTICLE_FORMAT_SUPPORT,
  ARTICLE_FORMAT_PROFILE,
  ARTICLE_FORMAT_PROFILE_DATE,
  PUBLISHABLE_BODY_END_MARKER,
  PUBLISHABLE_BODY_START_MARKER,
  createCanonicalAllinCmsSlateExamples,
  extractPublishableArticleMarkdown,
  markdownToAllinCmsSlate,
  publishableArticleMarkdownToAllinCmsSlate,
} from './article-content-formats.mjs';

export const WORKSPACE_ORIGIN = 'https://workspace.laicms.com';
export const ARTICLE_MODES = Object.freeze(['update', 'publish', 'unpublish']);
// P0-3.3a create canonical contract fields (8 + siteId) live in
// content-mutation-primitives.mjs (ARTICLE_CREATE_CONTRACT_FIELDS) as the
// single machine truth for both the article create expected comparison and
// the host driver's desired-state strict field validation; shared cross-module
// via named import only (never via the `_internal` facade).
export const ARTICLE_FIELDS = Object.freeze([
  'title', 'slug', 'excerpt', 'order', 'coverImage',
  'categories', 'tags', 'content', 'siteId', 'postId', 'mode',
]);
export const TAXONOMY_TYPES = Object.freeze(['category', 'tag']);
export const COVER_IMAGE_PERSISTED_FIELDS = Object.freeze([
  'name', 'alt', 'type', 'source', 'path', 'size', 'mimeType',
]);

const SUCCESS_STATUSES = new Set([
  'mutation_succeeded',
  'reconciled_success',
  'exact_absence_confirmed',
  'skipped_completed',
]);

function asNonEmptyString(value, label) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} is required`);
  return value.trim();
}

function assertSiteId(value) {
  return asNonEmptyString(value, 'siteId');
}

function assertSiteKey(value) {
  const siteKey = asNonEmptyString(value, 'siteKey');
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(siteKey)) {
    throw new Error('siteKey must be a single safe route segment');
  }
  return siteKey;
}

function assertControlledRetryBudget(value) {
  if (!Number.isInteger(value) || value < 0 || value > 1) {
    throw new Error('maxControlledRetries must be 0 or 1');
  }
  return value;
}

function assertRuntime(runtime, actionName) {
  if (!runtime || typeof runtime !== 'object') throw new Error('Runtime contract is required');
  const action = runtime.actions
    ? runtime.actions[actionName]
    : (runtime[actionName] || runtime);
  if (!action) throw new Error(`Missing runtime action for ${actionName}`);
  const actionId = action.actionId || action.nextAction;
  const routerTree = action.routerTree || runtime.routerTree;
  const deploymentId = action.deploymentId || action.xDeploymentId || runtime.deploymentId;
  if (!asNonEmptyString(actionId, `${actionName}.actionId`)) throw new Error(`Missing runtime action for ${actionName}`);
  if (!asNonEmptyString(routerTree, `${actionName}.routerTree`)) throw new Error('Missing current Next.js router tree');
  if (!asNonEmptyString(deploymentId, `${actionName}.deploymentId`)) throw new Error('Missing current deployment ID');
  return { actionId, routerTree, deploymentId, action };
}

function actionRoute(siteKey, suffix) {
  const key = assertSiteKey(siteKey);
  return `/${key}/posts${suffix || ''}`;
}

function normalizeComparableJson(value) {
  if (value === undefined) return ['undefined'];
  if (value === null) return ['null'];
  if (Array.isArray(value)) return ['array', value.map(normalizeComparableJson)];
  if (typeof value === 'object') {
    return ['object', Object.keys(value).sort().map((key) => [key, normalizeComparableJson(value[key])])];
  }
  return [typeof value, value];
}

function sameJson(left, right) {
  // CDP/browser readback objects can carry a different realm prototype even
  // when their persisted JSON values are identical. Compare JSON semantics,
  // not JavaScript realm identity or prototype provenance.
  return JSON.stringify(normalizeComparableJson(left)) === JSON.stringify(normalizeComparableJson(right));
}

// Canonical stable text for create-readback comparison (canonicalTexts), the
// bottom-owned create-readback record extraction
// (extractCreateReadbackRecord), and the irreplaceable canonical expected
// comparison (createdRecordExpectedProblems) moved to
// content-mutation-primitives.mjs (2026-09-04 poisoning fix): product imports
// them by name from that module, and this module re-imports the exact same
// immutable bindings, so article and product can never drift apart and no
// mutable `_internal` property sits on the sharing channel anymore.

function readbackStatus(actual) {
  const values = ['status', '_status', 'state', 'publishStatus']
    .map((field) => actual?.[field])
    .filter((value) => typeof value === 'string' && value.trim())
    .map((value) => value.trim().toLowerCase());
  const distinct = [...new Set(values)];
  if (distinct.length > 1) return { status: null, conflict: true };
  return { status: distinct[0] || null, conflict: false };
}

function articleModeStatusMismatch(actual, mode) {
  const { status, conflict } = readbackStatus(actual);
  if (conflict) return 'article readback contains conflicting publish states';
  if (!status) return 'article publish state is missing from readback';
  if (['update', 'unpublish'].includes(mode) && !['draft', 'unpublished'].includes(status)) return 'article is not in draft state';
  if (mode === 'publish' && status !== 'published') return 'article is not confirmed as published';
  return null;
}

function assertRecordsSnapshot(records, label = 'records') {
  if (!Array.isArray(records)) throw new Error(`${label} snapshot is required`);
  return records;
}

function normalizeIdArray(value, label) {
  if (!Array.isArray(value)) throw new Error(`${label} must be an array of IDs`);
  const normalized = value.map((id) => asNonEmptyString(id, `${label} item`));
  if (new Set(normalized).size !== normalized.length) throw new Error(`${label} must not contain duplicate IDs`);
  return normalized;
}

function validateSlateContent(content) {
  if (!Array.isArray(content)) throw new Error('content must be a Slate node array');
  const ids = new Set();
  for (const [index, node] of content.entries()) {
    if (!node || typeof node !== 'object') throw new Error(`content[${index}] must be an object`);
    if (!asNonEmptyString(node.type, `content[${index}].type`)) throw new Error(`content[${index}].type is required`);
    if (!Array.isArray(node.children)) throw new Error(`content[${index}].children must be an array`);
    if (node.id !== undefined) {
      asNonEmptyString(node.id, `content[${index}].id`);
      if (ids.has(node.id)) throw new Error(`duplicate Slate node id: ${node.id}`);
      ids.add(node.id);
    }
  }
}

export function normalizeArticleCoverImage(coverImage) {
  if (coverImage === null || coverImage === undefined) return coverImage ?? null;
  if (!coverImage || typeof coverImage !== 'object' || Array.isArray(coverImage)) {
    throw new Error('coverImage must be a media object or null');
  }
  const missing = COVER_IMAGE_PERSISTED_FIELDS.filter((field) => !Object.hasOwn(coverImage, field));
  if (missing.length) {
    throw new Error(`coverImage is missing canonical persisted fields: ${missing.join(', ')}`);
  }
  asNonEmptyString(coverImage.name, 'coverImage.name');
  if (typeof coverImage.alt !== 'string') throw new Error('coverImage.alt must be a string');
  asNonEmptyString(coverImage.type, 'coverImage.type');
  asNonEmptyString(coverImage.source, 'coverImage.source');
  asNonEmptyString(coverImage.path, 'coverImage.path');
  if (!Number.isInteger(coverImage.size) || coverImage.size < 0) {
    throw new Error('coverImage.size must be a non-negative integer');
  }
  asNonEmptyString(coverImage.mimeType, 'coverImage.mimeType');
  return structuredClone(coverImage);
}

export function buildArticlePayload({
  defaults = {},
  overrides = {},
  siteId,
  postId,
  mode = 'update',
}) {
  assertSiteId(siteId);
  asNonEmptyString(postId, 'postId');
  if (!ARTICLE_MODES.includes(mode)) throw new Error(`Unsupported article mode: ${mode}`);
  const payload = {
    title: overrides.title ?? defaults.title ?? '',
    slug: overrides.slug ?? defaults.slug ?? '',
    excerpt: overrides.excerpt ?? defaults.excerpt ?? '',
    order: overrides.order ?? defaults.order ?? 0,
    coverImage: Object.hasOwn(overrides, 'coverImage') ? overrides.coverImage : (defaults.coverImage ?? null),
    categories: overrides.categories ?? defaults.categories ?? [],
    tags: overrides.tags ?? defaults.tags ?? [],
    content: overrides.content ?? defaults.content ?? [],
    siteId,
    postId,
    mode,
  };
  payload.title = asNonEmptyString(payload.title, 'Article title');
  payload.slug = asNonEmptyString(payload.slug, 'Article slug');
  if (!Number.isInteger(payload.order)) throw new Error('Article order must be an integer');
  payload.categories = normalizeIdArray(payload.categories, 'categories');
  payload.tags = normalizeIdArray(payload.tags, 'tags');
  validateSlateContent(payload.content);
  payload.coverImage = normalizeArticleCoverImage(payload.coverImage);
  return payload;
}

export function buildCategoryPayload({ siteId, name, slug, description, cover = null, parent, order = 0, contentType = 'posts' }) {
  assertSiteId(siteId);
  if (contentType !== 'posts') throw new Error('AllinCMS article taxonomy contentType must be posts');
  asNonEmptyString(name, 'category name');
  asNonEmptyString(slug, 'category slug');
  if (!Number.isInteger(order)) throw new Error('category order must be an integer');
  const payload = { siteId, contentType, name: name.trim(), slug: slug.trim(), order };
  if (description !== undefined && `${description}`.trim() !== '') payload.description = description;
  if (cover !== undefined) payload.cover = cover;
  if (parent !== undefined && parent !== null) payload.parent = asNonEmptyString(parent, 'category parent');
  return payload;
}

export function buildTagPayload({ siteId, name, slug, description, contentType = 'posts', id }) {
  assertSiteId(siteId);
  if (contentType !== 'posts') throw new Error('AllinCMS article taxonomy contentType must be posts');
  asNonEmptyString(name, 'tag name');
  asNonEmptyString(slug, 'tag slug');
  const payload = { siteId, contentType, name: name.trim(), slug: slug.trim() };
  if (description !== undefined && `${description}`.trim() !== '') payload.description = description;
  if (id !== undefined) payload.id = asNonEmptyString(id, 'tag id');
  return payload;
}

export function assertNoDuplicateSlug(records, slug, siteId, label = 'taxonomy') {
  const normalizedSlug = asNonEmptyString(slug, `${label} slug`);
  const normalizedSiteId = assertSiteId(siteId);
  const snapshot = assertRecordsSnapshot(records, label);
  for (const [index, record] of snapshot.entries()) {
    if (!record || typeof record !== 'object' || Array.isArray(record)) {
      throw new Error(`${label}[${index}] must be a record object`);
    }
    const recordSiteId = asNonEmptyString(record.siteId, `${label}[${index}].siteId`);
    if (recordSiteId === normalizedSiteId && String(record.slug || '').trim() === normalizedSlug) {
      throw new Error(`${label} slug already exists: ${slug}`);
    }
  }
  return true;
}

export function assertSameSite(record, siteId, label = 'record') {
  const expectedSiteId = assertSiteId(siteId);
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    throw new Error(`${label} readback record is required`);
  }
  const actualSiteId = asNonEmptyString(record.siteId, `${label}.siteId`);
  if (actualSiteId !== expectedSiteId) throw new Error(`${label} belongs to a different site`);
  return true;
}

function compareCreatedTaxonomyReadback(actual, payload, label) {
  const comparableActual = actual && typeof actual === 'object' && !Array.isArray(actual)
    ? { ...actual }
    : actual;
  // The current posts taxonomy RSC records omit contentType. The exact
  // /posts taxonomy route and the fixed payload contract already scope the
  // record to contentType=posts. Preserve an explicit conflicting value as a
  // mismatch, but do not turn an omitted route-scoped field into a false
  // mutation failure.
  if (comparableActual && !Object.hasOwn(comparableActual, 'contentType') && payload.contentType === 'posts') {
    comparableActual.contentType = 'posts';
  }
  const result = compareExpectedReadback(comparableActual, payload, { fields: Object.keys(payload) });
  if (actual && typeof actual === 'object' && !Array.isArray(actual)) {
    try {
      assertSameSite(actual, payload.siteId, label);
    } catch (error) {
      result.mismatches.push(error.message);
    }
    try {
      asNonEmptyString(actual.id, `${label}.id`);
    } catch (error) {
      result.mismatches.push(error.message);
    }
  } else if (!result.mismatches.includes('record is absent')) {
    result.mismatches.push(`${label} readback record is required`);
  }
  result.mismatches = [...new Set(result.mismatches)];
  result.ok = result.mismatches.length === 0;
  return result;
}

export function compareExpectedReadback(actual, expected, { fields = [], mode = 'present' } = {}) {
  if (mode === 'absent') {
    const absent = actual === null || actual === undefined || actual === false;
    return absent
      ? { ok: true, exactAbsence: true, mismatches: [] }
      : { ok: false, exactAbsence: false, mismatches: ['record still exists'] };
  }
  if (actual === null || actual === undefined || actual === false) {
    return { ok: false, exactAbsence: true, mismatches: ['record is absent'] };
  }
  const mismatches = fields.filter((field) => !sameJson(actual[field], expected[field]));
  return { ok: mismatches.length === 0, exactAbsence: false, mismatches };
}

export function reconcileAmbiguousPostAction({ actual, expected, mode = 'update' }) {
  const isDelete = mode === 'delete';
  const result = compareExpectedReadback(actual, expected, {
    mode: isDelete ? 'absent' : 'present',
    fields: isDelete ? [] : ARTICLE_FIELDS.filter((field) => field !== 'mode'),
  });
  if (result.ok) {
    return {
      status: isDelete ? 'exact_absence_confirmed' : 'reconciled_success',
      readback: actual,
      mismatches: [],
    };
  }
  return {
    status: 'stopped_manual_intervention',
    readback: actual,
    mismatches: result.mismatches,
  };
}

function normalizeResponse(response) {
  if (!response || typeof response !== 'object') return { status: null, contentType: null, ok: false };
  return {
    ...response,
    status: Number(response.status),
    contentType: response.contentType || response.headers?.['content-type'] || response.headers?.get?.('content-type') || null,
    ok: response.ok ?? (Number(response.status) === 200),
  };
}

// markRequestStarted moved to content-mutation-primitives.mjs (2026-09-04
// poisoning fix); imported by name above and shared bit-for-bit with
// product-operations.mjs.

export function createAllinCmsActionClient({ siteKey, runtime, request, authorizationContext = null }) {
  if (typeof request !== 'function') throw new Error('request callback is required');
  assertSiteKey(siteKey);
  return {
    async send({ route, actionName, payload, payloadText }) {
      const contract = assertRuntime(runtime, actionName);
      if (payloadText !== undefined && typeof payloadText !== 'string') {
        throw new Error('payloadText must be an immutable string when provided');
      }
      const binding = deriveAllinCmsMutationBinding({ siteKey, route, actionName, payload, payloadText });
      validateAllinCmsMutationAuthorizationContext(authorizationContext, {
        expectedSiteKey: binding.siteKey, operation: binding.operation, target: binding.target,
      });
      const requestDetails = {
        url: `${WORKSPACE_ORIGIN}${route}`,
        method: 'POST',
        headers: {
          Accept: 'text/x-component',
          'Content-Type': 'text/plain;charset=UTF-8',
          'next-action': contract.actionId,
          'next-router-state-tree': contract.routerTree,
          'x-deployment-id': contract.deploymentId,
        },
        // B2 stable create payload: when the caller carries the prepared
        // payloadText, the wire body is EXACTLY `[${payloadText}]` — the same
        // immutable string the authorization digest hashed — on the first send
        // and on every controlled retry. Non-create callers keep the
        // JSON.stringify body. The adapter's byte guarantee ends at the input
        // of the host `request` callback handed this exact string: the actual
        // socket bytes are the host transport's responsibility.
        body: typeof payloadText === 'string' ? `[${payloadText}]` : JSON.stringify([payload]),
        siteKey,
        route,
        actionName,
        payload,
        payloadText,
      };
      try {
        return normalizeResponse(await request(requestDetails));
      } catch (error) {
        throw markRequestStarted(error);
      }
    },
  };
}

async function refreshAndRead({ refresh, readback }) {
  if (typeof refresh === 'function') await refresh();
  if (typeof readback !== 'function') throw new Error('readback callback is required after a mutation');
  return readback();
}

export async function runActionWithRecovery({
  client,
  route,
  actionName,
  payload,
  payloadText,
  expected,
  readback,
  refresh,
  compare = (actual) => compareExpectedReadback(actual, expected, { fields: Object.keys(expected || {}) }),
  operation,
  maxControlledRetries = 1,
  retryOnExactAbsence = false,
  confirmExactAbsence,
}) {
  if (!client?.send) throw new Error('AllinCMS action client is required');
  assertControlledRetryBudget(maxControlledRetries);
  if (typeof readback !== 'function') throw new Error('readback callback is required');
  // B2: the prepared create payloadText is an immutable string held for the
  // whole recovery loop, so the first send and every controlled retry hand
  // the transport the identical string (the wire body and the digest input
  // can never drift across attempts).
  if (payloadText !== undefined && typeof payloadText !== 'string') {
    throw new Error('payloadText must be an immutable string when provided');
  }
  let attempt = 0;
  let lastResponse = null;
  let lastError = null;
  while (true) {
    let requestStarted = false;
    try {
      requestStarted = true;
      lastResponse = await client.send({ route, actionName, payload, payloadText });
    } catch (error) {
      // Trust only an own, locked data property. An inherited
      // `Object.prototype.requestStarted = true` (prototype pollution) must
      // never upgrade a pre-send failure (e.g. an authorization refusal) into
      // "a request was sent", which would route it into reconciliation.
      requestStarted = error !== null
        && typeof error === 'object'
        && Object.getOwnPropertyDescriptor(error, 'requestStarted')?.value === true;
      if (!requestStarted) throw error;
      lastError = error;
      lastResponse = null;
    }

    let actual;
    try {
      actual = await refreshAndRead({ refresh, readback });
    } catch (error) {
      return {
        status: 'stopped_manual_intervention',
        operation,
        attempt,
        requestStarted,
        response: lastResponse,
        error: lastError?.message || error.message,
        readbackError: error.message,
        automaticRetryAllowed: false,
      };
    }
    let reconciliation;
    try {
      reconciliation = compare(actual);
    } catch (error) {
      return {
        status: 'stopped_manual_intervention',
        operation,
        attempt,
        requestStarted,
        response: lastResponse,
        readback: actual,
        error: error.message,
        automaticRetryAllowed: false,
      };
    }
    const responseOk = lastResponse?.status === 200 && String(lastResponse.contentType || '').startsWith('text/x-component');
    if (reconciliation.ok) {
      return {
        status: responseOk ? 'mutation_succeeded' : 'reconciled_success',
        operation,
        attempt,
        requestStarted,
        response: lastResponse,
        readback: actual,
        automaticRetryAllowed: false,
      };
    }

    let exactAbsenceConfirmed = false;
    if (!responseOk && reconciliation.exactAbsence && retryOnExactAbsence) {
      try {
        exactAbsenceConfirmed = typeof confirmExactAbsence === 'function'
          && Boolean(await confirmExactAbsence({ actual, attempt, response: lastResponse, payload }));
      } catch (error) {
        return {
          status: 'stopped_manual_intervention',
          operation,
          attempt,
          requestStarted,
          response: lastResponse,
          readback: actual,
          error: error.message,
          automaticRetryAllowed: false,
        };
      }
    }
    const canRetry = !responseOk
      && reconciliation.exactAbsence
      && exactAbsenceConfirmed
      && attempt < maxControlledRetries;
    if (canRetry) {
      attempt += 1;
      continue;
    }
    return {
      status: 'stopped_manual_intervention',
      operation,
      attempt,
      requestStarted,
      response: lastResponse,
      readback: actual,
      error: lastError?.message || null,
      mismatches: reconciliation.mismatches,
      automaticRetryAllowed: false,
    };
  }
}

async function requireClient({ client, siteKey, runtime, request, authorizationContext }) {
  if (!client) return createAllinCmsActionClient({ siteKey, runtime, request, authorizationContext });
  if (typeof client.send !== 'function') throw new Error('AllinCMS action client is required');
  return {
    async send(details) {
      const binding = deriveAllinCmsMutationBinding({ siteKey, ...details });
      validateAllinCmsMutationAuthorizationContext(authorizationContext, {
        expectedSiteKey: binding.siteKey, operation: binding.operation, target: binding.target,
      });
      try {
        return await client.send(details);
      } catch (error) {
        throw markRequestStarted(error);
      }
    },
  };
}

async function runArticleMutation({
  client, siteKey, runtime, request, authorizationContext,
  postId, siteId, defaults, overrides, mode, readback, refresh, maxControlledRetries = 1,
}) {
  const actionClient = await requireClient({ client, siteKey, runtime, request, authorizationContext });
  const payload = buildArticlePayload({ defaults, overrides, siteId, postId, mode });
  const expectedFields = ARTICLE_FIELDS.filter((field) => field !== 'mode');
  return runActionWithRecovery({
    client: actionClient,
    route: actionRoute(siteKey, `/${postId}/update`),
    actionName: 'postUpdate',
    payload,
    expected: payload,
    operation: `post:${mode}`,
    readback,
    refresh,
    maxControlledRetries,
    compare: (actual) => {
      const result = compareExpectedReadback(actual, payload, { fields: expectedFields });
      const statusMismatch = articleModeStatusMismatch(actual, mode);
      if (statusMismatch) result.mismatches.push(statusMismatch);
      result.ok = result.mismatches.length === 0;
      return result;
    },
  });
}

export function savePostDraft(options) {
  return runArticleMutation({ ...options, mode: 'update' });
}

export function publishPost(options) {
  return runArticleMutation({ ...options, mode: 'publish' });
}

export function unpublishPost(options) {
  return runArticleMutation({ ...options, mode: 'unpublish' });
}

function editorReopenProblems(evidence, createdPostId) {
  if (!evidence || typeof evidence !== 'object' || Array.isArray(evidence)) {
    return ['editor reopen evidence object is required'];
  }
  const problems = [];
  if (Number(evidence.status) !== 200) problems.push('reopened article editor did not return HTTP 200');
  if (evidence.authenticated !== true) problems.push('reopened article editor was not authenticated');
  if (evidence.healthy !== true) problems.push('reopened article editor is not healthy');
  if (evidence.postId !== createdPostId) problems.push('reopened article editor postId does not match the created article');
  return problems;
}

export async function createPostDraft({
  client, siteKey, runtime, request, authorizationContext = null,
  siteId, payload = { siteId }, expected, expectedMatch, readback, refresh, beforePostIds,
  getCreatedPostId, getCreatedPostSiteId, getAfterPostIds,
  match, editorReopen, maxControlledRetries = 0,
}) {
  siteId = assertSiteId(siteId);
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('article create payload must be an object');
  // payload.siteId agreement with siteId is enforced descriptor-only inside
  // prepareStableCreatePayload (the 2026-09-04 stable create payload rule);
  // a [[Get]]-based check here would invoke hostile getters for nothing.
  // P0-3.3a.1 fail-closed expected binding: canonical create never runs without
  // an expected readback. `expected` must be a non-array object and must be the
  // exact same object reference as `payload` (the canonical driver freezes one
  // payload object and passes it as both). A missing, junk, or equal-but-
  // separate expected value is refused before any client, provider, or request.
  if (!expected || typeof expected !== 'object' || Array.isArray(expected)) {
    throw new Error('article create expected must be a non-array object (missing expected, arrays and non-object values are refused before any request)');
  }
  if (expected !== payload) {
    throw new Error('article create expected must be the same object reference as payload (an equal but separate expected object is refused before any request)');
  }
  // P0-3.3a.3: `expectedMatch` is no longer a parameter. The canonical
  // expected comparison over the 8 contract fields + siteId is owned by this
  // function itself (see createdRecordExpectedProblems) and runs on the
  // bottom-extracted record (raw record or the known {record, afterIds}
  // wrapper), so no caller can supply, replace, or waive it — not even with a
  // predicate that always returns true. Supplying the removed parameter is
  // refused loudly before any client, provider, or request so a legacy caller
  // can never believe its own matcher is still in charge.
  if (expectedMatch !== undefined && expectedMatch !== null) {
    throw new Error('article create expectedMatch has been removed: the canonical expected comparison is owned by createPostDraft itself and cannot be supplied, replaced, or waived by any caller callback (use match only for extra AND-ed constraints)');
  }
  if (match !== undefined && match !== null && typeof match !== 'function') {
    throw new Error('article create match must be a function when provided');
  }
  if (typeof readback !== 'function') throw new Error('readback callback is required');
  if (typeof getCreatedPostId !== 'function') throw new Error('getCreatedPostId callback is required');
  if (typeof getCreatedPostSiteId !== 'function') throw new Error('getCreatedPostSiteId callback is required');
  if (typeof getAfterPostIds !== 'function') throw new Error('getAfterPostIds callback is required');
  if (typeof editorReopen !== 'function') throw new Error('editorReopen callback is required');
  // Create is not safely retryable: a resend would duplicate the draft. The
  // request either reconciles from readback or stops for manual intervention.
  if (maxControlledRetries !== 0) throw new Error('article create does not allow controlled retries; maxControlledRetries must be 0');
  if (!Array.isArray(beforePostIds)) throw new Error('beforePostIds snapshot is required');
  const knownPostIds = new Set(normalizeIdArray(beforePostIds, 'beforePostIds'));
  // B1 stable create payload: one synchronous prepare of the exact outgoing
  // payload (8 contract fields + siteId) BEFORE any client/provider/request.
  // A driver that already prepared the branded frozen snapshot gets the very
  // same object and payloadText back (idempotent re-prepare), so the bottom
  // layer can never rebuild a second, differently-semantic payload; the
  // historical `{...payload, siteId}` second construction is gone. After this
  // point the caller's original object is never read again: the request
  // payload, the authorization binding input, and the expected readback are
  // all this one frozen snapshot plus its immutable payloadText.
  const { snapshot, payloadText } = prepareStableCreatePayload('article', payload, siteId);
  const actionClient = await requireClient({ client, siteKey, runtime, request, authorizationContext });
  let reconciledCreatedPostId = null;
  const result = await runActionWithRecovery({
    client: actionClient,
    route: actionRoute(siteKey),
    actionName: 'postCreate',
    payload: snapshot,
    payloadText,
    expected: snapshot,
    operation: 'post:create',
    readback,
    refresh,
    maxControlledRetries: 0,
    compare: (rawActual) => {
      reconciledCreatedPostId = null;
      if (rawActual === null || rawActual === undefined) return { ok: false, exactAbsence: true, mismatches: ['created article is absent from readback'] };
      // B2 readback stabilization: one synchronous descriptor-only capture of
      // the whole readback. The canonical comparison and every caller getter
      // below consume this SAME stable copy, so a getter/proxy readback can
      // never serve one record to the comparison (A) and a different record
      // to ID extraction (B); accessors and trap-throwing proxies fail closed
      // here without any getter ever being invoked.
      let actual;
      try {
        actual = captureStableReadback(rawActual, 'created article readback');
      } catch (stableError) {
        return { ok: false, exactAbsence: false, mismatches: [`created article readback could not be captured as stable plain data (${stableError.message})`] };
      }
      const mismatches = [];
      let createdPostId = null;
      let createdPostSiteId = null;
      let afterPostIds = [];
      // P0-3.3a.3: the canonical expected comparison is irreplaceable
      // bottom-layer logic. The record is extracted here (raw record or the
      // known {record, afterPostIds} host wrapper) and compared against the
      // prepared snapshot over ARTICLE_CREATE_CONTRACT_FIELDS + siteId
      // with no caller-supplied predicate anywhere on this channel. A custom
      // `match` can only AND an additional constraint on top of this PASS, so
      // a permissive `match` alone can never wave a drifted record through.
      const canonicalProblems = createdRecordExpectedProblems(
        extractCreateReadbackRecord(actual),
        snapshot,
        ARTICLE_CREATE_CONTRACT_FIELDS,
        'article',
      );
      if (canonicalProblems.length > 0) {
        mismatches.push(`created article did not match the canonical expected readback: ${canonicalProblems.join('; ')}`);
      }
      if (match !== undefined && match !== null) {
        try {
          if (!match(actual, snapshot)) mismatches.push('created article did not match the additional expected constraints');
        } catch (error) {
          mismatches.push(`created article additional match failed: ${error.message}`);
        }
      }
      try {
        createdPostId = asNonEmptyString(getCreatedPostId(actual), 'created article ID');
        reconciledCreatedPostId = createdPostId;
      } catch (error) {
        mismatches.push('created article ID is missing from readback');
      }
      try {
        createdPostSiteId = asNonEmptyString(getCreatedPostSiteId(actual), 'created article siteId');
      } catch (error) {
        mismatches.push('created article siteId is missing from readback');
      }
      try {
        afterPostIds = normalizeIdArray(getAfterPostIds(actual), 'after post ID snapshot');
      } catch (error) {
        mismatches.push(error.message);
      }
      const newPostIds = afterPostIds.filter((id) => !knownPostIds.has(id));
      if (createdPostSiteId && createdPostSiteId !== siteId) mismatches.push('created article belongs to a different site');
      if (newPostIds.length !== 1) mismatches.push(`expected exactly one new article ID after create, found ${newPostIds.length}`);
      if (createdPostId && knownPostIds.has(createdPostId)) mismatches.push('readback ID already existed before create');
      if (createdPostId && newPostIds.length === 1 && createdPostId !== newPostIds[0]) {
        mismatches.push('created article ID does not match the sole before/after snapshot difference');
      }
      return { ok: mismatches.length === 0, exactAbsence: false, mismatches: [...new Set(mismatches)] };
    },
  });
  if (!SUCCESS_STATUSES.has(result.status)) {
    return { ...result, createdPostId: null, automaticRetryAllowed: false };
  }
  const createdPostId = asNonEmptyString(reconciledCreatedPostId, 'created article ID');
  let editorReopenEvidence = null;
  try {
    editorReopenEvidence = await editorReopen(createdPostId);
  } catch (error) {
    return {
      ...result,
      status: 'stopped_manual_intervention',
      createdPostId,
      error: error.message,
      editorReopen: null,
      mismatches: [`editor reopen failed: ${error.message}`],
      automaticRetryAllowed: false,
    };
  }
  const reopenProblems = editorReopenProblems(editorReopenEvidence, createdPostId);
  if (reopenProblems.length > 0) {
    return {
      ...result,
      status: 'stopped_manual_intervention',
      createdPostId,
      editorReopen: editorReopenEvidence,
      mismatches: reopenProblems,
      automaticRetryAllowed: false,
    };
  }
  return { ...result, createdPostId, editorReopen: editorReopenEvidence, automaticRetryAllowed: false };
}

export function deletePost({
  client, siteKey, runtime, request, authorizationContext = null,
  siteId, postId, readback, refresh, maxControlledRetries = 1,
}) {
  siteId = assertSiteId(siteId);
  asNonEmptyString(postId, 'postId');
  return requireClient({ client, siteKey, runtime, request, authorizationContext }).then((actionClient) => runActionWithRecovery({
    client: actionClient,
    route: actionRoute(siteKey, '?tab=list'),
    actionName: 'postDelete',
    payload: { id: postId, siteId },
    expected: null,
    operation: 'post:delete',
    readback,
    refresh,
    maxControlledRetries,
    compare: (actual) => compareExpectedReadback(actual, null, { mode: 'absent' }),
  }));
}

function taxonomyRoute(siteKey, type) {
  return actionRoute(siteKey, `?tab=${type === 'category' ? 'categories' : 'tags'}`);
}

function taxonomyActionName(type, action) {
  return `${type}${action[0].toUpperCase()}${action.slice(1)}`;
}

async function runTaxonomyMutation({ type, action, payload, expected, client, siteKey, runtime, request, authorizationContext, readback, refresh, compare, operation, maxControlledRetries = 1 }) {
  const actionClient = await requireClient({ client, siteKey, runtime, request, authorizationContext });
  return runActionWithRecovery({
    client: actionClient,
    route: taxonomyRoute(siteKey, type),
    actionName: taxonomyActionName(type, action),
    payload,
    expected,
    operation: operation || `${type}:${action}`,
    readback,
    refresh,
    maxControlledRetries,
    compare,
  });
}

export function createPostCategory({
  existing, siteId, name, slug, description, cover = null, parent, order = 0,
  client, siteKey, runtime, request, authorizationContext = null, readback, refresh, maxControlledRetries = 1,
}) {
  assertNoDuplicateSlug(existing, slug, siteId, 'category');
  const payload = buildCategoryPayload({ siteId, name, slug, description, cover, parent, order });
  return runTaxonomyMutation({
    type: 'category', action: 'create', payload, expected: payload,
    client, siteKey, runtime, request, authorizationContext, readback, refresh, maxControlledRetries,
    compare: (actual) => compareCreatedTaxonomyReadback(actual, payload, 'created category'),
  });
}

export function updatePostCategory({
  id, siteId, name, slug, description, cover = null, parent, order = 0,
  client, siteKey, runtime, request, authorizationContext = null, readback, refresh, maxControlledRetries = 1,
}) {
  const payload = { ...buildCategoryPayload({ siteId, name, slug, description, cover, parent, order }), id: asNonEmptyString(id, 'category id') };
  return runTaxonomyMutation({
    type: 'category', action: 'update', payload, expected: payload,
    client, siteKey, runtime, request, authorizationContext, readback, refresh, maxControlledRetries,
    compare: (actual) => compareExpectedReadback(actual, payload, { fields: ['id', 'siteId', 'name', 'slug', 'description', 'cover', 'parent', 'order'] }),
  });
}

export function deletePostCategory({ id, siteId, client, siteKey, runtime, request, authorizationContext = null, readback, refresh, maxControlledRetries = 1 }) {
  siteId = assertSiteId(siteId);
  const payload = { id: asNonEmptyString(id, 'category id'), siteId, contentType: 'posts' };
  return runTaxonomyMutation({
    type: 'category', action: 'delete', payload, expected: null,
    client, siteKey, runtime, request, authorizationContext, readback, refresh, maxControlledRetries,
    compare: (actual) => compareExpectedReadback(actual, null, { mode: 'absent' }),
  });
}

export function createPostTag({
  existing, siteId, name, slug, description,
  client, siteKey, runtime, request, authorizationContext = null, readback, refresh, maxControlledRetries = 1,
}) {
  assertNoDuplicateSlug(existing, slug, siteId, 'tag');
  const payload = buildTagPayload({ siteId, name, slug, description });
  return runTaxonomyMutation({
    type: 'tag', action: 'create', payload, expected: payload,
    client, siteKey, runtime, request, authorizationContext, readback, refresh, maxControlledRetries,
    compare: (actual) => compareCreatedTaxonomyReadback(actual, payload, 'created tag'),
  });
}

export function updatePostTag({
  id, siteId, name, slug, description,
  client, siteKey, runtime, request, authorizationContext = null, readback, refresh, maxControlledRetries = 1,
}) {
  const payload = { ...buildTagPayload({ siteId, name, slug, description, id }), id };
  return runTaxonomyMutation({
    type: 'tag', action: 'update', payload, expected: payload,
    client, siteKey, runtime, request, authorizationContext, readback, refresh, maxControlledRetries,
    compare: (actual) => compareExpectedReadback(actual, payload, { fields: ['id', 'siteId', 'name', 'slug', 'description'] }),
  });
}

export function deletePostTag({ id, siteId, client, siteKey, runtime, request, authorizationContext = null, readback, refresh, maxControlledRetries = 1 }) {
  siteId = assertSiteId(siteId);
  const payload = { id: asNonEmptyString(id, 'tag id'), siteId, contentType: 'posts' };
  return runTaxonomyMutation({
    type: 'tag', action: 'delete', payload, expected: null,
    client, siteKey, runtime, request, authorizationContext, readback, refresh, maxControlledRetries,
    compare: (actual) => compareExpectedReadback(actual, null, { mode: 'absent' }),
  });
}

export async function runArticleBatchSerial({ items, execute, completedKeys = [], maxItems = 50 }) {
  if (!Array.isArray(items)) throw new Error('items must be an array');
  if (typeof execute !== 'function') throw new Error('execute callback is required');
  if (items.length > maxItems) throw new Error(`batch exceeds safety limit of ${maxItems}`);
  const completed = new Set(completedKeys);
  const report = { status: 'completed', total: items.length, skipped: [], completed: [], stopped: null, results: [] };
  for (const [index, item] of items.entries()) {
    const key = item.key || item.slug || item.id || `item-${index}`;
    if (completed.has(key)) {
      const result = { key, status: 'skipped_completed' };
      report.skipped.push(key);
      report.results.push(result);
      continue;
    }
    let result;
    try {
      result = await execute(item, { index, key });
    } catch (error) {
      result = { status: 'stopped_manual_intervention', error: error.message };
    }
    report.results.push({ key, ...result });
    if (!SUCCESS_STATUSES.has(result?.status)) {
      report.status = 'stopped';
      report.stopped = { key, index, result };
      break;
    }
    report.completed.push(key);
  }
  return report;
}

export function makeProbeIdentity(prefix = 'codex-probe') {
  return `${prefix}-${randomUUID()}`;
}

// Test/diagnostic-only facade. FROZEN since the 2026-09-04 poisoning fix:
// before it, product-operations.mjs destructured markRequestStarted /
// createdRecordExpectedProblems / extractCreateReadbackRecord out of this
// mutable object at first import, so an external actor that imported this
// module first could swap them and silently bypass product's transport-error
// reconcile or canonical create comparison. Cross-module consumers now use
// named imports from content-mutation-primitives.mjs instead; this facade is
// read-only (assignment throws TypeError in ESM strict mode) and mutating it
// can never affect the lexical functions above.
export const _internal = Object.freeze({
  actionRoute,
  assertRuntime,
  normalizeResponse,
  taxonomyActionName,
  taxonomyRoute,
  validateSlateContent,
  // P0-3.3a.3 shared canonical create-comparison internals (single machine
  // truth in content-mutation-primitives.mjs; exposed read-only for the host
  // driver's desired-state strict field validation and diagnostics).
  ARTICLE_CREATE_CONTRACT_FIELDS,
  canonicalTexts,
  createdRecordExpectedProblems,
  extractCreateReadbackRecord,
  // P0-A shared transport-error marking semantics: the same implementation
  // from content-mutation-primitives.mjs that product-operations.mjs imports
  // by name, so requestStarted=true transport semantics cannot drift per
  // module and cannot be replaced through this facade.
  markRequestStarted,
});
