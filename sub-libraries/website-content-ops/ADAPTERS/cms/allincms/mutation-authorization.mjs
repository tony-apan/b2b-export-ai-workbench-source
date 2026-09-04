import { createHash } from 'node:crypto';

export const ALLINCMS_MUTATION_AUTHORIZATION_VERSION = 1;
export const ALLINCMS_MUTATION_AUTHORIZATION_TTL_MS = 30 * 60 * 1000;
export const ARTICLE_IMAGE_DRAFT_OPERATION = 'allincms.article.update-with-images';
const AI_OR_SYSTEM_ACTOR = /\b(ai|assistant|agent|bot|codex|claude|system|unknown)\b/i;

function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  throw new Error('Mutation authorization target contains a non-canonical JSON value');
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function nonEmptyString(value, label) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} is required`);
  return value.trim();
}

function safeSiteKey(value) {
  const siteKey = nonEmptyString(value, 'siteKey');
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(siteKey)) throw new Error('siteKey must be a single safe route segment');
  return siteKey;
}

function canonicalTimestamp(value, label) {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed) || new Date(parsed).toISOString() !== value) {
    throw new Error(`${label} must be a canonical ISO-8601 UTC timestamp`);
  }
  return parsed;
}

export function computeAllinCmsMutationTargetDigest(target) {
  if (!target || typeof target !== 'object' || Array.isArray(target) || Object.keys(target).length === 0) {
    throw new Error('Mutation authorization target must be a non-empty object');
  }
  return sha256(Buffer.from(canonicalJson(target), 'utf8'));
}

// Create-action payload digest input (2026-09-04 stable create payload B2):
// when the caller carries the prepared immutable payloadText, the digest is
// the SHA-256 of exactly those UTF-8 bytes — the same string the native wire
// body embeds as `[${payloadText}]` — and payloadText must equal the canonical
// JSON serialization of the exact payload object, so the digest input and the
// wire body can never diverge. Callers without a payloadText (update/delete
// actions and legacy create bindings) keep hashing canonicalJson(payload).
function createPayloadDigestInput(body, payloadText, actionName) {
  const canonical = canonicalJson(body);
  if (payloadText === undefined) return canonical;
  if (typeof payloadText !== 'string') {
    throw new Error(`${actionName} payloadText must be an immutable string when provided`);
  }
  if (payloadText !== canonical) {
    throw new Error(`${actionName} payloadText must equal the canonical JSON serialization of the exact create payload (digest input and wire body must not diverge)`);
  }
  return payloadText;
}

export function deriveAllinCmsMutationBinding({ siteKey, route, actionName, payload, payloadText }) {
  const key = safeSiteKey(siteKey);
  const body = payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {};
  let operation;
  let target;
  if (actionName === 'postUpdate') {
    if (!['update', 'publish', 'unpublish'].includes(body.mode)) throw new Error('postUpdate mutation requires update, publish, or unpublish mode');
    operation = `allincms.article.${body.mode}`;
    target = { site_id: nonEmptyString(body.siteId, 'payload.siteId'), post_id: nonEmptyString(body.postId, 'payload.postId') };
  } else if (actionName === 'postCreate') {
    operation = 'allincms.article.create-draft';
    target = { site_id: nonEmptyString(body.siteId, 'payload.siteId'), payload_digest: sha256(Buffer.from(createPayloadDigestInput(body, payloadText, 'postCreate'), 'utf8')) };
  } else if (actionName === 'postDelete') {
    operation = 'allincms.article.delete';
    target = { site_id: nonEmptyString(body.siteId, 'payload.siteId'), post_id: nonEmptyString(body.id, 'payload.id') };
  } else if (actionName === 'siteCreate') {
    operation = 'allincms.site.create';
    target = {
      name: nonEmptyString(body.name, 'payload.name'),
      ...(body.description !== undefined ? { description: body.description } : {}),
    };
  } else if (actionName === 'productCreate') {
    operation = 'allincms.product.create';
    target = { site_id: nonEmptyString(body.siteId, 'payload.siteId'), payload_digest: sha256(Buffer.from(createPayloadDigestInput(body, payloadText, 'productCreate'), 'utf8')) };
  } else if (actionName === 'productUpdate') {
    if (!['update', 'publish', 'unpublish'].includes(body.mode)) throw new Error('productUpdate mutation requires update, publish, or unpublish mode');
    operation = `allincms.product.${body.mode}`;
    target = { site_id: nonEmptyString(body.siteId, 'payload.siteId'), product_id: nonEmptyString(body.productId, 'payload.productId') };
  } else {
    const match = /^(category|tag)(Create|Update|Delete)$/.exec(actionName || '');
    if (!match) throw new Error(`Unsupported AllinCMS mutation actionName: ${actionName ?? 'missing'}`);
    const type = match[1];
    const action = match[2].toLowerCase();
    operation = `allincms.taxonomy.${type}.${action}`;
    target = action === 'create'
      ? { site_id: nonEmptyString(body.siteId, 'payload.siteId'), slug: nonEmptyString(body.slug, 'payload.slug') }
      : { site_id: nonEmptyString(body.siteId, 'payload.siteId'), id: nonEmptyString(body.id, 'payload.id') };
  }
  return { siteKey: key, route: nonEmptyString(route, 'route'), operation, target };
}

export function validateAllinCmsMutationAuthorizationContext(authorizationContext, {
  expectedSiteKey,
  operation,
  target,
  now = Date.now(),
}) {
  if (!authorizationContext || typeof authorizationContext !== 'object' || Array.isArray(authorizationContext)) {
    throw new Error('Explicit structured authorizationContext is required before any AllinCMS mutation request');
  }
  const requiredKeys = [
    'authorization_context_version', 'site_key', 'operation',
    'target_digest_algorithm', 'target_digest',
    'approval_actor', 'approval_actor_type', 'approval_identity_status',
    'approved_at', 'expires_at',
  ];
  if (JSON.stringify(Object.keys(authorizationContext).sort()) !== JSON.stringify([...requiredKeys].sort())) {
    throw new Error(`authorizationContext must contain exactly: ${requiredKeys.join(', ')}`);
  }
  if (authorizationContext.authorization_context_version !== ALLINCMS_MUTATION_AUTHORIZATION_VERSION) {
    throw new Error(`authorizationContext.authorization_context_version must be ${ALLINCMS_MUTATION_AUTHORIZATION_VERSION}`);
  }
  if (authorizationContext.site_key !== safeSiteKey(expectedSiteKey)) {
    throw new Error('authorizationContext.site_key must exactly match the requested AllinCMS site');
  }
  if (authorizationContext.operation !== nonEmptyString(operation, 'operation')) {
    throw new Error(`authorizationContext.operation must exactly match ${operation}`);
  }
  if (authorizationContext.target_digest_algorithm !== 'sha256-canonical-json-v1') {
    throw new Error('authorizationContext.target_digest_algorithm must be sha256-canonical-json-v1');
  }
  if (!/^[a-f0-9]{64}$/.test(authorizationContext.target_digest || '')) {
    throw new Error('authorizationContext.target_digest must be 64 lowercase hexadecimal characters');
  }
  if (authorizationContext.target_digest !== computeAllinCmsMutationTargetDigest(target)) {
    throw new Error('authorizationContext.target_digest does not match the exact mutation target');
  }
  const actor = typeof authorizationContext.approval_actor === 'string' ? authorizationContext.approval_actor.trim() : '';
  if (!actor || AI_OR_SYSTEM_ACTOR.test(actor)) throw new Error('authorizationContext.approval_actor must be a named non-AI approval actor');
  if (authorizationContext.approval_actor_type !== 'human-asserted') throw new Error('authorizationContext.approval_actor_type must be human-asserted');
  if (authorizationContext.approval_identity_status !== 'not_verified') throw new Error('authorizationContext.approval_identity_status must remain not_verified');
  const approvedAt = canonicalTimestamp(authorizationContext.approved_at, 'authorizationContext.approved_at');
  const expiresAt = canonicalTimestamp(authorizationContext.expires_at, 'authorizationContext.expires_at');
  if (approvedAt > now) throw new Error('authorizationContext.approved_at must not be in the future');
  if (expiresAt <= approvedAt || expiresAt - approvedAt > ALLINCMS_MUTATION_AUTHORIZATION_TTL_MS) {
    throw new Error('authorizationContext.expires_at must be after approved_at and no more than 30 minutes later');
  }
  if (now >= expiresAt) throw new Error('authorizationContext has expired; obtain fresh explicit approval');
  return authorizationContext;
}

export function createAllinCmsMutationAuthorizationContext({
  siteKey,
  operation,
  target,
  approvalActor,
  approvedAt = new Date().toISOString(),
  expiresAt = new Date(Date.parse(approvedAt) + ALLINCMS_MUTATION_AUTHORIZATION_TTL_MS).toISOString(),
}) {
  const context = {
    authorization_context_version: ALLINCMS_MUTATION_AUTHORIZATION_VERSION,
    site_key: safeSiteKey(siteKey),
    operation: nonEmptyString(operation, 'operation'),
    target_digest_algorithm: 'sha256-canonical-json-v1',
    target_digest: computeAllinCmsMutationTargetDigest(target),
    approval_actor: nonEmptyString(approvalActor, 'approvalActor'),
    approval_actor_type: 'human-asserted',
    approval_identity_status: 'not_verified',
    approved_at: approvedAt,
    expires_at: expiresAt,
  };
  validateAllinCmsMutationAuthorizationContext(context, {
    expectedSiteKey: context.site_key,
    operation: context.operation,
    target,
    now: Date.parse(approvedAt),
  });
  return Object.freeze(context);
}

export function createAllinCmsArticleImageAuthorizationContext({ siteKey, postId, approvalActor, approvedAt, expiresAt }) {
  return createAllinCmsMutationAuthorizationContext({
    siteKey,
    operation: ARTICLE_IMAGE_DRAFT_OPERATION,
    target: { post_id: nonEmptyString(postId, 'postId') },
    approvalActor,
    approvedAt,
    expiresAt,
  });
}
