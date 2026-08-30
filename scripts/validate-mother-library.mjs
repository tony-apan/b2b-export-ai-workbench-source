#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const scriptPath = fileURLToPath(import.meta.url);
const root = resolve(dirname(scriptPath), '..');
const releaseMode = process.argv.includes('--release');
const prepareMode = process.argv.includes('--prepare');
const GOVERNANCE_COMMAND_TIMEOUT_MS = 120_000;
const failures = [];
const warnings = [];

const allowedMaturity = new Set(['draft', 'validated', 'stable', 'deprecated']);
const allowedVerification = new Set(['unverified', 'structure-pass', 'evidence-partial', 'e2e-pass']);
const allowedRelease = new Set(['BLOCK', 'Preview', 'candidate', 'Ready', 'Published', 'retired']);
const allowedLicense = new Set(['pending', 'cleared', 'restricted', 'unknown']);
const allowedApproval = new Set(['pending', 'approved', 'rejected', 'expired']);
const allowedRepositorySync = new Set(['Working', 'Ready', 'Synced', 'Archived']);
const allowedDependency = new Set(['self-contained', 'declared-external-runtime']);
const allowedPackageKinds = new Set(['standalone-sub-library']);
const allowedDeliveryModes = new Set(['human-playbook', 'ai-skill-draft', 'ai-skill-stable', 'toolkit', 'adapter', 'template-pack', 'reference-implementation', 'course']);
const allowedSkillStatus = new Set(['draft-adapter-not-installable', 'preview-adapter-not-installable', 'validated-adapter', 'stable-adapter', 'retired']);
const ignoredSourceDirs = new Set(['.git', '.obsidian', 'node_modules', 'dist', 'secrets', '.secrets', 'private', 'runtime', 'customer-runtime', 'credentials', 'workspace']);
const requiredStateProjections = new Map([
  ['VERSION.md', ['repository_sync_status', 'release_status']],
  ['RELEASE.md', ['repository_sync_status', 'release_status']],
  ['LICENSE.md', ['release_status', 'license_status']],
]);

const requiredFiles = [
  'README.md', 'AGENTS.md', 'CLAUDE.md', 'MANIFEST.md', 'RELEASE.md', 'VERSION.md',
  'CHANGELOG.md', 'wiki/index.md', 'wiki/00_meta/publishing-and-redaction.md',
  'sub-libraries/README.md', 'sub-libraries/registry.json', 'scripts/README.md', 'scripts/validate-mother-library.mjs', 'scripts/validate-indexes.mjs', 'scripts/sync-indexes.mjs', 'scripts/validate-artifact.mjs', 'scripts/validate-links.mjs', 'scripts/validate-release-approval.mjs', 'scripts/build-mother-release.mjs',
];
function fail(message) { failures.push(message); }
function warn(message) { warnings.push(message); }
function read(path) { return readFileSync(path, 'utf8'); }
function statSafeDir(path) { try { return statSync(path).isDirectory(); } catch { return false; } }
function isInside(parent, candidate) { const p = resolve(parent) + sep; return resolve(candidate) === resolve(parent) || resolve(candidate).startsWith(p); }
function walk(dir) {
  const result = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (['.git', '.obsidian', 'node_modules', 'dist'].includes(entry.name)) continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) result.push(...walk(path));
    else result.push(path);
  }
  return result;
}
function frontMatter(path, content) {
  if (!path.endsWith('.md')) return null;
  if (content.startsWith('---\n')) {
    const end = content.indexOf('\n---', 4);
    return end === -1 ? null : content.slice(4, end);
  }
  if (content.startsWith('<!--\n')) {
    const end = content.indexOf('\n-->', 5);
    if (end === -1) return null;
    return content.slice(5, end).replace(/^Repository metadata:\s*$/m, '').trim();
  }
  return null;
}
function fieldValue(front, field) { return front?.match(new RegExp(`^${field}:\\s*["']?([^\\n"']+)["']?\\s*$`, 'm'))?.[1]?.trim() ?? null; }
function fieldArray(front, field) {
  const line = front?.match(new RegExp(`^${field}:\\s*(\\[[^\\n]*\\])`, 'm'))?.[1];
  if (!line) return [];
  return [...line.matchAll(/"([^"]*)"|'([^']*)'/g)].map((m) => m[1] ?? m[2]);
}
function hasField(front, field) { return new RegExp(`^${field}:`, 'm').test(front ?? ''); }
function validateStateProjections(scopeRoot, markdownFiles) {
  const markdownByDocument = new Map(markdownFiles
    .filter((file) => extname(file).toLowerCase() === '.md')
    .map((file) => [relative(scopeRoot, file).split(sep).join('/'), file]));
  for (const document of requiredStateProjections.keys()) {
    if (!markdownByDocument.has(document)) fail(`missing required state projection document: ${document}`);
  }

  for (const [document, path] of markdownByDocument) {
    const requiredFields = requiredStateProjections.get(document);
    const front = frontMatter(path, read(path));
    if (!front) {
      if (requiredFields) fail(`${document} required state projection document must have readable front matter`);
      continue;
    }
    const hasSource = hasField(front, 'state_source');
    const hasProjection = hasField(front, 'state_projection');
    if (!hasSource && !hasProjection && !requiredFields) continue;

    if (!hasSource || !hasProjection) {
      fail(requiredFields
        ? `${document} required state projection must declare both state_source and state_projection`
        : `${document} state projection must declare both state_source and state_projection`);
      continue;
    }

    const sourceReference = fieldValue(front, 'state_source');
    const projectedFields = fieldArray(front, 'state_projection');
    if (!sourceReference) {
      fail(`${document} state_source must be a non-empty relative MANIFEST.md path`);
      continue;
    }
    if (sourceReference.startsWith('/') || /^file:/i.test(sourceReference) || sourceReference.includes('\\')) {
      fail(`${document} state_source must be a portable relative path: ${sourceReference}`);
      continue;
    }
    const sourcePath = resolve(dirname(path), sourceReference);
    if (!isInside(scopeRoot, sourcePath)) {
      fail(`${document} state_source escapes validation scope: ${sourceReference}`);
      continue;
    }
    const relativeParts = relative(scopeRoot, path).split(sep);
    const documentScopeRoot = relativeParts[0] === 'sub-libraries' && relativeParts.length > 2
      ? resolve(scopeRoot, 'sub-libraries', relativeParts[1])
      : resolve(scopeRoot);
    const canonicalSourcePath = resolve(documentScopeRoot, 'MANIFEST.md');
    if (sourcePath !== canonicalSourcePath) {
      fail(`${document} state_source must resolve to the canonical scope MANIFEST.md: ${sourceReference}`);
      continue;
    }
    if (!existsSync(sourcePath)) {
      fail(`${document} state_source does not exist: ${sourceReference}`);
      continue;
    }
    if (!projectedFields.length) {
      fail(`${document} state_projection must be a non-empty inline string array`);
      continue;
    }
    if (new Set(projectedFields).size !== projectedFields.length) {
      fail(`${document} state_projection contains duplicate fields`);
      continue;
    }
    if (requiredFields && (
      projectedFields.length !== requiredFields.length
      || requiredFields.some((field) => !projectedFields.includes(field))
    )) {
      fail(`${document} required state_projection must exactly equal ${JSON.stringify(requiredFields)}`);
      continue;
    }

    const sourceFront = frontMatter(sourcePath, read(sourcePath));
    if (!sourceFront) {
      fail(`${document} state_source has no readable front matter: ${sourceReference}`);
      continue;
    }
    for (const field of projectedFields) {
      if (!/^[a-z][a-z0-9_]*$/.test(field)) {
        fail(`${document} state_projection has invalid field name: ${field}`);
        continue;
      }
      const expected = fieldValue(sourceFront, field);
      const actual = fieldValue(front, field);
      if (expected === null) fail(`${document} projects ${field}, but ${sourceReference} does not declare it`);
      else if (actual === null) fail(`${document} projects ${field}, but the document does not declare it`);
      else if (actual !== expected) fail(`${document} state drift for ${field}: expected ${JSON.stringify(expected)} from ${sourceReference}, got ${JSON.stringify(actual)}`);
    }
  }
}
function isExternal(value) { return /^(https?:|mailto:|data:|tel:|#)/i.test(value); }
function isPathLike(value) { return !isExternal(value) && !/[\s]/.test(value) && (value.startsWith('.') || /\.(md|json|mjs|js|txt|yaml|yml|sh|png|jpg|jpeg|webp)$/i.test(value)); }
function checkLocalReference(path, value, field) {
  if (!isPathLike(value)) return;
  if (value.startsWith('/') || /^file:/i.test(value)) { fail(`${relative(root, path)} ${field} has non-portable local path: ${value}`); return; }
  const resolved = resolve(dirname(path), value);
  if (!isInside(root, resolved)) fail(`${relative(root, path)} ${field} escapes mother-library root: ${value}`);
  else if (!existsSync(resolved)) fail(`${relative(root, path)} ${field} links to missing path: ${value}`);
}
function checkMarkdownLinks(path, content) {
  const linkRe = /!?!?\[[^\]]*\]\(([^)]+)\)/g;
  let match;
  while ((match = linkRe.exec(content))) {
    const target = match[1].trim().replace(/^<|>$/g, '');
    if (!target || isExternal(target)) continue;
    checkLocalReference(path, target.split('#')[0].split('?')[0], 'markdown link');
  }
}

function enforceCleanGitRelease() {
  if (!releaseMode) return;
  const probe = spawnSync('git', ['rev-parse', '--show-toplevel'], { cwd: root, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
  if (probe.status !== 0) { warn('release mode running without Git metadata; commit/artifact provenance remains unverified'); return; }
  const status = spawnSync('git', ['status', '--porcelain', '--untracked-files=all'], { cwd: root, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
  if ((status.stdout ?? '').trim()) fail('release mode requires a clean Git worktree');
}

for (const file of requiredFiles) if (!existsSync(join(root, file))) fail(`missing required file: ${file}`);

// State projection drift is both release-critical and cheap to detect. Run the
// mandatory root projections before the expensive link/index/child validators
// so adversarial mutation fixtures fail closed without exhausting their budget.
const requiredProjectionFiles = [...requiredStateProjections.keys()]
  .map((document) => join(root, document))
  .filter((path) => existsSync(path));
validateStateProjections(root, requiredProjectionFiles);
if (failures.length) {
  for (const item of failures) console.log(`FAIL: ${item}`);
  console.error(`\nBLOCK: ${failures.length} preflight check(s) failed.`);
  process.exit(1);
}

const linkGate = spawnSync(process.execPath, [join(root, 'scripts/validate-links.mjs'), ...((releaseMode || prepareMode) ? ['--release'] : []), root], { encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
if (linkGate.status !== 0) fail('local Markdown link validation failed');
process.stdout.write(linkGate.stdout ?? '');
process.stderr.write(linkGate.stderr ?? '');

enforceCleanGitRelease();
const files = walk(root);
for (const path of files) {
  const content = read(path);
  if (extname(path).toLowerCase() === '.md') {
    if (!frontMatter(path, content)) fail(`missing front matter or README metadata block: ${relative(root, path)}`);
    checkMarkdownLinks(path, content);
    const front = frontMatter(path, content);
    const description = fieldValue(front, 'description');
    if (!description) fail(`missing description: ${relative(root, path)}`);
    else if (/^(文档说明|页面说明|资料索引|索引|document|documentation|page|file|placeholder)$/i.test(description)) fail(`generic placeholder description: ${relative(root, path)}`);
    for (const field of ['sources', 'related']) for (const value of fieldArray(front, field)) checkLocalReference(path, value, `${field} reference`);
  }
  if (/\/Users\/|\/var\/folders\/|\/private\/var\/folders\/|\/tmp\//.test(content)) fail(`machine-local path pattern found: ${relative(root, path)}`);
  if (/(?:api[_ -]?key|secret|access[_ -]?token|password|cookie|session)\s*[:=]\s*['"]?[A-Za-z0-9_\-/+=]{12,}/i.test(content)) fail(`possible credential pattern found: ${relative(root, path)}`);
}
validateStateProjections(root, files);


function checkNameCollisions(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isSymbolicLink()) { fail(`symlink is not allowed: ${relative(root, join(dir, entry.name))}`); continue; }
    if (!entry.isDirectory() || ['.git', '.obsidian', 'node_modules', 'dist'].includes(entry.name)) continue;
    const child = join(dir, entry.name);
    const names = new Set(readdirSync(child, { withFileTypes: true }).filter((item) => item.isDirectory()).map((item) => item.name));
    for (const item of readdirSync(child, { withFileTypes: true })) {
      if (!item.isFile()) continue;
      const stem = basename(item.name, extname(item.name));
      if (names.has(stem)) fail(`file/directory name collision in ${relative(root, child)}: ${item.name} and ${stem}/`);
    }
    checkNameCollisions(child);
  }
}
checkNameCollisions(root);

const indexValidator = join(root, 'scripts/validate-indexes.mjs');
if (existsSync(indexValidator)) {
  const indexResult = spawnSync(process.execPath, [indexValidator, '--check'], { cwd: root, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
  if (indexResult.status !== 0) {
    const evidence = `${indexResult.stdout ?? ''}${indexResult.stderr ?? ''}`.trim().split('\n').slice(-8).join(' | ');
    fail(`index validator failed${evidence ? `: ${evidence}` : ''}`);
  }
} else fail('missing scripts/validate-indexes.mjs');

const manifestPath = join(root, 'MANIFEST.md');
const manifestFront = frontMatter(manifestPath, read(manifestPath));
const version = read(join(root, 'VERSION.md')).match(/Version：`([^`]+)`/)?.[1];
const manifestStatus = fieldValue(manifestFront, 'release_status');
const maturityStatus = fieldValue(manifestFront, 'maturity_status');
const verificationStatus = fieldValue(manifestFront, 'verification_status');
const releaseScope = fieldValue(manifestFront, 'release_scope');
const packageId = fieldValue(manifestFront, 'package_id');
const licenseStatus = fieldValue(manifestFront, 'license_status');
const approvalRequired = fieldValue(manifestFront, 'approval_required');
const approvalStatus = fieldValue(manifestFront, 'approval_status');
const repositoryStatus = fieldValue(manifestFront, 'repository_status');
const repositorySyncStatus = fieldValue(manifestFront, 'repository_sync_status');
const visibility = fieldValue(manifestFront, 'visibility');
const tagNamespace = fieldValue(manifestFront, 'tag_namespace');
const tagPrefix = fieldValue(manifestFront, 'tag_prefix');
if (!allowedMaturity.has(maturityStatus)) fail(`MANIFEST.md maturity_status is invalid: ${maturityStatus ?? 'missing'}`);
if (!allowedVerification.has(verificationStatus)) fail(`MANIFEST.md verification_status is invalid: ${verificationStatus ?? 'missing'}`);
if (!allowedRelease.has(manifestStatus)) fail(`MANIFEST.md release_status is invalid: ${manifestStatus ?? 'missing'}`);
if (!allowedLicense.has(licenseStatus)) fail(`MANIFEST.md license_status is invalid: ${licenseStatus ?? 'missing'}`);
if (approvalRequired !== 'true') fail(`MANIFEST.md approval_required must be true: ${approvalRequired ?? 'missing'}`);
if (!allowedApproval.has(approvalStatus)) fail(`MANIFEST.md approval_status is invalid: ${approvalStatus ?? 'missing'}`);
if (tagNamespace !== 'mother') fail(`MANIFEST.md tag_namespace must be mother: ${tagNamespace ?? 'missing'}`);
if (tagPrefix !== 'mother/v') fail(`MANIFEST.md tag_prefix must be mother/v: ${tagPrefix ?? 'missing'}`);
if (releaseScope !== 'standalone-mother-library') fail(`MANIFEST.md release_scope is not standalone-mother-library: ${releaseScope ?? 'missing'}`);
if (packageId !== 'b2b-export-ai-workbench-mother-library') fail(`MANIFEST.md package_id is invalid: ${packageId ?? 'missing'}`);
if (manifestStatus === 'Ready' || manifestStatus === 'Published') {
  if (licenseStatus !== 'cleared') fail('mother-library Ready/Published requires license_status cleared');
  if (!prepareMode && approvalStatus !== 'approved') fail('mother-library Ready/Published requires approval_status approved outside preparation mode');
  if (prepareMode && approvalStatus !== 'pending') fail('mother-library preparation requires approval_status pending so the frozen candidate cannot self-certify approval');
  if (prepareMode && manifestStatus !== 'Ready') fail('mother-library preparation requires release_status Ready; Published is an external post-qualification state');
  if (verificationStatus !== 'e2e-pass') fail('mother-library Ready/Published requires verification_status e2e-pass');
  if (maturityStatus !== 'stable') fail('mother-library Ready/Published requires maturity_status stable');
}
if (!version) fail('VERSION.md has no machine-readable Version field');
if (!read(join(root, 'CHANGELOG.md')).includes(version)) fail(`CHANGELOG.md does not contain ${version}`);
if (fieldValue(manifestFront, 'package_kind') !== 'private-master-source') fail('MANIFEST.md package_kind is not private-master-source');
if (repositoryStatus !== 'private-source') fail(`MANIFEST.md repository_status must be private-source: ${repositoryStatus ?? 'missing'}`);
if (!allowedRepositorySync.has(repositorySyncStatus)) fail(`MANIFEST.md repository_sync_status is invalid: ${repositorySyncStatus ?? 'missing'}`);
if (visibility !== 'private') fail(`MANIFEST.md visibility must be private: ${visibility ?? 'missing'}`);
if (!read(join(root, 'RELEASE.md')).includes('母库 release') || !read(join(root, 'RELEASE.md')).includes('子库 release')) fail('RELEASE.md does not declare two independent release lines');
if (!read(join(root, 'README.md')).includes('MANIFEST.md') || !read(join(root, 'README.md')).includes('RELEASE.md')) warn('README.md does not expose both mother-library release contracts');
if ((releaseMode || prepareMode) && !/release_status:\s*["']?(Ready|Published)["']?/m.test(manifestFront ?? '')) fail('release mode requires MANIFEST.md release_status Ready or Published');
if (manifestStatus === 'BLOCK') warn('mother-library release_status is BLOCK for external distribution; private repository sync is evaluated separately');
if (licenseStatus !== 'cleared') warn('license status is not cleared; this blocks external release');
if (approvalStatus !== 'approved') warn('approval status is not approved; a human approval sidecar is still required for external release');

const wikiIndex = read(join(root, 'wiki/index.md'));
const registryPath = join(root, 'sub-libraries/README.md');
const registry = read(registryPath);
if (!wikiIndex.includes('../sub-libraries/README.md')) fail('wiki/index.md lacks canonical sub-libraries/README.md entry');
if (!registry.includes('registry.json') || !registry.includes('机器可读唯一注册表')) fail('sub-libraries/README.md does not declare registry.json as the machine-readable source of truth');
const machineRegistryPath = join(root, 'sub-libraries/registry.json');
let machineRegistry;
try { machineRegistry = JSON.parse(read(machineRegistryPath)); } catch { fail('sub-libraries/registry.json is not valid JSON'); machineRegistry = { entries: [] }; }
if (machineRegistry.schema_version !== 2) fail(`sub-libraries/registry.json schema_version must be 2, got ${machineRegistry.schema_version ?? 'missing'}`);
const registryEntries = Array.isArray(machineRegistry.entries) ? machineRegistry.entries : [];
if (!Array.isArray(machineRegistry.entries)) fail('sub-libraries/registry.json entries must be an array');
const ids = new Set();
const paths = new Set();
for (const item of registryEntries) {
  if (!item?.id || !item?.path) { fail('sub-libraries/registry.json entry requires id and path'); continue; }
  for (const field of ['package_id', 'version', 'maturity_status', 'verification_status', 'release_status', 'license_status', 'approval_required', 'approval_status', 'tag_namespace', 'tag_prefix', 'release_scope', 'runtime_contract', 'dependency_mode', 'source_package_only', 'package_kind', 'delivery_modes', 'canonical_entry', 'included_in_mother']) {
    if (item[field] === undefined || item[field] === null || item[field] === '') fail(`registry entry ${item.id} is missing ${field}`);
  }
  if (item.package_id !== item.id) fail(`registry entry ${item.id} package_id must equal id`);
  if (item.path !== `sub-libraries/${item.id}`) fail(`registry entry ${item.id} path must equal sub-libraries/${item.id}`);
  if (!allowedMaturity.has(item.maturity_status)) fail(`registry entry ${item.id} has invalid maturity_status: ${item.maturity_status}`);
  if (!allowedVerification.has(item.verification_status)) fail(`registry entry ${item.id} has invalid verification_status: ${item.verification_status}`);
  if (!allowedRelease.has(item.release_status)) fail(`registry entry ${item.id} has invalid release_status: ${item.release_status}`);
  if (!allowedLicense.has(item.license_status)) fail(`registry entry ${item.id} has invalid license_status: ${item.license_status}`);
  if (item.approval_required !== true) fail(`registry entry ${item.id} approval_required must be true`);
  if (!allowedApproval.has(item.approval_status)) fail(`registry entry ${item.id} has invalid approval_status: ${item.approval_status}`);
  if (item.tag_namespace !== `sub-library/${item.id}`) fail(`registry entry ${item.id} tag_namespace must be sub-library/${item.id}`);
  if (item.tag_prefix !== `sub-library/${item.id}/v`) fail(`registry entry ${item.id} tag_prefix must be sub-library/${item.id}/v`);
  if (item.release_scope !== 'standalone-sub-library') fail(`registry entry ${item.id} release_scope must be standalone-sub-library`);
  if (!allowedDependency.has(item.dependency_mode)) fail(`registry entry ${item.id} has invalid dependency_mode: ${item.dependency_mode}`);
  if (item.source_package_only !== true) fail(`registry entry ${item.id} source_package_only must be true`);
  if (!allowedPackageKinds.has(item.package_kind)) fail(`registry entry ${item.id} has invalid package_kind: ${item.package_kind}`);
  if (item.canonical_entry !== 'README.md') fail(`registry entry ${item.id} canonical_entry must be README.md`);
  if (item.included_in_mother !== 'source-only') fail(`registry entry ${item.id} included_in_mother must be source-only`);
  if (typeof item.runtime_contract !== 'string' || item.runtime_contract.startsWith('/') || item.runtime_contract.includes('..')) fail(`registry entry ${item.id} runtime_contract must be a portable relative path`);
  if (!Array.isArray(item.delivery_modes) || item.delivery_modes.length === 0 || item.delivery_modes.some((mode) => !allowedDeliveryModes.has(mode)) || new Set(item.delivery_modes).size !== item.delivery_modes.length) fail(`registry entry ${item.id} delivery_modes are invalid`);
  const skillDeclared = typeof item.skill_entrypoint === 'string' && item.skill_entrypoint.length > 0;
  if (skillDeclared) {
    if (item.skill_entrypoint.startsWith('/') || item.skill_entrypoint.includes('..')) fail(`registry entry ${item.id} skill_entrypoint must be portable`);
    if (!item.delivery_modes.includes('ai-skill-draft') && !item.delivery_modes.includes('ai-skill-stable')) fail(`registry entry ${item.id} declares skill_entrypoint without an ai-skill delivery mode`);
    if (!allowedSkillStatus.has(item.skill_status)) fail(`registry entry ${item.id} has invalid or missing skill_status`);
  } else {
    if (item.skill_entrypoint !== null && item.skill_entrypoint !== undefined) fail(`registry entry ${item.id} skill_entrypoint must be null when undeclared`);
    if (item.delivery_modes.some((mode) => mode.startsWith('ai-skill-'))) fail(`registry entry ${item.id} has ai-skill delivery mode without skill_entrypoint`);
    if (item.skill_status !== null && item.skill_status !== undefined) fail(`registry entry ${item.id} skill_status must be null when skill_entrypoint is undeclared`);
  }
  if (ids.has(item.id)) fail(`duplicate sub-library registry id: ${item.id}`);
  if (paths.has(item.path)) fail(`duplicate sub-library registry path: ${item.path}`);
  ids.add(item.id); paths.add(item.path);
}
const subEntries = readdirSync(join(root, 'sub-libraries'), { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && !ignoredSourceDirs.has(entry.name));
if (!subEntries.length) fail('sub-libraries registry has no discoverable sub-library directory');
const registeredRows = new Set();
for (const line of registry.split('\n')) {
  const match = line.match(/\]\(([^)]+)\/README\.md\)/);
  if (match) registeredRows.add(match[1]);
}
for (const rowId of registeredRows) if (!ids.has(rowId)) fail(`sub-libraries/README.md contains unregistered sub-library row: ${rowId}`);
if (registeredRows.size !== registryEntries.length) fail(`sub-libraries/README.md row count ${registeredRows.size} does not match registry entry count ${registryEntries.length}`);
for (const entry of subEntries) {
  const name = entry.name;
  const subRoot = join(root, 'sub-libraries', name);
  const item = registryEntries.find((candidate) => candidate?.id === name);
  if (!item) fail(`sub-libraries/registry.json lacks discovered sub-library directory: ${name}`);
  for (const required of ['README.md', 'MANIFEST.md', 'VERSION.md', 'AGENTS.md', 'scripts/validate-sub-library.mjs']) {
    if (!existsSync(join(subRoot, required))) fail(`${name} sub-library is missing ${required}`);
  }
  if (!item) continue;
  const subVersion = existsSync(join(subRoot, 'VERSION.md')) ? read(join(subRoot, 'VERSION.md')).match(/Version：`([^`]+)`/)?.[1] : null;
  const subManifestPath = join(subRoot, 'MANIFEST.md');
  const subManifest = existsSync(subManifestPath) ? frontMatter(subManifestPath, read(subManifestPath)) : null;
  const subPackageId = fieldValue(subManifest, 'package_id');
  const subStatus = fieldValue(subManifest, 'release_status');
  const subMaturity = fieldValue(subManifest, 'maturity_status');
  const subVerification = fieldValue(subManifest, 'verification_status');
  const subReleaseScope = fieldValue(subManifest, 'release_scope');
  const subRuntimeContract = fieldValue(subManifest, 'runtime_contract');
  const subDependencyMode = fieldValue(subManifest, 'dependency_mode');
  const subSourceOnly = fieldValue(subManifest, 'source_package_only');
  const subPackageKind = fieldValue(subManifest, 'package_kind');
  const subSkill = fieldValue(subManifest, 'skill_entrypoint');
  const subSkillStatus = fieldValue(subManifest, 'skill_status');
  const subDeliveryModes = fieldArray(subManifest, 'delivery_modes');
  const subCanonical = fieldValue(subManifest, 'canonical_entry') ?? 'README.md';
  const subIncludedInMother = fieldValue(subManifest, 'included_in_mother');
  const subLicense = fieldValue(subManifest, 'license_status');
  if (subPackageId !== name) fail(`${name} manifest package_id must equal directory name: ${subPackageId ?? 'missing'}`);
  if (!subVersion) fail(`${name} VERSION.md has no machine-readable Version field`);
  if (!allowedMaturity.has(subMaturity)) fail(`${name} manifest maturity_status is invalid: ${subMaturity ?? 'missing'}`);
  if (!allowedVerification.has(subVerification)) fail(`${name} manifest verification_status is invalid: ${subVerification ?? 'missing'}`);
  if (!allowedRelease.has(subStatus)) fail(`${name} manifest release_status is invalid: ${subStatus ?? 'missing'}`);
  if (!allowedLicense.has(subLicense)) fail(`${name} manifest license_status is invalid: ${subLicense ?? 'missing'}`);
  if (subReleaseScope !== 'standalone-sub-library') fail(`${name} manifest release_scope is not standalone-sub-library`);
  if (!allowedDependency.has(subDependencyMode)) fail(`${name} manifest dependency_mode is invalid: ${subDependencyMode ?? 'missing'}`);
  if (subSourceOnly !== 'true') fail(`${name} manifest source_package_only must be true`);
  if (subPackageKind !== 'standalone-sub-library') fail(`${name} manifest package_kind is invalid: ${subPackageKind ?? 'missing'}`);
  if (subCanonical !== 'README.md') fail(`${name} manifest canonical_entry must be README.md`);
  if (subIncludedInMother !== 'source-only') fail(`${name} manifest included_in_mother must be source-only`);
  if (!subDeliveryModes.length || subDeliveryModes.some((mode) => !allowedDeliveryModes.has(mode)) || new Set(subDeliveryModes).size !== subDeliveryModes.length) fail(`${name} manifest delivery_modes are invalid`);
  if (!subRuntimeContract || subRuntimeContract.startsWith('/') || subRuntimeContract.includes('..') || !existsSync(join(subRoot, subRuntimeContract))) fail(`${name} runtime contract is missing or non-portable: ${subRuntimeContract ?? 'missing'}`);
  if (subRuntimeContract && existsSync(join(subRoot, subRuntimeContract))) {
    try {
      const runtime = JSON.parse(read(join(subRoot, subRuntimeContract)));
      for (const key of ['contract_version', 'package_id', 'inputs', 'outputs', 'required_permissions', 'network_access', 'external_side_effects', 'human_approval_points', 'rollback_strategy', 'writeback_scope', 'private_runtime_required']) if (runtime[key] === undefined) fail(`${name} runtime contract missing ${key}`);
      if (runtime.package_id !== name) fail(`${name} runtime contract package_id mismatch: ${runtime.package_id}`);
      if (!Array.isArray(runtime.inputs) || !Array.isArray(runtime.outputs) || !Array.isArray(runtime.required_permissions) || !Array.isArray(runtime.external_side_effects)) fail(`${name} runtime contract array fields are invalid`);
    } catch { fail(`${name} runtime contract is not valid JSON: ${subRuntimeContract}`); }
  }
  if (!existsSync(join(subRoot, subCanonical))) fail(`${name} canonical entry is missing`);
  if (subSkill && subSkill !== 'null') {
    if (subSkill.startsWith('/') || subSkill.includes('..') || !existsSync(join(subRoot, subSkill))) fail(`${name} manifest skill_entrypoint is missing or non-portable: ${subSkill}`);
    if (!subDeliveryModes.includes('ai-skill-draft') && !subDeliveryModes.includes('ai-skill-stable')) fail(`${name} declares skill_entrypoint without an ai-skill delivery mode`);
    if (!allowedSkillStatus.has(subSkillStatus)) fail(`${name} skill_status is invalid or missing`);
    if (existsSync(join(subRoot, subSkill))) {
      const skillFront = frontMatter(join(subRoot, subSkill), read(join(subRoot, subSkill)));
      const skillFileStatus = fieldValue(skillFront, 'skill_status');
      if (skillFileStatus && skillFileStatus !== subSkillStatus) fail(`${name} SKILL.md skill_status ${skillFileStatus} does not match manifest ${subSkillStatus}`);
    }
  } else {
    if (subSkillStatus) fail(`${name} skill_status must be omitted when skill_entrypoint is undeclared`);
    if (subDeliveryModes.some((mode) => mode.startsWith('ai-skill-'))) fail(`${name} has ai-skill delivery mode without skill_entrypoint`);
  }
  if (item.path !== `sub-libraries/${name}`) fail(`${name} registry path is not canonical`);
  if (item.version !== subVersion) fail(`${name} registry version ${item.version} does not match ${subVersion}`);
  if (item.release_status !== subStatus) fail(`${name} registry release_status ${item.release_status} does not match ${subStatus}`);
  const expected = { package_id: name, maturity_status: subMaturity, verification_status: subVerification, release_scope: subReleaseScope, runtime_contract: subRuntimeContract, dependency_mode: subDependencyMode, source_package_only: true, package_kind: subPackageKind, skill_entrypoint: subSkill && subSkill !== 'null' ? subSkill : null, skill_status: subSkillStatus ?? null, canonical_entry: subCanonical, included_in_mother: subIncludedInMother, license_status: subLicense };
  for (const [field, value] of Object.entries(expected)) if (item[field] !== value) fail(`${name} registry ${field} ${JSON.stringify(item[field])} does not match ${JSON.stringify(value)}`);
  if (JSON.stringify(item.delivery_modes) !== JSON.stringify(subDeliveryModes)) fail(`${name} registry delivery_modes does not match manifest`);
  const row = registry.split('\n').find((line) => line.includes(`](${name}/README.md)`));
  if (!row) fail(`sub-libraries/README.md lacks canonical ${name}/README.md row`);
  else {
    const displayMaturity = subMaturity.charAt(0).toUpperCase() + subMaturity.slice(1);
    for (const token of [subVersion, subStatus, displayMaturity, ...subDeliveryModes]) if (!row.includes(token)) fail(`${name} README registry row is stale: missing ${token}`);
  }
  const childValidator = join(subRoot, 'scripts/validate-sub-library.mjs');
  if (existsSync(childValidator)) {
    const motherGovernanceFixture = process.env.GOVERNANCE_TEST_FIXTURE === '1'
      && root.startsWith(join(realpathSync(tmpdir()), '701-governance-'))
      && root.endsWith(join('repo'))
      && !releaseMode
      && !prepareMode;
    const childModeArgs = [releaseMode ? '--release' : null, prepareMode ? '--prepare' : null].filter(Boolean);
    const result = spawnSync(process.execPath, [childValidator, ...childModeArgs], {
      cwd: subRoot,
      encoding: 'utf8',
      timeout: GOVERNANCE_COMMAND_TIMEOUT_MS,
      env: motherGovernanceFixture
        ? { ...process.env, WCO_GOVERNANCE_FIXTURE_FAST: '1' }
        : { ...process.env },
    });
    if (result.status !== 0) {
      const evidence = `${result.stdout ?? ''}${result.stderr ?? ''}`.trim().split('\n').slice(-3).join(' | ');
      fail(`${name} child validator failed${evidence ? `: ${evidence}` : ''}`);
    }
  }
}
for (const item of registryEntries) if (!subEntries.some((entry) => entry.name === item.id)) fail(`registry contains unknown sub-library or missing directory: ${item.id}`);

function verifyArtifact(rootPath) {
  const manifestPath = join(rootPath, 'MANIFEST.json');
  const sumsPath = join(rootPath, 'SHA256SUMS');
  if (!existsSync(manifestPath) && !existsSync(sumsPath)) return;
  if (!existsSync(manifestPath) || !existsSync(sumsPath)) { fail('artifact must contain both MANIFEST.json and SHA256SUMS'); return; }
  let artifact;
  try { artifact = JSON.parse(readFileSync(manifestPath, 'utf8')); } catch { fail('MANIFEST.json is not valid JSON'); return; }
  if (!Array.isArray(artifact.files) || !artifact.files.length) { fail('MANIFEST.json files list is missing or empty'); return; }
  const listed = new Set(artifact.files);
  for (const file of listed) {
    if (file.startsWith('/') || file.includes('..') || !existsSync(join(rootPath, file))) fail(`artifact manifest lists missing or unsafe file: ${file}`);
  }
  const actual = new Set(walk(rootPath).map((file) => relative(rootPath, file)));
  for (const file of actual) if (!['MANIFEST.json', 'SHA256SUMS'].includes(file) && !listed.has(file)) fail(`artifact contains unlisted file: ${file}`);
  const sums = readFileSync(sumsPath, 'utf8').trim().split('\n').filter(Boolean);
  const sumMap = new Map();
  for (const line of sums) { const match = line.match(/^([a-f0-9]{64})  (.+)$/); if (!match) { fail(`invalid SHA256SUMS line: ${line}`); continue; } sumMap.set(match[2], match[1]); }
  for (const file of [...listed, 'MANIFEST.json']) {
    const expected = sumMap.get(file);
    const actualHash = createHash('sha256').update(readFileSync(join(rootPath, file))).digest('hex');
    if (expected !== actualHash) fail(`artifact checksum mismatch: ${file}`);
  }
}
verifyArtifact(root);

console.log(`Mother library: ${root}`);
console.log(`Version: ${version ?? 'unknown'}`);
console.log(`Mode: ${releaseMode ? 'release' : prepareMode ? 'prepare' : 'structure'}`);
for (const item of warnings) console.log(`WARN: ${item}`);
for (const item of failures) console.log(`FAIL: ${item}`);
if (failures.length) { console.error(`\nBLOCK: ${failures.length} check(s) failed.`); process.exitCode = 1; }
else console.log('\nSTRUCTURE_PASS: static mother-library checks passed; this is not release approval.');
