#!/usr/bin/env node
import assert from 'node:assert/strict';
import { chmodSync, cpSync, lstatSync, mkdtempSync, mkdirSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const scriptPath = fileURLToPath(import.meta.url);
const libraryRoot = resolve(dirname(scriptPath), '..');
const sentinelPath = 'WORKSPACE-TEMPLATE/TEMPLATES/company-profile.md';
const sentinel = '<!-- fail-closed-write-sentinel -->';

function makeTemporaryCopyOwnerWritable(path) {
  const stat = lstatSync(path);
  if (stat.isSymbolicLink()) return;
  if (stat.isDirectory()) {
    chmodSync(path, stat.mode | 0o700);
    for (const entry of readdirSync(path)) makeTemporaryCopyOwnerWritable(join(path, entry));
    return;
  }
  if (stat.isFile()) chmodSync(path, stat.mode | 0o600);
}

function run(root, ...args) {
  return spawnSync(process.execPath, [join(root, 'scripts/sync-workspace-template.mjs'), ...args], {
    cwd: root,
    encoding: 'utf8',
    timeout: 5000,
    killSignal: 'SIGKILL',
  });
}

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'website-content-ops-sync-'));
  for (const path of ['scripts/sync-workspace-template.mjs', 'TEMPLATES', 'PLAYBOOKS', 'WORKSPACE-TEMPLATE/TEMPLATES', 'WORKSPACE-TEMPLATE/30_tasks']) {
    const target = join(root, path);
    cpSync(join(libraryRoot, path), target, { recursive: true });
    makeTemporaryCopyOwnerWritable(target);
  }
  const syncResult = run(root);
  assert.equal(syncResult.error, undefined, syncResult.error?.message);
  assert.equal(syncResult.status, 0, `${syncResult.stdout}\n${syncResult.stderr}`);
  assert.match(syncResult.stdout, /WORKSPACE_TEMPLATE_SYNCED: \d+ files/);
  return root;
}

function makeFifo(path) {
  const result = spawnSync('mkfifo', [path], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
}

function assertFailsClosedInBothModes(root, expectedPatterns) {
  const protectedTarget = join(root, sentinelPath);
  writeFileSync(protectedTarget, `${readFileSync(protectedTarget, 'utf8')}\n${sentinel}\n`);
  for (const args of [['--check'], []]) {
    const result = run(root, ...args);
    assert.equal(result.error, undefined, `sync process timed out or failed to launch: ${result.error?.message}`);
    assert.notEqual(result.status, 0, `${result.stdout}\n${result.stderr}`);
    const output = `${result.stdout}\n${result.stderr}`;
    for (const pattern of expectedPatterns) assert.match(output, pattern);
    assert.match(readFileSync(protectedTarget, 'utf8'), new RegExp(sentinel));
  }
}

test('freshly generated projections pass byte and metadata verification', () => {
  const root = fixture();
  try {
    const result = run(root, '--check');
    assert.equal(result.error, undefined, result.error?.message);
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(result.stdout, /\d+ generated files are current with verified metadata/);
    const stageProjection = readFileSync(join(root, 'WORKSPACE-TEMPLATE/30_tasks/b2b-article-stage-patterns.runtime.md'), 'utf8');
    assert.match(stageProjection, /generated_from: "\.\.\/\.\.\/PLAYBOOKS\/id-0004-b2b-article-stage-patterns\.md"/);
    const taskIndex = readFileSync(join(root, 'WORKSPACE-TEMPLATE/30_tasks/index.md'), 'utf8');
    assert.match(taskIndex, /\[B2B Article Stage Patterns\]\(b2b-article-stage-patterns\.runtime\.md\)/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});


test('workspace article template CTA skeleton cannot drift from the canonical template', () => {
  const root = fixture();
  try {
    const projection = join(root, 'WORKSPACE-TEMPLATE/TEMPLATES/article-draft.md');
    const current = readFileSync(projection, 'utf8');
    assert.match(current, /Trigger: \[state the exact condition that makes the next action appropriate\]/);
    writeFileSync(projection, current.replace(
      'Expected output: [state the observable buyer-facing return]',
      'Expected result: [state a vague response]',
    ));
    const result = run(root, '--check');
    assert.equal(result.error, undefined, result.error?.message);
    assert.notEqual(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(`${result.stdout}\n${result.stderr}`, /stale or missing runtime template: WORKSPACE-TEMPLATE\/TEMPLATES\/article-draft\.md/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('playbook transform rewrites only the related front-matter route and preserves body literals', () => {
  const root = fixture();
  try {
    const sourcePath = join(root, 'PLAYBOOKS/id-0004-b2b-article-stage-patterns.md');
    writeFileSync(sourcePath, `${readFileSync(sourcePath, 'utf8')}
Literal body example: "README.md" must remain unchanged.
`);
    const sync = run(root);
    assert.equal(sync.error, undefined, sync.error?.message);
    assert.equal(sync.status, 0, `${sync.stdout}
${sync.stderr}`);
    const projected = readFileSync(join(root, 'WORKSPACE-TEMPLATE/30_tasks/b2b-article-stage-patterns.runtime.md'), 'utf8');
    assert.match(projected, /^related: \["index\.md",/m);
    assert.match(projected, /Literal body example: "README\.md" must remain unchanged\./);
    assert.doesNotMatch(projected, /Literal body example: "index\.md"/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('TEMPLATES rejects every unlisted name and node kind before check or write reads it', () => {
  const root = fixture();
  try {
    const directory = join(root, 'WORKSPACE-TEMPLATE/TEMPLATES');
    writeFileSync(join(directory, 'index.md'), '# forbidden second index\n');
    writeFileSync(join(directory, 'shadow.md'), '# second truth source\n');
    writeFileSync(join(directory, 'shadow.txt'), 'wrong extension\n');
    mkdirSync(join(directory, 'shadow-dir'));
    symlinkSync('../../TEMPLATES/article-brief.md', join(directory, 'shadow-link.md'));
    makeFifo(join(directory, 'shadow.pipe'));
    assertFailsClosedInBothModes(root, [
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/TEMPLATES\/index\.md/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/TEMPLATES\/shadow\.md/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/TEMPLATES\/shadow\.txt/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/TEMPLATES\/shadow-dir/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/TEMPLATES\/shadow-link\.md/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/TEMPLATES\/shadow\.pipe/,
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('30_tasks rejects every unlisted file, extension, directory, symlink, and FIFO in both modes', () => {
  const root = fixture();
  try {
    const directory = join(root, 'WORKSPACE-TEMPLATE/30_tasks');
    writeFileSync(join(directory, 'shadow.md'), '# forbidden task\n');
    writeFileSync(join(directory, 'shadow.txt'), 'wrong extension\n');
    mkdirSync(join(directory, 'shadow-dir'));
    symlinkSync('../../PLAYBOOKS/id-0001-b2b-seo-article-standard.md', join(directory, 'shadow-link.runtime.md'));
    makeFifo(join(directory, 'shadow.pipe'));
    assertFailsClosedInBothModes(root, [
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/30_tasks\/shadow\.md/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/30_tasks\/shadow\.txt/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/30_tasks\/shadow-dir/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/30_tasks\/shadow-link\.runtime\.md/,
      /unexpected generated projection entry: WORKSPACE-TEMPLATE\/30_tasks\/shadow\.pipe/,
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('allowlisted projection names still reject symlinks and FIFOs before read', () => {
  const root = fixture();
  try {
    const linkedTarget = join(root, 'WORKSPACE-TEMPLATE/TEMPLATES/article-draft.md');
    rmSync(linkedTarget);
    symlinkSync('../../TEMPLATES/article-draft.md', linkedTarget);

    const fifoTarget = join(root, 'WORKSPACE-TEMPLATE/30_tasks/b2b-seo-article-standard.runtime.md');
    rmSync(fifoTarget);
    makeFifo(fifoTarget);

    assertFailsClosedInBothModes(root, [
      /non-regular generated projection entry: WORKSPACE-TEMPLATE\/TEMPLATES\/article-draft\.md/,
      /non-regular generated projection entry: WORKSPACE-TEMPLATE\/30_tasks\/b2b-seo-article-standard\.runtime\.md/,
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('missing canonical 30_tasks index blocks both modes', () => {
  const root = fixture();
  try {
    rmSync(join(root, 'WORKSPACE-TEMPLATE/30_tasks/index.md'));
    assertFailsClosedInBothModes(root, [
      /missing canonical runtime task index: WORKSPACE-TEMPLATE\/30_tasks\/index\.md/,
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('non-regular canonical 30_tasks index blocks both modes', () => {
  const root = fixture();
  try {
    const indexPath = join(root, 'WORKSPACE-TEMPLATE/30_tasks/index.md');
    rmSync(indexPath);
    mkdirSync(indexPath);
    assertFailsClosedInBothModes(root, [
      /non-regular generated projection entry: WORKSPACE-TEMPLATE\/30_tasks\/index\.md/,
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('generated metadata tampering fails even when the file remains Markdown', () => {
  const root = fixture();
  try {
    const readme = join(root, 'WORKSPACE-TEMPLATE/TEMPLATES/README.md');
    writeFileSync(readme, readFileSync(readme, 'utf8').replace(
      'generated_by: "scripts/sync-workspace-template.mjs"',
      'generated_by: "manual-second-source"',
    ));
    const result = run(root, '--check');
    assert.equal(result.error, undefined, result.error?.message);
    assert.notEqual(result.status, 0);
    assert.match(`${result.stdout}\n${result.stderr}`, /stale or missing runtime template|invalid generated_by/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

function validatorFixture() {
  const root = mkdtempSync(join(tmpdir(), 'website-content-ops-validator-'));
  const subLibrariesRoot = join(root, 'sub-libraries');
  const scopeRoot = join(subLibrariesRoot, 'website-content-ops');
  mkdirSync(subLibrariesRoot, { recursive: true });
  cpSync(libraryRoot, scopeRoot, {
    recursive: true,
    filter(source) {
      const parts = relative(libraryRoot, source).split(sep);
      return !parts.some((part) => ['.git', 'dist', 'node_modules'].includes(part));
    },
  });
  makeTemporaryCopyOwnerWritable(scopeRoot);
  cpSync(resolve(libraryRoot, '../README.md'), join(subLibrariesRoot, 'README.md'));
  cpSync(resolve(libraryRoot, '../registry.json'), join(subLibrariesRoot, 'registry.json'));
  return { root, scopeRoot };
}

test('validate-sub-library rejects a projection FIFO without blocking', {
  skip: Boolean(process.env.WCO_SKIP_VALIDATOR_FIFO_TEST),
}, () => {
  const { root, scopeRoot } = validatorFixture();
  try {
    makeFifo(join(scopeRoot, 'WORKSPACE-TEMPLATE/TEMPLATES/shadow.md'));
    const result = spawnSync(process.execPath, [join(scopeRoot, 'scripts/validate-sub-library.mjs')], {
      cwd: scopeRoot,
      encoding: 'utf8',
      timeout: 30000,
      killSignal: 'SIGKILL',
      env: { ...process.env, WCO_SKIP_VALIDATOR_FIFO_TEST: '1' },
    });
    assert.equal(result.error, undefined, `validator timed out or failed to launch: ${result.error?.message}`);
    assert.notEqual(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(`${result.stdout}\n${result.stderr}`, /unexpected generated projection entry: WORKSPACE-TEMPLATE\/TEMPLATES\/shadow\.md/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
