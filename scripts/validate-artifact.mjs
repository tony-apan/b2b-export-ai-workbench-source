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

function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string' || typeof value === 'number') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (typeof value !== 'object') return JSON.stringify(String(value));
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
}
function validateSourceProvenance(manifest, files) {
  const provenance = manifest?.source_provenance;
  if (!provenance || typeof provenance !== 'object' || Array.isArray(provenance)) {
    fail('MANIFEST.json source_provenance must be an object');
    return;
  }
  if (provenance.schema !== 'git-file-provenance/v1') fail('MANIFEST.json source_provenance.schema must be git-file-provenance/v1');
  if (provenance.source_commit !== manifest.source_commit) fail('MANIFEST.json source_provenance.source_commit must equal source_commit');
  if (Object.hasOwn(provenance, 'source_scope') && provenance.source_scope !== manifest.source_scope) fail('MANIFEST.json source_provenance.source_scope must equal source_scope');

  const records = Array.isArray(provenance.files) ? provenance.files : [];
  if (!Array.isArray(provenance.files)) fail('MANIFEST.json source_provenance.files must be an array');
  const recordPaths = [];
  const seenPaths = new Set();
  const allowedGitStates = new Set(['committed', 'modified', 'untracked', 'ignored']);
  const hex64 = /^[a-f0-9]{64}$/;
  const gitObject = /^[a-f0-9]{40,64}$/;

  for (const [index, record] of records.entries()) {
    const label = `MANIFEST.json source_provenance.files[${index}]`;
    if (!record || typeof record !== 'object' || Array.isArray(record)) {
      fail(`${label} must be an object`);
      continue;
    }
    const path = record.path;
    if (typeof path !== 'string' || !path) {
      fail(`${label}.path must be a non-empty string`);
      continue;
    }
    recordPaths.push(path);
    if (seenPaths.has(path)) fail(`MANIFEST.json source_provenance.files has duplicate path: ${path}`);
    seenPaths.add(path);
    if (!files.includes(path)) fail(`MANIFEST.json source_provenance.files has unmanifested path: ${path}`);
    if (!hex64.test(record.sha256 ?? '')) fail(`${label}.sha256 must be a lowercase SHA-256 digest`);
    else if (files.includes(path) && record.sha256 !== sha256(join(artifactRoot, path))) fail(`source provenance file SHA mismatch: ${path}`);
    if (!allowedGitStates.has(record.git_state)) fail(`${label}.git_state is invalid: ${String(record.git_state)}`);
    if (typeof record.commit_bound !== 'boolean') fail(`${label}.commit_bound must be boolean`);

    if (record.commit_bound === true) {
      if (record.git_state !== 'committed') fail(`${label} commit_bound=true requires git_state committed`);
      if (!gitObject.test(record.commit_blob ?? '')) fail(`${label}.commit_blob must be a Git object SHA when commit_bound=true`);
      if (!hex64.test(record.commit_sha256 ?? '')) fail(`${label}.commit_sha256 must be a SHA-256 digest when commit_bound=true`);
      else if (record.commit_sha256 !== record.sha256) fail(`source provenance commit SHA-256 mismatch: ${path}`);
    } else if (record.commit_bound === false) {
      if (record.git_state === 'committed') fail(`${label} commit_bound=false cannot use git_state committed`);
      if (record.git_state === 'modified') {
        if (!gitObject.test(record.commit_blob ?? '')) fail(`${label}.commit_blob must be a Git object SHA when git_state=modified`);
        if (!hex64.test(record.commit_sha256 ?? '')) fail(`${label}.commit_sha256 must be a SHA-256 digest when git_state=modified`);
        else if (record.commit_sha256 === record.sha256) fail(`${label} git_state=modified requires different candidate and commit SHA-256 values`);
      } else if (record.git_state === 'untracked' || record.git_state === 'ignored') {
        if (record.commit_blob !== null) fail(`${label}.commit_blob must be null when git_state=${record.git_state}`);
        if (record.commit_sha256 !== undefined && record.commit_sha256 !== null) fail(`${label}.commit_sha256 must be omitted when git_state=${record.git_state}`);
      }
    }
  }

  if (recordPaths.length === files.length && recordPaths.some((path, index) => path !== files[index])) {
    fail('MANIFEST.json source_provenance.files paths must exactly match MANIFEST.json files in deterministic order');
  }
  for (const file of files) if (!seenPaths.has(file)) fail(`MANIFEST.json source_provenance.files missing path: ${file}`);

  const computedUnbound = records.filter((record) => record && record.commit_bound === false);
  if (!Array.isArray(provenance.unbound_files)) fail('MANIFEST.json source_provenance.unbound_files must be an array');
  else if (canonicalJson(provenance.unbound_files) !== canonicalJson(computedUnbound)) fail('MANIFEST.json source_provenance.unbound_files does not match unbound file records');

  const missing = Array.isArray(provenance.missing_commit_files) ? provenance.missing_commit_files : [];
  if (!Array.isArray(provenance.missing_commit_files)) fail('MANIFEST.json source_provenance.missing_commit_files must be an array');
  else {
    const seenMissing = new Set();
    for (const path of missing) {
      if (typeof path !== 'string' || !path || path.startsWith('/') || path.includes('\\') || path.split('/').some((segment) => !segment || segment === '.' || segment === '..')) fail(`unsafe source_provenance.missing_commit_files path: ${String(path)}`);
      else if (seenMissing.has(path)) fail(`duplicate source_provenance.missing_commit_files path: ${path}`);
      else if (seenPaths.has(path)) fail(`source_provenance.missing_commit_files overlaps packaged file: ${path}`);
      seenMissing.add(path);
    }
  }

  const commitBoundCount = records.filter((record) => record?.commit_bound === true).length;
  const commitRebuildable = records.length === files.length && commitBoundCount === records.length && missing.length === 0;
  if (provenance.selected_file_count !== records.length) fail('MANIFEST.json source_provenance.selected_file_count does not match file records');
  if (provenance.commit_bound_file_count !== commitBoundCount) fail('MANIFEST.json source_provenance.commit_bound_file_count does not match file records');
  if (provenance.commit_rebuildable !== commitRebuildable) fail('MANIFEST.json source_provenance.commit_rebuildable does not match file records');
  if (manifest.source_commit_rebuildable !== commitRebuildable) fail('MANIFEST.json source_commit_rebuildable does not match source_provenance records');
  if (manifest.source_selected_dirty !== !commitRebuildable) fail('MANIFEST.json source_selected_dirty does not match source_provenance records');
  const expectedSnapshotKind = commitRebuildable ? 'source-commit' : 'working-tree-snapshot';
  if (manifest.source_snapshot_kind !== expectedSnapshotKind) fail(`MANIFEST.json source_snapshot_kind must be ${expectedSnapshotKind}`);
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
  validateSourceProvenance(manifest, files);
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
  const allowedArtifactExtensions = new Set(['.md', '.json', '.mjs', '.yml', '.yaml', '.tsv', '.txt', '.jsonl', '.sh', '.py', '.cmd']);
  const allowedExtensionlessArtifactFiles = new Set(['.gitignore', '.gitattributes', '.npmignore', 'LICENSE', 'NOTICE']);
  const absolutePathPattern = /(?:\/Users\/[A-Za-z0-9._-]+\/|\/(?:private\/)?var\/folders\/[A-Za-z0-9._-]+\/|\/tmp\/[A-Za-z0-9._-]+\/)/;
  const credentialPattern = /(?:api[_ -]?key|access[_ -]?token|secret|password|cookie|authorization)\s*[:=]\s*["'"]?([A-Za-z0-9_./+=-]{12,})/i;
  for (const file of actual) {
    if (['MANIFEST.json', 'SHA256SUMS'].includes(file)) continue;
    const ext = extname(file).toLowerCase();
    if (!allowedArtifactExtensions.has(ext) && !allowedExtensionlessArtifactFiles.has(file.split('/').at(-1))) {
      fail(`unsupported artifact file extension: ${file}`);
      continue;
    }
    const content = readFileSync(join(artifactRoot, file), 'utf8');
    if (absolutePathPattern.test(content)) fail(`possible local absolute path in artifact: ${file}`);
    const _cm = content.match(credentialPattern);
    if (_cm) {
      const _cv = (_cm[1] ?? '').replace(/[=._-]+$/, '');
      const _safe = [/^[A-Za-z_$][A-Za-z0-9_$]*\.[A-Za-z_$][A-Za-z0-9_$]*$/, /^\$[A-Za-z_][A-Za-z0-9_]*$/, /^[a-z]+(?:-[a-z]+)+$/, /^[a-z]+(?:_[a-z]+)+$/, /^(?:[a-z][a-z-]*-)?(?:key|token|cookie|secret|password|authorization)$/i].some(r => r.test(_cv));
      if (!_safe) fail(`possible credential assignment in artifact: ${file}`);
    }
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
  if (!failures.length && releaseMode) {
    runEmbeddedValidator('validate-indexes.mjs', ['--strict']);
    runEmbeddedValidator('validate-links.mjs', ['--release', artifactRoot]);
    runEmbeddedValidator('validate-logs.mjs', ['--release']);
    runEmbeddedValidator('validate-knowledge-chain.mjs', ['--release']);
    runEmbeddedValidator('validate-mother-library.mjs', ['--prepare']);
  } else if (!failures.length && prepareMode) {
    runEmbeddedValidator('validate-indexes.mjs', ['--strict']);
    runEmbeddedValidator('validate-links.mjs', ['--release', artifactRoot]);
    runEmbeddedValidator('validate-logs.mjs', ['--release']);
    runEmbeddedValidator('validate-knowledge-chain.mjs');
    runEmbeddedValidator('validate-mother-library.mjs', ['--prepare']);
  } else if (!failures.length) {
    runEmbeddedValidator('validate-mother-library.mjs');
  }
}
if (releaseMode && qualificationTreeBefore && treeDigest(artifactRoot) !== qualificationTreeBefore) fail('release qualification modified the frozen candidate tree');
if (failures.length) { for (const failure of failures) console.error(`FAIL: ${failure}`); process.exit(1); }
console.log(`ARTIFACT_PASS: ${artifactRoot}`);
