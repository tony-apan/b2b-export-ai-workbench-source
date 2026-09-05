/**
 * AllinCMS article:create real providers — pure-HTTP RSC readers (P0-3.3b).
 *
 * Cross-platform by construction (pure Node `fetch`, no AppleScript, no
 * Chrome, no Playwright): works identically on macOS, Windows and Linux.
 * This is the real (non-fixture) implementation of the three article:create
 * host providers the canonical driver requires:
 *
 *   - `beforePostIds`      → articleBeforePostIdsProvider: the same-site
 *     before snapshot. GET `/{siteKey}/posts?_rsc=1` (RSC:1 header +
 *     `Cookie: payload-token=<authCookie>`) on the workspace origin, parse
 *     the posts-list props out of the RSC flight stream, follow list
 *     pagination when the platform reports more pages.
 *   - `createReadback`     → articleCreateReadbackProvider: GET
 *     `/{siteKey}/posts/{createdPostId}/update?_rsc=1`, parse the editor
 *     `defaultValues` (title/slug/excerpt/order/coverImage/categories/tags/
 *     content) plus a fresh after-snapshot of the posts list, and return the
 *     `{ record, afterPostIds }` wrapper the bottom-layer create comparison
 *     consumes. `createdPostId` is taken from `args.createdPostId` when the
 *     caller supplies one, otherwise derived as the SOLE before/after delta
 *     of the same-site post ID list (the same uniqueness rule the bottom
 *     layer enforces; zero or multiple new IDs fail closed).
 *   - `editorReopen`       → articleEditorReopenProvider: plain HTML GET of
 *     the same editor URL, asserting HTTP 200, no sign-in redirect, and that
 *     the returned HTML still carries this post's edit context (the created
 *     post id appears in the document) → `{ status, authenticated, healthy,
 *     postId }`.
 *
 * RSC flight parsing is a JS port of the proven Python semantics in
 * TOOLS/interface-kit/allincms_api.py (`rsc_records` / `find_json` /
 * `read_lists` / `read_post`): split the flight stream into `<key>:<json>`
 * rows (including `o<len>,<id>:` length-prefixed rows), keep only rows whose
 * value parses as JSON, then depth-first find the first dict that owns all
 * requested keys. Any structural drift — missing props box, rows without
 * IDs, duplicate IDs, unparsable editor payloads, missing contract fields —
 * fails closed with a thrown Error; this module never silently returns an
 * empty list or a partial record.
 *
 * Boundaries (documented, deliberate):
 *   - Origin defaults to the WORKSPACE domain `https://workspace.laicms.com`
 *     (the editor/list routes live there, path `/{siteKey}/posts/...` —
 *     identical to allincms_api.py ORIGIN), NOT the per-site public domain
 *     `<slug>.web.allincms.com`. Inject `origin` to override.
 *   - The `siteId` returned in the readback record is the RSC payload's own
 *     `siteId` when the editor props carry one; otherwise the factory-bound
 *     siteId is used (the posts editor defaultValues historically omit it).
 *     A conflicting RSC siteId fails closed.
 *   - Pagination uses the `page` query parameter when `pagination.totalPages`
 *     (or `hasNextPage`) reports more data; an unsupported parameter surfaces
 *     as a duplicate-ID fail-closed error, never as a silently truncated
 *     snapshot.
 *   - Reads only. This module never mutates; it never sends the create
 *     request itself (the driver + article-operations own that path).
 *
 * Registered in interface-registry.json as `internal` exposure (adapter
 * wiring surface for content-plan-host-driver / host-run-template), never a
 * public or canonical entry point.
 */

// Mirrors article-operations.mjs `WORKSPACE_ORIGIN` / allincms_api.py ORIGIN.
export const ALLINCMS_ARTICLE_PROVIDERS_DEFAULT_ORIGIN = 'https://workspace.laicms.com';

const POSTS_ROUTE_SEGMENT_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

// The 8 article create contract fields (ARTICLE_CREATE_CONTRACT_FIELDS in
// content-mutation-primitives.mjs). Duplicated here as plain strings only for
// structural drift detection of the parsed editor payload — the canonical
// comparison itself stays owned by the bottom layer.
const ARTICLE_CREATE_FIELDS = ['title', 'slug', 'excerpt', 'order', 'coverImage', 'categories', 'tags', 'content'];

function providerError(message) {
  return new Error(`article-create-providers: ${message}`);
}

function requireSiteSegment(value, label) {
  if (typeof value !== 'string' || !POSTS_ROUTE_SEGMENT_RE.test(value)) {
    throw providerError(`${label} must be a non-empty URL path segment without '/', '?' or '#' (got ${JSON.stringify(value)})`);
  }
  return value;
}

function requireNonEmptyString(value, label) {
  if (typeof value !== 'string' || !value.trim()) {
    throw providerError(`${label} is required (got ${JSON.stringify(value)})`);
  }
  return value;
}

function normalizeOrigin(origin) {
  let parsed;
  try {
    parsed = new URL(origin);
  } catch {
    throw providerError(`origin must be a valid http(s) URL (got ${JSON.stringify(origin)})`);
  }
  if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
    throw providerError(`origin must be http(s) (got ${parsed.protocol})`);
  }
  if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
    throw providerError(`origin must carry no path, query or fragment (got ${JSON.stringify(origin)})`);
  }
  return `${parsed.protocol}//${parsed.host}`;
}

function providerFailure(message) {
  return providerError(message);
}

// --- RSC flight parsing (JS port of allincms_api.py rsc_records/find_json) ---

// Flight row key: `12:` or length-prefixed `o1000,12:`. Mirrors the Python
// RECORD_RE `^((?:[A-Za-z0-9_]+)|(?:o[0-9a-fA-F]+,[A-Za-z0-9_]+)):(.*)$`.
const RSC_ROW_RE = /^(?:[A-Za-z0-9_]+|o[0-9a-fA-F]+,[A-Za-z0-9_]+):(.*)$/;

function rscRecords(text) {
  const out = [];
  for (const rawLine of String(text).split('\n')) {
    const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;
    if (!line) continue;
    const match = RSC_ROW_RE.exec(line);
    if (!match) continue;
    const value = match[1];
    if (!value) continue;
    try {
      out.push(JSON.parse(value));
    } catch {
      // Special-value rows (I[...] / $S... / T... / X / C / R) and reference
      // rows that are not self-contained JSON are skipped, exactly like the
      // Python parser.
    }
  }
  return out;
}

// Depth-first search for the first dict that owns ALL needles (own keys,
// mirroring Python `k in obj` on dicts). Object insertion order and array
// order are preserved, so the traversal matches the Python `_search`.
function searchDict(obj, needles) {
  if (Array.isArray(obj)) {
    for (const item of obj) {
      const found = searchDict(item, needles);
      if (found) return found;
    }
    return null;
  }
  if (obj !== null && typeof obj === 'object') {
    if (needles.every((key) => Object.hasOwn(obj, key))) return obj;
    for (const value of Object.values(obj)) {
      const found = searchDict(value, needles);
      if (found) return found;
    }
  }
  return null;
}

function findJson(records, needles) {
  for (const value of records) {
    const found = searchDict(value, needles);
    if (found) return found;
  }
  return null;
}

// --- HTTP helpers ---

function isSignInLocation(location) {
  return typeof location === 'string' && /sign-in|signin|login/i.test(location);
}

function statusFailure(url, status, location) {
  if (status >= 300 && status < 400) {
    if (isSignInLocation(location)) {
      return providerFailure(`GET ${url} redirected to sign-in (${status} Location=${JSON.stringify(location)}): the payload-token cookie is missing, invalid or expired`);
    }
    return providerFailure(`GET ${url} was redirected (${status} Location=${JSON.stringify(location ?? null)}); a provider read must land on 200, refusing to follow an unexpected redirect`);
  }
  return providerFailure(`GET ${url} returned HTTP ${String(status)}, expected 200`);
}

async function readResponseText(response, url) {
  try {
    return await response.text();
  } catch (error) {
    throw providerFailure(`reading the body of GET ${url} failed (${error?.message})`);
  }
}

/**
 * Create the three real article:create providers over pure-HTTP RSC reads.
 *
 * @param {object} options
 * @param {string} options.siteKey      site slug used in /{siteKey}/posts routes
 * @param {string} options.siteId       site id stamped into the readback record
 * @param {string} options.authCookie   payload-token JWT (the Cookie VALUE, not
 *                                      a full Cookie header; sent as
 *                                      `Cookie: payload-token=<authCookie>`)
 * @param {string} [options.origin]     workspace origin; default
 *                                      https://workspace.laicms.com (the editor
 *                                      pages live on the workspace domain, not
 *                                      the per-site public domain)
 * @param {Function} [options.fetchFn]  fetch-compatible injection for tests
 * @param {number} [options.maxListPages] hard cap on followed list pages
 * @returns {{ beforePostIds: Function, createReadback: Function, editorReopen: Function }}
 */
export function createArticleCreateProviders({
  siteKey,
  siteId,
  authCookie,
  origin = ALLINCMS_ARTICLE_PROVIDERS_DEFAULT_ORIGIN,
  fetchFn,
  maxListPages = 50,
} = {}) {
  const boundSiteKey = requireSiteSegment(siteKey, 'siteKey');
  const boundSiteId = requireNonEmptyString(siteId, 'siteId');
  requireNonEmptyString(authCookie, 'authCookie (payload-token value)');
  if (/[\r\n;]/.test(authCookie)) {
    throw providerError('authCookie must be a single payload-token value without separators (send the raw token, not a full Cookie header)');
  }
  const boundOrigin = normalizeOrigin(origin);
  const fetchImpl = fetchFn === undefined ? fetch : fetchFn;
  if (typeof fetchImpl !== 'function') throw providerError('fetchFn must be a function when provided');
  if (!Number.isInteger(maxListPages) || maxListPages < 1) throw providerError('maxListPages must be a positive integer');

  const baseHeaders = {
    Accept: 'text/x-component',
    'User-Agent': 'Mozilla/5.0 (article-create-providers; pure-HTTP RSC reader)',
    Cookie: `payload-token=${authCookie}`,
  };

  // GET one URL manually-redirected: 307/308 (the RSC router-state redirects,
  // e.g. adding ?_rsc=...) are followed up to 4 hops exactly like
  // allincms_api.py get_page; anything else — including a 302 to sign-in —
  // fails closed instead of being silently followed.
  async function get(url, headers, label) {
    let current = url;
    for (let hop = 0; hop < 5; hop += 1) {
      let response;
      try {
        response = await fetchImpl(current, { method: 'GET', headers, redirect: 'manual' });
      } catch (error) {
        throw providerFailure(`${label}: GET ${current} failed at the transport layer (${error?.message})`);
      }
      if (response === null || typeof response !== 'object' || typeof response.status !== 'number') {
        throw providerFailure(`${label}: GET ${current} returned a non-Response result`);
      }
      const status = response.status;
      const location = typeof response.headers?.get === 'function' ? response.headers.get('location') : null;
      if (status === 200) return { response, status, text: await readResponseText(response, current), url: current };
      if ((status === 307 || status === 308) && location) {
        let next;
        try {
          next = new URL(location, current).toString();
        } catch {
          throw providerFailure(`${label}: GET ${current} redirected (${status}) with an unresolvable Location ${JSON.stringify(location)}`);
        }
        current = next;
        continue;
      }
      throw statusFailure(current, status, location);
    }
    throw providerFailure(`${label}: GET ${url} exceeded the redirect budget`);
  }

  function listUrl(page) {
    const suffix = page > 1 ? `?_rsc=1&page=${String(page)}` : '?_rsc=1';
    return `${boundOrigin}/${boundSiteKey}/posts${suffix}`;
  }

  // Parse one list page's flight stream into { ids, pagination }. Mirrors
  // read_lists: find the props box owning the list data (the full
  // data+pagination+categoryOptions+tagOptions shape first, the minimal
  // data+pagination shape second).
  async function fetchListPage(page) {
    const url = listUrl(page);
    const referer = `${boundOrigin}/${boundSiteKey}/posts`;
    const { text } = await get(url, { ...baseHeaders, RSC: '1', Origin: boundOrigin, Referer: referer }, 'posts list read');
    const records = rscRecords(text);
    if (records.length === 0) {
      throw providerFailure(`posts list read (${url}) yielded no parsable RSC rows; the workspace origin/cookie/path is wrong or the deployment changed its flight shape (fail-closed, no empty snapshot)`);
    }
    const box = findJson(records, ['data', 'pagination', 'categoryOptions', 'tagOptions'])
      ?? findJson(records, ['data', 'pagination']);
    if (!box || !Array.isArray(box.data)) {
      throw providerFailure(`posts list read (${url}) did not contain a list props box with a data array (structure drift; fail-closed, no empty snapshot)`);
    }
    const ids = [];
    for (const [index, row] of box.data.entries()) {
      if (row === null || typeof row !== 'object' || Array.isArray(row)) {
        throw providerFailure(`posts list read (${url}) row ${index} is not an object (structure drift; fail-closed)`);
      }
      if (typeof row.id !== 'string' || !row.id.trim()) {
        throw providerFailure(`posts list read (${url}) row ${index} has no non-empty string id (structure drift; fail-closed)`);
      }
      ids.push(row.id.trim());
    }
    const pagination = (box.pagination !== null && typeof box.pagination === 'object' && !Array.isArray(box.pagination)) ? box.pagination : {};
    return { ids, pagination, url };
  }

  // Full same-site snapshot across list pagination. `page` support is best
  // effort per platform; an unsupported parameter shows up as duplicated
  // rows and fails closed below instead of truncating silently.
  async function fetchAllPostIds() {
    const collected = [];
    const seen = new Set();
    let page = 1;
    let firstPageIds = null;
    while (page <= maxListPages) {
      const { ids, pagination } = await fetchListPage(page);
      if (page === 1) {
        firstPageIds = ids.join('\n');
      } else if (ids.join('\n') === firstPageIds) {
        throw providerFailure(`posts list page ${String(page)} returned the exact first-page rows: the ?page= pagination parameter appears unsupported by this deployment (fail-closed, refusing a silently truncated ID snapshot)`);
      }
      for (const id of ids) {
        if (seen.has(id)) {
          throw providerFailure(`posts list snapshot contains duplicate post id ${JSON.stringify(id)} (page ${String(page)}); fail-closed instead of de-duplicating a drifted snapshot`);
        }
        seen.add(id);
        collected.push(id);
      }
      const totalPages = typeof pagination.totalPages === 'number' && Number.isFinite(pagination.totalPages) ? Math.floor(pagination.totalPages) : null;
      const hasNextPage = pagination.hasNextPage === true;
      const moreByTotalPages = totalPages !== null && page < totalPages;
      const moreByHasNext = totalPages === null && hasNextPage;
      if (!(moreByTotalPages || moreByHasNext)) break;
      if (page >= maxListPages) {
        throw providerFailure(`posts list snapshot exceeded the maxListPages cap (${String(maxListPages)}) while more pages remained; raise maxListPages instead of accepting a truncated ID snapshot (fail-closed)`);
      }
      page += 1;
    }
    return collected;
  }

  // Editor read (RSC). Mirrors read_post: find the props box owning
  // defaultValues, then take its defaultValues as the created record's
  // authoritative field source.
  async function fetchEditorDefaultValues(postId) {
    const url = `${boundOrigin}/${boundSiteKey}/posts/${encodeURIComponent(postId)}/update?_rsc=1`;
    const referer = `${boundOrigin}/${boundSiteKey}/posts`;
    const { text } = await get(url, { ...baseHeaders, RSC: '1', Origin: boundOrigin, Referer: referer }, `editor readback for post ${postId}`);
    const records = rscRecords(text);
    if (records.length === 0) {
      throw providerFailure(`editor readback (${url}) yielded no parsable RSC rows (fail-closed; a sign-in or error page never reaches the comparison)`);
    }
    const box = findJson(records, ['defaultValues']);
    if (!box || box.defaultValues === null || typeof box.defaultValues !== 'object' || Array.isArray(box.defaultValues)) {
      throw providerFailure(`editor readback (${url}) did not contain a defaultValues object (structure drift; fail-closed, no fabricated record)`);
    }
    const defaultValues = box.defaultValues;
    const missing = ARTICLE_CREATE_FIELDS.filter((field) => !Object.hasOwn(defaultValues, field));
    if (missing.length > 0) {
      throw providerFailure(`editor readback (${url}) defaultValues is missing article create contract fields: ${missing.join(', ')} (structure drift; fail-closed, no defaulted record)`);
    }
    return defaultValues;
  }

  // Instance state linking the before snapshot to the create readback. The
  // driver calls beforePostIds() inside execute before the request and
  // createReadback() right after the response, so the memo holds the exact
  // same-site before snapshot the delta is computed against.
  let memoizedBeforePostIds = null;

  return {
    /**
     * articleBeforePostIdsProvider: full same-site post id snapshot before
     * the create request (paginated when the platform reports more pages).
     */
    async beforePostIds() {
      const ids = await fetchAllPostIds();
      memoizedBeforePostIds = ids;
      return [...ids];
    },

    /**
     * articleCreateReadbackProvider: `{ record, afterPostIds }` from the
     * authoritative backend. `args.createdPostId` (when a host supplies it)
     * must agree with the sole before/after delta; without it the delta
     * alone identifies the created post. Both zero and multiple new IDs —
     * and a missing before snapshot — fail closed.
     */
    async createReadback(args = {}) {
      const afterPostIds = await fetchAllPostIds();
      let createdPostId = null;
      if (args !== null && typeof args === 'object' && typeof args.createdPostId === 'string' && args.createdPostId.trim()) {
        createdPostId = args.createdPostId.trim();
        requireSiteSegment(createdPostId, 'createdPostId');
      }
      if (memoizedBeforePostIds !== null) {
        const known = new Set(memoizedBeforePostIds);
        const newIds = afterPostIds.filter((id) => !known.has(id));
        if (newIds.length !== 1) {
          throw providerFailure(`expected exactly one new post id in the before/after snapshot delta, found ${String(newIds.length)} (before ${String(memoizedBeforePostIds.length)} ids, after ${String(afterPostIds.length)} ids); fail-closed instead of guessing the created post`);
        }
        if (createdPostId === null) {
          createdPostId = newIds[0];
        } else if (createdPostId !== newIds[0]) {
          throw providerFailure(`args.createdPostId ${JSON.stringify(createdPostId)} drifted from the sole before/after snapshot delta ${JSON.stringify(newIds[0])}; fail-closed instead of trusting either side`);
        }
      } else if (createdPostId === null) {
        throw providerFailure('createReadback requires either args.createdPostId or a before snapshot taken through this provider set\'s beforePostIds() first (fail-closed, no fabricated delta)');
      }
      const defaultValues = await fetchEditorDefaultValues(createdPostId);
      if (Object.hasOwn(defaultValues, 'siteId') && defaultValues.siteId !== null && defaultValues.siteId !== undefined) {
        if (defaultValues.siteId !== boundSiteId) {
          throw providerFailure(`editor readback for post ${createdPostId} reports siteId ${JSON.stringify(defaultValues.siteId)} but the operation is bound to ${JSON.stringify(boundSiteId)} (cross-site record; fail-closed)`);
        }
      }
      const record = { ...defaultValues, id: createdPostId, siteId: boundSiteId };
      return { record, afterPostIds };
    },

    /**
     * articleEditorReopenProvider: actually re-open the created editor over
     * plain HTML (no RSC header — exactly like a browser re-open) and assert
     * HTTP 200, no sign-in redirect, and that the returned document still
     * carries this post's edit context.
     */
    async editorReopen(args = {}) {
      const createdPostId = requireNonEmptyString(
        args !== null && typeof args === 'object' ? args.createdPostId : undefined,
        'editorReopen args.createdPostId',
      );
      requireSiteSegment(createdPostId, 'createdPostId');
      const url = `${boundOrigin}/${boundSiteKey}/posts/${encodeURIComponent(createdPostId)}/update`;
      const { text } = await get(
        url,
        { Accept: 'text/html,application/xhtml+xml', 'User-Agent': baseHeaders['User-Agent'], Cookie: baseHeaders.Cookie },
        `editor reopen for post ${createdPostId}`,
      );
      if (!text.includes(createdPostId)) {
        throw providerFailure(`reopened editor (${url}) returned HTTP 200 but the document does not contain the created post id ${JSON.stringify(createdPostId)}: the edit context is missing (an authenticated sign-in or error page would look exactly like this; fail-closed)`);
      }
      return { status: 200, authenticated: true, healthy: true, postId: createdPostId };
    },
  };
}
