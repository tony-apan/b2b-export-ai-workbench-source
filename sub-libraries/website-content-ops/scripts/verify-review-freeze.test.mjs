import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  chmodSync,
  copyFileSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const TEST_DIR = dirname(fileURLToPath(import.meta.url));
const BUILDER_SOURCE = join(TEST_DIR, 'build-review-freeze.mjs');
const VERIFIER_SOURCE = join(TEST_DIR, 'verify-review-freeze.mjs');

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function write(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function makeWritable(path) {
  let stat;
  try {
    stat = lstatSync(path);
  } catch {
    return;
  }
  if (stat.isSymbolicLink() || stat.isFile()) {
    if (!stat.isSymbolicLink()) chmodSync(path, 0o644);
    return;
  }
  if (stat.isDirectory()) {
    chmodSync(path, 0o755);
    for (const entry of readdirSync(path)) makeWritable(join(path, entry));
  }
}

function makeFixture(t) {
  const base = mkdtempSync(join(tmpdir(), 'wco-review-verify-'));
  const repo = join(base, 'repo');
  const scope = join(repo, 'sub-libraries', 'website-content-ops');
  const scripts = join(scope, 'scripts');
  const controls = join(base, 'controls');
  const outputs = join(base, 'outputs');
  mkdirSync(scripts, { recursive: true });
  mkdirSync(controls, { recursive: true });
  mkdirSync(outputs, { recursive: true });
  copyFileSync(BUILDER_SOURCE, join(scripts, 'build-review-freeze.mjs'));
  copyFileSync(VERIFIER_SOURCE, join(scripts, 'verify-review-freeze.mjs'));
  write(join(scripts, 'root.mjs'), `import './helper.mjs';\nexport const root = true;\n`);
  write(join(scripts, 'helper.mjs'), `export const helper = true;\n`);
  write(join(scope, 'README.md'), `synthetic review resource\n`);
  write(join(scope, 'ADAPTERS', 'README.md'), `uppercase lexical-order fixture\n`);
  write(join(scope, 'ADAPTERS', '_template.md'), `underscore lexical-order fixture\n`);
  write(join(scope, 'ADAPTERS', 'cms', 'allincms-overview.md'), `path-prefix ordering fixture\n`);
  write(join(scope, 'ADAPTERS', 'cms', 'allincms', 'README.md'), `directory-prefix ordering fixture\n`);
  write(join(controls, 'roots.txt'), [
    'sub-libraries/website-content-ops/scripts/root.mjs',
    'sub-libraries/website-content-ops/scripts/build-review-freeze.mjs',
    'sub-libraries/website-content-ops/scripts/verify-review-freeze.mjs',
    '',
  ].join('\n'));
  write(join(controls, 'resources.txt'), [
    'sub-libraries/website-content-ops/README.md',
    'sub-libraries/website-content-ops/ADAPTERS/README.md',
    'sub-libraries/website-content-ops/ADAPTERS/_template.md',
    'sub-libraries/website-content-ops/ADAPTERS/cms/allincms-overview.md',
    'sub-libraries/website-content-ops/ADAPTERS/cms/allincms/README.md',
    '',
  ].join('\n'));

  const fixture = {
    base,
    repo,
    scope,
    scripts,
    controls,
    outputs,
    manifest: join(outputs, 'manifest.json'),
    freezeRoot: join(outputs, 'freeze-root'),
    fileList: join(outputs, 'files.txt'),
    shaFile: join(outputs, 'manifest.sha256'),
    rootsFile: join(controls, 'roots.txt'),
    resourcesFile: join(controls, 'resources.txt'),
    builder: join(scripts, 'build-review-freeze.mjs'),
    verifier: join(scripts, 'verify-review-freeze.mjs'),
  };
  t.after(() => {
    makeWritable(base);
    rmSync(base, { recursive: true, force: true });
  });
  return fixture;
}

function build(fixture) {
  const result = spawnSync(process.execPath, [
    fixture.builder,
    '--freeze-id', 'WCO-VERIFY-TEST-F1',
    '--generated-at', '2026-08-02T00:00:00.000Z',
    '--manifest', fixture.manifest,
    '--freeze-root', fixture.freezeRoot,
    '--file-list', fixture.fileList,
    '--sha-file', fixture.shaFile,
    '--roots-file', fixture.rootsFile,
    '--resources-file', fixture.resourcesFile,
  ], { cwd: fixture.repo, encoding: 'utf8', timeout: 20_000, maxBuffer: 4 * 1024 * 1024 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  return sha256(readFileSync(fixture.manifest));
}

function verify(fixture, expectedSha, extra = []) {
  return spawnSync(process.execPath, [
    fixture.verifier,
    '--freeze-root', fixture.freezeRoot,
    '--manifest', fixture.manifest,
    '--file-list', fixture.fileList,
    '--roots-file', fixture.rootsFile,
    '--resources-file', fixture.resourcesFile,
    '--expected-manifest-sha256', expectedSha,
    '--sha-file', fixture.shaFile,
    ...extra,
  ], { cwd: fixture.repo, encoding: 'utf8', timeout: 20_000, maxBuffer: 4 * 1024 * 1024 });
}

function assertBlocked(result, pattern) {
  assert.notEqual(result.status, 0, result.stdout);
  assert.doesNotMatch(result.stdout, /REVIEW_FREEZE_VERIFY_PASS/);
  assert.match(result.stderr, pattern);
}

function rewriteReadOnlyFile(path, content) {
  chmodSync(path, 0o644);
  writeFileSync(path, content);
  chmodSync(path, 0o444);
}

function openFreezeRootForMutation(fixture, mutate) {
  chmodSync(fixture.freezeRoot, 0o755);
  try {
    mutate();
  } finally {
    chmodSync(fixture.freezeRoot, 0o555);
  }
}

test('valid freeze verifies exact bytes and becomes locally read-only', (t) => {
  const fixture = makeFixture(t);
  const digest = build(fixture);
  const result = verify(fixture, digest);
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stdout, /REVIEW_FREEZE_VERIFY_PASS/);
  assert.match(result.stdout, /generated_at=2026-08-02T00:00:00.000Z/);
  assert.match(result.stdout, /trust_scope=local-review-immutability-only/);
  assert.equal(lstatSync(fixture.freezeRoot).mode & 0o777, 0o555);
  assert.equal(lstatSync(fixture.manifest).mode & 0o777, 0o444);
  assert.equal(lstatSync(fixture.fileList).mode & 0o777, 0o444);
  assert.equal(lstatSync(fixture.shaFile).mode & 0o777, 0o444);
  assert.equal(lstatSync(fixture.rootsFile).mode & 0o777, 0o444);
  assert.equal(lstatSync(fixture.resourcesFile).mode & 0o777, 0o444);
  const frozenRoot = join(fixture.freezeRoot, 'sub-libraries', 'website-content-ops', 'scripts', 'root.mjs');
  assert.equal(lstatSync(frozenRoot).mode & 0o777, 0o444);
  assert.throws(() => writeFileSync(frozenRoot, 'tamper\n'), /EACCES|EPERM/);
  const second = verify(fixture, digest);
  assert.equal(second.status, 0, `${second.stdout}\n${second.stderr}`);
});

test('controller-provided wrong manifest SHA blocks', (t) => {
  const fixture = makeFixture(t);
  build(fixture);
  assertBlocked(verify(fixture, '0'.repeat(64)), /controller manifest SHA-256 mismatch/);
});

test('manifest byte mutation blocks before schema can self-authorize it', (t) => {
  const fixture = makeFixture(t);
  const digest = build(fixture);
  rewriteReadOnlyFile(fixture.manifest, `${readFileSync(fixture.manifest, 'utf8')} `);
  assertBlocked(verify(fixture, digest), /controller manifest SHA-256 mismatch/);
});

test('frozen file byte mutation blocks', (t) => {
  const fixture = makeFixture(t);
  const digest = build(fixture);
  const target = join(fixture.freezeRoot, 'sub-libraries', 'website-content-ops', 'scripts', 'root.mjs');
  rewriteReadOnlyFile(target, 'tampered\n');
  assertBlocked(verify(fixture, digest), /byte-count mismatch|SHA-256 mismatch/);
});

test('file list removal and reordering both block exact order and set', (t) => {
  for (const mutation of ['remove', 'reorder']) {
    const fixture = makeFixture(t);
    const digest = build(fixture);
    const paths = readFileSync(fixture.fileList, 'utf8').trim().split('\n');
    const mutated = mutation === 'remove' ? paths.slice(1) : [paths[1], paths[0], ...paths.slice(2)];
    rewriteReadOnlyFile(fixture.fileList, `${mutated.join('\n')}\n`);
    assertBlocked(verify(fixture, digest), /file list (?:byte-count|SHA-256 mismatch|must exactly match)/);
  }
});

test('extra freeze file blocks exact file set', (t) => {
  const fixture = makeFixture(t);
  const digest = build(fixture);
  openFreezeRootForMutation(fixture, () => {
    write(join(fixture.freezeRoot, 'unexpected.txt'), 'unexpected\n');
    chmodSync(join(fixture.freezeRoot, 'unexpected.txt'), 0o444);
  });
  assertBlocked(verify(fixture, digest), /exact file set mismatch/);
});

test('symlink and non-regular FIFO in freeze root both block', (t) => {
  {
    const fixture = makeFixture(t);
    const digest = build(fixture);
    openFreezeRootForMutation(fixture, () => symlinkSync('sub-libraries', join(fixture.freezeRoot, 'alias')));
    assertBlocked(verify(fixture, digest), /contains symlink/);
  }
  {
    const fixture = makeFixture(t);
    const digest = build(fixture);
    const fifo = join(fixture.freezeRoot, 'named-pipe');
    chmodSync(fixture.freezeRoot, 0o755);
    const created = spawnSync('mkfifo', [fifo], { encoding: 'utf8' });
    assert.equal(created.status, 0, created.stderr);
    chmodSync(fixture.freezeRoot, 0o555);
    assertBlocked(verify(fixture, digest), /contains non-regular entry/);
  }
});

test('synchronized manifest and sidecar rewrite cannot bypass unchanged controller SHA', (t) => {
  const fixture = makeFixture(t);
  const controllerDigest = build(fixture);
  const manifest = JSON.parse(readFileSync(fixture.manifest, 'utf8'));
  manifest.freeze_id = 'ATTACKER-REWRITE';
  const rewritten = `${JSON.stringify(manifest, null, 2)}\n`;
  rewriteReadOnlyFile(fixture.manifest, rewritten);
  rewriteReadOnlyFile(fixture.shaFile, `${sha256(Buffer.from(rewritten))}  ${basename(fixture.manifest)}\n`);
  assertBlocked(verify(fixture, controllerDigest), /controller manifest SHA-256 mismatch/);
});

test('sidecar mismatch blocks even when controller manifest SHA is correct', (t) => {
  const fixture = makeFixture(t);
  const digest = build(fixture);
  rewriteReadOnlyFile(fixture.shaFile, `${'f'.repeat(64)}  ${basename(fixture.manifest)}\n`);
  assertBlocked(verify(fixture, digest), /SHA sidecar does not exactly match/);
});

test('duplicate manifest JSON keys block before JSON.parse can collapse them', (t) => {
  const fixture = makeFixture(t);
  build(fixture);
  const original = readFileSync(fixture.manifest, 'utf8');
  const duplicated = original.replace('  "schema_version": 2,\n', '  "schema_version": 2,\n  "schema_version": 2,\n');
  assert.notEqual(duplicated, original);
  const digest = sha256(Buffer.from(duplicated));
  rewriteReadOnlyFile(fixture.manifest, duplicated);
  rewriteReadOnlyFile(fixture.shaFile, `${digest}  ${basename(fixture.manifest)}\n`);
  assertBlocked(verify(fixture, digest), /duplicate JSON key.*schema_version/);
});

test('pre-verification 0644 mode drift blocks and verifier never repairs it', async (t) => {
  const cases = [
    ['manifest', (fixture) => fixture.manifest, /manifest read-only mode mismatch/],
    ['frozen file', (fixture) => join(fixture.freezeRoot, 'sub-libraries', 'website-content-ops', 'scripts', 'root.mjs'), /freeze file .*read-only mode mismatch/],
  ];
  for (const [name, targetFor, branch] of cases) {
    await t.test(name, (t) => {
      const fixture = makeFixture(t);
      const digest = build(fixture);
      const target = targetFor(fixture);
      chmodSync(target, 0o644);
      assertBlocked(verify(fixture, digest), branch);
      assert.equal(lstatSync(target).mode & 0o777, 0o644, 'verifier must not chmod-repair drift');
    });
  }
});

test('roots and resources auxiliary evidence blocks byte tampering and mode drift', async (t) => {
  await t.test('roots bytes', (t) => {
    const fixture = makeFixture(t);
    const digest = build(fixture);
    rewriteReadOnlyFile(fixture.rootsFile, `${readFileSync(fixture.rootsFile, 'utf8')}# tampered\n`);
    assertBlocked(verify(fixture, digest), /roots file byte-count mismatch|roots file SHA-256 mismatch/);
  });
  await t.test('resources bytes', (t) => {
    const fixture = makeFixture(t);
    const digest = build(fixture);
    rewriteReadOnlyFile(fixture.resourcesFile, `${readFileSync(fixture.resourcesFile, 'utf8')}# tampered\n`);
    assertBlocked(verify(fixture, digest), /resources file byte-count mismatch|resources file SHA-256 mismatch/);
  });
  await t.test('resources mode', (t) => {
    const fixture = makeFixture(t);
    const digest = build(fixture);
    chmodSync(fixture.resourcesFile, 0o644);
    assertBlocked(verify(fixture, digest), /resources file read-only mode mismatch/);
    assert.equal(lstatSync(fixture.resourcesFile).mode & 0o777, 0o644);
  });
});

test('generated_at is controller-bound in manifest bytes and must remain canonical UTC', (t) => {
  const fixture = makeFixture(t);
  build(fixture);
  const manifest = JSON.parse(readFileSync(fixture.manifest, 'utf8'));
  manifest.generated_at = '2026-08-02T08:00:00+08:00';
  const rewritten = `${JSON.stringify(manifest, null, 2)}\n`;
  const digest = sha256(Buffer.from(rewritten));
  rewriteReadOnlyFile(fixture.manifest, rewritten);
  rewriteReadOnlyFile(fixture.shaFile, `${digest}  ${basename(fixture.manifest)}\n`);
  assertBlocked(verify(fixture, digest), /manifest.generated_at must be a controller-supplied canonical UTC timestamp/);
});

test('review-freeze runbook binds all verifier controls without machine-local literal paths', () => {
  const readme = readFileSync(join(TEST_DIR, 'README.md'), 'utf8');
  const verifierInvocation = readme.match(/node scripts\/verify-review-freeze\.mjs[\s\S]{0,1000}/)?.[0] || '';
  assert.match(verifierInvocation, /--roots-file\s+"\$roots_file"/);
  assert.match(verifierInvocation, /--resources-file\s+"\$resources_file"/);
  assert.doesNotMatch(readme, /(?:^|[\s`"'])\/tmp\//m);
  assert.match(readme, /验证[^\n]{0,80}(?:已经|已是)[^\n]{0,40}只读|verif(?:y|ies)[^\n]{0,80}read-only/i);
  assert.doesNotMatch(readme, /verifier[^\n]{0,40}(?:设置|设为)[^\n]{0,40}只读/i);
});
