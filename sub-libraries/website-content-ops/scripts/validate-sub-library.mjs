#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { scanPublishableContent } from './content-safety.mjs';
import { validateJsonSchema } from './json-schema-lite.mjs';
import { parseMarkdownFrontMatter } from './front-matter.mjs';
import {
  GENERATED_ARTIFACT_FILES,
  isManifestExcluded,
  isManifestIncluded,
} from './manifest-policy.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const libraryRoot = resolve(dirname(scriptPath), '..');
const releaseMode = process.argv.includes('--release');
const prepareMode = process.argv.includes('--prepare');
const failures = [];
const warnings = [];

const linkGate = spawnSync(process.execPath, [join(libraryRoot, 'scripts/validate-links.mjs'), ...((releaseMode || prepareMode) ? ['--release'] : []), libraryRoot], { encoding: 'utf8' });
if (linkGate.status !== 0) fail('local Markdown link validation failed');
process.stdout.write(linkGate.stdout ?? '');
process.stderr.write(linkGate.stderr ?? '');
const allowedMaturity = new Set(['draft', 'validated', 'stable', 'deprecated']);
const allowedVerification = new Set(['unverified', 'structure-pass', 'evidence-partial', 'e2e-pass']);
const allowedRelease = new Set(['BLOCK', 'Preview', 'candidate', 'Ready', 'Published', 'retired']);
const allowedLicense = new Set(['pending', 'cleared', 'restricted', 'unknown']);
const allowedApproval = new Set(['pending', 'approved', 'rejected', 'expired']);
const allowedDependency = new Set(['self-contained', 'declared-external-runtime']);
const allowedPackageKinds = new Set(['standalone-sub-library']);
const allowedDeliveryModes = new Set(['human-playbook', 'ai-skill-draft', 'ai-skill-stable', 'toolkit', 'adapter', 'template-pack', 'reference-implementation', 'course']);
const allowedSkillStatus = new Set(['draft-adapter-not-installable', 'preview-adapter-not-installable', 'validated-adapter', 'stable-adapter', 'retired']);
const ignoredSourceDirs = new Set(['.git', '.obsidian', 'node_modules', 'dist', 'credentials', 'workspace']);

const requiredFiles = [
  'README.md', 'MANIFEST.md', 'AGENTS.md', 'START-HERE.md', 'COURSE-MAP.md',
  'LICENSE', 'LICENSE.md', 'NOTICE', 'THIRD-PARTY-NOTICES.md',
  'MENTAL-MODEL.md', 'PLAYBOOK.md', 'TOOLS.md', 'TEMPLATES/README.md',
  'EXAMPLES/README.md', 'ADAPTERS/README.md', 'ADAPTERS/_template.md',
  'QA-CHECKLIST.md', 'SOURCES.md', 'BRAND.md', 'CONTACT.md', 'VERSION.md',
  'WRITEBACK.md', 'CHANGELOG.md', 'RELEASE.md', 'INSTALL.md',
  'REFERENCES/README.md', 'scripts/README.md', 'scripts/validate-artifact.mjs', 'scripts/validate-links.mjs', 'scripts/validate-release-approval.mjs', 'scripts/sync-workspace-template.mjs',
  'scripts/content-safety.mjs', 'scripts/front-matter.mjs', 'scripts/json-schema-lite.mjs', 'scripts/manifest-policy.mjs', 'scripts/release-governance.test.mjs',
  '.gitignore', 'RUNTIME-CONTRACT.json', 'SCHEMAS/runtime-contract.schema.json',
];

function fail(message) { failures.push(message); }
function warn(message) { warnings.push(message); }
function read(path) { return readFileSync(path, 'utf8'); }
function statSafeDir(path) { try { return statSync(path).isDirectory(); } catch { return false; } }
function enforceCleanGitRelease() {
  if (!releaseMode) return;
  const probe = spawnSync('git', ['rev-parse', '--show-toplevel'], { cwd: libraryRoot, encoding: 'utf8' });
  if (probe.status !== 0) { warn('release mode running without Git metadata; commit/artifact provenance remains unverified'); return; }
  const status = spawnSync('git', ['status', '--porcelain', '--untracked-files=all'], { cwd: libraryRoot, encoding: 'utf8' });
  if ((status.stdout ?? '').trim()) fail('release mode requires a clean Git worktree');
}
function isInside(parent, candidate) {
  const p = resolve(parent) + sep;
  return resolve(candidate) === resolve(parent) || resolve(candidate).startsWith(p);
}
function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (ignoredSourceDirs.has(entry.name)) continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(path));
    else out.push(path);
  }
  return out;
}
function parseFrontMatter(path, content) {
  const source = relative(libraryRoot, path).split(sep).join('/');
  try {
    return parseMarkdownFrontMatter(content, { source }).attributes;
  } catch (error) {
    fail(error.message);
    return null;
  }
}
function fieldValue(front, field) {
  return front && Object.hasOwn(front, field) ? front[field] : null;
}
function fieldArray(front, field, source = 'front matter') {
  const value = fieldValue(front, field);
  if (value === null) return [];
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string' || !item.trim())) {
    fail(`${source} ${field} must be an array of strings`);
    return [];
  }
  return value.map((item) => item.trim());
}
function isExternal(value) { return /^(https?:|mailto:|data:|tel:|#)/i.test(value); }
function isPathLike(value) {
  if (typeof value !== 'string' || isExternal(value)) return false;
  const candidate = value.trim();
  return candidate.startsWith('.')
    || candidate.startsWith('/')
    || /^file:/i.test(candidate)
    || /^[A-Za-z]:[\\/]/.test(candidate)
    || candidate.includes('\\')
    || /\.(md|json|mjs|js|txt|yaml|yml|sh|png|jpg|jpeg|webp)(?:[?#].*)?$/i.test(candidate)
    || (candidate.includes('/') && !/\s/.test(candidate));
}
function checkLocalReference(path, value, field) {
  if (!isPathLike(value)) return;
  const portable = value.trim().replace(/^<|>$/g, '').split('#')[0].split('?')[0];
  if (portable.startsWith('/') || /^file:/i.test(portable) || /^[A-Za-z]:[\\/]/.test(portable) || portable.includes('\\')) {
    fail(`${relative(libraryRoot, path)} ${field} has non-portable local path: ${value}`);
    return;
  }
  const resolved = resolve(dirname(path), portable);
  if (!isInside(libraryRoot, resolved)) {
    fail(`${relative(libraryRoot, path)} ${field} escapes sub-library root: ${value}`);
  } else if (!existsSync(resolved)) {
    fail(`${relative(libraryRoot, path)} ${field} links to missing path: ${value}`);
  }
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

for (const file of requiredFiles) if (!existsSync(join(libraryRoot, file))) fail(`missing required file: ${file}`);
const workspaceSync = spawnSync(process.execPath, [join(libraryRoot, 'scripts/sync-workspace-template.mjs'), '--check'], { cwd: libraryRoot, encoding: 'utf8' });
if (workspaceSync.status !== 0) {
  fail('WORKSPACE-TEMPLATE generated copies are stale or not self-contained');
  if (workspaceSync.stderr?.trim()) console.error(workspaceSync.stderr.trim());
}
enforceCleanGitRelease();

const files = walk(libraryRoot);
const textFiles = files.filter((p) => ['.md', '.json', '.mjs', '.js', '.txt', '.yaml', '.yml'].includes(extname(p).toLowerCase()));
const markdownFiles = files.filter((p) => extname(p).toLowerCase() === '.md');
const markdownMetadata = new Map();
for (const path of markdownFiles) {
  const content = read(path);
  const front = parseFrontMatter(path, content);
  markdownMetadata.set(path, front);
  checkMarkdownLinks(path, content);
  for (const field of ['sources', 'related']) {
    for (const value of fieldArray(front, field, relative(libraryRoot, path))) checkLocalReference(path, value, `${field} reference`);
  }
}

function validateDurableIds(durableRoots) {
  const stable = new Map();
  const singletonNames = new Set(['index.md', 'README.md', 'AGENTS.md', 'CLAUDE.md', 'MANIFEST.md', 'VERSION.md', 'RELEASE.md', 'CHANGELOG.md', 'LICENSE.md']);
  const ignoredRecordTypes = new Set(['redirect', 'verification-record', 'writeback-record']);
  for (const path of markdownFiles) {
    const rel = relative(libraryRoot, path).split(sep).join('/');
    const rootName = rel.split('/')[0];
    if (!durableRoots.some((root) => rootName === root || rel.startsWith(`${root}/`))) continue;
    const base = basename(path);
    const front = markdownMetadata.get(path) ?? parseFrontMatter(path, read(path));
    const type = fieldValue(front, 'type');
    if (singletonNames.has(base) || ignoredRecordTypes.has(type)) continue;
    const match = base.match(/^id-(\d{4})-[a-z0-9][a-z0-9-]*\.md$/);
    if (!match) { fail(`durable root page must use id-####-slug.md: ${rel}`); continue; }
    const id = `ID-${match[1]}`;
    if (!stable.has(id)) stable.set(id, []);
    stable.get(id).push(rel);
    if (fieldValue(front, 'doc_id') !== id) fail(`durable page doc_id must be ${id}: ${rel}`);
    const keywords = fieldArray(front, 'keywords');
    if (keywords.length < 3 || keywords.length > 8) fail(`durable page keywords must contain 3-8 retrieval terms: ${rel}`);
    if (!fieldValue(front, 'when_to_read')) fail(`durable page missing when_to_read: ${rel}`);
  }
  for (const [id, paths] of stable) if (paths.length > 1) fail(`duplicate durable page ID ${id}: ${paths.join(', ')}`);
}

for (const path of textFiles) {
  const content = read(path);
  for (const issue of scanPublishableContent(content)) fail(`content safety ${issue.code}: ${relative(libraryRoot, path)}`);
  const staleAllinCmsPath = 'allincms' + '.md';
  if (path !== scriptPath && content.includes(staleAllinCmsPath)) fail(`stale AllinCMS path reference: ${relative(libraryRoot, path)}`);
}

function checkNameCollisions(dir) {
  const entries = readdirSync(dir, { withFileTypes: true });
  const names = new Set(entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name));
  for (const entry of entries) {
    if (entry.isSymbolicLink()) { fail(`symlink is not allowed: ${relative(libraryRoot, join(dir, entry.name))}`); continue; }
    if (['.git', '.obsidian', 'node_modules', 'dist'].includes(entry.name)) continue;
    if (entry.isFile()) {
      const stem = basename(entry.name, extname(entry.name));
      if (names.has(stem)) fail(`file/directory name collision in ${relative(libraryRoot, dir)}: ${entry.name} and ${stem}/`);
    } else if (entry.isDirectory()) checkNameCollisions(join(dir, entry.name));
  }
}
checkNameCollisions(libraryRoot);

const versionText = read(join(libraryRoot, 'VERSION.md'));
const version = versionText.match(/Version：`([^`]+)`/)?.[1];
const manifestText = read(join(libraryRoot, 'MANIFEST.md'));
const manifestFront = markdownMetadata.get(join(libraryRoot, 'MANIFEST.md')) ?? parseFrontMatter(join(libraryRoot, 'MANIFEST.md'), manifestText);
const manifestStatus = fieldValue(manifestFront, 'release_status');
const maturityStatus = fieldValue(manifestFront, 'maturity_status');
const verificationStatus = fieldValue(manifestFront, 'verification_status');
const releaseScope = fieldValue(manifestFront, 'release_scope');
const packageId = fieldValue(manifestFront, 'package_id') ?? basename(libraryRoot);
const runtimeContract = fieldValue(manifestFront, 'runtime_contract');
const dependencyMode = fieldValue(manifestFront, 'dependency_mode');
const durableRoots = fieldArray(manifestFront, 'durable_roots', 'MANIFEST.md');
const sourcePackageOnly = fieldValue(manifestFront, 'source_package_only');
const packageKind = fieldValue(manifestFront, 'package_kind');
const includedInMother = fieldValue(manifestFront, 'included_in_mother');
const licenseStatus = fieldValue(manifestFront, 'license_status');
const approvalRequired = fieldValue(manifestFront, 'approval_required');
const approvalStatus = fieldValue(manifestFront, 'approval_status');
const repositoryStatus = fieldValue(manifestFront, 'repository_status');
const previewPublicationStatus = fieldValue(manifestFront, 'preview_publication_status');
const previewVersion = fieldValue(manifestFront, 'preview_version');
const previewTag = fieldValue(manifestFront, 'preview_tag');
const tagNamespace = fieldValue(manifestFront, 'tag_namespace');
const tagPrefix = fieldValue(manifestFront, 'tag_prefix');
const skillEntrypoint = fieldValue(manifestFront, 'skill_entrypoint');
const skillStatus = fieldValue(manifestFront, 'skill_status');
const deliveryModes = fieldArray(manifestFront, 'delivery_modes', 'MANIFEST.md');
const includePatterns = fieldArray(manifestFront, 'include', 'MANIFEST.md');
const excludePatterns = fieldArray(manifestFront, 'exclude', 'MANIFEST.md');
if (!version) fail('VERSION.md has no machine-readable Version field');
const hasSourceRegistry = existsSync(resolve(libraryRoot, '../README.md')) && existsSync(resolve(libraryRoot, '../registry.json'));
if (hasSourceRegistry && packageId !== basename(libraryRoot)) fail(`MANIFEST.md package_id must equal directory name: ${packageId}`);
if (!allowedMaturity.has(maturityStatus)) fail(`MANIFEST.md maturity_status is invalid: ${maturityStatus ?? 'missing'}`);
if (!allowedVerification.has(verificationStatus)) fail(`MANIFEST.md verification_status is invalid: ${verificationStatus ?? 'missing'}`);
if (!allowedRelease.has(manifestStatus)) fail(`MANIFEST.md release_status is invalid: ${manifestStatus ?? 'missing'}`);
if (!allowedLicense.has(licenseStatus)) fail(`MANIFEST.md license_status is invalid: ${licenseStatus ?? 'missing'}`);
if (approvalRequired !== true) fail(`MANIFEST.md approval_required must be boolean true: ${approvalRequired ?? 'missing'}`);
if (!allowedApproval.has(approvalStatus)) fail(`MANIFEST.md approval_status is invalid: ${approvalStatus ?? 'missing'}`);
if (manifestStatus === 'Preview') {
  if (repositoryStatus !== 'public-preview') fail(`Preview requires repository_status public-preview: ${repositoryStatus ?? 'missing'}`);
  if (!['Ready', 'Published'].includes(previewPublicationStatus)) fail(`Preview publication status is invalid: ${previewPublicationStatus ?? 'missing'}`);
  if (previewVersion !== version) fail(`preview_version must match VERSION.md: ${previewVersion ?? 'missing'} != ${version ?? 'missing'}`);
  if (previewTag !== `v${version}`) fail(`preview_tag must be v${version}: ${previewTag ?? 'missing'}`);
  if (licenseStatus !== 'cleared') fail('Preview requires license_status cleared');
}
const expectedTagNamespace = `sub-library/${packageId}`;
if (tagNamespace !== expectedTagNamespace) fail(`MANIFEST.md tag_namespace must be ${expectedTagNamespace}: ${tagNamespace ?? 'missing'}`);
if (tagPrefix !== `${expectedTagNamespace}/v`) fail(`MANIFEST.md tag_prefix must be ${expectedTagNamespace}/v: ${tagPrefix ?? 'missing'}`);
if (releaseScope !== 'standalone-sub-library') fail(`MANIFEST.md release_scope is not standalone-sub-library: ${releaseScope ?? 'missing'}`);
if (!allowedDependency.has(dependencyMode)) fail(`MANIFEST.md dependency_mode is invalid: ${dependencyMode ?? 'missing'}`);
if (!durableRoots.length || durableRoots.some((item) => item.startsWith('/') || item.includes('..') || item.includes('\\'))) fail(`MANIFEST.md durable_roots are invalid: ${JSON.stringify(durableRoots)}`);
if (packageKind !== 'standalone-sub-library' || !allowedPackageKinds.has(packageKind)) fail(`MANIFEST.md package_kind is invalid: ${packageKind ?? 'missing'}`);
if (runtimeContract !== 'RUNTIME-CONTRACT.json') fail(`MANIFEST.md runtime_contract must be RUNTIME-CONTRACT.json: ${runtimeContract ?? 'missing'}`);
if (sourcePackageOnly !== true) fail('MANIFEST.md source_package_only must be boolean true');
if (includedInMother !== 'source-only') fail(`MANIFEST.md included_in_mother must be source-only: ${includedInMother ?? 'missing'}`);
if (!deliveryModes.length || deliveryModes.some((mode) => !allowedDeliveryModes.has(mode)) || new Set(deliveryModes).size !== deliveryModes.length) fail(`MANIFEST.md delivery_modes are invalid: ${JSON.stringify(deliveryModes)}`);
if (!includePatterns.length) fail('MANIFEST.md include allowlist must not be empty');
for (const path of files) {
  const rel = relative(libraryRoot, path).split(sep).join('/');
  if (GENERATED_ARTIFACT_FILES.has(rel)) continue;
  if (!isManifestIncluded(rel, includePatterns) && !isManifestExcluded(rel, excludePatterns)) {
    fail(`source file is not covered by manifest include/exclude rules: ${rel}`);
  }
}
try {
  const runtime = JSON.parse(read(join(libraryRoot, runtimeContract)));
  const schemaRef = runtime.schema_ref;
  if (schemaRef !== 'SCHEMAS/runtime-contract.schema.json') fail(`RUNTIME-CONTRACT.json schema_ref must be SCHEMAS/runtime-contract.schema.json: ${schemaRef ?? 'missing'}`);
  const schemaPath = resolve(libraryRoot, schemaRef ?? '');
  if (!schemaRef || !isInside(libraryRoot, schemaPath) || !existsSync(schemaPath)) {
    fail('RUNTIME-CONTRACT.json schema_ref is missing, unsafe, or unresolved');
  } else {
    const schema = JSON.parse(read(schemaPath));
    if (schema?.properties?.package_id?.const !== packageId) fail('runtime contract schema package_id const does not match MANIFEST.md');
    for (const issue of validateJsonSchema(runtime, schema)) fail(`RUNTIME-CONTRACT schema violation: ${issue}`);
  }
  if (runtime.package_id !== packageId) fail(`RUNTIME-CONTRACT.json package_id mismatch: ${runtime.package_id}`);
 } catch (error) { fail(`RUNTIME-CONTRACT.json or its schema is not valid JSON: ${error.message}`); }

function validateAdapterPackage() {
  const adapterRoot = join(libraryRoot, 'ADAPTERS/cms/allincms');
  const packagePath = join(adapterRoot, 'package.json');
  const lockPath = join(adapterRoot, 'package-lock.json');
  for (const required of ['.gitignore', '.npmignore', 'package.json', 'package-lock.json']) {
    if (!existsSync(join(adapterRoot, required))) fail(`AllinCMS adapter missing package boundary file: ADAPTERS/cms/allincms/${required}`);
  }
  if (!existsSync(packagePath) || !existsSync(lockPath)) return;
  let packageJson;
  let packageLock;
  try { packageJson = JSON.parse(read(packagePath)); } catch (error) { fail(`AllinCMS package.json is invalid JSON: ${error.message}`); return; }
  try { packageLock = JSON.parse(read(lockPath)); } catch (error) { fail(`AllinCMS package-lock.json is invalid JSON: ${error.message}`); return; }
  if (packageJson.name !== 'allincms-media-adapter') fail('AllinCMS package name must remain allincms-media-adapter');
  if (packageJson.version !== version) fail(`AllinCMS package version ${packageJson.version ?? 'missing'} must match sub-library ${version}`);
  if (packageJson.private !== true) fail('AllinCMS package must remain private:true while release/license approval is blocked');
  if (licenseStatus !== 'cleared' && packageJson.license !== 'UNLICENSED') fail('AllinCMS package license must be UNLICENSED while sub-library license_status is not cleared');
  if (licenseStatus === 'cleared' && packageJson.license !== 'Apache-2.0') fail('AllinCMS package license must be Apache-2.0 when sub-library license_status is cleared');
  if (packageJson.engines?.node !== '>=20.9.0') fail('AllinCMS package engines.node must be >=20.9.0');
  if (packageJson.dependencies?.sharp !== '0.35.3') fail('AllinCMS sharp dependency must be exactly pinned to 0.35.3');
  const lifecycle = ['preinstall', 'install', 'postinstall', 'prepack', 'prepare', 'postpack'];
  for (const name of lifecycle) if (Object.hasOwn(packageJson.scripts || {}, name)) fail(`AllinCMS package must not define lifecycle script ${name}`);
  if (!Array.isArray(packageJson.files) || packageJson.files.length === 0 || packageJson.files.some((item) => typeof item !== 'string' || !item.trim())) {
    fail('AllinCMS package files allowlist must be a non-empty string array');
  }
  if (packageLock.lockfileVersion !== 3) fail(`AllinCMS package-lock lockfileVersion must be 3: ${packageLock.lockfileVersion ?? 'missing'}`);
  const lockRoot = packageLock.packages?.[''];
  if (!lockRoot || lockRoot.name !== packageJson.name || lockRoot.version !== packageJson.version
      || lockRoot.license !== packageJson.license || lockRoot.engines?.node !== packageJson.engines.node
      || JSON.stringify(lockRoot.dependencies) !== JSON.stringify(packageJson.dependencies)) {
    fail('AllinCMS package-lock root metadata does not exactly match package.json');
  }
  for (const [name, record] of Object.entries(packageLock.packages || {})) {
    if (!name) continue;
    if (record.resolved && !/^https:\/\//.test(record.resolved)) fail(`AllinCMS lock entry ${name} resolved URL must use HTTPS`);
    if (record.resolved && !record.integrity) fail(`AllinCMS lock entry ${name} is missing integrity`);
  }
  const packed = spawnSync('npm', ['pack', '--dry-run', '--json'], { cwd: adapterRoot, encoding: 'utf8' });
  if (packed.status !== 0) {
    fail(`AllinCMS npm package dry-run failed: ${(packed.stderr || packed.stdout || '').trim()}`);
    return;
  }
  let filesInPack;
  try { filesInPack = JSON.parse(packed.stdout)?.[0]?.files?.map((item) => item.path) ?? []; }
  catch (error) { fail(`AllinCMS npm pack dry-run did not return valid JSON: ${error.message}`); return; }
  if (!filesInPack.length) fail('AllinCMS npm pack dry-run produced no inspectable files');
  for (const path of filesInPack) {
    if (path.startsWith('/') || path.includes('..') || /(^|\/)(node_modules|fixtures|coverage)(\/|$)/.test(path)
        || /\.test\.mjs$/.test(path) || /\.redacted\.(?:md|json)$/.test(path)) {
      fail(`AllinCMS npm package contains forbidden file: ${path}`);
    }
  }
}
validateAdapterPackage();
if (skillEntrypoint && skillEntrypoint !== 'null') {
  if (skillEntrypoint.startsWith('/') || skillEntrypoint.includes('..') || !existsSync(join(libraryRoot, skillEntrypoint))) fail(`manifest skill_entrypoint is missing or non-portable: ${skillEntrypoint}`);
  if (!deliveryModes.includes('ai-skill-draft') && !deliveryModes.includes('ai-skill-stable')) fail('manifest skill_entrypoint requires an ai-skill delivery mode');
  if (!allowedSkillStatus.has(skillStatus)) fail(`MANIFEST.md skill_status is invalid or missing: ${skillStatus ?? 'missing'}`);
  if (existsSync(join(libraryRoot, skillEntrypoint))) {
    const skillPath = join(libraryRoot, skillEntrypoint);
    const skillFront = markdownMetadata.get(skillPath) ?? parseFrontMatter(skillPath, read(skillPath));
    const skillFileStatus = fieldValue(skillFront, 'skill_status');
    if (skillFileStatus && skillFileStatus !== skillStatus) fail(`SKILL.md skill_status ${skillFileStatus} does not match manifest ${skillStatus}`);
  }
} else {
  if (skillStatus) fail('MANIFEST.md skill_status must be omitted when skill_entrypoint is undeclared');
  if (deliveryModes.some((mode) => mode.startsWith('ai-skill-'))) fail('manifest has ai-skill delivery mode without skill_entrypoint');
}
const registryPath = resolve(libraryRoot, '../README.md');
const machineRegistryPath = resolve(libraryRoot, '../registry.json');
if (hasSourceRegistry) {
  const registry = read(registryPath);
  let machineRegistry;
  try { machineRegistry = JSON.parse(read(machineRegistryPath)); } catch { fail('sub-libraries/registry.json is not valid JSON'); machineRegistry = { entries: [] }; }
  const entry = Array.isArray(machineRegistry.entries) ? machineRegistry.entries.find((item) => item?.id === basename(libraryRoot)) : null;
  if (!entry) fail(`sub-library registry lacks ${basename(libraryRoot)}`);
  else {
    if (entry.id !== basename(libraryRoot) || entry.path !== `sub-libraries/${basename(libraryRoot)}`) fail('sub-library registry id/path is not canonical');
    if (entry.version !== version) fail(`sub-library registry version ${entry.version} does not match ${version}`);
    if (entry.release_status !== manifestStatus) fail(`sub-library registry release_status ${entry.release_status} does not match ${manifestStatus}`);
    const expected = { package_id: packageId, maturity_status: maturityStatus, verification_status: verificationStatus, release_scope: releaseScope, runtime_contract: runtimeContract, dependency_mode: dependencyMode, durable_roots: durableRoots, source_package_only: true, package_kind: packageKind, skill_entrypoint: skillEntrypoint && skillEntrypoint !== 'null' ? skillEntrypoint : null, skill_status: skillStatus ?? null, canonical_entry: 'README.md', included_in_mother: includedInMother, license_status: licenseStatus, approval_required: approvalRequired === true, approval_status: approvalStatus, tag_namespace: tagNamespace, tag_prefix: tagPrefix };
    for (const [field, value] of Object.entries(expected)) {
      const matches = Array.isArray(value) ? JSON.stringify(entry[field]) === JSON.stringify(value) : entry[field] === value;
      if (!matches) fail(`sub-library registry ${field} ${JSON.stringify(entry[field])} does not match ${JSON.stringify(value)}`);
    }
    if (!Array.isArray(entry.delivery_modes) || JSON.stringify(entry.delivery_modes) !== JSON.stringify(deliveryModes)) fail('sub-library registry delivery_modes does not match manifest');
    if (!registry.split('\n').some((line) => line.includes(`](${basename(libraryRoot)}/README.md)`) && line.includes(version) && line.includes(manifestStatus))) fail('sub-libraries/README.md canonical row is stale');
  }
} else {
  warn('standalone artifact has no mother-library registry; source-level registry check skipped as expected');
}
if ((releaseMode || prepareMode) && !['Ready', 'Published'].includes(manifestStatus)) {
  fail('release mode requires MANIFEST.md release_status Ready or Published');
}
validateDurableIds(durableRoots);
if (manifestStatus === 'BLOCK') warn('release_status is BLOCK: structural checks may pass, but external stable release is not approved');
if (manifestStatus === 'Preview') warn('release_status is Preview: public single-sample use is allowed, but formal Stable qualification remains blocked');
if (licenseStatus !== 'cleared') warn('license status is not cleared; this blocks external release');
if (approvalStatus !== 'approved') warn('approval status is not approved; a human approval sidecar is still required for external release');
if (manifestStatus === 'Ready' || manifestStatus === 'Published') {
  if (licenseStatus !== 'cleared') fail('Ready/Published requires license_status cleared');
  if (!prepareMode && approvalStatus !== 'approved') fail('Ready/Published requires approval_status approved outside preparation mode');
  if (prepareMode && approvalStatus !== 'pending') fail('preparation requires approval_status pending so the frozen candidate cannot self-certify approval');
  if (prepareMode && manifestStatus !== 'Ready') fail('preparation requires release_status Ready; Published is an external post-qualification state');
  if (verificationStatus !== 'e2e-pass') fail('Ready/Published requires verification_status e2e-pass');
  if (maturityStatus !== 'stable') fail('Ready/Published requires maturity_status stable');
}

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
verifyArtifact(libraryRoot);

console.log(`Sub-library: ${relative(resolve(libraryRoot, '..'), libraryRoot)}`);
console.log(`Version: ${version ?? 'unknown'}`);
console.log(`Mode: ${releaseMode ? 'release' : prepareMode ? 'prepare' : 'structure'}`);
for (const item of warnings) console.log(`WARN: ${item}`);
for (const item of failures) console.log(`FAIL: ${item}`);
if (failures.length) {
  console.error(`\nBLOCK: ${failures.length} check(s) failed.`);
  process.exitCode = 1;
} else {
  console.log('\nSTRUCTURE_PASS: static sub-library checks passed; this is not release approval.');
}
