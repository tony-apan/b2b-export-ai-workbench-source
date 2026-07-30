import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const validatorSource = join(repoRoot, 'scripts/validate-knowledge-chain.mjs');
const frontMatterParserSource = join(repoRoot, 'scripts/lib/markdown-front-matter.mjs');
const creatorSource = join(repoRoot, 'scripts/create-document.mjs');
const temporaryRoots = [];
const sha256 = (path) => createHash('sha256').update(readFileSync(path)).digest('hex');

function tempRoot(prefix) {
  const root = mkdtempSync(join(tmpdir(), prefix));
  temporaryRoots.push(root);
  return root;
}
function write(root, path, content) {
  const target = join(root, path);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, content.trimStart());
  return target;
}
function run(root, script, args = [], options = {}) {
  return spawnSync(process.execPath, [script, ...args], { cwd: root, encoding: 'utf8', env: { ...process.env, ...(options.env ?? {}) } });
}
function command(root, executable, args = [], options = {}) {
  return spawnSync(executable, args, { cwd: root, encoding: 'utf8', env: { ...process.env, ...(options.env ?? {}) } });
}
function output(result) { return `${result.stdout ?? ''}\n${result.stderr ?? ''}`; }
function fm(fields, body = '') {
  return `---\n${Object.entries(fields).map(([key, value]) => `${key}: ${value}`).join('\n')}\n---\n${body}\n`;
}

function makeValidChain() {
  const root = tempRoot('701-g2-chain-');
  write(root, 'scripts/validate-knowledge-chain.mjs', readFileSync(validatorSource, 'utf8'));
  write(root, 'scripts/lib/markdown-front-matter.mjs', readFileSync(frontMatterParserSource, 'utf8'));
  const sourceId = 'SRC-20260729-0001';
  const rawPath = 'raw/10_conversations/src-20260729-0001-fixture.md';
  write(root, rawPath, fm({
    source_id: `"${sourceId}"`, title: '"Synthetic fixture"', description: '"Synthetic public fixture for G2 regression testing only."', type: '"conversation-source"', status: '"Working"', owner: '"AI"', created: '"2026-07-29"', last_updated: '"2026-07-29"', sources: '[]', related: '[]', source_kind: '"virtual-fixture"', synthetic: 'true', fixture_id: '"FIX-G2-CHAIN-0001"', fixture_provenance: '"authored-for-governance-testing"', raw_kind: '"conversation"', conversation_type: '"codex-chat"', source_date: '"2026-07-29"', captured_at: '"2026-07-29T00:00:00+08:00"', ingested_at: '"2026-07-29T00:00:00+08:00"', channel: '"test"', participants: '["Synthetic learner"]', topics: '["knowledge-chain"]', keywords: '["fixture", "course", "review"]', language: '"en"', sensitivity: '"public"', visibility: '"public"', consent_status: '"original-synthetic-fixture"', ingestion_status: '"ingested"', derived_to: '["ID-0001", "ID-0002", "ID-0003", "VER-20260729-g2", "WB-20260729-g2"]', verification_status: '"structure-pass"', redaction_status: '"safe-to-publish"',
  }, '# Synthetic fixture'));
  write(root, 'wiki/10_sources/source-registry.md', `| Source ID | Title |\n|---|---|\n| ${sourceId} | G2 fixture |\n`);
  write(root, `wiki/10_sources/${sourceId}.md`, fm({
    source_id: `"${sourceId}"`, title: '"Source"', description: '"Source note."', type: '"source-note"', status: '"Working"', owner: '"AI"', created: '"2026-07-29"', last_updated: '"2026-07-29"', sources: '[]', related: '[]', raw_path: `"${rawPath}"`, derived_pages: '["../20_concepts/id-0001-concept.md", "../30_playbooks/id-0002-playbook.md", "../90_outputs/courses/id-0003-course.md", "../90_outputs/courses/verification/VER-20260729-g2.md", "../90_outputs/courses/writeback/WB-20260729-g2.md"]', verification_record: '"../90_outputs/courses/verification/VER-20260729-g2.md"', writeback_record: '"../90_outputs/courses/writeback/WB-20260729-g2.md"',
  }));
  const common = { status: '"Working"', owner: '"AI"', created: '"2026-07-29"', last_updated: '"2026-07-29"', sources: `["${sourceId}"]`, related: '[]' };
  write(root, 'wiki/20_concepts/id-0001-concept.md', fm({ doc_id: '"ID-0001"', title: '"Concept"', description: '"Concept."', type: '"concept"', ...common }));
  write(root, 'wiki/30_playbooks/id-0002-playbook.md', fm({ doc_id: '"ID-0002"', title: '"Playbook"', description: '"Playbook."', type: '"playbook"', ...common }));
  const exercisePath = write(root, 'wiki/90_outputs/courses/evidence/EX-20260729-g2.md', fm({ title: '"Exercise"', description: '"Independent exercise with a second scenario and concrete submitted output."', type: '"evidence"', ...common, exercise_id: '"EX-20260729-g2"', course_doc_id: '"ID-0003"', submission_status: '"submitted"', scenario_count: '2', rubric_id: '"RUBRIC-G2-V1"' }, '# Submission\n\n## Scenario 2 Input\nA second synthetic organization must route a raw conversation through source, course, review, verification, and writeback without reusing the first scenario values.\n\n## Submitted Output\nThe learner produced five separately linked records, preserved the Source ID, and recorded explicit scope limits for the synthetic result.\n\n## Self Check\nThe learner checked path binding, role uniqueness, evidence hashes, and the difference between structure proof and real-world effectiveness.'));
  const snapshotBody1 = '# Snapshot One\n\n## Captured Evidence\nThe captured exercise output contains a second scenario, a concrete submitted result, and a self-check that can be independently inspected.';
  const snapshotBody2 = '# Snapshot Two\n\n## Captured Evidence\nThe captured writeback comparison records the target knowledge page and the exact scope-limited change derived from the verified synthetic exercise.';
  const snapshot1 = fm({ title: '"Snapshot one"', description: '"Immutable-style evidence snapshot for the submitted exercise."', type: '"evidence-snapshot"', ...common, snapshot_id: '"SNAPSHOT-20260729-g2-1"', captured_at: '"2026-07-29T01:00:00Z"', subject: '"EX-20260729-g2"', evidence_digest: `"sha256:${createHash('sha256').update(snapshotBody1).digest('hex')}"` }, snapshotBody1);
  const snapshot2 = fm({ title: '"Snapshot two"', description: '"Immutable-style evidence snapshot for the knowledge writeback comparison."', type: '"evidence-snapshot"', ...common, snapshot_id: '"SNAPSHOT-20260729-g2-2"', captured_at: '"2026-07-29T01:10:00Z"', subject: '"WB-20260729-g2"', evidence_digest: `"sha256:${createHash('sha256').update(snapshotBody2).digest('hex')}"` }, snapshotBody2);
  write(root, 'wiki/90_outputs/courses/evidence/SNAPSHOT-20260729-g2-1.md', snapshot1);
  write(root, 'wiki/90_outputs/courses/evidence/SNAPSHOT-20260729-g2-2.md', snapshot2);
  write(root, 'wiki/90_outputs/courses/reviews/REV-20260729-g2.md', fm({ title: '"Review"', description: '"Human review with an explicit rubric result and concrete findings."', type: '"review-record"', ...common, review_id: '"REV-20260729-g2"', course_doc_id: '"ID-0003"', reviewer_id: '"HUMAN-REVIEWER-001"', reviewer_type: '"human"', review_status: '"completed"', review_result: '"pass"', reviewed_artifact: '"../evidence/EX-20260729-g2.md"', artifact_sha256: `"${sha256(exercisePath)}"`, rubric_id: '"RUBRIC-G2-V1"', score: '9', score_max: '10', pass_threshold: '8', event_refs: '["EVT-20260729-0001"]', snapshot_refs: '["../evidence/SNAPSHOT-20260729-g2-1.md"]' }, '# Review\n\n## Rubric Results\nThe submission scored nine of ten points against the declared rubric and exceeded the passing threshold of eight points.\n\n## Reviewer Findings\nThe second scenario is distinct, every derived role is linked, and the reviewer limited the result to structural behavior rather than production effectiveness.'));
  write(root, 'wiki/90_outputs/courses/verification/VER-20260729-g2.md', fm({ title: '"Verification"', description: '"Verified evidence with observed results and explicit claim boundaries."', type: '"verification-record"', ...common, verification_id: '"VER-20260729-g2"', course_doc_id: '"ID-0003"', structure_verification_status: '"verified"', exercise_verification_status: '"verified"', effectiveness_verification_status: '"unverified"', exercise_artifact: '"../evidence/EX-20260729-g2.md"', review_record: '"../reviews/REV-20260729-g2.md"', sample_size: '1', observed_result: '"The synthetic second scenario completed the declared chain."', allowed_claim: '"The validator enforces the tested structural contract."', non_claim: '"No customer, market, or production outcome is proven."', event_refs: '["EVT-20260729-0002"]', snapshot_refs: '["../evidence/SNAPSHOT-20260729-g2-1.md"]' }, '# Verification\n\n## Steps And Evidence\nThe reviewer replayed the synthetic scenario, checked each linked artifact and hash, and observed the expected structural result in one bounded sample.\n\n## Result And Boundary\nThe result proves only the tested structural contract; it does not establish customer impact, learning effectiveness, or production readiness.'));
  write(root, 'wiki/90_outputs/courses/writeback/WB-20260729-g2.md', fm({ title: '"Writeback"', description: '"Completed writeback with explicit targets and before-after evidence snapshots."', type: '"writeback-record"', ...common, writeback_id: '"WB-20260729-g2"', course_doc_id: '"ID-0003"', writeback_status: '"completed"', verification_record: '"../verification/VER-20260729-g2.md"', review_record: '"../reviews/REV-20260729-g2.md"', change_summary: '"Recorded the bounded validator behavior in the course page."', writeback_targets: '["../id-0003-course.md"]', event_refs: '["EVT-20260729-0003"]', snapshot_refs: '["../evidence/SNAPSHOT-20260729-g2-1.md", "../evidence/SNAPSHOT-20260729-g2-2.md"]' }, '# Writeback\n\n## Observed Evidence\nThe reviewed exercise and verification record show a single synthetic scenario completing the exact structural chain with explicit scope limitations.\n\n## Knowledge Changes\nThe course page now records the bounded structural result and keeps customer outcomes, production evidence, and broad effectiveness outside the allowed claim.'));
  write(root, 'wiki/90_outputs/courses/id-0003-course.md', fm({ doc_id: '"ID-0003"', title: '"Course"', description: '"Course."', type: '"course-module"', ...common, structure_verification_status: '"verified"', exercise_verification_status: '"verified"', effectiveness_verification_status: '"unverified"', exercise_artifact: '"evidence/EX-20260729-g2.md"', review_record: '"reviews/REV-20260729-g2.md"', verification_record: '"verification/VER-20260729-g2.md"', writeback_record: '"writeback/WB-20260729-g2.md"' }));
  write(root, 'wiki/00_meta/logs/2026/2026-07/2026-07-29.md', '# Events\n\nEVT-20260729-0001\nEVT-20260729-0002\nEVT-20260729-0003\n');
  return root;
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
  return value;
}
function canonicalJson(value) { return JSON.stringify(canonicalize(value)); }
function fixtureManifest(root, sourceCommit = 'a'.repeat(40)) {
  const sourceId = 'SRC-20260729-0001';
  const entries = [
    ['raw', 'raw/10_conversations/src-20260729-0001-fixture.md', sourceId],
    ['source-note', `wiki/10_sources/${sourceId}.md`, sourceId],
    ['concept', 'wiki/20_concepts/id-0001-concept.md', sourceId],
    ['playbook', 'wiki/30_playbooks/id-0002-playbook.md', sourceId],
    ['course', 'wiki/90_outputs/courses/id-0003-course.md'],
    ['exercise', 'wiki/90_outputs/courses/evidence/EX-20260729-g2.md'],
    ['review', 'wiki/90_outputs/courses/reviews/REV-20260729-g2.md'],
    ['verification', 'wiki/90_outputs/courses/verification/VER-20260729-g2.md'],
    ['writeback', 'wiki/90_outputs/courses/writeback/WB-20260729-g2.md'],
  ];
  const artifacts = entries.map(([role, relativePath, entrySourceId]) => ({
    role,
    path: relativePath,
    sha256: sha256(join(root, relativePath)),
    ...(entrySourceId ? { source_id: entrySourceId } : {}),
  }));
  const snapshot = { schema: 'knowledge-chain-snapshot/v1', course_doc_id: 'ID-0003', source_ids: [sourceId], artifacts };
  return {
    schema: 'knowledge-chain-manifest/v1',
    source_commit: sourceCommit,
    snapshot_digest: `sha256:${createHash('sha256').update(canonicalJson(snapshot)).digest('hex')}`,
    course_doc_id: 'ID-0003',
    source_ids: [sourceId],
    artifacts,
  };
}
function createSignedFixtureApproval(root) {
  const sidecarRoot = tempRoot('701-g2-approval-');
  const gpgHome = join(sidecarRoot, 'gnupg');
  mkdirSync(gpgHome, { recursive: true, mode: 0o700 });
  const identity = 'Synthetic Fixture Signer <fixture@example.com>';
  const generated = command(sidecarRoot, 'gpg', ['--batch', '--homedir', gpgHome, '--pinentry-mode', 'loopback', '--passphrase', '', '--quick-generate-key', identity, 'ed25519', 'sign', '1d']);
  assert.equal(generated.status, 0, output(generated));
  const listed = command(sidecarRoot, 'gpg', ['--batch', '--homedir', gpgHome, '--with-colons', '--list-secret-keys']);
  assert.equal(listed.status, 0, output(listed));
  const fingerprint = listed.stdout.split('\n').find((line) => line.startsWith('fpr:'))?.split(':')[9];
  assert.match(fingerprint ?? '', /^[A-F0-9]{40}(?:[A-F0-9]{24})?$/);
  const manifest = fixtureManifest(root);
  const approvalPath = join(sidecarRoot, 'COURSE-APPROVAL.json');
  const signaturePath = join(sidecarRoot, 'COURSE-APPROVAL.json.asc');
  writeFileSync(approvalPath, `${JSON.stringify({
    schema: 'course-review-approval/v2',
    approvals: [{
      course_doc_id: 'ID-0003',
      approval_status: 'approved',
      approved_by: 'Synthetic Fixture Signer',
      approved_at: '2026-07-29T02:00:00Z',
      approval_context: 'synthetic-test-fixture',
      reviewer_identity: 'not_verified',
      knowledge_chain_manifest: manifest,
      knowledge_chain_manifest_sha256: createHash('sha256').update(canonicalJson(manifest)).digest('hex'),
    }],
  }, null, 2)}\n`);
  const signed = command(sidecarRoot, 'gpg', ['--batch', '--homedir', gpgHome, '--pinentry-mode', 'loopback', '--passphrase', '', '--armor', '--detach-sign', '--output', signaturePath, approvalPath]);
  assert.equal(signed.status, 0, output(signed));
  return { approvalPath, signaturePath, fingerprint, gpgHome, sourceCommit: 'a'.repeat(40) };
}

function makeCreatorRoot(...templatePaths) {
  const root = tempRoot('701-g2-creator-');
  write(root, 'scripts/create-document.mjs', readFileSync(creatorSource, 'utf8'));
  for (const templatePath of templatePaths) write(root, templatePath, readFileSync(join(repoRoot, templatePath), 'utf8'));
  return root;
}

test.after(() => { for (const root of temporaryRoots) rmSync(root, { recursive: true, force: true }); });

test('complete content-bearing five-role chain passes only structural validation in ordinary mode', () => {
  const root = makeValidChain();
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.equal(result.status, 0, output(result));
  assert.match(output(result), /KNOWLEDGE_CHAIN_STRUCTURE_PASS/);
  assert.doesNotMatch(output(result), /KNOWLEDGE_CHAIN_RELEASE_PASS/);
  assert.match(output(result), /does not prove exercise completion, human review, real-world effectiveness, external approval, or release eligibility/);
});

test('self-declared reviewer_type human cannot substitute for signed external approval', () => {
  const root = makeValidChain();
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'), ['--release']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /requires --course-approval and --course-approval-signature/);
  assert.match(output(result), /no trusted signed external course approval/);
  assert.doesNotMatch(output(result), /KNOWLEDGE_CHAIN_RELEASE_PASS/);
});

test('unknown raw lifecycle fails closed', () => {
  const root = makeValidChain();
  const path = join(root, 'raw/10_conversations/src-20260729-0001-fixture.md');
  writeFileSync(path, readFileSync(path, 'utf8').replace('ingestion_status: "ingested"', 'ingestion_status: "magic-done"'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /unknown ingestion_status magic-done/);
});

test('duplicate derived paths cannot impersonate five unique roles', () => {
  const root = makeValidChain();
  const path = join(root, 'wiki/10_sources/SRC-20260729-0001.md');
  writeFileSync(path, readFileSync(path, 'utf8').replace(/derived_pages: \[[^\n]+\]/, 'derived_pages: ["../20_concepts/id-0001-concept.md", "../20_concepts/id-0001-concept.md", "../20_concepts/id-0001-concept.md", "../20_concepts/id-0001-concept.md", "../20_concepts/id-0001-concept.md"]'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /duplicate values are not allowed|missing unique derived role/);
});

test('forged metadata strings cannot replace evidence and review artifacts', () => {
  const root = makeValidChain();
  const path = join(root, 'wiki/90_outputs/courses/id-0003-course.md');
  let content = readFileSync(path, 'utf8');
  for (const field of ['exercise_artifact', 'review_record', 'verification_record', 'writeback_record']) content = content.replace(new RegExp(`^${field}:.*\\n`, 'm'), '');
  writeFileSync(path, content);
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'), ['--release']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /missing required front matter field exercise_artifact/);
  assert.doesNotMatch(output(result), /KNOWLEDGE_CHAIN_PASS:/);
});

test('public release rejects unsafe raw metadata even on a synthetic path', () => {
  const root = makeValidChain();
  const path = join(root, 'raw/10_conversations/src-20260729-0001-fixture.md');
  writeFileSync(path, readFileSync(path, 'utf8').replace('sensitivity: "public"', 'sensitivity: "private"').replace('redaction_status: "safe-to-publish"', 'redaction_status: "not-reviewed"'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'), ['--release']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /sensitivity must be public/);
  assert.match(output(result), /redaction_status must be safe-to-publish/);
});


test('customer-like body cannot hide behind synthetic public metadata', () => {
  const root = makeValidChain();
  const path = join(root, 'raw/10_conversations/src-20260729-0001-fixture.md');
  writeFileSync(path, `${readFileSync(path, 'utf8')}\nCustomer Name: Acme Corp\nContact Person: Alice\nEmail: alice@acme.invalid\nInternal Note: renewal risk\n`);
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'), ['--release']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /public synthetic content scan detected (email address|customer\/contact\/internal-note label)/);
  assert.doesNotMatch(output(result), /KNOWLEDGE_CHAIN_PASS:/);
});

test('raw filename date source id and facet types fail closed together', () => {
  const root = makeValidChain();
  const oldRaw = join(root, 'raw/10_conversations/src-20260729-0001-fixture.md');
  const malformedRel = 'raw/10_conversations/src-19990101-9999-mismatched-fixture.md';
  let content = readFileSync(oldRaw, 'utf8')
    .replace('participants: ["Synthetic learner"]', 'participants: "Alice,Bob"')
    .replace('topics: ["knowledge-chain"]', 'topics: "not-an-array"')
    .replace('keywords: ["fixture", "course", "review"]', 'keywords: "not-an-array"');
  write(root, malformedRel, content);
  rmSync(oldRaw);
  const sourceNote = join(root, 'wiki/10_sources/SRC-20260729-0001.md');
  writeFileSync(sourceNote, readFileSync(sourceNote, 'utf8').replace('raw/10_conversations/src-20260729-0001-fixture.md', malformedRel));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /participants must be an array/);
  assert.match(output(result), /topics must be an array/);
  assert.match(output(result), /keywords must be an array/);
  assert.match(output(result), /filename date 19990101 must equal source_date 2026-07-29/);
  assert.match(output(result), /source_id must equal SRC-19990101-9999/);
});

test('source-note creator rejects README as raw_path', () => {
  const root = makeCreatorRoot('wiki/_templates/source-note.md');
  write(root, 'README.md', fm({ source_id: '"SRC-20990101-0001"', title: '"README"', description: '"Repository entry, not a raw source record."', type: '"meta"', status: '"Working"', owner: '"AI"', created: '"2099-01-01"', last_updated: '"2099-01-01"', sources: '[]', related: '[]' }, '# README'));
  const result = run(root, join(root, 'scripts/create-document.mjs'), ['--dir', 'wiki/10_sources', '--slug', 'readme-binding', '--title', 'README binding attack', '--description', '用于验证 source note 不能把仓库 README 冒充为可追溯的原始来源记录。', '--template', 'wiki/_templates/source-note.md', '--source-id', 'SRC-20990101-0001', '--raw-path', 'README.md', '--dry-run']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /--raw-path must point to a concrete source record under raw/);
  assert.doesNotMatch(output(result), /VALIDATED:/);
});

test('mother document numbering ignores sub-library ID-9999', () => {
  const root = makeCreatorRoot('wiki/_templates/concept-page.md');
  write(root, 'sub-libraries/example/knowledge/id-9999-sub-library-only.md', '# Sub-library ID');
  const result = run(root, join(root, 'scripts/create-document.mjs'), ['--dir', 'wiki/20_concepts', '--slug', 'mother-scope-probe', '--title', 'Mother scope probe', '--description', '用于验证子库中的最高编号不会污染母库 durable page 的独立取号范围。', '--template', 'wiki/_templates/concept-page.md', '--when-to-read', '需要创建并核对 durable 文档的编号、范围和检索元数据时。', '--keywords', 'document id,mother scope,durable page', '--date', '2026-07-29', '--dry-run']);
  assert.equal(result.status, 0, output(result));
  assert.match(output(result), /VALIDATED: wiki\/20_concepts\/id-0001-mother-scope-probe\.md/);
  assert.match(output(result), /doc_id: "ID-0001"/);
  assert.doesNotMatch(output(result), /ID-10000/);
});

test('creator fails closed when four-digit mother ID space is exhausted', () => {
  const root = makeCreatorRoot('wiki/_templates/concept-page.md');
  write(root, 'wiki/20_concepts/id-9999-existing.md', '# Existing ID-9999');
  const result = run(root, join(root, 'scripts/create-document.mjs'), ['--dir', 'wiki/20_concepts', '--slug', 'exhausted-id-probe', '--title', 'Exhausted ID probe', '--description', '用于验证四位文档编号耗尽后创建器必须阻断，而不是生成五位 ID。', '--template', 'wiki/_templates/concept-page.md', '--when-to-read', '需要创建并核对 durable 文档的编号、范围和检索元数据时。', '--keywords', 'document id,mother scope,durable page', '--date', '2026-07-29', '--dry-run']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /four-digit document ID space is exhausted/);
  assert.doesNotMatch(output(result), /VALIDATED:|ID-10000/);
});

test('durable creator rejects templates missing when_to_read and keywords', () => {
  const root = makeCreatorRoot();
  write(root, 'wiki/_templates/missing-retrieval.md', fm({ title: '"Missing retrieval metadata template"', description: '"Attack template intentionally omitting durable retrieval metadata."', type: '"template"', status: '"Working"', owner: '"AI"', created: '"2026-07-29"', last_updated: '"2026-07-29"', sources: '[]', related: '[]', when_to_read: '"需要验证 creator 对模板 payload 的检索字段执行 fail-closed 校验时。"', keywords: '["creator contract", "retrieval metadata", "negative test"]', template_usage: '"creator-compatible"', template_target_kind: '"durable"', template_target_type: '"concept"' }, '<!-- DOCUMENT_TEMPLATE_START -->\n---\ndoc_id: "{{doc_id}}"\ntitle: "{{title}}"\ndescription: "{{description}}"\ntype: "{{type}}"\nstatus: "Seed"\nowner: "AI"\ncreated: "{{today}}"\nlast_updated: "{{today}}"\nsources: []\nrelated: []\n---\n# {{title}}\n<!-- DOCUMENT_TEMPLATE_END -->'));
  const result = run(root, join(root, 'scripts/create-document.mjs'), ['--dir', 'wiki/20_concepts', '--slug', 'missing-retrieval', '--title', 'Missing retrieval metadata', '--description', '用于验证 durable page 缺少读取时机与检索词时创建器必须直接阻断。', '--template', 'wiki/_templates/missing-retrieval.md', '--when-to-read', '需要验证生成后的 durable 页面是否具备具体读取条件时。', '--keywords', 'retrieval metadata,creator contract,negative test', '--date', '2026-07-29', '--dry-run']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /missing required field when_to_read/);
  assert.match(output(result), /missing required field keywords/);
  assert.doesNotMatch(output(result), /VALIDATED:/);
});

test('create-document rejects manual-copy templates', () => {
  const root = makeCreatorRoot();
  const manual = readFileSync(join(repoRoot, 'wiki/_templates/concept-page.md'), 'utf8')
    .replace('template_usage: "creator-compatible"', 'template_usage: "manual-copy"');
  write(root, 'wiki/_templates/manual-copy.md', manual);
  const result = run(root, join(root, 'scripts/create-document.mjs'), ['--dir', 'wiki/20_concepts', '--slug', 'manual-copy', '--title', 'Manual copy probe', '--description', '用于验证人工复制模板不能被 create-document 当成结构化创建入口。', '--template', 'wiki/_templates/manual-copy.md', '--when-to-read', '需要验证 creator-compatible 与 manual-copy 边界时。', '--keywords', 'manual copy,creator compatible,template usage', '--date', '2026-07-29', '--dry-run']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /accepts only template_usage: creator-compatible/);
  assert.doesNotMatch(output(result), /VALIDATED:/);
});

test('create-document rejects semantic placeholders in template discovery metadata', () => {
  const base = readFileSync(join(repoRoot, 'wiki/_templates/concept-page.md'), 'utf8');
  const attacks = [
    ['description', base.replace(/^description:.*$/m, 'description: "TODO"'), /semantic placeholder in template metadata description/],
    ['when-to-read', base.replace(/^when_to_read:.*$/m, 'when_to_read: "说明什么时候读取"'), /semantic placeholder in template metadata when_to_read/],
    ['keywords', base.replace(/^keywords:.*$/m, 'keywords: ["关键词 1", "creator", "contract"]'), /template metadata keywords must contain 3-8 concrete retrieval terms/],
  ];
  for (const [name, template, marker] of attacks) {
    const root = makeCreatorRoot();
    write(root, `wiki/_templates/${name}-placeholder.md`, template);
    const result = run(root, join(root, 'scripts/create-document.mjs'), ['--dir', 'wiki/20_concepts', '--slug', `${name}-placeholder`, '--title', `${name} placeholder probe`, '--description', `用于验证模板 ${name} 中的语义占位词不能进入创建流程。`, '--template', `wiki/_templates/${name}-placeholder.md`, '--when-to-read', '需要验证模板发现元数据不含语义占位词时。', '--keywords', 'template metadata,semantic placeholder,fail closed', '--date', '2026-07-29', '--dry-run']);
    assert.notEqual(result.status, 0, `${name}: ${output(result)}`);
    assert.match(output(result), marker, name);
    assert.doesNotMatch(output(result), /VALIDATED:/, name);
  }
});

test('raw conversation creator permits empty or de-identified refs and rejects identifying or malformed refs', () => {
  const base = readFileSync(join(repoRoot, 'raw/_templates/conversation-source.md'), 'utf8');
  const runTemplate = (name, template) => {
    const root = makeCreatorRoot();
    write(root, `raw/_templates/${name}.md`, template);
    return run(root, join(root, 'scripts/create-document.mjs'), ['--dir', 'raw/10_conversations', '--slug', name, '--title', `Raw ${name} probe`, '--description', `用于验证 raw conversation 的 subject_ref 与 client_ref 只接受空值或去敏引用格式。`, '--template', `raw/_templates/${name}.md`, '--source-id', 'SRC-20260729-9000', '--date', '2026-07-29', '--dry-run']);
  };

  const empty = runTemplate('empty-refs', base);
  assert.equal(empty.status, 0, output(empty));
  assert.match(output(empty), /^subject_ref: ""$/m);
  assert.match(output(empty), /^client_ref: ""$/m);

  const valid = runTemplate('valid-refs', base.replace('subject_ref: ""', 'subject_ref: "SUBJ-ACME-001"').replace('client_ref: ""', 'client_ref: "CLIENT-TEST-001"'));
  assert.equal(valid.status, 0, output(valid));
  assert.match(output(valid), /^subject_ref: "SUBJ-ACME-001"$/m);
  assert.match(output(valid), /^client_ref: "CLIENT-TEST-001"$/m);

  const attacks = [
    ['email-ref', base.replace('subject_ref: ""', 'subject_ref: "buyer@example.com"'), /subject_ref must be empty or a de-identified uppercase reference/],
    ['space-ref', base.replace('subject_ref: ""', 'subject_ref: "SUBJ-ACME 001"'), /subject_ref must be empty or a de-identified uppercase reference/],
    ['path-ref', base.replace('client_ref: ""', 'client_ref: "file:///customer-a"'), /client_ref must be empty or a de-identified uppercase reference/],
    ['wrong-prefix-ref', base.replace('client_ref: ""', 'client_ref: "SUBJ-ACME-001"'), /client_ref must be empty or a de-identified uppercase reference/],
  ];
  for (const [name, template, marker] of attacks) {
    const result = runTemplate(name, template);
    assert.notEqual(result.status, 0, `${name}: ${output(result)}`);
    assert.match(output(result), marker, name);
    assert.doesNotMatch(output(result), /VALIDATED:/, name);
  }
});

test('semantically empty exercise evidence cannot pass release validation', () => {
  const root = makeValidChain();
  const exercise = join(root, 'wiki/90_outputs/courses/evidence/EX-20260729-g2.md');
  const content = readFileSync(exercise, 'utf8').replace(/# Submission[\s\S]*$/, '# Submission\n\n## Scenario 2 Input\nTBD\n\n## Submitted Output\nPlaceholder\n\n## Self Check\nNot provided\n');
  writeFileSync(exercise, content);
  const review = join(root, 'wiki/90_outputs/courses/reviews/REV-20260729-g2.md');
  writeFileSync(review, readFileSync(review, 'utf8').replace(/^artifact_sha256:.*$/m, `artifact_sha256: "${sha256(exercise)}"`));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'), ['--release']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /section ## Scenario 2 Input must contain at least 20 characters of concrete, non-placeholder evidence/);
  assert.match(output(result), /section ## Submitted Output must contain at least 20 characters of concrete, non-placeholder evidence/);
  assert.match(output(result), /section ## Self Check must contain at least 20 characters of concrete, non-placeholder evidence/);
  assert.doesNotMatch(output(result), /KNOWLEDGE_CHAIN_PASS:/);
});

test('course cannot cross-wire verification and writeback outside each Source ID unique five-role path', () => {
  const root = makeValidChain();
  const verification = join(root, 'wiki/90_outputs/courses/verification/VER-20260729-g2.md');
  const writeback = join(root, 'wiki/90_outputs/courses/writeback/WB-20260729-g2.md');
  cpSync(verification, join(root, 'wiki/90_outputs/courses/verification/VER-20260729-alt.md'));
  cpSync(writeback, join(root, 'wiki/90_outputs/courses/writeback/WB-20260729-alt.md'));
  const course = join(root, 'wiki/90_outputs/courses/id-0003-course.md');
  writeFileSync(course, readFileSync(course, 'utf8')
    .replace('verification/VER-20260729-g2.md', 'verification/VER-20260729-alt.md')
    .replace('writeback/WB-20260729-g2.md', 'writeback/WB-20260729-alt.md'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /unique verification-record path does not match the course verification_record/);
  assert.match(output(result), /unique writeback-record path does not match the course writeback_record/);
});

test('course verification and writeback sources sets must match exactly', () => {
  const root = makeValidChain();
  const verification = join(root, 'wiki/90_outputs/courses/verification/VER-20260729-g2.md');
  writeFileSync(verification, readFileSync(verification, 'utf8').replace(/^sources:.*$/m, 'sources: []'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /course and verification sources sets must be exactly equal/);
});

test('one five-role ID cannot resolve to two different paths', () => {
  const root = makeValidChain();
  const alternate = 'wiki/20_concepts/id-0001-alternate.md';
  write(root, alternate, readFileSync(join(root, 'wiki/20_concepts/id-0001-concept.md'), 'utf8'));
  const sourceNote = join(root, 'wiki/10_sources/SRC-20260729-0001.md');
  writeFileSync(sourceNote, readFileSync(sourceNote, 'utf8').replace('../30_playbooks/id-0002-playbook.md', '../20_concepts/id-0001-alternate.md'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /role ID concept:ID-0001 is reused by different paths/);
});

test('an unreferenced durable page cannot reuse a five-role ID', () => {
  const root = makeValidChain();
  write(root, 'wiki/20_concepts/id-0001-orphan-duplicate.md', readFileSync(join(root, 'wiki/20_concepts/id-0001-concept.md'), 'utf8'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /role ID concept:ID-0001 is reused by different paths/);
});

test('unknown split verification states fail closed in structural mode', () => {
  const root = makeValidChain();
  for (const relativePath of ['wiki/90_outputs/courses/id-0003-course.md', 'wiki/90_outputs/courses/verification/VER-20260729-g2.md']) {
    const target = join(root, relativePath);
    writeFileSync(target, readFileSync(target, 'utf8').replace('structure_verification_status: "verified"', 'structure_verification_status: "self-asserted-pass"'));
  }
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /unknown structure_verification_status self-asserted-pass/);
});

test('course and verification three-layer states must match exactly', () => {
  const root = makeValidChain();
  const course = join(root, 'wiki/90_outputs/courses/id-0003-course.md');
  writeFileSync(course, readFileSync(course, 'utf8').replace('exercise_verification_status: "verified"', 'exercise_verification_status: "pending"'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /course and verification exercise_verification_status must match exactly/);
  assert.doesNotMatch(output(result), /KNOWLEDGE_CHAIN_STRUCTURE_PASS/);
});

test('signed canonical manifest detects mutation of every upstream and evidence artifact', (t) => {
  if (command(repoRoot, 'gpg', ['--version']).status !== 0) return t.skip('gpg is unavailable');
  const root = makeValidChain();
  const approval = createSignedFixtureApproval(root);
  const args = ['--release', '--course-approval', approval.approvalPath, '--course-approval-signature', approval.signaturePath, '--source-commit', approval.sourceCommit];
  const env = { GNUPGHOME: approval.gpgHome, COURSE_REVIEW_TRUSTED_SIGNERS: approval.fingerprint };
  const baseline = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'), args, { env });
  assert.notEqual(baseline.status, 0, output(baseline));
  assert.match(output(baseline), /synthetic fixture signer or reviewer_identity=not_verified cannot qualify a formal release/);
  assert.doesNotMatch(output(baseline), /KNOWLEDGE_CHAIN_RELEASE_PASS/);
  assert.doesNotMatch(output(baseline), /signed canonical knowledge_chain_manifest does not match/);
  const paths = [
    'raw/10_conversations/src-20260729-0001-fixture.md',
    'wiki/10_sources/SRC-20260729-0001.md',
    'wiki/20_concepts/id-0001-concept.md',
    'wiki/30_playbooks/id-0002-playbook.md',
    'wiki/90_outputs/courses/id-0003-course.md',
    'wiki/90_outputs/courses/evidence/EX-20260729-g2.md',
    'wiki/90_outputs/courses/reviews/REV-20260729-g2.md',
    'wiki/90_outputs/courses/verification/VER-20260729-g2.md',
    'wiki/90_outputs/courses/writeback/WB-20260729-g2.md',
  ];
  for (const relativePath of paths) {
    const target = join(root, relativePath);
    const original = readFileSync(target, 'utf8');
    writeFileSync(target, `${original}\n<!-- mutation attack -->\n`);
    const attacked = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'), args, { env });
    assert.notEqual(attacked.status, 0, `${relativePath}: ${output(attacked)}`);
    assert.match(output(attacked), /signed canonical knowledge_chain_manifest does not match/, relativePath);
    writeFileSync(target, original);
  }
});

test('synthetic-only chain cannot claim real-world effectiveness', () => {
  const root = makeValidChain();
  for (const relativePath of ['wiki/90_outputs/courses/id-0003-course.md', 'wiki/90_outputs/courses/verification/VER-20260729-g2.md']) {
    const target = join(root, relativePath);
    writeFileSync(target, readFileSync(target, 'utf8').replace('effectiveness_verification_status: "unverified"', 'effectiveness_verification_status: "real-world-effectiveness-verified"'));
  }
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /synthetic-only knowledge chain cannot claim real-world-effectiveness-verified/);
});

test('duplicate front matter keys fail closed instead of last-value-wins', () => {
  const root = makeValidChain();
  const raw = join(root, 'raw/10_conversations/src-20260729-0001-fixture.md');
  writeFileSync(raw, readFileSync(raw, 'utf8').replace('synthetic: true', 'synthetic: false\nsynthetic: true'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /duplicate metadata key\(s\): synthetic/);
});

test('non-array sources and mapping-shaped safety fields fail closed', () => {
  const root = makeValidChain();
  const course = join(root, 'wiki/90_outputs/courses/id-0003-course.md');
  writeFileSync(course, readFileSync(course, 'utf8').replace(/^sources:.*$/m, 'sources: "SRC-20260729-0001"'));
  const raw = join(root, 'raw/10_conversations/src-20260729-0001-fixture.md');
  writeFileSync(raw, readFileSync(raw, 'utf8').replace('synthetic: true', 'synthetic: { value: true }'));
  const result = run(root, join(root, 'scripts/validate-knowledge-chain.mjs'));
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /flow mappings are not supported/);
  assert.match(output(result), /sources must be an array/);
});

test('course verification and writeback templates expose validator fields with safe defaults', () => {
  const course = readFileSync(join(repoRoot, 'wiki/_templates/course-module.md'), 'utf8');
  for (const field of ['structure_verification_status', 'exercise_verification_status', 'effectiveness_verification_status', 'exercise_artifact', 'review_record', 'verification_record', 'writeback_record']) assert.match(course, new RegExp(`^${field}:`, 'm'), field);
  assert.match(course, /^structure_verification_status: "pending"$/m);
  assert.match(course, /^exercise_verification_status: "pending"$/m);
  assert.match(course, /^effectiveness_verification_status: "unverified"$/m);
  assert.doesNotMatch(course, /^exercise_status:/m);
  assert.doesNotMatch(course, /^verification_status:/m);
  const verification = readFileSync(join(repoRoot, 'wiki/_templates/verification-record.md'), 'utf8');
  for (const field of ['structure_verification_status', 'exercise_verification_status', 'effectiveness_verification_status', 'sample_size', 'observed_result', 'allowed_claim', 'non_claim']) assert.match(verification, new RegExp(`^${field}:`, 'm'), field);
  assert.match(verification, /^structure_verification_status: "pending"$/m);
  assert.match(verification, /^exercise_verification_status: "pending"$/m);
  assert.match(verification, /^effectiveness_verification_status: "unverified"$/m);
  const writeback = readFileSync(join(repoRoot, 'wiki/_templates/writeback-record.md'), 'utf8');
  for (const field of ['writeback_status', 'change_summary', 'writeback_targets']) assert.match(writeback, new RegExp(`^${field}:`, 'm'), field);
  assert.match(writeback, /^writeback_status: "pending"$/m);
});

test('structured templates generate correct course concept playbook source and raw schemas', () => {
  const cases = [
    ['wiki/20_concepts', 'wiki/_templates/concept-page.md', 'concept', 'concept', true, []],
    ['wiki/30_playbooks', 'wiki/_templates/playbook.md', 'playbook', 'playbook', true, []],
    ['wiki/90_outputs/courses', 'wiki/_templates/course-module.md', 'course', 'course-module', true, ['--source-id', 'SRC-20990101-9999']],
    ['wiki/10_sources', 'wiki/_templates/source-note.md', 'source', 'source-note', false, ['--source-id', 'SRC-20990101-9999', '--raw-path', 'raw/10_conversations/src-20990101-9999-g2.md'], true],
    ['raw/10_conversations', 'raw/_templates/conversation-source.md', 'raw', 'conversation-source', false, ['--source-id', 'SRC-20990101-9999']],
  ];
  for (const [dir, template, slug, type, needsDocId, extra, isolated = false] of cases) {
    let runRoot = repoRoot;
    let runScript = creatorSource;
    if (isolated) {
      runRoot = tempRoot('701-g2-source-create-');
      runScript = join(runRoot, 'scripts/create-document.mjs');
      write(runRoot, 'scripts/create-document.mjs', readFileSync(creatorSource, 'utf8'));
      write(runRoot, template, readFileSync(join(repoRoot, template), 'utf8'));
      write(runRoot, 'raw/10_conversations/src-20990101-9999-g2.md', fm({ source_id: '"SRC-20990101-9999"', title: '"Raw"', description: '"Raw fixture for isolated source note creation test."', type: '"conversation-source"', status: '"Seed"', owner: '"AI"', created: '"2099-01-01"', last_updated: '"2099-01-01"', sources: '[]', related: '[]' }, '# Raw'));
    }
    const retrievalArgs = needsDocId
      ? ['--when-to-read', `需要创建并核对 ${slug} durable 页面结构、范围与检索入口时。`, '--keywords', `${slug},template contract,retrieval metadata`]
      : [];
    const result = run(runRoot, runScript, ['--dir', dir, '--slug', `g2-${slug}-probe`, '--title', `G2 ${slug} probe`, '--description', `用于对抗验证 ${slug} 模板只渲染显式 payload、类型正确、标识正确且不会继承正文代码块字段。`, '--template', template, ...extra, ...retrievalArgs, '--date', '2026-07-29', '--dry-run']);
    assert.equal(result.status, 0, `${slug}: ${output(result)}`);
    assert.match(output(result), new RegExp(`type: "${type}"`));
    if (needsDocId) assert.match(output(result), /doc_id: "ID-\d{4}"/);
    else assert.doesNotMatch(output(result), /^doc_id:/m);
    assert.match(output(result), /VALIDATED:/);
  }
});

test('body code block cannot spoof a missing payload doc_id and failed generation never says CREATED', () => {
  const root = tempRoot('701-g2-create-');
  write(root, 'scripts/create-document.mjs', readFileSync(creatorSource, 'utf8'));
  write(root, 'wiki/_templates/attack.md', fm({ title: '"Attack"', description: '"Attack template."', type: '"template"', status: '"Working"', owner: '"AI"', created: '"2026-07-29"', last_updated: '"2026-07-29"', sources: '[]', related: '[]', when_to_read: '"需要验证正文代码块无法伪造结构化 payload 字段时。"', keywords: '["payload spoofing", "doc id", "creator contract"]', template_usage: '"creator-compatible"', template_target_kind: '"durable"', template_target_type: '"concept"' }, '```yaml\ndoc_id: "ID-9999"\n```\n<!-- DOCUMENT_TEMPLATE_START -->\n---\ntitle: "{{title}}"\ndescription: "{{description}}"\ntype: "{{type}}"\nstatus: "Seed"\nowner: "AI"\ncreated: "{{today}}"\nlast_updated: "{{today}}"\nsources: []\nrelated: []\n---\n# {{title}}\n<!-- DOCUMENT_TEMPLATE_END -->'));
  mkdirSync(join(root, 'wiki/20_concepts'), { recursive: true });
  const result = run(root, join(root, 'scripts/create-document.mjs'), ['--dir', 'wiki/20_concepts', '--slug', 'attack', '--title', 'Attack', '--description', '用于验证正文代码块中的 doc_id 不能绕过结构化 payload 的真实 front matter 校验。', '--template', 'wiki/_templates/attack.md', '--when-to-read', '需要验证 payload 真实字段而不是正文代码块伪造值时。', '--keywords', 'payload spoofing,doc id,creator contract', '--date', '2026-07-29']);
  assert.notEqual(result.status, 0, output(result));
  assert.match(output(result), /doc_id must equal/);
  assert.doesNotMatch(output(result), /CREATED:/);
  assert.equal(existsSync(join(root, 'wiki/20_concepts/id-0001-attack.md')), false);
});
