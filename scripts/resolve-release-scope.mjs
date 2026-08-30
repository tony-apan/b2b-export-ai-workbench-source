#!/usr/bin/env node
import { appendFileSync, existsSync, readFileSync, realpathSync, statSync } from 'node:fs';
import { dirname, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptPath = fileURLToPath(import.meta.url);
const sourceRoot = resolve(process.env.RELEASE_SOURCE_ROOT?.trim() || resolve(dirname(scriptPath), '..'));
const releaseTag = (process.argv[2] ?? process.env.RELEASE_TRIGGER_TAG ?? '').trim();

function block(message) {
  console.error(`BLOCK: ${message}`);
  process.exit(1);
}

function readJson(path, label) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch {
    block(`${label} is missing or invalid JSON: ${relative(sourceRoot, path)}`);
  }
}

function readVersion(path, label) {
  if (!existsSync(path) || !statSync(path).isFile()) block(`${label} VERSION.md is missing: ${relative(sourceRoot, path)}`);
  const text = readFileSync(path, 'utf8');
  const version = text.match(/^- Version：`([^`\r\n]+)`\s*$/m)?.[1]?.trim();
  if (!version || !/^[0-9A-Za-z][0-9A-Za-z._-]*$/.test(version)) block(`${label} VERSION.md does not contain a safe Version value`);
  return version;
}

function readIdentityProjection(path, label) {
  if (!existsSync(path) || !statSync(path).isFile()) block(`${label} is missing: ${relative(sourceRoot, path)}`);
  const text = readFileSync(path, 'utf8').replace(/\r\n?/g, '\n');
  const frontMatter = text.match(/^---\n([\s\S]*?)\n---(?:\n|$)/)?.[1];
  if (!frontMatter) block(`${label} has no readable front matter`);
  const values = new Map();
  for (const line of frontMatter.split('\n')) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_-]*):\s*(.+)$/);
    if (!match) continue;
    if (values.has(match[1])) block(`${label} has duplicate front matter field ${match[1]}`);
    const raw = match[2].trim();
    let value;
    if (raw === 'null' || raw === '~') value = null;
    else if (raw.startsWith('"')) {
      try { value = JSON.parse(raw); } catch { block(`${label} has invalid quoted value for ${match[1]}`); }
    } else if (raw.startsWith("'") && raw.endsWith("'")) value = raw.slice(1, -1).replace(/''/g, "'");
    else value = raw;
    values.set(match[1], value);
  }
  const required = ['historical_published_version', 'historical_published_tag', 'current_candidate_identity', 'current_candidate_snapshot', 'current_candidate_version'];
  for (const field of required) if (!values.has(field)) block(`${label} lacks required identity field ${field}`);
  return Object.fromEntries(values);
}

function assertSafeVersion(value, label) {
  if (typeof value !== 'string' || !/^[0-9A-Za-z][0-9A-Za-z._-]*$/.test(value)) block(`${label} is missing or unsafe`);
}

function assertSafeRegistryPath(path, id) {
  if (typeof path !== 'string' || !/^sub-libraries\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*$/.test(path)) {
    block(`registry path for ${id} is not a safe sub-libraries relative path`);
  }
  const absolute = resolve(sourceRoot, path);
  const rel = relative(sourceRoot, absolute);
  if (!rel || rel === '..' || rel.startsWith(`..${sep}`) || resolve(sourceRoot, rel) !== absolute) {
    block(`registry path for ${id} escapes the repository root`);
  }
  if (!existsSync(absolute) || !statSync(absolute).isDirectory()) block(`registry path for ${id} does not exist: ${path}`);
  const realRoot = realpathSync(sourceRoot);
  const realAbsolute = realpathSync(absolute);
  const realRel = relative(realRoot, realAbsolute);
  if (!realRel || realRel === '..' || realRel.startsWith(`..${sep}`)) block(`registry path for ${id} resolves outside the repository root`);
  return realAbsolute;
}

function writeOutputs(values) {
  const outputPath = process.env.GITHUB_OUTPUT?.trim();
  if (outputPath) {
    for (const [key, value] of Object.entries(values)) appendFileSync(outputPath, `${key}=${value}\n`);
  } else {
    console.log(JSON.stringify(values));
  }
}

if (!existsSync(sourceRoot) || !statSync(sourceRoot).isDirectory()) block(`release source root is missing or not a directory: ${sourceRoot}`);
if (!releaseTag) block('release_tag is required');
if (/\s/.test(releaseTag)) block('release_tag must not contain whitespace');

const motherMatch = releaseTag.match(/^mother\/v([^/]+)$/);
if (motherMatch) {
  const version = readVersion(resolve(sourceRoot, 'VERSION.md'), 'mother library');
  const expectedTag = `mother/v${version}`;
  if (releaseTag !== expectedTag) block(`mother tag version mismatch: expected ${expectedTag}, got ${releaseTag}`);
  writeOutputs({
    scope: 'mother-library',
    package_id: 'b2b-export-ai-workbench-mother-library',
    path: '.',
    version,
    release_tag: releaseTag,
  });
  console.log(`RELEASE_SCOPE_PASS: mother-library ${releaseTag}`);
  process.exit(0);
}

const subMatch = releaseTag.match(/^sub-library\/([a-z0-9]+(?:-[a-z0-9]+)*)\/v([^/]+)$/);
if (!subMatch) block(`unknown release tag namespace: ${releaseTag}`);

const [, id] = subMatch;
const registry = readJson(resolve(sourceRoot, 'sub-libraries/registry.json'), 'sub-library registry');
if (!Array.isArray(registry.entries)) block('sub-library registry entries must be an array');
const matches = registry.entries.filter((entry) => entry?.id === id);
if (matches.length !== 1) block(`sub-library ${id} must have exactly one registry entry; found ${matches.length}`);
const entry = matches[0];
if (entry.package_id !== id) block(`sub-library ${id} registry package_id must equal id`);
if (entry.tag_namespace !== `sub-library/${id}`) block(`sub-library ${id} registry tag_namespace mismatch`);
if (entry.tag_prefix !== `sub-library/${id}/v`) block(`sub-library ${id} registry tag_prefix mismatch`);
const childRoot = assertSafeRegistryPath(entry.path, id);
const manifestIdentity = readIdentityProjection(resolve(childRoot, 'MANIFEST.md'), `sub-library ${id} MANIFEST.md`);
const versionIdentity = readIdentityProjection(resolve(childRoot, 'VERSION.md'), `sub-library ${id} VERSION.md`);
const legacyVersion = readVersion(resolve(childRoot, 'VERSION.md'), `sub-library ${id}`);
for (const field of ['historical_published_version', 'historical_published_tag', 'current_candidate_identity', 'current_candidate_snapshot', 'current_candidate_version']) {
  if (versionIdentity[field] !== manifestIdentity[field]) block(`sub-library ${id} VERSION.md ${field} does not match MANIFEST.md`);
  if (entry[field] !== manifestIdentity[field]) block(`sub-library ${id} registry ${field} does not match MANIFEST.md`);
}
const historicalVersion = manifestIdentity.historical_published_version;
const historicalTag = manifestIdentity.historical_published_tag;
const currentIdentity = manifestIdentity.current_candidate_identity;
const currentSnapshot = manifestIdentity.current_candidate_snapshot;
const version = manifestIdentity.current_candidate_version;
assertSafeVersion(historicalVersion, `sub-library ${id} historical_published_version`);
if (historicalTag !== `v${historicalVersion}`) block(`sub-library ${id} historical_published_tag must be v${historicalVersion}`);
if (legacyVersion !== historicalVersion) block(`sub-library ${id} legacy VERSION.md Version must equal historical_published_version`);
if (entry.version !== historicalVersion || entry.version_semantics !== 'historical-published-only') block(`sub-library ${id} legacy registry version must be historical-published-only and match historical_published_version`);
if (entry.release_status !== manifestIdentity.release_status) block(`sub-library ${id} registry release_status does not match MANIFEST.md`);
if (currentIdentity === 'unassigned' || version === null) block(`sub-library ${id} current candidate identity/version is unassigned`);
assertSafeVersion(version, `sub-library ${id} current_candidate_version`);
if (typeof currentSnapshot !== 'string' || !currentSnapshot || currentSnapshot === 'dirty-working-tree') block(`sub-library ${id} current_candidate_snapshot is not release-eligible`);
if (version === historicalVersion) block(`sub-library ${id} current_candidate_version collides with immutable historical_published_version`);
if (`v${version}` === historicalTag) block(`sub-library ${id} current candidate tag collides with immutable historical_published_tag`);
if (manifestIdentity.release_status !== 'Ready') block(`sub-library ${id} current candidate release_status must be Ready before routing a release tag`);
const expectedTag = `sub-library/${id}/v${version}`;
if (releaseTag !== expectedTag) block(`sub-library tag version mismatch: expected ${expectedTag}, got ${releaseTag}`);

writeOutputs({
  scope: 'sub-library',
  package_id: id,
  path: entry.path,
  version,
  historical_published_version: historicalVersion,
  historical_published_tag: historicalTag,
  current_candidate_identity: currentIdentity,
  current_candidate_snapshot: currentSnapshot,
  current_candidate_version: version,
  release_tag: releaseTag,
});
console.log(`RELEASE_SCOPE_PASS: sub-library ${id} ${releaseTag}`);
