/**
 * AllinCMS product lifecycle operations.
 *
 * This module follows the same contract-driven pattern as article-operations.mjs.
 * It never stores or invents action IDs, router trees, deployment IDs or entity IDs.
 * The caller must supply a current runtime contract from the authenticated deployment.
 */
import { createAllinCmsActionClient, runActionWithRecovery } from './article-operations.mjs';

export const WORKSPACE_ORIGIN = 'https://workspace.laicms.com';
export const PRODUCT_MODES = Object.freeze(['update', 'publish', 'unpublish']);
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

async function requireClient({ client, siteKey, runtime, request, authorizationContext }) {
  if (!client) {
    return createAllinCmsActionClient({ siteKey, runtime, request, authorizationContext });
  }
  if (typeof client.send !== 'function') throw new Error('AllinCMS action client is required');
  return { send: (details) => client.send(details) };
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
  siteId, payload = { siteId }, expected, readback, refresh, beforeProductIds,
  getCreatedProductId, getCreatedProductSiteId, getAfterProductIds,
  match, maxControlledRetries = 1,
}) {
  siteId = assertSiteId(siteId);
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('product create payload must be an object');
  if (Object.hasOwn(payload, 'siteId') && payload.siteId !== siteId) throw new Error('product create payload.siteId must match siteId');
  if (typeof readback !== 'function') throw new Error('readback callback is required');
  if (typeof getCreatedProductId !== 'function') throw new Error('getCreatedProductId callback is required');
  if (typeof getCreatedProductSiteId !== 'function') throw new Error('getCreatedProductSiteId callback is required');
  if (typeof getAfterProductIds !== 'function') throw new Error('getAfterProductIds callback is required');
  if (!Array.isArray(beforeProductIds)) throw new Error('beforeProductIds snapshot is required');
  const knownProductIds = new Set(normalizeIdArray(beforeProductIds));
  const actionClient = await requireClient({ client, siteKey, runtime, request, authorizationContext });
  const matcher = match || ((actual) => Boolean(actual && (!expected || JSON.stringify(actual) === JSON.stringify(expected))));
  let reconciledCreatedProductId = null;
  const result = await runActionWithRecovery({
    client: actionClient,
    route: productRoute(siteKey),
    actionName: 'productCreate',
    payload: { ...payload, siteId },
    expected,
    operation: 'product:create',
    readback,
    refresh,
    maxControlledRetries,
    compare: (actual) => {
      reconciledCreatedProductId = null;
      if (actual === null || actual === undefined) return { ok: false, exactAbsence: true, mismatches: ['created product is absent from readback'] };
      const mismatches = [];
      let createdProductId = null;
      let createdProductSiteId = null;
      let afterProductIds = [];
      try {
        if (!matcher(actual)) mismatches.push('created product did not match expected readback');
      } catch (error) {
        mismatches.push(`created product matcher failed: ${error.message}`);
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

export const _internal = {
  productRoute,
  normalizeSpecifications,
  normalizeMediaUploadItem,
  normalizeMediaUploadItemList,
};
