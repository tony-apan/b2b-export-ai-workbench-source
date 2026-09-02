import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { chmodSync, cpSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { scanPublishableContent } from './content-safety.mjs';
import { classifyGovernanceFixtureRoot, shouldUseGovernanceFixtureFastMode } from './governance-fixture-fast-mode.mjs';
import { matchesManifestPattern } from './manifest-policy.mjs';
import { parseMarkdownFrontMatter, requireStringArrayField } from './front-matter.mjs';

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const TRUSTED_RUNTIME_TEST_PROFILE = Object.freeze([
  Object.freeze({ file: 'upload-media-browser.test.mjs', tests: 47 }),
  Object.freeze({ file: 'article-image-binding.test.mjs', tests: 52 }),
  Object.freeze({ file: 'article-content-formats.test.mjs', tests: 13 }),
  Object.freeze({ file: 'article-operations.test.mjs', tests: 48 }),
]);
const TRUSTED_RUNTIME_TEST_PLAN = TRUSTED_RUNTIME_TEST_PROFILE.map(({ file }) => file);
const TRUSTED_RUNTIME_TEST_COUNT = TRUSTED_RUNTIME_TEST_PROFILE.reduce((total, { tests }) => total + tests, 0);
const GOVERNANCE_COMMAND_TIMEOUT_MS = 120_000;
const FIXTURE_SETUP_TIMEOUT_MS = 120_000;
const GOVERNANCE_TEST_PLAN = Object.freeze([
  'active status projections fail closed when they drift from MANIFEST.md',
  'blocked current candidates reject affirmative release-state claims in public entry and release documents',
  'release-state prose permits explicit denial, historical artifacts, and future prerequisites',
  'a root basename glob never authorizes nested Markdown',
  'an unregistered clients/acme.md blocks validation and the builder',
  'an unregistered private-notes directory fails closed',
  'an unregistered private directory is not silently auto-ignored',
  'supplementary content scanning detects cross-platform paths and common PII',
  'artifact validation rejects cross-platform paths and PII even after integrity metadata is recomputed',
  'a semantically empty runtime contract blocks validation and build',
  'the declared agency runtime dependency and private runtime boundaries fail closed',
  'current candidate identity is separate from the immutable historical release and prepare fails closed on unassigned or colliding versions',
  'package-level license clearance cannot override pending source publication clearance during prepare',
  'source-card identity, required fields, legal values, rename, and relocation attacks fail closed during prepare',
  'source inventory binds protected IDs, card digests, and derived-page backlinks and cannot be silently shrunk',
  'the sub-library builder binds selected files to commit provenance and rejects ignored, untracked, and modified inputs',
  'governance fixtures remain reproducible from immutable 0444/0555 freeze sources without masking setup failures',
  'the formal runtime profile matches the adapter contract and exact 160-test plan',
  'pending source clearance independently blocks approval and artifact qualification even when package license is cleared',
  'frozen source-card identity, field, value, rename, and relocation attacks block approval and artifact qualification after self-consistent rebinding',
  'post-build frozen MANIFEST identity drift blocks approval and artifact qualification after self-consistent sidecar recomputation',
  'formal qualification binds workflow tag identity and canonical approval data without claiming human identity',
]);
const listGovernancePlanOnly = process.argv.includes('--list');
const registeredGovernanceTests = [];
function governanceTest(name, ...args) {
  registeredGovernanceTests.push(name);
  if (!listGovernancePlanOnly) test(name, ...args);
}
const SOURCE_CARD_FILENAME_PATTERN = /^SRC-[A-Za-z0-9][A-Za-z0-9._-]*\.md$/;
const SOURCE_INVENTORY_PATH = 'REFERENCES/SOURCE-INVENTORY.json';

function sourceCardPaths(root) {
  return readdirSync(join(root, 'REFERENCES'), { withFileTypes: true })
    .filter((entry) => entry.isFile() && SOURCE_CARD_FILENAME_PATTERN.test(entry.name))
    .map((entry) => `REFERENCES/${entry.name}`)
    .sort();
}

function setFrontMatterFields(content, fields) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n/);
  assert.ok(match, 'source card fixture must have Markdown front matter');
  const fieldNames = new Set(Object.keys(fields));
  const lines = match[1]
    .split('\n')
    .filter((line) => !fieldNames.has(line.match(/^([A-Za-z0-9_-]+):/)?.[1]));
  for (const [field, value] of Object.entries(fields)) lines.push(`${field}: ${JSON.stringify(value)}`);
  return `---\n${lines.join('\n')}\n---\n${content.slice(match[0].length)}`;
}

function deleteFrontMatterFields(content, fields) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n/);
  assert.ok(match, 'source card fixture must have Markdown front matter');
  const fieldNames = new Set(fields);
  const lines = match[1]
    .split('\n')
    .filter((line) => !fieldNames.has(line.match(/^([A-Za-z0-9_-]+):/)?.[1]));
  return `---\n${lines.join('\n')}\n---\n${content.slice(match[0].length)}`;
}

function setSourceCardClearance(root, path, approved) {
  const sourcePath = join(root, path);
  const content = readFileSync(sourcePath, 'utf8');
  writeFileSync(sourcePath, setFrontMatterFields(content, {
    type: 'source-note',
    publication_review_status: approved ? 'approved' : 'pending',
    publication_status: approved ? 'PASS' : 'BLOCK',
    license_status: approved ? 'cleared' : 'pending',
  }));
}

function setAllSourceCardClearance(root, approved) {
  const paths = sourceCardPaths(root);
  assert.ok(paths.length > 0, 'fixture must contain at least one REFERENCES/SRC-*.md source card');
  for (const path of paths) setSourceCardClearance(root, path, approved);
  refreshSourceInventoryDigests(root);
  return paths;
}

function refreshSourceInventoryDigests(root) {
  const inventoryPath = join(root, SOURCE_INVENTORY_PATH);
  const inventory = JSON.parse(readFileSync(inventoryPath, 'utf8'));
  for (const entry of inventory.entries ?? []) {
    const cardPath = join(root, entry.card_path);
    const cardFront = parseMarkdownFrontMatter(readFileSync(cardPath, 'utf8'), { source: entry.card_path }).attributes;
    entry.card_sha256 = createHash('sha256').update(readFileSync(cardPath)).digest('hex');
    for (const field of ['publication_review_status', 'publication_status', 'license_status']) {
      entry[field] = cardFront[field];
    }
  }
  writeFileSync(inventoryPath, `${JSON.stringify(inventory, null, 2)}\n`);
}

function copySourceTree(fromRoot, toRoot) {
  cpSync(fromRoot, toRoot, {
    recursive: true,
    filter(path) {
      const rel = relative(fromRoot, path);
      if (!rel) return true;
      return !rel.split(sep).some((part) => ['.git', '.DS_Store', 'dist', 'node_modules'].includes(part));
    },
  });
}

function makeTreeOwnerWritable(root) {
  let stats;
  try {
    stats = lstatSync(root);
  } catch (error) {
    if (error?.code === 'ENOENT') return;
    throw error;
  }
  if (stats.isSymbolicLink()) return;
  chmodSync(root, stats.mode | (stats.isDirectory() ? 0o700 : 0o600));
  if (!stats.isDirectory()) return;
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.isSymbolicLink()) continue;
    makeTreeOwnerWritable(join(root, entry.name));
  }
}

function makeTreeImmutable(root) {
  const stats = lstatSync(root);
  if (stats.isSymbolicLink()) return;
  if (stats.isDirectory()) {
    for (const entry of readdirSync(root, { withFileTypes: true })) {
      if (entry.isSymbolicLink()) continue;
      makeTreeImmutable(join(root, entry.name));
    }
    chmodSync(root, 0o555);
    return;
  }
  chmodSync(root, 0o444);
}

function cleanupCopy(copyRoot, { suppressErrors = false } = {}) {
  const tempRoot = dirname(copyRoot);
  let permissionError;
  try {
    makeTreeOwnerWritable(tempRoot);
  } catch (error) {
    permissionError = error;
  }
  try {
    rmSync(tempRoot, { recursive: true, force: true });
  } catch (removeError) {
    if (!suppressErrors) {
      throw new AggregateError(
        permissionError ? [permissionError, removeError] : [removeError],
        `failed to clean governance fixture ${tempRoot}`,
      );
    }
  }
}

function rethrowSetupErrorAfterCleanup(setupError, cleanup) {
  try {
    cleanup({ suppressErrors: true });
  } catch {
    // The setup error is the causal failure; cleanup is best-effort on this path.
  }
  throw setupError;
}

function runFixtureCommand(command, args, options = {}) {
  return execFileSync(command, args, {
    ...options,
    timeout: options.timeout ?? FIXTURE_SETUP_TIMEOUT_MS,
  });
}
function makeCopy(t) {
  const tempRoot = mkdtempSync(join(tmpdir(), 'wco-governance-'));
  const copyRoot = join(tempRoot, 'website-content-ops');
  let setupFailed = false;
  const cleanup = (options = {}) => cleanupCopy(copyRoot, {
    suppressErrors: options.suppressErrors ?? setupFailed,
  });
  t.after(cleanup);
  try {
    copySourceTree(sourceRoot, copyRoot);
    makeTreeOwnerWritable(copyRoot);
    setAllSourceCardClearance(copyRoot, false);
    runFixtureCommand(process.execPath, [join(copyRoot, 'scripts/sync-workspace-template.mjs')], { cwd: copyRoot, stdio: 'ignore' });
    runFixtureCommand('git', ['init', '-q'], { cwd: copyRoot });
    runFixtureCommand('git', ['config', 'user.email', 'reviewer@example.invalid'], { cwd: copyRoot });
    runFixtureCommand('git', ['config', 'user.name', 'Release Governance Test'], { cwd: copyRoot });
    runFixtureCommand('git', ['add', '.'], { cwd: copyRoot });
    runFixtureCommand('git', ['commit', '-qm', 'fixture'], { cwd: copyRoot });
    return copyRoot;
  } catch (error) {
    setupFailed = true;
    return rethrowSetupErrorAfterCleanup(error, cleanup);
  }
}

function setCurrentCandidateIdentity(root, { identity, snapshot, version }) {
  for (const file of ['MANIFEST.md', 'VERSION.md']) {
    const path = join(root, file);
    let content = readFileSync(path, 'utf8');
    content = content
      .replace('current_candidate_identity: "unassigned"', `current_candidate_identity: "${identity}"`)
      .replace('current_candidate_snapshot: "dirty-working-tree"', `current_candidate_snapshot: "${snapshot}"`)
      .replace('current_candidate_version: null', `current_candidate_version: ${version === null ? 'null' : `"${version}"`}`);
    writeFileSync(path, content);
  }
}

const RESEARCH_SOURCE_PATH = 'REFERENCES/SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md';

function setResearchSourceClearance(root, approved) {
  setSourceCardClearance(root, RESEARCH_SOURCE_PATH, approved);
  refreshSourceInventoryDigests(root);
}

function configureFormalCandidateSourceTree(root, { approveSourceCards = false } = {}) {
  const candidateVersion = '0.3.3-preview.1';
  setCurrentCandidateIdentity(root, {
    identity: 'assigned',
    snapshot: 'source-commit',
    version: candidateVersion,
  });
  const manifestPath = join(root, 'MANIFEST.md');
  let manifestText = readFileSync(manifestPath, 'utf8');
  for (const [from, to] of [
    ['release_status: "BLOCK"', 'release_status: "Ready"'],
    ['maturity_status: "validated"', 'maturity_status: "stable"'],
    ['verification_status: "evidence-partial"', 'verification_status: "e2e-pass"'],
    ['license_status: "pending"', 'license_status: "cleared"'],
  ]) {
    assert.ok(manifestText.includes(from), `formal candidate fixture lacks expected state: ${from}`);
    manifestText = manifestText.replace(from, to);
  }
  writeFileSync(manifestPath, manifestText);
  const projectedStatusDocs = ['INSTALL.md', 'LICENSE.md', 'README.md', 'RELEASE.md', 'SKILL.md', 'VERSION.md'];
  for (const file of projectedStatusDocs) {
    const path = join(root, file);
    const content = readFileSync(path, 'utf8');
    assert.match(content, /release_status: "BLOCK"/);
    let projected = content.replace('release_status: "BLOCK"', 'release_status: "Ready"');
    if (/license_status: "pending"/.test(projected)) projected = projected.replace('license_status: "pending"', 'license_status: "cleared"');
    writeFileSync(path, projected);
  }
  const adapterPackagePath = join(root, 'ADAPTERS/cms/allincms/package.json');
  const adapterLockPath = join(root, 'ADAPTERS/cms/allincms/package-lock.json');
  const adapterPackage = JSON.parse(readFileSync(adapterPackagePath, 'utf8'));
  const adapterLock = JSON.parse(readFileSync(adapterLockPath, 'utf8'));
  adapterPackage.license = 'Apache-2.0';
  adapterLock.packages[''].license = 'Apache-2.0';
  writeFileSync(adapterPackagePath, `${JSON.stringify(adapterPackage, null, 2)}\n`);
  writeFileSync(adapterLockPath, `${JSON.stringify(adapterLock, null, 2)}\n`);
  const sourceCards = approveSourceCards ? setAllSourceCardClearance(root, true) : sourceCardPaths(root);
  const sync = runNode(root, 'scripts/sync-workspace-template.mjs');
  assert.equal(sync.status, 0, `${sync.stdout}\n${sync.stderr}`);
  runFixtureCommand('git', ['add', 'MANIFEST.md', ...projectedStatusDocs, 'ADAPTERS/cms/allincms/package.json', 'ADAPTERS/cms/allincms/package-lock.json'], { cwd: root });
  if (approveSourceCards) runFixtureCommand('git', ['add', ...sourceCards, SOURCE_INVENTORY_PATH], { cwd: root });
  runFixtureCommand('git', ['add', 'WORKSPACE-TEMPLATE'], { cwd: root });
  runFixtureCommand('git', ['commit', '-qm', approveSourceCards ? 'prepare formal qualification fixture with source clearance' : 'prepare package-only clearance bypass fixture'], { cwd: root });
  return candidateVersion;
}

function runNode(root, script, args = [], options = {}) {
  return spawnSync(process.execPath, [join(root, script), ...args], {
    cwd: root,
    encoding: 'utf8',
    env: { ...process.env, ...(script === 'scripts/validate-sub-library.mjs' ? { WCO_GOVERNANCE_FIXTURE_FAST: '1' } : {}), ...(options.env ?? {}) },
    timeout: options.timeout ?? GOVERNANCE_COMMAND_TIMEOUT_MS,
    killSignal: 'SIGKILL',
    maxBuffer: 16 * 1024 * 1024,
  });
}

function parseTapCount(output, field, testFile) {
  const matches = [...output.matchAll(new RegExp(`^\\s*# ${field} (\\d+)\\s*$`, 'gm'))];
  assert.equal(matches.length, 1, `${testFile} TAP must report exactly one ${field} summary`);
  return Number(matches[0][1]);
}

function runTrustedRuntimeTestProfile() {
  const adapterRoot = join(sourceRoot, 'ADAPTERS/cms/allincms');
  const { NODE_TEST_CONTEXT: ignoredNodeTestContext, ...runtimeTestEnv } = process.env;
  void ignoredNodeTestContext;
  return TRUSTED_RUNTIME_TEST_PROFILE.map(({ file, tests }) => {
    const result = spawnSync(process.execPath, ['--test', '--test-reporter=tap', file], {
      cwd: adapterRoot,
      encoding: 'utf8',
      env: runtimeTestEnv,
      timeout: GOVERNANCE_COMMAND_TIMEOUT_MS,
      killSignal: 'SIGKILL',
      maxBuffer: 16 * 1024 * 1024,
    });
    assert.equal(result.error, undefined, result.error?.message);
    assert.equal(result.signal, null, `${file} trusted runtime TAP was terminated by ${result.signal}`);
    assert.equal(result.status, 0, `${file} trusted runtime TAP failed\n${result.stdout}\n${result.stderr}`);
    const summary = Object.fromEntries(
      ['tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo']
        .map((field) => [field, parseTapCount(result.stdout, field, file)]),
    );
    assert.deepEqual(summary, {
      tests,
      pass: tests,
      fail: 0,
      cancelled: 0,
      skipped: 0,
      todo: 0,
    }, `${file} trusted runtime TAP count drifted`);
    return summary.tests;
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

governanceTest('active status projections fail closed when they drift from MANIFEST.md', (t) => {
  const root = makeCopy(t);
  const installPath = join(root, 'INSTALL.md');
  const baselineContent = readFileSync(installPath, 'utf8');
  const baseline = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.equal(baseline.status, 0, `${baseline.stdout}\n${baseline.stderr}`);

  const attacks = [
    [
      'projected value drift',
      (content) => content.replace('release_status: "BLOCK"', 'release_status: "Preview"'),
      /INSTALL\.md state drift for release_status: expected "BLOCK" from MANIFEST\.md, got "Preview"/,
    ],
    [
      'projected field removed',
      (content) => content.replace('preview_publication_status: "BLOCK"\n', ''),
      /INSTALL\.md projects preview_publication_status, but the document does not declare it/,
    ],
    [
      'non-manifest source',
      (content) => content.replace('state_source: "MANIFEST.md"', 'state_source: "RELEASE.md"'),
      /INSTALL\.md state_source must resolve to the canonical scope MANIFEST\.md: RELEASE\.md/,
    ],
    [
      'empty projection',
      (content) => content.replace('state_projection: ["release_status", "preview_publication_status"]', 'state_projection: []'),
      /INSTALL\.md state_projection must be a non-empty string array/,
    ],
    [
      'required projection declarations removed together',
      (content) => content
        .replace('state_source: "MANIFEST.md"\n', '')
        .replace('state_projection: ["release_status", "preview_publication_status"]\n', ''),
      /INSTALL\.md required state projection must declare both state_source and state_projection/,
    ],
    [
      'required projection field set narrowed',
      (content) => content.replace('state_projection: ["release_status", "preview_publication_status"]', 'state_projection: ["release_status"]'),
      /INSTALL\.md required state_projection must exactly equal/,
    ],
  ];
  for (const [label, mutate, expected] of attacks) {
    const mutated = mutate(baselineContent);
    assert.notEqual(mutated, baselineContent, `fixture mutation failed: ${label}`);
    writeFileSync(installPath, mutated);
    const validation = runNode(root, 'scripts/validate-sub-library.mjs');
    assert.notEqual(validation.status, 0, label);
    assert.match(`${validation.stdout}\n${validation.stderr}`, expected, label);
    writeFileSync(installPath, baselineContent);
  }

  const ignoredManifestPath = join(root, 'dist', 'stale', 'MANIFEST.md');
  mkdirSync(dirname(ignoredManifestPath), { recursive: true });
  writeFileSync(ignoredManifestPath, readFileSync(join(root, 'MANIFEST.md'), 'utf8'));
  writeFileSync(
    installPath,
    baselineContent.replace('state_source: "MANIFEST.md"', 'state_source: "dist/stale/MANIFEST.md"'),
  );
  const ignoredManifestAttack = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(ignoredManifestAttack.status, 0, 'ignored stale manifest source');
  assert.match(
    `${ignoredManifestAttack.stdout}\n${ignoredManifestAttack.stderr}`,
    /INSTALL\.md state_source must resolve to the canonical scope MANIFEST\.md: dist\/stale\/MANIFEST\.md/,
  );
  rmSync(join(root, 'dist'), { recursive: true, force: true });
  writeFileSync(installPath, baselineContent);

  const build = runNode(root, 'scripts/build-release.mjs');
  assert.equal(build.status, 0, `${build.stdout}\n${build.stderr}`);
  const artifactRoot = join(root, 'dist', 'latest');
  const artifactInstallPath = join(artifactRoot, 'INSTALL.md');
  writeFileSync(
    artifactInstallPath,
    readFileSync(artifactInstallPath, 'utf8').replace('release_status: "BLOCK"', 'release_status: "Preview"'),
  );
  const artifactManifestPath = join(artifactRoot, 'MANIFEST.json');
  const artifactManifest = JSON.parse(readFileSync(artifactManifestPath, 'utf8'));
  const installRecord = artifactManifest.source_provenance.files.find((item) => item.path === 'INSTALL.md');
  assert.ok(installRecord, 'INSTALL.md provenance record missing');
  installRecord.sha256 = sha256(artifactRoot, 'INSTALL.md');
  installRecord.commit_sha256 = installRecord.sha256;
  writeFileSync(artifactManifestPath, `${JSON.stringify(artifactManifest, null, 2)}\n`);
  rewriteArtifactIntegrity(artifactRoot);
  const artifactValidation = runNode(root, 'scripts/validate-artifact.mjs', [artifactRoot]);
  assert.notEqual(artifactValidation.status, 0);
  assert.match(
    `${artifactValidation.stdout}\n${artifactValidation.stderr}`,
    /INSTALL\.md state drift for release_status: expected "BLOCK" from MANIFEST\.md, got "Preview"/,
  );

  rmSync(join(root, 'dist'), { recursive: true, force: true });
  const requiredDocuments = ['README.md', 'INSTALL.md', 'RELEASE.md', 'VERSION.md', 'SKILL.md', 'LICENSE.md'];
  for (const document of requiredDocuments) {
    const path = join(root, document);
    const content = readFileSync(path, 'utf8')
      .replace(/^state_source:.*\n/m, '')
      .replace(/^state_projection:.*\n/m, '');
    writeFileSync(path, content);
  }
  const manifestPath = join(root, 'MANIFEST.md');
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, 'utf8')
      .replace('release_status: "BLOCK"', 'release_status: "Ready"')
      .replace('maturity_status: "validated"', 'maturity_status: "stable"')
      .replace('verification_status: "evidence-partial"', 'verification_status: "e2e-pass"'),
  );
  setCurrentCandidateIdentity(root, {
    identity: 'candidate-v9-projection-test',
    snapshot: 'frozen-test-snapshot',
    version: '0.3.3-preview.1',
  });
  runFixtureCommand('git', ['add', '.'], { cwd: root });
  runFixtureCommand('git', ['commit', '-qm', 'projection opt-out attack'], { cwd: root });
  for (const [script, args] of [
    ['scripts/validate-sub-library.mjs', ['--prepare']],
    ['scripts/build-release.mjs', ['--prepare']],
  ]) {
    const optOut = runNode(root, script, args);
    assert.notEqual(optOut.status, 0, `${script} must reject projection opt-out`);
    assert.match(`${optOut.stdout}\n${optOut.stderr}`, /required state projection must declare both state_source and state_projection/);
  }
});

governanceTest('blocked current candidates reject affirmative release-state claims in public entry and release documents', (t) => {
  const root = makeCopy(t);
  const attacks = [
    ['README.md', 'The current candidate is Stable.', 'Stable'],
    ['INSTALL.md', 'This package is Published.', 'Published'],
    ['RELEASE.md', 'The current release is production-ready.', 'production-ready'],
    ['VERSION.md', 'Current candidate status: approved.', 'approved'],
    ['SKILL.md', 'This build has been deployed.', 'deployed'],
    ['LICENSE.md', 'The current candidate is accepted for live SEO.', 'live SEO accepted'],
    ['START-HERE.md', 'The current candidate is Published.', 'Published'],
  ];

  for (const [document, mutation, claim] of attacks) {
    const path = join(root, document);
    const baseline = readFileSync(path, 'utf8');
    writeFileSync(path, `${baseline}\n\n${mutation}\n`);
    const validation = runNode(root, 'scripts/validate-sub-library.mjs');
    assert.notEqual(validation.status, 0, `${document} must reject ${claim}`);
    const output = `${validation.stdout}\n${validation.stderr}`;
    assert.match(
      output,
      new RegExp(`WCO_RELEASE_STATE_CONTRADICTION: ${document.replace('.', '\\.')} current-candidate claim=${claim.replace('-', '\\-')} conflicts with release_status=BLOCK, current_candidate_identity=unassigned, current_candidate_version=unassigned, license_status=pending, approval_status=pending`),
      `${document} must report the release-state contradiction branch`,
    );
    assert.doesNotMatch(output, /STRUCTURE_PASS/, `${document} contradiction must be fatal`);
    writeFileSync(path, baseline);
  }
});

governanceTest('release-state prose permits explicit denial, historical artifacts, and future prerequisites', (t) => {
  const root = makeCopy(t);
  const baselineValidation = runNode(root, 'scripts/validate-sub-library.mjs');
  const baselineOutput = `${baselineValidation.stdout}\n${baselineValidation.stderr}`;
  assert.doesNotMatch(baselineOutput, /WCO_RELEASE_STATE_CONTRADICTION/);
  const allowedStatements = new Map([
    ['README.md', 'The current candidate is not Stable, Published, production-ready, approved, or deployed; live SEO is not accepted.'],
    ['INSTALL.md', 'This package is not production-ready while license_status remains pending.'],
    ['RELEASE.md', 'The historical artifact v0.3.2-preview.1 was Published and deployed within its limited preview scope.'],
    ['VERSION.md', 'The current candidate may become Stable only after source clearance and independent human approval.'],
    ['SKILL.md', 'Before this build can be approved or deployed, every future prerequisite must pass.'],
    ['LICENSE.md', '当前源码候选不是 Stable，也未发布、未批准、未部署；只有许可闭合后才可进入下一阶段。'],
    ['MANIFEST.md', 'The current candidate can become production-ready only after every future prerequisite is satisfied.'],
    ['CHANGELOG.md', 'Historical artifact v0.3.2-preview.1 was approved and deployed for its prior preview scope.'],
  ]);
  for (const [document, statement] of allowedStatements) {
    const path = join(root, document);
    writeFileSync(path, `${readFileSync(path, 'utf8')}\n\n${statement}\n`);
  }

  const validation = runNode(root, 'scripts/validate-sub-library.mjs');
  const output = `${validation.stdout}\n${validation.stderr}`;
  assert.equal(validation.status, baselineValidation.status, output);
  assert.doesNotMatch(output, /WCO_RELEASE_STATE_CONTRADICTION/);
  assert.equal((output.match(/^FAIL:/gm) ?? []).length, (baselineOutput.match(/^FAIL:/gm) ?? []).length, 'allowed prose must not add a fatal validation branch');
  if (baselineValidation.status === 0) assert.match(validation.stdout, /STRUCTURE_PASS/);
});

governanceTest('a root basename glob never authorizes nested Markdown', () => {
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
governanceTest('an unregistered clients/acme.md blocks validation and the builder', (t) => {
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
  writeFileSync(manifestPath, manifestOriginal.replace('dependency_mode: "declared-external-runtime"', 'dependency_mode: "declared-external-runtime"\ndependency_mode: "self-contained"'));
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
governanceTest('an unregistered private-notes directory fails closed', (t) => {
  const root = makeCopy(t);
  mkdirSync(join(root, 'private-notes'));
  writeFileSync(join(root, 'private-notes', 'customer.md'), validMarkdown('Private notes fixture'));
  const validation = runNode(root, 'scripts/validate-sub-library.mjs');
  assert.notEqual(validation.status, 0);
  assert.match(`${validation.stdout}\n${validation.stderr}`, /source file is not covered by manifest include\/exclude rules: private-notes\/customer\.md/);
});

governanceTest('an unregistered private directory is not silently auto-ignored', (t) => {
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

governanceTest('supplementary content scanning detects cross-platform paths and common PII', (t) => {
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

governanceTest('artifact validation rejects cross-platform paths and PII even after integrity metadata is recomputed', (t) => {
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

governanceTest('a semantically empty runtime contract blocks validation and build', (t) => {
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

governanceTest('the declared agency runtime dependency and private runtime boundaries fail closed', (t) => {
  const manifestRoot = makeCopy(t);
  const manifestPath = join(manifestRoot, 'MANIFEST.md');
  writeFileSync(manifestPath, readFileSync(manifestPath, 'utf8').replace('dependency_mode: "declared-external-runtime"', 'dependency_mode: "self-contained"'));
  let result = runNode(manifestRoot, 'scripts/validate-sub-library.mjs');
  assert.notEqual(result.status, 0);
  assert.match(`${result.stdout}
${result.stderr}`, /must declare dependency_mode=declared-external-runtime/);

  const contractRoot = makeCopy(t);
  const contractPath = join(contractRoot, 'RUNTIME-CONTRACT.json');
  const contract = JSON.parse(readFileSync(contractPath, 'utf8'));
  delete contract.external_runtime_dependency;
  writeFileSync(contractPath, `${JSON.stringify(contract, null, 2)}
`);
  result = runNode(contractRoot, 'scripts/validate-sub-library.mjs');
  assert.notEqual(result.status, 0);
  assert.match(`${result.stdout}
${result.stderr}`, /external_runtime_dependency|agency-operations external runtime dependency/);

  const scopeRoot = makeCopy(t);
  const scopePath = join(scopeRoot, 'RUNTIME-CONTRACT.json');
  const scoped = JSON.parse(readFileSync(scopePath, 'utf8'));
  scoped.external_runtime_dependency.required_scope_keys = ['client_id', 'task_id'];
  writeFileSync(scopePath, `${JSON.stringify(scoped, null, 2)}
`);
  result = runNode(scopeRoot, 'scripts/validate-sub-library.mjs');
  assert.notEqual(result.status, 0);
  assert.match(`${result.stdout}
${result.stderr}`, /required_scope_keys|client_id\/company_id\/task_id/);

  const ignoreRoot = makeCopy(t);
  const ignorePath = join(ignoreRoot, '.gitignore');
  writeFileSync(ignorePath, readFileSync(ignorePath, 'utf8').replace(/^customer-runtime\/$/m, ''));
  result = runNode(ignoreRoot, 'scripts/validate-sub-library.mjs');
  assert.notEqual(result.status, 0);
  assert.match(`${result.stdout}
${result.stderr}`, /\.gitignore must contain private runtime boundary customer-runtime\//);
});

governanceTest('current candidate identity is separate from the immutable historical release and prepare fails closed on unassigned or colliding versions', (t) => {
  const unassignedRoot = makeCopy(t);
  const ordinaryBuild = runNode(unassignedRoot, 'scripts/build-release.mjs');
  assert.equal(ordinaryBuild.status, 0, `${ordinaryBuild.stdout}\n${ordinaryBuild.stderr}`);
  const ordinaryManifest = JSON.parse(readFileSync(join(unassignedRoot, 'dist/latest/MANIFEST.json'), 'utf8'));
  assert.equal(ordinaryManifest.version, null);
  assert.equal(ordinaryManifest.version_semantics, 'current-candidate-only');
  assert.equal(ordinaryManifest.historical_published_version, '0.3.2-preview.1');
  assert.equal(ordinaryManifest.historical_published_tag, 'v0.3.2-preview.1');
  assert.equal(ordinaryManifest.current_candidate_identity, 'unassigned');
  assert.equal(ordinaryManifest.current_candidate_snapshot, 'dirty-working-tree');
  assert.equal(ordinaryManifest.current_candidate_version, null);

  const unassignedPrepare = runNode(unassignedRoot, 'scripts/build-release.mjs', ['--prepare']);
  assert.notEqual(unassignedPrepare.status, 0);
  assert.match(`${unassignedPrepare.stdout}\n${unassignedPrepare.stderr}`, /release build requires an assigned current candidate identity and non-null current_candidate_version/);

  const collisionRoot = makeCopy(t);
  setCurrentCandidateIdentity(collisionRoot, {
    identity: 'assigned',
    snapshot: 'dirty-working-tree',
    version: '0.3.2-preview.1',
  });
  const collisionValidation = runNode(collisionRoot, 'scripts/validate-sub-library.mjs', ['--prepare']);
  assert.notEqual(collisionValidation.status, 0);
  assert.match(`${collisionValidation.stdout}\n${collisionValidation.stderr}`, /current_candidate_version must not collide with immutable historical_published_version/);
  const collisionBuild = runNode(collisionRoot, 'scripts/build-release.mjs', ['--prepare']);
  assert.notEqual(collisionBuild.status, 0);
  assert.match(`${collisionBuild.stdout}\n${collisionBuild.stderr}`, /current_candidate_version collides with immutable historical_published_version/);

  const legacyOverwriteRoot = makeCopy(t);
  setCurrentCandidateIdentity(legacyOverwriteRoot, {
    identity: 'assigned',
    snapshot: 'source-commit',
    version: '0.3.3-preview.1',
  });
  const legacyVersionPath = join(legacyOverwriteRoot, 'VERSION.md');
  const legacyVersionText = readFileSync(legacyVersionPath, 'utf8');
  assert.match(legacyVersionText, /- Version：`0\.3\.2-preview\.1`/);
  writeFileSync(legacyVersionPath, legacyVersionText.replace('- Version：`0.3.2-preview.1`', '- Version：`0.3.3-preview.1`'));
  const legacyOverwrite = runNode(legacyOverwriteRoot, 'scripts/validate-sub-library.mjs');
  assert.notEqual(legacyOverwrite.status, 0);
  assert.match(`${legacyOverwrite.stdout}\n${legacyOverwrite.stderr}`, /VERSION\.md legacy Version must equal historical_published_version/);
});

governanceTest('package-level license clearance cannot override pending source publication clearance during prepare', (t) => {
  const root = makeCopy(t);
  configureFormalCandidateSourceTree(root, { approveSourceCards: false });
  const sourceText = readFileSync(join(root, RESEARCH_SOURCE_PATH), 'utf8');
  assert.match(sourceText, /publication_review_status: "pending"/);
  assert.match(sourceText, /publication_status: "BLOCK"/);
  assert.match(sourceText, /license_status: "pending"/);

  const validation = runNode(root, 'scripts/validate-sub-library.mjs', ['--prepare']);
  assert.notEqual(validation.status, 0);
  assert.match(`${validation.stdout}\n${validation.stderr}`, /source publication clearance BLOCK for REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md/);

  const build = runNode(root, 'scripts/build-release.mjs', ['--prepare']);
  assert.notEqual(build.status, 0);
  assert.match(`${build.stdout}\n${build.stderr}`, /source publication clearance BLOCK for REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md/);
});

governanceTest('source-card identity, required fields, legal values, rename, and relocation attacks fail closed during prepare', (t) => {
  const attacks = [
    [
      'type change with clearance fields retained',
      (root) => {
        const path = join(root, RESEARCH_SOURCE_PATH);
        writeFileSync(path, setFrontMatterFields(readFileSync(path, 'utf8'), { type: 'source' }));
      },
      /source card REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md type must be exactly "source-note"/,
    ],
    [
      'all clearance fields deleted while source-note remains',
      (root) => {
        const path = join(root, RESEARCH_SOURCE_PATH);
        writeFileSync(path, deleteFrontMatterFields(readFileSync(path, 'utf8'), ['publication_review_status', 'publication_status', 'license_status']));
      },
      /source card REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md publication_review_status must be one of/,
    ],
    [
      'all source identity markers stripped at the controlled path',
      (root) => {
        const path = join(root, RESEARCH_SOURCE_PATH);
        writeFileSync(path, deleteFrontMatterFields(readFileSync(path, 'utf8'), ['type', 'publication_review_status', 'publication_status', 'license_status']));
      },
      /source card REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md type must be exactly "source-note"/,
    ],
    [
      'illegal source clearance values',
      (root) => {
        const path = join(root, RESEARCH_SOURCE_PATH);
        writeFileSync(path, setFrontMatterFields(readFileSync(path, 'utf8'), {
          publication_review_status: 'cleared',
          publication_status: 'Published',
          license_status: 'PASS',
        }));
      },
      /source card REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md publication_review_status must be one of/,
    ],
    [
      'source card renamed inside REFERENCES to a non-controlled filename',
      (root) => renameSync(
        join(root, RESEARCH_SOURCE_PATH),
        join(root, 'REFERENCES/RENAMED-B2B-SEO-CONTENT-RESEARCH.md'),
      ),
      /reference Markdown path must match REFERENCES\/SRC-\*\.md or be REFERENCES\/README\.md: REFERENCES\/RENAMED-B2B-SEO-CONTENT-RESEARCH\.md/,
    ],
    [
      'source card moved outside REFERENCES with source metadata retained',
      (root) => renameSync(
        join(root, RESEARCH_SOURCE_PATH),
        join(root, 'MOVED-B2B-SEO-CONTENT-RESEARCH.md'),
      ),
      /source card metadata must remain under REFERENCES\/SRC-\*\.md: MOVED-B2B-SEO-CONTENT-RESEARCH\.md/,
    ],
  ];

  for (const [label, attack, expected] of attacks) {
    const root = makeCopy(t);
    configureFormalCandidateSourceTree(root, { approveSourceCards: true });
    attack(root);

    const validation = runNode(root, 'scripts/validate-sub-library.mjs', ['--prepare']);
    assert.notEqual(validation.status, 0, `${label}: prepare validator must fail closed`);
    assert.match(`${validation.stdout}\n${validation.stderr}`, expected, `${label}: prepare validator source identity gate`);

    const build = runNode(root, 'scripts/build-release.mjs', ['--prepare']);
    assert.notEqual(build.status, 0, `${label}: prepare builder must fail closed`);
    assert.match(`${build.stdout}\n${build.stderr}`, expected, `${label}: prepare builder source identity gate`);
  }
});

governanceTest('source inventory binds protected IDs, card digests, and derived-page backlinks and cannot be silently shrunk', (t) => {
  const runStructureValidation = (root, label, expected) => {
    const result = runNode(root, 'scripts/validate-sub-library.mjs');
    assert.notEqual(result.status, 0, `${label}: validator must fail closed`);
    assert.match(`${result.stdout}\n${result.stderr}`, expected, label);
  };

  const baselineRoot = makeCopy(t);
  const baseline = runNode(baselineRoot, 'scripts/validate-sub-library.mjs');
  assert.equal(baseline.status, 0, `${baseline.stdout}\n${baseline.stderr}`);

  const missingProjectionRoot = makeCopy(t);
  const missingProjectionPath = join(missingProjectionRoot, SOURCE_INVENTORY_PATH);
  const missingProjectionInventory = JSON.parse(readFileSync(missingProjectionPath, 'utf8'));
  const missingProjectionEntry = missingProjectionInventory.entries.find((entry) => entry.source_id === 'SRC-20260731-B2B-SEO-CONTENT-RESEARCH');
  delete missingProjectionEntry.publication_review_status;
  writeFileSync(missingProjectionPath, `${JSON.stringify(missingProjectionInventory, null, 2)}\n`);
  runStructureValidation(
    missingProjectionRoot,
    'inventory omitted source-card publication review projection',
    /SOURCE-INVENTORY\.json source SRC-20260731-B2B-SEO-CONTENT-RESEARCH must project source card publication_review_status/,
  );

  const forgedClearanceRoot = makeCopy(t);
  const forgedClearancePath = join(forgedClearanceRoot, SOURCE_INVENTORY_PATH);
  const forgedClearanceInventory = JSON.parse(readFileSync(forgedClearancePath, 'utf8'));
  const forgedClearanceEntry = forgedClearanceInventory.entries.find((entry) => entry.source_id === 'SRC-20260731-B2B-SEO-CONTENT-RESEARCH');
  Object.assign(forgedClearanceEntry, {
    publication_review_status: 'approved',
    publication_status: 'PASS',
    license_status: 'cleared',
  });
  writeFileSync(forgedClearancePath, `${JSON.stringify(forgedClearanceInventory, null, 2)}\n`);
  runStructureValidation(
    forgedClearanceRoot,
    'inventory forged publication and license clearance without changing the source card',
    /SOURCE-INVENTORY\.json source SRC-20260731-B2B-SEO-CONTENT-RESEARCH publication_review_status does not match REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md/,
  );

  const digestRoot = makeCopy(t);
  writeFileSync(join(digestRoot, RESEARCH_SOURCE_PATH), `${readFileSync(join(digestRoot, RESEARCH_SOURCE_PATH), 'utf8')}\nDigest drift fixture.\n`);
  runStructureValidation(
    digestRoot,
    'source card content changed without inventory digest refresh',
    /SOURCE-INVENTORY\.json source SRC-20260731-B2B-SEO-CONTENT-RESEARCH card_sha256 does not match/,
  );

  const missingBacklinkRoot = makeCopy(t);
  const missingBacklinkPage = 'PLAYBOOKS/id-0003-b2b-article-optimization-sop.md';
  const missingBacklinkPath = join(missingBacklinkRoot, missingBacklinkPage);
  const missingBacklinkContent = readFileSync(missingBacklinkPath, 'utf8');
  const missingBacklinkFront = parseMarkdownFrontMatter(missingBacklinkContent, { source: missingBacklinkPage }).attributes;
  writeFileSync(missingBacklinkPath, setFrontMatterFields(missingBacklinkContent, {
    sources: missingBacklinkFront.sources.filter((value) => !value.includes('SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md')),
  }));
  runStructureValidation(
    missingBacklinkRoot,
    'inventory-derived page removed its source backlink',
    /derived page PLAYBOOKS\/id-0003-b2b-article-optimization-sop\.md must bind back to REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md/,
  );

  const unregisteredBacklinkRoot = makeCopy(t);
  const unregisteredBacklinkPage = 'BRAND.md';
  const unregisteredBacklinkPath = join(unregisteredBacklinkRoot, unregisteredBacklinkPage);
  const unregisteredBacklinkContent = readFileSync(unregisteredBacklinkPath, 'utf8');
  const unregisteredBacklinkFront = parseMarkdownFrontMatter(unregisteredBacklinkContent, { source: unregisteredBacklinkPage }).attributes;
  writeFileSync(unregisteredBacklinkPath, setFrontMatterFields(unregisteredBacklinkContent, {
    sources: [...unregisteredBacklinkFront.sources, RESEARCH_SOURCE_PATH],
  }));
  runStructureValidation(
    unregisteredBacklinkRoot,
    'derived page added a backlink without inventory registration',
    /SOURCE-INVENTORY\.json source SRC-20260731-B2B-SEO-CONTENT-RESEARCH derived_pages do not exactly match source-card backlinks/,
  );

  const shrinkRoot = makeCopy(t);
  const inventoryPath = join(shrinkRoot, SOURCE_INVENTORY_PATH);
  const inventory = JSON.parse(readFileSync(inventoryPath, 'utf8'));
  const removedEntry = inventory.entries.find((entry) => entry.source_id === 'SRC-20260731-B2B-SEO-CONTENT-RESEARCH');
  assert.ok(removedEntry, 'protected research source must exist before shrink attack');
  for (const derivedPage of removedEntry.derived_pages) {
    const pagePath = join(shrinkRoot, derivedPage);
    const content = readFileSync(pagePath, 'utf8');
    const front = parseMarkdownFrontMatter(content, { source: derivedPage }).attributes;
    writeFileSync(pagePath, setFrontMatterFields(content, {
      sources: front.sources.filter((value) => !value.includes('SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md')),
    }));
  }
  const referencesReadmePath = join(shrinkRoot, 'REFERENCES/README.md');
  const referencesReadmeContent = readFileSync(referencesReadmePath, 'utf8');
  const referencesReadmeFront = parseMarkdownFrontMatter(referencesReadmeContent, { source: 'REFERENCES/README.md' }).attributes;
  writeFileSync(referencesReadmePath, setFrontMatterFields(
    referencesReadmeContent
      .split('\n')
      .filter((line) => !line.includes('SRC-20260731-B2B-SEO-CONTENT-RESEARCH'))
      .join('\n'),
    { related: referencesReadmeFront.related.filter((value) => !value.includes('SRC-20260731-B2B-SEO-CONTENT-RESEARCH.md')) },
  ));
  const sourcesPolicyPath = join(shrinkRoot, 'SOURCES.md');
  writeFileSync(sourcesPolicyPath, readFileSync(sourcesPolicyPath, 'utf8')
    .split('\n')
    .filter((line) => !line.includes('SRC-20260731-B2B-SEO-CONTENT-RESEARCH'))
    .join('\n'));
  rmSync(join(shrinkRoot, RESEARCH_SOURCE_PATH));
  inventory.protected_source_ids = inventory.protected_source_ids.filter((sourceId) => sourceId !== 'SRC-20260731-B2B-SEO-CONTENT-RESEARCH');
  inventory.entries = inventory.entries.filter((entry) => entry.source_id !== 'SRC-20260731-B2B-SEO-CONTENT-RESEARCH');
  writeFileSync(inventoryPath, `${JSON.stringify(inventory, null, 2)}\n`);
  runStructureValidation(
    shrinkRoot,
    'source card, backlinks, and rebuilt inventory were synchronously shrunk',
    /SOURCE-INVENTORY\.json protected Source ID is missing: SRC-20260731-B2B-SEO-CONTENT-RESEARCH/,
  );
});


governanceTest('the sub-library builder binds selected files to commit provenance and rejects ignored, untracked, and modified inputs', (t) => {
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

  writeFileSync(readmePath, readFileSync(readmePath, 'utf8').replace('\n<!-- modified provenance attack -->\n', ''));
  const ordinaryBuild = runNode(root, 'scripts/build-release.mjs');
  assert.equal(ordinaryBuild.status, 0, `${ordinaryBuild.stdout}\n${ordinaryBuild.stderr}`);
  const artifactRoot = join(root, 'dist', 'latest');
  const artifactBaseline = runNode(root, 'scripts/validate-artifact.mjs', [artifactRoot]);
  assert.equal(artifactBaseline.status, 0, `${artifactBaseline.stdout}\n${artifactBaseline.stderr}`);
  const artifactManifestPath = join(artifactRoot, 'MANIFEST.json');
  const baselineArtifactManifest = readFileSync(artifactManifestPath, 'utf8');
  const assertProvenanceMutationRejected = (mutate, expected, label) => {
    writeFileSync(artifactManifestPath, baselineArtifactManifest);
    const manifest = JSON.parse(readFileSync(artifactManifestPath, 'utf8'));
    mutate(manifest);
    writeFileSync(artifactManifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
    rewriteArtifactIntegrity(artifactRoot);
    const result = runNode(root, 'scripts/validate-artifact.mjs', [artifactRoot]);
    assert.notEqual(result.status, 0, label);
    assert.match(`${result.stdout}\n${result.stderr}`, expected, label);
  };
  assertProvenanceMutationRejected(
    (manifest) => { manifest.source_provenance.schema = 'git-file-provenance/v2'; },
    /source_provenance\.schema must be git-file-provenance\/v1/,
    'ordinary sub-library artifact rejects malformed provenance schema',
  );
  assertProvenanceMutationRejected(
    (manifest) => { manifest.source_provenance.files[1].path = manifest.source_provenance.files[0].path; },
    /source_provenance\.files has duplicate path/,
    'ordinary sub-library artifact rejects duplicate provenance path',
  );
  assertProvenanceMutationRejected(
    (manifest) => { manifest.source_provenance.files.pop(); },
    /source_provenance\.files missing path/,
    'ordinary sub-library artifact rejects missing provenance path',
  );
  assertProvenanceMutationRejected(
    (manifest) => { manifest.source_provenance.files.push({ ...manifest.source_provenance.files[0], path: 'extra-provenance-record.md' }); },
    /source_provenance\.files has unmanifested path: extra-provenance-record\.md/,
    'ordinary sub-library artifact rejects extra provenance path',
  );
  assertProvenanceMutationRejected(
    (manifest) => { [manifest.source_provenance.files[0], manifest.source_provenance.files[1]] = [manifest.source_provenance.files[1], manifest.source_provenance.files[0]]; },
    /source_provenance\.files paths must exactly match MANIFEST\.json files in deterministic order/,
    'ordinary sub-library artifact rejects reordered provenance paths',
  );
  assertProvenanceMutationRejected(
    (manifest) => { manifest.source_provenance.selected_file_count += 1; },
    /source_provenance\.selected_file_count does not match file records/,
    'ordinary sub-library artifact rejects forged selected file count',
  );
  assertProvenanceMutationRejected(
    (manifest) => { manifest.source_provenance.commit_bound_file_count += 1; },
    /source_provenance\.commit_bound_file_count does not match file records/,
    'ordinary sub-library artifact rejects forged commit-bound file count',
  );
  assertProvenanceMutationRejected(
    (manifest) => { manifest.source_provenance.unbound_files = [{ ...manifest.source_provenance.files[0] }]; },
    /source_provenance\.unbound_files does not match unbound file records/,
    'ordinary sub-library artifact rejects forged unbound summary',
  );
  assertProvenanceMutationRejected(
    (manifest) => { manifest.source_provenance.missing_commit_files = [manifest.source_provenance.files[0].path]; },
    /source_provenance\.missing_commit_files overlaps packaged file/,
    'ordinary sub-library artifact rejects overlapping missing-commit path',
  );
  writeFileSync(artifactManifestPath, baselineArtifactManifest);
  rewriteArtifactIntegrity(artifactRoot);
  const toolsPath = join(artifactRoot, 'TOOLS.md');
  writeFileSync(toolsPath, `${readFileSync(toolsPath, 'utf8')}\n<!-- safe artifact provenance mutation -->\n`);
  rewriteArtifactIntegrity(artifactRoot);
  const staleReceipt = runNode(root, 'scripts/validate-artifact.mjs', [artifactRoot]);
  assert.notEqual(staleReceipt.status, 0);
  assert.match(`${staleReceipt.stdout}\n${staleReceipt.stderr}`, /source provenance file SHA mismatch: TOOLS\.md/);

  const artifactManifest = JSON.parse(readFileSync(artifactManifestPath, 'utf8'));
  const record = artifactManifest.source_provenance.files.find((item) => item.path === 'TOOLS.md');
  assert.ok(record, 'TOOLS.md provenance record missing');
  record.sha256 = sha256(artifactRoot, 'TOOLS.md');
  writeFileSync(artifactManifestPath, `${JSON.stringify(artifactManifest, null, 2)}\n`);
  rewriteArtifactIntegrity(artifactRoot);
  const forgedReceipt = runNode(root, 'scripts/validate-artifact.mjs', [artifactRoot]);
  assert.notEqual(forgedReceipt.status, 0);
  assert.match(`${forgedReceipt.stdout}\n${forgedReceipt.stderr}`, /source provenance commit SHA-256 mismatch: TOOLS\.md/);
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

function releaseEvidenceChecks(manifest, tagName, binding, candidateVersion = manifest.current_candidate_version) {
  const outputSha = '0'.repeat(64);
  const common = (command) => ({ schema: 'release-check-result/v1', command, exit_code: 0, output_sha256: outputSha });
  const validation = (id, mode) => ({ id, status: 'pass', result: { ...common(`node scripts/${id}.mjs`), mode, checked_items: 1, error_count: 0 } });
  return [
    {
      id: 'governance-tests', status: 'pass', result: {
        ...common('node --test scripts/release-governance.test.mjs'),
        test_plan: ['scripts/release-governance.test.mjs'], expected_tests: GOVERNANCE_TEST_PLAN.length, passed_tests: GOVERNANCE_TEST_PLAN.length, failed_tests: 0, skipped_tests: 0,
      },
    },
    validation('index-validation', 'strict'),
    validation('link-validation', 'release'),
    validation('document-id-validation', 'default'),
    validation('sub-library-structure-validation', 'release'),
    {
      id: 'runtime-tests', status: 'pass', result: {
        ...common('node --test upload-media-browser.test.mjs article-image-binding.test.mjs article-content-formats.test.mjs article-operations.test.mjs'),
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
        version: candidateVersion,
        candidate_content_digest: manifest.content_digest,
      },
    },
  ];
}

governanceTest('governance fixtures remain reproducible from immutable 0444/0555 freeze sources without masking setup failures', (t) => {
  const directFixtureTempRoot = mkdtempSync(join(tmpdir(), 'wco-governance-classifier-'));
  const motherFixtureTempRoot = mkdtempSync(join(tmpdir(), '701-governance-classifier-'));
  const ordinaryCheckoutTempRoot = mkdtempSync(join(tmpdir(), 'wco-fast-mode-ordinary-'));
  t.after(() => {
    for (const root of [directFixtureTempRoot, motherFixtureTempRoot, ordinaryCheckoutTempRoot]) {
      rmSync(root, { recursive: true, force: true });
    }
  });
  const directFixtureRoot = join(directFixtureTempRoot, 'website-content-ops');
  const motherFixtureRoot = join(motherFixtureTempRoot, 'repo', 'sub-libraries', 'website-content-ops');
  const ordinaryCheckoutRoot = join(ordinaryCheckoutTempRoot, 'website-content-ops');
  for (const root of [directFixtureRoot, motherFixtureRoot, ordinaryCheckoutRoot]) mkdirSync(root, { recursive: true });
  const fastEnv = { WCO_GOVERNANCE_FIXTURE_FAST: '1' };
  const motherFastEnv = { ...fastEnv, GOVERNANCE_TEST_FIXTURE: '1' };

  assert.equal(classifyGovernanceFixtureRoot(directFixtureRoot, { env: fastEnv }), 'direct');
  assert.equal(shouldUseGovernanceFixtureFastMode({ libraryRoot: directFixtureRoot, env: fastEnv }), true);
  assert.equal(classifyGovernanceFixtureRoot(motherFixtureRoot, { env: motherFastEnv }), 'mother');
  assert.equal(shouldUseGovernanceFixtureFastMode({ libraryRoot: ordinaryCheckoutRoot, env: fastEnv }), false);
  assert.equal(shouldUseGovernanceFixtureFastMode({ libraryRoot: directFixtureRoot, env: {}, releaseMode: false }), false);
  assert.equal(shouldUseGovernanceFixtureFastMode({ libraryRoot: directFixtureRoot, env: fastEnv, prepareMode: true }), false);
  assert.equal(shouldUseGovernanceFixtureFastMode({ libraryRoot: directFixtureRoot, env: fastEnv, releaseMode: true }), false);

  const systemTempRoot = realpathSync(tmpdir());
  if (systemTempRoot.startsWith('/private/')) {
    const aliasedTempRoot = systemTempRoot.slice('/private'.length);
    assert.equal(shouldUseGovernanceFixtureFastMode({ libraryRoot: directFixtureRoot, tempRoot: aliasedTempRoot, env: fastEnv }), true);
  }

  const setupError = new Error('fixture setup sentinel');
  assert.throws(
    () => rethrowSetupErrorAfterCleanup(setupError, () => { throw new Error('cleanup sentinel'); }),
    (error) => error === setupError,
    'cleanup failure must not replace the original fixture setup error',
  );

  if (process.env.WCO_IMMUTABLE_FREEZE_CHILD === '1') {
    const root = makeCopy(t);
    const probePath = join(root, 'scripts', '.owner-writable-probe');
    writeFileSync(probePath, 'owner-writable\n');
    assert.equal(readFileSync(probePath, 'utf8'), 'owner-writable\n');
    rmSync(probePath);
    return;
  }

  const freezeTempRoot = mkdtempSync(join(tmpdir(), 'wco-governance-freeze-'));
  const frozenSourceRoot = join(freezeTempRoot, 'website-content-ops');
  t.after(() => cleanupCopy(frozenSourceRoot));
  copySourceTree(sourceRoot, frozenSourceRoot);
  makeTreeImmutable(frozenSourceRoot);

  const testName = 'governance fixtures remain reproducible from immutable 0444/0555 freeze sources without masking setup failures';
  const { NODE_TEST_CONTEXT: ignoredNodeTestContext, ...childTestEnv } = process.env;
  void ignoredNodeTestContext;
  const result = spawnSync(process.execPath, [
    '--test',
    '--test-reporter=tap',
    '--test-name-pattern',
    `^${testName}$`,
    join(frozenSourceRoot, 'scripts/release-governance.test.mjs'),
  ], {
    cwd: frozenSourceRoot,
    encoding: 'utf8',
    env: { ...childTestEnv, WCO_IMMUTABLE_FREEZE_CHILD: '1' },
    timeout: GOVERNANCE_COMMAND_TIMEOUT_MS,
    killSignal: 'SIGKILL',
    maxBuffer: 16 * 1024 * 1024,
  });
  assert.equal(result.error, undefined, result.error?.message);
  assert.equal(result.signal, null, `immutable freeze regression was terminated by ${result.signal}`);
  assert.equal(result.status, 0, `immutable freeze regression failed\n${result.stdout}\n${result.stderr}`);
  assert.match(result.stdout, new RegExp(String.raw`ok \d+ - ${testName}`));
});

governanceTest('the formal runtime profile matches the adapter contract and exact 160-test plan', () => {
  const contract = JSON.parse(readFileSync(join(sourceRoot, 'ADAPTERS/cms/allincms/article-operations-contract.json'), 'utf8'));
  const localVerification = contract.localVerification;
  assert.equal(localVerification.articleOperationsTests, 48);
  assert.equal(localVerification.articleContentFormatsTests, 13);
  assert.equal(localVerification.articleImageBindingTests, 52);
  assert.equal(localVerification.mediaUploadTests, 47);
  assert.equal(localVerification.totalTests, TRUSTED_RUNTIME_TEST_COUNT);
  assert.equal(localVerification.lastVerified, '2026-09-02');
  assert.equal(localVerification.profileScope, 'article/media four-file specialized profile');
  assert.equal(localVerification.workspacePreflightTests, 21);
  assert.equal(localVerification.contentRunControllerTests, 58);
  assert.equal(localVerification.interfaceRegistryTests, 11);
  assert.equal(localVerification.adapterTotalTests, 250);
  assert.equal(
    localVerification.totalTests
      + localVerification.workspacePreflightTests
      + localVerification.contentRunControllerTests
      + localVerification.interfaceRegistryTests,
    localVerification.adapterTotalTests,
  );
  assert.equal(
    contract.localVerification.articleOperationsTests
      + contract.localVerification.articleContentFormatsTests
      + contract.localVerification.articleImageBindingTests
      + contract.localVerification.mediaUploadTests,
    TRUSTED_RUNTIME_TEST_COUNT,
  );
  const observedRuntimeTestCounts = runTrustedRuntimeTestProfile();
  assert.deepEqual(observedRuntimeTestCounts, TRUSTED_RUNTIME_TEST_PROFILE.map(({ tests }) => tests));
  assert.equal(observedRuntimeTestCounts.reduce((total, count) => total + count, 0), TRUSTED_RUNTIME_TEST_COUNT);
  const packed = spawnSync('npm', ['pack', '--dry-run', '--json'], {
    cwd: join(sourceRoot, 'ADAPTERS/cms/allincms'),
    encoding: 'utf8',
    timeout: FIXTURE_SETUP_TIMEOUT_MS,
    killSignal: 'SIGKILL',
  });
  assert.equal(packed.error, undefined, packed.error?.message);
  assert.equal(packed.status, 0, `${packed.stdout}\n${packed.stderr}`);
  const files = JSON.parse(packed.stdout)[0].files.map((entry) => entry.path);
  const allowedPackagedRedactedContracts = new Set([
    'media-operations-contract.redacted.json',
    'observed-contract.redacted.json',
  ]);
  assert.deepEqual(
    files.filter((path) => /\.redacted\.(?:md|json)$/.test(path)).sort(),
    [...allowedPackagedRedactedContracts].sort(),
  );
  for (const path of files) {
    assert.doesNotMatch(path, /(^|\/)(node_modules|fixtures|coverage)(\/|$)/);
    assert.doesNotMatch(path, /(?:^|\/).+\.test\.mjs$/);
    if (/\.redacted\.(?:md|json)$/.test(path)) assert.equal(allowedPackagedRedactedContracts.has(path), true);
    assert.doesNotMatch(path, /\.(?:png|jpe?g|gif|webp)$/i);
  }
});

function prepareFormalQualificationFixture(t) {
  const root = makeCopy(t);
  const candidateVersion = configureFormalCandidateSourceTree(root, { approveSourceCards: true });
  const build = runNode(root, 'scripts/build-release.mjs', ['--prepare'], { env: { SOURCE_DATE_EPOCH: '0' } });
  assert.equal(build.status, 0, `${build.stdout}\n${build.stderr}`);
  const candidateRoot = `${build.stdout}\n${build.stderr}`.match(/(?:PREPARED_UNAPPROVED_CANDIDATE|PREPARED_CANDIDATE_REUSED): (.+)/)?.[1]?.trim();
  assert.ok(candidateRoot, 'prepare mode must report the content-addressed candidate path');
  const manifest = JSON.parse(readFileSync(join(candidateRoot, 'MANIFEST.json'), 'utf8'));
  assert.equal(manifest.version, candidateVersion);
  assert.equal(manifest.current_candidate_version, candidateVersion);
  assert.equal(manifest.current_candidate_identity, 'assigned');
  assert.equal(manifest.historical_published_version, '0.3.2-preview.1');
  assert.notEqual(manifest.version, manifest.historical_published_version);
  const tagName = `sub-library/${manifest.package_id}/v${manifest.current_candidate_version}`;
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
      immutable_locator: `https://releases.example.com/${manifest.package_id}/v${manifest.current_candidate_version}/${manifest.content_digest}/candidate`,
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
    version: manifest.current_candidate_version,
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

function mutateFrozenManifestAndRebindSidecars(fixture, mutateManifest) {
  const manifestPath = join(fixture.candidateRoot, 'MANIFEST.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  mutateManifest(manifest);
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  rewriteArtifactIntegrity(fixture.candidateRoot);

  const reboundManifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const attackerSelectedVersion = reboundManifest.version;
  const tagName = `sub-library/${reboundManifest.package_id}/v${attackerSelectedVersion}`;
  const approval = JSON.parse(readFileSync(fixture.approvalPath, 'utf8'));
  approval.candidate.content_digest = reboundManifest.content_digest;
  approval.candidate.manifest_sha256 = sha256(fixture.candidateRoot, 'MANIFEST.json');
  approval.candidate.sha256sums_sha256 = sha256(fixture.candidateRoot, 'SHA256SUMS');
  approval.candidate.immutable_locator = `https://releases.example.com/${reboundManifest.package_id}/v${attackerSelectedVersion}/${reboundManifest.content_digest}/candidate`;
  approval.tag.name = tagName;
  approval.tag.approval_binding_sha256 = canonicalDigest(approvalBindingProjection(approval));

  const annotation = {
    approval_binding_sha256: approval.tag.approval_binding_sha256,
    approval_id: approval.approval_id,
    candidate_content_digest: reboundManifest.content_digest,
    schema: 'release-tag-annotation/v1',
    scope: { kind: approval.scope.kind, id: approval.scope.id },
    version: attackerSelectedVersion,
  };
  const annotationText = canonicalJson(annotation);
  approval.tag.annotation_sha256 = createHash('sha256').update(annotationText, 'utf8').digest('hex');
  const binding = {
    tagObjectSha: approval.tag.object_sha,
    signerFingerprint: approval.tag.signer_fingerprint,
    annotationSha256: approval.tag.annotation_sha256,
    approvalBindingSha256: approval.tag.approval_binding_sha256,
    approvalId: approval.approval_id,
  };

  const evidence = JSON.parse(readFileSync(fixture.evidencePath, 'utf8'));
  evidence.candidate = {
    content_digest: reboundManifest.content_digest,
    manifest_sha256: approval.candidate.manifest_sha256,
    sha256sums_sha256: approval.candidate.sha256sums_sha256,
  };
  evidence.checks = releaseEvidenceChecks(reboundManifest, tagName, binding, attackerSelectedVersion);
  approval.validation.evidence_digest = canonicalDigest(evidence);
  writeFileSync(fixture.approvalPath, `${JSON.stringify(approval, null, 2)}\n`);
  writeFileSync(fixture.evidencePath, `${JSON.stringify(evidence, null, 2)}\n`);

  const fakeGitFixture = JSON.parse(readFileSync(fixture.fakeGitFixturePath, 'utf8'));
  fakeGitFixture.sourceCommit = reboundManifest.source_commit;
  fakeGitFixture.tagName = tagName;
  fakeGitFixture.annotationText = annotationText;
  fakeGitFixture.records = reboundManifest.source_provenance.files;
  writeFileSync(fixture.fakeGitFixturePath, `${JSON.stringify(fakeGitFixture, null, 2)}\n`);

  Object.assign(fixture.env, {
    RELEASE_TRIGGER_TAG: tagName,
    RELEASE_ACTUAL_TAG_ANNOTATION_SHA256: binding.annotationSha256,
    RELEASE_ACTUAL_TAG_ANNOTATION_BASE64: Buffer.from(annotationText, 'utf8').toString('base64'),
    RELEASE_ACTUAL_APPROVAL_BINDING_SHA256: binding.approvalBindingSha256,
  });
}

function restorePendingResearchSourceInsideCandidate(fixture) {
  setResearchSourceClearance(fixture.candidateRoot, false);
  const manifestPath = join(fixture.candidateRoot, 'MANIFEST.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  for (const changedPath of [RESEARCH_SOURCE_PATH, SOURCE_INVENTORY_PATH]) {
    const record = manifest.source_provenance.files.find((item) => item.path === changedPath);
    assert.ok(record, `${changedPath} provenance record missing from prepared candidate`);
    record.sha256 = sha256(fixture.candidateRoot, changedPath);
    record.commit_sha256 = record.sha256;
  }
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  mutateFrozenManifestAndRebindSidecars(fixture, () => {});
}

function mutateFrozenSourceCardAndRebindSidecars(fixture, {
  sourcePath = RESEARCH_SOURCE_PATH,
  destinationPath = sourcePath,
  mutateContent,
}) {
  const originalPath = join(fixture.candidateRoot, sourcePath);
  const destination = join(fixture.candidateRoot, destinationPath);
  const mutatedContent = mutateContent(readFileSync(originalPath, 'utf8'));
  if (destinationPath !== sourcePath) {
    mkdirSync(dirname(destination), { recursive: true });
    renameSync(originalPath, destination);
  }
  writeFileSync(destination, mutatedContent);

  const manifestPath = join(fixture.candidateRoot, 'MANIFEST.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const fileIndex = manifest.files.indexOf(sourcePath);
  assert.notEqual(fileIndex, -1, `prepared candidate manifest is missing ${sourcePath}`);
  manifest.files[fileIndex] = destinationPath;
  manifest.files.sort();

  const record = manifest.source_provenance.files.find((item) => item.path === sourcePath);
  assert.ok(record, `prepared candidate provenance is missing ${sourcePath}`);
  const repositoryPrefix = record.repository_path.slice(0, -sourcePath.length);
  assert.ok(record.repository_path.endsWith(sourcePath), `repository path must end with ${sourcePath}`);
  record.path = destinationPath;
  record.repository_path = `${repositoryPrefix}${destinationPath}`;
  record.sha256 = sha256(fixture.candidateRoot, destinationPath);
  record.commit_sha256 = record.sha256;
  manifest.source_provenance.files.sort((left, right) => left.path.localeCompare(right.path));
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  mutateFrozenManifestAndRebindSidecars(fixture, () => {});
}

governanceTest('pending source clearance independently blocks approval and artifact qualification even when package license is cleared', (t) => {
  const fixture = prepareFormalQualificationFixture(t);
  restorePendingResearchSourceInsideCandidate(fixture);
  const manifest = JSON.parse(readFileSync(join(fixture.candidateRoot, 'MANIFEST.json'), 'utf8'));
  assert.equal(manifest.license_status, 'cleared');

  const approval = runNode(fixture.candidateRoot, 'scripts/validate-release-approval.mjs', [fixture.candidateRoot, fixture.approvalPath, fixture.evidencePath], { env: fixture.env });
  assert.notEqual(approval.status, 0);
  assert.match(`${approval.stdout}\n${approval.stderr}`, /source publication clearance BLOCK for REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md/);
  assert.match(`${approval.stdout}\n${approval.stderr}`, /candidate package license_status cannot override source-level clearance/);

  const qualification = runNode(fixture.candidateRoot, 'scripts/validate-artifact.mjs', ['--release', fixture.candidateRoot], { env: fixture.env });
  assert.notEqual(qualification.status, 0);
  assert.match(`${qualification.stdout}\n${qualification.stderr}`, /source publication clearance BLOCK for REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md/);
});

governanceTest('frozen source-card identity, field, value, rename, and relocation attacks block approval and artifact qualification after self-consistent rebinding', (t) => {
  const fixture = prepareFormalQualificationFixture(t);
  const baseline = {
    source: readFileSync(join(fixture.candidateRoot, RESEARCH_SOURCE_PATH), 'utf8'),
    manifest: readFileSync(join(fixture.candidateRoot, 'MANIFEST.json'), 'utf8'),
    sums: readFileSync(join(fixture.candidateRoot, 'SHA256SUMS'), 'utf8'),
    approval: readFileSync(fixture.approvalPath, 'utf8'),
    evidence: readFileSync(fixture.evidencePath, 'utf8'),
    fakeGit: readFileSync(fixture.fakeGitFixturePath, 'utf8'),
    env: { ...fixture.env },
  };
  const renamedPath = 'REFERENCES/RENAMED-B2B-SEO-CONTENT-RESEARCH.md';
  const movedPath = 'MOVED-B2B-SEO-CONTENT-RESEARCH.md';
  const attacks = [
    [
      'type change with fields retained',
      { mutateContent: (content) => setFrontMatterFields(content, { type: 'source' }) },
      /source card REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md type must be exactly "source-note"/,
    ],
    [
      'all clearance fields deleted',
      { mutateContent: (content) => deleteFrontMatterFields(content, ['publication_review_status', 'publication_status', 'license_status']) },
      /source card REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md publication_review_status must be one of/,
    ],
    [
      'all source markers stripped',
      { mutateContent: (content) => deleteFrontMatterFields(content, ['type', 'publication_review_status', 'publication_status', 'license_status']) },
      /source card REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md type must be exactly "source-note"/,
    ],
    [
      'illegal source clearance values',
      {
        mutateContent: (content) => setFrontMatterFields(content, {
          publication_review_status: 'cleared',
          publication_status: 'Published',
          license_status: 'PASS',
        }),
      },
      /source card REFERENCES\/SRC-20260731-B2B-SEO-CONTENT-RESEARCH\.md publication_review_status must be one of/,
    ],
    [
      'rename inside REFERENCES',
      { destinationPath: renamedPath, mutateContent: (content) => content },
      /reference Markdown path must match REFERENCES\/SRC-\*\.md or be REFERENCES\/README\.md: REFERENCES\/RENAMED-B2B-SEO-CONTENT-RESEARCH\.md/,
    ],
    [
      'move outside REFERENCES with metadata retained',
      { destinationPath: movedPath, mutateContent: (content) => content },
      /source card metadata must remain under REFERENCES\/SRC-\*\.md: MOVED-B2B-SEO-CONTENT-RESEARCH\.md/,
    ],
  ];

  for (const [label, attack, expected] of attacks) {
    rmSync(join(fixture.candidateRoot, renamedPath), { force: true });
    rmSync(join(fixture.candidateRoot, movedPath), { force: true });
    writeFileSync(join(fixture.candidateRoot, RESEARCH_SOURCE_PATH), baseline.source);
    writeFileSync(join(fixture.candidateRoot, 'MANIFEST.json'), baseline.manifest);
    writeFileSync(join(fixture.candidateRoot, 'SHA256SUMS'), baseline.sums);
    writeFileSync(fixture.approvalPath, baseline.approval);
    writeFileSync(fixture.evidencePath, baseline.evidence);
    writeFileSync(fixture.fakeGitFixturePath, baseline.fakeGit);
    Object.assign(fixture.env, baseline.env);

    mutateFrozenSourceCardAndRebindSidecars(fixture, attack);
    const reboundApproval = JSON.parse(readFileSync(fixture.approvalPath, 'utf8'));
    assert.equal(reboundApproval.candidate.manifest_sha256, sha256(fixture.candidateRoot, 'MANIFEST.json'), `${label}: approval must bind the recomputed manifest checksum`);
    assert.equal(reboundApproval.candidate.sha256sums_sha256, sha256(fixture.candidateRoot, 'SHA256SUMS'), `${label}: approval must bind the recomputed checksum sidecar`);

    const approval = runNode(fixture.candidateRoot, 'scripts/validate-release-approval.mjs', [fixture.candidateRoot, fixture.approvalPath, fixture.evidencePath], { env: fixture.env });
    assert.notEqual(approval.status, 0, `${label}: approval must fail closed`);
    assert.match(`${approval.stdout}\n${approval.stderr}`, expected, `${label}: approval source identity gate`);

    const qualification = runNode(fixture.candidateRoot, 'scripts/validate-artifact.mjs', ['--release', fixture.candidateRoot], { env: fixture.env });
    assert.notEqual(qualification.status, 0, `${label}: artifact qualification must fail closed`);
    assert.match(`${qualification.stdout}\n${qualification.stderr}`, expected, `${label}: qualification source identity gate`);
  }
});

governanceTest('post-build frozen MANIFEST identity drift blocks approval and artifact qualification after self-consistent sidecar recomputation', (t) => {
  const fixture = prepareFormalQualificationFixture(t);
  const baseline = {
    manifest: readFileSync(join(fixture.candidateRoot, 'MANIFEST.json'), 'utf8'),
    sums: readFileSync(join(fixture.candidateRoot, 'SHA256SUMS'), 'utf8'),
    approval: readFileSync(fixture.approvalPath, 'utf8'),
    evidence: readFileSync(fixture.evidencePath, 'utf8'),
    fakeGit: readFileSync(fixture.fakeGitFixturePath, 'utf8'),
    env: { ...fixture.env },
  };
  const attacks = [
    ['generated version reuses historical version', (manifest) => { manifest.version = manifest.historical_published_version; }, /MANIFEST\.json version must equal current_candidate_version/],
    ['current candidate version drifts after build', (manifest) => { manifest.current_candidate_version = '0.3.4-preview.1'; }, /MANIFEST\.json version must equal current_candidate_version/],
    ['version semantics drifts after build', (manifest) => { manifest.version_semantics = 'legacy-or-historical'; }, /MANIFEST\.json version_semantics must be current-candidate-only/],
    ['candidate snapshot becomes dirty after build', (manifest) => { manifest.current_candidate_snapshot = 'dirty-working-tree'; }, /MANIFEST\.json current_candidate_snapshot must be a safe non-dirty value/],
    ['historical tag drifts after build', (manifest) => { manifest.historical_published_tag = 'v0.3.2-preview.2'; }, /MANIFEST\.json historical_published_tag must equal v<historical_published_version>/],
    ['candidate identity becomes a placeholder after build', (manifest) => { manifest.current_candidate_identity = 'unassigned'; }, /MANIFEST\.json current_candidate_identity must be an assigned non-placeholder string/],
  ];

  for (const [label, mutate, expected] of attacks) {
    writeFileSync(join(fixture.candidateRoot, 'MANIFEST.json'), baseline.manifest);
    writeFileSync(join(fixture.candidateRoot, 'SHA256SUMS'), baseline.sums);
    writeFileSync(fixture.approvalPath, baseline.approval);
    writeFileSync(fixture.evidencePath, baseline.evidence);
    writeFileSync(fixture.fakeGitFixturePath, baseline.fakeGit);
    Object.assign(fixture.env, baseline.env);

    mutateFrozenManifestAndRebindSidecars(fixture, mutate);
    const reboundApproval = JSON.parse(readFileSync(fixture.approvalPath, 'utf8'));
    assert.equal(reboundApproval.candidate.manifest_sha256, sha256(fixture.candidateRoot, 'MANIFEST.json'), `${label}: approval must bind the recomputed manifest checksum`);
    assert.equal(reboundApproval.candidate.sha256sums_sha256, sha256(fixture.candidateRoot, 'SHA256SUMS'), `${label}: approval must bind the recomputed checksum sidecar`);

    const approval = runNode(fixture.candidateRoot, 'scripts/validate-release-approval.mjs', [fixture.candidateRoot, fixture.approvalPath, fixture.evidencePath], { env: fixture.env });
    assert.notEqual(approval.status, 0, `${label}: approval must fail closed`);
    assert.match(`${approval.stdout}\n${approval.stderr}`, expected, `${label}: approval identity invariant`);

    const qualification = runNode(fixture.candidateRoot, 'scripts/validate-artifact.mjs', ['--release', fixture.candidateRoot], { env: fixture.env });
    assert.notEqual(qualification.status, 0, `${label}: qualification must fail closed`);
    assert.match(`${qualification.stdout}\n${qualification.stderr}`, expected, `${label}: qualification identity invariant`);
  }
});

governanceTest('formal qualification binds workflow tag identity and canonical approval data without claiming human identity', (t) => {
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
  const governanceEvidenceAttacks = [
    ['stale governance count', (result) => { result.expected_tests -= 1; result.passed_tests -= 1; }, /governance-tests expected_tests must match the current registered governance plan/],
    ['wrong governance test plan', (result) => { result.test_plan = ['scripts/legacy-governance.test.mjs']; }, /governance-tests test_plan must exactly equal/],
  ];
  for (const [label, mutate, expected] of governanceEvidenceAttacks) {
    const approvalRecord = JSON.parse(baselineApproval);
    const evidenceRecord = JSON.parse(baselineEvidence);
    const governanceResult = evidenceRecord.checks.find((check) => check.id === 'governance-tests').result;
    mutate(governanceResult);
    approvalRecord.validation.evidence_digest = canonicalDigest(evidenceRecord);
    writeFileSync(fixture.approvalPath, `${JSON.stringify(approvalRecord, null, 2)}\n`);
    writeFileSync(fixture.evidencePath, `${JSON.stringify(evidenceRecord, null, 2)}\n`);
    const result = runNode(fixture.candidateRoot, 'scripts/validate-release-approval.mjs', [fixture.candidateRoot, fixture.approvalPath, fixture.evidencePath], { env: fixture.env });
    assert.notEqual(result.status, 0, label);
    assert.match(`${result.stdout}\n${result.stderr}`, expected, label);
  }
  writeFileSync(fixture.approvalPath, baselineApproval);
  writeFileSync(fixture.evidencePath, baselineEvidence);

  const runtimeEvidenceAttacks = [
    ['stale 156/156 count', (result) => { result.expected_tests = 156; result.passed_tests = 156; }, /runtime-tests expected_tests must be 160/],
    ['stale 158/158 count', (result) => { result.expected_tests = 158; result.passed_tests = 158; }, /runtime-tests expected_tests must be 160/],
    ['off-by-one low 159/159 count', (result) => { result.expected_tests = 159; result.passed_tests = 159; }, /runtime-tests expected_tests must be 160/],
    ['off-by-one high 161/161 count', (result) => { result.expected_tests = 161; result.passed_tests = 161; }, /runtime-tests expected_tests must be 160/],
    ['partial pass count', (result) => { result.passed_tests = 159; }, /must bind exact all-pass counts with no failed or skipped tests/],
    ['non-zero failed count', (result) => { result.passed_tests = 159; result.failed_tests = 1; }, /must bind exact all-pass counts with no failed or skipped tests/],
    ['non-zero skipped count', (result) => { result.passed_tests = 159; result.skipped_tests = 1; }, /must bind exact all-pass counts with no failed or skipped tests/],
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

assert.deepEqual(
  registeredGovernanceTests,
  GOVERNANCE_TEST_PLAN,
  'GOVERNANCE_TEST_PLAN must exactly match the registered top-level governance tests in order',
);
if (listGovernancePlanOnly) {
  console.log(`GOVERNANCE_TEST_PLAN_JSON: ${JSON.stringify(GOVERNANCE_TEST_PLAN)}`);
}
