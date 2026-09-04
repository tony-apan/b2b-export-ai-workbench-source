#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, readdirSync, realpathSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { scanPublishableContent } from './content-safety.mjs';
import { validateJsonSchema } from './json-schema-lite.mjs';
import { parseMarkdownFrontMatter } from './front-matter.mjs';
import { shouldUseGovernanceFixtureFastMode } from './governance-fixture-fast-mode.mjs';
import {
  GENERATED_ARTIFACT_FILES,
  isManifestExcluded,
  isManifestIncluded,
} from './manifest-policy.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const libraryRoot = resolve(dirname(scriptPath), '..');
const releaseMode = process.argv.includes('--release');
const prepareMode = process.argv.includes('--prepare');
const GOVERNANCE_COMMAND_TIMEOUT_MS = 120_000;
const ARTICLE_REGRESSION_TIMEOUT_MS = 240_000;
const failures = [];
const warnings = [];
const requiredStateProjections = new Map([
  ['README.md', ['release_status', 'preview_publication_status', 'license_status']],
  ['INSTALL.md', ['release_status', 'preview_publication_status']],
  ['RELEASE.md', ['release_status', 'preview_publication_status']],
  ['VERSION.md', ['release_status', 'preview_publication_status', 'historical_published_version', 'historical_published_tag', 'current_candidate_identity', 'current_candidate_snapshot', 'current_candidate_version']],
  ['SKILL.md', ['release_status', 'preview_publication_status', 'skill_status']],
  ['LICENSE.md', ['release_status', 'license_status']],
]);
const minimumPublicReleaseClaimDocuments = Object.freeze([
  'MANIFEST.md', 'README.md', 'START-HERE.md', 'INSTALL.md', 'RELEASE.md',
  'VERSION.md', 'CHANGELOG.md', 'SKILL.md', 'LICENSE.md',
]);
const releaseStateContradictionCode = 'WCO_RELEASE_STATE_CONTRADICTION';

const linkGate = spawnSync(process.execPath, [join(libraryRoot, 'scripts/validate-links.mjs'), ...((releaseMode || prepareMode) ? ['--release'] : []), libraryRoot], { encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
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
const sourcePublicationClearanceFields = ['publication_review_status', 'publication_status', 'license_status'];
const sourceCardPathPattern = /^REFERENCES\/SRC-[A-Za-z0-9][A-Za-z0-9._-]*\.md$/;
const referenceMarkdownPathPattern = /^REFERENCES\/.+\.md$/i;
const allowedSourcePublicationReviewStatuses = new Set(['pending', 'approved', 'rejected']);
const allowedSourcePublicationStatuses = new Set(['BLOCK', 'PASS']);
const allowedSourceLicenseStatuses = new Set(['pending', 'cleared', 'restricted', 'unknown']);
const sourceInventoryRelativePath = 'REFERENCES/SOURCE-INVENTORY.json';
const sourceIdPattern = /^SRC-[A-Za-z0-9][A-Za-z0-9._-]*$/;
const sha256Pattern = /^[a-f0-9]{64}$/;
const protectedSourceIds = Object.freeze([
  'SRC-20260727-ALLINCMS-OFFICIAL',
  'SRC-20260727-PICGO-IMAGE-HOSTS-OFFICIAL',
  'SRC-20260731-B2B-SEO-CONTENT-RESEARCH',
]);

const requiredFiles = [
  'README.md', 'MANIFEST.md', 'AGENTS.md', 'START-HERE.md', 'COURSE-MAP.md',
  'LICENSE', 'LICENSE.md', 'NOTICE', 'THIRD-PARTY-NOTICES.md',
  'MENTAL-MODEL.md', 'PLAYBOOK.md', 'TOOLS-INDEX.md', 'TEMPLATES/README.md',
  'EXAMPLES/README.md', 'ADAPTERS/README.md', 'ADAPTERS/_template.md',
  'QA-CHECKLIST.md', 'SOURCES.md', 'BRAND.md', 'CONTACT.md', 'VERSION.md',
  'WRITEBACK.md', 'CHANGELOG.md', 'RELEASE.md', 'INSTALL.md',
  'REFERENCES/README.md', sourceInventoryRelativePath,
  'PLAYBOOKS/README.md', 'PLAYBOOKS/id-0001-b2b-seo-article-standard.md', 'PLAYBOOKS/id-0003-b2b-article-optimization-sop.md', 'PLAYBOOKS/id-0004-b2b-article-stage-patterns.md', 'PLAYBOOKS/id-0005-source-driven-cms-operation-sop.md',
  'TEMPLATES/article-brief.md', 'TEMPLATES/article-draft.md', 'TEMPLATES/article-quality-review.md', 'TEMPLATES/content-operation-plan.md',
  'EXAMPLES/fluxpedal-motors/b2b-seo-article-brief.md', 'EXAMPLES/fluxpedal-motors/b2b-seo-article-draft.md', 'EXAMPLES/fluxpedal-motors/b2b-seo-article-review.md', 'EXAMPLES/fluxpedal-motors/b2b-seo-publish-record.md',
  'scripts/README.md', 'scripts/validate-artifact.mjs', 'scripts/validate-links.mjs', 'scripts/validate-release-approval.mjs', 'scripts/sync-workspace-template.mjs',
  'scripts/validate-article-package.mjs', 'scripts/article-package.test.mjs', 'scripts/content-operation-plan.test.mjs', 'scripts/validate-content-operation-plan.mjs', 'scripts/sync-workspace-template.test.mjs',
  'scripts/build-review-freeze.mjs', 'scripts/build-review-freeze.test.mjs', 'scripts/verify-review-freeze.mjs', 'scripts/verify-review-freeze.test.mjs',
  'scripts/content-safety.mjs', 'scripts/front-matter.mjs', 'scripts/json-schema-lite.mjs', 'scripts/manifest-policy.mjs', 'scripts/release-governance.test.mjs',
  '.gitignore', 'RUNTIME-CONTRACT.json', 'SCHEMAS/runtime-contract.schema.json', 'SCHEMAS/content-operation-plan.schema.json',
];

function fail(message) { failures.push(message); }
function warn(message) { warnings.push(message); }
function readBytes(path) {
  const label = relative(libraryRoot, path).split(sep).join('/');
  let stats;
  try {
    stats = lstatSync(path);
  } catch (error) {
    fail(`${label} cannot be inspected before read: ${error.message}`);
    return Buffer.alloc(0);
  }
  if (stats.isSymbolicLink() || !stats.isFile()) {
    fail(`${label} must be a regular non-symlink file before read`);
    return Buffer.alloc(0);
  }
  return readFileSync(path);
}
function read(path) { return readBytes(path).toString('utf8'); }
function enforceCleanGitRelease() {
  if (!releaseMode) return;
  const probe = spawnSync('git', ['rev-parse', '--show-toplevel'], { cwd: libraryRoot, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
  if (probe.status !== 0) { warn('release mode running without Git metadata; commit/artifact provenance remains unverified'); return; }
  const status = spawnSync('git', ['status', '--porcelain', '--untracked-files=all'], { cwd: libraryRoot, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
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
    const label = relative(libraryRoot, path).split(sep).join('/');
    let stats;
    try {
      stats = lstatSync(path);
    } catch (error) {
      fail(`${label} cannot be inspected during traversal: ${error.message}`);
      continue;
    }
    if (stats.isSymbolicLink()) {
      fail(`${label} must not be a symbolic link`);
      continue;
    }
    if (stats.isDirectory()) out.push(...walk(path));
    else if (stats.isFile()) out.push(path);
    else fail(`${label} must be a regular file or directory`);
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
function validateInstallableSkillMetadata() {
  const rel = 'SKILL-INSTALL/SKILL.md';
  const path = join(libraryRoot, rel);
  if (!existsSync(path)) { fail(`${rel} is missing`); return; }
  const parsed = parseFrontMatter(path, read(path));
  if (!parsed) return;
  const name = fieldValue(parsed, 'name');
  const description = fieldValue(parsed, 'description');
  if (name !== 'allincms-bulk-content-upload' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name) || name.length > 64) {
    fail(`${rel} name must be the canonical lowercase kebab-case identifier`);
  }
  if (typeof description !== 'string' || !description.trim()) {
    fail(`${rel} description must be a non-empty string`);
    return;
  }
  if (description.length > 1024 || Buffer.byteLength(description, 'utf8') > 1024) {
    fail(`${rel} description exceeds the 1024-character/UTF-8-byte host discovery limit`);
  }
  const prefix = description.slice(0, 250);
  const triggerFamilies = [
    ['CMS brand', /AllinCMS|LAICMS/i],
    ['Chinese site task', /建站|更新网站/],
    ['product/taxonomy', /产品|categor|tag/i],
    ['article', /文章|article/i],
    ['image/media', /图片|image|media/i],
    ['bulk/import', /批量|bulk|import/i],
  ];
  for (const [label, pattern] of triggerFamilies) {
    if (!pattern.test(prefix)) fail(`${rel} first 250 description characters miss trigger family: ${label}`);
  }
}
function displaySourceClearanceValue(front, field) {
  return front && Object.hasOwn(front, field) ? JSON.stringify(front[field]) : 'missing';
}
function validateSourceCardField(front, rel, field, allowed) {
  const value = fieldValue(front, field);
  if (typeof value !== 'string' || !allowed.has(value)) {
    fail(`source card ${rel} ${field} must be one of ${JSON.stringify([...allowed])}; got ${displaySourceClearanceValue(front, field)}`);
    return false;
  }
  return true;
}
function validateSourcePublicationClearance(markdownPaths, enforce) {
  for (const path of markdownPaths) {
    const rel = relative(libraryRoot, path).split(sep).join('/');
    const front = markdownMetadata.get(path);
    const isReferenceMarkdown = referenceMarkdownPathPattern.test(rel);
    const isReferenceIndex = rel === 'REFERENCES/README.md';
    const isSourceCardPath = sourceCardPathPattern.test(rel);
    const hasRelocatedSourceIdentity = fieldValue(front, 'type') === 'source-note'
      || (front && Object.hasOwn(front, 'publication_review_status'));

    if (isReferenceMarkdown && !isReferenceIndex && !isSourceCardPath) {
      fail(`reference Markdown path must match REFERENCES/SRC-*.md or be REFERENCES/README.md: ${rel}`);
    }
    if (!isSourceCardPath) {
      if (!isReferenceMarkdown && hasRelocatedSourceIdentity) {
        fail(`source card metadata must remain under REFERENCES/SRC-*.md: ${rel}`);
      }
      continue;
    }

    let identityValid = true;
    if (fieldValue(front, 'type') !== 'source-note') {
      fail(`source card ${rel} type must be exactly "source-note"; got ${displaySourceClearanceValue(front, 'type')}`);
      identityValid = false;
    }
    identityValid = validateSourceCardField(front, rel, 'publication_review_status', allowedSourcePublicationReviewStatuses) && identityValid;
    identityValid = validateSourceCardField(front, rel, 'publication_status', allowedSourcePublicationStatuses) && identityValid;
    identityValid = validateSourceCardField(front, rel, 'license_status', allowedSourceLicenseStatuses) && identityValid;
    if (!identityValid) continue;

    const cleared = fieldValue(front, 'publication_review_status') === 'approved'
      && fieldValue(front, 'publication_status') === 'PASS'
      && fieldValue(front, 'license_status') === 'cleared';
    if (cleared) continue;
    const message = `source publication clearance BLOCK for ${rel}: expected publication_review_status="approved", publication_status="PASS", license_status="cleared"; got publication_review_status=${displaySourceClearanceValue(front, 'publication_review_status')}, publication_status=${displaySourceClearanceValue(front, 'publication_status')}, license_status=${displaySourceClearanceValue(front, 'license_status')}`;
    if (enforce) fail(message);
    else warn(`${message}; structure may pass, but prepare and approval/qualification remain blocked`);
  }
}
function normalizedRelativePath(path) {
  return relative(libraryRoot, path).split(sep).join('/');
}
function resolvedLocalMetadataReference(pagePath, value) {
  if (typeof value !== 'string') return null;
  const target = value.trim().split('#')[0].split('?')[0];
  if (!target || isExternal(target)) return null;
  const resolved = resolve(dirname(pagePath), target);
  if (!isInside(libraryRoot, resolved)) return null;
  return normalizedRelativePath(resolved);
}
function validateSourceInventory(markdownPaths) {
  const inventoryPath = join(libraryRoot, sourceInventoryRelativePath);
  if (!existsSync(inventoryPath)) return;

  let inventory;
  try {
    inventory = JSON.parse(read(inventoryPath));
  } catch (error) {
    fail(`${sourceInventoryRelativePath} is not valid JSON: ${error.message}`);
    return;
  }
  if (inventory.schema_version !== 1) fail(`${sourceInventoryRelativePath} schema_version must be 1`);
  if (inventory.inventory_policy !== 'append-only-protected-source-ids-v1') fail(`${sourceInventoryRelativePath} inventory_policy must be append-only-protected-source-ids-v1`);

  const declaredProtectedIds = Array.isArray(inventory.protected_source_ids) ? inventory.protected_source_ids : [];
  if (JSON.stringify(declaredProtectedIds) !== JSON.stringify(protectedSourceIds)) {
    fail(`${sourceInventoryRelativePath} protected_source_ids must exactly preserve the validator baseline ${JSON.stringify(protectedSourceIds)}`);
  }
  const entries = Array.isArray(inventory.entries) ? inventory.entries : [];
  if (!Array.isArray(inventory.entries)) fail(`${sourceInventoryRelativePath} entries must be an array`);

  const sourceBacklinks = new Map();
  for (const pagePath of markdownPaths) {
    const pageRel = normalizedRelativePath(pagePath);
    const front = markdownMetadata.get(pagePath);
    for (const value of fieldArray(front, 'sources', pageRel)) {
      const targetRel = resolvedLocalMetadataReference(pagePath, value);
      if (!targetRel || !sourceCardPathPattern.test(targetRel)) continue;
      if (!sourceBacklinks.has(targetRel)) sourceBacklinks.set(targetRel, new Set());
      sourceBacklinks.get(targetRel).add(pageRel);
    }
  }

  const entriesById = new Map();
  const entriesByCardPath = new Map();
  for (const entry of entries) {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      fail(`${sourceInventoryRelativePath} entries must contain objects`);
      continue;
    }
    const sourceId = entry.source_id;
    const cardPath = entry.card_path;
    if (typeof sourceId !== 'string' || !sourceIdPattern.test(sourceId)) {
      fail(`${sourceInventoryRelativePath} entry source_id is invalid: ${JSON.stringify(sourceId)}`);
      continue;
    }
    if (entriesById.has(sourceId)) fail(`${sourceInventoryRelativePath} contains duplicate source_id ${sourceId}`);
    else entriesById.set(sourceId, entry);
    if (entry.status !== 'active') fail(`${sourceInventoryRelativePath} protected source ${sourceId} status must remain active unless a separately reviewed removal migration changes the validator baseline`);
    const expectedCardPath = `REFERENCES/${sourceId}.md`;
    if (cardPath !== expectedCardPath || !sourceCardPathPattern.test(String(cardPath ?? ''))) {
      fail(`${sourceInventoryRelativePath} source ${sourceId} card_path must be ${expectedCardPath}`);
      continue;
    }
    if (entriesByCardPath.has(cardPath)) fail(`${sourceInventoryRelativePath} contains duplicate card_path ${cardPath}`);
    else entriesByCardPath.set(cardPath, entry);

    const cardAbsolutePath = join(libraryRoot, cardPath);
    if (!existsSync(cardAbsolutePath)) {
      fail(`${sourceInventoryRelativePath} active source card is missing: ${cardPath}`);
      continue;
    }
    const cardFront = markdownMetadata.get(cardAbsolutePath);
    if (fieldValue(cardFront, 'source_id') !== sourceId) {
      fail(`source card ${cardPath} source_id must exactly equal ${sourceId}`);
    }
    for (const field of sourcePublicationClearanceFields) {
      if (!Object.hasOwn(entry, field)) {
        fail(`${sourceInventoryRelativePath} source ${sourceId} must project source card ${field}`);
        continue;
      }
      const cardValue = fieldValue(cardFront, field);
      if (entry[field] !== cardValue) {
        fail(`${sourceInventoryRelativePath} source ${sourceId} ${field} does not match ${cardPath}: expected ${JSON.stringify(cardValue)}, got ${JSON.stringify(entry[field])}`);
      }
    }
    if (typeof entry.card_sha256 !== 'string' || !sha256Pattern.test(entry.card_sha256)) {
      fail(`${sourceInventoryRelativePath} source ${sourceId} card_sha256 must be a lowercase SHA-256 digest`);
    } else {
      const actualDigest = createHash('sha256').update(readBytes(cardAbsolutePath)).digest('hex');
      if (entry.card_sha256 !== actualDigest) fail(`${sourceInventoryRelativePath} source ${sourceId} card_sha256 does not match ${cardPath}`);
    }

    const derivedPages = Array.isArray(entry.derived_pages) ? entry.derived_pages : [];
    if (!Array.isArray(entry.derived_pages) || derivedPages.some((value) => typeof value !== 'string' || !value.trim())) {
      fail(`${sourceInventoryRelativePath} source ${sourceId} derived_pages must be an array of non-empty paths`);
      continue;
    }
    const canonicalDerivedPages = [...new Set(derivedPages)].sort();
    if (JSON.stringify(derivedPages) !== JSON.stringify(canonicalDerivedPages)) {
      fail(`${sourceInventoryRelativePath} source ${sourceId} derived_pages must be unique and sorted`);
    }
    for (const derivedPage of canonicalDerivedPages) {
      if (derivedPage.startsWith('/') || derivedPage.includes('..') || !derivedPage.endsWith('.md')) {
        fail(`${sourceInventoryRelativePath} source ${sourceId} has unsafe derived page path: ${derivedPage}`);
        continue;
      }
      const derivedAbsolutePath = join(libraryRoot, derivedPage);
      if (!existsSync(derivedAbsolutePath)) {
        fail(`${sourceInventoryRelativePath} source ${sourceId} derived page is missing: ${derivedPage}`);
        continue;
      }
      if (!(sourceBacklinks.get(cardPath)?.has(derivedPage))) {
        fail(`derived page ${derivedPage} must bind back to ${cardPath} in front matter sources`);
      }
    }
    const actualBacklinks = [...(sourceBacklinks.get(cardPath) ?? [])].sort();
    if (JSON.stringify(actualBacklinks) !== JSON.stringify(canonicalDerivedPages)) {
      fail(`${sourceInventoryRelativePath} source ${sourceId} derived_pages do not exactly match source-card backlinks: expected ${JSON.stringify(actualBacklinks)}, got ${JSON.stringify(canonicalDerivedPages)}`);
    }
  }

  for (const sourceId of protectedSourceIds) {
    if (!entriesById.has(sourceId)) fail(`${sourceInventoryRelativePath} protected Source ID is missing: ${sourceId}`);
  }
  for (const cardPath of markdownPaths.map(normalizedRelativePath).filter((rel) => sourceCardPathPattern.test(rel))) {
    if (!entriesByCardPath.has(cardPath)) fail(`${sourceInventoryRelativePath} does not register source card ${cardPath}`);
  }
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
function validateStateProjections(scopeRoot, markdownFiles) {
  const markdownByDocument = new Map(markdownFiles
    .filter((file) => extname(file).toLowerCase() === '.md')
    .map((file) => [relative(scopeRoot, file).split(sep).join('/'), file]));
  for (const document of requiredStateProjections.keys()) {
    if (!markdownByDocument.has(document)) fail(`missing required state projection document: ${document}`);
  }

  for (const [document, path] of markdownByDocument) {
    const requiredFields = requiredStateProjections.get(document);
    const front = parseFrontMatter(path, read(path));
    if (!front) {
      if (requiredFields) fail(`${document} required state projection document must have readable front matter`);
      continue;
    }
    const hasSource = Object.hasOwn(front, 'state_source');
    const hasProjection = Object.hasOwn(front, 'state_projection');
    if (!hasSource && !hasProjection && !requiredFields) continue;

    if (!hasSource || !hasProjection) {
      fail(requiredFields
        ? `${document} required state projection must declare both state_source and state_projection`
        : `${document} state projection must declare both state_source and state_projection`);
      continue;
    }

    const sourceReference = fieldValue(front, 'state_source');
    const projectedFields = fieldArray(front, 'state_projection', document);
    if (typeof sourceReference !== 'string' || !sourceReference.trim()) {
      fail(`${document} state_source must be a non-empty relative MANIFEST.md path`);
      continue;
    }
    const portableSource = sourceReference.trim();
    if (portableSource.startsWith('/') || /^file:/i.test(portableSource) || /^[A-Za-z]:[\/]/.test(portableSource) || portableSource.includes('\\')) {
      fail(`${document} state_source must be a portable relative path: ${sourceReference}`);
      continue;
    }
    const sourcePath = resolve(dirname(path), portableSource);
    if (!isInside(scopeRoot, sourcePath)) {
      fail(`${document} state_source escapes validation scope: ${sourceReference}`);
      continue;
    }
    const canonicalSourcePath = resolve(scopeRoot, 'MANIFEST.md');
    if (sourcePath !== canonicalSourcePath) {
      fail(`${document} state_source must resolve to the canonical scope MANIFEST.md: ${sourceReference}`);
      continue;
    }
    if (!existsSync(sourcePath)) {
      fail(`${document} state_source does not exist: ${sourceReference}`);
      continue;
    }
    if (!projectedFields.length) {
      fail(`${document} state_projection must be a non-empty string array`);
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

    const sourceFront = parseFrontMatter(sourcePath, read(sourcePath));
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
      if (!Object.hasOwn(sourceFront, field)) fail(`${document} projects ${field}, but ${sourceReference} does not declare it`);
      else if (!Object.hasOwn(front, field)) fail(`${document} projects ${field}, but the document does not declare it`);
      else if (JSON.stringify(actual) !== JSON.stringify(expected)) fail(`${document} state drift for ${field}: expected ${JSON.stringify(expected)} from ${sourceReference}, got ${JSON.stringify(actual)}`);
    }
  }
}

function publicReleaseClaimText(content) {
  return content
    .replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/[`*_~\[\]{}()<>#|]/g, ' ')
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function findAffirmativeCurrentCandidateClaims(content) {
  const text = publicReleaseClaimText(content);
  const englishSubject = String.raw`(?:the\s+)?(?:current|this)\s+(?:source\s+)?(?:candidate|package|release|build|version|snapshot|artifact|repository|repo|site|deployment)`;
  const englishCopula = String.raw`(?:is|are|was|were|has\s+been|have\s+been|became|remains?)`;
  const englishQualifier = String.raw`(?:(?:now|currently|fully|formally|officially|already|successfully|externally|publicly|declared|considered|certified)\s+){0,4}`;
  const claims = [
    ['Stable', String.raw`stable`],
    ['Published', String.raw`published`],
    ['production-ready', String.raw`production[-\s]+ready`],
    ['approved', String.raw`approved`],
    ['deployed', String.raw`deployed`],
    ['live SEO accepted', String.raw`(?:live\s+seo\s+(?:is\s+)?accepted|accepted\s+for\s+live\s+seo)`],
  ];
  const matches = [];
  for (const [claim, term] of claims) {
    const patterns = [
      new RegExp(String.raw`\b${englishSubject}\s+${englishCopula}\s+${englishQualifier}\b${term}\b`, 'giu'),
      new RegExp(String.raw`\b(?:current|this)\s+(?:candidate|package|release|build|deployment)\s+status\s*[:=\-–—]\s*${term}\b`, 'giu'),
    ];
    for (const pattern of patterns) {
      for (const match of text.matchAll(pattern)) matches.push({ claim, excerpt: match[0] });
    }
  }

  const chineseClaims = [
    ['Stable', /(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点))\s*(?:现为|为|是|已(?:经)?(?:成为|达到))\s*(?:Stable|稳定版|稳定状态)/giu],
    ['Published', /(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点))\s*(?:现为|为|是)\s*Published|(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点))\s*已(?:经)?(?:正式)?发布/giu],
    ['production-ready', /(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点))\s*(?:现为|为|是|已(?:经)?(?:成为|达到))\s*(?:production[-\s]+ready|生产就绪|可用于生产)/giu],
    ['approved', /(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点))\s*(?:现为|为|是)\s*approved|(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点))\s*已(?:经)?(?:正式)?(?:获得)?批准/giu],
    ['deployed', /(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点))\s*(?:现为|为|是)\s*deployed|(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点))\s*已(?:经)?(?:正式)?(?:部署|上线)/giu],
    ['live SEO accepted', /(?:当前(?:源码|工作树)?候选|本(?:候选|包|版本|发布|构建|站点)).{0,24}?(?:live\s+seo|正式\s*seo).{0,12}?(?:已验收|已接受|通过验收)/giu],
  ];
  for (const [claim, pattern] of chineseClaims) {
    for (const match of text.matchAll(pattern)) matches.push({ claim, excerpt: match[0] });
  }

  return [...new Map(matches.map((match) => [`${match.claim}\u0000${match.excerpt.toLowerCase()}`, match])).values()];
}

function currentCandidateReleaseClaimBlockers({ manifestStatus, currentCandidateIdentity, currentCandidateVersion, licenseStatus, approvalStatus }) {
  const blockers = [];
  if (!['Ready', 'Published'].includes(manifestStatus)) blockers.push(`release_status=${manifestStatus ?? 'missing'}`);
  if (currentCandidateIdentity === 'unassigned') blockers.push('current_candidate_identity=unassigned');
  if (currentCandidateVersion === null) blockers.push('current_candidate_version=unassigned');
  if (licenseStatus !== 'cleared') blockers.push(`license_status=${licenseStatus ?? 'missing'}`);
  if (approvalStatus !== 'approved') blockers.push(`approval_status=${approvalStatus ?? 'missing'}`);
  return blockers;
}

function validatePublicReleaseStateClaims(scopeRoot, blockers) {
  if (!blockers.length) return;
  const rootPublicMarkdown = readdirSync(scopeRoot, { withFileTypes: true })
    .filter((entry) => entry.isFile() && extname(entry.name).toLowerCase() === '.md')
    .filter((entry) => fieldValue(parseFrontMatter(join(scopeRoot, entry.name), read(join(scopeRoot, entry.name))), 'visibility') === 'public')
    .map((entry) => entry.name);
  const documents = [...new Set([...minimumPublicReleaseClaimDocuments, ...rootPublicMarkdown])].sort();
  for (const document of documents) {
    const path = join(scopeRoot, document);
    if (!existsSync(path)) continue;
    for (const { claim, excerpt } of findAffirmativeCurrentCandidateClaims(read(path))) {
      fail(`${releaseStateContradictionCode}: ${document} current-candidate claim=${claim} conflicts with ${blockers.join(', ')}; excerpt=${JSON.stringify(excerpt)}`);
    }
  }
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
const governanceFixtureFastMode = shouldUseGovernanceFixtureFastMode({
  libraryRoot,
  tempRoot: tmpdir(),
  env: process.env,
  releaseMode,
  prepareMode,
});
const workspaceSync = spawnSync(process.execPath, [join(libraryRoot, 'scripts/sync-workspace-template.mjs'), '--check'], { cwd: libraryRoot, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
if (workspaceSync.status !== 0) {
  fail('WORKSPACE-TEMPLATE generated content projections are stale or not self-consistent');
  if (workspaceSync.stderr?.trim()) console.error(workspaceSync.stderr.trim());
}
if (!governanceFixtureFastMode) {
  const workspaceSyncSuite = spawnSync(process.execPath, ['--test', join(libraryRoot, 'scripts/sync-workspace-template.test.mjs')], { cwd: libraryRoot, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
  if (workspaceSyncSuite.status !== 0) {
    fail('WORKSPACE-TEMPLATE adversarial regression suite failed');
    if (workspaceSyncSuite.stdout?.trim()) console.error(workspaceSyncSuite.stdout.trim());
    if (workspaceSyncSuite.stderr?.trim()) console.error(workspaceSyncSuite.stderr.trim());
  }
  const operationPlanSuite = spawnSync(process.execPath, ['--test', join(libraryRoot, 'scripts/content-operation-plan.test.mjs')], { cwd: libraryRoot, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
  if (operationPlanSuite.status !== 0) {
    fail('source-driven CMS content operation plan negative regression suite failed');
    if (operationPlanSuite.stdout?.trim()) console.error(operationPlanSuite.stdout.trim());
    if (operationPlanSuite.stderr?.trim()) console.error(operationPlanSuite.stderr.trim());
  }
  const articleSuite = spawnSync(process.execPath, ['--test', join(libraryRoot, 'scripts/article-package.test.mjs')], { cwd: libraryRoot, encoding: 'utf8', timeout: ARTICLE_REGRESSION_TIMEOUT_MS });
  if (articleSuite.status !== 0) {
    fail('B2B article package negative regression suite failed');
    if (articleSuite.stdout?.trim()) console.error(articleSuite.stdout.trim());
    if (articleSuite.stderr?.trim()) console.error(articleSuite.stderr.trim());
  }
  const articlePackage = spawnSync(process.execPath, [
    join(libraryRoot, 'scripts/validate-article-package.mjs'),
    '--brief', join(libraryRoot, 'EXAMPLES/fluxpedal-motors/b2b-seo-article-brief.md'),
    '--draft', join(libraryRoot, 'EXAMPLES/fluxpedal-motors/b2b-seo-article-draft.md'),
    '--review', join(libraryRoot, 'EXAMPLES/fluxpedal-motors/b2b-seo-article-review.md'),
    '--publish', join(libraryRoot, 'EXAMPLES/fluxpedal-motors/b2b-seo-publish-record.md'),
  ], { cwd: libraryRoot, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
  if (articlePackage.status !== 0) {
    fail('bundled B2B article package contract validation failed');
    if (articlePackage.stdout?.trim()) console.error(articlePackage.stdout.trim());
    if (articlePackage.stderr?.trim()) console.error(articlePackage.stderr.trim());
  }
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
validateInstallableSkillMetadata();
validateStateProjections(libraryRoot, markdownFiles);
validateSourcePublicationClearance(markdownFiles, releaseMode || prepareMode);
validateSourceInventory(markdownFiles);

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
  for (const issue of scanPublishableContent(content, relative(libraryRoot, path))) fail(`content safety ${issue.code}: ${relative(libraryRoot, path)}`);
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
const manifestFront = markdownMetadata.get(join(libraryRoot, 'MANIFEST.md'))
  ?? parseFrontMatter(join(libraryRoot, 'MANIFEST.md'), manifestText)
  ?? {};
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
const historicalPublishedVersion = fieldValue(manifestFront, 'historical_published_version');
const historicalPublishedTag = fieldValue(manifestFront, 'historical_published_tag');
const currentCandidateIdentity = fieldValue(manifestFront, 'current_candidate_identity');
const currentCandidateSnapshot = fieldValue(manifestFront, 'current_candidate_snapshot');
const currentCandidateVersionDeclared = Object.hasOwn(manifestFront, 'current_candidate_version');
const currentCandidateVersion = fieldValue(manifestFront, 'current_candidate_version');
const tagNamespace = fieldValue(manifestFront, 'tag_namespace');
const tagPrefix = fieldValue(manifestFront, 'tag_prefix');
const skillEntrypoint = fieldValue(manifestFront, 'skill_entrypoint');
const skillStatus = fieldValue(manifestFront, 'skill_status');
const deliveryModes = fieldArray(manifestFront, 'delivery_modes', 'MANIFEST.md');
const includePatterns = fieldArray(manifestFront, 'include', 'MANIFEST.md');
const excludePatterns = fieldArray(manifestFront, 'exclude', 'MANIFEST.md');
if (!version) fail('VERSION.md has no machine-readable legacy Version field');
const safeVersionPattern = /^[0-9A-Za-z][0-9A-Za-z._-]*$/;
if (typeof historicalPublishedVersion !== 'string' || !safeVersionPattern.test(historicalPublishedVersion)) fail(`MANIFEST.md historical_published_version is missing or unsafe: ${historicalPublishedVersion ?? 'missing'}`);
if (historicalPublishedTag !== `v${historicalPublishedVersion}`) fail(`historical_published_tag must be v${historicalPublishedVersion}: ${historicalPublishedTag ?? 'missing'}`);
if (version !== historicalPublishedVersion) fail(`VERSION.md legacy Version must equal historical_published_version: ${version ?? 'missing'} != ${historicalPublishedVersion ?? 'missing'}`);
if (previewVersion !== historicalPublishedVersion) fail(`preview_version is a historical compatibility projection and must equal historical_published_version: ${previewVersion ?? 'missing'} != ${historicalPublishedVersion ?? 'missing'}`);
if (previewTag !== historicalPublishedTag) fail(`preview_tag is a historical compatibility projection and must equal historical_published_tag: ${previewTag ?? 'missing'} != ${historicalPublishedTag ?? 'missing'}`);
if (typeof currentCandidateIdentity !== 'string' || !currentCandidateIdentity.trim()) fail(`MANIFEST.md current_candidate_identity is missing or invalid: ${currentCandidateIdentity ?? 'missing'}`);
if (typeof currentCandidateSnapshot !== 'string' || !currentCandidateSnapshot.trim()) fail(`MANIFEST.md current_candidate_snapshot is missing or invalid: ${currentCandidateSnapshot ?? 'missing'}`);
if (!currentCandidateVersionDeclared) fail('MANIFEST.md current_candidate_version must be explicitly declared as null or a safe new version');
if (currentCandidateVersion !== null && (typeof currentCandidateVersion !== 'string' || !safeVersionPattern.test(currentCandidateVersion))) fail(`MANIFEST.md current_candidate_version is unsafe: ${currentCandidateVersion}`);
if (currentCandidateIdentity === 'unassigned' && currentCandidateVersion !== null) fail('current_candidate_identity unassigned requires current_candidate_version null');
if (currentCandidateIdentity !== 'unassigned' && currentCandidateVersion === null) fail('assigned current_candidate_identity requires a non-null current_candidate_version');
if (currentCandidateVersion !== null && currentCandidateVersion === historicalPublishedVersion) fail('current_candidate_version must not collide with immutable historical_published_version');
if (currentCandidateVersion !== null && `v${currentCandidateVersion}` === historicalPublishedTag) fail('current candidate tag must not collide with immutable historical_published_tag');
const hasSourceRegistry = existsSync(resolve(libraryRoot, '../README.md')) && existsSync(resolve(libraryRoot, '../registry.json'));
if (hasSourceRegistry && packageId !== basename(libraryRoot)) fail(`MANIFEST.md package_id must equal directory name: ${packageId}`);
if (!allowedMaturity.has(maturityStatus)) fail(`MANIFEST.md maturity_status is invalid: ${maturityStatus ?? 'missing'}`);
if (!allowedVerification.has(verificationStatus)) fail(`MANIFEST.md verification_status is invalid: ${verificationStatus ?? 'missing'}`);
if (!allowedRelease.has(manifestStatus)) fail(`MANIFEST.md release_status is invalid: ${manifestStatus ?? 'missing'}`);
if (!allowedLicense.has(licenseStatus)) fail(`MANIFEST.md license_status is invalid: ${licenseStatus ?? 'missing'}`);
if (approvalRequired !== true) fail(`MANIFEST.md approval_required must be boolean true: ${approvalRequired ?? 'missing'}`);
if (!allowedApproval.has(approvalStatus)) fail(`MANIFEST.md approval_status is invalid: ${approvalStatus ?? 'missing'}`);
validatePublicReleaseStateClaims(libraryRoot, currentCandidateReleaseClaimBlockers({
  manifestStatus,
  currentCandidateIdentity,
  currentCandidateVersion,
  licenseStatus,
  approvalStatus,
}));
if (manifestStatus === 'Preview') {
  if (repositoryStatus !== 'public-preview') fail(`Preview requires repository_status public-preview: ${repositoryStatus ?? 'missing'}`);
  if (!['Ready', 'Published'].includes(previewPublicationStatus)) fail(`Preview publication status is invalid: ${previewPublicationStatus ?? 'missing'}`);
  if (licenseStatus !== 'cleared') fail('Preview requires license_status cleared');
}
const expectedTagNamespace = `sub-library/${packageId}`;
if (tagNamespace !== expectedTagNamespace) fail(`MANIFEST.md tag_namespace must be ${expectedTagNamespace}: ${tagNamespace ?? 'missing'}`);
if (tagPrefix !== `${expectedTagNamespace}/v`) fail(`MANIFEST.md tag_prefix must be ${expectedTagNamespace}/v: ${tagPrefix ?? 'missing'}`);
if (releaseScope !== 'standalone-sub-library') fail(`MANIFEST.md release_scope is not standalone-sub-library: ${releaseScope ?? 'missing'}`);
if (!allowedDependency.has(dependencyMode)) fail(`MANIFEST.md dependency_mode is invalid: ${dependencyMode ?? 'missing'}`);
if (dependencyMode !== 'declared-external-runtime') fail('website-content-ops must declare dependency_mode=declared-external-runtime because customer runtime isolation is provided by agency-operations');
if (!durableRoots.length || durableRoots.some((item) => item.startsWith('/') || item.includes('..') || item.includes('\\'))) fail(`MANIFEST.md durable_roots are invalid: ${JSON.stringify(durableRoots)}`);
if (packageKind !== 'standalone-sub-library' || !allowedPackageKinds.has(packageKind)) fail(`MANIFEST.md package_kind is invalid: ${packageKind ?? 'missing'}`);
if (runtimeContract !== 'RUNTIME-CONTRACT.json') fail(`MANIFEST.md runtime_contract must be RUNTIME-CONTRACT.json: ${runtimeContract ?? 'missing'}`);
if (sourcePackageOnly !== true) fail('MANIFEST.md source_package_only must be boolean true');
if (includedInMother !== 'source-only') fail(`MANIFEST.md included_in_mother must be source-only: ${includedInMother ?? 'missing'}`);
if (!deliveryModes.length || deliveryModes.some((mode) => !allowedDeliveryModes.has(mode)) || new Set(deliveryModes).size !== deliveryModes.length) fail(`MANIFEST.md delivery_modes are invalid: ${JSON.stringify(deliveryModes)}`);
if (!includePatterns.length) fail('MANIFEST.md include allowlist must not be empty');
for (const requiredRuntimeExclude of ['customer-runtime/**', 'secrets/**', 'browser-profiles/**']) {
  if (!excludePatterns.includes(requiredRuntimeExclude)) fail(`MANIFEST.md exclude must contain private runtime boundary ${requiredRuntimeExclude}`);
}
const gitignoreLines = new Set(read(join(libraryRoot, '.gitignore')).split(/\r?\n/).map((line) => line.trim()).filter(Boolean));
for (const requiredRuntimeIgnore of ['customer-runtime/', 'secrets/', 'browser-profiles/']) {
  if (!gitignoreLines.has(requiredRuntimeIgnore)) fail(`.gitignore must contain private runtime boundary ${requiredRuntimeIgnore}`);
}
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
    const dependency = runtime.external_runtime_dependency;
    if (!dependency || dependency.package_id !== 'agency-operations' || dependency.dependency_mode !== 'required') fail('RUNTIME-CONTRACT.json must bind the required agency-operations external runtime dependency');
    if (JSON.stringify(dependency?.required_scope_keys) !== JSON.stringify(['client_id', 'company_id', 'task_id'])) fail('RUNTIME-CONTRACT.json agency runtime dependency must require exact client_id/company_id/task_id scope keys');
    if (dependency?.fail_closed_without_active_scope !== true || dependency?.runtime_upgrade_must_not_overwrite_existing_data !== true) fail('RUNTIME-CONTRACT.json agency runtime dependency must fail closed without scope and forbid runtime overwrite during upgrades');
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
  for (const [dependency, expected] of Object.entries({ acorn: '8.15.0', ajv: '8.20.0', sharp: '0.35.3' })) {
    if (packageJson.dependencies?.[dependency] !== expected) fail(`AllinCMS ${dependency} runtime dependency must be exactly pinned to ${expected}`);
    if (packageJson.devDependencies?.[dependency]) fail(`AllinCMS ${dependency} is used by packaged runtime code and must not be dev-only`);
  }
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
  const packed = spawnSync('npm', ['pack', '--dry-run', '--json'], { cwd: adapterRoot, encoding: 'utf8', timeout: GOVERNANCE_COMMAND_TIMEOUT_MS });
  if (packed.status !== 0) {
    fail(`AllinCMS npm package dry-run failed: ${(packed.stderr || packed.stdout || '').trim()}`);
    return;
  }
  let filesInPack;
  try { filesInPack = JSON.parse(packed.stdout)?.[0]?.files?.map((item) => item.path) ?? []; }
  catch (error) { fail(`AllinCMS npm pack dry-run did not return valid JSON: ${error.message}`); return; }
  if (!filesInPack.length) fail('AllinCMS npm pack dry-run produced no inspectable files');
  const allowedPackagedRedactedContracts = new Set([
    'media-operations-contract.redacted.json',
    'observed-contract.redacted.json',
  ]);
  for (const required of allowedPackagedRedactedContracts) {
    if (!filesInPack.includes(required)) fail(`AllinCMS npm package is missing required redacted contract: ${required}`);
  }
  const packageFileSet = new Set(filesInPack);
  const interfaceRegistryPath = join(adapterRoot, 'interface-registry.json');
  if (!packageFileSet.has('interface-registry.json')) {
    fail('AllinCMS npm package is missing interface-registry.json');
  } else {
    try {
      const interfaceRegistry = JSON.parse(read(interfaceRegistryPath));
      if (interfaceRegistry.registry_version !== 2) fail(`AllinCMS interface Registry must use registry_version 2: ${interfaceRegistry.registry_version ?? 'missing'}`);
      for (const item of interfaceRegistry.interfaces || []) {
        for (const ref of item.contract_refs || []) {
          if (item.runtime_availability === 'packaged' && ref.availability !== 'packaged') {
            fail(`AllinCMS packaged interface contract_ref must declare availability=packaged: ${item.interface_id ?? 'unknown'} -> ${ref.path ?? 'missing'}`);
          }
        }
        for (const ref of item.test_refs || []) {
          if (ref.availability !== 'source_only') {
            fail(`AllinCMS Registry test_ref must declare availability=source_only: ${item.interface_id ?? 'unknown'} -> ${ref.path ?? 'missing'}`);
          }
        }
        for (const ref of [...(item.contract_refs || []), ...(item.test_refs || []), ...(item.evidence?.refs || [])]) {
          if (!['packaged', 'source_only'].includes(ref.availability)) {
            fail(`AllinCMS Registry reference has invalid availability: ${item.interface_id ?? 'unknown'} -> ${ref.path ?? 'missing'}`);
          } else if (ref.availability === 'packaged' && !packageFileSet.has(ref.path)) {
            fail(`AllinCMS npm package is missing Registry packaged reference: ${item.interface_id ?? 'unknown'} -> ${ref.path ?? 'missing'}`);
          } else if (ref.availability === 'source_only' && packageFileSet.has(ref.path)) {
            fail(`AllinCMS npm package unexpectedly contains Registry source_only reference: ${item.interface_id ?? 'unknown'} -> ${ref.path ?? 'missing'}`);
          }
        }
      }
    } catch (error) {
      fail(`AllinCMS interface-registry.json is invalid JSON: ${error.message}`);
    }
  }
  for (const path of filesInPack) {
    const forbiddenRedacted = /\.redacted\.(?:md|json)$/.test(path) && !allowedPackagedRedactedContracts.has(path);
    if (path.startsWith('/') || path.includes('..') || /(^|\/)(node_modules|fixtures|coverage)(\/|$)/.test(path)
        || /\.test\.mjs$/.test(path) || forbiddenRedacted) {
      fail(`AllinCMS npm package contains forbidden file: ${path}`);
    }
  }
  for (const markdownPath of filesInPack.filter((path) => path.endsWith('.md'))) {
    const markdown = read(join(adapterRoot, markdownPath));
    for (const match of markdown.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
      const target = match[1].trim();
      if (!target || target.startsWith('#') || /^[a-z][a-z0-9+.-]*:/i.test(target)) continue;
      let pathOnly = target.split('#', 1)[0].split('?', 1)[0];
      try { pathOnly = decodeURIComponent(pathOnly); }
      catch { fail(`AllinCMS npm package Markdown link has invalid encoding: ${markdownPath} -> ${target}`); continue; }
      const resolvedTarget = relative(adapterRoot, resolve(adapterRoot, dirname(markdownPath), pathOnly)).split(sep).join('/');
      if (resolvedTarget.startsWith('../') || resolvedTarget === '..' || !packageFileSet.has(resolvedTarget)) {
        fail(`AllinCMS npm package Markdown link target is not packaged: ${markdownPath} -> ${target}`);
      }
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
    if (entry.version !== historicalPublishedVersion) fail(`sub-library registry legacy version ${entry.version} does not match historical_published_version ${historicalPublishedVersion}`);
    if (entry.version_semantics !== 'historical-published-only') fail(`sub-library registry version_semantics ${entry.version_semantics ?? 'missing'} must be historical-published-only`);
    if (entry.release_status !== manifestStatus) fail(`sub-library registry release_status ${entry.release_status} does not match ${manifestStatus}`);
    const expected = { package_id: packageId, historical_published_version: historicalPublishedVersion, historical_published_tag: historicalPublishedTag, current_candidate_identity: currentCandidateIdentity, current_candidate_snapshot: currentCandidateSnapshot, current_candidate_version: currentCandidateVersion, maturity_status: maturityStatus, verification_status: verificationStatus, release_scope: releaseScope, runtime_contract: runtimeContract, dependency_mode: dependencyMode, durable_roots: durableRoots, source_package_only: true, package_kind: packageKind, skill_entrypoint: skillEntrypoint && skillEntrypoint !== 'null' ? skillEntrypoint : null, skill_status: skillStatus ?? null, canonical_entry: 'README.md', included_in_mother: includedInMother, license_status: licenseStatus, approval_required: approvalRequired === true, approval_status: approvalStatus, tag_namespace: tagNamespace, tag_prefix: tagPrefix };
    for (const [field, value] of Object.entries(expected)) {
      const matches = Array.isArray(value) ? JSON.stringify(entry[field]) === JSON.stringify(value) : entry[field] === value;
      if (!matches) fail(`sub-library registry ${field} ${JSON.stringify(entry[field])} does not match ${JSON.stringify(value)}`);
    }
    if (!Array.isArray(entry.delivery_modes) || JSON.stringify(entry.delivery_modes) !== JSON.stringify(deliveryModes)) fail('sub-library registry delivery_modes does not match manifest');
    if (!registry.split('\n').some((line) => line.includes(`](${basename(libraryRoot)}/README.md)`) && line.includes(`historical \`${historicalPublishedVersion}\``) && line.includes(`current \`${currentCandidateIdentity}\``) && line.includes(manifestStatus))) fail('sub-libraries/README.md canonical row is stale or conflates historical/current identity');
  }
} else {
  warn('standalone artifact has no mother-library registry; source-level registry check skipped as expected');
}
if ((releaseMode || prepareMode) && !['Ready', 'Published'].includes(manifestStatus)) {
  fail('release mode requires MANIFEST.md release_status Ready or Published');
}
if (releaseMode || prepareMode) {
  if (currentCandidateIdentity === 'unassigned' || currentCandidateVersion === null) fail('release preparation requires an assigned current candidate identity and non-null current_candidate_version');
  if (currentCandidateSnapshot === 'dirty-working-tree') fail('release preparation cannot use current_candidate_snapshot dirty-working-tree');
  if (currentCandidateVersion === historicalPublishedVersion || `v${currentCandidateVersion}` === historicalPublishedTag) fail('release preparation current candidate identity collides with immutable historical release identity');
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
  try { artifact = JSON.parse(read(manifestPath)); } catch { fail('MANIFEST.json is not valid JSON'); return; }
  if (!Array.isArray(artifact.files) || !artifact.files.length) { fail('MANIFEST.json files list is missing or empty'); return; }
  const listed = new Set(artifact.files);
  for (const file of listed) {
    if (file.startsWith('/') || file.includes('..') || !existsSync(join(rootPath, file))) fail(`artifact manifest lists missing or unsafe file: ${file}`);
  }
  const actual = new Set(walk(rootPath).map((file) => relative(rootPath, file)));
  for (const file of actual) if (!['MANIFEST.json', 'SHA256SUMS'].includes(file) && !listed.has(file)) fail(`artifact contains unlisted file: ${file}`);
  const sums = read(sumsPath).trim().split('\n').filter(Boolean);
  const sumMap = new Map();
  for (const line of sums) { const match = line.match(/^([a-f0-9]{64})  (.+)$/); if (!match) { fail(`invalid SHA256SUMS line: ${line}`); continue; } sumMap.set(match[2], match[1]); }
  for (const file of [...listed, 'MANIFEST.json']) {
    const expected = sumMap.get(file);
    const actualHash = createHash('sha256').update(readBytes(join(rootPath, file))).digest('hex');
    if (expected !== actualHash) fail(`artifact checksum mismatch: ${file}`);
  }
}
verifyArtifact(libraryRoot);

console.log(`Sub-library: ${relative(resolve(libraryRoot, '..'), libraryRoot)}`);
console.log(`Historical published version: ${historicalPublishedVersion ?? 'unknown'}`);
console.log(`Current candidate version: ${currentCandidateVersion ?? 'unassigned'}`);
console.log(`Mode: ${releaseMode ? 'release' : prepareMode ? 'prepare' : 'structure'}`);
for (const item of warnings) console.log(`WARN: ${item}`);
for (const item of failures) console.log(`FAIL: ${item}`);
if (failures.length) {
  console.error(`\nBLOCK: ${failures.length} check(s) failed.`);
  process.exitCode = 1;
} else {
  console.log('\nSTRUCTURE_PASS: static sub-library checks passed; this is not release approval.');
}
