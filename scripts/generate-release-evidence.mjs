#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { readFrontMatter } from './lib/markdown-front-matter.mjs';
import {
  EXPECTED_RUNTIME_TEST_PLAN,
  EXPECTED_RUNTIME_TESTS,
  MOTHER_RUNTIME_REASON,
  SUB_LIBRARY_RUNTIME_REASON,
  TRUSTED_EVIDENCE_SCHEMA,
  TRUSTED_EVIDENCE_SOURCE,
  TRUSTED_RESULT_SCHEMA,
  trustedCheckContract,
  trustedProfile,
} from './lib/release-evidence-contract.mjs';

const args = process.argv.slice(2);
const flag = (name) => { const index = args.indexOf(name); return index >= 0 ? args[index + 1] : ''; };
const fail = (message) => { console.error(`BLOCK: ${message}`); process.exit(1); };
const sha256Bytes = (value) => createHash('sha256').update(value).digest('hex');
const sha256File = (path) => sha256Bytes(readFileSync(path));
function required(value, label, pattern) {
  const text = `${value ?? ''}`.trim();
  if (!text || (pattern && !pattern.test(text))) fail(`${label} is missing or invalid`);
  return text;
}
function portable(value, label) {
  const text = required(value, label);
  if (text.startsWith('/') || text.includes('\\') || text.split('/').some((part) => !part || part === '.' || part === '..')) fail(`${label} must be a portable relative path`);
  return text;
}
function lineCount(buffer) {
  if (!buffer.length) return 0;
  const text = buffer.toString('utf8');
  return text.split('\n').length - (text.endsWith('\n') ? 1 : 0);
}
function runCommand({ id, command, cwd, argv, env = {}, logRoot }) {
  const result = spawnSync(argv[0], argv.slice(1), { cwd, env: { ...process.env, ...env }, encoding: null, maxBuffer: 64 * 1024 * 1024 });
  if (result.error) fail(`${id} could not execute: ${result.error.message}`);
  const stdout = Buffer.isBuffer(result.stdout) ? result.stdout : Buffer.from(result.stdout ?? '');
  const stderr = Buffer.isBuffer(result.stderr) ? result.stderr : Buffer.from(result.stderr ?? '');
  const output = Buffer.concat([stdout, stderr]);
  const outputFile = `checks/${id}.log`;
  writeFileSync(join(logRoot, outputFile), output);
  if (result.status !== 0) {
    process.stdout.write(stdout);
    process.stderr.write(stderr);
    fail(`${id} fixed command failed with exit code ${result.status}`);
  }
  return {
    schema: TRUSTED_RESULT_SCHEMA,
    command,
    exit_code: result.status,
    output_file: outputFile,
    output_sha256: sha256Bytes(output),
    output_bytes: output.length,
    output_lines: lineCount(output),
  };
}
function gitText(sourceRoot, gitArgs, label) {
  const result = spawnSync('git', gitArgs, { cwd: sourceRoot, encoding: 'utf8' });
  if (result.status !== 0) fail(`${label} failed: ${result.stderr || result.stdout}`);
  return result.stdout;
}
function verifyProvenance(sourceRoot, candidateRoot, manifest) {
  const sourceCommit = required(manifest.source_commit, 'candidate source_commit', /^[a-f0-9]{40}$/);
  if (manifest.source_commit_rebuildable !== true || manifest.source_snapshot_kind !== 'source-commit' || manifest.source_selected_dirty !== false) fail('candidate commit provenance is not rebuildable and clean');
  const records = manifest.source_provenance?.files;
  if (!Array.isArray(manifest.files) || !Array.isArray(records) || records.length !== manifest.files.length) fail('candidate provenance must cover every selected file');
  const byPath = new Map(records.map((record) => [record.path, record]));
  let bound = 0;
  for (const file of manifest.files) {
    const record = byPath.get(file);
    if (!record || record.commit_bound !== true || record.git_state !== 'committed') fail(`candidate provenance is not commit-bound: ${file}`);
    const repositoryPath = manifest.release_scope === 'standalone-mother-library' ? file : `${manifest.source_scope}/${file}`;
    const line = gitText(sourceRoot, ['ls-tree', sourceCommit, '--', repositoryPath], `git ls-tree ${repositoryPath}`).trim();
    const match = line.match(/^([0-7]{6})\s+blob\s+([a-f0-9]{40})\t(.+)$/);
    if (!match || match[3] !== repositoryPath || match[2] !== record.commit_blob) fail(`source commit tree does not match candidate provenance: ${repositoryPath}`);
    const blob = spawnSync('git', ['cat-file', 'blob', match[2]], { cwd: sourceRoot });
    if (blob.status !== 0) fail(`could not read source commit blob: ${repositoryPath}`);
    const blobDigest = sha256Bytes(blob.stdout);
    if (blobDigest !== record.commit_sha256 || sha256File(join(candidateRoot, file)) !== record.sha256 || record.sha256 !== record.commit_sha256) fail(`candidate bytes do not match source commit: ${repositoryPath}`);
    bound += 1;
  }
  return {
    source_commit: sourceCommit,
    selected_file_count: manifest.files.length,
    commit_bound_file_count: bound,
    unbound_file_count: 0,
    missing_commit_file_count: 0,
  };
}
function verifyMotherRuntime(sourceRoot, candidateRoot, manifest) {
  let frontMatter;
  try { frontMatter = readFrontMatter(join(sourceRoot, 'MANIFEST.md'), { rejectDuplicates: true }); } catch (error) { fail(`mother MANIFEST.md front matter is invalid: ${error.message}`); }
  if (frontMatter?.data.get('runtime_applicability') !== 'none' || frontMatter?.data.get('runtime_contract') !== null) fail('mother MANIFEST.md must declare runtime_applicability: none and runtime_contract: null');
  if (manifest.runtime_applicability !== 'none' || manifest.runtime_contract !== null) fail('frozen mother candidate machine contract must declare runtime_applicability=none and runtime_contract=null');
  if (existsSync(join(sourceRoot, 'RUNTIME-CONTRACT.json'))) fail('mother runtime N/A is forbidden when the source root contains RUNTIME-CONTRACT.json');
  if (manifest.files?.includes('RUNTIME-CONTRACT.json') || existsSync(join(candidateRoot, 'RUNTIME-CONTRACT.json'))) fail('mother runtime N/A is forbidden when the candidate contains root RUNTIME-CONTRACT.json');
  return { applicability: 'none', contract_path: null, contract_present: false, status: 'runtime_not_applicable', reason: MOTHER_RUNTIME_REASON };
}

const scope = required(flag('--scope'), '--scope', /^(mother-library|sub-library)$/);
const sourceRoot = resolve(required(flag('--source-root'), '--source-root'));
const candidateRoot = resolve(required(flag('--candidate'), '--candidate'));
const outputRoot = resolve(required(flag('--output-root'), '--output-root'));
const approvalIntentPath = resolve(required(flag('--approval-intent'), '--approval-intent'));
const packageId = required(flag('--package-id'), '--package-id', /^[a-z0-9][a-z0-9-]*$/);
for (const [label, path] of [['source root', sourceRoot], ['candidate root', candidateRoot]]) if (!existsSync(path) || !statSync(path).isDirectory()) fail(`${label} is missing: ${path}`);
if (!existsSync(approvalIntentPath) || !statSync(approvalIntentPath).isFile()) fail(`approval intent is missing: ${approvalIntentPath}`);
mkdirSync(join(outputRoot, 'checks'), { recursive: true });
const manifestPath = join(candidateRoot, 'MANIFEST.json');
const sumsPath = join(candidateRoot, 'SHA256SUMS');
if (!existsSync(manifestPath) || !existsSync(sumsPath)) fail('candidate must contain MANIFEST.json and SHA256SUMS');
let manifest; let approvalIntent;
try { manifest = JSON.parse(readFileSync(manifestPath, 'utf8')); } catch { fail('candidate MANIFEST.json is invalid JSON'); }
try { approvalIntent = JSON.parse(readFileSync(approvalIntentPath, 'utf8')); } catch { fail('approval intent is invalid JSON'); }
if (manifest.package_id !== packageId) fail('candidate package_id does not match --package-id');
if (approvalIntent?.validation?.evidence_bundle !== null || approvalIntent?.validation?.evidence_digest !== null || approvalIntent?.validation?.completed_at !== null) fail('approval intent must not inject final governance evidence fields');
const profile = trustedProfile(scope);
const contract = trustedCheckContract(scope);
const workflowSha = required(process.env.RELEASE_ACTUAL_WORKFLOW_SHA, 'RELEASE_ACTUAL_WORKFLOW_SHA', /^[a-f0-9]{40}$/);
const runId = required(process.env.RELEASE_ACTUAL_RUN_ID, 'RELEASE_ACTUAL_RUN_ID', /^\d+$/);
const runAttempt = Number(required(process.env.RELEASE_ACTUAL_RUN_ATTEMPT, 'RELEASE_ACTUAL_RUN_ATTEMPT', /^\d+$/));
const jobId = required(process.env.RELEASE_ACTUAL_JOB_ID, 'RELEASE_ACTUAL_JOB_ID', /^[a-z0-9][a-z0-9-]*$/);
const candidateCommit = required(process.env.RELEASE_ACTUAL_CANDIDATE_COMMIT, 'RELEASE_ACTUAL_CANDIDATE_COMMIT', /^[a-f0-9]{40}$/);
const tagName = required(process.env.RELEASE_ACTUAL_TAG_NAME, 'RELEASE_ACTUAL_TAG_NAME');
const tagObjectSha = required(process.env.RELEASE_ACTUAL_TAG_OBJECT_SHA, 'RELEASE_ACTUAL_TAG_OBJECT_SHA', /^[a-f0-9]{40}$/);
const signerFingerprint = required(process.env.RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT, 'RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT', /^[A-F0-9]{40}(?:[A-F0-9]{24})?$/);
const completedAt = required(process.env.RELEASE_EVIDENCE_COMPLETED_AT, 'RELEASE_EVIDENCE_COMPLETED_AT');
if (Number.isNaN(Date.parse(completedAt))) fail('RELEASE_EVIDENCE_COMPLETED_AT must be an ISO timestamp');
if (manifest.source_commit !== candidateCommit) fail('candidate source_commit does not match trusted workflow candidate commit');
const execution = {
  source: TRUSTED_EVIDENCE_SOURCE,
  workflow_sha: workflowSha,
  run_id: runId,
  run_attempt: runAttempt,
  job_id: jobId,
  runtime_job_id: 'isolated-runtime-tests',
  candidate_commit: candidateCommit,
  tag_name: tagName,
  tag_object_sha: tagObjectSha,
};
const contextSha256 = sha256Bytes(JSON.stringify(execution, Object.keys(execution).sort()));
const checks = [];
const add = (id, result) => checks.push({ id, status: 'pass', result: { ...result, context_sha256: contextSha256, producer_job: id === 'runtime-tests' ? execution.runtime_job_id : jobId } });
const runNode = (id, script, scriptArgs = [], cwd = sourceRoot) => runCommand({ id, command: contract.get(id), cwd, argv: [process.execPath, script, ...scriptArgs], logRoot: outputRoot });

let result = runNode('governance-tests', join(sourceRoot, 'scripts/run-governance-tests.mjs'), ['--timeout-ms', '30000']);
const governanceOutput = readFileSync(join(outputRoot, result.output_file), 'utf8');
const summary = governanceOutput.match(/GOVERNANCE_TEST_SUMMARY: total=(\d+) passed=(\d+) known_gaps=(\d+) failed=(\d+)/);
if (!summary || summary[1] !== summary[2] || summary[3] !== '0' || summary[4] !== '0') fail('governance test output lacks an exact all-pass summary');
const list = spawnSync(process.execPath, [join(sourceRoot, 'scripts/run-governance-tests.mjs'), '--list'], { cwd: sourceRoot, encoding: 'utf8' });
if (list.status !== 0) fail('could not resolve the fixed governance test plan');
const governancePlan = list.stdout.trim().split('\n').filter(Boolean).map((line) => line.split('\t')[0]);
if (governancePlan.length !== Number(summary[1])) fail('governance test plan count does not match executed summary');
add('governance-tests', { ...result, test_plan: governancePlan, expected_tests: Number(summary[1]), passed_tests: Number(summary[2]), failed_tests: 0, skipped_tests: 0 });

result = runNode('index-validation', join(sourceRoot, 'scripts/validate-indexes.mjs'), ['--strict']); add('index-validation', { ...result, mode: 'strict' });
result = runNode('link-validation', join(sourceRoot, 'scripts/validate-links.mjs'), ['--release']); add('link-validation', { ...result, mode: 'release' });
if (scope === 'mother-library') {
  result = runNode('document-id-validation', join(sourceRoot, 'scripts/validate-document-ids.mjs')); add('document-id-validation', { ...result, mode: 'default' });
  result = runNode('log-validation', join(sourceRoot, 'scripts/validate-logs.mjs'), ['--release']); add('log-validation', { ...result, mode: 'release' });
  result = runNode('knowledge-chain-validation', join(sourceRoot, 'scripts/validate-knowledge-chain.mjs'), ['--release']); add('knowledge-chain-validation', { ...result, mode: 'release' });
  result = runNode('mother-structure-validation', join(sourceRoot, 'scripts/validate-mother-library.mjs'), ['--release']); add('mother-structure-validation', { ...result, mode: 'release' });
  const runtime = verifyMotherRuntime(sourceRoot, candidateRoot, manifest);
  const runtimeOutput = Buffer.from(`${JSON.stringify(runtime)}\n`, 'utf8');
  const runtimeOutputFile = 'checks/runtime-applicability.log';
  writeFileSync(join(outputRoot, runtimeOutputFile), runtimeOutput);
  add('runtime-applicability', { schema: TRUSTED_RESULT_SCHEMA, command: contract.get('runtime-applicability'), exit_code: 0, output_file: runtimeOutputFile, output_sha256: sha256Bytes(runtimeOutput), output_bytes: runtimeOutput.length, output_lines: 1, ...runtime });
} else {
  result = runNode('document-id-validation', join(sourceRoot, 'scripts/validate-document-ids.mjs'), ['--scope', `sub-library:${packageId}`]); add('document-id-validation', { ...result, mode: 'sub-library-scope' });
  const packagePath = `sub-libraries/${packageId}`;
  result = runNode('sub-library-structure-validation', join(sourceRoot, packagePath, 'scripts/validate-sub-library.mjs'), ['--release']); add('sub-library-structure-validation', { ...result, mode: 'release' });
  const runtimeOutputSha256 = required(process.env.RELEASE_ACTUAL_RUNTIME_OUTPUT_SHA256, 'RELEASE_ACTUAL_RUNTIME_OUTPUT_SHA256', /^[a-f0-9]{64}$/);
  const runtimeImageDigest = required(process.env.RELEASE_ACTUAL_RUNTIME_IMAGE_DIGEST, 'RELEASE_ACTUAL_RUNTIME_IMAGE_DIGEST', /^sha256:[a-f0-9]{64}$/);
  const expected = Number(required(process.env.RELEASE_ACTUAL_RUNTIME_EXPECTED_TESTS, 'RELEASE_ACTUAL_RUNTIME_EXPECTED_TESTS', /^\d+$/));
  const passed = Number(required(process.env.RELEASE_ACTUAL_RUNTIME_PASSED_TESTS, 'RELEASE_ACTUAL_RUNTIME_PASSED_TESTS', /^\d+$/));
  const failed = Number(required(process.env.RELEASE_ACTUAL_RUNTIME_FAILED_TESTS, 'RELEASE_ACTUAL_RUNTIME_FAILED_TESTS', /^\d+$/));
  const skipped = Number(required(process.env.RELEASE_ACTUAL_RUNTIME_SKIPPED_TESTS, 'RELEASE_ACTUAL_RUNTIME_SKIPPED_TESTS', /^\d+$/));
  if (expected !== EXPECTED_RUNTIME_TESTS || passed !== expected || failed !== 0 || skipped !== 0) fail('trusted runtime job counters do not match the fixed all-pass profile');
  add('runtime-tests', { schema: TRUSTED_RESULT_SCHEMA, command: contract.get('runtime-tests'), exit_code: 0, output_file: null, output_sha256: runtimeOutputSha256, output_bytes: Number(required(process.env.RELEASE_ACTUAL_RUNTIME_OUTPUT_BYTES, 'RELEASE_ACTUAL_RUNTIME_OUTPUT_BYTES', /^\d+$/)), output_lines: Number(required(process.env.RELEASE_ACTUAL_RUNTIME_OUTPUT_LINES, 'RELEASE_ACTUAL_RUNTIME_OUTPUT_LINES', /^\d+$/)), test_plan: EXPECTED_RUNTIME_TEST_PLAN, expected_tests: expected, passed_tests: passed, failed_tests: failed, skipped_tests: skipped, image_digest: runtimeImageDigest, status: 'runtime_verified', reason: SUB_LIBRARY_RUNTIME_REASON });
}
result = runNode('artifact-validation', join(candidateRoot, 'scripts/validate-artifact.mjs'), ['--prepare', candidateRoot], candidateRoot); add('artifact-validation', { ...result, mode: 'prepare', content_digest: manifest.content_digest });
const provenance = verifyProvenance(sourceRoot, candidateRoot, manifest);
const provenanceOutput = Buffer.from(`${JSON.stringify(provenance)}\n`, 'utf8');
const provenanceFile = 'checks/commit-provenance.log'; writeFileSync(join(outputRoot, provenanceFile), provenanceOutput);
add('commit-provenance', { schema: TRUSTED_RESULT_SCHEMA, command: contract.get('commit-provenance'), exit_code: 0, output_file: provenanceFile, output_sha256: sha256Bytes(provenanceOutput), output_bytes: provenanceOutput.length, output_lines: 1, ...provenance });
const tagResult = spawnSync('git', ['verify-tag', '--raw', tagName], { cwd: sourceRoot, encoding: null, maxBuffer: 16 * 1024 * 1024 });
const tagOutput = Buffer.concat([Buffer.from(tagResult.stdout ?? ''), Buffer.from(tagResult.stderr ?? '')]);
const tagOutputFile = 'checks/tag-signature.log'; writeFileSync(join(outputRoot, tagOutputFile), tagOutput);
if (tagResult.status !== 0) fail('trusted tag signature command failed');
const fingerprintMatch = tagOutput.toString('utf8').match(/\[GNUPG:\] VALIDSIG ([A-Fa-f0-9]{40}(?:[A-Fa-f0-9]{24})?)/);
if (!fingerprintMatch || fingerprintMatch[1].toUpperCase() !== signerFingerprint) fail('trusted tag signature output does not match the workflow signer fingerprint');
const actualTagObject = gitText(sourceRoot, ['rev-parse', '--verify', `refs/tags/${tagName}`], 'resolve tag object').trim();
if (actualTagObject !== tagObjectSha) fail('trusted tag signature result does not match workflow tag object');
const approvalTag = approvalIntent?.tag ?? {};
if (approvalIntent?.approval_id == null || approvalIntent?.scope?.kind !== scope || approvalIntent?.scope?.id !== manifest.package_id || approvalIntent?.candidate?.content_digest !== manifest.content_digest) fail('approval intent identity does not match the generated evidence candidate');
if (approvalTag.name !== tagName || approvalTag.target_commit !== candidateCommit || approvalTag.object_sha !== tagObjectSha || `${approvalTag.signer_fingerprint ?? ''}`.toUpperCase() !== signerFingerprint) fail('approval intent tag receipt does not match the trusted Git tag context');
for (const [field, expected] of [
  ['annotation_schema', 'release-tag-annotation/v1'],
  ['approval_binding_digest_algorithm', 'sha256-canonical-approval-binding-v1'],
]) if (approvalTag[field] !== expected) fail(`approval intent tag.${field} must be ${expected}`);
for (const field of ['annotation_sha256', 'approval_binding_sha256']) if (!/^[a-f0-9]{64}$/.test(approvalTag[field] ?? '')) fail(`approval intent tag.${field} is missing or invalid`);
add('tag-signature', {
  schema: TRUSTED_RESULT_SCHEMA, command: contract.get('tag-signature'), exit_code: 0, output_file: tagOutputFile,
  output_sha256: sha256Bytes(tagOutput), output_bytes: tagOutput.length, output_lines: lineCount(tagOutput),
  tag_name: tagName, target_commit: candidateCommit, tag_object_sha: tagObjectSha, signer_fingerprint: signerFingerprint, signature_status: 'trusted',
  annotation_schema: approvalTag.annotation_schema, annotation_sha256: approvalTag.annotation_sha256,
  approval_binding_digest_algorithm: approvalTag.approval_binding_digest_algorithm, approval_binding_sha256: approvalTag.approval_binding_sha256,
  approval_id: approvalIntent.approval_id, scope_kind: scope, scope_id: manifest.package_id, version: manifest.version, candidate_content_digest: manifest.content_digest,
});
if (checks.map((check) => check.id).join('\n') !== [...contract.keys()].join('\n')) fail('generated check order/set does not exactly match the trusted profile');
const evidence = {
  schema: TRUSTED_EVIDENCE_SCHEMA,
  profile,
  scope: { kind: scope, id: manifest.package_id, package_kind: manifest.package_kind },
  source: { commit: manifest.source_commit, dirty: false },
  candidate: { content_digest: manifest.content_digest, manifest_sha256: sha256File(manifestPath), sha256sums_sha256: sha256File(sumsPath) },
  execution,
  completed_at: new Date(completedAt).toISOString(),
  checks,
};
const outputPath = join(outputRoot, 'RELEASE-EVIDENCE.json');
writeFileSync(outputPath, `${JSON.stringify(evidence, null, 2)}\n`, { mode: 0o600 });
console.log(`TRUSTED_RELEASE_EVIDENCE: ${outputPath}`);
console.log(`TRUSTED_RELEASE_EVIDENCE_CHECKS: ${checks.length}`);
