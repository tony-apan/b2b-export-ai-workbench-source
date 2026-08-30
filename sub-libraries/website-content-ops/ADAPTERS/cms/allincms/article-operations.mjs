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

export function createAllinCmsActionClient({ siteKey, runtime, request, authorizationContext = null }) {
  if (typeof request !== 'function') throw new Error('request callback is required');
  assertSiteKey(siteKey);
  return {
    async send({ route, actionName, payload }) {
      const contract = assertRuntime(runtime, actionName);
      const binding = deriveAllinCmsMutationBinding({ siteKey, route, actionName, payload });
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
        body: JSON.stringify([payload]),
        siteKey,
        route,
        actionName,
        payload,
      };
      try {
        return normalizeResponse(await request(requestDetails));
      } catch (error) {
        if (error && typeof error === 'object') error.requestStarted = error.requestStarted ?? true;
        throw error;
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
  let attempt = 0;
  let lastResponse = null;
  let lastError = null;
  while (true) {
    let requestStarted = false;
    try {
      requestStarted = true;
      lastResponse = await client.send({ route, actionName, payload });
    } catch (error) {
      requestStarted = error?.requestStarted === true;
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
      return client.send(details);
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

export async function createPostDraft({
  client, siteKey, runtime, request, authorizationContext = null,
  createContractConfirmed = false, siteId, payload = { siteId }, expected, readback, refresh, match,
  getCreatedPostId, getCreatedPostSiteId, getAfterPostIds, beforePostIds,
  confirmExactAbsence, maxControlledRetries = 1,
}) {
  siteId = assertSiteId(siteId);
  if (!createContractConfirmed) throw new Error('Live post-create contract confirmation is required');
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('post create payload must be an object');
  if (Object.hasOwn(payload, 'siteId') && payload.siteId !== siteId) throw new Error('post create payload.siteId must match siteId');
  if (typeof readback !== 'function') throw new Error('readback callback is required');
  if (typeof getCreatedPostId !== 'function') throw new Error('getCreatedPostId callback is required');
  if (typeof getCreatedPostSiteId !== 'function') throw new Error('getCreatedPostSiteId callback is required');
  if (typeof getAfterPostIds !== 'function') throw new Error('getAfterPostIds callback is required');
  if (!Array.isArray(beforePostIds)) throw new Error('beforePostIds snapshot is required');
  const normalizedBeforePostIds = normalizeIdArray(beforePostIds, 'beforePostIds');
  const knownPostIds = new Set(normalizedBeforePostIds);
  const actionClient = await requireClient({ client, siteKey, runtime, request, authorizationContext });
  const matcher = match || ((actual) => Boolean(actual && (!expected || compareExpectedReadback(actual, expected, { fields: Object.keys(expected) }).ok)));
  let reconciledCreatedPostId = null;
  const result = await runActionWithRecovery({
    client: actionClient,
    route: actionRoute(siteKey, ''),
    actionName: 'postCreate',
    payload: { ...payload, siteId },
    expected,
    operation: 'post:create',
    readback,
    refresh,
    maxControlledRetries,
    retryOnExactAbsence: typeof confirmExactAbsence === 'function',
    confirmExactAbsence,
    compare: (actual) => {
      reconciledCreatedPostId = null;
      if (actual === null || actual === undefined) {
        return { ok: false, exactAbsence: true, mismatches: ['created post is absent from readback'] };
      }
      const mismatches = [];
      let matches = false;
      let createdPostId = null;
      let createdPostSiteId = null;
      let afterPostIds = [];
      try {
        matches = Boolean(matcher(actual));
      } catch (error) {
        mismatches.push(`created post matcher failed: ${error.message}`);
      }
      try {
        createdPostId = asNonEmptyString(getCreatedPostId(actual), 'created post ID');
        reconciledCreatedPostId = createdPostId;
      } catch (error) {
        mismatches.push('created post ID is missing from readback');
      }
      try {
        createdPostSiteId = asNonEmptyString(getCreatedPostSiteId(actual), 'created post siteId');
      } catch (error) {
        mismatches.push('created post siteId is missing from readback');
      }
      try {
        afterPostIds = normalizeIdArray(getAfterPostIds(actual), 'afterPostIds');
      } catch (error) {
        mismatches.push(error.message);
      }
      const newPostIds = afterPostIds.filter((id) => !knownPostIds.has(id));
      if (!matches) mismatches.push('created post did not match expected readback');
      if (createdPostSiteId && createdPostSiteId !== siteId) mismatches.push('created post belongs to a different site');
      if (newPostIds.length !== 1) mismatches.push(`expected exactly one new post ID after create, found ${newPostIds.length}`);
      if (createdPostId && knownPostIds.has(createdPostId)) mismatches.push('readback ID already existed before create');
      if (createdPostId && newPostIds.length === 1 && createdPostId !== newPostIds[0]) {
        mismatches.push('created post ID does not match the sole before/after snapshot difference');
      }
      return {
        ok: mismatches.length === 0,
        exactAbsence: false,
        mismatches: [...new Set(mismatches)],
      };
    },
  });
  return {
    ...result,
    createdPostId: reconciledCreatedPostId,
  };
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

export const _internal = {
  actionRoute,
  assertRuntime,
  normalizeResponse,
  taxonomyActionName,
  taxonomyRoute,
  validateSlateContent,
};
