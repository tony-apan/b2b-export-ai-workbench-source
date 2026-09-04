import { createHash } from 'node:crypto';
import { cpSync, mkdirSync, readFileSync, renameSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, relative } from 'node:path';
import { spawnSync } from 'node:child_process';

// 动态读当前母库版本（避免硬编码漂移）
import { fileURLToPath as _fileURLToPath } from 'node:url';
const _caseRoot = _fileURLToPath(new URL('.', import.meta.url)).replace(/\/scripts\/tests\/$/, '/');
const currentMotherVersion = (() => {
  try {
    const vm = readFileSync(join(_caseRoot, 'VERSION.md'), 'utf8');
    const m = vm.match(/Version[：:]\s*`?([0-9][0-9a-z.-]+)`?/);
    return m ? m[1] : '0.0.0-working';
  } catch { return '0.0.0-working'; }
})();


const sha256Buffer = (value) => createHash('sha256').update(value).digest('hex');
const sha256File = (path) => sha256Buffer(readFileSync(path));
function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string' || typeof value === 'number') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
}
const canonicalDigest = (value) => sha256Buffer(canonicalJson(value));

function relocatePreparedArtifact(artifact) {
  const manifest = JSON.parse(readFileSync(join(artifact, 'MANIFEST.json'), 'utf8'));
  const destination = join(dirname(artifact), 'prepared', `v${manifest.version}`, manifest.content_digest);
  mkdirSync(dirname(destination), { recursive: true });
  renameSync(artifact, destination);
  return destination;
}

function outputOf(result) {
  return `${result.stdout ?? ''}${result.stderr ?? ''}`;
}

function shortOutput(result) {
  return outputOf(result).trim().split('\n').slice(-30).join('\n');
}

function ensureCompleted(result, label) {
  if (result.error) throw new Error(`${label} could not execute: ${result.error.message}`);
  if (result.signal) throw new Error(`${label} terminated by signal ${result.signal}\n${shortOutput(result)}`);
}

function assertRejected(result, expected, label) {
  ensureCompleted(result, label);
  if (result.status === 0) throw new Error(`${label} accepted the attack; expected rejection matching ${expected}\n${shortOutput(result)}`);
  if (!expected.test(outputOf(result))) throw new Error(`${label} failed for an unrelated reason; missing target diagnostic ${expected}\n${shortOutput(result)}`);
}

function assertAccepted(result, expected, label) {
  ensureCompleted(result, label);
  if (result.status !== 0) throw new Error(`${label} rejected a permitted boundary\n${shortOutput(result)}`);
  if (expected && !expected.test(outputOf(result))) throw new Error(`${label} passed without the expected proof marker ${expected}\n${shortOutput(result)}`);
}

function assertValidatorBaseline(root, script, args, expected, label, timeoutMs) {
  const result = run(root, script, args, { timeoutMs });
  assertAccepted(result, expected, `${label} baseline`);
}

function replaceExact(path, before, after) {
  const content = readFileSync(path, 'utf8');
  if (!content.includes(before)) throw new Error(`fixture mutation target not found in ${path}: ${before}`);
  writeFileSync(path, content.replace(before, after));
}

function removeLine(path, pattern) {
  const content = readFileSync(path, 'utf8');
  const next = content.replace(pattern, '');
  if (next === content) throw new Error(`fixture line was not found in ${path}: ${pattern}`);
  writeFileSync(path, next);
}

function mutateJson(path, mutate) {
  const value = JSON.parse(readFileSync(path, 'utf8'));
  mutate(value);
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

function run(root, script, args = [], options = {}) {
  return spawnSync(process.execPath, [join(root, script), ...args], {
    cwd: options.cwd ?? root,
    encoding: 'utf8',
    timeout: options.timeoutMs,
    env: { ...process.env, ...options.env },
  });
}

function contentDigest(root, files) {
  const hash = createHash('sha256');
  for (const file of files) hash.update(`${file}\0${sha256File(join(root, file))}\n`);
  return hash.digest('hex');
}

function writeArtifact(root, options = {}) {
  mkdirSync(root, { recursive: true });
  const kind = options.kind ?? 'mother';
  const contents = { ...(options.contents ?? { 'README.md': '# Fixture\n' }) };
  for (const scriptName of options.embeddedValidators ?? []) {
    contents[`scripts/${scriptName}`] = `#!/usr/bin/env node\nconsole.log(${JSON.stringify(`STUB_PASS: ${scriptName}`)});\n`;
  }
  for (const [relativePath, content] of Object.entries(contents)) {
    const target = join(root, relativePath);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, content);
  }
  const files = Object.keys(contents).sort();
  const packageId = kind === 'mother' ? 'b2b-export-ai-workbench-mother-library' : 'website-content-ops';
  const manifest = {
    package_id: packageId,
    package_kind: kind === 'mother' ? 'mother-library-release-candidate' : 'sub-library-release-candidate',
    version: '1.2.3',
    release_status: 'BLOCK',
    maturity_status: 'draft',
    verification_status: 'evidence-partial',
    release_scope: kind === 'mother' ? 'standalone-mother-library' : 'standalone-sub-library',
    license_status: 'pending',
    approval_required: true,
    approval_status: 'pending',
    tag_namespace: kind === 'mother' ? 'mother' : `sub-library/${packageId}`,
    source_commit: 'a'.repeat(40),
    source_dirty: false,
    durable_roots: kind === 'sub' ? [] : undefined,
    files,
    ...options.manifest,
  };
  if (manifest.qualification_state === undefined && manifest.release_status === 'Ready') manifest.qualification_state = 'prepared-unapproved';
  if (manifest.durable_roots === undefined) delete manifest.durable_roots;
  if (manifest.source_provenance === undefined) {
    const provenanceFiles = files.map((path) => {
      const digest = sha256File(join(root, path));
      return {
        path,
        ...(kind === 'sub' ? { repository_path: `sub-libraries/${packageId}/${path}` } : {}),
        sha256: digest,
        git_state: 'committed',
        commit_bound: true,
        commit_blob: createHash('sha1').update(`fixture:${path}`).digest('hex'),
        commit_sha256: digest,
      };
    });
    manifest.source_scope = kind === 'mother' ? 'repository-root' : `sub-libraries/${packageId}`;
    manifest.source_selected_dirty = false;
    manifest.source_commit_rebuildable = true;
    manifest.source_snapshot_kind = 'source-commit';
    manifest.source_provenance = {
      schema: 'git-file-provenance/v1',
      source_commit: manifest.source_commit,
      ...(kind === 'sub' ? { source_scope: manifest.source_scope } : {}),
      commit_rebuildable: true,
      selected_file_count: files.length,
      commit_bound_file_count: files.length,
      unbound_files: [],
      missing_commit_files: [],
      files: provenanceFiles,
    };
  }
  manifest.content_digest = contentDigest(root, files);
  writeFileSync(join(root, 'MANIFEST.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  const sums = [...files, 'MANIFEST.json'].map((file) => `${sha256File(join(root, file))}  ${file}`).join('\n');
  writeFileSync(join(root, 'SHA256SUMS'), `${sums}\n`);
  return manifest;
}

function rewriteArtifactManifest(root, mutate) {
  const manifestPath = join(root, 'MANIFEST.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  mutate(manifest);
  manifest.content_digest = contentDigest(root, manifest.files);
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  const sums = [...manifest.files, 'MANIFEST.json'].map((file) => `${sha256File(join(root, file))}  ${file}`).join('\n');
  writeFileSync(join(root, 'SHA256SUMS'), `${sums}\n`);
  return manifest;
}


function fixedEvidenceChecks(manifest, profile, tagName) {
  const outputSha = '0'.repeat(64);
  const common = (command) => ({ schema: 'release-check-result/v1', command, exit_code: 0, output_sha256: outputSha });
  const validation = (id, mode) => ({ id, status: 'pass', result: { ...common(`node scripts/${id}.mjs`), mode, checked_items: 1, error_count: 0 } });
  const checks = [
    {
      id: 'governance-tests', status: 'pass', result: {
        ...common('node scripts/run-governance-tests.mjs --timeout-ms 120000'),
        test_plan: ['scripts/run-governance-tests.mjs'], expected_tests: 1, passed_tests: 1, failed_tests: 0, skipped_tests: 0,
      },
    },
    validation('index-validation', 'strict'),
    validation('link-validation', 'release'),
    validation('document-id-validation', 'default'),
  ];
  if (profile === 'mother-release-v1') {
    checks.push(
      validation('log-validation', 'release'),
      validation('knowledge-chain-validation', 'release'),
      validation('mother-structure-validation', 'release'),
    );
  } else {
    checks.push(
      validation('sub-library-structure-validation', 'release'),
      {
        id: 'runtime-tests', status: 'pass', result: {
          ...common('node --test upload-media-browser.test.mjs article-image-binding.test.mjs article-content-formats.test.mjs article-operations.test.mjs'),
          test_plan: ['upload-media-browser.test.mjs', 'article-image-binding.test.mjs', 'article-content-formats.test.mjs', 'article-operations.test.mjs'],
          expected_tests: 160, passed_tests: 160, failed_tests: 0, skipped_tests: 0,
        },
      },
    );
  }
  checks.push(
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
        ...common('git verify-tag --raw'), tag_name: tagName, target_commit: manifest.source_commit,
        tag_object_sha: '1'.repeat(40), signer_fingerprint: 'A'.repeat(40), signature_status: 'trusted',
      },
    },
  );
  return checks;
}

function writeApproval(candidateRoot, path, mutate = () => {}) {
  const manifest = JSON.parse(readFileSync(join(candidateRoot, 'MANIFEST.json'), 'utf8'));
  const isMother = manifest.release_scope === 'standalone-mother-library';
  const scopeKind = isMother ? 'mother-library' : 'sub-library';
  const namespace = isMother ? 'mother' : `sub-library/${manifest.package_id}`;
  const approval = {
    schema: 'release-approval/v1',
    approval_id: 'APR-GOVERNANCE-FIXTURE-0001',
    decision: 'approved',
    scope: {
      kind: scopeKind,
      id: manifest.package_id,
      package_kind: manifest.package_kind,
    },
    source: {
      commit: manifest.source_commit,
      dirty: false,
    },
    candidate: {
      content_digest: manifest.content_digest,
      manifest_sha256: sha256File(join(candidateRoot, 'MANIFEST.json')),
      sha256sums_sha256: sha256File(join(candidateRoot, 'SHA256SUMS')),
      immutable_locator: `https://github.com/fixture/repository/releases/download/v${manifest.version}/${manifest.content_digest}/candidate`,
    },
    validation: {
      profile: isMother ? 'mother-release-v1' : 'sub-library-release-v1',
      evidence_digest_algorithm: 'sha256-canonical-json-v1',
      evidence_bundle: `${basename(path)}.evidence.json`,
      evidence_digest: '',
      completed_at: '2026-07-28T00:01:00Z',
    },
    approval: {
      approved_by: 'Tony Human Reviewer',
      approved_at: '2026-07-28T00:00:00Z',
      basis_ref: 'review-record:fixture-0001',
    },
    tag: {
      name: `${namespace}/v${manifest.version}`,
      target_commit: manifest.source_commit,
    },
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
    checks: fixedEvidenceChecks(manifest, approval.validation.profile, approval.tag.name),
  };
  approval.validation.evidence_digest = canonicalDigest(evidence);
  mutate(approval, manifest, evidence);
  writeFileSync(join(dirname(path), approval.validation.evidence_bundle), `${JSON.stringify(evidence, null, 2)}\n`);
  writeFileSync(path, `${JSON.stringify(approval, null, 2)}\n`);
}

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

function writeCanonicalTagApproval(candidateRoot, approvalPath, mutate = () => {}) {
  writeApproval(candidateRoot, approvalPath);
  const approval = JSON.parse(readFileSync(approvalPath, 'utf8'));
  const evidencePath = join(dirname(approvalPath), approval.validation.evidence_bundle);
  const evidence = JSON.parse(readFileSync(evidencePath, 'utf8'));
  const manifest = JSON.parse(readFileSync(join(candidateRoot, 'MANIFEST.json'), 'utf8'));
  approval.tag.object_sha = '1'.repeat(40);
  approval.tag.signer_fingerprint = 'A'.repeat(40);
  approval.tag.annotation_schema = 'release-tag-annotation/v1';
  approval.tag.approval_binding_digest_algorithm = 'sha256-canonical-approval-binding-v1';
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
  approval.tag.annotation_sha256 = sha256Buffer(annotationText);
  const tagCheck = evidence.checks.find((check) => check.id === 'tag-signature');
  Object.assign(tagCheck.result, {
    tag_object_sha: approval.tag.object_sha,
    signer_fingerprint: approval.tag.signer_fingerprint,
    annotation_schema: approval.tag.annotation_schema,
    annotation_sha256: approval.tag.annotation_sha256,
    approval_binding_digest_algorithm: approval.tag.approval_binding_digest_algorithm,
    approval_binding_sha256: approval.tag.approval_binding_sha256,
    approval_id: approval.approval_id,
    scope_kind: approval.scope.kind,
    scope_id: approval.scope.id,
    version: manifest.version,
    candidate_content_digest: manifest.content_digest,
  });
  const fixture = { approval, evidence, manifest, annotation, annotationText, evidencePath };
  mutate(fixture);
  approval.validation.evidence_digest = canonicalDigest(evidence);
  writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`);
  writeFileSync(approvalPath, `${JSON.stringify(approval, null, 2)}\n`);
  return {
    ...fixture,
    env: {
      RELEASE_ACTUAL_TAG_OBJECT_SHA: approval.tag.object_sha,
      RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT: approval.tag.signer_fingerprint,
      RELEASE_ACTUAL_TAG_ANNOTATION_SHA256: sha256Buffer(fixture.annotationText),
      RELEASE_ACTUAL_TAG_ANNOTATION_BASE64: Buffer.from(fixture.annotationText, 'utf8').toString('base64'),
      RELEASE_ACTUAL_APPROVAL_BINDING_SHA256: approval.tag.approval_binding_sha256,
    },
  };
}

function createTarArchive(sourceRoot, archivePath) {
  mkdirSync(dirname(archivePath), { recursive: true });
  const result = spawnSync('tar', ['-czf', archivePath, '-C', sourceRoot, '.'], { encoding: 'utf8' });
  ensureCompleted(result, 'fixture archive creation');
  if (result.status !== 0) throw new Error(`fixture archive creation failed\n${shortOutput(result)}`);
  writeFileSync(`${archivePath}.sha256`, `${sha256File(archivePath)}  ${basename(archivePath)}\n`);
}

function extractTarArchive(archivePath, targetRoot) {
  rmSync(targetRoot, { recursive: true, force: true });
  mkdirSync(targetRoot, { recursive: true });
  const result = spawnSync('tar', ['-xzf', archivePath, '-C', targetRoot], { encoding: 'utf8' });
  ensureCompleted(result, 'fixture archive extraction');
  if (result.status !== 0) throw new Error(`fixture archive extraction failed\n${shortOutput(result)}`);
}

function createQualificationFixture(root, name, options = {}) {
  const kind = options.kind ?? 'mother';
  let candidate = join(root, `.governance-fixtures/${name}-candidate`);
  writeArtifact(candidate, {
    kind,
    contents: { 'README.md': `# ${name}\n` },
    manifest: {
      release_status: 'Ready',
      maturity_status: 'stable',
      verification_status: 'e2e-pass',
      license_status: 'cleared',
      approval_status: 'pending',
      ...(kind === 'mother' ? { runtime_applicability: 'none', runtime_contract: null } : {}),
    },
  });
  candidate = relocatePreparedArtifact(candidate);
  const approvalPath = join(root, `.governance-fixtures/${name}-approval.json`);
  const canonical = writeCanonicalTagApproval(candidate, approvalPath, options.mutateApproval);
  if (kind === 'mother') {
    const artifactIndex = canonical.evidence.checks.findIndex((check) => check.id === 'artifact-validation');
    canonical.evidence.checks.splice(artifactIndex, 0, {
      id: 'runtime-applicability',
      status: 'pass',
      result: {
        schema: 'release-check-result/v1',
        command: 'node scripts/generate-release-evidence.mjs --internal-check mother-runtime-applicability',
        exit_code: 0,
        output_sha256: '0'.repeat(64),
        applicability: 'none',
        contract_path: null,
        contract_present: false,
        status: 'runtime_not_applicable',
        reason: 'mother-library-machine-contract-declares-none',
      },
    });
    canonical.approval.validation.evidence_digest = canonicalDigest(canonical.evidence);
    writeFileSync(canonical.evidencePath, `${JSON.stringify(canonical.evidence, null, 2)}\n`);
    writeFileSync(approvalPath, `${JSON.stringify(canonical.approval, null, 2)}\n`);
  }
  const archivePath = join(root, `.governance-fixtures/${name}.tar.gz`);
  createTarArchive(options.archiveSource ?? candidate, archivePath);
  const verifiedTreeRoot = join(root, `.governance-fixtures/${name}-verified-tree`);
  extractTarArchive(archivePath, verifiedTreeRoot);
  const manifest = JSON.parse(readFileSync(join(candidate, 'MANIFEST.json'), 'utf8'));
  const runtime = kind === 'sub'
    ? {
        QUALIFICATION_RUNTIME_STATUS: 'runtime_verified',
        QUALIFICATION_RUNTIME_REASON: 'trusted-sub-library-runtime-profile',
        QUALIFICATION_RUNTIME_IMAGE_DIGEST: `sha256:${'e'.repeat(64)}`,
        QUALIFICATION_TEST_PLAN_JSON: '["upload-media-browser.test.mjs","article-image-binding.test.mjs","article-content-formats.test.mjs","article-operations.test.mjs"]',
        QUALIFICATION_EXPECTED_TESTS: '160', QUALIFICATION_PASSED_TESTS: '160',
        QUALIFICATION_FAILED_TESTS: '0', QUALIFICATION_SKIPPED_TESTS: '0',
      }
    : {
        QUALIFICATION_RUNTIME_STATUS: 'runtime_not_applicable',
        QUALIFICATION_RUNTIME_REASON: 'mother-library-machine-contract-declares-none',
        QUALIFICATION_RUNTIME_IMAGE_DIGEST: '', QUALIFICATION_TEST_PLAN_JSON: '[]',
        QUALIFICATION_EXPECTED_TESTS: '0', QUALIFICATION_PASSED_TESTS: '0',
        QUALIFICATION_FAILED_TESTS: '0', QUALIFICATION_SKIPPED_TESTS: '0',
      };
  const env = {
    QUALIFICATION_SCOPE: kind === 'sub' ? 'sub-library' : 'mother-library',
    QUALIFICATION_PACKAGE_ID: manifest.package_id,
    QUALIFICATION_VERSION: manifest.version,
    QUALIFICATION_CONTENT_DIGEST: manifest.content_digest,
    QUALIFICATION_WORKFLOW_SHA: 'b'.repeat(40),
    QUALIFICATION_RUN_ID: '12345',
    QUALIFICATION_RUN_ATTEMPT: '1',
    QUALIFICATION_CANDIDATE_COMMIT: manifest.source_commit,
    QUALIFICATION_TAG_OBJECT_SHA: canonical.approval.tag.object_sha,
    QUALIFICATION_TAG_NAME: canonical.approval.tag.name,
    QUALIFICATION_SIGNER_FINGERPRINT: canonical.approval.tag.signer_fingerprint,
    QUALIFICATION_TAG_ANNOTATION_SHA256: canonical.approval.tag.annotation_sha256,
    QUALIFICATION_TAG_ANNOTATION_BASE64: Buffer.from(canonical.annotationText, 'utf8').toString('base64'),
    QUALIFICATION_APPROVAL_BINDING_SHA256: canonical.approval.tag.approval_binding_sha256,
    QUALIFICATION_TIMESTAMP: '2026-07-29T00:00:00Z',
    ...runtime,
  };
  const outputPath = join(root, `.governance-fixtures/${name}-QUALIFICATION-ATTESTATION.json`);
  const args = [
    '--candidate', candidate,
    '--verified-tree', verifiedTreeRoot,
    '--archive', archivePath,
    '--checksum', `${archivePath}.sha256`,
    '--approval', approvalPath,
    '--evidence', canonical.evidencePath,
    '--output', outputPath,
  ];
  return { candidate, approvalPath, archivePath, checksumPath: `${archivePath}.sha256`, verifiedTreeRoot, manifest, canonical, env, outputPath, args };
}

function runQualification(root, fixture, timeoutMs, env = fixture.env, args = fixture.args) {
  return run(root, 'scripts/create-qualification-attestation.mjs', args, { timeoutMs, env });
}

function syncIndexes(root, timeoutMs) {
  const result = run(root, 'scripts/sync-indexes.mjs', [], { timeoutMs });
  assertAccepted(result, /INDEXES_SYNCED:/, 'fixture index synchronization');
}

const releaseValidatorStubs = [
  'validate-indexes.mjs',
  'validate-links.mjs',
  'validate-logs.mjs',
  'validate-knowledge-chain.mjs',
  'validate-mother-library.mjs',
];

export const governanceCases = new Map([
  ['frontmatter-missing-description', {
    title: 'Missing required description is rejected by metadata validation',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'Markdown metadata', timeoutMs);
      const path = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      removeLine(path, /^description:.*\n/m);
      // The fixture starts from an intentionally dirty repository snapshot.
      // Run bottom-up synchronization twice so parent indexes observe child
      // metadata updated during the first pass without mutating the real tree.
      syncIndexes(root, timeoutMs);
      syncIndexes(root, timeoutMs);
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /BLOCK: missing description: wiki\/20_concepts\/id-0001-search-intent\.md/, 'front matter description gate');
    },
  }],
  ['frontmatter-missing-sources', {
    title: 'Missing required sources is rejected by metadata validation',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'Markdown metadata', timeoutMs);
      const path = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      removeLine(path, /^sources:.*\n/m);
      syncIndexes(root, timeoutMs);
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /BLOCK: missing required metadata field sources: wiki\/20_concepts\/id-0001-search-intent\.md/, 'front matter sources gate');
    },
  }],
  ['frontmatter-sources-scalar', {
    title: 'Sources must remain a machine-readable inline string array',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'Markdown metadata', timeoutMs);
      const path = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      replaceExact(path, 'sources: ["../10_sources/SRC-20260628-GOOGLE-SEARCH-OFFICIAL.md", "User direction on 2026-07-26"]', 'sources: unknown');
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /BLOCK: sources must be an inline array of unique non-empty quoted strings: wiki\/20_concepts\/id-0001-search-intent\.md/, 'front matter array shape gate');
    },
  }],
  ['frontmatter-duplicate-key', {
    title: 'Duplicate top-level metadata keys are rejected',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'Markdown metadata', timeoutMs);
      const path = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      replaceExact(path, 'owner: "AI"', 'owner: "AI"\nowner: "Human"');
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /BLOCK: duplicate metadata key owner: wiki\/20_concepts\/id-0001-search-intent\.md/, 'duplicate front matter key gate');
    },
  }],
  ['frontmatter-template-leak', {
    title: 'Unresolved generator template placeholders in front matter are rejected',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-mother-library.mjs', [], /STRUCTURE_PASS:/, 'mother library structure', timeoutMs);
      const path = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      replaceExact(path, 'title: "Search Intent"', 'title: "{d.split("/")[1].replace(".md","")} 日志"');
      const result = run(root, 'scripts/validate-mother-library.mjs', [], { timeoutMs });
      assertRejected(result, /unresolved template placeholder in front matter: wiki\/20_concepts\/id-0001-search-intent\.md/, 'front matter template leak gate');
    },
  }],
  ['frontmatter-related-missing-path', {
    title: 'Related metadata paths must resolve inside the repository',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'Markdown metadata', timeoutMs);
      const path = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      replaceExact(path, 'related: ["index.md", "../40_business/id-0012-customer-pain-map.md", "../30_playbooks/id-0011-seo-content.md", "../30_playbooks/id-0010-geo-ai-search.md", "../50_channels/seo/index.md", "../50_channels/geo-ai-search/index.md", "../_templates/customer-voice-to-search-intent.md"]', 'related: ["missing-governance-target.md"]');
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /BLOCK: related path is missing or escapes root: wiki\/20_concepts\/id-0001-search-intent\.md -> missing-governance-target\.md/, 'related path gate');
    },
  }],
  ['frontmatter-unknown-type', {
    title: 'Unknown Markdown type is rejected by the authoritative enum',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'Markdown metadata', timeoutMs);
      const path = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      replaceExact(path, 'type: "concept"', 'type: "fabricated-governance-type"');
      syncIndexes(root, timeoutMs);
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /BLOCK: unknown type fabricated-governance-type: wiki\/20_concepts\/id-0001-search-intent\.md;/, 'front matter type enum gate');
    },
  }],
  ['index-grandchild-entry', {
    title: 'A parent index cannot hand-add a grandchild into the generated direct-entry block',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'hierarchical index', timeoutMs);
      const path = join(root, 'wiki/index.md');
      replaceExact(path, '<!-- INDEX:END -->', '| ID-0001 | [forged grandchild](20_concepts/id-0001-search-intent.md) | 越级条目 | concept | Working | 不应出现 | forged |\n\n<!-- INDEX:END -->');
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /generated index blocks are stale: STALE_INDEXES:.*wiki\/index\.md/s, 'hierarchical index gate');
    },
  }],
  ['index-manual-grandchild-entry', {
    title: 'A parent index cannot hide recursive grandchild links outside the generated block',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'hierarchical index', timeoutMs);
      const path = join(root, 'wiki/index.md');
      replaceExact(path, '<!-- INDEX:END -->', '<!-- INDEX:END -->\n\n- [forged manual grandchild](20_concepts/id-0001-search-intent.md)');
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /BLOCK: index manual area recursively links to non-direct descendant: wiki\/index\.md -> 20_concepts\/id-0001-search-intent\.md/, 'manual recursive index gate');
    },
  }],
  ['index-last-updated-stale', {
    title: 'An index date cannot be older than its newest direct entry',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'index date freshness', timeoutMs);
      const path = join(root, 'wiki/index.md');
      const content = readFileSync(path, 'utf8');
      const next = content.replace(/^last_updated: "\d{4}-\d{2}-\d{2}"$/m, 'last_updated: "2026-01-01"');
      if (next === content) throw new Error(`fixture last_updated field was not found in ${path}`);
      writeFileSync(path, next);
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /BLOCK: index last_updated 2026-01-01 is older than direct entry \d{4}-\d{2}-\d{2}: wiki\/index\.md <- wiki\//, 'index metadata freshness gate');
    },
  }],
  ['index-stale-description', {
    title: 'A metadata change without index regeneration is rejected as stale',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-indexes.mjs', ['--check'], /INDEX_VALIDATION_PASS:/, 'generated index freshness', timeoutMs);
      const path = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      replaceExact(path, 'description: "面向把客户语言和搜索证据转成页面任务的人与 AI，说明意图识别、页面映射和验证指标；不把单次聊天或 query 假设当作市场事实。"', 'description: "这是一个故意不重建索引的治理测试描述，用于确认陈旧索引会被准确阻断。"');
      const result = run(root, 'scripts/validate-indexes.mjs', ['--check'], { timeoutMs });
      assertRejected(result, /generated index blocks are stale: STALE_INDEXES:.*wiki\/20_concepts\/index\.md/s, 'stale index gate');
    },
  }],
  ['document-id-duplicate-same-scope', {
    title: 'Duplicate stable IDs inside the mother scope are rejected',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-document-ids.mjs', [], /DOCUMENT_ID_PASS:/, 'document ID', timeoutMs);
      const source = join(root, 'wiki/20_concepts/id-0001-search-intent.md');
      const target = join(root, 'wiki/20_concepts/id-0001-governance-duplicate.md');
      writeFileSync(target, readFileSync(source, 'utf8').replace('# Search Intent', '# Duplicate Fixture'));
      const result = run(root, 'scripts/validate-document-ids.mjs', [], { timeoutMs });
      assertRejected(result, /BLOCK: duplicate stable ID mother:ID-0001:/, 'same-scope document ID gate');
    },
  }],
  ['document-id-duplicate-cross-scope-allowed', {
    title: 'The same stable ID remains legal in an independent sub-library scope',
    expected: 'accept',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-document-ids.mjs', [], /DOCUMENT_ID_PASS:/, 'document ID', timeoutMs);
      const target = join(root, 'sub-libraries/website-content-ops/KNOWLEDGE/id-0999-scope-fixture.md');
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, `---\ndoc_id: "ID-0999"\ntitle: "Independent Scope Fixture"\ndescription: "验证母库和独立子库可以各自拥有 ID-0999，而不会把两个发布 scope 错误合并。"\ntype: "concept"\nstatus: "Working"\nowner: "AI"\ncreated: "2026-07-29"\nlast_updated: "2026-07-29"\nsources: ["governance regression fixture"]\nrelated: []\nwhen_to_read: "验证子库编号 scope 隔离时读取。"\nkeywords: ["document id", "scope", "sub-library"]\n---\n# Independent Scope Fixture\n`);
      const result = run(root, 'scripts/validate-document-ids.mjs', [], { timeoutMs });
      assertAccepted(result, /DOCUMENT_ID_PASS:/, 'cross-scope document ID boundary');
    },
  }],
  ['synthetic-real-verification-claim', {
    title: 'Synthetic source cannot claim real-world verification',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-knowledge-chain.mjs', [], /KNOWLEDGE_CHAIN_STRUCTURE_PASS:/, 'knowledge chain', timeoutMs);
      const path = join(root, 'raw/10_conversations/src-20260728-0001-knowledge-base-structure-closure.md');
      replaceExact(path, 'verification_status: "structure-pass"', 'verification_status: "production-verified"');
      const result = run(root, 'scripts/validate-knowledge-chain.mjs', [], { timeoutMs });
      assertRejected(result, /synthetic source cannot claim real-world verification \(production-verified\)/, 'synthetic evidence gate');
    },
  }],
  ['log-event-date-mismatch', {
    title: 'Event ID date must match the daily-log path date',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-logs.mjs', ['--release'], /LOG_VALIDATION_PASS/, 'release log', timeoutMs);
      const path = join(root, 'wiki/00_meta/logs/2026/07/2026-07-28.md');
      replaceExact(path, 'EVT-20260728-0001', 'EVT-20260727-0001');
      const result = run(root, 'scripts/validate-logs.mjs', ['--release'], { timeoutMs });
      assertRejected(result, /event_id date `2026-07-27` does not match daily-log path date `2026-07-28`/, 'log date gate');
    },
  }],
  ['log-duplicate-event-id', {
    title: 'Duplicate event IDs are rejected in release mode',
    expected: 'reject',
    run({ root, timeoutMs }) {
      assertValidatorBaseline(root, 'scripts/validate-logs.mjs', ['--release'], /LOG_VALIDATION_PASS/, 'release log', timeoutMs);
      const path = join(root, 'wiki/00_meta/logs/2026/07/2026-07-28.md');
      replaceExact(path, 'EVT-20260728-0002', 'EVT-20260728-0001');
      const result = run(root, 'scripts/validate-logs.mjs', ['--release'], { timeoutMs });
      assertRejected(result, /duplicate event_id `EVT-20260728-0001`:/, 'duplicate log event gate');
    },
  }],
  ['artifact-unknown-extension', {
    title: 'Unknown artifact extensions are rejected after checksums are made valid',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const artifact = join(root, '.governance-fixtures/artifact-unknown-extension');
      writeArtifact(artifact, { embeddedValidators: ['validate-mother-library.mjs'] });
      assertValidatorBaseline(root, 'scripts/validate-artifact.mjs', [artifact], /ARTIFACT_PASS:/, 'mother artifact boundary', timeoutMs);
      writeFileSync(join(artifact, 'unexpected.exe'), 'registered but forbidden\n');
      rewriteArtifactManifest(artifact, (manifest) => { manifest.files.push('unexpected.exe'); manifest.files.sort(); });
      const result = run(root, 'scripts/validate-artifact.mjs', [artifact], { timeoutMs });
      assertRejected(result, /FAIL: unsupported artifact file extension: unexpected\.exe/, 'artifact extension allowlist');
    },
  }],
  ['artifact-local-absolute-path', {
    title: 'Machine-local absolute paths are rejected after artifact integrity passes',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const artifact = join(root, '.governance-fixtures/artifact-absolute-path');
      writeArtifact(artifact, { embeddedValidators: ['validate-mother-library.mjs'] });
      assertValidatorBaseline(root, 'scripts/validate-artifact.mjs', [artifact], /ARTIFACT_PASS:/, 'mother artifact boundary', timeoutMs);
      const forbiddenLocalPath = `/${['Users', 'tony', 'private', 'customer.md'].join('/')}`;
      replaceExact(join(artifact, 'README.md'), '# Fixture\n', `# Fixture\nSource: ${forbiddenLocalPath}\n`);
      rewriteArtifactManifest(artifact, () => {});
      const result = run(root, 'scripts/validate-artifact.mjs', [artifact], { timeoutMs });
      assertRejected(result, /FAIL: possible local absolute path in artifact: README\.md/, 'artifact path redaction gate');
    },
  }],
  ['artifact-manifest-path-preflight', {
    title: 'Artifact manifest paths are rejected before any traversal or symlink-backed content read',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const traversal = join(root, '.governance-fixtures/artifact-manifest-traversal');
      writeArtifact(traversal);
      mutateJson(join(traversal, 'MANIFEST.json'), (manifest) => {
        manifest.files = ['../missing-private.md'];
        manifest.content_digest = '0'.repeat(64);
      });
      writeFileSync(
        join(traversal, 'SHA256SUMS'),
        `${sha256File(join(traversal, 'MANIFEST.json'))}  MANIFEST.json\n`,
      );
      assertRejected(
        run(root, 'scripts/validate-artifact.mjs', [traversal], { timeoutMs }),
        /FAIL: unsafe manifest path: \.\.\/missing-private\.md/,
        'manifest traversal preflight',
      );

      const symlinkArtifact = join(root, '.governance-fixtures/artifact-manifest-symlink');
      writeArtifact(symlinkArtifact);
      const outside = join(root, '.governance-fixtures/artifact-manifest-symlink-target.md');
      writeFileSync(outside, '# outside bytes\n');
      rmSync(join(symlinkArtifact, 'README.md'));
      symlinkSync(outside, join(symlinkArtifact, 'README.md'));
      assertRejected(
        run(root, 'scripts/validate-artifact.mjs', [symlinkArtifact], { timeoutMs }),
        /FAIL: manifest path must not traverse a symlink: README\.md/,
        'manifest symlink preflight',
      );
    },
  }],
  ['approval-ai-placeholder-rejected', {
    title: 'An explicit AI placeholder cannot approve a release',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const candidate = join(root, '.governance-fixtures/approval-ai-placeholder');
      writeArtifact(candidate, { manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
      const approvalPath = join(root, '.governance-fixtures/approval-ai-placeholder.json');
      writeApproval(candidate, approvalPath);
      assertValidatorBaseline(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], /APPROVAL_RECORD_PASS:/, 'release approval binding', timeoutMs);
      mutateJson(approvalPath, (approval) => { approval.approval.approved_by = 'Codex'; });
      const result = run(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], { timeoutMs });
      assertRejected(result, /approved_by must not contain an AI\/system identity token/, 'AI approval identity gate');
    },
  }],
  ['approval-decorated-ai-name-rejected', {
    title: 'Decorated AI and system identities cannot masquerade as human reviewers',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const scopes = [
        { kind: 'mother', validator: 'scripts/validate-release-approval.mjs' },
        { kind: 'sub', validator: 'scripts/validate-release-approval.mjs' },
      ];
      const identities = ['Codex Agent 1', 'Claude reviewer', 'AI assistant', 'system bot'];
      for (const { kind, validator } of scopes) {
        const candidate = join(root, `.governance-fixtures/approval-decorated-ai-name-${kind}`);
        writeArtifact(candidate, { kind, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        const approvalPath = join(root, `.governance-fixtures/approval-decorated-ai-name-${kind}.json`);
        writeApproval(candidate, approvalPath);
        assertValidatorBaseline(root, validator, [candidate, approvalPath], /APPROVAL_RECORD_PASS:/, `${kind} release approval binding`, timeoutMs);
        for (const identity of identities) {
          writeApproval(candidate, approvalPath, (approval) => { approval.approval.approved_by = identity; });
          const result = run(root, validator, [candidate, approvalPath], { timeoutMs });
          assertRejected(result, /approved_by must not contain an AI\/system identity token/, `${kind} decorated AI reviewer gate: ${identity}`);
        }
      }
    },
  }],
  ['approval-self-asserted-check-set-rejected', {
    title: 'A self-asserted pass object cannot replace the fixed scope validation profile',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const scopes = [
        { kind: 'mother', validator: 'scripts/validate-release-approval.mjs' },
        { kind: 'sub', validator: 'scripts/validate-release-approval.mjs' },
      ];
      for (const { kind, validator } of scopes) {
        const candidate = join(root, `.governance-fixtures/approval-self-asserted-${kind}`);
        writeArtifact(candidate, { kind, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        const approvalPath = join(root, `.governance-fixtures/approval-self-asserted-${kind}.json`);
        writeApproval(candidate, approvalPath);
        const approval = JSON.parse(readFileSync(approvalPath, 'utf8'));
        const evidencePath = join(dirname(approvalPath), approval.validation.evidence_bundle);
        const evidence = JSON.parse(readFileSync(evidencePath, 'utf8'));
        evidence.checks = [{ id: 'self-asserted', status: 'pass', result: { claimed: true } }];
        writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`);
        approval.validation.evidence_digest = canonicalDigest(evidence);
        writeFileSync(approvalPath, `${JSON.stringify(approval, null, 2)}\n`);
        const result = run(root, validator, [candidate, approvalPath, evidencePath], { timeoutMs });
        assertRejected(result, /missing required .* check|unsupported .* check/, `${kind} fixed evidence profile gate`);
      }
    },
  }],
  ['approval-scope-crosswire', {
    title: 'A mother approval cannot be reused for a sub-library candidate',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const candidate = join(root, '.governance-fixtures/approval-scope-crosswire');
      writeArtifact(candidate, { kind: 'sub', manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
      const approvalPath = join(root, '.governance-fixtures/approval-scope-crosswire.json');
      writeApproval(candidate, approvalPath);
      assertValidatorBaseline(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], /APPROVAL_RECORD_PASS:/, 'release approval binding', timeoutMs);
      mutateJson(approvalPath, (approval) => {
        approval.scope = { kind: 'mother-library', id: 'b2b-export-ai-workbench-mother-library', package_kind: 'mother-library-release-candidate' };
        approval.validation.profile = 'mother-release-v1';
        approval.tag.name = 'mother/v1.2.3';
      });
      const result = run(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], { timeoutMs });
      assertRejected(result, /approval scope\.kind mother-library does not match candidate sub-library/, 'approval scope binding');
    },
  }],
  ['approval-tag-crosswire', {
    title: 'Approval tag namespace must match the exact release scope',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const candidate = join(root, '.governance-fixtures/approval-tag-crosswire');
      writeArtifact(candidate, { manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
      const approvalPath = join(root, '.governance-fixtures/approval-tag-crosswire.json');
      writeApproval(candidate, approvalPath);
      assertValidatorBaseline(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], /APPROVAL_RECORD_PASS:/, 'release approval binding', timeoutMs);
      mutateJson(approvalPath, (approval) => { approval.tag.name = 'sub-library/website-content-ops/v1.2.3'; });
      const result = run(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], { timeoutMs });
      assertRejected(result, /approval tag\.name must be mother\/v1\.2\.3/, 'approval tag namespace binding');
    },
  }],
  ['approval-digest-crosswire', {
    title: 'Approval digest and immutable HTTPS locator are bound to the exact release candidate',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const scopes = [
        { kind: 'mother', validator: 'scripts/validate-release-approval.mjs' },
        { kind: 'sub', validator: 'scripts/validate-release-approval.mjs' },
      ];
      for (const { kind, validator } of scopes) {
        const candidate = join(root, `.governance-fixtures/approval-digest-crosswire-${kind}`);
        const manifest = writeArtifact(candidate, { kind, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        const approvalPath = join(root, `.governance-fixtures/approval-digest-crosswire-${kind}.json`);
        writeApproval(candidate, approvalPath);
        assertValidatorBaseline(root, validator, [candidate, approvalPath], /APPROVAL_RECORD_PASS:/, `${kind} release approval binding`, timeoutMs);

        mutateJson(approvalPath, (approval) => { approval.candidate.content_digest = 'c'.repeat(64); });
        const digestResult = run(root, validator, [candidate, approvalPath], { timeoutMs });
        assertRejected(digestResult, /approval candidate\.content_digest does not match candidate MANIFEST\.json/, `${kind} approval digest binding`);

        const version = `v${manifest.version}`;
        const digest = manifest.content_digest;
        const attacks = [
          ['file URL', `file:///releases/${version}/${digest}/candidate`, /immutable_locator must use https/],
          ['literal parent segment', `https://downloads.example.com/releases/${version}/../${digest}/candidate`, /immutable_locator must not contain dot path segments/],
          ['encoded parent segment', `https://downloads.example.com/releases/${version}/%2e%2e/${digest}/candidate`, /immutable_locator must not contain dot path segments/],
          ['double-encoded parent segment', `https://downloads.example.com/releases/${version}/%252e%252e/${digest}/candidate`, /immutable_locator must not contain dot path segments/],
          ['malformed percent encoding', `https://downloads.example.com/releases/${version}/%zz/${digest}/candidate`, /immutable_locator contains malformed percent encoding/],
          ['localhost', `https://localhost/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['private hostname', `https://artifacts.internal/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['single-label hostname', `https://artifacts/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['private IPv4', `https://192.168.1.10/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['link-local IPv4', `https://169.254.169.254/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['loopback IPv6', `https://[::1]/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['private IPv6', `https://[fd00::10]/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['link-local IPv6', `https://[fe80::10]/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['IPv4-mapped private IPv6', `https://[::ffff:c0a8:10a]/releases/${version}/${digest}/candidate`, /immutable_locator must not target a local, private, loopback, or link-local host/],
          ['URL credentials', `https://reviewer:secret@downloads.example.com/releases/${version}/${digest}/candidate`, /immutable_locator must not contain URL credentials/],
          ['query', `https://downloads.example.com/releases/${version}/${digest}/candidate?download=1`, /immutable_locator must not contain query or fragment/],
          ['fragment', `https://downloads.example.com/releases/${version}/${digest}/candidate#asset`, /immutable_locator must not contain query or fragment/],
          ['mutable marker', `https://downloads.example.com/releases/${version}/${digest}/latest/candidate`, /immutable_locator contains a forbidden mutable or credential marker/],
          ['credential marker', `https://downloads.example.com/releases/${version}/${digest}/access-token/candidate`, /immutable_locator contains a forbidden mutable or credential marker/],
          ['missing version', `https://downloads.example.com/releases/${digest}/candidate`, /immutable_locator path must contain candidate version as a complete segment/],
          ['missing digest', `https://downloads.example.com/releases/${version}/candidate`, /immutable_locator path must contain candidate content_digest as a complete segment/],
        ];
        for (const [name, immutableLocator, expected] of attacks) {
          writeApproval(candidate, approvalPath, (approval) => { approval.candidate.immutable_locator = immutableLocator; });
          const result = run(root, validator, [candidate, approvalPath], { timeoutMs });
          assertRejected(result, expected, `${kind} immutable locator gate: ${name}`);
        }

        writeApproval(candidate, approvalPath, (approval) => {
          approval.candidate.immutable_locator = `https://downloads.example.com/releases/${version}/${digest}/template/candidate`;
        });
        const markerBoundary = run(root, validator, [candidate, approvalPath], { timeoutMs });
        assertAccepted(markerBoundary, /APPROVAL_RECORD_PASS:/, `${kind} immutable locator marker boundary`);
      }
    },
  }],
  ['approval-evidence-content-binding', {
    title: 'Approval evidence digest must match the actual canonical evidence bundle content',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const candidate = join(root, '.governance-fixtures/approval-evidence-content-binding');
      writeArtifact(candidate, { manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
      const approvalPath = join(root, '.governance-fixtures/approval-evidence-content-binding.json');
      writeApproval(candidate, approvalPath);
      assertValidatorBaseline(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], /APPROVAL_RECORD_PASS:/, 'canonical evidence bundle binding', timeoutMs);

      mutateJson(approvalPath, (approval) => { approval.validation.evidence_digest = '0'.repeat(64); });
      const arbitraryDigest = run(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], { timeoutMs });
      assertRejected(arbitraryDigest, /validation\.evidence_digest does not match the canonical evidence bundle content/, 'arbitrary evidence digest');

      writeApproval(candidate, approvalPath);
      const approval = JSON.parse(readFileSync(approvalPath, 'utf8'));
      const evidencePath = join(dirname(approvalPath), approval.validation.evidence_bundle);
      mutateJson(evidencePath, (evidence) => { evidence.checks[0].result.fixture = false; });
      const tamperedEvidence = run(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], { timeoutMs });
      assertRejected(tamperedEvidence, /validation\.evidence_digest does not match the canonical evidence bundle content/, 'tampered evidence bundle');

      const chronologyApprovalPath = join(root, '.governance-fixtures/approval-evidence-reversed-chronology.json');
      writeApproval(candidate, chronologyApprovalPath, (approval) => {
        approval.approval.approved_at = '2026-07-28T00:02:00Z';
      });
      assertRejected(
        run(root, 'scripts/validate-release-approval.mjs', [candidate, chronologyApprovalPath], { timeoutMs }),
        /approval approved_at must not be later than validation\.completed_at/,
        'approval timestamp after trusted evidence completion',
      );

      const subCandidate = join(root, '.governance-fixtures/approval-evidence-legacy-runtime-count');
      writeArtifact(subCandidate, {
        kind: 'sub',
        manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' },
      });
      for (const staleCount of [120, 135, 137, 156, 158]) {
        const subApprovalPath = join(root, `.governance-fixtures/approval-evidence-runtime-count-${staleCount}.json`);
        writeApproval(subCandidate, subApprovalPath);
        const subApproval = JSON.parse(readFileSync(subApprovalPath, 'utf8'));
        const subEvidencePath = join(dirname(subApprovalPath), subApproval.validation.evidence_bundle);
        const subEvidence = JSON.parse(readFileSync(subEvidencePath, 'utf8'));
        const runtimeCheck = subEvidence.checks.find((check) => check.id === 'runtime-tests');
        runtimeCheck.result.expected_tests = staleCount;
        runtimeCheck.result.passed_tests = staleCount;
        writeFileSync(subEvidencePath, `${JSON.stringify(subEvidence, null, 2)}\n`);
        subApproval.validation.evidence_digest = canonicalDigest(subEvidence);
        writeFileSync(subApprovalPath, `${JSON.stringify(subApproval, null, 2)}\n`);
        assertRejected(
          run(root, 'scripts/validate-release-approval.mjs', [subCandidate, subApprovalPath, subEvidencePath], { timeoutMs }),
          /approval evidence runtime-tests expected_tests must be 160/,
          `non-canonical ${staleCount}-test approval evidence`,
        );
      }
    },
  }],
  ['approval-mother-provenance-binding', {
    title: 'Mother approval rejects self-consistent candidate manifests that do not prove every packaged file is commit-bound',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const attacks = [
        {
          id: 'rebuildability-flag',
          mutate(manifest) { manifest.source_commit_rebuildable = false; },
          expected: /source_commit_rebuildable must be true/,
        },
        {
          id: 'unbound-file',
          mutate(manifest) {
            manifest.source_provenance.files[0].git_state = 'untracked';
            manifest.source_provenance.files[0].commit_bound = false;
            manifest.source_provenance.unbound_files = [manifest.source_provenance.files[0]];
            manifest.source_provenance.commit_rebuildable = false;
          },
          expected: /source_provenance\.commit_rebuildable must be true/,
        },
        {
          id: 'forged-commit-content',
          mutate(manifest) { manifest.source_provenance.files[0].commit_sha256 = 'b'.repeat(64); },
          expected: /does not bind identical candidate and commit content/,
        },
      ];
      for (const attack of attacks) {
        const candidate = join(root, `.governance-fixtures/approval-mother-provenance-${attack.id}`);
        writeArtifact(candidate, { contents: { 'README.md': `# ${attack.id}\n` }, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        rewriteArtifactManifest(candidate, attack.mutate);
        const approvalPath = join(root, `.governance-fixtures/approval-mother-provenance-${attack.id}.json`);
        writeApproval(candidate, approvalPath);
        const result = run(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath], { timeoutMs });
        assertRejected(result, attack.expected, `mother approval provenance attack: ${attack.id}`);
      }
    },
  }],
  ['approval-sub-library-provenance-binding', {
    title: 'Sub-library approval rejects candidate files that are not bound to repository-relative commit provenance',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const attacks = [
        {
          id: 'wrong-repository-path',
          mutate(manifest) { manifest.source_provenance.files[0].repository_path = `sub-libraries/other/${manifest.source_provenance.files[0].path}`; },
          expected: /repository_path must be sub-libraries\/website-content-ops\//,
        },
        {
          id: 'unbound-file',
          mutate(manifest) {
            manifest.source_provenance.files[0].git_state = 'ignored';
            manifest.source_provenance.files[0].commit_bound = false;
            manifest.source_provenance.unbound_files = [manifest.source_provenance.files[0]];
            manifest.source_provenance.commit_rebuildable = false;
          },
          expected: /source_provenance\.commit_rebuildable must be true/,
        },
        {
          id: 'forged-commit-content',
          mutate(manifest) { manifest.source_provenance.files[0].commit_sha256 = 'b'.repeat(64); },
          expected: /does not bind identical candidate and commit content/,
        },
      ];
      for (const attack of attacks) {
        const candidate = join(root, `.governance-fixtures/approval-sub-provenance-${attack.id}`);
        writeArtifact(candidate, { kind: 'sub', manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        rewriteArtifactManifest(candidate, attack.mutate);
        const approvalPath = join(root, `.governance-fixtures/approval-sub-provenance-${attack.id}.json`);
        writeApproval(candidate, approvalPath);
        const evidencePath = join(dirname(approvalPath), JSON.parse(readFileSync(approvalPath, 'utf8')).validation.evidence_bundle);
        const result = run(root, 'scripts/validate-release-approval.mjs', [candidate, approvalPath, evidencePath], { timeoutMs });
        assertRejected(result, attack.expected, `sub-library approval provenance attack: ${attack.id}`);
      }
    },
  }],
  ['mother-builder-commit-provenance', {
    title: 'Mother builder rejects ignored, untracked, and modified selected inputs when commit provenance is required',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const git = (args) => spawnSync('git', args, { cwd: root, encoding: 'utf8' });
      const mustGit = (args, label) => {
        const result = git(args);
        ensureCompleted(result, label);
        if (result.status !== 0) throw new Error(`${label} failed\n${shortOutput(result)}`);
      };
      const ignorePath = 'scripts/ignored-provenance-fixture.mjs';
      const untrackedPath = 'scripts/untracked-provenance-fixture.mjs';
      const gitignorePath = join(root, '.gitignore');
      const originalGitignore = readFileSync(gitignorePath, 'utf8');
      writeFileSync(gitignorePath, `${originalGitignore.replace(/\n?$/, '\n')}${ignorePath}\n`);
      mustGit(['init', '-q'], 'initialize provenance fixture Git repository');
      mustGit(['config', 'user.name', 'Governance Fixture'], 'configure fixture Git user');
      mustGit(['config', 'user.email', 'fixture@example.invalid'], 'configure fixture Git email');
      mustGit(['add', '-f', '.'], 'stage provenance fixture baseline');
      mustGit(['commit', '-qm', 'fixture baseline'], 'commit provenance fixture baseline');

      writeFileSync(join(root, ignorePath), 'export default "ignored attack";\n');
      const ignored = run(root, 'scripts/build-mother-release.mjs', ['--require-commit-provenance'], { timeoutMs });
      assertRejected(ignored, /ignored-provenance-fixture\.mjs\(ignored\)/, 'ignored selected source provenance');
      rmSync(join(root, ignorePath), { force: true });

      writeFileSync(join(root, untrackedPath), 'export default "untracked attack";\n');
      const untracked = run(root, 'scripts/build-mother-release.mjs', ['--require-commit-provenance'], { timeoutMs });
      assertRejected(untracked, /untracked-provenance-fixture\.mjs\(untracked\)/, 'untracked selected source provenance');
      rmSync(join(root, untrackedPath), { force: true });

      const readmePath = join(root, 'README.md');
      const originalReadme = readFileSync(readmePath, 'utf8');
      writeFileSync(readmePath, `${originalReadme}\n<!-- modified provenance attack -->\n`);
      const modified = run(root, 'scripts/build-mother-release.mjs', ['--require-commit-provenance'], { timeoutMs });
      assertRejected(modified, /README\.md\(modified\)/, 'modified selected source provenance');
      writeFileSync(readmePath, originalReadme);
      const matrixArtifactRoot = join(root, '.governance-fixtures/mother-provenance-shape');
      writeArtifact(matrixArtifactRoot, {
        contents: { 'README.md': '# Fixture\n', 'SECOND.md': '# Second fixture\n' },
      });
      const artifactManifestPath = join(matrixArtifactRoot, 'MANIFEST.json');
      const baselineArtifactManifest = readFileSync(artifactManifestPath, 'utf8');
      const assertProvenanceMutationRejected = (mutate, expectedDiagnostics, label) => {
        writeFileSync(artifactManifestPath, baselineArtifactManifest);
        rewriteArtifactManifest(matrixArtifactRoot, mutate);
        const result = run(root, 'scripts/validate-artifact.mjs', [matrixArtifactRoot], { timeoutMs });
        const diagnostics = Array.isArray(expectedDiagnostics) ? expectedDiagnostics : [expectedDiagnostics];
        assertRejected(result, diagnostics[0], label);
        for (const expected of diagnostics.slice(1)) {
          if (!expected.test(outputOf(result))) throw new Error(`${label} missed diagnostic ${expected}\n${shortOutput(result)}`);
        }
      };
      assertProvenanceMutationRejected(
        (manifest) => {
          manifest.source_provenance.schema = 'git-file-provenance/v2';
          manifest.source_provenance.selected_file_count += 1;
          manifest.source_provenance.commit_bound_file_count += 1;
          manifest.source_provenance.unbound_files = [{ ...manifest.source_provenance.files[0] }];
          manifest.source_provenance.missing_commit_files = [manifest.source_provenance.files[0].path];
        },
        [
          /source_provenance\.schema must be git-file-provenance\/v1/,
          /source_provenance\.selected_file_count does not match file records/,
          /source_provenance\.commit_bound_file_count does not match file records/,
          /source_provenance\.unbound_files does not match unbound file records/,
          /source_provenance\.missing_commit_files overlaps packaged file/,
        ],
        'ordinary mother artifact rejects forged provenance schema and summaries',
      );
      assertProvenanceMutationRejected(
        (manifest) => { manifest.source_provenance.files[1].path = manifest.source_provenance.files[0].path; },
        [
          /source_provenance\.files has duplicate path/,
          /source_provenance\.files missing path/,
        ],
        'ordinary mother artifact rejects duplicate and missing provenance paths',
      );
      assertProvenanceMutationRejected(
        (manifest) => {
          manifest.source_provenance.files[0] = { ...manifest.source_provenance.files[0], path: 'extra-provenance-record.md' };
        },
        [
          /source_provenance\.files has unmanifested path: extra-provenance-record\.md/,
          /source_provenance\.files missing path/,
          /source_provenance\.files paths must exactly match MANIFEST\.json files in deterministic order/,
        ],
        'ordinary mother artifact rejects extra, missing, and position-drifted provenance paths',
      );
      assertProvenanceMutationRejected(
        (manifest) => { [manifest.source_provenance.files[0], manifest.source_provenance.files[1]] = [manifest.source_provenance.files[1], manifest.source_provenance.files[0]]; },
        /source_provenance\.files paths must exactly match MANIFEST\.json files in deterministic order/,
        'ordinary mother artifact rejects reordered provenance paths',
      );
      rmSync(matrixArtifactRoot, { recursive: true, force: true });
      const ordinaryBuild = run(root, 'scripts/build-mother-release.mjs', [], { timeoutMs });
      assertAccepted(ordinaryBuild, /RELEASE_CANDIDATE:/, 'ordinary mother provenance artifact baseline');
      if (!/ARTIFACT_PASS:/.test(outputOf(ordinaryBuild))) {
        throw new Error(`ordinary mother provenance build did not prove embedded artifact validation\n${shortOutput(ordinaryBuild)}`);
      }
      const artifactRoot = join(root, 'dist/mother/latest');
      const toolsPath = join(artifactRoot, 'sub-libraries/website-content-ops/TOOLS-INDEX.md');
      writeFileSync(toolsPath, `${readFileSync(toolsPath, 'utf8')}\n<!-- safe artifact provenance mutation -->\n`);
      rewriteArtifactManifest(artifactRoot, () => {});
      const staleReceipt = run(root, 'scripts/validate-artifact.mjs', [artifactRoot], { timeoutMs });
      assertRejected(staleReceipt, /source provenance file SHA mismatch: sub-libraries\/website-content-ops\/TOOLS-INDEX\.md/, 'ordinary mother artifact stale provenance receipt');

      rewriteArtifactManifest(artifactRoot, (manifest) => {
        const record = manifest.source_provenance.files.find((item) => item.path === 'sub-libraries/website-content-ops/TOOLS-INDEX.md');
        if (!record) throw new Error('TOOLS.md provenance record missing');
        record.sha256 = sha256File(toolsPath);
      });
      const forgedReceipt = run(root, 'scripts/validate-artifact.mjs', [artifactRoot], { timeoutMs });
      assertRejected(forgedReceipt, /source provenance commit SHA-256 mismatch: sub-libraries\/website-content-ops\/TOOLS-INDEX\.md/, 'ordinary mother artifact forged candidate provenance digest');
    },
  }],
  ['release-artifact-dirty-source', {
    title: 'Formal qualification rejects a dirty prepared source independently of checksum validity',
    expected: 'reject',
    run({ root, timeoutMs }) {
      let artifact = join(root, '.governance-fixtures/release-dirty-source');
      writeArtifact(artifact, { embeddedValidators: releaseValidatorStubs, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
      artifact = relocatePreparedArtifact(artifact);
      const noSidecar = run(root, 'scripts/validate-artifact.mjs', ['--release', artifact], { timeoutMs });
      assertRejected(noSidecar, /release qualification requires RELEASE_APPROVAL_PATH sidecar/, 'prepared release sidecar baseline');
      rewriteArtifactManifest(artifact, (manifest) => { manifest.source_dirty = true; });
      const result = run(root, 'scripts/validate-artifact.mjs', ['--release', artifact], { timeoutMs });
      assertRejected(result, /FAIL: prepared\/release artifact must be built from a clean source worktree/, 'dirty source release gate');
    },
  }],
  ['release-final-state-requires-sidecar', {
    title: 'Only a frozen Ready pending candidate can enter qualification and it still requires sidecars',
    expected: 'reject',
    run({ root, timeoutMs }) {
      let artifact = join(root, '.governance-fixtures/release-ready-without-sidecar');
      writeArtifact(artifact, { embeddedValidators: releaseValidatorStubs, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
      artifact = relocatePreparedArtifact(artifact);
      const result = run(root, 'scripts/validate-artifact.mjs', ['--release', artifact], { timeoutMs });
      assertRejected(result, /FAIL: release qualification requires RELEASE_APPROVAL_PATH sidecar/, 'Ready prepared candidate sidecar gate');
      rewriteArtifactManifest(artifact, (manifest) => { manifest.release_status = 'Published'; });
      const forged = run(root, 'scripts/validate-artifact.mjs', ['--release', artifact], { timeoutMs });
      assertRejected(forged, /candidate release_status must be Ready|approval.*release_status must be Ready/, 'candidate cannot self-assert Published before qualification');
    },
  }],
  ['ordinary-final-state-artifact-requires-sidecar', {
    title: 'Ordinary inspection never qualifies an artifact; explicit qualification remains sidecar-bound',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const scopes = [
        { kind: 'mother', validator: 'scripts/validate-artifact.mjs', embeddedValidators: ['validate-mother-library.mjs'] },
        { kind: 'sub', validator: 'sub-libraries/website-content-ops/scripts/validate-artifact.mjs', embeddedValidators: ['validate-sub-library.mjs'] },
      ];
      for (const { kind, validator, embeddedValidators } of scopes) {
        let artifact = join(root, `.governance-fixtures/ordinary-${kind}-prepared`);
        writeArtifact(artifact, { kind, embeddedValidators, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        const inspect = run(root, validator, [artifact], { timeoutMs });
        assertAccepted(inspect, /ARTIFACT_PASS:/, `${kind} ordinary inspection`);
        artifact = relocatePreparedArtifact(artifact);
        const qualify = run(root, validator, ['--release', artifact], { timeoutMs });
        assertRejected(qualify, /FAIL: release qualification requires RELEASE_APPROVAL_PATH sidecar/, `${kind} explicit qualification sidecar gate`);
      }
    },
  }],
  ['mother-sub-artifact-pass-isolation', {
    title: 'Mother and sub-library artifact PASS cannot be reused across package kinds',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const subArtifact = join(root, '.governance-fixtures/sub-through-mother-validator');
      writeArtifact(subArtifact, { kind: 'sub', embeddedValidators: ['validate-sub-library.mjs'] });
      assertValidatorBaseline(root, 'sub-libraries/website-content-ops/scripts/validate-artifact.mjs', [subArtifact], /ARTIFACT_PASS:/, 'sub-library artifact scope', timeoutMs);
      const motherResult = run(root, 'scripts/validate-artifact.mjs', [subArtifact], { timeoutMs });
      assertRejected(motherResult, /FAIL: MANIFEST\.json package_kind must be mother-library-release-candidate/, 'mother artifact scope isolation');

      const motherArtifact = join(root, '.governance-fixtures/mother-through-sub-validator');
      writeArtifact(motherArtifact, { kind: 'mother', embeddedValidators: ['validate-mother-library.mjs'] });
      assertValidatorBaseline(root, 'scripts/validate-artifact.mjs', [motherArtifact], /ARTIFACT_PASS:/, 'mother artifact scope', timeoutMs);
      const subResult = run(root, 'sub-libraries/website-content-ops/scripts/validate-artifact.mjs', [motherArtifact], { timeoutMs });
      assertRejected(subResult, /FAIL: MANIFEST\.json package_kind must be sub-library-release-candidate/, 'sub-library artifact scope isolation');
    },
  }],
  ['release-router-unknown-tag', {
    title: 'Unknown release tag namespaces are rejected before any scope runs',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const result = run(root, 'scripts/resolve-release-scope.mjs', ['test-tag'], { timeoutMs });
      assertRejected(result, /BLOCK: unknown release tag namespace: test-tag/, 'unknown release tag route');
    },
  }],
  ['release-router-bare-tag', {
    title: 'Bare version tags cannot bypass mother and sub-library namespaces',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const result = run(root, 'scripts/resolve-release-scope.mjs', ['v0.1.1-draft'], { timeoutMs });
      assertRejected(result, /BLOCK: unknown release tag namespace: v0\.1\.1-draft/, 'bare release tag route');
    },
  }],
  ['release-router-mother-version-mismatch', {
    title: 'Mother release tags must match the exact current VERSION.md value',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const result = run(root, 'scripts/resolve-release-scope.mjs', ['mother/v9.9.9'], { timeoutMs });
      assertRejected(result, new RegExp(`BLOCK: mother tag version mismatch: expected mother\\/v${currentMotherVersion}, got mother\\/v9\\.9\\.9`), 'mother release version route');
    },
  }],
  ['release-router-unregistered-sub-library', {
    title: 'Unregistered sub-library tags cannot select an arbitrary repository path',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const result = run(root, 'scripts/resolve-release-scope.mjs', ['sub-library/unknown/v1.0.0'], { timeoutMs });
      assertRejected(result, /BLOCK: sub-library unknown must have exactly one registry entry; found 0/, 'unregistered sub-library route');
    },
  }],
  ['release-router-mother-scope', {
    title: 'A valid mother tag resolves to only the mother-library scope',
    expected: 'accept',
    run({ root, timeoutMs }) {
      const outputPath = join(root, '.governance-fixtures/router-mother-output.txt');
      mkdirSync(dirname(outputPath), { recursive: true });
      const result = run(root, 'scripts/resolve-release-scope.mjs', [`mother/v${currentMotherVersion}`], { timeoutMs, env: { GITHUB_OUTPUT: outputPath } });
      assertAccepted(result, new RegExp(`RELEASE_SCOPE_PASS: mother-library mother\\/v${currentMotherVersion}`), 'mother release route');
      const output = readFileSync(outputPath, 'utf8');
      if (!new RegExp(`^scope=mother-library\npackage_id=b2b-export-ai-workbench-mother-library\npath=\\.\nversion=${currentMotherVersion}\nrelease_tag=mother\\/v${currentMotherVersion}\n$`).test(output)) {
        throw new Error(`mother route emitted unexpected or multiple scope outputs:
${output}`);
      }
    },
  }],
  ['release-router-sub-library-scope', {
    title: 'A sub-library route rejects historical or colliding candidate identities and accepts only a distinct assigned current version',
    expected: 'accept',
    run({ root, timeoutMs }) {
      const outputPath = join(root, '.governance-fixtures/router-sub-output.txt');
      mkdirSync(dirname(outputPath), { recursive: true });
      const historicalTag = 'sub-library/website-content-ops/v0.3.2-preview.1';

      const manifestPath = join(root, 'sub-libraries/website-content-ops/MANIFEST.md');
      const versionPath = join(root, 'sub-libraries/website-content-ops/VERSION.md');
      const registryPath = join(root, 'sub-libraries/registry.json');
      // 场景 1：先把真实候选态（Preview/0.4.0-preview.1，2026-09-03 起的仓默认）临时降回 unassigned，验证路由拒绝未分配身份
      for (const path of [manifestPath, versionPath]) {
        replaceExact(path, 'current_candidate_identity: "website-content-ops-0.4.0-preview.1"', 'current_candidate_identity: "unassigned"');
        replaceExact(path, 'current_candidate_version: "0.4.0-preview.1"', 'current_candidate_version: null');
      }
      mutateJson(registryPath, (registry) => {
        const entry = registry.entries.find((item) => item.id === 'website-content-ops');
        if (!entry) throw new Error('website-content-ops registry fixture entry missing');
        entry.current_candidate_identity = 'unassigned';
        entry.current_candidate_version = null;
      });

      const unassigned = run(root, 'scripts/resolve-release-scope.mjs', [historicalTag], { timeoutMs, env: { GITHUB_OUTPUT: outputPath } });
      assertRejected(unassigned, /current candidate identity\/version is unassigned/, 'unassigned sub-library candidate route');

      // 场景 2：升到 Ready + 已分配身份，但候选版本与历史版本碰撞 → 拒绝
      for (const path of [manifestPath, versionPath]) {
        replaceExact(path, 'release_status: "Preview"', 'release_status: "Ready"');
        replaceExact(path, 'current_candidate_identity: "unassigned"', 'current_candidate_identity: "assigned"');
        replaceExact(path, 'current_candidate_snapshot: "clean-committed-tree"', 'current_candidate_snapshot: "source-commit"');
        replaceExact(path, 'current_candidate_version: null', 'current_candidate_version: "0.3.2-preview.1"');
      }
      mutateJson(registryPath, (registry) => {
        const entry = registry.entries.find((item) => item.id === 'website-content-ops');
        if (!entry) throw new Error('website-content-ops registry fixture entry missing');
        entry.release_status = 'Ready';
        entry.current_candidate_identity = 'assigned';
        entry.current_candidate_snapshot = 'source-commit';
        entry.current_candidate_version = '0.3.2-preview.1';
      });

      const collision = run(root, 'scripts/resolve-release-scope.mjs', [historicalTag], { timeoutMs, env: { GITHUB_OUTPUT: outputPath } });
      assertRejected(collision, /current_candidate_version collides with immutable historical_published_version/, 'historical/current sub-library version collision');

      for (const path of [manifestPath, versionPath]) {
        replaceExact(path, 'current_candidate_version: "0.3.2-preview.1"', 'current_candidate_version: "0.3.3-preview.1"');
      }
      mutateJson(registryPath, (registry) => {
        const entry = registry.entries.find((item) => item.id === 'website-content-ops');
        if (!entry) throw new Error('website-content-ops registry fixture entry missing');
        entry.current_candidate_version = '0.3.3-preview.1';
      });

      const releaseTag = 'sub-library/website-content-ops/v0.3.3-preview.1';
      const result = run(root, 'scripts/resolve-release-scope.mjs', [releaseTag], { timeoutMs, env: { GITHUB_OUTPUT: outputPath } });
      assertAccepted(result, /RELEASE_SCOPE_PASS: sub-library website-content-ops sub-library\/website-content-ops\/v0\.3\.3-preview\.1/, 'assigned sub-library candidate release route');
      const output = readFileSync(outputPath, 'utf8');
      if (!/^scope=sub-library\npackage_id=website-content-ops\npath=sub-libraries\/website-content-ops\nversion=0\.3\.3-preview\.1\nhistorical_published_version=0\.3\.2-preview\.1\nhistorical_published_tag=v0\.3\.2-preview\.1\ncurrent_candidate_identity=assigned\ncurrent_candidate_snapshot=source-commit\ncurrent_candidate_version=0\.3\.3-preview\.1\nrelease_tag=sub-library\/website-content-ops\/v0\.3\.3-preview\.1\n$/.test(output)) {
        throw new Error(`sub-library route emitted unexpected or multiple scope outputs:
${output}`);
      }
    },
  }],
  ['approval-trigger-tag-crosswire', {
    title: 'The workflow trigger tag must match the approval sidecar tag for both scopes',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const scopes = [
        { kind: 'mother', validator: 'scripts/validate-release-approval.mjs', expectedTag: 'mother/v1.2.3' },
        { kind: 'sub', validator: 'scripts/validate-release-approval.mjs', expectedTag: 'sub-library/website-content-ops/v1.2.3' },
      ];
      for (const { kind, validator, expectedTag } of scopes) {
        const candidate = join(root, `.governance-fixtures/approval-trigger-${kind}`);
        writeArtifact(candidate, { kind, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        const approvalPath = join(root, `.governance-fixtures/approval-trigger-${kind}.json`);
        writeApproval(candidate, approvalPath);
        const baseline = run(root, validator, [candidate, approvalPath], { timeoutMs, env: { RELEASE_TRIGGER_TAG: expectedTag } });
        assertAccepted(baseline, /APPROVAL_RECORD_PASS:/, `${kind} trigger-tag approval baseline`);
        const result = run(root, validator, [candidate, approvalPath], { timeoutMs, env: { RELEASE_TRIGGER_TAG: 'mother/v9.9.9' } });
        assertRejected(result, /RELEASE_TRIGGER_TAG mother\/v9\.9\.9 does not match approval tag\.name/, `${kind} trigger-tag crosswire`);
      }
    },
  }],
  ['approval-strict-trigger-required', {
    title: 'Strict Git tag verification cannot run without an explicit workflow trigger tag',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const scopes = [
        { kind: 'mother', validator: 'scripts/validate-release-approval.mjs' },
        { kind: 'sub', validator: 'scripts/validate-release-approval.mjs' },
      ];
      for (const { kind, validator } of scopes) {
        const candidate = join(root, `.governance-fixtures/approval-strict-trigger-${kind}`);
        writeArtifact(candidate, { kind, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        const approvalPath = join(root, `.governance-fixtures/approval-strict-trigger-${kind}.json`);
        writeApproval(candidate, approvalPath);
        const result = run(root, validator, [candidate, approvalPath], { timeoutMs, env: { RELEASE_REQUIRE_GIT_TAG: '1', RELEASE_TRIGGER_TAG: '' } });
        assertRejected(result, /RELEASE_TRIGGER_TAG is required when strict Git tag verification is enabled/, `${kind} strict trigger-tag requirement`);
      }
    },
  }],

  ['runtime-profile-control-files', {
    title: 'Candidate npm controls at the adapter or any ancestor cannot replace the trusted runtime-test control plane',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const adapter = 'sub-libraries/website-content-ops/ADAPTERS/cms/allincms';
      const helperArgs = (candidateRoot, subjectName) => [
        '--trusted-root', root,
        '--candidate-root', candidateRoot,
        '--package-id', 'website-content-ops',
        '--subject-root', join(root, `.governance-fixtures/${subjectName}`),
      ];
      const buildCandidate = (name) => {
        const candidateRoot = join(root, `.governance-fixtures/${name}`);
        const target = join(candidateRoot, adapter);
        mkdirSync(dirname(target), { recursive: true });
        cpSync(join(root, adapter), target, {
          recursive: true,
          filter(source) {
            return !source.split('/').includes('node_modules');
          },
        });
        const baseline = run(root, 'scripts/verify-runtime-test-profile.mjs', helperArgs(candidateRoot, `${name}-baseline-subject`), { timeoutMs });
        assertAccepted(baseline, /RUNTIME_TEST_SUBJECT_READY:/, `${name} baseline`);
        return candidateRoot;
      };

      const attacks = [
        {
          name: 'runtime-profile-npmrc',
          path: (candidateRoot) => join(candidateRoot, adapter, '.npmrc'),
          content: 'script-shell=/bin/true\n',
          expected: /runtime control file mismatch.*\.npmrc/,
          label: 'candidate adapter .npmrc override',
        },
        {
          name: 'runtime-profile-shrinkwrap',
          path: (candidateRoot) => join(candidateRoot, adapter, 'npm-shrinkwrap.json'),
          content: '{"lockfileVersion":3}\n',
          expected: /runtime control file mismatch.*npm-shrinkwrap\.json/,
          label: 'candidate adapter npm-shrinkwrap override',
        },
        {
          name: 'runtime-profile-root-npmrc',
          path: (candidateRoot) => join(candidateRoot, '.npmrc'),
          content: 'ignore-scripts=false\n',
          expected: /runtime control file mismatch.*\.npmrc/,
          label: 'candidate root .npmrc override',
        },
        {
          name: 'runtime-profile-root-package',
          path: (candidateRoot) => join(candidateRoot, 'package.json'),
          content: '{"workspaces":["sub-libraries/*"]}\n',
          expected: /runtime control file mismatch.*package\.json/,
          label: 'candidate root workspace package override',
        },
        {
          name: 'runtime-profile-parent-workspace',
          path: (candidateRoot) => join(candidateRoot, 'sub-libraries/website-content-ops/pnpm-workspace.yaml'),
          content: 'packages:\n  - ADAPTERS/**\n',
          expected: /runtime control file mismatch.*pnpm-workspace\.yaml/,
          label: 'candidate parent workspace override',
        },
      ];
      for (const attack of attacks) {
        const candidateRoot = buildCandidate(attack.name);
        const target = attack.path(candidateRoot);
        mkdirSync(dirname(target), { recursive: true });
        writeFileSync(target, attack.content);
        const result = run(root, 'scripts/verify-runtime-test-profile.mjs', helperArgs(candidateRoot, `${attack.name}-attack-subject`), { timeoutMs });
        assertRejected(result, attack.expected, attack.label);
      }
    },
  }],
  ['runtime-profile-symlink-boundaries', {
    title: 'Runtime profile rejects adapter and ancestor symlinks before reading candidate files',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const adapter = 'sub-libraries/website-content-ops/ADAPTERS/cms/allincms';
      const runProfile = (candidateRoot, subjectName) => run(root, 'scripts/verify-runtime-test-profile.mjs', [
        '--trusted-root', root,
        '--candidate-root', candidateRoot,
        '--package-id', 'website-content-ops',
        '--subject-root', join(root, `.governance-fixtures/${subjectName}`),
      ], { timeoutMs });

      const adapterLinkRoot = join(root, '.governance-fixtures/runtime-adapter-symlink');
      mkdirSync(dirname(join(adapterLinkRoot, adapter)), { recursive: true });
      symlinkSync(join(root, adapter), join(adapterLinkRoot, adapter), 'dir');
      assertRejected(
        runProfile(adapterLinkRoot, 'runtime-adapter-symlink-subject'),
        /contains a non-directory or symlink ancestor/,
        'candidate adapter symlink to governance',
      );

      const parentLinkRoot = join(root, '.governance-fixtures/runtime-parent-symlink');
      const parent = join(parentLinkRoot, 'sub-libraries/website-content-ops');
      mkdirSync(parent, { recursive: true });
      symlinkSync(join(root, 'sub-libraries/website-content-ops/ADAPTERS'), join(parent, 'ADAPTERS'), 'dir');
      assertRejected(
        runProfile(parentLinkRoot, 'runtime-parent-symlink-subject'),
        /contains a non-directory or symlink ancestor/,
        'candidate adapter ancestor symlink to governance',
      );
    },
  }],
  ['runtime-subject-provenance-isolation', {
    title: 'Materialized runtime subject executes candidate implementation without a visible governance sibling',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const adapter = 'sub-libraries/website-content-ops/ADAPTERS/cms/allincms';
      const candidateRoot = join(root, '.governance-fixtures/runtime-reexport-candidate');
      const candidateAdapter = join(candidateRoot, adapter);
      mkdirSync(dirname(candidateAdapter), { recursive: true });
      cpSync(join(root, adapter), candidateAdapter, {
        recursive: true,
        filter(source) {
          return !source.split('/').includes('node_modules');
        },
      });
      const candidateSource = join(candidateAdapter, 'article-operations.mjs');
      const trustedSource = join(root, adapter, 'article-operations.mjs');
      let specifier = relative(dirname(candidateSource), trustedSource).split('\\').join('/');
      if (!specifier.startsWith('.')) specifier = `./${specifier}`;
      writeFileSync(candidateSource, `export * from ${JSON.stringify(specifier)};\n`);

      const directCandidate = spawnSync(process.execPath, [
        '--input-type=module',
        '--eval',
        "await import('./article-operations.mjs'); console.log('REEXPORT_RESOLVED')",
      ], {
        cwd: candidateAdapter,
        encoding: 'utf8',
        timeout: timeoutMs,
      });
      assertAccepted(directCandidate, /REEXPORT_RESOLVED/, 'candidate re-export attack in sibling layout');

      const subject = join(root, '.governance-fixtures/runtime-reexport-subject');
      const profile = run(root, 'scripts/verify-runtime-test-profile.mjs', [
        '--trusted-root', root,
        '--candidate-root', candidateRoot,
        '--package-id', 'website-content-ops',
        '--subject-root', subject,
      ], { timeoutMs });
      assertAccepted(profile, /RUNTIME_TEST_SUBJECT_READY:/, 'materialize candidate implementation with trusted tests');
      if (readFileSync(join(subject, 'article-operations.mjs'), 'utf8') !== readFileSync(candidateSource, 'utf8')) {
        throw new Error('runtime subject did not preserve the candidate implementation bytes');
      }
      if (readFileSync(join(subject, 'article-operations.test.mjs'), 'utf8') !== readFileSync(join(root, adapter, 'article-operations.test.mjs'), 'utf8')) {
        throw new Error('runtime subject did not use the trusted governance test bytes');
      }

      const isolatedSubject = spawnSync(process.execPath, [
        '--input-type=module',
        '--eval',
        "await import('./article-operations.mjs')",
      ], {
        cwd: subject,
        encoding: 'utf8',
        timeout: timeoutMs,
      });
      assertRejected(isolatedSubject, /ERR_MODULE_NOT_FOUND|Cannot find module/, 'candidate re-export cannot resolve governance from isolated subject');
    },
  }],
  ['tested-candidate-identity-binding', {
    title: 'Executable identity gate rejects mismatches and malformed values for every cross-job identity field',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const helper = 'scripts/verify-tested-candidate-identity.mjs';
      const commitA = 'a'.repeat(40);
      const commitB = 'b'.repeat(40);
      const tagA = 'c'.repeat(40);
      const tagB = 'd'.repeat(40);
      const baselineArgs = {
        'expected-commit': commitA,
        'expected-tag-object': tagA,
        'actual-commit': commitA,
        'actual-tag-object': tagA,
      };
      const toArgs = (values) => Object.entries(values).flatMap(([key, value]) => [`--${key}`, value]);
      const baseline = run(root, helper, toArgs(baselineArgs), { timeoutMs });
      assertAccepted(baseline, /TESTED_CANDIDATE_IDENTITY_PASS:/, 'matching runtime and qualification identity');

      const commitMismatch = run(root, helper, toArgs({ ...baselineArgs, 'actual-commit': commitB }), { timeoutMs });
      assertRejected(commitMismatch, /does not match the exact tag object and commit tested/, 'cross-job candidate commit mismatch');
      const tagMismatch = run(root, helper, toArgs({ ...baselineArgs, 'actual-tag-object': tagB }), { timeoutMs });
      assertRejected(tagMismatch, /does not match the exact tag object and commit tested/, 'cross-job annotated tag object mismatch');

      const invalidValues = ['', 'A'.repeat(40), 'g'.repeat(40), 'a'.repeat(39), 'a'.repeat(41), 'a'.repeat(63), 'a'.repeat(65)];
      for (const field of Object.keys(baselineArgs)) {
        for (const invalid of invalidValues) {
          const result = run(root, helper, toArgs({ ...baselineArgs, [field]: invalid }), { timeoutMs });
          assertRejected(result, new RegExp(`${field} must be a 40- or 64-character`), `${field} invalid object id length or alphabet`);
        }
      }
    },
  }],

  ['trusted-node-test-summary', {
    title: 'Trusted runtime evidence requires the exact final Node test plan and summary',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const helper = 'scripts/verify-node-test-summary.mjs';
      const validPath = join(root, '.governance-fixtures/node-test-valid.tap');
      mkdirSync(dirname(validPath), { recursive: true });
      writeFileSync(validPath, 'TAP version 13\n1..120\n# tests 120\n# pass 120\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n');
      const baseline = run(root, helper, ['--log', validPath, '--expected-tests', '120'], { timeoutMs });
      assertAccepted(baseline, /NODE_TEST_SUMMARY_PASS: tests=120/, 'trusted Node test summary baseline');

      const earlyExitPath = join(root, '.governance-fixtures/node-test-early-exit.tap');
      writeFileSync(earlyExitPath, '# tests 120\n# pass 120\n1..3\n# tests 3\n# pass 3\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n');
      const earlyExit = run(root, helper, ['--log', earlyExitPath, '--expected-tests', '120'], { timeoutMs });
      assertRejected(earlyExit, /test plan expected 120 tests but found 3/, 'candidate early process exit or forged pre-summary');

      const skippedPath = join(root, '.governance-fixtures/node-test-skipped.tap');
      writeFileSync(skippedPath, '1..120\n# tests 120\n# pass 119\n# fail 0\n# cancelled 0\n# skipped 1\n# todo 0\n');
      const skipped = run(root, helper, ['--log', skippedPath, '--expected-tests', '120'], { timeoutMs });
      assertRejected(skipped, /summary expected pass=120 but found 119/, 'candidate skipped-test summary');
    },
  }],
  ['two-phase-release-cli-boundaries', {
    title: 'Builders cannot rebuild and approve in one step or consume sidecars during prepare',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const builders = ['scripts/build-mother-release.mjs', 'sub-libraries/website-content-ops/scripts/build-release.mjs'];
      for (const builder of builders) {
        const retired = run(root, builder, ['--release'], { timeoutMs });
        assertRejected(retired, /builder --release is retired/, `${builder} retired release mode`);
        const sidecar = run(root, builder, ['--prepare', '--approval', '.governance-fixtures/forged-approval.json'], { timeoutMs });
        assertRejected(sidecar, /--prepare must not receive approval or evidence/, `${builder} prepare sidecar separation`);
      }
    },
  }],
  ['approval-canonical-tag-binding', {
    title: 'Canonical tag annotation, approval binding, actual tag identity and evidence receipt are inseparable',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const prepare = (name, mutate) => {
        let candidate = join(root, `.governance-fixtures/${name}-candidate`);
        writeArtifact(candidate, { contents: { 'README.md': `# ${name}\n` }, manifest: { release_status: 'Ready', maturity_status: 'stable', verification_status: 'e2e-pass', license_status: 'cleared', approval_status: 'pending' } });
        candidate = relocatePreparedArtifact(candidate);
        const approvalPath = join(root, `.governance-fixtures/${name}-approval.json`);
        const canonical = writeCanonicalTagApproval(candidate, approvalPath, mutate);
        return { candidate, approvalPath, canonical, args: [candidate, approvalPath, canonical.evidencePath] };
      };

      const baseline = prepare('canonical-tag-baseline');
      assertAccepted(
        run(root, 'scripts/validate-release-approval.mjs', baseline.args, { timeoutMs, env: baseline.canonical.env }),
        /APPROVAL_RECORD_PASS:/,
        'canonical tag binding baseline',
      );

      const nonCanonical = prepare('canonical-tag-whitespace', (fixture) => { fixture.annotationText = `${fixture.annotationText} `; });
      assertRejected(
        run(root, 'scripts/validate-release-approval.mjs', nonCanonical.args, { timeoutMs, env: nonCanonical.canonical.env }),
        /actual release tag annotation must use canonical JSON/,
        'non-canonical tag annotation whitespace',
      );

      const wrongBinding = prepare('canonical-tag-wrong-binding', (fixture) => {
        fixture.approval.tag.approval_binding_sha256 = 'f'.repeat(64);
      });
      assertRejected(
        run(root, 'scripts/validate-release-approval.mjs', wrongBinding.args, { timeoutMs, env: wrongBinding.canonical.env }),
        /approval_binding_sha256 does not match the canonical approval binding projection/,
        'forged approval binding digest',
      );

      const tagObjectCrosswire = prepare('canonical-tag-object-crosswire');
      assertRejected(
        run(root, 'scripts/validate-release-approval.mjs', tagObjectCrosswire.args, { timeoutMs, env: { ...tagObjectCrosswire.canonical.env, RELEASE_ACTUAL_TAG_OBJECT_SHA: '2'.repeat(40) } }),
        /actual tag object SHA does not match approval tag\.object_sha/,
        'workflow actual tag object crosswire',
      );

      const signerCrosswire = prepare('canonical-tag-signer-crosswire');
      assertRejected(
        run(root, 'scripts/validate-release-approval.mjs', signerCrosswire.args, { timeoutMs, env: { ...signerCrosswire.canonical.env, RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT: 'B'.repeat(40) } }),
        /actual tag signer does not match approval tag\.signer_fingerprint/,
        'workflow actual signer crosswire',
      );

      const evidenceCrosswire = prepare('canonical-tag-evidence-crosswire', (fixture) => {
        fixture.evidence.checks.find((check) => check.id === 'tag-signature').result.approval_id = 'APR-FORGED-EVIDENCE-0001';
      });
      assertRejected(
        run(root, 'scripts/validate-release-approval.mjs', evidenceCrosswire.args, { timeoutMs, env: evidenceCrosswire.canonical.env }),
        /approval evidence tag-signature approval_id must match the canonical tag annotation/,
        'tag evidence approval identity crosswire',
      );
    },
  }],
  ['qualification-archive-tree-equivalence', {
    title: 'Qualification rejects archive bytes, extracted trees and checksum sidecars that differ from the verified candidate tree',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const baseline = createQualificationFixture(root, 'archive-tree-baseline');
      assertAccepted(runQualification(root, baseline, timeoutMs), /QUALIFICATION_TREE_EQUIVALENCE_PASS:/, 'archive tree-equivalence baseline');

      const arbitrary = createQualificationFixture(root, 'archive-arbitrary-bytes');
      writeFileSync(arbitrary.archivePath, 'not a gzip tar archive\n');
      writeFileSync(arbitrary.checksumPath, `${sha256File(arbitrary.archivePath)}  ${basename(arbitrary.archivePath)}\n`);
      assertRejected(runQualification(root, arbitrary, timeoutMs), /archive cannot be listed as gzip-compressed tar/, 'arbitrary archive bytes');

      const alteredArchive = createQualificationFixture(root, 'archive-content-crosswire');
      const tamperedSource = join(root, '.governance-fixtures/archive-content-crosswire-source');
      cpSync(alteredArchive.candidate, tamperedSource, { recursive: true });
      writeFileSync(join(tamperedSource, 'README.md'), '# Tampered after candidate verification\n');
      createTarArchive(tamperedSource, alteredArchive.archivePath);
      assertRejected(runQualification(root, alteredArchive, timeoutMs), /archive bytes do not extract to the exact verified candidate tree/, 'archive content crosswire');

      const alteredVerifiedTree = createQualificationFixture(root, 'archive-verified-tree-crosswire');
      writeFileSync(join(alteredVerifiedTree.verifiedTreeRoot, 'README.md'), '# Not the candidate tree\n');
      assertRejected(runQualification(root, alteredVerifiedTree, timeoutMs), /archive-extracted tree is not byte\/type\/mode equivalent/, 'supplied verified tree crosswire');

      const wrongFilename = createQualificationFixture(root, 'archive-checksum-filename');
      writeFileSync(wrongFilename.checksumPath, `${sha256File(wrongFilename.archivePath)}  other.tar.gz\n`);
      assertRejected(runQualification(root, wrongFilename, timeoutMs), /archive checksum sidecar must contain exactly/, 'checksum filename crosswire');

      const multiline = createQualificationFixture(root, 'archive-checksum-multiline');
      writeFileSync(multiline.checksumPath, `${sha256File(multiline.archivePath)}  ${basename(multiline.archivePath)}\n${'0'.repeat(64)}  ignored.tar.gz\n`);
      assertRejected(runQualification(root, multiline, timeoutMs), /archive checksum sidecar must contain exactly/, 'checksum multiline prefix forgery');
    },
  }],
  ['qualification-runtime-contract', {
    title: 'Qualification uses exact machine-readable runtime applicability states instead of fabricated mother-library runtime tests',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const mother = createQualificationFixture(root, 'runtime-mother-baseline');
      assertAccepted(runQualification(root, mother, timeoutMs), /QUALIFICATION_ATTESTATION_PASS:/, 'mother runtime_not_applicable baseline');
      const motherAttestation = JSON.parse(readFileSync(mother.outputPath, 'utf8'));
      if (canonicalJson(motherAttestation.runtime) !== canonicalJson({
        status: 'runtime_not_applicable', applicable: false,
        reason: 'mother-library-machine-contract-declares-none', image_digest: null,
        test_plan: [], expected: 0, passed: 0, failed: 0, skipped: 0,
      })) throw new Error('mother attestation did not preserve the exact runtime_not_applicable contract');

      assertRejected(
        runQualification(root, mother, timeoutMs, { ...mother.env, QUALIFICATION_RUNTIME_STATUS: 'runtime_unknown' }),
        /QUALIFICATION_RUNTIME_STATUS is missing or invalid/,
        'unknown runtime lifecycle state',
      );
      assertRejected(
        runQualification(root, mother, timeoutMs, {
          ...mother.env,
          QUALIFICATION_RUNTIME_STATUS: 'runtime_verified',
          QUALIFICATION_RUNTIME_REASON: 'trusted-sub-library-runtime-profile',
          QUALIFICATION_RUNTIME_IMAGE_DIGEST: `sha256:${'e'.repeat(64)}`,
          QUALIFICATION_TEST_PLAN_JSON: '["fabricated-mother-runtime.test.mjs"]',
          QUALIFICATION_EXPECTED_TESTS: '1', QUALIFICATION_PASSED_TESTS: '1',
        }),
        /mother-library runtime contract must be the exact runtime_not_applicable/,
        'fabricated mother runtime tests',
      );

      const sub = createQualificationFixture(root, 'runtime-sub-baseline', { kind: 'sub' });
      assertAccepted(runQualification(root, sub, timeoutMs), /QUALIFICATION_ATTESTATION_PASS:/, 'sub-library runtime_verified baseline');
      assertRejected(
        runQualification(root, sub, timeoutMs, {
          ...sub.env,
          QUALIFICATION_RUNTIME_STATUS: 'runtime_not_applicable',
          QUALIFICATION_RUNTIME_REASON: 'mother-library-machine-contract-declares-none',
          QUALIFICATION_RUNTIME_IMAGE_DIGEST: '', QUALIFICATION_TEST_PLAN_JSON: '[]',
          QUALIFICATION_EXPECTED_TESTS: '0', QUALIFICATION_PASSED_TESTS: '0',
        }),
        /sub-library attestation must bind the trusted runtime_verified 160-test profile/,
        'sub-library runtime_not_applicable forgery',
      );
      assertRejected(
        runQualification(root, sub, timeoutMs, { ...sub.env, QUALIFICATION_PASSED_TESTS: '159' }),
        /runtime test counters do not represent an exact clean pass/,
        'sub-library incomplete 159-of-160 runtime count',
      );
      assertRejected(
        runQualification(root, sub, timeoutMs, {
          ...sub.env,
          QUALIFICATION_EXPECTED_TESTS: '120',
          QUALIFICATION_PASSED_TESTS: '120',
        }),
        /sub-library attestation must bind the trusted runtime_verified 160-test profile/,
        'stale 120-test qualification profile',
      );
      assertRejected(
        runQualification(root, sub, timeoutMs, {
          ...sub.env,
          QUALIFICATION_EXPECTED_TESTS: '161',
          QUALIFICATION_PASSED_TESTS: '161',
        }),
        /sub-library attestation must bind the trusted runtime_verified 160-test profile/,
        'inflated 161-test qualification profile',
      );
    },
  }],
  ['qualification-attestation-binding', {
    title: 'Qualification attestation binds candidate identity, canonical approval, evidence, workflow and tag identity',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const fixture = createQualificationFixture(root, 'attestation-binding');
      assertAccepted(runQualification(root, fixture, timeoutMs), /QUALIFICATION_ATTESTATION_PASS:/, 'qualification attestation baseline');
      assertRejected(
        runQualification(root, fixture, timeoutMs, { ...fixture.env, QUALIFICATION_CONTENT_DIGEST: 'd'.repeat(64) }),
        /attestation identity does not match frozen candidate/,
        'qualification digest crosswire',
      );
      assertRejected(
        runQualification(root, fixture, timeoutMs, { ...fixture.env, QUALIFICATION_TAG_OBJECT_SHA: 'c'.repeat(40) }),
        /actual tag object, signer, or annotation digest does not match the approval sidecar/,
        'qualification tag object crosswire',
      );
      const insideArgs = [...fixture.args];
      insideArgs[insideArgs.indexOf('--output') + 1] = join(fixture.candidate, 'QUALIFICATION.json');
      assertRejected(
        runQualification(root, fixture, timeoutMs, fixture.env, insideArgs),
        /must be written outside both verified trees/,
        'qualification receipt candidate mutation',
      );
    },
  }],
  ['formal-release-workflow-shape', {
    title: 'Formal release workflow remains approval-bound, single-scope, and isolates candidate runtime execution from artifact qualification',
    expected: 'accept',
    run({ root }) {
      const ordinary = readFileSync(join(root, '.github/workflows/validate-library.yml'), 'utf8');
      const formal = readFileSync(join(root, '.github/workflows/release-library.yml'), 'utf8');
      const required = [
        'name: Formal release qualification gate',
        'workflow_dispatch:',
        'environment: formal-release',
        'WORKFLOW_SHA: ${{ github.workflow_sha }}',
        'TRUSTED_WORKFLOW_SHA: ${{ vars.FORMAL_RELEASE_TRUSTED_WORKFLOW_SHA }}',
        'ENVIRONMENT_READY: ${{ secrets.FORMAL_RELEASE_ENVIRONMENT_READY }}',
        'if [[ "$WORKFLOW_SHA" != "$TRUSTED_WORKFLOW_SHA" ]]',
        'ref: ${{ github.workflow_sha }}',
        'path: governance',
        'ref: refs/tags/${{ inputs.release_tag }}',
        'path: candidate',
        'RELEASE_SOURCE_ROOT: ${{ github.workspace }}/candidate',
        'node scripts/resolve-release-scope.mjs "$RELEASE_TRIGGER_TAG"',
        'git verify-tag --raw "$tag_ref"',
        '\\[GNUPG:\\] VALIDSIG',
        'FORMAL_RELEASE_TRUSTED_TAG_SIGNERS',
        'diff -qr governance/scripts candidate/scripts',
        'diff -q governance/.github/workflows/release-library.yml candidate/.github/workflows/release-library.yml',
        'diff -q governance/sub-libraries/registry.json candidate/sub-libraries/registry.json',
        '$RUNNER_TEMP/RELEASE-APPROVAL.json',
        "if: steps.release.outputs.scope == 'mother-library'",
        "if: steps.release.outputs.scope == 'sub-library'",
        'build-mother-release.mjs --prepare | tee "$prepare_log"',
        'node "$archive_verification_root/scripts/validate-artifact.mjs" --release "$archive_verification_root"',
        'build-release.mjs" --prepare | tee "$prepare_log"',
        'validate-artifact.mjs" --prepare "$candidate_path"',
        'RELEASE_TRIGGER_TAG: ${{ inputs.release_tag }}',
        'isolated-runtime-tests:',
        'needs: isolated-runtime-tests',
        'candidate_commit: ${{ steps.candidate_identity.outputs.candidate_commit }}',
        'tag_object_sha: ${{ steps.candidate_identity.outputs.tag_object_sha }}',
        'signer_fingerprint: ${{ steps.candidate_identity.outputs.signer_fingerprint }}',
        'tag_annotation_sha256: ${{ steps.candidate_identity.outputs.tag_annotation_sha256 }}',
        'tag_annotation_base64: ${{ steps.candidate_identity.outputs.tag_annotation_base64 }}',
        'approval_binding_sha256: ${{ steps.candidate_identity.outputs.approval_binding_sha256 }}',
        "const expectedKeys = ['approval_binding_sha256','approval_id','candidate_content_digest','schema','scope','version'];",
        "annotation.schema !== 'release-tag-annotation/v1'",
        'TESTED_SIGNER_FINGERPRINT: ${{ needs.isolated-runtime-tests.outputs.signer_fingerprint }}',
        'TESTED_TAG_ANNOTATION_SHA256: ${{ needs.isolated-runtime-tests.outputs.tag_annotation_sha256 }}',
        'TESTED_APPROVAL_BINDING_SHA256: ${{ needs.isolated-runtime-tests.outputs.approval_binding_sha256 }}',
        'test "$fingerprint" = "$TESTED_SIGNER_FINGERPRINT"',
        'test "$tag_annotation_sha256" = "$TESTED_TAG_ANNOTATION_SHA256"',
        'test "$approval_binding_sha256" = "$TESTED_APPROVAL_BINDING_SHA256"',
        'RELEASE_ACTUAL_TAG_OBJECT_SHA: ${{ steps.candidate_identity.outputs.tag_object_sha }}',
        'RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT: ${{ steps.candidate_identity.outputs.signer_fingerprint }}',
        'RELEASE_ACTUAL_TAG_ANNOTATION_SHA256: ${{ steps.candidate_identity.outputs.tag_annotation_sha256 }}',
        'RELEASE_ACTUAL_TAG_ANNOTATION_BASE64: ${{ steps.candidate_identity.outputs.tag_annotation_base64 }}',
        'RELEASE_ACTUAL_APPROVAL_BINDING_SHA256: ${{ steps.candidate_identity.outputs.approval_binding_sha256 }}',
        'TESTED_CANDIDATE_COMMIT: ${{ needs.isolated-runtime-tests.outputs.candidate_commit }}',
        'TESTED_TAG_OBJECT_SHA: ${{ needs.isolated-runtime-tests.outputs.tag_object_sha }}',
        'Prove trusted runtime-test profile and materialize isolated subject',
        'Run selected sub-library tests in a filesystem-isolated container',
        'npm ci --ignore-scripts --no-audit --no-fund',
        'node scripts/verify-runtime-test-profile.mjs',
        'scripts/verify-tested-candidate-identity.mjs',
        'scripts/verify-node-test-summary.mjs',
        'FORMAL_RELEASE_NODE20_IMAGE_DIGEST',
        '--subject-root "$RUNNER_TEMP/runtime-subject"',
        '--network none',
        '--read-only',
        '--mount "type=bind,src=$subject,dst=/subject,readonly"',
        'node --test --test-reporter=tap upload-media-browser.test.mjs article-image-binding.test.mjs article-content-formats.test.mjs article-operations.test.mjs',
        '--expected-tests 172',
        'trusted signer allowlist contains an invalid fingerprint',
        'BLOCK: no trusted formal qualification test profile exists for sub-library',
        'tar --sort=name --mtime=',
        'gzip -n > "$archive_path"',
        'archive_verification_root="$RUNNER_TEMP/archive-verification/prepared/v${VERSION}/${content_digest}"',
        'tar -xzf "$archive_path" -C "$archive_verification_root"',
        'validate-release-approval.mjs" "$archive_verification_root"',
        'validate-artifact.mjs" --release "$archive_verification_root"',
        'validate-artifact.mjs" --prepare "$archive_verification_root"',
        "printf 'verified_tree_root=%s\\n'",
        '--verified-tree "${{ steps.artifact.outputs.verified_tree_root }}"',
        "QUALIFICATION_RUNTIME_STATUS: ${{ steps.release.outputs.scope == 'sub-library' && 'runtime_verified' || 'runtime_not_applicable' }}",
        'mother-library-machine-contract-declares-none',
        'trusted-sub-library-runtime-profile',
        'sha256sum "$archive_name"',
        'Create qualification attestation outside the frozen candidate',
        'scripts/create-qualification-attestation.mjs',
        'QUALIFICATION-ATTESTATION.json',
        'Upload the exact qualified artifact and attestation',
        'qualification-${PACKAGE_ID}-${content_digest}',
      ];
      for (const marker of required) {
        if (!formal.includes(marker)) throw new Error(`formal release workflow missing required marker: ${marker}`);
      }
      if (/printf 'tag_annotation_(?:sha256|base64)=%s\\n' "\$tag_annotation_(?:sha256|base64)"/.test(formal) || /printf 'approval_binding_sha256=%s\\n' "\$approval_binding_sha256"/.test(formal)) {
        throw new Error('formal release workflow re-exports annotation variables that are not assigned by the shell');
      }
      const artifactStep = formal.slice(formal.indexOf('      - name: Freeze the qualified artifact by content digest'), formal.indexOf('      - name: Create qualification attestation outside the frozen candidate'));
      if (!artifactStep.includes('RELEASE_APPROVAL_PATH: ${{ steps.approval.outputs.path }}') || !artifactStep.includes('RELEASE_EVIDENCE_PATH: ${{ steps.evidence.outputs.path }}')) throw new Error('archive re-verification is not bound to the finalized approval and trusted evidence paths');
      if (!artifactStep.includes('validate-release-approval.mjs" "$archive_verification_root" "$RELEASE_APPROVAL_PATH" "$RELEASE_EVIDENCE_PATH"')) throw new Error('archive re-verification does not consume both bound sidecars');
      if (/^  (push|pull_request):/m.test(formal)) throw new Error('formal release workflow must not run on push or pull_request');
      if (/release-gate|RELEASE_REQUIRE_GIT_TAG|RELEASE_APPROVAL_PATH/.test(ordinary)) throw new Error('ordinary validation workflow still contains a formal release gate');
      if (/\bgh release\b|actions\/create-release|softprops\/action-gh-release/i.test(formal)) throw new Error('qualification workflow must not publish a GitHub Release');
      const actionRefs = [...formal.matchAll(/^\s*uses:\s*([^\s#]+).*$/gm)].map((match) => match[1]);
      if (actionRefs.length < 4) throw new Error(`formal release workflow unexpectedly contains only ${actionRefs.length} action references`);
      for (const ref of actionRefs) {
        if (!/@[a-f0-9]{40}$/.test(ref)) throw new Error(`formal release workflow action is not pinned to a full commit SHA: ${ref}`);
      }
      const runtimeStart = formal.indexOf('  isolated-runtime-tests:');
      const qualificationStart = formal.indexOf('  formal-release-qualification:');
      if (runtimeStart < 0 || qualificationStart <= runtimeStart) throw new Error('formal release workflow must define the isolated runtime-test job before qualification');
      const runtimeJob = formal.slice(runtimeStart, qualificationStart);
      const qualificationJob = formal.slice(qualificationStart);
      if (!runtimeJob.includes('node --test --test-reporter=tap upload-media-browser.test.mjs article-image-binding.test.mjs article-content-formats.test.mjs article-operations.test.mjs')) throw new Error('isolated runtime-test job does not execute the trusted direct Node test profile');
      if (runtimeJob.includes('npm test')) throw new Error('isolated runtime-test job delegates test execution to candidate-controlled npm lifecycle');
      if (!runtimeJob.includes("printf 'candidate_commit=%s\\n'") || !runtimeJob.includes("printf 'tag_object_sha=%s\\n'")) throw new Error('isolated runtime-test job does not export the exact tested commit and tag object');
      if (qualificationJob.includes('npm test') || qualificationJob.includes('npm ci')) throw new Error('candidate runtime execution remains in the artifact qualification job');
      if (!qualificationJob.includes('needs: isolated-runtime-tests')) throw new Error('artifact qualification does not depend on the isolated runtime-test job');
      if (!qualificationJob.includes('TESTED_CANDIDATE_COMMIT') || !qualificationJob.includes('TESTED_TAG_OBJECT_SHA')) throw new Error('artifact qualification does not bind its fresh checkout to the tested commit and tag object');
      if (!qualificationJob.includes('--expected-commit "$TESTED_CANDIDATE_COMMIT"') || !qualificationJob.includes('--expected-tag-object "$TESTED_TAG_OBJECT_SHA"') || !qualificationJob.includes('--actual-commit "$candidate_commit"') || !qualificationJob.includes('--actual-tag-object "$tag_object_sha"')) throw new Error('artifact qualification does not execute the trusted exact identity comparison');
      const runtimeConditions = [...runtimeJob.matchAll(/if: steps\.release\.outputs\.scope == '([^']+)'/g)].map((match) => match[1]);
      const qualificationConditions = [...qualificationJob.matchAll(/if: steps\.release\.outputs\.scope == '([^']+)'/g)].map((match) => match[1]);
      if (runtimeConditions.length !== 2 || runtimeConditions.some((scope) => scope !== 'sub-library')) throw new Error(`runtime-test job must contain exactly two sub-library-only branches: ${runtimeConditions.join(', ')}`);
      if (qualificationConditions.filter((scope) => scope === 'mother-library').length !== 1) throw new Error('formal release workflow must contain exactly one mother-library qualification branch');
      if (qualificationConditions.filter((scope) => scope === 'sub-library').length !== 1) throw new Error('formal release workflow must contain exactly one sub-library qualification branch');
      if (qualificationConditions.some((scope) => !['mother-library', 'sub-library'].includes(scope))) throw new Error(`formal release workflow contains an unknown qualification scope condition: ${qualificationConditions.join(', ')}`);
    },
  }],
  ['formal-release-evidence-workflow-shape', {
    title: 'Formal mother and sub-library releases require a separately decoded scope-bound evidence bundle',
    expected: 'accept',
    run({ root }) {
      const ordinary = readFileSync(join(root, '.github/workflows/validate-library.yml'), 'utf8');
      const formal = readFileSync(join(root, '.github/workflows/release-library.yml'), 'utf8');
      const required = [
        'approval_sidecar_base64:',
        'Decode non-secret approval intent without printing it',
        '$RUNNER_TEMP/RELEASE-APPROVAL-INTENT.json',
        'dispatcher approval intent must not inject final governance evidence fields',
        'Generate trusted fixed-profile evidence from actual job outputs',
        'scripts/generate-release-evidence.mjs',
        'Finalize approval sidecar with trusted evidence digest',
        'scripts/finalize-release-approval.mjs',
        'RELEASE_APPROVAL_PATH: ${{ steps.approval.outputs.path }}',
        'RELEASE_EVIDENCE_PATH: ${{ steps.evidence.outputs.path }}',
        'build-mother-release.mjs --prepare | tee "$prepare_log"',
        'node scripts/validate-artifact.mjs --prepare "$candidate_path"',
        'build-release.mjs" --prepare | tee "$prepare_log"',
        'node "$candidate_path/scripts/validate-artifact.mjs" --prepare "$candidate_path"',
      ];
      for (const marker of required) {
        if (!formal.includes(marker)) throw new Error(`formal release evidence workflow missing required marker: ${marker}`);
      }
      if (/RELEASE_EVIDENCE_PATH|RELEASE_APPROVAL_PATH|evidence_bundle_base64|approval_sidecar_base64/.test(ordinary)) throw new Error('ordinary validation workflow must not claim or require formal approval/evidence');
      if (/^\s{6}evidence_bundle_base64:/m.test(formal)) throw new Error('dispatcher must not inject a self-asserted evidence bundle into formal qualification');
    },
  }],
  ['mother-state-projection-drift', {
    title: 'Mother active status documents cannot drift from their canonical manifest',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const versionPath = join(root, 'VERSION.md');
      const baselineContent = readFileSync(versionPath, 'utf8');
      // Each source-level attack is checked by the validator's mandatory state-projection
      // preflight. The successful full builder run below is the positive baseline and also
      // exercises the packaged artifact, avoiding a redundant ~25s whole-repository scan
      // that made this single governance case exceed the fixed 120s release-evidence budget.
      const attacks = [
        {
          label: 'projected value drift',
          mutate: (content) => content.replace('repository_sync_status: "Synced"', 'repository_sync_status: "Ready"'),
          expected: /VERSION\.md state drift for repository_sync_status: expected "Synced" from MANIFEST\.md, got "Ready"/,
        },
        {
          label: 'projected field removed',
          mutate: (content) => content.replace('release_status: "BLOCK"\n', ''),
          expected: /VERSION\.md projects release_status, but the document does not declare it/,
        },
        {
          label: 'non-manifest source',
          mutate: (content) => content.replace('state_source: "MANIFEST.md"', 'state_source: "RELEASE.md"'),
          expected: /VERSION\.md state_source must resolve to the canonical scope MANIFEST\.md: RELEASE\.md/,
        },
        {
          label: 'cross-scope manifest source',
          mutate: (content) => content
            .replace('state_source: "MANIFEST.md"', 'state_source: "sub-libraries/website-content-ops/MANIFEST.md"')
            .replace('state_projection: ["repository_sync_status", "release_status"]', 'state_projection: ["release_status"]')
            .replace('release_status: "BLOCK"', 'release_status: "Preview"'),
          expected: /VERSION\.md state_source must resolve to the canonical scope MANIFEST\.md: sub-libraries\/website-content-ops\/MANIFEST\.md/,
        },
        {
          label: 'empty projection',
          mutate: (content) => content.replace('state_projection: \["repository_sync_status", "release_status"\]', 'state_projection: []'),
          expected: /VERSION\.md state_projection must be a non-empty inline string array/,
        },
        {
          label: 'required projection declarations removed together',
          mutate: (content) => content
            .replace('state_source: "MANIFEST.md"\n', '')
            .replace('state_projection: ["repository_sync_status", "release_status"]\n', ''),
          expected: /VERSION\.md required state projection must declare both state_source and state_projection/,
        },
        {
          label: 'required projection field set narrowed',
          mutate: (content) => content.replace('state_projection: ["repository_sync_status", "release_status"]', 'state_projection: ["release_status"]'),
          expected: /VERSION\.md required state_projection must exactly equal/,
        },
      ];
      for (const attack of attacks) {
        const mutated = attack.mutate(baselineContent);
        if (mutated === baselineContent) throw new Error(`fixture mutation failed: ${attack.label}`);
        writeFileSync(versionPath, mutated);
        const result = run(root, 'scripts/validate-mother-library.mjs', [], { timeoutMs });
        assertRejected(result, attack.expected, attack.label);
        writeFileSync(versionPath, baselineContent);
      }

      const git = (args) => spawnSync('git', args, { cwd: root, encoding: 'utf8' });
      for (const [args, label] of [
        [['init', '-q'], 'initialize state-projection artifact fixture'],
        [['config', 'user.name', 'Governance Fixture'], 'configure fixture Git user'],
        [['config', 'user.email', 'fixture@example.invalid'], 'configure fixture Git email'],
        [['add', '-f', '.'], 'stage state-projection fixture'],
        [['commit', '-qm', 'state projection artifact baseline'], 'commit state-projection fixture'],
      ]) {
        const result = git(args);
        ensureCompleted(result, label);
        if (result.status !== 0) throw new Error(`${label} failed\n${shortOutput(result)}`);
      }
      const build = run(root, 'scripts/build-mother-release.mjs', [], { timeoutMs });
      assertAccepted(build, /RELEASE_CANDIDATE:/, 'mother artifact state-projection baseline');
      const artifactRoot = join(root, 'dist/mother/latest');
      const artifactVersionPath = join(artifactRoot, 'VERSION.md');
      replaceExact(artifactVersionPath, 'repository_sync_status: "Synced"', 'repository_sync_status: "Ready"');
      rewriteArtifactManifest(artifactRoot, (manifest) => {
        const record = manifest.source_provenance.files.find((item) => item.path === 'VERSION.md');
        if (!record) throw new Error('VERSION.md provenance record missing');
        record.sha256 = sha256File(artifactVersionPath);
        record.commit_sha256 = record.sha256;
      });
      const artifactValidation = run(root, 'scripts/validate-artifact.mjs', [artifactRoot], { timeoutMs });
      assertRejected(artifactValidation, /VERSION\.md state drift for repository_sync_status: expected "Synced" from MANIFEST\.md, got "Ready"/, 'mother artifact state drift with recomputed integrity metadata');
    },
  }],
  ['mother-index-layered-sub-library-entry', {
    title: 'Mother validator preserves layered sub-library routing and propagates formal modes to child validators',
    expected: 'reject',
    run({ root, timeoutMs }) {
      const indexPath = join(root, 'wiki/index.md');
      const baseline = run(root, 'scripts/validate-mother-library.mjs', [], { timeoutMs });
      ensureCompleted(baseline, 'layered mother-to-sub-library navigation baseline');
      if (!/Mother library:/.test(outputOf(baseline))) throw new Error(`mother validator did not reach its verdict output\n${shortOutput(baseline)}`);
      if (/lacks canonical website-content-ops entry/.test(outputOf(baseline))) {
        throw new Error('mother validator still expects a grandchild sub-library entry in wiki/index.md');
      }

      const registry = JSON.parse(readFileSync(join(root, 'sub-libraries/registry.json'), 'utf8'));
      const childValidators = registry.entries.map((entry) => join(root, entry.path, 'scripts/validate-sub-library.mjs'));
      for (const mode of ['--prepare', '--release']) {
        for (const childValidator of childValidators) {
          writeFileSync(childValidator, `#!/usr/bin/env node
const expected = process.env.EXPECTED_CHILD_MODE;
const seen = process.argv.slice(2);
if (seen.includes(expected)) {
  console.error('CHILD_MODE_OK:' + expected);
  process.exit(1);
}
console.error('CHILD_MODE_MISSING:' + expected + ':' + JSON.stringify(seen));
process.exit(1);
`);
        }
        const result = run(root, 'scripts/validate-mother-library.mjs', [mode], {
          timeoutMs,
          env: { EXPECTED_CHILD_MODE: mode },
        });
        assertRejected(result, new RegExp(`CHILD_MODE_OK:${mode}`), `mother ${mode} child-mode propagation`);
        if (/CHILD_MODE_MISSING:/.test(outputOf(result))) throw new Error(`mother ${mode} failed to propagate to at least one child validator\n${shortOutput(result)}`);
      }

      removeLine(indexPath, /^.*\(\.\.\/sub-libraries\/README\.md\).*\n/m);
      const result = run(root, 'scripts/validate-mother-library.mjs', [], { timeoutMs });
      assertRejected(result, /wiki\/index\.md lacks canonical sub-libraries\/README\.md entry/, 'mother-to-sub-library canonical registry entry');
    },
  }],
]);
