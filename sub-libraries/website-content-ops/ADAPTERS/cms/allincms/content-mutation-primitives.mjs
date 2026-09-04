/**
 * AllinCMS adapter-internal content mutation safety primitives.
 *
 * Single machine truth for the safety-critical helpers that article
 * (article-operations.mjs) and product (product-operations.mjs) mutations
 * MUST share bit-for-bit:
 *
 *   - `markRequestStarted`: transport-error requestStarted semantics. Every
 *     send path (native client and authorized injected-client wrapper) marks
 *     real transport errors requestStarted=true so runActionWithRecovery
 *     reconciles instead of blindly rethrowing or resending.
 *   - `extractCreateReadbackRecord` + `createdRecordExpectedProblems` +
 *     `canonicalTexts`: the irreplaceable canonical create-readback record
 *     extraction/comparison used by both createPostDraft and
 *     createProductDraft. No caller callback can replace or waive it.
 *   - `prepareStableCreatePayload` (2026-09-04 stable create payload B1): the
 *     one synchronous descriptor-only projection from caller input to a deep-
 *     frozen stable JSON snapshot plus its single immutable canonical
 *     `payloadText`. The article/product bottom create functions and the host
 *     driver both call this exact function, so input validation, the wire
 *     body, the authorization digest, and the expected-readback comparison
 *     can never consume three different shapes of the same create.
 *   - `captureStableReadback` (2026-09-04 stable create payload B2): the
 *     one-shot stable projection of a create readback. The canonical
 *     comparison and every caller getter consume this same snapshot, so a
 *     getter/proxy readback cannot serve one record to the comparison and a
 *     different record to ID extraction.
 *   - `ARTICLE_CREATE_CONTRACT_FIELDS` / `PRODUCT_CREATE_CONTRACT_FIELDS`:
 *     the canonical create contract field lists compared against the
 *     authoritative readback record (8 article / 10 product fields + siteId).
 *
 * WHY A DEDICATED MODULE (2026-09-04 poisoning fix): product-operations.mjs
 * used to consume these functions by destructuring the mutable `_internal`
 * export object of article-operations.mjs at first import. An external actor
 * that imported article-operations first could overwrite
 * `_internal.markRequestStarted` / `_internal.createdRecordExpectedProblems`
 * before product's first import, silently skipping post-request reconcile or
 * accepting field drift. Cross-module sharing now happens exclusively through
 * named ESM imports of this module. ESM export bindings are immutable
 * (module namespace properties are non-writable/non-configurable), so this
 * channel cannot be poisoned by property assignment from any importer.
 *
 * This module is dependency-free (no imports) by design: it must never become
 * part of an import cycle, and its functions are pure transforms except
 * `markRequestStarted`, which only annotates/wraps the error it is given.
 * It is adapter-internal surface: registered in interface-registry.json as
 * `internal` exposure, never a public/canonical entry point.
 */

// P0-3.3a create canonical contract fields (8 + siteId, article). Single
// machine truth for both the article create expected comparison and the host
// driver's desired-state strict field validation; callers can neither add nor
// remove compared fields.
export const ARTICLE_CREATE_CONTRACT_FIELDS = Object.freeze([
  'title', 'slug', 'excerpt', 'order', 'coverImage',
  'categories', 'tags', 'content',
]);

// P0-3.3a create canonical contract fields (10 + siteId, product). Single
// machine truth for both the product create expected comparison and the host
// driver's desired-state strict field validation; callers can neither add nor
// remove compared fields.
export const PRODUCT_CREATE_CONTRACT_FIELDS = Object.freeze([
  'name', 'slug', 'description', 'order', 'media', 'mediaList',
  'content', 'categories', 'tags', 'specifications',
]);

// Canonical stable text for create-readback comparison: object key order is
// irrelevant (keys are sorted), array order is strict, and non-JSON values are
// stringified by type so `undefined` can never equal `null` or `''`.
export function canonicalTexts(value) {
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number') return String(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (Array.isArray(value)) return `[${value.map(canonicalTexts).join(',')}]`;
  if (typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalTexts(value[key])}`).join(',')}}`;
  return 'undefined';
}

// P0-3.3a.3 bottom-owned create-readback record extraction. The host create
// readback is either the known `{ record, afterIds }` wrapper or a bare
// record. The rule is fixed data-shape logic inside this module: no
// caller-supplied callback can select which object gets compared, so the
// extraction channel cannot be used to point the comparison at a
// caller-fabricated object any more than the readback itself could.
export function extractCreateReadbackRecord(actual) {
  if (actual !== null && typeof actual === 'object' && !Array.isArray(actual) && Object.hasOwn(actual, 'record')) {
    return actual.record;
  }
  return actual;
}

// P0-3.3a.3 comparison-only normalization for the canonical create expected
// comparison. These helpers NEVER feed the request payload or the
// authorization digest (both use the frozen payload verbatim); they only
// decide whether the authoritative readback record matches the expected
// payload on the canonical contract fields. Missing contract fields are
// problems — they are never defaulted or skipped.
function normalizedTaxonomyIdList(value, field, kind) {
  if (!Array.isArray(value)) return { error: `${kind} create record ${field} must be an array of taxonomy IDs` };
  const ids = [];
  for (const entry of value) {
    if (typeof entry === 'string') {
      if (!entry.trim()) return { error: `${kind} create record ${field} carries an empty taxonomy ID` };
      ids.push(entry.trim());
      continue;
    }
    if (entry && typeof entry === 'object' && !Array.isArray(entry) && Object.hasOwn(entry, 'id')) {
      if (typeof entry.id !== 'string' || !entry.id.trim()) return { error: `${kind} create record ${field} carries a non-string taxonomy id` };
      ids.push(entry.id.trim());
      continue;
    }
    return { error: `${kind} create record ${field} entries must be taxonomy ID strings or {id} objects` };
  }
  if (new Set(ids).size !== ids.length) return { error: `${kind} create record ${field} carries duplicate taxonomy IDs` };
  return { ids: [...ids].sort() };
}

function unwrappedMediaValue(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return { wrapperType: null, core: value };
  const typeIsString = Object.hasOwn(value, 'type') && typeof value.type === 'string';
  const hasValue = Object.hasOwn(value, 'value');
  if (typeIsString && hasValue) return { wrapperType: value.type, core: value.value };
  return { wrapperType: null, core: value };
}

// The media `type` a comparison can see on a flat media object, if any. Only
// own-data reads run here: both sides of every media comparison are either the
// frozen prepared snapshot or the captured stable readback copy, never a live
// getter/proxy object.
function mediaTypeOf(core) {
  if (core !== null && typeof core === 'object' && !Array.isArray(core) && typeof core.type === 'string') return core.type;
  return null;
}

// Comparison-only alt normalization: `alt` is normalized to missing on the
// write path (string/null/missing are all accepted and dropped), so both
// sides of the media comparison drop a string/null alt before canonical
// comparison. Any other alt value survives and fails the canonical
// comparison fail-closed.
function comparableMediaCore(core) {
  if (core === null || typeof core !== 'object' || Array.isArray(core)) return core;
  if (!Object.hasOwn(core, 'alt')) return core;
  if (core.alt === null || typeof core.alt === 'string') {
    const comparable = { ...core };
    delete comparable.alt;
    return comparable;
  }
  return core;
}

// 2026-09-04 single-sided media wrapper type conflict fix: a readback may be
// flat URL/OSS media or a one-level editor `{type, value}` wrapper, but the
// wrapper's outer type must agree with the wrapped media's own type and with
// the frozen expected effective media type. The wrapper is comparison-only:
// it can never enter the write path (prepareStableCreatePayload refuses it).
function mediaComparisonProblem(expectedMedia, actualMedia, field, kind) {
  const expected = unwrappedMediaValue(expectedMedia);
  const actual = unwrappedMediaValue(actualMedia);
  const expectedType = mediaTypeOf(expected.core);
  const actualInnerType = mediaTypeOf(actual.core);
  if (actual.wrapperType !== null) {
    if (actualInnerType !== null && actualInnerType !== actual.wrapperType) {
      return `${kind} create record ${field} media wrapper type ${JSON.stringify(actual.wrapperType)} conflicts with the wrapped media type ${JSON.stringify(actualInnerType)}`;
    }
    if (expected.wrapperType === null && expectedType !== null && expectedType !== actual.wrapperType) {
      return `${kind} create record ${field} media wrapper type ${JSON.stringify(actual.wrapperType)} conflicts with the frozen expected media type ${JSON.stringify(expectedType)}`;
    }
  }
  if (expected.wrapperType !== null && actual.wrapperType !== null && expected.wrapperType !== actual.wrapperType) {
    return `${kind} create record ${field} media wrapper type ${JSON.stringify(actual.wrapperType)} conflicts with the frozen expected ${JSON.stringify(expected.wrapperType)}`;
  }
  if (canonicalTexts(comparableMediaCore(expected.core)) !== canonicalTexts(comparableMediaCore(actual.core))) {
    return `${field} drifted from the frozen expected payload`;
  }
  return null;
}

function mediaListComparisonProblem(expectedList, actualList, field, kind) {
  if (!Array.isArray(expectedList) || !Array.isArray(actualList)) {
    return canonicalTexts(expectedList) !== canonicalTexts(actualList)
      ? `${field} drifted from the frozen expected payload`
      : null;
  }
  if (expectedList.length !== actualList.length) return `${field} drifted from the frozen expected payload`;
  for (const index of expectedList.keys()) {
    const problem = mediaComparisonProblem(expectedList[index], actualList[index], `${field}[${index}]`, kind);
    if (problem) return problem;
  }
  return null;
}

// The irreplaceable canonical expected comparison for article/product create.
// Returns the list of human-readable problems (empty means PASS). Every
// canonical contract field plus siteId must be an own field of the record with
// an equal value; taxonomy lists normalize plain IDs and `{id}` wrappers
// order-insensitively; media fields (product media/mediaList, article
// coverImage) unwrap one editor `{type, value}` wrapper whose outer type must
// agree with the wrapped/expected effective type and normalize a string/null
// alt away; everything else compares by canonicalTexts (key-order-insensitive
// objects, strict array order). Backend-only fields outside the contract are
// ignored. This function is only ever called with this module's own
// `extractCreateReadbackRecord` result over a captured stable readback and the
// bound prepared `expected` snapshot — never with a caller-supplied boolean or
// record selector.
export function createdRecordExpectedProblems(record, expected, contractFields, kind) {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    return [`${kind} create readback record must be a non-array object`];
  }
  const problems = [];
  for (const field of [...contractFields, 'siteId']) {
    if (!Object.hasOwn(record, field)) {
      problems.push(`${field} is missing from the created ${kind} record`);
      continue;
    }
    if (field === 'categories' || field === 'tags') {
      const expectedIds = normalizedTaxonomyIdList(expected[field], field, kind);
      const actualIds = normalizedTaxonomyIdList(record[field], field, kind);
      if (expectedIds.error || actualIds.error) {
        problems.push(expectedIds.error || actualIds.error);
        continue;
      }
      if (JSON.stringify(expectedIds.ids) !== JSON.stringify(actualIds.ids)) {
        problems.push(`${field} drifted from the frozen expected payload`);
      }
      continue;
    }
    if (field === 'media' || field === 'coverImage') {
      const problem = mediaComparisonProblem(expected[field], record[field], field, kind);
      if (problem) problems.push(problem);
      continue;
    }
    if (field === 'mediaList') {
      const problem = mediaListComparisonProblem(expected[field], record[field], field, kind);
      if (problem) problems.push(problem);
      continue;
    }
    if (canonicalTexts(record[field]) !== canonicalTexts(expected[field])) {
      problems.push(`${field} drifted from the frozen expected payload`);
    }
  }
  return problems;
}

// Descriptor-only own-data string read. Getters are NEVER invoked: an accessor
// `requestStarted`/`message` on a hostile error only has to answer the reads
// that happen inside the marking function and lie afterwards (TOCTOU), so the
// only safe channel is the property descriptor's recorded data value. A Proxy
// whose getOwnPropertyDescriptor trap throws, an accessor descriptor, a
// non-string data value, or an inherited (prototype) property all yield the
// placeholder. The returned value can never trigger attacker code.
function safeOwnDataString(error, key, placeholder) {
  let descriptor;
  try {
    descriptor = Object.getOwnPropertyDescriptor(error, key);
  } catch {
    return placeholder; // e.g. a Proxy whose getOwnPropertyDescriptor trap throws.
  }
  try {
    if (descriptor
      && descriptor.get === undefined && descriptor.set === undefined
      && typeof descriptor.value === 'string') {
      return descriptor.value;
    }
  } catch {
    return placeholder;
  }
  return placeholder;
}

const UNAVAILABLE_MESSAGE = '[transport failed: original message unavailable (accessor/proxy message was not invoked)]';

// Shared transport-error marking semantics (P0-A): a real transport failure
// after the request was handed to the wire is ambiguous — the server may have
// processed it. Marking requestStarted=true routes the failure into
// runActionWithRecovery's readback reconcile path instead of a blind rethrow
// (which could be retried into a duplicate). Never called for authorization
// or validation failures, which must fail hard before/without requestStarted.
//
// TOCTOU fix (2026-09-04): the original error object is NEVER trusted,
// mutated, or returned, no matter how benign it looks. The previous
// read-then-write-then-read sequence (`error.requestStarted = error.requestStarted ?? true;
// if (error.requestStarted === true) return error;`) could be defeated by an
// accessor that answers `true` for exactly those reads and `false` for every
// downstream read (runActionWithRecovery's `error?.requestStarted === true`,
// the controller's `error?.requestStarted !== false`), silently skipping the
// mandatory post-request reconcile. Frozen, cross-realm, Proxy, setter-backed,
// and later-mutated data properties are the same class of lie. Therefore this
// function ALWAYS returns a fresh ordinary Error wrapper whose own
// `requestStarted` is a non-writable, non-configurable data property with the
// permanent value `true` — every read by every downstream consumer, at any
// time, sees true, and no caller can flip it back. Message/name/stack are
// copied only through `safeOwnDataString` descriptor reads (never getters);
// `cause` keeps the original error by reference for debugging and is attached
// via defineProperty (a polluted `Object.prototype.cause` setter can never
// run). The wrapper is always a plain Error of this realm: class
// identity is intentionally not preserved because inheriting the original's
// prototype chain would re-open the accessor channel.
export function markRequestStarted(error) {
  const source = error !== null && (typeof error === 'object' || typeof error === 'function') ? error : null;
  const message = source === null
    ? String(error)
    : safeOwnDataString(source, 'message', UNAVAILABLE_MESSAGE);
  const wrapped = new Error(message);
  // `cause` is attached with defineProperty, never plain assignment: a
  // polluted `Object.prototype.cause` setter would otherwise run during this
  // assignment, throw, and replace the wrapper with an unlocked error — a
  // sent request would then skip readback reconciliation.
  Object.defineProperty(wrapped, 'cause', {
    value: error,
    writable: false,
    enumerable: false,
    configurable: false,
  });
  const name = source === null ? null : safeOwnDataString(source, 'name', null);
  if (name !== null) {
    // defineProperty, not assignment: a polluted `Error.prototype.name` setter
    // would otherwise throw here and replace the locked wrapper.
    Object.defineProperty(wrapped, 'name', {
      value: name,
      writable: true,
      enumerable: false,
      configurable: true,
    });
  }
  const stack = source === null ? null : safeOwnDataString(source, 'stack', null);
  if (stack !== null) wrapped.stack = stack;
  Object.defineProperty(wrapped, 'requestStarted', {
    value: true,
    writable: false,
    enumerable: false,
    configurable: false,
  });
  return wrapped;
}

// ---------------------------------------------------------------------------
// 2026-09-04 stable create payload B1: one synchronous, descriptor-only
// projection from caller input to a deep-frozen stable JSON snapshot plus a
// single immutable canonical payloadText. The bottom create functions
// (createPostDraft/createProductDraft) and the host driver both call
// prepareStableCreatePayload, and after it returns neither ever reads the
// caller's original object again, so Date/Map/accessor/Proxy/TOCTOU inputs and
// post-prepare mutations can no longer desynchronize the validated input, the
// authorization digest, the wire body, and the expected readback.
// ---------------------------------------------------------------------------

const STABLE_CREATE_KINDS = new Set(['article', 'product']);
const CREATE_CONTRACT_FIELDS_BY_KIND = Object.freeze({
  article: ARTICLE_CREATE_CONTRACT_FIELDS,
  product: PRODUCT_CREATE_CONTRACT_FIELDS,
});

// Branding for already-prepared snapshots: a private module-level WeakMap from
// the frozen snapshot object to its kind + payloadText. A WeakMap key is not
// an own property, so the canonical serialization stays clean, and no external
// actor can forge or enumerate the brand. Re-preparing a branded snapshot
// returns the SAME object and text instead of rebuilding a second semantics.
const STABLE_CREATE_BRANDS = new WeakMap();

function stableDataRefusal(label, detail) {
  return new Error(`${label} is not stable plain data: ${detail}`);
}

function ownKeysOrFail(value, label) {
  try {
    return Reflect.ownKeys(value);
  } catch (trapError) {
    throw stableDataRefusal(label, `enumerating own keys threw (${trapError?.message})`);
  }
}

// Descriptor-only own-data property read. Getters/setters are never invoked
// (an accessor can answer every read differently — TOCTOU), a disappeared key
// (mutated between enumeration and read) fails closed, and a non-enumerable
// own data property is refused instead of being silently dropped from the
// snapshot.
function ownDataDescriptorOrFail(value, key, label) {
  let descriptor;
  try {
    descriptor = Object.getOwnPropertyDescriptor(value, key);
  } catch (trapError) {
    throw stableDataRefusal(label, `reading the own descriptor of ${String(key)} threw (${trapError?.message})`);
  }
  if (!descriptor) throw stableDataRefusal(label, `the own key ${String(key)} disappeared between enumeration and descriptor read`);
  if (descriptor.get !== undefined || descriptor.set !== undefined) {
    throw stableDataRefusal(label, `${String(key)} is an accessor property; getters are never invoked`);
  }
  if (!descriptor.enumerable) {
    throw stableDataRefusal(label, `${String(key)} is a non-enumerable own property`);
  }
  return descriptor;
}

// Array `length` is a non-enumerable own data property by specification, so it
// gets its own descriptor read (the length VALUE comes from the descriptor,
// never from a [[Get]] that a Proxy could trap).
function arrayLengthDescriptorOrFail(value, label) {
  let descriptor;
  try {
    descriptor = Object.getOwnPropertyDescriptor(value, 'length');
  } catch (trapError) {
    throw stableDataRefusal(label, `reading the own length descriptor threw (${trapError?.message})`);
  }
  if (!descriptor || descriptor.get !== undefined || descriptor.set !== undefined) {
    throw stableDataRefusal(label, 'length is not an own data property');
  }
  if (typeof descriptor.value !== 'number' || !Number.isInteger(descriptor.value) || descriptor.value < 0) {
    throw stableDataRefusal(label, 'length is not a non-negative integer');
  }
  return descriptor;
}

const CANONICAL_ARRAY_INDEX = /^(?:0|[1-9][0-9]*)$/;

// The one synchronous stable copy. Allowed: null, boolean, string, finite
// non-negative-zero number, dense plain array, plain object. Refused:
// undefined, function, symbol, bigint, NaN/Infinity/-0, every non-plain
// prototype (Date, Map, Set, Error, RegExp, typed arrays, class instances,
// cross-realm values), cycles, symbol keys, accessor properties,
// non-enumerable properties, sparse arrays, arrays with extra own keys, and
// any Proxy whose traps throw. A Proxy that behaves exactly like a plain
// object cannot be absolutely distinguished; its declared descriptor data is
// copied once and the original object is never used again afterwards.
function copyStableValue(value, label, seen) {
  if (value === null) return null;
  const type = typeof value;
  if (type === 'string' || type === 'boolean') return value;
  if (type === 'number') {
    if (!Number.isFinite(value)) throw stableDataRefusal(label, 'carries NaN, Infinity, or -Infinity');
    if (Object.is(value, -0)) throw stableDataRefusal(label, 'carries negative zero');
    return value;
  }
  if (type === 'undefined') throw stableDataRefusal(label, 'carries the undefined value');
  if (type === 'function') throw stableDataRefusal(label, 'carries a function value');
  if (type === 'symbol') throw stableDataRefusal(label, 'carries a symbol value');
  if (type === 'bigint') throw stableDataRefusal(label, 'carries a bigint value');
  let prototype;
  try {
    prototype = Object.getPrototypeOf(value);
  } catch (trapError) {
    throw stableDataRefusal(label, `reading the prototype threw (${trapError?.message})`);
  }
  if (seen.has(value)) throw stableDataRefusal(label, 'contains a reference cycle');
  seen.add(value);
  try {
    if (Array.isArray(value)) {
      if (prototype !== Array.prototype) {
        throw stableDataRefusal(label, 'is an array with a non-standard (subclassed or cross-realm) prototype');
      }
      const length = arrayLengthDescriptorOrFail(value, label).value;
      const keys = ownKeysOrFail(value, label);
      const indexKeys = [];
      for (const key of keys) {
        if (key === 'length') continue;
        if (typeof key !== 'string' || !CANONICAL_ARRAY_INDEX.test(key) || Number(key) >= length) {
          throw stableDataRefusal(label, 'is a sparse array or carries extra own keys beyond its dense indices');
        }
        indexKeys.push(key);
      }
      if (indexKeys.length !== length) {
        throw stableDataRefusal(label, 'is a sparse array (holes are refused)');
      }
      const copy = [];
      for (let index = 0; index < length; index += 1) {
        const descriptor = ownDataDescriptorOrFail(value, String(index), label);
        copy.push(copyStableValue(descriptor.value, `${label}[${index}]`, seen));
      }
      return copy;
    }
    if (prototype !== Object.prototype && prototype !== null) {
      throw stableDataRefusal(label, 'is an object with a non-plain prototype (Date, Map, Set, Error, RegExp, typed arrays, class instances and other exotics are refused)');
    }
    const keys = ownKeysOrFail(value, label);
    const copy = {};
    for (const key of keys) {
      if (typeof key === 'symbol') throw stableDataRefusal(label, `carries the symbol key ${String(key)}`);
      const descriptor = ownDataDescriptorOrFail(value, key, label);
      copy[key] = copyStableValue(descriptor.value, `${label}.${key}`, seen);
    }
    return copy;
  } finally {
    seen.delete(value);
  }
}

function deepFreezeStableData(value) {
  if (value !== null && typeof value === 'object') {
    for (const key of Object.keys(value)) deepFreezeStableData(value[key]);
    Object.freeze(value);
  }
  return value;
}

// Canonical serialization of validated stable data: sorted object keys, strict
// array order, JSON.stringify scalars. Byte-identical to the canonicalJson of
// mutation-authorization.mjs for every value that can appear in a prepared
// snapshot, which is what lets the authorization digest hash payloadText
// directly while still being verifiable against the snapshot object.
export function canonicalStableCreateText(value) {
  if (value === null) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((item) => canonicalStableCreateText(item)).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalStableCreateText(value[key])}`).join(',')}}`;
}

function stableNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.trim() === '') throw new Error(`${label} must be a non-empty string`);
  return value;
}

function stableStringList(value, field, kind) {
  if (!Array.isArray(value)) throw new Error(`${kind} create payload ${field} must be a dense array of non-empty ID strings`);
  const trimmed = [];
  for (const [index, item] of value.entries()) {
    stableNonEmptyString(item, `${kind} create payload ${field}[${index}]`);
    trimmed.push(item.trim());
  }
  if (new Set(trimmed).size !== trimmed.length) throw new Error(`${kind} create payload ${field} must not contain duplicate IDs`);
  return value;
}

function collectSlateIds(node, ids, label) {
  if (Array.isArray(node)) {
    for (const [index, child] of node.entries()) collectSlateIds(child, ids, `${label}[${index}]`);
    return;
  }
  if (node === null || typeof node !== 'object') return;
  if (Object.hasOwn(node, 'id')) {
    stableNonEmptyString(node.id, `${label}.id`);
    if (ids.has(node.id)) throw new Error(`${label}.id duplicates the Slate node id ${node.id}`);
    ids.add(node.id);
  }
  for (const [key, child] of Object.entries(node)) collectSlateIds(child, ids, `${label}.${key}`);
}

function stableSlateContent(value, kind) {
  if (!Array.isArray(value)) throw new Error(`${kind} create payload content must be a dense array of Slate nodes`);
  const ids = new Set();
  for (const [index, node] of value.entries()) {
    if (node === null || typeof node !== 'object' || Array.isArray(node)) {
      throw new Error(`${kind} create payload content[${index}] must be a Slate node object`);
    }
    stableNonEmptyString(node.type, `${kind} create payload content[${index}].type`);
    if (!Array.isArray(node.children)) {
      throw new Error(`${kind} create payload content[${index}].children must be a dense array`);
    }
    collectSlateIds(node, ids, `${kind} create payload content[${index}]`);
  }
  return value;
}

// Flat URL/OSS media union for the create write path. The editor
// `{type, value}` wrapper is WRITE-REFUSED (it is a readback-comparison shape
// only); URL media may never carry path/size/mimeType, OSS media may never
// carry url, type must be exactly 'image', and a string/null/missing alt is
// normalized to missing (dropped) on both sides of the comparison.
function normalizeStableMediaValue(value, label, { allowNull }) {
  if (value === null) {
    if (allowNull) return null;
    throw new Error(`${label} must be a non-null flat URL or OSS media object (null and {type,value} editor wrappers are refused on the create write path)`);
  }
  if (typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} must be a flat URL or OSS media object`);
  }
  if (Object.hasOwn(value, 'type') && Object.hasOwn(value, 'value')) {
    throw new Error(`${label} must be flat URL/OSS media; the {type,value} editor wrapper is a readback shape and is refused on the create write path`);
  }
  if (value.source !== 'url' && value.source !== 'oss') {
    throw new Error(`${label}.source must be exactly 'url' or 'oss'`);
  }
  const forbidden = value.source === 'url' ? ['path', 'size', 'mimeType'] : ['url'];
  for (const key of forbidden) {
    if (Object.hasOwn(value, key)) {
      throw new Error(`${label} (${value.source} media) must not carry the ${value.source === 'url' ? 'OSS-only' : 'URL-only'} field ${key}`);
    }
  }
  const allowed = value.source === 'url'
    ? ['name', 'type', 'source', 'url', 'alt']
    : ['name', 'type', 'source', 'path', 'size', 'mimeType', 'alt'];
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) throw new Error(`${label} carries the unknown media field ${key}`);
  }
  stableNonEmptyString(value.name, `${label}.name`);
  if (value.type !== 'image') throw new Error(`${label}.type must be exactly 'image'`);
  if (Object.hasOwn(value, 'alt') && value.alt !== null && typeof value.alt !== 'string') {
    throw new Error(`${label}.alt must be a string or null when present`);
  }
  const normalized = { name: value.name, type: 'image', source: value.source };
  if (value.source === 'url') {
    if (typeof value.url !== 'string' || value.url.trim() === '') throw new Error(`${label}.url is required and must be a non-empty string`);
    let parsed;
    try {
      parsed = new URL(value.url);
    } catch {
      throw new Error(`${label}.url must be an absolute http:// or https:// URL`);
    }
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      throw new Error(`${label}.url must be an absolute http:// or https:// URL`);
    }
    normalized.url = value.url;
    return normalized;
  }
  stableNonEmptyString(value.path, `${label}.path`);
  if (!Number.isInteger(value.size) || value.size < 0) throw new Error(`${label}.size must be a non-negative integer`);
  stableNonEmptyString(value.mimeType, `${label}.mimeType`);
  normalized.path = value.path;
  normalized.size = value.size;
  normalized.mimeType = value.mimeType;
  return normalized;
}

function normalizeStableMediaList(value, label) {
  if (!Array.isArray(value)) throw new Error(`${label} must be a dense array of flat URL/OSS media objects`);
  return value.map((item, index) => normalizeStableMediaValue(item, `${label}[${index}]`, { allowNull: false }));
}

function normalizeStableSpecifications(value) {
  if (!Array.isArray(value)) throw new Error('product create payload specifications must be a dense array');
  return value.map((row, index) => {
    if (row === null || typeof row !== 'object' || Array.isArray(row)) {
      throw new Error(`product create payload specifications[${index}] must be an object owning exactly the fields key and value`);
    }
    const keys = Object.keys(row);
    if (keys.length !== 2 || !keys.includes('key') || !keys.includes('value')) {
      throw new Error(`product create payload specifications[${index}] must own exactly the fields key and value`);
    }
    stableNonEmptyString(row.key, `product create payload specifications[${index}].key`);
    stableNonEmptyString(row.value, `product create payload specifications[${index}].value`);
    if (row.value.length > 200) {
      throw new Error(`product create payload specifications[${index}].value must be at most 200 characters`);
    }
    return { key: row.key, value: row.value };
  });
}

function stableString(value, label) {
  if (typeof value !== 'string') throw new Error(`${label} must be a string`);
  return value;
}

function stableInteger(value, label) {
  if (!Number.isInteger(value)) throw new Error(`${label} must be an integer`);
  return value;
}

// Semantic validation + normalization over the already-copied stable values.
// Building the snapshot object literal fixes the field set (exactly the
// contract fields + siteId — never a caller key) and the normalized shapes.
function buildStableCreateSnapshot(kind, copied, siteId) {
  if (kind === 'article') {
    return {
      title: stableNonEmptyString(copied.title, 'article create payload title'),
      slug: stableNonEmptyString(copied.slug, 'article create payload slug'),
      excerpt: stableString(copied.excerpt, 'article create payload excerpt'),
      order: stableInteger(copied.order, 'article create payload order'),
      coverImage: normalizeStableMediaValue(copied.coverImage, 'article create payload coverImage', { allowNull: true }),
      categories: stableStringList(copied.categories, 'categories', 'article'),
      tags: stableStringList(copied.tags, 'tags', 'article'),
      content: stableSlateContent(copied.content, 'article'),
      siteId,
    };
  }
  return {
    name: stableNonEmptyString(copied.name, 'product create payload name'),
    slug: stableNonEmptyString(copied.slug, 'product create payload slug'),
    description: stableNonEmptyString(copied.description, 'product create payload description'),
    order: stableInteger(copied.order, 'product create payload order'),
    media: normalizeStableMediaValue(copied.media, 'product create payload media', { allowNull: false }),
    mediaList: normalizeStableMediaList(copied.mediaList, 'product create payload mediaList'),
    content: stableSlateContent(copied.content, 'product'),
    categories: stableStringList(copied.categories, 'categories', 'product'),
    tags: stableStringList(copied.tags, 'tags', 'product'),
    specifications: normalizeStableSpecifications(copied.specifications),
    siteId,
  };
}

// B1 entry point: kind ('article'|'product') + payload (contract fields, with
// an optional matching siteId) + siteId -> { snapshot, payloadText }.
//
// The snapshot is a deep-frozen plain-data object owning exactly the contract
// fields plus siteId; payloadText is its single immutable canonical JSON
// serialization (sorted keys). Re-preparing an already-branded frozen
// snapshot returns the SAME object and text, so the driver-to-bottom-layer
// handoff never rebuilds a second, differently-semantic payload. This
// function is synchronous and performs no I/O; it throws before any request
// on every refusal.
export function prepareStableCreatePayload(kind, payload, siteId) {
  if (!STABLE_CREATE_KINDS.has(kind)) {
    throw new Error(`stable create payload kind must be 'article' or 'product' (got ${JSON.stringify(kind)})`);
  }
  if (typeof siteId !== 'string' || siteId.trim() === '') {
    throw new Error(`${kind} create payload siteId must be a non-empty string`);
  }
  const normalizedSiteId = siteId.trim();
  const brand = STABLE_CREATE_BRANDS.get(payload);
  if (brand !== undefined) {
    if (brand.kind !== kind) {
      throw new Error(`${kind} create payload is already a prepared frozen ${brand.kind} create snapshot; re-preparing under a different kind is refused`);
    }
    if (!Object.isFrozen(payload)) {
      throw new Error(`${kind} create payload branding requires a still-frozen snapshot`);
    }
    if (payload.siteId !== normalizedSiteId) {
      throw new Error(`${kind} create payload.siteId must match siteId`);
    }
    if (canonicalStableCreateText(payload) !== brand.payloadText) {
      throw new Error(`${kind} create payload snapshot no longer serializes to its frozen payload text`);
    }
    return { snapshot: payload, payloadText: brand.payloadText };
  }
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${kind} create payload must be a non-array object`);
  }
  let prototype;
  try {
    prototype = Object.getPrototypeOf(payload);
  } catch (trapError) {
    throw stableDataRefusal(`${kind} create payload`, `reading the prototype threw (${trapError?.message})`);
  }
  if (prototype !== Object.prototype && prototype !== null) {
    throw new Error(`${kind} create payload must be a plain object (class instances and exotics are refused before any request)`);
  }
  const ownKeys = ownKeysOrFail(payload, `${kind} create payload`);
  for (const key of ownKeys) {
    if (typeof key === 'symbol') throw stableDataRefusal(`${kind} create payload`, `carries the symbol key ${String(key)}`);
  }
  const contractFields = CREATE_CONTRACT_FIELDS_BY_KIND[kind];
  const allowed = new Set([...contractFields, 'siteId']);
  const extras = ownKeys.filter((key) => !allowed.has(key));
  if (extras.length > 0) {
    throw new Error(`${kind} create payload carries unknown extra field(s): ${extras.join(', ')} (exactly [${[...contractFields].join(', ')}] plus siteId are accepted; missing and extra fields are both refused)`);
  }
  const missing = contractFields.filter((field) => !ownKeys.includes(field));
  if (missing.length > 0) {
    throw new Error(`${kind} create payload is missing the contract field(s): ${missing.join(', ')} (missing fields are never defaulted)`);
  }
  if (Object.hasOwn(payload, 'siteId')) {
    const siteIdDescriptor = ownDataDescriptorOrFail(payload, 'siteId', `${kind} create payload`);
    if (siteIdDescriptor.value !== normalizedSiteId) {
      throw new Error(`${kind} create payload.siteId must match siteId (the exact same string)`);
    }
  }
  // One synchronous descriptor-only copy per field. After this loop the
  // caller's original object is never read again.
  const copied = {};
  for (const field of contractFields) {
    const descriptor = ownDataDescriptorOrFail(payload, field, `${kind} create payload`);
    copied[field] = copyStableValue(descriptor.value, `${kind} create payload ${field}`, new Set());
  }
  const snapshot = buildStableCreateSnapshot(kind, copied, normalizedSiteId);
  deepFreezeStableData(snapshot);
  const payloadText = canonicalStableCreateText(snapshot);
  STABLE_CREATE_BRANDS.set(snapshot, Object.freeze({ kind, payloadText }));
  return { snapshot, payloadText };
}

// B2 readback stabilization: one synchronous descriptor-only projection of a
// create readback (wrapper, record, IDs — the whole value). The canonical
// comparison and every caller getter consume this same captured copy, so a
// getter/proxy readback cannot serve one object to the comparison and a
// different object to ID extraction (comparison A / ID B). Throws on any
// non-stable shape; callers turn the throw into a fail-closed mismatch.
export function captureStableReadback(value, label) {
  return copyStableValue(value, label, new Set());
}
