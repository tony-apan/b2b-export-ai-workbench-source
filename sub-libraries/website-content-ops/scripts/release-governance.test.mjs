import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { chmodSync, cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { scanPublishableContent } from './content-safety.mjs';
import { matchesManifestPattern } from './manifest-policy.mjs';
import { parseMarkdownFrontMatter, requireStringArrayField } from './front-matter.mjs';

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const TRUSTED_RUNTIME_TEST_PLAN = [
  'upload-media-browser.test.mjs',
  'article-image-binding.test.mjs',
  'article-operations.test.mjs',
];
const TRUSTED_RUNTIME_TEST_COUNT = 131;

function makeCopy(t) {
  const tempRoot = mkdtempSync(join(tmpdir(), 'wco-governance-'));
  const copyRoot = join(tempRoot, 'website-content-ops');
  cpSync(sourceRoot, copyRoot, {
    recursive: true,
    filter(path) {
      const rel = relative(sourceRoot, path);
      if (!rel) return true;
      const first = rel.split(sep)[0];
      return !['.git', 'dist', 'node_modules'].includes(first);
    },
  });
  t.after(() => rmSync(tempRoot, { recursive: true, force: true }));
  execFileSync('git', ['init', '-q'], { cwd: copyRoot });
  execFileSync('git', ['config', 'user.email', 'reviewer@example.invalid'], { cwd: copyRoot });
  execFileSync('git', ['config', 'user.name', 'Release Governance Test'], { cwd: copyRoot });
  execFileSync('git', ['add', '.'], { cwd: copyRoot });
  execFileSync('git', ['commit', '-qm', 'fixture'], { cwd: copyRoot });
  return copyRoot;
}

function runNode(root, script, args = [], options = {}) {
  return spawnSync(process.execPath, [join(root, script), ...args], {
    cwd: root,
    encoding: 'utf8',
    env: { ...process.env, ...(options.env ?? {}) },
  });
}


function validMarkdown(title) {
  return `---\ntitle: "${title}"\ndescription: "Adversarial fixture for fail-closed package coverage."\ntype: "note"\nstatus: "Working"\nowner: "Test"\ncreated: "2026-07-29"\nlast_updated: "2026-07-29"\nsources: ["synthetic test"]\nrelated: []\n---\n# ${title}\nSynthetic fixture only.\n`;
}

function crossPlatformSensitivePayload() {
  const linuxPath = ['', 'home', 'alice', 'customer', 'export.csv'].join('/');
  const volumePath = ['', 'Volumes', 'Client Drive', 'exports', 'customer.csv'].join('/');
  const windowsPath = ['C:', 'Users', 'Alice', 'Customers', 'export.csv'].join('\\');
  const uncPath = `${'\\'.repeat(2)}fileserver\\customers\\export.csv`;
  const fileUri = ['file:', '', '', 'home', 'alice', 'customer.csv'].join('/');
  const email = ['jane.doe', 'acme-customer.com'].join('@');
  const phone = ['+1', '415', '555', '0199'].join('-');
  const customerId = ['customer', 'id'].join('_') + ': ACME-739201';
  return [linuxPath, volumePath, windowsPath, uncPath, fileUri, email, `Phone: ${phone}`, customerId].join('\n');
}

function sha256(root, file) {
  return createHash('sha256').update(readFileSync(join(root, file))).digest('hex');
}

function rewriteArtifactIntegrity(artifactRoot) {
  const manifestPath = join(artifactRoot, 'MANIFEST.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const digest = createHash('sha256');
  for (const file of manifest.files) digest.update(`${file}\0${sha256(artifactRoot, file)}\n`);
  manifest.content_digest = digest.digest('hex');
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  const checksumFiles = [...manifest.files, 'MANIFEST.json'];
  writeFileSync(
    join(artifactRoot, 'SHA256SUMS'),
    `${checksumFiles.map((file) => `${sha256(artifactRoot, file)}  ${file}`).join('\n')}\n`,
  );
}

test('a root basename glob never authorizes nested Markdown', () => {
  assert.equal(matchesManifestPattern('README.md', '*.md'), true);
  assert.equal(matchesManifestPattern('clients/acme.md', '*.md'), false);

  const parsed = parseMarkdownFrontMatter(`---
title: "中文, quoted comma"
approval_required: true
sources: ["路径, 一.md", "REFERENCES/中文.md"]
---
# Fixture
`, { filePath: 'fixture.md' }).attributes;
  assert.equal(parsed.title, '中文, quoted comma');
  assert.equal(parsed.approval_required, true);
  assert.deepEqual(requireStringArrayField(parsed, 'sources', { filePath: 'fixture.md' }), ['路径, 一.md', 'REFERENCES/中文.md']);
  assert.throws(() => parseMarkdownFrontMatter('---\ntitle: one\ntitle: two\n---\n', { filePath: 'duplicate.md' }), /duplicate front matter key/);
  assert.throws(() => parseMarkdownFrontMatter('---\ndescription: |\n  multiline\n---\n', { filePath: 'multiline.md' }), /multiline|nested|unsupported/i);
  assert.throws(() => parseMarkdownFrontMatter('---\napproval_required: yes\n---\n', { filePath: 'ambiguous.md' }), /ambiguous/i);
  const typed = parseMarkdownFrontMatter('---\nsources: ["ok.md", 3]\n---\n', { filePath: 'typed.md' }).attributes;
  assert.throws(() => requireStringArrayField(typed, 'sources', { filePath: 'typed.md' }), /array of strings/);
});
test('an unregistered clients/acme.md blocks validation and the builder', (t) => {
  const root = makeCopy(t);
  mkdirSync(join(root, 'clients'));
  writeFileSync(join(root, 'clients', 'acme.md'), validMarkdown('ACME fixture'));

  const validation = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(validation.status, 0);
  assert.match(`${validation.stdout}\n${validation.stderr}`, /source file is not covered by manifest include\/exclude rules: clients\/acme\.md/);

  const build = runNode(root, 'scripts/build-release.mjs');
  assert.notEqual(build.status, 0);
  assert.match(`${build.stdout}\n${build.stderr}`, /source file is not covered by manifest include\/exclude rules: clients\/acme\.md/);

  rmSync(join(root, 'clients'), { recursive: true, force: true });
  const manifestPath = join(root, 'MANIFEST.md');
  const manifestOriginal = readFileSync(manifestPath, 'utf8');
  writeFileSync(manifestPath, manifestOriginal.replace('dependency_mode: "self-contained"', 'dependency_mode: "self-contained"\ndependency_mode: "declared-external-runtime"'));
  for (const script of ['scripts/validate-sub-library.mjs', 'scripts/build-release.mjs']) {
    const duplicate = runNode(root, script);
    assert.notEqual(duplicate.status, 0, `${script} must reject duplicate front matter keys`);
    assert.match(`${duplicate.stdout}\n${duplicate.stderr}`, /duplicate front matter key.*dependency_mode/i);
  }
  writeFileSync(manifestPath, manifestOriginal);

  const readmePath = join(root, 'README.md');
  const readmeOriginal = readFileSync(readmePath, 'utf8');
  writeFileSync(readmePath, readmeOriginal.replace(/^sources: .*$/m, 'sources: ["../../Mother Notes/private.md"]'));
  const spacedEscape = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(spacedEscape.status, 0);
  assert.match(`${spacedEscape.stdout}\n${spacedEscape.stderr}`, /sources (?:path |reference )?escapes sub-library|local absolute path|missing local path/i);
  writeFileSync(readmePath, readmeOriginal);

  const gitignorePath = join(root, '.gitignore');
  const gitignoreOriginal = readFileSync(gitignorePath, 'utf8');
  rmSync(gitignorePath);
  const missingGitignore = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(missingGitignore.status, 0);
  assert.match(`${missingGitignore.stdout}\n${missingGitignore.stderr}`, /missing required file: \.gitignore/);
  writeFileSync(gitignorePath, gitignoreOriginal);

  const packagePath = join(root, 'ADAPTERS/cms/allincms/package.json');
  const packageOriginal = readFileSync(packagePath, 'utf8');
  const packageJson = JSON.parse(packageOriginal);
  packageJson.version = '9.9.9-attack';
  writeFileSync(packagePath, `${JSON.stringify(packageJson, null, 2)}\n`);
  const packageMismatch = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(packageMismatch.status, 0);
  assert.match(`${packageMismatch.stdout}\n${packageMismatch.stderr}`, /package-lock.*(?:version|metadata)|package and lock.*version/i);
  writeFileSync(packagePath, packageOriginal);
});
test('an unregistered private-notes directory fails closed', (t) => {
  const root = makeCopy(t);
  mkdirSync(join(root, 'private-notes'));
  writeFileSync(join(root, 'private-notes', 'customer.md'), validMarkdown('Private notes fixture'));
  const validation = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(validation.status, 0);
  assert.match(`${validation.stdout}\n${validation.stderr}`, /source file is not covered by manifest include\/exclude rules: private-notes\/customer\.md/);
});

test('an unregistered private directory is not silently auto-ignored', (t) => {
  const root = makeCopy(t);
  mkdirSync(join(root, 'private'));
  writeFileSync(join(root, 'private', 'notes.md'), validMarkdown('Private directory fixture'));

  const validation = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(validation.status, 0);
  assert.match(`${validation.stdout}\n${validation.stderr}`, /source file is not covered by manifest include\/exclude rules: private\/notes\.md/);

  const build = runNode(root, 'scripts/build-release.mjs');
  assert.notEqual(build.status, 0);
  assert.match(`${build.stdout}\n${build.stderr}`, /source file is not covered by manifest include\/exclude rules: private\/notes\.md/);
});

test('supplementary content scanning detects cross-platform paths and common PII', (t) => {
  const root = makeCopy(t);
  const payload = crossPlatformSensitivePayload();
  const windowsForwardPath = ['D:', 'Users', 'Alice', 'Customers', 'export.csv'].join('/');

  const codes = new Set(scanPublishableContent(payload).map((issue) => issue.code));
  for (const expected of [
    'local-path-linux-home', 'local-path-macos-volume', 'local-path-windows-drive',
    'local-path-windows-unc', 'local-path-file-uri', 'possible-non-example-email',
    'possible-phone-number', 'possible-customer-identifier',
  ]) assert.equal(codes.has(expected), true, `missing scanner result: ${expected}`);
  assert.equal(
    scanPublishableContent(windowsForwardPath).some((issue) => issue.code === 'local-path-windows-drive'),
    true,
    'forward-slash Windows drive path must be detected',
  );

  writeFileSync(join(root, 'README.md'), `${readFileSync(join(root, 'README.md'), 'utf8')}\n${payload}\n`);
  const validation = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(validation.status, 0);
  const output = `${validation.stdout}\n${validation.stderr}`;
  for (const expected of codes) assert.match(output, new RegExp(`content safety ${expected}`));
});

test('artifact validation rejects cross-platform paths and PII even after integrity metadata is recomputed', (t) => {
  const root = makeCopy(t);
  const build = runNode(root, 'scripts/build-release.mjs');
  assert.equal(build.status, 0, `${build.stdout}\n${build.stderr}`);

  const artifactRoot = join(root, 'dist', 'latest');
  const readmePath = join(artifactRoot, 'README.md');
  writeFileSync(readmePath, `${readFileSync(readmePath, 'utf8')}\n${crossPlatformSensitivePayload()}\n`);
  rewriteArtifactIntegrity(artifactRoot);

  const validation = runNode(root, 'scripts/validate-artifact.mjs', [artifactRoot]);
  assert.notEqual(validation.status, 0);
  const output = `${validation.stdout}\n${validation.stderr}`;
  for (const expected of [
    'local-path-linux-home', 'local-path-macos-volume', 'local-path-windows-drive',
    'local-path-windows-unc', 'local-path-file-uri', 'possible-non-example-email',
    'possible-phone-number', 'possible-customer-identifier',
  ]) assert.match(output, new RegExp(`content safety ${expected} in artifact: README\\.md`));
  assert.doesNotMatch(output, /content_digest does not match|checksum mismatch/);
});

test('a semantically empty runtime contract blocks validation and build', (t) => {
  const root = makeCopy(t);
  const contractPath = join(root, 'RUNTIME-CONTRACT.json');
  const contract = JSON.parse(readFileSync(contractPath, 'utf8'));
  for (const field of ['inputs', 'outputs', 'required_permissions', 'network_access', 'external_side_effects', 'human_approval_points', 'unsupported_claims']) contract[field] = [];
  contract.rollback_strategy = '';
  contract.writeback_scope = '';
  contract.private_runtime_required = false;
  writeFileSync(contractPath, `${JSON.stringify(contract, null, 2)}\n`);

  const validation = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(validation.status, 0);
  assert.match(`${validation.stdout}\n${validation.stderr}`, /RUNTIME-CONTRACT schema violation/);

  const build = runNode(root, 'scripts/build-release.mjs');
  assert.notEqual(build.status, 0);
  assert.match(`${build.stdout}\n${build.stderr}`, /RUNTIME-CONTRACT schema violation/);
});


test('the sub-library builder binds selected files to commit provenance and rejects ignored, untracked, and modified inputs', (t) => {
  const root = makeCopy(t);
  const baseline = runNode(root, 'scripts/build-release.mjs', ['--require-commit-provenance']);
  assert.equal(baseline.status, 0, `${baseline.stdout}\n${baseline.stderr}`);
  const manifest = JSON.parse(readFileSync(join(root, 'dist', 'latest', 'MANIFEST.json'), 'utf8'));
  assert.equal(manifest.source_scope, 'repository-root');
  assert.equal(manifest.source_selected_dirty, false);
  assert.equal(manifest.source_commit_rebuildable, true);
  assert.equal(manifest.source_snapshot_kind, 'source-commit');
  assert.equal(manifest.source_provenance.commit_bound_file_count, manifest.files.length);
  assert.deepEqual(manifest.source_provenance.unbound_files, []);
  assert.ok(manifest.delivery_modes.length > 0, 'delivery_modes must be copied from MANIFEST.md');
  assert.ok(manifest.external_dependencies.length > 0, 'external_dependencies must be copied from MANIFEST.md');

  writeFileSync(join(root, 'scripts', 'untracked-provenance-fixture.mjs'), 'export default "untracked";\n');
  const untracked = runNode(root, 'scripts/build-release.mjs', ['--require-commit-provenance']);
  assert.notEqual(untracked.status, 0);
  assert.match(`${untracked.stdout}\n${untracked.stderr}`, /untracked-provenance-fixture\.mjs\(untracked\)/);
  rmSync(join(root, 'scripts', 'untracked-provenance-fixture.mjs'));

  const readmePath = join(root, 'README.md');
  writeFileSync(readmePath, `${readFileSync(readmePath, 'utf8')}\n<!-- modified provenance attack -->\n`);
  const modified = runNode(root, 'scripts/build-release.mjs', ['--require-commit-provenance']);
  assert.notEqual(modified.status, 0);
  assert.match(`${modified.stdout}\n${modified.stderr}`, /README\.md\(modified\)/);
});

function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string' || typeof value === 'number') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
}

function canonicalDigest(value) {
  return createHash('sha256').update(canonicalJson(value), 'utf8').digest('hex');
}

function approvalBindingProjection(approval) {
  return {
    schema: approval.schema,
    approval_id: approval.approval_id,
    decision: approval.decision,
    scope: approval.scope,
    source: approval.source,
    candidate: approval.candidate,
    validation: { profile: approval.validation.profile },
    approval: approval.approval,
    tag: {
      name: approval.tag.name,
      target_commit: approval.tag.target_commit,
      signer_fingerprint: approval.tag.signer_fingerprint,
    },
  };
}

function releaseEvidenceChecks(manifest, tagName, binding) {
  const outputSha = '0'.repeat(64);
  const common = (command) => ({ schema: 'release-check-result/v1', command, exit_code: 0, output_sha256: outputSha });
  const validation = (id, mode) => ({ id, status: 'pass', result: { ...common(`node scripts/${id}.mjs`), mode, checked_items: 1, error_count: 0 } });
  return [
    {
      id: 'governance-tests', status: 'pass', result: {
        ...common('node --test scripts/release-governance.test.mjs'),
        test_plan: ['scripts/release-governance.test.mjs'], expected_tests: 10, passed_tests: 10, failed_tests: 0, skipped_tests: 0,
      },
    },
    validation('index-validation', 'strict'),
    validation('link-validation', 'release'),
    validation('document-id-validation', 'default'),
    validation('sub-library-structure-validation', 'release'),
    {
      id: 'runtime-tests', status: 'pass', result: {
        ...common('node --test upload-media-browser.test.mjs article-image-binding.test.mjs article-operations.test.mjs'),
        test_plan: [...TRUSTED_RUNTIME_TEST_PLAN],
        expected_tests: TRUSTED_RUNTIME_TEST_COUNT, passed_tests: TRUSTED_RUNTIME_TEST_COUNT, failed_tests: 0, skipped_tests: 0,
      },
    },
    { id: 'artifact-validation', status: 'pass', result: { ...common('node scripts/validate-artifact.mjs --release'), content_digest: manifest.content_digest } },
    {
      id: 'commit-provenance', status: 'pass', result: {
        ...common('git provenance verification'), source_commit: manifest.source_commit,
        selected_file_count: manifest.files.length, commit_bound_file_count: manifest.files.length,
        unbound_file_count: 0, missing_commit_file_count: 0,
      },
    },
    {
      id: 'tag-signature', status: 'pass', result: {
        ...common('git verify-tag --raw'),
        tag_name: tagName,
        target_commit: manifest.source_commit,
        tag_object_sha: binding.tagObjectSha,
        signer_fingerprint: binding.signerFingerprint,
        signature_status: 'trusted',
        annotation_schema: 'release-tag-annotation/v1',
        annotation_sha256: binding.annotationSha256,
        approval_binding_digest_algorithm: 'sha256-canonical-approval-binding-v1',
        approval_binding_sha256: binding.approvalBindingSha256,
        approval_id: binding.approvalId,
        scope_kind: 'sub-library',
        scope_id: manifest.package_id,
        version: manifest.version,
        candidate_content_digest: manifest.content_digest,
      },
    },
  ];
}

test('the formal runtime profile matches the adapter contract and exact 131-test plan', () => {
  const contract = JSON.parse(readFileSync(join(sourceRoot, 'ADAPTERS/cms/allincms/article-operations-contract.json'), 'utf8'));
  assert.deepEqual(contract.localVerification, {
    articleOperationsTests: 36,
    articleImageBindingTests: 50,
    mediaUploadTests: 45,
    totalTests: TRUSTED_RUNTIME_TEST_COUNT,
    lastVerified: '2026-07-29',
  });
  assert.equal(
    contract.localVerification.articleOperationsTests
      + contract.localVerification.articleImageBindingTests
      + contract.localVerification.mediaUploadTests,
    TRUSTED_RUNTIME_TEST_COUNT,
  );
  const packed = spawnSync('npm', ['pack', '--dry-run', '--json'], {
    cwd: join(sourceRoot, 'ADAPTERS/cms/allincms'),
    encoding: 'utf8',
  });
  assert.equal(packed.status, 0, `${packed.stdout}\n${packed.stderr}`);
  const files = JSON.parse(packed.stdout)[0].files.map((entry) => entry.path);
  for (const path of files) {
    assert.doesNotMatch(path, /(^|\/)(node_modules|fixtures|coverage)(\/|$)/);
    assert.doesNotMatch(path, /(?:^|\/).+\.test\.mjs$/);
    assert.doesNotMatch(path, /\.redacted\.(?:md|json)$/);
    assert.doesNotMatch(path, /\.(?:png|jpe?g|gif|webp)$/i);
  }
});

function prepareFormalQualificationFixture(t) {
  const root = makeCopy(t);
  const manifestPath = join(root, 'MANIFEST.md');
  let manifestText = readFileSync(manifestPath, 'utf8');
  for (const [from, to] of [
    ['release_status: "Preview"', 'release_status: "Ready"'],
    ['maturity_status: "validated"', 'maturity_status: "stable"'],
    ['verification_status: "evidence-partial"', 'verification_status: "e2e-pass"'],
  ]) {
    assert.match(manifestText, new RegExp(from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    manifestText = manifestText.replace(from, to);
  }
  writeFileSync(manifestPath, manifestText);
  execFileSync('git', ['add', 'MANIFEST.md'], { cwd: root });
  execFileSync('git', ['commit', '-qm', 'prepare formal qualification fixture'], { cwd: root });

  const build = runNode(root, 'scripts/build-release.mjs', ['--prepare'], { env: { SOURCE_DATE_EPOCH: '0' } });
  assert.equal(build.status, 0, `${build.stdout}\n${build.stderr}`);
  const candidateRoot = `${build.stdout}\n${build.stderr}`.match(/(?:PREPARED_UNAPPROVED_CANDIDATE|PREPARED_CANDIDATE_REUSED): (.+)/)?.[1]?.trim();
  assert.ok(candidateRoot, 'prepare mode must report the content-addressed candidate path');
  const manifest = JSON.parse(readFileSync(join(candidateRoot, 'MANIFEST.json'), 'utf8'));
  const tagName = `sub-library/${manifest.package_id}/v${manifest.version}`;
  const approvalPath = join(dirname(root), 'RELEASE-APPROVAL.json');
  const evidencePath = join(dirname(root), 'RELEASE-EVIDENCE.json');
  const tagObjectSha = '1'.repeat(40);
  const signerFingerprint = 'A'.repeat(40);
  const approvalId = 'APR-WCO-G4-0001';
  const approval = {
    schema: 'release-approval/v1',
    approval_id: approvalId,
    decision: 'approved',
    scope: { kind: 'sub-library', id: manifest.package_id, package_kind: manifest.package_kind },
    source: { commit: manifest.source_commit, dirty: false },
    candidate: {
      content_digest: manifest.content_digest,
      manifest_sha256: sha256(candidateRoot, 'MANIFEST.json'),
      sha256sums_sha256: sha256(candidateRoot, 'SHA256SUMS'),
      immutable_locator: `https://releases.example.com/${manifest.package_id}/v${manifest.version}/${manifest.content_digest}/candidate`,
    },
    validation: {
      profile: 'sub-library-release-v1',
      evidence_digest_algorithm: 'sha256-canonical-json-v1',
      evidence_bundle: 'RELEASE-EVIDENCE.json',
      evidence_digest: '',
      completed_at: '2026-07-28T00:00:00Z',
    },
    approval: {
      approved_by: 'Tony Human Reviewer',
      approved_at: '2026-07-28T00:01:00Z',
      basis_ref: 'review-record:g4-fixture-0001',
    },
    tag: {
      name: tagName,
      target_commit: manifest.source_commit,
      object_sha: tagObjectSha,
      signer_fingerprint: signerFingerprint,
      annotation_schema: 'release-tag-annotation/v1',
      annotation_sha256: '',
      approval_binding_digest_algorithm: 'sha256-canonical-approval-binding-v1',
      approval_binding_sha256: '',
    },
  };
  approval.tag.approval_binding_sha256 = canonicalDigest(approvalBindingProjection(approval));
  const annotation = {
    approval_binding_sha256: approval.tag.approval_binding_sha256,
    approval_id: approval.approval_id,
    candidate_content_digest: manifest.content_digest,
    schema: 'release-tag-annotation/v1',
    scope: { kind: approval.scope.kind, id: approval.scope.id },
    version: manifest.version,
  };
  const annotationText = canonicalJson(annotation);
  approval.tag.annotation_sha256 = createHash('sha256').update(annotationText, 'utf8').digest('hex');
  const binding = {
    tagObjectSha,
    signerFingerprint,
    annotationSha256: approval.tag.annotation_sha256,
    approvalBindingSha256: approval.tag.approval_binding_sha256,
    approvalId,
  };
  const evidence = {
    schema: 'release-evidence/v1',
    profile: approval.validation.profile,
    scope: { ...approval.scope },
    source: { ...approval.source },
    candidate: {
      content_digest: approval.candidate.content_digest,
      manifest_sha256: approval.candidate.manifest_sha256,
      sha256sums_sha256: approval.candidate.sha256sums_sha256,
    },
    completed_at: approval.validation.completed_at,
    checks: releaseEvidenceChecks(manifest, tagName, binding),
  };
  approval.validation.evidence_digest = canonicalDigest(evidence);
  writeFileSync(approvalPath, `${JSON.stringify(approval, null, 2)}\n`);
  writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`);

  const fakeBin = join(dirname(root), 'fake-bin');
  const fakeGitPath = join(fakeBin, 'git');
  const fakeGitFixturePath = join(dirname(root), 'fake-git-fixture.json');
  mkdirSync(fakeBin, { recursive: true });
  writeFileSync(fakeGitFixturePath, `${JSON.stringify({
    candidateRoot,
    sourceCommit: manifest.source_commit,
    tagObjectSha,
    signerFingerprint,
    annotationText,
    tagName,
    records: manifest.source_provenance.files,
  }, null, 2)}\n`);
  writeFileSync(fakeGitPath, `#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const fixture = JSON.parse(fs.readFileSync(process.env.WCO_FAKE_GIT_FIXTURE, 'utf8'));
const args = process.argv.slice(2);
const same = (...expected) => args.length === expected.length && args.every((arg, index) => arg === expected[index]);
if (same('cat-file', '-t', 'refs/tags/' + fixture.tagName)) process.stdout.write('tag\\n');
else if (same('rev-parse', '--verify', 'refs/tags/' + fixture.tagName)) process.stdout.write(fixture.tagObjectSha + '\\n');
else if (same('rev-parse', '--verify', 'refs/tags/' + fixture.tagName + '^{commit}')) process.stdout.write(fixture.sourceCommit + '\\n');
else if (same('cat-file', 'tag', 'refs/tags/' + fixture.tagName)) process.stdout.write('object ' + fixture.sourceCommit + '\\ntype commit\\ntag ' + fixture.tagName + '\\ntagger Fixture <fixture@example.invalid> 0 +0000\\n\\n' + fixture.annotationText + '\\n-----BEGIN PGP SIGNATURE-----\\nfixture\\n-----END PGP SIGNATURE-----\\n');
else if (same('verify-tag', '--raw', 'refs/tags/' + fixture.tagName)) process.stderr.write('[GNUPG:] VALIDSIG ' + fixture.signerFingerprint + ' 1970-01-01 0 4 0 1 10 00 ' + fixture.signerFingerprint + '\\n');
else if (args[0] === 'ls-tree') {
  const repositoryPath = args.at(-1);
  const record = fixture.records.find((item) => (item.repository_path || item.path) === repositoryPath);
  if (!record) process.exit(1);
  process.stdout.write('100644 blob ' + record.commit_blob + '\\t' + repositoryPath + '\\n');
} else if (args[0] === 'cat-file' && args[1] === 'blob') {
  const record = fixture.records.find((item) => item.commit_blob === args[2]);
  if (!record) process.exit(1);
  process.stdout.write(fs.readFileSync(path.join(fixture.candidateRoot, record.path)));
} else process.exit(1);
`);
  chmodSync(fakeGitPath, 0o755);

  const env = {
    SOURCE_DATE_EPOCH: '0',
    PATH: `${fakeBin}:${process.env.PATH}`,
    WCO_FAKE_GIT_FIXTURE: fakeGitFixturePath,
    RELEASE_APPROVAL_PATH: approvalPath,
    RELEASE_EVIDENCE_PATH: evidencePath,
    RELEASE_SOURCE_ROOT: root,
    RELEASE_REQUIRE_GIT_TAG: '1',
    RELEASE_TRIGGER_TAG: tagName,
    RELEASE_ACTUAL_TAG_OBJECT_SHA: tagObjectSha,
    RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT: signerFingerprint,
    RELEASE_ACTUAL_TAG_ANNOTATION_SHA256: binding.annotationSha256,
    RELEASE_ACTUAL_TAG_ANNOTATION_BASE64: Buffer.from(annotationText, 'utf8').toString('base64'),
    RELEASE_ACTUAL_APPROVAL_BINDING_SHA256: binding.approvalBindingSha256,
  };
  return { root, candidateRoot, approvalPath, evidencePath, fakeGitFixturePath, env };
}

test('formal qualification binds workflow tag identity and canonical approval data without claiming human identity', (t) => {
  const fixture = prepareFormalQualificationFixture(t);
  const approval = runNode(fixture.candidateRoot, 'scripts/validate-release-approval.mjs', [fixture.candidateRoot, fixture.approvalPath, fixture.evidencePath], { env: fixture.env });
  assert.equal(approval.status, 0, `${approval.stdout}\n${approval.stderr}`);
  assert.match(approval.stdout, /APPROVAL_RECORD_PASS: record structure and exact candidate, evidence, canonical tag, and workflow-injected binding passed/);
  assert.match(approval.stdout, /does not verify the approver identity/);

  const artifact = runNode(fixture.candidateRoot, 'scripts/validate-artifact.mjs', ['--release', fixture.candidateRoot], { env: fixture.env });
  assert.equal(artifact.status, 0, `${artifact.stdout}\n${artifact.stderr}`);
  assert.match(artifact.stdout, /ARTIFACT_QUALIFICATION_RECORD_PASS:/);
  assert.match(artifact.stdout, /approver identity.*are not verified here/);

  const baselineApproval = readFileSync(fixture.approvalPath, 'utf8');
  const baselineEvidence = readFileSync(fixture.evidencePath, 'utf8');
  const runtimeEvidenceAttacks = [
    ['legacy 120/120 count', (result) => { result.expected_tests = 120; result.passed_tests = 120; }, /runtime-tests expected_tests must be 131/],
    ['off-by-one low 130/130 count', (result) => { result.expected_tests = 130; result.passed_tests = 130; }, /runtime-tests expected_tests must be 131/],
    ['off-by-one high 132/132 count', (result) => { result.expected_tests = 132; result.passed_tests = 132; }, /runtime-tests expected_tests must be 131/],
    ['partial pass count', (result) => { result.passed_tests = 130; }, /must bind exact all-pass counts with no failed or skipped tests/],
    ['non-zero failed count', (result) => { result.passed_tests = 130; result.failed_tests = 1; }, /must bind exact all-pass counts with no failed or skipped tests/],
    ['non-zero skipped count', (result) => { result.passed_tests = 130; result.skipped_tests = 1; }, /must bind exact all-pass counts with no failed or skipped tests/],
    ['reordered runtime test plan', (result) => { result.test_plan = [...TRUSTED_RUNTIME_TEST_PLAN].reverse(); }, /runtime-tests test_plan must exactly equal/],
  ];
  for (const [label, mutate, expected] of runtimeEvidenceAttacks) {
    const approvalRecord = JSON.parse(baselineApproval);
    const evidenceRecord = JSON.parse(baselineEvidence);
    const runtimeResult = evidenceRecord.checks.find((check) => check.id === 'runtime-tests').result;
    mutate(runtimeResult);
    approvalRecord.validation.evidence_digest = canonicalDigest(evidenceRecord);
    writeFileSync(fixture.approvalPath, `${JSON.stringify(approvalRecord, null, 2)}\n`);
    writeFileSync(fixture.evidencePath, `${JSON.stringify(evidenceRecord, null, 2)}\n`);
    const result = runNode(fixture.candidateRoot, 'scripts/validate-release-approval.mjs', [fixture.candidateRoot, fixture.approvalPath, fixture.evidencePath], { env: fixture.env });
    assert.notEqual(result.status, 0, label);
    assert.match(`${result.stdout}\n${result.stderr}`, expected, label);
  }
  writeFileSync(fixture.approvalPath, baselineApproval);
  writeFileSync(fixture.evidencePath, baselineEvidence);

  const attacks = [
    ['missing tag object injection', { RELEASE_ACTUAL_TAG_OBJECT_SHA: '' }, /RELEASE_ACTUAL_TAG_OBJECT_SHA is required/],
    ['forged tag object injection', { RELEASE_ACTUAL_TAG_OBJECT_SHA: '2'.repeat(40) }, /actual tag object SHA does not match approval tag\.object_sha/],
    ['forged signer injection', { RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT: 'B'.repeat(40) }, /actual tag signer does not match approval tag\.signer_fingerprint/],
    ['forged annotation digest', { RELEASE_ACTUAL_TAG_ANNOTATION_SHA256: '2'.repeat(64) }, /RELEASE_ACTUAL_TAG_ANNOTATION_SHA256 does not match the canonical annotation bytes/],
    ['forged approval binding digest', { RELEASE_ACTUAL_APPROVAL_BINDING_SHA256: '2'.repeat(64) }, /RELEASE_ACTUAL_APPROVAL_BINDING_SHA256 does not match the canonical approval binding/],
    ['noncanonical annotation bytes', { RELEASE_ACTUAL_TAG_ANNOTATION_BASE64: Buffer.from('{}', 'utf8').toString('base64') }, /actual release tag annotation does not exactly match/],
  ];
  for (const [label, envOverride, expected] of attacks) {
    const result = runNode(fixture.candidateRoot, 'scripts/validate-release-approval.mjs', [fixture.candidateRoot, fixture.approvalPath, fixture.evidencePath], { env: { ...fixture.env, ...envOverride } });
    assert.notEqual(result.status, 0, label);
    assert.match(`${result.stdout}\n${result.stderr}`, expected, label);
  }

  const fakeGitFixture = JSON.parse(readFileSync(fixture.fakeGitFixturePath, 'utf8'));
  fakeGitFixture.tagObjectSha = '3'.repeat(40);
  writeFileSync(fixture.fakeGitFixturePath, `${JSON.stringify(fakeGitFixture, null, 2)}\n`);
  const gitObjectAttack = runNode(fixture.candidateRoot, 'scripts/validate-release-approval.mjs', [fixture.candidateRoot, fixture.approvalPath, fixture.evidencePath], { env: fixture.env });
  assert.notEqual(gitObjectAttack.status, 0);
  assert.match(`${gitObjectAttack.stdout}\n${gitObjectAttack.stderr}`, /workflow-reported tag object SHA does not match the Git tag object/);
});
