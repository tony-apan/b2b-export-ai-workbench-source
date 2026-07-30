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
  if (!version || !/^[0-9A-Za-z][0-9A-Za-z._-]*$/.test(version)) block(`${label} VERSION.md does not contain a safe current Version value`);
  return version;
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
const version = readVersion(resolve(childRoot, 'VERSION.md'), `sub-library ${id}`);
if (entry.version !== version) block(`sub-library ${id} registry version ${entry.version ?? 'missing'} does not match VERSION.md ${version}`);
const expectedTag = `sub-library/${id}/v${version}`;
if (releaseTag !== expectedTag) block(`sub-library tag version mismatch: expected ${expectedTag}, got ${releaseTag}`);

writeOutputs({
  scope: 'sub-library',
  package_id: id,
  path: entry.path,
  version,
  release_tag: releaseTag,
});
console.log(`RELEASE_SCOPE_PASS: sub-library ${id} ${releaseTag}`);
