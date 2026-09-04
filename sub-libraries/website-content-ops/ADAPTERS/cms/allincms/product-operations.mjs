/**
 * AllinCMS product lifecycle operations.
 *
 * This module follows the same contract-driven pattern as article-operations.mjs.
 * It never stores or invents action IDs, router trees, deployment IDs or entity IDs.
 * The caller must supply a current runtime contract from the authenticated deployment.
 */
import { createAllinCmsActionClient, runActionWithRecovery } from './article-operations.mjs';
import { deriveAllinCmsMutationBinding, validateAllinCmsMutationAuthorizationContext } from './mutation-authorization.mjs';
// 2026-09-04 poisoning fix: this module used to destructured-share
// markRequestStarted / createdRecordExpectedProblems /
// extractCreateReadbackRecord out of article-operations.mjs's mutable
// `_internal` export, so an external actor that imported article-operations
// first could overwrite them before product's first import and silently skip
// the post-request reconcile or accept create field drift. The shared
// safety-critical primitives now come from dependency-free
// content-mutation-primitives.mjs via named ESM imports (immutable bindings),
// never through any mutable `_internal` object.
import {
  PRODUCT_CREATE_CONTRACT_FIELDS,
  captureStableReadback,
  createdRecordExpectedProblems,
  extractCreateReadbackRecord,
  markRequestStarted,
  prepareStableCreatePayload,
} from './content-mutation-primitives.mjs';

export const WORKSPACE_ORIGIN = 'https://workspace.laicms.com';
export const PRODUCT_MODES = Object.freeze(['update', 'publish', 'unpublish']);
// P0-3.3a create canonical contract fields (10 + siteId) live in
// content-mutation-primitives.mjs (PRODUCT_CREATE_CONTRACT_FIELDS) as the
// single machine truth for both the product create expected comparison and
// the host driver's desired-state strict field validation; callers can
// neither add nor remove compared fields, and the bottom layer shares them
// with article only via named imports.
export const PRODUCT_FIELDS = Object.freeze([
  'name', 'slug', 'description', 'order', 'media', 'mediaList',
  'content', 'categories', 'tags', 'specifications', 'siteId', 'productId', 'mode',
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
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(siteKey)) throw new Error('siteKey must be a single safe route segment');
  return siteKey;
}

function asNonEmptyArray(value, label) {
  if (!Array.isArray(value)) throw new Error(`${label} must be an array`);
  return value.map((item) => asNonEmptyString(item, `${label} item`));
}

function normalizeSpecifications(value) {
  if (!Array.isArray(value)) throw new Error('specifications must be an array');
  return value.map((row, index) => {
    if (!row || typeof row !== 'object') throw new Error(`specifications[${index}] must be an object`);
    return {
      key: asNonEmptyString(row.key, `specifications[${index}].key`),
      value: asNonEmptyString(row.value, `specifications[${index}].value`),
    };
  });
}

function normalizeMediaUploadItem(value) {
  if (value === null || value === undefined) return value ?? null;
  if (typeof value !== 'object' || Array.isArray(value)) throw new Error('media must be a media upload item object or null');
  // Deployment media input contract (observed 2026-08-27, dpl 83eddf…):
  //   discriminatedUnion('source'): oss {name,alt?,type,source:'oss',path,size,mimeType}
  //                                  url  {name,alt?,type,source:'url',url(http)}
  // Accept editor-bound {type,value:{name,alt,type,source,url}}, the URL/OSS
  // top-level forms, and plain string ids; always emit the canonical input shape.
  if (value.source === 'url' || value.source === 'oss') {
    const name = typeof value.name === 'string' && value.name.trim() ? value.name : null;
    const type = typeof value.type === 'string' && value.type.trim() ? value.type : 'image';
    if (value.source === 'url' && typeof value.url === 'string') {
      if (!name) throw new Error('media.name is required for url media input');
      return structuredClone({ name, alt: value.alt ?? null, type, source: 'url', url: value.url });
    }
    if (value.source === 'oss') {
      if (!name) throw new Error('media.name is required for oss media input');
      if (typeof value.path !== 'string' || !Number.isInteger(value.size) || typeof value.mimeType !== 'string') {
        throw new Error('media.path, media.size (int) and media.mimeType are required for oss media input');
      }
      return structuredClone({ name, alt: value.alt ?? null, type, source: 'oss', path: value.path, size: value.size, mimeType: value.mimeType });
    }
  }
  if (typeof value.type === 'string' && typeof value.value === 'string') {
    return structuredClone({ name: value.value, alt: null, type: value.type, source: 'url', url: value.value });
  }
  if (typeof value.type === 'string' && value.value && typeof value.value === 'object' && !Array.isArray(value.value)) {
    const inner = value.value;
    const name = typeof inner.name === 'string' && inner.name.trim() ? inner.name : (typeof inner.url === 'string' ? inner.url.split('/').pop() : null);
    const type = typeof inner.type === 'string' ? inner.type : value.type;
    if (name && typeof inner.url === 'string') {
      return structuredClone({ name, alt: inner.alt ?? null, type, source: 'url', url: inner.url });
    }
    if (name && typeof inner.path === 'string') {
      return structuredClone({ name, alt: inner.alt ?? null, type, source: 'oss', path: inner.path, size: Number.isInteger(inner.size) ? inner.size : 0, mimeType: inner.mimeType ?? 'application/octet-stream' });
    }
  }
  for (const field of ['name', 'alt', 'type', 'source', 'path', 'size', 'mimeType']) {
    if (typeof value[field] !== 'string' && !(field === 'size' && Number.isInteger(value[field]))) {
      throw new Error(`media.${field} is required`);
    }
  }
  return structuredClone(value);
}

function normalizeMediaUploadItemList(value) {
  if (!Array.isArray(value)) throw new Error('mediaList must be an array');
  return value.map(normalizeMediaUploadItem);
}

export function buildProductPayload({ defaults = {}, overrides = {}, siteId, productId, mode }) {
  siteId = assertSiteId(siteId);
  productId = asNonEmptyString(productId, 'productId');
  if (!PRODUCT_MODES.includes(mode)) throw new Error(`mode must be one of ${PRODUCT_MODES.join(', ')}`);
  const payload = {
    name: overrides.name ?? defaults.name,
    slug: overrides.slug ?? defaults.slug,
    description: overrides.description ?? defaults.description,
    order: overrides.order ?? defaults.order ?? 0,
    media: normalizeMediaUploadItem(overrides.media !== undefined ? overrides.media : (defaults.media ?? null)),
    mediaList: normalizeMediaUploadItemList(overrides.mediaList !== undefined ? overrides.mediaList : (defaults.mediaList ?? [])),
    content: overrides.content !== undefined ? overrides.content : (defaults.content ?? []),
    categories: asNonEmptyArray(overrides.categories ?? defaults.categories ?? [], 'categories'),
    tags: asNonEmptyArray(overrides.tags ?? defaults.tags ?? [], 'tags'),
    specifications: normalizeSpecifications(overrides.specifications ?? defaults.specifications ?? []),
    siteId,
    productId,
    mode,
  };
  payload.name = asNonEmptyString(payload.name, 'Product name');
  payload.slug = asNonEmptyString(payload.slug, 'Product slug');
  if (`${payload.description ?? ''}`.trim() === '') throw new Error('Product description is required and must be non-empty (observed 2026-08-27: deployment zod requires description trim().min(1))');
  if (!Number.isInteger(payload.order)) throw new Error('Product order must be an integer');
  return payload;
}

function productRoute(siteKey, productId = null) {
  const key = assertSiteKey(siteKey);
  return productId ? `/${key}/products/${asNonEmptyString(productId, 'productId')}/update` : `/${key}/products`;
}

// P0-A: an injected client is transport only — it carries no authorization
// exemption. Exactly like requireClient in article-operations.mjs, every
// underlying send (the first attempt and every controlled retry) re-derives the
// exact mutation binding from the live route/action/payload and validates the
// structured authorizationContext against it immediately before the transport
// fires. deriveAllinCmsMutationBinding/validateAllinCmsMutationAuthorizationContext
// are the single machine truth from mutation-authorization.mjs (also used by the
// native createAllinCmsActionClient path), so injected and native clients can
// never disagree on what a valid authorization is. A validation failure throws
// without requestStarted, so it propagates out of runActionWithRecovery instead
// of turning into a reconciled/ambiguous result or a blind retry; only real
// transport errors are marked requestStarted by the shared markRequestStarted.
async function requireClient({ client, siteKey, runtime, request, authorizationContext }) {
  if (!client) {
    return createAllinCmsActionClient({ siteKey, runtime, request, authorizationContext });
  }
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

async function runProductMutation({
  client, siteKey, runtime, request, authorizationContext,
  productId, siteId, defaults, overrides, mode, readback, refresh, maxControlledRetries = 1,
}) {
  const actionClient = await requireClient({ client, siteKey, runtime, request, authorizationContext });
  const payload = buildProductPayload({ defaults, overrides, siteId, productId, mode });
  const expectedFields = PRODUCT_FIELDS.filter((field) => field !== 'mode');
  return runActionWithRecovery({
    client: actionClient,
    route: productRoute(siteKey, productId),
    actionName: 'productUpdate',
    payload,
    expected: payload,
    operation: `product:${mode}`,
    readback,
    refresh,
    maxControlledRetries,
  });
}

export function saveProductDraft(options) {
  return runProductMutation({ ...options, mode: 'update' });
}

export function publishProduct(options) {
  return runProductMutation({ ...options, mode: 'publish' });
}

export function unpublishProduct(options) {
  return runProductMutation({ ...options, mode: 'unpublish' });
}

export async function createProductDraft({
  client, siteKey, runtime, request, authorizationContext = null,
  siteId, payload = { siteId }, expected, expectedMatch, readback, refresh, beforeProductIds,
  getCreatedProductId, getCreatedProductSiteId, getAfterProductIds,
  match, maxControlledRetries = 1,
}) {
  siteId = assertSiteId(siteId);
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('product create payload must be an object');
  // payload.siteId agreement with siteId is enforced descriptor-only inside
  // prepareStableCreatePayload (the 2026-09-04 stable create payload rule);
  // a [[Get]]-based check here would invoke hostile getters for nothing.
  // P0-3.3a.1 fail-closed expected binding: canonical create never runs without
  // an expected readback. `expected` must be a non-array object and must be the
  // exact same object reference as `payload` (the canonical driver freezes one
  // payload object and passes it as both). A missing, junk, or equal-but-
  // separate expected value is refused before any client, provider, or request.
  if (!expected || typeof expected !== 'object' || Array.isArray(expected)) {
    throw new Error('product create expected must be a non-array object (missing expected, arrays and non-object values are refused before any request)');
  }
  if (expected !== payload) {
    throw new Error('product create expected must be the same object reference as payload (an equal but separate expected object is refused before any request)');
  }
  // P0-3.3a.3: `expectedMatch` is no longer a parameter. The canonical
  // expected comparison over the 10 contract fields + siteId is owned by this
  // function itself (createdRecordExpectedProblems in article-operations.mjs)
  // and runs on the bottom-extracted record (raw record or the known
  // {record, afterIds} wrapper), so no caller can supply, replace, or waive it
  // — not even with a predicate that always returns true. Supplying the
  // removed parameter is refused loudly before any client, provider, or
  // request so a legacy caller can never believe its own matcher still runs.
  if (expectedMatch !== undefined && expectedMatch !== null) {
    throw new Error('product create expectedMatch has been removed: the canonical expected comparison is owned by createProductDraft itself and cannot be supplied, replaced, or waived by any caller callback (use match only for extra AND-ed constraints)');
  }
  if (match !== undefined && match !== null && typeof match !== 'function') {
    throw new Error('product create match must be a function when provided');
  }
  if (typeof readback !== 'function') throw new Error('readback callback is required');
  if (typeof getCreatedProductId !== 'function') throw new Error('getCreatedProductId callback is required');
  if (typeof getCreatedProductSiteId !== 'function') throw new Error('getCreatedProductSiteId callback is required');
  if (typeof getAfterProductIds !== 'function') throw new Error('getAfterProductIds callback is required');
  if (!Array.isArray(beforeProductIds)) throw new Error('beforeProductIds snapshot is required');
  const knownProductIds = new Set(normalizeIdArray(beforeProductIds));
  // B1 stable create payload: one synchronous prepare of the exact outgoing
  // payload (10 contract fields + siteId) BEFORE any client/provider/request,
  // exactly like article create. A driver that already prepared the branded
  // frozen snapshot gets the very same object and payloadText back
  // (idempotent re-prepare), and the historical `{...payload, siteId}`
  // second construction is gone. After this point the caller's original
  // object is never read again: the request payload, the authorization
  // binding input, and the expected readback are all this one frozen
  // snapshot plus its immutable payloadText.
  const { snapshot, payloadText } = prepareStableCreatePayload('product', payload, siteId);
  const actionClient = await requireClient({ client, siteKey, runtime, request, authorizationContext });
  let reconciledCreatedProductId = null;
  const result = await runActionWithRecovery({
    client: actionClient,
    route: productRoute(siteKey),
    actionName: 'productCreate',
    payload: snapshot,
    payloadText,
    expected: snapshot,
    operation: 'product:create',
    readback,
    refresh,
    maxControlledRetries,
    compare: (rawActual) => {
      reconciledCreatedProductId = null;
      if (rawActual === null || rawActual === undefined) return { ok: false, exactAbsence: true, mismatches: ['created product is absent from readback'] };
      // B2 readback stabilization (same rule as article create): one
      // synchronous descriptor-only capture; the canonical comparison and
      // every caller getter consume this SAME stable copy, so a getter/proxy
      // readback can never serve comparison A and ID extraction B.
      let actual;
      try {
        actual = captureStableReadback(rawActual, 'created product readback');
      } catch (stableError) {
        return { ok: false, exactAbsence: false, mismatches: [`created product readback could not be captured as stable plain data (${stableError.message})`] };
      }
      const mismatches = [];
      let createdProductId = null;
      let createdProductSiteId = null;
      let afterProductIds = [];
      // P0-3.3a.3: the canonical expected comparison is irreplaceable
      // bottom-layer logic (shared with article create). The record is
      // extracted here (raw record or the known {record, afterProductIds}
      // host wrapper) and compared against the prepared snapshot over
      // PRODUCT_CREATE_CONTRACT_FIELDS + siteId with no caller-supplied
      // predicate anywhere on this channel. A custom `match` can only AND an
      // additional constraint on top of this PASS, so a permissive `match`
      // alone can never wave a drifted record through.
      const canonicalProblems = createdRecordExpectedProblems(
        extractCreateReadbackRecord(actual),
        snapshot,
        PRODUCT_CREATE_CONTRACT_FIELDS,
        'product',
      );
      if (canonicalProblems.length > 0) {
        mismatches.push(`created product did not match the canonical expected readback: ${canonicalProblems.join('; ')}`);
      }
      if (match !== undefined && match !== null) {
        try {
          if (!match(actual, snapshot)) mismatches.push('created product did not match the additional expected constraints');
        } catch (error) {
          mismatches.push(`created product additional match failed: ${error.message}`);
        }
      }
      try {
        createdProductId = asNonEmptyString(getCreatedProductId(actual), 'created product ID');
        reconciledCreatedProductId = createdProductId;
      } catch (error) {
        mismatches.push('created product ID is missing from readback');
      }
      try {
        createdProductSiteId = asNonEmptyString(getCreatedProductSiteId(actual), 'created product siteId');
      } catch (error) {
        mismatches.push('created product siteId is missing from readback');
      }
      try {
        afterProductIds = normalizeIdArray(getAfterProductIds(actual));
      } catch (error) {
        mismatches.push(error.message);
      }
      const newProductIds = afterProductIds.filter((id) => !knownProductIds.has(id));
      if (createdProductSiteId && createdProductSiteId !== siteId) mismatches.push('created product belongs to a different site');
      if (newProductIds.length !== 1) mismatches.push(`expected exactly one new product ID after create, found ${newProductIds.length}`);
      if (createdProductId && knownProductIds.has(createdProductId)) mismatches.push('readback ID already existed before create');
      if (createdProductId && newProductIds.length === 1 && createdProductId !== newProductIds[0]) {
        mismatches.push('created product ID does not match the sole before/after snapshot difference');
      }
      return { ok: mismatches.length === 0, exactAbsence: false, mismatches: [...new Set(mismatches)] };
    },
  });
  return { ...result, createdProductId: reconciledCreatedProductId };
}

function normalizeIdArray(value) {
  if (!Array.isArray(value)) throw new Error('product ID snapshot must be an array');
  return value.map((id) => asNonEmptyString(id, 'productId'));
}

// FROZEN test/diagnostic-only facade (2026-09-04 poisoning fix): mutation
// throws TypeError in ESM strict mode and can never affect the lexical
// functions or the named imports from content-mutation-primitives.mjs above.
export const _internal = Object.freeze({
  productRoute,
  normalizeSpecifications,
  normalizeMediaUploadItem,
  normalizeMediaUploadItemList,
  // P0-A: the authorized injected-client wrapper is the security-critical seam
  // (every underlying send re-validates the exact binding). Exposed for direct
  // transport-level tests (per-retry re-validation, expiry across a second
  // send) that the no-retry public product paths cannot reach on their own.
  requireClient,
  // P0-3.3a.3 shared canonical create-comparison internal (consumed by the
  // host driver's desired-state strict field validation).
  PRODUCT_CREATE_CONTRACT_FIELDS,
});
