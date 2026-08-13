#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { extname, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { scanPublishableContent } from './content-safety.mjs';

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

const safeVersionPattern = /^[0-9A-Za-z][0-9A-Za-z._-]*$/;
const placeholderCandidateIdentities = new Set(['unassigned', 'unknown', 'pending', 'placeholder', 'tbd', 'todo', 'null', 'none', 'n/a']);
function manifestString(value) {
  return typeof value === 'string' ? value.trim() : '';
}
function validateFrozenManifestIdentity(manifest) {
  const versionSemantics = manifestString(manifest?.version_semantics);
  const currentCandidateIdentity = manifestString(manifest?.current_candidate_identity);
  const currentCandidateSnapshot = manifestString(manifest?.current_candidate_snapshot);
  const currentCandidateVersion = manifestString(manifest?.current_candidate_version);
  const manifestVersion = manifestString(manifest?.version);
  const historicalPublishedVersion = manifestString(manifest?.historical_published_version);
  const historicalPublishedTag = manifestString(manifest?.historical_published_tag);

  if (versionSemantics !== 'current-candidate-only') fail('MANIFEST.json version_semantics must be current-candidate-only');
  if (!currentCandidateIdentity || placeholderCandidateIdentities.has(currentCandidateIdentity.toLowerCase())) fail('MANIFEST.json current_candidate_identity must be an assigned non-placeholder string');
  if (!currentCandidateSnapshot || !safeVersionPattern.test(currentCandidateSnapshot) || currentCandidateSnapshot === 'dirty-working-tree') fail('MANIFEST.json current_candidate_snapshot must be a safe non-dirty value');
  if (!currentCandidateVersion || !safeVersionPattern.test(currentCandidateVersion)) fail('MANIFEST.json current_candidate_version must be a safe non-empty version');
  if (manifestVersion !== currentCandidateVersion) fail('MANIFEST.json version must equal current_candidate_version');
  if (!historicalPublishedVersion || !safeVersionPattern.test(historicalPublishedVersion)) fail('MANIFEST.json historical_published_version must be a safe non-empty version');
  if (historicalPublishedTag !== `v${historicalPublishedVersion}`) fail('MANIFEST.json historical_published_tag must equal v<historical_published_version>');
  if (currentCandidateVersion && historicalPublishedVersion && currentCandidateVersion === historicalPublishedVersion) fail('MANIFEST.json current_candidate_version must not equal historical_published_version');
  if (currentCandidateVersion && historicalPublishedTag && `v${currentCandidateVersion}` === historicalPublishedTag) fail('MANIFEST.json current candidate tag must not collide with historical_published_tag');

  return currentCandidateVersion;
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
  const currentCandidateVersion = releaseMode || prepareMode ? validateFrozenManifestIdentity(manifest) : manifestString(manifest?.current_candidate_version);
  if (manifest?.package_kind !== 'sub-library-release-candidate') fail('MANIFEST.json package_kind must be sub-library-release-candidate');
  if (prepareMode && manifest?.qualification_state !== 'prepared-unapproved') fail('prepared artifact qualification_state must be prepared-unapproved');
  if (releaseMode && manifest?.qualification_state !== 'prepared-unapproved') fail('release qualification only accepts a frozen prepared-unapproved candidate');
  if (releaseMode && manifest?.release_status !== 'Ready') fail('release qualification candidate release_status must be Ready');
  if (releaseMode && manifest?.approval_status !== 'pending') fail('release qualification frozen candidate approval_status must remain pending');
  if (releaseMode) {
    const normalized = artifactRoot.split('\\').join('/');
    const expectedSuffix = `/prepared/v${currentCandidateVersion}/${manifest?.content_digest}`;
    if (!normalized.endsWith(expectedSuffix)) fail(`release qualification requires the exact content-addressed prepared path ending ${expectedSuffix}`);
  }
  const embeddedManifest = existsSync(join(artifactRoot, 'MANIFEST.md')) ? readFileSync(join(artifactRoot, 'MANIFEST.md'), 'utf8') : '';
  const durableLine = embeddedManifest.match(/^durable_roots:\s*(\[[^\n]*\])/m)?.[1] ?? '[]';
  const embeddedDurableRoots = [...durableLine.matchAll(/"([^"]*)"|'([^']*)'/g)].map((m) => m[1] ?? m[2]);
  if (JSON.stringify(manifest?.durable_roots ?? []) !== JSON.stringify(embeddedDurableRoots)) fail('MANIFEST.json durable_roots does not match MANIFEST.md');
  if (!listed.size) fail('MANIFEST.json files list is empty');
  if (!/^[0-9a-f]{40}$/.test(manifest?.source_commit ?? '')) fail('MANIFEST.json source_commit must be a 40-character Git SHA');
  if (typeof manifest?.source_dirty !== 'boolean') fail('MANIFEST.json source_dirty must be boolean');
  if ((releaseMode || prepareMode) && manifest?.source_dirty) fail('prepared/release artifact must be built from a clean source worktree');
  if ((releaseMode || prepareMode) && (manifest?.source_commit_rebuildable !== true || manifest?.source_snapshot_kind !== 'source-commit' || manifest?.source_selected_dirty !== false)) fail('prepared/release artifact must be fully rebuildable from its source commit');
  if (listed.size !== files.length) fail('MANIFEST.json files list contains duplicates');
  validateSourceProvenance(manifest, files);
  if (JSON.stringify(files) !== JSON.stringify([...files].sort())) fail('MANIFEST.json files list must be sorted for deterministic artifacts');
  if (manifest?.content_digest !== contentDigest(artifactRoot, files)) fail('MANIFEST.json content_digest does not match listed file content');
  for (const file of listed) {
    if (file.startsWith('/') || file.includes('..')) fail(`unsafe manifest path: ${file}`);
    if (!existsSync(join(artifactRoot, file))) fail(`manifest file missing: ${file}`);
  }
  const actual = new Set(walk(artifactRoot).map((path) => relative(artifactRoot, path)));
  for (const file of actual) if (!['MANIFEST.json', 'SHA256SUMS'].includes(file) && !listed.has(file)) fail(`unlisted artifact file: ${file}`);

  // Artifact-level redaction checks are intentionally repeated after packaging.
  // A correct checksum only proves integrity, not that the packaged content is safe.
  // The allowlist is fail-closed: any file type not declared here blocks the artifact.
  const allowedArtifactExtensions = new Set(['.md', '.json', '.mjs', '.yml', '.yaml']);
  const allowedExtensionlessArtifactFiles = new Set(['.gitignore', '.npmignore', 'LICENSE', 'NOTICE']);
  for (const file of actual) {
    if (['MANIFEST.json', 'SHA256SUMS'].includes(file)) continue;
    const ext = extname(file).toLowerCase();
    if (!allowedArtifactExtensions.has(ext) && !allowedExtensionlessArtifactFiles.has(file.split('/').at(-1))) {
      fail(`unsupported artifact file extension: ${file}`);
      continue;
    }
    const content = readFileSync(join(artifactRoot, file), 'utf8');
    for (const issue of scanPublishableContent(content)) fail(`content safety ${issue.code} in artifact: ${file}`);
  }
  const sums = readFileSync(join(artifactRoot, 'SHA256SUMS'), 'utf8').trim().split('\n').filter(Boolean);
  const map = new Map();
  for (const line of sums) { const match = line.match(/^([a-f0-9]{64})  (.+)$/); if (!match) fail(`invalid checksum line: ${line}`); else if (map.has(match[2])) fail(`duplicate checksum entry: ${match[2]}`); else map.set(match[2], match[1]); }
  const expectedChecksumFiles = new Set([...listed, 'MANIFEST.json']);
  for (const file of map.keys()) if (!expectedChecksumFiles.has(file)) fail(`checksum lists unmanifested file: ${file}`);
  for (const file of expectedChecksumFiles) if (!map.has(file)) fail(`checksum missing file: ${file}`);
  for (const file of [...listed, 'MANIFEST.json']) {
    if (map.get(file) !== sha256(join(artifactRoot, file))) fail(`checksum mismatch: ${file}`);
  }
  for (const path of actual) if (path.includes('/dist/') || path === 'dist' || path === 'dist/latest') fail(`nested build output in artifact: ${path}`);
  if (releaseMode) {
    const approvalPath = process.env.RELEASE_APPROVAL_PATH?.trim();
    const evidencePath = process.env.RELEASE_EVIDENCE_PATH?.trim();
    const approvalValidator = join(artifactRoot, 'scripts', 'validate-release-approval.mjs');
    const workflowBindingFields = [
      'RELEASE_ACTUAL_TAG_OBJECT_SHA',
      'RELEASE_ACTUAL_TAG_SIGNER_FINGERPRINT',
      'RELEASE_ACTUAL_TAG_ANNOTATION_SHA256',
      'RELEASE_ACTUAL_TAG_ANNOTATION_BASE64',
      'RELEASE_ACTUAL_APPROVAL_BINDING_SHA256',
    ];
    if (!approvalPath) fail('release qualification requires RELEASE_APPROVAL_PATH sidecar');
    if (!evidencePath) fail('release qualification requires RELEASE_EVIDENCE_PATH bundle');
    for (const field of workflowBindingFields) {
      if (!process.env[field]?.trim()) fail(`release qualification requires workflow-injected ${field}`);
    }
    if (!existsSync(approvalValidator)) fail('release artifact is missing scripts/validate-release-approval.mjs for final approval gate');
    if (approvalPath && evidencePath && workflowBindingFields.every((field) => process.env[field]?.trim()) && existsSync(approvalValidator)) {
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
  if (!failures.length && (releaseMode || prepareMode)) {
    // These are the child artifact's available release validators; do not assume
    // mother-library validators exist in a standalone sub-library package.
    runEmbeddedValidator('validate-links.mjs', ['--release', artifactRoot]);
    runEmbeddedValidator('sync-workspace-template.mjs', ['--check']);
    runEmbeddedValidator('validate-sub-library.mjs', ['--prepare']);
  } else if (!failures.length) {
    runEmbeddedValidator('validate-sub-library.mjs');
  }
}
if (releaseMode && qualificationTreeBefore && treeDigest(artifactRoot) !== qualificationTreeBefore) fail('release qualification modified the frozen candidate tree');
if (failures.length) { for (const failure of failures) console.error(`FAIL: ${failure}`); process.exit(1); }
if (releaseMode) {
  console.log(`ARTIFACT_QUALIFICATION_RECORD_PASS: ${artifactRoot}`);
  console.log('QUALIFICATION_LIMIT: frozen candidate integrity plus approval/evidence/canonical-tag/workflow binding passed; approver identity, reviewer independence, remote signer allowlist, Protected Environment, workflow origin, publication, and Published status are not verified here.');
} else {
  console.log(`ARTIFACT_PASS: ${artifactRoot}`);
}
