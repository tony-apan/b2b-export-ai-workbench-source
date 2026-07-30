#!/usr/bin/env node
import { cpSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { governanceCases } from './tests/governance-cases.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const root = resolve(dirname(scriptPath), '..');
const worker = join(root, 'scripts/tests/run-case.mjs');
const TEST_ALLOWLIST = [
  'frontmatter-missing-description',
  'frontmatter-missing-sources',
  'frontmatter-sources-scalar',
  'frontmatter-duplicate-key',
  'frontmatter-related-missing-path',
  'frontmatter-unknown-type',
  'index-grandchild-entry',
  'index-manual-grandchild-entry',
  'index-last-updated-stale',
  'index-stale-description',
  'document-id-duplicate-same-scope',
  'document-id-duplicate-cross-scope-allowed',
  'synthetic-real-verification-claim',
  'log-event-date-mismatch',
  'log-duplicate-event-id',
  'artifact-unknown-extension',
  'artifact-local-absolute-path',
  'artifact-manifest-path-preflight',
  'approval-ai-placeholder-rejected',
  'approval-decorated-ai-name-rejected',
  'approval-self-asserted-check-set-rejected',
  'approval-scope-crosswire',
  'approval-tag-crosswire',
  'approval-digest-crosswire',
  'approval-evidence-content-binding',
  'approval-mother-provenance-binding',
  'approval-sub-library-provenance-binding',
  'mother-builder-commit-provenance',
  'release-artifact-dirty-source',
  'release-final-state-requires-sidecar',
  'ordinary-final-state-artifact-requires-sidecar',
  'mother-sub-artifact-pass-isolation',
  'release-router-unknown-tag',
  'release-router-bare-tag',
  'release-router-mother-version-mismatch',
  'release-router-unregistered-sub-library',
  'release-router-mother-scope',
  'release-router-sub-library-scope',
  'approval-trigger-tag-crosswire',
  'approval-strict-trigger-required',
  'runtime-profile-control-files',
  'runtime-profile-symlink-boundaries',
  'runtime-subject-provenance-isolation',
  'tested-candidate-identity-binding',
  'trusted-node-test-summary',
  'two-phase-release-cli-boundaries',
  'approval-canonical-tag-binding',
  'qualification-archive-tree-equivalence',
  'qualification-runtime-contract',
  'qualification-attestation-binding',
  'formal-release-workflow-shape',
  'formal-release-evidence-workflow-shape',
  'mother-index-layered-sub-library-entry',
];

const args = process.argv.slice(2);
const listOnly = args.includes('--list');
const selectedFlag = args.indexOf('--test');
const timeoutFlag = args.indexOf('--timeout-ms');
const selected = selectedFlag >= 0 ? args[selectedFlag + 1] : '';
const perTestTimeoutMs = timeoutFlag >= 0 ? Number(args[timeoutFlag + 1]) : 30_000;
const unknownArgs = args.filter((arg, index) => {
  if (['--list', '--test', '--timeout-ms'].includes(arg)) return false;
  if (index === selectedFlag + 1 || index === timeoutFlag + 1) return false;
  return true;
});

if (unknownArgs.length) {
  console.error(`Unsupported argument(s): ${unknownArgs.join(', ')}`);
  process.exit(2);
}
if (!Number.isInteger(perTestTimeoutMs) || perTestTimeoutMs < 2_000 || perTestTimeoutMs > 120_000) {
  console.error('--timeout-ms must be an integer between 2000 and 120000');
  process.exit(2);
}

const registered = [...governanceCases.keys()];
const unregistered = TEST_ALLOWLIST.filter((id) => !governanceCases.has(id));
const unallowlisted = registered.filter((id) => !TEST_ALLOWLIST.includes(id));
const duplicates = TEST_ALLOWLIST.filter((id, index) => TEST_ALLOWLIST.indexOf(id) !== index);
if (unregistered.length || unallowlisted.length || duplicates.length) {
  console.error('GOVERNANCE_TEST_REGISTRY_INVALID');
  if (unregistered.length) console.error(`- allowlisted but missing implementation: ${unregistered.join(', ')}`);
  if (unallowlisted.length) console.error(`- implemented but not explicitly allowlisted: ${unallowlisted.join(', ')}`);
  if (duplicates.length) console.error(`- duplicate allowlist entries: ${[...new Set(duplicates)].join(', ')}`);
  process.exit(2);
}
if (selected && !TEST_ALLOWLIST.includes(selected)) {
  console.error(`Unknown or non-allowlisted test: ${selected}`);
  process.exit(2);
}

if (listOnly) {
  for (const id of TEST_ALLOWLIST) {
    const test = governanceCases.get(id);
    console.log(`${id}\t${test.expected}\t${test.title}`);
  }
  process.exit(0);
}

function gitStatus() {
  const result = spawnSync('git', ['status', '--porcelain=v1', '--untracked-files=all'], { cwd: root, encoding: 'utf8' });
  if (result.status !== 0) throw new Error(`could not snapshot source worktree status: ${result.stderr || result.stdout}`);
  return result.stdout;
}

function copyFixture(destination) {
  const excludedSegments = new Set([
    '.git',
    '.obsidian',
    '.cache',
    'node_modules',
    'dist',
    'coverage',
    'runtime',
    'customer-runtime',
    'credentials',
    'secrets',
    '.secrets',
    'private',
    'workspace',
  ]);
  cpSync(root, destination, {
    recursive: true,
    filter(source) {
      const rel = relative(root, source).split(sep).join('/');
      if (!rel) return true;
      const parts = rel.split('/');
      if (parts.some((part) => excludedSegments.has(part))) return false;
      if (parts.includes('.governance-fixtures')) return false;
      return true;
    },
  });
}

const sourceStatusBefore = gitStatus();
const ids = selected ? [selected] : TEST_ALLOWLIST;
const results = [];
const failures = [];

console.log(`GOVERNANCE_TEST_START: tests=${ids.length} timeout_ms=${perTestTimeoutMs}`);
for (const id of ids) {
  const tempRoot = mkdtempSync(join(tmpdir(), `701-governance-${id}-`));
  const fixtureRoot = join(tempRoot, 'repo');
  try {
    copyFixture(fixtureRoot);
    const result = spawnSync(process.execPath, [worker, id, fixtureRoot, String(Math.max(2_000, perTestTimeoutMs - 2_000))], {
      cwd: root,
      encoding: 'utf8',
      timeout: perTestTimeoutMs,
      env: { ...process.env, GOVERNANCE_TEST_FIXTURE: '1' },
    });
    const output = `${result.stdout ?? ''}${result.stderr ?? ''}`;
    const marker = [...output.matchAll(/^CASE_RESULT:(\{.*\})$/gm)].at(-1)?.[1];
    if (result.error) throw new Error(result.error.code === 'ETIMEDOUT' ? `test timed out after ${perTestTimeoutMs} ms` : result.error.message);
    if (result.signal) throw new Error(`test terminated by signal ${result.signal}`);
    if (result.status !== 0) throw new Error(output.trim() || `worker exited ${result.status}`);
    if (!marker) throw new Error(`worker did not emit CASE_RESULT\n${output.trim()}`);
    const parsed = JSON.parse(marker);
    results.push(parsed);
    console.log(`${parsed.status}: ${id} — ${parsed.title}`);
    if (parsed.status === 'KNOWN_GAP') console.log(`  GAP: ${parsed.gap}`);
  } catch (error) {
    failures.push({ id, error: error?.message ?? String(error) });
    console.error(`FAIL: ${id}`);
    console.error(String(error?.message ?? error).split('\n').map((line) => `  ${line}`).join('\n'));
  } finally {
    rmSync(tempRoot, { recursive: true, force: true });
  }
}

const sourceStatusAfter = gitStatus();
if (sourceStatusAfter !== sourceStatusBefore) {
  failures.push({ id: 'source-worktree-pollution', error: 'source git status changed while tests ran' });
  console.error('FAIL: source-worktree-pollution');
  console.error('  The governance harness changed the real repository or concurrent edits occurred during the run.');
} else {
  console.log('SOURCE_WORKTREE_UNCHANGED');
}

const knownGaps = results.filter((item) => item.status === 'KNOWN_GAP');
console.log(`GOVERNANCE_TEST_SUMMARY: total=${ids.length} passed=${results.length - knownGaps.length} known_gaps=${knownGaps.length} failed=${failures.length}`);
if (knownGaps.length) {
  console.log('KNOWN_GAPS');
  for (const item of knownGaps) console.log(`- ${item.id}: ${item.gap}`);
}
if (failures.length) {
  console.error('GOVERNANCE_TEST_FAILURES');
  for (const failure of failures) console.error(`- ${failure.id}: ${failure.error.split('\n')[0]}`);
  process.exit(1);
}
console.log(knownGaps.length
  ? 'GOVERNANCE_TEST_PASS: all enforced controls rejected their targeted attacks; known gaps remain explicit and pinned.'
  : 'GOVERNANCE_TEST_PASS: all allowlisted attacks were rejected; no known gaps remain in this suite.');
