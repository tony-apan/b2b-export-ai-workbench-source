/**
 * AllinCMS account-scope site bootstrap operations.
 *
 * This module follows the same contract-driven pattern as article-operations.mjs.
 * It does not store action IDs, router trees, deployment IDs, or credentials.
 */
import { createAllinCmsActionClient } from './article-operations.mjs';
import {
  validateAllinCmsCreateSiteInput,
  buildAllinCmsCreateSiteActionRequest,
} from './workspace-preflight.mjs';

export const WORKSPACE_ORIGIN = 'https://workspace.laicms.com';
export const SITE_CREATE_ACTION_NAME = 'siteCreate';
export const SITE_BOOTSTRAP_SITE_KEY = 'workspace';

export function buildSiteCreatePayload(input) {
  return validateAllinCmsCreateSiteInput(input);
}

export function buildSiteCreateRequest(options) {
  return buildAllinCmsCreateSiteActionRequest(options);
}

export async function createSite({
  client,
  runtime,
  request,
  authorizationContext = null,
  input,
  readback,
  refresh,
  beforeSiteIds,
  getAfterSiteIds,
  getCreatedSiteId,
  getCreatedSiteKey,
  getCreatedSiteDomain,
  maxControlledRetries = 1,
}) {
  const payload = buildSiteCreatePayload(input);
  const actionClient = client || createAllinCmsActionClient({
    siteKey: SITE_BOOTSTRAP_SITE_KEY,
    runtime,
    request,
    authorizationContext,
  });
  const response = await actionClient.send({
    route: '/sites',
    actionName: SITE_CREATE_ACTION_NAME,
    payload,
  });
  if (typeof refresh === 'function') await refresh();
  if (typeof readback !== 'function') {
    return { status: 'site_mutation_sent', response, needsReadback: true, requestMayHaveSucceeded: true };
  }
  const actual = await readback();
  const result = {
    status: response.status === 200 ? 'site_mutation_succeeded' : 'site_mutation_response_non_200',
    response,
    readback: actual,
    requestMayHaveSucceeded: response.status === 200,
    automaticRetryAllowed: false,
  };
  const deltaEvidence = {
    performed: false,
    verdict: 'not_performed',
    problems: [],
  };
  if (Array.isArray(beforeSiteIds) && typeof getAfterSiteIds === 'function' && typeof getCreatedSiteId === 'function') {
    try {
      const before = new Set(beforeSiteIds.map((id) => String(id)));
      const after = getAfterSiteIds(actual).map((id) => String(id));
      const newIds = after.filter((id) => !before.has(id));
      const createdId = String(getCreatedSiteId(actual));
      deltaEvidence.performed = true;
      if (newIds.length !== 1) deltaEvidence.problems.push(`expected exactly one new site ID, found ${newIds.length}`);
      if (createdId && before.has(createdId)) deltaEvidence.problems.push('created site ID already existed before create');
      if (newIds.length === 1 && createdId && createdId !== newIds[0]) deltaEvidence.problems.push('created site ID does not match before/after delta');
      if (typeof getCreatedSiteKey === 'function') deltaEvidence.siteKey = getCreatedSiteKey(actual);
      if (typeof getCreatedSiteDomain === 'function') deltaEvidence.domain = getCreatedSiteDomain(actual);
      deltaEvidence.verdict = deltaEvidence.problems.length === 0 ? 'pass' : 'block';
      if (deltaEvidence.verdict !== 'pass') result.status = 'site_delta_verification_failed';
    } catch (error) {
      deltaEvidence.problems.push(error.message);
      deltaEvidence.verdict = 'block';
      result.status = 'site_delta_verification_failed';
    }
  } else {
    deltaEvidence.problems.push('beforeSiteIds / getAfterSiteIds / getCreatedSiteId are required for qualified site create evidence');
  }
  result.siteDeltaEvidence = deltaEvidence;
  return result;
}

export const _internal = {
  buildSiteCreatePayload,
  buildSiteCreateRequest,
  SITE_BOOTSTRAP_SITE_KEY,
};
