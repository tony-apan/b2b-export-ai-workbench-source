#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { isIP } from 'node:net';
import { basename, dirname, resolve } from 'node:path';
import { parseMarkdownFrontMatter } from './front-matter.mjs';

const candidateRoot = resolve(process.argv[2] ?? '');
const approvalPath = resolve(process.argv[3] ?? '');
const failures = [];
const sourcePublicationClearanceFields = ['publication_review_status', 'publication_status', 'license_status'];
const sourceCardPathPattern = /^REFERENCES\/SRC-[A-Za-z0-9][A-Za-z0-9._-]*\.md$/;
const referenceMarkdownPathPattern = /^REFERENCES\/.+\.md$/i;
const allowedSourcePublicationReviewStatuses = new Set(['pending', 'approved', 'rejected']);
const allowedSourcePublicationStatuses = new Set(['BLOCK', 'PASS']);
const allowedSourceLicenseStatuses = new Set(['pending', 'cleared', 'restricted', 'unknown']);
function fail(message) { failures.push(message); }
function sha256(path) { return createHash('sha256').update(readFileSync(path)).digest('hex'); }
function requiredString(value, field) {
  if (typeof value !== 'string' || !value.trim()) fail(`approval ${field} must be a non-empty string`);
  return typeof value === 'string' ? value.trim() : '';
}
function hex(value, field, length = 64) {
  const text = requiredString(value, field);
  if (text && !new RegExp(`^[a-f0-9]{${length}}$`).test(text)) fail(`approval ${field} must be ${length} lowercase hexadecimal characters`);
  return text;
}
const safeVersionPattern = /^[0-9A-Za-z][0-9A-Za-z._-]*$/;
const placeholderCandidateIdentities = new Set(['unassigned', 'unknown', 'pending', 'placeholder', 'tbd', 'todo', 'null', 'none', 'n/a']);
function manifestString(value) {
  return typeof value === 'string' ? value.trim() : '';
}
function validateFrozenManifestIdentity(manifest) {
  const versionSemantics = manifestString(manifest?.version_semantics);
  const currentCandidateIdentity = manifestString(manifest?.current_candidate_identity);
  const currentCandidateSnapshot = manifestString(manifest?.current_candidate_snapshot);
  const currentCandidateVersion = manifestString(manifest?.current_candidate_version);
  const manifestVersion = manifestString(manifest?.version);
  const historicalPublishedVersion = manifestString(manifest?.historical_published_version);
  const historicalPublishedTag = manifestString(manifest?.historical_published_tag);

  if (versionSemantics !== 'current-candidate-only') fail('MANIFEST.json version_semantics must be current-candidate-only');
  if (!currentCandidateIdentity || placeholderCandidateIdentities.has(currentCandidateIdentity.toLowerCase())) fail('MANIFEST.json current_candidate_identity must be an assigned non-placeholder string');
  if (!currentCandidateSnapshot || !safeVersionPattern.test(currentCandidateSnapshot) || currentCandidateSnapshot === 'dirty-working-tree') fail('MANIFEST.json current_candidate_snapshot must be a safe non-dirty value');
  if (!currentCandidateVersion || !safeVersionPattern.test(currentCandidateVersion)) fail('MANIFEST.json current_candidate_version must be a safe non-empty version');
  if (manifestVersion !== currentCandidateVersion) fail('MANIFEST.json version must equal current_candidate_version');
  if (!historicalPublishedVersion || !safeVersionPattern.test(historicalPublishedVersion)) fail('MANIFEST.json historical_published_version must be a safe non-empty version');
  if (historicalPublishedTag !== `v${historicalPublishedVersion}`) fail('MANIFEST.json historical_published_tag must equal v<historical_published_version>');
  if (currentCandidateVersion && historicalPublishedVersion && currentCandidateVersion === historicalPublishedVersion) fail('MANIFEST.json current_candidate_version must not equal historical_published_version');
  if (currentCandidateVersion && historicalPublishedTag && `v${currentCandidateVersion}` === historicalPublishedTag) fail('MANIFEST.json current candidate tag must not collide with historical_published_tag');

  return currentCandidateVersion;
}

function canonicalJson(value, field = 'evidence') {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) fail(`approval ${field} contains a non-finite number`);
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map((item, index) => canonicalJson(item, `${field}[${index}]`)).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key], `${field}.${key}`)}`).join(',')}}`;
  }
  fail(`approval ${field} contains an unsupported JSON value`);
  return 'null';
}
function canonicalDigest(value, field = 'canonical value') {
  return createHash('sha256').update(canonicalJson(value, field), 'utf8').digest('hex');
}
function canonicalEvidenceDigest(value) {
  return canonicalDigest(value, 'evidence');
}
const TAG_ANNOTATION_SCHEMA = 'release-tag-annotation/v1';
const APPROVAL_BINDING_ALGORITHM = 'sha256-canonical-approval-binding-v1';
function approvalBindingProjection(approval) {
  return {
    schema: approval?.schema ?? null,
    approval_id: approval?.approval_id ?? null,
    decision: approval?.decision ?? null,
    scope: approval?.scope ?? null,
    source: approval?.source ?? null,
    candidate: approval?.candidate ?? null,
    validation: { profile: approval?.validation?.profile ?? null },
    approval: approval?.approval ?? null,
    tag: {
      name: approval?.tag?.name ?? null,
      target_commit: approval?.tag?.target_commit ?? null,
      signer_fingerprint: approval?.tag?.signer_fingerprint ?? null,
    },
  };
}
function expectedTagAnnotation(approval, manifest, approvalBindingSha256, currentCandidateVersion) {
  return {
    approval_binding_sha256: approvalBindingSha256,
    approval_id: approval?.approval_id ?? null,
    candidate_content_digest: manifest?.content_digest ?? null,
    schema: TAG_ANNOTATION_SCHEMA,
    scope: { kind: approval?.scope?.kind ?? null, id: approval?.scope?.id ?? null },
    version: currentCandidateVersion || null,
  };
}
function parseCanonicalTagAnnotation(text, field) {
  if (typeof text !== 'string' || !text) { fail(`${field} must be a non-empty canonical JSON object`); return {}; }
  if (text.includes('\n') || text.includes('\r')) fail(`${field} must be a single canonical JSON line`);
  let value = {};
  try { value = JSON.parse(text); } catch { fail(`${field} must be valid JSON`); return {}; }
  exactKeys(value, ['approval_binding_sha256', 'approval_id', 'candidate_content_digest', 'schema', 'scope', 'version'], field);
  exactKeys(value.scope, ['kind', 'id'], `${field}.scope`);
  if (canonicalJson(value, field) !== text) fail(`${field} must use canonical JSON with sorted keys and no extra whitespace`);
  return value;
}
function decodeCanonicalBase64(value, field) {
  const text = requiredString(value, field);
  if (!text || !/^[A-Za-z0-9+/]+={0,2}$/.test(text) || text.length % 4 !== 0) {
    fail(`${field} must be canonical base64`);
    return '';
  }
  const decoded = Buffer.from(text, 'base64');
  if (decoded.toString('base64') !== text) fail(`${field} must be canonical base64`);
  return decoded.toString('utf8');
}
function annotationFromTagObject(raw, field) {
  const separator = raw.indexOf('\n\n');
  if (separator < 0) { fail(`${field} is missing the annotated tag message separator`); return ''; }
  const body = raw.slice(separator + 2);
  const signatureMarker = '\n-----BEGIN PGP SIGNATURE-----';
  const signatureIndex = body.indexOf(signatureMarker);
  if (signatureIndex < 0) { fail(`${field} is missing an inline GPG signature block`); return ''; }
  const message = body.slice(0, signatureIndex);
  if (!message) fail(`${field} has an empty annotation message`);
  return message;
}
const REQUIRED_EVIDENCE_CHECKS = {
  'mother-release-v1': [
    'governance-tests',
    'index-validation',
    'link-validation',
    'document-id-validation',
    'log-validation',
    'knowledge-chain-validation',
    'mother-structure-validation',
    'artifact-validation',
    'commit-provenance',
    'tag-signature',
  ],
  'sub-library-release-v1': [
    'governance-tests',
    'index-validation',
    'link-validation',
    'document-id-validation',
    'sub-library-structure-validation',
    'runtime-tests',
    'artifact-validation',
    'commit-provenance',
    'tag-signature',
  ],
};
const EXPECTED_GOVERNANCE_TEST_PLAN = ['scripts/release-governance.test.mjs'];
const EXPECTED_RUNTIME_TEST_PLAN = [
  'upload-media-browser.test.mjs',
  'article-image-binding.test.mjs',
  'article-content-formats.test.mjs',
  'article-operations.test.mjs',
];
const EXPECTED_RUNTIME_TEST_COUNT = 172;
function currentGovernanceTestPlan(root) {
  const planScript = resolve(root, EXPECTED_GOVERNANCE_TEST_PLAN[0]);
  if (!existsSync(planScript) || !statSync(planScript).isFile()) {
    fail(`approval governance plan source is missing: ${EXPECTED_GOVERNANCE_TEST_PLAN[0]}`);
    return [];
  }
  const result = spawnSync(process.execPath, [planScript, '--list'], {
    cwd: root,
    encoding: 'utf8',
    timeout: 10_000,
    killSignal: 'SIGKILL',
  });
  if (result.error || result.status !== 0) {
    fail(`approval governance plan discovery failed for ${EXPECTED_GOVERNANCE_TEST_PLAN[0]}`);
    return [];
  }
  const payload = result.stdout.match(/^GOVERNANCE_TEST_PLAN_JSON:\s*(\[[^\n]+\])$/m)?.[1];
  if (!payload) {
    fail('approval governance plan discovery did not return GOVERNANCE_TEST_PLAN_JSON');
    return [];
  }
  try {
    const plan = JSON.parse(payload);
    if (!Array.isArray(plan) || plan.length === 0 || plan.some((name) => typeof name !== 'string' || !name.trim()) || new Set(plan).size !== plan.length) {
      fail('approval governance plan discovery returned an invalid or duplicate test list');
      return [];
    }
    return plan;
  } catch {
    fail('approval governance plan discovery returned invalid JSON');
    return [];
  }
}
function integerAtLeast(value, field, minimum = 0) {
  if (!Number.isInteger(value) || value < minimum) fail(`approval ${field} must be an integer >= ${minimum}`);
  return Number.isInteger(value) ? value : 0;
}
function exactKeys(value, allowed, field) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    fail(`approval ${field} must be an object`);
    return;
  }
  for (const key of Object.keys(value)) if (!allowed.includes(key)) fail(`approval ${field} contains unsupported key ${key}`);
  for (const key of allowed) if (!(key in value)) fail(`approval ${field} is missing required key ${key}`);
}
function validateStringArray(value, field) {
  if (!Array.isArray(value) || value.length === 0) {
    fail(`approval ${field} must be a non-empty array`);
    return [];
  }
  const items = value.map((item, index) => requiredString(item, `${field}[${index}]`));
  if (new Set(items).size !== items.length) fail(`approval ${field} must not contain duplicate entries`);
  return items;
}
function validateEvidenceChecks(checks, profile, manifest, sourceCommit, contentDigest, tagName, governanceTestPlan, tagBinding = null) {
  const requiredIds = REQUIRED_EVIDENCE_CHECKS[profile] ?? [];
  if (!Array.isArray(checks)) {
    fail('approval evidence checks must be an array');
    return;
  }
  const byId = new Map();
  for (const [index, check] of checks.entries()) {
    if (!check || typeof check !== 'object' || Array.isArray(check)) {
      fail(`approval evidence checks[${index}] must be an object`);
      continue;
    }
    exactKeys(check, ['id', 'status', 'result'], `evidence.checks[${index}]`);
    const checkId = requiredString(check.id, `evidence.checks[${index}].id`);
    if (checkId && !/^[a-z0-9][a-z0-9._-]*$/.test(checkId)) fail(`approval evidence checks[${index}].id must be a stable lowercase identifier`);
    if (byId.has(checkId)) fail(`approval evidence contains duplicate check id: ${checkId}`);
    byId.set(checkId, check);
    if (check.status !== 'pass') fail(`approval evidence check ${checkId || index} must have status pass`);
  }
  for (const id of requiredIds) if (!byId.has(id)) fail(`approval evidence is missing required ${profile} check: ${id}`);
  for (const id of byId.keys()) if (!requiredIds.includes(id)) fail(`approval evidence contains unsupported ${profile} check: ${id}`);
  if (byId.size !== requiredIds.length) fail(`approval evidence ${profile} check set must contain exactly ${requiredIds.length} checks`);

  for (const id of requiredIds) {
    const check = byId.get(id);
    if (!check) continue;
    const result = check.result;
    const common = ['schema', 'command', 'exit_code', 'output_sha256'];
    const testKeys = [...common, 'test_plan', 'expected_tests', 'passed_tests', 'failed_tests', 'skipped_tests'];
    const validationKeys = [...common, 'mode', 'checked_items', 'error_count'];
    const allowed = id === 'governance-tests' || id === 'runtime-tests'
      ? testKeys
      : id === 'artifact-validation'
        ? [...common, 'content_digest']
        : id === 'commit-provenance'
          ? [...common, 'source_commit', 'selected_file_count', 'commit_bound_file_count', 'unbound_file_count', 'missing_commit_file_count']
          : id === 'tag-signature'
            ? [...common, 'tag_name', 'target_commit', 'tag_object_sha', 'signer_fingerprint', 'signature_status', ...(tagBinding ? [
              'annotation_schema', 'annotation_sha256', 'approval_binding_digest_algorithm', 'approval_binding_sha256',
              'approval_id', 'scope_kind', 'scope_id', 'version', 'candidate_content_digest',
            ] : [])]
            : validationKeys;
    exactKeys(result, allowed, `evidence check ${id}.result`);
    if (!result || typeof result !== 'object' || Array.isArray(result)) continue;
    if (result.schema !== 'release-check-result/v1') fail(`approval evidence check ${id} result.schema must be release-check-result/v1`);
    requiredString(result.command, `evidence check ${id}.result.command`);
    if (result.exit_code !== 0) fail(`approval evidence check ${id} result.exit_code must be 0`);
    hex(result.output_sha256, `evidence check ${id}.result.output_sha256`);

    if (id === 'governance-tests' || id === 'runtime-tests') {
      const plan = validateStringArray(result.test_plan, `evidence check ${id}.result.test_plan`);
      const expected = integerAtLeast(result.expected_tests, `evidence check ${id}.result.expected_tests`, 1);
      const passed = integerAtLeast(result.passed_tests, `evidence check ${id}.result.passed_tests`);
      const failed = integerAtLeast(result.failed_tests, `evidence check ${id}.result.failed_tests`);
      const skipped = integerAtLeast(result.skipped_tests, `evidence check ${id}.result.skipped_tests`);
      if (passed !== expected || failed !== 0 || skipped !== 0) fail(`approval evidence check ${id} must bind exact all-pass counts with no failed or skipped tests`);
      if (id === 'governance-tests') {
        if (JSON.stringify(plan) !== JSON.stringify(EXPECTED_GOVERNANCE_TEST_PLAN)) fail(`approval evidence governance-tests test_plan must exactly equal ${EXPECTED_GOVERNANCE_TEST_PLAN.join(', ')}`);
        if (expected !== governanceTestPlan.length) fail(`approval evidence governance-tests expected_tests must match the current registered governance plan (${governanceTestPlan.length})`);
      } else if (id === 'runtime-tests') {
        if (expected !== EXPECTED_RUNTIME_TEST_COUNT) fail(`approval evidence runtime-tests expected_tests must be ${EXPECTED_RUNTIME_TEST_COUNT}`);
        if (JSON.stringify(plan) !== JSON.stringify(EXPECTED_RUNTIME_TEST_PLAN)) fail(`approval evidence runtime-tests test_plan must exactly equal ${EXPECTED_RUNTIME_TEST_PLAN.join(', ')}`);
      }
      continue;
    }
    if (validationKeys.every((key) => allowed.includes(key))) {
      const expectedMode = id === 'index-validation' ? 'strict' : id === 'link-validation' || id === 'log-validation' || id === 'knowledge-chain-validation' || id.endsWith('structure-validation') ? 'release' : 'default';
      if (result.mode !== expectedMode) fail(`approval evidence check ${id} result.mode must be ${expectedMode}`);
      integerAtLeast(result.checked_items, `evidence check ${id}.result.checked_items`, 1);
      if (result.error_count !== 0) fail(`approval evidence check ${id} result.error_count must be 0`);
    } else if (id === 'artifact-validation') {
      if (result.content_digest !== contentDigest) fail('approval evidence artifact-validation content_digest must match candidate');
    } else if (id === 'commit-provenance') {
      if (result.source_commit !== sourceCommit) fail('approval evidence commit-provenance source_commit must match candidate');
      const selected = integerAtLeast(result.selected_file_count, 'evidence check commit-provenance.result.selected_file_count', 1);
      const bound = integerAtLeast(result.commit_bound_file_count, 'evidence check commit-provenance.result.commit_bound_file_count', 1);
      if (selected !== manifest.files?.length || bound !== selected) fail('approval evidence commit-provenance counts must bind every candidate file');
      if (result.unbound_file_count !== 0 || result.missing_commit_file_count !== 0) fail('approval evidence commit-provenance must report zero unbound and missing files');
    } else if (id === 'tag-signature') {
      if (result.tag_name !== tagName) fail('approval evidence tag-signature tag_name must match approval tag');
      if (result.target_commit !== sourceCommit) fail('approval evidence tag-signature target_commit must match candidate source commit');
      const evidenceTagObjectSha = hex(result.tag_object_sha, 'evidence check tag-signature.result.tag_object_sha', 40);
      const fingerprint = requiredString(result.signer_fingerprint, 'evidence check tag-signature.result.signer_fingerprint').toUpperCase();
      if (fingerprint && !/^[A-F0-9]{40}(?:[A-F0-9]{24})?$/.test(fingerprint)) fail('approval evidence tag-signature signer_fingerprint must be a full GPG fingerprint');
      if (result.signature_status !== 'trusted') fail('approval evidence tag-signature signature_status must be trusted');
      if (tagBinding) {
        if (evidenceTagObjectSha !== tagBinding.tagObjectSha) fail('approval evidence tag-signature tag_object_sha must match the actual and approved tag object');
        if (fingerprint !== tagBinding.signerFingerprint) fail('approval evidence tag-signature signer_fingerprint must match the actual and approved signer');
        if (result.annotation_schema !== TAG_ANNOTATION_SCHEMA) fail(`approval evidence tag-signature annotation_schema must be ${TAG_ANNOTATION_SCHEMA}`);
        if (result.annotation_sha256 !== tagBinding.annotationSha256) fail('approval evidence tag-signature annotation_sha256 must match the actual canonical tag annotation');
        if (result.approval_binding_digest_algorithm !== APPROVAL_BINDING_ALGORITHM) fail(`approval evidence tag-signature approval_binding_digest_algorithm must be ${APPROVAL_BINDING_ALGORITHM}`);
        if (result.approval_binding_sha256 !== tagBinding.approvalBindingSha256) fail('approval evidence tag-signature approval_binding_sha256 must match the canonical approval binding');
        if (result.approval_id !== tagBinding.annotation.approval_id) fail('approval evidence tag-signature approval_id must match the canonical tag annotation');
        if (result.scope_kind !== tagBinding.annotation.scope?.kind || result.scope_id !== tagBinding.annotation.scope?.id) fail('approval evidence tag-signature scope must match the canonical tag annotation');
        if (result.version !== tagBinding.annotation.version) fail('approval evidence tag-signature version must match the canonical tag annotation');
        if (result.candidate_content_digest !== tagBinding.annotation.candidate_content_digest) fail('approval evidence tag-signature candidate_content_digest must match the canonical tag annotation');
      }
    }
  }
}

function portableRelativePath(value, field) {
  if (typeof value !== 'string' || !value) {
    fail(`approval ${field} must be a non-empty portable relative path`);
    return '';
  }
  if (value.includes('\\') || value.startsWith('/') || /^[A-Za-z]:/.test(value)) {
    fail(`approval ${field} must be a portable relative path`);
    return '';
  }
  const segments = value.split('/');
  if (segments.some((segment) => !segment || segment === '.' || segment === '..')) {
    fail(`approval ${field} must not contain empty or dot path segments`);
    return '';
  }
  return value;
}
function displaySourceClearanceValue(front, field) {
  return front && Object.hasOwn(front, field) ? JSON.stringify(front[field]) : 'missing';
}
function validateCandidateSourceCardField(front, path, field, allowed) {
  const value = front && Object.hasOwn(front, field) ? front[field] : undefined;
  if (typeof value !== 'string' || !allowed.has(value)) {
    fail(`source card ${path} ${field} must be one of ${JSON.stringify([...allowed])}; got ${displaySourceClearanceValue(front, field)}`);
    return false;
  }
  return true;
}
function validateCandidateSourcePublicationClearance(manifest, root) {
  if (!Array.isArray(manifest.files)) return;
  for (const [index, value] of manifest.files.entries()) {
    if (typeof value !== 'string' || !value.toLowerCase().endsWith('.md')) continue;
    const path = portableRelativePath(value, `candidate.files[${index}]`);
    if (!path) continue;
    const isReferenceMarkdown = referenceMarkdownPathPattern.test(path);
    const isReferenceIndex = path === 'REFERENCES/README.md';
    const isSourceCardPath = sourceCardPathPattern.test(path);
    const sourcePath = resolve(root, path);
    if (!existsSync(sourcePath) || !statSync(sourcePath).isFile()) {
      if (isReferenceMarkdown || isSourceCardPath) fail(`source publication clearance file is missing from frozen candidate: ${path}`);
      continue;
    }
    let front;
    try {
      front = parseMarkdownFrontMatter(readFileSync(sourcePath, 'utf8'), { source: path }).attributes;
    } catch (error) {
      if (isReferenceMarkdown || isSourceCardPath) fail(`source publication clearance front matter is invalid for ${path}: ${error.message}`);
      continue;
    }
    const hasRelocatedSourceIdentity = front.type === 'source-note'
      || Object.hasOwn(front, 'publication_review_status');

    if (isReferenceMarkdown && !isReferenceIndex && !isSourceCardPath) {
      fail(`reference Markdown path must match REFERENCES/SRC-*.md or be REFERENCES/README.md: ${path}`);
    }
    if (!isSourceCardPath) {
      if (!isReferenceMarkdown && hasRelocatedSourceIdentity) {
        fail(`source card metadata must remain under REFERENCES/SRC-*.md: ${path}`);
      }
      continue;
    }

    let identityValid = true;
    if (front.type !== 'source-note') {
      fail(`source card ${path} type must be exactly "source-note"; got ${displaySourceClearanceValue(front, 'type')}`);
      identityValid = false;
    }
    identityValid = validateCandidateSourceCardField(front, path, 'publication_review_status', allowedSourcePublicationReviewStatuses) && identityValid;
    identityValid = validateCandidateSourceCardField(front, path, 'publication_status', allowedSourcePublicationStatuses) && identityValid;
    identityValid = validateCandidateSourceCardField(front, path, 'license_status', allowedSourceLicenseStatuses) && identityValid;
    if (!identityValid) continue;

    const cleared = front.publication_review_status === 'approved'
      && front.publication_status === 'PASS'
      && front.license_status === 'cleared';
    if (cleared) continue;
    fail(`source publication clearance BLOCK for ${path}: expected publication_review_status="approved", publication_status="PASS", license_status="cleared"; got publication_review_status=${displaySourceClearanceValue(front, 'publication_review_status')}, publication_status=${displaySourceClearanceValue(front, 'publication_status')}, license_status=${displaySourceClearanceValue(front, 'license_status')}; candidate package license_status cannot override source-level clearance`);
  }
}
function validateCommitProvenance(manifest, root, sourceCommit) {
  const scopeLabel = manifest.release_scope === 'standalone-mother-library' ? 'mother-library' : 'sub-library';
  if (!['standalone-mother-library', 'standalone-sub-library'].includes(manifest.release_scope)) return [];
  if (manifest.source_selected_dirty !== false) fail(`candidate source_selected_dirty must be false for ${scopeLabel} approval`);
  if (manifest.source_commit_rebuildable !== true) fail(`candidate source_commit_rebuildable must be true for ${scopeLabel} approval`);
  if (manifest.source_snapshot_kind !== 'source-commit') fail(`candidate source_snapshot_kind must be source-commit for ${scopeLabel} approval`);
  const sourceScope = manifest.source_scope;
  if (manifest.release_scope === 'standalone-mother-library') {
    if (sourceScope !== 'repository-root') fail('candidate source_scope must be repository-root for commit-bound approval');
  } else {
    if (sourceScope !== 'repository-root') portableRelativePath(sourceScope, 'candidate.source_scope');
  }

  const provenance = manifest.source_provenance ?? {};
  if (!provenance || typeof provenance !== 'object' || Array.isArray(provenance)) {
    fail('candidate source_provenance must be an object for commit-bound approval');
    return [];
  }
  if (provenance.schema !== 'git-file-provenance/v1') fail('candidate source_provenance.schema must be git-file-provenance/v1');
  if (provenance.source_commit !== sourceCommit) fail('candidate source_provenance.source_commit must match candidate source_commit');
  if (provenance.commit_rebuildable !== true) fail('candidate source_provenance.commit_rebuildable must be true');
  if (!Array.isArray(provenance.unbound_files) || provenance.unbound_files.length !== 0) fail('candidate source_provenance.unbound_files must be an empty array');
  if (!Array.isArray(provenance.missing_commit_files) || provenance.missing_commit_files.length !== 0) fail('candidate source_provenance.missing_commit_files must be an empty array');

  const candidateFiles = Array.isArray(manifest.files) ? manifest.files : [];
  if (!Array.isArray(manifest.files)) fail('candidate files must be an array before commit provenance can be approved');
  const expectedPaths = new Set();
  for (const [index, value] of candidateFiles.entries()) {
    const path = portableRelativePath(value, `candidate.files[${index}]`);
    if (!path) continue;
    if (expectedPaths.has(path)) fail(`candidate files contains duplicate path: ${path}`);
    expectedPaths.add(path);
  }

  if (!Array.isArray(provenance.files)) {
    fail('candidate source_provenance.files must be an array');
    return [];
  }
  if (provenance.selected_file_count !== candidateFiles.length) fail('candidate source_provenance.selected_file_count must equal candidate files length');
  if (provenance.commit_bound_file_count !== candidateFiles.length) fail('candidate source_provenance.commit_bound_file_count must equal candidate files length');
  if (provenance.files.length !== candidateFiles.length) fail('candidate source_provenance.files must cover every candidate source file exactly once');

  const records = [];
  const seen = new Set();
  for (const [index, record] of provenance.files.entries()) {
    if (!record || typeof record !== 'object' || Array.isArray(record)) {
      fail(`candidate source_provenance.files[${index}] must be an object`);
      continue;
    }
    const path = portableRelativePath(record.path, `source_provenance.files[${index}].path`);
    if (!path) continue;
    if (seen.has(path)) fail(`candidate source_provenance contains duplicate path: ${path}`);
    seen.add(path);
    if (!expectedPaths.has(path)) fail(`candidate source_provenance contains a path outside candidate files: ${path}`);
    const expectedRepositoryPath = manifest.source_scope === 'repository-root' ? path : `${manifest.source_scope}/${path}`;
    if (manifest.release_scope === 'standalone-sub-library') {
      const repositoryPath = portableRelativePath(record.repository_path, `source_provenance.files[${index}].repository_path`);
      if (repositoryPath !== expectedRepositoryPath) fail(`candidate source_provenance file ${path} repository_path must be ${expectedRepositoryPath}`);
    } else if (record.repository_path !== undefined && record.repository_path !== expectedRepositoryPath) {
      fail(`candidate source_provenance file ${path} repository_path must be ${expectedRepositoryPath}`);
    }
    if (record.git_state !== 'committed') fail(`candidate source_provenance file ${path} must have git_state committed`);
    if (record.commit_bound !== true) fail(`candidate source_provenance file ${path} must have commit_bound true`);
    if (typeof record.commit_blob !== 'string' || !/^[a-f0-9]{40}$/.test(record.commit_blob)) fail(`candidate source_provenance file ${path} must contain a 40-character lowercase commit_blob`);
    if (typeof record.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(record.sha256)) fail(`candidate source_provenance file ${path} must contain a lowercase SHA-256`);
    if (typeof record.commit_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(record.commit_sha256)) fail(`candidate source_provenance file ${path} must contain a lowercase commit_sha256`);
    if (record.sha256 !== record.commit_sha256) fail(`candidate source_provenance file ${path} does not bind identical candidate and commit content`);
    const artifactPath = resolve(root, path);
    if (!existsSync(artifactPath) || !statSync(artifactPath).isFile()) fail(`candidate source_provenance file is missing from artifact: ${path}`);
    else if (record.sha256 !== sha256(artifactPath)) fail(`candidate source_provenance file ${path} SHA-256 does not match artifact content`);
    records.push(record);
  }
  for (const path of expectedPaths) {
    if (!seen.has(path)) fail(`candidate source_provenance is missing candidate file: ${path}`);
  }
  return records;
}
function isoTimestamp(value, field) {
  const text = requiredString(value, field);
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed) || !text.endsWith('Z')) fail(`approval ${field} must be an ISO-8601 UTC timestamp ending in Z`);
  if (Number.isFinite(parsed) && parsed > Date.now() + 60_000) fail(`approval ${field} cannot be in the future`);
}
function expectedTagNamespace(manifest) {
  if (manifest.release_scope === 'standalone-mother-library') return 'mother';
  if (manifest.release_scope === 'standalone-sub-library' && manifest.package_id) return `sub-library/${manifest.package_id}`;
  return null;
}
function ipv4Bytes(address) {
  const parts = address.split('.');
  if (parts.length !== 4 || parts.some((part) => !/^\d{1,3}$/.test(part) || Number(part) > 255)) return null;
  return parts.map(Number);
}
function ipv6Bytes(address) {
  let value = address.toLowerCase();
  if (value.startsWith('[') && value.endsWith(']')) value = value.slice(1, -1);
  const zone = value.indexOf('%');
  if (zone >= 0) value = value.slice(0, zone);
  if (value.includes('.')) {
    const lastColon = value.lastIndexOf(':');
    const tail = ipv4Bytes(value.slice(lastColon + 1));
    if (!tail) return null;
    value = `${value.slice(0, lastColon)}:${((tail[0] << 8) | tail[1]).toString(16)}:${((tail[2] << 8) | tail[3]).toString(16)}`;
  }
  const halves = value.split('::');
  if (halves.length > 2) return null;
  const left = halves[0] ? halves[0].split(':') : [];
  const right = halves.length === 2 && halves[1] ? halves[1].split(':') : [];
  if ([...left, ...right].some((part) => !/^[a-f0-9]{1,4}$/.test(part))) return null;
  const missing = 8 - left.length - right.length;
  if ((halves.length === 1 && missing !== 0) || (halves.length === 2 && missing < 1)) return null;
  const groups = [...left, ...Array(missing).fill('0'), ...right].map((part) => Number.parseInt(part, 16));
  if (groups.length !== 8) return null;
  return groups.flatMap((group) => [group >> 8, group & 0xff]);
}
function isUnsafeIpv4(bytes) {
  const [a, b] = bytes;
  return a === 0
    || a === 10
    || (a === 100 && b >= 64 && b <= 127)
    || a === 127
    || (a === 169 && b === 254)
    || (a === 172 && b >= 16 && b <= 31)
    || (a === 192 && b === 168);
}
function isUnsafeHost(hostname) {
  const host = hostname.replace(/^\[|\]$/g, '').replace(/\.$/, '').toLowerCase();
  const ipVersion = isIP(host);
  if (ipVersion === 4) return isUnsafeIpv4(ipv4Bytes(host));
  if (ipVersion === 6) {
    const bytes = ipv6Bytes(host);
    if (!bytes) return true;
    const unspecified = bytes.every((byte) => byte === 0);
    const loopback = bytes.slice(0, 15).every((byte) => byte === 0) && bytes[15] === 1;
    const uniqueLocal = (bytes[0] & 0xfe) === 0xfc;
    const linkOrSiteLocal = bytes[0] === 0xfe && (bytes[1] & 0x80) === 0x80;
    const mappedIpv4 = bytes.slice(0, 10).every((byte) => byte === 0) && bytes[10] === 0xff && bytes[11] === 0xff;
    const compatibleIpv4 = bytes.slice(0, 12).every((byte) => byte === 0);
    return unspecified || loopback || uniqueLocal || linkOrSiteLocal
      || ((mappedIpv4 || compatibleIpv4) && isUnsafeIpv4(bytes.slice(12)));
  }
  return !host.includes('.')
    || host === 'localhost'
    || host.endsWith('.localhost')
    || ['.local', '.internal', '.home', '.home.arpa', '.lan'].some((suffix) => host.endsWith(suffix));
}
function decodePathFailClosed(rawPath) {
  let current = rawPath;
  for (let depth = 0; depth < 4; depth += 1) {
    if (/%(?![a-f0-9]{2})/i.test(current)) return { error: 'contains malformed percent encoding' };
    if (current.split('/').some((segment) => segment === '.' || segment === '..')) return { error: 'must not contain dot path segments' };
    let decoded;
    try { decoded = decodeURIComponent(current); } catch { return { error: 'contains malformed percent encoding' }; }
    if (decoded === current) return { path: current };
    current = decoded;
  }
  if (current.includes('%')) return { error: 'contains excessive or ambiguous percent encoding' };
  if (current.split('/').some((segment) => segment === '.' || segment === '..')) return { error: 'must not contain dot path segments' };
  return { path: current };
}
function validateImmutableLocator(locator, version, contentDigest) {
  const prefix = 'approval candidate.immutable_locator';
  let parsed;
  try { parsed = new URL(locator); } catch { fail(`${prefix} must be an absolute HTTPS URL`); return; }
  if (parsed.protocol !== 'https:') { fail(`${prefix} must use https`); return; }
  if (locator.includes('\\')) fail(`${prefix} must not contain backslashes`);
  if (parsed.username || parsed.password) fail(`${prefix} must not contain URL credentials`);
  if (locator.includes('?') || locator.includes('#')) fail(`${prefix} must not contain query or fragment`);
  if (isUnsafeHost(parsed.hostname)) fail(`${prefix} must not target a local, private, loopback, or link-local host`);

  const authorityStart = locator.indexOf('://') + 3;
  const pathStart = locator.indexOf('/', authorityStart);
  const rawPath = pathStart >= 0 ? locator.slice(pathStart) : '/';
  const decoded = decodePathFailClosed(rawPath);
  if (decoded.error) { fail(`${prefix} ${decoded.error}`); return; }

  const markerTokens = `${parsed.hostname}/${decoded.path}`.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  const forbiddenMarkers = new Set([
    'latest', 'tmp', 'temp',
    'credential', 'credentials', 'cookie', 'cookies', 'token', 'tokens',
    'secret', 'secrets', 'password', 'passwords', 'passwd', 'pwd',
    'auth', 'authorization', 'bearer', 'session',
  ]);
  if (markerTokens.some((token) => forbiddenMarkers.has(token))) fail(`${prefix} contains a forbidden mutable or credential marker`);

  const pathSegments = decoded.path.split('/').filter(Boolean);
  const versionText = typeof version === 'string' ? version.trim() : '';
  if (!versionText || (!pathSegments.includes(versionText) && !pathSegments.includes(`v${versionText}`))) {
    fail(`${prefix} path must contain candidate version as a complete segment`);
  }
  if (!contentDigest || !pathSegments.includes(contentDigest)) {
    fail(`${prefix} path must contain candidate content_digest as a complete segment`);
  }
}

if (!candidateRoot || !existsSync(candidateRoot) || !statSync(candidateRoot).isDirectory()) fail(`candidate root does not exist or is not a directory: ${candidateRoot}`);
if (!approvalPath || !existsSync(approvalPath) || !statSync(approvalPath).isFile()) fail(`approval record does not exist: ${approvalPath}`);
let manifest;
let approval;
try { manifest = JSON.parse(readFileSync(resolve(candidateRoot, 'MANIFEST.json'), 'utf8')); } catch { fail('candidate MANIFEST.json is missing or invalid JSON'); manifest = {}; }
try { approval = JSON.parse(readFileSync(approvalPath, 'utf8')); } catch { fail('approval record is not valid JSON'); approval = {}; }
const currentCandidateVersion = validateFrozenManifestIdentity(manifest);

if (approval.schema !== 'release-approval/v1') fail(`approval schema must be release-approval/v1, got ${approval.schema ?? 'missing'}`);
const approvalId = requiredString(approval.approval_id, 'approval_id');
if (approvalId && !/^APR-[A-Z0-9-]+$/.test(approvalId)) fail('approval approval_id must use APR-... format');
if (approval.decision !== 'approved') fail(`approval decision must be approved, got ${approval.decision ?? 'missing'}`);
const scope = approval.scope ?? {};
if (!scope || typeof scope !== 'object' || Array.isArray(scope)) fail('approval scope must be an object');
const scopeKind = requiredString(scope.kind, 'scope.kind');
const scopeId = requiredString(scope.id, 'scope.id');
const scopePackageKind = requiredString(scope.package_kind, 'scope.package_kind');
const expectedScopeKind = manifest.release_scope === 'standalone-mother-library'
  ? 'mother-library'
  : manifest.release_scope === 'standalone-sub-library'
    ? 'sub-library'
    : '';
const expectedPackageKind = expectedScopeKind === 'mother-library'
  ? 'mother-library-release-candidate'
  : expectedScopeKind === 'sub-library'
    ? 'sub-library-release-candidate'
    : '';
if (!expectedScopeKind) fail(`candidate release_scope is unsupported: ${manifest.release_scope ?? 'missing'}`);
if (scopeKind !== expectedScopeKind) fail(`approval scope.kind ${scopeKind} does not match candidate ${expectedScopeKind || 'supported scope'}`);
if (scopeId !== manifest.package_id) fail(`approval scope.id ${scopeId} does not match candidate ${manifest.package_id ?? 'missing'}`);
if (scopePackageKind !== expectedPackageKind) fail(`approval scope.package_kind ${scopePackageKind} does not match candidate ${expectedPackageKind}`);

const source = approval.source ?? {};
if (!source || typeof source !== 'object' || Array.isArray(source)) fail('approval source must be an object');
const sourceCommit = requiredString(source.commit, 'source.commit');
if (sourceCommit && !/^[a-f0-9]{40}$/.test(sourceCommit)) fail('approval source.commit must be a 40-character lowercase Git SHA');
if (source.dirty !== false) fail('approval source.dirty must be false');
if (sourceCommit !== manifest.source_commit) fail('approval source.commit does not match candidate MANIFEST.json');
if (manifest.source_dirty !== false) fail('candidate source_dirty must be false; approval cannot bless a dirty source snapshot');
const provenanceRecords = validateCommitProvenance(manifest, candidateRoot, sourceCommit);
validateCandidateSourcePublicationClearance(manifest, candidateRoot);

const candidate = approval.candidate ?? {};
if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) fail('approval candidate must be an object');
const contentDigest = hex(candidate.content_digest, 'candidate.content_digest');
const manifestSha = hex(candidate.manifest_sha256, 'candidate.manifest_sha256');
const sumsSha = hex(candidate.sha256sums_sha256, 'candidate.sha256sums_sha256');
if (contentDigest !== manifest.content_digest) fail('approval candidate.content_digest does not match candidate MANIFEST.json');
const manifestPath = resolve(candidateRoot, 'MANIFEST.json');
const sumsPath = resolve(candidateRoot, 'SHA256SUMS');
if (!existsSync(manifestPath) || !existsSync(sumsPath)) fail('candidate must contain MANIFEST.json and SHA256SUMS');
else {
  if (manifestSha !== sha256(manifestPath)) fail('approval candidate.manifest_sha256 does not match candidate MANIFEST.json');
  if (sumsSha !== sha256(sumsPath)) fail('approval candidate.sha256sums_sha256 does not match candidate SHA256SUMS');
}
const locator = requiredString(candidate.immutable_locator, 'candidate.immutable_locator');
if (locator) validateImmutableLocator(locator, currentCandidateVersion, contentDigest);

const validation = approval.validation ?? {};
if (!validation || typeof validation !== 'object' || Array.isArray(validation)) fail('approval validation must be an object');
const profile = requiredString(validation.profile, 'validation.profile');
const expectedProfile = expectedScopeKind === 'mother-library'
  ? 'mother-release-v1'
  : expectedScopeKind === 'sub-library'
    ? 'sub-library-release-v1'
    : '';
if (profile !== expectedProfile) fail(`approval validation.profile must be ${expectedProfile}`);
const evidenceDigestAlgorithm = requiredString(validation.evidence_digest_algorithm, 'validation.evidence_digest_algorithm');
if (evidenceDigestAlgorithm !== 'sha256-canonical-json-v1') fail('approval validation.evidence_digest_algorithm must be sha256-canonical-json-v1');
const evidenceDigest = hex(validation.evidence_digest, 'validation.evidence_digest');
const evidenceReference = requiredString(validation.evidence_bundle, 'validation.evidence_bundle');
if (evidenceReference && !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(evidenceReference)) fail('approval validation.evidence_bundle must be a portable filename without path separators');
isoTimestamp(validation.completed_at, 'validation.completed_at');

const evidenceOverride = process.argv[4]?.trim() || process.env.RELEASE_EVIDENCE_PATH?.trim() || '';
const evidencePath = evidenceOverride ? resolve(evidenceOverride) : resolve(dirname(approvalPath), evidenceReference || '');
let evidence = {};
if (!evidenceReference) {
  fail('approval validation.evidence_bundle is required');
} else if (evidenceOverride && basename(evidencePath) !== evidenceReference) {
  fail(`approval validation.evidence_bundle ${evidenceReference} does not match supplied evidence filename ${basename(evidencePath)}`);
} else if (!evidencePath || !existsSync(evidencePath) || !statSync(evidencePath).isFile()) {
  fail(`approval evidence bundle does not exist: ${evidencePath}`);
} else {
  try { evidence = JSON.parse(readFileSync(evidencePath, 'utf8')); } catch { fail('approval evidence bundle is not valid JSON'); }
}
if (evidence.schema !== 'release-evidence/v1') fail(`approval evidence schema must be release-evidence/v1, got ${evidence.schema ?? 'missing'}`);
if (evidence.profile !== expectedProfile) fail(`approval evidence profile must be ${expectedProfile}`);
const evidenceScope = evidence.scope ?? {};
if (!evidenceScope || typeof evidenceScope !== 'object' || Array.isArray(evidenceScope)) fail('approval evidence scope must be an object');
if (evidenceScope.kind !== expectedScopeKind) fail('approval evidence scope.kind does not match candidate scope');
if (evidenceScope.id !== manifest.package_id) fail('approval evidence scope.id does not match candidate package_id');
if (evidenceScope.package_kind !== expectedPackageKind) fail('approval evidence scope.package_kind does not match candidate package_kind');
const evidenceSource = evidence.source ?? {};
if (!evidenceSource || typeof evidenceSource !== 'object' || Array.isArray(evidenceSource)) fail('approval evidence source must be an object');
if (evidenceSource.commit !== sourceCommit) fail('approval evidence source.commit does not match candidate source commit');
if (evidenceSource.dirty !== false) fail('approval evidence source.dirty must be false');
const evidenceCandidate = evidence.candidate ?? {};
if (!evidenceCandidate || typeof evidenceCandidate !== 'object' || Array.isArray(evidenceCandidate)) fail('approval evidence candidate must be an object');
if (evidenceCandidate.content_digest !== contentDigest) fail('approval evidence candidate.content_digest does not match candidate');
if (evidenceCandidate.manifest_sha256 !== manifestSha) fail('approval evidence candidate.manifest_sha256 does not match approval candidate');
if (evidenceCandidate.sha256sums_sha256 !== sumsSha) fail('approval evidence candidate.sha256sums_sha256 does not match approval candidate');
isoTimestamp(evidence.completed_at, 'evidence.completed_at');
if (evidence.completed_at !== validation.completed_at) fail('approval evidence completed_at must equal validation.completed_at');
const humanApproval = approval.approval ?? {};
if (!humanApproval || typeof humanApproval !== 'object' || Array.isArray(humanApproval)) fail('approval approval must be an object');
const approver = requiredString(humanApproval.approved_by, 'approval.approved_by');
const aiOrSystemIdentityToken = /\b(ai|assistant|agent|bot|codex|claude|system|unknown)\b/i;
if (aiOrSystemIdentityToken.test(approver)) fail('approval approved_by must not contain an AI/system identity token');
isoTimestamp(humanApproval.approved_at, 'approval.approved_at');
requiredString(humanApproval.basis_ref, 'approval.basis_ref');

const tag = approval.tag ?? {};
if (!tag || typeof tag !== 'object' || Array.isArray(tag)) fail('approval tag must be an object');
const namespace = expectedTagNamespace(manifest);
const tagName = requiredString(tag.name, 'tag.name');
const triggerTag = process.env.RELEASE_TRIGGER_TAG?.trim() ?? '';
const strictGitTag = process.env.RELEASE_REQUIRE_GIT_TAG === '1';
if (strictGitTag && !triggerTag) fail('RELEASE_TRIGGER_TAG is required when strict Git tag verification is enabled');
if (triggerTag && triggerTag !== tagName) fail(`RELEASE_TRIGGER_TAG ${triggerTag} does not match approval tag.name ${tagName}`);
const targetCommit = requiredString(tag.target_commit, 'tag.target_commit');
if (targetCommit !== sourceCommit) fail('approval tag.target_commit must equal approval source.commit');
if (namespace && tagName !== `${namespace}/v${currentCandidateVersion}`) fail(`approval tag.name must be ${namespace}/v${currentCandidateVersion}`);
if (manifest.tag_namespace !== namespace) fail(`candidate tag_namespace must be ${namespace}, got ${manifest.tag_namespace ?? 'missing'}`);
if (manifest.qualification_state !== 'prepared-unapproved') fail(`candidate qualification_state must be prepared-unapproved, got ${manifest.qualification_state ?? 'missing'}`);
if (manifest.approval_status !== 'pending') fail(`frozen candidate approval_status must remain pending; external approval must not rewrite candidate bytes, got ${manifest.approval_status ?? 'missing'}`);
if (manifest.release_status !== 'Ready') fail(`frozen candidate release_status must be Ready, got ${manifest.release_status ?? 'missing'}`);
if (manifest.license_status !== 'cleared') fail(`candidate license_status must be cleared, got ${manifest.license_status ?? 'missing'}`);
if (manifest.verification_status !== 'e2e-pass') fail(`candidate verification_status must be e2e-pass, got ${manifest.verification_status ?? 'missing'}`);

const actualEnv = {
  tagObjectSha: process.env.RELEASE_ACTUAL_TAG_OBJECT_SHA?.trim() ?? '',
  signerFingerprint: (process.env.RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT?.trim() ?? '').toUpperCase(),
  annotationSha256: process.env.RELEASE_ACTUAL_TAG_ANNOTATION_SHA256?.trim() ?? '',
  approvalBindingSha256: process.env.RELEASE_ACTUAL_APPROVAL_BINDING_SHA256?.trim() ?? '',
  annotationBase64: process.env.RELEASE_ACTUAL_TAG_ANNOTATION_BASE64?.trim() ?? '',
};
const canonicalTagFields = ['object_sha', 'signer_fingerprint', 'annotation_schema', 'annotation_sha256', 'approval_binding_digest_algorithm', 'approval_binding_sha256'];
const formalTagBindingRequired = strictGitTag
  || Object.values(actualEnv).some(Boolean)
  || canonicalTagFields.some((key) => Object.prototype.hasOwnProperty.call(tag, key));
let tagBinding = null;
if (formalTagBindingRequired) {
  const approvedTagObjectSha = hex(tag.object_sha, 'tag.object_sha', 40);
  const approvedSignerFingerprint = requiredString(tag.signer_fingerprint, 'tag.signer_fingerprint').toUpperCase();
  if (approvedSignerFingerprint && !/^[A-F0-9]{40}(?:[A-F0-9]{24})?$/.test(approvedSignerFingerprint)) fail('approval tag.signer_fingerprint must be a full GPG fingerprint');
  if (tag.annotation_schema !== TAG_ANNOTATION_SCHEMA) fail(`approval tag.annotation_schema must be ${TAG_ANNOTATION_SCHEMA}`);
  const approvedAnnotationSha256 = hex(tag.annotation_sha256, 'tag.annotation_sha256');
  if (tag.approval_binding_digest_algorithm !== APPROVAL_BINDING_ALGORITHM) fail(`approval tag.approval_binding_digest_algorithm must be ${APPROVAL_BINDING_ALGORITHM}`);
  const approvedBindingSha256 = hex(tag.approval_binding_sha256, 'tag.approval_binding_sha256');
  const computedBindingSha256 = canonicalDigest(approvalBindingProjection(approval), 'approval binding projection');
  if (approvedBindingSha256 !== computedBindingSha256) fail('approval tag.approval_binding_sha256 does not match the canonical approval binding projection');
  const expectedAnnotation = expectedTagAnnotation(approval, manifest, computedBindingSha256, currentCandidateVersion);
  const expectedAnnotationText = canonicalJson(expectedAnnotation, 'expected tag annotation');
  const expectedAnnotationSha256 = createHash('sha256').update(expectedAnnotationText, 'utf8').digest('hex');
  if (approvedAnnotationSha256 !== expectedAnnotationSha256) fail('approval tag.annotation_sha256 does not match the canonical tag annotation');

  for (const [field, value, pattern] of [
    ['RELEASE_ACTUAL_TAG_OBJECT_SHA', actualEnv.tagObjectSha, /^[a-f0-9]{40}$/],
    ['RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT', actualEnv.signerFingerprint, /^[A-F0-9]{40}(?:[A-F0-9]{24})?$/],
    ['RELEASE_ACTUAL_TAG_ANNOTATION_SHA256', actualEnv.annotationSha256, /^[a-f0-9]{64}$/],
    ['RELEASE_ACTUAL_APPROVAL_BINDING_SHA256', actualEnv.approvalBindingSha256, /^[a-f0-9]{64}$/],
  ]) {
    if (!value) fail(`${field} is required for formal canonical tag binding`);
    else if (!pattern.test(value)) fail(`${field} has an invalid format`);
  }
  const actualAnnotationText = decodeCanonicalBase64(actualEnv.annotationBase64, 'RELEASE_ACTUAL_TAG_ANNOTATION_BASE64');
  const actualAnnotation = parseCanonicalTagAnnotation(actualAnnotationText, 'actual release tag annotation');
  if (actualAnnotationText !== expectedAnnotationText) fail('actual release tag annotation does not exactly match the approval, scope, version, and candidate digest');
  if (actualEnv.annotationSha256 !== expectedAnnotationSha256) fail('RELEASE_ACTUAL_TAG_ANNOTATION_SHA256 does not match the canonical annotation bytes');
  if (actualEnv.approvalBindingSha256 !== computedBindingSha256) fail('RELEASE_ACTUAL_APPROVAL_BINDING_SHA256 does not match the canonical approval binding');
  if (actualEnv.tagObjectSha !== approvedTagObjectSha) fail('actual tag object SHA does not match approval tag.object_sha');
  if (actualEnv.signerFingerprint !== approvedSignerFingerprint) fail('actual tag signer does not match approval tag.signer_fingerprint');

  tagBinding = {
    annotation: actualAnnotation,
    annotationSha256: expectedAnnotationSha256,
    approvalBindingSha256: computedBindingSha256,
    tagObjectSha: approvedTagObjectSha,
    signerFingerprint: approvedSignerFingerprint,
  };
}

if (strictGitTag) {
  const sourceRoot = process.env.RELEASE_SOURCE_ROOT ? resolve(process.env.RELEASE_SOURCE_ROOT) : '';
  if (!sourceRoot || !existsSync(sourceRoot) || !statSync(sourceRoot).isDirectory()) {
    fail('strict tag verification requires RELEASE_SOURCE_ROOT pointing to the clean Git checkout');
  } else {
    const gitText = (args) => {
      const result = spawnSync('git', args, { cwd: sourceRoot, encoding: 'utf8' });
      return result.status === 0 ? result.stdout : '';
    };
    const gitTrimmed = (args) => gitText(args).trim();
    const tagRef = `refs/tags/${tagName}`;
    const tagObjectType = gitTrimmed(['cat-file', '-t', tagRef]);
    const actualTagObjectSha = gitTrimmed(['rev-parse', '--verify', tagRef]);
    const resolvedTagCommit = gitTrimmed(['rev-parse', '--verify', `${tagRef}^{commit}`]);
    if (tagObjectType !== 'tag') fail(`Git tag ${tagName} must exist as an annotated tag; got ${tagObjectType || 'missing'}`);
    if (resolvedTagCommit !== sourceCommit) fail(`Git tag ${tagName} resolves to ${resolvedTagCommit || 'missing'}, expected ${sourceCommit}`);
    if (actualTagObjectSha !== actualEnv.tagObjectSha) fail('workflow-reported tag object SHA does not match the Git tag object');
    const rawTagObject = gitText(['cat-file', 'tag', tagRef]);
    const gitAnnotationText = annotationFromTagObject(rawTagObject, `Git tag ${tagName}`);
    if (gitAnnotationText && Buffer.from(gitAnnotationText, 'utf8').toString('base64') !== actualEnv.annotationBase64) fail('workflow-reported tag annotation does not match the Git tag object message');
    if (gitAnnotationText && createHash('sha256').update(gitAnnotationText, 'utf8').digest('hex') !== actualEnv.annotationSha256) fail('workflow-reported tag annotation digest does not match the Git tag object message');
    const verification = spawnSync('git', ['verify-tag', '--raw', tagRef], { cwd: sourceRoot, encoding: 'utf8' });
    const verifyOutput = `${verification.stdout ?? ''}\n${verification.stderr ?? ''}`;
    const signerMatch = verifyOutput.match(/\[GNUPG:\] VALIDSIG ([A-Fa-f0-9]{40}(?:[A-Fa-f0-9]{24})?)/);
    const gitSignerFingerprint = signerMatch?.[1]?.toUpperCase() ?? '';
    if (verification.status !== 0 || !gitSignerFingerprint) fail(`Git tag ${tagName} signature verification did not produce a valid signer fingerprint`);
    else if (gitSignerFingerprint !== actualEnv.signerFingerprint) fail('workflow-reported signer fingerprint does not match git verify-tag output');
    for (const record of provenanceRecords) {
      const repositoryPath = manifest.source_scope === 'repository-root' ? record.path : `${manifest.source_scope}/${record.path}`;
      const treeLine = gitTrimmed(['ls-tree', sourceCommit, '--', repositoryPath]);
      const treeMatch = treeLine.match(/^([0-7]{6})\s+blob\s+([a-f0-9]{40})\t(.+)$/);
      if (!treeMatch || treeMatch[3] !== repositoryPath) {
        fail(`source commit does not contain approved ${expectedScopeKind} file: ${repositoryPath}`);
        continue;
      }
      if (treeMatch[2] !== record.commit_blob) fail(`candidate source_provenance file ${record.path} commit_blob does not match source commit tree`);
      const blob = spawnSync('git', ['cat-file', 'blob', treeMatch[2]], { cwd: sourceRoot });
      if (blob.status !== 0) fail(`could not read source commit blob for approved file: ${repositoryPath}`);
      else if (createHash('sha256').update(blob.stdout).digest('hex') !== record.commit_sha256) fail(`candidate source_provenance file ${record.path} commit_sha256 does not match source commit blob`);
    }
  }
}

const governanceTestPlan = currentGovernanceTestPlan(candidateRoot);
validateEvidenceChecks(
  evidence.checks,
  expectedProfile,
  manifest,
  sourceCommit,
  contentDigest,
  `${expectedTagNamespace(manifest)}/v${currentCandidateVersion}`,
  governanceTestPlan,
  tagBinding,
);
if (evidenceDigest && evidenceDigest !== canonicalEvidenceDigest(evidence)) {
  fail('approval validation.evidence_digest does not match the canonical evidence bundle content');
}

console.log(`Candidate: ${basename(candidateRoot)}`);
console.log(`Package: ${manifest.package_id ?? 'unknown'}`);
console.log(`Version: ${currentCandidateVersion || 'unknown'}`);
for (const item of failures) console.log(`FAIL: ${item}`);
if (failures.length) {
  console.error(`\nBLOCK: ${failures.length} approval check(s) failed.`);
  process.exitCode = 1;
} else {
  console.log('\nAPPROVAL_RECORD_PASS: record structure and exact candidate, evidence, canonical tag, and workflow-injected binding passed. This does not verify the approver identity, reviewer independence, remote signer allowlist, Protected Environment, workflow origin, publication, or Published status.');
}
