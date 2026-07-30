#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const tests = [];

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function canonicalRefs(refs) {
  return refs.map((ref) => ({ kind: ref.kind, locator: ref.locator, sha256: ref.sha256 }))
    .sort((left, right) => compareText(`${left.kind}\0${left.locator}\0${left.sha256}`, `${right.kind}\0${right.locator}\0${right.sha256}`));
}

function bundleDigest(refs) {
  return `sha256:${sha256(JSON.stringify(canonicalRefs(refs)))}`;
}

function eventPayload(id, fields) {
  const payload = {
    event_id: id,
    occurred_at: fields.occurred_at,
    recorded_at: fields.recorded_at,
    actor: fields.actor,
    scope: fields.scope,
    action: fields.action,
    evidence: fields.evidence,
    commands: fields.commands,
    files_changed: fields.files_changed,
    result: fields.result,
    risk: fields.risk,
    next: fields.next,
    writeback: fields.writeback,
    correction_of: fields.correction_of,
    evidence_digest: fields.evidence_summary_digest,
  };
  if (fields.evidence_role !== undefined) payload.evidence_role = fields.evidence_role;
  if (fields.evidence_refs !== undefined) payload.evidence_refs = fields.evidence_refs;
  if (fields.evidence_bundle_digest !== undefined) payload.evidence_bundle_digest = fields.evidence_bundle_digest;
  return JSON.stringify(payload);
}

function renderEvent({ id = 'EVT-20260727-9001', overrides = {}, duplicateLine = '', summaryLabel = 'evidence_summary_digest' } = {}) {
  const fields = {
    occurred_at: '2026-07-27T10:00:00+08:00',
    recorded_at: '2026-07-27T10:01:00+08:00',
    actor: 'G5 fixture',
    scope: 'mother-library',
    action: 'exercise the log validator',
    evidence: 'synthetic fixture only',
    commands: 'node scripts/validate-logs.mjs --release',
    files_changed: 'none',
    result: 'fixture complete',
    risk: 'none',
    next: 'none',
    writeback: 'none',
    correction_of: 'none',
    evidence_role: 'summary-only',
    ...overrides,
  };
  fields.evidence_summary_digest = overrides.evidence_summary_digest ?? `sha256:${sha256(fields.evidence)}`;
  if (fields.evidence_refs_array) {
    fields.evidence_refs = JSON.stringify(fields.evidence_refs_array);
    delete fields.evidence_refs_array;
  }
  if (fields.evidence_role === 'qualification' && fields.evidence_bundle_digest === 'auto') {
    fields.evidence_bundle_digest = bundleDigest(JSON.parse(fields.evidence_refs));
  }
  fields.event_digest = overrides.event_digest ?? `sha256:${sha256(eventPayload(id, fields))}`;
  const optional = [];
  if (fields.evidence_role !== undefined) optional.push(`- **evidence_role**：${fields.evidence_role}\n`);
  if (fields.evidence_refs !== undefined) optional.push(`- **evidence_refs**：${fields.evidence_refs}\n`);
  if (fields.evidence_bundle_digest !== undefined) optional.push(`- **evidence_bundle_digest**：${fields.evidence_bundle_digest}\n`);
  return `### ${id} — synthetic G5 fixture\n\n`
    + `- **occurred_at**：${fields.occurred_at}\n`
    + `- **recorded_at**：${fields.recorded_at}\n`
    + `- **actor**：${fields.actor}\n`
    + `- **scope**：${fields.scope}\n`
    + `- **action**：${fields.action}\n`
    + `- **evidence**：${fields.evidence}\n`
    + `- **${summaryLabel}**：${fields.evidence_summary_digest}\n`
    + optional.join('')
    + `- **commands**：${fields.commands}\n`
    + `- **files changed**：${fields.files_changed}\n`
    + `- **result**：${fields.result}\n`
    + `- **risk / blocker**：${fields.risk}\n`
    + duplicateLine
    + `- **next**：${fields.next}\n`
    + `- **writeback**：${fields.writeback}\n`
    + `- **correction_of**：${fields.correction_of}\n`
    + `- **event_digest**：${fields.event_digest}\n`;
}

function frontmatter(extra = '') {
  return `---\ntitle: "fixture"\ndescription: "fixture"\ntype: "log"\nstatus: "Working"\nowner: "AI"\ncreated: "2026-07-27"\nlast_updated: "2026-07-27"\nsources: []\nrelated: []\nvisibility: "public"\nredaction_status: "safe-to-publish"\n${extra}---\n# Fixture\n\n`;
}

function withFixture(callback) {
  const root = mkdtempSync(join(tmpdir(), '701-g5-test-'));
  try {
    mkdirSync(join(root, 'scripts/schemas'), { recursive: true });
    mkdirSync(join(root, 'scripts/lib'), { recursive: true });
    cpSync(join(repoRoot, 'scripts/validate-logs.mjs'), join(root, 'scripts/validate-logs.mjs'));
    cpSync(join(repoRoot, 'scripts/validate-handoff.mjs'), join(root, 'scripts/validate-handoff.mjs'));
    cpSync(join(repoRoot, 'scripts/lib/public-network-policy.mjs'), join(root, 'scripts/lib/public-network-policy.mjs'));
    cpSync(join(repoRoot, 'scripts/log-legacy-digest-baseline.json'), join(root, 'scripts/log-legacy-digest-baseline.json'));
    cpSync(join(repoRoot, 'scripts/schemas/handoff.schema.json'), join(root, 'scripts/schemas/handoff.schema.json'));
    for (const date of ['2026-07-28', '2026-07-29']) {
      const targetDir = join(root, 'wiki/00_meta/logs/2026/07');
      mkdirSync(targetDir, { recursive: true });
      cpSync(join(repoRoot, `wiki/00_meta/logs/2026/07/${date}.md`), join(targetDir, `${date}.md`));
    }
    callback(root);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

function writeDaily(root, date, content, shard = '') {
  const [year, month] = date.split('-');
  const dir = join(root, 'wiki/00_meta/logs', year, month);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, `${date}${shard ? `--${shard}` : ''}.md`), content);
}

function run(root, script, args) {
  return spawnSync(process.execPath, [script, ...args], { cwd: root, encoding: 'utf8' });
}

function runLogs(root, ...args) {
  return run(root, 'scripts/validate-logs.mjs', args.length ? args : ['--release']);
}

function runHandoff(root, file = 'handoff.json', release = false) {
  return run(root, 'scripts/validate-handoff.mjs', ['--file', file, ...(release ? ['--release'] : [])]);
}

function output(result) {
  return `${result.stdout}\n${result.stderr}`;
}

function expectPass(result, pattern) {
  if (result.status !== 0 || (pattern && !pattern.test(output(result)))) throw new Error(`expected pass, got ${result.status}: ${output(result)}`);
}

function expectReject(result, pattern) {
  if (result.status === 0 || !pattern.test(output(result))) throw new Error(`expected rejection ${pattern}, got ${result.status}: ${output(result)}`);
}

function test(name, fn) {
  tests.push([name, fn]);
}

function repinBaseline(root, mutate) {
  const baselinePath = join(root, 'scripts/log-legacy-digest-baseline.json');
  const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'));
  mutate(baseline);
  const canonical = [...baseline.entries].map(({ event_id, path, sha256: digest }) => ({ event_id, path, sha256: digest }))
    .sort((left, right) => compareText(`${left.path}\0${left.event_id}`, `${right.path}\0${right.event_id}`));
  baseline.entries_digest = `sha256:${sha256(JSON.stringify(canonical))}`;
  const bytes = `${JSON.stringify(baseline, null, 2)}\n`;
  writeFileSync(baselinePath, bytes);
  const validatorPath = join(root, 'scripts/validate-logs.mjs');
  const validator = readFileSync(validatorPath, 'utf8').replace(/const pinnedBaselineFileSha256 = '[0-9a-f]{64}';/, `const pinnedBaselineFileSha256 = '${sha256(bytes)}';`);
  writeFileSync(validatorPath, validator);
}

function repoRef(root, locator, content) {
  const path = join(root, locator);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
  return { kind: 'repository-relative', locator, sha256: `sha256:${sha256(content)}` };
}

function immutableRef(seed) {
  const digest = `sha256:${sha256(seed)}`;
  return { kind: 'immutable-https', locator: `https://evidence.example/objects/${digest.slice(7)}/record.json`, sha256: digest };
}

function binding(record) {
  return {
    handoff_id: record.handoff_id,
    scope: record.scope,
    reviewer_agent_id: record.reviewer.agent_id,
    source_commit: record.scope_binding.source_commit,
    content_digest: record.scope_binding.content_digest,
    verdict: record.verdict,
  };
}

function claimRef(record, claimType) {
  const statement = JSON.stringify({ schema_version: 1, claim_type: claimType, ...binding(record) });
  return immutableRef(statement);
}

function validHandoff(root) {
  const sourceCommit = 'a'.repeat(40);
  const scopeManifest = repoRef(root, 'scope/manifest.json', `${JSON.stringify({ schema_version: 1, scope: 'file-set:G5', head: sourceCommit })}\n`);
  const record = {
    schema_version: 1,
    handoff_id: 'HND-20260729-G5-0001',
    scope: 'file-set:G5',
    producer: { name: 'Producer', agent_id: 'producer-task-1' },
    reviewer: { name: 'Reviewer', agent_id: 'reviewer-task-2' },
    reviewer_provenance: 'reviewer-authored',
    identity_status: 'verified',
    independence_status: 'verified',
    scope_binding: {
      scope_manifest: scopeManifest,
      source_commit: sourceCommit,
      source_commit_binding: 'content-bound',
      content_digest: scopeManifest.sha256,
    },
    original_verdict: { available: true, immutable: true, ref: null, binding: null },
    attestations: {
      identity: { ref: null, binding: null },
      independence: { ref: null, binding: null },
      reviewer_authorship: { ref: null, binding: null },
    },
    verdict: 'pass',
    blocks_next_step: false,
    evidence_refs: [],
    evidence_bundle_digest: '',
    not_verified: ['local validation does not retrieve remote locators or prove human identity'],
    return_to: 'producer',
    approval_required: 'Tony before publish',
  };
  const exact = binding(record);
  record.original_verdict.ref = claimRef(record, 'original-verdict');
  record.original_verdict.binding = { ...exact };
  for (const [name, attestation] of Object.entries(record.attestations)) {
    attestation.ref = claimRef(record, `attestation:${name}`);
    attestation.binding = { ...exact };
  }
  record.evidence_refs = [scopeManifest, record.original_verdict.ref, ...Object.values(record.attestations).map((item) => item.ref)];
  record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
  return record;
}

function writeHandoff(root, record, name = 'handoff.json') {
  writeFileSync(join(root, name), `${JSON.stringify(record, null, 2)}\n`);
}

// Log v2 and baseline integrity.
test('valid-summary-event', () => withFixture((root) => {
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent());
  expectPass(runLogs(root), /LOG_VALIDATION_PASS/);
}));


test('valid-scope-shards-are-all-scanned', () => withFixture((root) => {
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ id: 'EVT-20260727-9001', overrides: { scope: 'mother-library' } }), 'mother-library');
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ id: 'EVT-20260727-9002', overrides: { scope: 'sub-library:website-content-ops' } }), 'sub-library-website-content-ops');
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ id: 'EVT-20260727-9003', overrides: { scope: 'private-runtime:customer-a' } }), 'private-runtime-customer-a');
  const result = runLogs(root);
  expectPass(result, /LOG_VALIDATION_PASS/);
  if (!/daily_logs=5(?:\s|$)/.test(output(result))) throw new Error(`expected all three shards plus two frozen logs to be counted: ${output(result)}`);
}));

test('bad-event-inside-valid-shard-is-not-skipped', () => withFixture((root) => {
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { event_digest: `sha256:${'0'.repeat(64)}` } }), 'mother-library');
  expectReject(runLogs(root), /event_digest mismatch/);
}));

test('scope-shard-requires-exact-event-scope', () => withFixture((root) => {
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { scope: 'mother-library' } }), 'sub-library-website-content-ops');
  expectReject(runLogs(root), /scope shard requires exact event scope `sub-library:website-content-ops`, got `mother-library`/);
}));

test('malformed-scope-shard-filename-is-rejected', () => withFixture((root) => {
  const path = join(root, 'wiki/00_meta/logs/2026/07/2026-07-27--sub-library-.md');
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, frontmatter() + renderEvent({ overrides: { scope: 'sub-library:website-content-ops' } }));
  expectReject(runLogs(root), /malformed daily log filename under YYYY\/MM/);
}));

test('legacy-event-tamper-release-rejected', () => withFixture((root) => {
  const path = join(root, 'wiki/00_meta/logs/2026/07/2026-07-28.md');
  writeFileSync(path, readFileSync(path, 'utf8').replace('### EVT-20260728-0001 — 结构升级方案落地', '### EVT-20260728-0001 — tampered title'));
  expectReject(runLogs(root), /frozen legacy event digest mismatch/);
}));

test('baseline-byte-tamper-rejected-by-pin', () => withFixture((root) => {
  const path = join(root, 'scripts/log-legacy-digest-baseline.json');
  writeFileSync(path, `${readFileSync(path, 'utf8')} `);
  expectReject(runLogs(root), /baseline file digest mismatch/);
}));

test('baseline-missing-entry-rejected-even-when-repinned', () => withFixture((root) => {
  repinBaseline(root, (baseline) => baseline.entries.shift());
  expectReject(runLogs(root), /legacy event is not present in the independent digest baseline/);
}));

test('baseline-duplicate-entry-rejected-even-when-repinned', () => withFixture((root) => {
  repinBaseline(root, (baseline) => baseline.entries.push({ ...baseline.entries[0] }));
  expectReject(runLogs(root), /baseline contains duplicate entry/);
}));

test('new-event-legacy-evidence-digest-alias-rejected', () => withFixture((root) => {
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ summaryLabel: 'evidence_digest' }));
  expectReject(runLogs(root), /evidence_digest is a frozen historical alias/);
}));

test('summary-only-cannot-smuggle-qualification-refs', () => withFixture((root) => {
  const ref = repoRef(root, 'evidence/summary.txt', 'summary');
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_refs_array: [ref], evidence_bundle_digest: bundleDigest([ref]) } }));
  expectReject(runLogs(root), /summary-only evidence must not present/);
}));

test('valid-qualification-evidence', () => withFixture((root) => {
  const ref = repoRef(root, 'evidence/proof.txt', 'proof bytes');
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: 'auto' } }));
  expectPass(runLogs(root), /qualification_evidence_events=1/);
}));

test('qualification-repository-evidence-content-tamper-rejected', () => withFixture((root) => {
  const ref = repoRef(root, 'evidence/proof.txt', 'proof bytes');
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: 'auto' } }));
  writeFileSync(join(root, ref.locator), 'changed bytes');
  expectReject(runLogs(root), /repository evidence digest mismatch/);
}));

test('qualification-empty-refs-rejected', () => withFixture((root) => {
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [], evidence_bundle_digest: bundleDigest([]) } }));
  expectReject(runLogs(root), /requires at least one evidence_refs entry/);
}));

test('qualification-arbitrary-bundle-digest-rejected', () => withFixture((root) => {
  const ref = repoRef(root, 'evidence/proof.txt', 'proof bytes');
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: `sha256:${'0'.repeat(64)}` } }));
  expectReject(runLogs(root), /evidence_bundle_digest mismatch/);
}));

test('qualification-absolute-path-rejected', () => withFixture((root) => {
  const ref = { kind: 'repository-relative', locator: '/' + ['t', 'm', 'p'].join('') + '/proof', sha256: `sha256:${'0'.repeat(64)}` };
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: bundleDigest([ref]) } }));
  expectReject(runLogs(root), /not a clean repository path/);
}));

test('qualification-parent-path-rejected', () => withFixture((root) => {
  const ref = { kind: 'repository-relative', locator: '../proof', sha256: `sha256:${'0'.repeat(64)}` };
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: bundleDigest([ref]) } }));
  expectReject(runLogs(root), /dot segment/);
}));

test('qualification-repository-symlink-escape-rejected', () => withFixture((root) => {
  const outside = mkdtempSync(join(tmpdir(), '701-g5-outside-'));
  try {
    const outsideFile = join(outside, 'proof.txt');
    writeFileSync(outsideFile, 'outside proof');
    mkdirSync(join(root, 'evidence'), { recursive: true });
    symlinkSync(outsideFile, join(root, 'evidence/proof-link.txt'));
    const ref = { kind: 'repository-relative', locator: 'evidence/proof-link.txt', sha256: `sha256:${sha256('outside proof')}` };
    writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: bundleDigest([ref]) } }));
    expectReject(runLogs(root), /must not traverse a symlink/);
  } finally {
    rmSync(outside, { recursive: true, force: true });
  }
}));

test('qualification-mutable-https-rejected', () => withFixture((root) => {
  const digest = `sha256:${'a'.repeat(64)}`;
  const ref = { kind: 'immutable-https', locator: `https://example.com/latest/${digest.slice(7)}/proof.json`, sha256: digest };
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: bundleDigest([ref]) } }));
  expectReject(runLogs(root), /mutable or dot segment/);
}));

test('qualification-private-https-rejected', () => withFixture((root) => {
  const digest = `sha256:${'a'.repeat(64)}`;
  const ref = { kind: 'immutable-https', locator: `https://127.0.0.1/${digest.slice(7)}/proof.json`, sha256: digest };
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: bundleDigest([ref]) } }));
  expectReject(runLogs(root), /private host/);
}));

test('qualification-private-ipv6-https-rejected', () => withFixture((root) => {
  for (const host of ['[::1]', '[fc00::1]', '[fd00::1]', '[fe80::1]']) {
    const digest = `sha256:${sha256(host)}`;
    const ref = { kind: 'immutable-https', locator: `https://${host}/${digest.slice(7)}/proof.json`, sha256: digest };
    writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: bundleDigest([ref]) } }));
    expectReject(runLogs(root), /private host/);
  }
}));

test('qualification-invalid-url-encoding-rejected-without-crash', () => withFixture((root) => {
  const digest = `sha256:${'a'.repeat(64)}`;
  const ref = { kind: 'immutable-https', locator: `https://example.com/%ZZ/${digest.slice(7)}`, sha256: digest };
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { evidence_role: 'qualification', evidence_refs_array: [ref], evidence_bundle_digest: bundleDigest([ref]) } }));
  expectReject(runLogs(root), /invalid percent-encoding/);
}));

// Correction graph and effective/superseded closure.
test('unknown-correction-target-rejected', () => withFixture((root) => {
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { correction_of: 'EVT-20260727-8999' } }));
  expectReject(runLogs(root), /references unknown event_id/);
}));

test('self-correction-rejected', () => withFixture((root) => {
  writeDaily(root, '2026-07-27', frontmatter() + renderEvent({ overrides: { correction_of: 'EVT-20260727-9001' } }));
  expectReject(runLogs(root), /cannot reference the event itself/);
}));

test('two-node-correction-cycle-rejected', () => withFixture((root) => {
  const a = renderEvent({ id: 'EVT-20260727-9001', overrides: { correction_of: 'EVT-20260727-9002' } });
  const b = renderEvent({ id: 'EVT-20260727-9002', overrides: { occurred_at: '2026-07-27T10:02:00+08:00', recorded_at: '2026-07-27T10:03:00+08:00', correction_of: 'EVT-20260727-9001' } });
  writeDaily(root, '2026-07-27', frontmatter() + a + '\n' + b);
  expectReject(runLogs(root), /correction_of cycle detected/);
}));

test('three-node-correction-cycle-rejected', () => withFixture((root) => {
  const a = renderEvent({ id: 'EVT-20260727-9001', overrides: { correction_of: 'EVT-20260727-9003' } });
  const b = renderEvent({ id: 'EVT-20260727-9002', overrides: { occurred_at: '2026-07-27T10:02:00+08:00', recorded_at: '2026-07-27T10:03:00+08:00', correction_of: 'EVT-20260727-9001' } });
  const c = renderEvent({ id: 'EVT-20260727-9003', overrides: { occurred_at: '2026-07-27T10:04:00+08:00', recorded_at: '2026-07-27T10:05:00+08:00', correction_of: 'EVT-20260727-9002' } });
  writeDaily(root, '2026-07-27', frontmatter() + a + '\n' + b + '\n' + c);
  expectReject(runLogs(root), /correction_of cycle detected/);
}));

test('parallel-direct-corrections-rejected-as-ambiguous', () => withFixture((root) => {
  const a = renderEvent({ id: 'EVT-20260727-9001' });
  const b = renderEvent({ id: 'EVT-20260727-9002', overrides: { occurred_at: '2026-07-27T10:02:00+08:00', recorded_at: '2026-07-27T10:03:00+08:00', correction_of: 'EVT-20260727-9001' } });
  const c = renderEvent({ id: 'EVT-20260727-9003', overrides: { occurred_at: '2026-07-27T10:04:00+08:00', recorded_at: '2026-07-27T10:05:00+08:00', correction_of: 'EVT-20260727-9001' } });
  writeDaily(root, '2026-07-27', frontmatter() + a + '\n' + b + '\n' + c);
  expectReject(runLogs(root), /already has direct correction/);
}));

test('correction-closure-emits-effective-and-superseded-view', () => withFixture((root) => {
  const a = renderEvent({ id: 'EVT-20260727-9001', overrides: { result: 'PASS claim' } });
  const b = renderEvent({ id: 'EVT-20260727-9002', overrides: { occurred_at: '2026-07-27T10:02:00+08:00', recorded_at: '2026-07-27T10:03:00+08:00', correction_of: 'EVT-20260727-9001', result: 'WARN correction' } });
  const c = renderEvent({ id: 'EVT-20260727-9003', overrides: { occurred_at: '2026-07-27T10:04:00+08:00', recorded_at: '2026-07-27T10:05:00+08:00', correction_of: 'EVT-20260727-9002', result: 'BLOCK correction' } });
  writeDaily(root, '2026-07-27', frontmatter() + a + '\n' + b + '\n' + c);
  const result = runLogs(root, '--release', '--closure-json');
  expectPass(result, /LOG_VALIDATION_PASS/);
  const text = output(result);
  if (!text.includes('"event_id":"EVT-20260727-9001","effective_event_id":"EVT-20260727-9003"')
    || !text.includes('"event_id":"EVT-20260727-9002","effective_event_id":"EVT-20260727-9003"')
    || !text.includes('LOG_FACTUAL_VERDICT: not_verified')) throw new Error(`closure or factual boundary missing: ${text}`);
}));

// Handoff schema, provenance, attestation, and release fail-closed behavior.
test('valid-handoff-pass-structure-and-release-contract', () => withFixture((root) => {
  writeHandoff(root, validHandoff(root));
  expectPass(runHandoff(root, 'handoff.json', true), /HANDOFF_RECORD_STRUCTURE_PASS/);
}));

test('handoff-private-ipv6-attestation-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  const digest = record.original_verdict.ref.sha256;
  record.original_verdict.ref = { ...record.original_verdict.ref, locator: `https://[::1]/objects/${digest.slice(7)}/record.json` };
  record.evidence_refs = [record.scope_binding.scope_manifest, record.original_verdict.ref, ...Object.values(record.attestations).map((item) => item.ref)];
  record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
  writeHandoff(root, record);
  expectReject(runHandoff(root, 'handoff.json', true), /private host/);
}));

test('handoff-schema-byte-tamper-rejected', () => withFixture((root) => {
  writeHandoff(root, validHandoff(root));
  const path = join(root, 'scripts/schemas/handoff.schema.json');
  writeFileSync(path, `${readFileSync(path, 'utf8')} `);
  expectReject(runHandoff(root), /schema digest mismatch/);
}));

test('handoff-arbitrary-evidence-bundle-digest-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  record.evidence_bundle_digest = `sha256:${'0'.repeat(64)}`;
  writeHandoff(root, record);
  expectReject(runHandoff(root), /evidence_bundle_digest mismatch/);
}));

test('handoff-content-bound-manifest-commit-mismatch-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  record.scope_binding.source_commit = 'c'.repeat(40);
  const exact = binding(record);
  record.original_verdict.binding = { ...exact };
  record.original_verdict.ref = claimRef(record, 'original-verdict');
  for (const [name, attestation] of Object.entries(record.attestations)) {
    attestation.binding = { ...exact };
    attestation.ref = claimRef(record, `attestation:${name}`);
  }
  record.evidence_refs = [record.scope_binding.scope_manifest, record.original_verdict.ref, ...Object.values(record.attestations).map((item) => item.ref)];
  record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
  writeHandoff(root, record);
  expectReject(runHandoff(root, 'handoff.json', true), /does not match the content-bound scope_manifest commit/);
}));

test('handoff-content-bound-manifest-digest-mismatch-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  record.scope_binding.content_digest = `sha256:${'d'.repeat(64)}`;
  const exact = binding(record);
  record.original_verdict.binding = { ...exact };
  record.original_verdict.ref = claimRef(record, 'original-verdict');
  for (const [name, attestation] of Object.entries(record.attestations)) {
    attestation.binding = { ...exact };
    attestation.ref = claimRef(record, `attestation:${name}`);
  }
  record.evidence_refs = [record.scope_binding.scope_manifest, record.original_verdict.ref, ...Object.values(record.attestations).map((item) => item.ref)];
  record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
  writeHandoff(root, record);
  expectReject(runHandoff(root, 'handoff.json', true), /must equal the verified scope_manifest byte digest/);
}));

test('handoff-pass-producer-reported-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  record.reviewer_provenance = 'producer-reported';
  writeHandoff(root, record);
  expectReject(runHandoff(root), /pass cannot use producer-reported/);
}));

test('handoff-verified-without-external-attestation-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  record.attestations.identity = null;
  record.evidence_refs = record.evidence_refs.filter((ref) => ref.locator !== claimRef(record, 'attestation:identity').locator);
  record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
  writeHandoff(root, record);
  expectReject(runHandoff(root), /verified requires external identity attestation/);
}));

test('handoff-reviewer-authored-without-immutable-original-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  record.original_verdict = { available: false, immutable: false, ref: null, binding: null };
  record.evidence_refs = record.evidence_refs.filter((ref) => ref.locator !== claimRef(record, 'original-verdict').locator);
  record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
  writeHandoff(root, record);
  expectReject(runHandoff(root), /reviewer-authored provenance requires an available immutable original verdict/);
}));

test('handoff-attestation-scope-mismatch-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  record.attestations.independence.binding.scope = 'file-set:other';
  writeHandoff(root, record);
  expectReject(runHandoff(root), /does not bind the handoff scope\/reviewer\/source exactly/);
}));

test('handoff-special-ref-outside-bundle-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  record.evidence_refs = record.evidence_refs.filter((ref) => ref.locator !== record.original_verdict.ref.locator);
  record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
  writeHandoff(root, record);
  expectReject(runHandoff(root), /qualification ref is outside evidence_refs bundle/);
}));

test('handoff-scope-manifest-symlink-escape-rejected', () => withFixture((root) => {
  const record = validHandoff(root);
  const outside = mkdtempSync(join(tmpdir(), '701-g5-handoff-outside-'));
  try {
    const outsideFile = join(outside, 'manifest.json');
    writeFileSync(outsideFile, '{"scope":"outside"}\n');
    symlinkSync(outsideFile, join(root, 'scope/manifest-link.json'));
    const escaped = { kind: 'repository-relative', locator: 'scope/manifest-link.json', sha256: `sha256:${sha256('{"scope":"outside"}\n')}` };
    record.scope_binding.scope_manifest = escaped;
    record.evidence_refs[0] = escaped;
    record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
    writeHandoff(root, record);
    expectReject(runHandoff(root), /must not traverse a symlink/);
  } finally {
    rmSync(outside, { recursive: true, force: true });
  }
}));

test('handoff-block-record-valid-for-storage-but-release-fails-closed', () => withFixture((root) => {
  const record = validHandoff(root);
  record.verdict = 'block';
  record.blocks_next_step = true;
  record.reviewer_provenance = 'producer-reported';
  record.identity_status = 'not_verified';
  record.independence_status = 'not_verified';
  record.original_verdict = { available: false, immutable: false, ref: null, binding: null };
  record.attestations = { identity: null, independence: null, reviewer_authorship: null };
  record.evidence_refs = [record.scope_binding.scope_manifest];
  record.evidence_bundle_digest = bundleDigest(record.evidence_refs);
  writeHandoff(root, record);
  expectPass(runHandoff(root), /HANDOFF_RECORD_STRUCTURE_PASS/);
  expectReject(runHandoff(root, 'handoff.json', true), /release mode requires verdict=pass/);
}));

test('handoff-absolute-input-path-rejected', () => withFixture((root) => {
  writeHandoff(root, validHandoff(root));
  expectReject(runHandoff(root, join(root, 'handoff.json')), /--file must be a clean repository-relative path/);
}));

test('historical-review-records-remain-unverified', () => {
  const recordsDir = join(repoRoot, 'REVIEW-RECORDS');
  const records = readdirSync(recordsDir).filter((name) => /^REV-.*\.json$/.test(name));
  if (records.length !== 5) throw new Error(`expected 5 migrated reviewer records, got ${records.length}`);
  for (const name of records) {
    const record = JSON.parse(readFileSync(join(recordsDir, name), 'utf8'));
    if (record.provenance_status !== 'producer-reported') throw new Error(`${name} overstates provenance`);
    if (record.independence_status !== 'not_verified' || record.identity_status !== 'not_verified') throw new Error(`${name} overstates identity or independence`);
  }
});

let passed = 0;
for (const [name, fn] of tests) {
  try {
    fn();
    passed += 1;
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}: ${error.message}`);
  }
}
console.log(`G5_TEST_SUMMARY: total=${tests.length} passed=${passed} failed=${tests.length - passed}`);
if (passed !== tests.length) process.exitCode = 1;
