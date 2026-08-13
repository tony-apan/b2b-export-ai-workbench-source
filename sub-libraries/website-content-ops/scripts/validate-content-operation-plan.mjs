#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, dirname, join } from 'node:path';
import { validateJsonSchema, validateJsonSchemaDefinition } from './json-schema-lite.mjs';
import { validateRuntimeScopeBinding, validateTaskRuntimePath } from './runtime-scope.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const schemaPath = join(here, '..', 'SCHEMAS', 'content-operation-plan.schema.json');
const entityTypes = new Set(['site', 'article', 'product', 'category', 'tag', 'media', 'theme_page']);
const facts = new Set(['confirmed', 'inferred', 'missing', 'conflicting', 'expired']);
const maturities = new Set(['live_verified_current_deployment', 'local_tested', 'exploration_only', 'unsupported']);
const forbiddenKeys = new Set([
  'action_id', 'server_action_id', 'next_action_id', 'router_tree', 'build_id', 'deployment_id',
  'cookie', 'cookies', 'authorization_header', 'access_token', 'refresh_token', 'session_token', 'bearer_token', 'jwt'
]);
const shaPattern = /^sha256:[a-f0-9]{64}$/;
const datePattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/;
const blockedFactStatuses = new Set(['missing', 'conflicting', 'expired']);
const publishableSourceClearances = new Set(['approved', 'not-applicable']);
const usableMethodClearances = new Set(['approved', 'not-applicable']);
const operationActions = new Set(['discover', 'create', 'update', 'publish', 'readback', 'delete']);
const planPhases = new Set(['site_bootstrap', 'site_operation']);
const schema = JSON.parse(readFileSync(schemaPath, 'utf8'));
const schemaDefinitionProblems = validateJsonSchemaDefinition(schema);

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

export function canonicalPlanProjection(plan) {
  const clone = structuredClone(plan);
  delete clone.plan_digest;
  if (clone.authorization_scope) {
    clone.authorization_scope = {
      target_scope: clone.authorization_scope.target_scope,
      target_key: clone.authorization_scope.target_key,
      operation_ids: clone.authorization_scope.operation_ids,
    };
  }
  return clone;
}

export function calculatePlanDigest(plan) {
  return `sha256:${createHash('sha256').update(stable(canonicalPlanProjection(plan))).digest('hex')}`;
}

function nonEmpty(value) { return typeof value === 'string' && value.trim().length > 0; }
function object(value) { return value && typeof value === 'object' && !Array.isArray(value); }
function unique(values) { return new Set(values).size === values.length; }

export function validateContentOperationPlanSchema() { return [...schemaDefinitionProblems]; }

export function validateContentOperationPlan(plan, { now = new Date() } = {}) {
  const problems = [];
  const nowMs = now instanceof Date ? now.getTime() : Date.parse(now);
  const add = (message) => problems.push(message);
  for (const issue of schemaDefinitionProblems) add(`schema definition: ${issue}`);
  if (!Number.isFinite(nowMs)) return { ok: false, executionReady: false, digest: null, problems: ['validation now must be a valid date-time'] };
  if (!object(plan)) return { ok: false, executionReady: false, digest: null, problems: ['plan must be a JSON object'] };
  for (const issue of validateJsonSchema(plan, schema)) add(`schema: ${issue}`);

  const required = ['schema_version','plan_id','plan_digest','client_id','company_id','task_id','runtime_scope','execution_mode','plan_phase','cms_adapter','site_selector','source_snapshot','claim_ledger','capability_snapshot','desired_state','current_state_fingerprint','diff','operations','authorization_scope','reconciliation_policy','verification_plan','writeback_targets'];
  for (const key of required) if (!(key in plan)) add(`$.${key} is required`);
  if (plan.schema_version !== '1.1') add('$.schema_version must equal 1.1');
  for (const key of ['plan_id','client_id','company_id','task_id']) if (!nonEmpty(plan[key])) add(`$.${key} must be non-empty`);
  const runtimeBinding = validateRuntimeScopeBinding(plan);
  for (const problem of runtimeBinding.problems) add(problem);
  const taskRoot = runtimeBinding.expected?.task_root;
  const taskPath = (value, label, options) => {
    for (const problem of validateTaskRuntimePath(value, taskRoot, label, options)) add(problem);
  };
  if (!['fast','audit'].includes(plan.execution_mode)) add('$.execution_mode must be fast or audit');
  if (!planPhases.has(plan.plan_phase)) add('$.plan_phase must be site_bootstrap or site_operation');

  function scan(value, path = '$') {
    if (Array.isArray(value)) return value.forEach((item, index) => scan(item, `${path}[${index}]`));
    if (!object(value)) {
      if (typeof value === 'string') {
        if (/\bBearer\s+[A-Za-z0-9._~-]+/i.test(value)) add(`${path} contains a bearer credential`);
        if (/\b(?:cookie|set-cookie)\s*:/i.test(value)) add(`${path} contains a cookie header`);
        if (/\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/.test(value)) add(`${path} resembles a JWT`);
      }
      return;
    }
    for (const [key, child] of Object.entries(value)) {
      if (forbiddenKeys.has(key.toLowerCase())) add(`${path}.${key} is forbidden; dynamic interface IDs and credentials must stay in memory/private evidence`);
      scan(child, `${path}.${key}`);
    }
  }
  scan(plan);

  if (!datePattern.test(plan.source_snapshot?.captured_at ?? '')) add('$.source_snapshot.captured_at must be an RFC3339 UTC timestamp');
  else if (Date.parse(plan.source_snapshot.captured_at) > nowMs) add('$.source_snapshot.captured_at cannot be in the future');
  const sourceRows = plan.source_snapshot?.sources;
  const sources = new Map();
  if (!Array.isArray(sourceRows) || sourceRows.length === 0) add('$.source_snapshot.sources must contain at least one source');
  else for (const [index, row] of sourceRows.entries()) {
    const path = `$.source_snapshot.sources[${index}]`;
    if (!object(row) || !nonEmpty(row.source_id)) { add(`${path}.source_id must be non-empty`); continue; }
    if (sources.has(row.source_id)) add(`duplicate source_id: ${row.source_id}`);
    sources.set(row.source_id, row);
    if (row.source_scope !== `${plan.client_id}/${plan.company_id}/${plan.task_id}`) add(`${path}.source_scope must exactly match client_id/company_id/task_id`);
    taskPath(row.location, `${path}.location`);
    if (!shaPattern.test(row.digest ?? '')) add(`source ${row.source_id} digest must be sha256`);
    if (!usableMethodClearances.has(row.method_use_clearance)) add(`${path}.method_use_clearance=${row.method_use_clearance ?? 'missing'} blocks source consumption`);
    if (!['approved','pending','blocked','not-applicable'].includes(row.publication_clearance)) add(`source ${row.source_id} publication_clearance is invalid`);
    if (row.publication_clearance === 'approved' && !['owned','authorized','public'].includes(row.rights_status)) add(`${path}.publication_clearance=approved requires rights_status owned, authorized, or public`);
    if (row.source_date !== null && Date.parse(row.source_date) > nowMs) add(`${path}.source_date cannot be in the future`);
    if (row.review_after !== null && Date.parse(row.review_after) <= nowMs) add(`${path}.review_after is due or expired; refresh or explicitly reconfirm the source`);
    const extractionRows = row.extractions;
    if (!Array.isArray(extractionRows) || extractionRows.length === 0) add(`${path}.extractions must contain at least one validated extraction artifact`);
    else {
      const extractionIds = new Set();
      for (const [extractionIndex, extraction] of extractionRows.entries()) {
        const extractionPath = `${path}.extractions[${extractionIndex}]`;
        if (extractionIds.has(extraction?.extraction_id)) add(`${extractionPath}.extraction_id must be unique within the source`);
        extractionIds.add(extraction?.extraction_id);
        taskPath(extraction?.artifact_ref, `${extractionPath}.artifact_ref`);
        if (extraction?.source_digest !== row.digest) add(`${extractionPath}.source_digest must equal source.digest`);
        if (Date.parse(extraction?.captured_at) > nowMs) add(`${extractionPath}.captured_at cannot be in the future`);
        const unitRows = extraction?.units;
        if (!Array.isArray(unitRows) || unitRows.length === 0) add(`${extractionPath}.units must contain at least one validated extraction unit`);
        else {
          const unitIds = new Set();
          for (const [unitIndex, unit] of unitRows.entries()) {
            const unitPath = `${extractionPath}.units[${unitIndex}]`;
            if (unitIds.has(unit?.unit_id)) add(`${unitPath}.unit_id must be unique within the extraction`);
            unitIds.add(unit?.unit_id);
          }
        }
      }
    }
  }
  const sourceRefCheck = (refs, path, requiredRefs = false) => {
    if (!Array.isArray(refs)) { add(`${path} must be an array`); return; }
    if (!unique(refs)) add(`${path} must contain unique source refs`);
    if (requiredRefs && refs.length === 0) add(`${path} must not be empty`);
    for (const ref of refs) if (!sources.has(ref)) add(`${path} references missing source ${ref}`);
  };

  const claims = new Map();
  if (!Array.isArray(plan.claim_ledger)) add('$.claim_ledger must be an array');
  else for (const [index, claim] of plan.claim_ledger.entries()) {
    const path = `$.claim_ledger[${index}]`;
    if (!nonEmpty(claim?.claim_id)) { add(`${path}.claim_id must be non-empty`); continue; }
    if (claims.has(claim.claim_id)) add(`duplicate claim_id: ${claim.claim_id}`);
    claims.set(claim.claim_id, claim);
    if (!facts.has(claim.status)) add(`${path}.status is invalid`);
    sourceRefCheck(claim.source_refs, `${path}.source_refs`, claim.status === 'confirmed' || claim.status === 'inferred');
    if (!Array.isArray(claim.evidence_refs)) add(`${path}.evidence_refs must be an array`);
    else {
      if (['confirmed','inferred'].includes(claim.status) && claim.evidence_refs.length === 0) add(`${path}.evidence_refs must not be empty for ${claim.status} claims`);
      for (const [evidenceIndex, evidence] of claim.evidence_refs.entries()) {
        const evidencePath = `${path}.evidence_refs[${evidenceIndex}]`;
        if (!object(evidence)) { add(`${evidencePath} must be an object`); continue; }
        if (!nonEmpty(evidence.source_id) || !sources.has(evidence.source_id)) add(`${evidencePath}.source_id references a missing source`);
        else if (!Array.isArray(claim.source_refs) || !claim.source_refs.includes(evidence.source_id)) add(`${evidencePath}.source_id must also appear in claim.source_refs`);
        if (!nonEmpty(evidence.locator)) add(`${evidencePath}.locator must be non-empty`);
        if (!shaPattern.test(evidence.extraction_digest ?? '')) add(`${evidencePath}.extraction_digest must be sha256`);
        const source = sources.get(evidence.source_id);
        if (source && evidence.source_digest !== source.digest) add(`${evidencePath}.source_digest must equal the referenced source digest`);
        const extraction = Array.isArray(source?.extractions) ? source.extractions.find((row) => row?.extraction_id === evidence.extraction_id) : null;
        if (!extraction) add(`${evidencePath}.extraction_id must reference a source_snapshot extraction`);
        else {
          if (extraction.source_digest !== evidence.source_digest) add(`${evidencePath}.source_digest must equal the referenced extraction source digest`);
          const unit = Array.isArray(extraction.units) ? extraction.units.find((row) => row?.unit_id === evidence.unit_id) : null;
          if (!unit) add(`${evidencePath}.unit_id must reference the named extraction unit`);
          else {
            if (unit.locator !== evidence.locator) add(`${evidencePath}.locator must equal the referenced extraction unit locator`);
            if (unit.extraction_digest !== evidence.extraction_digest) add(`${evidencePath}.extraction_digest must equal the referenced extraction unit digest`);
          }
        }
      }
    }
  }

  const adapter = plan.cms_adapter;
  if (!object(adapter) || !nonEmpty(adapter.id) || !nonEmpty(adapter.version)) add('$.cms_adapter must identify adapter id and version');
  if (!shaPattern.test(adapter?.deployment_fingerprint ?? '')) add('$.cms_adapter.deployment_fingerprint must be sha256');
  if (!datePattern.test(adapter?.observed_at ?? '')) add('$.cms_adapter.observed_at must be an RFC3339 UTC timestamp');
  else if (Date.parse(adapter.observed_at) > nowMs) add('$.cms_adapter.observed_at cannot be in the future');

  const site = plan.site_selector;
  taskPath(site?.bootstrap_readback_ref, '$.site_selector.bootstrap_readback_ref', { nullable: true });
  const bootstrapPhase = plan.plan_phase === 'site_bootstrap';
  const siteOperationPhase = plan.plan_phase === 'site_operation';
  if (!object(site)) add('$.site_selector must be an object');
  if (site?.cross_site_fallback !== false) add('$.site_selector.cross_site_fallback must be false');
  if (bootstrapPhase) {
    if (site?.target_scope !== 'account') add('site_bootstrap requires site_selector.target_scope=account');
    if (!nonEmpty(site?.account_user_id)) add('site_bootstrap requires exact account_user_id from current readback');
    if (site?.site_key !== null || site?.site_id !== null) add('site_bootstrap must keep future site_key and site_id null; do not invent a future site identity');
    if (site?.selection_source !== 'planned-create') add('site_bootstrap requires selection_source=planned-create');
    if (site?.bootstrap_readback_ref !== null || site?.bootstrap_plan_digest !== null) add('site_bootstrap cannot claim a prior bootstrap readback');
  }
  if (siteOperationPhase) {
    if (site?.target_scope !== 'site') add('site_operation requires site_selector.target_scope=site');
    if (!nonEmpty(site?.site_key)) add('site_operation requires an exact non-empty site_key');
    if (!['user-confirmed','runtime-exact-match','bootstrap-readback'].includes(site?.selection_source)) add('site_operation selection_source must resolve an existing site');
    if (site?.selection_source === 'bootstrap-readback') {
      if (!nonEmpty(site?.bootstrap_readback_ref)) add('bootstrap-readback site selection requires private readback evidence');
      if (!shaPattern.test(site?.bootstrap_plan_digest ?? '')) add('bootstrap-readback site selection requires the Plan A bootstrap digest');
    } else if (site?.bootstrap_readback_ref !== null || site?.bootstrap_plan_digest !== null) {
      add('non-bootstrap site selection must keep bootstrap evidence fields null');
    }
  }

  const capabilities = new Map();
  const capRows = plan.capability_snapshot?.capabilities;
  if (!Array.isArray(capRows) || capRows.length === 0) add('$.capability_snapshot.capabilities must contain at least one capability');
  else for (const [index, cap] of capRows.entries()) {
    const path = `$.capability_snapshot.capabilities[${index}]`;
    if (!nonEmpty(cap?.capability_id)) { add(`${path}.capability_id must be non-empty`); continue; }
    if (capabilities.has(cap.capability_id)) add(`duplicate capability_id: ${cap.capability_id}`);
    capabilities.set(cap.capability_id, cap);
    if (!entityTypes.has(cap.entity_type)) add(`${path}.entity_type is invalid`);
    if (!operationActions.has(cap.action)) add(`${path}.action is invalid`);
    if (!maturities.has(cap.maturity)) add(`${path}.maturity is invalid`);
    if (!Array.isArray(cap.evidence_refs) || cap.evidence_refs.length === 0) add(`${path}.evidence_refs must not be empty`);
    else cap.evidence_refs.forEach((ref, evidenceIndex) => taskPath(ref, `${path}.evidence_refs[${evidenceIndex}]`));
  }
  if (plan.capability_snapshot?.deployment_fingerprint !== adapter?.deployment_fingerprint) add('capability and adapter deployment fingerprints must match');
  const capabilityCapturedAt = Date.parse(plan.capability_snapshot?.captured_at);
  const capabilityExpiresAt = Date.parse(plan.capability_snapshot?.expires_at);
  if (!Number.isFinite(capabilityCapturedAt) || !Number.isFinite(capabilityExpiresAt)) add('capability snapshot requires valid captured_at and expires_at');
  else {
    if (capabilityCapturedAt > nowMs) add('capability snapshot captured_at cannot be in the future');
    if (capabilityExpiresAt <= capabilityCapturedAt) add('capability snapshot expires_at must be after captured_at');
    if (nowMs >= capabilityExpiresAt) add('capability snapshot is expired; rediscover the current deployment before execution');
  }

  function validateIdentity(identity, path) {
    if (!object(identity)) { add(`${path} must be an object`); return false; }
    if (identity.match_strategy === 'exact_id') {
      if (!nonEmpty(identity.id)) add(`${path}.id is required for exact_id`);
      return nonEmpty(identity.id);
    }
    if (identity.match_strategy !== 'exact_natural_key') { add(`${path}.match_strategy must be exact_id or exact_natural_key`); return false; }
    const key = identity.natural_key;
    if (!object(key)) add(`${path}.natural_key must be an object`);
    if (bootstrapPhase) {
      if ('site_key' in (key ?? {})) add(`${path}.natural_key must not contain a future site_key during bootstrap`);
    } else if (key?.site_key !== site?.site_key) add(`${path}.natural_key.site_key must equal selected site_key`);
    const stableKeys = ['slug', 'external_key', 'site_key_candidate'].filter((name) => nonEmpty(key?.[name]));
    if (stableKeys.length === 0) add(`${path}.natural_key needs slug, external_key, or site_key_candidate; name/title-only matching is forbidden`);
    const bannedNaturalKeys = ['name', 'title', 'label'];
    if (object(key) && bannedNaturalKeys.some((name) => name in key) && stableKeys.length === 0) add(`${path}.natural_key cannot rely on a display name/title`);
    return stableKeys.length > 0 && (bootstrapPhase ? !('site_key' in (key ?? {})) : key?.site_key === site?.site_key);
  }

  const entities = new Map();
  if (!Array.isArray(plan.desired_state) || plan.desired_state.length === 0) add('$.desired_state must contain at least one entity');
  else for (const [index, entity] of plan.desired_state.entries()) {
    const path = `$.desired_state[${index}]`;
    if (!nonEmpty(entity?.entity_ref)) { add(`${path}.entity_ref must be non-empty`); continue; }
    if (entities.has(entity.entity_ref)) add(`duplicate entity_ref: ${entity.entity_ref}`);
    entities.set(entity.entity_ref, entity);
    if (!entityTypes.has(entity.entity_type)) add(`${path}.entity_type is invalid`);
    if (!['create','update','upsert','noop','explore'].includes(entity.intent)) add(`${path}.intent is invalid`);
    validateIdentity(entity.identity, `${path}.identity`);
    if (!object(entity.fields)) add(`${path}.fields must be an object`);
    else for (const [fieldName, field] of Object.entries(entity.fields)) {
      const fieldPath = `${path}.fields.${fieldName}`;
      if (!facts.has(field?.fact_status)) add(`${fieldPath}.fact_status is invalid`);
      sourceRefCheck(field?.source_refs, `${fieldPath}.source_refs`, field?.fact_status === 'confirmed' || field?.fact_status === 'inferred');
      const fieldClaims = [];
      if (!Array.isArray(field?.claim_refs)) add(`${fieldPath}.claim_refs must be an array`);
      else {
        if (!unique(field.claim_refs)) add(`${fieldPath}.claim_refs must contain unique claim refs`);
        if (['confirmed','inferred'].includes(field.fact_status) && field.claim_refs.length === 0) add(`${fieldPath}.claim_refs must not be empty for ${field.fact_status} facts`);
        for (const claimRef of field.claim_refs) {
          const claim = claims.get(claimRef);
          if (!claim) { add(`${fieldPath}.claim_refs references missing claim ${claimRef}`); continue; }
          fieldClaims.push(claim);
          if (field.fact_status === 'confirmed' && claim.status !== 'confirmed') add(`${fieldPath} confirmed fact cannot rely on claim ${claimRef}:${claim.status}`);
          if (field.fact_status === 'inferred' && !['confirmed','inferred'].includes(claim.status)) add(`${fieldPath} inferred fact cannot rely on claim ${claimRef}:${claim.status}`);
          if (blockedFactStatuses.has(field.fact_status) && claim.status !== field.fact_status) add(`${fieldPath} blocked fact status ${field.fact_status} does not match claim ${claimRef}:${claim.status}`);
          const fieldSources = Array.isArray(field.source_refs) ? field.source_refs : [];
          const claimSources = Array.isArray(claim.source_refs) ? claim.source_refs : [];
          const overlap = fieldSources.some((ref) => claimSources.includes(ref));
          if ((fieldSources.length > 0 || claimSources.length > 0) && !overlap) add(`${fieldPath} and claim ${claimRef} must share at least one source_ref`);
        }
      }
      const derivation = field?.derivation;
      if (!object(derivation) || !['direct','normalized','composed'].includes(derivation.mode)) add(`${fieldPath}.derivation must declare direct, normalized, or composed`);
      else if (derivation.mode === 'direct' && fieldClaims.length > 0 && !fieldClaims.some((claim) => stable(claim.value) === stable(field.value))) add(`${fieldPath} direct value must equal at least one referenced claim value`);
      else if (derivation.mode !== 'direct' && !nonEmpty(derivation.notes)) add(`${fieldPath}.derivation.notes is required for ${derivation.mode}`);
      if (field?.clear_existing === true && field?.value !== null && field?.value !== '') add(`${fieldPath}.clear_existing requires null or empty value`);
    }
  }

  if (bootstrapPhase) {
    if (plan.desired_state?.length !== 1 || plan.desired_state?.[0]?.entity_type !== 'site' || plan.desired_state?.[0]?.intent !== 'create') {
      add('site_bootstrap Plan A must contain exactly one desired site create; populate/configure content belongs in Plan B');
    }
  }
  if (siteOperationPhase && plan.desired_state?.some((entity) => entity?.entity_type === 'site' && entity?.intent === 'create')) {
    add('site_operation Plan B cannot create a site; it must use a resolved existing site from readback');
  }

  const operations = Array.isArray(plan.operations) ? plan.operations : [];
  if (!Array.isArray(plan.operations)) add('$.operations must be an array');
  else if (plan.operations.length === 0) add('$.operations must contain at least one operation');
  const operationIds = operations.map((op) => op?.operation_id);
  if (!unique(operationIds)) add('operation_id values must be unique');
  const diffRows = Array.isArray(plan.diff) ? plan.diff : [];
  const diffIds = diffRows.map((row) => row?.operation_id);
  if (!Array.isArray(plan.diff)) add('$.diff must be an array');
  else if (plan.diff.length === 0) add('$.diff must contain at least one row');
  if (!unique(diffIds)) add('diff operation_id values must be unique');
  if (diffRows.length !== operations.length) add('diff and operations must have the same number of rows');
  const diffByOperation = new Map(diffRows.map((row) => [row.operation_id, row]));

  for (const [index, op] of operations.entries()) {
    const path = `$.operations[${index}]`;
    if (!nonEmpty(op?.operation_id)) add(`${path}.operation_id must be non-empty`);
    if (!['create','update','noop','explore','publish'].includes(op?.intent)) add(`${path}.intent must be resolved before execution; raw upsert is forbidden`);
    if (op?.intent === 'upsert') add(`${path}.intent cannot be upsert`);
    const entity = entities.get(op?.entity_ref);
    if (!entity) add(`${path}.entity_ref does not exist in desired_state`);
    else {
      if (entity.entity_type !== op.entity_type) add(`${path}.entity_type does not match desired_state`);
      if (stable(entity.identity) !== stable(op.identity)) add(`${path}.identity must exactly match desired_state identity`);
      const compatible = op.intent === 'publish' || ({ create: ['create'], update: ['update','noop'], upsert: ['create','update','noop'], noop: ['noop'], explore: ['explore'] }[entity.intent] ?? []).includes(op.intent);
      if (!compatible) add(`${path}.intent ${op.intent} is incompatible with desired_state intent ${entity.intent}`);
    }
    validateIdentity(op?.identity, `${path}.identity`);
    if (op?.intent === 'update' && !shaPattern.test(op?.expected_current_fingerprint ?? '')) add(`${path}.expected_current_fingerprint is required for update`);
    if (op?.intent !== 'update' && op?.expected_current_fingerprint !== null) add(`${path}.expected_current_fingerprint must be null unless intent is update`);
    const expectedDeps = index === 0 ? [] : [operations[index - 1]?.operation_id];
    if (JSON.stringify(op?.dependencies) !== JSON.stringify(expectedDeps)) add(`${path}.dependencies must form one strict serial chain: ${JSON.stringify(expectedDeps)}`);
    if (op?.mutation !== !['noop','explore'].includes(op?.intent)) add(`${path}.mutation does not match intent`);
    const publicationEffect = op?.publication_effect;
    if (['noop','explore'].includes(op?.intent) && publicationEffect !== 'none') add(`${path}.publication_effect must be none for ${op.intent}`);
    if (op?.intent === 'publish' && publicationEffect !== 'publish_transition') add(`${path}.publication_effect must be publish_transition for publish`);
    if (['create','update'].includes(op?.intent)) {
      if (op.entity_type === 'site') {
        if (publicationEffect !== 'non_public_resource') add(`${path}.publication_effect must be non_public_resource for site create/update`);
      } else if (!['private_draft','public_immediate'].includes(publicationEffect)) add(`${path}.publication_effect must declare private_draft or public_immediate for content mutation`);
    }
    const cap = capabilities.get(op?.capability_ref);
    if (!cap) add(`${path}.capability_ref is missing from capability_snapshot`);
    else {
      if (cap.entity_type !== op.entity_type) add(`${path} capability entity_type mismatch`);
      if (cap.action !== op.intent && !(op.intent === 'noop' && cap.action === 'readback') && !(op.intent === 'explore' && cap.action === 'discover')) add(`${path} capability action mismatch`);
      if (cap.maturity === 'unsupported') add(`${path} uses unsupported capability`);
      if (op.mutation && cap.maturity !== 'live_verified_current_deployment') add(`${path} remote mutation requires live_verified_current_deployment; got ${cap.maturity}`);
    }
    const refs = Array.isArray(op?.field_refs) ? op.field_refs : [];
    if (['create','update'].includes(op?.intent) && refs.length === 0) add(`${path}.field_refs must not be empty for ${op.intent}`);
    if (['noop','explore','publish'].includes(op?.intent) && refs.length !== 0) add(`${path}.field_refs must be empty for ${op.intent}`);
    for (const fieldName of refs) {
      const field = entity?.fields?.[fieldName];
      if (!field) add(`${path}.field_refs references missing field ${fieldName}`);
      else {
        if (blockedFactStatuses.has(field.fact_status)) add(`${path}.field_refs includes blocked fact ${fieldName}:${field.fact_status}`);
        if (!Array.isArray(field.claim_refs) || field.claim_refs.length === 0) add(`${path}.field_refs field ${fieldName} has no claim evidence`);
        for (const claimRef of Array.isArray(field.claim_refs) ? field.claim_refs : []) {
          const claim = claims.get(claimRef);
          if (claim && blockedFactStatuses.has(claim.status)) add(`${path}.field_refs uses blocked claim ${claimRef}:${claim.status}`);
        }
      }
    }
    if (!Array.isArray(op?.readback_requirements) || op.readback_requirements.length === 0) add(`${path}.readback_requirements must not be empty`);
    if (['public_immediate','publish_transition'].includes(publicationEffect)) {
      const publicationFields = publicationEffect === 'publish_transition'
        ? Object.values(entity?.fields ?? {}).filter((field) => ['confirmed','inferred'].includes(field?.fact_status))
        : refs.map((fieldName) => entity?.fields?.[fieldName]).filter(Boolean);
      const publicationSources = new Set();
      for (const field of publicationFields) for (const sourceRef of Array.isArray(field?.source_refs) ? field.source_refs : []) publicationSources.add(sourceRef);
      for (const sourceRef of publicationSources) {
        const clearance = sources.get(sourceRef)?.publication_clearance;
        if (!publishableSourceClearances.has(clearance)) add(`${path} public mutation is blocked by source ${sourceRef} publication_clearance=${clearance ?? 'missing'}`);
      }
    }
    const row = diffByOperation.get(op?.operation_id);
    if (!row) add(`${path} has no matching diff row`);
    else {
      if (row.entity_ref !== op.entity_ref || row.resolved_intent !== op.intent) add(`${path} does not match its diff row`);
      if (JSON.stringify(row.changed_fields) !== JSON.stringify(refs)) add(`${path}.field_refs must equal diff.changed_fields in order`);
    }
  }
  for (const row of diffRows) if (!operationIds.includes(row.operation_id)) add(`diff row ${row.operation_id} has no operation`);
  if (bootstrapPhase) {
    if (operations.length !== 1 || operations[0]?.entity_type !== 'site' || operations[0]?.intent !== 'create') {
      add('site_bootstrap Plan A must contain exactly one site create operation; no taxonomy/media/content operation may share it');
    }
  }

  if (!shaPattern.test(plan.current_state_fingerprint ?? '')) add('$.current_state_fingerprint must be sha256');
  if (plan.reconciliation_policy?.ambiguous_write !== 'read-only-reconcile-before-any-retry') add('ambiguous writes must use read-only reconciliation');
  if (plan.reconciliation_policy?.automatic_retry_after_request_started !== false) add('automatic retry after request_started must be false');
  if (plan.reconciliation_policy?.identity_rule !== 'exact-id-or-site-scoped-natural-key') add('identity rule must be exact and site scoped');
  if (plan.verification_plan?.backend_readback !== true) add('backend readback is mandatory');
  if (operations.some((op) => ['article','product'].includes(op.entity_type) && op.mutation) && plan.verification_plan?.editor_reopen !== true) add('article/product mutation requires editor_reopen');
  if (operations.some((op) => op.intent === 'publish') && plan.verification_plan?.frontend !== true) add('publish requires frontend verification');
  if (Array.isArray(plan.verification_plan?.evidence_targets)) {
    plan.verification_plan.evidence_targets.forEach((ref, index) => taskPath(ref, `$.verification_plan.evidence_targets[${index}]`));
  }
  if (!Array.isArray(plan.writeback_targets) || plan.writeback_targets.length === 0) add('writeback_targets must not be empty');
  else for (const [index, target] of plan.writeback_targets.entries()) {
    if (target?.visibility !== 'private-runtime') add(`writeback_targets[${index}] must remain private-runtime`);
    taskPath(target?.path, `$.writeback_targets[${index}].path`);
  }

  const digest = calculatePlanDigest(plan);
  if (plan.plan_digest !== digest) add(`$.plan_digest mismatch; expected ${digest}`);
  const auth = plan.authorization_scope;
  let executionReady = false;
  if (!object(auth)) add('$.authorization_scope must be an object');
  else {
    const expectedTargetScope = bootstrapPhase ? 'account' : 'site';
    const expectedTargetKey = bootstrapPhase ? site?.account_user_id : site?.site_key;
    if (auth.target_scope !== expectedTargetScope) add(`authorization target_scope must match ${expectedTargetScope} plan scope`);
    if (auth.target_key !== expectedTargetKey) add('authorization target_key must match the exact account or site target');
    if (JSON.stringify(auth.operation_ids) !== JSON.stringify(operationIds)) add('authorization operation_ids must exactly match ordered operations');
    if (auth.identity_status !== 'not_verified') add('authorization identity_status must remain not_verified');
    if (auth.status === 'approved') {
      if (!nonEmpty(auth.actor)) add('approved authorization requires named human-asserted actor');
      if (!datePattern.test(auth.approved_at ?? '') || !datePattern.test(auth.expires_at ?? '')) add('approved authorization requires UTC approved_at and expires_at');
      const start = Date.parse(auth.approved_at); const end = Date.parse(auth.expires_at);
      if (!(end > start && end - start <= 30 * 60 * 1000)) add('authorization validity must be greater than zero and no more than 30 minutes');
      if (start > nowMs) add('authorization approved_at cannot be in the future');
      if (nowMs >= end) add('authorization is expired');
      if (auth.plan_sha256 !== digest) add('authorization plan_sha256 must bind the calculated plan digest');
      executionReady = problems.length === 0;
    } else if (auth.status === 'pending') {
      if (auth.actor !== null || auth.approved_at !== null || auth.expires_at !== null || auth.plan_sha256 !== null) add('pending authorization must keep actor/timestamps/plan_sha256 null');
    } else add('authorization status must be pending or approved');
  }

  return { ok: problems.length === 0, executionReady: problems.length === 0 && executionReady, digest, problems };
}

export function loadAndValidatePlan(path) {
  const plan = JSON.parse(readFileSync(resolve(path), 'utf8'));
  return validateContentOperationPlan(plan);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const path = process.argv[2];
  if (!path) {
    console.error('usage: node scripts/validate-content-operation-plan.mjs path/to/content-operation-plan.json');
    process.exit(2);
  }
  let result;
  try { result = loadAndValidatePlan(path); }
  catch (error) { console.error(`CONTENT_OPERATION_PLAN_BLOCK: ${error.message}`); process.exit(1); }
  if (!result.ok) {
    console.error('CONTENT_OPERATION_PLAN_BLOCK');
    for (const problem of result.problems) console.error(`- ${problem}`);
    process.exit(1);
  }
  console.log(result.executionReady ? 'CONTENT_OPERATION_PLAN_EXECUTION_READY' : 'CONTENT_OPERATION_PLAN_STRUCTURE_PASS_AUTHORIZATION_PENDING');
  console.log(`plan_digest=${result.digest}`);
  console.log('Boundary: local validation does not prove CMS login, remote mutation, publication, frontend correctness, SEO, inquiry, or conversion.');
}
