#!/usr/bin/env node
import {
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  writeFileSync,
} from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';

const PROFILES = new Map([
  ['website-content-ops', {
    adapterPath: 'sub-libraries/website-content-ops/ADAPTERS/cms/allincms',
    packageFiles: ['package.json', 'package-lock.json'],
    implementationFiles: [
      'upload-media-browser.mjs',
      'article-image-binding.mjs',
      'article-operations.mjs',
    ],
    testFiles: [
      'upload-media-browser.test.mjs',
      'article-image-binding.test.mjs',
      'article-operations.test.mjs',
    ],
    expectedTests: 131,
  }],
]);

const CONTROL_FILES = [
  '.npmrc',
  '.yarnrc',
  '.yarnrc.yml',
  'bun.lock',
  'bun.lockb',
  'deno.json',
  'deno.jsonc',
  'npm-shrinkwrap.json',
  'package-lock.json',
  'package.json',
  'pnpm-lock.yaml',
  'pnpm-workspace.yaml',
  'yarn.lock',
];

function fail(message) {
  console.error(`BLOCK: ${message}`);
  process.exit(1);
}

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!flag?.startsWith('--') || value === undefined) fail('runtime profile arguments must use --name value pairs');
    if (values[flag.slice(2)] !== undefined) fail(`runtime profile argument is duplicated: ${flag}`);
    values[flag.slice(2)] = value;
  }
  return values;
}

function lexicalPathInside(root, path, label) {
  const rel = relative(root, path);
  if (!rel || rel === '.' || (!rel.startsWith(`..${sep}`) && rel !== '..' && !isAbsolute(rel))) return;
  fail(`${label} escapes its declared root: ${path}`);
}

function assertRoot(path, label) {
  if (!path || !isAbsolute(path)) fail(`${label} must be an absolute path`);
  const resolved = resolve(path);
  let stat;
  try {
    stat = lstatSync(resolved);
  } catch {
    fail(`${label} does not exist: ${resolved}`);
  }
  if (!stat.isDirectory() || stat.isSymbolicLink()) fail(`${label} must be a real directory: ${resolved}`);
  return { lexical: resolved, real: realpathSync(resolved) };
}

function assertDirectoryChain(root, target, label) {
  const resolvedTarget = resolve(target);
  lexicalPathInside(root.lexical, resolvedTarget, label);
  const rel = relative(root.lexical, resolvedTarget);
  const parts = rel.split(sep).filter(Boolean);
  let current = root.lexical;
  for (const part of parts) {
    current = join(current, part);
    let stat;
    try {
      stat = lstatSync(current);
    } catch {
      fail(`${label} is missing: ${current}`);
    }
    if (!stat.isDirectory() || stat.isSymbolicLink()) fail(`${label} contains a non-directory or symlink ancestor: ${current}`);
    lexicalPathInside(root.real, realpathSync(current), `${label} realpath`);
  }
  return resolvedTarget;
}

function regularFileState(root, path, label) {
  try {
    const stat = lstatSync(path);
    if (!stat.isFile() || stat.isSymbolicLink()) return { kind: 'unsafe' };
    lexicalPathInside(root.real, realpathSync(path), `${label} realpath`);
    return { kind: 'file', bytes: readFileSync(path) };
  } catch (error) {
    if (error?.code === 'ENOENT') return { kind: 'missing' };
    throw error;
  }
}

function assertSameFile(trustedRoot, candidateRoot, trustedPath, candidatePath, label, required = false) {
  const trusted = regularFileState(trustedRoot, trustedPath, label);
  const candidate = regularFileState(candidateRoot, candidatePath, label);
  if (trusted.kind === 'unsafe' || candidate.kind === 'unsafe') fail(`${label} must be a regular non-symlink file`);
  if (required && (trusted.kind !== 'file' || candidate.kind !== 'file')) fail(`${label} is required in trusted and candidate trees`);
  if (trusted.kind !== candidate.kind) fail(`runtime control file mismatch for ${label}`);
  if (trusted.kind === 'file' && !trusted.bytes.equals(candidate.bytes)) fail(`runtime control file mismatch for ${label}`);
}

function assertProfiledFile(root, adapter, name, label) {
  const path = join(adapter, name);
  const state = regularFileState(root, path, label);
  if (state.kind !== 'file') fail(`${label} must be a regular non-symlink file`);
  return { path, bytes: state.bytes };
}

function ancestry(root, target) {
  const rel = relative(root.lexical, target);
  lexicalPathInside(root.lexical, target, 'runtime adapter path');
  const parts = rel.split(sep).filter(Boolean);
  return Array.from({ length: parts.length + 1 }, (_, index) => join(root.lexical, ...parts.slice(0, index)));
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function prepareSubject(subjectPath, packageId, profile, trustedRoot, candidateRoot, trustedAdapter, candidateAdapter) {
  if (!subjectPath || !isAbsolute(subjectPath)) fail('subject root must be an absolute path');
  const subject = resolve(subjectPath);
  if (existsSync(subject)) fail(`subject root must not already exist: ${subject}`);
  const parent = dirname(subject);
  let parentStat;
  try {
    parentStat = lstatSync(parent);
  } catch {
    fail(`subject root parent does not exist: ${parent}`);
  }
  if (!parentStat.isDirectory() || parentStat.isSymbolicLink()) fail(`subject root parent must be a real directory: ${parent}`);
  mkdirSync(subject, { mode: 0o755 });

  const manifest = {
    schema_version: 1,
    package_id: packageId,
    adapter_path: profile.adapterPath,
    expected_tests: profile.expectedTests,
    files: [],
  };
  const copyProfileFile = (name, sourceRole, sourceRoot, sourceAdapter) => {
    const label = `${profile.adapterPath}/${name}`;
    const source = assertProfiledFile(sourceRoot, sourceAdapter, name, label);
    const target = join(subject, name);
    copyFileSync(source.path, target);
    const copied = readFileSync(target);
    if (!copied.equals(source.bytes)) fail(`runtime subject copy mismatch for ${label}`);
    manifest.files.push({ path: name, source: sourceRole, sha256: sha256(copied) });
  };

  for (const file of profile.packageFiles) copyProfileFile(file, 'candidate-byte-equal-to-trusted', candidateRoot, candidateAdapter);
  for (const file of profile.implementationFiles) copyProfileFile(file, 'candidate-implementation', candidateRoot, candidateAdapter);
  for (const file of profile.testFiles) copyProfileFile(file, 'trusted-governance-test', trustedRoot, trustedAdapter);
  writeFileSync(join(subject, 'RUNTIME-SUBJECT.json'), `${JSON.stringify(manifest, null, 2)}\n`, { mode: 0o644 });
  return subject;
}

const args = parseArgs(process.argv.slice(2));
const packageId = args['package-id'];
const profile = PROFILES.get(packageId);
if (!profile) fail(`no trusted formal qualification test profile exists for sub-library ${packageId || 'missing'}`);

const trustedRoot = assertRoot(args['trusted-root'], 'trusted root');
const candidateRoot = assertRoot(args['candidate-root'], 'candidate root');
const trustedAdapter = assertDirectoryChain(trustedRoot, resolve(trustedRoot.lexical, profile.adapterPath), 'trusted adapter path');
const candidateAdapter = assertDirectoryChain(candidateRoot, resolve(candidateRoot.lexical, profile.adapterPath), 'candidate adapter path');

for (const packageFile of profile.packageFiles) {
  assertSameFile(
    trustedRoot,
    candidateRoot,
    join(trustedAdapter, packageFile),
    join(candidateAdapter, packageFile),
    `${profile.adapterPath}/${packageFile}`,
    true,
  );
}

const trustedTests = readdirSync(trustedAdapter, { withFileTypes: true })
  .filter((entry) => entry.isFile() && entry.name.endsWith('.test.mjs'))
  .map((entry) => entry.name)
  .sort();
const candidateTests = readdirSync(candidateAdapter, { withFileTypes: true })
  .filter((entry) => entry.isFile() && entry.name.endsWith('.test.mjs'))
  .map((entry) => entry.name)
  .sort();
const expectedTests = [...profile.testFiles].sort();
if (trustedTests.join('\0') !== expectedTests.join('\0') || candidateTests.join('\0') !== expectedTests.join('\0')) {
  fail(`runtime-test file set does not match the explicit trusted profile for ${packageId}`);
}
for (const testFile of profile.testFiles) {
  assertSameFile(
    trustedRoot,
    candidateRoot,
    join(trustedAdapter, testFile),
    join(candidateAdapter, testFile),
    `${profile.adapterPath}/${testFile}`,
    true,
  );
}
for (const implementationFile of profile.implementationFiles) {
  assertProfiledFile(trustedRoot, trustedAdapter, implementationFile, `${profile.adapterPath}/${implementationFile}`);
  assertProfiledFile(candidateRoot, candidateAdapter, implementationFile, `${profile.adapterPath}/${implementationFile}`);
}

const trustedAncestry = ancestry(trustedRoot, trustedAdapter);
const candidateAncestry = ancestry(candidateRoot, candidateAdapter);
for (let index = 0; index < trustedAncestry.length; index += 1) {
  const relDir = relative(trustedRoot.lexical, trustedAncestry[index]) || '.';
  for (const controlFile of CONTROL_FILES) {
    if (relDir === profile.adapterPath && profile.packageFiles.includes(controlFile)) continue;
    assertSameFile(
      trustedRoot,
      candidateRoot,
      join(trustedAncestry[index], controlFile),
      join(candidateAncestry[index], controlFile),
      `${relDir}/${controlFile}`,
    );
  }
}

const subject = prepareSubject(
  args['subject-root'],
  packageId,
  profile,
  trustedRoot,
  candidateRoot,
  trustedAdapter,
  candidateAdapter,
);
console.log(`RUNTIME_TEST_PROFILE_PASS: package_id=${packageId} tests=${profile.testFiles.length} expected_assertions=${profile.expectedTests}`);
console.log(`RUNTIME_TEST_SUBJECT_READY: ${subject}`);
