#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, mkdtempSync, readFileSync, readdirSync, readlinkSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import {
  EXPECTED_RUNTIME_TEST_PLAN,
  EXPECTED_RUNTIME_TESTS,
  MOTHER_RUNTIME_REASON,
  SUB_LIBRARY_RUNTIME_REASON,
} from './lib/release-evidence-contract.mjs';

const TAG_ANNOTATION_SCHEMA = 'release-tag-annotation/v1';
const APPROVAL_BINDING_ALGORITHM = 'sha256-canonical-approval-binding-v1';
const TREE_DIGEST_ALGORITHM = 'sha256-canonical-tree-v1';
const args = process.argv.slice(2);
function flag(name) { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : ''; }
function fail(message) { console.error(`BLOCK: ${message}`); process.exit(1); }
function readJson(path, label) { try { return JSON.parse(readFileSync(path, 'utf8')); } catch { fail(`${label} is missing or invalid JSON: ${path}`); } }
function sha256Bytes(value) { return createHash('sha256').update(value).digest('hex'); }
function sha256File(path) { return sha256Bytes(readFileSync(path)); }
function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  fail('attestation input contains a non-canonical JSON value');
}
function canonicalDigest(value) { return sha256Bytes(canonicalJson(value)); }
function requiredEnv(name, pattern) { const value = (process.env[name] ?? '').trim(); if (!value || (pattern && !pattern.test(value))) fail(`${name} is missing or invalid`); return value; }
function intEnv(name) { const value = Number(requiredEnv(name, /^\d+$/)); if (!Number.isSafeInteger(value) || value < 0) fail(`${name} must be a non-negative integer`); return value; }
function isWithin(parent, child) { const rel = relative(resolve(parent), resolve(child)); return rel === '' || (!rel.startsWith('..') && !rel.startsWith('/')); }
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
function decodeCanonicalBase64(value, field) {
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(value) || value.length % 4 !== 0) fail(`${field} must be canonical base64`);
  const decoded = Buffer.from(value, 'base64');
  if (decoded.toString('base64') !== value) fail(`${field} must be canonical base64`);
  return decoded.toString('utf8');
}
function parseCanonicalAnnotation(text) {
  if (!text || text.includes('\n') || text.includes('\r')) fail('tag annotation must be one canonical JSON line');
  let annotation;
  try { annotation = JSON.parse(text); } catch { fail('tag annotation is not valid JSON'); }
  const keys = Object.keys(annotation).sort();
  const expectedKeys = ['approval_binding_sha256', 'approval_id', 'candidate_content_digest', 'schema', 'scope', 'version'];
  if (JSON.stringify(keys) !== JSON.stringify(expectedKeys)) fail('tag annotation has an unsupported or incomplete schema');
  if (!annotation.scope || Array.isArray(annotation.scope) || JSON.stringify(Object.keys(annotation.scope).sort()) !== JSON.stringify(['id', 'kind'])) fail('tag annotation scope must contain exactly id and kind');
  if (canonicalJson(annotation) !== text) fail('tag annotation must use canonical JSON with sorted keys and no extra whitespace');
  return annotation;
}
function treeDigest(root) {
  if (!existsSync(root) || !statSync(root).isDirectory()) fail(`verified tree root does not exist or is not a directory: ${root}`);
  const records = [];
  function walk(current, prefix = '') {
    for (const name of readdirSync(current).sort()) {
      const path = prefix ? `${prefix}/${name}` : name;
      const absolute = resolve(current, name);
      const stat = lstatSync(absolute);
      const mode = stat.mode & 0o7777;
      if (stat.isDirectory()) {
        records.push({ path, type: 'directory', mode });
        walk(absolute, path);
      } else if (stat.isFile()) {
        records.push({ path, type: 'file', mode, size: stat.size, sha256: sha256File(absolute) });
      } else if (stat.isSymbolicLink()) {
        records.push({ path, type: 'symlink', mode, target: readlinkSync(absolute) });
      } else {
        fail(`tree digest does not support filesystem entry: ${path}`);
      }
    }
  }
  walk(root);
  return { algorithm: TREE_DIGEST_ALGORITHM, sha256: canonicalDigest(records), entry_count: records.length };
}

const candidateRoot = resolve(flag('--candidate') || '');
const verifiedTreeRoot = resolve(flag('--verified-tree') || '');
const archivePath = resolve(flag('--archive') || '');
const checksumPath = resolve(flag('--checksum') || '');
const approvalPath = resolve(flag('--approval') || '');
const evidencePath = resolve(flag('--evidence') || '');
const outputPath = resolve(flag('--output') || '');
for (const [label, path, directory] of [
  ['candidate', candidateRoot, true], ['verified-tree', verifiedTreeRoot, true], ['archive', archivePath, false],
  ['checksum', checksumPath, false], ['approval', approvalPath, false], ['evidence', evidencePath, false],
]) {
  if (!path || !existsSync(path) || (directory ? !statSync(path).isDirectory() : !statSync(path).isFile())) fail(`${label} path does not exist or has the wrong type: ${path}`);
}
if (!flag('--verified-tree')) fail('--verified-tree is required');
if (!outputPath) fail('--output is required');
if (isWithin(candidateRoot, outputPath) || isWithin(verifiedTreeRoot, outputPath)) fail('qualification attestation must be written outside both verified trees');

const manifestPath = resolve(candidateRoot, 'MANIFEST.json');
const sumsPath = resolve(candidateRoot, 'SHA256SUMS');
const verifiedManifestPath = resolve(verifiedTreeRoot, 'MANIFEST.json');
const verifiedSumsPath = resolve(verifiedTreeRoot, 'SHA256SUMS');
const manifest = readJson(manifestPath, 'candidate MANIFEST.json');
const verifiedManifest = readJson(verifiedManifestPath, 'verified-tree MANIFEST.json');
const approval = readJson(approvalPath, 'approval sidecar');
const evidence = readJson(evidencePath, 'evidence bundle');
const scope = requiredEnv('QUALIFICATION_SCOPE', /^(mother-library|sub-library)$/);
const packageId = requiredEnv('QUALIFICATION_PACKAGE_ID', /^[a-z0-9][a-z0-9-]*$/);
const version = requiredEnv('QUALIFICATION_VERSION', /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/);
const contentDigest = requiredEnv('QUALIFICATION_CONTENT_DIGEST', /^[a-f0-9]{64}$/);
const workflowSha = requiredEnv('QUALIFICATION_WORKFLOW_SHA', /^[a-f0-9]{40}$/);
const runId = requiredEnv('QUALIFICATION_RUN_ID', /^\d+$/);
const runAttempt = intEnv('QUALIFICATION_RUN_ATTEMPT');
const candidateCommit = requiredEnv('QUALIFICATION_CANDIDATE_COMMIT', /^[a-f0-9]{40}$/);
const tagObjectSha = requiredEnv('QUALIFICATION_TAG_OBJECT_SHA', /^[a-f0-9]{40}$/);
const tagName = requiredEnv('QUALIFICATION_TAG_NAME');
const signerFingerprint = requiredEnv('QUALIFICATION_SIGNER_FINGERPRINT', /^[A-F0-9]{40}(?:[A-F0-9]{24})?$/);
const annotationSha256 = requiredEnv('QUALIFICATION_TAG_ANNOTATION_SHA256', /^[a-f0-9]{64}$/);
const approvalBindingSha256 = requiredEnv('QUALIFICATION_APPROVAL_BINDING_SHA256', /^[a-f0-9]{64}$/);
const annotationText = decodeCanonicalBase64(requiredEnv('QUALIFICATION_TAG_ANNOTATION_BASE64'), 'QUALIFICATION_TAG_ANNOTATION_BASE64');
const annotation = parseCanonicalAnnotation(annotationText);
const qualificationTimestamp = requiredEnv('QUALIFICATION_TIMESTAMP');
if (Number.isNaN(Date.parse(qualificationTimestamp))) fail('QUALIFICATION_TIMESTAMP must be an ISO timestamp');
let testPlan; try { testPlan = JSON.parse(requiredEnv('QUALIFICATION_TEST_PLAN_JSON')); } catch { fail('QUALIFICATION_TEST_PLAN_JSON must be valid JSON'); }
if (!Array.isArray(testPlan) || testPlan.some((item) => typeof item !== 'string' || !item)) fail('QUALIFICATION_TEST_PLAN_JSON must be a string array');
const expected = intEnv('QUALIFICATION_EXPECTED_TESTS');
const passed = intEnv('QUALIFICATION_PASSED_TESTS');
const failed = intEnv('QUALIFICATION_FAILED_TESTS');
const skipped = intEnv('QUALIFICATION_SKIPPED_TESTS');
const runtimeStatus = requiredEnv('QUALIFICATION_RUNTIME_STATUS', /^(runtime_not_applicable|runtime_verified)$/);
const runtimeReason = requiredEnv('QUALIFICATION_RUNTIME_REASON', /^[a-z0-9][a-z0-9-]*$/);
const runtimeImageDigest = (process.env.QUALIFICATION_RUNTIME_IMAGE_DIGEST ?? '').trim() || null;
if (runtimeImageDigest && !/^sha256:[a-f0-9]{64}$/.test(runtimeImageDigest)) fail('QUALIFICATION_RUNTIME_IMAGE_DIGEST is invalid');
if (failed !== 0 || skipped !== 0 || passed !== expected) fail('runtime test counters do not represent an exact clean pass');
if (scope === 'mother-library') {
  if (runtimeStatus !== 'runtime_not_applicable' || runtimeReason !== MOTHER_RUNTIME_REASON || runtimeImageDigest || testPlan.length || expected !== 0 || passed !== 0) fail('mother-library runtime contract must be the exact runtime_not_applicable machine-readable state');
} else if (runtimeStatus !== 'runtime_verified' || runtimeReason !== SUB_LIBRARY_RUNTIME_REASON || !runtimeImageDigest || JSON.stringify(testPlan) !== JSON.stringify(EXPECTED_RUNTIME_TEST_PLAN) || expected !== EXPECTED_RUNTIME_TESTS || passed !== EXPECTED_RUNTIME_TESTS) {
  fail(`sub-library attestation must bind the trusted runtime_verified ${EXPECTED_RUNTIME_TESTS}-test profile`);
}
if (manifest.package_id !== packageId || manifest.version !== version || manifest.content_digest !== contentDigest || manifest.source_commit !== candidateCommit) fail('attestation identity does not match frozen candidate MANIFEST.json');
if (canonicalJson(verifiedManifest) !== canonicalJson(manifest) || sha256File(verifiedManifestPath) !== sha256File(manifestPath) || sha256File(verifiedSumsPath) !== sha256File(sumsPath)) fail('archive-extracted MANIFEST.json or SHA256SUMS differs from the verified candidate');
if (manifest.qualification_state !== 'prepared-unapproved' || manifest.approval_status !== 'pending') fail('attestation only accepts an unmodified prepared-unapproved candidate');
if (scope === 'mother-library') {
  if (manifest.runtime_applicability !== 'none' || manifest.runtime_contract !== null || verifiedManifest.runtime_applicability !== 'none' || verifiedManifest.runtime_contract !== null) fail('mother runtime N/A requires matching machine contracts in candidate and verified tree manifests');
  if (manifest.files?.includes('RUNTIME-CONTRACT.json') || existsSync(join(candidateRoot, 'RUNTIME-CONTRACT.json')) || existsSync(join(verifiedTreeRoot, 'RUNTIME-CONTRACT.json'))) fail('mother runtime N/A is forbidden when candidate or verified tree contains root RUNTIME-CONTRACT.json');
  const runtimeChecks = Array.isArray(evidence.checks) ? evidence.checks.filter((check) => check?.id === 'runtime-applicability') : [];
  if (runtimeChecks.length !== 1) fail('mother evidence must contain exactly one runtime-applicability check');
  const runtimeEvidence = runtimeChecks[0]?.result ?? {};
  if (runtimeChecks[0]?.status !== 'pass' || runtimeEvidence.applicability !== 'none' || runtimeEvidence.contract_path !== null || runtimeEvidence.contract_present !== false || runtimeEvidence.status !== 'runtime_not_applicable' || runtimeEvidence.reason !== MOTHER_RUNTIME_REASON) fail('mother runtime-applicability evidence does not match the exact machine contract');
}
if (approval?.scope?.id !== packageId || approval?.scope?.kind !== scope || approval?.source?.commit !== candidateCommit || approval?.candidate?.content_digest !== contentDigest || approval?.tag?.name !== tagName) fail('approval sidecar identity does not match qualification identity');
if (evidence?.scope?.id !== packageId || evidence?.scope?.kind !== scope) fail('evidence scope does not match qualification package');
const computedApprovalBindingSha256 = canonicalDigest(approvalBindingProjection(approval));
if (approvalBindingSha256 !== computedApprovalBindingSha256 || approval?.tag?.approval_binding_sha256 !== approvalBindingSha256 || approval?.tag?.approval_binding_digest_algorithm !== APPROVAL_BINDING_ALGORITHM) fail('approval binding digest is inconsistent across workflow and approval sidecar');
if (approval?.tag?.object_sha !== tagObjectSha || approval?.tag?.signer_fingerprint !== signerFingerprint || approval?.tag?.annotation_schema !== TAG_ANNOTATION_SCHEMA || approval?.tag?.annotation_sha256 !== annotationSha256) fail('actual tag object, signer, or annotation digest does not match the approval sidecar');
const expectedAnnotation = {
  approval_binding_sha256: approvalBindingSha256,
  approval_id: approval.approval_id,
  candidate_content_digest: contentDigest,
  schema: TAG_ANNOTATION_SCHEMA,
  scope: { kind: scope, id: packageId },
  version,
};
if (canonicalJson(annotation) !== canonicalJson(expectedAnnotation) || sha256Bytes(annotationText) !== annotationSha256) fail('canonical tag annotation is not exactly bound to approval_id, scope, version, and candidate digest');
const tagChecks = Array.isArray(evidence.checks) ? evidence.checks.filter((check) => check?.id === 'tag-signature') : [];
if (tagChecks.length !== 1) fail('evidence must contain exactly one tag-signature check');
const tagEvidence = tagChecks[0]?.result ?? {};
if (tagEvidence.tag_name !== tagName || tagEvidence.target_commit !== candidateCommit || tagEvidence.tag_object_sha !== tagObjectSha || tagEvidence.signer_fingerprint !== signerFingerprint || tagEvidence.signature_status !== 'trusted' || tagEvidence.annotation_schema !== TAG_ANNOTATION_SCHEMA || tagEvidence.annotation_sha256 !== annotationSha256 || tagEvidence.approval_binding_digest_algorithm !== APPROVAL_BINDING_ALGORITHM || tagEvidence.approval_binding_sha256 !== approvalBindingSha256 || tagEvidence.approval_id !== approval.approval_id || tagEvidence.scope_kind !== scope || tagEvidence.scope_id !== packageId || tagEvidence.version !== version || tagEvidence.candidate_content_digest !== contentDigest) fail('tag-signature evidence is not exactly bound to the actual tag, approval, scope, version, and candidate');

const archiveSha256 = sha256File(archivePath);
const checksumText = readFileSync(checksumPath, 'utf8');
const expectedChecksumText = `${archiveSha256}  ${basename(archivePath)}\n`;
if (checksumText !== expectedChecksumText) fail('archive checksum sidecar must contain exactly the archive SHA-256 and archive basename');
const candidateTree = treeDigest(candidateRoot);
const verifiedTree = treeDigest(verifiedTreeRoot);
if (candidateTree.sha256 !== verifiedTree.sha256 || candidateTree.entry_count !== verifiedTree.entry_count) fail('archive-extracted tree is not byte/type/mode equivalent to the verified candidate tree');
const archiveList = spawnSync('tar', ['-tzf', archivePath], { encoding: 'utf8' });
if (archiveList.status !== 0) fail(`archive cannot be listed as gzip-compressed tar: ${archiveList.stderr || archiveList.stdout}`);
for (const entry of archiveList.stdout.split('\n').filter(Boolean)) {
  const normalized = entry.replace(/^\.\//, '').replace(/\/$/, '');
  if (!normalized) continue;
  const segments = normalized.split('/');
  if (entry.startsWith('/') || entry.includes('\\') || segments.some((segment) => !segment || segment === '.' || segment === '..')) fail(`archive contains a non-portable or unsafe path: ${entry}`);
}
const attestationExtractionRoot = mkdtempSync(join(tmpdir(), 'qualification-archive-'));
let archiveExtractedTree;
let archiveRuntimeContractPresent = false;
try {
  const extraction = spawnSync('tar', ['-xzf', archivePath, '-C', attestationExtractionRoot], { encoding: 'utf8' });
  if (extraction.status !== 0) fail(`archive extraction failed during attestation: ${extraction.stderr || extraction.stdout}`);
  archiveRuntimeContractPresent = existsSync(join(attestationExtractionRoot, 'RUNTIME-CONTRACT.json'));
  archiveExtractedTree = treeDigest(attestationExtractionRoot);
} finally {
  rmSync(attestationExtractionRoot, { recursive: true, force: true });
}
if (archiveExtractedTree.sha256 !== candidateTree.sha256 || archiveExtractedTree.entry_count !== candidateTree.entry_count) fail('archive bytes do not extract to the exact verified candidate tree');
if (scope === 'mother-library' && archiveRuntimeContractPresent) fail('mother runtime N/A is forbidden when archive-extracted tree contains root RUNTIME-CONTRACT.json');

const attestation = {
  schema: 'qualification-attestation/v2',
  qualification_state: 'qualified-not-published',
  scope: { kind: scope, package_id: packageId, version },
  candidate: {
    content_digest: contentDigest,
    manifest_sha256: sha256File(manifestPath),
    sha256sums_sha256: sha256File(sumsPath),
    source_commit: candidateCommit,
    tree_digest_algorithm: candidateTree.algorithm,
    tree_sha256: candidateTree.sha256,
    tree_entry_count: candidateTree.entry_count,
  },
  artifact: {
    archive_name: basename(archivePath),
    archive_sha256: archiveSha256,
    checksum_sha256: sha256File(checksumPath),
    extracted_tree_sha256: archiveExtractedTree.sha256,
    extracted_tree_entry_count: archiveExtractedTree.entry_count,
    extraction_verified: true,
  },
  approval: {
    approval_id: approval.approval_id,
    canonical_sha256: canonicalDigest(approval),
    binding_digest_algorithm: APPROVAL_BINDING_ALGORITHM,
    binding_sha256: approvalBindingSha256,
  },
  evidence: { profile: evidence.profile ?? null, canonical_sha256: canonicalDigest(evidence) },
  governance: { trusted_workflow_sha: workflowSha, github_run_id: runId, github_run_attempt: runAttempt },
  tag: {
    name: tagName,
    annotated_tag_object_sha: tagObjectSha,
    trusted_signer_fingerprint: signerFingerprint,
    annotation_schema: TAG_ANNOTATION_SCHEMA,
    annotation_sha256: annotationSha256,
  },
  runtime: {
    status: runtimeStatus,
    applicable: scope === 'sub-library',
    reason: runtimeReason,
    image_digest: runtimeImageDigest,
    test_plan: testPlan,
    expected,
    passed,
    failed,
    skipped,
  },
  qualified_at: new Date(qualificationTimestamp).toISOString(),
};
writeFileSync(outputPath, `${JSON.stringify(attestation, null, 2)}\n`);
console.log(`QUALIFICATION_ATTESTATION_PASS: ${outputPath}`);
console.log(`QUALIFICATION_TREE_EQUIVALENCE_PASS: ${candidateTree.sha256}`);
console.log(`QUALIFICATION_ATTESTATION_SHA256: ${sha256File(outputPath)}`);
