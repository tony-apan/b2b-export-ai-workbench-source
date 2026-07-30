#!/usr/bin/env node
/**
 * Validate raw -> source note -> five durable roles -> evidence/review/
 * verification/writeback without treating metadata strings as proof.
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { basename, dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { parseFrontMatterText, stringField, stringListField } from './lib/markdown-front-matter.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const releaseMode = process.argv.includes('--release');
const argValue = (flag) => {
  const index = process.argv.indexOf(flag);
  return index >= 0 ? process.argv[index + 1]?.trim() ?? '' : '';
};
const courseApprovalArg = argValue('--course-approval') || process.env.COURSE_REVIEW_APPROVAL_PATH?.trim() || '';
const courseApprovalSignatureArg = argValue('--course-approval-signature') || process.env.COURSE_REVIEW_APPROVAL_SIGNATURE_PATH?.trim() || '';
const sourceCommitArg = argValue('--source-commit') || process.env.COURSE_REVIEW_SOURCE_COMMIT?.trim() || '';
const failures = [];
const warnings = [];
const read = (path) => readFileSync(path, 'utf8');
const rel = (path) => relative(root, path).replaceAll('\\', '/');
const normalized = (value = '') => typeof value === 'string' ? value.trim().toLowerCase().replace(/[_\s]+/gu, '-') : '';
const sha256Buffer = (value) => createHash('sha256').update(value).digest('hex');
const sha256 = (path) => sha256Buffer(readFileSync(path));

const RAW_LIFECYCLE = new Set(['inbox', 'classified', 'registered', 'extracted', 'linked', 'ingested', 'derived', 'verified', 'archived']);
const RAW_STATES_REQUIRING_DERIVATION = new Set(['ingested', 'derived', 'verified', 'archived']);
const PUBLIC_RAW_CONSENT = new Set([
  'original-synthetic-fixture',
  'synthetic-fixture-publication-approved',
  'explicit-public-consent',
  'licensed-for-publication',
  'public-domain',
]);
const DERIVED_ROLES = new Map([
  ['concept', 'doc_id'],
  ['playbook', 'doc_id'],
  ['course-module', 'doc_id'],
  ['verification-record', 'verification_id'],
  ['writeback-record', 'writeback_id'],
]);
const STRUCTURE_STATES = new Set(['pending', 'verified', 'failed']);
const EXERCISE_STATES = new Set(['pending', 'verified', 'failed']);
const EFFECTIVENESS_STATES = new Set(['unverified', 'real-world-effectiveness-verified', 'failed']);
const MANIFEST_ARTIFACT_ORDER = new Map([
  ['raw', 0],
  ['source-note', 1],
  ['concept', 2],
  ['playbook', 3],
  ['course', 4],
  ['exercise', 5],
  ['review', 6],
  ['verification', 7],
  ['writeback', 8],
]);

function frontMatter(path, bucket = failures) {
  const content = read(path);
  let parsed;
  try {
    parsed = parseFrontMatterText(content, { rejectDuplicates: true });
  } catch (error) {
    bucket.push(`${rel(path)}: invalid YAML front matter: ${error.message}`);
    return null;
  }
  if (!parsed) return null;
  const raw = (field) => parsed.data.get(field);
  const value = (field) => stringField(parsed, field);
  const arrayResult = (field) => stringListField(parsed, field);
  const array = (field) => {
    const result = arrayResult(field);
    return result.valid ? result.values : [];
  };
  return { content, parsed, raw, value, array, arrayResult };
}

function hasField(meta, field) {
  return Boolean(meta?.parsed.data.has(field));
}

function requireString(meta, path, field, bucket = failures) {
  if (!hasField(meta, field)) {
    bucket.push(`${path}: missing required front matter field ${field}`);
    return '';
  }
  const value = meta.raw(field);
  if (typeof value !== 'string' || !value.trim()) {
    bucket.push(`${path}: front matter field ${field} must be a non-empty string`);
    return '';
  }
  return value.trim();
}

function requireBoolean(meta, path, field, bucket = failures) {
  if (!hasField(meta, field)) {
    bucket.push(`${path}: missing required front matter field ${field}`);
    return null;
  }
  const value = meta.raw(field);
  if (typeof value !== 'boolean') {
    bucket.push(`${path}: front matter field ${field} must be a YAML boolean`);
    return null;
  }
  return value;
}

function requireNumber(meta, path, field, bucket = warnings, options = {}) {
  if (!hasField(meta, field)) {
    bucket.push(`${path}: missing required front matter field ${field}`);
    return null;
  }
  const value = meta.raw(field);
  if (typeof value !== 'number' || !Number.isFinite(value) || (options.integer && !Number.isInteger(value))) {
    bucket.push(`${path}: front matter field ${field} must be ${options.integer ? 'an integer' : 'a number'}`);
    return null;
  }
  return value;
}

function requireStringArray(meta, path, field, bucket = failures, options = {}) {
  const result = meta?.arrayResult(field) ?? { valid: false, values: [], reason: 'missing field' };
  if (!result.valid) {
    bucket.push(`${path}: ${field} ${result.reason}`);
    return [];
  }
  if (options.nonEmpty && !result.values.length) bucket.push(`${path}: ${field} must contain at least one value`);
  return result.values;
}

function markdownFiles(dir) {
  if (!existsSync(dir)) return [];
  const files = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) files.push(...markdownFiles(path));
    else if (entry.isFile() && ['.md', '.mdx'].includes(extname(entry.name).toLowerCase())) files.push(path);
  }
  return files;
}

function isIndexOrTemplate(path, meta) {
  const name = basename(path).toLowerCase();
  const type = normalized(meta?.value('type'));
  return name === 'index.md'
    || name === 'index.mdx'
    || /(^|[-_.])template([-.]|$)/u.test(name)
    || type === 'index'
    || type === 'raw-guide'
    || type === 'template'
    || type.endsWith('-template');
}

function isSyntheticKind(sourceKind) {
  return /(^|-)(synthetic|virtual|fixture)(-|$)/u.test(normalized(sourceKind));
}

function claimsRealWorldVerification(status) {
  return new Set(['verified', 'human-verified', 'real-world-verified', 'real-world-effectiveness-verified', 'production-verified', 'field-verified', 'customer-verified']).has(normalized(status));
}

function hasClearConsent(consentStatus) {
  const status = normalized(consentStatus);
  if (!status || /(unknown|unclear|pending|review-required|not-authorized|unauthorized|not-approved|denied|revoked)/u.test(status)) return false;
  return /(^|-)(authorized|authorised|approved|granted|licensed|consented)(-|$)/u.test(status);
}

function resolveSafe(fromFile, target, label, bucket = failures) {
  if (!target) return null;
  if (typeof target !== 'string') {
    bucket.push(`${label}: path must be a string`);
    return null;
  }
  const resolved = resolve(dirname(fromFile), target);
  if (resolved !== root && !resolved.startsWith(`${root}${sep}`)) {
    bucket.push(`${label}: path escapes repository: ${target}`);
    return null;
  }
  return resolved;
}

function unique(values, label, bucket = failures) {
  const duplicates = values.filter((value, index) => values.indexOf(value) !== index);
  if (duplicates.length) bucket.push(`${label}: duplicate values are not allowed: ${[...new Set(duplicates)].join(', ')}`);
  return duplicates.length === 0;
}

function samePath(left, right) {
  return Boolean(left && right && resolve(left) === resolve(right));
}

function sortedSet(values) {
  return [...new Set(values)].sort((left, right) => left.localeCompare(right, 'en'));
}

function sameStringSet(left, right) {
  return JSON.stringify(sortedSet(left)) === JSON.stringify(sortedSet(right));
}

function documentBody(meta) {
  const normalizedContent = meta.content.replaceAll('\r\n', '\n').replaceAll('\r', '\n');
  const lines = normalizedContent.split('\n');
  if (lines[0]?.trim() !== '---') return '';
  const end = lines.findIndex((line, index) => index > 0 && /^---[ \t]*$/u.test(line));
  return end >= 0 ? lines.slice(end + 1).join('\n').trim() : '';
}

function meaningfulSection(meta, heading, label, bucket = warnings) {
  const body = documentBody(meta);
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&');
  const headingMatch = new RegExp(`^##\\s+${escaped}\\s*$`, 'mi').exec(body);
  const remainder = headingMatch ? body.slice(headingMatch.index + headingMatch[0].length) : '';
  const nextHeading = remainder.search(/^##\s+/mu);
  const section = nextHeading >= 0 ? remainder.slice(0, nextHeading) : remainder;
  const text = section.replace(/<!--[\s\S]*?-->/gu, '').replace(/[|#>*_`\-:\\]/gu, ' ').replace(/\s+/gu, ' ').trim();
  if (!headingMatch || text.length < 20 || /(^|\b)(todo|tbd|placeholder|not provided)(\b|$)|待补|待填写|示例内容/iu.test(text)) {
    bucket.push(`${label}: section ## ${heading} must contain at least 20 characters of concrete, non-placeholder evidence`);
    return false;
  }
  return true;
}

const SENSITIVE_CONTENT_PATTERNS = [
  ['email address', /\b[A-Z0-9._%+-]+@(?!example\.(?:com|org|net)\b)[A-Z0-9.-]+\.[A-Z]{2,}\b/iu],
  ['phone number', /(?:\+?86[-\s]?)?(?:1[3-9]\d{9}|0\d{2,3}[-\s]?\d{7,8})/u],
  ['customer/contact/internal-note label', /(?:^|\n)\s*(?:客户名|客户名称|联系人|联系电话|手机号码|邮箱地址|内部备注|customer\s*name|contact\s*person|internal\s*note)\s*[:：]/iu],
  ['credential-like token', /(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*["']?[A-Za-z0-9_\-]{12,}/iu],
  ['local absolute path', /(?:\/Users\/[^\s`"']+|[A-Za-z]:\\Users\\[^\s`"']+)/u],
];

function scanPublicSyntheticContent(meta, path) {
  const fixtureId = requireString(meta, path, 'fixture_id');
  const fixtureProvenance = requireString(meta, path, 'fixture_provenance');
  if (fixtureId && !/^FIX-[A-Z0-9][A-Z0-9-]{5,}$/u.test(fixtureId)) failures.push(`${path}: fixture_id must use FIX- plus a stable uppercase identifier`);
  if (normalized(fixtureProvenance) !== 'authored-for-governance-testing') failures.push(`${path}: fixture_provenance must be authored-for-governance-testing`);
  for (const [label, pattern] of SENSITIVE_CONTENT_PATTERNS) {
    if (pattern.test(meta.content)) failures.push(`${path}: public synthetic content scan detected ${label}; automated scanning is supplementary and a human publication review is still required`);
  }
}

function validateRawState(meta, path) {
  const sourceId = requireString(meta, path, 'source_id');
  const sourceKind = requireString(meta, path, 'source_kind');
  const synthetic = requireBoolean(meta, path, 'synthetic');
  const consentStatus = requireString(meta, path, 'consent_status');
  const verificationStatus = requireString(meta, path, 'verification_status');
  const ingestionStatus = requireString(meta, path, 'ingestion_status');
  const lifecycle = normalized(ingestionStatus);

  if (synthetic === true && sourceKind && !isSyntheticKind(sourceKind)) failures.push(`${path}: synthetic true conflicts with source_kind ${sourceKind}`);
  if (synthetic === false && isSyntheticKind(sourceKind)) failures.push(`${path}: source_kind ${sourceKind} requires synthetic true`);
  if (lifecycle && !RAW_LIFECYCLE.has(lifecycle)) failures.push(`${path}: unknown ingestion_status ${ingestionStatus}; allowed=${[...RAW_LIFECYCLE].join(',')}`);
  if (claimsRealWorldVerification(verificationStatus)) {
    if (synthetic === true) failures.push(`${path}: synthetic source cannot claim real-world verification (${verificationStatus})`);
    if (!hasClearConsent(consentStatus)) failures.push(`${path}: real-world verification requires clearly authorized consent_status`);
  }
  if (releaseMode) {
    if (synthetic !== true) failures.push(`${path}: public release raw must set synthetic: true as a YAML boolean`);
    if (!isSyntheticKind(sourceKind)) failures.push(`${path}: public release raw source_kind must be synthetic/virtual/fixture`);
    if (normalized(requireString(meta, path, 'visibility')) !== 'public') failures.push(`${path}: public release raw visibility must be public`);
    if (normalized(requireString(meta, path, 'sensitivity')) !== 'public') failures.push(`${path}: public release raw sensitivity must be public`);
    if (normalized(requireString(meta, path, 'redaction_status')) !== 'safe-to-publish') failures.push(`${path}: public release raw redaction_status must be safe-to-publish`);
    if (!PUBLIC_RAW_CONSENT.has(normalized(consentStatus))) failures.push(`${path}: public release raw consent_status is not explicitly public-approved`);
    scanPublicSyntheticContent(meta, path);
  }
  return { sourceId, synthetic: synthetic === true, lifecycle };
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
  }
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

function validatePlainObject(value, label, bucket = failures) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    bucket.push(`${label} must be an object`);
    return false;
  }
  return true;
}

let signedCourseApprovals;
function loadSignedCourseApprovals() {
  if (signedCourseApprovals) return signedCourseApprovals;
  signedCourseApprovals = new Map();
  if (!courseApprovalArg || !courseApprovalSignatureArg) {
    failures.push('release knowledge-chain requires --course-approval and --course-approval-signature; in-repository reviewer_type fields cannot self-prove identity or approval');
    return signedCourseApprovals;
  }
  const approvalPath = resolve(courseApprovalArg);
  const signaturePath = resolve(courseApprovalSignatureArg);
  for (const [label, path] of [['course approval', approvalPath], ['course approval signature', signaturePath]]) {
    if (path === root || path.startsWith(`${root}${sep}`)) failures.push(`${label} must be a sidecar outside the repository working tree`);
    if (!existsSync(path) || !statSync(path).isFile()) failures.push(`${label} file does not exist: ${path}`);
  }
  const trusted = (process.env.COURSE_REVIEW_TRUSTED_SIGNERS ?? '').split(/[;,\s]+/u).map((item) => item.trim().toUpperCase()).filter(Boolean);
  if (!trusted.length || trusted.some((item) => !/^[A-F0-9]{40}(?:[A-F0-9]{24})?$/u.test(item))) failures.push('COURSE_REVIEW_TRUSTED_SIGNERS must contain valid trusted GPG fingerprints supplied by the protected release environment');
  if (failures.some((item) => item.startsWith('course approval') || item.startsWith('COURSE_REVIEW_'))) return signedCourseApprovals;
  const verify = spawnSync('gpg', ['--status-fd=1', '--verify', signaturePath, approvalPath], { encoding: 'utf8' });
  const fingerprint = `${verify.stdout ?? ''}\n${verify.stderr ?? ''}`.match(/\[GNUPG:\]\s+VALIDSIG\s+([A-F0-9]{40,64})/iu)?.[1]?.toUpperCase() ?? '';
  if (verify.status !== 0 || !fingerprint) failures.push('course approval detached GPG signature is invalid or unverifiable');
  else if (!trusted.includes(fingerprint)) failures.push(`course approval signer ${fingerprint} is not in COURSE_REVIEW_TRUSTED_SIGNERS`);
  let bundle;
  try {
    bundle = JSON.parse(readFileSync(approvalPath, 'utf8'));
  } catch {
    failures.push('course approval sidecar is not valid JSON');
    return signedCourseApprovals;
  }
  if (!validatePlainObject(bundle, 'course approval sidecar')) return signedCourseApprovals;
  if (bundle.schema !== 'course-review-approval/v2') failures.push(`course approval schema must be course-review-approval/v2, got ${bundle.schema ?? 'missing'}`);
  if (!Array.isArray(bundle.approvals) || !bundle.approvals.length) failures.push('course approval approvals must be a non-empty array');
  for (const entry of Array.isArray(bundle.approvals) ? bundle.approvals : []) {
    if (!validatePlainObject(entry, 'course approval entry')) continue;
    if (!/^ID-\d{4}$/u.test(entry.course_doc_id ?? '')) {
      failures.push('course approval course_doc_id must use ID-####');
      continue;
    }
    if (signedCourseApprovals.has(entry.course_doc_id)) {
      failures.push(`duplicate course approval for ${entry.course_doc_id}`);
      continue;
    }
    if (entry.approval_status !== 'approved') failures.push(`${entry.course_doc_id}: signed course approval_status must be approved`);
    if (typeof entry.approved_by !== 'string' || !entry.approved_by.trim()) failures.push(`${entry.course_doc_id}: signed course approved_by must be a non-empty signer label`);
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/u.test(entry.approved_at ?? '')) failures.push(`${entry.course_doc_id}: signed course approved_at must be UTC ISO-8601`);
    if (entry.approval_context === 'synthetic-test-fixture' || entry.reviewer_identity === 'not_verified') {
      failures.push(`${entry.course_doc_id}: synthetic fixture signer or reviewer_identity=not_verified cannot qualify a formal release`);
    } else {
      if (entry.approval_context !== 'independent-review') failures.push(`${entry.course_doc_id}: approval_context must be independent-review`);
      if (entry.reviewer_identity !== 'externally_verified') failures.push(`${entry.course_doc_id}: reviewer_identity must be externally_verified by the trusted signing environment`);
    }
    if (!validatePlainObject(entry.knowledge_chain_manifest, `${entry.course_doc_id}: knowledge_chain_manifest`)) continue;
    if (!/^[a-f0-9]{64}$/u.test(entry.knowledge_chain_manifest_sha256 ?? '')) failures.push(`${entry.course_doc_id}: knowledge_chain_manifest_sha256 must be a lowercase SHA-256 hex digest`);
    signedCourseApprovals.set(entry.course_doc_id, entry);
  }
  return signedCourseApprovals;
}

const registryPath = join(root, 'wiki/10_sources/source-registry.md');
const registry = existsSync(registryPath) ? read(registryPath) : '';
const logCorpus = markdownFiles(join(root, 'wiki/00_meta/logs')).map(read).join('\n');
const chainBySource = new Map();
const globalRoleIdentityToPath = new Map();
const globalRolePathToIdentity = new Map();
const rawRoots = ['raw/10_conversations', 'raw/20_web', 'raw/30_documents', 'raw/40_media', 'raw/50_exports'];
const durableRoleRoots = ['wiki/20_concepts', 'wiki/30_playbooks', 'wiki/90_outputs/courses'];

function registerGlobalRole(role, id, path, sourceId) {
  if (!id) return;
  const identity = `${role}:${id}`;
  const normalizedPath = rel(path);
  const priorPath = globalRoleIdentityToPath.get(identity);
  if (priorPath && priorPath !== normalizedPath) failures.push(`${sourceId}: role ID ${identity} is reused by different paths: ${priorPath}, ${normalizedPath}`);
  else globalRoleIdentityToPath.set(identity, normalizedPath);
  const priorIdentity = globalRolePathToIdentity.get(normalizedPath);
  if (priorIdentity && priorIdentity !== identity) failures.push(`${sourceId}: role path ${normalizedPath} is reused by different role IDs: ${priorIdentity}, ${identity}`);
  else globalRolePathToIdentity.set(normalizedPath, identity);
}

// Global uniqueness is a repository property, not merely a property of pages
// currently referenced by a source note. Scan every durable role root first so
// an orphan or not-yet-linked duplicate cannot bypass the five-role contract.
for (const roleRoot of durableRoleRoots) {
  for (const rolePath of markdownFiles(join(root, roleRoot)).sort()) {
    const roleMeta = frontMatter(rolePath);
    if (!roleMeta || isIndexOrTemplate(rolePath, roleMeta)) continue;
    const role = normalized(roleMeta.value('type'));
    if (!DERIVED_ROLES.has(role)) continue;
    const idField = DERIVED_ROLES.get(role);
    // Legacy durable pages are not forced into the progressive ID migration by
    // this validator. Once an ID field exists, however, it participates in the
    // repository-wide uniqueness contract and must be a valid string.
    if (!hasField(roleMeta, idField)) continue;
    const id = requireString(roleMeta, rel(rolePath), idField);
    registerGlobalRole(role, id, rolePath, 'global durable-role scan');
  }
}

for (const rawRoot of rawRoots) {
  for (const rawPath of markdownFiles(join(root, rawRoot)).sort()) {
    const rawRel = rel(rawPath);
    const meta = frontMatter(rawPath);
    if (isIndexOrTemplate(rawPath, meta)) continue;
    if (!meta) {
      failures.push(`${rawRel}: missing or invalid front matter`);
      continue;
    }
    const rawState = validateRawState(meta, rawRel);
    if (rawRoot === 'raw/10_conversations') {
      for (const field of ['source_date', 'captured_at', 'ingested_at', 'sensitivity', 'ingestion_status', 'raw_kind', 'conversation_type', 'channel', 'language']) requireString(meta, rawRel, field);
      for (const field of ['participants', 'topics', 'keywords']) requireStringArray(meta, rawRel, field, failures, { nonEmpty: releaseMode });
      const filename = basename(rawPath).match(/^src-(\d{8})-(\d{4})-[a-z0-9][a-z0-9-]*\.md$/u);
      if (!filename) failures.push(`${rawRel}: raw conversation filename must use src-YYYYMMDD-####-slug.md`);
      else {
        const sourceDate = meta.value('source_date').replaceAll('-', '');
        if (sourceDate !== filename[1]) failures.push(`${rawRel}: filename date ${filename[1]} must equal source_date ${meta.value('source_date') || 'missing'}`);
        if (rawState.sourceId !== `SRC-${filename[1]}-${filename[2]}`) failures.push(`${rawRel}: source_id must equal SRC-${filename[1]}-${filename[2]} for this raw conversation`);
      }
      for (const forbiddenHeading of ['## Extraction Boundary', '## Summary', '## Recommendations', '## Analysis']) {
        if (meta.content.includes(`\n${forbiddenHeading}`)) failures.push(`${rawRel}: raw conversation contains distilled heading ${forbiddenHeading}`);
      }
    }

    const derivedTo = requireStringArray(meta, rawRel, 'derived_to');
    if (RAW_STATES_REQUIRING_DERIVATION.has(rawState.lifecycle) && !derivedTo.length) failures.push(`${rawRel}: ${rawState.lifecycle} source must list derived_to IDs`);

    const sourceId = rawState.sourceId;
    if (!sourceId) continue;
    if (chainBySource.has(sourceId)) {
      failures.push(`${rawRel}: duplicate raw source_id ${sourceId}; each Source ID must bind exactly one raw path`);
      continue;
    }
    const sourceNotePath = join(root, 'wiki/10_sources', `${sourceId}.md`);
    if (!existsSync(sourceNotePath)) {
      failures.push(`${rawRel}: source note missing for ${sourceId}`);
      continue;
    }
    const note = frontMatter(sourceNotePath);
    if (!note) {
      failures.push(`${sourceId}: source note missing or invalid front matter`);
      continue;
    }
    if (requireString(note, rel(sourceNotePath), 'source_id') !== sourceId) failures.push(`${sourceId}: source note source_id does not match raw source_id`);
    if (requireString(note, rel(sourceNotePath), 'raw_path') !== rawRel) failures.push(`${sourceId}: raw_path does not point to ${rawRel}`);
    if (!registry.includes(`| ${sourceId} |`)) failures.push(`${sourceId}: missing source registry row`);

    const derived = requireStringArray(note, rel(sourceNotePath), 'derived_pages');
    if (derived.length !== DERIVED_ROLES.size) failures.push(`${sourceId}: derived_pages must contain exactly five unique role paths`);
    const rolePaths = new Map();
    const roleIds = new Map();
    const derivedIds = [];
    for (const target of derived) {
      const targetPath = resolveSafe(sourceNotePath, target, `${sourceId}: derived_pages`);
      if (!targetPath || !existsSync(targetPath)) {
        failures.push(`${sourceId}: derived page missing: ${target}`);
        continue;
      }
      const targetMeta = frontMatter(targetPath);
      if (!targetMeta) {
        failures.push(`${sourceId}: derived page missing or invalid front matter: ${target}`);
        continue;
      }
      const role = normalized(requireString(targetMeta, rel(targetPath), 'type'));
      if (!DERIVED_ROLES.has(role)) {
        failures.push(`${sourceId}: unsupported derived role ${role || 'missing'} at ${target}`);
        continue;
      }
      if (rolePaths.has(role)) failures.push(`${sourceId}: role ${role} appears more than once in derived_pages`);
      rolePaths.set(role, targetPath);
      const idField = DERIVED_ROLES.get(role);
      const id = requireString(targetMeta, rel(targetPath), idField);
      if (id) {
        roleIds.set(role, id);
        derivedIds.push(id);
        registerGlobalRole(role, id, targetPath, sourceId);
      }
      const targetSources = requireStringArray(targetMeta, rel(targetPath), 'sources');
      if (!targetSources.includes(sourceId)) failures.push(`${sourceId}: ${role} does not bind back through sources: ${target}`);
    }
    for (const role of DERIVED_ROLES.keys()) if (!rolePaths.has(role)) failures.push(`${sourceId}: missing unique derived role ${role}`);
    if (!sameStringSet(derivedTo, derivedIds)) failures.push(`${sourceId}: raw derived_to IDs do not exactly match source-note derived page IDs`);

    for (const [field, role] of [['verification_record', 'verification-record'], ['writeback_record', 'writeback-record']]) {
      const declaredValue = requireString(note, rel(sourceNotePath), field);
      const declared = resolveSafe(sourceNotePath, declaredValue, `${sourceId}: ${field}`);
      if (declared && !existsSync(declared)) failures.push(`${sourceId}: ${field} target missing: ${declaredValue}`);
      if (declared && rolePaths.get(role) && !samePath(declared, rolePaths.get(role))) failures.push(`${sourceId}: ${field} does not match the unique ${role} derived page`);
    }
    chainBySource.set(sourceId, { rawPath, sourceNotePath, rolePaths, roleIds, synthetic: rawState.synthetic });
  }
}

function evidenceWarning(message) {
  warnings.push(message);
}
function requireEvidenceString(meta, path, field) {
  return requireString(meta, path, field, warnings);
}
function requireEvidenceArray(meta, path, field, options = {}) {
  return requireStringArray(meta, path, field, warnings, options);
}

function validateEventAndSnapshots(meta, recordPath, label, minimumSnapshots = 1) {
  const events = requireEvidenceArray(meta, label, 'event_refs', { nonEmpty: true });
  const snapshots = requireEvidenceArray(meta, label, 'snapshot_refs');
  if (snapshots.length < minimumSnapshots) evidenceWarning(`${label}: snapshot_refs must contain at least ${minimumSnapshots} evidence path(s)`);
  for (const event of events) {
    if (!new RegExp(`\\b${event.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&')}\\b`, 'u').test(logCorpus)) evidenceWarning(`${label}: event reference does not exist in wiki/00_meta/logs: ${event}`);
  }
  for (const snapshot of snapshots) {
    const target = resolveSafe(recordPath, snapshot, `${label}: snapshot_refs`, warnings);
    if (!target || !existsSync(target)) {
      evidenceWarning(`${label}: snapshot path does not exist: ${snapshot}`);
      continue;
    }
    const snapshotMeta = frontMatter(target, warnings);
    if (!snapshotMeta) {
      evidenceWarning(`${label}: snapshot missing or invalid front matter: ${snapshot}`);
      continue;
    }
    if (normalized(requireEvidenceString(snapshotMeta, rel(target), 'type')) !== 'evidence-snapshot') evidenceWarning(`${label}: snapshot ${snapshot} must use type evidence-snapshot`);
    for (const field of ['snapshot_id', 'captured_at', 'subject', 'evidence_digest']) requireEvidenceString(snapshotMeta, rel(target), field);
    const body = documentBody(snapshotMeta);
    const digest = sha256Buffer(body);
    if (snapshotMeta.value('evidence_digest') !== `sha256:${digest}`) evidenceWarning(`${rel(target)}: evidence_digest must equal sha256 of the snapshot body`);
    meaningfulSection(snapshotMeta, 'Captured Evidence', rel(target));
  }
}

function loadEvidencePath(coursePath, course, field, expectedType) {
  const value = requireEvidenceString(course, rel(coursePath), field);
  if (!value) return null;
  const target = resolveSafe(coursePath, value, `${rel(coursePath)}: ${field}`, warnings);
  if (!target || !existsSync(target)) {
    evidenceWarning(`${rel(coursePath)}: ${field} target missing: ${value}`);
    return null;
  }
  const meta = frontMatter(target, warnings);
  if (!meta) {
    evidenceWarning(`${rel(coursePath)}: ${field} target missing or invalid front matter: ${value}`);
    return null;
  }
  if (normalized(requireEvidenceString(meta, rel(target), 'type')) !== expectedType) evidenceWarning(`${rel(coursePath)}: ${field} must point to type ${expectedType}`);
  return { path: target, meta };
}

function validateStatus(meta, path, field, allowed, missingBucket = warnings) {
  const rawValue = requireString(meta, path, field, missingBucket);
  const value = normalized(rawValue);
  if (value && !allowed.has(value)) failures.push(`${path}: unknown ${field} ${rawValue}; allowed=${[...allowed].join(',')}`);
  return value;
}

function artifact(role, path, sourceId = '') {
  const result = { role, path: rel(path), sha256: sha256(path) };
  if (sourceId) result.source_id = sourceId;
  return result;
}

function buildKnowledgeChainManifest(courseId, sourceIds, coursePath, evidence) {
  const artifacts = [];
  for (const sourceId of sortedSet(sourceIds)) {
    const chain = chainBySource.get(sourceId);
    if (!chain) continue;
    artifacts.push(artifact('raw', chain.rawPath, sourceId));
    artifacts.push(artifact('source-note', chain.sourceNotePath, sourceId));
    if (chain.rolePaths.get('concept')) artifacts.push(artifact('concept', chain.rolePaths.get('concept'), sourceId));
    if (chain.rolePaths.get('playbook')) artifacts.push(artifact('playbook', chain.rolePaths.get('playbook'), sourceId));
  }
  artifacts.push(artifact('course', coursePath));
  if (evidence.exercise) artifacts.push(artifact('exercise', evidence.exercise.path));
  if (evidence.review) artifacts.push(artifact('review', evidence.review.path));
  if (evidence.verification) artifacts.push(artifact('verification', evidence.verification.path));
  if (evidence.writeback) artifacts.push(artifact('writeback', evidence.writeback.path));
  artifacts.sort((left, right) => (MANIFEST_ARTIFACT_ORDER.get(left.role) - MANIFEST_ARTIFACT_ORDER.get(right.role))
    || (left.source_id ?? '').localeCompare(right.source_id ?? '', 'en')
    || left.path.localeCompare(right.path, 'en'));
  const snapshot = {
    schema: 'knowledge-chain-snapshot/v1',
    course_doc_id: courseId,
    source_ids: sortedSet(sourceIds),
    artifacts,
  };
  return {
    schema: 'knowledge-chain-manifest/v1',
    source_commit: sourceCommitArg,
    snapshot_digest: `sha256:${sha256Buffer(canonicalJson(snapshot))}`,
    course_doc_id: courseId,
    source_ids: snapshot.source_ids,
    artifacts,
  };
}

function validateManifestCommitBinding(manifest, courseRel) {
  if (!/^[a-f0-9]{40}$/u.test(sourceCommitArg)) {
    evidenceWarning(`${courseRel}: --source-commit or COURSE_REVIEW_SOURCE_COMMIT must be a lowercase 40-hex commit`);
    return;
  }
  const head = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' });
  if (head.status !== 0 || head.stdout.trim() !== sourceCommitArg) {
    evidenceWarning(`${courseRel}: source_commit must equal the currently checked-out Git commit`);
    return;
  }
  for (const item of manifest.artifacts) {
    const object = spawnSync('git', ['show', `${sourceCommitArg}:${item.path}`], { cwd: root, encoding: null, maxBuffer: 16 * 1024 * 1024 });
    if (object.status !== 0) {
      evidenceWarning(`${courseRel}: manifest artifact is not present in source_commit: ${item.path}`);
      continue;
    }
    const committedDigest = sha256Buffer(object.stdout);
    if (committedDigest !== item.sha256) evidenceWarning(`${courseRel}: manifest artifact differs from source_commit: ${item.path}`);
  }
}

function validateSignedManifest(courseId, courseRel, manifest) {
  const approval = loadSignedCourseApprovals().get(courseId);
  if (!approval) {
    evidenceWarning(`${courseRel}: no trusted signed external course approval is bound to ${courseId}`);
    return;
  }
  const actualJson = canonicalJson(manifest);
  const expectedJson = canonicalJson(approval.knowledge_chain_manifest);
  if (actualJson !== expectedJson) evidenceWarning(`${courseRel}: signed canonical knowledge_chain_manifest does not match the current raw/source/concept/playbook/course/evidence chain`);
  const digest = sha256Buffer(actualJson);
  if (approval.knowledge_chain_manifest_sha256 !== digest) evidenceWarning(`${courseRel}: signed knowledge_chain_manifest_sha256 does not match the canonical current manifest`);
  validateManifestCommitBinding(manifest, courseRel);
}

const courseDir = join(root, 'wiki/90_outputs/courses');
if (existsSync(courseDir)) {
  for (const name of readdirSync(courseDir).filter((entry) => /^id-\d{4}-.*\.md$/u.test(entry)).sort()) {
    const coursePath = join(courseDir, name);
    const course = frontMatter(coursePath);
    if (!course) {
      failures.push(`${name}: missing or invalid front matter`);
      continue;
    }
    const courseRel = rel(coursePath);
    const courseId = requireString(course, courseRel, 'doc_id');
    const sourceIds = requireStringArray(course, courseRel, 'sources', failures, { nonEmpty: true }).filter((source) => source.startsWith('SRC-'));
    if (!sourceIds.length) failures.push(`${courseRel}: course must bind at least one Source ID`);

    const chainsPointingToCourse = [...chainBySource.entries()]
      .filter(([, chain]) => samePath(chain.rolePaths.get('course-module'), coursePath))
      .map(([sourceId]) => sourceId);
    if (!sameStringSet(sourceIds, chainsPointingToCourse)) failures.push(`${courseRel}: course sources must exactly equal every Source ID whose unique course-module role points to this course; course=${sortedSet(sourceIds).join(',') || 'none'} chain=${sortedSet(chainsPointingToCourse).join(',') || 'none'}`);
    for (const sourceId of sourceIds) {
      const chain = chainBySource.get(sourceId);
      if (!chain) failures.push(`${courseRel}: no validated raw/source chain for ${sourceId}`);
      else if (!samePath(chain.rolePaths.get('course-module'), coursePath)) failures.push(`${courseRel}: ${sourceId} unique course-module path does not match the consumed course`);
    }

    const structureStatus = validateStatus(course, courseRel, 'structure_verification_status', STRUCTURE_STATES);
    const exerciseStatus = validateStatus(course, courseRel, 'exercise_verification_status', EXERCISE_STATES);
    const effectivenessStatus = validateStatus(course, courseRel, 'effectiveness_verification_status', EFFECTIVENESS_STATES);
    if (structureStatus !== 'verified') evidenceWarning(`${courseRel}: structure_verification_status must be verified for release evidence`);
    if (exerciseStatus !== 'verified') evidenceWarning(`${courseRel}: exercise_verification_status must be verified for release evidence`);

    const exercise = loadEvidencePath(coursePath, course, 'exercise_artifact', 'evidence');
    const review = loadEvidencePath(coursePath, course, 'review_record', 'review-record');
    const verification = loadEvidencePath(coursePath, course, 'verification_record', 'verification-record');
    const writeback = loadEvidencePath(coursePath, course, 'writeback_record', 'writeback-record');
    const evidencePaths = [exercise?.path, review?.path, verification?.path, writeback?.path].filter(Boolean).map((path) => rel(path));
    unique(evidencePaths, `${courseRel}: evidence paths`, warnings);

    for (const sourceId of sourceIds) {
      const chain = chainBySource.get(sourceId);
      if (!chain) continue;
      if (verification && !samePath(chain.rolePaths.get('verification-record'), verification.path)) failures.push(`${courseRel}: ${sourceId} unique verification-record path does not match the course verification_record`);
      if (writeback && !samePath(chain.rolePaths.get('writeback-record'), writeback.path)) failures.push(`${courseRel}: ${sourceId} unique writeback-record path does not match the course writeback_record`);
    }

    const verificationSources = verification ? requireStringArray(verification.meta, rel(verification.path), 'sources') : [];
    const writebackSources = writeback ? requireStringArray(writeback.meta, rel(writeback.path), 'sources') : [];
    if (verification && !sameStringSet(sourceIds, verificationSources)) failures.push(`${courseRel}: course and verification sources sets must be exactly equal`);
    if (writeback && !sameStringSet(sourceIds, writebackSources)) failures.push(`${courseRel}: course and writeback sources sets must be exactly equal`);

    const allSynthetic = sourceIds.length > 0 && sourceIds.every((sourceId) => chainBySource.get(sourceId)?.synthetic === true);
    if (allSynthetic && effectivenessStatus === 'real-world-effectiveness-verified') failures.push(`${courseRel}: synthetic-only knowledge chain cannot claim real-world-effectiveness-verified`);

    if (exercise) {
      for (const field of ['exercise_id', 'course_doc_id', 'submission_status', 'rubric_id']) requireEvidenceString(exercise.meta, rel(exercise.path), field);
      const scenarioCount = requireNumber(exercise.meta, rel(exercise.path), 'scenario_count', warnings, { integer: true });
      if (scenarioCount !== null && scenarioCount < 2) evidenceWarning(`${rel(exercise.path)}: scenario_count must be an integer >= 2`);
      meaningfulSection(exercise.meta, 'Scenario 2 Input', rel(exercise.path));
      meaningfulSection(exercise.meta, 'Submitted Output', rel(exercise.path));
      meaningfulSection(exercise.meta, 'Self Check', rel(exercise.path));
      if (exercise.meta.value('course_doc_id') !== courseId) evidenceWarning(`${rel(exercise.path)}: course_doc_id does not match ${courseId}`);
      if (normalized(exercise.meta.value('submission_status')) !== 'submitted') evidenceWarning(`${rel(exercise.path)}: submission_status must be submitted`);
      const exerciseSources = requireEvidenceArray(exercise.meta, rel(exercise.path), 'sources', { nonEmpty: true });
      if (!sameStringSet(sourceIds, exerciseSources)) evidenceWarning(`${rel(exercise.path)}: sources must exactly equal the course sources set`);
    }
    if (review) {
      for (const field of ['review_id', 'course_doc_id', 'reviewer_id', 'reviewer_type', 'review_status', 'review_result', 'reviewed_artifact', 'artifact_sha256', 'rubric_id']) requireEvidenceString(review.meta, rel(review.path), field);
      const score = requireNumber(review.meta, rel(review.path), 'score');
      const scoreMax = requireNumber(review.meta, rel(review.path), 'score_max');
      const threshold = requireNumber(review.meta, rel(review.path), 'pass_threshold');
      if ([score, scoreMax, threshold].every((value) => value !== null)
        && (scoreMax <= 0 || threshold < 0 || threshold > scoreMax || score < threshold || score > scoreMax)) evidenceWarning(`${rel(review.path)}: score, score_max and pass_threshold must prove a valid passing rubric result`);
      meaningfulSection(review.meta, 'Rubric Results', rel(review.path));
      meaningfulSection(review.meta, 'Reviewer Findings', rel(review.path));
      if (review.meta.value('course_doc_id') !== courseId) evidenceWarning(`${rel(review.path)}: course_doc_id does not match ${courseId}`);
      if (normalized(review.meta.value('reviewer_type')) !== 'human') evidenceWarning(`${rel(review.path)}: reviewer_type must be human for the review record, but this metadata alone does not verify identity`);
      if (normalized(review.meta.value('review_status')) !== 'completed') evidenceWarning(`${rel(review.path)}: review_status must be completed`);
      if (normalized(review.meta.value('review_result')) !== 'pass') evidenceWarning(`${rel(review.path)}: review_result must be pass`);
      const reviewed = resolveSafe(review.path, review.meta.value('reviewed_artifact'), `${rel(review.path)}: reviewed_artifact`, warnings);
      if (exercise && reviewed && !samePath(reviewed, exercise.path)) evidenceWarning(`${rel(review.path)}: reviewed_artifact does not match course exercise_artifact`);
      if (exercise && review.meta.value('artifact_sha256') !== sha256(exercise.path)) evidenceWarning(`${rel(review.path)}: artifact_sha256 does not match exercise artifact content`);
      const reviewSources = requireEvidenceArray(review.meta, rel(review.path), 'sources', { nonEmpty: true });
      if (!sameStringSet(sourceIds, reviewSources)) evidenceWarning(`${rel(review.path)}: sources must exactly equal the course sources set`);
      validateEventAndSnapshots(review.meta, review.path, rel(review.path));
    }
    if (verification) {
      for (const field of ['verification_id', 'course_doc_id', 'exercise_artifact', 'review_record', 'observed_result', 'allowed_claim', 'non_claim']) requireEvidenceString(verification.meta, rel(verification.path), field);
      const sampleSize = requireNumber(verification.meta, rel(verification.path), 'sample_size', warnings, { integer: true });
      if (sampleSize !== null && sampleSize < 1) evidenceWarning(`${rel(verification.path)}: sample_size must be an integer >= 1`);
      const verificationStructure = validateStatus(verification.meta, rel(verification.path), 'structure_verification_status', STRUCTURE_STATES);
      const verificationExercise = validateStatus(verification.meta, rel(verification.path), 'exercise_verification_status', EXERCISE_STATES);
      const verificationEffectiveness = validateStatus(verification.meta, rel(verification.path), 'effectiveness_verification_status', EFFECTIVENESS_STATES);
      if (verificationStructure !== structureStatus) failures.push(`${courseRel}: course and verification structure_verification_status must match exactly`);
      if (verificationExercise !== exerciseStatus) failures.push(`${courseRel}: course and verification exercise_verification_status must match exactly`);
      if (verificationEffectiveness !== effectivenessStatus) failures.push(`${courseRel}: course and verification effectiveness_verification_status must match exactly`);
      if (allSynthetic && verificationEffectiveness === 'real-world-effectiveness-verified') failures.push(`${rel(verification.path)}: synthetic-only knowledge chain cannot claim real-world-effectiveness-verified`);
      meaningfulSection(verification.meta, 'Steps And Evidence', rel(verification.path));
      meaningfulSection(verification.meta, 'Result And Boundary', rel(verification.path));
      if (verification.meta.value('course_doc_id') !== courseId) evidenceWarning(`${rel(verification.path)}: course_doc_id does not match ${courseId}`);
      const verificationExercisePath = resolveSafe(verification.path, verification.meta.value('exercise_artifact'), `${rel(verification.path)}: exercise_artifact`, warnings);
      const verificationReviewPath = resolveSafe(verification.path, verification.meta.value('review_record'), `${rel(verification.path)}: review_record`, warnings);
      if (exercise && verificationExercisePath && !samePath(verificationExercisePath, exercise.path)) evidenceWarning(`${rel(verification.path)}: exercise_artifact does not match course evidence`);
      if (review && verificationReviewPath && !samePath(verificationReviewPath, review.path)) evidenceWarning(`${rel(verification.path)}: review_record does not match course evidence`);
      validateEventAndSnapshots(verification.meta, verification.path, rel(verification.path));
    }
    if (writeback) {
      for (const field of ['writeback_id', 'course_doc_id', 'writeback_status', 'verification_record', 'review_record', 'change_summary']) requireEvidenceString(writeback.meta, rel(writeback.path), field);
      const targets = requireEvidenceArray(writeback.meta, rel(writeback.path), 'writeback_targets', { nonEmpty: true });
      for (const target of targets) {
        const resolvedTarget = resolveSafe(writeback.path, target, `${rel(writeback.path)}: writeback_targets`, warnings);
        if (resolvedTarget && !existsSync(resolvedTarget)) evidenceWarning(`${rel(writeback.path)}: writeback target does not exist: ${target}`);
      }
      meaningfulSection(writeback.meta, 'Observed Evidence', rel(writeback.path));
      meaningfulSection(writeback.meta, 'Knowledge Changes', rel(writeback.path));
      if (writeback.meta.value('course_doc_id') !== courseId) evidenceWarning(`${rel(writeback.path)}: course_doc_id does not match ${courseId}`);
      if (normalized(writeback.meta.value('writeback_status')) !== 'completed') evidenceWarning(`${rel(writeback.path)}: writeback_status must be completed`);
      const writebackVerification = resolveSafe(writeback.path, writeback.meta.value('verification_record'), `${rel(writeback.path)}: verification_record`, warnings);
      const writebackReview = resolveSafe(writeback.path, writeback.meta.value('review_record'), `${rel(writeback.path)}: review_record`, warnings);
      if (verification && writebackVerification && !samePath(writebackVerification, verification.path)) evidenceWarning(`${rel(writeback.path)}: verification_record does not match course evidence`);
      if (review && writebackReview && !samePath(writebackReview, review.path)) evidenceWarning(`${rel(writeback.path)}: review_record does not match course evidence`);
      validateEventAndSnapshots(writeback.meta, writeback.path, rel(writeback.path), 2);
    }

    if (releaseMode) {
      const manifest = buildKnowledgeChainManifest(courseId, sourceIds, coursePath, { exercise, review, verification, writeback });
      validateSignedManifest(courseId, courseRel, manifest);
    }
  }
}

if (releaseMode && warnings.length) {
  for (const warning of warnings) failures.push(`release evidence incomplete: ${warning}`);
}
if (warnings.length) {
  console.log(`KNOWLEDGE_CHAIN_WARNINGS: ${warnings.length}`);
  for (const warning of warnings) console.log(`WARN: ${warning}`);
}
if (failures.length) {
  console.error(`KNOWLEDGE_CHAIN_FAILURES: ${failures.length}`);
  for (const failure of failures) console.error(`BLOCK: ${failure}`);
  process.exitCode = 1;
} else if (releaseMode) {
  console.log('KNOWLEDGE_CHAIN_RELEASE_PASS: release evidence, trusted external approval signature, source commit binding, and canonical manifest validation passed within the declared claim scope. This release result does not by itself prove real-world effectiveness beyond an explicitly verified effectiveness state.');
} else {
  console.log('KNOWLEDGE_CHAIN_STRUCTURE_PASS: raw/source/five-role paths, source sets, and declared three-layer status values are structurally consistent. This local structural result does not prove exercise completion, human review, real-world effectiveness, external approval, or release eligibility.');
}
