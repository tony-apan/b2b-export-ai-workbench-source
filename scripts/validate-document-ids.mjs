#!/usr/bin/env node
/**
 * Validate stable document IDs, a frozen legacy path/type allowlist, typed
 * record path/ID contracts, and single-hop redirect integrity per release scope.
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, extname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFrontMatter, stringField } from './lib/markdown-front-matter.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const root = resolve(dirname(scriptPath), '..');
const scopeArgIndex = process.argv.indexOf('--scope');
const requestedScope = scopeArgIndex === -1 ? 'all' : (process.argv[scopeArgIndex + 1] || '');
const unknownArgs = process.argv.slice(2).filter((arg, index, args) => arg !== '--strict' && arg !== '--scope' && args[index - 1] !== '--scope');
const ignoredDirs = new Set(['.git', '.obsidian', 'node_modules', 'dist', '.cache', 'runtime', 'customer-runtime', 'credentials', 'secrets', '.secrets', 'private', 'workspace']);
const singletonNames = new Set(['index.md', 'README.md', 'AGENTS.md', 'CLAUDE.md', 'MANIFEST.md', 'VERSION.md', 'RELEASE.md', 'CHANGELOG.md', 'LICENSE.md']);
const typedRecordTypes = new Set(['verification-record', 'writeback-record']);
const allowlistPath = join(root, 'scripts', 'document-id-legacy-allowlist.json');
const failures = [];
const warnings = [];

function fail(message) { failures.push(message); }
function warn(message) { warnings.push(message); }
function portable(path) { return path.split(sep).join('/'); }
function inside(base, target) { return target === base || target.startsWith(`${base}${sep}`); }
function walk(dir) {
  const result = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (ignoredDirs.has(entry.name)) continue;
    const target = join(dir, entry.name);
    if (entry.isDirectory()) result.push(...walk(target));
    else result.push(target);
  }
  return result;
}
function parseFrontMatter(filePath) {
  try {
    const parsed = readFrontMatter(filePath);
    if (!parsed) { fail(`missing front matter: ${portable(relative(root, filePath))}`); return {}; }
    return {
      doc_id: stringField(parsed, 'doc_id'),
      type: stringField(parsed, 'type'),
      redirect_to: stringField(parsed, 'redirect_to'),
      verification_id: stringField(parsed, 'verification_id'),
      writeback_id: stringField(parsed, 'writeback_id'),
    };
  } catch (error) {
    fail(`invalid front matter: ${portable(relative(root, filePath))} (${error.message})`);
    return {};
  }
}
function isTemplatePath(rel) { return rel.split('/').some((part) => part === '_templates' || part === 'TEMPLATES'); }
function isLogPath(rel) { return rel.includes('/logs/') || rel.startsWith('wiki/00_meta/logs/'); }
function isRawPath(rel) { return rel === 'raw/index.md' || rel.startsWith('raw/'); }
function scopeFor(rel) {
  const parts = rel.split('/');
  if (parts[0] === 'sub-libraries' && parts[1]) return `sub-library:${parts[1]}`;
  return 'mother';
}
function scopeRootFor(scope) {
  if (scope === 'mother' || scope === 'all') return root;
  const match = scope.match(/^sub-library:([^/]+)$/);
  return match ? join(root, 'sub-libraries', match[1]) : null;
}
function readYamlList(filePath, field) {
  if (!existsSync(filePath)) return [];
  const content = readFileSync(filePath, 'utf8');
  const line = content.match(new RegExp(`^${field}:\\s*\\[([^\\]]*)\\]\\s*$`, 'm'))?.[1];
  return line ? line.split(',').map((item) => item.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean) : [];
}
function subLibraryDurableRoots(subLibraryName) {
  const manifest = join(root, 'sub-libraries', subLibraryName, 'MANIFEST.md');
  return readYamlList(manifest, 'durable_roots').map((item) => item.replace(/^\/+|\/+$/g, '')).filter(Boolean);
}
function shouldBeNumbered(rel, basename) {
  if (singletonNames.has(basename) || isTemplatePath(rel) || isLogPath(rel) || isRawPath(rel)) return false;
  if (basename.startsWith('SRC-') || basename.startsWith('CONV-')) return false;
  const numberedRoots = ['wiki/20_concepts/', 'wiki/30_playbooks/', 'wiki/40_business/', 'wiki/50_channels/', 'wiki/60_clients/', 'wiki/70_competitors/', 'wiki/80_metrics/', 'wiki/90_outputs/'];
  if (numberedRoots.some((prefix) => rel.startsWith(prefix))) return true;
  const scope = scopeFor(rel);
  if (!scope.startsWith('sub-library:')) return false;
  const libraryName = scope.slice('sub-library:'.length);
  const insideLibrary = rel.split('/').slice(2).join('/');
  return subLibraryDurableRoots(libraryName).some((prefix) => insideLibrary === prefix || insideLibrary.startsWith(`${prefix}/`));
}
function loadAllowlist() {
  if (!existsSync(allowlistPath)) { fail('missing machine-readable legacy allowlist: scripts/document-id-legacy-allowlist.json'); return { entries: [], policies: [] }; }
  let data;
  try { data = JSON.parse(readFileSync(allowlistPath, 'utf8')); }
  catch (error) { fail(`invalid legacy allowlist JSON: ${error.message}`); return { entries: [], policies: [] }; }
  if (data.schema_version !== 1 || !/^\d{4}-\d{2}-\d{2}$/.test(data.frozen_on ?? '') || !Array.isArray(data.legacy_entries) || !Array.isArray(data.record_policies)) {
    fail('legacy allowlist must declare schema_version=1, frozen_on, legacy_entries[], and record_policies[]');
    return { entries: [], policies: [] };
  }
  const entries = [];
  const seenPaths = new Set();
  for (const entry of data.legacy_entries) {
    if (!entry || typeof entry.path !== 'string' || typeof entry.type !== 'string' || !entry.path || !entry.type) { fail('legacy allowlist contains an invalid path/type entry'); continue; }
    if (seenPaths.has(entry.path)) fail(`legacy allowlist contains duplicate path: ${entry.path}`);
    seenPaths.add(entry.path);
    entries.push(entry);
  }
  const policies = [];
  const seenTypes = new Set();
  for (const policy of data.record_policies) {
    if (!policy || !typedRecordTypes.has(policy.type) || typeof policy.path_pattern !== 'string' || typeof policy.id_field !== 'string') {
      fail('legacy allowlist contains an invalid typed record policy');
      continue;
    }
    if (seenTypes.has(policy.type)) fail(`legacy allowlist contains duplicate record policy: ${policy.type}`);
    seenTypes.add(policy.type);
    try { policies.push({ ...policy, regex: new RegExp(policy.path_pattern) }); }
    catch (error) { fail(`invalid record policy regex for ${policy.type}: ${error.message}`); }
  }
  for (const type of typedRecordTypes) if (!seenTypes.has(type)) fail(`legacy allowlist is missing record policy: ${type}`);
  return { entries, policies };
}

if (unknownArgs.length) fail(`unsupported argument(s): ${unknownArgs.join(', ')}`);
const scopeRoot = scopeRootFor(requestedScope);
if (!scopeRoot || !existsSync(scopeRoot)) fail(`invalid --scope: ${requestedScope}`);
const files = failures.length ? [] : walk(scopeRoot).filter((file) => extname(file).toLowerCase() === '.md');
const fileRecords = new Map();
for (const filePath of files) {
  const rel = portable(relative(root, filePath));
  if (requestedScope !== 'all' && scopeFor(rel) !== requestedScope) continue;
  fileRecords.set(rel, { filePath, rel, basename: rel.split('/').pop(), meta: parseFrontMatter(filePath), scope: scopeFor(rel) });
}

const { entries: legacyEntries, policies: recordPolicies } = loadAllowlist();
const legacyByPath = new Map(legacyEntries.map((entry) => [entry.path, entry]));
const recordPolicyByType = new Map(recordPolicies.map((policy) => [policy.type, policy]));
const selectedScopes = new Set(fileRecords.values().map((item) => item.scope));
for (const entry of legacyEntries) {
  const entryScope = scopeFor(entry.path);
  if (requestedScope !== 'all' && entryScope !== requestedScope) continue;
  if (requestedScope === 'all' && !selectedScopes.has(entryScope)) continue;
  const record = fileRecords.get(entry.path);
  if (!record) { fail(`frozen legacy allowlist path is missing: ${entry.path}`); continue; }
  if (record.meta.type !== entry.type) fail(`frozen legacy allowlist type drift: ${entry.path} expected=${entry.type} actual=${record.meta.type || 'missing'}`);
  if (!shouldBeNumbered(entry.path, record.basename)) fail(`legacy allowlist entry is outside a durable root or is an exempt singleton: ${entry.path}`);
  if (/^id-\d{4}-/.test(record.basename)) fail(`legacy allowlist entry is already numbered and must be removed: ${entry.path}`);
}

const seenIds = new Map();
const numbered = [];
const allowedLegacy = [];
const redirectRecords = [];
let typedRecords = 0;
for (const record of fileRecords.values()) {
  const { rel, basename, meta, scope } = record;
  const numberedMatch = basename.match(/^id-(\d{4})-[a-z0-9][a-z0-9-]*\.md$/);
  const upperMatch = basename.match(/^ID-(\d{4})-/);
  if (upperMatch) fail(`${rel}: filename must use lowercase id-####-slug.md`);
  if (numberedMatch) {
    const id = `ID-${numberedMatch[1]}`;
    const key = `${scope}:${id}`;
    const paths = seenIds.get(key) ?? [];
    paths.push(rel);
    seenIds.set(key, paths);
    numbered.push({ rel, scope, id });
    if (meta.doc_id !== id) fail(`${rel}: numbered durable page must declare matching doc_id: "${id}"`);
    if (meta.type === 'redirect' || typedRecordTypes.has(meta.type)) fail(`${rel}: ${meta.type} cannot claim a numbered durable filename`);
    continue;
  }

  if (meta.type === 'redirect') {
    const allowed = legacyByPath.get(rel);
    if (!allowed || allowed.type !== 'redirect') fail(`redirect legacy path is not frozen in the path/type allowlist: ${rel}`);
    else allowedLegacy.push(rel);
    redirectRecords.push(record);
    continue;
  }

  if (typedRecordTypes.has(meta.type)) {
    typedRecords += 1;
    const policy = recordPolicyByType.get(meta.type);
    const match = policy?.regex.exec(rel);
    if (!policy || !match) {
      fail(`${meta.type} is outside its allowed path: ${rel}`);
      continue;
    }
    const declaredId = meta[policy.id_field];
    if (!declaredId || declaredId !== match[1]) fail(`${rel}: ${policy.id_field} must equal filename ID ${match[1]}`);
    continue;
  }

  if (shouldBeNumbered(rel, basename)) {
    const allowed = legacyByPath.get(rel);
    if (!allowed) fail(`new or unregistered unnumbered durable page: ${rel}; use id-####-slug.md or add an explicitly reviewed frozen migration entry`);
    else if (allowed.type !== meta.type) fail(`frozen legacy allowlist type drift: ${rel} expected=${allowed.type} actual=${meta.type || 'missing'}`);
    else allowedLegacy.push(rel);
  }
}
for (const [key, paths] of seenIds) if (paths.length > 1) fail(`duplicate stable ID ${key}: ${paths.join(', ')}`);

const redirectGraph = new Map();
for (const record of redirectRecords) {
  const { rel, filePath, meta, scope } = record;
  const rawTarget = meta.redirect_to;
  if (!rawTarget) { fail(`${rel}: redirect_to is required for type: redirect`); continue; }
  if (isAbsolute(rawTarget) || /^(?:[a-z][a-z0-9+.-]*:|\/|\\)/i.test(rawTarget) || rawTarget.includes('#') || rawTarget.includes('?')) {
    fail(`${rel}: redirect_to must be a plain relative Markdown path inside the same release scope`);
    continue;
  }
  const targetPath = resolve(dirname(filePath), rawTarget);
  if (!inside(root, targetPath)) { fail(`${rel}: redirect_to escapes repository scope: ${rawTarget}`); continue; }
  const targetRel = portable(relative(root, targetPath));
  if (targetRel === rel) fail(`${rel}: redirect_to cannot reference itself`);
  if (scopeFor(targetRel) !== scope) fail(`${rel}: redirect_to crosses release scope: ${rawTarget}`);
  if (!existsSync(targetPath) || extname(targetPath).toLowerCase() !== '.md') { fail(`${rel}: redirect_to target does not exist as Markdown: ${rawTarget}`); continue; }
  redirectGraph.set(rel, targetRel);
}
const visitState = new Map();
const stack = [];
function visitRedirect(rel) {
  const state = visitState.get(rel) ?? 0;
  if (state === 2) return;
  if (state === 1) {
    const start = stack.indexOf(rel);
    fail(`redirect cycle detected: ${[...stack.slice(start), rel].join(' -> ')}`);
    return;
  }
  visitState.set(rel, 1);
  stack.push(rel);
  const target = redirectGraph.get(rel);
  if (target && redirectGraph.has(target)) visitRedirect(target);
  stack.pop();
  visitState.set(rel, 2);
}
for (const rel of redirectGraph.keys()) visitRedirect(rel);
for (const [rel, targetRel] of redirectGraph) {
  const target = fileRecords.get(targetRel) ?? (() => {
    const filePath = join(root, targetRel);
    return { rel: targetRel, basename: targetRel.split('/').pop(), meta: parseFrontMatter(filePath), scope: scopeFor(targetRel) };
  })();
  if (target.meta.type === 'redirect') { fail(`${rel}: redirect multihop is forbidden; target is another redirect: ${targetRel}`); continue; }
  const match = target.basename.match(/^id-(\d{4})-[a-z0-9][a-z0-9-]*\.md$/);
  if (!match) { fail(`${rel}: redirect_to final target must be a numbered canonical durable page: ${targetRel}`); continue; }
  const expectedId = `ID-${match[1]}`;
  if (target.meta.doc_id !== expectedId) fail(`${rel}: redirect_to final target doc_id must equal ${expectedId}: ${targetRel}`);
  if (!shouldBeNumbered(targetRel, target.basename)) fail(`${rel}: redirect_to final target is outside a durable root: ${targetRel}`);
}

const byScope = new Map();
for (const item of numbered) {
  const values = byScope.get(item.scope) ?? [];
  values.push(Number(item.id.slice(3)));
  byScope.set(item.scope, values);
}
for (const [scope, values] of byScope) {
  values.sort((a, b) => a - b);
  const present = new Set(values);
  const gaps = [];
  for (let number = 1; number <= values.at(-1); number += 1) if (!present.has(number)) gaps.push(String(number).padStart(4, '0'));
  if (gaps.length) warn(`${scope} has numbering gaps (allowed during legacy migration): ${gaps.slice(0, 20).join(', ')}${gaps.length > 20 ? ' ...' : ''}`);
}
for (const rel of [...new Set(allowedLegacy)].sort()) warn(`frozen legacy path/type entry: ${rel}`);

console.log(`DOCUMENT_ID_REPORT: scope=${requestedScope} markdown=${fileRecords.size} numbered=${numbered.length} frozen_legacy=${new Set(allowedLegacy).size} typed_records=${typedRecords} redirects=${redirectRecords.length}`);
console.log('POLICY: new durable pages fail closed unless numbered; legacy exemptions are exact path/type entries; typed records bind path and ID; redirects are same-scope single-hop pointers to numbered non-redirect canonical pages.');
for (const item of numbered.sort((a, b) => a.scope.localeCompare(b.scope) || a.id.localeCompare(b.id))) console.log(`ID: ${item.scope} ${item.id} ${item.rel}`);
for (const message of warnings) console.log(`WARN: ${message}`);
for (const message of failures) console.error(`BLOCK: ${message}`);
if (failures.length) process.exitCode = 1;
else console.log('DOCUMENT_ID_PASS: stable IDs, frozen legacy entries, typed records, and redirects satisfy the current structural contract.');
