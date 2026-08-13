/**
 * AllinCMS workspace/session/site discovery contract.
 *
 * This module is read-only by default. It does not read cookies, export tokens,
 * submit forms, or create sites. Network and browser capabilities are injected
 * by the host so the same signed-in browser session can be used without moving
 * credentials into Node.js or the repository.
 */

export const ALLINCMS_WORKSPACE_ORIGIN = 'https://workspace.laicms.com';
export const ALLINCMS_SITES_PATH = '/sites';
export const ALLINCMS_SIGN_IN_PATH = '/sign-in';
export const ALLINCMS_SIGN_IN_URL = `${ALLINCMS_WORKSPACE_ORIGIN}${ALLINCMS_SIGN_IN_PATH}`;
export const ALLINCMS_WORKSPACE_PREFLIGHT_STATUSES = Object.freeze([
  'authenticated',
  'login_required',
  'zero_sites',
  'single_site',
  'multiple_sites',
  'target_selected',
  'target_not_visible',
  'pagination_incomplete',
  'contract_drift',
  'http_error',
]);

const SITE_FIELDS = Object.freeze([
  'id', 'name', 'description', 'slug', 'domains', 'displayDomain',
  'active', 'themeCount', 'createdAt',
]);

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : null;
}

function asTrimmedString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function headerValue(headers, name) {
  if (!headers) return '';
  if (typeof headers.get === 'function') return headers.get(name) || '';
  const target = name.toLowerCase();
  for (const [key, value] of Object.entries(headers)) {
    if (key.toLowerCase() === target) return String(value || '');
  }
  return '';
}

function normalizeUrl(value, fallback = `${ALLINCMS_WORKSPACE_ORIGIN}${ALLINCMS_SITES_PATH}`) {
  try {
    return new URL(value || fallback, ALLINCMS_WORKSPACE_ORIGIN).toString();
  } catch {
    return fallback;
  }
}

function isSignInUrl(value) {
  try {
    const url = new URL(value, ALLINCMS_WORKSPACE_ORIGIN);
    return url.origin === ALLINCMS_WORKSPACE_ORIGIN
      && (url.pathname === ALLINCMS_SIGN_IN_PATH || url.pathname.startsWith(`${ALLINCMS_SIGN_IN_PATH}/`));
  } catch {
    return false;
  }
}

function containsLoginMarkers(text) {
  const body = String(text || '');
  return /(?:\/sign-in|signIn|sign-in|登录账号|登录到|type=["']password["'])/i.test(body);
}

function extractBalancedJsonValues(text) {
  const source = String(text || '');
  const values = [];

  for (let start = 0; start < source.length; start += 1) {
    const opening = source[start];
    if (opening !== '{' && opening !== '[') continue;

    const stack = [opening];
    let inString = false;
    let escaped = false;
    let end = start + 1;

    for (; end < source.length; end += 1) {
      const char = source[end];
      if (inString) {
        if (escaped) escaped = false;
        else if (char === '\\') escaped = true;
        else if (char === '"') inString = false;
        continue;
      }
      if (char === '"') {
        inString = true;
        continue;
      }
      if (char === '{' || char === '[') stack.push(char);
      else if (char === '}' || char === ']') {
        const expected = char === '}' ? '{' : '[';
        if (stack.at(-1) !== expected) break;
        stack.pop();
        if (stack.length === 0) {
          const candidate = source.slice(start, end + 1);
          try {
            values.push(JSON.parse(candidate));
            start = end;
          } catch {
            // RSC may contain non-JSON rows. Continue scanning at the next byte.
          }
          break;
        }
      }
    }
  }

  return values;
}

function walk(value, visitor, seen = new Set()) {
  if (!value || typeof value !== 'object' || seen.has(value)) return;
  seen.add(value);
  visitor(value);
  if (Array.isArray(value)) {
    for (const item of value) walk(item, visitor, seen);
  } else {
    for (const item of Object.values(value)) walk(item, visitor, seen);
  }
}

function looksLikeWorkspaceUser(value) {
  const object = asObject(value);
  return Boolean(
    object
    && asTrimmedString(object.id)
    && (asTrimmedString(object.email) || asTrimmedString(object.name))
    && ('tenant' in object || 'role' in object),
  );
}

function looksLikeSite(value) {
  const object = asObject(value);
  return Boolean(
    object
    && asTrimmedString(object.id)
    && asTrimmedString(object.name)
    && asTrimmedString(object.slug)
    && ('displayDomain' in object || 'domains' in object || 'active' in object),
  );
}

function looksLikeSitesPayload(value) {
  const object = asObject(value);
  if (!object || !Array.isArray(object.data)) return false;
  if (!('canCreate' in object) && !asObject(object.pagination)) return false;
  return object.data.length === 0 || object.data.every(looksLikeSite);
}

function normalizeUser(value) {
  const object = asObject(value) || {};
  return {
    id: asTrimmedString(object.id),
    name: asTrimmedString(object.name),
    email: asTrimmedString(object.email),
    role: asTrimmedString(object.role),
    tenant: asTrimmedString(object.tenant),
  };
}

function normalizeSite(value) {
  const object = asObject(value) || {};
  return Object.fromEntries(SITE_FIELDS.map((field) => {
    if (field === 'domains') return [field, Array.isArray(object[field]) ? object[field] : []];
    if (field === 'active') return [field, typeof object[field] === 'boolean' ? object[field] : null];
    if (field === 'themeCount') return [field, Number.isInteger(object[field]) ? object[field] : null];
    return [field, object[field] ?? null];
  }));
}

function normalizePagination(value, siteCount) {
  const object = asObject(value) || {};
  const integer = (candidate, fallback) => Number.isInteger(candidate) && candidate >= 0 ? candidate : fallback;
  const page = Math.max(1, integer(object.page, 1));
  const limit = Math.max(1, integer(object.limit, Math.max(siteCount, 1)));
  const totalDocs = integer(object.totalDocs, siteCount);
  const totalPages = Math.max(1, integer(object.totalPages, Math.ceil(totalDocs / limit) || 1));
  return {
    page,
    limit,
    totalDocs,
    totalPages,
    hasNextPage: typeof object.hasNextPage === 'boolean' ? object.hasNextPage : page < totalPages,
    hasPrevPage: typeof object.hasPrevPage === 'boolean' ? object.hasPrevPage : page > 1,
  };
}

export function parseAllinCmsWorkspaceRsc(text) {
  const candidates = extractBalancedJsonValues(text);
  let user = null;
  let sitesPayload = null;

  for (const candidate of candidates) {
    walk(candidate, (value) => {
      const object = asObject(value);
      if (!object) return;
      if (!user && looksLikeWorkspaceUser(object.user)) user = object.user;
      if (!user && looksLikeWorkspaceUser(object)) user = object;
      if (!sitesPayload && looksLikeSitesPayload(object)) sitesPayload = object;
    });
  }

  if (!user || !sitesPayload) {
    return {
      status: 'contract_drift',
      user: user ? normalizeUser(user) : null,
      sites: sitesPayload ? sitesPayload.data.map(normalizeSite) : [],
      pagination: sitesPayload ? normalizePagination(sitesPayload.pagination, sitesPayload.data.length) : null,
      canCreate: sitesPayload && typeof sitesPayload.canCreate === 'boolean' ? sitesPayload.canCreate : null,
      missing: [!user ? 'user' : null, !sitesPayload ? 'sites_payload' : null].filter(Boolean),
    };
  }

  const sites = sitesPayload.data.map(normalizeSite);
  return {
    status: 'authenticated',
    user: normalizeUser(user),
    userId: asTrimmedString(user.id),
    tenantId: asTrimmedString(user.tenant),
    sites,
    pagination: normalizePagination(sitesPayload.pagination, sites.length),
    canCreate: typeof sitesPayload.canCreate === 'boolean' ? sitesPayload.canCreate : null,
  };
}

export function inspectAllinCmsWorkspaceSession(response) {
  const statusCode = Number(response?.status ?? response?.statusCode ?? 0);
  const finalUrl = normalizeUrl(response?.url || response?.finalUrl);
  const contentType = headerValue(response?.headers, 'content-type').toLowerCase();
  const text = String(response?.text ?? response?.body ?? '');

  if (statusCode === 401 || statusCode === 403 || isSignInUrl(finalUrl)) {
    return { status: 'login_required', statusCode, finalUrl, reason: 'auth_redirect_or_status' };
  }
  if (statusCode < 200 || statusCode >= 300) {
    return { status: 'http_error', statusCode, finalUrl, reason: 'unexpected_http_status' };
  }
  if (containsLoginMarkers(text) && (!contentType.includes('text/x-component') || !text.includes('canCreate'))) {
    return { status: 'login_required', statusCode, finalUrl, reason: 'login_content_detected' };
  }

  const parsed = parseAllinCmsWorkspaceRsc(text);
  return { ...parsed, statusCode, finalUrl, contentType };
}

export function buildAllinCmsSitesRscRequest({
  page = 1,
  search = '',
  rscToken = 'workspace-preflight',
  origin = ALLINCMS_WORKSPACE_ORIGIN,
} = {}) {
  if (!Number.isInteger(page) || page < 1) throw new Error('page must be a positive integer');
  const url = new URL(ALLINCMS_SITES_PATH, origin);
  if (page > 1) url.searchParams.set('page', String(page));
  if (typeof search === 'string' && search.trim()) url.searchParams.set('search', search.trim());
  url.searchParams.set('_rsc', asTrimmedString(rscToken) || 'workspace-preflight');
  return {
    method: 'GET',
    url: url.toString(),
    headers: { Accept: 'text/x-component', RSC: '1' },
    credentials: 'include',
    mutation: false,
    browserTransport: 'existing_same_origin_session',
    requiresVisibleNavigation: false,
    foreground: false,
  };
}

function exactSiteMatches(site, target) {
  const normalized = asTrimmedString(target);
  if (!normalized) return false;
  return [site.id, site.slug, site.displayDomain]
    .filter((value) => typeof value === 'string')
    .some((value) => value === normalized);
}

export function selectExactAllinCmsSite(sites, targetSite) {
  const list = Array.isArray(sites) ? sites : [];
  const target = asTrimmedString(targetSite);
  if (target) {
    const matches = list.filter((site) => exactSiteMatches(site, target));
    return matches.length === 1
      ? { status: 'target_selected', site: matches[0] }
      : { status: 'target_not_visible', site: null, targetSite: target };
  }
  if (list.length === 0) return { status: 'zero_sites', site: null };
  if (list.length === 1) return { status: 'single_site', site: list[0] };
  return { status: 'multiple_sites', site: null };
}

export async function listAllinCmsSites({
  fetchPage,
  targetSite = null,
  search = '',
  maxPages = 100,
  rscToken = 'workspace-preflight',
} = {}) {
  if (typeof fetchPage !== 'function') throw new Error('fetchPage callback is required');
  if (!Number.isInteger(maxPages) || maxPages < 1) throw new Error('maxPages must be a positive integer');

  const sites = [];
  let session = null;
  let expectedTotalPages = 1;
  let expectedTotalDocs = null;

  for (let page = 1; page <= expectedTotalPages; page += 1) {
    if (page > maxPages) {
      return {
        status: 'pagination_incomplete',
        user: session?.user || null,
        sites,
        expectedTotalPages,
        fetchedPages: page - 1,
      };
    }
    const request = buildAllinCmsSitesRscRequest({ page, search, rscToken: `${rscToken}-${page}` });
    const inspected = inspectAllinCmsWorkspaceSession(await fetchPage(request));
    if (inspected.status !== 'authenticated') return { ...inspected, request };

    if (!session) {
      session = inspected;
      expectedTotalPages = inspected.pagination.totalPages;
      expectedTotalDocs = inspected.pagination.totalDocs;
    } else if (inspected.user.id !== session.user.id || inspected.pagination.totalPages !== expectedTotalPages) {
      return {
        status: 'contract_drift',
        reason: 'workspace_identity_or_pagination_changed_during_read',
        user: session.user,
        sites,
      };
    }
    sites.push(...inspected.sites);
  }

  const unique = new Map();
  for (const site of sites) {
    const key = site.id || site.slug;
    if (!key || unique.has(key)) {
      return { status: 'contract_drift', reason: 'duplicate_or_missing_site_identity', user: session.user, sites };
    }
    unique.set(key, site);
  }
  const completeSites = [...unique.values()];
  if (expectedTotalDocs !== null && completeSites.length !== expectedTotalDocs) {
    return {
      status: 'pagination_incomplete',
      reason: 'site_count_does_not_match_total_docs',
      user: session.user,
      sites: completeSites,
      expectedTotalDocs,
    };
  }

  const selection = selectExactAllinCmsSite(completeSites, targetSite);
  return {
    ...selection,
    user: session.user,
    userId: session.user.id,
    tenantId: session.user.tenant,
    sites: completeSites,
    canCreate: session.canCreate,
    pagination: { ...session.pagination, page: expectedTotalPages, totalPages: expectedTotalPages },
    complete: true,
  };
}

export function buildAllinCmsLoginHandoff({ browserOpened = false, error = null } = {}) {
  return {
    status: 'login_required',
    openUrl: ALLINCMS_SIGN_IN_URL,
    browser: 'host-in-app-browser',
    keepVisible: true,
    bringToForeground: true,
    browserOpened,
    recheckRequired: true,
    reusePreviousCheck: false,
    userMessage: 'AllinCMS 后台尚未登录。我已打开登录页，请完成登录；完成后告诉我“已登录”，我会重新通过接口检查当前用户和网站列表。',
    ...(error ? { browserOpenError: String(error.message || error) } : {}),
  };
}

export async function runAllinCmsWorkspacePreflight(options = {}) {
  const result = await listAllinCmsSites(options);
  if (result.status !== 'login_required') return result;

  if (typeof options.openLoginPage !== 'function') {
    return {
      ...result,
      handoff: buildAllinCmsLoginHandoff(),
      hostActionRequired: 'open_login_in_in_app_browser',
    };
  }

  try {
    await options.openLoginPage(ALLINCMS_SIGN_IN_URL, { foreground: true, keepVisible: true });
    return { ...result, handoff: buildAllinCmsLoginHandoff({ browserOpened: true }) };
  } catch (error) {
    return { ...result, handoff: buildAllinCmsLoginHandoff({ error }), hostActionRequired: 'open_login_in_in_app_browser' };
  }
}

export function discoverAllinCmsCreateSiteClientContract(scriptTexts) {
  const scripts = Array.isArray(scriptTexts) ? scriptTexts : [scriptTexts];
  const joined = scripts.map((entry) => typeof entry === 'string' ? entry : entry?.text || '').join('\n');
  const actionMatch = joined.match(/createServerReference\)\(["']([0-9a-f]{40,64})["'][\s\S]{0,500}?["']createSiteAction["']/)
    || joined.match(/createServerReference\(["']([0-9a-f]{40,64})["'][\s\S]{0,500}?["']createSiteAction["']/);
  const hasNameRules = /name[^\n]{0,300}?\.min\(2,[^\n]{0,200}?\.max\(50,/.test(joined);
  const hasDescriptionRules = /description[^\n]{0,300}?\.max\(200,[^\n]{0,200}?\.optional\(\)/.test(joined);

  if (!actionMatch || !hasNameRules || !hasDescriptionRules) {
    return {
      status: 'contract_drift',
      actionName: 'createSiteAction',
      actionId: actionMatch?.[1] || null,
      missing: [!actionMatch ? 'action_reference' : null, !hasNameRules ? 'name_rules' : null, !hasDescriptionRules ? 'description_rules' : null].filter(Boolean),
    };
  }

  return {
    status: 'observed',
    actionName: 'createSiteAction',
    actionId: actionMatch[1],
    route: ALLINCMS_SITES_PATH,
    method: 'POST',
    fields: {
      name: { type: 'string', required: true, minLength: 2, maxLength: 50 },
      description: { type: 'string', required: false, maxLength: 200, uiDefault: '' },
    },
    serverSessionFields: ['user.id', 'user.tenant', 'user.role'],
  };
}

export function validateAllinCmsCreateSiteInput(input) {
  const object = asObject(input);
  if (!object) throw new Error('create-site input must be an object');
  if (typeof object.name !== 'string' || object.name.length < 2 || object.name.length > 50) {
    throw new Error('name must be a string between 2 and 50 characters');
  }
  if (object.description !== undefined && (typeof object.description !== 'string' || object.description.length > 200)) {
    throw new Error('description must be an optional string up to 200 characters');
  }
  const unknown = Object.keys(object).filter((key) => !['name', 'description'].includes(key));
  if (unknown.length) throw new Error(`Unsupported create-site fields: ${unknown.join(', ')}`);
  return object.description === undefined
    ? { name: object.name }
    : { name: object.name, description: object.description };
}

export function buildAllinCmsCreateSiteActionRequest({
  actionId,
  routerStateTree,
  deploymentId = null,
  nextUrl = null,
  input,
  origin = ALLINCMS_WORKSPACE_ORIGIN,
} = {}) {
  const id = asTrimmedString(actionId);
  if (!id || !/^[0-9a-f]{40,64}$/.test(id)) throw new Error('A current 40-64 character hexadecimal createSiteAction ID is required');
  const tree = asTrimmedString(routerStateTree);
  if (!tree) throw new Error('The current Next.js router state tree is required');
  const payload = validateAllinCmsCreateSiteInput(input);
  const headers = {
    Accept: 'text/x-component',
    'Next-Action': id,
    'Next-Router-State-Tree': tree,
  };
  if (asTrimmedString(deploymentId)) headers['x-deployment-id'] = deploymentId.trim();
  if (asTrimmedString(nextUrl)) headers['Next-Url'] = nextUrl.trim();

  return {
    method: 'POST',
    url: new URL(ALLINCMS_SITES_PATH, origin).toString(),
    headers,
    credentials: 'include',
    body: JSON.stringify([payload]),
    bodyEncoding: 'React Flight encodeReply for one plain-object action argument',
    mutation: true,
    actionName: 'createSiteAction',
    serverInjectedNotInPayload: ['user.id', 'user.tenant', 'user.role'],
  };
}
