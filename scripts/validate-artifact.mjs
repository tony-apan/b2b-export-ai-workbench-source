#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, readdirSync } from 'node:fs';
import { extname, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const args = process.argv.slice(2);
const releaseMode = args.includes('--release');
const prepareMode = args.includes('--prepare');
if (releaseMode && prepareMode) { console.error('FAIL: --prepare and --release are mutually exclusive'); process.exit(1); }
const artifactRoot = resolve(args.find((arg) => !arg.startsWith('--')) ?? '.');
const failures = [];
const fail = (message) => failures.push(message);
const sha256 = (path) => createHash('sha256').update(readFileSync(path)).digest('hex');
function treeDigest(root) {
  const hash = createHash('sha256');
  for (const path of walk(root).map((item) => relative(root, item)).sort()) hash.update(`${path}\0${sha256(join(root, path))}\n`);
  return hash.digest('hex');
}
function contentDigest(root, files) {
  const hash = createHash('sha256');
  for (const file of files) hash.update(`${file}\0${sha256(join(root, file))}\n`);
  return hash.digest('hex');
}
function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isSymbolicLink()) { fail(`symlink is not allowed in artifact: ${relative(artifactRoot, path)}`); continue; }
    if (entry.isDirectory()) out.push(...walk(path)); else out.push(path);
  }
  return out;
}
function validateManifestFilePath(file) {
  if (typeof file !== 'string' || !file || file.includes('\0') || file.includes('\r') || file.includes('\n') || file.startsWith('/') || file.includes('\\')) {
    fail(`unsafe manifest path: ${String(file)}`);
    return false;
  }
  const segments = file.split('/');
  if (segments.some((segment) => !segment || segment === '.' || segment === '..')) {
    fail(`unsafe manifest path: ${file}`);
    return false;
  }
  let current = artifactRoot;
  for (const [index, segment] of segments.entries()) {
    current = join(current, segment);
    if (!existsSync(current)) {
      fail(`manifest file missing: ${file}`);
      return false;
    }
    const stat = lstatSync(current);
    if (stat.isSymbolicLink()) {
      fail(`manifest path must not traverse a symlink: ${file}`);
      return false;
    }
    if (index < segments.length - 1 && !stat.isDirectory()) {
      fail(`manifest path ancestor is not a directory: ${file}`);
      return false;
    }
    if (index === segments.length - 1 && !stat.isFile()) {
      fail(`manifest path is not a regular file: ${file}`);
      return false;
    }
  }
  return true;
}
function runEmbeddedValidator(scriptName, validatorArgs = []) {
  const validatorPath = join(artifactRoot, 'scripts', scriptName);
  if (!existsSync(validatorPath)) {
    fail(`artifact is missing embedded validator: scripts/${scriptName}`);
    return;
  }
  const result = spawnSync(process.execPath, [validatorPath, ...validatorArgs], {
    cwd: artifactRoot,
    encoding: 'utf8',
  });
  process.stdout.write(result.stdout ?? '');
  process.stderr.write(result.stderr ?? '');
  if (result.error) {
    fail(`could not execute embedded validator: ${scriptName}: ${result.error.message}`);
  } else if (result.status !== 0) {
    fail(`embedded release validator failed: ${scriptName}`);
  }
}
if (!existsSync(join(artifactRoot, 'MANIFEST.json'))) fail('missing MANIFEST.json');
if (!existsSync(join(artifactRoot, 'SHA256SUMS'))) fail('missing SHA256SUMS');
const qualificationTreeBefore = releaseMode && !failures.length ? treeDigest(artifactRoot) : '';
if (!failures.length) {
  let manifest;
  try { manifest = JSON.parse(readFileSync(join(artifactRoot, 'MANIFEST.json'), 'utf8')); } catch { fail('MANIFEST.json is invalid JSON'); }
  const files = Array.isArray(manifest?.files) ? manifest.files : [];
  const listed = new Set(files);
  if (manifest?.package_kind !== 'mother-library-release-candidate') fail('MANIFEST.json package_kind must be mother-library-release-candidate');
  if (prepareMode && manifest?.qualification_state !== 'prepared-unapproved') fail('prepared artifact qualification_state must be prepared-unapproved');
  if (releaseMode && manifest?.qualification_state !== 'prepared-unapproved') fail('release qualification only accepts a frozen prepared-unapproved candidate');
  if (releaseMode && manifest?.release_status !== 'Ready') fail('release qualification candidate release_status must be Ready');
  if (releaseMode && manifest?.approval_status !== 'pending') fail('release qualification frozen candidate approval_status must remain pending');
  if (releaseMode) {
    const normalized = artifactRoot.split('\\').join('/');
    const expectedSuffix = `/prepared/v${manifest?.version}/${manifest?.content_digest}`;
    if (!normalized.endsWith(expectedSuffix)) fail(`release qualification requires the exact content-addressed prepared path ending ${expectedSuffix}`);
  }
  const embeddedRegistryPath = join(artifactRoot, 'sub-libraries', 'registry.json');
  if (existsSync(embeddedRegistryPath) && Array.isArray(manifest?.children)) {
    try {
      const registry = JSON.parse(readFileSync(embeddedRegistryPath, 'utf8'));
      for (const entry of registry.entries ?? []) {
        const child = manifest.children.find((item) => item.id === entry.id);
        if (!child || JSON.stringify(child.durable_roots ?? []) !== JSON.stringify(entry.durable_roots ?? [])) fail(`MANIFEST.json child durable_roots mismatch: ${entry.id}`);
      }
    } catch { fail('embedded sub-libraries/registry.json is invalid JSON'); }
  }
  if (!listed.size) fail('MANIFEST.json files list is empty');
  if (!/^[0-9a-f]{40}$/.test(manifest?.source_commit ?? '')) fail('MANIFEST.json source_commit must be a 40-character Git SHA');
  if (typeof manifest?.source_dirty !== 'boolean') fail('MANIFEST.json source_dirty must be boolean');
  if ((releaseMode || prepareMode) && manifest?.source_dirty) fail('prepared/release artifact must be built from a clean source worktree');
  if ((releaseMode || prepareMode) && (manifest?.source_commit_rebuildable !== true || manifest?.source_snapshot_kind !== 'source-commit' || manifest?.source_selected_dirty !== false)) fail('prepared/release artifact must be fully rebuildable from its source commit');
  if (listed.size !== files.length) fail('MANIFEST.json files list contains duplicates');
  if (JSON.stringify(files) !== JSON.stringify([...files].sort())) fail('MANIFEST.json files list must be sorted for deterministic artifacts');
  const safeListed = new Set([...listed].filter((file) => validateManifestFilePath(file)));
  if (safeListed.size !== listed.size) {
    for (const failure of failures) console.error(`FAIL: ${failure}`);
    process.exit(1);
  }
  if (safeListed.size === listed.size && manifest?.content_digest !== contentDigest(artifactRoot, files)) fail('MANIFEST.json content_digest does not match listed file content');
  const actual = new Set(walk(artifactRoot).map((path) => relative(artifactRoot, path)));
  for (const file of actual) if (!['MANIFEST.json', 'SHA256SUMS'].includes(file) && !listed.has(file)) fail(`unlisted artifact file: ${file}`);

  // Artifact-level redaction checks are intentionally repeated after packaging.
  // A correct checksum only proves integrity, not that the packaged content is safe.
  // The allowlist is fail-closed: any file type not declared here blocks the artifact.
  const allowedArtifactExtensions = new Set(['.md', '.json', '.mjs', '.yml', '.yaml']);
  const allowedExtensionlessArtifactFiles = new Set(['.gitignore']);
  const absolutePathPattern = /(?:\/Users\/[A-Za-z0-9._-]+\/|\/(?:private\/)?var\/folders\/[A-Za-z0-9._-]+\/|\/tmp\/[A-Za-z0-9._-]+\/)/;
  const credentialPattern = /(?:api[_ -]?key|access[_ -]?token|secret|password|cookie|authorization)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}/i;
  for (const file of actual) {
    if (['MANIFEST.json', 'SHA256SUMS'].includes(file)) continue;
    const ext = extname(file).toLowerCase();
    if (!allowedArtifactExtensions.has(ext) && !allowedExtensionlessArtifactFiles.has(file.split('/').at(-1))) {
      fail(`unsupported artifact file extension: ${file}`);
      continue;
    }
    const content = readFileSync(join(artifactRoot, file), 'utf8');
    if (absolutePathPattern.test(content)) fail(`possible local absolute path in artifact: ${file}`);
    if (credentialPattern.test(content)) fail(`possible credential assignment in artifact: ${file}`);
  }
  const sums = readFileSync(join(artifactRoot, 'SHA256SUMS'), 'utf8').trim().split('\n').filter(Boolean);
  const map = new Map();
  for (const line of sums) { const match = line.match(/^([a-f0-9]{64})  (.+)$/); if (!match) fail(`invalid checksum line: ${line}`); else if (map.has(match[2])) fail(`duplicate checksum entry: ${match[2]}`); else map.set(match[2], match[1]); }
  const expectedChecksumFiles = new Set([...listed, 'MANIFEST.json']);
  for (const file of map.keys()) if (!expectedChecksumFiles.has(file)) fail(`checksum lists unmanifested file: ${file}`);
  for (const file of expectedChecksumFiles) if (!map.has(file)) fail(`checksum missing file: ${file}`);
  for (const file of [...safeListed, 'MANIFEST.json']) {
    if (map.get(file) !== sha256(join(artifactRoot, file))) fail(`checksum mismatch: ${file}`);
  }
  for (const path of actual) if (path.includes('/dist/') || path === 'dist' || path === 'dist/latest') fail(`nested build output in artifact: ${path}`);
  if (releaseMode) {
    const approvalPath = process.env.RELEASE_APPROVAL_PATH?.trim();
    const evidencePath = process.env.RELEASE_EVIDENCE_PATH?.trim();
    const approvalValidator = join(artifactRoot, 'scripts', 'validate-release-approval.mjs');
    if (!approvalPath) fail('release qualification requires RELEASE_APPROVAL_PATH sidecar');
    else if (!evidencePath) fail('release qualification requires RELEASE_EVIDENCE_PATH bundle');
    else if (!existsSync(approvalValidator)) fail('release artifact is missing scripts/validate-release-approval.mjs for final approval gate');
    else {
      const approvalResult = spawnSync(process.execPath, [approvalValidator, artifactRoot, resolve(approvalPath), resolve(evidencePath)], {
        cwd: artifactRoot,
        encoding: 'utf8',
        env: { ...process.env, RELEASE_REQUIRE_GIT_TAG: '1' },
      });
      process.stdout.write(approvalResult.stdout ?? '');
      process.stderr.write(approvalResult.stderr ?? '');
      if (approvalResult.error) fail(`could not execute release approval validator: ${approvalResult.error.message}`);
      else if (approvalResult.status !== 0) fail('release approval sidecar/tag gate failed');
    }
  }
  if (releaseMode) {
    runEmbeddedValidator('validate-indexes.mjs', ['--strict']);
    runEmbeddedValidator('validate-links.mjs', ['--release', artifactRoot]);
    runEmbeddedValidator('validate-logs.mjs', ['--release']);
    runEmbeddedValidator('validate-knowledge-chain.mjs', ['--release']);
    runEmbeddedValidator('validate-mother-library.mjs', ['--prepare']);
  } else if (prepareMode) {
    runEmbeddedValidator('validate-indexes.mjs', ['--strict']);
    runEmbeddedValidator('validate-links.mjs', ['--release', artifactRoot]);
    runEmbeddedValidator('validate-logs.mjs', ['--release']);
    runEmbeddedValidator('validate-knowledge-chain.mjs');
    runEmbeddedValidator('validate-mother-library.mjs', ['--prepare']);
  } else {
    runEmbeddedValidator('validate-mother-library.mjs');
  }
}
if (releaseMode && qualificationTreeBefore && treeDigest(artifactRoot) !== qualificationTreeBefore) fail('release qualification modified the frozen candidate tree');
if (failures.length) { for (const failure of failures) console.error(`FAIL: ${failure}`); process.exit(1); }
console.log(`ARTIFACT_PASS: ${artifactRoot}`);
