/**
 * AllinCMS canonical content-plan host driver.
 *
 * Wires the canonical `runAllinCmsContentPlan` controller (content-run-controller.mjs)
 * to this adapter's operation modules. The host supplies transports and evidence
 * persistence; the driver supplies plan-consistent handler semantics:
 *
 *   handlers["entity_type:intent"] = { execute, readback, readCurrent?, reconcile? }
 *
 * - `execute(...)` returns `{ request_started, status }` and MUST have performed the
 *   mutation through `allinCms` operations bound to the host `request` callback;
 *   article:create and product:create additionally return the unified
 *   `{ request_started, status, entity_id }` transport contract so the controller
 *   can bind the final backend/editor/frontend evidence to the exact created ID;
 * - handler contexts carry `runtime_entity_id`/`runtime_entity_id_source` resolved
 *   by the controller (plan exact ID, execute result, or a readback-verified ID
 *   saved for the same entity_ref). article/product update, publish and unpublish
 *   execute paths prefer that verified runtime ID over a plan natural-key
 *   placeholder; standalone exact-ID operations are unchanged;
 * - `readback(...)` MUST return `{ requirements, evidence_ref, checks }` with
 *   checks matching `verification-evidence-contract.json` check semantics (the
 *   controller re-validates requirements against profiles and artifact digests);
 * - `readCurrent(...)` returns `{ fingerprint }` (sha256:64hex) for update intents;
 * - `reconcile(...)` returns `{ performed, verdict: 'applied'|'not_applied',
 *   authoritative, evidence_ref }` and must be read-only.
 *
 * The driver never stores action IDs, router trees or deployment IDs; hosts supply a
 * `runtime` contract captured from the authenticated deployment (see AI-START-HERE.md
 * sections 0 and "内容变更授权入口").
 *
 * article:create additionally fails closed unless the host supplies real providers:
 * `articleBeforePostIdsProvider` (duplicate-free same-site before snapshot taken inside
 * execute before the request), `articleCreateReadbackProvider` ({ record, afterPostIds }
 * from the authoritative backend), and `articleEditorReopenProvider` ({ status,
 * authenticated, healthy, postId } from actually reopening the created editor).
 * product:create follows the same rule with `productBeforeProductIdsProvider` and
 * `productCreateReadbackProvider`; an upload dialog is not a create precondition.
 * The driver never fabricates entity IDs or empty ID lists.
 *
 * article:create and product:create additionally bind expected full-field
 * readback (P0-3.3a): the operation must resolve exactly one desired_state
 * entity by entity_ref with a matching entity_type, every contract field
 * (8 article / 10 product fields) must be an own wrapper with an own value
 * (no `??` defaults), and the one outgoing payload (fields + siteId) is
 * prepared through the shared prepareStableCreatePayload (2026-09-04 stable
 * create payload B1) — a synchronous descriptor-only stable copy that is
 * deep-frozen and branded with its canonical payloadText — before any await,
 * provider call, or authorization. That same branded snapshot plus its
 * immutable payloadText are the request payload, the authorization digest
 * input (hashed over the exact UTF-8 payloadText), the native wire body
 * (`[payloadText]`), and the expected readback value, so plan mutations after
 * the prepare cannot desynchronize the digest, the wire body, or the verified
 * expectation, and the bottom layer's idempotent re-prepare hands back this
 * exact object. The strict actual record comparison (P0-3.3a.3) is owned by
 * the bottom layer itself: the driver passes no matcher callback at all, and
 * createPostDraft/createProductDraft capture the readback as stable data and
 * run their own irreplaceable canonical comparison, so no caller predicate
 * can replace or waive it.
 */
import { createHash } from 'node:crypto';
import {
  _internal as articleInternal,
  createPostCategory,
  createPostDraft,
  createPostTag,
  publishPost,
  savePostDraft,
  updatePostCategory,
  updatePostTag,
} from './article-operations.mjs';
import { _internal as productInternal, createProductDraft, publishProduct, saveProductDraft, unpublishProduct } from './product-operations.mjs';
import { uploadAllinCmsUploadViaDialog } from './upload-media-browser.mjs';
import { createAllinCmsMutationAuthorizationContext, deriveAllinCmsMutationBinding } from './mutation-authorization.mjs';
// 2026-09-04 stable create payload B1: the driver and the article/product
// bottom create functions share the exact same prepare function (named ESM
// import, immutable binding), so the driver-side and bottom-layer payloads,
// validations, and payload texts can never drift apart.
import { prepareStableCreatePayload } from './content-mutation-primitives.mjs';

// P0-3.3a.3: the canonical create contract field lists (8 article / 10
// product) and the comparison canonical text come from the bottom operation
// modules via the registered `_internal` bindings, so desired-state validation
// and the bottom-layer readback comparison can never drift apart.
const { ARTICLE_CREATE_CONTRACT_FIELDS, canonicalTexts } = articleInternal;
const { PRODUCT_CREATE_CONTRACT_FIELDS } = productInternal;

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function requireUniqueDesiredEntity(plan, operation) {
  const entityType = operation.entity_type;
  const entityRef = operation.entity_ref;
  if (!Array.isArray(plan?.desired_state)) {
    throw new Error(`${entityType}:create requires plan.desired_state to be an array (got ${plan?.desired_state === null ? 'null' : typeof plan?.desired_state}); ambiguous desired state is refused before any request`);
  }
  const matches = plan.desired_state.filter((row) => row?.entity_ref === entityRef);
  if (matches.length === 0) {
    throw new Error(`${entityType}:create entity_ref ${JSON.stringify(entityRef)} matches no desired_state entity; ambiguous desired state is refused before any request`);
  }
  if (matches.length > 1) {
    throw new Error(`${entityType}:create entity_ref ${JSON.stringify(entityRef)} matches ${matches.length} desired_state entities; ambiguous desired state is refused before any request`);
  }
  const entity = matches[0];
  if (entity.entity_type !== entityType) {
    throw new Error(`${entityType}:create entity_ref ${JSON.stringify(entityRef)} resolved a desired_state entity of entity_type ${JSON.stringify(entity.entity_type)}; entity_type mismatch is refused before any request`);
  }
  return entity;
}

// P0-3.3a expected full-field binding: article and product create operations
// own an exact persisted-field contract (ARTICLE_CREATE_CONTRACT_FIELDS /
// PRODUCT_CREATE_CONTRACT_FIELDS imported from the bottom operation modules —
// the same constants the bottom layer compares readbacks against). Every
// contract field must arrive as an own desired_state field wrapper carrying an
// own value; partial, wrapper-less, defaulted, or entity_ref-ambiguous desired
// states are refused before any provider call or request (`??`-filled defaults
// are forbidden on the create path; the update path keeps its own merge
// semantics).
function strictCreateFieldValues(entity, contractFields, kind) {
  const wrappers = entity?.fields;
  if (!wrappers || typeof wrappers !== 'object' || Array.isArray(wrappers)) {
    throw new Error(`${kind} create desired_state entity must carry a fields object (got ${wrappers === null || wrappers === undefined ? String(wrappers) : typeof wrappers})`);
  }
  const values = {};
  for (const field of contractFields) {
    if (!Object.hasOwn(wrappers, field)) {
      throw new Error(`${kind} create desired state is missing the contract field ${field}: all ${contractFields.length} fields [${contractFields.join(', ')}] must be own field wrappers with own values, and missing fields are never defaulted`);
    }
    const wrapper = wrappers[field];
    if (!wrapper || typeof wrapper !== 'object' || Array.isArray(wrapper)) {
      throw new Error(`${kind} create desired state field ${field} must be a field wrapper object with an own value`);
    }
    if (!Object.hasOwn(wrapper, 'value')) {
      throw new Error(`${kind} create desired state field ${field} wrapper is missing its own value (defaulted values are refused before any request)`);
    }
    if (wrapper.value === undefined) {
      throw new Error(`${kind} create desired state field ${field} wrapper value is undefined (defaulted values are refused before any request)`);
    }
    values[field] = wrapper.value;
  }
  return values;
}

function articleCreatePayloadFromDesired(entity) {
  const payload = strictCreateFieldValues(entity, ARTICLE_CREATE_CONTRACT_FIELDS, 'article');
  for (const field of ['title', 'slug']) {
    if (typeof payload[field] !== 'string' || !payload[field].trim()) {
      throw new Error(`article create desired payload requires a non-empty ${field}`);
    }
  }
  return payload;
}

function articleFieldsFromEntity(entity) {
  const fields = entity?.fields || {};
  return {
    title: fields.title?.value,
    slug: fields.slug?.value,
    excerpt: fields.excerpt?.value ?? '',
    order: fields.order?.value ?? 0,
    coverImage: Object.hasOwn(fields, 'coverImage') ? fields.coverImage.value : null,
    categories: fields.categories?.value ?? [],
    tags: fields.tags?.value ?? [],
    content: fields.content?.value ?? [],
  };
}

function productCreatePayloadFromDesired(entity) {
  const payload = strictCreateFieldValues(entity, PRODUCT_CREATE_CONTRACT_FIELDS, 'product');
  for (const field of ['name', 'slug', 'description']) {
    if (typeof payload[field] !== 'string' || !payload[field].trim()) {
      throw new Error(`product create desired payload requires a non-empty ${field}`);
    }
  }
  return payload;
}

// 2026-09-04 stable create payload B1: the single outgoing create payload is
// prepared (synchronously, descriptor-only, deep-frozen, branded) from the
// strict desired-state projection BEFORE any await, provider call, or
// authorization. The bottom create functions re-prepare idempotently and get
// this exact snapshot/payloadText back, so the digest input, the wire body,
// and the expected readback all stay this one object. structuredClone (which
// invokes getters) is no longer used on this path.
function preparedCreatePayload(plan, operation, siteId, kind, buildFromDesired) {
  const entity = requireUniqueDesiredEntity(plan, operation);
  return prepareStableCreatePayload(kind, buildFromDesired(entity), siteId);
}

function normalizeIdSnapshot(value, providerLabel) {
  if (!Array.isArray(value)) throw new Error(`${providerLabel} must return an array of IDs`);
  const ids = value.map((id) => {
    if (typeof id !== 'string' || !id.trim()) throw new Error(`${providerLabel} returned an empty ID`);
    return id.trim();
  });
  if (new Set(ids).size !== ids.length) throw new Error(`${providerLabel} returned duplicate IDs`);
  return ids;
}

// Consumed by the authorization create branches: the driver create handlers
// pass the exact frozen outgoing payload so the authorization target digest
// binds the same object the request layer will send. Standalone callers that
// do not carry a frozen payload get the identical strict projection built
// here from the unique desired_state entity.
function consumedCreatePayload(createPayload, siteId, kind) {
  if (createPayload === null || createPayload === undefined) return null;
  if (!createPayload || typeof createPayload !== 'object' || Array.isArray(createPayload)) {
    throw new Error(`${kind} create authorization requires createPayload to be a non-array object when provided`);
  }
  if (createPayload.siteId !== siteId) {
    throw new Error(`${kind} create authorization createPayload.siteId must equal the operation siteId`);
  }
  return createPayload;
}

export function allinCmsOperationAuthorization({ plan, operation, siteKey, siteId, approvalActor = plan.authorization_scope.actor, runtimeEntityId = null, createPayload = null, createPayloadText = null }) {
  // The mutation authorization window is the one the approved plan froze in
  // plan.authorization_scope. The driver must never mint a fresh now-based
  // window (that would silently renew the user's approval for every
  // operation), so both timestamps are required here and passed through
  // unchanged. Expiry after provider delays is enforced by the request
  // layer's immediate validateAllinCmsMutationAuthorizationContext check.
  const approvedAt = plan.authorization_scope.approved_at;
  const expiresAt = plan.authorization_scope.expires_at;
  if (typeof approvedAt !== 'string' || approvedAt.trim() === '') {
    throw new Error('allinCmsOperationAuthorization requires plan.authorization_scope.approved_at to be a non-empty string (frozen plan approval window; the driver never mints a new one)');
  }
  if (typeof expiresAt !== 'string' || expiresAt.trim() === '') {
    throw new Error('allinCmsOperationAuthorization requires plan.authorization_scope.expires_at to be a non-empty string (frozen plan approval window; the driver never mints a new one)');
  }
  const entityType = operation.entity_type;
  const intent = operation.intent;
  const isArticle = entityType === 'article';
  const isArticleCreate = isArticle && intent === 'create';
  const isArticleUpdate = isArticle && (intent === 'update' || intent === 'publish');
  const isProduct = entityType === 'product';
  const isProductCreate = isProduct && intent === 'create';
  const isProductUpdate = isProduct && (intent === 'update' || intent === 'publish' || intent === 'unpublish');
  // Exact-ID mutations keep using the plan ID; a same-plan created entity uses the
  // controller-verified runtime ID so the authorization target binds the exact
  // entity the request will actually mutate.
  const mutationEntityId = typeof runtimeEntityId === 'string' && runtimeEntityId.trim() !== '' ? runtimeEntityId : operation.identity.id;
  let actionName;
  let payload;
  let payloadText;
  if (isArticleCreate) {
    // The postCreate authorization target binds the payload digest, so the
    // digest input must be the exact prepared payload createPostDraft sends.
    // The driver passes that branded frozen snapshot (plus its payloadText) as
    // createPayload/createPayloadText; it is never rebuilt here, so a plan
    // mutated after the prepare cannot change the authorized target away from
    // the outgoing body. Standalone callers without a frozen payload get the
    // identical preparation built here from the unique desired_state entity.
    actionName = 'postCreate';
    if (consumedCreatePayload(createPayload, siteId, 'article') !== null) {
      payload = createPayload;
      payloadText = typeof createPayloadText === 'string' ? createPayloadText : undefined;
    } else {
      const prepared = preparedCreatePayload(plan, operation, siteId, 'article', articleCreatePayloadFromDesired);
      payload = prepared.snapshot;
      payloadText = prepared.payloadText;
    }
  } else if (isArticleUpdate) {
    actionName = 'postUpdate';
    payload = { siteId, postId: mutationEntityId, mode: intent === 'publish' ? 'publish' : 'update' };
  } else if (isProductCreate) {
    // Same digest-binding rule as article create: the authorization payload
    // must be the exact prepared body createProductDraft sends, never a
    // rebuilt projection of a possibly-mutated plan.
    actionName = 'productCreate';
    if (consumedCreatePayload(createPayload, siteId, 'product') !== null) {
      payload = createPayload;
      payloadText = typeof createPayloadText === 'string' ? createPayloadText : undefined;
    } else {
      const prepared = preparedCreatePayload(plan, operation, siteId, 'product', productCreatePayloadFromDesired);
      payload = prepared.snapshot;
      payloadText = prepared.payloadText;
    }
  } else {
    actionName = isProductUpdate ? 'productUpdate' : `${entityType}${intent[0].toUpperCase()}${intent.slice(1)}`;
    payload = { siteId, mode: isProduct ? (intent === 'publish' ? 'publish' : intent === 'unpublish' ? 'unpublish' : 'update') : undefined, productId: isProduct ? mutationEntityId : undefined, ...(mutationEntityId && !isProduct ? { id: mutationEntityId } : {}), ...(entityType === 'tag' || entityType === 'category' ? { slug: plan.desired_state.find((d) => d.entity_ref === operation.entity_ref)?.fields?.slug?.value ?? 'unused' } : {}) };
  }
  const binding = deriveAllinCmsMutationBinding({ siteKey, route: '/__driver__', actionName, payload, payloadText });
  return createAllinCmsMutationAuthorizationContext({
    siteKey,
    operation: binding.operation,
    target: binding.target,
    approvalActor: approvalActor || 'human-asserted-actor',
    approvedAt,
    expiresAt,
  });
}

function artifactFromCheck({ entityRef, entityId, checkId, observedAt, siteKey, siteId, result, observations, subjectDigest, kind, method }) {
  const envelope = {
    schema_version: '1.0', check_id: checkId, evidence_kind: kind || 'backend_readback',
    captured_at: observedAt, site_key: siteKey, site_id: siteId, entity_ref: entityRef, entity_id: entityId,
    subject_digest: subjectDigest || `sha256:${sha256(canonicalTexts({ entity: entityRef, site: siteKey, check: checkId }))}`,
    method: method || 'controller-host-driver', observed_result: String(result), observations,
  };
  return envelope;
}

const AUTHORIZATION_WINDOW_DRIFT_CODE = 'AUTHORIZATION_WINDOW_DRIFT';
const AUTHORIZATION_CONTEXT_NOT_STABLE_DATA_CODE = 'AUTHORIZATION_CONTEXT_NOT_STABLE_DATA';

// Exactly the fields the mutation-authorization request-layer contract allows
// on an authorization context (mutation-authorization.mjs requiredKeys). The
// projection below whitelists these fields and nothing else, so an extra
// provider field can never be laundered into the context the request layer
// validates.
const AUTHORIZATION_CONTEXT_STABLE_DATA_FIELDS = [
  'authorization_context_version',
  'site_key',
  'operation',
  'target_digest_algorithm',
  'target_digest',
  'approval_actor',
  'approval_actor_type',
  'approval_identity_status',
  'approved_at',
  'expires_at',
];

function authorizationContextNotStableData(detail) {
  const error = new Error(
    `${AUTHORIZATION_CONTEXT_NOT_STABLE_DATA_CODE}: authorizationProvider must return plain stable data owning exactly [${AUTHORIZATION_CONTEXT_STABLE_DATA_FIELDS.join(', ')}] as own data properties (accessor properties, symbol keys, extra keys, and non-plain values are refused before any request): ${detail}`,
  );
  error.code = AUTHORIZATION_CONTEXT_NOT_STABLE_DATA_CODE;
  return error;
}

// Read one own DATA property of the provider-returned object. Accessor
// properties and traps that throw fail closed here: a getter could serve the
// plan window to the driver check and a fresh window to the request layer, and
// a Proxy trap failure means the value cannot be copied reliably.
function readOwnDataPropertyValue(container, key, label) {
  let descriptor;
  try {
    descriptor = Object.getOwnPropertyDescriptor(container, key);
  } catch (trapError) {
    throw authorizationContextNotStableData(`${label}: reading the own property descriptor threw (${trapError?.message})`);
  }
  if (!descriptor) {
    throw authorizationContextNotStableData(`${label}: disappeared between key enumeration and descriptor read`);
  }
  if (descriptor.get !== undefined || descriptor.set !== undefined) {
    throw authorizationContextNotStableData(`${label}: is an accessor property; only own data properties are accepted`);
  }
  return descriptor.value;
}

// Structured whitelist copy of one provider-returned value. Primitives are
// copied verbatim (never coerced, dropped or defaulted) so the downstream
// request-layer schema still sees — and rejects — the provider's exact invalid
// values; the projection must not manufacture validity. Non-plain values
// (functions, symbols, bigints, non-finite numbers, exotic objects) fail
// closed. Nested plain objects/arrays are deep-copied with the same rules, so
// a future nested target field can never share a mutable reference with the
// provider.
function copyStableAuthorizationValue(value, label) {
  if (typeof value === 'function' || typeof value === 'symbol' || typeof value === 'bigint') {
    throw authorizationContextNotStableData(`${label}: is ${typeof value} data, not plain JSON-compatible data`);
  }
  if (typeof value === 'number' && !Number.isFinite(value)) {
    throw authorizationContextNotStableData(`${label}: is a non-finite number`);
  }
  if (value === null || value === undefined || typeof value !== 'object') return value;
  let nestedKeys;
  const isArray = Array.isArray(value);
  try {
    if (isArray) {
      if (Object.getPrototypeOf(value) !== Array.prototype) throw authorizationContextNotStableData(`${label}: is an array with a non-standard prototype`);
    } else {
      const proto = Object.getPrototypeOf(value);
      if (proto !== Object.prototype && proto !== null) throw authorizationContextNotStableData(`${label}: is an object with a non-plain prototype`);
    }
    nestedKeys = Reflect.ownKeys(value);
  } catch (trapError) {
    if (trapError?.code === AUTHORIZATION_CONTEXT_NOT_STABLE_DATA_CODE) throw trapError;
    throw authorizationContextNotStableData(`${label}: enumerating nested keys threw (${trapError?.message})`);
  }
  if (isArray) {
    const indexKeys = nestedKeys.filter((key) => key !== 'length');
    const looksLikeIndices = indexKeys.every((key, index) => typeof key === 'string' && key === String(index));
    if (!looksLikeIndices || indexKeys.length !== value.length) {
      throw authorizationContextNotStableData(`${label}: is a sparse array or carries extra own keys`);
    }
    const copy = [];
    for (let index = 0; index < value.length; index += 1) {
      copy.push(copyStableAuthorizationValue(readOwnDataPropertyValue(value, String(index), `${label}[${index}]`), `${label}[${index}]`));
    }
    return copy;
  }
  const copy = {};
  for (const key of nestedKeys) {
    if (typeof key === 'symbol') throw authorizationContextNotStableData(`${label}: carries the symbol key ${String(key)}`);
    copy[key] = copyStableAuthorizationValue(readOwnDataPropertyValue(value, key, `${label}.${key}`), `${label}.${key}`);
  }
  return copy;
}

function deepFreezePlainData(value) {
  if (value !== null && typeof value === 'object') {
    for (const key of Reflect.ownKeys(value)) deepFreezePlainData(value[key]);
    Object.freeze(value);
  }
  return value;
}

// P0-3.3a.3: the create-readback comparison helpers that used to live here
// (taxonomy ID normalization, media wrapper unwrapping, and the strict
// record-vs-expected matcher) moved into the bottom operation modules
// (article-operations.mjs `createdRecordExpectedProblems` +
// `extractCreateReadbackRecord`) so the canonical expected comparison is
// irreplaceable bottom-layer logic instead of a driver-supplied
// `expectedMatch` callback. The driver passes no matcher at all.

// P0 TOCTOU closure: whatever the authorizationProvider returns (default or
// host/test-injected) may be a mutable plain object whose window strings are
// flipped to a fresh window by a microtask after the driver check, or an
// accessor/Proxy object that serves the plan window to the driver check and a
// fresh window to the request layer. The provider result is therefore never
// used downstream: it is immediately projected into a driver-owned frozen
// plain-data snapshot holding exactly the contract fields. The window equality
// check runs on that snapshot and operations only ever receive that snapshot,
// so later mutations of the provider's object cannot cross the frozen plan
// expiry. The full operation/site/target/digest schema validation stays in the
// request layer and is neither duplicated nor weakened here.
function createStableAuthorizationSnapshot(provided) {
  if (provided === null || typeof provided !== 'object' || Array.isArray(provided)) {
    throw authorizationContextNotStableData(`returned ${provided === null ? 'null' : typeof provided} instead of a plain object`);
  }
  let ownKeys;
  try {
    const proto = Object.getPrototypeOf(provided);
    if (proto !== Object.prototype && proto !== null) {
      throw authorizationContextNotStableData('the returned object has a non-plain prototype');
    }
    ownKeys = Reflect.ownKeys(provided);
  } catch (trapError) {
    if (trapError?.code === AUTHORIZATION_CONTEXT_NOT_STABLE_DATA_CODE) throw trapError;
    throw authorizationContextNotStableData(`enumerating the returned object threw (${trapError?.message})`);
  }
  for (const key of ownKeys) {
    if (typeof key === 'symbol') throw authorizationContextNotStableData(`carries the symbol key ${String(key)}`);
  }
  const expected = [...AUTHORIZATION_CONTEXT_STABLE_DATA_FIELDS].sort();
  const actual = ownKeys.map((key) => String(key)).sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw authorizationContextNotStableData(`own keys are [${actual.join(', ')}]; only the contract fields are accepted`);
  }
  const snapshot = {};
  for (const field of AUTHORIZATION_CONTEXT_STABLE_DATA_FIELDS) {
    snapshot[field] = copyStableAuthorizationValue(readOwnDataPropertyValue(provided, field, `authorizationContext.${field}`), `authorizationContext.${field}`);
  }
  return deepFreezePlainData(snapshot);
}

// P0 fail-closed window binding: whatever produced the authorization context
// (the default allinCmsOperationAuthorization or a host/test-injected
// authorizationProvider), the context's approved_at/expires_at window must be
// string-identical to the window the approved plan froze in
// plan.authorization_scope. A provider that re-mints a fresh now-based window
// (e.g. after a provider delay crossed the frozen plan expiry) is refused
// here, before any request is attempted. operation/site/target/digest
// validation stays in the request layer
// (validateAllinCmsMutationAuthorizationContext) and is not duplicated.
function assertAuthorizationWindowMatchesPlanScope(context, plan) {
  const scope = plan?.authorization_scope;
  const drifts = [];
  for (const field of ['approved_at', 'expires_at']) {
    const planValue = scope?.[field];
    const contextValue = context?.[field];
    if (typeof planValue !== 'string' || planValue.trim() === '') {
      drifts.push(`${field}: plan.authorization_scope.${field} is missing or empty`);
    } else if (typeof contextValue !== 'string' || contextValue.trim() === '') {
      drifts.push(`${field}: authorizationContext.${field} is missing or empty`);
    } else if (contextValue !== planValue) {
      drifts.push(`${field}: authorizationContext has ${JSON.stringify(contextValue)}, plan froze ${JSON.stringify(planValue)}`);
    }
  }
  if (drifts.length > 0) {
    const error = new Error(`${AUTHORIZATION_WINDOW_DRIFT_CODE}: authorization context window must exactly equal the approved plan.authorization_scope window (re-minted or drifted windows are refused before any request): ${drifts.join('; ')}`);
    error.code = AUTHORIZATION_WINDOW_DRIFT_CODE;
    throw error;
  }
  return context;
}

export function createAllinCmsPlanHandlerSet({
  siteKey,
  siteId,
  runtime,
  request,
  authorizationProvider = allinCmsOperationAuthorization,
  readbackProvider,
  fingerprintProvider,
  reconcileProvider,
  backendReadback,
  writeEvidenceArtifact,
  uploadDialog = null,
  uiFallbackApproved = false,
  approvalActor = 'human-asserted-actor',
  articleBeforePostIdsProvider = null,
  articleCreateReadbackProvider = null,
  articleEditorReopenProvider = null,
  productBeforeProductIdsProvider = null,
  productCreateReadbackProvider = null,
}) {
  const authz = (plan, operation, runtimeEntityId, createPayload = null, createPayloadText = null) => {
    const provided = authorizationProvider({ plan, operation, siteKey, siteId, approvalActor, runtimeEntityId, createPayload, createPayloadText });
    // The provider's object never flows downstream: project it synchronously
    // into a frozen plain-data snapshot, check the plan-frozen window on that
    // snapshot, and hand only the snapshot to the operation. A post-check
    // microtask mutation or an accessor/Proxy serving a fresh window to the
    // request layer can then only ever re-present the plan-frozen window,
    // which the request layer's expiry check refuses.
    const snapshot = createStableAuthorizationSnapshot(provided);
    assertAuthorizationWindowMatchesPlanScope(snapshot, plan);
    return snapshot;
  };
  const adapterReadback = (plan, operation, runtimeEntityId) => (backendReadback
    ? backendReadback({ plan, operation, siteKey, siteId, runtime_entity_id: runtimeEntityId ?? null })
    : readbackProvider({ plan, operation, siteKey, siteId, runtime_entity_id: runtimeEntityId ?? null }));


  async function taxonomyReadback({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source }) {
    return readbackProvider({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source, siteKey, siteId });
  }

  const handlers = {
    'category:create': {
      execute: async ({ plan, operation, runtime_entity_id }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        const fields = entity.fields;
        await createPostCategory({ existing: [], siteId, name: fields.name.value, slug: fields.slug.value, description: fields.description?.value, siteKey, runtime, request, authorizationContext: authz(plan, operation), readback: () => adapterReadback(plan, operation, runtime_entity_id), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: taxonomyReadback,
    },
    'category:update': {
      readCurrent: async ({ plan, operation }) => fingerprintProvider({ plan, operation, siteKey, siteId }),
      execute: async ({ plan, operation, runtime_entity_id }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await updatePostCategory({ id: operation.identity.id, siteId, name: entity.fields.name.value, slug: entity.fields.slug.value, description: entity.fields.description?.value, siteKey, runtime, request, authorizationContext: authz(plan, operation), readback: () => adapterReadback(plan, operation, runtime_entity_id), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: taxonomyReadback,
    },
    'tag:create': {
      execute: async ({ plan, operation, runtime_entity_id }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await createPostTag({ existing: [], siteId, name: entity.fields.name.value, slug: entity.fields.slug.value, description: entity.fields.description?.value, siteKey, runtime, request, authorizationContext: authz(plan, operation), readback: () => adapterReadback(plan, operation, runtime_entity_id), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: taxonomyReadback,
    },
    'tag:update': {
      readCurrent: async ({ plan, operation }) => fingerprintProvider({ plan, operation, siteKey, siteId }),
      execute: async ({ plan, operation, runtime_entity_id }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await updatePostTag({ id: operation.identity.id, siteId, name: entity.fields.name.value, slug: entity.fields.slug.value, description: entity.fields.description?.value, siteKey, runtime, request, authorizationContext: authz(plan, operation), readback: () => adapterReadback(plan, operation, runtime_entity_id), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: taxonomyReadback,
    },
    'article:create': {
      execute: async ({ plan, operation }) => {
        if (typeof articleBeforePostIdsProvider !== 'function') throw new Error('article:create requires articleBeforePostIdsProvider (a real same-site before snapshot; fabricated empty snapshots are forbidden)');
        if (typeof articleCreateReadbackProvider !== 'function') throw new Error('article:create requires articleCreateReadbackProvider (record + afterPostIds from the authoritative backend)');
        if (typeof articleEditorReopenProvider !== 'function') throw new Error('article:create requires articleEditorReopenProvider (real editor reopen evidence)');
        // P0-3.3a + 2026-09-04 stable create payload B1: prepare the one
        // outgoing payload (8 contract fields + siteId) synchronously — before
        // any await, provider call, or authorization — then reuse the same
        // branded frozen snapshot as the request payload, the authorization
        // target input (with its payloadText), and the expected readback
        // value. The bottom layer re-prepares idempotently and hands back
        // this exact object.
        const { snapshot: createPayload, payloadText: createPayloadText } = preparedCreatePayload(plan, operation, siteId, 'article', articleCreatePayloadFromDesired);
        const providerArgs = { plan, operation, siteKey, siteId };
        const beforePostIds = normalizeIdSnapshot(await articleBeforePostIdsProvider(providerArgs), 'articleBeforePostIdsProvider');
        const result = await createPostDraft({
          siteKey,
          runtime,
          request,
          authorizationContext: authz(plan, operation, null, createPayload, createPayloadText),
          siteId,
          payload: createPayload,
          expected: createPayload,
          beforePostIds,
          readback: () => articleCreateReadbackProvider(providerArgs),
          refresh: async () => {},
          getCreatedPostId: (actual) => actual?.record?.id,
          getCreatedPostSiteId: (actual) => actual?.record?.siteId,
          getAfterPostIds: (actual) => actual?.afterPostIds,
          // P0-3.3a.3: no matcher callback is passed at all. The bottom layer
          // extracts the record from the {record, afterPostIds} wrapper (or a
          // bare record) itself and runs its own irreplaceable canonical
          // comparison over ARTICLE_CREATE_CONTRACT_FIELDS + siteId, so no
          // caller predicate — permissive or strict — sits on that channel.
          editorReopen: (createdPostId) => articleEditorReopenProvider({ ...providerArgs, createdPostId }),
          maxControlledRetries: 0,
        });
        if (!['mutation_succeeded', 'reconciled_success'].includes(result.status)) {
          const detail = [result.error, ...(result.mismatches ?? [])].filter(Boolean).join('; ');
          const error = new Error(`article create not confirmed: ${result.status}${detail ? ` (${detail})` : ''}`);
          // Locked own data property: a polluted Object.prototype.requestStarted
          // accessor must never flip an already-sent ambiguity into
          // "not started" downstream (the controller reads the own descriptor).
          Object.defineProperty(error, 'requestStarted', {
            value: result.requestStarted !== false,
            writable: false,
            enumerable: false,
            configurable: false,
          });
          throw error;
        }
        return { request_started: true, status: 'completed', entity_id: result.createdPostId };
      },
      readback: ({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source }) => readbackProvider({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source, siteKey, siteId }),
    },
    'article:update': {
      readCurrent: async ({ plan, operation }) => fingerprintProvider({ plan, operation, siteKey, siteId }),
      execute: async ({ plan, operation, runtime_entity_id }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await savePostDraft({ siteKey, runtime, request, authorizationContext: authz(plan, operation, runtime_entity_id), postId: runtime_entity_id ?? operation.identity.id, siteId, defaults: articleFieldsFromEntity(entity), readback: () => adapterReadback(plan, operation, runtime_entity_id), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: ({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source }) => readbackProvider({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source, siteKey, siteId }),
    },
    'article:publish': {
      execute: async ({ plan, operation, runtime_entity_id }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await publishPost({ siteKey, runtime, request, authorizationContext: authz(plan, operation, runtime_entity_id), postId: runtime_entity_id ?? operation.identity.id, siteId, defaults: articleFieldsFromEntity(entity), readback: () => adapterReadback(plan, operation, runtime_entity_id), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: ({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source }) => readbackProvider({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source, siteKey, siteId }),
    },
    'product:update': {
      readCurrent: async ({ plan, operation }) => fingerprintProvider({ plan, operation, siteKey, siteId }),
      execute: async ({ plan, operation, runtime_entity_id }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await saveProductDraft({ siteKey, runtime, request, authorizationContext: authz(plan, operation, runtime_entity_id), productId: runtime_entity_id ?? operation.identity.id, siteId, defaults: fromEntity(entity), readback: () => adapterReadback(plan, operation, runtime_entity_id), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: ({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source }) => readbackProvider({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source, siteKey, siteId }),
    },
    'product:publish': {
      execute: async ({ plan, operation, runtime_entity_id }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await publishProduct({ siteKey, runtime, request, authorizationContext: authz(plan, operation, runtime_entity_id), productId: runtime_entity_id ?? operation.identity.id, siteId, defaults: fromEntity(entity), readback: () => adapterReadback(plan, operation, runtime_entity_id), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: ({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source }) => readbackProvider({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source, siteKey, siteId }),
    },
    'product:create': {
      execute: async ({ plan, operation }) => {
        if (typeof productBeforeProductIdsProvider !== 'function') throw new Error('product:create requires productBeforeProductIdsProvider (a real same-site before snapshot; fabricated empty snapshots are forbidden)');
        if (typeof productCreateReadbackProvider !== 'function') throw new Error('product:create requires productCreateReadbackProvider (record + afterProductIds from the authoritative backend)');
        // P0-3.3a + 2026-09-04 stable create payload B1: same single-prepared-
        // payload rule as article create (10 contract fields + siteId), built
        // synchronously before any await, provider call, or authorization.
        const { snapshot: createPayload, payloadText: createPayloadText } = preparedCreatePayload(plan, operation, siteId, 'product', productCreatePayloadFromDesired);
        const providerArgs = { plan, operation, siteKey, siteId };
        const beforeProductIds = normalizeIdSnapshot(await productBeforeProductIdsProvider(providerArgs), 'productBeforeProductIdsProvider');
        const result = await createProductDraft({
          siteKey,
          runtime,
          request,
          authorizationContext: authz(plan, operation, null, createPayload, createPayloadText),
          siteId,
          payload: createPayload,
          expected: createPayload,
          beforeProductIds,
          readback: () => productCreateReadbackProvider(providerArgs),
          refresh: async () => {},
          getCreatedProductId: (actual) => actual?.record?.id,
          getCreatedProductSiteId: (actual) => actual?.record?.siteId,
          getAfterProductIds: (actual) => actual?.afterProductIds,
          // P0-3.3a.3: same rule as article create — no matcher callback is
          // passed at all; the bottom layer owns the extraction and the
          // canonical comparison over PRODUCT_CREATE_CONTRACT_FIELDS + siteId.
          maxControlledRetries: 0,
        });
        if (!['mutation_succeeded', 'reconciled_success'].includes(result.status)) {
          const detail = [result.error, ...(result.mismatches ?? [])].filter(Boolean).join('; ');
          const error = new Error(`product create not confirmed: ${result.status}${detail ? ` (${detail})` : ''}`);
          // Locked own data property (see the article:create twin above).
          Object.defineProperty(error, 'requestStarted', {
            value: result.requestStarted !== false,
            writable: false,
            enumerable: false,
            configurable: false,
          });
          throw error;
        }
        return { request_started: true, status: 'completed', entity_id: result.createdProductId };
      },
      readback: ({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source }) => readbackProvider({ plan, operation, observed, priorReadbacks, runtime_entity_id, runtime_entity_id_source, siteKey, siteId }),
    },
    'media:create': {
      execute: async ({ plan, operation }) => {
        if (!uploadDialog) throw new Error('media:create requires host uploadDialog (runInTab) bridge');
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        const file = entity.fields.local_file?.value || entity.fields.file?.value;
        if (!file) throw new Error('media:create desired state is missing local_file/file');
        const result = await uploadDialog({ siteKey, file, uiFallbackApproved });
        if (result.status !== 'uploaded_for_dialog_driver') throw new Error(`media dialog upload not confirmed: ${result.status}`);
        return { request_started: true, status: 'completed' };
      },
      readback: ({ plan, operation, observed, priorReadbacks }) => readbackProvider({ plan, operation, observed, priorReadbacks, siteKey, siteId }),
      reconcile: reconcileProvider ? async (args) => reconcileProvider({ ...args, siteKey, siteId }) : undefined,
    },
  };

  function fromEntity(entity) {
    const fields = entity.fields || {};
    return {
      name: fields.name?.value, slug: fields.slug?.value, description: fields.description?.value,
      order: fields.order?.value ?? 0, media: fields.media?.value ?? null,
      mediaList: [], content: fields.content?.value ?? [], categories: fields.categories?.value ?? [],
      tags: fields.tags?.value ?? [], specifications: fields.specifications?.value ?? [],
    };
  }

  for (const intent of ['noop']) {
    for (const type of ['category', 'tag', 'media', 'product', 'article']) {
      handlers[`${type}:${intent}`] = {
        readback: (args) => readbackProvider({ ...args, siteKey, siteId }),
      };
    }
  }
  return handlers;
}

export { artifactFromCheck, canonicalTexts };
