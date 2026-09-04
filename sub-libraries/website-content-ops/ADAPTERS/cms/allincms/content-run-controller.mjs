import { createHash, randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateContentOperationPlan } from '../../../scripts/validate-content-operation-plan.mjs';
import { validateRuntimeScopeBinding, validateTaskRuntimePath } from '../../../scripts/runtime-scope.mjs';
import { validateJsonSchema, validateJsonSchemaDefinition } from '../../../scripts/json-schema-lite.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const evidenceSchema = JSON.parse(readFileSync(join(here, 'live-run-evidence.schema.json'), 'utf8'));
const interfaceRegistry = JSON.parse(readFileSync(join(here, 'interface-registry.json'), 'utf8'));
const verificationContract = JSON.parse(readFileSync(join(here, 'verification-evidence-contract.json'), 'utf8'));
const evidenceSchemaProblems = validateJsonSchemaDefinition(evidenceSchema);
const boundary = 'This evidence proves only controller-local ordering, checks and supplied authoritative readbacks; it does not by itself prove browser login, remote truth, frontend correctness, SEO, inquiry or conversion.';
const forbiddenRuntimeKeys = new Set([
  'actionid', 'serveractionid', 'nextactionid', 'deploymentid',
  'cookie', 'setcookie', 'session', 'sessionid', 'password', 'secret', 'apikey',
  'token', 'accesstoken', 'refreshtoken', 'authorization',
]);
const sha256Pattern = /^sha256:[a-f0-9]{64}$/;
const routeByKey = new Map(interfaceRegistry.capability_routes.map((route) => [`${route.entity_type}:${route.action}`, route]));
const verificationProfileByCapability = new Map(verificationContract.profiles.map((profile) => [profile.capability_id, profile]));
const readOnlyVerificationProfileByIntent = new Map((verificationContract.read_only_profiles ?? []).map((profile) => [profile.intent, profile]));
const verificationCheckById = new Map(verificationContract.check_definitions.map((check) => [check.check_id, check]));

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function digest(value) { return `sha256:${createHash('sha256').update(stable(value)).digest('hex')}`; }
function bytesDigest(value) { return `sha256:${createHash('sha256').update(value).digest('hex')}`; }
function timestamp(clock) { return new Date(clock()).toISOString(); }
function handlerKey(operation) { return `${operation.entity_type}:${operation.intent}`; }
function safeErrorMessage(error) {
  const message = error instanceof Error ? error.message : String(error ?? 'unknown error');
  return message
    .replace(/\bBearer\s+[^\s,;]+/gi, 'Bearer [REDACTED]')
    .replace(/\b(?:cookie|set-cookie|authorization)\s*:[^\n]*/gi, '[REDACTED HEADER]')
    .replace(/\b(?:cookie|session(?:[_-]?id)?|password|secret|api[_-]?key|token|access[_-]?token|refresh[_-]?token|authorization|action[_-]?id|server[_-]?action[_-]?id|next[_-]?action[_-]?id|deployment[_-]?id)\b\s*[=:]\s*(?:["'][^"']*["']|[^\s,;}]+)/gi, (match) => `${match.split(/[=:]/, 1)[0].trim()}=[REDACTED]`)
    .slice(0, 500);
}
function deepFreeze(value) {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  Object.freeze(value);
  for (const child of Object.values(value)) deepFreeze(child);
  return value;
}
function operationSubject(plan, operation) {
  return {
    operation_id: operation.operation_id,
    entity_ref: operation.entity_ref,
    entity_type: operation.entity_type,
    intent: operation.intent,
    identity: operation.identity,
    field_refs: operation.field_refs,
    publication_effect: operation.publication_effect,
    capability_ref: operation.capability_ref,
    expected_current_fingerprint: operation.expected_current_fingerprint,
    dependencies: operation.dependencies,
    desired_entity: plan.desired_state.find((entity) => entity.entity_ref === operation.entity_ref),
  };
}

function operationSubjectDigest(plan, operation) { return digest(operationSubject(plan, operation)); }

function planExactEntityId(operation) {
  return typeof operation.identity?.id === 'string' && operation.identity.id.trim() !== '' ? operation.identity.id : null;
}

// article:create and product:create are the only intents whose runtime entity ID
// must come from the execute result itself: the entity does not exist before the
// request, so no plan identity can name it and a readback alone cannot prove the
// verified record is the one this operation created.
function createRequiresExecuteEntityId(operation) {
  return operation.intent === 'create' && (operation.entity_type === 'article' || operation.entity_type === 'product');
}

function blankOperationEvidence(operation, plan, clock) {
  const runtimeEntityId = planExactEntityId(operation);
  return {
    operation_id: operation.operation_id,
    entity_ref: operation.entity_ref,
    entity_type: operation.entity_type,
    intent: operation.intent,
    capability_ref: operation.capability_ref,
    request_summary_digest: operationSubjectDigest(plan, operation),
    runtime_entity_id: runtimeEntityId,
    runtime_entity_id_source: runtimeEntityId === null ? 'unresolved' : 'plan_exact_id',
    preflight: {
      checked_at: timestamp(clock),
      plan_digest: plan.plan_digest,
      target_scope: plan.authorization_scope.target_scope,
      target_key: plan.authorization_scope.target_key,
      deployment_fingerprint: plan.cms_adapter.deployment_fingerprint,
      capability_ref: operation.capability_ref,
      authorization_expires_at: plan.authorization_scope.expires_at,
      expected_current_fingerprint: operation.expected_current_fingerprint,
      observed_current_fingerprint: null,
    },
    started_at: timestamp(clock),
    completed_at: null,
    status: 'preflight_passed',
    transport: { request_started: false, status: 'not_started', entity_id: null },
    reconciliation: { performed: false, verdict: 'not_needed', authoritative: false, evidence_ref: null },
    readback: { performed: false, authoritative: false, passed: false, requirements: [], evidence_ref: null, checks: [] },
    failure_code: null,
    failure_message: null,
  };
}

export function validateAllinCmsLiveRunEvidence(evidence) {
  const problems = evidenceSchemaProblems.map((problem) => `schema definition: ${problem}`);
  for (const problem of validateJsonSchema(evidence, evidenceSchema)) problems.push(`schema: ${problem}`);
  const binding = validateRuntimeScopeBinding(evidence);
  problems.push(...binding.problems);
  const taskRoot = binding.expected?.task_root;
  for (const [index, row] of (evidence?.operations ?? []).entries()) {
    for (const [field, value] of [['reconciliation.evidence_ref', row?.reconciliation?.evidence_ref], ['readback.evidence_ref', row?.readback?.evidence_ref]]) {
      if (value !== null) problems.push(...validateTaskRuntimePath(value, taskRoot, `$.operations[${index}].${field}`));
    }
    const checks = row?.readback?.checks ?? [];
    for (const [checkIndex, check] of checks.entries()) {
      problems.push(...validateTaskRuntimePath(check?.artifact_ref, taskRoot, `$.operations[${index}].readback.checks[${checkIndex}].artifact_ref`));
      if (check?.site_key !== evidence?.target?.key) problems.push(`$.operations[${index}].readback.checks[${checkIndex}] site_key must match evidence target`);
      if (check?.site_id !== evidence?.target?.id) problems.push(`$.operations[${index}].readback.checks[${checkIndex}] site_id must match evidence target`);
      if (check?.entity_ref !== row?.entity_ref) problems.push(`$.operations[${index}].readback.checks[${checkIndex}] entity_ref must match operation evidence`);
      if (check?.subject_digest !== row?.request_summary_digest) problems.push(`$.operations[${index}].readback.checks[${checkIndex}] subject_digest must match request_summary_digest`);
      const observedAt = Date.parse(check?.observed_at);
      if (!Number.isFinite(observedAt) || observedAt < Date.parse(row?.started_at) || (row?.completed_at !== null && observedAt > Date.parse(row.completed_at))) problems.push(`$.operations[${index}].readback.checks[${checkIndex}] observed_at must be inside the operation evidence window`);
    }
    if (row?.status === 'readback_passed') {
      if (!(row.readback?.performed === true && row.readback?.authoritative === true && row.readback?.passed === true && row.completed_at !== null)) problems.push(`$.operations[${index}] readback_passed requires completed authoritative readback evidence`);
      if ((row.runtime_entity_id === null || row.runtime_entity_id === undefined) !== (row.runtime_entity_id_source === 'unresolved')) problems.push(`$.operations[${index}] runtime_entity_id and runtime_entity_id_source must agree`);
      if (typeof row.runtime_entity_id !== 'string' || row.runtime_entity_id.trim() === '') problems.push(`$.operations[${index}] readback_passed requires a non-null runtime_entity_id (identity-bound PASS)`);
      const requirements = row.readback?.requirements ?? [];
      const checkIds = checks.map((check) => check?.check_id);
      if (checks.length === 0) problems.push(`$.operations[${index}] readback_passed requires structured verification checks`);
      if (stable([...requirements].sort()) !== stable([...checkIds].sort())) problems.push(`$.operations[${index}] readback requirements and structured check IDs must match exactly`);
      const readOnlyProfile = readOnlyVerificationProfileByIntent.get(row.intent);
      const route = routeByKey.get(`${row.entity_type}:${row.intent}`);
      const mutationProfile = route ? verificationProfileByCapability.get(route.capability_id) : null;
      const profile = readOnlyProfile ?? mutationProfile;
      if (readOnlyProfile) {
        if (row.intent === 'noop' && row.transport?.request_started === true) {
          problems.push(`$.operations[${index}] noop evidence must not claim a remote request`);
        }
        if (row.reconciliation?.performed === true) {
          problems.push(`$.operations[${index}] ${row.intent} read-only evidence must not claim write reconciliation`);
        }
      } else if (!mutationProfile || route.execution_surface !== 'full_source_checkout') {
        problems.push(`$.operations[${index}] readback_passed mutation has no authoritative verification profile`);
      }
      if (profile && stable([...requirements].sort()) !== stable([...profile.required_check_ids].sort())) {
        problems.push(`$.operations[${index}] readback requirements must exactly match authoritative verification profile`);
      }
      for (const [checkIndex, check] of checks.entries()) {
        const definition = verificationCheckById.get(check?.check_id);
        if (!definition) problems.push(`$.operations[${index}].readback.checks[${checkIndex}] check_id is not defined by the verification contract`);
        else if (check?.evidence_kind !== definition.evidence_kind) problems.push(`$.operations[${index}].readback.checks[${checkIndex}] evidence_kind must match the verification contract`);
      }
      if (new Set(checks.map((check) => check?.entity_id)).size !== 1) problems.push(`$.operations[${index}] structured checks must bind one exact entity ID`);
      if (checks.some((check) => check?.entity_id !== row.runtime_entity_id)) problems.push(`$.operations[${index}] readback checks must bind exactly the operation runtime_entity_id, not merely agree with each other`);
      for (const group of [
        ['media.persisted_url', 'media.anonymous_https_get', 'media.image_decode'],
        ['article.public_url', 'article.anonymous_frontend_detail', 'article.visible_content_and_media'],
      ]) {
        const urls = checks.filter((check) => group.includes(check?.check_id)).map((check) => check?.observations?.resource_url);
        if (urls.length > 1 && new Set(urls).size !== 1) problems.push(`$.operations[${index}] verification resource URLs drift for ${group[0]}`);
      }
    }
    if (['blocked', 'failed', 'ambiguous'].includes(row?.status) && (!row.failure_code || !row.failure_message || row.completed_at === null)) problems.push(`$.operations[${index}] terminal failure status requires failure details and completed_at`);
  }
  const operationIds = (evidence?.operations ?? []).map((row) => row?.operation_id);
  if (new Set(operationIds).size !== operationIds.length) problems.push('operation evidence IDs must be unique');
  if (evidence?.current_operation_id !== null && !operationIds.includes(evidence.current_operation_id)) problems.push('current_operation_id must reference a recorded operation');
  if (evidence?.status === 'completed') {
    if (evidence.current_operation_id !== null || evidence.completed_at === null) problems.push('completed evidence requires current_operation_id=null and completed_at');
    if ((evidence.operations ?? []).some((row) => row.status !== 'readback_passed')) problems.push('completed evidence requires every operation to pass authoritative readback');
  }
  return { ok: problems.length === 0, problems };
}

function forbiddenRuntimeKey(name) {
  const normalized = name.toLowerCase().replace(/[-_]/g, '');
  return forbiddenRuntimeKeys.has(normalized)
    || normalized.endsWith('actionid')
    || normalized.endsWith('deploymentid')
    || normalized.endsWith('token')
    || normalized.endsWith('cookie');
}

function assertNoForbiddenRuntimeFields(value, path = 'runtime value', seen = new Set()) {
  if (!value || (typeof value !== 'object' && typeof value !== 'function') || seen.has(value)) return;
  seen.add(value);
  for (const [name, child] of Object.entries(value)) {
    if (forbiddenRuntimeKey(name)) throw new Error(`${path}.${name} must not expose dynamic Action IDs, deployment IDs, credentials, or authorization material`);
    assertNoForbiddenRuntimeFields(child, `${path}.${name}`, seen);
  }
}

function isolatedReadbacks(readbacks) {
  return new Map([...readbacks].map(([key, value]) => [key, deepFreeze(structuredClone(value))]));
}

function assertHandler(handler, key, operation) {
  if (!handler || typeof handler !== 'object' || Array.isArray(handler)) throw new Error(`Missing handler for ${key}`);
  assertNoForbiddenRuntimeFields(handler, `handlers.${key}`);
  if (typeof handler.readback !== 'function') throw new Error(`Handler ${key} requires a readback function`);
  if (operation.intent !== 'noop' && typeof handler.execute !== 'function') throw new Error(`Handler ${key} requires an execute function`);
}

function validateOperationRoutes(plan) {
  const problems = [];
  for (const operation of plan.operations) {
    if (!operation.mutation) {
      const profile = readOnlyVerificationProfileByIntent.get(operation.intent);
      if (!profile) {
        problems.push(`${operation.operation_id} has no authoritative read-only verification profile for ${operation.intent}`);
      } else if (stable([...operation.readback_requirements].sort()) !== stable([...profile.required_check_ids].sort())) {
        problems.push(`${operation.operation_id} readback_requirements must exactly match authoritative read-only profile ${operation.intent}`);
      }
      continue;
    }
    const routeKey = `${operation.entity_type}:${operation.intent}`;
    const route = routeByKey.get(routeKey);
    if (!route) {
      problems.push(`${operation.operation_id} has no allowlisted AllinCMS capability route for ${routeKey}`);
      continue;
    }
    if (!['canonical', 'supported'].includes(route.availability)
        || route.execution_gate !== 'fresh_live_verified_current_deployment'
        || route.execution_surface !== 'full_source_checkout'
        || route.controller_interface_id !== 'allincms.content-run-controller.run-allin-cms-content-plan') {
      problems.push(`${operation.operation_id} route ${route.capability_id} is ${route.availability}/${route.execution_gate}/${route.execution_surface} and is not executable by the generic content controller`);
      continue;
    }
    const profile = verificationProfileByCapability.get(route.capability_id);
    if (!profile) {
      problems.push(`${operation.operation_id} route ${route.capability_id} has no authoritative verification profile`);
      continue;
    }
    if (stable([...operation.readback_requirements].sort()) !== stable([...profile.required_check_ids].sort())) {
      problems.push(`${operation.operation_id} readback_requirements must exactly match authoritative profile ${route.capability_id}`);
    }
  }
  return problems;
}

function verifyPreflight(plan, operation, observed) {
  if (!observed || observed.login_status !== 'authenticated') throw new Error('login_required');
  assertNoForbiddenRuntimeFields(observed, 'preflight result');
  if (observed.current_fingerprint !== undefined && observed.current_fingerprint !== null && !sha256Pattern.test(observed.current_fingerprint)) throw new Error('invalid_current_fingerprint');
  if (observed.deployment_fingerprint !== plan.cms_adapter.deployment_fingerprint) throw new Error('deployment_fingerprint_mismatch');
  if (!Array.isArray(observed.capability_ids) || !observed.capability_ids.includes(operation.capability_ref)) throw new Error(`capability_not_current:${operation.capability_ref}`);
  if (plan.plan_phase === 'site_bootstrap') {
    if (observed.account_user_id !== plan.site_selector.account_user_id) throw new Error('account_target_mismatch');
  } else {
    if (observed.site_key !== plan.site_selector.site_key) throw new Error('site_target_mismatch');
    if (plan.site_selector.site_id !== null && observed.site_id !== plan.site_selector.site_id) throw new Error('site_id_mismatch');
  }
}

function verificationArtifactEnvelope(check) {
  return {
    schema_version: '1.0',
    check_id: check.check_id,
    evidence_kind: check.evidence_kind,
    captured_at: check.observed_at,
    site_key: check.site_key,
    site_id: check.site_id,
    entity_ref: check.entity_ref,
    entity_id: check.entity_id,
    subject_digest: check.subject_digest,
    method: check.method,
    observed_result: check.observed_result,
    observations: check.observations,
  };
}

function artifactBytes(value) {
  if (typeof value === 'string') return Buffer.from(value);
  if (Buffer.isBuffer(value)) return value;
  if (value instanceof Uint8Array) return Buffer.from(value);
  throw new Error('verification_artifact_bytes_required');
}

function exactHttpsUrl(value, checkId) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !url.hostname) throw new Error();
    return url;
  } catch {
    throw new Error(`verification_https_url_invalid:${checkId}`);
  }
}

async function verifyVerificationCheck(plan, operation, check, taskRoot, readEvidenceArtifact, operationStartedAt, checkedAt, runtimeEntityId) {
  if (!check || typeof check !== 'object' || Array.isArray(check)) throw new Error('verification_check_invalid');
  const definition = verificationCheckById.get(check.check_id);
  if (!definition) throw new Error(`verification_check_unknown:${check.check_id}`);
  if (check.evidence_kind !== definition.evidence_kind) throw new Error(`verification_evidence_kind_mismatch:${check.check_id}`);
  if (check.passed !== true) throw new Error(`verification_check_not_passed:${check.check_id}`);
  if (check.artifact_media_type !== 'application/json') throw new Error(`verification_primary_artifact_must_be_json:${check.check_id}`);
  if (check.site_key !== plan.site_selector.site_key) throw new Error(`verification_site_mismatch:${check.check_id}`);
  if (check.site_id !== plan.site_selector.site_id) throw new Error(`verification_site_id_mismatch:${check.check_id}`);
  if (check.entity_ref !== operation.entity_ref) throw new Error(`verification_entity_mismatch:${check.check_id}`);
  if (typeof check.entity_id !== 'string' || check.entity_id.trim() === '') throw new Error(`verification_entity_id_missing:${check.check_id}`);
  if (runtimeEntityId !== null && check.entity_id !== runtimeEntityId) throw new Error(`verification_entity_id_mismatch:${check.check_id}`);
  if (!sha256Pattern.test(check.artifact_digest) || !sha256Pattern.test(check.subject_digest)) throw new Error(`verification_digest_invalid:${check.check_id}`);
  if (check.subject_digest !== operationSubjectDigest(plan, operation)) throw new Error(`verification_subject_digest_mismatch:${check.check_id}`);
  const observedAt = Date.parse(check.observed_at);
  if (!Number.isFinite(observedAt)) throw new Error(`verification_observed_at_invalid:${check.check_id}`);
  if (observedAt < Date.parse(operationStartedAt) || observedAt > Date.parse(checkedAt)) throw new Error(`verification_observed_at_outside_operation:${check.check_id}`);
  const pathProblems = validateTaskRuntimePath(check.artifact_ref, taskRoot, `verification_check:${check.check_id}.artifact_ref`);
  if (pathProblems.length > 0) throw new Error(pathProblems.join('; '));
  const o = check.observations;
  if (!o || typeof o !== 'object' || Array.isArray(o)) throw new Error(`verification_observations_invalid:${check.check_id}`);
  if (check.evidence_kind === 'backend_readback' && !(o.backend_authoritative === true && o.exact_match === true)) throw new Error(`backend_readback_not_authoritative_exact:${check.check_id}`);
  if (check.evidence_kind === 'concurrency_match' && !(o.backend_authoritative === true && o.exact_match === true && o.current_fingerprint === operation.expected_current_fingerprint)) throw new Error(`expected_current_fingerprint_not_proven:${check.check_id}`);
  if (check.evidence_kind === 'duplicate_exclusion' && !(o.backend_authoritative === true && o.duplicate_count === 0)) throw new Error(`duplicate_exclusion_not_proven:${check.check_id}`);
  if (check.evidence_kind === 'editor_reopen' && !(o.editor_healthy === true && o.exact_match === true)) throw new Error(`editor_reopen_not_healthy:${check.check_id}`);
  if (check.evidence_kind === 'anonymous_resource' && !(o.anonymous === true && o.http_status === 200)) throw new Error(`anonymous_resource_not_proven:${check.check_id}`);
  if (check.evidence_kind === 'anonymous_frontend' && !(o.anonymous === true && o.http_status === 200 && o.exact_match === true)) throw new Error(`anonymous_frontend_not_proven:${check.check_id}`);
  if (check.evidence_kind === 'image_fetch_decode' && !(o.anonymous === true && o.http_status === 200 && o.decoded === true && /^image\//i.test(o.content_type ?? ''))) throw new Error(`image_decode_not_proven:${check.check_id}`);
  if (check.check_id === 'article.visible_content_and_media' && o.media_applicable === true && o.decoded !== true) throw new Error('article_required_media_decode_not_proven');
  if (['anonymous_resource', 'anonymous_frontend', 'image_fetch_decode'].includes(check.evidence_kind) || check.check_id === 'media.persisted_url') exactHttpsUrl(o.resource_url, check.check_id);

  const rawArtifact = artifactBytes(await readEvidenceArtifact({ path: check.artifact_ref, check: structuredClone(check), operation, plan, runtime_entity_id: runtimeEntityId }));
  if (bytesDigest(rawArtifact) !== check.artifact_digest) throw new Error(`verification_artifact_digest_mismatch:${check.check_id}`);
  let parsedArtifact;
  try { parsedArtifact = JSON.parse(rawArtifact.toString('utf8')); }
  catch { throw new Error(`verification_artifact_json_invalid:${check.check_id}`); }
  if (stable(parsedArtifact) !== stable(verificationArtifactEnvelope(check))) throw new Error(`verification_artifact_envelope_mismatch:${check.check_id}`);
}

async function verifyReadback(plan, operation, readback, taskRoot, readEvidenceArtifact, operationStartedAt, checkedAt, runtimeEntityId) {
  if (!readback || readback.authoritative !== true || readback.ok !== true) throw new Error('authoritative_readback_failed');
  assertNoForbiddenRuntimeFields(readback, 'readback result');
  const requirements = Array.isArray(readback.requirements) ? readback.requirements : [];
  if (requirements.length === 0 || requirements.some((value) => typeof value !== 'string' || value.trim() === '') || new Set(requirements).size !== requirements.length) throw new Error('readback_requirements_invalid');
  if (stable([...requirements].sort()) !== stable([...operation.readback_requirements].sort())) throw new Error('readback_requirements_must_exactly_match_plan');
  const pathProblems = validateTaskRuntimePath(readback.evidence_ref, taskRoot, 'readback.evidence_ref');
  if (pathProblems.length > 0) throw new Error(pathProblems.join('; '));
  if (!Array.isArray(readback.checks) || readback.checks.length === 0) throw new Error('structured_verification_checks_required');
  const checkIds = readback.checks.map((check) => check?.check_id);
  if (checkIds.some((checkId) => typeof checkId !== 'string' || checkId.trim() === '') || new Set(checkIds).size !== checkIds.length) throw new Error('verification_check_ids_invalid');
  if (stable([...checkIds].sort()) !== stable([...operation.readback_requirements].sort())) throw new Error('verification_checks_must_exactly_match_plan');
  for (const check of readback.checks) await verifyVerificationCheck(plan, operation, check, taskRoot, readEvidenceArtifact, operationStartedAt, checkedAt, runtimeEntityId);
  if (new Set(readback.checks.map((check) => check.entity_id)).size !== 1) throw new Error('verification_entity_id_drift');
  if (runtimeEntityId !== null && readback.checks.some((check) => check.entity_id !== runtimeEntityId)) throw new Error('verification_entity_id_mismatch:runtime_entity_id');
  for (const group of [
    ['media.persisted_url', 'media.anonymous_https_get', 'media.image_decode'],
    ['article.public_url', 'article.anonymous_frontend_detail', 'article.visible_content_and_media'],
  ]) {
    const urls = readback.checks.filter((check) => group.includes(check.check_id)).map((check) => check.observations.resource_url);
    if (urls.length > 1 && new Set(urls).size !== 1) throw new Error(`verification_resource_url_drift:${group[0]}`);
  }
}
export async function runAllinCmsContentPlan({
  plan,
  handlers,
  preflight,
  writeEvidence,
  readEvidenceArtifact,
  evidencePath,
  clock = () => Date.now(),
  runId = `ACRUN-${randomUUID()}`,
}) {
  const initialNow = new Date(clock());
  const initialValidation = validateContentOperationPlan(plan, { now: initialNow });
  if (!initialValidation.ok || !initialValidation.executionReady) {
    return { ok: false, status: 'blocked', code: 'PLAN_NOT_EXECUTION_READY', problems: initialValidation.problems, evidence: null };
  }
  if (plan.cms_adapter?.id !== 'allincms') return { ok: false, status: 'blocked', code: 'ADAPTER_MISMATCH', problems: ['cms_adapter.id must be allincms'], evidence: null };
  const routeProblems = validateOperationRoutes(plan);
  if (routeProblems.length > 0) return { ok: false, status: 'blocked', code: 'CAPABILITY_ROUTE_BLOCK', problems: routeProblems, evidence: null };
  if (typeof preflight !== 'function' || typeof writeEvidence !== 'function' || typeof readEvidenceArtifact !== 'function') {
    return { ok: false, status: 'blocked', code: 'CONTROLLER_DEPENDENCY_MISSING', problems: ['preflight, writeEvidence and readEvidenceArtifact are mandatory'], evidence: null };
  }

  const snapshot = deepFreeze(structuredClone(plan));
  const runtimeBinding = validateRuntimeScopeBinding(snapshot);
  const taskRoot = runtimeBinding.expected.task_root;
  const evidencePathProblems = validateTaskRuntimePath(evidencePath, taskRoot, 'evidencePath');
  if (evidencePathProblems.length > 0 || !snapshot.verification_plan.evidence_targets.includes(evidencePath)) {
    return { ok: false, status: 'blocked', code: 'EVIDENCE_PATH_OUT_OF_SCOPE', problems: [...evidencePathProblems, 'evidencePath must be declared in verification_plan.evidence_targets'], evidence: null };
  }

  const evidence = {
    schema_version: '1.1', run_id: runId,
    client_id: snapshot.client_id, company_id: snapshot.company_id, task_id: snapshot.task_id,
    runtime_scope: snapshot.runtime_scope,
    plan_id: snapshot.plan_id, plan_digest: snapshot.plan_digest,
    target: { scope: snapshot.authorization_scope.target_scope, key: snapshot.authorization_scope.target_key, id: snapshot.plan_phase === 'site_operation' ? snapshot.site_selector.site_id : null },
    started_at: timestamp(clock), completed_at: null, status: 'running', current_operation_id: null,
    operations: [], boundary,
  };

  const persist = async () => {
    const validation = validateAllinCmsLiveRunEvidence(evidence);
    if (!validation.ok) throw new Error(`live_run_evidence_invalid:${validation.problems.join('; ')}`);
    const result = await writeEvidence({ path: evidencePath, evidence: structuredClone(evidence) });
    if (!result || result.ok !== true || result.evidence_ref !== evidencePath) throw new Error('evidence_write_not_confirmed');
  };
  const stop = async (status, code, message, row = null) => {
    if (row) {
      row.status = status;
      row.completed_at = timestamp(clock);
      row.failure_code = code;
      row.failure_message = safeErrorMessage(message);
    }
    evidence.status = status;
    evidence.completed_at = timestamp(clock);
    try { await persist(); }
    catch (error) {
      return { ok: false, status, code: 'EVIDENCE_WRITE_FAILED', original_code: code, problems: [safeErrorMessage(message), safeErrorMessage(error)], evidence };
    }
    return { ok: false, status, code, problems: [safeErrorMessage(message)], evidence };
  };

  try { await persist(); }
  catch (error) { return { ok: false, status: 'failed', code: 'EVIDENCE_WRITE_FAILED', problems: [safeErrorMessage(error)], evidence }; }

  const priorReadbacks = new Map();
  // Runtime identities are keyed by entity_ref and only recorded after that
  // entity's authoritative readback passed; a later operation for the same
  // entity_ref may reuse the verified ID but never blindly inherits whatever
  // identity the previous operation happened to carry.
  const runtimeIdentitiesByEntityRef = new Map();
  for (const operation of snapshot.operations) {
    evidence.current_operation_id = operation.operation_id;
    const row = blankOperationEvidence(operation, snapshot, clock);
    evidence.operations.push(row);

    const currentValidation = validateContentOperationPlan(snapshot, { now: new Date(clock()) });
    if (!currentValidation.ok || !currentValidation.executionReady || currentValidation.digest !== snapshot.plan_digest) {
      return stop('blocked', 'AUTHORIZATION_OR_PLAN_DRIFT', currentValidation.problems.join('; ') || 'plan authorization drift', row);
    }

    let observed;
    try {
      const rawObserved = await preflight({ plan: snapshot, operation, priorReadbacks: isolatedReadbacks(priorReadbacks) });
      verifyPreflight(snapshot, operation, rawObserved);
      observed = deepFreeze(structuredClone(rawObserved));
      row.preflight.observed_current_fingerprint = observed.current_fingerprint ?? null;
    } catch (error) {
      return stop('blocked', 'PREFLIGHT_BLOCK', error, row);
    }

    const key = handlerKey(operation);
    let handler;
    try { handler = handlers?.[key]; assertHandler(handler, key, operation); }
    catch (error) { return stop('blocked', 'HANDLER_BLOCK', error, row); }

    const verifiedEntityId = runtimeIdentitiesByEntityRef.get(operation.entity_ref) ?? null;
    if (verifiedEntityId !== null && row.runtime_entity_id !== null && row.runtime_entity_id !== verifiedEntityId) {
      return stop('blocked', 'RUNTIME_IDENTITY_CONFLICT', `plan exact ID ${row.runtime_entity_id} conflicts with the readback-verified runtime ID ${verifiedEntityId} for ${operation.entity_ref}`, row);
    }
    if (verifiedEntityId !== null && row.runtime_entity_id === null) {
      row.runtime_entity_id = verifiedEntityId;
      row.runtime_entity_id_source = 'authoritative_readback';
    }

    // The runtime identity context must be rebuilt at every handler call, never
    // captured once before execute: a create binds runtime_entity_id from its
    // execute result after the request, so a pre-execute snapshot would hand
    // readback (and any later handler stage) a stale null identity.
    const runtimeEntityContext = () => ({
      runtime_entity_id: row.runtime_entity_id,
      runtime_entity_id_source: row.runtime_entity_id_source,
    });

    for (const dependency of operation.dependencies) {
      if (!priorReadbacks.has(dependency)) return stop('blocked', 'DEPENDENCY_READBACK_MISSING', `dependency ${dependency} has no authoritative readback`, row);
    }

    if (operation.expected_current_fingerprint !== null) {
      if (typeof handler.readCurrent !== 'function') return stop('blocked', 'CURRENT_FINGERPRINT_READER_MISSING', `Handler ${key} requires readCurrent`, row);
      try {
        const current = await handler.readCurrent({ plan: snapshot, operation, observed, priorReadbacks: isolatedReadbacks(priorReadbacks), ...runtimeEntityContext() });
        assertNoForbiddenRuntimeFields(current, 'readCurrent result');
        row.preflight.observed_current_fingerprint = current?.fingerprint ?? null;
        if (!sha256Pattern.test(current?.fingerprint ?? '') || current.fingerprint !== operation.expected_current_fingerprint) throw new Error('expected_current_fingerprint_mismatch');
      } catch (error) { return stop('blocked', 'CURRENT_FINGERPRINT_BLOCK', error, row); }
    }

    try { await persist(); }
    catch (error) { return { ok: false, status: 'failed', code: 'EVIDENCE_WRITE_FAILED', problems: [safeErrorMessage(error)], evidence }; }

    const executeValidation = validateContentOperationPlan(snapshot, { now: new Date(clock()) });
    if (!executeValidation.ok || !executeValidation.executionReady || executeValidation.digest !== snapshot.plan_digest) {
      return stop('blocked', 'AUTHORIZATION_EXPIRED_BEFORE_REQUEST', executeValidation.problems.join('; ') || 'authorization or capability snapshot expired before request', row);
    }

    let transport = { request_started: false, status: 'not_started' };
    let handlerOutputContractViolation = null;
    if (operation.intent !== 'noop') {
      try {
        transport = await handler.execute({
          plan: snapshot, operation, observed, priorReadbacks: isolatedReadbacks(priorReadbacks), ...runtimeEntityContext(),
          authorization: Object.freeze({
            plan_id: snapshot.plan_id, plan_digest: snapshot.plan_digest,
            operation_id: operation.operation_id, target_scope: snapshot.authorization_scope.target_scope,
            target_key: snapshot.authorization_scope.target_key, actor: snapshot.authorization_scope.actor,
            approved_at: snapshot.authorization_scope.approved_at, expires_at: snapshot.authorization_scope.expires_at,
          }),
        });
        try { assertNoForbiddenRuntimeFields(transport, 'transport result'); }
        catch (error) {
          // Locked own data property: the catch below reads the own descriptor,
          // so a polluted prototype accessor can never lie about this value.
          Object.defineProperty(error, 'requestStarted', {
            value: transport?.request_started !== false,
            writable: false,
            enumerable: false,
            configurable: false,
          });
          error.handlerOutputContractViolation = true;
          throw error;
        }
        row.transport.request_started = transport?.request_started === true;
        row.transport.status = ['completed', 'failed', 'unknown', 'not_started'].includes(transport?.status)
          ? transport.status
          : (row.transport.request_started ? 'unknown' : 'not_started');
        row.transport.entity_id = typeof transport?.entity_id === 'string' && transport.entity_id.trim() !== '' ? transport.entity_id : null;
      } catch (error) {
        if (error?.handlerOutputContractViolation === true) handlerOutputContractViolation = error;
        // Own-descriptor read with a fail-safe default: a missing own property
        // means "the request may have started" (read-only reconciliation), and
        // a polluted prototype accessor can never produce a false here — an
        // own accessor's descriptor value is undefined, which also means true.
        row.transport.request_started = error !== null && typeof error === 'object'
          ? Object.getOwnPropertyDescriptor(error, 'requestStarted')?.value !== false
          : true;
        row.transport.status = row.transport.request_started ? 'unknown' : 'failed';
        transport = { error };
      }
    }

    const transportCompleted = operation.intent === 'noop'
      || (row.transport.request_started === true && row.transport.status === 'completed');
    if (!transportCompleted) {
      if (!row.transport.request_started) return stop('failed', 'REQUEST_NOT_STARTED', transport?.error ?? `transport status ${row.transport.status}`, row);
      if (!operation.mutation) return stop('failed', 'READ_OPERATION_FAILED', transport?.error ?? `read-only transport status ${row.transport.status}`, row);
      row.status = 'request_started';
      if (typeof handler.reconcile !== 'function') return stop('ambiguous', 'RECONCILIATION_HANDLER_MISSING', 'request may have started and no read-only reconcile handler exists', row);
      let reconciliation;
      try {
        reconciliation = await handler.reconcile({ plan: snapshot, operation, observed, priorReadbacks: isolatedReadbacks(priorReadbacks), ...runtimeEntityContext() });
        assertNoForbiddenRuntimeFields(reconciliation, 'reconciliation result');
      } catch (error) { return stop('ambiguous', 'RECONCILIATION_FAILED', error, row); }
      const reconciliationRef = reconciliation?.evidence_ref ?? null;
      const reconciliationPathProblems = reconciliationRef === null ? ['reconciliation evidence_ref is required'] : validateTaskRuntimePath(reconciliationRef, taskRoot, 'reconciliation.evidence_ref');
      row.reconciliation = {
        performed: true,
        verdict: ['applied', 'not_applied'].includes(reconciliation?.verdict) ? reconciliation.verdict : 'unknown',
        authoritative: reconciliation?.authoritative === true,
        evidence_ref: reconciliationPathProblems.length === 0 ? reconciliationRef : null,
      };
      if (!row.reconciliation.authoritative || reconciliationPathProblems.length > 0 || row.reconciliation.verdict === 'unknown') return stop('ambiguous', 'AMBIGUOUS_WRITE', reconciliationPathProblems.join('; ') || 'read-only reconciliation remained unknown', row);
      if (row.reconciliation.verdict === 'not_applied') return stop('failed', 'WRITE_CONFIRMED_NOT_APPLIED', 'read-only reconciliation confirmed the write was not applied; no automatic retry is allowed', row);
    }

    if (createRequiresExecuteEntityId(operation)) {
      if (row.transport.entity_id === null) {
        return stop('blocked', 'CREATE_RUNTIME_ENTITY_ID_MISSING', `${operation.entity_type}:create transport completed without a non-empty entity_id; the request may have succeeded, so the run fails closed and automatic retry is forbidden`, row);
      }
      if (row.runtime_entity_id !== null && row.runtime_entity_id !== row.transport.entity_id) {
        return stop('blocked', 'CREATE_RUNTIME_ENTITY_ID_CONFLICT', `${operation.entity_type}:create execute returned entity_id ${row.transport.entity_id} but the operation was already bound to runtime ID ${row.runtime_entity_id}; fail closed without retry`, row);
      }
      row.runtime_entity_id = row.transport.entity_id;
      row.runtime_entity_id_source = 'execute_result';
    }

    let readback;
    try {
      readback = await handler.readback({ plan: snapshot, operation, observed, priorReadbacks: isolatedReadbacks(priorReadbacks), ...runtimeEntityContext() });
      await verifyReadback(snapshot, operation, readback, taskRoot, readEvidenceArtifact, row.started_at, timestamp(clock), row.runtime_entity_id);
    } catch (error) { return stop('failed', 'AUTHORITATIVE_READBACK_FAILED', error, row); }

    if (operation.intent !== 'noop') {
      row.transport.request_started = true;
      if (row.transport.status !== 'completed') row.transport.status = 'unknown';
    }
    row.readback = {
      performed: true, authoritative: true, passed: true,
      requirements: [...readback.requirements], evidence_ref: readback.evidence_ref,
      checks: structuredClone(readback.checks),
    };
    // A natural-key identity (or a create that only reconciled ambiguously) resolves
    // exclusively from the authoritative readback checks that just passed; an
    // already-bound runtime ID (plan exact, execute result or inherited verified
    // ID) was enforced to equal every check inside verifyReadback.
    if (row.runtime_entity_id === null) {
      row.runtime_entity_id = readback.checks[0].entity_id;
      row.runtime_entity_id_source = 'authoritative_readback';
    }
    runtimeIdentitiesByEntityRef.set(operation.entity_ref, row.runtime_entity_id);
    row.status = 'readback_passed';
    row.completed_at = timestamp(clock);
    priorReadbacks.set(operation.operation_id, deepFreeze(structuredClone(readback)));
    if (handlerOutputContractViolation) {
      return stop('blocked', 'HANDLER_OUTPUT_CONTRACT_VIOLATION_APPLIED', handlerOutputContractViolation, row);
    }
    try { await persist(); }
    catch (error) { return { ok: false, status: 'failed', code: 'EVIDENCE_WRITE_FAILED', problems: [safeErrorMessage(error)], evidence }; }
  }

  evidence.current_operation_id = null;
  evidence.status = 'completed';
  evidence.completed_at = timestamp(clock);
  try { await persist(); }
  catch (error) { return { ok: false, status: 'failed', code: 'EVIDENCE_WRITE_FAILED', problems: [safeErrorMessage(error)], evidence }; }
  return { ok: true, status: 'completed', code: 'ALLINCMS_CONTENT_RUN_COMPLETED', evidence, readbacks: priorReadbacks };
}
