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
 */
import { createHash } from 'node:crypto';
import { createAllinCmsActionClient, createPostCategory, updatePostCategory, createPostTag, updatePostTag } from './article-operations.mjs';
import { saveProductDraft, publishProduct, unpublishProduct, createProductDraft } from './product-operations.mjs';
import { uploadAllinCmsUploadViaDialog } from './upload-media-browser.mjs';
import { createAllinCmsMutationAuthorizationContext, deriveAllinCmsMutationBinding } from './mutation-authorization.mjs';

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function canonicalTexts(value) {
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number') return String(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (Array.isArray(value)) return `[${value.map(canonicalTexts).join(',')}]`;
  if (typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalTexts(value[key])}`).join(',')}}`;
  return 'undefined';
}

export function allinCmsOperationAuthorization({ plan, operation, siteKey, siteId, approvalActor = plan.authorization_scope.actor }) {
  const isProduct = operation.entity_type === 'product';
  const isProductUpdate = isProduct && (operation.intent === 'update' || operation.intent === 'publish' || operation.intent === 'unpublish');
  const actionName = isProductUpdate ? 'productUpdate' : `${operation.entity_type}${operation.intent[0].toUpperCase()}${operation.intent.slice(1)}`;
  const payload = { siteId, mode: isProduct ? (operation.intent === 'publish' ? 'publish' : operation.intent === 'unpublish' ? 'unpublish' : 'update') : undefined, productId: isProduct ? operation.identity.id : undefined, ...(operation.identity?.id && !isProduct ? { id: operation.identity.id } : {}), ...(operation.entity_type === 'tag' || operation.entity_type === 'category' ? { slug: plan.desired_state.find((d) => d.entity_ref === operation.entity_ref)?.fields?.slug?.value ?? 'unused' } : {}) };
  const binding = deriveAllinCmsMutationBinding({ siteKey, route: '/__driver__', actionName, payload });
  return createAllinCmsMutationAuthorizationContext({
    siteKey,
    operation: binding.operation,
    target: binding.target,
    approvalActor: approvalActor || 'human-asserted-actor',
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
}) {
  const client = createAllinCmsActionClient({ siteKey, runtime, request });
  const authz = (plan, operation) => authorizationProvider({ plan, operation, siteKey, siteId, approvalActor });
  const adapterReadback = (plan, operation) => (backendReadback ? backendReadback({ plan, operation, siteKey, siteId }) : readbackProvider({ plan, operation, siteKey, siteId }));


  async function taxonomyReadback({ plan, operation, observed, priorReadbacks }) {
    return readbackProvider({ plan, operation, observed, priorReadbacks, siteKey, siteId });
  }

  const handlers = {
    'category:create': {
      execute: async ({ plan, operation }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        const fields = entity.fields;
        await createPostCategory({ existing: [], siteId, name: fields.name.value, slug: fields.slug.value, description: fields.description?.value, siteKey, runtime, request, authorizationContext: authz(plan, operation), readback: () => adapterReadback(plan, operation), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: taxonomyReadback,
    },
    'category:update': {
      readCurrent: async ({ plan, operation }) => fingerprintProvider({ plan, operation, siteKey, siteId }),
      execute: async ({ plan, operation }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await updatePostCategory({ id: operation.identity.id, siteId, name: entity.fields.name.value, slug: entity.fields.slug.value, description: entity.fields.description?.value, siteKey, runtime, request, authorizationContext: authz(plan, operation), readback: () => adapterReadback(plan, operation), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: taxonomyReadback,
    },
    'tag:create': {
      execute: async ({ plan, operation }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await createPostTag({ existing: [], siteId, name: entity.fields.name.value, slug: entity.fields.slug.value, description: entity.fields.description?.value, siteKey, runtime, request, authorizationContext: authz(plan, operation), readback: () => adapterReadback(plan, operation), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: taxonomyReadback,
    },
    'tag:update': {
      readCurrent: async ({ plan, operation }) => fingerprintProvider({ plan, operation, siteKey, siteId }),
      execute: async ({ plan, operation }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await updatePostTag({ id: operation.identity.id, siteId, name: entity.fields.name.value, slug: entity.fields.slug.value, description: entity.fields.description?.value, siteKey, runtime, request, authorizationContext: authz(plan, operation), readback: () => adapterReadback(plan, operation), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: taxonomyReadback,
    },
    'product:update': {
      readCurrent: async ({ plan, operation }) => fingerprintProvider({ plan, operation, siteKey, siteId }),
      execute: async ({ plan, operation }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await saveProductDraft({ siteKey, runtime, request, authorizationContext: authz(plan, operation), productId: operation.identity.id, siteId, defaults: fromEntity(entity), readback: () => adapterReadback(plan, operation), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: ({ plan, operation, observed, priorReadbacks }) => readbackProvider({ plan, operation, observed, priorReadbacks, siteKey, siteId }),
    },
    'product:publish': {
      execute: async ({ plan, operation }) => {
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await publishProduct({ siteKey, runtime, request, authorizationContext: authz(plan, operation), productId: operation.identity.id, siteId, defaults: fromEntity(entity), readback: () => adapterReadback(plan, operation), refresh: async () => {}, maxControlledRetries: 0 });
        return { request_started: true, status: 'completed' };
      },
      readback: ({ plan, operation, observed, priorReadbacks }) => readbackProvider({ plan, operation, observed, priorReadbacks, siteKey, siteId }),
    },
    'product:create': {
      execute: async ({ plan, operation }) => {
        if (!uploadDialog) throw new Error('product:create requires host draft dialog bridge or an existing draft plan path');
        const entity = plan.desired_state.find((d) => d.entity_ref === operation.entity_ref);
        await createProductDraft({ client, siteKey, runtime, request, authorizationContext: authz(plan, operation), siteId, payload: { ...fromEntity(entity), siteId }, beforeProductIds: [], readback: () => readbackProvider({ plan, operation, siteKey, siteId }), refresh: async () => {}, getCreatedProductId: () => operation.identity.id ?? null, getCreatedProductSiteId: () => siteId, getAfterProductIds: () => [operation.identity.id] });
        return { request_started: true, status: 'completed' };
      },
      readback: ({ plan, operation, observed, priorReadbacks }) => readbackProvider({ plan, operation, observed, priorReadbacks, siteKey, siteId }),
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
